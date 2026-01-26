"""Tests for MCP tools"""

import asyncio

# Import all tools from tools_impl
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from short_term_mcp.database import Database
from short_term_mcp.models import ConceptStatus
from short_term_mcp.tools_impl import get_active_session_impl as get_active_session
from short_term_mcp.tools_impl import get_concepts_by_session_impl as get_concepts_by_session
from short_term_mcp.tools_impl import get_stage_data_impl as get_stage_data
from short_term_mcp.tools_impl import get_unstored_concepts_impl as get_unstored_concepts
from short_term_mcp.tools_impl import initialize_daily_session_impl as initialize_daily_session
from short_term_mcp.tools_impl import mark_concept_stored_impl as mark_concept_stored
from short_term_mcp.tools_impl import (
    normalize_optional_param,
)
from short_term_mcp.tools_impl import (
    store_concepts_from_research_impl as store_concepts_from_research,
)
from short_term_mcp.tools_impl import store_stage_data_impl as store_stage_data
from short_term_mcp.tools_impl import update_concept_status_impl as update_concept_status


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    test_db_path = Path("test_tools.db")
    db = Database(test_db_path)
    db.initialize()

    # Replace global db with test db for tools
    from short_term_mcp import database

    original_db = database._db
    database._db = db

    yield db

    # Cleanup
    database._db = original_db
    db.close()
    if test_db_path.exists():
        test_db_path.unlink()


class TestSessionTools:
    """Test session management tools"""

    @pytest.mark.asyncio
    async def test_initialize_daily_session_success(self, test_db):
        """Test creating a new session"""
        result = await initialize_daily_session(
            learning_goal="Learn React Hooks", building_goal="Build todo app", date="2025-10-09"
        )

        assert result["status"] == "success"
        assert result["session_id"] == "2025-10-09"
        assert "cleaned_old_sessions" in result

    @pytest.mark.asyncio
    async def test_initialize_daily_session_duplicate(self, test_db):
        """Test creating duplicate session returns warning"""
        # Create first session
        await initialize_daily_session(
            learning_goal="Learn React", building_goal="Build app", date="2025-10-09"
        )

        # Try to create duplicate
        result = await initialize_daily_session(
            learning_goal="Learn Vue", building_goal="Build app", date="2025-10-09"
        )

        assert result["status"] == "warning"
        assert "already exists" in result["message"]

    @pytest.mark.asyncio
    async def test_get_active_session_success(self, test_db):
        """Test retrieving active session"""
        # Create session
        await initialize_daily_session(
            learning_goal="Learn Python", building_goal="Build MCP", date="2025-10-09"
        )

        # Get session
        result = await get_active_session(date="2025-10-09")

        assert result["status"] == "success"
        assert result["session_id"] == "2025-10-09"
        assert result["learning_goal"] == "Learn Python"
        assert result["building_goal"] == "Build MCP"
        assert result["concept_count"] == 0
        assert "concepts_by_status" in result

    @pytest.mark.asyncio
    async def test_get_active_session_not_found(self, test_db):
        """Test retrieving non-existent session returns structured error"""
        result = await get_active_session(date="2025-12-31")

        assert result["status"] == "error"
        assert result["error_code"] == "SESSION_NOT_FOUND"
        assert "2025-12-31" in result["message"]


