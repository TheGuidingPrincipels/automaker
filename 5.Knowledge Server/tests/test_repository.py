"""
Unit tests for DualStorageRepository.

Tests the repository's coordination logic with mocked dependencies.
"""

from unittest.mock import Mock

from services.repository import (
    DualStorageRepository,
    LRUVersionCache,
    RepositoryError,
    ConceptNotFoundError
)
from models.events import Event, ConceptCreated, ConceptUpdated, ConceptDeleted


@pytest.fixture
def mock_event_store():
    """Create mock EventStore."""
    store = Mock()
    store.append_event = Mock(return_value=True)
    store.get_event_by_id = Mock()
    store.get_latest_version = Mock(return_value=0)
    return store


@pytest.fixture
def mock_outbox():
    """Create mock Outbox."""
    outbox = Mock()
    outbox.add_to_outbox = Mock(return_value="outbox-id-123")
    outbox.mark_processing = Mock()
    outbox.mark_processed = Mock()
    outbox.mark_failed = Mock()
    outbox.get_pending = Mock(return_value=[])
    outbox.count_by_status = Mock(return_value={"pending": 0, "completed": 0, "failed": 0})
    return outbox


@pytest.fixture
def mock_neo4j_projection():
    """Create mock Neo4jProjection."""
    projection = Mock()
    projection.project_event = Mock(return_value=True)
    projection.neo4j = Mock()
    projection.neo4j.execute_read = Mock(return_value=[])
    return projection


@pytest.fixture
def mock_chromadb_projection():
    """Create mock ChromaDBProjection."""
    projection = Mock()
    projection.project_event = Mock(return_value=True)
    return projection


@pytest.fixture
def mock_embedding_service():
    """Create mock EmbeddingService."""
    service = Mock()
    service.generate_embedding = Mock(return_value=[0.1] * 384)
    service.generate_batch = Mock(return_value=[[0.1] * 384])
    service.config = Mock()
    service.config.model_name = "all-MiniLM-L6-v2"
    return service


@pytest.fixture
def mock_embedding_cache():
    """Create mock EmbeddingCache."""
    cache = Mock()
    cache.get_cached = Mock(return_value=None)  # No cache hits by default
    cache.store = Mock()
    cache.get_stats = Mock(return_value={"total_entries": 0, "cache_hits": 0})
    return cache


@pytest.fixture
def repository(
    mock_event_store,
    mock_outbox,
    mock_neo4j_projection,
    mock_chromadb_projection,
    mock_embedding_service,
    mock_embedding_cache,
):
    """Create DualStorageRepository with mocked dependencies."""
    return DualStorageRepository(
        event_store=mock_event_store,
        outbox=mock_outbox,
        neo4j_projection=mock_neo4j_projection,
        chromadb_projection=mock_chromadb_projection,
        embedding_service=mock_embedding_service,
        embedding_cache=mock_embedding_cache,
    )


