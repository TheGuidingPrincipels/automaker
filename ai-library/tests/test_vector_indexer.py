# tests/test_vector_indexer.py
"""Tests for library indexer."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os

from src.vector.indexer import LibraryIndexer
from src.vector.store import QdrantVectorStore


class MockVectorStore:
    """Mock vector store for testing indexer."""

    def __init__(self):
        self.stored_items = []
        self.deleted_files = []
        self.deleted_ids = []

    async def add_contents_batch(self, items, batch_size=100):
        """Store items."""
        self.stored_items.extend(items)

    async def delete_by_file(self, file_path):
        """Track deleted files."""
        self.deleted_files.append(file_path)

    async def search(self, query, n_results=10, **kwargs):
        """Mock search."""
        return []


class TestLibraryIndexer:
    """Tests for LibraryIndexer class."""

    @pytest.fixture
    def temp_library(self, tmp_path):
        """Create a temporary library directory with test files."""
        # Create library structure
        (tmp_path / "tech").mkdir()
        (tmp_path / "design").mkdir()

        # Create markdown files
        (tmp_path / "tech" / "auth.md").write_text(
            "# Authentication\n\n"
            "This section covers authentication patterns.\n\n"
            "## JWT Tokens\n\n"
            "JSON Web Tokens are commonly used for stateless auth.\n\n"
            "## OAuth2\n\n"
            "OAuth2 is a standard for authorization."
        )

        (tmp_path / "tech" / "database.md").write_text(
            "# Database\n\n"
            "Database concepts and patterns.\n\n"
            "## PostgreSQL\n\n"
            "PostgreSQL is a powerful relational database."
        )

        (tmp_path / "design" / "patterns.md").write_text(
            "# Design Patterns\n\n"
            "Common software design patterns.\n\n"
            "## Factory Pattern\n\n"
            "The factory pattern creates objects without specifying their concrete classes."
        )

        # Create an index file that should be skipped
        (tmp_path / "_index.yaml").write_text("# Index file")

        return tmp_path

    @pytest.fixture
    def mock_store(self):
        """Create mock vector store."""
        return MockVectorStore()

    @pytest.fixture
    def indexer(self, temp_library, mock_store):
        """Create indexer with mock store."""
        return LibraryIndexer(
            library_path=str(temp_library),
            vector_store=mock_store,
        )

    def test_extract_chunks_creates_chunks(self, indexer):
        """Extract chunks creates meaningful chunks."""
        content = (
            "# Main Title\n\n"
            "Introduction paragraph here.\n\n"
            "## Section One\n\n"
            "Content for section one that is long enough to be a chunk.\n\n"
            "## Section Two\n\n"
            "Content for section two that is also long enough to be indexed."
        )

        chunks = indexer._extract_chunks_for_indexing(content, "test/file.md")

        # Should create multiple chunks
        assert len(chunks) > 0

        # Each chunk should have required fields
        for chunk in chunks:
            assert "id" in chunk
            assert "content" in chunk
            assert "payload" in chunk
            assert chunk["payload"].file_path == "test/file.md"

    def test_extract_chunks_sets_total(self, indexer):
        """Extract chunks sets chunk_total correctly."""
        content = (
            "# Title\n\n"
            "First paragraph with enough content to be indexed as a chunk.\n\n"
            "Second paragraph also with enough content to be indexed separately."
        )

        chunks = indexer._extract_chunks_for_indexing(content, "test.md")

        if chunks:
            total = chunks[0]["payload"].chunk_total
            for chunk in chunks:
                assert chunk["payload"].chunk_total == total

    def test_extract_chunks_skips_small_content(self, indexer):
        """Extract chunks skips content below minimum size."""
        content = "# Title\n\nTiny."

        chunks = indexer._extract_chunks_for_indexing(content, "small.md")

        # Very small content should not create chunks
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_calculate_checksum_consistent(self, indexer, temp_library):
        """Calculate checksum returns consistent results."""
        file_path = temp_library / "tech" / "auth.md"

        checksum1 = await indexer._calculate_checksum(file_path)
        checksum2 = await indexer._calculate_checksum(file_path)

        assert checksum1 == checksum2
        assert len(checksum1) == 32  # MD5 hex length

    @pytest.mark.asyncio
    async def test_index_file(self, indexer, temp_library, mock_store):
        """Index a single file."""
        file_path = temp_library / "tech" / "auth.md"

        chunk_count = await indexer.index_file(file_path)

        # Should create chunks
        assert chunk_count > 0

        # Should store items
        assert len(mock_store.stored_items) > 0

        # Should delete old content first
        assert "tech/auth.md" in mock_store.deleted_files

    @pytest.mark.asyncio
    async def test_index_all_indexes_md_files(self, indexer, temp_library, mock_store):
        """Index all markdown files in library."""
        results = await indexer.index_all(force=True)

        # Should index 3 files (auth.md, database.md, patterns.md)
        assert len(results) == 3

        # All should have chunks
        for path, count in results.items():
            assert count > 0, f"{path} should have chunks"

    @pytest.mark.asyncio
    async def test_index_all_skips_index_files(self, indexer, temp_library, mock_store):
        """Index all skips files starting with underscore."""
        results = await indexer.index_all(force=True)

        # Should not include _index.yaml
        assert not any("_index" in path for path in results.keys())

    @pytest.mark.asyncio
    async def test_incremental_indexing_skips_unchanged(self, indexer, mock_store):
        """Incremental indexing skips unchanged files."""
        # First index
        results1 = await indexer.index_all(force=True)

        # Clear mock store
        mock_store.stored_items = []
        mock_store.deleted_files = []

        # Second index without force
        results2 = await indexer.index_all(force=False)

        # Should not reindex anything
        assert len(results2) == 0

    @pytest.mark.asyncio
    async def test_incremental_indexing_detects_changes(self, indexer, temp_library, mock_store):
        """Incremental indexing detects changed files."""
        # First index
        await indexer.index_all(force=True)

        # Modify a file
        (temp_library / "tech" / "auth.md").write_text(
            "# Updated Auth\n\nNew content that is different from before."
        )

        # Clear mock store
        mock_store.stored_items = []
        mock_store.deleted_files = []

        # Second index
        results = await indexer.index_all(force=False)

        # Should reindex the changed file
        assert "tech/auth.md" in results

    @pytest.mark.asyncio
    async def test_remove_deleted_files(self, indexer, temp_library, mock_store):
        """Remove vectors for deleted files."""
        # First index
        await indexer.index_all(force=True)

        # Delete a file
        (temp_library / "tech" / "auth.md").unlink()

        # Clear mock
        mock_store.deleted_files = []

        # Remove deleted
        removed = await indexer.remove_deleted_files()

        # Should have removed the deleted file
        assert "tech/auth.md" in removed
        assert "tech/auth.md" in mock_store.deleted_files

    @pytest.mark.asyncio
    async def test_find_similar(self, indexer, mock_store):
        """Find similar content."""
        results = await indexer.find_similar(
            content="test content",
            n_results=5,
        )

        # With empty store, should return empty
        assert results == []

    @pytest.mark.asyncio
    async def test_state_persistence(self, indexer, temp_library):
        """Indexer persists state to file."""
        # Index a file
        file_path = temp_library / "tech" / "auth.md"
        await indexer.index_file(file_path)

        # State file should exist
        assert indexer.index_state_file.exists()

        # Load state
        state = await indexer._load_state()

        # Should contain the indexed file
        assert "tech/auth.md" in state
        assert "checksum" in state["tech/auth.md"]
        assert "indexed_at" in state["tech/auth.md"]

    @pytest.mark.asyncio
    async def test_state_io_does_not_use_sync_open(self, indexer, monkeypatch):
        """State load/save must not use blocking built-in open() in async code."""
        import src.vector.indexer as indexer_module

        def _fail_open(*args, **kwargs):
            raise AssertionError("sync open() used in async state I/O")

        monkeypatch.setattr(indexer_module, "open", _fail_open, raising=False)

        await indexer._save_state({"a.md": {"checksum": "x", "indexed_at": "now"}})
        state = await indexer._load_state()
        assert "a.md" in state
