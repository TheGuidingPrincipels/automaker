#!/usr/bin/env python3
"""Schema update script for confidence scoring properties."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from neo4j import AsyncDriver, AsyncGraphDatabase, basic_auth

from config import Config
from services.confidence.config import ConfidenceConfig


logger = logging.getLogger(__name__)


class _AsyncSession(Protocol):
    async def run(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> Any:  # pragma: no cover - protocol
        ...


SessionFactory = Callable[[], Awaitable[_AsyncSession]]


def _resolve_session_factory(provider: AsyncDriver | SessionFactory) -> SessionFactory:
    """
    Accept either an AsyncDriver instance or an async session factory callable.

    Returns:
        A callable that yields an async session supporting ``run``.
    """
    if hasattr(provider, "session") and callable(provider.session):
        return provider.session
    if callable(provider):
        return provider
    raise TypeError("Expected an AsyncGraphDatabase driver or async session factory")


async def update_schema(
    provider: AsyncDriver | SessionFactory,
    *,
    default_tau: int | None = None,
) -> dict[str, Any]:
    """
    Add confidence-related properties to all Concept nodes.

    Args:
        provider: Neo4j async driver or session factory.
        default_tau: Optional override for the retention tau default.

    Returns:
        Dictionary with update status metadata.
    """
    session_factory = _resolve_session_factory(provider)
    confidence_config = ConfidenceConfig()
    tau = default_tau if default_tau is not None else confidence_config.DEFAULT_TAU_DAYS

    query = """
    MATCH (c:Concept)
    SET c.confidence_score = coalesce(c.confidence_score, 0.0),
        c.confidence_last_updated = coalesce(c.confidence_last_updated, datetime()),
        c.confidence_components = coalesce(
            c.confidence_components,
            {understanding: 0.0, retention: 0.0}
        ),
        c.retention_tau = coalesce(c.retention_tau, $default_tau)
    RETURN count(c) AS updated_count
    """

    async with session_factory() as session:
        result = await session.run(query, {"default_tau": int(tau)})
        record = await result.single()

    updated_count = int(record.get("updated_count", 0)) if record else 0
    logger.info("Schema update complete; %s concepts updated", updated_count)
    return {"status": "success", "updated_count": updated_count}


async def verify_schema_update(
    provider: AsyncDriver | SessionFactory,
) -> dict[str, Any]:
    """
    Verify Concept nodes contain all confidence properties.

    Args:
        provider: Neo4j async driver or session factory.

    Returns:
        Dictionary with verification results.
    """
    session_factory = _resolve_session_factory(provider)

    query = """
    MATCH (c:Concept)
    WHERE c.confidence_score IS NULL
       OR c.confidence_last_updated IS NULL
       OR c.confidence_components IS NULL
       OR c.retention_tau IS NULL
    RETURN count(c) AS missing_properties_count
    """

    async with session_factory() as session:
        result = await session.run(query)
        record = await result.single()

    missing = int(record.get("missing_properties_count", 0)) if record else 0
    valid = missing == 0

    if valid:
        logger.info("Schema verification passed; all concepts have required properties")
    else:
        logger.warning("%s concepts missing confidence properties", missing)

    return {"valid": valid, "missing_count": missing}


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

        update_result = await update_schema(driver)
        print(f"✅ Schema update complete: {update_result['updated_count']} concepts processed")

        verification = await verify_schema_update(driver)
        if verification["valid"]:
            print("✅ Schema verification passed")
            return 0

        print(
            f"⚠️  Schema verification failed: {verification['missing_count']} concepts missing properties"
        )
        return 1

    finally:
        await driver.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