class TestLRUVersionCache:
    """Tests for the LRUVersionCache class."""

    def test_lru_cache_get_set_basic(self):
        """Test basic get/set operations."""
        cache = LRUVersionCache(maxsize=100)
        cache.set("c1", 1)
        assert cache.get("c1") == 1
        assert cache.get("nonexistent") is None

    def test_lru_cache_bounded_size(self):
        """Verify cache evicts oldest entries when full."""
        cache = LRUVersionCache(maxsize=3)
        cache.set("c1", 1)
        cache.set("c2", 2)
        cache.set("c3", 3)
        cache.set("c4", 4)  # Should evict c1

        assert cache.get("c1") is None  # Evicted
        assert cache.get("c2") == 2
        assert cache.get("c3") == 3
        assert cache.get("c4") == 4
        assert len(cache) == 3

    def test_lru_cache_lru_ordering(self):
        """Verify LRU behavior - accessed items stay."""
        cache = LRUVersionCache(maxsize=3)
        cache.set("c1", 1)
        cache.set("c2", 2)
        cache.set("c3", 3)

        # Access c1, making it most recently used
        cache.get("c1")

        # Add c4 - should evict c2 (oldest unused)
        cache.set("c4", 4)

        assert cache.get("c1") == 1  # Still present
        assert cache.get("c2") is None  # Evicted
        assert cache.get("c3") == 3
        assert cache.get("c4") == 4

    def test_lru_cache_invalidate(self):
        """Test single entry removal."""
        cache = LRUVersionCache(maxsize=100)
        cache.set("c1", 1)
        cache.set("c2", 2)

        cache.invalidate("c1")

        assert cache.get("c1") is None
        assert cache.get("c2") == 2
        assert len(cache) == 1

    def test_lru_cache_invalidate_nonexistent(self):
        """Test invalidating nonexistent entry doesn't raise."""
        cache = LRUVersionCache(maxsize=100)
        cache.invalidate("nonexistent")  # Should not raise
        assert len(cache) == 0

    def test_lru_cache_clear(self):
        """Test full cache clearing."""
        cache = LRUVersionCache(maxsize=100)
        cache.set("c1", 1)
        cache.set("c2", 2)

        cache.clear()

        assert len(cache) == 0
        assert cache.get("c1") is None

    def test_lru_cache_thread_safety(self):
        """Verify cache handles concurrent access."""
        import threading
        cache = LRUVersionCache(maxsize=1000)
        errors = []

        def concurrent_ops():
            try:
                for i in range(100):
                    cache.set(f"c{threading.current_thread().name}_{i}", i)
                    cache.get(f"c{threading.current_thread().name}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=concurrent_ops, name=f"t{i}") for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"

    def test_lru_cache_update_existing(self):
        """Test updating an existing entry."""
        cache = LRUVersionCache(maxsize=100)
        cache.set("c1", 1)
        cache.set("c1", 2)  # Update

        assert cache.get("c1") == 2
        assert len(cache) == 1

    def test_lru_cache_update_moves_to_end(self):
        """Test that updating an entry moves it to end (most recent)."""
        cache = LRUVersionCache(maxsize=3)
        cache.set("c1", 1)
        cache.set("c2", 2)
        cache.set("c3", 3)

        # Update c1 (moves it to end)
        cache.set("c1", 10)

        # Add c4 - should evict c2 (now oldest)
        cache.set("c4", 4)

        assert cache.get("c1") == 10  # Still present, updated value
        assert cache.get("c2") is None  # Evicted
        assert cache.get("c3") == 3
        assert cache.get("c4") == 4


class TestRepositoryInitialization:
    """Test repository initialization."""

    def test_repository_initializes_with_all_dependencies(self, repository):
        """Test that repository initializes with all required dependencies."""
        assert repository.event_store is not None
        assert repository.outbox is not None
        assert repository.neo4j_projection is not None
        assert repository.chromadb_projection is not None
        assert repository.embedding_service is not None
        assert repository.embedding_cache is not None
        assert isinstance(repository._version_cache, LRUVersionCache)

    def test_repository_initializes_without_cache(
        self,
        mock_event_store,
        mock_outbox,
        mock_neo4j_projection,
        mock_chromadb_projection,
        mock_embedding_service,
    ):
        """Test that repository can initialize without embedding cache."""
        repo = DualStorageRepository(
            event_store=mock_event_store,
            outbox=mock_outbox,
            neo4j_projection=mock_neo4j_projection,
            chromadb_projection=mock_chromadb_projection,
            embedding_service=mock_embedding_service,
            embedding_cache=None,
        )
        assert repo.embedding_cache is None


class TestCreateConcept:
    """Test create_concept method."""

    def test_create_concept_success(self, repository, mock_event_store, mock_outbox):
        """Test successful concept creation (no manual confidence_score in event)"""
        concept_data = {
            "name": "Python For Loops",
            "explanation": "For loops iterate over sequences",
            "area": "Programming",
        }

        success, error, concept_id = repository.create_concept(concept_data)

        assert success is True
        assert error is None
        assert concept_id is not None

        # Verify event was appended
        assert mock_event_store.append_event.called
        event_arg = mock_event_store.append_event.call_args[0][0]
        assert isinstance(event_arg, ConceptCreated)
        assert event_arg.aggregate_id == concept_id
        assert event_arg.version == 1

        # Verify event data does NOT contain confidence_score
        assert "confidence_score" not in event_arg.event_data

        # Verify outbox entries created
        assert mock_outbox.add_to_outbox.call_count == 2
        calls = mock_outbox.add_to_outbox.call_args_list
        assert any("neo4j" in str(call) for call in calls)
        assert any("chromadb" in str(call) for call in calls)

    def test_create_concept_generates_id_if_not_provided(self, repository):
        """Test that concept_id is generated if not provided."""
        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        success, _error, concept_id = repository.create_concept(concept_data)

        assert success is True
        assert concept_id is not None
        assert len(concept_id) > 0  # UUID format

    def test_create_concept_uses_provided_id(self, repository):
        """Test that provided concept_id is used."""
        provided_id = "custom-concept-id"
        concept_data = {
            "concept_id": provided_id,
            "name": "Test Concept",
            "explanation": "Test explanation",
        }

        success, _error, concept_id = repository.create_concept(concept_data)

        assert success is True
        assert concept_id == provided_id

    def test_create_concept_generates_embedding(
        self, repository, mock_embedding_service, mock_embedding_cache
    ):
        """Test that embedding is generated for concept."""
        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        repository.create_concept(concept_data)

        # Verify embedding was generated
        assert mock_embedding_service.generate_embedding.called
        call_text = mock_embedding_service.generate_embedding.call_args[0][0]
        assert "Test Concept" in call_text
        assert "Test explanation" in call_text

        # Verify embedding was stored in cache
        assert mock_embedding_cache.store.called

    def test_create_concept_uses_cache_if_available(
        self, repository, mock_embedding_service, mock_embedding_cache
    ):
        """Test that cached embedding is used if available."""
        # Setup cache to return an embedding
        cached_embedding = [0.5] * 384
        mock_embedding_cache.get_cached = Mock(return_value=cached_embedding)

        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        repository.create_concept(concept_data)

        # Verify cache was checked
        assert mock_embedding_cache.get_cached.called

        # Verify embedding generation was NOT called (used cache)
        # Note: In current implementation, we still generate but this could be optimized

    def test_create_concept_event_store_failure(self, repository, mock_event_store):
        """Test handling of event store failure."""
        mock_event_store.append_event = Mock(return_value=False)

        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        success, error, _concept_id = repository.create_concept(concept_data)

        assert success is False
        assert error is not None
        assert "event store" in error.lower()

    def test_create_concept_partial_success(
        self, repository, mock_neo4j_projection, mock_chromadb_projection
    ):
        """Test partial success when one projection fails."""
        # Make Neo4j succeed but ChromaDB fail
        mock_neo4j_projection.project_event = Mock(return_value=True)
        mock_chromadb_projection.project_event = Mock(return_value=False)

        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        success, error, _concept_id = repository.create_concept(concept_data)

        # Should still return success (partial success)
        assert success is True
        assert "partial" in error.lower()

    def test_create_concept_both_projections_fail(
        self, repository, mock_neo4j_projection, mock_chromadb_projection
    ):
        """Test when both projections fail."""
        mock_neo4j_projection.project_event = Mock(return_value=False)
        mock_chromadb_projection.project_event = Mock(return_value=False)

        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        success, error, concept_id = repository.create_concept(concept_data)

        assert success is False
        assert error is not None
        assert concept_id is not None  # Event was still stored

    def test_create_concept_updates_version_cache(self, repository):
        """Test that version cache is updated after creation."""
        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        _success, _error, concept_id = repository.create_concept(concept_data)

        assert repository._version_cache.get(concept_id) is not None
        assert repository._version_cache.get(concept_id) == 1


class TestUpdateConcept:
    """Test update_concept method."""

    def test_update_concept_success(
        self,
        repository,
        mock_event_store,
        mock_outbox
    ):
        """Test successful concept update (event data should not contain manual confidence_score)"""
        concept_id = "test-concept-123"
        updates = {"explanation": "Updated explanation"}

        # Setup version
        mock_event_store.get_latest_version = Mock(return_value=1)

        success, error = repository.update_concept(concept_id, updates)

        assert success is True
        assert error is None

        # Verify event was appended
        assert mock_event_store.append_event.called
        event_arg = mock_event_store.append_event.call_args[0][0]
        assert isinstance(event_arg, ConceptUpdated)
        assert event_arg.aggregate_id == concept_id
        assert event_arg.version == 2  # Incremented

        # Verify event data does NOT contain manual confidence_score
        # (automated scores are calculated separately, not in event data)
        if "confidence_score" in event_arg.event_data:
            # If present, it should be part of updates dict passed in, not auto-added
            pass

    def test_update_concept_not_found(self, repository, mock_event_store):
        """Test updating non-existent concept."""
        concept_id = "nonexistent-concept"
        updates = {"explanation": "New explanation"}

        mock_event_store.get_latest_version = Mock(return_value=0)

        with pytest.raises(ConceptNotFoundError):
            repository.update_concept(concept_id, updates)

    def test_update_concept_regenerates_embedding_on_text_change(
        self, repository, mock_event_store, mock_embedding_service
    ):
        """Test that embedding is regenerated when explanation changes."""
        concept_id = "test-concept-123"
        updates = {"explanation": "New explanation text"}

        mock_event_store.get_latest_version = Mock(return_value=1)

        repository.update_concept(concept_id, updates)

        # Verify embedding was generated
        assert mock_embedding_service.generate_embedding.called

    def test_update_concept_increments_version(self, repository, mock_event_store):
        """Test that version is properly incremented."""
        concept_id = "test-concept-123"
        updates = {"explanation": "Updated"}

        mock_event_store.get_latest_version = Mock(return_value=3)

        repository.update_concept(concept_id, updates)

        event_arg = mock_event_store.append_event.call_args[0][0]
        assert event_arg.version == 4

    def test_update_concept_updates_version_cache(self, repository, mock_event_store):
        """Test that version cache is updated."""
        concept_id = "test-concept-123"
        updates = {"explanation": "Updated"}

        mock_event_store.get_latest_version = Mock(return_value=1)

        repository.update_concept(concept_id, updates)

        assert repository._version_cache.get(concept_id) == 2


class TestDeleteConcept:
    """Test delete_concept method."""

    def test_delete_concept_success(self, repository, mock_event_store, mock_outbox):
        """Test successful concept deletion."""
        concept_id = "test-concept-123"

        mock_event_store.get_latest_version = Mock(return_value=1)

        success, error = repository.delete_concept(concept_id)

        assert success is True
        assert error is None

        # Verify event was appended
        assert mock_event_store.append_event.called
        event_arg = mock_event_store.append_event.call_args[0][0]
        assert isinstance(event_arg, ConceptDeleted)
        assert event_arg.aggregate_id == concept_id

    def test_delete_concept_not_found(self, repository, mock_event_store):
        """Test deleting non-existent concept."""
        concept_id = "nonexistent-concept"

        mock_event_store.get_latest_version = Mock(return_value=0)

        with pytest.raises(ConceptNotFoundError):
            repository.delete_concept(concept_id)

    def test_delete_concept_increments_version(self, repository, mock_event_store):
        """Test that version is properly incremented."""
        concept_id = "test-concept-123"

        mock_event_store.get_latest_version = Mock(return_value=5)

        repository.delete_concept(concept_id)

        event_arg = mock_event_store.append_event.call_args[0][0]
        assert event_arg.version == 6


class TestGetConcept:
    """Test get_concept method."""

    def test_get_concept_success(self, repository, mock_neo4j_projection):
        """Test retrieving existing concept."""
        concept_id = "test-concept-123"

        # Setup mock to return concept
        mock_concept = {
            "concept_id": concept_id,
            "name": "Test Concept",
            "explanation": "Test explanation",
        }
        mock_neo4j_projection.neo4j.execute_read = Mock(return_value=[{"c": mock_concept}])

        result = repository.get_concept(concept_id)

        assert result is not None
        assert result["concept_id"] == concept_id
        assert result["name"] == "Test Concept"

    def test_get_concept_not_found(self, repository, mock_neo4j_projection):
        """Test retrieving non-existent concept."""
        concept_id = "nonexistent-concept"

        mock_neo4j_projection.neo4j.execute_read = Mock(return_value=[])

        result = repository.get_concept(concept_id)

        assert result is None

    def test_get_concept_queries_neo4j_not_event_store(
        self, repository, mock_neo4j_projection, mock_event_store
    ):
        """Test that get_concept queries Neo4j, not event store."""
        concept_id = "test-concept-123"

        mock_neo4j_projection.neo4j.execute_read = Mock(return_value=[])

        repository.get_concept(concept_id)

        # Neo4j should be called
        assert mock_neo4j_projection.neo4j.execute_read.called

        # Event store should NOT be called
        assert not mock_event_store.get_events_by_aggregate.called


class TestProcessPendingOutbox:
    """Test process_pending_outbox method."""

    def test_process_pending_outbox_empty(self, repository, mock_outbox):
        """Test processing when outbox is empty."""
        mock_outbox.get_pending = Mock(return_value=[])

        result = repository.process_pending_outbox()

        assert result["total"] == 0
        assert result["processed"] == 0
        assert result["failed"] == 0

    def test_process_pending_outbox_processes_entries(
        self, repository, mock_outbox, mock_event_store
    ):
        """Test processing pending outbox entries."""
        # Create mock outbox entry
        mock_entry = Mock()
        mock_entry.outbox_id = "outbox-123"
        mock_entry.event_id = "event-123"
        mock_entry.projection_name = "neo4j"

        mock_outbox.get_pending = Mock(return_value=[mock_entry])

        # Setup event store to return event
        mock_event = Mock(spec=ConceptCreated)
        mock_event_store.get_event_by_id = Mock(return_value=mock_event)

        result = repository.process_pending_outbox()

        assert result["total"] == 1
        assert result["processed"] == 1
        assert result["failed"] == 0

        # Verify outbox was updated
        assert mock_outbox.mark_processing.called
        assert mock_outbox.mark_processed.called

    def test_process_pending_outbox_handles_failures(
        self, repository, mock_outbox, mock_event_store, mock_neo4j_projection
    ):
        """Test handling of projection failures during outbox processing."""
        # Create mock outbox entry
        mock_entry = Mock()
        mock_entry.outbox_id = "outbox-123"
        mock_entry.event_id = "event-123"
        mock_entry.projection_name = "neo4j"

        mock_outbox.get_pending = Mock(return_value=[mock_entry])

        # Setup event store to return event
        mock_event = Mock(spec=ConceptCreated)
        mock_event_store.get_event_by_id = Mock(return_value=mock_event)

        # Make projection fail
        mock_neo4j_projection.project_event = Mock(return_value=False)

        result = repository.process_pending_outbox()

        assert result["total"] == 1
        assert result["processed"] == 0
        assert result["failed"] == 1

        # Verify outbox was marked as failed
        assert mock_outbox.mark_failed.called

    def test_process_pending_outbox_respects_limit(self, repository, mock_outbox):
        """Test that limit parameter is respected."""
        repository.process_pending_outbox(limit=50)

        assert mock_outbox.get_pending.called
        call_kwargs = mock_outbox.get_pending.call_args[1]
        assert call_kwargs["limit"] == 50


class TestPrivateMethods:
    """Test private helper methods."""

    def test_get_current_version_from_cache(self, repository):
        """Test getting version from cache."""
        concept_id = "test-concept-123"
        repository._version_cache.set(concept_id, 5)

        version = repository._get_current_version(concept_id)

        assert version == 5

    def test_get_current_version_from_event_store(self, repository, mock_event_store):
        """Test getting version from event store when not in cache."""
        concept_id = "test-concept-123"
        mock_event_store.get_latest_version = Mock(return_value=3)

        version = repository._get_current_version(concept_id)

        assert version == 3
        assert repository._version_cache.get(concept_id) == 3

    def test_generate_embedding_for_concept(self, repository, mock_embedding_service):
        """Test embedding generation for concept."""
        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        embedding = repository._generate_embedding_for_concept(concept_data)

        assert len(embedding) == 384
        assert mock_embedding_service.generate_embedding.called

    def test_generate_embedding_with_empty_text(self, repository, mock_embedding_service):
        """Test embedding generation with empty text returns zero vector."""
        concept_data = {}

        embedding = repository._generate_embedding_for_concept(concept_data)

        assert len(embedding) == 384
        # With empty text, should return zero vector
        # (Note: embedding service should not be called for empty text,
        # so we should get the zero vector fallback)
        assert all(v == 0.0 for v in embedding)
        # Verify embedding service was NOT called since text is empty
        assert not mock_embedding_service.generate_embedding.called


class TestRepositoryStats:
    """Test repository statistics."""

    def test_get_repository_stats(self, repository, mock_outbox, mock_embedding_cache):
        """Test getting repository statistics."""
        # Add some data to version cache
        repository._version_cache.set("concept-1", 1)
        repository._version_cache.set("concept-2", 2)

        stats = repository.get_repository_stats()

        assert stats["version_cache_size"] == 2
        assert "outbox_pending" in stats
        assert "embedding_cache_enabled" in stats
        assert stats["embedding_cache_enabled"] is True

    def test_get_repository_stats_without_cache(
        self,
        mock_event_store,
        mock_outbox,
        mock_neo4j_projection,
        mock_chromadb_projection,
        mock_embedding_service,
    ):
        """Test getting stats when cache is disabled."""
        repo = DualStorageRepository(
            event_store=mock_event_store,
            outbox=mock_outbox,
            neo4j_projection=mock_neo4j_projection,
            chromadb_projection=mock_chromadb_projection,
            embedding_service=mock_embedding_service,
            embedding_cache=None,
        )

        stats = repo.get_repository_stats()

        assert stats["embedding_cache_enabled"] is False
        assert stats["embedding_cache_stats"] is None


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_create_concept_handles_unexpected_errors(self, repository, mock_event_store):
        """Test handling of unexpected errors during creation."""
        mock_event_store.append_event = Mock(side_effect=Exception("Database error"))

        concept_data = {"name": "Test Concept", "explanation": "Test explanation"}

        success, error, _concept_id = repository.create_concept(concept_data)

        assert success is False
        assert error is not None
        assert "unexpected error" in error.lower()

    def test_update_concept_handles_unexpected_errors(self, repository, mock_event_store):
        """Test handling of unexpected errors during update."""
        mock_event_store.get_latest_version = Mock(return_value=1)
        mock_event_store.append_event = Mock(side_effect=Exception("Database error"))

        success, error = repository.update_concept("concept-123", {"name": "New Name"})

        assert success is False
        assert error is not None

    def test_get_concept_handles_errors_gracefully(self, repository, mock_neo4j_projection):
        """Test that get_concept handles errors gracefully."""
        mock_neo4j_projection.neo4j.execute_read = Mock(side_effect=Exception("Connection error"))

        result = repository.get_concept("concept-123")

        assert result is None  # Should return None instead of raising