class TestConceptTools:
    """Test concept management tools"""

    @pytest.mark.asyncio
    async def test_store_concepts_from_research_success(self, test_db):
        """Test bulk storing concepts"""
        # Create session first
        await initialize_daily_session(
            learning_goal="Test", building_goal="Test", date="2025-10-09"
        )

        # Store concepts
        concepts = [{"concept_name": f"Concept {i}", "data": {"index": i}} for i in range(25)]

        result = await store_concepts_from_research(session_id="2025-10-09", concepts=concepts)

        assert result["status"] == "success"
        assert result["concepts_created"] == 25
        assert len(result["concept_ids"]) == 25

    @pytest.mark.asyncio
    async def test_store_concepts_session_not_found(self, test_db):
        """Test storing concepts with invalid session"""
        concepts = [{"concept_name": "Test", "data": {}}]

        result = await store_concepts_from_research(session_id="invalid-session", concepts=concepts)

        assert result["status"] == "error"
        assert result["error_code"] == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_concepts_by_session_all(self, test_db):
        """Test retrieving all concepts for a session"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": f"C{i}", "data": {}} for i in range(10)]
        await store_concepts_from_research("2025-10-09", concepts)

        # Get all concepts
        result = await get_concepts_by_session("2025-10-09")

        assert result["status"] == "success"
        assert result["count"] == 10
        assert len(result["concepts"]) == 10

    @pytest.mark.asyncio
    async def test_get_concepts_by_session_filtered(self, test_db):
        """Test retrieving concepts with status filter"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": f"C{i}", "data": {}} for i in range(10)]
        store_result = await store_concepts_from_research("2025-10-09", concepts)

        # Update some to chunked
        for concept_id in store_result["concept_ids"][:5]:
            await update_concept_status(concept_id, "chunked")

        # Get only identified
        result = await get_concepts_by_session("2025-10-09", status_filter="identified")
        assert result["count"] == 5

        # Get only chunked
        result = await get_concepts_by_session("2025-10-09", status_filter="chunked")
        assert result["count"] == 5

    @pytest.mark.asyncio
    async def test_get_concepts_with_stage_data(self, test_db):
        """Test retrieving concepts with stage data included"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "TestConcept", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Add stage data
        await store_stage_data(concept_id, "aim", {"test": "aim_data"})
        await store_stage_data(concept_id, "shoot", {"test": "shoot_data"})

        # Get with stage data
        result = await get_concepts_by_session("2025-10-09", include_stage_data=True)

        assert result["count"] == 1
        concept = result["concepts"][0]
        assert "stage_data" in concept
        assert "aim" in concept["stage_data"]
        assert "shoot" in concept["stage_data"]
        assert concept["stage_data"]["aim"]["test"] == "aim_data"

    @pytest.mark.asyncio
    async def test_update_concept_status_success(self, test_db):
        """Test updating concept status"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "Test", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Update status
        result = await update_concept_status(concept_id, "chunked")

        assert result["status"] == "success"
        assert result["previous_status"] == "identified"
        assert result["new_status"] == "chunked"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_update_concept_status_invalid(self, test_db):
        """Test updating with invalid status"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "Test", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Try invalid status
        result = await update_concept_status(concept_id, "invalid_status")

        assert result["status"] == "error"
        assert result["error_code"] == "INVALID_STATUS"

    @pytest.mark.asyncio
    async def test_update_concept_status_not_found(self, test_db):
        """Test updating non-existent concept"""
        result = await update_concept_status("invalid-id", "chunked")

        assert result["status"] == "error"
        assert result["error_code"] == "CONCEPT_NOT_FOUND"


class TestStageDataTools:
    """Test stage data management tools"""

    @pytest.mark.asyncio
    async def test_store_stage_data_success(self, test_db):
        """Test storing stage data"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "Test", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Store stage data
        result = await store_stage_data(
            concept_id, "aim", {"chunks": ["chunk1", "chunk2"], "questions": ["Q1", "Q2"]}
        )

        assert result["status"] == "success"
        assert result["concept_id"] == concept_id
        assert result["stage"] == "aim"
        assert "data_id" in result

    @pytest.mark.asyncio
    async def test_store_stage_data_upsert(self, test_db):
        """Test UPSERT behavior of stage data"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "Test", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Store initial data
        await store_stage_data(concept_id, "aim", {"version": 1})

        # Update same stage
        await store_stage_data(concept_id, "aim", {"version": 2})

        # Verify updated
        result = await get_stage_data(concept_id, "aim")
        assert result["data"]["version"] == 2

    @pytest.mark.asyncio
    async def test_get_stage_data_success(self, test_db):
        """Test retrieving stage data"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "Test", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Store and retrieve
        test_data = {"test": "data", "number": 42}
        await store_stage_data(concept_id, "shoot", test_data)
        result = await get_stage_data(concept_id, "shoot")

        assert result["status"] == "success"
        assert result["data"] == test_data
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_get_stage_data_not_found(self, test_db):
        """Test retrieving non-existent stage data"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "Test", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Get non-existent data
        result = await get_stage_data(concept_id, "aim")

        assert result["status"] == "not_found"


class TestStorageTools:
    """Test Knowledge MCP storage linking tools"""

    @pytest.mark.asyncio
    async def test_mark_concept_stored_success(self, test_db):
        """Test marking concept as stored"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "Test", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Mark as stored
        knowledge_id = "perm-12345"
        result = await mark_concept_stored(concept_id, knowledge_id)

        assert result["status"] == "success"
        assert result["concept_id"] == concept_id
        assert result["knowledge_mcp_id"] == knowledge_id
        assert "stored_at" in result

    @pytest.mark.asyncio
    async def test_mark_concept_stored_updates_status(self, test_db):
        """Test marking as stored updates status to STORED"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": "Test", "data": {}}]
        store_result = await store_concepts_from_research("2025-10-09", concepts)
        concept_id = store_result["concept_ids"][0]

        # Mark as stored
        await mark_concept_stored(concept_id, "perm-123")

        # Verify status changed to stored
        result = await get_concepts_by_session("2025-10-09")
        concept = result["concepts"][0]
        assert concept["current_status"] == "stored"
        assert concept["knowledge_mcp_id"] == "perm-123"

    @pytest.mark.asyncio
    async def test_get_unstored_concepts_empty(self, test_db):
        """Test getting unstored concepts when all are stored"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": f"C{i}", "data": {}} for i in range(5)]
        store_result = await store_concepts_from_research("2025-10-09", concepts)

        # Mark all as stored
        for i, concept_id in enumerate(store_result["concept_ids"]):
            await mark_concept_stored(concept_id, f"perm-{i}")

        # Get unstored
        result = await get_unstored_concepts("2025-10-09")

        assert result["status"] == "success"
        assert result["unstored_count"] == 0
        assert len(result["concepts"]) == 0

    @pytest.mark.asyncio
    async def test_get_unstored_concepts_partial(self, test_db):
        """Test getting unstored concepts when some are stored"""
        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": f"C{i}", "data": {}} for i in range(10)]
        store_result = await store_concepts_from_research("2025-10-09", concepts)

        # Mark only first 5 as stored
        for i, concept_id in enumerate(store_result["concept_ids"][:5]):
            await mark_concept_stored(concept_id, f"perm-{i}")

        # Get unstored
        result = await get_unstored_concepts("2025-10-09")

        assert result["status"] == "success"
        assert result["unstored_count"] == 5
        assert len(result["concepts"]) == 5


