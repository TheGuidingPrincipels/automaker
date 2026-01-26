"""Tests for the confidence event listener."""

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, MagicMock

import pytest

from models.events import Event
from services.confidence.event_listener import ConfidenceEventListener
from services.confidence.models import Error, ErrorCode, Success
from services.event_store import EventStore
from services.neo4j_service import Neo4jService


def create_mock_concept_lock(always_acquired: bool = True, per_concept: dict = None):
    """
    Create a mock concept_lock context manager.

    Args:
        always_acquired: If True, lock is always acquired. If False, never acquired.
        per_concept: Dict mapping concept_id -> bool for per-concept control.
    """
    @asynccontextmanager
    async def mock_concept_lock(concept_id: str):
        if per_concept is not None:
            acquired = per_concept.get(concept_id, True)
        else:
            acquired = always_acquired
        yield acquired
    return mock_concept_lock


def build_listener(tmp_path, events, lock_always_acquired=True, lock_per_concept=None):
    event_store = Mock(spec=EventStore)
    event_store.get_all_events.return_value = events

    calculator = SimpleNamespace()
    calculator.calculate_composite_score = AsyncMock()

    cache_manager = SimpleNamespace()
    cache_manager.set_cached_score = AsyncMock()
    cache_manager.invalidate_concept_cache = AsyncMock()
    cache_manager.concept_lock = create_mock_concept_lock(
        always_acquired=lock_always_acquired,
        per_concept=lock_per_concept,
    )

    neo4j = Mock(spec=Neo4jService)

    listener = ConfidenceEventListener(
        event_store=event_store,
        calculator=calculator,  # type: ignore[arg-type]
        cache_manager=cache_manager,  # type: ignore[arg-type]
        neo4j_service=neo4j,
        checkpoint_path=tmp_path / "checkpoint.json",
        recalc_db_path=tmp_path / "pending_recalc.db",
    )

    return listener, calculator, cache_manager, neo4j, event_store


@pytest.mark.asyncio
async def test_concept_created_event_updates_score(tmp_path):
    event = Event(
        event_id="evt-1",
        event_type="ConceptCreated",
        aggregate_id="concept-1",
        aggregate_type="Concept",
        event_data={},
        version=1,
    )

    listener, calculator, cache_manager, neo4j, event_store = build_listener(tmp_path, [event])
    calculator.calculate_composite_score.return_value = Success(0.82)

    stats = await listener.process_pending_events()

    assert stats == {"processed": 1, "failed": 0, "skipped": 0, "pending_retries": 0}
    calculator.calculate_composite_score.assert_awaited_once_with("concept-1")
    cache_manager.set_cached_score.assert_awaited_once_with("concept-1", 82.0)
    neo4j.execute_write.assert_called_once()
    _, kwargs = neo4j.execute_write.call_args
    assert kwargs["parameters"]["concept_id"] == "concept-1"
    assert pytest.approx(kwargs["parameters"]["score"], rel=1e-9) == 82.0

    checkpoint_path = tmp_path / "checkpoint.json"
    with checkpoint_path.open() as fp:
        checkpoint = json.load(fp)
    assert checkpoint["last_offset"] == 1
    assert checkpoint["last_event_id"] == "evt-1"

    event_store.get_all_events.assert_called_once_with(limit=100, offset=0)


@pytest.mark.asyncio
async def test_concept_deleted_event_clears_cache(tmp_path):
    event = Event(
        event_id="evt-del",
        event_type="ConceptDeleted",
        aggregate_id="concept-42",
        aggregate_type="Concept",
        event_data={},
        version=2,
    )

    listener, calculator, cache_manager, neo4j, _ = build_listener(tmp_path, [event])

    stats = await listener.process_pending_events()

    assert stats == {"processed": 1, "failed": 0, "skipped": 0, "pending_retries": 0}
    cache_manager.invalidate_concept_cache.assert_awaited_once_with("concept-42")
    neo4j.execute_write.assert_called_once()
    args, kwargs = neo4j.execute_write.call_args
    assert "SET c.confidence_score = 0.0" in args[0]
    assert kwargs["parameters"]["concept_id"] == "concept-42"
    calculator.calculate_composite_score.assert_not_called()


