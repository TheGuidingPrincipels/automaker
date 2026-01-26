"""
Tests for EventStore event signaling mechanism.

Tests that EventStore can signal waiting tasks when new events are appended,
enabling event-driven processing instead of polling.
"""

import asyncio
from datetime import datetime

import pytest

from models.events import Event
from services.event_store import EventStore


@pytest.fixture
def event_store(tmp_path):
    """Create a temporary EventStore for testing."""
    db_path = tmp_path / "test_events.db"
    # Initialize database schema
    store = EventStore(str(db_path))
    conn = store._get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            aggregate_type TEXT NOT NULL,
            event_data TEXT NOT NULL,
            metadata TEXT,
            version INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()
    return store


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return Event(
        event_id="test-event-001",
        event_type="ConceptCreated",
        aggregate_id="concept-123",
        aggregate_type="Concept",
        event_data={"name": "Test Concept"},
        metadata={},
        version=1,
        created_at=datetime.utcnow().isoformat(),
    )


def test_event_store_has_new_event_signal(event_store):
    """Test that EventStore has a new_event_signal attribute."""
    assert hasattr(event_store, "new_event_signal")
    assert isinstance(event_store.new_event_signal, asyncio.Event)


@pytest.mark.asyncio
async def test_signal_is_set_when_event_appended(event_store, sample_event):
    """Test that appending an event sets the new_event_signal."""
    # Signal should not be set initially
    assert not event_store.new_event_signal.is_set()

    # Append event
    event_store.append_event(sample_event)

    # Signal should now be set
    assert event_store.new_event_signal.is_set()


@pytest.mark.asyncio
async def test_signal_can_be_awaited(event_store, sample_event):
    """Test that the signal can be awaited and triggers immediately when set."""
    # Clear the signal
    event_store.new_event_signal.clear()

    async def wait_for_signal():
        """Wait for the signal to be set."""
        await event_store.new_event_signal.wait()
        return True

    # Start waiting in background
    wait_task = asyncio.create_task(wait_for_signal())

    # Give the task a moment to start waiting
    await asyncio.sleep(0.01)

    # Append event (should trigger signal)
    event_store.append_event(sample_event)

    # Wait should complete immediately
    result = await asyncio.wait_for(wait_task, timeout=0.1)
    assert result is True


@pytest.mark.asyncio
async def test_signal_persists_after_first_wait(event_store, sample_event):
    """Test that signal remains set until explicitly cleared."""
    event_store.new_event_signal.clear()

    # Append event
    event_store.append_event(sample_event)

    # Signal should be set
    assert event_store.new_event_signal.is_set()

    # Wait for signal (should return immediately)
    await event_store.new_event_signal.wait()

    # Signal should still be set (doesn't auto-clear)
    assert event_store.new_event_signal.is_set()

    # Manually clear for next iteration
    event_store.new_event_signal.clear()
    assert not event_store.new_event_signal.is_set()


@pytest.mark.asyncio
async def test_multiple_events_trigger_signal(event_store):
    """Test that multiple events can be appended and signal works each time."""
    event_store.new_event_signal.clear()

    for i in range(3):
        event = Event(
            event_id=f"test-event-{i:03d}",
            event_type="ConceptCreated",
            aggregate_id=f"concept-{i}",
            aggregate_type="Concept",
            event_data={"name": f"Test Concept {i}"},
            metadata={},
            version=1,
            created_at=datetime.utcnow().isoformat(),
        )

        event_store.append_event(event)
        assert event_store.new_event_signal.is_set()

        # Clear for next iteration
        event_store.new_event_signal.clear()
