"""Comprehensive database tests for Phase 1"""

import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from short_term_mcp.database import Database, DatabaseError
from short_term_mcp.models import (
    Concept,
    ConceptStatus,
    Session,
    SessionStatus,
    Stage,
    UserQuestion,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    db_path = Path("test_temp.db")
    db = Database(db_path)
    db.initialize()
    yield db
    db.close()
    if db_path.exists():
        db_path.unlink()


class TestSchemaValidation:
    """Test Agent 1: Schema Validation"""

    def test_database_initialization(self, temp_db):
        """Test database creates all tables"""
        cursor = temp_db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "sessions" in tables
        assert "concepts" in tables
        assert "concept_stage_data" in tables

    def test_indexes_created(self, temp_db):
        """Test all indexes are created"""
        cursor = temp_db.connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_sessions_date" in indexes
        assert "idx_sessions_status" in indexes
        assert "idx_concepts_session" in indexes
        assert "idx_concepts_status" in indexes
        assert "idx_concepts_session_status" in indexes
        assert "idx_concepts_name" in indexes
        assert "idx_stage_data_concept_stage" in indexes

    def test_wal_mode_enabled(self, temp_db):
        """Test WAL mode is enabled"""
        cursor = temp_db.connection.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

    def test_foreign_key_constraints(self, temp_db):
        """Test foreign key constraints are enforced"""
        # Try to create concept without session (should fail)
        concept = Concept(
            concept_id="test-123", session_id="nonexistent-session", concept_name="Test Concept"
        )

        # Enable foreign keys
        temp_db.connection.execute("PRAGMA foreign_keys = ON")

        with pytest.raises(DatabaseError):
            temp_db.create_concept(concept)


class TestSessionOperations:
    """Test Agent 1: Session CRUD"""

    def test_create_session(self, temp_db):
        """Test session creation"""
        session = Session(
            session_id="2025-10-10",
            date="2025-10-10",
            learning_goal="Test learning",
            building_goal="Test building",
        )

        session_id = temp_db.create_session(session)
        assert session_id == "2025-10-10"

    def test_get_session(self, temp_db):
        """Test session retrieval"""
        session = Session(
            session_id="2025-10-10",
            date="2025-10-10",
            learning_goal="Test learning",
            building_goal="Test building",
        )
        temp_db.create_session(session)

        retrieved = temp_db.get_session("2025-10-10")
        assert retrieved is not None
        assert retrieved["learning_goal"] == "Test learning"
        assert retrieved["building_goal"] == "Test building"
        assert retrieved["status"] == "in_progress"

    def test_get_nonexistent_session(self, temp_db):
        """Test getting non-existent session returns None"""
        result = temp_db.get_session("2025-01-01")
        assert result is None


class TestConceptOperations:
    """Test Agent 2: Concept CRUD"""

    def test_create_concept(self, temp_db):
        """Test concept creation"""
        # Create session first
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        # Create concept
        concept = Concept(
            concept_id=str(uuid.uuid4()),
            session_id="2025-10-10",
            concept_name="Test Concept",
            current_status=ConceptStatus.IDENTIFIED,
            current_data={"test": "data"},
        )

        concept_id = temp_db.create_concept(concept)
        assert concept_id is not None

    def test_get_concept(self, temp_db):
        """Test concept retrieval"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concept = Concept(
            concept_id="test-123",
            session_id="2025-10-10",
            concept_name="Test Concept",
            current_data={"key": "value"},
        )
        temp_db.create_concept(concept)

        retrieved = temp_db.get_concept("test-123")
        assert retrieved is not None
        assert retrieved["concept_name"] == "Test Concept"
        assert retrieved["current_data"]["key"] == "value"
        assert retrieved["current_status"] == "identified"

    def test_update_concept_status(self, temp_db):
        """Test concept status update"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concept = Concept(
            concept_id="test-123", session_id="2025-10-10", concept_name="Test Concept"
        )
        temp_db.create_concept(concept)

        # Update to chunked
        success = temp_db.update_concept_status("test-123", ConceptStatus.CHUNKED)
        assert success

        updated = temp_db.get_concept("test-123")
        assert updated["current_status"] == "chunked"
        assert updated["chunked_at"] is not None

    def test_update_through_all_statuses(self, temp_db):
        """Test concept progresses through all statuses"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concept = Concept(
            concept_id="test-123", session_id="2025-10-10", concept_name="Test Concept"
        )
        temp_db.create_concept(concept)

        statuses = [
            ConceptStatus.CHUNKED,
            ConceptStatus.ENCODED,
            ConceptStatus.EVALUATED,
            ConceptStatus.STORED,
        ]

        for status in statuses:
            temp_db.update_concept_status("test-123", status)
            updated = temp_db.get_concept("test-123")
            assert updated["current_status"] == status.value
            assert updated[f"{status.value}_at"] is not None

    def test_get_concepts_by_session(self, temp_db):
        """Test getting all concepts for a session"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        # Create 5 concepts
        for i in range(5):
            concept = Concept(
                concept_id=f"concept-{i}", session_id="2025-10-10", concept_name=f"Concept {i}"
            )
            temp_db.create_concept(concept)

        concepts = temp_db.get_concepts_by_session("2025-10-10")
        assert len(concepts) == 5

    def test_get_concepts_by_status(self, temp_db):
        """Test filtering concepts by status"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        # Create 10 concepts
        for i in range(10):
            concept = Concept(
                concept_id=f"concept-{i}", session_id="2025-10-10", concept_name=f"Concept {i}"
            )
            temp_db.create_concept(concept)

        # Update first 5 to chunked
        for i in range(5):
            temp_db.update_concept_status(f"concept-{i}", ConceptStatus.CHUNKED)

        identified = temp_db.get_concepts_by_session("2025-10-10", ConceptStatus.IDENTIFIED)
        chunked = temp_db.get_concepts_by_session("2025-10-10", ConceptStatus.CHUNKED)

        assert len(identified) == 5
        assert len(chunked) == 5

    def test_concept_with_user_questions(self, temp_db):
        """Test storing and retrieving concepts with user questions"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        questions = [
            UserQuestion(
                question="Why is this important?", session_stage="research", answered=False
            ),
            UserQuestion(
                question="How does it work?",
                session_stage="aim",
                answered=True,
                answer="It works by...",
            ),
        ]

        concept = Concept(
            concept_id="test-123",
            session_id="2025-10-10",
            concept_name="Test Concept",
            user_questions=questions,
        )
        temp_db.create_concept(concept)

        retrieved = temp_db.get_concept("test-123")
        assert len(retrieved["user_questions"]) == 2
        assert retrieved["user_questions"][0]["question"] == "Why is this important?"
        assert retrieved["user_questions"][1]["answered"] is True


