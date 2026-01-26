"""Comprehensive integration tests for complete pipeline workflows"""

import asyncio

# Import tools
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from short_term_mcp.database import Database
from short_term_mcp.models import ConceptStatus, Stage
from short_term_mcp.tests.fixtures.mock_data import (
    AIM_OUTPUT,
    ERROR_SCENARIOS,
    RESEARCH_OUTPUT,
    SHOOT_OUTPUT,
    SKIN_OUTPUT,
)
from short_term_mcp.tools_impl import get_active_session_impl as get_active_session
from short_term_mcp.tools_impl import get_concepts_by_session_impl as get_concepts_by_session
from short_term_mcp.tools_impl import get_stage_data_impl as get_stage_data
from short_term_mcp.tools_impl import get_unstored_concepts_impl as get_unstored_concepts
from short_term_mcp.tools_impl import initialize_daily_session_impl as initialize_daily_session
from short_term_mcp.tools_impl import mark_concept_stored_impl as mark_concept_stored
from short_term_mcp.tools_impl import (
    store_concepts_from_research_impl as store_concepts_from_research,
)
from short_term_mcp.tools_impl import store_stage_data_impl as store_stage_data
from short_term_mcp.tools_impl import update_concept_status_impl as update_concept_status


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    test_db_path = Path("test_integration.db")
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


class TestResearchToAIMFlow:
    """Test Research → AIM pipeline stage transition"""

    @pytest.mark.asyncio
    async def test_research_session_creates_concepts(self, test_db):
        """Test Research session stores all identified concepts"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Initialize session
        result = await initialize_daily_session(
            learning_goal=RESEARCH_OUTPUT["learning_goal"],
            building_goal=RESEARCH_OUTPUT["building_goal"],
            date=session_id,
        )
        assert result["status"] == "success"

        # Store all 25 concepts
        result = await store_concepts_from_research(session_id, RESEARCH_OUTPUT["concepts"])
        assert result["status"] == "success"
        assert result["concepts_created"] == 25

        # Verify all are in 'identified' status
        result = await get_concepts_by_session(session_id)
        assert result["count"] == 25
        assert all(c["current_status"] == "identified" for c in result["concepts"])

    @pytest.mark.asyncio
    async def test_aim_session_loads_identified_concepts(self, test_db):
        """Test AIM session can load all identified concepts from Research"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Setup Research session
        await initialize_daily_session(
            RESEARCH_OUTPUT["learning_goal"], RESEARCH_OUTPUT["building_goal"], session_id
        )
        await store_concepts_from_research(session_id, RESEARCH_OUTPUT["concepts"])

        # AIM session: Load identified concepts
        result = await get_concepts_by_session(session_id, status_filter="identified")
        assert result["status"] == "success"
        assert result["count"] == 25

        # Verify concept data is preserved
        concepts = result["concepts"]
        assert concepts[0]["concept_name"] == "useState Hook"
        assert concepts[0]["current_data"]["area"] == "Frontend"

    @pytest.mark.asyncio
    async def test_aim_chunking_workflow(self, test_db):
        """Test complete AIM chunking workflow"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Setup Research output
        await initialize_daily_session(
            RESEARCH_OUTPUT["learning_goal"], RESEARCH_OUTPUT["building_goal"], session_id
        )
        store_result = await store_concepts_from_research(session_id, RESEARCH_OUTPUT["concepts"])
        concept_ids = store_result["concept_ids"]

        # Process through AIM: chunk by groups of 5
        chunks_processed = 0
        for i in range(0, 25, 5):
            chunk = AIM_OUTPUT["chunks"][chunks_processed]
            chunk_concepts = concept_ids[i : i + 5]

            for concept_id in chunk_concepts:
                # Store AIM data
                aim_data = {
                    "chunk_name": chunk["chunk_name"],
                    "questions": chunk["questions"],
                    "priority": chunk["priority"],
                }
                result = await store_stage_data(concept_id, "aim", aim_data)
                assert result["status"] == "success"

                # Update status to chunked
                result = await update_concept_status(concept_id, "chunked")
                assert result["status"] == "success"

            chunks_processed += 1

        # Verify all concepts are chunked
        result = await get_concepts_by_session(session_id, status_filter="chunked")
        assert result["count"] == 25

        # Verify no concepts remain identified
        result = await get_concepts_by_session(session_id, status_filter="identified")
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_aim_stage_data_preserved(self, test_db):
        """Test AIM stage data is preserved and retrievable"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Setup
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:5]
        )
        concept_id = store_result["concept_ids"][0]

        # Store AIM data
        aim_data = {
            "chunk_name": "State Hooks",
            "questions": ["Why?", "How?", "When?"],
            "priority": "high",
            "estimated_time_minutes": 30,
        }
        await store_stage_data(concept_id, "aim", aim_data)

        # Retrieve and verify
        result = await get_stage_data(concept_id, "aim")
        assert result["status"] == "success"
        assert result["data"]["chunk_name"] == "State Hooks"
        assert len(result["data"]["questions"]) == 3
        assert result["data"]["priority"] == "high"


