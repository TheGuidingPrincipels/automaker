"""Factory utilities for wiring the confidence scoring runtime."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

import redis.asyncio as redis

from services.confidence.cache_manager import CacheManager
from services.confidence.composite_calculator import CompositeCalculator
from services.confidence.config import CacheConfig, ConfidenceConfig
from services.confidence.data_access import DataAccessLayer
from services.confidence.retention_calculator import RetentionCalculator
from services.confidence.tau_event_emitter import TauEventEmitter
from services.confidence.understanding_calculator import UnderstandingCalculator
from services.neo4j_service import Neo4jService

if TYPE_CHECKING:
    from projections.neo4j_projection import Neo4jProjection
    from services.event_store import EventStore
    from services.outbox import Outbox

logger = logging.getLogger(__name__)


class _ResultAdapter:
    """Async-friendly wrapper around Neo4j query results."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    def single(self) -> dict[str, Any] | None:
        return self._records[0] if self._records else None

    async def data(self) -> list[dict[str, Any]]:
        return self._records


class AsyncNeo4jSessionAdapter:
    """
    Minimal async adapter over the synchronous Neo4jService.

    DataAccessLayer expects an async-compatible session interface. This adapter
    executes synchronous queries on a thread to avoid blocking the event loop.
    """

    def __init__(self, neo4j_service: Neo4jService, *, database: str = "neo4j") -> None:
        self._neo4j = neo4j_service
        self._database = database

    async def run(self, query: str, **parameters: Any) -> _ResultAdapter:
        records = await asyncio.to_thread(self._execute, query, parameters)
        return _ResultAdapter(records)

    def _execute(self, query: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        with self._neo4j.session(database=self._database) as session:
            result = session.run(query, parameters)
            return result.data()


@dataclass
class ConfidenceRuntime:
    """Runtime bundle for confidence scoring components."""

    redis_client: redis.Redis
    cache_manager: CacheManager
    calculator: CompositeCalculator
    data_access: DataAccessLayer

    async def close(self) -> None:
        try:
            await self.redis_client.close()
        except Exception as exc:  # pragma: no cover - defensive cleanup
            logger.warning("Failed to close Redis client: %s", exc)


async def build_confidence_runtime(
    neo4j_service: Neo4jService,
    *,
    redis_override: Optional[redis.Redis] = None,
    event_store: Optional["EventStore"] = None,
    outbox: Optional["Outbox"] = None,
    neo4j_projection: Optional["Neo4jProjection"] = None,
) -> Optional[ConfidenceRuntime]:
    """
    Build confidence scoring components if dependencies are available.

    Args:
        neo4j_service: Neo4j service for database operations
        redis_override: Optional Redis client override (for testing)
        event_store: Optional EventStore for event sourcing (enables tau event emission)
        outbox: Optional Outbox for reliable event processing (enables tau event emission)
        neo4j_projection: Optional Neo4j projection (enables tau event emission)

    Returns:
        ConfidenceRuntime when Redis and Neo4j are reachable, otherwise None.

    Note:
        If event_store, outbox, and neo4j_projection are all provided,
        the TauEventEmitter will be configured for proper event sourcing.
        Otherwise, a NoOpTauEventEmitter is used which logs warnings.
    """
    cache_config = CacheConfig()

    redis_client = redis_override or redis.Redis(
        host=cache_config.REDIS_HOST,
        port=cache_config.REDIS_PORT,
        db=cache_config.REDIS_DB,
        password=cache_config.REDIS_PASSWORD or None,
        decode_responses=True,
    )

    try:
        await redis_client.ping()
    except Exception as exc:
        logger.warning(
            "Confidence runtime disabled (Redis unavailable at %s:%s): %s",
            cache_config.REDIS_HOST,
            cache_config.REDIS_PORT,
            exc,
        )
        if redis_override is None:
            try:
                await redis_client.close()
            except Exception:  # pragma: no cover - defensive
                pass
        return None

    session_adapter = AsyncNeo4jSessionAdapter(neo4j_service)
    data_access = DataAccessLayer(session_adapter)

    cache_manager = CacheManager(redis_client, cache_config)
    confidence_config = ConfidenceConfig()
    understanding = UnderstandingCalculator(
        data_access, cache_manager, max_relationships=confidence_config.MAX_RELATIONSHIPS
    )

    # Configure tau event emitter for proper event sourcing
    tau_event_emitter = None
    if event_store is not None and outbox is not None and neo4j_projection is not None:
        tau_event_emitter = TauEventEmitter(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
        )
        logger.info("TauEventEmitter configured for event sourcing")
    else:
        logger.warning(
            "TauEventEmitter not configured (missing event_store, outbox, or neo4j_projection). "
            "Tau updates will use NoOpTauEventEmitter (bypasses event sourcing)."
        )

    retention = RetentionCalculator(
        data_access,
        cache_manager,
        tau_event_emitter=tau_event_emitter,
    )
    calculator = CompositeCalculator(understanding, retention)

    logger.info("Confidence scoring runtime initialized")
    return ConfidenceRuntime(
        redis_client=redis_client,
        cache_manager=cache_manager,
        calculator=calculator,
        data_access=data_access,
    )
