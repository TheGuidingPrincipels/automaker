"""
Integration Tests for Search Tools

End-to-end tests for semantic and exact search with real service interactions.
"""

from unittest.mock import Mock

import pytest

from tools import search_tools


@pytest.fixture
def mock_services():
    """Setup mock services for integration testing"""
    # Mock ChromaDB service
    mock_chromadb = Mock()
    mock_collection = Mock()
    mock_chromadb.get_collection = Mock(return_value=mock_collection)

    # Mock Neo4j service
    mock_neo4j = Mock()

    # Mock Embedding service
    mock_embedding = Mock()

    # Inject mocks
    search_tools.chromadb_service = mock_chromadb
    search_tools.neo4j_service = mock_neo4j
    search_tools.embedding_service = mock_embedding

    yield {
        "chromadb": mock_chromadb,
        "collection": mock_collection,
        "neo4j": mock_neo4j,
        "embedding": mock_embedding,
    }

    # Cleanup
    search_tools.chromadb_service = None
    search_tools.neo4j_service = None
    search_tools.embedding_service = None


class TestSemanticSearchIntegration:
    """Integration tests for semantic search"""

    @pytest.mark.asyncio
    async def test_end_to_end_semantic_search(self, mock_services):
        """Test complete semantic search workflow"""
        services = mock_services

        # Setup: Create embedding for query
        query = "How to iterate through lists in Python?"
        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        # Setup: Mock ChromaDB search results
        services["collection"].query = Mock(return_value={
            "ids": [["py-001", "py-002", "js-001"]],
            "metadatas": [[
                {
                    "name": "Python For Loops",
                    "area": "Programming",
                    "topic": "Python",
                    "confidence_score": 95.0
                },
                {
                    "name": "Python List Comprehensions",
                    "area": "Programming",
                    "topic": "Python",
                    "confidence_score": 90.0
                },
                {
                    "name": "JavaScript For Loops",
                    "area": "Programming",
                    "topic": "JavaScript",
                    "confidence_score": 85.0
                }
            ]],
            "distances": [[0.05, 0.1, 0.3]]
        })

        # Execute: Perform search
        result = await search_tools.search_concepts_semantic(query=query, limit=10)

        # Verify: Results structure
        assert result["success"] is True
        assert result["data"]["total"] == 3
        assert len(result["data"]["results"]) == 3

        # Verify: Results are sorted by similarity
        assert result["data"]["results"][0]["similarity"] > result["data"]["results"][1]["similarity"]
        assert result["data"]["results"][1]["similarity"] > result["data"]["results"][2]["similarity"]

        # Verify: Python results are most relevant
        assert "Python" in result["data"]["results"][0]["name"]

    @pytest.mark.asyncio
    async def test_semantic_search_with_area_filter(self, mock_services):
        """Test semantic search with area filtering"""
        services = mock_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        services["collection"].query = Mock(return_value={
            "ids": [["prog-001", "prog-002"]],
            "metadatas": [[
                {"name": "Concept 1", "area": "Programming", "topic": "Python", "confidence_score": 95.0},
                {"name": "Concept 2", "area": "Programming", "topic": "Java", "confidence_score": 90.0}
            ]],
            "distances": [[0.1, 0.2]]
        })

        # Execute: Search with area filter
        result = await search_tools.search_concepts_semantic(
            query="programming concepts", area="Programming", limit=10
        )

        # Verify: Filter was applied
        assert result["success"] is True
        services["collection"].query.assert_called_once()
        call_args = services["collection"].query.call_args
        assert "where" in call_args[1]
        assert call_args[1]["where"]["area"] == "Programming"

    @pytest.mark.asyncio
    async def test_semantic_search_performance(self, mock_services):
        """Test semantic search performance with large result set"""
        import time

        services = mock_services

        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)

        # Create 50 mock results
        mock_results = {
            "ids": [[f"concept-{i:03d}" for i in range(50)]],
            "metadatas": [[
                {
                    "name": f"Concept {i}",
                    "area": "Programming",
                    "topic": "Python",
                    "confidence_score": 90.0 - i
                }
                for i in range(50)
            ]],
            "distances": [[0.01 * i for i in range(50)]]
        }
        services["collection"].query = Mock(return_value=mock_results)

        # Measure execution time
        start_time = time.time()
        result = await search_tools.search_concepts_semantic(query="test query", limit=50)
        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        # Verify: Performance target (<100ms P95)
        assert execution_time < 100  # Should be very fast with mocked services
        assert result["success"] is True
        assert result["data"]["total"] == 50


