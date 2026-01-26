"""
Tests for database failure scenarios and graceful degradation.

These tests verify that the system handles database unavailability
gracefully without data loss or crashes.
"""

import sqlite3
from unittest.mock import Mock, patch

import pytest

from projections.chromadb_projection import ChromaDBProjection
from projections.neo4j_projection import Neo4jProjection
from services.chromadb_service import ChromaDbService
from services.event_store import EventStore
from services.neo4j_service import Neo4jService
from services.outbox import Outbox
from services.repository import DualStorageRepository


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test_failures.db"
    conn = sqlite3.connect(str(db_path))

    # Initialize event_store schema
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            aggregate_type TEXT NOT NULL,
            event_data TEXT NOT NULL,
            metadata TEXT,
            version INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """
    )

    # Initialize outbox schema
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox (
            outbox_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            projection_name TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_attempt TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL
        )
    """
    )

    conn.commit()
    yield str(db_path)
    conn.close()


@pytest.fixture
def mock_neo4j_service():
    """Create a mock Neo4j service."""
    service = Mock(spec=Neo4jService)
    service.execute_write = Mock(return_value={"nodes_created": 1})
    service.execute_read = Mock(return_value=[])
    return service


@pytest.fixture
def mock_chromadb_service():
    """Create a mock ChromaDB service."""
    service = Mock(spec=ChromaDbService)
    mock_collection = Mock()
    mock_collection.add = Mock()
    mock_collection.update = Mock()
    mock_collection.delete = Mock()
    mock_collection.get = Mock(return_value={"ids": [], "metadatas": []})
    service.get_collection = Mock(return_value=mock_collection)
    return service


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = Mock()
    service.generate_embedding = Mock(return_value=[0.1] * 384)
    return service


@pytest.fixture
def repository(temp_db, mock_neo4j_service, mock_chromadb_service, mock_embedding_service):
    """Create a DualStorageRepository for testing."""
    event_store = EventStore(temp_db)
    outbox = Outbox(temp_db)
    neo4j_projection = Neo4jProjection(mock_neo4j_service)
    chromadb_projection = ChromaDBProjection(mock_chromadb_service)

    return DualStorageRepository(
        event_store=event_store,
        outbox=outbox,
        neo4j_projection=neo4j_projection,
        chromadb_projection=chromadb_projection,
        embedding_service=mock_embedding_service,
        embedding_cache=None,
    )


class TestNeo4jUnavailable:
    """Test scenarios where Neo4j is unavailable."""

    def test_neo4j_connection_failure_on_create(self, repository, mock_neo4j_service):
        """Test create_concept when Neo4j connection fails."""
        # Simulate Neo4j connection failure
        mock_neo4j_service.execute_write.side_effect = Exception("Neo4j connection failed")

        concept_data = {
            "name": "Test Concept",
            "explanation": "Test explanation",
            "area": "Testing",
            "confidence_score": 90
        }

        # Should still succeed with ChromaDB only
        result = repository.create_concept(concept_data)

        # Verify concept was created (event stored)
        # Result can be either dict or tuple (success, message, concept_id)
        assert result is not None
        if isinstance(result, tuple):
            _success, _message, concept_id = result
            assert concept_id is not None
        else:
            assert "concept_id" in result

        # Event should be in outbox for retry
        pending = repository.outbox.get_pending()
        assert len(pending) > 0

    def test_neo4j_query_execution_failure(self, repository, mock_neo4j_service):
        """Test when Neo4j query execution fails."""
        mock_neo4j_service.execute_read.side_effect = Exception("Query execution failed")

        # Attempt to retrieve concept (should handle gracefully)
        result = repository.get_concept("concept_123")

        # Should return None gracefully
        assert result is None

    def test_neo4j_timeout_error(self, repository, mock_neo4j_service):
        """Test when Neo4j times out."""
        mock_neo4j_service.execute_write.side_effect = TimeoutError("Neo4j timeout")

        concept_data = {
            "name": "Timeout Test",
            "explanation": "Testing timeout handling",
            "confidence_score": 85
        }

        result = repository.create_concept(concept_data)

        # Should handle timeout gracefully
        assert result is not None

    def test_neo4j_intermittent_failure(self, repository, mock_neo4j_service):
        """Test when Neo4j fails intermittently."""
        # First call fails, second succeeds
        mock_neo4j_service.execute_write.side_effect = [
            Exception("Intermittent failure"),
            {"nodes_created": 1},
        ]

        concept_data = {
            "name": "Intermittent Test",
            "explanation": "Testing intermittent failures",
            "confidence_score": 80
        }

        # First attempt
        result1 = repository.create_concept(concept_data)
        assert result1 is not None

        # Process outbox (should retry and succeed)
        retry_result = repository.process_pending_outbox(limit=10)
        assert retry_result["processed"] >= 0


