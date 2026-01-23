# tests/test_vector_store.py
"""Tests for Qdrant vector store."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.vector.store import QdrantVectorStore
from src.vector.providers.base import EmbeddingProvider, EmbeddingProviderConfig
from src.payloads.schema import ContentPayload, ContentType, RelationshipType


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""

    def __init__(self, dimensions: int = 128):
        config = EmbeddingProviderConfig(
            provider="mock",
            model="mock-embed",
            api_key="test-key",
        )
        super().__init__(config)
        self._dimensions = dimensions

    async def embed(self, texts):
        """Return mock embeddings."""
        return [[0.1 * (i + 1)] * self._dimensions for i, _ in enumerate(texts)]

    @property
    def dimensions(self):
        return self._dimensions


class TestQdrantVectorStore:
    """Tests for QdrantVectorStore class."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock AsyncQdrantClient."""
        client = MagicMock()

        # Mock async methods
        client.get_collections = AsyncMock()
        client.create_collection = AsyncMock()
        client.create_payload_index = AsyncMock()
        client.upsert = AsyncMock()
        client.search = AsyncMock()
        client.retrieve = AsyncMock()
        client.scroll = AsyncMock()
        client.delete = AsyncMock()
        client.set_payload = AsyncMock()
        client.get_collection = AsyncMock()
        client.close = AsyncMock()

        # Mock get_collections return value
        collections_mock = MagicMock()
        collections_mock.collections = []
        client.get_collections.return_value = collections_mock

        # Mock search/retrieve/scroll return values
        client.search.return_value = []
        client.retrieve.return_value = []
        client.scroll.return_value = ([], None)

        # Mock get_collection for stats
        collection_info = MagicMock()
        collection_info.points_count = 0
        collection_info.vectors_count = 0
        collection_info.indexed_vectors_count = 0
        collection_info.status = "green"
        client.get_collection.return_value = collection_info

        return client

    @pytest.fixture
    def mock_embeddings(self):
        """Create mock embeddings provider."""
        return MockEmbeddingProvider(dimensions=128)

    @pytest.fixture
    def store(self, mock_qdrant_client, mock_embeddings):
        """Create a QdrantVectorStore with mocked dependencies."""
        with patch("src.vector.store.AsyncQdrantClient", return_value=mock_qdrant_client):
            store = QdrantVectorStore(
                url="localhost",
                port=6333,
                embeddings=mock_embeddings,
            )
            store.client = mock_qdrant_client
            return store

    @pytest.mark.asyncio
    async def test_initialize_creates_collection(self, mock_qdrant_client, mock_embeddings):
        """Store creates collection if it doesn't exist."""
        with patch("src.vector.store.AsyncQdrantClient", return_value=mock_qdrant_client):
            store = QdrantVectorStore(
                url="localhost",
                port=6333,
                embeddings=mock_embeddings,
            )
            
            await store.initialize()

            mock_qdrant_client.get_collections.assert_awaited_once()
            mock_qdrant_client.create_collection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_initialize_skips_existing_collection(self, mock_qdrant_client, mock_embeddings):
        """Store skips creation for existing collection."""
        # Simulate existing collection
        existing = MagicMock()
        existing.name = "knowledge_library"
        collections_mock = MagicMock()
        collections_mock.collections = [existing]
        mock_qdrant_client.get_collections.return_value = collections_mock

        with patch("src.vector.store.AsyncQdrantClient", return_value=mock_qdrant_client):
            store = QdrantVectorStore(
                url="localhost",
                port=6333,
                embeddings=mock_embeddings,
            )
            
            await store.initialize()

            mock_qdrant_client.create_collection.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_initialize_raises_on_payload_index_error(self, mock_qdrant_client, mock_embeddings):
        """Do not swallow unexpected payload index creation errors."""
        mock_qdrant_client.create_payload_index.side_effect = RuntimeError("qdrant down")

        with patch("src.vector.store.AsyncQdrantClient", return_value=mock_qdrant_client):
            store = QdrantVectorStore(
                url="localhost",
                port=6333,
                embeddings=mock_embeddings,
            )
            
            with pytest.raises(RuntimeError, match="qdrant down"):
                await store.initialize()

    @pytest.mark.asyncio
    async def test_add_content(self, store, mock_qdrant_client):
        """Add single content item."""
        payload = ContentPayload.create_basic(
            content_id="test-id",
            file_path="test/file.md",
            section="Test Section",
        )

        await store.add_content(
            content_id="test-id",
            text="This is test content",
            payload=payload,
        )

        mock_qdrant_client.upsert.assert_awaited_once()
        call_args = mock_qdrant_client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "knowledge_library"
        assert len(call_args.kwargs["points"]) == 1

    @pytest.mark.asyncio
    async def test_add_contents_batch(self, store, mock_qdrant_client):
        """Add multiple content items in batch."""
        items = [
            (
                f"id-{i}",
                f"Content {i}",
                ContentPayload.create_basic(
                    content_id=f"id-{i}",
                    file_path=f"test/file{i}.md",
                ),
            )
            for i in range(3)
        ]

        await store.add_contents_batch(items)

        # Should be called once for a batch of 3 items
        assert mock_qdrant_client.upsert.call_count == 1
        mock_qdrant_client.upsert.assert_awaited()

    @pytest.mark.asyncio
    async def test_search_basic(self, store, mock_qdrant_client):
        """Basic search returns results."""
        # Mock search result
        mock_hit = MagicMock()
        mock_hit.id = "result-id"
        mock_hit.score = 0.85
        mock_hit.payload = ContentPayload.create_basic(
            content_id="result-id",
            file_path="found/file.md",
        ).to_qdrant_payload()
        mock_qdrant_client.search.return_value = [mock_hit]

        results = await store.search(
            query="test query",
            n_results=5,
        )

        assert len(results) == 1
        assert results[0]["id"] == "result-id"
        assert results[0]["score"] == 0.85
        assert results[0]["payload"].file_path == "found/file.md"
        mock_qdrant_client.search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_with_filters(self, store, mock_qdrant_client):
        """Search with taxonomy and content type filters."""
        mock_qdrant_client.search.return_value = []

        await store.search(
            query="test query",
            n_results=10,
            filter_taxonomy_l1="Tech",
            filter_taxonomy_l2="Auth",
            filter_content_type="blueprint",
        )

        call_args = mock_qdrant_client.search.call_args
        assert call_args.kwargs["query_filter"] is not None
        mock_qdrant_client.search.assert_awaited()

    @pytest.mark.asyncio
    async def test_find_duplicates(self, store, mock_qdrant_client):
        """Find duplicates by content hash."""
        mock_qdrant_client.scroll.return_value = ([], None)

        await store.find_duplicates("abc123hash")

        mock_qdrant_client.scroll.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_content(self, store, mock_qdrant_client):
        """Delete content by ID."""
        await store.delete_content("delete-me")

        mock_qdrant_client.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_by_file(self, store, mock_qdrant_client):
        """Delete all content from a file."""
        await store.delete_by_file("delete/this/file.md")

        mock_qdrant_client.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_payload(self, store, mock_qdrant_client):
        """Update payload fields."""
        await store.update_payload(
            content_id="update-me",
            payload_updates={"title": "New Title"},
        )

        mock_qdrant_client.set_payload.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_stats(self, store, mock_qdrant_client):
        """Get collection statistics."""
        stats = await store.get_stats()

        mock_qdrant_client.get_collection.assert_awaited_once()
        assert "total_points" in stats
        assert "vectors_count" in stats
        assert "embedding_dimensions" in stats
        assert stats["embedding_dimensions"] == 128

    @pytest.mark.asyncio
    async def test_search_by_relationship_empty(self, store, mock_qdrant_client):
        """Search by relationship with empty source."""
        mock_qdrant_client.retrieve.return_value = []

        results = await store.search_by_relationship(
            content_id="missing-id",
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        assert results == []
        mock_qdrant_client.retrieve.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_by_taxonomy_path(self, store, mock_qdrant_client):
        """Find content by taxonomy path."""
        mock_qdrant_client.scroll.return_value = ([], None)

        await store.find_by_taxonomy_path("Tech/Auth")

        mock_qdrant_client.scroll.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_by_taxonomy_returns_vectors(
        self,
        store,
        mock_qdrant_client,
    ):
        """Search by taxonomy should request vectors."""
        point = MagicMock()
        point.vector = [0.1, 0.2, 0.3]
        mock_qdrant_client.scroll.return_value = ([point], None)

        results = await store.search_by_taxonomy("Tech/Auth", limit=10, with_vectors=True)

        assert results == [point]
        call_args = mock_qdrant_client.scroll.call_args
        assert call_args.kwargs["with_vectors"] is True

    @pytest.mark.asyncio
    async def test_iter_by_taxonomy(self, store, mock_qdrant_client):
        """Test iterating by taxonomy with pagination."""
        # Setup mock for two pages of results
        page1 = [MagicMock(id="p1"), MagicMock(id="p2")]
        page2 = [MagicMock(id="p3")]
        
        # side_effect needs to handle multiple calls:
        # 1. First call returns page1 and offset="next"
        # 2. Second call returns page2 and offset=None (done)
        mock_qdrant_client.scroll.side_effect = [
            (page1, "next"),
            (page2, None),
        ]

        results = []
        async for item in store.iter_by_taxonomy("Tech/Auth", batch_size=2):
            results.append(item)

        assert len(results) == 3
        assert results[0].id == "p1"
        assert results[2].id == "p3"
        assert mock_qdrant_client.scroll.call_count == 2

    @pytest.mark.asyncio
    async def test_close(self, store, mock_qdrant_client):
        """Close client connection."""
        await store.close()
        mock_qdrant_client.close.assert_awaited_once()