class TestAIMToSHOOTFlow:
    """Test AIM → SHOOT pipeline stage transition"""

    @pytest.mark.asyncio
    async def test_shoot_loads_chunked_concepts(self, test_db):
        """Test SHOOT session loads concepts with chunked status"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Setup: Research + AIM complete
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:10]
        )

        # Process through AIM
        for concept_id in store_result["concept_ids"]:
            await store_stage_data(concept_id, "aim", {"chunk": "test"})
            await update_concept_status(concept_id, "chunked")

        # SHOOT session: Load chunked concepts
        result = await get_concepts_by_session(session_id, status_filter="chunked")
        assert result["count"] == 10
        assert all(c["current_status"] == "chunked" for c in result["concepts"])

    @pytest.mark.asyncio
    async def test_shoot_encoding_workflow(self, test_db):
        """Test SHOOT encoding workflow with self-explanations"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Setup: Research + AIM
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:3]
        )
        concept_ids = store_result["concept_ids"]

        # Process through AIM
        for concept_id in concept_ids:
            await store_stage_data(concept_id, "aim", {})
            await update_concept_status(concept_id, "chunked")

        # Process through SHOOT
        for i, concept_id in enumerate(concept_ids):
            encoding = SHOOT_OUTPUT["encodings"][i]
            shoot_data = {
                "self_explanation": encoding["self_explanation"],
                "difficulty": encoding["difficulty"],
                "analogies": encoding["analogies"],
                "examples": encoding["examples"],
                "confidence": encoding["confidence"],
            }

            result = await store_stage_data(concept_id, "shoot", shoot_data)
            assert result["status"] == "success"

            result = await update_concept_status(concept_id, "encoded")
            assert result["status"] == "success"

        # Verify all encoded
        result = await get_concepts_by_session(session_id, status_filter="encoded")
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_shoot_stage_data_includes_aim_data(self, test_db):
        """Test concepts retain AIM data when moving to SHOOT"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Setup
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:1]
        )
        concept_id = store_result["concept_ids"][0]

        # AIM stage
        aim_data = {"chunk_name": "Test Chunk", "questions": ["Q1"]}
        await store_stage_data(concept_id, "aim", aim_data)
        await update_concept_status(concept_id, "chunked")

        # SHOOT stage
        shoot_data = {"self_explanation": "Test explanation"}
        await store_stage_data(concept_id, "shoot", shoot_data)
        await update_concept_status(concept_id, "encoded")

        # Verify both stage data exist
        result = await get_concepts_by_session(session_id, include_stage_data=True)
        concept = result["concepts"][0]
        assert "stage_data" in concept
        assert "aim" in concept["stage_data"]
        assert "shoot" in concept["stage_data"]
        assert concept["stage_data"]["aim"]["chunk_name"] == "Test Chunk"
        assert concept["stage_data"]["shoot"]["self_explanation"] == "Test explanation"


class TestSHOOTToSKINFlow:
    """Test SHOOT → SKIN pipeline stage transition"""

    @pytest.mark.asyncio
    async def test_skin_loads_encoded_concepts(self, test_db):
        """Test SKIN session loads encoded concepts"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Setup: Research + AIM + SHOOT complete
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:5]
        )

        # Process through AIM and SHOOT
        for concept_id in store_result["concept_ids"]:
            await store_stage_data(concept_id, "aim", {})
            await update_concept_status(concept_id, "chunked")
            await store_stage_data(concept_id, "shoot", {})
            await update_concept_status(concept_id, "encoded")

        # SKIN session: Load encoded concepts
        result = await get_concepts_by_session(session_id, status_filter="encoded")
        assert result["count"] == 5

    @pytest.mark.asyncio
    async def test_skin_evaluation_workflow(self, test_db):
        """Test SKIN evaluation workflow"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # Setup: Research + AIM + SHOOT
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:3]
        )
        concept_ids = store_result["concept_ids"]

        # Process to encoded status
        for concept_id in concept_ids:
            await store_stage_data(concept_id, "aim", {})
            await update_concept_status(concept_id, "chunked")
            await store_stage_data(concept_id, "shoot", {})
            await update_concept_status(concept_id, "encoded")

        # Process through SKIN
        for i, concept_id in enumerate(concept_ids):
            evaluation = SKIN_OUTPUT["evaluations"][i]
            skin_data = {
                "understanding_level": evaluation["understanding_level"],
                "confidence_score": evaluation["confidence_score"],
                "can_explain": evaluation["can_explain"],
                "can_implement": evaluation["can_implement"],
                "remaining_confusion": evaluation["remaining_confusion"],
            }

            result = await store_stage_data(concept_id, "skin", skin_data)
            assert result["status"] == "success"

            result = await update_concept_status(concept_id, "evaluated")
            assert result["status"] == "success"

        # Verify all evaluated
        result = await get_concepts_by_session(session_id, status_filter="evaluated")
        assert result["count"] == 3


class TestCompletePipeline:
    """Test complete end-to-end pipeline"""

    @pytest.mark.asyncio
    async def test_complete_research_to_storage_pipeline(self, test_db):
        """Test full pipeline: Research → AIM → SHOOT → SKIN → Storage"""
        session_id = RESEARCH_OUTPUT["session_id"]

        # 1. RESEARCH SESSION
        result = await initialize_daily_session(
            learning_goal=RESEARCH_OUTPUT["learning_goal"],
            building_goal=RESEARCH_OUTPUT["building_goal"],
            date=session_id,
        )
        assert result["status"] == "success"

        # Store all 25 concepts
        result = await store_concepts_from_research(session_id, RESEARCH_OUTPUT["concepts"])
        assert result["concepts_created"] == 25
        concept_ids = result["concept_ids"]

        # 2. AIM SESSION - Chunk concepts
        for concept_id in concept_ids:
            aim_data = {"chunk_name": "Test", "questions": ["Q1"]}
            await store_stage_data(concept_id, "aim", aim_data)
            await update_concept_status(concept_id, "chunked")

        # Verify progression
        result = await get_active_session(session_id)
        assert result["concepts_by_status"]["chunked"] == 25
        assert result["concepts_by_status"]["identified"] == 0

        # 3. SHOOT SESSION - Encode concepts
        for concept_id in concept_ids:
            shoot_data = {"self_explanation": "Test explanation", "difficulty": 5, "confidence": 7}
            await store_stage_data(concept_id, "shoot", shoot_data)
            await update_concept_status(concept_id, "encoded")

        # Verify progression
        result = await get_active_session(session_id)
        assert result["concepts_by_status"]["encoded"] == 25
        assert result["concepts_by_status"]["chunked"] == 0

        # 4. SKIN SESSION - Evaluate concepts
        for concept_id in concept_ids:
            skin_data = {"understanding_level": "well_understood", "confidence_score": 8}
            await store_stage_data(concept_id, "skin", skin_data)
            await update_concept_status(concept_id, "evaluated")

        # Verify progression
        result = await get_active_session(session_id)
        assert result["concepts_by_status"]["evaluated"] == 25
        assert result["concepts_by_status"]["encoded"] == 0

        # 5. STORING SESSION - Link to Knowledge MCP
        for i, concept_id in enumerate(concept_ids):
            knowledge_id = f"knowledge-mcp-{i:04d}"
            result = await mark_concept_stored(concept_id, knowledge_id)
            assert result["status"] == "success"

        # FINAL VERIFICATION
        # All concepts stored
        unstored = await get_unstored_concepts(session_id)
        assert unstored["unstored_count"] == 0

        # All have Knowledge MCP IDs
        result = await get_concepts_by_session(session_id)
        assert all(c["knowledge_mcp_id"] is not None for c in result["concepts"])

        # Session stats correct
        session_stats = await get_active_session(session_id)
        assert session_stats["concept_count"] == 25
        assert session_stats["concepts_by_status"]["stored"] == 25

    @pytest.mark.asyncio
    async def test_pipeline_with_stage_data_retrieval(self, test_db):
        """Test pipeline preserves all stage data"""
        session_id = "2025-10-10"

        # Setup and process through entire pipeline
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:5]
        )
        concept_id = store_result["concept_ids"][0]

        # Store distinct data at each stage
        await store_stage_data(concept_id, "aim", {"stage": "aim", "data": "aim_value"})
        await update_concept_status(concept_id, "chunked")

        await store_stage_data(concept_id, "shoot", {"stage": "shoot", "data": "shoot_value"})
        await update_concept_status(concept_id, "encoded")

        await store_stage_data(concept_id, "skin", {"stage": "skin", "data": "skin_value"})
        await update_concept_status(concept_id, "evaluated")

        await mark_concept_stored(concept_id, "perm-001")

        # Retrieve with all stage data
        result = await get_concepts_by_session(session_id, include_stage_data=True)
        concept = result["concepts"][0]

        # Verify all stage data preserved
        assert concept["stage_data"]["aim"]["data"] == "aim_value"
        assert concept["stage_data"]["shoot"]["data"] == "shoot_value"
        assert concept["stage_data"]["skin"]["data"] == "skin_value"
        assert concept["current_status"] == "stored"
        assert concept["knowledge_mcp_id"] == "perm-001"


class TestErrorRecovery:
    """Test error recovery and edge cases"""

    @pytest.mark.asyncio
    async def test_incomplete_session_recovery(self, test_db):
        """Test recovery from incomplete session (crashed during AIM)"""
        session_id = "2025-10-10"

        # Simulate partial session
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:20]
        )
        concept_ids = store_result["concept_ids"]

        # Only process first 12 concepts through AIM (simulating crash)
        for concept_id in concept_ids[:12]:
            await store_stage_data(concept_id, "aim", {})
            await update_concept_status(concept_id, "chunked")

        # RECOVERY: Identify unprocessed concepts
        identified = await get_concepts_by_session(session_id, status_filter="identified")
        assert identified["count"] == 8  # 20 - 12 = 8 unprocessed

        chunked = await get_concepts_by_session(session_id, status_filter="chunked")
        assert chunked["count"] == 12

        # Process remaining concepts
        for concept in identified["concepts"]:
            await store_stage_data(concept["concept_id"], "aim", {})
            await update_concept_status(concept["concept_id"], "chunked")

        # Verify recovery complete
        identified = await get_concepts_by_session(session_id, status_filter="identified")
        assert identified["count"] == 0

        chunked = await get_concepts_by_session(session_id, status_filter="chunked")
        assert chunked["count"] == 20

    @pytest.mark.asyncio
    async def test_partial_storage_detection(self, test_db):
        """Test detection of partially stored sessions"""
        session_id = "2025-10-10"

        # Setup complete pipeline
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, RESEARCH_OUTPUT["concepts"][:15]
        )
        concept_ids = store_result["concept_ids"]

        # Process all to evaluated
        for concept_id in concept_ids:
            await store_stage_data(concept_id, "aim", {})
            await update_concept_status(concept_id, "chunked")
            await store_stage_data(concept_id, "shoot", {})
            await update_concept_status(concept_id, "encoded")
            await store_stage_data(concept_id, "skin", {})
            await update_concept_status(concept_id, "evaluated")

        # Only store first 10 concepts
        for i, concept_id in enumerate(concept_ids[:10]):
            await mark_concept_stored(concept_id, f"perm-{i}")

        # Detect unstored concepts
        unstored = await get_unstored_concepts(session_id)
        assert unstored["unstored_count"] == 5
        assert len(unstored["concepts"]) == 5

        # All unstored should be in 'evaluated' status
        assert all(c["current_status"] == "evaluated" for c in unstored["concepts"])

    @pytest.mark.asyncio
    async def test_duplicate_session_handling(self, test_db):
        """Test handling of duplicate session initialization"""
        session_id = "2025-10-10"

        # Create first session
        result1 = await initialize_daily_session("Learn React", "Build App", session_id)
        assert result1["status"] == "success"

        # Try to create duplicate
        result2 = await initialize_daily_session("Learn Vue", "Build SPA", session_id)
        assert result2["status"] == "warning"
        assert "already exists" in result2["message"]

        # Original session unchanged
        session = await get_active_session(session_id)
        assert session["learning_goal"] == "Learn React"  # Original goal preserved

    @pytest.mark.asyncio
    async def test_invalid_status_transitions(self, test_db):
        """Test validation of status transitions"""
        session_id = "2025-10-10"

        # Setup
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, [{"concept_name": "Test", "data": {}}]
        )
        concept_id = store_result["concept_ids"][0]

        # Try invalid status
        result = await update_concept_status(concept_id, "invalid_status")
        assert result["status"] == "error"
        assert result["error_code"] == "INVALID_STATUS"

        # Concept status unchanged
        concepts = await get_concepts_by_session(session_id)
        assert concepts["concepts"][0]["current_status"] == "identified"

    @pytest.mark.asyncio
    async def test_missing_session_error_handling(self, test_db):
        """Test error handling for missing session"""
        # Try to store concepts in non-existent session
        result = await store_concepts_from_research(
            "non-existent-session", [{"concept_name": "Test", "data": {}}]
        )
        assert result["status"] == "error"
        assert result["error_code"] == "SESSION_NOT_FOUND"


class TestPerformanceIntegration:
    """Test performance requirements for complete pipeline"""

    @pytest.mark.asyncio
    async def test_complete_pipeline_performance(self, test_db):
        """Verify complete pipeline meets <5 second target"""
        session_id = "2025-10-10"
        start_time = time.time()

        # Run complete pipeline with 25 concepts
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(session_id, RESEARCH_OUTPUT["concepts"])
        concept_ids = store_result["concept_ids"]

        # Process through all stages
        for concept_id in concept_ids:
            # AIM
            await store_stage_data(concept_id, "aim", {"chunk": "test"})
            await update_concept_status(concept_id, "chunked")

            # SHOOT
            await store_stage_data(concept_id, "shoot", {"encoding": "test"})
            await update_concept_status(concept_id, "encoded")

            # SKIN
            await store_stage_data(concept_id, "skin", {"evaluation": "test"})
            await update_concept_status(concept_id, "evaluated")

            # STORAGE
            await mark_concept_stored(concept_id, f"perm-{concept_id}")

        elapsed = time.time() - start_time

        # Verify performance target
        assert elapsed < 5.0, f"Pipeline took {elapsed:.2f}s (target: <5s)"
        print(f"✅ Complete pipeline (25 concepts, 4 stages): {elapsed:.2f}s")

    @pytest.mark.asyncio
    async def test_database_size_reasonable(self, test_db):
        """Test database size remains reasonable after full session"""
        session_id = "2025-10-10"

        # Run complete pipeline
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(session_id, RESEARCH_OUTPUT["concepts"])

        for concept_id in store_result["concept_ids"]:
            await store_stage_data(concept_id, "aim", {"data": "x" * 100})
            await update_concept_status(concept_id, "chunked")
            await store_stage_data(concept_id, "shoot", {"data": "x" * 200})
            await update_concept_status(concept_id, "encoded")
            await store_stage_data(concept_id, "skin", {"data": "x" * 100})
            await update_concept_status(concept_id, "evaluated")
            await mark_concept_stored(concept_id, f"perm-{concept_id}")

        # Check database file size
        db_path = Path("test_integration.db")
        db_size_bytes = db_path.stat().st_size
        db_size_kb = db_size_bytes / 1024

        # Should be under 1MB for a full day's session
        assert db_size_kb < 1024, f"Database size {db_size_kb:.2f}KB exceeds 1MB limit"
        print(f"✅ Database size after full session: {db_size_kb:.2f}KB")

    @pytest.mark.asyncio
    async def test_concurrent_read_performance(self, test_db):
        """Test concurrent reads don't significantly impact performance"""
        session_id = "2025-10-10"

        # Setup session with data
        await initialize_daily_session("Learn", "Build", session_id)
        await store_concepts_from_research(session_id, RESEARCH_OUTPUT["concepts"])

        # Time concurrent reads
        start_time = time.time()

        # Simulate multiple concurrent reads
        tasks = [
            get_concepts_by_session(session_id),
            get_active_session(session_id),
            get_concepts_by_session(session_id, status_filter="identified"),
            get_concepts_by_session(session_id, include_stage_data=True),
            get_unstored_concepts(session_id),
        ]

        results = await asyncio.gather(*tasks)
        elapsed_ms = (time.time() - start_time) * 1000

        # All queries should complete quickly
        assert elapsed_ms < 200, f"Concurrent reads took {elapsed_ms:.2f}ms (target: <200ms)"
        print(f"✅ 5 concurrent reads: {elapsed_ms:.2f}ms")

        # All results should be valid
        assert all(r["status"] in ["success", "not_found"] for r in results if "status" in r)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
