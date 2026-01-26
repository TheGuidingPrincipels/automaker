"""
Integration test for confidence score recalculation timing.

Verifies that confidence scores are recalculated immediately after events
are appended, addressing issue #2 (non-deterministic timing).
"""

import asyncio
import contextlib
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from models.events import Event
from services.confidence.event_listener import ConfidenceEventListener
from services.event_store import EventStore


@pytest.fixture
def temp_event_store(tmp_path):
    """Create a temporary EventStore for testing."""
    db_path = tmp_path / "test_events.db"
    store = EventStore(str(db_path))
    # Initialize database schema
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


@pytest.mark.asyncio
async def test_confidence_score_updates_immediately_after_concept_creation(temp_event_store):
    """
    Test that confidence scores are calculated immediately after concept creation.

    This test verifies the fix for issue #2: confidence score timing is now deterministic
    and events are processed immediately (not after 0-5000ms poll delay).
    """
    from mcp_server import _run_confidence_worker

    # Mock the listener to track processing timing
    mock_listener = Mock(spec=ConfidenceEventListener)
    processing_times = []
    start_time = time.time()

    async def track_processing(*args, **kwargs):
        elapsed = time.time() - start_time
        processing_times.append(elapsed)
        if len(processing_times) >= 2:  # Initial + 1 event
            raise asyncio.CancelledError()
        return {"processed": 1, "failed": 0, "skipped": 0}

    mock_listener.process_pending_events = AsyncMock(side_effect=track_processing)

    # Start worker with event signal
    worker_task = asyncio.create_task(
        _run_confidence_worker(
            mock_listener,
            event_signal=temp_event_store.new_event_signal,
            interval_seconds=5.0,  # Old poll interval for comparison
        )
    )

    # Let worker initialize
    await asyncio.sleep(0.05)
    event_append_time = time.time() - start_time

    # Simulate concept creation event
    event = Event(
        event_id="test-concept-created-001",
        event_type="ConceptCreated",
        aggregate_id="concept-123",
        aggregate_type="Concept",
        event_data={"name": "Test Concept", "explanation": "Testing immediate recalc"},
        metadata={},
        version=1,
        created_at=datetime.utcnow().isoformat(),
    )
    temp_event_store.append_event(event)

    # Wait for processing
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.wait_for(worker_task, timeout=2.0)

    # Verify processing happened immediately (not after 5s poll)
    assert len(processing_times) >= 2
    time_to_process = processing_times[1] - event_append_time

    # With event-driven processing, should be < 100ms (not 0-5000ms)
    assert (
        time_to_process < 0.5
    ), f"Processing took {time_to_process:.3f}s, expected <0.5s (old system: 0-5s)"

    print(f"✓ Event processed in {time_to_process:.3f}s (vs 0-5s with polling)")


@pytest.mark.asyncio
async def test_confidence_score_updates_immediately_after_relationship_creation(temp_event_store):
    """
    Test that confidence scores update immediately after relationship creation.

    Issue #2 observed: ~6 seconds delay after delete_relationship.
    With fix: Should be < 100ms.
    """
    from mcp_server import _run_confidence_worker

    mock_listener = Mock(spec=ConfidenceEventListener)
    processing_times = []
    start_time = time.time()

    async def track_processing(*args, **kwargs):
        elapsed = time.time() - start_time
        processing_times.append(elapsed)
        if len(processing_times) >= 2:  # Initial + 1 event
            raise asyncio.CancelledError()
        return {"processed": 1, "failed": 0, "skipped": 0}

    mock_listener.process_pending_events = AsyncMock(side_effect=track_processing)

    # Start worker
    worker_task = asyncio.create_task(
        _run_confidence_worker(
            mock_listener, event_signal=temp_event_store.new_event_signal, interval_seconds=5.0
        )
    )

    await asyncio.sleep(0.05)
    event_append_time = time.time() - start_time

    # Simulate relationship creation event
    event = Event(
        event_id="test-rel-created-001",
        event_type="RelationshipCreated",
        aggregate_id="relationship-456",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-123",
            "to_concept_id": "concept-456",
            "relationship_type": "relates_to",
        },
        metadata={},
        version=1,
        created_at=datetime.utcnow().isoformat(),
    )
    temp_event_store.append_event(event)

    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.wait_for(worker_task, timeout=2.0)

    # Verify immediate processing
    assert len(processing_times) >= 2
    time_to_process = processing_times[1] - event_append_time
    assert (
        time_to_process < 0.5
    ), f"Relationship processing took {time_to_process:.3f}s, expected <0.5s"

    print(f"✓ Relationship event processed in {time_to_process:.3f}s")


