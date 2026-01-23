# tests/test_semantic_search.py
"""Tests for semantic search interface."""

import os
import anyio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.vector.search import SemanticSearch, SearchResult
from src.vector.store import QdrantVectorStore
from src.payloads.schema import ContentPayload, ContentType, TaxonomyPath


class MockVectorStore:
    """Mock vector store for testing semantic search."""

    def __init__(self):
        self.search_results = []

    async def search(self, query, n_results=10, **kwargs):
        """Return mock search results."""
        return self.search_results[:n_results]

    async def get_stats(self):
        """Return mock stats."""
        return {
            "total_points": 100,
            "vectors_count": 100,
            "indexed_vectors_count": 100,
            "status": "green",
            "embedding_dimensions": 1024,
            "provider": "mock",
            "model": "mock-embed",
        }


class MockIndexer:
    """Mock indexer for testing."""

    def __init__(self):
        self.indexed = False
        self.index_results = {}

    async def index_all(self, force=False):
        """Mock index all."""
        self.indexed = True
        return self.index_results

    def extract_chunks(self, content: str, file_path: str):
        """Basic chunk extraction for hydration tests."""
        text = content.strip()
        if len(text) <= 50:
            return []
        payload = ContentPayload.create_basic(
            content_id="mock-chunk",
            file_path=file_path,
            section="",
            chunk_index=0,
            content_hash="",
            source_file=file_path,
        )
        return [{"id": "mock-chunk", "content": text, "payload": payload}]


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_search_result(self):
        """Create a search result."""
        result = SearchResult(
            content="Some matching content",
            file_path="tech/auth.md",
            section="JWT Tokens",
            similarity=0.85,
            chunk_id="uuid-123",
        )

        assert result.content == "Some matching content"
        assert result.file_path == "tech/auth.md"
        assert result.section == "JWT Tokens"
        assert result.similarity == 0.85
        assert result.chunk_id == "uuid-123"
        assert result.taxonomy_path is None
        assert result.content_type is None

    def test_search_result_with_phase_3a_fields(self):
        """Create result with Phase 3A fields."""
        payload = ContentPayload.create_basic(
            content_id="uuid-456",
            file_path="design/patterns.md",
        )

        result = SearchResult(
            content="",
            file_path="design/patterns.md",
            section="Factory",
            similarity=0.72,
            chunk_id="uuid-456",
            taxonomy_path="Design/Patterns/Factory",
            content_type="blueprint",
            payload=payload,
        )

        assert result.taxonomy_path == "Design/Patterns/Factory"
        assert result.content_type == "blueprint"
        assert result.payload is not None


