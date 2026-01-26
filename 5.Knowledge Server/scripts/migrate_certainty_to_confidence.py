#!/usr/bin/env python3
"""
Migration script: certainty_score → confidence_score

This migration:
1. Renames the Neo4j property from certainty_score to confidence_score
2. Converts values from 0-1 scale to 0-100 scale (multiply by 100)
3. Updates related property names (certainty_last_updated → confidence_last_updated)

Part of Phase 1: Terminology Standardization
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Protocol

from neo4j import AsyncDriver, AsyncGraphDatabase, basic_auth

from config import Config

logger = logging.getLogger(__name__)


class _AsyncSession(Protocol):
    async def run(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        ...


SessionFactory = Callable[[], Awaitable[_AsyncSession]]


def _resolve_session_factory(provider: AsyncDriver | SessionFactory) -> SessionFactory:
    """Accept either an AsyncDriver instance or an async session factory callable."""
    if hasattr(provider, "session") and callable(getattr(provider, "session")):
        return getattr(provider, "session")
    if callable(provider):
        return provider
    raise TypeError("Expected an AsyncGraphDatabase driver or async session factory")


async def migrate_certainty_to_confidence(
    provider: AsyncDriver | SessionFactory,
) -> dict[str, Any]:
    """
    Migrate certainty_score to confidence_score with scale conversion.

    - Renames certainty_score → confidence_score
    - Converts 0-1 scale to 0-100 scale
    - Renames certainty_last_updated → confidence_last_updated
    - Renames certainty_components → confidence_components

    Args:
        provider: Neo4j async driver or session factory.

    Returns:
        Dictionary with migration status metadata.
    """
    session_factory = _resolve_session_factory(provider)

    # Step 1: Migrate certainty_score → confidence_score with scale conversion
    migrate_score_query = """
    MATCH (c:Concept)
    WHERE c.certainty_score IS NOT NULL
    SET c.confidence_score = c.certainty_score * 100
    REMOVE c.certainty_score
    RETURN count(c) AS migrated_count
    """

    # Step 2: Migrate certainty_last_updated → confidence_last_updated
    migrate_timestamp_query = """
    MATCH (c:Concept)
    WHERE c.certainty_last_updated IS NOT NULL
    SET c.confidence_last_updated = c.certainty_last_updated
    REMOVE c.certainty_last_updated
    RETURN count(c) AS migrated_count
    """

    # Step 3: Migrate certainty_components → confidence_components
    migrate_components_query = """
    MATCH (c:Concept)
    WHERE c.certainty_components IS NOT NULL
    SET c.confidence_components = c.certainty_components
    REMOVE c.certainty_components
    RETURN count(c) AS migrated_count
    """

    results = {}

    async with session_factory() as session:
        # Migrate scores
        result = await session.run(migrate_score_query)
        record = await result.single()
        results["scores_migrated"] = int(record.get("migrated_count", 0)) if record else 0
        logger.info("Migrated %s certainty_score → confidence_score", results["scores_migrated"])

        # Migrate timestamps
        result = await session.run(migrate_timestamp_query)
        record = await result.single()
        results["timestamps_migrated"] = int(record.get("migrated_count", 0)) if record else 0
        logger.info("Migrated %s certainty_last_updated → confidence_last_updated", results["timestamps_migrated"])

        # Migrate components
        result = await session.run(migrate_components_query)
        record = await result.single()
        results["components_migrated"] = int(record.get("migrated_count", 0)) if record else 0
        logger.info("Migrated %s certainty_components → confidence_components", results["components_migrated"])

    results["status"] = "success"
    return results


async def verify_migration(
    provider: AsyncDriver | SessionFactory,
) -> dict[str, Any]:
    """
    Verify the migration completed successfully.

    Checks that:
    - No concepts have old certainty_* properties
    - Concepts have new confidence_* properties with valid ranges

    Args:
        provider: Neo4j async driver or session factory.

    Returns:
        Dictionary with verification results.
    """
    session_factory = _resolve_session_factory(provider)

    # Check for remaining old properties
    old_properties_query = """
    MATCH (c:Concept)
    WHERE c.certainty_score IS NOT NULL
       OR c.certainty_last_updated IS NOT NULL
       OR c.certainty_components IS NOT NULL
    RETURN count(c) AS old_property_count
    """

    # Check new properties and valid ranges (0-100 scale)
    new_properties_query = """
    MATCH (c:Concept)
    WHERE c.confidence_score IS NOT NULL
    RETURN count(c) AS concepts_with_score,
           min(c.confidence_score) AS min_score,
           max(c.confidence_score) AS max_score,
           avg(c.confidence_score) AS avg_score
    """

    # Check for out-of-range values
    range_check_query = """
    MATCH (c:Concept)
    WHERE c.confidence_score IS NOT NULL
      AND (c.confidence_score < 0 OR c.confidence_score > 100)
    RETURN count(c) AS out_of_range_count
    """

    async with session_factory() as session:
        # Check old properties
        result = await session.run(old_properties_query)
        record = await result.single()
        old_count = int(record.get("old_property_count", 0)) if record else 0

        # Check new properties
        result = await session.run(new_properties_query)
        record = await result.single()
        if record:
            concepts_with_score = int(record.get("concepts_with_score", 0))
            min_score = record.get("min_score")
            max_score = record.get("max_score")
            avg_score = record.get("avg_score")
        else:
            concepts_with_score = 0
            min_score = max_score = avg_score = None

        # Check range
        result = await session.run(range_check_query)
        record = await result.single()
        out_of_range = int(record.get("out_of_range_count", 0)) if record else 0

    valid = old_count == 0 and out_of_range == 0

    return {
        "valid": valid,
        "old_properties_remaining": old_count,
        "concepts_with_confidence_score": concepts_with_score,
        "min_score": min_score,
        "max_score": max_score,
        "avg_score": avg_score,
        "out_of_range_count": out_of_range,
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

        print("Starting migration: certainty_score → confidence_score (0-1 → 0-100 scale)")
        print("-" * 60)

        migration_result = await migrate_certainty_to_confidence(driver)
        print(f"  Scores migrated: {migration_result['scores_migrated']}")
        print(f"  Timestamps migrated: {migration_result['timestamps_migrated']}")
        print(f"  Components migrated: {migration_result['components_migrated']}")

        print("\nVerifying migration...")
        verification = await verify_migration(driver)

        if verification["valid"]:
            print("  Migration verification passed")
            print(f"  Concepts with confidence_score: {verification['concepts_with_confidence_score']}")
            if verification["min_score"] is not None:
                print(f"  Score range: {verification['min_score']:.2f} - {verification['max_score']:.2f}")
                print(f"  Average score: {verification['avg_score']:.2f}")
            return 0

        print("  Migration verification FAILED:")
        if verification["old_properties_remaining"] > 0:
            print(f"    - {verification['old_properties_remaining']} concepts still have old properties")
        if verification["out_of_range_count"] > 0:
            print(f"    - {verification['out_of_range_count']} concepts have out-of-range scores")
        return 1

    finally:
        await driver.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
