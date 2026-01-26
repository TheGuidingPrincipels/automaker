"""
Unit tests for Outbox
"""

import tempfile
from pathlib import Path

import pytest

from services.outbox import Outbox


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize the database schema
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create outbox table
    cursor.execute(
        """
        CREATE TABLE outbox (
            outbox_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            projection_name TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_attempt DATETIME,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE INDEX idx_status ON outbox(status, projection_name)
    """
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_outbox_initialization(temp_db):
    """Test that Outbox initializes correctly"""
    outbox = Outbox(temp_db)
    assert outbox.db_path == Path(temp_db)


def test_add_to_outbox(temp_db):
    """Test adding an event to outbox"""
    outbox = Outbox(temp_db)

    outbox_id = outbox.add_to_outbox(event_id="event_001", projection_name="neo4j")

    assert outbox_id is not None
    assert len(outbox_id) > 0


def test_get_pending(temp_db):
    """Test getting pending outbox items"""
    outbox = Outbox(temp_db)

    # Add items
    outbox.add_to_outbox("event_001", "neo4j")
    outbox.add_to_outbox("event_002", "chromadb")

    # Get pending items
    pending = outbox.get_pending()

    assert len(pending) == 2


def test_get_pending_by_projection(temp_db):
    """Test getting pending items filtered by projection"""
    outbox = Outbox(temp_db)

    # Add items for different projections
    outbox.add_to_outbox("event_001", "neo4j")
    outbox.add_to_outbox("event_002", "chromadb")
    outbox.add_to_outbox("event_003", "neo4j")

    # Get pending for neo4j only
    pending = outbox.get_pending(projection_name="neo4j")

    assert len(pending) == 2
    assert all(item.projection_name == "neo4j" for item in pending)


def test_mark_processing(temp_db):
    """Test marking an item as processing"""
    outbox = Outbox(temp_db)

    outbox_id = outbox.add_to_outbox("event_001", "neo4j")

    result = outbox.mark_processing(outbox_id)

    assert result is True


def test_mark_processed(temp_db):
    """Test marking an item as processed"""
    outbox = Outbox(temp_db)

    outbox_id = outbox.add_to_outbox("event_001", "neo4j")

    result = outbox.mark_processed(outbox_id)

    assert result is True

    # Verify it's no longer in pending
    pending = outbox.get_pending()
    assert len(pending) == 0


def test_mark_failed(temp_db):
    """Test marking an item as failed"""
    outbox = Outbox(temp_db)

    outbox_id = outbox.add_to_outbox("event_001", "neo4j")

    result = outbox.mark_failed(outbox_id, "Test error message")

    assert result is True


def test_retry_logic(temp_db):
    """Test that failed items are retried up to MAX_ATTEMPTS"""
    outbox = Outbox(temp_db)

    outbox_id = outbox.add_to_outbox("event_001", "neo4j")

    # Fail it multiple times
    for i in range(Outbox.MAX_ATTEMPTS):
        outbox.mark_failed(outbox_id, f"Error attempt {i+1}")

    # After MAX_ATTEMPTS, it should be permanently failed
    pending = outbox.get_pending()
    assert len(pending) == 0

    # Check failed items
    failed = outbox.get_failed_items()
    assert len(failed) == 1
    assert failed[0].attempts == Outbox.MAX_ATTEMPTS


def test_increment_attempts(temp_db):
    """Test incrementing attempt counter"""
    outbox = Outbox(temp_db)

    outbox_id = outbox.add_to_outbox("event_001", "neo4j")

    result = outbox.increment_attempts(outbox_id)

    assert result is True


def test_get_failed_items(temp_db):
    """Test getting failed outbox items"""
    outbox = Outbox(temp_db)

    # Add and fail multiple items
    for i in range(3):
        outbox_id = outbox.add_to_outbox(f"event_{i:03d}", "neo4j")
        for _ in range(Outbox.MAX_ATTEMPTS):
            outbox.mark_failed(outbox_id, "Test error")

    failed = outbox.get_failed_items()

    assert len(failed) == 3


def test_retry_failed(temp_db):
    """Test retrying a failed item"""
    outbox = Outbox(temp_db)

    outbox_id = outbox.add_to_outbox("event_001", "neo4j")

    # Fail it
    for _ in range(Outbox.MAX_ATTEMPTS):
        outbox.mark_failed(outbox_id, "Test error")

    # Retry it
    result = outbox.retry_failed(outbox_id)

    assert result is True

    # Should be back in pending
    pending = outbox.get_pending()
    assert len(pending) == 1


def test_count_by_status(temp_db):
    """Test counting outbox items by status"""
    outbox = Outbox(temp_db)

    # Add items with different statuses
    id1 = outbox.add_to_outbox("event_001", "neo4j")
    id2 = outbox.add_to_outbox("event_002", "neo4j")
    outbox.add_to_outbox("event_003", "neo4j")

    outbox.mark_processed(id1)
    for _ in range(Outbox.MAX_ATTEMPTS):
        outbox.mark_failed(id2, "Test error")

    counts = outbox.count_by_status()

    assert counts.get(Outbox.STATUS_COMPLETED, 0) == 1
    assert counts.get(Outbox.STATUS_FAILED, 0) == 1
    assert counts.get(Outbox.STATUS_PENDING, 0) == 1


def test_pending_limit(temp_db):
    """Test getting pending items with limit"""
    outbox = Outbox(temp_db)

    # Add multiple items
    for i in range(10):
        outbox.add_to_outbox(f"event_{i:03d}", "neo4j")

    # Get with limit
    pending = outbox.get_pending(limit=5)

    assert len(pending) == 5


def test_outbox_item_attributes(temp_db):
    """Test that OutboxItem has all required attributes"""
    outbox = Outbox(temp_db)

    outbox.add_to_outbox("event_001", "neo4j")

    pending = outbox.get_pending()
    item = pending[0]

    assert hasattr(item, "outbox_id")
    assert hasattr(item, "event_id")
    assert hasattr(item, "projection_name")
    assert hasattr(item, "status")
    assert hasattr(item, "attempts")
    assert hasattr(item, "last_attempt")
    assert hasattr(item, "error_message")
    assert hasattr(item, "created_at")

    assert item.event_id == "event_001"
    assert item.projection_name == "neo4j"
    assert item.status == Outbox.STATUS_PENDING
    assert item.attempts == 0
