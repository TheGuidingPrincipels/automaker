"""
Tests for MCP list_areas tool contract.

These tests verify that the MCP list_areas tool properly delegates to
analytics_tools.list_areas() and returns the expected response format.
"""

from unittest.mock import Mock

import pytest

from config import PREDEFINED_AREAS
from tools import analytics_tools

# Number of predefined areas (used in tests)
NUM_PREDEFINED_AREAS = len(PREDEFINED_AREAS)


@pytest.fixture
def setup_services(configured_container):
    """Setup services for tests using container fixture."""
    # Clear cache to ensure fresh state for each test
    analytics_tools._query_cache.clear()

    return {
        "neo4j": configured_container.neo4j_service
    }


class TestListAreasTool:
    """Tests for MCP list_areas tool contract."""

    @pytest.mark.asyncio
    async def test_list_areas_returns_all_predefined_areas(self, setup_services):
        """list_areas should return all predefined areas with concept counts."""
        services = setup_services

        # Mock Neo4j to return some areas with counts
        mock_results = [
            {"area": "coding-development", "count": 5},
            {"area": "learning", "count": 3},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # Call analytics_tools.list_areas (same function MCP tool delegates to)
        result = await analytics_tools.list_areas()

        assert result["success"] is True
        data = result["data"]
        assert data["total_areas"] == NUM_PREDEFINED_AREAS
        assert data["total_concepts"] == 8  # 5 + 3

        # All predefined areas should be present
        area_names = {a["name"] for a in data["areas"]}
        for predefined in PREDEFINED_AREAS:
            assert predefined.slug in area_names, f"Missing predefined area: {predefined.slug}"

    @pytest.mark.asyncio
    async def test_list_areas_response_format(self, setup_services):
        """list_areas should return correct response format with all required fields."""
        services = setup_services

        mock_results = [
            {"area": "coding-development", "count": 10},
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        assert "data" in result
        assert "message" in result

        data = result["data"]
        assert "total_areas" in data
        assert "total_concepts" in data
        assert "areas" in data

        # Check area structure
        coding_area = next(a for a in data["areas"] if a["name"] == "coding-development")
        assert "name" in coding_area
        assert "label" in coding_area
        assert "description" in coding_area
        assert "concept_count" in coding_area
        assert "is_predefined" in coding_area

        assert coding_area["concept_count"] == 10
        assert coding_area["is_predefined"] is True
        assert coding_area["label"] == "Coding & Development"

    @pytest.mark.asyncio
    async def test_list_areas_empty_database(self, setup_services):
        """list_areas should return all predefined areas even with empty database."""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        data = result["data"]
        assert data["total_areas"] == NUM_PREDEFINED_AREAS
        assert data["total_concepts"] == 0
        assert len(data["areas"]) == NUM_PREDEFINED_AREAS

        # All areas should have 0 concepts
        for area in data["areas"]:
            assert area["concept_count"] == 0
            assert area["is_predefined"] is True

    @pytest.mark.asyncio
    async def test_list_areas_includes_custom_areas(self, setup_services):
        """list_areas should include custom areas not in predefined list."""
        services = setup_services

        mock_results = [
            {"area": "coding-development", "count": 5},
            {"area": "CustomDomain", "count": 3},  # Non-predefined custom area
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await analytics_tools.list_areas()

        assert result["success"] is True
        data = result["data"]
        # All predefined areas + 1 custom area
        assert data["total_areas"] == NUM_PREDEFINED_AREAS + 1
        assert data["total_concepts"] == 8

        # Check custom area is present and marked correctly
        custom_area = next(a for a in data["areas"] if a["name"] == "CustomDomain")
        assert custom_area["concept_count"] == 3
        assert custom_area["is_predefined"] is False

    @pytest.mark.asyncio
    async def test_list_areas_error_handling(self, setup_services):
        """list_areas should handle database errors gracefully."""
        services = setup_services
        services["neo4j"].execute_read = Mock(side_effect=Exception("Database error"))

        result = await analytics_tools.list_areas()

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error", "database_error"]


class TestListAreasToolAvailability:
    """Tests for list_areas tool availability reporting."""

    @pytest.mark.asyncio
    async def test_list_areas_in_tool_availability(self):
        """list_areas should be reported in tool availability."""
        from tools.service_utils import get_available_tools

        result = get_available_tools()

        # list_areas should be in one of the lists
        all_tools = result["available"] + result["unavailable"]
        assert "list_areas" in all_tools
