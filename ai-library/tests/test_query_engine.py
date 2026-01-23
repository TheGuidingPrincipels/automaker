# tests/test_query_engine.py
"""Tests for the QueryEngine module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil

from src.query.engine import QueryEngine, QueryResult, ConversationNotFoundError
from src.query.retriever import RetrievedChunk
from src.sdk.client import SDKResponse
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


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_query_result_creation(self):
        """Test creating a QueryResult."""
        result = QueryResult(
            answer="Test answer",
            sources=["file.md"],
            confidence=0.8,
            conversation_id="conv-123",
            related_topics=["topic1", "topic2"],
        )

        assert result.answer == "Test answer"
        assert result.sources == ["file.md"]
        assert result.confidence == 0.8
        assert result.conversation_id == "conv-123"
        assert len(result.related_topics) == 2

    def test_query_result_defaults(self):
        """Test QueryResult default values."""
        result = QueryResult(
            answer="Answer",
            sources=[],
            confidence=0.5,
        )

        assert result.conversation_id is None
        assert result.related_topics == []
        assert result.raw_chunks == []


class TestQueryEngine:
    """Tests for QueryEngine class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for conversations."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def mock_search(self):
        """Create mock SemanticSearch."""
        search = AsyncMock()
        search.search.return_value = [
            make_search_result(
                content="Test content about Python",
                file_path="python/basics.md",
                section="Introduction",
                similarity=0.85,
            ),
        ]
        return search

    @pytest.fixture
    def mock_sdk_client(self):
        """Create mock SDK client."""
        client = AsyncMock()
        client.query_text.return_value = SDKResponse(
            success=True,
            raw_response=(
                "Python is a programming language [source: python/basics.md]. "
                "It's widely used for data science."
            ),
        )
        return client

    @pytest.fixture
    def engine(self, mock_search, mock_sdk_client, temp_dir):
        """Create QueryEngine with mocks."""
        return QueryEngine(
            search=mock_search,
            sdk_client=mock_sdk_client,
            storage_dir=temp_dir,
        )

    @pytest.mark.asyncio
    async def test_query_basic(self, engine, mock_search, mock_sdk_client):
        """Test basic query execution."""
        result = await engine.query("What is Python?")

        assert result.answer is not None
        assert "[source:" not in result.answer  # Citations extracted
        assert result.confidence > 0
        assert result.conversation_id is not None

        # Verify SDK was called
        mock_sdk_client.query_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_no_results(self, engine, mock_search):
        """Test query with no search results."""
        mock_search.search.return_value = []

        result = await engine.query("Something not in library")

        assert "couldn't find" in result.answer
        assert result.confidence == 0.0
        assert result.sources == []

    @pytest.mark.asyncio
    async def test_query_with_conversation(self, engine, mock_search, mock_sdk_client):
        """Test continuing a conversation."""
        # First query creates conversation
        result1 = await engine.query("What is Python?")
        conv_id = result1.conversation_id

        # Continue with same conversation
        result2 = await engine.query(
            "Tell me more",
            conversation_id=conv_id,
        )

        assert result2.conversation_id == conv_id

        # Check conversation was used in prompt
        call_args = mock_sdk_client.query_text.call_args_list[-1]
        user_prompt = call_args.kwargs.get("user_prompt", "")
        # Should include conversation history
        assert "What is Python?" in user_prompt or "Previous conversation" in user_prompt

    @pytest.mark.asyncio
    async def test_query_missing_conversation_id_raises(
        self, engine, mock_sdk_client
    ):
        """Test missing conversation ID raises."""
        with pytest.raises(ConversationNotFoundError):
            await engine.query(
                "What is Python?",
                conversation_id="missing-conv",
            )

    @pytest.mark.asyncio
    async def test_query_sdk_error_raises(self, engine, mock_sdk_client):
        """Test SDK errors surface."""
        mock_sdk_client.query_text.return_value = SDKResponse(
            success=False,
            raw_response="Model error",
            error="Model error",
        )

        with pytest.raises(RuntimeError):
            await engine.query("What is Python?")

    @pytest.mark.asyncio
    async def test_search_only(self, engine, mock_search):
        """Test search_only method."""
        results = await engine.search_only("test query")

        assert len(results) == 1
        mock_search.search.assert_called_with(
            query="test query",
            n_results=10,
            min_similarity=0.3,
        )

    @pytest.mark.asyncio
    async def test_confidence_calculation(self, engine, mock_search, mock_sdk_client):
        """Test confidence calculation."""
        # High similarity results
        mock_search.search.return_value = [
            make_search_result(
                content="Content " * 50,  # Longer content
                file_path=f"file{i}.md",
                section="Section",
                similarity=0.9,
                chunk_id=f"chunk-{i}",
            )
            for i in range(5)
        ]

        result = await engine.query("test")

        # Should have decent confidence
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_confidence_low_similarity(self, engine, mock_search, mock_sdk_client):
        """Test confidence with low similarity results."""
        mock_search.search.return_value = [
            make_search_result(
                content="Short",
                file_path="file.md",
                section="",
                similarity=0.4,  # Low similarity
            ),
        ]

        result = await engine.query("test")

        # Should have lower confidence
        assert result.confidence < 0.8

    @pytest.mark.asyncio
    async def test_related_topics_extraction(self, engine, mock_search, mock_sdk_client):
        """Test related topics extraction."""
        mock_search.search.return_value = [
            make_search_result(
                content="Python content",
                file_path="programming/python.md",
                section="Functions",
                similarity=0.9,
            ),
            make_search_result(
                content="More content",
                file_path="tutorials/basics.md",
                section="Variables",
                similarity=0.85,
                chunk_id="chunk-2",
            ),
        ]

        result = await engine.query("Python basics")

        # Should extract topics from sections and categories
        assert len(result.related_topics) > 0

    @pytest.mark.asyncio
    async def test_get_conversation(self, engine):
        """Test getting a conversation."""
        # Create via query
        result = await engine.query("Initial question")

        # Retrieve it
        conv = await engine.get_conversation(result.conversation_id)

        assert conv is not None
        assert conv.id == result.conversation_id
        assert len(conv.turns) == 2  # user + assistant

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, engine):
        """Test getting nonexistent conversation."""
        conv = await engine.get_conversation("nonexistent")

        assert conv is None

    @pytest.mark.asyncio
    async def test_list_conversations(self, engine):
        """Test listing conversations."""
        # Create some conversations
        await engine.query("Question 1")
        await engine.query("Question 2")

        convs = await engine.list_conversations()

        assert len(convs) == 2

    @pytest.mark.asyncio
    async def test_delete_conversation(self, engine):
        """Test deleting a conversation."""
        result = await engine.query("Question")

        deleted = await engine.delete_conversation(result.conversation_id)

        assert deleted is True

        # Verify it's gone
        conv = await engine.get_conversation(result.conversation_id)
        assert conv is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, engine):
        """Test deleting nonexistent conversation."""
        deleted = await engine.delete_conversation("nonexistent")

        assert deleted is False


