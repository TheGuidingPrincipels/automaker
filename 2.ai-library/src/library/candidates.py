# src/library/candidates.py
"""
Lexical candidate finder for routing pre-filtering.

Uses simple keyword/TF-IDF matching to pre-filter destination candidates
before AI ranking. This improves routing accuracy by constraining choices.

This module is designed to be replaced/augmented by vector search in Phase 3A.
"""

import re
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set


@dataclass
class CandidateMatch:
    """A destination candidate match with relevance score."""
    file_path: str
    section: Optional[str] = None
    score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)


class CandidateFinder:
    """
    Finds candidate destinations using lexical similarity.

    Uses a combination of:
    - Keyword overlap (exact word matches)
    - TF-IDF scoring (term frequency-inverse document frequency)
    - Heading similarity (matches against section titles)
    """

    def __init__(self, top_n: int = 5, min_score: float = 0.1):
        """
        Initialize the candidate finder.

        Args:
            top_n: Maximum number of candidates to return per block
            min_score: Minimum score threshold for candidates
        """
        self.top_n = top_n
        self.min_score = min_score
        self._idf_cache: Dict[str, float] = {}
        self._tokens_cache: Dict[str, List[str]] = {}
        self._doc_count = 0

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into normalized words.

        Args:
            text: Input text

        Returns:
            List of lowercase word tokens
        """
        # Remove markdown formatting
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links
        text = re.sub(r'[#*_~]', '', text)  # Markdown emphasis

        # Extract words
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]*\b', text.lower())

        # Filter stopwords
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
            'until', 'while', 'this', 'that', 'these', 'those', 'it',
        }

        return [w for w in words if w not in stopwords and len(w) > 2]

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """
        Compute term frequency for tokens.

        Args:
            tokens: List of word tokens

        Returns:
            Dictionary mapping token to TF score
        """
        counts = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {token: count / total for token, count in counts.items()}

    def _build_idf(self, documents: List[Dict[str, Any]]) -> None:
        """
        Build IDF (inverse document frequency) from documents.

        Args:
            documents: List of document dictionaries
        """
        self._doc_count = len(documents)
        term_doc_counts: Dict[str, int] = {}

        for doc in documents:
            file_path = doc.get("path", "")
            
            # Use cached tokens if available
            if file_path in self._tokens_cache:
                tokens = self._tokens_cache[file_path]
            else:
                # Combine title and sections for document representation
                text = doc.get("title", "")
                sections = doc.get("sections", [])
                if sections:
                    text += " " + " ".join(sections)
                
                tokens = self._tokenize(text)
                self._tokens_cache[file_path] = tokens

            for token in set(tokens):
                term_doc_counts[token] = term_doc_counts.get(token, 0) + 1

        # Compute IDF
        for term, count in term_doc_counts.items():
            self._idf_cache[term] = math.log(self._doc_count / (1 + count))

    def _tfidf_similarity(
        self,
        query_tokens: List[str],
        doc_tokens: List[str],
    ) -> float:
        """
        Compute TF-IDF similarity between query and document.

        Args:
            query_tokens: Query word tokens
            doc_tokens: Document word tokens

        Returns:
            Similarity score (0-1)
        """
        if not query_tokens or not doc_tokens:
            return 0.0

        query_tf = self._compute_tf(query_tokens)
        doc_tf = self._compute_tf(doc_tokens)

        # Compute TF-IDF vectors
        all_terms = set(query_tf.keys()) | set(doc_tf.keys())

        query_vec = []
        doc_vec = []

        for term in all_terms:
            idf = self._idf_cache.get(term, 1.0)
            query_vec.append(query_tf.get(term, 0) * idf)
            doc_vec.append(doc_tf.get(term, 0) * idf)

        # Cosine similarity
        dot_product = sum(q * d for q, d in zip(query_vec, doc_vec))
        query_norm = math.sqrt(sum(q * q for q in query_vec))
        doc_norm = math.sqrt(sum(d * d for d in doc_vec))

        if query_norm == 0 or doc_norm == 0:
            return 0.0

        return dot_product / (query_norm * doc_norm)

    def _keyword_overlap(
        self,
        query_tokens: Set[str],
        doc_tokens: Set[str],
    ) -> float:
        """
        Compute keyword overlap ratio.

        Args:
            query_tokens: Query word set
            doc_tokens: Document word set

        Returns:
            Overlap ratio (0-1)
        """
        if not query_tokens:
            return 0.0

        overlap = query_tokens & doc_tokens
        return len(overlap) / len(query_tokens)

    def _heading_match(
        self,
        block_heading_path: List[str],
        file_sections: List[str],
    ) -> tuple[float, Optional[str]]:
        """
        Find best matching section based on heading similarity.

        Args:
            block_heading_path: The block's heading path
            file_sections: List of section titles in the file

        Returns:
            Tuple of (match score, best matching section name)
        """
        if not block_heading_path or not file_sections:
            return 0.0, None

        block_tokens = set()
        for heading in block_heading_path:
            block_tokens.update(self._tokenize(heading))

        best_score = 0.0
        best_section = None

        for section in file_sections:
            section_tokens = set(self._tokenize(section))
            overlap = self._keyword_overlap(block_tokens, section_tokens)

            if overlap > best_score:
                best_score = overlap
                best_section = section

        return best_score, best_section

    async def top_candidates(
        self,
        library_context: Dict[str, Any],
        block: Dict[str, Any],
    ) -> List[CandidateMatch]:
        """
        Find top destination candidates for a block.

        Args:
            library_context: Library manifest/context
            block: Block dictionary with content, heading_path, etc.

        Returns:
            List of CandidateMatch objects, sorted by score descending
        """
        candidates: List[CandidateMatch] = []

        # Extract block content
        block_content = block.get("content", "")
        block_heading_path = block.get("heading_path", [])
        block_tokens = self._tokenize(block_content)
        block_token_set = set(block_tokens)

        # Build document list for IDF
        categories = library_context.get("categories", [])
        all_files = self._flatten_files(categories)

        # Build IDF if not cached
        if not self._idf_cache:
            self._build_idf(all_files)

        # Score each file
        for file_info in all_files:
            file_path = file_info.get("path", "")
            file_title = file_info.get("title", "")
            file_sections = file_info.get("sections", [])

            # Get document tokens (from cache or compute)
            if file_path in self._tokens_cache:
                doc_tokens = self._tokens_cache[file_path]
            else:
                doc_text = file_title + " " + " ".join(file_sections)
                doc_tokens = self._tokenize(doc_text)
                self._tokens_cache[file_path] = doc_tokens
                
            doc_token_set = set(doc_tokens)

            # Compute scores
            tfidf_score = self._tfidf_similarity(block_tokens, doc_tokens)
            keyword_score = self._keyword_overlap(block_token_set, doc_token_set)
            heading_score, best_section = self._heading_match(
                block_heading_path, file_sections
            )

            # Combined score (weighted)
            combined_score = (
                tfidf_score * 0.5 +
                keyword_score * 0.3 +
                heading_score * 0.2
            )

            if combined_score >= self.min_score:
                match_reasons = []
                if tfidf_score > 0.1:
                    match_reasons.append(f"TF-IDF: {tfidf_score:.2f}")
                if keyword_score > 0.1:
                    match_reasons.append(f"Keywords: {keyword_score:.2f}")
                if heading_score > 0.1:
                    match_reasons.append(f"Heading: {heading_score:.2f}")

                candidates.append(
                    CandidateMatch(
                        file_path=file_path,
                        section=best_section,
                        score=combined_score,
                        match_reasons=match_reasons,
                    )
                )

        # Sort by score and return top N
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:self.top_n]

    def _flatten_files(
        self,
        categories: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Flatten category hierarchy to get all files.

        Args:
            categories: List of category dictionaries

        Returns:
            Flat list of file dictionaries
        """
        files = []
        for category in categories:
            files.extend(category.get("files", []))
            files.extend(self._flatten_files(category.get("subcategories", [])))
        return files

    def reset_cache(self) -> None:
        """Reset the IDF and token caches. Call when library structure changes."""
        self._idf_cache.clear()
        self._tokens_cache.clear()
        self._doc_count = 0


# Phase 3A: Alias for backward compatibility
# The original CandidateFinder is now LexicalCandidateFinder
LexicalCandidateFinder = CandidateFinder


def get_candidate_finder(
    use_vector: bool = False,
    vector_store=None,
    **kwargs,
):
    """
    Factory function to get the appropriate candidate finder.

    Phase 3A: Choose between lexical and vector-based candidate finding.

    Args:
        use_vector: If True, use vector-based candidate finder
        vector_store: QdrantVectorStore instance (required if use_vector=True)
        **kwargs: Additional arguments passed to the finder

    Returns:
        CandidateFinder (lexical) or VectorCandidateFinder instance
    """
    if use_vector:
        if vector_store is None:
            raise ValueError("vector_store is required when use_vector=True")
        from .candidates_vector import VectorCandidateFinder
        return VectorCandidateFinder(vector_store=vector_store, **kwargs)
    else:
        return CandidateFinder(**kwargs)