class TestIntegrationWorkflow:
    """Test complete pipeline workflows"""

    @pytest.mark.asyncio
    async def test_complete_research_to_storage_workflow(self, test_db):
        """Test full pipeline: Research → AIM → SHOOT → SKIN → Storage"""
        session_id = "2025-10-09"

        # 1. RESEARCH SESSION
        # Initialize session
        result = await initialize_daily_session(
            learning_goal="Learn React Hooks", building_goal="Build Todo App", date=session_id
        )
        assert result["status"] == "success"

        # Store concepts
        concepts = [
            {"concept_name": f"React Concept {i}", "data": {"priority": "high"}} for i in range(10)
        ]
        result = await store_concepts_from_research(session_id, concepts)
        assert result["concepts_created"] == 10
        concept_ids = result["concept_ids"]

        # 2. AIM SESSION
        # Process each concept through AIM
        for concept_id in concept_ids:
            # Store AIM data
            aim_data = {"chunk_name": "State Management", "questions": ["Why?", "How?"]}
            await store_stage_data(concept_id, "aim", aim_data)

            # Update status to chunked
            await update_concept_status(concept_id, "chunked")

        # Verify all are chunked
        result = await get_concepts_by_session(session_id, status_filter="chunked")
        assert result["count"] == 10

        # 3. SHOOT SESSION
        for concept_id in concept_ids:
            # Store SHOOT data
            shoot_data = {"self_explanation": "...", "analogies": ["..."]}
            await store_stage_data(concept_id, "shoot", shoot_data)

            # Update status to encoded
            await update_concept_status(concept_id, "encoded")

        # 4. SKIN SESSION
        for concept_id in concept_ids:
            # Store SKIN data
            skin_data = {"evaluation": "understood", "confidence": 8}
            await store_stage_data(concept_id, "skin", skin_data)

            # Update status to evaluated
            await update_concept_status(concept_id, "evaluated")

        # 5. STORING SESSION
        for i, concept_id in enumerate(concept_ids):
            await mark_concept_stored(concept_id, f"knowledge-mcp-{i}")

        # FINAL VERIFICATION
        # All concepts should be stored
        unstored = await get_unstored_concepts(session_id)
        assert unstored["unstored_count"] == 0

        # Check session stats
        session_stats = await get_active_session(session_id)
        assert session_stats["concepts_by_status"]["stored"] == 10

        # Verify stage data preserved
        result = await get_concepts_by_session(session_id, include_stage_data=True)
        concept = result["concepts"][0]
        assert "aim" in concept["stage_data"]
        assert "shoot" in concept["stage_data"]
        assert "skin" in concept["stage_data"]


