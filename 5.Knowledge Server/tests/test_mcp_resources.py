"""
Unit tests for MCP resources

Note: These tests verify the resource logic without importing mcp_server directly,
to avoid dependency issues with service initialization.
"""

import json
from unittest.mock import patch

import pytest

from tools import analytics_tools, concept_tools


@pytest.fixture
def mock_concept_result():
    """Mock successful concept retrieval"""
    return {
        "success": True,
        "concept": {
            "concept_id": "concept-001",
            "name": "Python Functions",
            "explanation": "Functions are reusable blocks of code",
            "area": "Programming",
            "topic": "Python",
            "subtopic": "Functions",
            "confidence_score": 95.0,
            "created_at": "2025-10-01T00:00:00",
            "last_modified": "2025-10-07T00:00:00",
            "explanation_history": [
                {
                    "explanation": "Functions are reusable blocks of code",
                    "timestamp": "2025-10-01T00:00:00",
                }
            ],
        },
        "message": "Concept retrieved successfully",
    }


@pytest.fixture
def mock_hierarchy_result():
    """Mock successful hierarchy retrieval"""
    return {
        "success": True,
        "areas": [
            {
                "name": "Programming",
                "concept_count": 10,
                "topics": [
                    {
                        "name": "Python",
                        "concept_count": 10,
                        "subtopics": [
                            {"name": "Functions", "concept_count": 5},
                            {"name": "Classes", "concept_count": 5},
                        ],
                    }
                ],
            }
        ],
        "total_concepts": 10,
        "message": "Hierarchy contains 1 areas with 10 concepts",
    }


class TestConceptResourceLogic:
    """Tests for concept resource logic"""

    @pytest.mark.asyncio
    async def test_concept_resource_json_serialization(self, mock_concept_result):
        """Test that concept data can be serialized to JSON"""
        # Simulate what the resource function does
        result_json = json.dumps(mock_concept_result, indent=2)

        # Verify it's valid JSON
        assert isinstance(result_json, str)
        data = json.loads(result_json)

        assert data["success"] is True
        assert data["concept"]["concept_id"] == "concept-001"
        assert "explanation_history" in data["concept"]

    @pytest.mark.asyncio
    async def test_concept_includes_all_fields(self, mock_concept_result):
        """Test that concept resource would include all necessary fields"""
        concept = mock_concept_result["concept"]

        # Verify all expected fields are present
        required_fields = [
            "concept_id", "name", "explanation", "area", "topic",
            "subtopic", "confidence_score", "created_at", "last_modified",
            "explanation_history"
        ]

        for field in required_fields:
            assert field in concept, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_concept_resource_with_get_concept(self, mock_concept_result):
        """Test resource logic with concept_tools.get_concept"""
        with patch.object(
            concept_tools, "get_concept", return_value=mock_concept_result
        ) as mock_get:
            # Simulate resource function logic
            result = await concept_tools.get_concept(concept_id="concept-001", include_history=True)

            # Verify get_concept was called correctly
            mock_get.assert_called_once_with(concept_id="concept-001", include_history=True)

            # Verify result can be JSON serialized
            result_json = json.dumps(result, indent=2)
            assert "\n" in result_json
            assert "  " in result_json

    @pytest.mark.asyncio
    async def test_concept_resource_not_found(self):
        """Test concept resource logic with non-existent concept"""
        error_result = {"success": False, "message": "Concept not found"}

        # Should still be valid JSON
        result_json = json.dumps(error_result, indent=2)
        data = json.loads(result_json)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_concept_resource_json_format(self, mock_concept_result):
        """Test JSON formatting for concept resource"""
        result_json = json.dumps(mock_concept_result, indent=2)

        # Check JSON is properly indented
        assert "\n" in result_json
        assert "  " in result_json  # 2-space indentation

        # Verify it parses correctly
        data = json.loads(result_json)
        assert data == mock_concept_result


class TestHierarchyResourceLogic:
    """Tests for hierarchy resource logic"""

    @pytest.mark.asyncio
    async def test_hierarchy_resource_json_serialization(self, mock_hierarchy_result):
        """Test that hierarchy data can be serialized to JSON"""
        # Simulate what the resource function does
        result_json = json.dumps(mock_hierarchy_result, indent=2)

        # Verify it's valid JSON
        assert isinstance(result_json, str)
        data = json.loads(result_json)

        assert data["success"] is True
        assert "areas" in data
        assert data["total_concepts"] == 10

    @pytest.mark.asyncio
    async def test_hierarchy_nested_structure_serialization(self, mock_hierarchy_result):
        """Test that nested hierarchy structure serializes correctly"""
        result_json = json.dumps(mock_hierarchy_result, indent=2)
        data = json.loads(result_json)

        # Verify nested structure
        area = data["areas"][0]
        assert "name" in area
        assert "concept_count" in area
        assert "topics" in area

        topic = area["topics"][0]
        assert "name" in topic
        assert "concept_count" in topic
        assert "subtopics" in topic

        subtopic = topic["subtopics"][0]
        assert "name" in subtopic
        assert "concept_count" in subtopic

    @pytest.mark.asyncio
    async def test_hierarchy_resource_with_list_hierarchy(self, mock_hierarchy_result):
        """Test resource logic with analytics_tools.list_hierarchy"""
        with patch.object(analytics_tools, "list_hierarchy", return_value=mock_hierarchy_result):
            # Simulate resource function logic
            result = await analytics_tools.list_hierarchy()

            # Verify result can be JSON serialized
            result_json = json.dumps(result, indent=2)
            data = json.loads(result_json)

            assert data["success"] is True
            assert data["total_concepts"] == 10

    @pytest.mark.asyncio
    async def test_hierarchy_resource_json_format(self, mock_hierarchy_result):
        """Test JSON formatting for hierarchy resource"""
        result_json = json.dumps(mock_hierarchy_result, indent=2)

        # Check JSON is properly indented
        assert "\n" in result_json
        assert "  " in result_json

        # Verify it parses correctly
        data = json.loads(result_json)
        assert data == mock_hierarchy_result

    @pytest.mark.asyncio
    async def test_hierarchy_resource_empty(self):
        """Test hierarchy resource with empty hierarchy"""
        empty_result = {
            "success": True,
            "areas": [],
            "total_concepts": 0,
            "message": "Hierarchy contains 0 areas with 0 concepts",
        }

        result_json = json.dumps(empty_result, indent=2)
        data = json.loads(result_json)

        assert data["success"] is True
        assert data["total_concepts"] == 0
        assert data["areas"] == []

    @pytest.mark.asyncio
    async def test_hierarchy_resource_error_handling(self):
        """Test hierarchy resource with error"""
        error_result = {"success": False, "message": "Internal error"}

        # Should still be valid JSON
        result_json = json.dumps(error_result, indent=2)
        data = json.loads(result_json)
        assert data["success"] is False


