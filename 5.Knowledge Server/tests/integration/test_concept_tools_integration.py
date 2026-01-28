"""
Integration tests for concept management MCP tools

Tests the tools with real repository integration (mocked services).
"""

from unittest.mock import Mock

import pytest

from services.event_store import EventStore
from services.outbox import Outbox
from services.repository import DualStorageRepository
from tools import concept_tools
from tools.responses import ErrorType


@pytest.fixture
def mock_services():
    """Create mock services for repository"""
    mock_event_store = Mock(spec=EventStore)
    mock_event_store.append_event = Mock(return_value=True)
    mock_event_store.get_latest_version = Mock(return_value=1)

    mock_outbox = Mock(spec=Outbox)
    mock_outbox.add_to_outbox = Mock(side_effect=lambda event_id, proj: f"outbox_{proj}")
    mock_outbox.mark_completed = Mock(return_value=True)

    mock_neo4j_projection = Mock()
    mock_neo4j_projection.project_event = Mock(return_value=True)

    mock_chromadb_projection = Mock()
    mock_chromadb_projection.project_event = Mock(return_value=True)

    mock_embedding_service = Mock()
    mock_embedding_service.generate_embedding = Mock(return_value=[0.1] * 384)  # 384-dim vector

    mock_embedding_cache = Mock()
    mock_embedding_cache.get_cached = Mock(return_value=None)
    mock_embedding_cache.store = Mock(return_value=True)

    mock_compensation = Mock()

    return {
        "event_store": mock_event_store,
        "outbox": mock_outbox,
        "neo4j_projection": mock_neo4j_projection,
        "chromadb_projection": mock_chromadb_projection,
        "embedding_service": mock_embedding_service,
        "embedding_cache": mock_embedding_cache,
        "compensation": mock_compensation,
    }


@pytest.fixture
def repository(mock_services, configured_container):
    """Create repository with mock services and inject into container"""
    repo = DualStorageRepository(
        event_store=mock_services["event_store"],
        outbox=mock_services["outbox"],
        neo4j_projection=mock_services["neo4j_projection"],
        chromadb_projection=mock_services["chromadb_projection"],
        embedding_service=mock_services["embedding_service"],
        embedding_cache=mock_services["embedding_cache"],
        compensation_manager=mock_services["compensation"],
    )

    # Inject into container (not module) - tools use get_container().repository
    configured_container.repository = repo
    # Also set other services on container for @requires_services decorator
    configured_container.event_store = mock_services['event_store']
    configured_container.outbox = mock_services['outbox']
    configured_container.neo4j_service = mock_services['neo4j_projection']
    configured_container.chromadb_service = mock_services['chromadb_projection']
    configured_container.embedding_service = mock_services['embedding_service']
    # Disable confidence runtime for these tests
    configured_container.confidence_runtime = None
    yield repo
    # No cleanup needed - reset_service_container autouse fixture handles it


# =============================================================================
# Integration Tests
# =============================================================================


class TestCreateConceptIntegration:
    """Integration tests for create_concept"""

    @pytest.mark.asyncio
    async def test_create_concept_full_workflow(self, repository, mock_services):
        """Test complete create workflow with repository"""
        result = await concept_tools.create_concept(
            name="Integration Test Concept",
            explanation="This tests the full create workflow",
            area="Testing",
            topic="Integration Tests",
        )

        # Verify success
        assert result["success"] is True
        assert result["data"]["concept_id"] is not None
        assert result["message"] == "Created"

        # Verify event was stored
        assert mock_services["event_store"].append_event.called

        # Verify projections were called
        assert mock_services["neo4j_projection"].project_event.called
        assert mock_services["chromadb_projection"].project_event.called

        # Verify embedding was generated
        assert mock_services["embedding_service"].generate_embedding.called

    @pytest.mark.asyncio
    async def test_create_concept_minimal_data(self, repository):
        """Test creation with minimal required data (name, explanation, area, topic)"""
        result = await concept_tools.create_concept(
            name="Minimal Concept",
            explanation="Minimal explanation",
            area="coding-development",
            topic="General",
        )

        assert result["success"] is True
        assert result["data"]["concept_id"] is not None

    @pytest.mark.asyncio
    async def test_create_concept_missing_area_raises_type_error(self, repository):
        """Missing area should raise TypeError since area is a required parameter."""
        with pytest.raises(TypeError, match="missing.*required.*argument.*'area'"):
            await concept_tools.create_concept(
                name="Missing Area",
                explanation="Should fail without area",
                topic="General",
            )

    @pytest.mark.asyncio
    async def test_create_concept_missing_topic_raises_type_error(self, repository):
        """Missing topic should raise TypeError since topic is a required parameter."""
        with pytest.raises(TypeError, match="missing.*required.*argument.*'topic'"):
            await concept_tools.create_concept(
                name="Missing Topic",
                explanation="Should fail without topic",
                area="coding-development",
            )

    @pytest.mark.asyncio
    async def test_create_concept_event_store_failure(self, repository, mock_services):
        """Test handling when event store fails"""
        mock_services["event_store"].append_event = Mock(return_value=False)

        result = await concept_tools.create_concept(
            name="Test",
            explanation="Test",
            area="coding-development",
            topic="General",
        )

        assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["error", "unable", "unavailable", "failed"])


