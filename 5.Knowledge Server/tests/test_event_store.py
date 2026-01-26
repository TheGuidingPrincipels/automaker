"""
Unit tests for EventStore
"""

import tempfile
from pathlib import Path

import pytest

from models.events import ConceptCreated, ConceptUpdated
from services.event_store import (
    DuplicateEventError,
    EventStore,
    VersionConflictError,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize the database schema
    Path(__file__).parent.parent / "data" / "events.db"

    # Temporarily change the db path
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.execute(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            aggregate_type TEXT NOT NULL,
            event_data TEXT NOT NULL,
            metadata TEXT,
            version INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE INDEX idx_aggregate ON events(aggregate_id, version)
    """
    )

    cursor.execute(
        """
        CREATE INDEX idx_created_at ON events(created_at)
    """
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_event_store_initialization(temp_db):
    """Test that EventStore initializes correctly"""
    store = EventStore(temp_db)
    assert store.db_path == Path(temp_db)


def test_append_event(temp_db):
    """Test appending an event to the store"""
    store = EventStore(temp_db)

    event = ConceptCreated(
        aggregate_id="concept_001",
        concept_data={"name": "Test Concept", "explanation": "Test"},
        version=1,
    )

    result = store.append_event(event)
    assert result is True


def test_append_duplicate_event(temp_db):
    """Test that duplicate events are rejected"""
    store = EventStore(temp_db)

    event = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

    store.append_event(event)

    # Try to append the same event again
    with pytest.raises(DuplicateEventError):
        store.append_event(event)


def test_version_conflict(temp_db):
    """Test that version conflicts are detected"""
    store = EventStore(temp_db)

    event1 = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

    store.append_event(event1)

    # Try to append event with wrong version
    event2 = ConceptUpdated(
        aggregate_id="concept_001", updates={"name": "Updated"}, version=3  # Should be 2
    )

    with pytest.raises(VersionConflictError):
        store.append_event(event2)


def test_get_events_by_aggregate(temp_db):
    """Test retrieving events for a specific aggregate"""
    store = EventStore(temp_db)

    # Create multiple events
    event1 = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

    event2 = ConceptUpdated(aggregate_id="concept_001", updates={"name": "Updated"}, version=2)

    store.append_event(event1)
    store.append_event(event2)

    # Retrieve events
    events = store.get_events_by_aggregate("concept_001")

    assert len(events) == 2
    assert events[0].event_type == "ConceptCreated"
    assert events[1].event_type == "ConceptUpdated"
    assert events[0].version == 1
    assert events[1].version == 2


def test_get_events_from_version(temp_db):
    """Test retrieving events from a specific version"""
    store = EventStore(temp_db)

    # Create multiple events
    for i in range(1, 5):
        event = ConceptUpdated(
            aggregate_id="concept_001", updates={"name": f"Update {i}"}, version=i
        )
        store.append_event(event)

    # Get events from version 3
    events = store.get_events_by_aggregate("concept_001", from_version=3)

    assert len(events) == 2
    assert events[0].version == 3
    assert events[1].version == 4


def test_get_all_events(temp_db):
    """Test retrieving all events"""
    store = EventStore(temp_db)

    # Create events for different aggregates
    event1 = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test 1"}, version=1)

    event2 = ConceptCreated(aggregate_id="concept_002", concept_data={"name": "Test 2"}, version=1)

    store.append_event(event1)
    store.append_event(event2)

    # Get all events
    events = store.get_all_events()

    assert len(events) == 2


def test_get_all_events_with_limit(temp_db):
    """Test retrieving all events with limit"""
    store = EventStore(temp_db)

    # Create multiple events
    for i in range(10):
        event = ConceptCreated(
            aggregate_id=f"concept_{i:03d}", concept_data={"name": f"Test {i}"}, version=1
        )
        store.append_event(event)

    # Get with limit
    events = store.get_all_events(limit=5)

    assert len(events) == 5


def test_get_event_by_id(temp_db):
    """Test retrieving a specific event by ID"""
    store = EventStore(temp_db)

    event = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

    store.append_event(event)

    # Retrieve by ID
    retrieved = store.get_event_by_id(event.event_id)

    assert retrieved is not None
    assert retrieved.event_id == event.event_id
    assert retrieved.event_type == "ConceptCreated"


def test_get_latest_version(temp_db):
    """Test getting the latest version for an aggregate"""
    store = EventStore(temp_db)

    # Create multiple versions
    for i in range(1, 6):
        event = ConceptUpdated(
            aggregate_id="concept_001", updates={"name": f"Update {i}"}, version=i
        )
        store.append_event(event)

    latest_version = store.get_latest_version("concept_001")

    assert latest_version == 5


def test_get_latest_version_no_events(temp_db):
    """Test getting latest version when no events exist"""
    store = EventStore(temp_db)

    latest_version = store.get_latest_version("nonexistent")

    assert latest_version == 0


def test_count_events(temp_db):
    """Test counting events"""
    store = EventStore(temp_db)

    # Create events
    for i in range(5):
        event = ConceptCreated(
            aggregate_id=f"concept_{i:03d}", concept_data={"name": f"Test {i}"}, version=1
        )
        store.append_event(event)

    count = store.count_events()

    assert count == 5


def test_count_events_by_aggregate(temp_db):
    """Test counting events for a specific aggregate"""
    store = EventStore(temp_db)

    # Create events for concept_001
    for i in range(1, 4):
        event = ConceptUpdated(
            aggregate_id="concept_001", updates={"name": f"Update {i}"}, version=i
        )
        store.append_event(event)

    # Create event for concept_002
    event = ConceptCreated(aggregate_id="concept_002", concept_data={"name": "Test"}, version=1)
    store.append_event(event)

    count = store.count_events(aggregate_id="concept_001")

    assert count == 3


def test_count_events_by_type(temp_db):
    """Test counting events by event type"""
    store = EventStore(temp_db)

    # Create different event types
    for i in range(3):
        event = ConceptCreated(
            aggregate_id=f"concept_{i:03d}", concept_data={"name": f"Test {i}"}, version=1
        )
        store.append_event(event)

    event_updated = ConceptUpdated(
        aggregate_id="concept_000", updates={"name": "Updated"}, version=2
    )
    store.append_event(event_updated)

    count_created = store.count_events(event_type="ConceptCreated")
    count_updated = store.count_events(event_type="ConceptUpdated")

    assert count_created == 3
    assert count_updated == 1
