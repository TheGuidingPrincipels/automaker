# src/vector/search.py

from typing import Optional
from dataclasses import dataclass

import anyio

from .store import QdrantVectorStore
from .indexer import LibraryIndexer
from ..payloads.schema import ContentPayload


@dataclass
class SearchResult:
    """
    A search result with metadata.

    BACKWARD COMPATIBLE with Sub-Plan B expectations.
    """
    content: str
    file_path: str
    section: str
    similarity: float
    chunk_id: str
    # Phase 3A additions
    taxonomy_path: Optional[str] = None
    content_type: Optional[str] = None
    payload: Optional[ContentPayload] = None


class SemanticSearch:
    """
    High-level semantic search interface for the knowledge library.

    BACKWARD COMPATIBLE with Sub-Plan B interfaces.
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        library_path: Optional[str] = None,
    ):
        self.store = vector_store
        self.library_path = library_path
        self.indexer = LibraryIndexer(
            library_path=library_path,
            vector_store=vector_store,
        ) if library_path else None

    async def search(
        self,
        query: str,
        n_results: int = 5,
        min_similarity: float = 0.5,
        filter_taxonomy: Optional[str] = None,
        filter_content_type: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Search the library for content similar to the query.

        BACKWARD COMPATIBLE interface.

        Args:
            query: Natural language search query
            n_results: Maximum number of results
            min_similarity: Minimum similarity threshold (0-1)
            filter_taxonomy: Optional taxonomy path filter
            filter_content_type: Optional content type filter

        Returns:
            List of SearchResult objects sorted by similarity
        """
        # Parse taxonomy filter
        taxonomy_l1 = None
        taxonomy_l2 = None
        if filter_taxonomy:
            parts = filter_taxonomy.split("/")
            taxonomy_l1 = parts[0] if len(parts) > 0 else None
            taxonomy_l2 = parts[1] if len(parts) > 1 else None

        raw_results = await self.store.search(
            query=query,
            n_results=n_results * 2,
            filter_taxonomy_l1=taxonomy_l1,
            filter_taxonomy_l2=taxonomy_l2,
            filter_content_type=filter_content_type,
        )

        results = []
        for r in raw_results:
            similarity = r["score"]
            if similarity >= min_similarity:
                payload = r["payload"]
                results.append(SearchResult(
                    content="",  # Content stored separately in Qdrant documents
                    file_path=payload.file_path,
                    section=payload.section or "",
                    similarity=similarity,
                    chunk_id=r["id"],
                    taxonomy_path=payload.taxonomy.full_path if payload.taxonomy else None,
                    content_type=payload.content_type.value if payload.content_type else None,
                    payload=payload,
                ))

        results = results[:n_results]
        await self._hydrate_contents(results)
        return results

    async def _hydrate_contents(self, results: list[SearchResult]) -> None:
        """Populate missing content from library files."""
        if not results or not self.library_path or not self.indexer:
            return

        grouped: dict[str, list[SearchResult]] = {}
        for result in results:
            if result.content or not result.payload:
                continue
            grouped.setdefault(result.file_path, []).append(result)

        if not grouped:
            return

        base_path = anyio.Path(self.library_path)
        for rel_path, group in grouped.items():
            full_path = base_path / rel_path
            if not await full_path.exists():
                # Gracefully handle missing files with placeholder content
                for result in group:
                    result.content = "[Content unavailable: file not found]"
                continue

            text = await full_path.read_text(encoding="utf-8")
            chunks = self.indexer.extract_chunks(text, rel_path)
            if not chunks:
                # Gracefully handle empty files with placeholder content
                for result in group:
                    result.content = "[Content unavailable: no chunks in file]"
                continue

            by_index = {c["payload"].chunk_index: c for c in chunks}
            by_hash = {
                c["payload"].content_hash: c
                for c in chunks
                if c["payload"].content_hash
            }

            for result in group:
                payload = result.payload
                if payload is None:
                    continue

                candidate = by_index.get(payload.chunk_index)
                if (
                    candidate
                    and payload.content_hash
                    and candidate["payload"].content_hash != payload.content_hash
                ):
                    candidate = None

                if not candidate and payload.content_hash:
                    candidate = by_hash.get(payload.content_hash)

                if not candidate:
                    # Gracefully handle missing chunks with placeholder content
                    result.content = "[Content unavailable: chunk not found]"
                    continue

                result.content = candidate["content"]

    async def find_merge_candidates(
        self,
        content: str,
        threshold: float = 0.7,
        exclude_file: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Find content that might be candidates for merging.

        BACKWARD COMPATIBLE with Sub-Plan B MergeDetector expectations.

        Args:
            content: New content to find matches for
            threshold: Similarity threshold for merge consideration
            exclude_file: File to exclude (typically the source file)

        Returns:
            List of potential merge candidates
        """
        results = await self.search(
            query=content,
            n_results=10,
            min_similarity=threshold,
        )

        # Filter out excluded file
        if exclude_file:
            results = [r for r in results if r.file_path != exclude_file]

        return results

    async def ensure_indexed(self, force: bool = False) -> dict:
        """
        Ensure the library is indexed before searching.

        BACKWARD COMPATIBLE interface.
        """
        if not self.indexer:
            return {"status": "no_indexer", "files_indexed": 0}

        indexed = await self.indexer.index_all(force=force)
        return {
            "status": "indexed",
            "files_indexed": len(indexed),
            "details": indexed,
        }

    async def get_stats(self) -> dict:
        """Get search index statistics."""
        return await self.store.get_stats()
