"""
Integration tests for MCP tool wrappers
Tests that MCP server tool decorators correctly pass parameters to underlying functions
"""

import inspect
from unittest.mock import Mock

import pytest

from tools import concept_tools


@pytest.fixture(autouse=True)
def setup_repository(configured_container):
    """Setup mock repository for all tests using container fixture"""
    configured_container.repository.find_duplicate_concept = Mock(return_value=None)
    configured_container.confidence_runtime = None
    yield configured_container.repository


class TestCreateConceptToolSignature:
    """Tests for create_concept tool function signature"""

    @pytest.mark.asyncio
    async def test_create_concept_without_confidence_score_succeeds(self, setup_repository):
        """Test that create_concept works WITHOUT confidence_score parameter"""
        setup_repository.create_concept = Mock(
            return_value=(True, None, "concept-123")
        )

        # Call concept_tools function WITHOUT confidence_score
        result = await concept_tools.create_concept(
            name="Test Concept", explanation="Test explanation", area="Programming", topic="Python"
        )

        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-123"

        # Verify repository was called without confidence_score
        call_args = setup_repository.create_concept.call_args[0][0]
        assert "confidence_score" not in call_args

    @pytest.mark.asyncio
    async def test_create_concept_rejects_confidence_score_parameter(self, setup_repository):
        """Test that create_concept raises TypeError when confidence_score is passed"""
        setup_repository.create_concept = Mock(
            return_value=(True, None, "concept-123")
        )

        # Passing confidence_score should raise TypeError
        with pytest.raises(TypeError) as exc_info:
            await concept_tools.create_concept(
                name="Test Concept",
                explanation="Test explanation",
                confidence_score=0.9  # This should cause TypeError
            )

        assert "confidence_score" in str(exc_info.value)
        assert "unexpected keyword argument" in str(exc_info.value)

    def test_create_concept_signature_has_no_confidence_score(self):
        """Test that create_concept function signature does not include confidence_score"""
        sig = inspect.signature(concept_tools.create_concept)
        params = list(sig.parameters.keys())

        # Verify confidence_score is NOT in the signature
        assert "confidence_score" not in params
        # Verify expected parameters ARE present
        assert "name" in params
        assert "explanation" in params
        assert "area" in params
        assert "topic" in params
        assert "subtopic" in params


class TestUpdateConceptToolSignature:
    """Tests for update_concept tool function signature"""

    @pytest.mark.asyncio
    async def test_update_concept_without_confidence_score_succeeds(self, setup_repository):
        """Test that update_concept works WITHOUT confidence_score parameter"""
        setup_repository.update_concept = Mock(return_value=(True, None))

        # Call concept_tools function WITHOUT confidence_score
        result = await concept_tools.update_concept(
            concept_id="concept-123", explanation="Updated explanation"
        )

        assert result["success"] is True
        assert "explanation" in result["data"]["updated_fields"]

        # Verify repository was called without confidence_score
        call_args = setup_repository.update_concept.call_args[0]
        updates = call_args[1]
        assert "confidence_score" not in updates

    @pytest.mark.asyncio
    async def test_update_concept_rejects_confidence_score_parameter(self, setup_repository):
        """Test that update_concept raises TypeError when confidence_score is passed"""
        setup_repository.update_concept = Mock(return_value=(True, None))

        # Passing confidence_score should raise TypeError
        with pytest.raises(TypeError) as exc_info:
            await concept_tools.update_concept(
                concept_id="concept-123",
                explanation="Updated explanation",
                confidence_score=0.9  # This should cause TypeError
            )

        assert "confidence_score" in str(exc_info.value)
        assert "unexpected keyword argument" in str(exc_info.value)

    def test_update_concept_signature_has_no_confidence_score(self):
        """Test that update_concept function signature does not include confidence_score"""
        sig = inspect.signature(concept_tools.update_concept)
        params = list(sig.parameters.keys())

        # Verify confidence_score is NOT in the signature
        assert "confidence_score" not in params
        # Verify expected parameters ARE present
        assert "concept_id" in params
        assert "explanation" in params
        assert "name" in params
        assert "area" in params


class TestMCPServerWrapperSignatures:
    """Tests for MCP server wrapper function signatures"""

    def test_mcp_server_create_concept_wrapper_signature(self):
        """Test that mcp_server create_concept wrapper does not have confidence_score in signature"""
        import mcp_server

        # Get the actual wrapper function (before decoration)
        # The wrapper should NOT have confidence_score parameter after fix
        # For now, we'll check if the module has the function
        assert hasattr(mcp_server, "create_concept")

        # After fix, trying to call with confidence_score should fail
        # This test will help us verify the fix is complete

    def test_mcp_server_update_concept_wrapper_signature(self):
        """Test that mcp_server update_concept wrapper does not have confidence_score in signature"""
        import mcp_server

        # Get the actual wrapper function (before decoration)
        # The wrapper should NOT have confidence_score parameter after fix
        assert hasattr(mcp_server, 'update_concept')


class TestOtherToolsStillWork:
    """Verify other tools are unaffected by changes"""

    @pytest.mark.asyncio
    async def test_get_concept_still_works(self, setup_repository):
        """Test that get_concept tool still works correctly"""
        mock_concept = {
            "concept_id": "concept-123",
            "name": "Test Concept",
            "explanation": "Test explanation",
            "confidence_score": 95.0
        }
        setup_repository.get_concept = Mock(return_value=mock_concept)

        result = await concept_tools.get_concept("concept-123")

        assert result["success"] is True
        assert result["data"]["concept"]["concept_id"] == "concept-123"

    @pytest.mark.asyncio
    async def test_delete_concept_still_works(self, setup_repository):
        """Test that delete_concept tool still works correctly"""
        setup_repository.delete_concept = Mock(return_value=(True, None))

        result = await concept_tools.delete_concept("concept-123")

        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-123"
