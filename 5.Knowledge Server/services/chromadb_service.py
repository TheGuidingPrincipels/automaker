"""
ChromaDB Service Module

Provides connection management and operations for ChromaDB vector database.

Features:
- Persistent storage with configurable directory
- Collection management with HNSW indexing
- Health check monitoring
- Metadata filtering support
- Error handling with retries
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings
from pydantic import BaseModel, Field, field_validator


logger = logging.getLogger(__name__)


class ChromaDbConfig(BaseModel):
    """Configuration for ChromaDB connection."""

    persist_directory: str = Field(
        default="./data/chroma", description="Directory for ChromaDB persistent storage"
    )
    collection_name: str = Field(default="concepts", description="Name of the collection to use")
    distance_function: str = Field(
        default="cosine", description="Distance function for similarity (cosine, l2, ip)"
    )
    hnsw_construction_ef: int = Field(
        default=128,
        ge=1,
        le=512,
        description="HNSW construction ef parameter (build-time accuracy)",
    )
    hnsw_search_ef: int = Field(
        default=64, ge=1, le=512, description="HNSW search ef parameter (query-time accuracy)"
    )
    hnsw_m: int = Field(
        default=16, ge=2, le=64, description="HNSW M parameter (connections per node)"
    )

    @field_validator("distance_function")
    @classmethod
    def validate_distance_function(cls, v: str) -> str:
        """Validate distance function is supported."""
        allowed = ["cosine", "l2", "ip"]
        if v not in allowed:
            raise ValueError(f"Distance function must be one of {allowed}, got: {v}")
        return v

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, v: str) -> str:
        """Validate collection name follows ChromaDB rules."""
        import re

        if not v or len(v) < 3 or len(v) > 63:
            raise ValueError("Collection name must be 3-63 characters")
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$", v):
            raise ValueError(
                "Collection name must start and end with alphanumeric, "
                "and contain only [a-zA-Z0-9._-]"
            )
        return v


class ChromaDbService:
    """Service for managing ChromaDB vector database connections and operations."""

    def __init__(
        self,
        persist_directory: str | None = None,
        collection_name: str = "concepts",
        config: ChromaDbConfig | None = None,
    ):
        """
        Initialize ChromaDB service.

        Args:
            persist_directory: Path to ChromaDB persistent storage
            collection_name: Name of the collection
            config: Optional ChromaDbConfig for advanced configuration

        Raises:
            ValueError: If configuration is invalid
        """
        if config:
            self.config = config
        else:
            self.config = ChromaDbConfig(
                persist_directory=persist_directory or "./data/chroma",
                collection_name=collection_name,
            )

        # Security: Prevent relative paths in production
        import os

        if os.getenv("ENV", "development") == "production":
            persist_path = Path(self.config.persist_directory)
            if not persist_path.is_absolute():
                raise ValueError(
                    "Relative persist directory not allowed in production. "
                    "Set CHROMA_PERSIST_DIRECTORY to absolute path."
                )

        self.client: ClientAPI | None = None
        self.collection: Collection | None = None
        self._connected = False

    def connect(self) -> bool:
        """
        Establish connection to ChromaDB and create/get collection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Close existing client if reconnecting to prevent resource leak
            if self.client is not None:
                try:
                    self.close()
                    logger.debug("Closed existing client before reconnecting")
                except Exception as e:
                    logger.warning(f"Error closing existing client: {e}")

            # Create persist directory if it doesn't exist
            persist_path = Path(self.config.persist_directory)
            persist_path.mkdir(parents=True, exist_ok=True)

            # Initialize PersistentClient
            self.client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                ),
            )

            # Create or get collection with HNSW configuration
            collection_metadata = {
                "hnsw:space": self.config.distance_function,
                "hnsw:construction_ef": self.config.hnsw_construction_ef,
                "hnsw:search_ef": self.config.hnsw_search_ef,
                "hnsw:M": self.config.hnsw_m,
            }

            self.collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                metadata=collection_metadata,
            )

            self._connected = True
            logger.info(
                f"Connected to ChromaDB at {self.config.persist_directory}, "
                f"collection: {self.config.collection_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            self._connected = False
            return False

    def close(self) -> None:
        """Close ChromaDB connection and cleanup resources."""
        if self.client:
            # ChromaDB PersistentClient doesn't have explicit close
            # but we clean up references
            self.collection = None
            self.client = None
            self._connected = False
            logger.info("ChromaDB connection closed")

    def is_connected(self) -> bool:
        """
        Check if service is connected to ChromaDB.

        Returns:
            True if connected to ChromaDB client, False otherwise
        """
        return self._connected and self.client is not None

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check on ChromaDB connection.

        Returns:
            Dictionary with health check results
        """
        health_status = {
            "service": "chromadb",
            "connected": self._connected,
            "persist_directory": self.config.persist_directory,
            "collection_name": self.config.collection_name,
            "collection_count": None,
            "status": "unhealthy",
        }

        if not self.client or not self._connected:
            health_status["error"] = "Not connected to ChromaDB"
            return health_status

        try:
            # Test connection by getting collection count
            if self.collection:
                count = self.collection.count()
                health_status["collection_count"] = count
                health_status["status"] = "healthy"
                health_status["collection_metadata"] = self.collection.metadata
            else:
                health_status["error"] = "Collection not initialized"

        except Exception as e:
            health_status["error"] = str(e)
            health_status["status"] = "unhealthy"
            logger.error(f"Health check failed: {e}")

        return health_status

    def get_collection(self) -> Collection:
        """
        Get the ChromaDB collection.

        Returns:
            ChromaDB collection instance

        Raises:
            RuntimeError: If not connected
        """
        if not self.collection or not self._connected:
            raise RuntimeError("Not connected to ChromaDB. Call connect() first.")
        return self.collection

    def list_collections(self) -> list[str]:
        """
        List all collections in ChromaDB.

        Returns:
            List of collection names

        Raises:
            RuntimeError: If not connected
        """
        if not self.client or not self._connected:
            raise RuntimeError("Not connected to ChromaDB. Call connect() first.")

        collections = self.client.list_collections()
        return [col.name for col in collections]

    def delete_collection(self, collection_name: str | None = None) -> bool:
        """
        Delete a collection from ChromaDB.

        Args:
            collection_name: Name of collection to delete (default: current collection)

        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self._connected:
            raise RuntimeError("Not connected to ChromaDB. Call connect() first.")

        name = collection_name or self.config.collection_name

        try:
            self.client.delete_collection(name=name)
            if name == self.config.collection_name:
                self.collection = None
                # Note: Keep _connected=True, client is still valid, just collection is gone
            logger.info(f"Deleted collection: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {name}: {e}")
            return False

    def __enter__(self) -> "ChromaDbService":
        """Context manager entry - connect to ChromaDB."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close ChromaDB connection."""
        self.close()


# Convenience function for creating service from environment
def create_chromadb_service_from_env() -> ChromaDbService:
    """
    Create ChromaDB service from environment variables.

    Uses centralized config system (config.get_settings()).

    Returns:
        Configured ChromaDbService instance
    """
    from config import get_settings

    settings = get_settings()

    config = ChromaDbConfig(
        persist_directory=settings.chromadb.persist_directory,
        collection_name=settings.chromadb.collection_name,
        distance_function=settings.chromadb.distance_function,
        hnsw_construction_ef=settings.chromadb.hnsw_construction_ef,
        hnsw_search_ef=settings.chromadb.hnsw_search_ef,
        hnsw_m=settings.chromadb.hnsw_m,
    )

    return ChromaDbService(config=config)