class TestStageDataOperations:
    """Test Agent 2: Stage Data CRUD"""

    def test_store_stage_data(self, temp_db):
        """Test storing stage-specific data"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concept = Concept(concept_id="test-123", session_id="2025-10-10", concept_name="Test")
        temp_db.create_concept(concept)

        stage_data = {"chunks": ["chunk1", "chunk2"], "questions": ["Q1", "Q2"]}
        result = temp_db.store_stage_data("test-123", Stage.AIM, stage_data)
        assert result is not None

    def test_get_stage_data(self, temp_db):
        """Test retrieving stage-specific data"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concept = Concept(concept_id="test-123", session_id="2025-10-10", concept_name="Test")
        temp_db.create_concept(concept)

        stage_data = {"chunks": ["chunk1", "chunk2"]}
        temp_db.store_stage_data("test-123", Stage.AIM, stage_data)

        retrieved = temp_db.get_stage_data("test-123", Stage.AIM)
        assert retrieved is not None
        assert retrieved["data"]["chunks"] == ["chunk1", "chunk2"]

    def test_stage_data_upsert(self, temp_db):
        """Test UPSERT functionality for stage data"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concept = Concept(concept_id="test-123", session_id="2025-10-10", concept_name="Test")
        temp_db.create_concept(concept)

        # Insert initial data
        temp_db.store_stage_data("test-123", Stage.AIM, {"version": 1})

        # Update same stage
        temp_db.store_stage_data("test-123", Stage.AIM, {"version": 2})

        retrieved = temp_db.get_stage_data("test-123", Stage.AIM)
        assert retrieved["data"]["version"] == 2

    def test_multiple_stages_same_concept(self, temp_db):
        """Test storing data for multiple stages of same concept"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concept = Concept(concept_id="test-123", session_id="2025-10-10", concept_name="Test")
        temp_db.create_concept(concept)

        # Store data for all stages
        for stage in Stage:
            temp_db.store_stage_data("test-123", stage, {"stage": stage.value})

        # Verify all stages have data
        for stage in Stage:
            retrieved = temp_db.get_stage_data("test-123", stage)
            assert retrieved["data"]["stage"] == stage.value