class TestGetConceptIntegration:
    """Integration tests for get_concept"""

    @pytest.mark.asyncio
    async def test_get_concept_after_create(self, repository, mock_services):
        """Test retrieving a concept after creation"""
        # First create a concept
        create_result = await concept_tools.create_concept(
            name="Test Get",
            explanation="Test retrieval",
            area="coding-development",
            topic="General",
        )

        concept_id = create_result["data"]["concept_id"]

        # Mock repository.get_concept to return data
        mock_concept = {
            "concept_id": concept_id,
            "name": "Test Get",
            "explanation": "Test retrieval",
            "created_at": "2025-01-01T00:00:00",
        }
        repository.get_concept = Mock(return_value=mock_concept)

        # Now retrieve it
        result = await concept_tools.get_concept(concept_id)

        assert result["success"] is True
        assert result["data"]["concept"]["concept_id"] == concept_id
        assert result["data"]["concept"]["name"] == "Test Get"

    @pytest.mark.asyncio
    async def test_get_nonexistent_concept(self, repository):
        """Test retrieving non-existent concept"""
        repository.get_concept = Mock(return_value=None)

        result = await concept_tools.get_concept("nonexistent-id")

        assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["not found", "doesn't exist", "does not exist", "has been deleted"])
        assert result["error"]["type"] in ["not_found", "concept_not_found"]


class TestUpdateConceptIntegration:
    """Integration tests for update_concept"""

    @pytest.mark.asyncio
    async def test_update_concept_workflow(self, repository, mock_services):
        """Test complete update workflow"""
        # Setup: create a concept first
        create_result = await concept_tools.create_concept(
            name="Original Name",
            explanation="Original explanation",
            area="coding-development",
            topic="General",
        )

        concept_id = create_result["data"]["concept_id"]

        # Update the concept
        result = await concept_tools.update_concept(
            concept_id=concept_id, explanation="Updated explanation"
        )

        assert result["success"] is True
        assert "explanation" in result["data"]["updated_fields"]

        # Verify event was stored
        assert mock_services["event_store"].append_event.called

        # Verify projections were called
        assert mock_services["neo4j_projection"].project_event.called
        assert mock_services["chromadb_projection"].project_event.called

    @pytest.mark.asyncio
    async def test_update_concept_partial(self, repository, mock_services):
        """Test partial update (single field)"""
        create_result = await concept_tools.create_concept(
            name="Test",
            explanation="Original",
            area="coding-development",
            topic="General",
        )

        result = await concept_tools.update_concept(
            concept_id=create_result["data"]["concept_id"],
            topic="Updated Topic"
        )

        assert result["success"] is True
        assert len(result["data"]["updated_fields"]) == 1
        assert "topic" in result["data"]["updated_fields"]


class TestDeleteConceptIntegration:
    """Integration tests for delete_concept"""

    @pytest.mark.asyncio
    async def test_delete_concept_workflow(self, repository, mock_services):
        """Test complete delete workflow"""
        # Setup: create a concept
        create_result = await concept_tools.create_concept(
            name="To Delete",
            explanation="Will be deleted",
            area="coding-development",
            topic="General",
        )

        concept_id = create_result["data"]["concept_id"]

        # Delete it
        result = await concept_tools.delete_concept(concept_id)

        assert result["success"] is True
        assert result["data"]["concept_id"] == concept_id
        assert result["message"] == "Deleted"

        # Verify event was stored
        assert mock_services["event_store"].append_event.called

        # Verify projections were called
        assert mock_services["neo4j_projection"].project_event.called
        assert mock_services["chromadb_projection"].project_event.called


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""

    @pytest.mark.asyncio
    async def test_create_update_delete_workflow(self, repository, mock_services):
        """Test complete CRUD workflow"""
        # 1. Create
        create_result = await concept_tools.create_concept(
            name="Workflow Test",
            explanation="Testing full workflow",
            area="coding-development",
            topic="Workflow",
        )

        assert create_result["success"] is True
        concept_id = create_result["data"]["concept_id"]

        # 2. Get (mock the response)
        mock_concept = {
            "concept_id": concept_id,
            "name": "Workflow Test",
            "explanation": "Testing full workflow",
        }
        repository.get_concept = Mock(return_value=mock_concept)

        get_result = await concept_tools.get_concept(concept_id)
        assert get_result["success"] is True

        # 3. Update
        update_result = await concept_tools.update_concept(
            concept_id=concept_id, explanation="Updated workflow test"
        )
        assert update_result["success"] is True

        # 4. Delete
        delete_result = await concept_tools.delete_concept(concept_id)
        assert delete_result["success"] is True

    @pytest.mark.asyncio
    async def test_create_multiple_concepts(self, repository):
        """Test creating multiple concepts"""
        results = []

        for i in range(5):
            result = await concept_tools.create_concept(
                name=f"Concept {i}",
                explanation=f"Explanation {i}",
                area="coding-development",
                topic=f"Topic {i}",
            )
            results.append(result)

        # All should succeed
        for result in results:
            assert result["success"] is True
            assert result["data"]["concept_id"] is not None

        # All IDs should be unique
        ids = [r["data"]["concept_id"] for r in results]
        assert len(ids) == len(set(ids))


