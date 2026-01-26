"""
Unit tests for concept management MCP tools
"""

from unittest.mock import Mock

import pytest

from tools import concept_tools
from services.confidence.models import Error, ErrorCode, Success
from services.container import get_container, set_container


@pytest.fixture(autouse=True)
def setup_repository(configured_container):
    """Setup mock repository for all tests using container fixture"""
    # Add default mock for find_duplicate_concept (returns None = no duplicate)
    configured_container.repository.find_duplicate_concept = Mock(return_value=None)
    # Ensure confidence_service is None by default (via confidence_runtime)
    configured_container.confidence_runtime = None
    yield configured_container.repository


# =============================================================================
# create_concept Tests
# =============================================================================


class TestCreateConcept:
    """Tests for create_concept tool"""

    @pytest.mark.asyncio
    async def test_create_concept_success(self, setup_repository):
        """Test successful concept creation"""
        setup_repository.create_concept = Mock(return_value=(True, None, "concept-123"))

        result = await concept_tools.create_concept(
            name="Test Concept", explanation="Test explanation", area="Programming", topic="Python"
        )

        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-123"
        assert result["message"] == "Created"
        assert setup_repository.create_concept.called

    @pytest.mark.asyncio
    async def test_create_concept_with_all_fields(self, setup_repository):
        """Test creation with all optional fields (no manual confidence_score)"""
        setup_repository.create_concept = Mock(
            return_value=(True, None, "concept-456")
        )

        result = await concept_tools.create_concept(
            name="Advanced Concept",
            explanation="Detailed explanation",
            area="Mathematics",
            topic="Algebra",
            subtopic="Linear Equations",
        )

        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-456"

        # Verify all fields passed to repository (no confidence_score)
        call_args = setup_repository.create_concept.call_args[0][0]
        assert call_args["name"] == "Advanced Concept"
        assert call_args["area"] == "Mathematics"
        assert call_args["topic"] == "Algebra"
        assert call_args["subtopic"] == "Linear Equations"
        # confidence_score should NOT be in call_args
        assert "confidence_score" not in call_args

    @pytest.mark.asyncio
    async def test_create_concept_minimal_fields(self, setup_repository):
        """Test creation with only required fields"""
        setup_repository.create_concept = Mock(return_value=(True, None, "concept-789"))

        result = await concept_tools.create_concept(
            name="Minimal", explanation="Minimal explanation"
        )

        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-789"

    @pytest.mark.asyncio
    async def test_create_concept_repository_failure(self, setup_repository):
        """Test handling of repository failure"""
        setup_repository.create_concept = Mock(
            return_value=(False, "Database error", "concept-999")
        )

        result = await concept_tools.create_concept(name="Test", explanation="Test")

        assert result["success"] is False
        assert "error" in result
        # New response format uses user-friendly messages
        assert result["error"]["type"] in ["database_error", "neo4j_error", "internal_error", "unexpected_error"]

    @pytest.mark.asyncio
    async def test_create_concept_empty_name(self, setup_repository):
        """Test validation error for empty name"""
        result = await concept_tools.create_concept(name="   ", explanation="Test explanation")

        assert result["success"] is False
        assert "error" in result
        # Validation errors contain the actual validation message
        assert result["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_create_concept_empty_explanation(self, setup_repository):
        """Test validation error for empty explanation"""
        result = await concept_tools.create_concept(name="Test", explanation="   ")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_create_concept_unexpected_error(self, setup_repository):
        """Test handling of unexpected errors"""
        setup_repository.create_concept = Mock(side_effect=Exception("Unexpected error"))

        result = await concept_tools.create_concept(name="Test", explanation="Test")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "internal_error"

    @pytest.mark.asyncio
    async def test_create_concept_token_efficiency(self, setup_repository):
        """Test response is token-efficient (<50 tokens)"""
        setup_repository.create_concept = Mock(return_value=(True, None, "concept-123"))

        result = await concept_tools.create_concept(name="Test", explanation="Test")

        # Estimate token count (rough: ~4 chars per token)
        response_str = str(result)
        estimated_tokens = len(response_str) / 4
        assert estimated_tokens < 50


# =============================================================================
# get_concept Tests
# =============================================================================


class TestGetConcept:
    """Tests for get_concept tool"""

    @pytest.mark.asyncio
    async def test_get_concept_success(self, setup_repository):
        """Test successful concept retrieval with automated score (0-100 scale)"""
        mock_concept = {
            "concept_id": "concept-123",
            "name": "Test Concept",
            "explanation": "Test explanation",
            "area": "Programming",
            "topic": "Python",
            "confidence_score": 95.0,  # 0-100 scale for API response
            "created_at": "2025-01-01T00:00:00",
            "last_modified": "2025-01-01T00:00:00",
        }
        setup_repository.get_concept = Mock(return_value=mock_concept)

        result = await concept_tools.get_concept("concept-123")

        assert result["success"] is True
        assert result["data"]["concept"] == mock_concept
        assert result["message"] == "Found"
        # Verify score is in valid range
        assert 0.0 <= result["data"]["concept"]["confidence_score"] <= 100.0

    @pytest.mark.asyncio
    async def test_get_concept_with_history(self, setup_repository):
        """Test retrieval with explanation history"""
        mock_concept = {
            "concept_id": "concept-123",
            "name": "Test",
            "explanation": "Current explanation",
            "explanation_history": ["Old explanation"],
        }
        setup_repository.get_concept = Mock(return_value=mock_concept)

        result = await concept_tools.get_concept("concept-123", include_history=True)

        assert result["success"] is True
        assert "explanation_history" in result["data"]["concept"]

    @pytest.mark.asyncio
    async def test_get_concept_without_history(self, setup_repository):
        """Test history is excluded when not requested"""
        mock_concept = {
            "concept_id": "concept-123",
            "name": "Test",
            "explanation": "Current explanation",
            "explanation_history": ["Old explanation"],
        }
        setup_repository.get_concept = Mock(return_value=mock_concept)

        result = await concept_tools.get_concept("concept-123", include_history=False)

        assert result["success"] is True
        assert "explanation_history" not in result["data"]["concept"]

    @pytest.mark.asyncio
    async def test_get_concept_not_found(self, setup_repository):
        """Test concept not found"""
        setup_repository.get_concept = Mock(return_value=None)

        result = await concept_tools.get_concept("nonexistent")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["not_found", "concept_not_found"]

    @pytest.mark.asyncio
    async def test_get_concept_error(self, setup_repository):
        """Test error handling"""
        setup_repository.get_concept = Mock(side_effect=Exception("Database error"))

        result = await concept_tools.get_concept("concept-123")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["database_error", "internal_error", "unexpected_error"]


# =============================================================================
# update_concept Tests
# =============================================================================


class TestUpdateConcept:
    """Tests for update_concept tool"""

    @pytest.mark.asyncio
    async def test_update_concept_explanation(self, setup_repository):
        """Test updating explanation (no manual confidence_score)"""
        setup_repository.update_concept = Mock(return_value=(True, None))

        result = await concept_tools.update_concept(
            concept_id="concept-123", explanation="Updated explanation"
        )

        assert result["success"] is True
        assert "explanation" in result["data"]["updated_fields"]
        assert result["message"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_concept_multiple_fields(self, setup_repository):
        """Test updating multiple fields (no manual confidence_score)"""
        setup_repository.update_concept = Mock(return_value=(True, None))

        result = await concept_tools.update_concept(
            concept_id="concept-123", explanation="New explanation", area="Updated Area"
        )

        assert result["success"] is True
        assert len(result["data"]["updated_fields"]) == 2
        assert "explanation" in result["data"]["updated_fields"]
        assert "area" in result["data"]["updated_fields"]
        # confidence_score should NOT be in updated_fields
        assert "confidence_score" not in result["data"]["updated_fields"]

    @pytest.mark.asyncio
    async def test_update_concept_all_fields(self, setup_repository):
        """Test updating all fields (no manual confidence_score)"""
        setup_repository.update_concept = Mock(return_value=(True, None))

        result = await concept_tools.update_concept(
            concept_id="concept-123",
            name="New Name",
            explanation="New explanation",
            area="New Area",
            topic="New Topic",
            subtopic="New Subtopic",
        )

        assert result["success"] is True
        assert len(result["data"]["updated_fields"]) == 5

    @pytest.mark.asyncio
    async def test_update_concept_no_fields(self, setup_repository):
        """Test error when no fields provided"""
        result = await concept_tools.update_concept(concept_id="concept-123")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_update_concept_repository_failure(self, setup_repository):
        """Test handling of repository failure"""
        setup_repository.update_concept = Mock(return_value=(False, "Version conflict"))

        result = await concept_tools.update_concept(concept_id="concept-123", explanation="New")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["database_error", "internal_error"]

    @pytest.mark.asyncio
    async def test_update_concept_empty_string_validation(self, setup_repository):
        """Test validation error for empty string"""
        result = await concept_tools.update_concept(concept_id="concept-123", explanation="   ")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_update_concept_unexpected_error(self, setup_repository):
        """Test handling of unexpected errors"""
        setup_repository.update_concept = Mock(side_effect=Exception("Unexpected"))

        result = await concept_tools.update_concept(concept_id="concept-123", explanation="New")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error"]

    @pytest.mark.asyncio
    async def test_update_concept_token_efficiency(self, setup_repository):
        """Test response is token-efficient (<50 tokens)"""
        setup_repository.update_concept = Mock(return_value=(True, None))

        result = await concept_tools.update_concept(concept_id="concept-123", explanation="Updated")

        response_str = str(result)
        estimated_tokens = len(response_str) / 4
        assert estimated_tokens < 50


# =============================================================================
# delete_concept Tests
# =============================================================================


class TestDeleteConcept:
    """Tests for delete_concept tool"""

    @pytest.mark.asyncio
    async def test_delete_concept_success(self, setup_repository):
        """Test successful deletion"""
        setup_repository.delete_concept = Mock(return_value=(True, None))

        result = await concept_tools.delete_concept("concept-123")

        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-123"
        assert result["message"] == "Deleted"

    @pytest.mark.asyncio
    async def test_delete_concept_failure(self, setup_repository):
        """Test deletion failure"""
        setup_repository.delete_concept = Mock(return_value=(False, "Concept not found"))

        result = await concept_tools.delete_concept("nonexistent")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["database_error", "not_found", "internal_error"]

    @pytest.mark.asyncio
    async def test_delete_concept_unexpected_error(self, setup_repository):
        """Test handling of unexpected errors"""
        setup_repository.delete_concept = Mock(side_effect=Exception("Database error"))

        result = await concept_tools.delete_concept("concept-123")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error", "database_error"]

    @pytest.mark.asyncio
    async def test_delete_concept_token_efficiency(self, setup_repository):
        """Test response is token-efficient (<30 tokens)"""
        setup_repository.delete_concept = Mock(return_value=(True, None))

        result = await concept_tools.delete_concept("concept-123")

        response_str = str(result)
        estimated_tokens = len(response_str) / 4
        assert estimated_tokens < 30


# =============================================================================
# Pydantic Model Tests
# =============================================================================


class TestPydanticModels:
    """Tests for Pydantic validation models"""

    def test_concept_create_valid(self):
        """Test ConceptCreate with valid data (no manual confidence_score)"""
        from tools.concept_tools import ConceptCreate

        data = ConceptCreate(
            name="Test Concept", explanation="Test explanation", area="Programming"
        )

        assert data.name == "Test Concept"
        assert data.explanation == "Test explanation"
        assert data.area == "Programming"

    def test_concept_create_strips_whitespace(self):
        """Test that whitespace is stripped from strings"""
        from tools.concept_tools import ConceptCreate

        data = ConceptCreate(name="  Test  ", explanation="  Explanation  ")

        assert data.name == "Test"
        assert data.explanation == "Explanation"

    def test_concept_update_valid(self):
        """Test ConceptUpdate with valid data (no manual confidence_score)"""
        from tools.concept_tools import ConceptUpdate

        data = ConceptUpdate(explanation="Updated")

        assert data.explanation == "Updated"

    def test_concept_update_all_none(self):
        """Test ConceptUpdate with all None values"""
        from tools.concept_tools import ConceptUpdate

        data = ConceptUpdate()

        assert data.explanation is None
        assert data.name is None


# =============================================================================
# _enrich_confidence_score Tests
# =============================================================================

class TestEnrichConfidenceScore:
    """Tests for _enrich_confidence_score function.

    This function enriches concept dictionaries with confidence scores.
    It has three code paths:
    1. Score exists in concept → clamp to 0-100 range
    2. Score missing + service available → calculate on-demand (0-1 → 0-100)
    3. Score missing + no service → default to 0.0

    IMPORTANT: When calculation fails, RuntimeError is raised (no silent fallbacks).
    This is intentional fail-fast behavior for critical business logic.
    """

    @pytest.mark.asyncio
    async def test_enrich_with_existing_score_in_range(self, setup_repository):
        """Test that existing scores within range are preserved."""
        from tools.concept_tools import _enrich_confidence_score

        concept = {"concept_id": "test-1", "confidence_score": 75.5}
        await _enrich_confidence_score("test-1", concept)

        assert concept["confidence_score"] == 75.5

    @pytest.mark.asyncio
    async def test_enrich_clamps_score_above_100(self, setup_repository):
        """Test that scores above 100 are clamped to 100."""
        from tools.concept_tools import _enrich_confidence_score

        concept = {"concept_id": "test-1", "confidence_score": 150.0}
        await _enrich_confidence_score("test-1", concept)

        assert concept["confidence_score"] == 100.0

    @pytest.mark.asyncio
    async def test_enrich_clamps_score_below_0(self, setup_repository):
        """Test that scores below 0 are clamped to 0."""
        from tools.concept_tools import _enrich_confidence_score

        concept = {"concept_id": "test-1", "confidence_score": -10.0}
        await _enrich_confidence_score("test-1", concept)

        assert concept["confidence_score"] == 0.0

    @pytest.mark.asyncio
    async def test_enrich_calculates_on_demand_when_missing(self, setup_repository):
        """Test on-demand calculation when score is missing (0-1 converted to 0-100)."""
        from tools.concept_tools import _enrich_confidence_score

        # Mock confidence service returning Success with 0-1 scale value
        mock_service = AsyncMock()
        mock_service.calculate_composite_score = AsyncMock(return_value=Success(0.75))

        # Set up confidence_runtime on container so confidence_service property returns mock
        container = get_container()
        container.confidence_runtime = Mock()
        container.confidence_runtime.calculator = mock_service

        concept = {"concept_id": "test-1"}  # No confidence_score
        await _enrich_confidence_score("test-1", concept)

        # Should be converted from 0.75 (0-1) to 75.0 (0-100)
        assert concept["confidence_score"] == 75.0
        mock_service.calculate_composite_score.assert_called_once_with("test-1")

    @pytest.mark.asyncio
    async def test_enrich_raises_runtime_error_on_calculation_failure(self, setup_repository):
        """Test RuntimeError is raised when calculation fails (no silent fallbacks).

        This is intentional fail-fast behavior. When confidence calculation fails,
        we don't want to silently return 0.0 - that would mask errors and give
        users incorrect data. Instead, we propagate the error so it can be handled
        appropriately by callers.
        """
        from tools.concept_tools import _enrich_confidence_score

        # Mock confidence service returning Error
        mock_service = AsyncMock()
        mock_service.calculate_composite_score = AsyncMock(
            return_value=Error("Database connection failed", ErrorCode.DATABASE_ERROR)
        )

        # Set up confidence_runtime on container so confidence_service property returns mock
        container = get_container()
        container.confidence_runtime = Mock()
        container.confidence_runtime.calculator = mock_service

        concept = {"concept_id": "test-1"}  # No confidence_score

        with pytest.raises(RuntimeError) as exc_info:
            await _enrich_confidence_score("test-1", concept)

        assert "Confidence calculation failed for test-1" in str(exc_info.value)
        assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_enrich_defaults_to_zero_when_no_service(self, setup_repository):
        """Test default to 0.0 when confidence service is unavailable."""
        from tools.concept_tools import _enrich_confidence_score

        # Ensure no confidence service is available (confidence_runtime is None)
        container = get_container()
        container.confidence_runtime = None

        concept = {"concept_id": "test-1"}  # No confidence_score
        await _enrich_confidence_score("test-1", concept)

        assert concept["confidence_score"] == 0.0

    @pytest.mark.asyncio
    async def test_enrich_handles_non_numeric_score(self, setup_repository):
        """Test that non-numeric scores are handled gracefully."""
        from tools.concept_tools import _enrich_confidence_score

        concept = {"concept_id": "test-1", "confidence_score": "invalid"}
        await _enrich_confidence_score("test-1", concept)

        # _clamp_confidence_score returns 0.0 for non-numeric values
        assert concept["confidence_score"] == 0.0


class TestGetConceptEnrichmentErrorHandling:
    """Tests for get_concept error handling when enrichment fails.

    When _enrich_confidence_score raises RuntimeError, get_concept
    should catch it and return an internal_error response.
    """

    @pytest.mark.asyncio
    async def test_get_concept_returns_internal_error_on_enrichment_failure(self, setup_repository):
        """Test get_concept converts enrichment RuntimeError to internal_error response.

        When confidence calculation fails during get_concept, the RuntimeError
        raised by _enrich_confidence_score is caught by the outer try/except
        and converted to an internal_error response.
        """
        # Mock repository returning concept WITHOUT confidence_score
        setup_repository.get_concept = Mock(return_value={
            "concept_id": "test-1",
            "name": "Test Concept",
            "explanation": "Test explanation"
            # Note: No confidence_score - triggers enrichment
        })

        # Mock confidence service returning Error
        mock_service = AsyncMock()
        mock_service.calculate_composite_score = AsyncMock(
            return_value=Error("Calculation failed", ErrorCode.DATABASE_ERROR)
        )

        # Set up confidence_runtime on container so confidence_service property returns mock
        container = get_container()
        container.confidence_runtime = Mock()
        container.confidence_runtime.calculator = mock_service

        result = await concept_tools.get_concept("test-1")

        # Should return error response, not raise exception
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "internal_error"

    @pytest.mark.asyncio
    async def test_get_concept_success_with_enrichment(self, setup_repository):
        """Test get_concept succeeds when enrichment calculates score on-demand."""
        # Mock repository returning concept WITHOUT confidence_score
        setup_repository.get_concept = Mock(return_value={
            "concept_id": "test-1",
            "name": "Test Concept",
            "explanation": "Test explanation"
            # Note: No confidence_score - triggers enrichment
        })

        # Mock confidence service returning Success
        mock_service = AsyncMock()
        mock_service.calculate_composite_score = AsyncMock(return_value=Success(0.85))

        # Set up confidence_runtime on container so confidence_service property returns mock
        container = get_container()
        container.confidence_runtime = Mock()
        container.confidence_runtime.calculator = mock_service

        result = await concept_tools.get_concept("test-1")

        assert result["success"] is True
        assert result["data"]["concept"]["confidence_score"] == 85.0  # 0.85 * 100
