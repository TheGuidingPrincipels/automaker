#!/usr/bin/env python3
"""Validate confidence score properties for Concept nodes."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from neo4j import AsyncDriver, AsyncGraphDatabase, basic_auth

from config import Config


logger = logging.getLogger(__name__)


class _AsyncSession(Protocol):
    async def run(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> Any:  # pragma: no cover - protocol
        ...


SessionFactory = Callable[[], Awaitable[_AsyncSession]]


def _resolve_session_factory(provider: AsyncDriver | SessionFactory) -> SessionFactory:
    if hasattr(provider, "session") and callable(provider.session):
        return provider.session
    if callable(provider):
        return provider
    raise TypeError("Expected an AsyncGraphDatabase driver or async session factory")


async def validate_scores(
    provider: AsyncDriver | SessionFactory,
) -> dict[str, Any]:
    """
    Verify existence and health of confidence score properties.

    Args:
        provider: Neo4j async driver or session factory.

    Returns:
        Dictionary summarizing validation metrics.
    """
    session_factory = _resolve_session_factory(provider)

    async with session_factory() as session:
        null_result = await session.run(
            """
            MATCH (c:Concept)
            WHERE c.confidence_score IS NULL
            RETURN count(c) AS null_score_count
            """
        )
        null_record = await null_result.single()
        null_scores = int(null_record.get("null_score_count", 0)) if null_record else 0

        range_result = await session.run(
            """
            MATCH (c:Concept)
            WHERE c.confidence_score < 0.0 OR c.confidence_score > 1.0
            RETURN count(c) AS out_of_range_count
            """
        )
        range_record = await range_result.single()
        out_of_range = int(range_record.get("out_of_range_count", 0)) if range_record else 0

        components_result = await session.run(
            """
            MATCH (c:Concept)
            WHERE c.confidence_components IS NULL
            RETURN count(c) AS missing_components_count
            """
        )
        components_record = await components_result.single()
        missing_components = (
            int(components_record.get("missing_components_count", 0)) if components_record else 0
        )

        stats_result = await session.run(
            """
            MATCH (c:Concept)
            WITH c.confidence_score AS score
            RETURN
                count(score) AS total_concepts,
                min(score) AS min_score,
                max(score) AS max_score,
                avg(score) AS avg_score
            """
        )
        stats_record = await stats_result.single() or {}
        stats = {
            "total": int(stats_record.get("total_concepts", 0) or 0),
            "min": float(stats_record.get("min_score") or 0.0),
            "max": float(stats_record.get("max_score") or 0.0),
            "avg": float(stats_record.get("avg_score") or 0.0),
        }

    valid = null_scores == 0 and out_of_range == 0 and missing_components == 0

    if valid:
        logger.info("Confidence score validation passed")
    else:
        logger.warning(
            "Confidence score validation failed "
            "(null=%s, out_of_range=%s, missing_components=%s)",
            null_scores,
            out_of_range,
            missing_components,
        )

    return {
        "valid": valid,
        "null_scores": null_scores,
        "out_of_range": out_of_range,
        "missing_components": missing_components,
        "stats": stats,
    }


async def _run() -> int:
    # Config is loaded from centralized config system
    Config.validate()

    driver = AsyncGraphDatabase.driver(
        Config.NEO4J_URI,
        auth=basic_auth(Config.NEO4J_USER, Config.NEO4J_PASSWORD),
    )

    try:
        await driver.verify_connectivity()
        logger.info("Connected to Neo4j at %s", Config.NEO4J_URI)

        result = await validate_scores(driver)

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📊 CONFIDENCE SCORE VALIDATION")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        if result["valid"]:
            print("✅ Validation PASSED\n")
        else:
            print("❌ Validation FAILED\n")

        print("Issues Found:")
        print(f"  - Null scores        : {result['null_scores']}")
        print(f"  - Out-of-range scores: {result['out_of_range']}")
        print(f"  - Missing components : {result['missing_components']}\n")

        stats = result["stats"]
        if stats["total"]:
            print("Score Statistics:")
            print(f"  - Total concepts: {stats['total']}")
            print(f"  - Min score     : {stats['min']:.3f}")
            print(f"  - Max score     : {stats['max']:.3f}")
            print(f"  - Avg score     : {stats['avg']:.3f}")
        else:
            print("Score Statistics: no concepts found.")

        return 0 if result["valid"] else 1

    finally:
        await driver.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
