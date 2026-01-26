"""
Outbox pattern implementation for reliable async event processing
"""

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OutboxItem:
    """Represents an item in the outbox queue"""

    outbox_id: str
    event_id: str
    projection_name: str
    status: str
    attempts: int
    last_attempt: datetime | None
    error_message: str | None
    created_at: datetime


class OutboxError(Exception):
    """Base exception for outbox errors"""

    pass


class Outbox:
    """
    Outbox pattern implementation for reliable async processing

    Ensures that events are reliably processed by downstream projections
    (Neo4j, ChromaDB) with automatic retry on failure.

    Uses a persistent connection to avoid connection overhead per operation.
    """

    # Outbox statuses
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    # Retry configuration
    MAX_ATTEMPTS = 3

    def __init__(self, db_path: str = "./data/events.db"):
        """
        Initialize Outbox

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._conn_lock = threading.Lock()
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Ensure database file exists"""
        if not self.db_path.exists():
            logger.warning(
                f"Database not found at {self.db_path}. Run scripts/init_database.py first."
            )

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection with foreign key enforcement enabled.

        Uses a persistent connection for performance. The connection is created
        lazily on first access and reused for subsequent operations.
        If the connection was closed externally, it will be recreated.

        Thread-safe: Uses a lock to prevent race conditions in multi-threaded contexts.
        """
        with self._conn_lock:
            # Check if connection needs to be (re)created
            need_new_connection = self._conn is None
            if not need_new_connection:
                try:
                    # Test if connection is still valid
                    self._conn.execute("SELECT 1")
                except sqlite3.ProgrammingError:
                    # Connection was closed externally, need to recreate
                    need_new_connection = True
                    self._conn = None

            if need_new_connection:
                # check_same_thread=False allows connection reuse across threads
                self._conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0  # 30 second timeout for lock acquisition
                )
                self._conn.row_factory = sqlite3.Row
                # Enable foreign key constraints (Bug #7 fix)
                self._conn.execute("PRAGMA foreign_keys = ON")
                # Enable WAL mode for better concurrent read/write performance
                self._conn.execute("PRAGMA journal_mode = WAL")
                logger.debug("Outbox: Created persistent connection to %s", self.db_path)
            return self._conn

    def close(self) -> None:
        """
        Close the persistent database connection.

        Should be called when shutting down the application to ensure
        proper cleanup of database resources.
        """
        if self._conn is not None:
            try:
                self._conn.close()
                logger.debug("Outbox: Closed persistent connection")
            except Exception as exc:
                logger.warning("Outbox: Error closing connection: %s", exc)
            finally:
                self._conn = None

    def add_to_outbox(self, event_id: str, projection_name: str) -> str:
        """
        Add event to outbox for async processing

        Args:
            event_id: ID of the event to process
            projection_name: Name of the projection ("neo4j" or "chromadb")

        Returns:
            Outbox ID

        Raises:
            OutboxError: If failed to add to outbox
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            outbox_id = str(uuid.uuid4())

            cursor.execute(
                """INSERT INTO outbox
                   (outbox_id, event_id, projection_name, status, attempts, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    outbox_id,
                    event_id,
                    projection_name,
                    self.STATUS_PENDING,
                    0,
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            logger.info(f"Added event {event_id} to outbox for {projection_name}")
            return outbox_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding to outbox: {e}")
            raise OutboxError(f"Failed to add to outbox: {e}")

    def get_pending(
        self, projection_name: str | None = None, limit: int | None = None
    ) -> list[OutboxItem]:
        """
        Get pending outbox items

        Args:
            projection_name: Optional filter by projection name
            limit: Maximum number of items to return (must be >= 0)

        Returns:
            List of pending outbox items

        Raises:
            ValueError: If limit is negative
        """
        # Validate parameters (Bug #5 fix)
        if limit is not None and limit < 0:
            raise ValueError(f"limit must be non-negative, got {limit}")

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = """SELECT * FROM outbox
                       WHERE status = ? AND attempts < ?"""
            params = [self.STATUS_PENDING, self.MAX_ATTEMPTS]

            if projection_name:
                query += " AND projection_name = ?"
                params.append(projection_name)

            query += " ORDER BY created_at ASC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_outbox_item(row) for row in rows]

        except ValueError:
            # Re-raise validation errors
            raise
        except sqlite3.Error as e:
            # Database errors
            logger.error(f"Database error fetching pending items: {e}")
            raise
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error fetching pending items: {e}", exc_info=True)
            raise

    def mark_processing(self, outbox_id: str) -> bool:
        """
        Mark outbox item as processing

        Args:
            outbox_id: ID of outbox item

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """UPDATE outbox
                   SET status = ?, last_attempt = ?
                   WHERE outbox_id = ?""",
                (self.STATUS_PROCESSING, datetime.now().isoformat(), outbox_id),
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error marking as processing: {e}")
            return False

    def mark_processed(self, outbox_id: str) -> bool:
        """
        Mark outbox item as successfully processed

        Args:
            outbox_id: ID of outbox item

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """UPDATE outbox
                   SET status = ?
                   WHERE outbox_id = ?""",
                (self.STATUS_COMPLETED, outbox_id),
            )

            conn.commit()
            logger.info(f"Marked outbox item {outbox_id} as completed")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error marking as processed: {e}")
            return False

    def mark_failed(
        self,
        outbox_id: str,
        error_message: str
    ) -> bool:
        """
        Mark outbox item as failed

        Args:
            outbox_id: ID of outbox item
            error_message: Error message describing the failure

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Increment attempts
            cursor.execute(
                """UPDATE outbox
                   SET attempts = attempts + 1,
                       last_attempt = ?,
                       error_message = ?,
                       status = CASE
                         WHEN attempts + 1 >= ? THEN ?
                         ELSE ?
                       END
                   WHERE outbox_id = ?""",
                (
                    datetime.now().isoformat(),
                    error_message,
                    self.MAX_ATTEMPTS,
                    self.STATUS_FAILED,
                    self.STATUS_PENDING,
                    outbox_id,
                ),
            )

            conn.commit()
            logger.warning(f"Marked outbox item {outbox_id} as failed: {error_message}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error marking as failed: {e}")
            return False

    def increment_attempts(self, outbox_id: str) -> bool:
        """
        Increment attempt counter for outbox item

        Args:
            outbox_id: ID of outbox item

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """UPDATE outbox
                   SET attempts = attempts + 1,
                       last_attempt = ?
                   WHERE outbox_id = ?""",
                (datetime.now().isoformat(), outbox_id),
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error incrementing attempts: {e}")
            return False

    def get_failed_items(
        self,
        projection_name: Optional[str] = None
    ) -> List[OutboxItem]:
        """
        Get all failed outbox items

        Args:
            projection_name: Optional filter by projection name

        Returns:
            List of failed outbox items
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM outbox WHERE status = ?"
            params = [self.STATUS_FAILED]

            if projection_name:
                query += " AND projection_name = ?"
                params.append(projection_name)

            query += " ORDER BY created_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_outbox_item(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching failed items: {e}")
            return []

    def retry_failed(self, outbox_id: str) -> bool:
        """
        Reset a failed item to pending for retry

        Args:
            outbox_id: ID of outbox item to retry

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """UPDATE outbox
                   SET status = ?,
                       attempts = 0,
                       error_message = NULL
                   WHERE outbox_id = ? AND status = ?""",
                (self.STATUS_PENDING, outbox_id, self.STATUS_FAILED),
            )

            conn.commit()
            logger.info(f"Reset outbox item {outbox_id} for retry")
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Error retrying failed item: {e}")
            return False

    def count_by_status(self, projection_name: Optional[str] = None) -> Dict[str, int]:
        """
        Count outbox items by status

        Args:
            projection_name: Optional filter by projection name

        Returns:
            Dictionary mapping status to count
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT status, COUNT(*) as count FROM outbox"
            params = []

            if projection_name:
                query += " WHERE projection_name = ?"
                params.append(projection_name)

            query += " GROUP BY status"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return {row["status"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(f"Error counting by status: {e}")
            return {}

    def _row_to_outbox_item(self, row: sqlite3.Row) -> OutboxItem:
        """Convert database row to OutboxItem"""
        return OutboxItem(
            outbox_id=row["outbox_id"],
            event_id=row["event_id"],
            projection_name=row["projection_name"],
            status=row["status"],
            attempts=row["attempts"],
            last_attempt=(
                datetime.fromisoformat(row["last_attempt"]) if row["last_attempt"] else None
            ),
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
