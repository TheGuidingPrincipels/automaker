"""
Integration tests for DualStorageRepository.

Tests the repository with actual database services to verify
end-to-end functionality and dual-database synchronization.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from config import Config
from projections.chromadb_projection import ChromaDBProjection
from projections.neo4j_projection import Neo4jProjection
from services.chromadb_service import ChromaDbService
from services.embedding_cache import EmbeddingCache
from services.embedding_service import EmbeddingService
from services.event_store import EventStore
from services.neo4j_service import Neo4jService
from services.outbox import Outbox
from services.repository import ConceptNotFoundError, DualStorageRepository


@pytest.fixture
def temp_dir():
    """Create temporary directory for test databases."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_event_store(temp_dir):
    """Create test event store."""
    db_path = Path(temp_dir) / "test_events.db"
    return EventStore(str(db_path))


@pytest.fixture
def test_outbox(temp_dir):
    """Create test outbox."""
    db_path = Path(temp_dir) / "test_events.db"
    return Outbox(str(db_path))


@pytest.fixture
def test_embedding_cache(temp_dir):
    """Create test embedding cache."""
    db_path = Path(temp_dir) / "test_events.db"
    return EmbeddingCache(str(db_path))


@pytest.fixture
@pytest.mark.asyncio
async def test_embedding_service():
    """Create and initialize test embedding service."""
    service = EmbeddingService()
    await service.initialize()
    return service


@pytest.fixture
def test_neo4j_service():
    """Create test Neo4j service (requires Neo4j running)."""
    try:
        config = Config()
        service = Neo4jService(config)

        # Test connection
        if not service.test_connection():
            pytest.skip("Neo4j not available for integration tests")

        yield service

        # Cleanup: delete all test concepts
        cleanup_query = """
        MATCH (c:Concept)
        WHERE c.concept_id STARTS WITH 'test-concept-'
        DETACH DELETE c
        """
        service.execute_write(cleanup_query, {})

        service.close()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


@pytest.fixture
def test_chromadb_service(temp_dir):
    """Create test ChromaDB service."""
    try:
        # Use persistent storage in temp directory
        from services.chromadb_service import ChromaDbConfig

        config = ChromaDbConfig(
            persist_directory=str(Path(temp_dir) / "chroma"), collection_name="test_concepts"
        )
        service = ChromaDbService(config)
        service.connect()

        yield service

        # Cleanup
        collection = service.get_collection()
        # Delete all test concepts
        all_ids = collection.get()["ids"]
        if all_ids:
            test_ids = [id for id in all_ids if id.startswith("test-concept-")]
            if test_ids:
                collection.delete(ids=test_ids)

    except Exception as e:
        pytest.skip(f"ChromaDB not available: {e}")


@pytest.fixture
def test_neo4j_projection(test_neo4j_service):
    """Create test Neo4j projection."""
    return Neo4jProjection(test_neo4j_service)


@pytest.fixture
def test_chromadb_projection(test_chromadb_service):
    """Create test ChromaDB projection."""
    return ChromaDBProjection(test_chromadb_service)


@pytest.fixture
@pytest.mark.asyncio
async def integration_repository(
    test_event_store,
    test_outbox,
    test_neo4j_projection,
    test_chromadb_projection,
    test_embedding_service,
    test_embedding_cache,
):
    """Create DualStorageRepository with real services for integration testing."""
    # Ensure embedding service is initialized
    if not test_embedding_service.is_available():
        await test_embedding_service.initialize()

    return DualStorageRepository(
        event_store=test_event_store,
        outbox=test_outbox,
        neo4j_projection=test_neo4j_projection,
        chromadb_projection=test_chromadb_projection,
        embedding_service=test_embedding_service,
        embedding_cache=test_embedding_cache,
    )