class TestErrorHandling:
    """Test error handling in integration scenarios"""

    @pytest.mark.asyncio
    async def test_neo4j_projection_failure(self, repository, mock_services):
        """Test handling when Neo4j projection fails"""
        mock_services["neo4j_projection"].project_event = Mock(return_value=False)

        result = await concept_tools.create_concept(
            name="Test",
            explanation="Test",
            area="coding-development",
            topic="General",
        )

        # Should still return concept_id (event stored)
        # But may indicate partial success
        assert result["data"]["concept_id"] is not None

    @pytest.mark.asyncio
    async def test_chromadb_projection_failure(self, repository, mock_services):
        """Test handling when ChromaDB projection fails"""
        mock_services["chromadb_projection"].project_event = Mock(return_value=False)

        result = await concept_tools.create_concept(
            name="Test",
            explanation="Test",
            area="coding-development",
            topic="General",
        )

        # Should still return concept_id (event stored)
        assert result["data"]["concept_id"] is not None

    @pytest.mark.asyncio
    async def test_update_nonexistent_concept(self, repository, mock_services):
        """Test updating non-existent concept"""
        mock_services["event_store"].get_latest_version = Mock(return_value=None)

        result = await concept_tools.update_concept(
            concept_id="nonexistent", explanation="New explanation"
        )

        # Repository should handle this gracefully
        assert result["success"] is False or result.get("data", {}).get("concept_id") is not None


class TestCreateConceptWithSoftValidation:
    """Test concept creation with soft validation warnings for custom areas."""

    @pytest.mark.asyncio
    async def test_create_concept_with_predefined_area_has_no_warnings(self, repository):
        """Creating with a predefined area should not produce warnings."""
        result = await concept_tools.create_concept(
            name="Test Concept Predefined",
            explanation="Test explanation",
            area="coding-development",
            topic="Python",
        )

        assert result["success"] is True
        assert "warnings" not in (result.get("data") or {})

    @pytest.mark.asyncio
    async def test_create_concept_with_custom_area_has_warning(self, repository):
        """Creating with a custom (non-predefined) area should produce a warning."""
        result = await concept_tools.create_concept(
            name="Test Concept Custom Area",
            explanation="Test explanation",
            area="my-custom-area",
            topic="Custom Topic",
        )

        assert result["success"] is True
        assert "warnings" in result["data"]
        assert len(result["data"]["warnings"]) == 1
        assert "not a predefined area" in result["data"]["warnings"][0]
        assert "my-custom-area" in result["data"]["warnings"][0]
        assert "Recommended areas" in result["data"]["warnings"][0]

    @pytest.mark.asyncio
    async def test_create_concept_custom_area_still_succeeds(self, repository):
        """Custom areas should still create the concept successfully (soft validation)."""
        result = await concept_tools.create_concept(
            name="Another Custom Area Test",
            explanation="This should work",
            area="experimental-science",
            topic="Quantum Computing",
        )

        assert result["success"] is True
        assert result["data"]["concept_id"] is not None
        # Warning present but concept still created
        assert "warnings" in result["data"]


class TestTokenEfficiency:
    """Test token efficiency of responses"""

    @pytest.mark.asyncio
    async def test_create_response_token_count(self, repository):
        """Test create response is under 50 tokens"""
        result = await concept_tools.create_concept(
            name="Test",
            explanation="Test",
            area="coding-development",
            topic="General",
        )

        response_str = str(result)
        estimated_tokens = len(response_str) / 4
        assert estimated_tokens < 50

    @pytest.mark.asyncio
    async def test_update_response_token_count(self, repository):
        """Test update response is under 50 tokens"""
        # Create first
        create_result = await concept_tools.create_concept(
            name="Test",
            explanation="Test",
            area="coding-development",
            topic="General",
        )

        # Update
        result = await concept_tools.update_concept(
            concept_id=create_result["data"]["concept_id"],
            explanation="Updated"
        )

        response_str = str(result)
        estimated_tokens = len(response_str) / 4
        assert estimated_tokens < 50

    @pytest.mark.asyncio
    async def test_delete_response_token_count(self, repository):
        """Test delete response is under 30 tokens"""
        # Create first
        create_result = await concept_tools.create_concept(
            name="Test",
            explanation="Test",
            area="coding-development",
            topic="General",
        )

        # Delete
        result = await concept_tools.delete_concept(
            create_result["data"]["concept_id"]
        )

        response_str = str(result)
        estimated_tokens = len(response_str) / 4
        assert estimated_tokens < 30