class TestSemanticSearch:
    """Tests for SemanticSearch class."""

    @pytest.fixture
    def mock_store(self):
        """Create mock vector store."""
        return MockVectorStore()

    @pytest.fixture
    def search(self, mock_store, tmp_path):
        """Create semantic search with mock store."""
        ss = SemanticSearch(
            vector_store=mock_store,
            library_path=str(tmp_path),
        )
        # Replace indexer with mock
        ss.indexer = MockIndexer()
        return ss

    @pytest.fixture
    async def sample_search_results(self, tmp_path):
        """Create sample search results with backing files."""
        contents = {
            "tech/auth.md": (
                "# JWT Tokens\n\n"
                "JWT tokens are used for stateless authentication and claims. "
                "This content is long enough to be indexed."
            ),
            "tech/security.md": (
                "# Token Validation\n\n"
                "Token validation ensures integrity and expiration checks. "
                "This content is long enough to be indexed."
            ),
            "general/notes.md": (
                "# Random Notes\n\n"
                "Some general notes that are long enough to be indexed."
            ),
        }

        for rel_path, content in contents.items():
            full_path = tmp_path / rel_path
            await anyio.Path(full_path.parent).mkdir(parents=True, exist_ok=True)
            await anyio.Path(full_path).write_text(content, encoding="utf-8")

        return [
            {
                "id": "chunk-1",
                "score": 0.92,
                "payload": ContentPayload.create_basic(
                    content_id="chunk-1",
                    file_path="tech/auth.md",
                    section="JWT Tokens",
                ),
            },
            {
                "id": "chunk-2",
                "score": 0.78,
                "payload": ContentPayload.create_basic(
                    content_id="chunk-2",
                    file_path="tech/security.md",
                    section="Token Validation",
                ),
            },
            {
                "id": "chunk-3",
                "score": 0.45,  # Below default threshold
                "payload": ContentPayload.create_basic(
                    content_id="chunk-3",
                    file_path="general/notes.md",
                    section="Random",
                ),
            },
        ]

    @pytest.mark.asyncio
    async def test_search_basic(self, search, mock_store, sample_search_results):
        """Basic search returns results."""
        mock_store.search_results = sample_search_results

        results = await search.search(
            query="JWT authentication tokens",
            n_results=5,
        )

        # Should return results above threshold (0.5 default)
        assert len(results) == 2  # Third result is below threshold

        # Should be SearchResult objects
        assert all(isinstance(r, SearchResult) for r in results)

        # Should be sorted by similarity
        assert results[0].similarity >= results[1].similarity

    @pytest.mark.asyncio
    async def test_search_with_min_similarity(self, search, mock_store, sample_search_results):
        """Search respects min_similarity threshold."""
        mock_store.search_results = sample_search_results

        # Lower threshold to include all
        results = await search.search(
            query="test",
            n_results=10,
            min_similarity=0.4,
        )

        assert len(results) == 3  # All results included

        # Higher threshold excludes more
        results_high = await search.search(
            query="test",
            n_results=10,
            min_similarity=0.8,
        )

        assert len(results_high) == 1  # Only highest score

    @pytest.mark.asyncio
    async def test_search_respects_n_results(self, search, mock_store, sample_search_results):
        """Search respects n_results limit."""
        mock_store.search_results = sample_search_results

        results = await search.search(
            query="test",
            n_results=1,
            min_similarity=0.4,
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_extracts_fields_correctly(self, search, mock_store, sample_search_results):
        """Search extracts all fields from payload."""
        mock_store.search_results = sample_search_results

        results = await search.search(
            query="test",
            n_results=5,
        )

        first = results[0]
        assert first.file_path == "tech/auth.md"
        assert first.section == "JWT Tokens"
        assert first.similarity == 0.92
        assert first.chunk_id == "chunk-1"
        assert first.payload is not None

    @pytest.mark.asyncio
    async def test_search_populates_content_from_library(
        self, search, mock_store, tmp_path
    ):
        """Search fills content from library files when missing."""
        file_path = tmp_path / "tech" / "auth.md"
        await anyio.Path(file_path.parent).mkdir(parents=True, exist_ok=True)
        content = (
            "# Authentication\n\n"
            "Authentication uses tokens and claims for access control. "
            "This paragraph is long enough to be indexed."
        )
        await anyio.Path(file_path).write_text(content, encoding="utf-8")

        payload = ContentPayload.create_basic(
            content_id="chunk-1",
            file_path="tech/auth.md",
            section="Authentication",
            chunk_index=0,
            content_hash="",
            source_file="tech/auth.md",
        )

        mock_store.search_results = [
            {"id": "chunk-1", "score": 0.92, "payload": payload},
        ]

        results = await search.search(
            query="auth tokens",
            n_results=1,
            min_similarity=0.4,
        )

        assert results
        assert results[0].content
        assert "Authentication uses tokens" in results[0].content

    @pytest.mark.asyncio
    async def test_find_merge_candidates(self, search, mock_store, sample_search_results):
        """Find merge candidates returns high-similarity results."""
        mock_store.search_results = sample_search_results

        candidates = await search.find_merge_candidates(
            content="JWT token validation patterns",
            threshold=0.7,
        )

        # Should only return results above threshold (0.7)
        assert len(candidates) == 2
        assert all(c.similarity >= 0.7 for c in candidates)

    @pytest.mark.asyncio
    async def test_find_merge_candidates_excludes_file(
        self, search, mock_store, sample_search_results
    ):
        """Find merge candidates can exclude source file."""
        mock_store.search_results = sample_search_results

        candidates = await search.find_merge_candidates(
            content="JWT tokens",
            threshold=0.5,
            exclude_file="tech/auth.md",
        )

        # Should not include the excluded file
        file_paths = [c.file_path for c in candidates]
        assert "tech/auth.md" not in file_paths

    @pytest.mark.asyncio
    async def test_ensure_indexed_calls_indexer(self, search):
        """Ensure indexed calls the indexer."""
        result = await search.ensure_indexed(force=True)

        assert search.indexer.indexed is True
        assert result["status"] == "indexed"

    @pytest.mark.asyncio
    async def test_ensure_indexed_without_indexer(self, mock_store):
        """Ensure indexed returns status when no indexer."""
        ss = SemanticSearch(
            vector_store=mock_store,
            library_path=None,
        )

        result = await ss.ensure_indexed()

        assert result["status"] == "no_indexer"

    @pytest.mark.asyncio
    async def test_get_stats(self, search):
        """Get stats returns store statistics."""
        stats = await search.get_stats()

        assert "total_points" in stats
        assert "embedding_dimensions" in stats
        assert stats["total_points"] == 100


class TestSemanticSearchIntegration:
    """Integration tests for semantic search (if Qdrant is available)."""

    @pytest.mark.integration
    @pytest.mark.skipif(
        os.getenv("RUN_QDRANT_INTEGRATION") != "1"
        or not os.getenv("MISTRAL_API_KEY"),
        reason=(
            "Set RUN_QDRANT_INTEGRATION=1 and MISTRAL_API_KEY; "
            "requires running Qdrant instance"
        ),
    )
    @pytest.mark.asyncio
    async def test_full_search_flow(self, tmp_path):
        """Full search flow with real components."""
        # This test requires:
        # 1. Running Qdrant instance
        # 2. Valid embedding API key

        from src.vector.store import QdrantVectorStore
        from src.vector.indexer import LibraryIndexer

        # Create test files
        await anyio.Path(tmp_path / "test.md").write_text(
            "# Test Document\n\n"
            "This is content about machine learning and neural networks."
        )

        store = QdrantVectorStore(
            url="localhost",
            port=6333,
            embedding_config={
                "provider": "mistral",
                "model": "mistral-embed",
            },
        )

        search = SemanticSearch(
            vector_store=store,
            library_path=str(tmp_path),
        )

        # Index the library
        await search.ensure_indexed(force=True)

        # Search
        results = await search.search(
            query="machine learning",
            n_results=5,
        )

        assert len(results) > 0