@pytest.mark.asyncio
async def test_non_confidence_event_is_skipped(tmp_path):
    """Test that RelationshipCreated events with missing concept IDs are handled gracefully.

    Note: The event is counted as 'processed' even though it's effectively skipped
    due to missing concept IDs. This is by design - the event type IS handled,
    but the handler logs a warning and returns early.
    """
    event = Event(
        event_id="evt-skip",
        event_type="ConceptArchived",  # Unhandled event type - should be skipped
        aggregate_id="concept-7",
        aggregate_type="Concept",
        event_data={},
        version=1,
    )

    listener, calculator, cache_manager, _neo4j, _ = build_listener(tmp_path, [event])

    stats = await listener.process_pending_events()

    assert stats == {"processed": 0, "failed": 0, "skipped": 1, "pending_retries": 0}
    calculator.calculate_composite_score.assert_not_called()
    cache_manager.set_cached_score.assert_not_called()
    # Neo4j may be called for other reasons, but not for score updates


@pytest.mark.asyncio
async def test_calculation_error_counts_as_failure(tmp_path):
    event = Event(
        event_id="evt-fail",
        event_type="ConceptUpdated",
        aggregate_id="concept-9",
        aggregate_type="Concept",
        event_data={},
        version=3,
    )

    listener, calculator, cache_manager, neo4j, _ = build_listener(tmp_path, [event])
    calculator.calculate_composite_score.return_value = Error(
        "DB error", code=ErrorCode.DATABASE_ERROR
    )

    stats = await listener.process_pending_events()

    assert stats == {"processed": 0, "failed": 1, "skipped": 0, "pending_retries": 0}
    calculator.calculate_composite_score.assert_awaited_once_with("concept-9")
    cache_manager.set_cached_score.assert_not_called()
    neo4j.execute_write.assert_not_called()

    with (tmp_path / "checkpoint.json").open() as fp:
        checkpoint = json.load(fp)
    assert checkpoint["last_offset"] == 1
    assert checkpoint["last_event_id"] == "evt-fail"


@pytest.mark.asyncio
async def test_unexpected_error_stops_processing_without_advancing_offset(tmp_path):
    event = Event(
        event_id="evt-err",
        event_type="ConceptUpdated",
        aggregate_id="concept-10",
        aggregate_type="Concept",
        event_data={},
        version=4,
    )

    listener, calculator, cache_manager, neo4j, _ = build_listener(tmp_path, [event])
    calculator.calculate_composite_score.return_value = Success(0.5)
    neo4j.execute_write.side_effect = RuntimeError("write failed")

    stats = await listener.process_pending_events()

    assert stats == {"processed": 0, "failed": 1, "skipped": 0, "pending_retries": 0}
    # Cache still attempted before write failure
    cache_manager.set_cached_score.assert_awaited_once_with("concept-10", 50.0)

    with (tmp_path / "checkpoint.json").open() as fp:
        checkpoint = json.load(fp)
    assert checkpoint["last_offset"] == 0
    assert checkpoint["last_event_id"] is None


# =============================================================================
# Lock Failure Tests - Issue 10 Fix
# =============================================================================