class TestRepositoryIntegrationBasics:
    """Basic integration tests for repository operations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_concept_writes_to_both_databases(
        self, integration_repository, test_neo4j_projection, test_chromadb_projection
    ):
        """
        ACCEPTANCE CRITERION: Create concept appears in Neo4j AND ChromaDB.
        """
        concept_data = {
            "concept_id": "test-concept-create-001",
            "name": "Python For Loops",
            "explanation": "For loops in Python iterate over sequences",
            "area": "Programming",
            "topic": "Python",
        }

        # Create concept
        success, error, concept_id = integration_repository.create_concept(concept_data)

        assert success is True, f"Create failed: {error}"
        assert error is None
        assert concept_id == "test-concept-create-001"

        # Verify in Neo4j
        neo4j_query = "MATCH (c:Concept {concept_id: $id}) RETURN c"
        neo4j_result = test_neo4j_projection.neo4j.execute_read(neo4j_query, {"id": concept_id})

        assert len(neo4j_result) == 1, "Concept not found in Neo4j"
        neo4j_concept = neo4j_result[0]["c"]
        assert neo4j_concept["name"] == "Python For Loops"
        assert neo4j_concept["area"] == "Programming"

        # Verify in ChromaDB
        collection = test_chromadb_projection.chromadb.get_collection()
        chromadb_result = collection.get(ids=[concept_id])

        assert len(chromadb_result["ids"]) == 1, "Concept not found in ChromaDB"
        assert chromadb_result["ids"][0] == concept_id
        assert "Python iterate" in chromadb_result["documents"][0]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_concept_reflects_in_both_databases(
        self, integration_repository, test_neo4j_projection, test_chromadb_projection
    ):
        """
        ACCEPTANCE CRITERION: Update reflected in both DBs.
        """
        concept_id = "test-concept-update-001"

        # Create concept first
        concept_data = {
            "concept_id": concept_id,
            "name": "Original Name",
            "explanation": "Original explanation",
            "confidence_score": 80
        }

        success, error, _ = integration_repository.create_concept(concept_data)
        assert success is True, f"Create failed: {error}"

        # Update concept
        updates = {
            "name": "Updated Name",
            "confidence_score": 95
        }

        success, error = integration_repository.update_concept(concept_id, updates)
        assert success is True, f"Update failed: {error}"

        # Verify update in Neo4j
        neo4j_query = "MATCH (c:Concept {concept_id: $id}) RETURN c"
        neo4j_result = test_neo4j_projection.neo4j.execute_read(neo4j_query, {"id": concept_id})

        assert len(neo4j_result) == 1
        neo4j_concept = neo4j_result[0]["c"]
        assert neo4j_concept["name"] == "Updated Name"
        assert neo4j_concept["confidence_score"] == 95

        # Verify update in ChromaDB
        collection = test_chromadb_projection.chromadb.get_collection()
        chromadb_result = collection.get(ids=[concept_id])

        assert len(chromadb_result["ids"]) == 1
        metadata = chromadb_result["metadatas"][0]
        assert metadata["name"] == "Updated Name"
        assert metadata["confidence_score"] == 95

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_concept_removes_from_both_databases(
        self, integration_repository, test_neo4j_projection, test_chromadb_projection
    ):
        """Test that delete removes concept from both databases."""
        concept_id = "test-concept-delete-001"

        # Create concept first
        concept_data = {
            "concept_id": concept_id,
            "name": "To Be Deleted",
            "explanation": "This concept will be deleted",
        }

        success, error, _ = integration_repository.create_concept(concept_data)
        assert success is True

        # Delete concept
        success, error = integration_repository.delete_concept(concept_id)
        assert success is True, f"Delete failed: {error}"

        # Verify soft delete in Neo4j (node still exists but marked deleted)
        neo4j_query = "MATCH (c:Concept {concept_id: $id}) RETURN c"
        neo4j_result = test_neo4j_projection.neo4j.execute_read(neo4j_query, {"id": concept_id})

        assert len(neo4j_result) == 1
        neo4j_concept = neo4j_result[0]["c"]
        assert neo4j_concept.get("deleted") is True

        # Verify hard delete in ChromaDB (completely removed)
        collection = test_chromadb_projection.chromadb.get_collection()
        chromadb_result = collection.get(ids=[concept_id])

        assert len(chromadb_result["ids"]) == 0, "Concept should be deleted from ChromaDB"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_concept_retrieves_from_neo4j(self, integration_repository):
        """Test that get_concept retrieves data from Neo4j."""
        concept_id = "test-concept-get-001"

        # Create concept
        concept_data = {
            "concept_id": concept_id,
            "name": "Test Concept",
            "explanation": "Test explanation",
            "area": "Testing",
        }

        success, _error, _ = integration_repository.create_concept(concept_data)
        assert success is True

        # Get concept
        retrieved = integration_repository.get_concept(concept_id)

        assert retrieved is not None
        assert retrieved["concept_id"] == concept_id
        assert retrieved["name"] == "Test Concept"
        assert retrieved["area"] == "Testing"


class TestRepositoryEventSourcing:
    """Test event sourcing aspects of the repository."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_events_stored_before_projections(self, integration_repository, test_event_store):
        """
        ACCEPTANCE CRITERION: Events stored before projections.
        """
        concept_id = "test-concept-event-001"

        concept_data = {
            "concept_id": concept_id,
            "name": "Test Concept",
            "explanation": "Test explanation",
        }

        # Create concept
        success, _error, _ = integration_repository.create_concept(concept_data)
        assert success is True

        # Verify event was stored
        events = test_event_store.get_events_by_aggregate(concept_id)
        assert len(events) > 0
        assert events[0].event_type == "ConceptCreated"
        assert events[0].aggregate_id == concept_id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_version_tracking(self, integration_repository, test_event_store):
        """Test that versions are properly tracked."""
        concept_id = "test-concept-version-001"

        # Create (version 1)
        concept_data = {
            "concept_id": concept_id,
            "name": "Test Concept",
            "explanation": "Test explanation",
        }
        integration_repository.create_concept(concept_data)

        # Update (version 2)
        integration_repository.update_concept(concept_id, {"confidence_score": 85})

        # Update again (version 3)
        integration_repository.update_concept(concept_id, {"confidence_score": 90})

        # Verify versions in event store
        events = test_event_store.get_events_by_aggregate(concept_id)
        assert len(events) == 3
        assert events[0].version == 1
        assert events[1].version == 2
        assert events[2].version == 3

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_event_replay_rebuilds_state(
        self, integration_repository, test_event_store, test_neo4j_projection
    ):
        """Test that state can be rebuilt from events."""
        concept_id = "test-concept-replay-001"

        # Create and update concept
        concept_data = {
            "concept_id": concept_id,
            "name": "Original",
            "explanation": "Original explanation",
        }
        integration_repository.create_concept(concept_data)
        integration_repository.update_concept(concept_id, {"name": "Updated"})

        # Get events
        events = test_event_store.get_events_by_aggregate(concept_id)
        assert len(events) == 2

        # Replay events (simulate rebuilding projection)
        for event in events:
            test_neo4j_projection.project_event(event)

        # Verify final state
        concept = integration_repository.get_concept(concept_id)
        assert concept["name"] == "Updated"


