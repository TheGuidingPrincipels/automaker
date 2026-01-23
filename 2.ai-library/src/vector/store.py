# src/vector/store.py

from typing import Optional, Union, AsyncGenerator
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from .embeddings import get_embedding_provider, EmbeddingProvider
from ..payloads.schema import ContentPayload, RelationshipType


def _is_payload_index_already_exists_error(exc: UnexpectedResponse) -> bool:
    if exc.status_code != 409:
        return False

    message = exc.content.decode("utf-8", errors="ignore").lower()
    return "already exists" in message


class QdrantVectorStore:
    """
    Qdrant-based vector store with rich metadata payloads.

    Phase 3A: Core vector storage and search functionality.
    Phase 3B: Adds relationship queries and advanced filtering.
    """

    COLLECTION_NAME = "knowledge_library"

    def __init__(
        self,
        url: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        embedding_config: Optional[dict] = None,
        collection_name: Optional[str] = None,
        embeddings: Optional[EmbeddingProvider] = None,
    ):
        # Initialize AsyncQdrantClient
        self.client = AsyncQdrantClient(
            url=url,
            port=port,
            api_key=api_key,
        )

        # Allow custom collection name
        if collection_name:
            self.COLLECTION_NAME = collection_name

        # Initialize embedding provider (allow injection for testing)
        if embeddings:
            self.embeddings = embeddings
        else:
            self.embeddings = get_embedding_provider(embedding_config)

    async def initialize(self) -> None:
        """
        Initialize the vector store (create collection and indexes).
        Must be called after instantiation.
        """
        await self._ensure_collection()

    async def close(self) -> None:
        """Close the async client connection."""
        await self.client.close()

    async def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        # Check existence via get_collections (async)
        collections_response = await self.client.get_collections()
        collections = collections_response.collections
        exists = any(c.name == self.COLLECTION_NAME for c in collections)

        if not exists:
            await self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.embeddings.dimensions,
                    distance=Distance.COSINE,
                ),
            )

            # Create payload indexes for efficient filtering
            await self._create_payload_indexes()

    async def _create_payload_indexes(self) -> None:
        """Create indexes on frequently queried payload fields."""
        indexes = [
            ("content_type", models.PayloadSchemaType.KEYWORD),
            ("taxonomy.full_path", models.PayloadSchemaType.KEYWORD),
            ("taxonomy.level1", models.PayloadSchemaType.KEYWORD),
            ("taxonomy.level2", models.PayloadSchemaType.KEYWORD),
            ("file_path", models.PayloadSchemaType.KEYWORD),
            ("content_hash", models.PayloadSchemaType.KEYWORD),
            ("classification.confidence", models.PayloadSchemaType.FLOAT),
            ("created_at", models.PayloadSchemaType.DATETIME),
            ("updated_at", models.PayloadSchemaType.DATETIME),
        ]

        for field_name, field_type in indexes:
            try:
                await self.client.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name=field_name,
                    field_schema=field_type,
                )
            except UnexpectedResponse as exc:
                if _is_payload_index_already_exists_error(exc):
                    continue
                raise RuntimeError(
                    f"Failed to create payload index for {field_name!r}: {exc}"
                ) from exc
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to create payload index for {field_name!r}: {exc}"
                ) from exc

    async def add_content(
        self,
        content_id: str,
        text: str,
        payload: ContentPayload,
    ) -> None:
        """
        Add a single content item with its embedding and rich payload.
        """
        embedding = await self.embeddings.embed_single(text)

        await self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[
                PointStruct(
                    id=content_id,
                    vector=embedding,
                    payload=payload.to_qdrant_payload(),
                )
            ],
        )

    async def add_contents_batch(
        self,
        items: list[tuple[str, str, ContentPayload]],  # (id, text, payload)
        batch_size: int = 100,
    ) -> None:
        """
        Add multiple content items in batches.
        """
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            texts = [item[1] for item in batch]
            embeddings = await self.embeddings.embed(texts)

            points = [
                PointStruct(
                    id=item[0],
                    vector=embeddings[j],
                    payload=item[2].to_qdrant_payload(),
                )
                for j, item in enumerate(batch)
            ]

            await self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points,
            )

    async def search(
        self,
        query: str,
        n_results: int = 10,
        filter_taxonomy_l1: Optional[str] = None,
        filter_taxonomy_l2: Optional[str] = None,
        filter_content_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> list[dict]:
        """
        Search for similar content with optional filters.

        Returns results with payloads and similarity scores.
        """
        query_embedding = await self.embeddings.embed_single(query)

        # Build filter conditions
        conditions = []

        if filter_taxonomy_l1:
            conditions.append(
                models.FieldCondition(
                    key="taxonomy.level1",
                    match=models.MatchValue(value=filter_taxonomy_l1),
                )
            )

        if filter_taxonomy_l2:
            conditions.append(
                models.FieldCondition(
                    key="taxonomy.level2",
                    match=models.MatchValue(value=filter_taxonomy_l2),
                )
            )

        if filter_content_type:
            conditions.append(
                models.FieldCondition(
                    key="content_type",
                    match=models.MatchValue(value=filter_content_type),
                )
            )

        if min_confidence is not None:
            conditions.append(
                models.FieldCondition(
                    key="classification.confidence",
                    range=models.Range(gte=min_confidence),
                )
            )

        query_filter = models.Filter(must=conditions) if conditions else None

        results = await self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=n_results,
            with_payload=True,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": ContentPayload.from_qdrant_payload(hit.payload),
            }
            for hit in results
        ]

    async def search_by_relationship(
        self,
        content_id: str,
        relationship_type: RelationshipType,
    ) -> list[dict]:
        """
        Find all content related to a given item by relationship type.

        This enables pseudo-graph traversal.
        (Phase 3B: Active use. Phase 3A: Available but relationships empty.)
        """
        # First, get the source content
        source = await self.client.retrieve(
            collection_name=self.COLLECTION_NAME,
            ids=[content_id],
            with_payload=True,
        )

        if not source:
            return []

        payload = ContentPayload.from_qdrant_payload(source[0].payload)
        related_ids = [
            r.target_id for r in payload.relationships
            if r.relationship_type == relationship_type
        ]

        if not related_ids:
            return []

        # Retrieve related content
        related = await self.client.retrieve(
            collection_name=self.COLLECTION_NAME,
            ids=related_ids,
            with_payload=True,
        )

        return [
            {
                "id": point.id,
                "payload": ContentPayload.from_qdrant_payload(point.payload),
            }
            for point in related
        ]

    async def find_by_taxonomy_path(
        self,
        taxonomy_path: str,
        n_results: int = 100,
    ) -> list[dict]:
        """
        Find all content under a taxonomy path.

        Supports prefix matching (e.g., "Blueprints/Development" matches all Development blueprints).
        """
        results, _ = await self.client.scroll(
            collection_name=self.COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="taxonomy.full_path",
                        match=models.MatchText(text=taxonomy_path),
                    )
                ]
            ),
            limit=n_results,
            with_payload=True,
        )

        return [
            {
                "id": point.id,
                "payload": ContentPayload.from_qdrant_payload(point.payload),
            }
            for point in results
        ]

    async def iter_by_taxonomy(
        self,
        taxonomy_path: str,
        batch_size: int = 100,
        with_vectors: bool = False,
    ) -> AsyncGenerator[models.Record, None]:
        """
        Yield all records under a taxonomy path using pagination.
        Handles arbitrary large result sets without loading all into memory.
        """
        offset = None
        while True:
            results, offset = await self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="taxonomy.full_path",
                            match=models.MatchText(text=taxonomy_path),
                        )
                    ]
                ),
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=with_vectors,
            )

            for point in results:
                yield point

            if offset is None:
                break

    async def search_by_taxonomy(
        self,
        taxonomy_path: str,
        limit: int = 1000,
        with_vectors: bool = False,
    ) -> list[models.Record]:
        """
        Retrieve points for a taxonomy path.
        """
        results, _ = await self.client.scroll(
            collection_name=self.COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="taxonomy.full_path",
                        match=models.MatchText(text=taxonomy_path),
                    )
                ]
            ),
            limit=limit,
            with_payload=False,
            with_vectors=with_vectors,
        )

        return results

    async def find_duplicates(
        self,
        content_hash: str,
    ) -> list[dict]:
        """Find content with matching hash (potential duplicates)."""
        results, _ = await self.client.scroll(
            collection_name=self.COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="content_hash",
                        match=models.MatchValue(value=content_hash),
                    )
                ]
            ),
            limit=10,
            with_payload=True,
        )

        return [
            {
                "id": point.id,
                "payload": ContentPayload.from_qdrant_payload(point.payload),
            }
            for point in results
        ]

    async def update_payload(
        self,
        content_id: str,
        payload_updates: dict,
    ) -> None:
        """Update specific payload fields for a content item."""
        await self.client.set_payload(
            collection_name=self.COLLECTION_NAME,
            payload=payload_updates,
            points=[content_id],
        )

    async def delete_content(self, content_id: str) -> None:
        """Delete a content item."""
        await self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=models.PointIdsList(points=[content_id]),
        )

    async def delete_by_file(self, file_path: str) -> None:
        """Delete all content from a specific file."""
        await self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_path",
                            match=models.MatchValue(value=file_path),
                        )
                    ]
                )
            ),
        )

    async def get_stats(self) -> dict:
        """Get collection statistics."""
        info = await self.client.get_collection(self.COLLECTION_NAME)
        return {
            "total_points": info.points_count,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "status": info.status,
            "embedding_dimensions": self.embeddings.dimensions,
            "provider": self.embeddings.config.provider,
            "model": self.embeddings.config.model,
        }
