from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import pytest

from services.confidence.event_processor import EventProcessor
from services.confidence.models import Error, Success
from services.confidence.scheduler import Priority


def build_processor():
    cache = SimpleNamespace()
    cache.invalidate_concept_cache = AsyncMock()
    cache.invalidate_score_cache = AsyncMock()

    scheduler = SimpleNamespace()
    scheduler.schedule_recalculation = AsyncMock()

    retention = SimpleNamespace()
    retention.update_retention_tau = AsyncMock(return_value=Success(10))

    processor = EventProcessor(  # type: ignore[arg-type]
        cache_manager=cache,
        scheduler=scheduler,
        retention_calculator=retention,
    )
    return processor, cache, scheduler, retention


@pytest.mark.asyncio
async def test_register_handler_tracks_handlers():
    processor, *_ = build_processor()
    handler = AsyncMock()

    processor.register_handler("custom.event", handler)

    assert "custom.event" in processor.handlers
    assert handler in processor.handlers["custom.event"]


@pytest.mark.asyncio
async def test_emit_invokes_registered_handlers():
    processor, *_ = build_processor()
    handler = AsyncMock()

    # Use processor without builtin handlers
    processor_no_defaults = EventProcessor(  # type: ignore[arg-type]
        cache_manager=processor.cache_manager,
        scheduler=processor.scheduler,
        retention_calculator=processor.retention_calculator,
        register_default_handlers=False,
    )
    processor_no_defaults.register_handler("concept.updated", handler)

    await processor_no_defaults.emit({"type": "concept.updated", "concept_id": "c-1"})

    assert handler.await_count == 1


@pytest.mark.asyncio
async def test_process_event_requires_type():
    processor, *_ = build_processor()

    with pytest.raises(ValueError):
        await processor.process_event({"concept_id": "missing-type"})


@pytest.mark.asyncio
async def test_concept_updated_handler_invalidates_cache_and_schedules():
    processor, cache, scheduler, _ = build_processor()

    await processor.process_event({"type": "concept.updated", "concept_id": "c-1"})

    assert cache.invalidate_concept_cache.await_count == 1
    assert cache.invalidate_concept_cache.await_args.args == ("c-1",)
    assert scheduler.schedule_recalculation.await_count == 1
    args, kwargs = scheduler.schedule_recalculation.await_args
    assert args[0] == "c-1"
    assert kwargs["priority"] == Priority.MEDIUM


@pytest.mark.asyncio
async def test_relationship_handler_requires_related_concept():
    processor, cache, scheduler, _ = build_processor()

    await processor.process_event({"type": "relationship.created", "concept_id": "c-1"})

    assert scheduler.schedule_recalculation.await_count == 0
    assert cache.invalidate_concept_cache.await_count == 0


@pytest.mark.asyncio
async def test_relationship_handler_invalidates_both_concepts():
    processor, cache, scheduler, _ = build_processor()

    await processor.process_event(
        {
            "type": "relationship.deleted",
            "concept_id": "c-1",
            "related_concept_id": "c-2",
        }
    )

    cache.invalidate_concept_cache.assert_has_awaits(
        [
            call("c-1", invalidate_score=False, invalidate_calc=True),
            call("c-2", invalidate_score=False, invalidate_calc=True),
        ],
        any_order=True,
    )
    calls = scheduler.schedule_recalculation.await_args_list
    assert {c.args[0] for c in calls} == {"c-1", "c-2"}
    assert all(c.kwargs["priority"] == Priority.HIGH for c in calls)


@pytest.mark.asyncio
async def test_review_completed_handler_updates_tau_and_schedules():
    processor, cache, scheduler, retention = build_processor()

    await processor.process_event({"type": "review.completed", "concept_id": "c-9"})

    assert retention.update_retention_tau.await_count == 1
    assert retention.update_retention_tau.await_args.args == ("c-9",)
    assert cache.invalidate_score_cache.await_count == 1
    assert cache.invalidate_score_cache.await_args.args == ("c-9",)
    assert scheduler.schedule_recalculation.await_count == 1
    assert scheduler.schedule_recalculation.await_args.kwargs["priority"] == Priority.LOW


@pytest.mark.asyncio
async def test_review_completed_handler_logs_error_on_failure(caplog):
    processor, cache, scheduler, retention = build_processor()
    retention.update_retention_tau.return_value = Error("boom", code="ERROR")  # type: ignore[arg-type]

    await processor.process_event({"type": "review.completed", "concept_id": "c-9"})

    assert "Retention tau update failed" in caplog.text
    assert cache.invalidate_score_cache.await_count == 1
    assert scheduler.schedule_recalculation.await_count == 1