@pytest.mark.asyncio
async def test_relationship_event_lock_failure_queues_pending_recalc(tmp_path):
    """When lock cannot be acquired, concept is queued for retry."""
    event = Event(
        event_id="evt-rel-1",
        event_type="RelationshipCreated",
        aggregate_id="relationship-1",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-a",
            "to_concept_id": "concept-b",
        },
        version=1,
    )

    # Lock always fails
    listener, calculator, cache_manager, neo4j, _ = build_listener(
        tmp_path, [event], lock_always_acquired=False
    )

    stats = await listener.process_pending_events()

    # Event should be marked as failed (not processed)
    assert stats["processed"] == 0
    assert stats["failed"] == 1

    # Checkpoint should NOT advance
    with (tmp_path / "checkpoint.json").open() as fp:
        checkpoint = json.load(fp)
    assert checkpoint["last_offset"] == 0

    # Verify concepts were queued for retry
    recalc_stats = await listener.get_pending_recalc_stats()
    assert recalc_stats.get("pending", 0) == 2  # Both concepts queued


@pytest.mark.asyncio
async def test_relationship_event_partial_lock_failure(tmp_path):
    """When one concept's lock fails, only that concept is queued."""
    event = Event(
        event_id="evt-rel-2",
        event_type="RelationshipCreated",
        aggregate_id="relationship-2",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-x",
            "to_concept_id": "concept-y",
        },
        version=1,
    )

    # concept-x gets lock, concept-y doesn't
    listener, calculator, cache_manager, neo4j, _ = build_listener(
        tmp_path,
        [event],
        lock_per_concept={"concept-x": True, "concept-y": False},
    )
    calculator.calculate_composite_score.return_value = Success(0.75)

    stats = await listener.process_pending_events()

    # Partial failure - event should fail
    assert stats["processed"] == 0
    assert stats["failed"] == 1

    # Checkpoint should NOT advance
    with (tmp_path / "checkpoint.json").open() as fp:
        checkpoint = json.load(fp)
    assert checkpoint["last_offset"] == 0

    # Only concept-y should be in pending queue
    recalc_stats = await listener.get_pending_recalc_stats()
    assert recalc_stats.get("pending", 0) == 1

    # concept-x should have been calculated
    calculator.calculate_composite_score.assert_awaited_once_with("concept-x")


@pytest.mark.asyncio
async def test_relationship_event_success_when_locks_acquired(tmp_path):
    """When both locks are acquired, both concepts are processed."""
    event = Event(
        event_id="evt-rel-3",
        event_type="RelationshipCreated",
        aggregate_id="relationship-3",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-p",
            "to_concept_id": "concept-q",
        },
        version=1,
    )

    listener, calculator, cache_manager, neo4j, _ = build_listener(
        tmp_path, [event], lock_always_acquired=True
    )
    calculator.calculate_composite_score.return_value = Success(0.65)

    stats = await listener.process_pending_events()

    # Both concepts processed successfully
    assert stats["processed"] == 1
    assert stats["failed"] == 0

    # Checkpoint should advance
    with (tmp_path / "checkpoint.json").open() as fp:
        checkpoint = json.load(fp)
    assert checkpoint["last_offset"] == 1
    assert checkpoint["last_event_id"] == "evt-rel-3"

    # Both concepts should have been calculated
    assert calculator.calculate_composite_score.await_count == 2


@pytest.mark.asyncio
async def test_pending_recalc_retried_on_next_cycle(tmp_path):
    """Pending recalculations are retried at the start of next processing cycle."""
    event = Event(
        event_id="evt-rel-4",
        event_type="RelationshipCreated",
        aggregate_id="relationship-4",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-m",
            "to_concept_id": "concept-n",
        },
        version=1,
    )

    # First cycle: locks fail
    listener, calculator, cache_manager, neo4j, event_store = build_listener(
        tmp_path, [event], lock_always_acquired=False
    )

    stats1 = await listener.process_pending_events()
    assert stats1["failed"] == 1

    # Verify concepts are in pending queue
    recalc_stats = await listener.get_pending_recalc_stats()
    assert recalc_stats.get("pending", 0) == 2

    # Second cycle: locks succeed - change the mock
    cache_manager.concept_lock = create_mock_concept_lock(always_acquired=True)
    calculator.calculate_composite_score.return_value = Success(0.80)
    event_store.get_all_events.return_value = []  # No new events

    stats2 = await listener.process_pending_events()

    # Pending recalculations should have been retried
    assert stats2["pending_retries"] == 2

    # Verify calculations were performed
    assert calculator.calculate_composite_score.await_count == 2


