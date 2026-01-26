"""Integration-style tests for retention and composite calculators."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pytest

from services.confidence.composite_calculator import CompositeCalculator
from services.confidence.models import Error, ErrorCode, ReviewData, Success
from services.confidence.retention_calculator import RetentionCalculator


pytestmark = pytest.mark.integration


class StubCache:
    def __init__(self):
        self.review_cache: dict[str, ReviewData] = {}

    async def get_cached_review_history(self, concept_id: str):
        return self.review_cache.get(concept_id)

    async def set_cached_review_history(self, concept_id: str, data: ReviewData, ttl=None):
        self.review_cache[concept_id] = data

    async def invalidate_concept_cache(
        self, concept_id: str, invalidate_score=True, invalidate_calc=True
    ):
        if invalidate_calc:
            self.review_cache.pop(concept_id, None)


class StubDataAccess:
    def __init__(self):
        now = datetime.now()
        self.review_data = {
            "recent": ReviewData(last_reviewed_at=now, days_since_review=0, review_count=1),
            "stale": ReviewData(
                last_reviewed_at=now - timedelta(days=30), days_since_review=30, review_count=2
            ),
        }
        self.tau_map = {"recent": 7, "stale": 7}
        self.review_call_count = 0

    async def get_review_history(self, concept_id: str):
        self.review_call_count += 1
        data = self.review_data.get(concept_id)
        if data:
            return Success(data)
        return Error("not found", ErrorCode.NOT_FOUND)

    async def get_concept_tau(self, concept_id: str):
        if concept_id not in self.review_data:
            return Error("not found", ErrorCode.NOT_FOUND)
        return Success(self.tau_map.get(concept_id, 7))


class StubTauEventEmitter:
    """
    Stub event emitter for integration tests.

    Actually updates the tau value in the stub data access layer,
    simulating what the real event sourcing pipeline would do.
    """

    def __init__(self, data_access: StubDataAccess):
        self.data_access = data_access

    def emit_tau_updated(
        self,
        concept_id: str,
        new_tau: int,
        previous_tau: Optional[int] = None,
    ):
        """Emit tau update by directly updating the stub's tau_map."""
        if concept_id not in self.data_access.review_data:
            return Error("not found", ErrorCode.NOT_FOUND)
        self.data_access.tau_map[concept_id] = new_tau
        return Success(new_tau)


class StubUnderstandingCalculator:
    def __init__(self, scores: dict[str, float]):
        self.scores = scores

    async def calculate_understanding_score(self, concept_id: str):
        if concept_id not in self.scores:
            return Error("missing", ErrorCode.NOT_FOUND)
        return Success(self.scores[concept_id])


@pytest.fixture
def stub_environment():
    data_access = StubDataAccess()
    cache = StubCache()
    # Create tau event emitter that updates the stub's tau_map
    tau_emitter = StubTauEventEmitter(data_access)
    retention = RetentionCalculator(data_access, cache, tau_event_emitter=tau_emitter)
    understanding = StubUnderstandingCalculator({"recent": 0.9, "stale": 0.6})
    composite = CompositeCalculator(understanding, retention)
    return data_access, cache, retention, understanding, composite


@pytest.mark.asyncio
async def test_retention_and_composite_for_recent_concept(stub_environment):
    _, _, retention, _, composite = stub_environment

    retention_score = await retention.calculate_retention_score("recent")
    composite_score = await composite.calculate_composite_score("recent")

    assert isinstance(retention_score, Success)
    assert retention_score.value == pytest.approx(1.0, abs=0.01)
    assert isinstance(composite_score, Success)
    assert composite_score.value > 0.85


@pytest.mark.asyncio
async def test_retention_for_stale_concept_is_low(stub_environment):
    _, _, retention, _, _ = stub_environment

    result = await retention.calculate_retention_score("stale")
    assert isinstance(result, Success)
    assert result.value < 0.02


@pytest.mark.asyncio
async def test_composite_reflects_both_scores(stub_environment):
    _, _, _, _, composite = stub_environment

    result = await composite.calculate_composite_score("stale")
    assert isinstance(result, Success)
    assert 0.20 < result.value < 0.50


@pytest.mark.asyncio
async def test_tau_update_increases_retention_window(stub_environment):
    data_access, _, retention, _, _ = stub_environment

    # Simulate review to increase tau
    update = await retention.update_retention_tau("stale", review_completed=True)
    assert isinstance(update, Success)
    assert update.value > 7

    # Move review date closer based on new tau
    data_access.review_data["stale"] = ReviewData(
        last_reviewed_at=datetime.now() - timedelta(days=10),
        days_since_review=10,
        review_count=3,
    )

    score = await retention.calculate_retention_score("stale")
    assert isinstance(score, Success)
    assert score.value > 0.3


@pytest.mark.asyncio
async def test_cache_hit_skips_data_access(stub_environment):
    data_access, cache, retention, _, _ = stub_environment

    # Prime cache
    cached = ReviewData(
        last_reviewed_at=datetime.now(),
        days_since_review=3,
        review_count=1,
    )
    await cache.set_cached_review_history("recent", cached)

    result = await retention.calculate_retention_score("recent")
    assert isinstance(result, Success)
    assert data_access.review_call_count == 0


@pytest.mark.asyncio
async def test_missing_concept_returns_error(stub_environment):
    _, _, retention, _, composite = stub_environment

    retention_result = await retention.calculate_retention_score("missing")
    composite_result = await composite.calculate_composite_score("missing")

    assert isinstance(retention_result, Error)
    assert retention_result.code == ErrorCode.NOT_FOUND
    assert isinstance(composite_result, Error)
    assert composite_result.code == ErrorCode.NOT_FOUND
