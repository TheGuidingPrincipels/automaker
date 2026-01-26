"""
Event Store service for event sourcing pattern
"""

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
import threading
from typing import List, Optional

from models.events import Event


logger = logging.getLogger(__name__)


class EventStoreError(Exception):
    """Base exception for event store errors"""

    pass


class DuplicateEventError(EventStoreError):
    """Raised when attempting to append an event with duplicate ID"""

    pass


class VersionConflictError(EventStoreError):
    """Raised when event version conflicts with existing version"""

    pass


class EventStore:
    """
    Event Store implementation using SQLite

    Provides append-only storage for events with strong consistency guarantees.
    Events are immutable once written.

    Uses a persistent connection to avoid connection overhead per operation.
    """

    def __init__(self, db_path: str = "./data/events.db"):
        """
        Initialize EventStore

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.new_event_signal = asyncio.Event()
        self._conn: Optional[sqlite3.Connection] = None
        self._conn_lock = threading.Lock()
        self._write_lock = threading.Lock()  # Serializes write operations for thread safety
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Ensure database file and directory exist"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning(
                "Unable to create directories for %s: %s. Continuing assuming read-only path.",
                self.db_path,
                exc,
            )

        if not self.db_path.exists():
            logger.warning(
                "Database not found at %s. Run scripts/init_database.py first.", self.db_path
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
                logger.debug("EventStore: Created persistent connection to %s", self.db_path)
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
                logger.debug("EventStore: Closed persistent connection")
            except Exception as exc:
                logger.warning("EventStore: Error closing connection: %s", exc)
            finally:
                self._conn = None

    def append_event(self, event: Event) -> bool:
        """
        Append event to event store

        Args:
            event: Event to append

        Returns:
            True if successful

        Raises:
            DuplicateEventError: If event_id already exists
            VersionConflictError: If version conflicts with existing version

        Thread-safe: Uses a write lock to serialize concurrent write operations.
        """
        with self._write_lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            try:
                # Use IMMEDIATE transaction to acquire write lock early
                # This prevents race conditions in version checking
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as e:
                # Don't close the shared connection - just rollback if needed
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise EventStoreError(f"Failed to begin transaction: {e}")

            try:
                # Check for duplicate event_id
                cursor.execute(
                    "SELECT event_id FROM events WHERE event_id = ?",
                    (event.event_id,)
                )
                if cursor.fetchone():
                    raise DuplicateEventError(f"Event {event.event_id} already exists")

                # Check for version conflict
                cursor.execute(
                    """SELECT MAX(version) as max_version FROM events
                       WHERE aggregate_id = ?""",
                    (event.aggregate_id,)
                )
                row = cursor.fetchone()
                max_version = row[0] if row[0] is not None else 0

                if event.version != max_version + 1:
                    raise VersionConflictError(
                        f"Version conflict: expected {max_version + 1}, got {event.version}"
                    )

                # Convert event to database format
                db_dict = event.to_db_dict()

                # Insert event
                cursor.execute(
                    """INSERT INTO events
                       (event_id, event_type, aggregate_id, aggregate_type,
                        event_data, metadata, version, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        db_dict['event_id'],
                        db_dict['event_type'],
                        db_dict['aggregate_id'],
                        db_dict['aggregate_type'],
                        db_dict['event_data'],
                        db_dict['metadata'],
                        db_dict['version'],
                        db_dict['created_at']
                    )
                )

                conn.commit()
                logger.info(f"Event {event.event_id} appended successfully")

                # Signal that a new event has been added
                self.new_event_signal.set()

                return True

            except (DuplicateEventError, VersionConflictError):
                conn.rollback()
                raise

            except sqlite3.IntegrityError as e:
                conn.rollback()
                # Check if this is a UNIQUE constraint violation on (aggregate_id, version)
                error_msg = str(e).lower()
                if "unique" in error_msg and "aggregate" in error_msg:
                    # Get the expected version for better error message
                    cursor.execute(
                        "SELECT MAX(version) as max_version FROM events WHERE aggregate_id = ?",
                        (event.aggregate_id,)
                    )
                    row = cursor.fetchone()
                    max_version = row[0] if row[0] is not None else 0
                    raise VersionConflictError(
                        f"Version conflict: expected {max_version + 1}, got {event.version}"
                    )
                else:
                    # Other integrity error (e.g., foreign key)
                    logger.error(f"Integrity error appending event: {e}")
                    raise EventStoreError(f"Integrity constraint violation: {e}")

            except Exception as e:
                conn.rollback()
                logger.error(f"Error appending event: {e}")
                raise EventStoreError(f"Failed to append event: {e}")

    def get_events_by_aggregate(
        self, aggregate_id: str, from_version: int | None = None
    ) -> list[Event]:
        """
        Get all events for a specific aggregate

        Args:
            aggregate_id: ID of the aggregate
            from_version: Optional minimum version (inclusive)

        Returns:
            List of events ordered by version
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if from_version is not None:
                cursor.execute(
                    """SELECT * FROM events
                       WHERE aggregate_id = ? AND version >= ?
                       ORDER BY version ASC""",
                    (aggregate_id, from_version),
                )
            else:
                cursor.execute(
                    """SELECT * FROM events
                       WHERE aggregate_id = ?
                       ORDER BY version ASC""",
                    (aggregate_id,),
                )

            rows = cursor.fetchall()

            # Parse events with specific error handling for corrupted JSON
            events = []
            skipped_corrupted = 0
            for row in rows:
                try:
                    events.append(Event.from_db_row(tuple(row)))
                except (json.JSONDecodeError, ValueError) as e:
                    skipped_corrupted += 1
                    logger.error(
                        "Corrupted JSON in event %s: %s. Skipping corrupted row.", row[0], e
                    )

            if skipped_corrupted:
                logger.warning(
                    "Skipped %s corrupted event(s) while fetching aggregate %s.",
                    skipped_corrupted,
                    aggregate_id,
                )

            return events

        except EventStoreError:
            # Re-raise our own errors
            raise
        except sqlite3.Error as e:
            # Database errors
            logger.error(f"Database error fetching events: {e}")
            raise EventStoreError(f"Failed to fetch events: {e}")
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error fetching events: {e}", exc_info=True)
            raise EventStoreError(f"Unexpected error fetching events: {e}")

    def get_all_events(
        self, limit: int | None = None, offset: int | None = None, event_type: str | None = None
    ) -> list[Event]:
        """
        Get all events with optional filtering

        Args:
            limit: Maximum number of events to return (must be >= 0)
            offset: Number of events to skip (must be >= 0)
            event_type: Optional filter by event type

        Returns:
            List of events ordered by created_at

        Raises:
            ValueError: If limit or offset is negative
            EventStoreError: If database error or corrupted data
        """
        # Validate parameters (Bug #5 fix) while keeping backwards compatibility
        if limit is not None and limit < 0:
            logger.warning("Received negative limit=%s; defaulting to no limit", limit)
            limit = None
        if offset is not None and offset < 0:
            logger.warning("Received negative offset=%s; defaulting to 0", offset)
            offset = 0

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM events"
            params = []

            if event_type:
                query += " WHERE event_type = ?"
                params.append(event_type)

            query += " ORDER BY created_at ASC"

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            if offset:
                query += " OFFSET ?"
                params.append(offset)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Parse events with specific error handling for corrupted JSON (Bug #3 fix)
            events = []
            skipped_corrupted = 0
            for row in rows:
                try:
                    events.append(Event.from_db_row(tuple(row)))
                except json.JSONDecodeError as e:
                    skipped_corrupted += 1
                    logger.error(
                        "Corrupted JSON in event %s: %s. Skipping corrupted row.", row[0], e
                    )
                except ValueError as e:
                    skipped_corrupted += 1
                    logger.error("Failed to deserialize event %s: %s. Skipping row.", row[0], e)

            if skipped_corrupted:
                logger.warning(
                    "Skipped %s corrupted event(s) while fetching all events.", skipped_corrupted
                )

            return events

        except EventStoreError:
            # Re-raise our own errors
            raise
        except sqlite3.Error as e:
            # Database errors
            logger.error(f"Database error fetching all events: {e}")
            raise EventStoreError(f"Failed to fetch all events: {e}")
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error fetching all events: {e}", exc_info=True)
            raise EventStoreError(f"Unexpected error fetching all events: {e}")

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """
        Get specific event by ID

        Args:
            event_id: Event ID to retrieve

        Returns:
            Event if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()

            if row:
                return Event.from_db_row(tuple(row))
            return None

        except Exception as e:
            logger.error(f"Error fetching event by ID: {e}")
            return None

    def get_latest_version(self, aggregate_id: str) -> int:
        """
        Get latest version number for an aggregate

        Args:
            aggregate_id: ID of the aggregate

        Returns:
            Latest version number, or 0 if no events exist
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """SELECT MAX(version) as max_version FROM events
                   WHERE aggregate_id = ?""",
                (aggregate_id,),
            )
            row = cursor.fetchone()
            return row[0] if row[0] is not None else 0

        except Exception as e:
            logger.error(f"Error fetching latest version: {e}")
            return 0

    def count_events(
        self,
        aggregate_id: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> int:
        """
        Count events with optional filtering

        Args:
            aggregate_id: Optional filter by aggregate ID
            event_type: Optional filter by event type

        Returns:
            Count of events
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT COUNT(*) FROM events WHERE 1=1"
            params = []

            if aggregate_id:
                query += " AND aggregate_id = ?"
                params.append(aggregate_id)

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            cursor.execute(query, params)
            return cursor.fetchone()[0]

        except Exception as e:
            logger.error(f"Error counting events: {e}")
            return 0