class TestConcurrentOperations:
    """Test Agent 3: Concurrent Operations"""

    def test_concurrent_reads(self, temp_db):
        """Test multiple concurrent reads"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        # Create 10 concepts
        for i in range(10):
            concept = Concept(
                concept_id=f"concept-{i}", session_id="2025-10-10", concept_name=f"Concept {i}"
            )
            temp_db.create_concept(concept)

        # Concurrent reads
        results = []

        def read_concepts():
            concepts = temp_db.get_concepts_by_session("2025-10-10")
            results.append(len(concepts))

        threads = [threading.Thread(target=read_concepts) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should read 10 concepts
        assert all(r == 10 for r in results)

    def test_transaction_rollback(self, temp_db):
        """Test transaction rollback on error"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        # This should fail and rollback
        try:
            with temp_db.transaction():
                # Valid insert
                temp_db.connection.execute(
                    "INSERT INTO concepts (concept_id, session_id, concept_name) VALUES (?, ?, ?)",
                    ("test-1", "2025-10-10", "Test"),
                )
                # Invalid insert (duplicate primary key)
                temp_db.connection.execute(
                    "INSERT INTO concepts (concept_id, session_id, concept_name) VALUES (?, ?, ?)",
                    ("test-1", "2025-10-10", "Test2"),
                )
        except DatabaseError:
            pass

        # Verify first insert was rolled back
        result = temp_db.get_concept("test-1")
        assert result is None


class TestPerformance:
    """Test Agent 3: Performance Benchmarks"""

    def test_database_initialization_performance(self):
        """Test database initialization is <100ms"""
        db_path = Path("test_perf.db")

        start = time.time()
        db = Database(db_path)
        db.initialize()
        elapsed = (time.time() - start) * 1000

        db.close()
        db_path.unlink()

        assert elapsed < 100, f"DB init took {elapsed:.2f}ms (target: <100ms)"

    def test_single_concept_insert_performance(self, temp_db):
        """Test single concept insert is <10ms"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concept = Concept(
            concept_id="test-perf", session_id="2025-10-10", concept_name="Performance Test"
        )

        start = time.time()
        temp_db.create_concept(concept)
        elapsed = (time.time() - start) * 1000

        assert elapsed < 10, f"Insert took {elapsed:.2f}ms (target: <10ms)"

    def test_batch_insert_performance(self, temp_db):
        """Test batch insert 25 concepts is <100ms"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        concepts = [
            Concept(
                concept_id=f"concept-{i}",
                session_id="2025-10-10",
                concept_name=f"Concept {i}",
                current_data={"index": i},
            )
            for i in range(25)
        ]

        start = time.time()
        for concept in concepts:
            temp_db.create_concept(concept)
        elapsed = (time.time() - start) * 1000

        assert elapsed < 100, f"Batch insert took {elapsed:.2f}ms (target: <100ms)"

    def test_query_performance(self, temp_db):
        """Test query session concepts is <50ms"""
        session = Session(session_id="2025-10-10", date="2025-10-10")
        temp_db.create_session(session)

        # Insert 25 concepts
        for i in range(25):
            concept = Concept(
                concept_id=f"concept-{i}", session_id="2025-10-10", concept_name=f"Concept {i}"
            )
            temp_db.create_concept(concept)

        start = time.time()
        temp_db.get_concepts_by_session("2025-10-10")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 50, f"Query took {elapsed:.2f}ms (target: <50ms)"