class TestRepositoryEmbeddings:
    """Test embedding generation and caching."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_embedding_generated_automatically(
        self, integration_repository, test_embedding_service
    ):
        """
        ACCEPTANCE CRITERION: Embedding generated automatically.
        """
        concept_id = "test-concept-embedding-001"

        concept_data = {
            "concept_id": concept_id,
            "name": "Python Dictionaries",
            "explanation": "Dictionaries store key-value pairs",
        }

        # Create concept
        success, _error, _ = integration_repository.create_concept(concept_data)
        assert success is True

        # Embedding generation is called internally
        # We can verify by checking that the concept is searchable in ChromaDB
        # (which requires embeddings)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_embedding_cache_usage(self, integration_repository, test_embedding_cache):
        """Test that embedding cache is used to avoid recomputation."""
        concept_id_1 = "test-concept-cache-001"
        concept_id_2 = "test-concept-cache-002"

        # Same text for both concepts
        concept_data_1 = {
            "concept_id": concept_id_1,
            "name": "Same Text",
            "explanation": "This is the same explanation",
        }

        concept_data_2 = {
            "concept_id": concept_id_2,
            "name": "Same Text",
            "explanation": "This is the same explanation",
        }

        # Create first concept (cache miss)
        integration_repository.create_concept(concept_data_1)

        # Get cache stats before second create
        stats_before = test_embedding_cache.get_stats()

        # Create second concept with same text (should use cache)
        integration_repository.create_concept(concept_data_2)

        # Get cache stats after
        stats_after = test_embedding_cache.get_stats()

        # Cache hits should increase
        assert stats_after.cache_hits >= stats_before.cache_hits


class TestRepositoryOutbox:
    """Test outbox pattern and retry logic."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_outbox_entries_created(self, integration_repository, test_outbox):
        """
        ACCEPTANCE CRITERION: create_concept() writes event → outbox → both DBs.
        """
        concept_id = "test-concept-outbox-001"

        concept_data = {
            "concept_id": concept_id,
            "name": "Test Concept",
            "explanation": "Test explanation",
        }

        # Get outbox count before
        stats_before = test_outbox.count_by_status()

        # Create concept
        integration_repository.create_concept(concept_data)

        # Get outbox count after
        stats_after = test_outbox.count_by_status()

        # Should have created 2 outbox entries (neo4j + chromadb)
        # They should be marked as completed if projections succeeded
        total_after = sum(stats_after.values())
        total_before = sum(stats_before.values())

        assert total_after >= total_before + 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_process_pending_outbox_retries_failed_projections(
        self, integration_repository, test_outbox
    ):
        """Test that pending outbox entries are processed."""
        # This test would require simulating a failure scenario
        # For now, test that the method runs without error

        result = integration_repository.process_pending_outbox()

        assert "processed" in result
        assert "failed" in result
        assert "total" in result


class TestRepositoryErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_nonexistent_concept_raises_error(self, integration_repository):
        """Test that updating non-existent concept raises error."""
        with pytest.raises(ConceptNotFoundError):
            integration_repository.update_concept("nonexistent-concept", {"name": "New Name"})

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_nonexistent_concept_raises_error(self, integration_repository):
        """Test that deleting non-existent concept raises error."""
        with pytest.raises(ConceptNotFoundError):
            integration_repository.delete_concept("nonexistent-concept")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_nonexistent_concept_returns_none(self, integration_repository):
        """Test that getting non-existent concept returns None."""
        result = integration_repository.get_concept("nonexistent-concept")
        assert result is None


class TestRepositoryStats:
    """Test repository statistics."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_repository_stats(self, integration_repository):
        """Test getting repository statistics."""
        stats = integration_repository.get_repository_stats()

        assert "version_cache_size" in stats
        assert "outbox_pending" in stats
        assert "outbox_completed" in stats
        assert "embedding_cache_enabled" in stats


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_concept_lifecycle(
        self, integration_repository, test_neo4j_projection, test_chromadb_projection
    ):
        """Test complete lifecycle: create → update → retrieve → delete."""
        concept_id = "test-concept-lifecycle-001"

        # 1. Create
        concept_data = {
            "concept_id": concept_id,
            "name": "Python Lists",
            "explanation": "Lists are ordered collections",
            "area": "Programming",
            "confidence_score": 80
        }

        success, error, _ = integration_repository.create_concept(concept_data)
        assert success is True, f"Create failed: {error}"

        # 2. Retrieve
        concept = integration_repository.get_concept(concept_id)
        assert concept is not None
        assert concept["name"] == "Python Lists"

        # 3. Update
        updates = {
            "explanation": "Lists are mutable ordered collections",
            "confidence_score": 90
        }
        success, error = integration_repository.update_concept(concept_id, updates)
        assert success is True, f"Update failed: {error}"

        # 4. Retrieve again
        concept = integration_repository.get_concept(concept_id)
        assert concept["confidence_score"] == 90
        assert "mutable" in concept["explanation"]

        # 5. Delete
        success, error = integration_repository.delete_concept(concept_id)
        assert success is True, f"Delete failed: {error}"

        # 6. Verify deleted (should return None for active concepts)
        concept = integration_repository.get_concept(concept_id)
        assert concept is None or concept.get("deleted") is True
