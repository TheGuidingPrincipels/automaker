# src/library/candidates_vector.py
"""
Vector-based candidate finder for routing pre-filtering.

Phase 3A upgrade: Uses semantic vector similarity for finding destination candidates.
Maintains backward compatibility with the existing CandidateFinder interface.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from ..vector.store import QdrantVectorStore
from ..vector.search import SemanticSearch
from .candidates import CandidateMatch


class VectorCandidateFinder:
    """
    Finds candidate destinations using vector similarity.

    Phase 3A: Replaces/augments lexical CandidateFinder with semantic search.

    INTERFACE PRESERVED for Sub-Plan B compatibility:
    - top_candidates(library_context, block) -> List[CandidateMatch]
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        search: Optional[SemanticSearch] = None,
        top_n: int = 5,
        min_score: float = 0.3,
    ):
        """
        Initialize the vector candidate finder.

        Args:
            vector_store: QdrantVectorStore instance
            search: Optional SemanticSearch instance (created if not provided)
            top_n: Maximum number of candidates to return per block
            min_score: Minimum similarity threshold for candidates
        """
        self.store = vector_store
        self.search = search or SemanticSearch(vector_store)
        self.top_n = top_n
        self.min_score = min_score

    async def top_candidates(
        self,
        library_context: Dict[str, Any],
        block: Dict[str, Any],
    ) -> List[CandidateMatch]:
        """
        Find top destination candidates for a block using vector similarity.

        BACKWARD COMPATIBLE with Sub-Plan B PlanningFlow.

        Args:
            library_context: Library manifest/context
            block: Block dictionary with content, heading_path, etc.

        Returns:
            List of CandidateMatch objects, sorted by similarity descending
        """
        # Ensure index is up to date
        await self.search.ensure_indexed()

        # Get block content for search
        block_content = block.get("content_canonical") or block.get("content", "")

        # Search for similar content
        results = await self.store.search(
            query=block_content,
            n_results=self.top_n * 2,  # Get more, filter by manifest
        )

        # Map results to candidates, constrained by manifest
        candidates: List[CandidateMatch] = []

        for result in results:
            similarity = result["score"]

            if similarity < self.min_score:
                continue

            payload = result["payload"]
            file_path = payload.file_path
            section = payload.section

            # Validate against manifest
            if not self._is_in_manifest(library_context, file_path, section):
                continue

            candidates.append(CandidateMatch(
                file_path=file_path,
                section=section,
                score=similarity,
                match_reasons=[f"Vector similarity: {similarity:.2f}"],
            ))

            if len(candidates) >= self.top_n:
                break

        # If not enough candidates from vector search, add from manifest
        if len(candidates) < 3:
            candidates.extend(
                self._fallback_from_manifest(
                    library_context, block, self.top_n - len(candidates)
                )
            )

        return candidates[:self.top_n]

    def _is_in_manifest(
        self,
        manifest: Dict[str, Any],
        file_path: str,
        section: Optional[str],
    ) -> bool:
        """Check if a file/section exists in the library manifest."""
        # Handle categories structure from library context
        categories = manifest.get("categories", [])
        all_files = self._flatten_files(categories)

        for file_info in all_files:
            if file_info.get("path") == file_path:
                if section is None:
                    return True
                sections = file_info.get("sections", [])
                return section in sections

        return False

    def _flatten_files(
        self,
        categories: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Flatten category hierarchy to get all files."""
        files = []
        for category in categories:
            files.extend(category.get("files", []))
            files.extend(self._flatten_files(category.get("subcategories", [])))
        return files

    def _fallback_from_manifest(
        self,
        manifest: Dict[str, Any],
        block: Dict[str, Any],
        limit: int,
    ) -> List[CandidateMatch]:
        """
        Fallback: suggest destinations from manifest when vector search
        doesn't have enough results.

        This preserves Phase 2 behavior as a safety net.
        """
        candidates = []
        categories = manifest.get("categories", [])
        all_files = self._flatten_files(categories)

        # Simple heuristic: match by keywords in file path
        block_content = block.get("content", "")
        block_words = set(block_content.lower().split())

        for file_info in all_files:
            path = file_info.get("path", "")
            path_words = set(path.lower().replace("/", " ").replace("-", " ").split())

            overlap = len(block_words & path_words)
            if overlap > 0:
                score = overlap / max(len(block_words), len(path_words), 1)
                candidates.append(CandidateMatch(
                    file_path=path,
                    section=None,
                    score=score,
                    match_reasons=["Manifest fallback: keyword overlap"],
                ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:limit]

    def reset_cache(self) -> None:
        """Reset any caches. For API compatibility with lexical finder."""
        pass
