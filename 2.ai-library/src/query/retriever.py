"""Retriever module for RAG query engine.

Wraps SemanticSearch with re-ranking, deduplication, and enrichment.
"""

from dataclasses import dataclass, field
from hashlib import md5
from typing import Optional

from src.vector.search import SemanticSearch, SearchResult


@dataclass
class RetrievedChunk:
    """An enriched chunk returned by the retriever."""

    content: str
    source_file: str
    section: Optional[str]
    similarity: float
    content_fingerprint: str
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_search_result(cls, result: SearchResult) -> "RetrievedChunk":
        """Create from a SemanticSearch result."""
        # Build metadata from available fields
        metadata: dict = {}
        if result.taxonomy_path:
            metadata["taxonomy_path"] = result.taxonomy_path
        if result.content_type:
            metadata["content_type"] = result.content_type
        if result.payload:
            if result.payload.taxonomy and result.payload.taxonomy.full_path:
                metadata["taxonomy_path"] = result.payload.taxonomy.full_path

        return cls(
            content=result.content,
            source_file=result.file_path,  # SearchResult uses file_path
            section=result.section,
            similarity=result.similarity,
            content_fingerprint=md5(result.content.encode()).hexdigest()[:16],
            metadata=metadata,
        )


class Retriever:
    """Retriever that wraps SemanticSearch with re-ranking and deduplication."""

    def __init__(
        self,
        search: SemanticSearch,
        min_similarity: float = 0.3,
        max_chunks: int = 10,
    ):
        """Initialize the retriever.

        Args:
            search: SemanticSearch instance for vector queries
            min_similarity: Minimum similarity threshold for results
            max_chunks: Maximum number of chunks to return
        """
        self.search = search
        self.min_similarity = min_similarity
        self.max_chunks = max_chunks

    async def retrieve(
        self,
        query: str,
        top_k: int = 20,
        file_filter: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks for a query.

        Args:
            query: The search query
            top_k: Number of initial candidates to fetch (before filtering)
            file_filter: Optional file path to restrict search to

        Returns:
            List of retrieved chunks, deduplicated and re-ranked
        """
        # Fetch initial candidates
        results = await self.search.search(
            query=query,
            n_results=top_k,
            min_similarity=self.min_similarity,
        )

        # Filter by file if specified
        if file_filter:
            results = [r for r in results if r.file_path == file_filter]

        # Convert to RetrievedChunk
        chunks = [RetrievedChunk.from_search_result(r) for r in results]

        # Deduplicate by content fingerprint
        chunks = self._deduplicate(chunks)

        # Re-rank based on multiple factors
        chunks = self._rerank(chunks, query)

        # Limit to max_chunks
        return chunks[: self.max_chunks]

    async def retrieve_for_file(
        self,
        query: str,
        file_path: str,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        """Retrieve chunks from a specific file.

        Args:
            query: The search query
            file_path: Path to the file to search within
            top_k: Number of chunks to return

        Returns:
            List of retrieved chunks from the specified file
        """
        return await self.retrieve(
            query=query,
            top_k=top_k,
            file_filter=file_path,
        )

    def _deduplicate(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Remove duplicate chunks based on content fingerprint."""
        seen: set[str] = set()
        unique: list[RetrievedChunk] = []

        for chunk in chunks:
            if chunk.content_fingerprint not in seen:
                seen.add(chunk.content_fingerprint)
                unique.append(chunk)

        return unique

    def _rerank(
        self, chunks: list[RetrievedChunk], query: str
    ) -> list[RetrievedChunk]:
        """Re-rank chunks based on multiple factors.

        Factors considered:
        - Base similarity score (from vector search)
        - Content length bonus (prefer more substantial chunks)
        - Section heading presence (prefer chunks with context)
        """
        query_lower = query.lower()

        def score(chunk: RetrievedChunk) -> float:
            base_score = chunk.similarity

            # Content length bonus (up to 0.1 for longer content)
            length_bonus = min(len(chunk.content) / 2000, 0.1)

            # Section heading bonus (0.05 if has section context)
            section_bonus = 0.05 if chunk.section else 0.0

            # Query term overlap bonus (up to 0.1)
            query_terms = set(query_lower.split())
            content_lower = chunk.content.lower()
            term_overlap = sum(1 for t in query_terms if t in content_lower)
            term_bonus = min(term_overlap * 0.02, 0.1)

            return base_score + length_bonus + section_bonus + term_bonus

        return sorted(chunks, key=score, reverse=True)