class TestQueryEngineConfidence:
    """Focused tests for confidence calculation."""

    @pytest.fixture
    def temp_dir(self):
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    def test_calculate_confidence_empty(self, temp_dir):
        """Test confidence with no chunks."""
        engine = QueryEngine(
            search=AsyncMock(),
            sdk_client=AsyncMock(),
            storage_dir=temp_dir,
        )

        confidence = engine._calculate_confidence([])

        assert confidence == 0.0

    def test_calculate_confidence_single_chunk(self, temp_dir):
        """Test confidence with single chunk."""
        engine = QueryEngine(
            search=AsyncMock(),
            sdk_client=AsyncMock(),
            storage_dir=temp_dir,
        )

        chunks = [
            RetrievedChunk(
                content="Test",
                source_file="file.md",
                section=None,
                similarity=0.8,
                content_fingerprint="abc123",
            )
        ]

        confidence = engine._calculate_confidence(chunks)

        assert 0 < confidence <= 1.0

    def test_calculate_confidence_capped(self, temp_dir):
        """Test that confidence is capped at 1.0."""
        engine = QueryEngine(
            search=AsyncMock(),
            sdk_client=AsyncMock(),
            storage_dir=temp_dir,
        )

        chunks = [
            RetrievedChunk(
                content="Content " * 200,
                source_file=f"file{i}.md",
                section="Section",
                similarity=0.99,
                content_fingerprint=f"fp{i}",
            )
            for i in range(10)
        ]

        confidence = engine._calculate_confidence(chunks)

        assert confidence <= 1.0


class TestQueryEngineRelatedTopics:
    """Focused tests for related topics extraction."""

    @pytest.fixture
    def temp_dir(self):
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    def test_find_related_topics_from_sections(self, temp_dir):
        """Test extracting topics from section names."""
        engine = QueryEngine(
            search=AsyncMock(),
            sdk_client=AsyncMock(),
            storage_dir=temp_dir,
        )

        chunks = [
            RetrievedChunk(
                content="Content",
                source_file="file.md",
                section="Python Functions",
                similarity=0.9,
                content_fingerprint="fp1",
            ),
            RetrievedChunk(
                content="Content",
                source_file="file.md",
                section="Data Types",
                similarity=0.85,
                content_fingerprint="fp2",
            ),
        ]

        topics = engine._find_related_topics(chunks)

        assert "Python Functions" in topics
        assert "Data Types" in topics

    def test_find_related_topics_from_metadata(self, temp_dir):
        """Test extracting topics from metadata."""
        engine = QueryEngine(
            search=AsyncMock(),
            sdk_client=AsyncMock(),
            storage_dir=temp_dir,
        )

        chunks = [
            RetrievedChunk(
                content="Content",
                source_file="file.md",
                section=None,
                similarity=0.9,
                content_fingerprint="fp1",
                metadata={"category": "Programming", "tags": ["python", "tutorial"]},
            ),
        ]

        topics = engine._find_related_topics(chunks)

        assert "Programming" in topics
        assert "python" in topics
        assert "tutorial" in topics

    def test_find_related_topics_max_limit(self, temp_dir):
        """Test that topics are limited to max."""
        engine = QueryEngine(
            search=AsyncMock(),
            sdk_client=AsyncMock(),
            storage_dir=temp_dir,
        )

        chunks = [
            RetrievedChunk(
                content="Content",
                source_file=f"cat{i}/file.md",
                section=f"Section {i}",
                similarity=0.9,
                content_fingerprint=f"fp{i}",
            )
            for i in range(10)
        ]

        topics = engine._find_related_topics(chunks, max_topics=5)

        assert len(topics) <= 5

    def test_find_related_topics_filters_generic(self, temp_dir):
        """Test that generic terms are filtered out."""
        engine = QueryEngine(
            search=AsyncMock(),
            sdk_client=AsyncMock(),
            storage_dir=temp_dir,
        )

        chunks = [
            RetrievedChunk(
                content="Content",
                source_file="library/file.md",
                section="content",
                similarity=0.9,
                content_fingerprint="fp1",
            ),
        ]

        topics = engine._find_related_topics(chunks)

        assert "library" not in topics
        assert "content" not in topics
