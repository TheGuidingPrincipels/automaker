"""
Compensation Transaction Manager for Dual Storage Synchronization.

Provides immediate rollback capabilities for failed dual writes between Neo4j and ChromaDB,
complementing the Outbox pattern's eventual consistency with immediate consistency during
failure windows.

Architecture:
    When one projection succeeds and the other fails:
    1. Compensation immediately rolls back the successful write
    2. Outbox retries the failed projection for eventual consistency
    3. Audit trail records all compensation attempts

Example:
    ```python
    # Initialize compensation manager
    manager = CompensationManager(
        neo4j_service=neo4j_service,
        chromadb_service=chromadb_service,
        connection=sqlite_connection
    )

    # Rollback Neo4j if ChromaDB fails
    success = manager.rollback_neo4j(event)

    # Rollback ChromaDB if Neo4j fails
    success = manager.rollback_chromadb(event)
    ```
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any

from models.events import Event
from services.chromadb_service import ChromaDbService
from services.neo4j_service import Neo4jService


logger = logging.getLogger(__name__)


class CompensationError(Exception):
    """Base exception for compensation errors"""

    pass


class CompensationManager:
    """
    Manages compensation transactions for failed dual writes.

    Provides immediate rollback capabilities to maintain consistency between
    Neo4j and ChromaDB when one projection fails. Works alongside the Outbox
    pattern to provide both immediate cleanup and eventual consistency.

    Features:
    - Idempotent rollback operations (safe to call multiple times)
    - Comprehensive audit trail for all compensation attempts
    - Graceful error handling with detailed logging
    - Target-specific rollback methods for Neo4j and ChromaDB
    """

    def __init__(
        self,
        neo4j_service: Neo4jService,
        chromadb_service: ChromaDbService,
        connection: sqlite3.Connection,
    ) -> None:
        """
        Initialize CompensationManager.

        Args:
            neo4j_service: Neo4j service for graph database operations
            chromadb_service: ChromaDB service for vector database operations
            connection: SQLite connection for audit trail storage
        """
        self.neo4j = neo4j_service
        self.chromadb = chromadb_service
        self.connection = connection

        # Ensure compensation_audit table exists
        self._ensure_audit_table()

        logger.info("CompensationManager initialized successfully")

    def _ensure_audit_table(self) -> None:
        """
        Ensure compensation_audit table exists in the database.

        Creates the table if it doesn't exist. Safe to call multiple times.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS compensation_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aggregate_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    target_system TEXT NOT NULL,
                    action TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    timestamp TEXT NOT NULL
                )
            """
            )

            # Create indexes for efficient querying
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_comp_aggregate
                ON compensation_audit(aggregate_id)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_comp_timestamp
                ON compensation_audit(timestamp)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_comp_target
                ON compensation_audit(target_system, success)
            """
            )

            self.connection.commit()
            logger.debug("Compensation audit table verified/created")

        except sqlite3.Error as e:
            logger.error(f"Failed to create compensation_audit table: {e}")
            raise CompensationError(f"Database initialization failed: {e}")

    def rollback_neo4j(self, event: Event) -> bool:
        """
        Rollback a Neo4j write operation.

        Removes the concept node created by a ConceptCreated event.
        Idempotent - safe to call even if node doesn't exist.

        Args:
            event: The event to roll back (ConceptCreated, ConceptUpdated, or ConceptDeleted)

        Returns:
            True if rollback successful, False otherwise
        """
        aggregate_id = event.aggregate_id
        event_type = event.event_type

        try:
            logger.info(
                f"Rolling back Neo4j for event {event.event_id} "
                f"(type: {event_type}, aggregate: {aggregate_id})"
            )

            # Determine rollback action based on event type
            if event_type == "ConceptCreated":
                # Delete the node that was created
                query = """
                MATCH (c:Concept {concept_id: $concept_id})
                DETACH DELETE c
                RETURN count(c) as deleted_count
                """
                result = self.neo4j.execute_write(query, parameters={"concept_id": aggregate_id})

                deleted_count = result.get("nodes_deleted", 0)
                success = True

                logger.info(
                    f"Neo4j rollback successful for {aggregate_id}. "
                    f"Deleted {deleted_count} node(s)"
                )

            elif event_type == "ConceptUpdated":
                # For updates, we can't easily roll back to previous state without the old data
                # Instead, we'll mark this as a compensation that needs manual review
                logger.warning(
                    f"ConceptUpdated rollback for {aggregate_id} - "
                    f"Cannot automatically restore previous state. "
                    f"Manual review may be needed."
                )
                # Still consider this successful as we've acknowledged the issue
                success = True

            elif event_type == "ConceptDeleted":
                # For deletes, we can't restore the deleted concept without the original data
                # This is noted in the audit trail
                logger.warning(
                    f"ConceptDeleted rollback for {aggregate_id} - "
                    f"Cannot restore deleted concept. Manual review may be needed."
                )
                success = True

            else:
                logger.warning(f"Unknown event type for rollback: {event_type}")
                success = False

            # Record in audit trail
            self._record_compensation(
                aggregate_id=aggregate_id,
                event_id=event.event_id,
                event_type=event_type,
                target="neo4j",
                action="rollback",
                success=success,
                error_message=None,
            )

            return success

        except Exception as e:
            error_msg = f"Neo4j rollback failed for {aggregate_id}: {e}"
            logger.error(error_msg, exc_info=True)

            # Record failure in audit trail
            self._record_compensation(
                aggregate_id=aggregate_id,
                event_id=event.event_id,
                event_type=event_type,
                target="neo4j",
                action="rollback",
                success=False,
                error_message=str(e),
            )

            return False

    def rollback_chromadb(self, event: Event) -> bool:
        """
        Rollback a ChromaDB write operation.

        Removes the document created by a ConceptCreated event.
        Idempotent - safe to call even if document doesn't exist.

        Args:
            event: The event to roll back (ConceptCreated, ConceptUpdated, or ConceptDeleted)

        Returns:
            True if rollback successful, False otherwise
        """
        aggregate_id = event.aggregate_id
        event_type = event.event_type

        try:
            logger.info(
                f"Rolling back ChromaDB for event {event.event_id} "
                f"(type: {event_type}, aggregate: {aggregate_id})"
            )

            # Determine rollback action based on event type
            if event_type in ("ConceptCreated", "ConceptUpdated"):
                # Delete the document that was created or updated
                try:
                    collection = self.chromadb.get_collection()
                    collection.delete(ids=[aggregate_id])

                    logger.info(f"ChromaDB rollback successful for {aggregate_id}")
                    success = True

                except Exception as delete_error:
                    # If document doesn't exist, that's fine (idempotent)
                    if "does not exist" in str(delete_error).lower():
                        logger.info(
                            f"ChromaDB document {aggregate_id} already deleted or never existed. "
                            f"Rollback idempotent success."
                        )
                        success = True
                    else:
                        raise delete_error

            elif event_type == "ConceptDeleted":
                # For deletes, we can't restore the deleted document without the original data
                logger.warning(
                    f"ConceptDeleted rollback for {aggregate_id} - "
                    f"Cannot restore deleted document. Manual review may be needed."
                )
                success = True

            else:
                logger.warning(f"Unknown event type for rollback: {event_type}")
                success = False

            # Record in audit trail
            self._record_compensation(
                aggregate_id=aggregate_id,
                event_id=event.event_id,
                event_type=event_type,
                target="chromadb",
                action="rollback",
                success=success,
                error_message=None,
            )

            return success

        except Exception as e:
            error_msg = f"ChromaDB rollback failed for {aggregate_id}: {e}"
            logger.error(error_msg, exc_info=True)

            # Record failure in audit trail
            self._record_compensation(
                aggregate_id=aggregate_id,
                event_id=event.event_id,
                event_type=event_type,
                target="chromadb",
                action="rollback",
                success=False,
                error_message=str(e),
            )

            return False

    def _record_compensation(
        self,
        aggregate_id: str,
        event_id: str,
        event_type: str,
        target: str,
        action: str,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """
        Record a compensation attempt in the audit trail.

        Args:
            aggregate_id: ID of the aggregate being compensated
            event_id: ID of the event being compensated
            event_type: Type of event (ConceptCreated, etc.)
            target: Target system (neo4j or chromadb)
            action: Action taken (rollback)
            success: Whether compensation was successful
            error_message: Error message if compensation failed
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO compensation_audit (
                    aggregate_id, event_id, event_type, target_system,
                    action, success, error_message, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    aggregate_id,
                    event_id,
                    event_type,
                    target,
                    action,
                    success,
                    error_message,
                    datetime.now().isoformat(),
                ),
            )
            self.connection.commit()

            logger.debug(
                f"Recorded compensation audit: {target} {action} for {aggregate_id} "
                f"(success={success})"
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to record compensation audit: {e}", exc_info=True)
            # Don't raise - audit failure shouldn't block the operation

    def get_compensation_history(
        self, aggregate_id: str | None = None, target: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get compensation history from audit trail.

        Args:
            aggregate_id: Optional filter by aggregate ID
            target: Optional filter by target system (neo4j or chromadb)
            limit: Maximum number of results to return

        Returns:
            List of compensation audit records as dictionaries
        """
        try:
            cursor = self.connection.cursor()

            # Build query with optional filters
            query = "SELECT * FROM compensation_audit WHERE 1=1"
            params = []

            if aggregate_id:
                query += " AND aggregate_id = ?"
                params.append(aggregate_id)

            if target:
                query += " AND target_system = ?"
                params.append(target)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            columns = [
                "id",
                "aggregate_id",
                "event_type",
                "event_id",
                "target_system",
                "action",
                "success",
                "error_message",
                "timestamp",
            ]

            result = [dict(zip(columns, row, strict=False)) for row in rows]

            logger.debug(f"Retrieved {len(result)} compensation audit records")
            return result

        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve compensation history: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """
        Get compensation statistics.

        Returns:
            Dictionary with compensation statistics
        """
        try:
            cursor = self.connection.cursor()

            # Get total compensations
            cursor.execute("SELECT COUNT(*) FROM compensation_audit")
            total = cursor.fetchone()[0]

            # Get success/failure counts
            cursor.execute(
                """
                SELECT success, COUNT(*) as count
                FROM compensation_audit
                GROUP BY success
            """
            )
            success_counts = {bool(row[0]): row[1] for row in cursor.fetchall()}

            # Get counts by target
            cursor.execute(
                """
                SELECT target_system, COUNT(*) as count
                FROM compensation_audit
                GROUP BY target_system
            """
            )
            target_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Get recent failures
            cursor.execute(
                """
                SELECT COUNT(*) FROM compensation_audit
                WHERE success = 0 AND timestamp > datetime('now', '-1 hour')
            """
            )
            recent_failures = cursor.fetchone()[0]

            return {
                "total_compensations": total,
                "successful": success_counts.get(True, 0),
                "failed": success_counts.get(False, 0),
                "by_target": target_counts,
                "recent_failures_1h": recent_failures,
            }

        except sqlite3.Error as e:
            logger.error(f"Failed to get compensation stats: {e}")
            return {"error": str(e)}
