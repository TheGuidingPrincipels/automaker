"""
Unit tests for ChromaDB Service

Tests cover:
- Configuration validation
- Connection establishment
- Collection management
- Health check functionality
- CRUD operations
- Metadata filtering
- Persistence across restarts
- Error handling
- Context manager usage
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from services.chromadb_service import (
    ChromaDbConfig,
    ChromaDbService,
    create_chromadb_service_from_env,
)


class TestChromaDbConfig:
    """Test ChromaDbConfig model."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = ChromaDbConfig()
        assert config.persist_directory == "./data/chroma"
        assert config.collection_name == "concepts"
        assert config.distance_function == "cosine"
        assert config.hnsw_construction_ef == 128
        assert config.hnsw_search_ef == 64
        assert config.hnsw_m == 16

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = ChromaDbConfig(
            persist_directory="/custom/path",
            collection_name="custom_collection",
            distance_function="l2",
            hnsw_construction_ef=256,
            hnsw_search_ef=128,
            hnsw_m=32,
        )
        assert config.persist_directory == "/custom/path"
        assert config.collection_name == "custom_collection"
        assert config.distance_function == "l2"
        assert config.hnsw_construction_ef == 256
        assert config.hnsw_search_ef == 128
        assert config.hnsw_m == 32

    def test_config_validation_distance_function(self):
        """Test distance function validation."""
        # Valid distance functions
        for dist_func in ["cosine", "l2", "ip"]:
            config = ChromaDbConfig(distance_function=dist_func)
            assert config.distance_function == dist_func

        # Invalid distance function
        with pytest.raises(ValueError, match="Distance function must be one of"):
            ChromaDbConfig(distance_function="invalid")

    def test_config_validation_hnsw_params(self):
        """Test HNSW parameter validation."""
        # Test construction_ef bounds
        with pytest.raises(ValueError):
            ChromaDbConfig(hnsw_construction_ef=0)  # Too low

        with pytest.raises(ValueError):
            ChromaDbConfig(hnsw_construction_ef=513)  # Too high

        # Test search_ef bounds
        with pytest.raises(ValueError):
            ChromaDbConfig(hnsw_search_ef=0)  # Too low

        with pytest.raises(ValueError):
            ChromaDbConfig(hnsw_search_ef=513)  # Too high

        # Test M bounds
        with pytest.raises(ValueError):
            ChromaDbConfig(hnsw_m=1)  # Too low

        with pytest.raises(ValueError):
            ChromaDbConfig(hnsw_m=65)  # Too high