@pytest.mark.asyncio
async def test_pending_recalc_survives_db_connection(tmp_path):
    """Pending recalculations persist in SQLite and survive reconnection."""
    event = Event(
        event_id="evt-rel-5",
        event_type="RelationshipCreated",
        aggregate_id="relationship-5",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-s",
            "to_concept_id": "concept-t",
        },
        version=1,
    )

    # Create listener and queue concepts
    listener, calculator, cache_manager, neo4j, event_store = build_listener(
        tmp_path, [event], lock_always_acquired=False
    )

    await listener.process_pending_events()
    recalc_stats1 = await listener.get_pending_recalc_stats()
    assert recalc_stats1.get("pending", 0) == 2

    # Close and reopen DB connection
    listener.close_recalc_db()

    # Stats should still be readable (connection will be recreated)
    recalc_stats2 = await listener.get_pending_recalc_stats()
    assert recalc_stats2.get("pending", 0) == 2


@pytest.mark.asyncio
async def test_calculation_error_queues_for_retry(tmp_path):
    """When calculation fails, concept is queued for retry instead of raising."""
    event = Event(
        event_id="evt-rel-6",
        event_type="RelationshipCreated",
        aggregate_id="relationship-6",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-u",
            "to_concept_id": "concept-v",
        },
        version=1,
    )

    listener, calculator, cache_manager, neo4j, _ = build_listener(
        tmp_path, [event], lock_always_acquired=True
    )

    # First concept succeeds, second fails
    calculator.calculate_composite_score.side_effect = [
        Success(0.70),
        Error("Calculation failed", code=ErrorCode.INTERNAL_ERROR),
    ]

    stats = await listener.process_pending_events()

    # Event should fail (not all concepts processed)
    assert stats["failed"] == 1
    assert stats["processed"] == 0

    # Only concept-v should be in pending queue (calculation failure)
    recalc_stats = await listener.get_pending_recalc_stats()
    assert recalc_stats.get("pending", 0) == 1