class TestDomainWhitelistOperations:
    """Test domain whitelist operations"""

    def test_list_all_domains_with_none(self, temp_db):
        """Test list_whitelisted_domains with None returns all domains"""
        # Get initial count (seed data)
        initial_count = len(temp_db.list_whitelisted_domains(category=None))

        # Add some test domains
        temp_db.add_domain_to_whitelist("example.com", "official", 0.95)
        temp_db.add_domain_to_whitelist("test.org", "in_depth", 0.85)
        temp_db.add_domain_to_whitelist("docs.io", "authoritative", 0.90)

        # Test with None - should return all domains (seed + new)
        domains = temp_db.list_whitelisted_domains(category=None)
        assert len(domains) == initial_count + 3
        domain_names = {d.domain for d in domains}
        assert "example.com" in domain_names
        assert "test.org" in domain_names
        assert "docs.io" in domain_names

    def test_list_domains_filtered_by_category(self, temp_db):
        """Test list_whitelisted_domains filters correctly by category"""
        # Get initial official count (seed data)
        initial_official = len(temp_db.list_whitelisted_domains(category="official"))
        initial_depth = len(temp_db.list_whitelisted_domains(category="in_depth"))

        temp_db.add_domain_to_whitelist("official1.com", "official", 0.95)
        temp_db.add_domain_to_whitelist("official2.com", "official", 0.90)
        temp_db.add_domain_to_whitelist("dev.org", "in_depth", 0.85)

        # Test filtering by "official" (seed + new)
        official_domains = temp_db.list_whitelisted_domains(category="official")
        assert len(official_domains) == initial_official + 2
        assert all(d.category == "official" for d in official_domains)

        # Test filtering by "in_depth" (seed + new)
        depth_domains = temp_db.list_whitelisted_domains(category="in_depth")
        assert len(depth_domains) == initial_depth + 1
        assert all(d.category == "in_depth" for d in depth_domains)

    def test_list_domains_no_match_for_nonexistent_category(self, temp_db):
        """Test list_whitelisted_domains returns empty for non-existent category"""
        temp_db.add_domain_to_whitelist("example.com", "official", 0.95)

        # Query with category that doesn't exist
        domains = temp_db.list_whitelisted_domains(category="nonexistent")
        assert len(domains) == 0

    def test_list_domains_explicit_none_check(self, temp_db):
        """Test that None is treated differently from empty string"""
        # Get initial count (seed data)
        initial_domains = temp_db.list_whitelisted_domains(category=None)
        initial_count = len(initial_domains)

        temp_db.add_domain_to_whitelist("test1.com", "official", 0.95)
        temp_db.add_domain_to_whitelist("test2.com", "in_depth", 0.85)

        # None should return all (initial + 2 new)
        all_domains = temp_db.list_whitelisted_domains(category=None)
        assert len(all_domains) == initial_count + 2

        # Empty string should be treated as a category filter (no matches expected)
        # This tests that we're using 'if category is not None:' not 'if category:'
        # Currently FAILS because 'if category:' treats "" as falsy, returning all domains
        empty_domains = temp_db.list_whitelisted_domains(category="")
        assert (
            len(empty_domains) == 0
        ), f"Expected 0 domains with empty category, got {len(empty_domains)}"
