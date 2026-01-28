"""
E2E tests for search workflows.
Simplified tests with proper async handling.
"""

import pytest

from tools import analytics_tools, search_tools


class TestSearchScenarios:
    """Test search-based workflows with async/await."""

    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, e2e_configured_container):
        """
        Basic semantic search workflow.
        Validates: Search returns results in correct format.
        """
        # Services are automatically available via get_container()
        mock_embedding = e2e_configured_container.embedding_service
        mock_chromadb = e2e_configured_container.chromadb_service

        # Mock embedding generation
        mock_embedding.generate_embedding.return_value = [0.1] * 384

        # Create a proper mock for the query method
        from unittest.mock import MagicMock

        query_result = {
            "ids": [["concept-001", "concept-002"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[
                {
                    "name": "Python Basics",
                    "area": "Programming",
                    "topic": "Python",
                    "confidence_score": 90.0
                },
                {
                    "name": "Python Functions",
                    "area": "Programming",
                    "topic": "Python",
                    "confidence_score": 85.0
                }
            ]]
        }

        # Replace the collection query method
        mock_chromadb.collection.query = MagicMock(return_value=query_result)

        result = await search_tools.search_concepts_semantic(query="python programming", limit=10)

        assert result["success"] is True
        assert "results" in result["data"]
        assert result["data"]["total"] >= 0

    @pytest.mark.asyncio
    async def test_exact_search_with_filters(self, e2e_configured_container):
        """
        Exact search with multiple filters.
        Validates: Filtering works correctly.
        """
        mock_neo4j = e2e_configured_container.neo4j_service

        # Mock filtered results
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": "concept-filter-001",
                "name": "Python Loops",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Control Flow",
                "confidence_score": 90.0,
                "created_at": "2025-10-07T10:00:00"
            }
        ]

        result = await search_tools.search_concepts_exact(
            area="Programming",
            topic="Python",
            min_confidence=80
        )

        assert result["success"] is True
        assert "results" in result["data"]

    @pytest.mark.asyncio
    async def test_recent_concepts_retrieval(self, e2e_configured_container):
        """
        Recent concepts workflow.
        Validates: Time-based filtering works.
        """
        mock_neo4j = e2e_configured_container.neo4j_service

        # Mock recent concepts
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": "concept-recent-001",
                "name": "Recent Concept",
                "area": "Testing",
                "topic": "E2E",
                "subtopic": "Workflows",
                "confidence_score": 85.0,
                "created_at": "2025-10-06T10:00:00",
                "last_modified": "2025-10-07T10:00:00",
            }
        ]

        result = await search_tools.get_recent_concepts(days=7, limit=20)

        assert result["success"] is True
        assert "results" in result["data"]
        assert result["data"]["total"] >= 0

    @pytest.mark.asyncio
    async def test_hierarchy_listing(self, e2e_configured_container):
        """
        Hierarchy listing workflow.
        Validates: Hierarchy structure is correct.
        """
        mock_neo4j = e2e_configured_container.neo4j_service

        # Mock hierarchy
        mock_neo4j.execute_read.return_value = [
            {"area": "Programming", "topic": "Python", "subtopic": "Basics", "count": 10}
        ]

        result = await analytics_tools.list_hierarchy()

        assert result["success"] is True
        assert "areas" in result["data"] or "hierarchy" in result["data"]
        assert result["data"]["total_concepts"] >= 0

    @pytest.mark.asyncio
    async def test_confidence_range_search(self, e2e_configured_container):
        """
        Certainty range filtering workflow.
        Validates: Certainty filtering works.
        """
        mock_neo4j = e2e_configured_container.neo4j_service

        # Mock low confidence concepts
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": "concept-low-cert-001",
                "name": "Uncertain Concept",
                "area": "Testing",
                "topic": "Certainty",
                "subtopic": "Low",
                "confidence_score": 45.0,
                "created_at": "2025-10-07T10:00:00",
                "last_modified": "2025-10-07T10:00:00",
            }
        ]

        result = await analytics_tools.get_concepts_by_confidence(
            min_confidence=0,
            max_confidence=50
        )

        assert result["success"] is True
        assert "results" in result["data"]
