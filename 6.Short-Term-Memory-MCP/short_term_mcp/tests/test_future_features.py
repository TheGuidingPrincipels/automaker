"""
Test suite for Phase 6: Future Features
- User questions on concepts
- Single-page concept view
- Concept relationships
"""

import uuid
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio

from short_term_mcp import tools_impl
from short_term_mcp.database import Database
from short_term_mcp.models import Concept, ConceptStatus, Session, SessionStatus, Stage


@pytest.fixture
def test_db():
    """Create a fresh test database for each test"""
    db_path = Path("test_future_features.db")
    if db_path.exists():
        db_path.unlink()

    db = Database(db_path)
    db.initialize()

    # Replace global db with test db for tools
    from short_term_mcp import database

    original_db = database._db
    database._db = db

    yield db

    # Cleanup
    database._db = original_db
    db.close()

    if db_path.exists():
        db_path.unlink()


@pytest_asyncio.fixture
async def setup_session_with_concepts(test_db):
    """Create a session with 5 test concepts"""
    session_id = "2025-10-10"
    session = Session(
        session_id=session_id,
        date=session_id,
        learning_goal="Test React Hooks",
        building_goal="Build todo app",
    )
    test_db.create_session(session)

    concept_ids = []
    for i in range(5):
        concept_id = f"concept-{i}"
        concept = Concept(
            concept_id=concept_id,
            session_id=session_id,
            concept_name=f"Concept {i}",
            current_status=ConceptStatus.IDENTIFIED,
            current_data={"index": i, "category": "React"},
        )
        test_db.create_concept(concept)
        concept_ids.append(concept_id)

    return session_id, concept_ids


# =============================================================================
# Test Class 1: Add Concept Question
# =============================================================================


class TestAddConceptQuestion:
    """Test adding questions to concepts"""

    @pytest.mark.asyncio
    async def test_add_question_success(self, test_db, setup_session_with_concepts):
        """Test successfully adding a question to a concept"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        result = await tools_impl.add_concept_question_impl(
            concept_id=concept_id, question="Why is this important?", session_stage="research"
        )

        assert result["status"] == "success"
        assert result["concept_id"] == concept_id
        assert result["question_added"] == "Why is this important?"
        assert result["total_questions"] == 1
        assert len(result["all_questions"]) == 1
        assert result["all_questions"][0]["question"] == "Why is this important?"
        assert result["all_questions"][0]["session_stage"] == "research"
        assert result["all_questions"][0]["answered"] is False

    @pytest.mark.asyncio
    async def test_add_multiple_questions(self, test_db, setup_session_with_concepts):
        """Test adding multiple questions to the same concept"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        questions = [
            ("Why is this used?", "research"),
            ("How does it work?", "aim"),
            ("When should I use it?", "shoot"),
        ]

        for question, stage in questions:
            await tools_impl.add_concept_question_impl(
                concept_id=concept_id, question=question, session_stage=stage
            )

        # Get final result
        result = await tools_impl.add_concept_question_impl(
            concept_id=concept_id, question="What are alternatives?", session_stage="skin"
        )

        assert result["status"] == "success"
        assert result["total_questions"] == 4
        assert len(result["all_questions"]) == 4

    @pytest.mark.asyncio
    async def test_add_question_invalid_concept(self, test_db):
        """Test adding question to non-existent concept"""
        result = await tools_impl.add_concept_question_impl(
            concept_id="nonexistent", question="Test question", session_stage="research"
        )

        assert result["status"] == "error"
        assert result["error_code"] == "CONCEPT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_question_invalid_stage(self, test_db, setup_session_with_concepts):
        """Test adding question with invalid stage"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        result = await tools_impl.add_concept_question_impl(
            concept_id=concept_id, question="Test question", session_stage="invalid_stage"
        )

        assert result["status"] == "error"
        assert result["error_code"] == "INVALID_STAGE"

    @pytest.mark.asyncio
    async def test_question_metadata(self, test_db, setup_session_with_concepts):
        """Test that question metadata is correctly stored"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        before_time = datetime.now().isoformat()

        result = await tools_impl.add_concept_question_impl(
            concept_id=concept_id, question="Test question", session_stage="aim"
        )

        after_time = datetime.now().isoformat()

        assert result["status"] == "success"
        question = result["all_questions"][0]
        assert question["answered"] is False
        assert question["answer"] is None
        assert before_time <= question["asked_at"] <= after_time


# =============================================================================
# Test Class 2: Get Concept Page
# =============================================================================


