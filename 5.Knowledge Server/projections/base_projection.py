"""
Base projection interface for event sourcing projections.

Defines the contract that all projection classes must implement.
"""

from abc import ABC, abstractmethod

from models.events import Event


class BaseProjection(ABC):
    """
    Abstract base class for event projections.

    Projections transform events from the event store into specialized
    read models (graph database, vector database, search index, etc.).
    """

    @abstractmethod
    def project_event(self, event: Event) -> bool:
        """
        Project an event to the target data store.

        Args:
            event: The event to project

        Returns:
            True if projection successful, False otherwise

        Raises:
            ProjectionError: If projection fails in an unrecoverable way
        """
        pass

    @abstractmethod
    def get_projection_name(self) -> str:
        """
        Get the name of this projection.

        Returns:
            Projection name (e.g., "neo4j", "chromadb")
        """
        pass


class ProjectionError(Exception):
    """Base exception for projection errors."""

    pass
