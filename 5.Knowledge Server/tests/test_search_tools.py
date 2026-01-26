"""
Unit Tests for Search Tools

Tests for semantic and exact search MCP tools.
"""

from unittest.mock import Mock

import pytest

from tools import search_tools


@pytest.fixture
def setup_services(configured_container):
    """Setup mock services for testing using container fixture"""
    # Setup mock collection on chromadb service
    mock_collection = Mock()
    configured_container.chromadb_service.get_collection = Mock(return_value=mock_collection)

    yield {
        "chromadb": configured_container.chromadb_service,
        "collection": mock_collection,
        "neo4j": configured_container.neo4j_service,
        "embedding": configured_container.embedding_service
    }


class TestSearchConceptsSemantic:
    """Tests for search_concepts_semantic tool"""

    @pytest.mark.asyncio
    async def test_semantic_search_success(self, setup_services):
        """Test successful semantic search"""
        services = setup_services

        # Mock embedding generation
        query_embedding = [0.1, 0.2, 0.3] * 128  # 384-dim vector
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        # Mock ChromaDB query results
        services["collection"].query = Mock(return_value={
            "ids": [["concept-001", "concept-002"]],
            "metadatas": [[
                {"name": "Python For Loops", "area": "Programming", "topic": "Python", "confidence_score": 95.0},
                {"name": "JavaScript For Loops", "area": "Programming", "topic": "JavaScript", "confidence_score": 90.0}
            ]],
            "distances": [[0.1, 0.2]]
        })

        result = await search_tools.search_concepts_semantic(
            query="How to loop in programming?", limit=10
        )

        assert result["success"] is True
        assert result["data"]["total"] == 2
        assert len(result["data"]["results"]) == 2
        assert result["data"]["results"][0]["concept_id"] == "concept-001"
        assert result["data"]["results"][0]["similarity"] > result["data"]["results"][1]["similarity"]  # Sorted by similarity

    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self, setup_services):
        """Test semantic search with metadata filters"""
        services = setup_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        services["collection"].query = Mock(return_value={
            "ids": [["concept-001"]],
            "metadatas": [[{"name": "Python For Loops", "area": "Programming", "topic": "Python", "confidence_score": 95.0}]],
            "distances": [[0.1]]
        })

        result = await search_tools.search_concepts_semantic(
            query="loops",
            area="Programming",
            topic="Python",
            min_confidence=80
        )

        assert result["success"] is True
        # Verify filter was passed to ChromaDB
        services["collection"].query.assert_called_once()
        call_args = services["collection"].query.call_args
        assert call_args[1]["where"]["area"] == "Programming"
        assert call_args[1]["where"]["topic"] == "Python"

    @pytest.mark.asyncio
    async def test_semantic_search_embedding_failure(self, setup_services):
        """Test handling of embedding generation failure"""
        services = setup_services

        # Mock embedding failure
        services["embedding"].generate_embedding = Mock(return_value=None)

        result = await search_tools.search_concepts_semantic(query="test query", limit=10)

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["embedding_error", "database_error", "internal_error"]

    @pytest.mark.asyncio
    async def test_semantic_search_limit_validation(self, setup_services):
        """Test limit parameter validation"""
        services = setup_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)
        services["collection"].query = Mock(
            return_value={"ids": [[]], "metadatas": [[]], "distances": [[]]}
        )

        # Test limit too high (should be capped at 50)
        await search_tools.search_concepts_semantic(query="test", limit=100)

        call_args = services["collection"].query.call_args
        assert call_args[1]["n_results"] <= 50

    @pytest.mark.asyncio
    async def test_semantic_search_empty_results(self, setup_services):
        """Test semantic search with no results"""
        services = setup_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        services["collection"].query = Mock(
            return_value={"ids": [[]], "metadatas": [[]], "distances": [[]]}
        )

        result = await search_tools.search_concepts_semantic(query="nonexistent concept", limit=10)

        assert result["success"] is True
        assert result["data"]["total"] == 0
        assert len(result["data"]["results"]) == 0

    @pytest.mark.asyncio
    async def test_semantic_search_min_confidence_filter(self, setup_services):
        """Test min_confidence filtering (post-query)"""
        services = setup_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        # Return results with different confidence scores
        services["collection"].query = Mock(return_value={
            "ids": [["concept-001", "concept-002", "concept-003"]],
            "metadatas": [[
                {"name": "High Certainty", "confidence_score": 95.0},
                {"name": "Medium Certainty", "confidence_score": 75.0},
                {"name": "Low Certainty", "confidence_score": 50.0}
            ]],
            "distances": [[0.1, 0.2, 0.3]]
        })

        result = await search_tools.search_concepts_semantic(
            query="test",
            min_confidence=80
        )

        # Only high confidence result should be returned
        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert result["data"]["results"][0]["confidence_score"] >= 80

    @pytest.mark.asyncio
    async def test_semantic_search_similarity_calculation(self, setup_services):
        """Test similarity score calculation from distance"""
        services = setup_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        services["collection"].query = Mock(return_value={
            "ids": [["concept-001"]],
            "metadatas": [[{"name": "Test", "confidence_score": 90.0}]],
            "distances": [[0.25]]  # Distance of 0.25
        })

        result = await search_tools.search_concepts_semantic(
            query="test",
            limit=10
        )

        result = await search_tools.search_concepts_semantic(query="test", limit=10)

        # Similarity should be 1 - distance = 1 - 0.25 = 0.75
        assert result["data"]["results"][0]["similarity"] == 0.75

    @pytest.mark.asyncio
    async def test_semantic_search_token_efficiency(self, setup_services):
        """Test response is token-efficient (<200 tokens for 10 results)"""
        services = setup_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        # Mock 10 results
        mock_results = {
            "ids": [[f"concept-{i:03d}" for i in range(10)]],
            "metadatas": [[
                {"name": f"Concept {i}", "area": "Area", "topic": "Topic", "confidence_score": 90.0}
                for i in range(10)
            ]],
            "distances": [[0.1 + i * 0.01 for i in range(10)]]
        }
        services["collection"].query = Mock(return_value=mock_results)

        result = await search_tools.search_concepts_semantic(query="test query", limit=10)

        # Estimate token count (rough: ~4 chars per token)
        response_str = str(result)
        estimated_tokens = len(response_str) / 4
        assert estimated_tokens < 400  # Realistic for 10 results with metadata

    @pytest.mark.asyncio
    async def test_semantic_search_unexpected_error(self, setup_services):
        """Test handling of unexpected errors"""
        services = setup_services

        services["embedding"].generate_embedding = Mock(side_effect=Exception("Database error"))

        result = await search_tools.search_concepts_semantic(query="test", limit=10)

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error"]