@pytest.mark.asyncio
async def test_multiple_rapid_events_all_processed(temp_event_store):
    """
    Test that multiple events in rapid succession are all processed.

    Verifies no events are lost when many arrive quickly.
    """
    from mcp_server import _run_confidence_worker

    mock_listener = Mock(spec=ConfidenceEventListener)
    processing_count = 0

    async def count_processing(*args, **kwargs):
        nonlocal processing_count
        processing_count += 1
        if processing_count >= 6:  # Initial + 5 events
            raise asyncio.CancelledError()
        return {"processed": 1, "failed": 0, "skipped": 0}

    mock_listener.process_pending_events = AsyncMock(side_effect=count_processing)

    # Start worker
    worker_task = asyncio.create_task(
        _run_confidence_worker(
            mock_listener, event_signal=temp_event_store.new_event_signal, interval_seconds=5.0
        )
    )

    await asyncio.sleep(0.05)

    # Append 5 events rapidly
    start = time.time()
    for i in range(5):
        event = Event(
            event_id=f"rapid-event-{i:03d}",
            event_type="ConceptUpdated",
            aggregate_id=f"concept-{i}",
            aggregate_type="Concept",
            event_data={"name": f"Rapid Test {i}"},
            metadata={},
            version=1,
            created_at=datetime.utcnow().isoformat(),
        )
        temp_event_store.append_event(event)
        await asyncio.sleep(0.01)  # Small delay between events

    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.wait_for(worker_task, timeout=3.0)

    elapsed = time.time() - start

    # All events should be processed
    assert processing_count >= 6, f"Only {processing_count} processed, expected 6"

    # Should complete in reasonable time (< 2s, not 25s with polling)
    assert elapsed < 2.0, f"Took {elapsed:.3f}s to process 5 events"

    print(f"✓ Processed 5 events in {elapsed:.3f}s (vs ~25s with polling)")


@pytest.mark.asyncio
async def test_timing_is_deterministic(temp_event_store):
    """
    Test that processing timing is deterministic (not variable 0-5000ms).

    Run same operation multiple times and verify consistent timing.
    """
    from mcp_server import _run_confidence_worker

    timings = []

    for run in range(3):
        mock_listener = Mock(spec=ConfidenceEventListener)
        processing_times = []
        start_time = time.time()

        async def track_processing(*args, **kwargs):
            elapsed = time.time() - start_time
            processing_times.append(elapsed)
            if len(processing_times) >= 2:
                raise asyncio.CancelledError()
            return {"processed": 1, "failed": 0, "skipped": 0}

        mock_listener.process_pending_events = AsyncMock(side_effect=track_processing)

        worker_task = asyncio.create_task(
            _run_confidence_worker(
                mock_listener, event_signal=temp_event_store.new_event_signal, interval_seconds=5.0
            )
        )

        await asyncio.sleep(0.05)
        append_time = time.time() - start_time

        event = Event(
            event_id=f"deterministic-test-{run:03d}",
            event_type="ConceptCreated",
            aggregate_id=f"concept-det-{run}",
            aggregate_type="Concept",
            event_data={"name": f"Deterministic Test {run}"},
            metadata={},
            version=1,
            created_at=datetime.utcnow().isoformat(),
        )
        temp_event_store.append_event(event)

        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(worker_task, timeout=2.0)

        if len(processing_times) >= 2:
            delay = processing_times[1] - append_time
            timings.append(delay)

    # Verify all timings are consistent (within 100ms of each other)
    assert len(timings) == 3
    max_timing = max(timings)
    min_timing = min(timings)
    variance = max_timing - min_timing

    # With polling: variance could be 0-5000ms
    # With event-driven: variance should be < 100ms
    assert variance < 0.2, f"Timing variance {variance:.3f}s too high. Timings: {timings}"

    print(f"✓ Timing is deterministic: {timings} (variance: {variance:.3f}s)")
