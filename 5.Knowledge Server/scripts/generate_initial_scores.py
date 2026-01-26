#!/usr/bin/env python3
"""Generate initial confidence scores for all Concept nodes."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from config import Config
from services.confidence.cache_manager import CacheManager
from services.confidence.composite_calculator import CompositeCalculator
from services.confidence.models import Error
from services.confidence.runtime import ConfidenceRuntime, build_confidence_runtime
from services.neo4j_service import Neo4jService


logger = logging.getLogger(__name__)


async def _fetch_concept_ids(session) -> list[str]:
    """Return all concept identifiers ordered by creation timestamp."""
    result = await session.run(
        """
        MATCH (c:Concept)
        RETURN coalesce(c.id, c.concept_id) AS concept_id
        ORDER BY c.created_at
        """
    )
    records = await result.data()
    return [record["concept_id"] for record in records if record and record.get("concept_id")]


async def _update_concept_score(
    session,
    *,
    concept_id: str,
    score: float,
    components: dict[str, float],
    updated_at: datetime,
    default_tau: int,
) -> None:
    """Persist generated score back to Neo4j."""
    await session.run(
        """
        MATCH (c:Concept)
        WHERE c.id = $concept_id OR c.concept_id = $concept_id
        SET c.confidence_score = $score,
            c.confidence_last_updated = $updated_at,
            c.confidence_components = $components,
            c.retention_tau = coalesce(c.retention_tau, $default_tau)
        RETURN c.confidence_score AS updated_score
        """,
        {
            "concept_id": concept_id,
            "score": float(score),
            "components": components,
            "updated_at": updated_at,
            "default_tau": int(default_tau),
        },
    )


def _chunked(iterable: Iterable[str], size: int) -> Iterable[list[str]]:
    """Yield successive chunks from iterable."""
    chunk: list[str] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


async def generate_initial_scores(
    session,
    calculator: CompositeCalculator,
    cache_manager: CacheManager,
    *,
    batch_size: int = 100,
    default_tau: int = 7,
) -> dict[str, Any]:
    """
    Generate composite confidence scores for all concepts.

    Args:
        session: Async Neo4j session adapter (must expose ``run``).
        calculator: Composite calculator instance.
        cache_manager: Cache manager for persisting latest scores.
        batch_size: Number of concepts processed per batch.
        default_tau: Default retention tau when property missing.

    Returns:
        Summary dictionary with totals and failures.
    """
    concept_ids = await _fetch_concept_ids(session)
    total = len(concept_ids)
    summary: dict[str, Any] = {
        "total": total,
        "successful": 0,
        "failed": 0,
        "failures": [],
    }

    if total == 0:
        logger.info("No Concept nodes found; nothing to process")
        return summary

    logger.info("Starting initial score generation for %s concepts", total)

    weight_understanding = float(calculator.understanding_weight)
    weight_retention = float(calculator.retention_weight)

    for batch_index, batch in enumerate(_chunked(concept_ids, batch_size), start=1):
        logger.info("Processing batch %s (%s concepts)", batch_index, len(batch))

        for concept_id in batch:
            try:
                u_result = await calculator.understanding_calc.calculate_understanding_score(
                    concept_id
                )
                if isinstance(u_result, Error):
                    summary["failed"] += 1
                    summary["failures"].append(
                        {"concept_id": concept_id, "reason": u_result.message}
                    )
                    logger.warning(
                        "Understanding score failed for %s: %s",
                        concept_id,
                        u_result.message,
                    )
                    continue

                r_result = await calculator.retention_calc.calculate_retention_score(concept_id)
                if isinstance(r_result, Error):
                    summary["failed"] += 1
                    summary["failures"].append(
                        {"concept_id": concept_id, "reason": r_result.message}
                    )
                    logger.warning(
                        "Retention score failed for %s: %s",
                        concept_id,
                        r_result.message,
                    )
                    continue

                understanding_value = float(u_result.value)
                retention_value = float(r_result.value)
                score = (
                    weight_understanding * understanding_value + weight_retention * retention_value
                )
                score = max(0.0, min(1.0, float(score)))

                timestamp = datetime.now(UTC)
                components = {
                    "understanding": understanding_value,
                    "retention": retention_value,
                }

                await _update_concept_score(
                    session,
                    concept_id=concept_id,
                    score=score,
                    components=components,
                    updated_at=timestamp,
                    default_tau=default_tau,
                )

                try:
                    await cache_manager.set_cached_score(concept_id, score)
                except Exception as cache_exc:  # pragma: no cover - cache failures logged only
                    logger.warning(
                        "Failed to cache score for %s: %s",
                        concept_id,
                        cache_exc,
                    )

                summary["successful"] += 1

            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error(
                    "Unexpected error generating score for %s: %s",
                    concept_id,
                    exc,
                    exc_info=True,
                )
                summary["failed"] += 1
                summary["failures"].append({"concept_id": concept_id, "reason": str(exc)})

        logger.info(
            "Batch %s complete (%s successful, %s failed)",
            batch_index,
            summary["successful"],
            summary["failed"],
        )

    logger.info(
        "Score generation finished: %s success, %s failures (total %s)",
        summary["successful"],
        summary["failed"],
        summary["total"],
    )
    return summary


async def _build_runtime() -> tuple[ConfidenceRuntime, Neo4jService] | None:
    neo4j_service = Neo4jService(
        uri=Config.NEO4J_URI,
        user=Config.NEO4J_USER,
        password=Config.NEO4J_PASSWORD,
    )

    if not neo4j_service.connect():
        logger.error(
            "Failed to connect to Neo4j at %s. Ensure the database is running.",
            Config.NEO4J_URI,
        )
        return None

    runtime = await build_confidence_runtime(neo4j_service)
    if runtime is None:
        logger.error("Confidence runtime could not be created (likely Redis unavailable).")
        neo4j_service.close()
        return None

    return runtime, neo4j_service


async def _run(batch_size: int = 100) -> int:
    # Config is loaded from centralized config system
    Config.validate()

    build_result = await _build_runtime()
    if build_result is None:
        return 1
    runtime, neo4j_service = build_result

    try:
        result = await generate_initial_scores(
            runtime.data_access.session,
            runtime.calculator,
            runtime.cache_manager,
            batch_size=batch_size,
            default_tau=runtime.calculator.retention_calc.default_tau,
        )

        print("\n✅ Initial confidence score generation complete")
        print(f"   Total concepts   : {result['total']}")
        print(f"   Successful       : {result['successful']}")
        print(f"   Failed           : {result['failed']}")

        if result["failed"]:
            print("   ⚠️  Failures:")
            for failure in result["failures"]:
                print(f"      - {failure['concept_id']}: {failure['reason']}")
            return 1

        return 0

    finally:
        try:
            await runtime.close()
        finally:
            neo4j_service.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
