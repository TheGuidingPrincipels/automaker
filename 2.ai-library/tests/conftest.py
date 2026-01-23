# tests/conftest.py
"""Shared pytest fixtures and test helpers."""

import pytest

from src.vector.search import SearchResult


@pytest.fixture
def search_result_factory():
    """Fixture providing a factory function for creating SearchResult instances.

    Usage:
        def test_example(search_result_factory):
            result = search_result_factory("content", "file.md")
    """
    def _make_search_result(
        content: str,
        file_path: str,
        section: str = "",
        similarity: float = 0.8,
        chunk_id: str = "chunk-1",
    ) -> SearchResult:
        """Create SearchResult with required fields."""
        return SearchResult(
            content=content,
            file_path=file_path,
            section=section,
            similarity=similarity,
            chunk_id=chunk_id,
        )
    return _make_search_result
