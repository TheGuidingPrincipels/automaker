import pytest

from services.confidence.event_processor import EventProcessor
from services.confidence.models import Success
from services.confidence.scheduler import RecalculationScheduler


class FakeRedis:
    def __init__(self):
        self.locks = set()

    async def set(self, key, value, nx=True, ex=10):
        if nx and key in self.locks:
            return False
        self.locks.add(key)
        return True

    async def eval(self, _script, _numkeys, key, _value):
        self.locks.discard(key)
        return 1


class FakeCache:
    def __init__(self):
        self.invalidations = []
        self.score_invalidations = []
        self.scores = {}

    async def invalidate_concept_cache(
        self, concept_id, invalidate_score=True, invalidate_calc=True
    ):
        self.invalidations.append((concept_id, invalidate_score, invalidate_calc))

    async def invalidate_score_cache(self, concept_id):
        self.score_invalidations.append(concept_id)

    async def set_cached_score(self, concept_id, score):
        self.scores[concept_id] = score


class FakeRetentionCalculator:
    def __init__(self):
        self.calls = []

    async def update_retention_tau(self, concept_id):
        self.calls.append(concept_id)
        return Success(10)


class FakeCompositeCalculator:
    def __init__(self, score=0.75):
        self.calls = []
        self.score = score

    async def calculate_composite_score(self, concept_id):
        self.calls.append(concept_id)
        return Success(self.score)


def build_components(score=0.75, *, batch_window=5.0):
    cache = FakeCache()
    calculator = FakeCompositeCalculator(score=score)
    redis_client = FakeRedis()
    scheduler = RecalculationScheduler(
        composite_calculator=calculator,  # type: ignore[arg-type]
        cache_manager=cache,  # type: ignore[arg-type]
        redis_client=redis_client,  # type: ignore[arg-type]
        batch_window_seconds=batch_window,
    )
    retention = FakeRetentionCalculator()
    processor = EventProcessor(  # type: ignore[arg-type]
        cache_manager=cache,
        scheduler=scheduler,
        retention_calculator=retention,
    )
    return processor, scheduler, cache, calculator, retention


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concept_updated_event_triggers_recalculation():
    processor, scheduler, cache, calculator, _ = build_components(score=0.9)

    await processor.process_event({"type": "concept.updated", "concept_id": "c-1"})
    await scheduler.process_queue()

    assert calculator.calls == ["c-1"]
    assert cache.scores["c-1"] == 0.9


@pytest.mark.asyncio
@pytest.mark.integration
async def test_relationship_event_schedules_both_concepts():
    processor, scheduler, cache, calculator, _ = build_components()

    await processor.process_event(
        {
            "type": "relationship.created",
            "concept_id": "c-1",
            "related_concept_id": "c-2",
        }
    )

    assert await scheduler.get_queue_size() == 2

    await scheduler.process_queue()

    assert set(calculator.calls) == {"c-1", "c-2"}
    assert set(cache.scores.keys()) == {"c-1", "c-2"}
    assert all(score == 0.75 for score in cache.scores.values())


@pytest.mark.asyncio
@pytest.mark.integration
async def test_review_completed_updates_tau_and_requeues():
    processor, scheduler, cache, calculator, retention = build_components(score=0.6)

    await processor.process_event({"type": "review.completed", "concept_id": "c-5"})
    await scheduler.process_queue()

    assert retention.calls == ["c-5"]
    assert cache.score_invalidations == ["c-5"]
    assert calculator.calls == ["c-5"]
    assert cache.scores["c-5"] == 0.6


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unknown_event_is_ignored():
    processor, scheduler, cache, calculator, retention = build_components()

    await processor.process_event({"type": "unregistered.event", "concept_id": "ignored"})

    assert await scheduler.get_queue_size() == 0
    assert calculator.calls == []
    assert retention.calls == []
    assert cache.scores == {}
