"""
End-to-End Compensation Workflow Tests.

Tests complete workflow: Create concept → One DB fails → Compensation triggers →
Verify rollback → Verify outbox retry.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

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
def mock_services():
    """Create all mock services needed for testing."""
    # Mock Neo4j
    neo4j_service = Mock(spec=Neo4jService)
    neo4j_service.is_connected = Mock(return_value=True)
    neo4j_service.execute_write = Mock(return_value={"nodes_created": 1, "properties_set": 5})
    neo4j_service.execute_read = Mock(return_value=[])

    # Mock ChromaDB
    chromadb_service = Mock(spec=ChromaDbService)
    chromadb_service.is_connected = Mock(return_value=True)

    mock_collection = Mock()
    mock_collection.add = Mock()
    mock_collection.update = Mock()
    mock_collection.delete = Mock()
    chromadb_service.get_collection = Mock(return_value=mock_collection)

    # Mock embedding service
    embedding_service = EmbeddingService()
    embedding_service._model_available = True
    embedding_service.model = Mock()
    embedding_service.model.encode = Mock(return_value=[[0.1] * 384])
    embedding_service.config = Mock()
    embedding_service.config.model_name = "test-model"

    return neo4j_service, chromadb_service, embedding_service


class TestEndToEndCompensation:
    """End-to-end compensation workflow tests."""

    def test_e2e_neo4j_fails_chromadb_compensated_outbox_retries(self, test_db, mock_services):
        """
        Complete E2E test:
        1. Create concept
        2. ChromaDB succeeds, Neo4j fails
        3. Compensation rolls back ChromaDB
        4. Outbox retries Neo4j
        5. Verify audit trail
        """
        conn, db_path = test_db
        neo4j_service, chromadb_service, embedding_service = mock_services

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)
        compensation_manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(neo4j_service)
        chromadb_projection = ChromaDBProjection(chromadb_service)

        # STEP 1: ChromaDB succeeds
        mock_collection = chromadb_service.get_collection()
        mock_collection.add = Mock()

        # STEP 2: Neo4j fails
        neo4j_service.execute_write = Mock(side_effect=Exception("Neo4j connection timeout"))

        # Create repository with compensation
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # STEP 3: Try to create concept
        concept_data = {
            "name": "E2E Test Concept",
            "explanation": "Testing end-to-end compensation workflow",
        }

        _success, _error, concept_id = repo.create_concept(concept_data)

        # Assertions
        assert concept_id is not None, "Concept ID should be generated"

        # STEP 4: Verify compensation audit
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT aggregate_id, event_type, target_system, success, error_message
            FROM compensation_audit
            WHERE aggregate_id = ?
        """,
            (concept_id,),
        )

        audit_records = cursor.fetchall()
        assert len(audit_records) > 0, "Compensation should be recorded in audit"

        # Verify ChromaDB was rolled back
        chromadb_rollbacks = [r for r in audit_records if r[2] == "chromadb"]
        assert len(chromadb_rollbacks) > 0, "ChromaDB rollback should be attempted"

        # STEP 5: Verify outbox has entry for retry
        cursor.execute(
            """
            SELECT projection_name, status, attempts
            FROM outbox
            WHERE event_id IN (
                SELECT event_id FROM events WHERE aggregate_id = ?
            )
        """,
            (concept_id,),
        )

        outbox_entries = cursor.fetchall()

        # Should have outbox entries for failed projections
        neo4j_entries = [e for e in outbox_entries if e[0] == "neo4j"]
        assert len(neo4j_entries) > 0, "Neo4j should be in outbox for retry"

        # STEP 6: Verify compensation stats
        stats = compensation_manager.get_stats()
        assert stats["total_compensations"] > 0
        assert "by_target" in stats
        assert stats["by_target"].get("chromadb", 0) > 0

    def test_e2e_chromadb_fails_neo4j_compensated_outbox_retries(self, test_db, mock_services):
        """
        Complete E2E test (reverse scenario):
        1. Create concept
        2. Neo4j succeeds, ChromaDB fails
        3. Compensation rolls back Neo4j
        4. Outbox retries ChromaDB
        5. Verify audit trail
        """
        conn, db_path = test_db
        neo4j_service, chromadb_service, embedding_service = mock_services

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)
        compensation_manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(neo4j_service)
        chromadb_projection = ChromaDBProjection(chromadb_service)

        # STEP 1: Neo4j succeeds
        neo4j_service.execute_write = Mock(return_value={"nodes_created": 1, "properties_set": 5})

        # STEP 2: ChromaDB fails
        chromadb_service.is_connected = Mock(return_value=False)

        # Create repository with compensation
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # STEP 3: Try to create concept
        concept_data = {
            "name": "E2E Test Concept 2",
            "explanation": "Testing reverse compensation workflow",
        }

        _success, _error, concept_id = repo.create_concept(concept_data)

        # Assertions
        assert concept_id is not None

        # STEP 4: Verify compensation audit
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT target_system, success
            FROM compensation_audit
            WHERE aggregate_id = ?
        """,
            (concept_id,),
        )

        audit_records = cursor.fetchall()

        # Verify Neo4j was rolled back
        neo4j_rollbacks = [r for r in audit_records if r[0] == "neo4j"]
        assert len(neo4j_rollbacks) > 0, "Neo4j rollback should be attempted"

        # STEP 5: Verify outbox has entry for retry
        cursor.execute(
            """
            SELECT projection_name, status
            FROM outbox
            WHERE event_id IN (
                SELECT event_id FROM events WHERE aggregate_id = ?
            )
        """,
            (concept_id,),
        )

        outbox_entries = cursor.fetchall()

        # Should have outbox entries for failed projections
        chromadb_entries = [e for e in outbox_entries if e[0] == "chromadb"]
        assert len(chromadb_entries) > 0, "ChromaDB should be in outbox for retry"

    def test_e2e_both_succeed_no_compensation(self, test_db, mock_services):
        """
        Happy path E2E test:
        1. Create concept
        2. Both Neo4j and ChromaDB succeed
        3. No compensation triggered
        4. Verify no audit records
        """
        conn, db_path = test_db
        neo4j_service, chromadb_service, embedding_service = mock_services

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)
        compensation_manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(neo4j_service)
        chromadb_projection = ChromaDBProjection(chromadb_service)

        # Both services succeed
        neo4j_service.execute_write = Mock(return_value={"nodes_created": 1})
        mock_collection = chromadb_service.get_collection()
        mock_collection.add = Mock()

        # Create repository
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Create concept
        concept_data = {"name": "Happy Path Concept", "explanation": "Everything succeeds"}

        success, error, concept_id = repo.create_concept(concept_data)

        # Assertions
        assert success is True
        assert error is None
        assert concept_id is not None

        # Verify NO compensation occurred
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM compensation_audit")
        count = cursor.fetchone()[0]
        assert count == 0, "No compensation should occur on success"

        # Verify stats show zero compensations
        stats = compensation_manager.get_stats()
        assert stats["total_compensations"] == 0

    def test_e2e_multiple_failures_audit_trail(self, test_db, mock_services):
        """
        Test multiple failures creating audit trail:
        1. Create multiple concepts with failures
        2. Verify comprehensive audit trail
        3. Verify stats accumulation
        """
        conn, db_path = test_db
        neo4j_service, chromadb_service, embedding_service = mock_services

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)
        compensation_manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(neo4j_service)
        chromadb_projection = ChromaDBProjection(chromadb_service)

        # Create repository
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Create 3 concepts with different failure patterns
        concept_ids = []

        # Concept 1: Neo4j fails
        neo4j_service.execute_write = Mock(side_effect=Exception("Neo4j fail"))
        chromadb_service.is_connected = Mock(return_value=True)
        mock_collection = chromadb_service.get_collection()
        mock_collection.add = Mock()

        _, _, cid1 = repo.create_concept({"name": "Concept 1", "explanation": "Test 1"})
        concept_ids.append(cid1)

        # Concept 2: ChromaDB fails
        neo4j_service.execute_write = Mock(return_value={"nodes_created": 1})
        chromadb_service.is_connected = Mock(return_value=False)

        _, _, cid2 = repo.create_concept({"name": "Concept 2", "explanation": "Test 2"})
        concept_ids.append(cid2)

        # Concept 3: Both succeed
        neo4j_service.execute_write = Mock(return_value={"nodes_created": 1})
        chromadb_service.is_connected = Mock(return_value=True)

        _, _, cid3 = repo.create_concept({"name": "Concept 3", "explanation": "Test 3"})
        concept_ids.append(cid3)

        # Verify comprehensive audit trail
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM compensation_audit")
        total_audits = cursor.fetchone()[0]

        assert total_audits >= 2, "Should have at least 2 compensation attempts"

        # Verify stats
        stats = compensation_manager.get_stats()
        assert stats["total_compensations"] >= 2
        assert stats["by_target"]["chromadb"] >= 1
        assert stats["by_target"]["neo4j"] >= 1

        # Verify history retrieval
        history = compensation_manager.get_compensation_history()
        assert len(history) >= 2

        # Verify filtering by aggregate
        for cid in concept_ids[:2]:  # First two had failures
            if cid:
                cid_history = compensation_manager.get_compensation_history(aggregate_id=cid)
                assert len(cid_history) >= 1

    def test_e2e_repository_stats_integration(self, test_db, mock_services):
        """
        Test that repository stats properly include compensation data:
        1. Create concepts with failures
        2. Get repository stats
        3. Verify compensation stats are included
        """
        conn, db_path = test_db
        neo4j_service, chromadb_service, embedding_service = mock_services

        # Setup services
        event_store = EventStore(db_path)
        outbox = Outbox(db_path)
        embedding_cache = EmbeddingCache(db_path)
        compensation_manager = CompensationManager(neo4j_service, chromadb_service, conn)

        # Create projections
        neo4j_projection = Neo4jProjection(neo4j_service)
        chromadb_projection = ChromaDBProjection(chromadb_service)

        # Create repository
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Create concept with failure
        neo4j_service.execute_write = Mock(side_effect=Exception("Neo4j fail"))
        chromadb_service.is_connected = Mock(return_value=True)
        mock_collection = chromadb_service.get_collection()
        mock_collection.add = Mock()

        repo.create_concept({"name": "Test", "explanation": "Test"})

        # Get repository stats
        stats = repo.get_repository_stats()

        # Verify compensation data is included
        assert "compensation_enabled" in stats
        assert stats["compensation_enabled"] is True
        assert "compensation_stats" in stats
        assert stats["compensation_stats"] is not None
        assert stats["compensation_stats"]["total_compensations"] > 0