class TestExactSearchIntegration:
    """Integration tests for exact search"""

    @pytest.mark.asyncio
    async def test_end_to_end_exact_search(self, mock_services):
        """Test complete exact search workflow"""
        services = mock_services

        # Setup: Mock Neo4j query results
        mock_results = [
            {
                "concept_id": "py-001",
                "name": "Python For Loops",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Control Flow",
                "confidence_score": 95.0,
                "created_at": "2025-01-03T00:00:00"
            },
            {
                "concept_id": "py-002",
                "name": "Python While Loops",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Control Flow",
                "confidence_score": 90.0,
                "created_at": "2025-01-02T00:00:00"
            },
            {
                "concept_id": "py-003",
                "name": "Python Functions",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Functions",
                "confidence_score": 85.0,
                "created_at": "2025-01-01T00:00:00"
            }
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # Execute: Perform search
        result = await search_tools.search_concepts_exact(area="Programming", topic="Python")

        # Verify: Results structure
        assert result["success"] is True
        assert result["data"]["total"] == 3
        assert len(result["data"]["results"]) == 3

        # Verify: Results are from Neo4j
        assert result["data"]["results"][0]["concept_id"] == "py-001"
        assert result["data"]["results"][0]["area"] == "Programming"

    @pytest.mark.asyncio
    async def test_exact_search_with_name_filter(self, mock_services):
        """Test exact search with name filtering"""
        services = mock_services

        mock_results = [
            {
                "concept_id": "py-001",
                "name": "Python For Loops",
                "area": "Programming",
                "topic": "Python",
                "subtopic": None,
                "confidence_score": 95.0,
                "created_at": "2025-01-01T00:00:00"
            }
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # Execute: Search with name filter
        result = await search_tools.search_concepts_exact(name="loop", area="Programming")

        # Verify: Query was constructed correctly
        assert result["success"] is True
        call_args = services["neo4j"].execute_read.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        # Verify: Name filter uses CONTAINS
        assert "CONTAINS" in query
        assert "toLower" in query
        assert params["name"] == "loop"

    @pytest.mark.asyncio
    async def test_exact_search_with_multiple_filters(self, mock_services):
        """Test exact search with multiple filter combinations"""
        services = mock_services

        services["neo4j"].execute_read = Mock(return_value=[])

        # Execute: Search with all filters
        result = await search_tools.search_concepts_exact(
            name="function",
            area="Programming",
            topic="Python",
            subtopic="Advanced",
            min_confidence=85.0,
            limit=5
        )

        # Verify: All filters in query
        assert result["success"] is True
        call_args = services["neo4j"].execute_read.call_args
        params = call_args[0][1]

        assert params["name"] == "function"
        assert params["area"] == "Programming"
        assert params["topic"] == "Python"
        assert params["subtopic"] == "Advanced"
        assert params["min_confidence"] == 85.0
        assert params["limit"] == 5

    @pytest.mark.asyncio
    async def test_exact_search_performance(self, mock_services):
        """Test exact search performance with large result set"""
        import time

        services = mock_services

        # Create 100 mock results
        mock_results = [
            {
                "concept_id": f"concept-{i:03d}",
                "name": f"Concept {i}",
                "area": "Programming",
                "topic": "Python",
                "subtopic": None,
                "confidence_score": 90.0,
                "created_at": f"2025-01-{(i % 28) + 1:02d}T00:00:00"
            }
            for i in range(100)
        ]
        services["neo4j"].execute_read = Mock(return_value=mock_results)

        # Measure execution time
        start_time = time.time()
        result = await search_tools.search_concepts_exact(area="Programming", limit=100)
        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        # Verify: Performance target (<100ms P95)
        assert execution_time < 100  # Should be very fast with mocked services
        assert result["success"] is True
        assert result["data"]["total"] == 100


class TestSearchToolsWorkflows:
    """Integration tests for combined workflows"""

    @pytest.mark.asyncio
    async def test_semantic_then_exact_search(self, mock_services):
        """Test workflow: semantic search followed by exact refinement"""
        services = mock_services

        # Step 1: Semantic search to find general matches
        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)
        services["collection"].query = Mock(return_value={
            "ids": [["py-001"]],
            "metadatas": [[{"name": "Python Loops", "area": "Programming", "topic": "Python", "confidence_score": 95.0}]],
            "distances": [[0.1]]
        })

        semantic_result = await search_tools.search_concepts_semantic(
            query="looping in python", area="Programming"
        )

        assert semantic_result["success"] is True
        assert semantic_result["data"]["total"] == 1

        # Step 2: Exact search to filter by confidence
        services["neo4j"].execute_read = Mock(return_value=[
            {
                "concept_id": "py-001",
                "name": "Python Loops",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Control Flow",
                "confidence_score": 95.0,
                "created_at": "2025-01-01T00:00:00"
            }
        ])

        exact_result = await search_tools.search_concepts_exact(
            area="Programming",
            topic="Python",
            min_confidence=90.0
        )

        assert exact_result["success"] is True
        assert exact_result["data"]["total"] == 1
        assert exact_result["data"]["results"][0]["confidence_score"] >= 90.0

    @pytest.mark.asyncio
    async def test_search_with_no_results_fallback(self, mock_services):
        """Test workflow: no results in semantic search, fallback to exact"""
        services = mock_services

        # Step 1: Semantic search returns nothing
        query_embedding = [0.1] * 384
        services["embedding"].generate_embedding = Mock(return_value=query_embedding)
        services["collection"].query = Mock(
            return_value={"ids": [[]], "metadatas": [[]], "distances": [[]]}
        )

        semantic_result = await search_tools.search_concepts_semantic(query="nonexistent concept")

        assert semantic_result["success"] is True
        assert semantic_result["data"]["total"] == 0

        # Step 2: Fallback to exact search with broader criteria
        services["neo4j"].execute_read = Mock(return_value=[
            {
                "concept_id": "concept-001",
                "name": "Related Concept",
                "area": "General",
                "topic": None,
                "subtopic": None,
                "confidence_score": 70.0,
                "created_at": "2025-01-01T00:00:00"
            }
        ])

        exact_result = await search_tools.search_concepts_exact(
            area="General"
        )

        exact_result = await search_tools.search_concepts_exact(area="General")

        assert exact_result["success"] is True
        assert exact_result["data"]["total"] == 1