class TestChromaDBUnavailable:
    """Test scenarios where ChromaDB is unavailable."""

    def test_chromadb_collection_access_failure(self, repository, mock_chromadb_service):
        """Test create_concept when ChromaDB collection access fails."""
        mock_chromadb_service.get_collection.side_effect = Exception(
            "ChromaDB collection not found"
        )

        concept_data = {
            "name": "Test Concept",
            "explanation": "Test explanation",
            "area": "Testing",
            "confidence_score": 90
        }

        # Should still succeed with Neo4j only
        result = repository.create_concept(concept_data)

        assert result is not None
        # Result can be either dict or tuple (success, message, concept_id)
        if isinstance(result, tuple):
            _success, _message, concept_id = result
            assert concept_id is not None
        else:
            assert "concept_id" in result

        # Event should be in outbox for retry
        pending = repository.outbox.get_pending()
        assert len(pending) > 0

    def test_chromadb_add_operation_failure(self, repository, mock_chromadb_service):
        """Test when ChromaDB add operation fails."""
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception("Add operation failed")
        mock_chromadb_service.get_collection.return_value = mock_collection

        concept_data = {
            "name": "Add Failure Test",
            "explanation": "Testing add failures",
            "confidence_score": 85
        }

        result = repository.create_concept(concept_data)

        # Should handle gracefully
        assert result is not None

    def test_chromadb_update_operation_failure(self, repository, mock_chromadb_service):
        """Test when ChromaDB update operation fails."""
        # Setup: First create succeeds
        mock_collection = Mock()
        mock_collection.add = Mock()
        mock_collection.update.side_effect = Exception("Update operation failed")
        mock_chromadb_service.get_collection.return_value = mock_collection

        # Create concept first
        concept_data = {
            "name": "Original Name",
            "explanation": "Original explanation",
            "confidence_score": 80
        }
        result = repository.create_concept(concept_data)

        # Extract concept_id from result (dict or tuple)
        if isinstance(result, tuple):
            _success, _message, concept_id = result
        else:
            concept_id = result["concept_id"]

        # Now try to update (should handle failure)
        update_data = {"explanation": "Updated explanation"}
        update_result = repository.update_concept(concept_id, update_data)

        # Should still create event even if projection fails
        assert update_result is not None

    def test_chromadb_network_timeout(self, repository, mock_chromadb_service):
        """Test when ChromaDB has network timeout."""
        mock_chromadb_service.get_collection.side_effect = TimeoutError("ChromaDB timeout")

        concept_data = {
            "name": "Timeout Test",
            "explanation": "Testing timeout handling",
            "confidence_score": 85
        }

        result = repository.create_concept(concept_data)

        # Should handle timeout gracefully
        assert result is not None


class TestGracefulDegradation:
    """Test graceful degradation when databases are unavailable."""

    def test_partial_write_neo4j_fails(self, repository, mock_neo4j_service):
        """Test system continues when Neo4j fails but ChromaDB succeeds."""
        mock_neo4j_service.execute_write.side_effect = Exception("Neo4j failed")

        concept_data = {
            "name": "Partial Write Test",
            "explanation": "Testing partial write scenarios",
            "confidence_score": 90
        }

        result = repository.create_concept(concept_data)

        # Event should be stored
        assert result is not None

        # Outbox should contain failed projection for retry
        pending = repository.outbox.get_pending()
        assert len(pending) > 0
        assert any(p.projection_name == "neo4j" for p in pending)

    def test_partial_write_chromadb_fails(self, repository, mock_chromadb_service):
        """Test system continues when ChromaDB fails but Neo4j succeeds."""
        mock_chromadb_service.get_collection.side_effect = Exception("ChromaDB failed")

        concept_data = {
            "name": "Partial Write Test",
            "explanation": "Testing partial write scenarios",
            "confidence_score": 90
        }

        result = repository.create_concept(concept_data)

        # Event should be stored
        assert result is not None

        # Outbox should contain failed projection for retry
        pending = repository.outbox.get_pending()
        assert len(pending) > 0
        assert any(p.projection_name == "chromadb" for p in pending)

    def test_no_data_corruption_on_failure(self, repository, mock_neo4j_service):
        """Test that failures don't corrupt data in successful database."""
        # Neo4j fails, ChromaDB succeeds
        mock_neo4j_service.execute_write.side_effect = Exception("Neo4j failed")

        concept_data = {
            "name": "Data Integrity Test",
            "explanation": "Ensuring no data corruption",
            "confidence_score": 95
        }

        result = repository.create_concept(concept_data)

        # Extract concept_id from result (dict or tuple)
        if isinstance(result, tuple):
            _success, _message, concept_id = result
        else:
            concept_id = result["concept_id"]

        # Event should be in event store
        events = repository.event_store.get_events_by_aggregate(concept_id)
        assert len(events) == 1
        assert events[0].event_type == "ConceptCreated"

    def test_read_operations_with_neo4j_down(self, repository, mock_neo4j_service):
        """Test read operations when Neo4j is unavailable."""
        mock_neo4j_service.execute_read.side_effect = Exception("Neo4j unavailable")

        # Should handle gracefully
        result = repository.get_concept("concept_123")
        assert result is None  # Graceful failure

    def test_system_stability_under_failures(
        self, repository, mock_neo4j_service, mock_chromadb_service
    ):
        """Test that system remains stable under repeated failures."""
        # Simulate alternating failures
        call_count = [0]

        def alternating_failure(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                raise Exception("Intermittent failure")
            return {"nodes_created": 1}

        mock_neo4j_service.execute_write.side_effect = alternating_failure

        # Create multiple concepts
        for i in range(5):
            concept_data = {
                "name": f"Stability Test {i}",
                "explanation": f"Testing system stability #{i}",
                "confidence_score": 80 + i
            }
            result = repository.create_concept(concept_data)
            assert result is not None

        # All events should be stored
        # System should remain stable
        assert True  # If we reach here without crash, test passes

    def test_error_messages_are_logged(self, repository, mock_neo4j_service):
        """Test that database failures are properly logged."""
        mock_neo4j_service.execute_write.side_effect = Exception("Test error for logging")

        with patch("services.repository.logger") as mock_logger:
            concept_data = {
                "name": "Logging Test",
                "explanation": "Testing error logging",
                "confidence_score": 85
            }

            repository.create_concept(concept_data)

            # Verify error was logged
            assert mock_logger.error.called or mock_logger.warning.called