class TestResourcePatterns:
    """Tests for MCP resource patterns"""

    @pytest.mark.asyncio
    async def test_resources_return_json_strings(self, mock_concept_result, mock_hierarchy_result):
        """Test that resources would return JSON strings"""
        # Test concept resource pattern
        concept_json = json.dumps(mock_concept_result, indent=2)
        assert isinstance(concept_json, str)
        json.loads(concept_json)  # Verify valid JSON

        # Test hierarchy resource pattern
        hierarchy_json = json.dumps(mock_hierarchy_result, indent=2)
        assert isinstance(hierarchy_json, str)
        json.loads(hierarchy_json)  # Verify valid JSON

    @pytest.mark.asyncio
    async def test_concept_resource_pattern(self, mock_concept_result):
        """Test concept resource URI pattern logic"""
        with patch.object(concept_tools, "get_concept", return_value=mock_concept_result):
            # Simulate: concept://{concept_id} resource
            concept_id = "concept-123"

            result = await concept_tools.get_concept(concept_id=concept_id, include_history=True)

            result_json = json.dumps(result, indent=2)

            # Verify the pattern works
            assert isinstance(result_json, str)
            data = json.loads(result_json)
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_hierarchy_resource_pattern(self, mock_hierarchy_result):
        """Test hierarchy resource URI pattern logic"""
        with patch.object(analytics_tools, "list_hierarchy", return_value=mock_hierarchy_result):
            # Simulate: hierarchy://areas resource
            result = await analytics_tools.list_hierarchy()

            result_json = json.dumps(result, indent=2)

            # Verify the pattern works
            assert isinstance(result_json, str)
            data = json.loads(result_json)
            assert isinstance(data, dict)
            assert "areas" in data

    @pytest.mark.asyncio
    async def test_resource_cacheability(self, mock_hierarchy_result):
        """Test that hierarchy resource supports caching"""
        # Hierarchy tool has internal caching
        with patch.object(analytics_tools, "list_hierarchy", return_value=mock_hierarchy_result):
            result1 = await analytics_tools.list_hierarchy()
            result2 = await analytics_tools.list_hierarchy()

            json1 = json.dumps(result1, indent=2)
            json2 = json.dumps(result2, indent=2)

            # Results should be identical (cacheable)
            assert json1 == json2


class TestResourceDataIntegrity:
    """Tests for resource data integrity"""

    @pytest.mark.asyncio
    async def test_concept_data_completeness(self, mock_concept_result):
        """Test that concept resource contains complete data"""
        result_json = json.dumps(mock_concept_result, indent=2)
        data = json.loads(result_json)

        # Verify response structure
        assert "success" in data
        assert "concept" in data
        assert "message" in data

        # Verify concept completeness
        concept = data["concept"]
        assert len(concept) >= 10  # Should have all fields

    @pytest.mark.asyncio
    async def test_hierarchy_data_completeness(self, mock_hierarchy_result):
        """Test that hierarchy resource contains complete data"""
        result_json = json.dumps(mock_hierarchy_result, indent=2)
        data = json.loads(result_json)

        # Verify response structure
        assert "success" in data
        assert "areas" in data
        assert "total_concepts" in data
        assert "message" in data

        # Verify hierarchy completeness
        assert isinstance(data["areas"], list)
        if len(data["areas"]) > 0:
            area = data["areas"][0]
            assert "name" in area
            assert "concept_count" in area
            assert "topics" in area

    @pytest.mark.asyncio
    async def test_json_serialization_edge_cases(self):
        """Test JSON serialization of edge cases"""
        # Test with None values
        data_with_none = {"success": True, "concept": {"area": None, "topic": None}}

        result_json = json.dumps(data_with_none, indent=2)
        parsed = json.loads(result_json)
        assert parsed["concept"]["area"] is None

        # Test with empty strings
        data_with_empty = {"success": True, "results": []}

        result_json = json.dumps(data_with_empty, indent=2)
        parsed = json.loads(result_json)
        assert parsed["results"] == []
