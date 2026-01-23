# tests/test_retriever.py
"""Tests for the Retriever module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.query.retriever import Retriever, RetrievedChunk
from src.payloads.schema import ContentPayload
from src.vector.search import SearchResult


def make_search_result(
    content: str,
    file_path: str,
    section: str = "",
    similarity: float = 0.8,
    chunk_id: str = "chunk-1",
) -> SearchResult:
    """Helper to create SearchResult with required fields."""
    return SearchResult(
        content=content,
        file_path=file_path,
        section=section,
        similarity=similarity,
        chunk_id=chunk_id,
    )


class TestRetrievedChunk:
    """Tests for RetrievedChunk dataclass."""

    def test_from_search_result(self):
        """Test creating RetrievedChunk from SearchResult."""
        result = make_search_result(
            content="Test content here",
            file_path="test/file.md",
            section="Test Section",
            similarity=0.85,
        )

        chunk = RetrievedChunk.from_search_result(result)

        assert chunk.content == "Test content here"
        assert chunk.source_file == "test/file.md"
        assert chunk.section == "Test Section"
        assert chunk.similarity == 0.85
        assert len(chunk.content_fingerprint) == 16

    def test_fingerprint_consistency(self):
        """Test that same content produces same fingerprint."""
        result1 = make_search_result(
            content="Same content",
            file_path="file1.md",
            similarity=0.9,
        )
        result2 = make_search_result(
            content="Same content",
            file_path="file2.md",
            similarity=0.8,
            chunk_id="chunk-2",
        )

        chunk1 = RetrievedChunk.from_search_result(result1)
        chunk2 = RetrievedChunk.from_search_result(result2)

        assert chunk1.content_fingerprint == chunk2.content_fingerprint

    def test_fingerprint_difference(self):
        """Test that different content produces different fingerprint."""
        result1 = make_search_result(
            content="Content A",
            file_path="file.md",
            similarity=0.9,
        )
        result2 = make_search_result(
            content="Content B",
            file_path="file.md",
            similarity=0.9,
            chunk_id="chunk-2",
        )

        chunk1 = RetrievedChunk.from_search_result(result1)
        chunk2 = RetrievedChunk.from_search_result(result2)

        assert chunk1.content_fingerprint != chunk2.content_fingerprint

    def test_from_search_result_ignores_missing_payload_fields(self):
        """Payload without category/tags should not raise."""
        payload = ContentPayload.create_basic(
            content_id="chunk-1",
            file_path="test/file.md",
            section="Section",
        )
        result = SearchResult(
            content="Chunk content",
            file_path="test/file.md",
            section="Section",
            similarity=0.91,
            chunk_id="chunk-1",
            payload=payload,
        )

        chunk = RetrievedChunk.from_search_result(result)

        assert chunk.content == "Chunk content"
        assert "category" not in chunk.metadata
        assert "tags" not in chunk.metadata


class TestRetriever:
    """Tests for Retriever class."""

    @pytest.fixture
    def mock_search(self):
        """Create a mock SemanticSearch."""
        return AsyncMock()

    @pytest.fixture
    def retriever(self, mock_search):
        """Create a Retriever with mock search."""
        return Retriever(
            search=mock_search,
            min_similarity=0.3,
            max_chunks=5,
        )

    @pytest.mark.asyncio
    async def test_retrieve_basic(self, retriever, mock_search):
        """Test basic retrieval."""
        mock_search.search.return_value = [
            make_search_result(
                content="First result",
                file_path="file1.md",
                section="Section 1",
                similarity=0.9,
            ),
            make_search_result(
                content="Second result",
                file_path="file2.md",
                section="Section 2",
                similarity=0.8,
                chunk_id="chunk-2",
            ),
        ]

        chunks = await retriever.retrieve("test query")

        assert len(chunks) == 2
        assert chunks[0].content == "First result"
        assert chunks[1].content == "Second result"
        mock_search.search.assert_called_once_with(
            query="test query",
            n_results=20,
            min_similarity=0.3,
        )

    @pytest.mark.asyncio
    async def test_retrieve_with_file_filter(self, retriever, mock_search):
        """Test retrieval with file filter."""
        mock_search.search.return_value = [
            make_search_result(
                content="Match",
                file_path="target.md",
                similarity=0.9,
            ),
            make_search_result(
                content="No match",
                file_path="other.md",
                similarity=0.85,
                chunk_id="chunk-2",
            ),
        ]

        chunks = await retriever.retrieve("test", file_filter="target.md")

        assert len(chunks) == 1
        assert chunks[0].source_file == "target.md"

    @pytest.mark.asyncio
    async def test_deduplication(self, retriever, mock_search):
        """Test that duplicate content is removed."""
        mock_search.search.return_value = [
            make_search_result(
                content="Duplicate content",
                file_path="file1.md",
                similarity=0.9,
            ),
            make_search_result(
                content="Duplicate content",  # Same content
                file_path="file2.md",
                similarity=0.85,
                chunk_id="chunk-2",
            ),
            make_search_result(
                content="Unique content",
                file_path="file3.md",
                similarity=0.8,
                chunk_id="chunk-3",
            ),
        ]

        chunks = await retriever.retrieve("test")

        assert len(chunks) == 2
        # Should keep the first occurrence
        assert chunks[0].source_file == "file1.md"
        assert chunks[1].content == "Unique content"

    @pytest.mark.asyncio
    async def test_max_chunks_limit(self, retriever, mock_search):
        """Test that max_chunks limit is respected."""
        mock_search.search.return_value = [
            make_search_result(
                content=f"Content {i}",
                file_path=f"file{i}.md",
                similarity=0.9 - (i * 0.05),
                chunk_id=f"chunk-{i}",
            )
            for i in range(10)
        ]

        chunks = await retriever.retrieve("test")

        assert len(chunks) == 5  # max_chunks is 5

    @pytest.mark.asyncio
    async def test_reranking_favors_longer_content(self, retriever, mock_search):
        """Test that reranking considers content length."""
        mock_search.search.return_value = [
            make_search_result(
                content="Short",
                file_path="file1.md",
                similarity=0.8,
            ),
            make_search_result(
                content="This is much longer content that provides more context " * 10,
                file_path="file2.md",
                similarity=0.8,  # Same base similarity
                chunk_id="chunk-2",
            ),
        ]

        chunks = await retriever.retrieve("test")

        # Longer content should rank first after reranking
        assert chunks[0].content.startswith("This is much longer"), \
            "Longer content should rank higher after reranking"

    @pytest.mark.asyncio
    async def test_reranking_favors_sections(self, retriever, mock_search):
        """Test that reranking considers section presence."""
        mock_search.search.return_value = [
            make_search_result(
                content="Content without section",
                file_path="file1.md",
                section="",  # No section
                similarity=0.8,
            ),
            make_search_result(
                content="Content with section",
                file_path="file2.md",
                section="Section",
                similarity=0.8,
                chunk_id="chunk-2",
            ),
        ]

        chunks = await retriever.retrieve("content")

        # The one with section should rank higher
        assert chunks[0].section == "Section"

    @pytest.mark.asyncio
    async def test_retrieve_for_file(self, retriever, mock_search):
        """Test retrieve_for_file helper method."""
        mock_search.search.return_value = [
            make_search_result(
                content="Content",
                file_path="target.md",
                similarity=0.9,
            ),
        ]

        chunks = await retriever.retrieve_for_file("query", "target.md", top_k=5)

        assert len(chunks) == 1
        mock_search.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_results(self, retriever, mock_search):
        """Test handling of empty results."""
        mock_search.search.return_value = []

        chunks = await retriever.retrieve("no results query")

        assert len(chunks) == 0