class TestChromaDbService:
    """Test ChromaDbService functionality."""

    def test_init_with_params(self, temp_chroma_dir):
        """Test initialization with individual parameters."""
        service = ChromaDbService(
            persist_directory=temp_chroma_dir,
            collection_name="test_collection",
        )
        assert service.config.persist_directory == temp_chroma_dir
        assert service.config.collection_name == "test_collection"
        assert service.client is None
        assert service.collection is None
        assert service._connected is False

    def test_init_with_config(self, temp_chroma_dir):
        """Test initialization with ChromaDbConfig object."""
        config = ChromaDbConfig(
            persist_directory=temp_chroma_dir,
            collection_name="config_collection",
            hnsw_m=32,
        )
        service = ChromaDbService(config=config)
        assert service.config.persist_directory == temp_chroma_dir
        assert service.config.hnsw_m == 32

    def test_connect_success(self, temp_chroma_dir):
        """Test successful connection."""
        service = ChromaDbService(
            persist_directory=temp_chroma_dir,
            collection_name="test_concepts",
        )
        result = service.connect()

        assert result is True
        assert service._connected is True
        assert service.client is not None
        assert service.collection is not None
        assert service.collection.name == "test_concepts"

        service.close()

    def test_connect_creates_directory(self, temp_chroma_dir):
        """Test that connect creates persist directory if it doesn't exist."""
        new_dir = Path(temp_chroma_dir) / "subdir" / "chroma"
        service = ChromaDbService(
            persist_directory=str(new_dir),
            collection_name="test",
        )

        assert not new_dir.exists()
        service.connect()
        assert new_dir.exists()

        service.close()

    def test_is_connected(self, chromadb_service):
        """Test is_connected status check."""
        assert chromadb_service.is_connected() is True

        chromadb_service.close()
        assert chromadb_service.is_connected() is False

    def test_health_check_healthy(self, chromadb_service):
        """Test health check when service is healthy."""
        health = chromadb_service.health_check()

        assert health["service"] == "chromadb"
        assert health["connected"] is True
        assert health["status"] == "healthy"
        assert health["collection_count"] == 0
        assert "collection_metadata" in health
        assert health["collection_metadata"]["hnsw:space"] == "cosine"

    def test_health_check_not_connected(self, temp_chroma_dir):
        """Test health check when not connected."""
        service = ChromaDbService(persist_directory=temp_chroma_dir)
        health = service.health_check()

        assert health["service"] == "chromadb"
        assert health["connected"] is False
        assert health["status"] == "unhealthy"
        assert "error" in health
        assert health["error"] == "Not connected to ChromaDB"

    def test_get_collection_success(self, chromadb_service):
        """Test getting collection when connected."""
        collection = chromadb_service.get_collection()
        assert collection is not None
        assert collection.name == "test_concepts"

    def test_get_collection_not_connected(self, temp_chroma_dir):
        """Test getting collection when not connected raises error."""
        service = ChromaDbService(persist_directory=temp_chroma_dir)

        with pytest.raises(RuntimeError, match="Not connected to ChromaDB"):
            service.get_collection()

    def test_list_collections(self, chromadb_service):
        """Test listing all collections."""
        collections = chromadb_service.list_collections()
        assert "test_concepts" in collections

    def test_delete_collection(self, temp_chroma_dir):
        """Test deleting a collection."""
        service = ChromaDbService(
            persist_directory=temp_chroma_dir,
            collection_name="to_delete",
        )
        service.connect()

        # Verify collection exists
        assert "to_delete" in service.list_collections()

        # Delete collection
        result = service.delete_collection()
        assert result is True
        assert service.collection is None

        # Verify collection is gone
        assert "to_delete" not in service.list_collections()

        service.close()

    def test_close(self, chromadb_service):
        """Test closing connection."""
        assert chromadb_service.is_connected() is True

        chromadb_service.close()

        assert chromadb_service.client is None
        assert chromadb_service.collection is None
        assert chromadb_service._connected is False

    def test_context_manager(self, temp_chroma_dir):
        """Test context manager usage."""
        with ChromaDbService(
            persist_directory=temp_chroma_dir,
            collection_name="ctx_test",
        ) as service:
            assert service.is_connected() is True
            collection = service.get_collection()
            assert collection is not None

        # After exiting context, should be closed
        assert service.is_connected() is False


