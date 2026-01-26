"""
Tests for recovery mechanisms and consistency validation.

These tests verify that the system can recover from failures through
rollback, retry, and consistency checking mechanisms.
"""

import sqlite3
from unittest.mock import Mock

import pytest

from models.events import ConceptCreated
from projections.chromadb_projection import ChromaDBProjection
from projections.neo4j_projection import Neo4jProjection
from services.chromadb_service import ChromaDbService
from services.compensation import CompensationManager
from services.consistency_checker import ConsistencyChecker
from services.event_store import EventStore
from services.neo4j_service import Neo4jService
from services.outbox import Outbox
from services.repository import DualStorageRepository


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test_recovery.db"
    conn = sqlite3.connect(str(db_path))

    # Initialize all required schemas
    cursor = conn.cursor()

    # Events table
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

    # Outbox table
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

    # Compensation audit table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS compensation_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aggregate_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_id TEXT NOT NULL,
            target_system TEXT NOT NULL,
            action TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            timestamp TEXT NOT NULL
        )
    """
    )

    # Consistency snapshots table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS consistency_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            neo4j_count INTEGER NOT NULL,
            chromadb_count INTEGER NOT NULL,
            discrepancies TEXT,
            checked_at TEXT NOT NULL,
            status TEXT NOT NULL
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
def compensation_manager(temp_db, mock_neo4j_service, mock_chromadb_service):
    """Create a CompensationManager for testing."""
    return CompensationManager(mock_neo4j_service, mock_chromadb_service, sqlite3.connect(temp_db))


@pytest.fixture
def outbox(temp_db):
    """Create an Outbox for testing."""
    return Outbox(temp_db)


@pytest.fixture
def event_store(temp_db):
    """Create an EventStore for testing."""
    return EventStore(temp_db)


class TestWriteFailureRollback:
    """Test rollback mechanisms when writes fail."""

    def test_neo4j_write_fails_triggers_rollback(self, compensation_manager, mock_neo4j_service):
        """Test that Neo4j write failure triggers compensation rollback."""
        # Simulate Neo4j write failure
        mock_neo4j_service.execute_write.side_effect = Exception("Write failed")

        event = ConceptCreated(
            aggregate_id="concept_123",
            concept_data={"name": "Test", "explanation": "Test explanation"},
            version=1,
        )

        # Attempt rollback
        compensation_manager.rollback_neo4j(event)

        # Rollback should be recorded in audit
        conn = compensation_manager.connection
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM compensation_audit WHERE aggregate_id = ?", ("concept_123",)
        )
        count = cursor.fetchone()[0]
        assert count >= 1

    def test_chromadb_write_fails_triggers_rollback(
        self, compensation_manager, mock_chromadb_service
    ):
        """Test that ChromaDB write failure triggers compensation rollback."""
        # Simulate ChromaDB write failure
        mock_collection = Mock()
        mock_collection.delete.side_effect = Exception("Delete failed")
        mock_chromadb_service.get_collection.return_value = mock_collection

        event = ConceptCreated(
            aggregate_id="concept_456",
            concept_data={"name": "Test", "explanation": "Test explanation"},
            version=1,
        )

        # Attempt rollback (should handle failure gracefully)
        compensation_manager.rollback_chromadb(event)

        # Should record the attempt
        conn = compensation_manager.connection
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM compensation_audit WHERE aggregate_id = ?", ("concept_456",)
        )
        count = cursor.fetchone()[0]
        assert count >= 1

    def test_rollback_success_after_partial_write(self, compensation_manager, mock_neo4j_service):
        """Test successful rollback after partial write."""
        # First write succeeds, second fails
        mock_neo4j_service.execute_write.return_value = {"nodes_deleted": 1}

        event = ConceptCreated(
            aggregate_id="concept_789",
            concept_data={"name": "Partial Write", "explanation": "Test"},
            version=1,
        )

        # Execute rollback
        success = compensation_manager.rollback_neo4j(event)

        # Verify rollback succeeded
        assert success is True

        # Check audit trail
        conn = compensation_manager.connection
        cursor = conn.cursor()
        cursor.execute(
            "SELECT success FROM compensation_audit WHERE aggregate_id = ? ORDER BY timestamp DESC LIMIT 1",
            ("concept_789",),
        )
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == 1  # success = True

    def test_idempotent_rollback(self, compensation_manager, mock_neo4j_service):
        """Test that rollback can be called multiple times safely."""
        mock_neo4j_service.execute_write.return_value = {"nodes_deleted": 0}

        event = ConceptCreated(
            aggregate_id="concept_idempotent",
            concept_data={"name": "Idempotent Test", "explanation": "Test"},
            version=1,
        )

        # Call rollback multiple times
        success1 = compensation_manager.rollback_neo4j(event)
        success2 = compensation_manager.rollback_neo4j(event)
        success3 = compensation_manager.rollback_neo4j(event)

        # All should succeed (idempotent)
        assert success1 is True
        assert success2 is True
        assert success3 is True

        # All attempts should be recorded
        conn = compensation_manager.connection
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM compensation_audit WHERE aggregate_id = ?",
            ("concept_idempotent",),
        )
        count = cursor.fetchone()[0]
        assert count == 3


class TestRetryMechanisms:
    """Test retry mechanisms through the Outbox pattern."""

    def test_outbox_retry_logic(self, outbox, event_store):
        """Test that failed items are retried up to MAX_ATTEMPTS."""
        # Create event
        event = ConceptCreated(
            aggregate_id="concept_retry",
            concept_data={"name": "Retry Test", "explanation": "Test"},
            version=1,
        )
        event_store.append_event(event)

        # Add to outbox
        outbox_id = outbox.add_to_outbox(event.event_id, "neo4j")

        # Fail it multiple times
        for i in range(Outbox.MAX_ATTEMPTS):
            outbox.mark_failed(outbox_id, f"Attempt {i+1} failed")

        # After MAX_ATTEMPTS, should be marked as failed
        pending = outbox.get_pending()
        assert len(pending) == 0

        failed_items = outbox.get_failed_items()
        assert len(failed_items) == 1
        assert failed_items[0].attempts == Outbox.MAX_ATTEMPTS

    def test_retry_after_first_failure(self, outbox, event_store):
        """Test that items are retried after first failure."""
        event = ConceptCreated(
            aggregate_id="concept_retry_once",
            concept_data={"name": "Retry Once", "explanation": "Test"},
            version=1,
        )
        event_store.append_event(event)

        outbox_id = outbox.add_to_outbox(event.event_id, "neo4j")

        # Fail once
        outbox.mark_failed(outbox_id, "First attempt failed")

        # Should still be in pending (retry available)
        pending = outbox.get_pending()
        assert len(pending) == 1
        assert pending[0].attempts == 1

    def test_successful_retry_after_failure(self, outbox, event_store):
        """Test successful processing after failure."""
        event = ConceptCreated(
            aggregate_id="concept_success_retry",
            concept_data={"name": "Success Retry", "explanation": "Test"},
            version=1,
        )
        event_store.append_event(event)

        outbox_id = outbox.add_to_outbox(event.event_id, "neo4j")

        # Fail first attempt
        outbox.mark_failed(outbox_id, "First attempt failed")

        # Succeed on second attempt
        outbox.mark_processed(outbox_id)

        # Should no longer be pending
        pending = outbox.get_pending()
        assert not any(p.outbox_id == outbox_id for p in pending)

    def test_retry_failed_item_reset(self, outbox, event_store):
        """Test that retry_failed resets attempts counter."""
        event = ConceptCreated(
            aggregate_id="concept_reset",
            concept_data={"name": "Reset Test", "explanation": "Test"},
            version=1,
        )
        event_store.append_event(event)

        outbox_id = outbox.add_to_outbox(event.event_id, "neo4j")

        # Exhaust retries
        for _ in range(Outbox.MAX_ATTEMPTS):
            outbox.mark_failed(outbox_id, "Test failure")

        # Manually retry
        result = outbox.retry_failed(outbox_id)
        assert result is True

        # Should be back in pending with reset attempts
        pending = outbox.get_pending()
        assert len(pending) == 1
        assert pending[0].attempts == 0


class TestOutboxProcessing:
    """Test outbox processing after failures."""

    def test_process_pending_after_failures(
        self, temp_db, mock_neo4j_service, mock_chromadb_service
    ):
        """Test that process_pending_outbox recovers failed projections."""
        event_store = EventStore(temp_db)
        outbox = Outbox(temp_db)
        neo4j_projection = Neo4jProjection(mock_neo4j_service)
        chromadb_projection = ChromaDBProjection(mock_chromadb_service)

        repository = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=Mock(generate_embedding=Mock(return_value=[0.1] * 384)),
            embedding_cache=None,
        )

        # Create concept with Neo4j failure
        mock_neo4j_service.execute_write.side_effect = Exception("Neo4j failed")

        concept_data = {
            "name": "Process Test",
            "explanation": "Testing outbox processing",
            "confidence_score": 90
        }

        result = repository.create_concept(concept_data)
        assert result is not None

        # Now fix Neo4j and process pending
        mock_neo4j_service.execute_write.side_effect = None
        mock_neo4j_service.execute_write.return_value = {"nodes_created": 1}

        process_result = repository.process_pending_outbox(limit=10)

        # Should have processed the failed entry
        assert process_result["total"] > 0

    def test_outbox_processes_oldest_first(self, outbox, event_store):
        """Test that outbox processes oldest entries first."""
        # Create multiple events
        for i in range(3):
            event = ConceptCreated(
                aggregate_id=f"concept_{i}",
                concept_data={"name": f"Concept {i}", "explanation": "Test"},
                version=1,
            )
            event_store.append_event(event)
            outbox.add_to_outbox(event.event_id, "neo4j")

        # Get pending (should be in chronological order)
        pending = outbox.get_pending()
        assert len(pending) == 3

        # Verify order (oldest first)
        for i in range(len(pending) - 1):
            # Later items should have later or equal creation times
            assert pending[i].created_at <= pending[i + 1].created_at

    def test_outbox_limit_parameter(self, outbox, event_store):
        """Test that process_pending respects limit parameter."""
        # Create many events
        for i in range(20):
            event = ConceptCreated(
                aggregate_id=f"concept_limit_{i}",
                concept_data={"name": f"Concept {i}", "explanation": "Test"},
                version=1,
            )
            event_store.append_event(event)
            outbox.add_to_outbox(event.event_id, "neo4j")

        # Get with limit
        pending = outbox.get_pending(limit=5)
        assert len(pending) == 5


class TestConsistencyChecker:
    """Test consistency checker validation after failures."""

    def test_consistency_checker_detects_discrepancies(
        self, temp_db, mock_neo4j_service, mock_chromadb_service
    ):
        """Test that consistency checker detects Neo4j/ChromaDB discrepancies."""
        # Setup: Neo4j has one concept, ChromaDB has none
        mock_neo4j_service.execute_read.return_value = [
            {
                "concept_id": "concept_001",
                "name": "Test",
                "area": "Testing",
                "topic": None,
                "subtopic": None,
                "confidence_score": 90,
                "deleted": False
            }
        ]

        mock_collection = Mock()
        mock_collection.get.return_value = {"ids": [], "metadatas": []}
        mock_chromadb_service.get_collection.return_value = mock_collection

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        report = checker.check_consistency(save_snapshot=True)

        # Should detect discrepancy
        assert report.is_consistent is False
        assert report.neo4j_count == 1
        assert report.chromadb_count == 0
        assert len(report.neo4j_only) == 1

    def test_consistency_checker_on_consistent_databases(
        self, temp_db, mock_neo4j_service, mock_chromadb_service
    ):
        """Test that consistency checker passes when databases match."""
        # Setup: Both have the same concept
        mock_neo4j_service.execute_read.return_value = [
            {
                "concept_id": "concept_001",
                "name": "Test",
                "area": "Testing",
                "topic": None,
                "subtopic": None,
                "confidence_score": 90,
                "deleted": False
            }
        ]

        mock_collection = Mock()
        mock_collection.get.return_value = {
            'ids': ['concept_001'],
            'metadatas': [{
                'name': 'Test',
                'area': 'Testing',
                'topic': None,
                'subtopic': None,
                'confidence_score': 90
            }]
        }
        mock_chromadb_service.get_collection.return_value = mock_collection

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        report = checker.check_consistency(save_snapshot=True)

        # Should be consistent
        assert report.is_consistent is True
        assert report.neo4j_count == 1
        assert report.chromadb_count == 1

    def test_consistency_checker_saves_snapshot(
        self, temp_db, mock_neo4j_service, mock_chromadb_service
    ):
        """Test that consistency checker saves snapshot to database."""
        mock_neo4j_service.execute_read.return_value = []
        mock_collection = Mock()
        mock_collection.get.return_value = {"ids": [], "metadatas": []}
        mock_chromadb_service.get_collection.return_value = mock_collection

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        checker.check_consistency(save_snapshot=True)

        # Verify snapshot was saved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM consistency_snapshots")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_consistency_checker_reports_mismatched_metadata(
        self, temp_db, mock_neo4j_service, mock_chromadb_service
    ):
        """Test that consistency checker detects metadata mismatches."""
        # Setup: Same concept ID but different metadata
        mock_neo4j_service.execute_read.return_value = [
            {
                "concept_id": "concept_001",
                "name": "Original Name",
                "area": "Testing",
                "topic": None,
                "subtopic": None,
                "confidence_score": 90,
                "deleted": False
            }
        ]

        mock_collection = Mock()
        mock_collection.get.return_value = {
            'ids': ['concept_001'],
            'metadatas': [{
                'name': 'Different Name',  # Mismatch
                'area': 'Testing',
                'topic': None,
                'subtopic': None,
                'confidence_score': 90
            }]
        }
        mock_chromadb_service.get_collection.return_value = mock_collection

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        report = checker.check_consistency(save_snapshot=False)

        # Should detect mismatch
        assert report.is_consistent is False
        assert len(report.mismatched) == 1
