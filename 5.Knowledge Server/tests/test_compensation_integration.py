"""
Integration tests for CompensationManager with DualStorageRepository.

Tests compensation behavior with real scenarios including Neo4j and ChromaDB failures.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from models.events import ConceptCreated
from projections.chromadb_projection import ChromaDBProjection
from projections.neo4j_projection import Neo4jProjection
from services.chromadb_service import ChromaDbService
from services.compensation import CompensationManager
from services.embedding_cache import EmbeddingCache
from services.embedding_service import EmbeddingService
from services.event_store import EventStore
from services.neo4j_service import Neo4jService
from services.outbox import Outbox
from services.repository import DualStorageRepository


@pytest.fixture
def test_db():
    """Create temporary SQLite database for testing."""
    # Use a temporary file
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = db_file.name
    db_file.close()

    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create events table
    cursor.execute(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            aggregate_type TEXT NOT NULL,
            event_data TEXT NOT NULL,
            metadata TEXT,
            version INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create outbox table
    cursor.execute(
        """
        CREATE TABLE outbox (
            outbox_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            projection_name TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_attempt DATETIME,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create embedding_cache table
    cursor.execute(
        """
        CREATE TABLE embedding_cache (
            text_hash TEXT NOT NULL,
            model_name TEXT NOT NULL,
            embedding TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (text_hash, model_name)
        )
    """
    )

    conn.commit()

    yield conn, db_path

    # Cleanup
    conn.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_neo4j_service():
    """Create mock Neo4j service."""
    service = Mock(spec=Neo4jService)
    service.is_connected = Mock(return_value=True)
    service.execute_write = Mock(
        return_value={"nodes_created": 1, "properties_set": 5, "relationships_created": 0}
    )
    service.execute_read = Mock(return_value=[])
    return service


@pytest.fixture
def mock_chromadb_service():
    """Create mock ChromaDB service."""
    service = Mock(spec=ChromaDbService)
    service.is_connected = Mock(return_value=True)

    # Mock collection
    mock_collection = Mock()
    mock_collection.add = Mock()
    mock_collection.update = Mock()
    mock_collection.delete = Mock()
    service.get_collection = Mock(return_value=mock_collection)

    return service


@pytest.fixture
def test_embedding_service():
    """Create embedding service for testing."""
    service = EmbeddingService()
    # Mock the service to avoid loading the actual model
    service._model_available = True
    service.model = Mock()
    service.model.encode = Mock(return_value=[[0.1] * 384])
    service.config = Mock()
    service.config.model_name = "test-model"
    return service


class TestRepositoryWithCompensation:
    """Test DualStorageRepository with CompensationManager."""

    def test_create_concept_neo4j_fails_chromadb_rolled_back(
        self, test_db, mock_neo4j_service, mock_chromadb_service, test_embedding_service
    ):
        """Test that ChromaDB is rolled back when Neo4j fails."""
        conn, db_path = test_db

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)

        # Create compensation manager
        compensation_manager = CompensationManager(mock_neo4j_service, mock_chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(mock_neo4j_service)
        chromadb_projection = ChromaDBProjection(mock_chromadb_service)

        # Mock Neo4j to fail
        mock_neo4j_service.execute_write = Mock(side_effect=Exception("Neo4j connection failed"))

        # ChromaDB succeeds initially
        mock_collection = mock_chromadb_service.get_collection()
        mock_collection.add = Mock()

        # Create repository with compensation
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=test_embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Try to create concept
        concept_data = {"name": "Test Concept", "explanation": "This is a test concept"}

        _success, _error, concept_id = repo.create_concept(concept_data)

        # Should still return partial success (ChromaDB succeeded initially)
        # But compensation should have been attempted
        assert concept_id is not None

        # Verify compensation was recorded
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM compensation_audit WHERE aggregate_id = ?", (concept_id,))
        audit = cursor.fetchone()

        assert audit is not None
        assert audit[4] == "chromadb"  # ChromaDB was rolled back

    def test_create_concept_chromadb_fails_neo4j_rolled_back(
        self, test_db, mock_neo4j_service, mock_chromadb_service, test_embedding_service
    ):
        """Test that Neo4j is rolled back when ChromaDB fails."""
        conn, db_path = test_db

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)

        # Create compensation manager
        compensation_manager = CompensationManager(mock_neo4j_service, mock_chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(mock_neo4j_service)
        chromadb_projection = ChromaDBProjection(mock_chromadb_service)

        # Neo4j succeeds
        mock_neo4j_service.execute_write = Mock(return_value={"nodes_created": 1})

        # Mock ChromaDB to fail
        mock_chromadb_service.is_connected = Mock(return_value=False)

        # Create repository with compensation
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=test_embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Try to create concept
        concept_data = {"name": "Test Concept", "explanation": "This is a test concept"}

        _success, _error, concept_id = repo.create_concept(concept_data)

        assert concept_id is not None

        # Verify compensation was recorded
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM compensation_audit WHERE aggregate_id = ?", (concept_id,))
        audit = cursor.fetchone()

        assert audit is not None
        assert audit[4] == "neo4j"  # Neo4j was rolled back

    def test_create_concept_both_succeed_no_compensation(
        self, test_db, mock_neo4j_service, mock_chromadb_service, test_embedding_service
    ):
        """Test that no compensation occurs when both projections succeed."""
        conn, db_path = test_db

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)

        # Create compensation manager
        compensation_manager = CompensationManager(mock_neo4j_service, mock_chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(mock_neo4j_service)
        chromadb_projection = ChromaDBProjection(mock_chromadb_service)

        # Both succeed
        mock_neo4j_service.execute_write = Mock(return_value={"nodes_created": 1})
        mock_collection = mock_chromadb_service.get_collection()
        mock_collection.add = Mock()

        # Create repository with compensation
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=test_embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Create concept
        concept_data = {"name": "Test Concept", "explanation": "This is a test concept"}

        success, error, concept_id = repo.create_concept(concept_data)

        assert success is True
        assert error is None
        assert concept_id is not None

        # Verify NO compensation occurred
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM compensation_audit")
        count = cursor.fetchone()[0]

        assert count == 0

    def test_outbox_retries_after_compensation(
        self, test_db, mock_neo4j_service, mock_chromadb_service, test_embedding_service
    ):
        """Test that Outbox still retries failed projections after compensation."""
        conn, db_path = test_db

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)

        # Create compensation manager
        compensation_manager = CompensationManager(mock_neo4j_service, mock_chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(mock_neo4j_service)
        chromadb_projection = ChromaDBProjection(mock_chromadb_service)

        # Neo4j succeeds, ChromaDB fails
        mock_neo4j_service.execute_write = Mock(return_value={"nodes_created": 1})
        mock_chromadb_service.is_connected = Mock(return_value=False)

        # Create repository with compensation
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=test_embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Create concept
        concept_data = {"name": "Test Concept", "explanation": "This is a test concept"}

        _success, _error, _concept_id = repo.create_concept(concept_data)

        # Verify outbox has entry for failed ChromaDB projection (marked as 'failed' for retry)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM outbox
            WHERE projection_name = 'chromadb' AND status IN ('failed', 'pending')
        """
        )
        failed_count = cursor.fetchone()[0]

        assert failed_count >= 1  # ChromaDB projection should be in outbox for retry

    def test_repository_stats_include_compensation(
        self, test_db, mock_neo4j_service, mock_chromadb_service, test_embedding_service
    ):
        """Test that repository stats include compensation statistics."""
        conn, db_path = test_db

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)

        # Create compensation manager
        compensation_manager = CompensationManager(mock_neo4j_service, mock_chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(mock_neo4j_service)
        chromadb_projection = ChromaDBProjection(mock_chromadb_service)

        # Create repository with compensation
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=test_embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Get stats
        stats = repo.get_repository_stats()

        assert "compensation_enabled" in stats
        assert stats["compensation_enabled"] is True
        assert "compensation_stats" in stats
        assert stats["compensation_stats"] is not None


class TestIdempotency:
    """Test idempotency of compensation operations."""

    def test_rollback_called_multiple_times(
        self, test_db, mock_neo4j_service, mock_chromadb_service
    ):
        """Test that rollback can be called multiple times safely."""
        conn, _db_path = test_db

        # Create compensation manager
        compensation_manager = CompensationManager(mock_neo4j_service, mock_chromadb_service, conn)

        # Create event
        event = ConceptCreated(aggregate_id="concept_123", concept_data={"name": "Test"}, version=1)

        # Call rollback multiple times
        mock_neo4j_service.execute_write = Mock(return_value={"nodes_deleted": 1})

        success1 = compensation_manager.rollback_neo4j(event)
        success2 = compensation_manager.rollback_neo4j(event)
        success3 = compensation_manager.rollback_neo4j(event)

        assert success1 is True
        assert success2 is True
        assert success3 is True

        # Verify all attempts recorded
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM compensation_audit WHERE aggregate_id = ?", ("concept_123",)
        )
        count = cursor.fetchone()[0]

        assert count == 3  # All three attempts recorded
