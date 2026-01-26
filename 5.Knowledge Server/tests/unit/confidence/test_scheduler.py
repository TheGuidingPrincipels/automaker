import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.confidence.models import Success
from services.confidence.scheduler import Priority, RecalculationScheduler


def build_scheduler(lock_side_effect=None):
    calculator = SimpleNamespace()
    calculator.calculate_composite_score = AsyncMock(return_value=Success(0.9))

    cache = SimpleNamespace()
    cache.set_cached_score = AsyncMock()

    redis_client = SimpleNamespace()
    redis_client.set = AsyncMock(side_effect=lock_side_effect or (lambda *_, **__: True))
    redis_client.eval = AsyncMock(return_value=1)

    scheduler = RecalculationScheduler(  # type: ignore[arg-type]
        composite_calculator=calculator,
        cache_manager=cache,
        redis_client=redis_client,
    )
    return scheduler, calculator, cache, redis_client


@pytest.mark.asyncio
async def test_schedule_recalculation_adds_to_queue():
    scheduler, *_ = build_scheduler()

    await scheduler.schedule_recalculation("concept-1", priority=Priority.HIGH)

    assert await scheduler.get_queue_size() == 1


@pytest.mark.asyncio
async def test_duplicate_schedule_is_deduplicated():
    scheduler, *_ = build_scheduler()

    await scheduler.schedule_recalculation("concept-1", priority=Priority.MEDIUM)
    await scheduler.schedule_recalculation("concept-1", priority=Priority.LOW)

    assert await scheduler.get_queue_size() == 1


@pytest.mark.asyncio
async def test_priority_upgrade_replaces_existing_entry():
    scheduler, calculator, _, _ = build_scheduler()

    await scheduler.schedule_recalculation("concept-1", priority=Priority.LOW)
    await scheduler.schedule_recalculation("concept-1", priority=Priority.HIGH)
    await scheduler.process_queue()

    assert calculator.calculate_composite_score.await_count == 1
    assert calculator.calculate_composite_score.call_args_list[0].args[0] == "concept-1"


@pytest.mark.asyncio
async def test_process_queue_orders_by_priority():
    scheduler, calculator, cache, _ = build_scheduler()

    await scheduler.schedule_recalculation("low", priority=Priority.LOW)
    await scheduler.schedule_recalculation("high", priority=Priority.HIGH)
    await scheduler.schedule_recalculation("medium", priority=Priority.MEDIUM)

    await scheduler.process_queue()

    processed = [call.args[0] for call in calculator.calculate_composite_score.call_args_list]
    assert processed == ["high", "medium", "low"]
    assert cache.set_cached_score.await_count == 3


@pytest.mark.asyncio
async def test_concurrent_recalculations_respect_lock():
    lock_effects = [True, False, False]

    async def lock_side_effect(*_args, **_kwargs):
        return lock_effects.pop(0)

    scheduler, calculator, cache, redis_client = build_scheduler(lock_side_effect=lock_side_effect)

    tasks = [
        scheduler.process_recalculation("concept-42"),
        scheduler.process_recalculation("concept-42"),
        scheduler.process_recalculation("concept-42"),
    ]
    await asyncio.gather(*tasks)

    assert calculator.calculate_composite_score.await_count == 1
    assert cache.set_cached_score.await_count == 1
    assert redis_client.eval.await_count == 1
