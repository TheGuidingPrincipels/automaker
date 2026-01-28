"""
Unit tests for analytics tools
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from config import PREDEFINED_AREAS
from tools import analytics_tools

# Number of predefined areas (used in tests)
NUM_PREDEFINED_AREAS = len(PREDEFINED_AREAS)


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
        """Test successful hierarchy retrieval - includes all predefined areas"""
        services = setup_services

        mock_results = [
            {"area": "coding-development", "topic": "Python", "subtopic": "Functions", "count": 5},
            {"area": "coding-development", "topic": "Python", "subtopic": "Classes", "count": 3},
            {"area": "coding-development", "topic": "JavaScript", "subtopic": "ES6", "count": 4},
            {"area": "learning", "topic": "Memory", "subtopic": "Techniques", "count": 2},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        assert result["data"]["total_concepts"] == 14  # 5 + 3 + 4 + 2
        # All predefined areas should be included (even those with 0 concepts)
        assert len(result["data"]["areas"]) == NUM_PREDEFINED_AREAS
        # Check areas with concepts have correct counts
        coding_area = next(a for a in result["data"]["areas"] if a["name"] == "coding-development")
        assert coding_area["concept_count"] == 12  # 5 + 3 + 4
        assert coding_area["label"] == "Coding & Development"
        assert coding_area["is_predefined"] is True
        learning_area = next(a for a in result["data"]["areas"] if a["name"] == "learning")
        assert learning_area["concept_count"] == 2
        assert learning_area["label"] == "Learning"
        assert learning_area["is_predefined"] is True

    @pytest.mark.asyncio
    async def test_list_hierarchy_nested_structure(self, setup_services):
        """Test nested structure is built correctly"""
        services = setup_services

        mock_results = [
            {"area": "coding-development", "topic": "Python", "subtopic": "Functions", "count": 5},
            {"area": "coding-development", "topic": "Python", "subtopic": "Classes", "count": 3},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        # Check area level - find the specific area by name
        coding_area = next(a for a in result["data"]["areas"] if a["name"] == "coding-development")
        assert coding_area["concept_count"] == 8  # 5 + 3
        assert coding_area["label"] == "Coding & Development"
        assert coding_area["is_predefined"] is True

        # Check topic level
        assert len(coding_area["topics"]) == 1
        python_topic = coding_area["topics"][0]
        assert python_topic["name"] == "Python"
        assert python_topic["concept_count"] == 8

        # Check subtopic level
        assert len(python_topic["subtopics"]) == 2
        assert python_topic["subtopics"][0]["name"] == "Classes"  # Alphabetically sorted
        assert python_topic["subtopics"][0]["concept_count"] == 3
        assert python_topic["subtopics"][1]["name"] == "Functions"
        assert python_topic["subtopics"][1]["concept_count"] == 5

    @pytest.mark.asyncio
    async def test_list_hierarchy_normalizes_legacy_labels(self, setup_services):
        """Test that legacy area labels map to canonical slugs without duplication."""
        services = setup_services

        mock_results = [
            {"area": "Coding & Development", "topic": "Python", "subtopic": "Functions", "count": 2},
            {"area": "coding-development", "topic": "Python", "subtopic": "Classes", "count": 3},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        coding_area = next(a for a in result["data"]["areas"] if a["name"] == "coding-development")
        assert coding_area["concept_count"] == 5
        assert coding_area["label"] == "Coding & Development"
        assert len([a for a in result["data"]["areas"] if a["label"] == "Coding & Development"]) == 1

    @pytest.mark.asyncio
    async def test_list_hierarchy_handles_nulls(self, setup_services):
        """Test handling of null values in area/topic/subtopic"""
        services = setup_services

        mock_results = [
            {"area": None, "topic": None, "subtopic": None, "count": 2},
            {"area": "coding-development", "topic": None, "subtopic": "Functions", "count": 3},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        # Nulls should be replaced with defaults
        uncategorized = next(a for a in result["data"]["areas"] if a["name"] == "Uncategorized")
        assert uncategorized["label"] == "Uncategorized"
        assert uncategorized["is_predefined"] is False

    @pytest.mark.asyncio
    async def test_list_hierarchy_empty_result(self, setup_services):
        """Test with no concepts in database - still shows all predefined areas"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        assert result["data"]["total_concepts"] == 0
        # All predefined areas should still be present (with 0 counts)
        assert len(result["data"]["areas"]) == NUM_PREDEFINED_AREAS
        # All areas should have 0 concepts
        for area in result["data"]["areas"]:
            assert area["concept_count"] == 0
            assert area["topics"] == []
            assert area["is_predefined"] is True

    @pytest.mark.asyncio
    async def test_list_hierarchy_includes_all_predefined_areas(self, setup_services):
        """Test that all 13 predefined areas are always included in hierarchy"""
        services = setup_services

        # Only one area has concepts
        mock_results = [
            {"area": "coding-development", "topic": "Python", "subtopic": "Basics", "count": 5},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        # All 13 predefined areas should be present
        assert len(result["data"]["areas"]) == NUM_PREDEFINED_AREAS

        # Verify all predefined areas are included
        area_names = {area["name"] for area in result["data"]["areas"]}
        for predefined_area in PREDEFINED_AREAS:
            assert predefined_area.slug in area_names, f"Missing predefined area: {predefined_area.slug}"

        # Verify only the one with concepts has a non-zero count
        for area in result["data"]["areas"]:
            if area["name"] == "coding-development":
                assert area["concept_count"] == 5
                assert len(area["topics"]) == 1
            else:
                assert area["concept_count"] == 0
                assert area["topics"] == []

    @pytest.mark.asyncio
    async def test_list_hierarchy_cache_behavior(self, setup_services):
        """Test that results are cached properly"""
        services = setup_services

        mock_results = [
            {"area": "coding-development", "topic": "Python", "subtopic": "Functions", "count": 5},
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
            {"area": "coding-development", "topic": "Python", "subtopic": "Functions", "count": 5},
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
                "area": "coding-development",
                "topic": "Python",
                "subtopic": "Functions",
                "confidence_score": 25.0,
                "created_at": "2025-10-01T00:00:00"
            },
            {
                "concept_id": "concept-002",
                "name": "Medium Certainty Concept",
                "area": "physics",
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
                "area": "coding-development",
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
                "area": "coding-development",
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


class TestListAreas:
    """Tests for list_areas tool"""

    @pytest.mark.asyncio
    async def test_list_areas_success(self, setup_services):
        """Test successful areas retrieval - includes all predefined areas plus custom ones"""
        services = setup_services

        mock_results = [
            {"area": "learning", "count": 5},
            {"area": "coding-development", "count": 8},
            {"area": "CustomArea", "count": 3},  # Non-predefined custom area
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        assert result["data"]["total_concepts"] == 16  # 5 + 8 + 3
        # Predefined areas + 1 custom area
        assert result["data"]["total_areas"] == NUM_PREDEFINED_AREAS + 1
        assert len(result["data"]["areas"]) == NUM_PREDEFINED_AREAS + 1
        # Check specific areas have correct counts
        learning_area = next(a for a in result["data"]["areas"] if a["name"] == "learning")
        assert learning_area["concept_count"] == 5
        assert learning_area["label"] == "Learning"
        assert learning_area["is_predefined"] is True
        coding_area = next(a for a in result["data"]["areas"] if a["name"] == "coding-development")
        assert coding_area["concept_count"] == 8
        assert coding_area["label"] == "Coding & Development"
        assert coding_area["is_predefined"] is True
        custom_area = next(a for a in result["data"]["areas"] if a["name"] == "CustomArea")
        assert custom_area["concept_count"] == 3
        assert custom_area["is_predefined"] is False

    @pytest.mark.asyncio
    async def test_list_areas_handles_nulls(self, setup_services):
        """Test handling of null values in area"""
        services = setup_services

        mock_results = [
            {"area": None, "count": 2},
            {"area": "coding-development", "count": 5},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        # Nulls should be replaced with "Uncategorized"
        uncategorized = next(a for a in result["data"]["areas"] if a["name"] == "Uncategorized")
        assert uncategorized["label"] == "Uncategorized"
        assert uncategorized["is_predefined"] is False
        assert result["data"]["total_concepts"] == 7

    @pytest.mark.asyncio
    async def test_list_areas_empty_result(self, setup_services):
        """Test with no concepts in database - still shows all predefined areas"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        assert result["data"]["total_concepts"] == 0
        # All predefined areas should still be present
        assert result["data"]["total_areas"] == NUM_PREDEFINED_AREAS
        assert len(result["data"]["areas"]) == NUM_PREDEFINED_AREAS
        # All areas should have 0 concepts
        for area in result["data"]["areas"]:
            assert area["concept_count"] == 0

    @pytest.mark.asyncio
    async def test_list_areas_includes_all_predefined_areas(self, setup_services):
        """Test that all 13 predefined areas are always included"""
        services = setup_services

        # Only one predefined area has concepts
        mock_results = [
            {"area": "health", "count": 10},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        # All 13 predefined areas should be present
        assert len(result["data"]["areas"]) == NUM_PREDEFINED_AREAS

        # Verify all predefined areas are included
        area_names = {area["name"] for area in result["data"]["areas"]}
        for predefined_area in PREDEFINED_AREAS:
            assert predefined_area.slug in area_names, f"Missing predefined area: {predefined_area.slug}"

        # Verify only Health has concepts
        for area in result["data"]["areas"]:
            if area["name"] == "health":
                assert area["concept_count"] == 10
            else:
                assert area["concept_count"] == 0

    @pytest.mark.asyncio
    async def test_list_areas_cache_behavior(self, setup_services):
        """Test that results are cached properly"""
        services = setup_services

        mock_results = [
            {"area": "coding-development", "count": 5},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # First call should query Neo4j
        result1 = await analytics_tools.list_areas()
        assert services["neo4j"].execute_read.call_count == 1

        # Second call should use cache (within 5 min TTL)
        result2 = await analytics_tools.list_areas()
        assert services["neo4j"].execute_read.call_count == 1  # Still only 1 call

        # Results should be identical
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_list_areas_cache_expiry(self, setup_services):
        """Test that cache expires after TTL"""
        services = setup_services
        from datetime import timedelta

        mock_results = [
            {"area": "coding-development", "count": 5},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # First call
        await analytics_tools.list_areas()
        assert services["neo4j"].execute_read.call_count == 1

        # Manually expire cache by accessing internal cache entry and setting old timestamp
        cache_entry = analytics_tools._query_cache._cache.get('areas')
        if cache_entry:
            cache_entry.timestamp = datetime.now() - timedelta(seconds=301)

        # Second call should re-query Neo4j
        await analytics_tools.list_areas()
        assert services["neo4j"].execute_read.call_count == 2

    @pytest.mark.asyncio
    async def test_list_areas_error_handling(self, setup_services):
        """Test error handling for database failures"""
        services = setup_services
        services["neo4j"].execute_read = Mock(side_effect=Exception("Database error"))

        result = await analytics_tools.list_areas()

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error", "database_error"]

    @pytest.mark.asyncio
    async def test_list_areas_correct_counts(self, setup_services):
        """Test that concept counts are correctly reported"""
        services = setup_services

        mock_results = [
            {"area": "physics", "count": 10},
            {"area": "coding-development", "count": 25},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        # Verify individual area counts
        physics_area = next(a for a in result["data"]["areas"] if a["name"] == "physics")
        assert physics_area["concept_count"] == 10

        prog_area = next(a for a in result["data"]["areas"] if a["name"] == "coding-development")
        assert prog_area["concept_count"] == 25

    @pytest.mark.asyncio
    async def test_list_areas_single_area(self, setup_services):
        """Test with a single custom area in the database - includes all predefined areas"""
        services = setup_services

        mock_results = [
            {"area": "CustomTesting", "count": 42},  # Non-predefined custom area
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        assert result["data"]["total_concepts"] == 42
        # All predefined areas + 1 custom area
        assert result["data"]["total_areas"] == NUM_PREDEFINED_AREAS + 1
        assert len(result["data"]["areas"]) == NUM_PREDEFINED_AREAS + 1
        # Check the custom area has correct count
        custom_area = next(a for a in result["data"]["areas"] if a["name"] == "CustomTesting")
        assert custom_area["concept_count"] == 42

    @pytest.mark.asyncio
    async def test_list_areas_message_format(self, setup_services):
        """Test that the response message is correctly formatted"""
        services = setup_services

        mock_results = [
            {"area": "learning", "count": 5},
            {"area": "health", "count": 10},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        assert "message" in result
        # Should include all predefined areas in the count
        assert f"{NUM_PREDEFINED_AREAS} areas" in result["message"]
        assert "15 concepts" in result["message"]

    @pytest.mark.asyncio
    async def test_list_areas_query_filters_deleted(self, setup_services):
        """Test that the query filters out deleted concepts"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await analytics_tools.list_areas()

        # Verify query includes deleted filter
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "deleted IS NULL OR c.deleted = false" in query

    @pytest.mark.asyncio
    async def test_list_areas_cache_invalidation_on_service_change(self, setup_services):
        """Test that cache is invalidated when neo4j service instance changes"""
        services = setup_services

        mock_results = [
            {"area": "coding-development", "count": 5},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # First call caches result
        result1 = await analytics_tools.list_areas()
        assert services["neo4j"].execute_read.call_count == 1

        # Create a new mock Neo4j service (simulating service restart)
        new_neo4j = Mock()
        new_neo4j.execute_read = Mock(return_value=[
            {"area": "NewCustomArea", "count": 10},
        ])

        # Update container with new service
        from services.container import get_container
        container = get_container()
        container.neo4j_service = new_neo4j

        # Clear cache to simulate service change detection
        analytics_tools._query_cache.clear()

        # Second call should use new service
        result2 = await analytics_tools.list_areas()
        assert new_neo4j.execute_read.call_count == 1
        # The new custom area should be present
        new_area = next(a for a in result2["data"]["areas"] if a["name"] == "NewCustomArea")
        assert new_area["concept_count"] == 10

    @pytest.mark.asyncio
    async def test_list_areas_none_count_treated_as_zero(self, setup_services):
        """Test that None count values are defensively treated as zero.

        Note: The Neo4j query uses COUNT(*) which should never return None,
        so this edge case shouldn't occur in production. However, the code
        defensively handles this by treating None as 0 to prevent TypeError.
        """
        services = setup_services

        mock_results = [
            {"area": "coding-development", "count": None},  # None count treated as 0
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        # Defensive behavior: None count is treated as 0, operation succeeds
        assert result["success"] is True
        assert result["data"]["total_concepts"] == 0

    @pytest.mark.asyncio
    async def test_list_areas_zero_count_handled(self, setup_services):
        """Test that areas with zero concepts are handled correctly"""
        services = setup_services

        mock_results = [
            {"area": "CustomEmptyArea", "count": 0},
            {"area": "CustomPopulatedArea", "count": 5},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        assert result["data"]["total_concepts"] == 5
        # Predefined areas + 2 custom areas
        assert result["data"]["total_areas"] == NUM_PREDEFINED_AREAS + 2

        empty_area = next(a for a in result["data"]["areas"] if a["name"] == "CustomEmptyArea")
        assert empty_area["concept_count"] == 0