class TestChromaDbCRUDOperations:
    """Test CRUD operations on ChromaDB."""

    def test_add_document(self, chromadb_service, sample_concept_data):
        """Test adding a document to collection."""
        collection = chromadb_service.get_collection()

        collection.add(
            ids=["concept_001"],
            documents=[sample_concept_data["explanation"]],
            metadatas=[{
                "name": sample_concept_data["name"],
                "area": sample_concept_data["area"],
                "topic": sample_concept_data["topic"],
                "confidence_score": sample_concept_data["confidence_score"],
            }],
        )

        # Verify document was added
        assert collection.count() == 1

        # Retrieve document
        result = collection.get(ids=["concept_001"])
        assert result["ids"][0] == "concept_001"
        assert result["metadatas"][0]["name"] == "Test Concept"

    def test_query_document(self, chromadb_service, sample_concept_data):
        """Test querying documents by similarity."""
        collection = chromadb_service.get_collection()

        # Add test documents
        collection.add(
            ids=["concept_001"],
            documents=[sample_concept_data["explanation"]],
            metadatas=[{"name": "Test Concept", "area": "Testing"}],
        )

        # Query for similar documents
        results = collection.query(
            query_texts=["unit testing concept"],
            n_results=1,
        )

        assert len(results["ids"][0]) == 1
        assert results["ids"][0][0] == "concept_001"

    def test_update_document(self, chromadb_service):
        """Test updating a document."""
        collection = chromadb_service.get_collection()

        # Add initial document
        collection.add(
            ids=["concept_001"],
            documents=["Original explanation"],
            metadatas=[{"name": "Original Name", "area": "Testing"}],
        )

        # Update document
        collection.update(
            ids=["concept_001"],
            documents=["Updated explanation"],
            metadatas=[{"name": "Updated Name", "area": "Testing"}],
        )

        # Verify update
        result = collection.get(ids=["concept_001"])
        assert result["documents"][0] == "Updated explanation"
        assert result["metadatas"][0]["name"] == "Updated Name"

    def test_delete_document(self, chromadb_service):
        """Test deleting a document."""
        collection = chromadb_service.get_collection()

        # Add document
        collection.add(
            ids=["concept_001"],
            documents=["Test document"],
            metadatas=[{"name": "Test"}],
        )

        assert collection.count() == 1

        # Delete document
        collection.delete(ids=["concept_001"])

        assert collection.count() == 0

    def test_metadata_filtering(self, chromadb_service):
        """Test filtering documents by metadata."""
        collection = chromadb_service.get_collection()

        # Add multiple documents with different metadata
        collection.add(
            ids=["concept_001", "concept_002", "concept_003"],
            documents=[
                "Python concept",
                "JavaScript concept",
                "Python advanced concept",
            ],
            metadatas=[
                {"area": "Python", "topic": "Basics"},
                {"area": "JavaScript", "topic": "Basics"},
                {"area": "Python", "topic": "Advanced"},
            ],
        )

        # Query with metadata filter
        results = collection.query(
            query_texts=["programming concept"],
            n_results=5,
            where={"area": "Python"},
        )

        # Should only return Python concepts
        assert len(results["ids"][0]) == 2
        for metadata in results["metadatas"][0]:
            assert metadata["area"] == "Python"


class TestChromaDbPersistence:
    """Test persistence across service restarts."""

    def test_collection_persists(self, temp_chroma_dir, sample_concept_data):
        """Test that collection persists after closing and reopening."""
        # Create service and add document
        service1 = ChromaDbService(
            persist_directory=temp_chroma_dir,
            collection_name="persistent_test",
        )
        service1.connect()

        collection1 = service1.get_collection()
        collection1.add(
            ids=["concept_001"],
            documents=[sample_concept_data["explanation"]],
            metadatas=[{"name": sample_concept_data["name"]}],
        )

        assert collection1.count() == 1
        service1.close()

        # Reopen service and verify data persists
        service2 = ChromaDbService(
            persist_directory=temp_chroma_dir,
            collection_name="persistent_test",
        )
        service2.connect()

        collection2 = service2.get_collection()
        assert collection2.count() == 1

        result = collection2.get(ids=["concept_001"])
        assert result["metadatas"][0]["name"] == sample_concept_data["name"]

        service2.close()


class TestChromaDbServiceFromEnv:
    """Test creating service from environment variables."""

    def test_create_from_env(self, temp_chroma_dir):
        """Test creating service from environment variables."""
        import os
        from config import reset_settings

        # Reset settings to pick up environment changes
        reset_settings()

        # Set environment variable (ChromaDbSettings uses env_prefix="CHROMA_")
        old_value = os.environ.get("CHROMA_PERSIST_DIRECTORY")
        os.environ["CHROMA_PERSIST_DIRECTORY"] = temp_chroma_dir

        try:
            reset_settings()  # Reset again after setting env var
            service = create_chromadb_service_from_env()

            assert service.config.persist_directory == temp_chroma_dir
            assert service.config.collection_name == "concepts"
        finally:
            # Cleanup
            if old_value is not None:
                os.environ["CHROMA_PERSIST_DIRECTORY"] = old_value
            else:
                os.environ.pop("CHROMA_PERSIST_DIRECTORY", None)
            reset_settings()
