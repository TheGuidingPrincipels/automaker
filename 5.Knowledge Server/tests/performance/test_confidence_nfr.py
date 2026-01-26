"""Non-functional requirement validation tests for the confidence scoring suite."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Iterable
from dataclasses import dataclass

import pytest
import pytest_asyncio

from services.confidence.models import Success
from services.confidence.nfr_validation import (
    build_validation_report,
    evaluate_accuracy_suite,
    run_cache_suite,
    run_latency_suite,
    run_scalability_suite,
)


@dataclass
class StubCalculator:
    """Deterministic calculator that mimics async composite score evaluation."""

    delay_seconds: float = 0.0004

    async def calculate_composite_score(self, concept_id: str) -> Success:
        await asyncio.sleep(self.delay_seconds)

        # Deterministically derive a score from the concept id hash.
        base_value = (hash(concept_id) % 1000) / 1000
        normalized = 0.2 + (base_value * 0.6)  # Keep within [0.2, 0.8]
        return Success(round(normalized, 4))


class StubCache:
    """In-memory async cache for simulating warm-cache lookups."""

    def __init__(self, hit_ratio: float = 0.9) -> None:
        self._store: dict[str, float] = {}
        self._hit_ratio = hit_ratio

    async def warm(self, concept_ids: Iterable[str]) -> None:
        ids = list(concept_ids)
        cutoff = int(len(ids) * self._hit_ratio)
        for concept_id in ids[:cutoff]:
            # Cached values remain within the [0.0, 1.0] range
            self._store[concept_id] = 0.55

    async def get_cached_score(self, concept_id: str) -> float | None:
        await asyncio.sleep(0)  # Yield control to mimic async redis client
        return self._store.get(concept_id)


@pytest.fixture
def concept_ids_1000() -> list[str]:
    return [f"concept-{idx}" for idx in range(1000)]


@pytest.fixture
def concept_ids_10000() -> list[str]:
    return [f"concept-{idx}" for idx in range(10000)]


@pytest.fixture
def stub_calculator() -> StubCalculator:
    return StubCalculator()


@pytest_asyncio.fixture
async def warm_cache(concept_ids_1000: list[str]) -> StubCache:
    cache = StubCache(hit_ratio=0.9)
    await cache.warm(concept_ids_1000)
    return cache


@pytest.fixture
def manual_scores() -> list[float]:
    rng = random.Random(42)
    return [round(rng.uniform(0.1, 0.95), 4) for _ in range(500)]


@pytest.fixture
def predicted_scores(manual_scores: list[float]) -> list[float]:
    # Preserve strong correlation with minor bounded noise.
    rng = random.Random(123)
    scores: list[float] = []
    for score in manual_scores:
        noise = rng.uniform(-0.05, 0.05)
        adjusted = min(1.0, max(0.0, (score * 0.88) + 0.06 + noise))
        scores.append(round(adjusted, 4))
    return scores


@pytest.mark.asyncio
async def test_run_latency_suite_meets_thresholds(
    stub_calculator: StubCalculator, concept_ids_1000: list[str]
) -> None:
    metrics = await run_latency_suite(stub_calculator, concept_ids_1000, iterations=2)

    assert metrics["p95_latency_ms"] < 50
    assert metrics["p50_latency_ms"] < 30
    assert metrics["sample_size"] == len(concept_ids_1000) * 2


@pytest.mark.asyncio
async def test_run_cache_suite_maintains_strong_hit_rate(
    warm_cache: StubCache, concept_ids_1000: list[str]
) -> None:
    metrics = await run_cache_suite(warm_cache, concept_ids_1000)

    assert metrics["hit_rate"] >= 0.85
    assert metrics["total_lookups"] == len(concept_ids_1000)


@pytest.mark.asyncio
async def test_run_scalability_suite_handles_ten_thousand(
    stub_calculator: StubCalculator, concept_ids_10000: list[str]
) -> None:
    metrics = await run_scalability_suite(stub_calculator, concept_ids_10000, batch_size=500)

    assert metrics["total_concepts"] == len(concept_ids_10000)
    assert metrics["max_batch_size"] == 500
    assert metrics["calc_per_second"] > 1000


def test_evaluate_accuracy_suite_hits_quality_targets(
    predicted_scores: list[float], manual_scores: list[float]
) -> None:
    metrics = evaluate_accuracy_suite(predicted_scores, manual_scores)

    assert metrics["r_squared"] >= 0.75
    assert metrics["mae"] <= 0.15
    assert metrics["min_score"] >= 0.0
    assert metrics["max_score"] <= 1.0


@pytest.mark.asyncio
async def test_build_validation_report_flags_overall_pass(
    stub_calculator: StubCalculator,
    warm_cache: StubCache,
    concept_ids_1000: list[str],
    concept_ids_10000: list[str],
    predicted_scores: list[float],
    manual_scores: list[float],
) -> None:
    report = await build_validation_report(
        calculator=stub_calculator,
        cache=warm_cache,
        sample_concept_ids=concept_ids_1000,
        large_concept_ids=concept_ids_10000,
        predicted_scores=predicted_scores,
        manual_scores=manual_scores,
    )

    assert report["overall_status"] == "PASS"
    assert report["performance"]["p95_latency_ms"] < 50
    assert report["cache"]["hit_rate"] >= 0.85
    assert report["accuracy"]["r_squared"] >= 0.75
    assert report["scalability"]["total_concepts"] == len(concept_ids_10000)
    assert not report["recommendations"]
