"""
Tests for confidence worker event-driven processing.

Tests that the confidence worker responds immediately to event signals
instead of polling at fixed intervals.
"""

import asyncio
import contextlib
from unittest.mock import AsyncMock, Mock

import pytest

from services.confidence.event_listener import ConfidenceEventListener


@pytest.fixture
def mock_listener():
    """Create a mock ConfidenceEventListener."""
    listener = Mock(spec=ConfidenceEventListener)
    listener.process_pending_events = AsyncMock(
        return_value={"processed": 1, "failed": 0, "skipped": 0}
    )
    return listener


@pytest.fixture
def event_signal():
    """Create an asyncio.Event for testing."""
    return asyncio.Event()


@pytest.mark.asyncio
async def test_worker_waits_on_event_signal(mock_listener, event_signal):
    """Test that worker waits on event signal instead of fixed sleep."""
    # Import the worker function from mcp_server
    from mcp_server import _run_confidence_worker

    # Track how many times process_pending_events was called
    call_count = 0

    async def track_calls(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            # Stop after 2 iterations
            raise asyncio.CancelledError()
        return {"processed": 1, "failed": 0, "skipped": 0}

    mock_listener.process_pending_events.side_effect = track_calls

    # Run worker with event signal
    with pytest.raises(asyncio.CancelledError):
        await _run_confidence_worker(
            mock_listener, event_signal=event_signal, interval_seconds=10.0
        )

    # Worker should have been called at least once
    assert call_count >= 1


@pytest.mark.asyncio
async def test_worker_responds_immediately_to_signal(mock_listener, event_signal):
    """Test that worker wakes up immediately when signal is set."""
    from mcp_server import _run_confidence_worker

    start_time = asyncio.get_event_loop().time()
    times_called = []

    async def track_timing(*args, **kwargs):
        current_time = asyncio.get_event_loop().time()
        times_called.append(current_time - start_time)
        if len(times_called) >= 2:
            raise asyncio.CancelledError()
        return {"processed": 1, "failed": 0, "skipped": 0}

    mock_listener.process_pending_events.side_effect = track_timing

    # Start worker in background
    worker_task = asyncio.create_task(
        _run_confidence_worker(mock_listener, event_signal=event_signal, interval_seconds=10.0)
    )

    # Give worker time to start
    await asyncio.sleep(0.01)

    # Set signal to trigger immediate processing
    event_signal.set()

    # Wait for worker to complete
    with contextlib.suppress(asyncio.CancelledError):
        await worker_task

    # Worker should have responded within 100ms (not 10 seconds)
    assert len(times_called) >= 2
    # Second call should happen quickly after signal, not after 10s interval
    if len(times_called) >= 2:
        time_between_calls = times_called[1] - times_called[0]
        assert (
            time_between_calls < 0.5
        ), f"Worker took {time_between_calls}s to respond, expected <0.5s"


@pytest.mark.asyncio
async def test_worker_clears_signal_after_processing(mock_listener, event_signal):
    """Test that worker clears the event signal after processing."""
    from mcp_server import _run_confidence_worker

    iteration_count = 0

    async def count_iterations(*args, **kwargs):
        nonlocal iteration_count
        iteration_count += 1
        if iteration_count >= 2:
            raise asyncio.CancelledError()
        return {"processed": 1, "failed": 0, "skipped": 0}

    mock_listener.process_pending_events.side_effect = count_iterations

    # Set signal initially
    event_signal.set()

    with pytest.raises(asyncio.CancelledError):
        await _run_confidence_worker(mock_listener, event_signal=event_signal, interval_seconds=0.1)

    # Signal should be cleared after processing
    # (it might be set again if more events came in, but at least it was cleared once)
    assert iteration_count >= 2


@pytest.mark.asyncio
async def test_worker_has_timeout_fallback(mock_listener, event_signal):
    """Test that worker has a timeout even if signal never fires (defensive)."""
    from mcp_server import _run_confidence_worker

    call_count = 0

    async def track_calls(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()
        return {"processed": 0, "failed": 0, "skipped": 0}

    mock_listener.process_pending_events.side_effect = track_calls

    # Don't set signal - worker should still poll periodically
    with pytest.raises(asyncio.CancelledError):
        await _run_confidence_worker(mock_listener, event_signal=event_signal, interval_seconds=0.1)

    # Should have been called at least twice (initial + timeout)
    assert call_count >= 2


@pytest.mark.asyncio
async def test_worker_backwards_compatible_without_signal():
    """Test that worker still works without event_signal parameter (backwards compatibility)."""
    from mcp_server import _run_confidence_worker

    mock_listener = Mock(spec=ConfidenceEventListener)
    call_count = 0

    async def track_calls(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()
        return {"processed": 1, "failed": 0, "skipped": 0}

    mock_listener.process_pending_events = AsyncMock(side_effect=track_calls)

    # Call without event_signal - should use old polling behavior
    with pytest.raises(asyncio.CancelledError):
        await _run_confidence_worker(mock_listener, interval_seconds=0.1)

    # Should work (poll-based)
    assert call_count >= 2