@pytest.mark.asyncio
async def test_max_retries_escalates_to_outbox(tmp_path):
    """When retry count exceeds MAX_RECALC_RETRIES, concept is escalated to outbox."""
    event = Event(
        event_id="evt-rel-7",
        event_type="RelationshipCreated",
        aggregate_id="relationship-7",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-escalate",
            "to_concept_id": "concept-other",
        },
        version=1,
    )

    # Create mock outbox
    mock_outbox = Mock()
    mock_outbox.add_to_outbox = Mock()

    listener, calculator, cache_manager, neo4j, event_store = build_listener(
        tmp_path, [event], lock_always_acquired=False
    )
    listener.outbox = mock_outbox

    # First failure - queues both concepts
    await listener.process_pending_events()
    recalc_stats = await listener.get_pending_recalc_stats()
    assert recalc_stats.get("pending", 0) == 2

    # Manually set retry_count to MAX_RECALC_RETRIES - 1 for one concept
    conn = listener._get_recalc_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE pending_confidence_recalc
        SET retry_count = ?
        WHERE concept_id = ?
        """,
        (listener._config.MAX_RECALC_RETRIES - 1, "concept-escalate"),
    )
    conn.commit()

    # Next retry cycle - lock still fails
    event_store.get_all_events.return_value = []

    await listener.process_pending_events()

    # Verify escalation to outbox
    mock_outbox.add_to_outbox.assert_called_once()
    call_kwargs = mock_outbox.add_to_outbox.call_args[1]
    assert "confidence_recalc_escalated:concept-escalate" in call_kwargs["projection_name"]

    # Verify escalated status in database
    cursor.execute(
        "SELECT status FROM pending_confidence_recalc WHERE concept_id = ?",
        ("concept-escalate",),
    )
    row = cursor.fetchone()
    assert row["status"] == "escalated"


@pytest.mark.asyncio
async def test_linear_backoff_respects_delay(tmp_path):
    """Items are not retried until backoff delay has elapsed."""
    import sqlite3
    from datetime import datetime, timedelta

    event = Event(
        event_id="evt-rel-8",
        event_type="RelationshipCreated",
        aggregate_id="relationship-8",
        aggregate_type="Relationship",
        event_data={
            "from_concept_id": "concept-backoff",
            "to_concept_id": "concept-other2",
        },
        version=1,
    )

    listener, calculator, cache_manager, neo4j, event_store = build_listener(
        tmp_path, [event], lock_always_acquired=False
    )

    # First failure - queues both concepts
    await listener.process_pending_events()

    # Get the config delay
    delay_seconds = listener._config.RECALC_RETRY_DELAY_SECONDS

    # Manually set last_attempt to now and retry_count to 2
    # Expected delay = retry_count * delay_seconds = 2 * 2 = 4 seconds
    conn = listener._get_recalc_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE pending_confidence_recalc
        SET retry_count = 2, last_attempt = datetime('now')
        WHERE concept_id = ?
        """,
        ("concept-backoff",),
    )
    conn.commit()

    # Now try to process - concept-backoff should NOT be retried (not enough time)
    event_store.get_all_events.return_value = []
    cache_manager.concept_lock = create_mock_concept_lock(always_acquired=True)
    calculator.calculate_composite_score.return_value = Success(0.85)

    stats = await listener.process_pending_events()

    # Only concept-other2 should be retried (retry_count=0, no delay)
    # concept-backoff needs 4+ seconds to pass
    assert stats["pending_retries"] >= 1  # At least the other concept

    # Verify concept-backoff is still pending (not retried yet)
    cursor.execute(
        "SELECT status, retry_count FROM pending_confidence_recalc WHERE concept_id = ?",
        ("concept-backoff",),
    )
    row = cursor.fetchone()
    assert row["status"] == "pending"
    assert row["retry_count"] == 2  # Unchanged


@pytest.mark.asyncio
async def test_duplicate_queue_increments_retry_count(tmp_path):
    """Queueing same concept twice (UPSERT) increments retry_count."""
    listener, calculator, cache_manager, neo4j, _ = build_listener(
        tmp_path, [], lock_always_acquired=True
    )

    # Manually queue same concept twice
    await listener._queue_pending_recalc(
        concept_id="concept-dup",
        event_id="evt-dup",
        event_offset=10,
        error_message="First failure",
    )

    # Check initial state
    conn = listener._get_recalc_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT retry_count, error_message FROM pending_confidence_recalc WHERE concept_id = ?",
        ("concept-dup",),
    )
    row1 = cursor.fetchone()
    assert row1["retry_count"] == 0
    assert row1["error_message"] == "First failure"

    # Queue again with same concept_id and event_offset (should UPSERT)
    await listener._queue_pending_recalc(
        concept_id="concept-dup",
        event_id="evt-dup",
        event_offset=10,
        error_message="Second failure",
    )

    cursor.execute(
        "SELECT retry_count, error_message FROM pending_confidence_recalc WHERE concept_id = ?",
        ("concept-dup",),
    )
    row2 = cursor.fetchone()
    assert row2["retry_count"] == 1  # Incremented
    # COALESCE keeps first error message if new one is provided
    # Actually, COALESCE(?, error_message) means: use new if provided, else keep old
    # So new message should be used
    assert row2["error_message"] == "Second failure"

    # Verify only one entry exists (UPSERT, not duplicate INSERT)
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM pending_confidence_recalc WHERE concept_id = ?",
        ("concept-dup",),
    )
    count_row = cursor.fetchone()
    assert count_row["cnt"] == 1
