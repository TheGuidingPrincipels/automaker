"""Event listener that reacts to repository events for confidence scoring."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from models.events import Event

if TYPE_CHECKING:
    from services.outbox import Outbox
from services.confidence.cache_manager import CacheManager
from services.confidence.composite_calculator import CompositeCalculator
from services.confidence.config import ConfidenceConfig
from services.confidence.models import Error, Success
from services.event_store import EventStore
from services.neo4j_service import Neo4jService


logger = logging.getLogger(__name__)


@dataclass
class PendingRecalc:
    """Represents a pending confidence recalculation item."""

    recalc_id: str
    concept_id: str
    event_id: str
    event_offset: int
    retry_count: int
    last_attempt: Optional[datetime]
    error_message: Optional[str]
    status: str
    created_at: datetime


@dataclass
class ListenerCheckpoint:
    """Persisted checkpoint for the event listener."""

    last_offset: int = 0
    last_event_id: str | None = None

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "last_offset": self.last_offset,
            "last_event_id": self.last_event_id,
        }

    @classmethod
    def from_file(cls, path: Path) -> ListenerCheckpoint:
        try:
            with path.open("r", encoding="utf-8") as fp:
                raw = json.load(fp)
        except FileNotFoundError:
            return cls()
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to read confidence listener checkpoint %s: %s. " "Starting from offset 0.",
                path,
                exc,
            )
            return cls()

        last_offset = int(raw.get("last_offset", 0))
        last_event_id = raw.get("last_event_id")
        return cls(last_offset=last_offset, last_event_id=last_event_id)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as fp:
            json.dump(self.to_dict(), fp)
        temp_path.replace(path)


class ConfidenceEventListener:
    """
    Polls the EventStore and keeps Neo4j/Redis confidence data in sync.

    The listener processes concept lifecycle events in order. For creations
    and updates it recalculates the composite confidence score and persists
    it to Neo4j as `confidence_score`. For deletions it clears cached
    confidence data.

    Lock failure handling:
        When a distributed lock cannot be acquired during relationship event
        processing, the concept is queued to a persistent SQLite table for
        later retry. This ensures no concept is ever lost due to lock contention.
    """

    # Use absolute paths based on project root to avoid CWD-dependent issues
    # when launched by Claude Desktop or other external processes
    _PROJECT_ROOT = Path(__file__).parent.parent.parent
    DEFAULT_CHECKPOINT = _PROJECT_ROOT / "data" / "confidence" / "checkpoint.json"
    DEFAULT_RECALC_DB = _PROJECT_ROOT / "data" / "confidence" / "pending_recalc.db"

    # Pending recalculation statuses
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_ESCALATED = "escalated"

    _HANDLED_EVENT_TYPES = {
        "ConceptCreated",
        "ConceptUpdated",
        "ConceptDeleted",
        "ConceptTauUpdated",
        "RelationshipCreated",
        "RelationshipDeleted",
    }

    def __init__(
        self,
        event_store: EventStore,
        calculator: CompositeCalculator,
        cache_manager: CacheManager,
        neo4j_service: Neo4jService,
        *,
        checkpoint_path: Optional[Path | str] = None,
        recalc_db_path: Optional[Path | str] = None,
        outbox: Optional["Outbox"] = None,  # For dead letter escalation
    ) -> None:
        self.event_store = event_store
        self.calculator = calculator
        self.cache = cache_manager
        self.neo4j = neo4j_service
        self.outbox = outbox
        self.checkpoint_path = Path(checkpoint_path or self.DEFAULT_CHECKPOINT)
        self.recalc_db_path = Path(recalc_db_path or self.DEFAULT_RECALC_DB)

        self._checkpoint = ListenerCheckpoint.from_file(self.checkpoint_path)

        # Configuration for retry behavior
        self._config = ConfidenceConfig()

        # SQLite connection for pending recalculations
        self._recalc_conn: Optional[sqlite3.Connection] = None
        self._recalc_lock = threading.Lock()
        self._init_recalc_db()

    def _init_recalc_db(self) -> None:
        """Initialize the SQLite database for pending recalculations."""
        self.recalc_db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = self._get_recalc_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_confidence_recalc (
                recalc_id TEXT PRIMARY KEY,
                concept_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                event_offset INTEGER NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_attempt DATETIME,
                error_message TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(concept_id, event_offset)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pending_status
            ON pending_confidence_recalc(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pending_offset
            ON pending_confidence_recalc(event_offset)
        """)

        conn.commit()
        logger.debug("Initialized pending recalculation database at %s", self.recalc_db_path)

    def _get_recalc_connection(self) -> sqlite3.Connection:
        """Get SQLite connection for pending recalculations (thread-safe)."""
        with self._recalc_lock:
            need_new_connection = self._recalc_conn is None
            if not need_new_connection:
                try:
                    self._recalc_conn.execute("SELECT 1")
                except sqlite3.ProgrammingError:
                    need_new_connection = True
                    self._recalc_conn = None

            if need_new_connection:
                self._recalc_conn = sqlite3.connect(
                    self.recalc_db_path,
                    check_same_thread=False,
                    timeout=30.0,
                )
                self._recalc_conn.row_factory = sqlite3.Row
                self._recalc_conn.execute("PRAGMA journal_mode = WAL")
                logger.debug("Created recalc DB connection to %s", self.recalc_db_path)

            return self._recalc_conn

    def close_recalc_db(self) -> None:
        """Close the pending recalculation database connection."""
        with self._recalc_lock:
            if self._recalc_conn is not None:
                try:
                    self._recalc_conn.close()
                    logger.debug("Closed pending recalculation DB connection")
                except Exception as exc:
                    logger.warning("Error closing recalc DB connection: %s", exc)
                finally:
                    self._recalc_conn = None

    async def _queue_pending_recalc(
        self,
        concept_id: str,
        event_id: str,
        event_offset: int,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Add concept to pending recalculation queue for retry.

        Uses SQLite for crash-safe persistence. If the concept is already
        queued for this event offset, increments retry count instead.
        """
        recalc_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        try:
            conn = self._get_recalc_connection()
            cursor = conn.cursor()

            # UPSERT: insert if new, increment retry if exists
            cursor.execute(
                """
                INSERT INTO pending_confidence_recalc
                    (recalc_id, concept_id, event_id, event_offset, error_message, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(concept_id, event_offset) DO UPDATE SET
                    retry_count = retry_count + 1,
                    last_attempt = ?,
                    error_message = COALESCE(?, error_message),
                    status = CASE
                        WHEN retry_count + 1 >= ? THEN ?
                        ELSE ?
                    END
                """,
                (
                    recalc_id,
                    concept_id,
                    event_id,
                    event_offset,
                    error_message,
                    self.STATUS_PENDING,
                    now,
                    now,
                    error_message,
                    self._config.MAX_RECALC_RETRIES,
                    self.STATUS_ESCALATED,
                    self.STATUS_PENDING,
                ),
            )

            conn.commit()

            # Check if escalation needed
            cursor.execute(
                """
                SELECT retry_count, status FROM pending_confidence_recalc
                WHERE concept_id = ? AND event_offset = ?
                """,
                (concept_id, event_offset),
            )

            row = cursor.fetchone()
            if row and row["status"] == self.STATUS_ESCALATED:
                await self._escalate_to_outbox(concept_id, event_id, error_message)
                logger.error(
                    "Concept %s exceeded max retries (%d), escalated to dead letter",
                    concept_id,
                    self._config.MAX_RECALC_RETRIES,
                )
            else:
                logger.warning(
                    "Queued concept %s for recalculation retry (attempt %d)",
                    concept_id,
                    row["retry_count"] if row else 1,
                )

        except Exception as exc:
            logger.error("Failed to queue pending recalc for %s: %s", concept_id, exc)
            # Critical: Even if queueing fails, NOT advancing checkpoint will cause retry

    async def _escalate_to_outbox(
        self,
        concept_id: str,
        event_id: str,
        error_message: Optional[str],
    ) -> None:
        """Escalate repeatedly failing concept to outbox for manual intervention."""
        if self.outbox:
            try:
                # Use projection_name to encode concept_id for tracking
                self.outbox.add_to_outbox(
                    event_id=event_id,
                    projection_name=f"confidence_recalc_escalated:{concept_id}",
                )
                logger.error(
                    "ESCALATED: Concept %s added to outbox dead letter queue",
                    concept_id,
                )
            except Exception as exc:
                logger.error(
                    "Failed to escalate concept %s to outbox: %s",
                    concept_id,
                    exc,
                )
        else:
            logger.error(
                "ESCALATED: Concept %s requires manual intervention (no outbox configured)",
                concept_id,
            )

    async def _process_pending_recalculations(self) -> Dict[str, int]:
        """
        Retry pending confidence recalculations with linear backoff.

        Backoff delay = retry_count * RECALC_RETRY_DELAY_SECONDS.
        Called at the START of each process_pending_events() cycle.
        Returns stats on retried, succeeded, failed, and escalated items.
        """
        stats = {"retried": 0, "succeeded": 0, "failed": 0, "escalated": 0}

        try:
            conn = self._get_recalc_connection()
            cursor = conn.cursor()

            # Get pending items ready for retry (with linear backoff: retry_count * delay)
            cursor.execute(
                """
                SELECT recalc_id, concept_id, event_id, event_offset, retry_count
                FROM pending_confidence_recalc
                WHERE status = ?
                  AND (last_attempt IS NULL
                       OR datetime(last_attempt, '+' || (retry_count * ?) || ' seconds') < datetime('now'))
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (
                    self.STATUS_PENDING,
                    self._config.RECALC_RETRY_DELAY_SECONDS,
                    self._config.RECALC_BATCH_SIZE,
                ),
            )

            pending = cursor.fetchall()

            for row in pending:
                recalc_id = row["recalc_id"]
                concept_id = row["concept_id"]
                event_id = row["event_id"]
                retry_count = row["retry_count"]
                stats["retried"] += 1

                async with self.cache.concept_lock(concept_id) as acquired:
                    if not acquired:
                        # Still locked - increment retry, will try again next cycle
                        cursor.execute(
                            """
                            UPDATE pending_confidence_recalc
                            SET retry_count = retry_count + 1,
                                last_attempt = datetime('now'),
                                status = CASE
                                    WHEN retry_count + 1 >= ? THEN ?
                                    ELSE ?
                                END
                            WHERE recalc_id = ?
                            """,
                            (
                                self._config.MAX_RECALC_RETRIES,
                                self.STATUS_ESCALATED,
                                self.STATUS_PENDING,
                                recalc_id,
                            ),
                        )
                        conn.commit()

                        if retry_count + 1 >= self._config.MAX_RECALC_RETRIES:
                            stats["escalated"] += 1
                            await self._escalate_to_outbox(
                                concept_id, event_id, "Max retries exceeded - lock contention"
                            )
                        else:
                            stats["failed"] += 1
                            logger.debug(
                                "Lock still held for concept %s, will retry later",
                                concept_id,
                            )
                        continue

                    # Lock acquired - perform calculation
                    try:
                        result = await self.calculator.calculate_composite_score(concept_id)

                        if isinstance(result, Error):
                            raise RuntimeError(result.message)

                        # Persist score directly
                        score_100 = result.value * 100.0
                        await self.cache.set_cached_score(concept_id, score_100)

                        query = """
                        MATCH (c:Concept {concept_id: $concept_id})
                        SET c.confidence_score = $score,
                            c.confidence_last_calculated = datetime()
                        """
                        self.neo4j.execute_write(
                            query,
                            parameters={"concept_id": concept_id, "score": float(score_100)},
                        )

                        # Mark completed
                        cursor.execute(
                            """
                            UPDATE pending_confidence_recalc
                            SET status = ?, last_attempt = datetime('now')
                            WHERE recalc_id = ?
                            """,
                            (self.STATUS_COMPLETED, recalc_id),
                        )
                        conn.commit()

                        stats["succeeded"] += 1
                        logger.info(
                            "Retry succeeded for concept %s (score: %.2f)",
                            concept_id,
                            score_100,
                        )

                    except Exception as exc:
                        logger.error("Retry failed for %s: %s", concept_id, exc)
                        cursor.execute(
                            """
                            UPDATE pending_confidence_recalc
                            SET retry_count = retry_count + 1,
                                last_attempt = datetime('now'),
                                error_message = ?,
                                status = CASE
                                    WHEN retry_count + 1 >= ? THEN ?
                                    ELSE ?
                                END
                            WHERE recalc_id = ?
                            """,
                            (
                                str(exc),
                                self._config.MAX_RECALC_RETRIES,
                                self.STATUS_ESCALATED,
                                self.STATUS_PENDING,
                                recalc_id,
                            ),
                        )
                        conn.commit()
                        stats["failed"] += 1

        except Exception as exc:
            logger.error("Error processing pending recalculations: %s", exc)

        if stats["retried"] > 0:
            logger.info(
                "Pending recalculations: %d retried, %d succeeded, %d failed, %d escalated",
                stats["retried"],
                stats["succeeded"],
                stats["failed"],
                stats["escalated"],
            )

        return stats

    async def get_pending_recalc_stats(self) -> Dict[str, int]:
        """Return pending recalculation statistics for health monitoring."""
        try:
            conn = self._get_recalc_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT status, COUNT(*) as count
                FROM pending_confidence_recalc
                GROUP BY status
                """
            )

            return {row["status"]: row["count"] for row in cursor.fetchall()}
        except Exception as exc:
            logger.error("Error getting pending recalc stats: %s", exc)
            return {}

    async def process_pending_events(self, limit: int = 100) -> Dict[str, int]:
        """
        Process confidence-related events from the event store.

        This method has two phases:
        1. Process any pending recalculations from previous lock failures
        2. Process new events from the event store

        Args:
            limit: Maximum number of events to read in one batch.

        Returns:
            Dictionary with counts for processed, failed, skipped, and pending_retries.
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0, "pending_retries": 0}

        # PHASE 1: Process pending recalculations from previous lock failures
        retry_stats = await self._process_pending_recalculations()
        stats["pending_retries"] = retry_stats.get("retried", 0)

        # PHASE 2: Process new events from event store
        try:
            events = self.event_store.get_all_events(
                limit=limit, offset=self._checkpoint.last_offset
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to load events from store: %s", exc, exc_info=True)
            stats["failed"] += 1
            return stats

        for event in events:
            advance_offset = False
            try:
                if event.event_type not in self._HANDLED_EVENT_TYPES:
                    stats["skipped"] += 1
                    advance_offset = True
                    continue

                if event.event_type == "ConceptDeleted":
                    await self._handle_deleted_concept(event)
                    stats["processed"] += 1
                    advance_offset = True
                    continue

                # Handle relationship events by recalculating both connected concepts
                # CRITICAL: Only advance checkpoint if ALL concepts were processed
                if event.event_type in ("RelationshipCreated", "RelationshipDeleted"):
                    success = await self._handle_relationship_change(event)
                    if success:
                        stats["processed"] += 1
                        advance_offset = True
                    else:
                        # Some concepts failed - DON'T advance checkpoint
                        # Event will be retried on next poll cycle
                        stats["failed"] += 1
                        logger.warning(
                            "Event %s partially failed, checkpoint NOT advanced",
                            event.event_id,
                        )
                    continue

                result = await self.calculator.calculate_composite_score(event.aggregate_id)
                if isinstance(result, Error):
                    stats["failed"] += 1
                    logger.warning(
                        "Confidence calculation failed for %s (%s): %s",
                        event.aggregate_id,
                        event.event_type,
                        result.message,
                    )
                    advance_offset = True
                    continue

                await self._persist_score(event, result.value)
                stats["processed"] += 1
                advance_offset = True

            except Exception as exc:  # pragma: no cover - defensive
                stats["failed"] += 1
                logger.error(
                    "Unexpected error processing event %s (%s): %s",
                    event.event_id,
                    event.event_type,
                    exc,
                    exc_info=True,
                )
                break
            finally:
                if advance_offset:
                    self._advance_checkpoint(event)

        self._checkpoint.save(self.checkpoint_path)
        return stats

    async def _persist_score(
        self, event: Event, score: float, concept_id_override: str | None = None
    ) -> None:
        """
        Persist confidence score to both cache and Neo4j.

        The score from the calculator is in 0-1 scale. It is converted to 0-100
        scale before storage in both cache and Neo4j for consistency with API responses.

        Args:
            event: The event being processed
            score: Calculated confidence score (0.0-1.0 from calculator)
            concept_id_override: Optional concept_id to use instead of event.aggregate_id
        """
        # Use override if provided, otherwise use event's aggregate_id
        concept_id = concept_id_override if concept_id_override else event.aggregate_id

        # Convert to 0-100 scale for storage
        score_100 = score * 100.0

        try:
            await self.cache.set_cached_score(concept_id, score_100)
        except Exception as exc:  # pragma: no cover - cache failures should not abort
            logger.warning(
                "Failed to cache confidence score for %s: %s",
                concept_id,
                exc,
            )

        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        SET c.confidence_score = $score,
            c.confidence_last_calculated = datetime()
        """
        try:
            self.neo4j.execute_write(
                query,
                parameters={"concept_id": concept_id, "score": float(score_100)},
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "Failed to persist automated confidence score for %s: %s",
                concept_id,
                exc,
                exc_info=True,
            )
            raise

    async def _handle_deleted_concept(self, event: Event) -> None:
        """Handle deletions by clearing Neo4j properties and cache."""
        try:
            await self.cache.invalidate_concept_cache(event.aggregate_id)
        except Exception as exc:  # pragma: no cover - cache failures should not abort
            logger.warning(
                "Failed to invalidate cache for deleted concept %s: %s",
                event.aggregate_id,
                exc,
            )

        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        SET c.confidence_score = 0.0
        REMOVE c.confidence_last_calculated
        """
        try:
            self.neo4j.execute_write(query, parameters={"concept_id": event.aggregate_id})
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "Failed to remove confidence properties for %s: %s",
                event.aggregate_id,
                exc,
                exc_info=True,
            )
            raise

    async def _handle_relationship_change(self, event: Event) -> bool:
        """
        Handle relationship creation/deletion by recalculating scores for both connected concepts.

        When a relationship is added or removed, the relationship density component
        of the confidence score changes for both the source and target concepts.
        This method invalidates cached relationship data and recalculates scores.

        RACE CONDITION FIX: Uses distributed locking to prevent stale reads.
        The invalidate -> calculate -> persist cycle is atomic per concept,
        ensuring concurrent requests cannot read stale data between cache
        invalidation and score persistence.

        LOCK FAILURE HANDLING: When a lock cannot be acquired, the concept is
        queued to a persistent SQLite table for later retry. This ensures no
        concept is ever lost due to lock contention.

        Args:
            event: RelationshipCreated or RelationshipDeleted event

        Returns:
            True if ALL concepts were successfully processed
            False if any concept failed (caller should NOT advance checkpoint)
        """
        # Extract concept IDs from event data
        event_data = event.event_data
        from_concept_id = event_data.get("from_concept_id")
        to_concept_id = event_data.get("to_concept_id")

        if not from_concept_id or not to_concept_id:
            logger.warning(
                "Relationship event %s (%s) missing concept IDs, skipping confidence update",
                event.event_id,
                event.event_type,
            )
            return True  # Not a failure, just skip malformed event

        logger.info(
            "Processing relationship change for concepts: %s and %s",
            from_concept_id,
            to_concept_id,
        )

        concept_ids = [from_concept_id, to_concept_id]
        all_succeeded = True
        event_offset = self._checkpoint.last_offset + 1

        # Process each concept with distributed locking to prevent race conditions
        # The lock ensures invalidate -> calculate -> persist is atomic per concept
        for concept_id in concept_ids:
            async with self.cache.concept_lock(concept_id) as acquired:
                if not acquired:
                    # CHANGED: Queue for retry instead of silently skipping
                    logger.warning(
                        "Lock held for concept %s (event %s), queueing for retry",
                        concept_id,
                        event.event_id,
                    )
                    await self._queue_pending_recalc(
                        concept_id=concept_id,
                        event_id=event.event_id,
                        event_offset=event_offset,
                        error_message="Lock held by another process",
                    )
                    all_succeeded = False
                    continue

                # Phase 1: Invalidate cache (safe because we hold the lock)
                try:
                    await self.cache.invalidate_concept_cache(
                        concept_id,
                        invalidate_score=False,  # Keep score cache temporarily
                        invalidate_calc=True,  # Invalidate relationship/review cache
                    )
                except Exception as exc:  # pragma: no cover - cache failures should not abort
                    logger.warning(
                        "Failed to invalidate cache for concept %s: %s",
                        concept_id,
                        exc,
                    )

                # Phase 2: Calculate new score
                try:
                    result = await self.calculator.calculate_composite_score(concept_id)

                    if isinstance(result, Error):
                        error_msg = (
                            f"Failed to recalculate score for concept {concept_id} "
                            f"after relationship change: {result.message}"
                        )
                        logger.error(error_msg)
                        # CHANGED: Queue for retry instead of raising
                        await self._queue_pending_recalc(
                            concept_id=concept_id,
                            event_id=event.event_id,
                            event_offset=event_offset,
                            error_message=result.message,
                        )
                        all_succeeded = False
                        continue

                    logger.debug(
                        "Calculated score %.4f for concept %s",
                        result.value,
                        concept_id,
                    )

                    # Phase 3: Persist score (completes the atomic cycle while holding lock)
                    await self._persist_score(event, result.value, concept_id_override=concept_id)
                    logger.info(
                        "Updated confidence score for concept %s after relationship change",
                        concept_id,
                    )

                except Exception as exc:
                    error_msg = (
                        f"Unexpected error recalculating score for concept {concept_id}: {exc}"
                    )
                    logger.error(error_msg, exc_info=True)
                    # CHANGED: Queue for retry instead of raising
                    await self._queue_pending_recalc(
                        concept_id=concept_id,
                        event_id=event.event_id,
                        event_offset=event_offset,
                        error_message=str(exc),
                    )
                    all_succeeded = False

        return all_succeeded

    def _advance_checkpoint(self, event: Event) -> None:
        """Advance the checkpoint to the supplied event."""
        self._checkpoint.last_offset += 1
        self._checkpoint.last_event_id = event.event_id
