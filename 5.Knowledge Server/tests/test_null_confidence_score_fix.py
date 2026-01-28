"""
Tests for NULL confidence score handling (Issue #H003).

Verifies that get_concepts_by_confidence correctly handles concepts with
NULL confidence_score values by treating them as 0.

Related Issues:
- #H003: Missing NULL Confidence Score Handling
"""

import pytest
from unittest.mock import Mock

from tools import analytics_tools
from tools.analytics_tools import get_concepts_by_confidence


@pytest.fixture
def setup_services(configured_container):
    """Setup services for tests using container fixture."""
    analytics_tools._query_cache.clear()
    return {
        "neo4j": configured_container.neo4j_service
    }


class TestNullConfidenceScoreHandling:
    """Test suite for NULL confidence score handling fix."""

    @pytest.mark.asyncio
    async def test_null_confidence_included_in_full_range(self, setup_services):
        """Test that NULL confidence scores are included when querying full range 0-100."""
        services = setup_services

        # Mock Neo4j to return mix of concepts with and without confidence scores
        services["neo4j"].execute_read = Mock(return_value=[
            {
                'concept_id': 'concept-1',
                'name': 'Concept with NULL score',
                'area': 'Test',
                'topic': 'Testing',
                'subtopic': 'Unit Tests',
                'confidence_score': 0.0,  # NULL treated as 0
                'created_at': '2025-11-10T00:00:00'
            },
            {
                'concept_id': 'concept-2',
                'name': 'Concept with score',
                'area': 'Test',
                'topic': 'Testing',
                'subtopic': 'Unit Tests',
                'confidence_score': 50.0,
                'created_at': '2025-11-10T00:00:00'
            }
        ])

        # Query full range
        result = await get_concepts_by_confidence(min_confidence=0, max_confidence=100)

        # Verify success
        assert result['success'] is True
        assert result['data']['total'] == 2

        # CRITICAL: Verify query uses COALESCE in WHERE clause
        query_call = services["neo4j"].execute_read.call_args[0][0]
        assert 'COALESCE(c.confidence_score, 0.0)' in query_call

        # Verify COALESCE appears in WHERE clause (before RETURN)
        where_clause = query_call.split("WHERE")[1].split("RETURN")[0]
        assert "COALESCE" in where_clause

    @pytest.mark.asyncio
    async def test_null_confidence_excluded_from_high_range(self, setup_services):
        """Test that NULL confidence scores (treated as 0) are excluded from high ranges."""
        services = setup_services

        # Mock Neo4j to return only concepts with high scores
        # (NULL concepts would be filtered out by WHERE clause)
        services["neo4j"].execute_read = Mock(return_value=[
            {
                'concept_id': 'concept-high',
                'name': 'High confidence concept',
                'area': 'Test',
                'topic': 'Testing',
                'subtopic': 'Unit Tests',
                'confidence_score': 80.0,
                'created_at': '2025-11-10T00:00:00'
            }
        ])

        # Query high range (should exclude NULL which is treated as 0)
        result = await get_concepts_by_confidence(min_confidence=50, max_confidence=100)

        # Verify query was made with correct parameters
        query_params = services["neo4j"].execute_read.call_args[0][1]
        assert query_params['min_confidence'] == 50
        assert query_params['max_confidence'] == 100

        # Verify query uses COALESCE (NULL concepts would be filtered out)
        query_call = services["neo4j"].execute_read.call_args[0][0]
        assert 'COALESCE(c.confidence_score, 0.0)' in query_call

    @pytest.mark.asyncio
    async def test_query_uses_coalesce_consistently(self, setup_services):
        """Test that COALESCE is used consistently in WHERE and SELECT clauses."""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Call the function
        await get_concepts_by_confidence(min_confidence=0, max_confidence=100)

        # Get the query that was executed
        query = services["neo4j"].execute_read.call_args[0][0]

        # Count COALESCE occurrences
        coalesce_count = query.count('COALESCE(c.confidence_score, 0.0)')

        # Should appear 3 times:
        # - 2 times in WHERE clause (min and max)
        # - 1 time in SELECT clause
        assert coalesce_count == 3, f"Expected 3 COALESCE, found {coalesce_count}"

    @pytest.mark.asyncio
    async def test_boundary_values_include_zero(self, setup_services):
        """Test that querying exactly 0-100 includes concepts with NULL (treated as 0)."""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Query with exact boundaries
        await get_concepts_by_confidence(min_confidence=0, max_confidence=100)

        # Verify parameters
        query_params = services["neo4j"].execute_read.call_args[0][1]
        assert query_params['min_confidence'] == 0
        assert query_params['max_confidence'] == 100

        # Verify COALESCE in WHERE would allow NULL (treated as 0)
        # Note: Scores are now stored directly as 0-100, so no multiplication needed
        query = services["neo4j"].execute_read.call_args[0][0]
        assert 'COALESCE(c.confidence_score, 0.0) >= $min_confidence' in query
        assert 'COALESCE(c.confidence_score, 0.0) <= $max_confidence' in query

    @pytest.mark.asyncio
    async def test_null_concepts_sorted_first(self, setup_services):
        """Test that NULL concepts (treated as 0) appear first when sorted ascending."""
        services = setup_services

        # Mock data sorted by confidence ASC (NULL/0 first)
        services["neo4j"].execute_read = Mock(return_value=[
            {
                'concept_id': 'concept-null',
                'name': 'NULL score concept',
                'area': 'Test',
                'topic': 'Testing',
                'subtopic': None,
                'confidence_score': 0.0,  # NULL treated as 0
                'created_at': '2025-11-10T00:00:00'
            },
            {
                'concept_id': 'concept-low',
                'name': 'Low score concept',
                'area': 'Test',
                'topic': 'Testing',
                'subtopic': None,
                'confidence_score': 25.0,
                'created_at': '2025-11-10T00:00:00'
            },
            {
                'concept_id': 'concept-high',
                'name': 'High score concept',
                'area': 'Test',
                'topic': 'Testing',
                'subtopic': None,
                'confidence_score': 90.0,
                'created_at': '2025-11-10T00:00:00'
            }
        ])

        result = await get_concepts_by_confidence(min_confidence=0, max_confidence=100)

        # Verify sorting
        assert result['data']['results'][0]['confidence_score'] == 0.0  # NULL/0 first
        assert result['data']['results'][1]['confidence_score'] == 25.0
        assert result['data']['results'][2]['confidence_score'] == 90.0

    @pytest.mark.asyncio
    async def test_parameter_validation_with_null_handling(self, setup_services):
        """Test that parameter validation works correctly with NULL handling."""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Test negative min_confidence (should be clamped to 0)
        await get_concepts_by_confidence(min_confidence=-10, max_confidence=100)

        query_params = services["neo4j"].execute_read.call_args[0][1]
        assert query_params['min_confidence'] == 0

        # Test max_confidence > 100 (should be clamped to 100)
        await get_concepts_by_confidence(min_confidence=0, max_confidence=150)

        query_params = services["neo4j"].execute_read.call_args[0][1]
        assert query_params['max_confidence'] == 100

    @pytest.mark.asyncio
    async def test_inverted_range_swapped(self, setup_services):
        """Test that inverted range (min > max) is swapped."""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Provide inverted range
        await get_concepts_by_confidence(min_confidence=80, max_confidence=20)

        # Verify parameters were swapped
        query_params = services["neo4j"].execute_read.call_args[0][1]
        assert query_params['min_confidence'] == 20
        assert query_params['max_confidence'] == 80


