"""
Unit tests for analytics tools
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from tools import analytics_tools


@pytest.fixture
def setup_services(configured_container):
    """Setup services for tests using container fixture"""
    # Clear cache
    analytics_tools._query_cache.clear()

    return {
        "neo4j": configured_container.neo4j_service
    }


class TestListHierarchy:
    """Tests for list_hierarchy tool"""

    @pytest.mark.asyncio
    async def test_list_hierarchy_success(self, setup_services):
        """Test successful hierarchy retrieval"""
        services = setup_services

        mock_results = [
            {"area": "Programming", "topic": "Python", "subtopic": "Functions", "count": 5},
            {"area": "Programming", "topic": "Python", "subtopic": "Classes", "count": 3},
            {"area": "Programming", "topic": "JavaScript", "subtopic": "ES6", "count": 4},
            {"area": "Math", "topic": "Algebra", "subtopic": "Linear", "count": 2},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        assert result["data"]["total_concepts"] == 14  # 5 + 3 + 4 + 2
        assert len(result["data"]["areas"]) == 2  # Programming and Math
        assert result["data"]["areas"][0]["name"] == "Math"  # Alphabetically sorted
        assert result["data"]["areas"][1]["name"] == "Programming"

    @pytest.mark.asyncio
    async def test_list_hierarchy_nested_structure(self, setup_services):
        """Test nested structure is built correctly"""
        services = setup_services

        mock_results = [
            {"area": "Programming", "topic": "Python", "subtopic": "Functions", "count": 5},
            {"area": "Programming", "topic": "Python", "subtopic": "Classes", "count": 3},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        # Check area level
        programming = result["data"]["areas"][0]
        assert programming["name"] == "Programming"
        assert programming["concept_count"] == 8  # 5 + 3

        # Check topic level
        assert len(programming["topics"]) == 1
        python_topic = programming["topics"][0]
        assert python_topic["name"] == "Python"
        assert python_topic["concept_count"] == 8

        # Check subtopic level
        assert len(python_topic["subtopics"]) == 2
        assert python_topic["subtopics"][0]["name"] == "Classes"  # Alphabetically sorted
        assert python_topic["subtopics"][0]["concept_count"] == 3
        assert python_topic["subtopics"][1]["name"] == "Functions"
        assert python_topic["subtopics"][1]["concept_count"] == 5

    @pytest.mark.asyncio
    async def test_list_hierarchy_handles_nulls(self, setup_services):
        """Test handling of null values in area/topic/subtopic"""
        services = setup_services

        mock_results = [
            {"area": None, "topic": None, "subtopic": None, "count": 2},
            {"area": "Programming", "topic": None, "subtopic": "Functions", "count": 3},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        # Nulls should be replaced with defaults
        assert any(area["name"] == "Uncategorized" for area in result["data"]["areas"])

    @pytest.mark.asyncio
    async def test_list_hierarchy_empty_result(self, setup_services):
        """Test with no concepts in database"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        assert result["data"]["total_concepts"] == 0
        assert result["data"]["areas"] == []

    @pytest.mark.asyncio
    async def test_list_hierarchy_cache_behavior(self, setup_services):
        """Test that results are cached properly"""
        services = setup_services

        mock_results = [
            {"area": "Programming", "topic": "Python", "subtopic": "Functions", "count": 5},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # First call should query Neo4j
        result1 = await analytics_tools.list_hierarchy()
        assert services["neo4j"].execute_read.call_count == 1

        # Second call should use cache (within 5 min TTL)
        result2 = await analytics_tools.list_hierarchy()
        assert services["neo4j"].execute_read.call_count == 1  # Still only 1 call

        # Results should be identical
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_list_hierarchy_cache_expiry(self, setup_services):
        """Test that cache expires after TTL"""
        services = setup_services
        from datetime import timedelta

        mock_results = [
            {"area": "Programming", "topic": "Python", "subtopic": "Functions", "count": 5},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # First call
        await analytics_tools.list_hierarchy()
        assert services["neo4j"].execute_read.call_count == 1

        # Manually expire cache by accessing internal cache entry and setting old timestamp
        # The _query_cache uses CacheEntry objects with timestamp field
        cache_entry = analytics_tools._query_cache._cache.get('hierarchy')
        if cache_entry:
            cache_entry.timestamp = datetime.now() - timedelta(seconds=301)

        # Second call should re-query Neo4j
        await analytics_tools.list_hierarchy()
        assert services["neo4j"].execute_read.call_count == 2

    @pytest.mark.asyncio
    async def test_list_hierarchy_error_handling(self, setup_services):
        """Test error handling for database failures"""
        services = setup_services
        services["neo4j"].execute_read = Mock(side_effect=Exception("Database error"))

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error", "database_error"]


class TestGetConceptsByConfidence:
    """Tests for get_concepts_by_confidence tool"""

    @pytest.mark.asyncio
    async def test_get_concepts_success(self, setup_services):
        """Test successful retrieval of concepts by confidence"""
        services = setup_services

        mock_results = [
            {
                "concept_id": "concept-001",
                "name": "Low Certainty Concept",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Functions",
                "confidence_score": 25.0,
                "created_at": "2025-10-01T00:00:00"
            },
            {
                "concept_id": "concept-002",
                "name": "Medium Certainty Concept",
                "area": "Math",
                "topic": "Algebra",
                "subtopic": "Linear",
                "confidence_score": 50.0,
                "created_at": "2025-10-02T00:00:00"
            }
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.get_concepts_by_confidence(
            min_confidence=0,
            max_confidence=60,
            limit=20
        )

        assert result["success"] is True
        assert result["data"]["total"] == 2
        assert len(result["data"]["results"]) == 2
        assert result["data"]["results"][0]["confidence_score"] == 25.0

    @pytest.mark.asyncio
    async def test_get_concepts_low_confidence(self, setup_services):
        """Test filtering for low confidence concepts"""
        services = setup_services

        mock_results = [
            {
                "concept_id": "concept-001",
                "name": "Uncertain Concept",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Functions",
                "confidence_score": 10.0,
                "created_at": "2025-10-01T00:00:00"
            }
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.get_concepts_by_confidence(
            min_confidence=0,
            max_confidence=50
        )

        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert result["data"]["results"][0]["confidence_score"] == 10.0

        # Verify query parameters
        call_args = services["neo4j"].execute_read.call_args
        params = call_args[0][1]
        assert params["min_confidence"] == 0
        assert params["max_confidence"] == 50

    @pytest.mark.asyncio
    async def test_get_concepts_high_confidence(self, setup_services):
        """Test filtering for high confidence concepts"""
        services = setup_services

        mock_results = [
            {
                "concept_id": "concept-001",
                "name": "High Certainty Concept",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Functions",
                "confidence_score": 95.0,
                "created_at": "2025-10-01T00:00:00"
            }
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.get_concepts_by_confidence(
            min_confidence=80,
            max_confidence=100
        )

        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert result["data"]["results"][0]["confidence_score"] == 95.0

    @pytest.mark.asyncio
    async def test_get_concepts_parameter_validation(self, setup_services):
        """Test parameter validation and auto-correction"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Test with invalid parameters (should auto-correct)
        result = await analytics_tools.get_concepts_by_confidence(
            min_confidence=-10,  # Should become 0
            max_confidence=150,  # Should become 100
            limit=100  # Should become 50
        )

        assert result["success"] is True

        # Verify corrected parameters were used
        call_args = services["neo4j"].execute_read.call_args
        params = call_args[0][1]
        assert params["min_confidence"] == 0
        assert params["max_confidence"] == 100
        assert params["limit"] == 50

    @pytest.mark.asyncio
    async def test_get_concepts_swapped_min_max(self, setup_services):
        """Test that min > max gets swapped"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await analytics_tools.get_concepts_by_confidence(
            min_confidence=80,
            max_confidence=20  # Less than min
        )

        assert result["success"] is True

        # Verify parameters were swapped
        call_args = services["neo4j"].execute_read.call_args
        params = call_args[0][1]
        assert params["min_confidence"] == 20
        assert params["max_confidence"] == 80

    @pytest.mark.asyncio
    async def test_get_concepts_limit_validation(self, setup_services):
        """Test limit parameter validation"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Test limit < 1 (should become 1)
        result1 = await analytics_tools.get_concepts_by_confidence(limit=0)
        params1 = services["neo4j"].execute_read.call_args[0][1]
        assert params1["limit"] == 1

        # Test limit > 50 (should become 50)
        result2 = await analytics_tools.get_concepts_by_confidence(limit=100)
        params2 = services["neo4j"].execute_read.call_args[0][1]
        assert params2["limit"] == 50

    @pytest.mark.asyncio
    async def test_get_concepts_empty_result(self, setup_services):
        """Test with no concepts in range"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await analytics_tools.get_concepts_by_confidence(
            min_confidence=90,
            max_confidence=100
        )

        assert result["success"] is True
        assert result["data"]["total"] == 0
        assert result["data"]["results"] == []

    @pytest.mark.asyncio
    async def test_get_concepts_sorting(self, setup_services):
        """Test that results are sorted by confidence ascending"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await analytics_tools.get_concepts_by_confidence()

        # Verify query includes correct ORDER BY clause
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY c.confidence_score ASC" in query

    @pytest.mark.asyncio
    async def test_get_concepts_sort_order_asc(self, setup_services):
        """Test sorting with sort_order='asc' (learning mode - lowest first)"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await analytics_tools.get_concepts_by_confidence(sort_order="asc")

        # Verify query uses ASC for learning mode
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY c.confidence_score ASC" in query

    @pytest.mark.asyncio
    async def test_get_concepts_sort_order_desc(self, setup_services):
        """Test sorting with sort_order='desc' (discovery mode - highest first)"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await analytics_tools.get_concepts_by_confidence(sort_order="desc")

        # Verify query uses DESC for discovery mode
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY c.confidence_score DESC" in query

    @pytest.mark.asyncio
    async def test_get_concepts_sort_order_default(self, setup_services):
        """Test that default sort_order is 'asc' for learning-first approach"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Call without sort_order parameter
        await analytics_tools.get_concepts_by_confidence()

        # Verify default is ASC (learning mode)
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY c.confidence_score ASC" in query

    @pytest.mark.asyncio
    async def test_get_concepts_sort_order_case_insensitive(self, setup_services):
        """Test that sort_order parameter is case-insensitive"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Test uppercase
        await analytics_tools.get_concepts_by_confidence(sort_order="ASC")
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY c.confidence_score ASC" in query

        # Test mixed case
        await analytics_tools.get_concepts_by_confidence(sort_order="Desc")
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY c.confidence_score DESC" in query

    @pytest.mark.asyncio
    async def test_get_concepts_sort_order_invalid(self, setup_services):
        """Test that invalid sort_order values default to 'asc'"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Test invalid value defaults to ASC
        await analytics_tools.get_concepts_by_confidence(sort_order="invalid")
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY c.confidence_score ASC" in query

    @pytest.mark.asyncio
    async def test_get_concepts_error_handling(self, setup_services):
        """Test error handling for database failures"""
        services = setup_services
        services["neo4j"].execute_read = Mock(side_effect=Exception("Database error"))

        result = await analytics_tools.get_concepts_by_confidence()

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error", "database_error"]

    @pytest.mark.asyncio
    async def test_get_concepts_default_parameters(self, setup_services):
        """Test default parameter values"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await analytics_tools.get_concepts_by_confidence()

        assert result["success"] is True

        # Verify default parameters
        call_args = services["neo4j"].execute_read.call_args
        params = call_args[0][1]
        assert params["min_confidence"] == 0
        assert params["max_confidence"] == 100
        assert params["limit"] == 20
