"""Utilities for validating non-functional requirements of the confidence suite."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from statistics import mean
from typing import Any

from services.confidence.models import Error


def _compute_percentile(samples: Sequence[float], percentile: float) -> float:
    """Return the percentile for a sorted sequence using linear interpolation."""
    if not samples:
        return 0.0

    if len(samples) == 1:
        return float(samples[0])

    rank = (len(samples) - 1) * (percentile / 100.0)
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    lower_value = samples[lower_index]
    upper_value = samples[upper_index]

    if lower_index == upper_index:
        return float(lower_value)

    fraction = rank - lower_index
    return float(lower_value + (upper_value - lower_value) * fraction)


async def run_latency_suite(
    calculator: Any,
    concept_ids: Sequence[str],
    *,
    iterations: int = 1,
) -> dict[str, float]:
    """
    Measure latency metrics for composite score calculations.

    Args:
        calculator: Component exposing an async calculate_composite_score method.
        concept_ids: Iterable of concept identifiers to measure.
        iterations: Number of passes over the concept ids.
    """
    if iterations <= 0:
        raise ValueError("iterations must be positive")

    latencies: list[float] = []
    for _ in range(iterations):
        for concept_id in concept_ids:
            start = time.perf_counter()
            result = await calculator.calculate_composite_score(concept_id)
            end = time.perf_counter()

            if isinstance(result, Error):
                raise RuntimeError(f"Calculation failed for concept {concept_id}: {result.message}")

            latencies.append((end - start) * 1000)  # Convert to milliseconds

    latencies.sort()
    return {
        "p50_latency_ms": _compute_percentile(latencies, 50),
        "p95_latency_ms": _compute_percentile(latencies, 95),
        "p99_latency_ms": _compute_percentile(latencies, 99),
        "sample_size": len(latencies),
    }


async def run_cache_suite(
    cache: Any,
    concept_ids: Sequence[str],
) -> dict[str, float]:
    """Measure cache hit rate for provided concept ids."""
    total = len(concept_ids)
    if total == 0:
        return {"hit_rate": 0.0, "total_lookups": 0, "hits": 0, "misses": 0}

    hits = 0
    for concept_id in concept_ids:
        cached = await cache.get_cached_score(concept_id)
        if cached is not None:
            hits += 1

    hit_rate = hits / total
    return {"hit_rate": hit_rate, "total_lookups": total, "hits": hits, "misses": total - hits}


async def run_scalability_suite(
    calculator: Any,
    concept_ids: Sequence[str],
    *,
    batch_size: int = 1000,
) -> dict[str, float]:
    """Simulate high-volume score calculations and report throughput."""
    total = len(concept_ids)
    if total == 0:
        return {
            "total_concepts": 0,
            "duration_seconds": 0.0,
            "calc_per_second": 0.0,
            "max_batch_size": 0,
        }

    batch_size = max(1, batch_size)
    start = time.perf_counter()

    for index in range(0, total, batch_size):
        batch = concept_ids[index : index + batch_size]
        await asyncio.gather(
            *(calculator.calculate_composite_score(concept_id) for concept_id in batch)
        )

    duration = time.perf_counter() - start
    throughput = total / duration if duration > 0 else float("inf")

    return {
        "total_concepts": total,
        "duration_seconds": duration,
        "calc_per_second": throughput,
        "max_batch_size": min(batch_size, total),
    }


def evaluate_accuracy_suite(
    predicted_scores: Sequence[float],
    manual_scores: Sequence[float],
) -> dict[str, float]:
    """Compute accuracy metrics between predicted and manual scores."""
    if len(predicted_scores) != len(manual_scores):
        raise ValueError("predicted_scores and manual_scores must have identical lengths")

    if not predicted_scores:
        raise ValueError("score collections must not be empty")

    min_score = min(predicted_scores)
    max_score = max(predicted_scores)
    mean_score = mean(predicted_scores)

    # Ensure all scores are within valid range
    if min_score < 0.0 or max_score > 1.0:
        raise ValueError("predicted_scores must be within [0.0, 1.0]")

    mae = sum(abs(p - m) for p, m in zip(predicted_scores, manual_scores, strict=False)) / len(
        predicted_scores
    )

    manual_mean = mean(manual_scores)
    ss_tot = sum((obs - manual_mean) ** 2 for obs in manual_scores)
    if ss_tot == 0:
        r_squared = 1.0
    else:
        ss_res = sum(
            (obs - pred) ** 2 for obs, pred in zip(manual_scores, predicted_scores, strict=False)
        )
        r_squared = 1 - (ss_res / ss_tot)

    return {
        "min_score": min_score,
        "max_score": max_score,
        "mean_score": mean_score,
        "mae": mae,
        "r_squared": r_squared,
    }


def _default_timestamp() -> datetime:
    return datetime.now(UTC)


async def build_validation_report(
    *,
    calculator: Any,
    cache: Any,
    sample_concept_ids: Sequence[str],
    large_concept_ids: Sequence[str],
    predicted_scores: Sequence[float],
    manual_scores: Sequence[float],
    timestamp_provider: Callable[[], datetime] | None = None,
) -> dict[str, object]:
    """Aggregate all NFR suites into a single structured report."""
    timestamp = (timestamp_provider or _default_timestamp)()

    performance = await run_latency_suite(calculator, sample_concept_ids, iterations=2)
    cache_metrics = await run_cache_suite(cache, sample_concept_ids)
    scalability = await run_scalability_suite(calculator, large_concept_ids, batch_size=500)
    accuracy = evaluate_accuracy_suite(predicted_scores, manual_scores)

    recommendations: list[str] = []

    if performance["p95_latency_ms"] >= 50:
        recommendations.append("CRITICAL: p95 latency exceeded 50ms threshold")
    if cache_metrics["hit_rate"] < 0.8:
        recommendations.append("WARNING: Cache hit rate below 80% target")
    if accuracy["r_squared"] < 0.75:
        recommendations.append("CRITICAL: R² below 0.75 target")
    if accuracy["mae"] > 0.15:
        recommendations.append("WARNING: MAE above 0.15 threshold")
    if scalability["calc_per_second"] < 1000:
        recommendations.append("WARNING: Throughput below 1k calculations per second")

    overall_status = (
        "PASS" if not any(rec.startswith("CRITICAL") for rec in recommendations) else "FAIL"
    )

    return {
        "plan": "feat-20251103-confidence-automation",
        "generated_at": timestamp.isoformat(),
        "performance": performance,
        "cache": cache_metrics,
        "scalability": scalability,
        "accuracy": accuracy,
        "recommendations": recommendations,
        "overall_status": overall_status,
    }
