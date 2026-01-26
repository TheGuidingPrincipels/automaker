"""
Unit tests for CompensationManager.

Tests compensation transaction rollback logic for failed dual writes.
"""

import sqlite3
from unittest.mock import Mock, patch

from models.events import ConceptCreated, ConceptDeleted, ConceptUpdated
from services.compensation import CompensationManager


class TestCompensationManagerInit:
    """Test CompensationManager initialization."""

    def test_init_creates_audit_table(self):
        """Test that initialization creates the audit table."""
        # Create in-memory database
        conn = sqlite3.connect(":memory:")

        # Mock services
        neo4j_service = Mock()
        chromadb_service = Mock()

        # Initialize manager
        CompensationManager(neo4j_service, chromadb_service, conn)

        # Verify table exists
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='compensation_audit'
        """
        )
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == "compensation_audit"

    def test_init_creates_indexes(self):
        """Test that initialization creates indexes."""
        conn = sqlite3.connect(":memory:")
        neo4j_service = Mock()
        chromadb_service = Mock()

        CompensationManager(neo4j_service, chromadb_service, conn)

        # Verify indexes exist
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name IN (
                'idx_comp_aggregate',
                'idx_comp_timestamp',
                'idx_comp_target'
            )
        """
        )
        indexes = cursor.fetchall()

        assert len(indexes) == 3

    def test_init_idempotent(self):
        """Test that initialization is idempotent (can be called multiple times)."""
        conn = sqlite3.connect(":memory:")
        neo4j_service = Mock()
        chromadb_service = Mock()

        # Initialize twice
        manager1 = CompensationManager(neo4j_service, chromadb_service, conn)
        manager2 = CompensationManager(neo4j_service, chromadb_service, conn)

        # Should not raise error
        assert manager1 is not None
        assert manager2 is not None