class TestPerformance:
    """Test performance requirements"""

    @pytest.mark.asyncio
    async def test_batch_insert_25_concepts_performance(self, test_db):
        """Verify batch insert of 25 concepts meets <100ms target"""
        import time

        # Setup
        await initialize_daily_session("Test", "Test", "2025-10-09")

        # Prepare 25 concepts
        concepts = [{"concept_name": f"Concept {i}", "data": {"index": i}} for i in range(25)]

        # Time the batch insert
        start = time.time()
        await store_concepts_from_research("2025-10-09", concepts)
        elapsed_ms = (time.time() - start) * 1000

        # Verify performance target (10% margin for CI/CD system variability)
        assert elapsed_ms < 110, f"Batch insert took {elapsed_ms:.2f}ms (target: <110ms)"
        print(f"✅ Batch insert: {elapsed_ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_query_session_concepts_performance(self, test_db):
        """Verify query meets <50ms target"""
        import time

        # Setup with 25 concepts
        await initialize_daily_session("Test", "Test", "2025-10-09")
        concepts = [{"concept_name": f"C{i}", "data": {}} for i in range(25)]
        await store_concepts_from_research("2025-10-09", concepts)

        # Time the query
        start = time.time()
        await get_concepts_by_session("2025-10-09")
        elapsed_ms = (time.time() - start) * 1000

        # Verify performance target (10% margin for CI/CD system variability)
        assert elapsed_ms < 55, f"Query took {elapsed_ms:.2f}ms (target: <55ms)"
        print(f"✅ Query session concepts: {elapsed_ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_complete_pipeline_performance(self, test_db):
        """Verify complete pipeline completes in reasonable time"""
        import time

        session_id = "2025-10-09"
        start = time.time()

        # Run complete pipeline
        await initialize_daily_session("Test", "Test", session_id)
        concepts = [{"concept_name": f"C{i}", "data": {}} for i in range(25)]
        store_result = await store_concepts_from_research(session_id, concepts)
        concept_ids = store_result["concept_ids"]

        # Process through all stages
        for concept_id in concept_ids:
            await store_stage_data(concept_id, "aim", {})
            await update_concept_status(concept_id, "chunked")
            await store_stage_data(concept_id, "shoot", {})
            await update_concept_status(concept_id, "encoded")
            await store_stage_data(concept_id, "skin", {})
            await update_concept_status(concept_id, "evaluated")
            await mark_concept_stored(concept_id, f"perm-{concept_id}")

        elapsed = time.time() - start

        # Should complete in reasonable time (target: <5 seconds)
        assert elapsed < 5.0, f"Pipeline took {elapsed:.2f}s (target: <5s)"
        print(f"✅ Complete pipeline (25 concepts): {elapsed:.2f}s")


class TestNormalizeOptionalParam:
    """Test normalize_optional_param utility function"""

    def test_none_returns_none(self):
        """Test that None input returns None"""
        assert normalize_optional_param(None) is None

    def test_string_null_returns_none(self):
        """Test that string 'null' returns None"""
        assert normalize_optional_param("null") is None

    def test_empty_string_returns_none(self):
        """Test that empty string returns None"""
        assert normalize_optional_param("") is None

    def test_valid_string_unchanged(self):
        """Test that valid strings are returned unchanged"""
        assert normalize_optional_param("official") == "official"
        assert normalize_optional_param("development") == "development"
        assert normalize_optional_param("reference") == "reference"

    def test_zero_unchanged(self):
        """Test that zero (falsy but valid) is unchanged"""
        assert normalize_optional_param(0) == 0

    def test_false_unchanged(self):
        """Test that False (falsy but valid) is unchanged"""
        assert normalize_optional_param(False) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
