"""Centralized service container for dependency injection.

Replaces scattered global variables with a single, testable container.
Follows the singleton pattern from config/settings.py.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from services.chromadb_service import ChromaDbService
    from services.embedding_service import EmbeddingService
    from services.event_store import EventStore
    from services.neo4j_service import Neo4jService
    from services.outbox import Outbox
    from services.repository import DualStorageRepository
    from services.confidence.composite_calculator import CompositeCalculator
    from services.confidence.event_listener import ConfidenceEventListener
    from services.confidence.runtime import ConfidenceRuntime

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """
    Centralized container for all runtime service instances.

    Usage:
        from services.container import get_container
        container = get_container()
        container.repository.create_concept(...)

    Testing:
        from services.container import reset_container, set_container
        reset_container()  # Clear singleton
        set_container(mock_container)  # Inject test container
    """

    # Core infrastructure services
    event_store: Optional["EventStore"] = None
    outbox: Optional["Outbox"] = None

    # Database services
    neo4j_service: Optional["Neo4jService"] = None
    chromadb_service: Optional["ChromaDbService"] = None
    embedding_service: Optional["EmbeddingService"] = None

    # Repository (orchestrates dual storage)
    repository: Optional["DualStorageRepository"] = None

    # Confidence scoring
    confidence_runtime: Optional["ConfidenceRuntime"] = None
    confidence_listener: Optional["ConfidenceEventListener"] = None
    confidence_listener_task: Optional[asyncio.Task] = None

    @property
    def confidence_service(self) -> Optional["CompositeCalculator"]:
        """Convenience accessor for confidence calculator."""
        if self.confidence_runtime:
            return self.confidence_runtime.calculator
        return None

    def is_initialized(self) -> bool:
        """Check if core services are initialized."""
        return all([
            self.event_store is not None,
            self.outbox is not None,
            self.repository is not None,
            self.neo4j_service is not None,
            self.chromadb_service is not None,
        ])

    def get_service_status(self) -> dict:
        """Return initialization status of all services."""
        return {
            "event_store": self.event_store is not None,
            "outbox": self.outbox is not None,
            "neo4j_service": self.neo4j_service is not None,
            "chromadb_service": self.chromadb_service is not None,
            "embedding_service": self.embedding_service is not None,
            "repository": self.repository is not None,
            "confidence_runtime": self.confidence_runtime is not None,
            "confidence_listener": self.confidence_listener is not None,
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown all services."""
        logger.info("Shutting down service container...")

        # Cancel async task first
        if self.confidence_listener_task:
            self.confidence_listener_task.cancel()
            try:
                await self.confidence_listener_task
            except asyncio.CancelledError:
                pass
            logger.debug("Confidence listener task cancelled")

        # Close async service
        if self.confidence_runtime:
            await self.confidence_runtime.close()
            logger.debug("Confidence runtime closed")

        # Close sync services (SQLite connections)
        if self.event_store:
            self.event_store.close()
            logger.debug("Event store closed")

        if self.outbox:
            self.outbox.close()
            logger.debug("Outbox closed")

        # Close database services
        if self.neo4j_service:
            self.neo4j_service.close()
            logger.debug("Neo4j service closed")

        if self.chromadb_service:
            self.chromadb_service.close()
            logger.debug("ChromaDB service closed")

        logger.info("Service container shutdown complete")


# Module-level singleton (matches config/settings.py pattern)
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """
    Get the service container singleton.

    Creates an empty container on first access.
    Use initialize() in mcp_server.py to populate services.

    Returns:
        ServiceContainer instance (may be uninitialized)
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def set_container(container: ServiceContainer) -> None:
    """
    Replace the singleton container.

    Primarily used for testing to inject mock containers.

    Args:
        container: Pre-configured container to use
    """
    global _container
    _container = container


def reset_container() -> None:
    """
    Reset the container singleton.

    Should be called in test fixtures to ensure clean state.
    """
    global _container
    _container = None