class TestRollbackNeo4j:
    """Test Neo4j rollback operations."""

    def test_rollback_concept_created_success(self):
        """Test successful rollback of ConceptCreated event."""
        conn = sqlite3.connect(":memory:")

        # Mock Neo4j service
        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(
            return_value={"nodes_deleted": 1, "relationships_deleted": 0}
        )

        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Create event
        event = ConceptCreated(
            aggregate_id="concept_123",
            concept_data={"name": "Test", "explanation": "Test concept"},
            version=1,
        )

        # Rollback
        success = manager.rollback_neo4j(event)

        assert success is True
        neo4j_service.execute_write.assert_called_once()

        # Verify audit record
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM compensation_audit WHERE aggregate_id = ?", ("concept_123",))
        audit = cursor.fetchone()

        assert audit is not None
        assert audit[1] == "concept_123"  # aggregate_id
        assert audit[2] == "ConceptCreated"  # event_type
        assert audit[4] == "neo4j"  # target_system
        assert audit[6] == 1  # success

    def test_rollback_concept_created_idempotent(self):
        """Test that rollback is idempotent (safe to call multiple times)."""
        conn = sqlite3.connect(":memory:")

        # Mock Neo4j service - first call deletes 1, second call deletes 0 (already gone)
        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(side_effect=[{"nodes_deleted": 1}, {"nodes_deleted": 0}])

        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptCreated(aggregate_id="concept_123", concept_data={"name": "Test"}, version=1)

        # Call twice
        success1 = manager.rollback_neo4j(event)
        success2 = manager.rollback_neo4j(event)

        assert success1 is True
        assert success2 is True
        assert neo4j_service.execute_write.call_count == 2

    def test_rollback_concept_updated_warning(self):
        """Test that update rollback logs a warning (can't easily restore previous state)."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()
        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptUpdated(
            aggregate_id="concept_123", updates={"name": "Updated Name"}, version=2
        )

        # Rollback - should succeed but note it can't restore previous state
        with patch("services.compensation.logger") as mock_logger:
            success = manager.rollback_neo4j(event)

            assert success is True
            mock_logger.warning.assert_called()

    def test_rollback_concept_deleted_warning(self):
        """Test that delete rollback logs a warning (can't restore deleted concept)."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()
        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptDeleted(aggregate_id="concept_123", version=2)

        # Rollback - should succeed but note it can't restore
        with patch("services.compensation.logger") as mock_logger:
            success = manager.rollback_neo4j(event)

            assert success is True
            mock_logger.warning.assert_called()

    def test_rollback_neo4j_service_failure(self):
        """Test handling of Neo4j service failure during rollback."""
        conn = sqlite3.connect(":memory:")

        # Mock Neo4j service to raise exception
        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(side_effect=Exception("Neo4j connection failed"))

        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptCreated(aggregate_id="concept_123", concept_data={"name": "Test"}, version=1)

        # Rollback should fail gracefully
        success = manager.rollback_neo4j(event)

        assert success is False

        # Verify failure recorded in audit
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM compensation_audit WHERE aggregate_id = ?", ("concept_123",))
        audit = cursor.fetchone()

        assert audit is not None
        assert audit[6] == 0  # success = False
        assert "Neo4j connection failed" in audit[7]  # error_message


class TestRollbackChromaDB:
    """Test ChromaDB rollback operations."""

    def test_rollback_concept_created_success(self):
        """Test successful rollback of ConceptCreated event."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()

        # Mock ChromaDB service
        chromadb_service = Mock()
        mock_collection = Mock()
        mock_collection.delete = Mock()
        chromadb_service.get_collection = Mock(return_value=mock_collection)

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptCreated(aggregate_id="concept_123", concept_data={"name": "Test"}, version=1)

        # Rollback
        success = manager.rollback_chromadb(event)

        assert success is True
        mock_collection.delete.assert_called_once_with(ids=["concept_123"])

        # Verify audit record
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM compensation_audit WHERE aggregate_id = ?", ("concept_123",))
        audit = cursor.fetchone()

        assert audit is not None
        assert audit[4] == "chromadb"  # target_system
        assert audit[6] == 1  # success

    def test_rollback_concept_updated_success(self):
        """Test rollback of ConceptUpdated event (deletes document)."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()

        chromadb_service = Mock()
        mock_collection = Mock()
        mock_collection.delete = Mock()
        chromadb_service.get_collection = Mock(return_value=mock_collection)

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptUpdated(aggregate_id="concept_123", updates={"name": "Updated"}, version=2)

        success = manager.rollback_chromadb(event)

        assert success is True
        mock_collection.delete.assert_called_once_with(ids=["concept_123"])

    def test_rollback_idempotent_document_not_exists(self):
        """Test that rollback is idempotent when document doesn't exist."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()

        chromadb_service = Mock()
        mock_collection = Mock()
        # Simulate document doesn't exist
        mock_collection.delete = Mock(side_effect=Exception("Document does not exist"))
        chromadb_service.get_collection = Mock(return_value=mock_collection)

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptCreated(aggregate_id="concept_123", concept_data={"name": "Test"}, version=1)

        # Should still return success (idempotent)
        success = manager.rollback_chromadb(event)

        assert success is True

    def test_rollback_chromadb_service_failure(self):
        """Test handling of ChromaDB service failure during rollback."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()

        chromadb_service = Mock()
        chromadb_service.get_collection = Mock(side_effect=Exception("ChromaDB connection failed"))

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptCreated(aggregate_id="concept_123", concept_data={"name": "Test"}, version=1)

        # Rollback should fail gracefully
        success = manager.rollback_chromadb(event)

        assert success is False

        # Verify failure recorded in audit
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM compensation_audit WHERE aggregate_id = ?", ("concept_123",))
        audit = cursor.fetchone()

        assert audit is not None
        assert audit[6] == 0  # success = False
        assert "ChromaDB connection failed" in audit[7]  # error_message


class TestCompensationAudit:
    """Test compensation audit trail functionality."""

    def test_get_compensation_history(self):
        """Test retrieving compensation history."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(return_value={"nodes_deleted": 1})

        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Perform some compensations
        event1 = ConceptCreated(
            aggregate_id="concept_001", concept_data={"name": "Test 1"}, version=1
        )
        event2 = ConceptCreated(
            aggregate_id="concept_002", concept_data={"name": "Test 2"}, version=1
        )

        manager.rollback_neo4j(event1)
        manager.rollback_neo4j(event2)

        # Get history
        history = manager.get_compensation_history()

        assert len(history) == 2
        assert history[0]["aggregate_id"] in ["concept_001", "concept_002"]
        assert history[0]["target_system"] == "neo4j"

    def test_get_compensation_history_filtered_by_aggregate(self):
        """Test filtering history by aggregate ID."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(return_value={"nodes_deleted": 1})

        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Create compensations for different aggregates
        event1 = ConceptCreated(
            aggregate_id="concept_001", concept_data={"name": "Test 1"}, version=1
        )
        event2 = ConceptCreated(
            aggregate_id="concept_002", concept_data={"name": "Test 2"}, version=1
        )

        manager.rollback_neo4j(event1)
        manager.rollback_neo4j(event2)

        # Get history for specific aggregate
        history = manager.get_compensation_history(aggregate_id="concept_001")

        assert len(history) == 1
        assert history[0]["aggregate_id"] == "concept_001"

    def test_get_compensation_history_filtered_by_target(self):
        """Test filtering history by target system."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(return_value={"nodes_deleted": 1})

        chromadb_service = Mock()
        mock_collection = Mock()
        mock_collection.delete = Mock()
        chromadb_service.get_collection = Mock(return_value=mock_collection)

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

        # Perform compensations on both targets
        manager.rollback_neo4j(event)
        manager.rollback_chromadb(event)

        # Get history for specific target
        history = manager.get_compensation_history(target="neo4j")

        assert len(history) == 1
        assert history[0]["target_system"] == "neo4j"

    def test_get_compensation_history_with_limit(self):
        """Test limiting history results."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(return_value={"nodes_deleted": 1})

        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Create multiple compensations
        for i in range(10):
            event = ConceptCreated(
                aggregate_id=f"concept_{i:03d}", concept_data={"name": f"Test {i}"}, version=1
            )
            manager.rollback_neo4j(event)

        # Get limited history
        history = manager.get_compensation_history(limit=5)

        assert len(history) == 5


class TestCompensationStats:
    """Test compensation statistics."""

    def test_get_stats_empty(self):
        """Test getting stats when no compensations have occurred."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()
        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        stats = manager.get_stats()

        assert stats["total_compensations"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["by_target"] == {}

    def test_get_stats_with_compensations(self):
        """Test getting stats after compensations."""
        conn = sqlite3.connect(":memory:")

        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(return_value={"nodes_deleted": 1})

        chromadb_service = Mock()
        mock_collection = Mock()
        mock_collection.delete = Mock()
        chromadb_service.get_collection = Mock(return_value=mock_collection)

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Perform some compensations
        event1 = ConceptCreated(
            aggregate_id="concept_001", concept_data={"name": "Test 1"}, version=1
        )
        event2 = ConceptCreated(
            aggregate_id="concept_002", concept_data={"name": "Test 2"}, version=1
        )

        manager.rollback_neo4j(event1)
        manager.rollback_chromadb(event2)

        stats = manager.get_stats()

        assert stats["total_compensations"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        assert stats["by_target"]["neo4j"] == 1
        assert stats["by_target"]["chromadb"] == 1

    def test_get_stats_with_failures(self):
        """Test stats include failed compensations."""
        conn = sqlite3.connect(":memory:")

        # Mock Neo4j to fail
        neo4j_service = Mock()
        neo4j_service.execute_write = Mock(side_effect=Exception("Connection failed"))

        chromadb_service = Mock()

        manager = CompensationManager(neo4j_service, chromadb_service, conn)

        event = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

        manager.rollback_neo4j(event)

        stats = manager.get_stats()

        assert stats["total_compensations"] == 1
        assert stats["successful"] == 0
        assert stats["failed"] == 1