class TestNullConfidenceScoreEdgeCases:
    """Test edge cases for NULL confidence score handling."""

    @pytest.mark.asyncio
    async def test_only_null_concepts_in_database(self, setup_services):
        """Test behavior when database contains only NULL confidence scores."""
        services = setup_services

        # All concepts have NULL confidence (treated as 0)
        services["neo4j"].execute_read = Mock(return_value=[
            {
                'concept_id': f'concept-{i}',
                'name': f'Concept {i}',
                'area': 'Test',
                'topic': 'Testing',
                'subtopic': None,
                'confidence_score': 0.0,
                'created_at': '2025-11-10T00:00:00'
            }
            for i in range(5)
        ])

        result = await get_concepts_by_confidence(min_confidence=0, max_confidence=100)

        # All NULL concepts should be included
        assert result['success'] is True
        assert result['data']['total'] == 5

    @pytest.mark.asyncio
    async def test_exact_zero_boundary(self, setup_services):
        """Test that concepts with exactly 0 confidence are included at boundary."""
        services = setup_services

        services["neo4j"].execute_read = Mock(return_value=[
            {
                'concept_id': 'concept-zero',
                'name': 'Zero confidence',
                'area': 'Test',
                'topic': 'Testing',
                'subtopic': None,
                'confidence_score': 0.0,
                'created_at': '2025-11-10T00:00:00'
            }
        ])

        # Query starting at exactly 0
        result = await get_concepts_by_confidence(min_confidence=0, max_confidence=50)

        assert result['success'] is True
        assert result['data']['total'] == 1
        assert result['data']['results'][0]['confidence_score'] == 0.0


class TestCypherQueryCorrectness:
    """Test that Cypher query is correctly formed."""

    @pytest.mark.asyncio
    async def test_where_clause_uses_coalesce_for_min(self, setup_services):
        """Test that WHERE clause uses COALESCE for min_confidence check."""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await get_concepts_by_confidence(min_confidence=25, max_confidence=75)

        query = services["neo4j"].execute_read.call_args[0][0]

        # Verify COALESCE is used in min check
        # Note: Scores are now stored directly as 0-100, so no multiplication needed
        assert 'COALESCE(c.confidence_score, 0.0) >= $min_confidence' in query

    @pytest.mark.asyncio
    async def test_where_clause_uses_coalesce_for_max(self, setup_services):
        """Test that WHERE clause uses COALESCE for max_confidence check."""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await get_concepts_by_confidence(min_confidence=25, max_confidence=75)

        query = services["neo4j"].execute_read.call_args[0][0]

        # Verify COALESCE is used in max check
        # Note: Scores are now stored directly as 0-100, so no multiplication needed
        assert 'COALESCE(c.confidence_score, 0.0) <= $max_confidence' in query

    @pytest.mark.asyncio
    async def test_select_clause_uses_coalesce(self, setup_services):
        """Test that SELECT clause also uses COALESCE (existing behavior)."""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await get_concepts_by_confidence(min_confidence=0, max_confidence=100)

        query = services["neo4j"].execute_read.call_args[0][0]

        # Verify COALESCE in RETURN clause
        # Note: Scores are now stored directly as 0-100, so no multiplication needed
        assert 'COALESCE(c.confidence_score, 0.0) as confidence_score' in query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