class TestGetConceptPage:
    """Test single-page concept view"""

    @pytest.mark.asyncio
    async def test_concept_page_basic(self, test_db, setup_session_with_concepts):
        """Test getting basic concept page"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        result = await tools_impl.get_concept_page_impl(concept_id)

        assert result["status"] == "success"
        assert result["concept_id"] == concept_id
        assert result["concept_name"] == "Concept 0"
        assert result["session_id"] == session_id
        assert result["current_status"] == "identified"
        assert "timeline" in result
        assert "stage_data" in result
        assert "user_questions" in result
        assert "relationships" in result

    @pytest.mark.asyncio
    async def test_concept_page_with_stage_data(self, test_db, setup_session_with_concepts):
        """Test concept page includes all stage data"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        # Add stage data
        test_db.store_stage_data(concept_id, Stage.RESEARCH, {"source": "docs"})
        test_db.store_stage_data(concept_id, Stage.AIM, {"chunks": [1, 2, 3]})
        test_db.store_stage_data(concept_id, Stage.SHOOT, {"encoding": "test"})

        result = await tools_impl.get_concept_page_impl(concept_id)

        assert result["status"] == "success"
        assert "research" in result["stage_data"]
        assert "aim" in result["stage_data"]
        assert "shoot" in result["stage_data"]
        assert result["stage_data"]["research"]["data"]["source"] == "docs"
        assert result["stage_data"]["aim"]["data"]["chunks"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_concept_page_with_questions(self, test_db, setup_session_with_concepts):
        """Test concept page includes questions"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        # Add questions
        await tools_impl.add_concept_question_impl(concept_id, "Q1?", "research")
        await tools_impl.add_concept_question_impl(concept_id, "Q2?", "aim")

        result = await tools_impl.get_concept_page_impl(concept_id)

        assert result["status"] == "success"
        assert result["question_count"] == 2
        assert len(result["user_questions"]) == 2

    @pytest.mark.asyncio
    async def test_concept_page_timeline(self, test_db, setup_session_with_concepts):
        """Test concept page timeline shows status progression"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        # Progress through stages
        test_db.update_concept_status(concept_id, ConceptStatus.CHUNKED)
        test_db.update_concept_status(concept_id, ConceptStatus.ENCODED)
        test_db.update_concept_status(concept_id, ConceptStatus.EVALUATED)

        result = await tools_impl.get_concept_page_impl(concept_id)

        assert result["status"] == "success"
        assert len(result["timeline"]) == 4  # identified, chunked, encoded, evaluated
        assert result["timeline"][0]["status"] == "identified"
        assert result["timeline"][1]["status"] == "chunked"
        assert result["timeline"][2]["status"] == "encoded"
        assert result["timeline"][3]["status"] == "evaluated"

    @pytest.mark.asyncio
    async def test_concept_page_nonexistent(self, test_db):
        """Test getting page for non-existent concept"""
        result = await tools_impl.get_concept_page_impl("nonexistent")

        assert result["status"] == "error"
        assert result["error_code"] == "CONCEPT_NOT_FOUND"


# =============================================================================
# Test Class 3: Add Concept Relationship
# =============================================================================


class TestAddConceptRelationship:
    """Test adding relationships between concepts"""

    @pytest.mark.asyncio
    async def test_add_relationship_success(self, test_db, setup_session_with_concepts):
        """Test successfully adding a relationship"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]
        related_id = concept_ids[1]

        result = await tools_impl.add_concept_relationship_impl(
            concept_id=concept_id, related_concept_id=related_id, relationship_type="prerequisite"
        )

        assert result["status"] == "success"
        assert result["concept_id"] == concept_id
        assert result["related_to"]["concept_id"] == related_id
        assert result["related_to"]["relationship_type"] == "prerequisite"
        assert result["total_relationships"] == 1

    @pytest.mark.asyncio
    async def test_add_multiple_relationships(self, test_db, setup_session_with_concepts):
        """Test adding multiple relationships to one concept"""
        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        relationships = [
            (concept_ids[1], "prerequisite"),
            (concept_ids[2], "related"),
            (concept_ids[3], "similar"),
            (concept_ids[4], "builds_on"),
        ]

        for related_id, rel_type in relationships:
            result = await tools_impl.add_concept_relationship_impl(
                concept_id=concept_id, related_concept_id=related_id, relationship_type=rel_type
            )
            assert result["status"] == "success"

        # Check final count
        result = test_db.get_concept(concept_id)
        relationships_data = result["current_data"].get("relationships", [])
        assert len(relationships_data) == 4

    @pytest.mark.asyncio
    async def test_add_relationship_invalid_type(self, test_db, setup_session_with_concepts):
        """Test adding relationship with invalid type"""
        session_id, concept_ids = setup_session_with_concepts

        result = await tools_impl.add_concept_relationship_impl(
            concept_id=concept_ids[0],
            related_concept_id=concept_ids[1],
            relationship_type="invalid_type",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "INVALID_RELATIONSHIP_TYPE"

    @pytest.mark.asyncio
    async def test_add_duplicate_relationship(self, test_db, setup_session_with_concepts):
        """Test adding duplicate relationship (should warn)"""
        session_id, concept_ids = setup_session_with_concepts

        # Add first relationship
        await tools_impl.add_concept_relationship_impl(
            concept_id=concept_ids[0],
            related_concept_id=concept_ids[1],
            relationship_type="related",
        )

        # Try to add same relationship again
        result = await tools_impl.add_concept_relationship_impl(
            concept_id=concept_ids[0],
            related_concept_id=concept_ids[1],
            relationship_type="related",
        )

        assert result["status"] == "warning"

    @pytest.mark.asyncio
    async def test_add_relationship_nonexistent_concept(self, test_db, setup_session_with_concepts):
        """Test adding relationship with non-existent concept"""
        session_id, concept_ids = setup_session_with_concepts

        result = await tools_impl.add_concept_relationship_impl(
            concept_id="nonexistent", related_concept_id=concept_ids[0], relationship_type="related"
        )

        assert result["status"] == "error"
        assert result["error_code"] == "CONCEPT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_relationship_nonexistent_related(self, test_db, setup_session_with_concepts):
        """Test adding relationship to non-existent related concept"""
        session_id, concept_ids = setup_session_with_concepts

        result = await tools_impl.add_concept_relationship_impl(
            concept_id=concept_ids[0], related_concept_id="nonexistent", relationship_type="related"
        )

        assert result["status"] == "error"
        assert result["error_code"] == "RELATED_CONCEPT_NOT_FOUND"


# =============================================================================
# Test Class 4: Get Related Concepts
# =============================================================================


class TestGetRelatedConcepts:
    """Test querying related concepts"""

    @pytest.mark.asyncio
    async def test_get_related_concepts_basic(self, test_db, setup_session_with_concepts):
        """Test getting related concepts"""
        session_id, concept_ids = setup_session_with_concepts

        # Add relationships
        await tools_impl.add_concept_relationship_impl(
            concept_ids[0], concept_ids[1], "prerequisite"
        )
        await tools_impl.add_concept_relationship_impl(concept_ids[0], concept_ids[2], "related")

        result = await tools_impl.get_related_concepts_impl(concept_ids[0])

        assert result["status"] == "success"
        assert result["related_count"] == 2
        assert len(result["related_concepts"]) == 2

    @pytest.mark.asyncio
    async def test_get_related_concepts_filtered(self, test_db, setup_session_with_concepts):
        """Test filtering related concepts by type"""
        session_id, concept_ids = setup_session_with_concepts

        # Add relationships of different types
        await tools_impl.add_concept_relationship_impl(
            concept_ids[0], concept_ids[1], "prerequisite"
        )
        await tools_impl.add_concept_relationship_impl(concept_ids[0], concept_ids[2], "related")
        await tools_impl.add_concept_relationship_impl(
            concept_ids[0], concept_ids[3], "prerequisite"
        )

        result = await tools_impl.get_related_concepts_impl(
            concept_ids[0], relationship_type="prerequisite"
        )

        assert result["status"] == "success"
        assert result["related_count"] == 2
        assert all(r["relationship_type"] == "prerequisite" for r in result["related_concepts"])

    @pytest.mark.asyncio
    async def test_get_related_concepts_none(self, test_db, setup_session_with_concepts):
        """Test getting related concepts when there are none"""
        session_id, concept_ids = setup_session_with_concepts

        result = await tools_impl.get_related_concepts_impl(concept_ids[0])

        assert result["status"] == "success"
        assert result["related_count"] == 0
        assert result["related_concepts"] == []

    @pytest.mark.asyncio
    async def test_get_related_concepts_enriched_data(self, test_db, setup_session_with_concepts):
        """Test that related concepts include enriched data"""
        session_id, concept_ids = setup_session_with_concepts

        # Progress one of the concepts
        test_db.update_concept_status(concept_ids[1], ConceptStatus.CHUNKED)

        # Add relationship
        await tools_impl.add_concept_relationship_impl(concept_ids[0], concept_ids[1], "related")

        result = await tools_impl.get_related_concepts_impl(concept_ids[0])

        assert result["status"] == "success"
        related = result["related_concepts"][0]
        assert related["current_status"] == "chunked"
        assert related["session_id"] == session_id
        assert "created_at" in related


# =============================================================================
# Test Class 5: Integration Tests
# =============================================================================


class TestFutureFeaturesIntegration:
    """Integration tests for all Phase 6 features"""

    @pytest.mark.asyncio
    async def test_complete_feature_workflow(self, test_db, setup_session_with_concepts):
        """Test complete workflow using all Phase 6 features"""
        session_id, concept_ids = setup_session_with_concepts

        # 1. Add questions to concepts
        await tools_impl.add_concept_question_impl(concept_ids[0], "What is this?", "research")
        await tools_impl.add_concept_question_impl(concept_ids[0], "How does it work?", "aim")

        # 2. Add relationships
        await tools_impl.add_concept_relationship_impl(
            concept_ids[0], concept_ids[1], "prerequisite"
        )
        await tools_impl.add_concept_relationship_impl(concept_ids[0], concept_ids[2], "builds_on")

        # 3. Add stage data
        test_db.store_stage_data(concept_ids[0], Stage.RESEARCH, {"notes": "test"})
        test_db.store_stage_data(concept_ids[0], Stage.AIM, {"chunks": [1, 2]})

        # 4. Progress concept
        test_db.update_concept_status(concept_ids[0], ConceptStatus.CHUNKED)

        # 5. Get complete concept page
        page = await tools_impl.get_concept_page_impl(concept_ids[0])

        assert page["status"] == "success"
        assert page["question_count"] == 2
        assert page["related_concept_count"] == 2
        assert len(page["stage_data"]) == 2
        assert len(page["timeline"]) >= 2

    @pytest.mark.asyncio
    async def test_concept_page_includes_relationships(self, test_db, setup_session_with_concepts):
        """Test that concept page includes relationship data"""
        session_id, concept_ids = setup_session_with_concepts

        # Add relationship
        await tools_impl.add_concept_relationship_impl(concept_ids[0], concept_ids[1], "related")

        # Get page
        page = await tools_impl.get_concept_page_impl(concept_ids[0])

        assert page["status"] == "success"
        assert page["related_concept_count"] == 1
        assert len(page["relationships"]) == 1
        assert page["relationships"][0]["concept_id"] == concept_ids[1]


# =============================================================================
# Test Class 6: Performance Tests
# =============================================================================


class TestFutureFeaturesPerformance:
    """Performance tests for Phase 6 features"""

    @pytest.mark.asyncio
    async def test_concept_page_load_time(self, test_db, setup_session_with_concepts):
        """Test concept page loads in <100ms"""
        import time

        session_id, concept_ids = setup_session_with_concepts
        concept_id = concept_ids[0]

        # Add data
        for i in range(5):
            await tools_impl.add_concept_question_impl(concept_id, f"Question {i}?", "research")

        for i in range(3):
            await tools_impl.add_concept_relationship_impl(
                concept_id, concept_ids[i + 1], "related"
            )

        # Measure load time
        start = time.time()
        await tools_impl.get_concept_page_impl(concept_id)
        elapsed = (time.time() - start) * 1000

        assert elapsed < 100, f"Concept page load took {elapsed}ms (target: <100ms)"

    @pytest.mark.asyncio
    async def test_add_question_performance(self, test_db, setup_session_with_concepts):
        """Test adding question is <20ms"""
        import time

        session_id, concept_ids = setup_session_with_concepts

        start = time.time()
        await tools_impl.add_concept_question_impl(concept_ids[0], "Test question?", "research")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 20, f"Add question took {elapsed}ms (target: <20ms)"

    @pytest.mark.asyncio
    async def test_relationship_query_performance(self, test_db, setup_session_with_concepts):
        """Test relationship queries are <50ms"""
        import time

        session_id, concept_ids = setup_session_with_concepts

        # Add several relationships
        for i in range(4):
            await tools_impl.add_concept_relationship_impl(
                concept_ids[0], concept_ids[i + 1], "related"
            )

        # Measure query time
        start = time.time()
        await tools_impl.get_related_concepts_impl(concept_ids[0])
        elapsed = (time.time() - start) * 1000

        assert elapsed < 50, f"Relationship query took {elapsed}ms (target: <50ms)"
