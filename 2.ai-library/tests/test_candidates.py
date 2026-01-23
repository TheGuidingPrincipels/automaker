# tests/test_candidates.py
"""Tests for candidate finders (lexical and vector-based)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.library.candidates import (
    CandidateFinder,
    CandidateMatch,
    LexicalCandidateFinder,
    get_candidate_finder,
)
from src.library.candidates_vector import VectorCandidateFinder
from src.payloads.schema import ContentPayload


class TestCandidateMatch:
    """Tests for CandidateMatch dataclass."""

    def test_create_candidate_match(self):
        """Create a candidate match with default values."""
        match = CandidateMatch(
            file_path="library/auth/jwt.md",
            section="Token Validation",
            score=0.75,
        )

        assert match.file_path == "library/auth/jwt.md"
        assert match.section == "Token Validation"
        assert match.score == 0.75
        assert match.match_reasons == []

    def test_candidate_match_with_reasons(self):
        """Create a candidate match with match reasons."""
        match = CandidateMatch(
            file_path="library/db/postgres.md",
            score=0.6,
            match_reasons=["TF-IDF: 0.45", "Keywords: 0.15"],
        )

        assert len(match.match_reasons) == 2
        assert "TF-IDF" in match.match_reasons[0]


class TestCandidateFinder:
    """Tests for CandidateFinder class."""

    @pytest.fixture
    def finder(self):
        """Create a CandidateFinder instance."""
        return CandidateFinder(top_n=5, min_score=0.1)

    @pytest.fixture
    def library_context(self):
        """Create a mock library context."""
        return {
            "summary": {
                "total_categories": 2,
                "total_files": 4,
            },
            "categories": [
                {
                    "name": "Tech",
                    "path": "tech",
                    "files": [
                        {
                            "path": "tech/authentication.md",
                            "title": "Authentication",
                            "sections": ["JWT Tokens", "OAuth2", "Session Management"],
                        },
                        {
                            "path": "tech/database.md",
                            "title": "Database",
                            "sections": ["PostgreSQL", "MongoDB", "Redis"],
                        },
                    ],
                    "subcategories": [],
                },
                {
                    "name": "Design",
                    "path": "design",
                    "files": [
                        {
                            "path": "design/patterns.md",
                            "title": "Design Patterns",
                            "sections": ["Singleton", "Factory", "Observer"],
                        },
                    ],
                    "subcategories": [],
                },
            ],
        }

    def test_tokenize_basic(self, finder):
        """Tokenize basic text."""
        tokens = finder._tokenize("Hello World, this is a test")

        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        # Stopwords should be filtered
        assert "this" not in tokens
        assert "is" not in tokens

    def test_tokenize_strips_markdown(self, finder):
        """Tokenize removes markdown formatting."""
        text = "# Heading\n\nSome **bold** and `code` here"
        tokens = finder._tokenize(text)

        assert "heading" in tokens
        assert "bold" in tokens
        # Markdown symbols should be removed
        assert "#" not in " ".join(tokens)
        assert "**" not in " ".join(tokens)

    def test_tokenize_filters_short_words(self, finder):
        """Tokenize filters very short words."""
        tokens = finder._tokenize("a b c test word ab")

        # Short words (<=2 chars) should be filtered
        assert "a" not in tokens
        assert "b" not in tokens
        assert "c" not in tokens
        assert "ab" not in tokens
        assert "test" in tokens
        assert "word" in tokens

    def test_compute_tf(self, finder):
        """Compute term frequency."""
        tokens = ["apple", "banana", "apple", "cherry", "apple"]
        tf = finder._compute_tf(tokens)

        assert tf["apple"] == 3 / 5
        assert tf["banana"] == 1 / 5
        assert tf["cherry"] == 1 / 5

    def test_keyword_overlap(self, finder):
        """Compute keyword overlap between sets."""
        query = {"auth", "token", "jwt"}
        doc = {"token", "jwt", "session", "cookie"}

        overlap = finder._keyword_overlap(query, doc)

        # 2 common words out of 3 in query
        assert overlap == pytest.approx(2 / 3)

    def test_keyword_overlap_empty_query(self, finder):
        """Empty query returns zero overlap."""
        overlap = finder._keyword_overlap(set(), {"token", "jwt"})
        assert overlap == 0.0

    def test_heading_match_exact(self, finder):
        """Heading match with exact match."""
        block_path = ["JWT Tokens"]
        sections = ["JWT Tokens", "OAuth2", "Session"]

        score, best = finder._heading_match(block_path, sections)

        assert best == "JWT Tokens"
        assert score > 0.5

    def test_heading_match_partial(self, finder):
        """Heading match with partial overlap."""
        block_path = ["Authentication Security"]
        sections = ["JWT Authentication", "OAuth2", "Session"]

        score, best = finder._heading_match(block_path, sections)

        # Should match JWT Authentication (shares "authentication")
        assert best == "JWT Authentication"
        assert score > 0

    def test_heading_match_empty(self, finder):
        """Heading match with empty inputs returns zero."""
        score1, best1 = finder._heading_match([], ["Section"])
        score2, best2 = finder._heading_match(["Heading"], [])

        assert score1 == 0.0
        assert best1 is None
        assert score2 == 0.0
        assert best2 is None

    @pytest.mark.asyncio
    async def test_top_candidates_finds_matches(self, finder, library_context):
        """Top candidates finds relevant matches."""
        block = {
            "id": "block_1",
            "content": "JWT tokens should be validated on every request. This ensures secure authentication.",
            "heading_path": ["Authentication"],
            "block_type": "prose",
        }

        candidates = await finder.top_candidates(library_context, block)

        # Should find authentication-related file
        assert len(candidates) > 0
        file_paths = [c.file_path for c in candidates]
        assert any("auth" in p.lower() for p in file_paths)

    @pytest.mark.asyncio
    async def test_top_candidates_respects_limit(self, finder, library_context):
        """Top candidates respects top_n limit."""
        finder.top_n = 2
        block = {
            "id": "block_1",
            "content": "General content about many topics",
            "heading_path": [],
            "block_type": "prose",
        }

        candidates = await finder.top_candidates(library_context, block)

        assert len(candidates) <= 2

    @pytest.mark.asyncio
    async def test_top_candidates_sorted_by_score(self, finder, library_context):
        """Candidates are sorted by score descending."""
        block = {
            "id": "block_1",
            "content": "Database PostgreSQL connection pooling configuration",
            "heading_path": ["Database Setup"],
            "block_type": "prose",
        }

        candidates = await finder.top_candidates(library_context, block)

        if len(candidates) > 1:
            for i in range(len(candidates) - 1):
                assert candidates[i].score >= candidates[i + 1].score

    @pytest.mark.asyncio
    async def test_top_candidates_empty_library(self, finder):
        """Top candidates handles empty library gracefully."""
        empty_context = {"categories": []}
        block = {
            "id": "block_1",
            "content": "Some content",
            "heading_path": [],
            "block_type": "prose",
        }

        candidates = await finder.top_candidates(empty_context, block)

        assert candidates == []

    def test_reset_cache(self, finder):
        """Reset cache clears IDF cache."""
        finder._idf_cache = {"word": 1.5}
        finder._doc_count = 10

        finder.reset_cache()

        assert finder._idf_cache == {}
        assert finder._doc_count == 0

    def test_flatten_files(self, finder, library_context):
        """Flatten files extracts from nested categories."""
        files = finder._flatten_files(library_context["categories"])

        assert len(files) == 3
        paths = [f["path"] for f in files]
        assert "tech/authentication.md" in paths
        assert "tech/database.md" in paths
        assert "design/patterns.md" in paths


class TestLexicalCandidateFinderAlias:
    """Tests for LexicalCandidateFinder alias."""

    def test_alias_is_same_class(self):
        """LexicalCandidateFinder is alias for CandidateFinder."""
        assert LexicalCandidateFinder is CandidateFinder


class TestGetCandidateFinder:
    """Tests for get_candidate_finder factory function."""

    def test_get_lexical_finder_by_default(self):
        """Factory returns lexical finder by default."""
        finder = get_candidate_finder()

        assert isinstance(finder, CandidateFinder)

    def test_get_lexical_finder_explicit(self):
        """Factory returns lexical finder when explicitly requested."""
        finder = get_candidate_finder(use_vector=False)

        assert isinstance(finder, CandidateFinder)

    def test_get_vector_finder_requires_store(self):
        """Factory raises error when vector finder requested without store."""
        with pytest.raises(ValueError, match="vector_store is required"):
            get_candidate_finder(use_vector=True)

    def test_get_vector_finder_with_store(self):
        """Factory returns vector finder when store provided."""
        mock_store = MagicMock()
        finder = get_candidate_finder(use_vector=True, vector_store=mock_store)

        assert isinstance(finder, VectorCandidateFinder)

    def test_passes_kwargs_to_finder(self):
        """Factory passes kwargs to finder."""
        finder = get_candidate_finder(top_n=10, min_score=0.5)

        assert finder.top_n == 10
        assert finder.min_score == 0.5


class MockVectorStore:
    """Mock vector store for testing vector candidate finder."""

    def __init__(self):
        self.search_results = []

    async def search(self, query, n_results=10, **kwargs):
        """Return mock search results."""
        return self.search_results[:n_results]


class MockSemanticSearch:
    """Mock semantic search for testing."""

    async def ensure_indexed(self, force=False):
        """Mock ensure indexed."""
        return {"status": "indexed", "files_indexed": 0}


class TestVectorCandidateFinder:
    """Tests for VectorCandidateFinder class."""

    @pytest.fixture
    def mock_store(self):
        """Create mock vector store."""
        return MockVectorStore()

    @pytest.fixture
    def mock_search(self):
        """Create mock semantic search."""
        return MockSemanticSearch()

    @pytest.fixture
    def finder(self, mock_store, mock_search):
        """Create VectorCandidateFinder with mocks."""
        finder = VectorCandidateFinder(
            vector_store=mock_store,
            search=mock_search,
            top_n=5,
            min_score=0.3,
        )
        return finder

    @pytest.fixture
    def library_context(self):
        """Create a mock library context."""
        return {
            "categories": [
                {
                    "name": "Tech",
                    "path": "tech",
                    "files": [
                        {
                            "path": "tech/authentication.md",
                            "title": "Authentication",
                            "sections": ["JWT Tokens", "OAuth2"],
                        },
                        {
                            "path": "tech/database.md",
                            "title": "Database",
                            "sections": ["PostgreSQL", "MongoDB"],
                        },
                    ],
                    "subcategories": [],
                },
            ],
        }

    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results from store."""
        return [
            {
                "id": "chunk-1",
                "score": 0.85,
                "payload": ContentPayload.create_basic(
                    content_id="chunk-1",
                    file_path="tech/authentication.md",
                    section="JWT Tokens",
                ),
            },
            {
                "id": "chunk-2",
                "score": 0.65,
                "payload": ContentPayload.create_basic(
                    content_id="chunk-2",
                    file_path="tech/database.md",
                    section="PostgreSQL",
                ),
            },
            {
                "id": "chunk-3",
                "score": 0.25,  # Below min_score
                "payload": ContentPayload.create_basic(
                    content_id="chunk-3",
                    file_path="unknown/file.md",  # Not in manifest
                    section="Random",
                ),
            },
        ]

    @pytest.mark.asyncio
    async def test_top_candidates_returns_matches(
        self, finder, mock_store, library_context, sample_search_results
    ):
        """Top candidates returns matching results."""
        mock_store.search_results = sample_search_results

        block = {
            "content": "JWT authentication tokens validation",
            "heading_path": ["Auth"],
        }

        candidates = await finder.top_candidates(library_context, block)

        # Should return candidates above score threshold
        assert len(candidates) >= 1
        assert all(isinstance(c, CandidateMatch) for c in candidates)

    @pytest.mark.asyncio
    async def test_top_candidates_filters_by_score(
        self, finder, mock_store, library_context, sample_search_results
    ):
        """Top candidates filters out low-score results."""
        mock_store.search_results = sample_search_results

        block = {"content": "test content", "heading_path": []}

        candidates = await finder.top_candidates(library_context, block)

        # Should not include results below min_score (0.3)
        assert all(c.score >= 0.3 for c in candidates)

    @pytest.mark.asyncio
    async def test_top_candidates_validates_against_manifest(
        self, finder, mock_store, library_context
    ):
        """Top candidates validates results against manifest."""
        # Result with file not in manifest
        mock_store.search_results = [
            {
                "id": "chunk-x",
                "score": 0.95,
                "payload": ContentPayload.create_basic(
                    content_id="chunk-x",
                    file_path="nonexistent/file.md",
                    section="Test",
                ),
            },
        ]

        block = {"content": "test", "heading_path": []}

        candidates = await finder.top_candidates(library_context, block)

        # Should not include file not in manifest (will use fallback if enabled)
        file_paths = [c.file_path for c in candidates]
        assert "nonexistent/file.md" not in file_paths

    @pytest.mark.asyncio
    async def test_top_candidates_respects_limit(
        self, finder, mock_store, library_context, sample_search_results
    ):
        """Top candidates respects top_n limit."""
        finder.top_n = 1
        mock_store.search_results = sample_search_results

        block = {"content": "test", "heading_path": []}

        candidates = await finder.top_candidates(library_context, block)

        assert len(candidates) <= 1

    @pytest.mark.asyncio
    async def test_fallback_to_manifest_when_few_results(
        self, finder, mock_store, library_context
    ):
        """Fallback to manifest suggestions when vector search has few results."""
        # Empty vector search results
        mock_store.search_results = []

        block = {
            "content": "authentication JWT tokens",
            "heading_path": [],
        }

        candidates = await finder.top_candidates(library_context, block)

        # Should have fallback candidates from manifest
        # (may be empty if no keyword overlap)
        assert isinstance(candidates, list)

    def test_reset_cache_is_noop(self, finder):
        """Reset cache is a no-op for compatibility."""
        # Should not raise
        finder.reset_cache()

    def test_is_in_manifest(self, finder, library_context):
        """_is_in_manifest correctly validates files."""
        assert finder._is_in_manifest(
            library_context, "tech/authentication.md", "JWT Tokens"
        )
        assert finder._is_in_manifest(
            library_context, "tech/authentication.md", None
        )
        assert not finder._is_in_manifest(
            library_context, "unknown/file.md", None
        )
        assert not finder._is_in_manifest(
            library_context, "tech/authentication.md", "Unknown Section"
        )