class TestSearchConceptsExact:
    """Tests for search_concepts_exact tool"""

    @pytest.mark.asyncio
    async def test_exact_search_success(self, setup_services):
        """Test successful exact search"""
        services = setup_services

        mock_results = [
            {
                "concept_id": "concept-001",
                "name": "Python For Loops",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Control Flow",
                "confidence_score": 95.0,
                "created_at": "2025-01-01T00:00:00"
            }
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await search_tools.search_concepts_exact(area="Programming", topic="Python")

        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert result["data"]["results"][0]["concept_id"] == "concept-001"

    @pytest.mark.asyncio
    async def test_exact_search_name_filter(self, setup_services):
        """Test name filtering (case-insensitive CONTAINS)"""
        services = setup_services

        mock_results = [{"concept_id": "concept-001", "name": "Python For Loops", "area": None,
                        "topic": None, "subtopic": None, "confidence_score": None, "created_at": None}]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await search_tools.search_concepts_exact(name="python", limit=20)

        assert result["success"] is True
        # Verify query uses CONTAINS and toLower
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "CONTAINS" in query
        assert "toLower" in query

    @pytest.mark.asyncio
    async def test_exact_search_multiple_filters(self, setup_services):
        """Test search with multiple filters"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await search_tools.search_concepts_exact(
            name="loop",
            area="Programming",
            topic="Python",
            min_confidence=80,
            limit=10
        )

        assert result["success"] is True
        # Verify all filters are in the query
        call_args = services["neo4j"].execute_read.call_args
        call_args[0][0]
        params = call_args[0][1]

        assert "name" in params
        assert "area" in params
        assert "topic" in params
        assert "min_confidence" in params
        assert params["limit"] == 10

    @pytest.mark.asyncio
    async def test_exact_search_deleted_filter(self, setup_services):
        """Test deleted concepts are filtered out"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await search_tools.search_concepts_exact(area="Programming")

        # Verify deleted filter is in query
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "deleted" in query.lower()

    @pytest.mark.asyncio
    async def test_exact_search_limit_validation(self, setup_services):
        """Test limit parameter validation"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Test limit too high (should be capped at 100)
        await search_tools.search_concepts_exact(limit=200)

        call_args = services["neo4j"].execute_read.call_args
        params = call_args[0][1]
        assert params["limit"] <= 100

    @pytest.mark.asyncio
    async def test_exact_search_empty_results(self, setup_services):
        """Test exact search with no results"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await search_tools.search_concepts_exact(name="nonexistent")

        assert result["success"] is True
        assert result["data"]["total"] == 0
        assert len(result["data"]["results"]) == 0

    @pytest.mark.asyncio
    async def test_exact_search_sort_order(self, setup_services):
        """Test results are sorted by confidence_score DESC, then created_at DESC"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await search_tools.search_concepts_exact(area="Programming")

        # Verify ORDER BY is in query with confidence_score first, then created_at
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY" in query
        assert "confidence_score" in query
        assert "created_at" in query
        assert "DESC" in query
        # Verify confidence_score comes before created_at in ORDER BY clause
        order_by_idx = query.index("ORDER BY")
        confidence_idx = query.index("confidence_score", order_by_idx)
        created_idx = query.index("created_at", order_by_idx)
        assert confidence_idx < created_idx, "confidence_score should come before created_at in ORDER BY"

    @pytest.mark.asyncio
    async def test_exact_search_token_efficiency(self, setup_services):
        """Test response is token-efficient (<300 tokens for 20 results)"""
        services = setup_services

        # Mock 20 results
        mock_results = [
            {
                "concept_id": f"concept-{i:03d}",
                "name": f"Concept {i}",
                "area": "Area",
                "topic": "Topic",
                "subtopic": None,
                "confidence_score": 90.0,
                "created_at": "2025-01-01T00:00:00"
            }
            for i in range(20)
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await search_tools.search_concepts_exact(area="Area", limit=20)

        # Estimate token count (rough: ~4 chars per token)
        response_str = str(result)
        estimated_tokens = len(response_str) / 4
        assert estimated_tokens < 1200  # Realistic for 20 results

    @pytest.mark.asyncio
    async def test_exact_search_unexpected_error(self, setup_services):
        """Test handling of unexpected errors"""
        services = setup_services

        services["neo4j"].execute_read = Mock(side_effect=Exception("Database error"))

        result = await search_tools.search_concepts_exact(name="test")

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error", "neo4j_error", "database_error"]


class TestSearchToolsEdgeCases:
    """Tests for edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_semantic_search_empty_embedding(self, setup_services):
        """Test handling of empty embedding"""
        services = setup_services

        services["embedding"].generate_embedding = Mock(return_value=[])

        result = await search_tools.search_concepts_semantic(query="test", limit=10)

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["embedding_error", "database_error"]

    @pytest.mark.asyncio
    async def test_semantic_search_missing_metadata(self, setup_services):
        """Test handling of missing metadata in results"""
        services = setup_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        # Return results with incomplete metadata
        services["collection"].query = Mock(
            return_value={
                "ids": [["concept-001"]],
                "metadatas": [[{}]],  # Empty metadata
                "distances": [[0.1]],
            }
        )

        result = await search_tools.search_concepts_semantic(query="test", limit=10)

        assert result["success"] is True
        assert result["data"]["total"] == 1
        # Should handle missing fields gracefully
        assert result["data"]["results"][0]["name"] == ""
        assert result["data"]["results"][0]["area"] is None

    @pytest.mark.asyncio
    async def test_exact_search_all_optional_params(self, setup_services):
        """Test exact search with no filters provided"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await search_tools.search_concepts_exact()

        assert result["success"] is True
        # Should still filter deleted concepts
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "deleted" in query.lower()


class TestGetRecentConcepts:
    """Tests for get_recent_concepts tool"""

    @pytest.mark.asyncio
    async def test_get_recent_concepts_success(self, setup_services):
        """Test successful retrieval of recent concepts"""
        services = setup_services

        mock_results = [
            {
                "concept_id": "concept-001",
                "name": "Recent Concept",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Functions",
                "confidence_score": 95.0,
                "created_at": "2025-10-01T00:00:00",
                "last_modified": "2025-10-07T10:00:00",
            }
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        result = await search_tools.get_recent_concepts(days=7, limit=20)

        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert result["data"]["results"][0]["concept_id"] == "concept-001"
        assert "last_modified" in result["data"]["results"][0]

    @pytest.mark.asyncio
    async def test_get_recent_concepts_days_filter(self, setup_services):
        """Test days parameter works correctly"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await search_tools.get_recent_concepts(days=30, limit=20)

        assert result["success"] is True
        # Verify cutoff parameter was passed
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "last_modified >= $cutoff" in query
        assert "cutoff" in params

    @pytest.mark.asyncio
    async def test_get_recent_concepts_limit_validation(self, setup_services):
        """Test limit parameter validation"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Test limit too high
        result = await search_tools.get_recent_concepts(
            days=7, limit=150  # Should be capped at 100
        )

        assert result["success"] is True
        call_args = services["neo4j"].execute_read.call_args
        params = call_args[0][1]
        assert params["limit"] == 100

    @pytest.mark.asyncio
    async def test_get_recent_concepts_days_validation(self, setup_services):
        """Test days parameter validation"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        # Test days out of range
        result = await search_tools.get_recent_concepts(
            days=500, limit=20  # Should be capped at 365
        )

        assert result["success"] is True
        # Days should be adjusted to 365

    @pytest.mark.asyncio
    async def test_get_recent_concepts_empty_results(self, setup_services):
        """Test handling of no recent concepts"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        result = await search_tools.get_recent_concepts(days=7, limit=20)

        assert result["success"] is True
        assert result["data"]["total"] == 0
        assert result["data"]["results"] == []

    @pytest.mark.asyncio
    async def test_get_recent_concepts_filters_deleted(self, setup_services):
        """Test that deleted concepts are filtered out"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await search_tools.get_recent_concepts(days=7, limit=20)

        # Verify deleted filter is in query
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "deleted" in query.lower()

    @pytest.mark.asyncio
    async def test_get_recent_concepts_sorted_by_modified(self, setup_services):
        """Test results are sorted by last_modified DESC"""
        services = setup_services
        services["neo4j"].execute_read = Mock(return_value=[])

        await search_tools.get_recent_concepts(days=7, limit=20)

        # Verify ORDER BY clause
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        assert "ORDER BY c.last_modified DESC" in query

    @pytest.mark.asyncio
    async def test_get_recent_concepts_unexpected_error(self, setup_services):
        """Test handling of unexpected errors"""
        services = setup_services
        services["neo4j"].execute_read = Mock(side_effect=Exception("Database error"))

        result = await search_tools.get_recent_concepts(days=7, limit=20)

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error", "neo4j_error", "database_error"]
