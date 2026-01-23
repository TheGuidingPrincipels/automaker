# tests/test_execution.py
"""Tests for execution module."""

import pytest
from pathlib import Path

from src.execution.markers import BlockMarker, MarkerParser
from src.execution.writer import ContentWriter, WriteResult
from src.models.content import ContentBlock, BlockType
from src.models.content_mode import ContentMode
from src.extraction.checksums import generate_checksums


@pytest.fixture
def temp_library_dir(tmp_path):
    """Create a temporary library directory."""
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    return str(library_dir)


class TestBlockMarker:
    """Tests for BlockMarker."""

    def test_create_marker(self):
        """Create a new marker."""
        marker = BlockMarker.create(
            block_id="block_001",
            source_file="source.md",
            session_id="sess_123",
            checksum="1234567890123456",
        )

        assert marker.block_id == "block_001"
        assert marker.source_file == "source.md"
        assert marker.session_id == "sess_123"
        assert marker.checksum == "1234567890123456"
        assert marker.written_at is not None

    def test_start_marker_format(self):
        """Start marker has correct format."""
        marker = BlockMarker.create(
            block_id="block_001",
            source_file="source.md",
            session_id="sess_123",
            checksum="1234567890123456",
        )

        start = marker.to_start_marker()
        assert start.startswith("<!-- BLOCK_START")
        assert "id=block_001" in start
        assert "source=source.md" in start
        assert "session=sess_123" in start
        assert "checksum=1234567890123456" in start
        assert start.endswith("-->")

    def test_end_marker_format(self):
        """End marker has correct format."""
        marker = BlockMarker.create(
            block_id="block_001",
            source_file="source.md",
            session_id="sess_123",
            checksum="1234567890123456",
        )

        end = marker.to_end_marker()
        assert end == "<!-- BLOCK_END id=block_001 -->"

    def test_wrap_content(self):
        """Wrap content with markers."""
        marker = BlockMarker.create(
            block_id="block_001",
            source_file="source.md",
            session_id="sess_123",
            checksum="1234567890123456",
        )

        wrapped = marker.wrap_content("Hello world")
        assert wrapped.startswith("<!-- BLOCK_START")
        assert "Hello world" in wrapped
        assert wrapped.endswith("<!-- BLOCK_END id=block_001 -->")


class TestMarkerParser:
    """Tests for MarkerParser."""

    def test_find_markers(self):
        """Find markers in content."""
        content = """Some text
<!-- BLOCK_START id=block_001 source=test.md session=sess_123 checksum=1234567890123456 written=2024-01-01T00:00:00 -->
Block content here
<!-- BLOCK_END id=block_001 -->
More text
"""
        markers = MarkerParser.find_markers(content)

        assert len(markers) == 1
        assert markers[0].block_id == "block_001"
        assert markers[0].source_file == "test.md"

    def test_extract_block_content(self):
        """Extract content from a marked block."""
        content = """<!-- BLOCK_START id=block_001 source=test.md session=sess_123 checksum=1234567890123456 written=2024-01-01T00:00:00 -->
Block content here
<!-- BLOCK_END id=block_001 -->"""

        extracted = MarkerParser.extract_block_content(content, "block_001")
        assert extracted == "Block content here"

    def test_extract_nonexistent_block(self):
        """Extracting nonexistent block returns None."""
        content = "No markers here"
        extracted = MarkerParser.extract_block_content(content, "block_001")
        assert extracted is None

    def test_block_exists(self):
        """Check if block exists."""
        content = """<!-- BLOCK_START id=block_001 source=test.md session=sess checksum=1234567890123456 written=2024-01-01 -->
Content
<!-- BLOCK_END id=block_001 -->"""

        assert MarkerParser.block_exists(content, "block_001")
        assert not MarkerParser.block_exists(content, "block_002")

    def test_remove_markers(self):
        """Remove all markers from content."""
        content = """<!-- BLOCK_START id=block_001 source=test.md session=sess checksum=1234567890123456 written=2024-01-01 -->
Content here
<!-- BLOCK_END id=block_001 -->"""

        cleaned = MarkerParser.remove_markers(content)
        assert "BLOCK_START" not in cleaned
        assert "BLOCK_END" not in cleaned
        assert "Content here" in cleaned


class TestContentWriter:
    """Tests for ContentWriter."""

    @pytest.fixture
    def sample_block(self):
        """Create a sample content block."""
        content = "Test block content"
        exact, canonical = generate_checksums(content, is_code=False)

        return ContentBlock(
            id="block_001",
            block_type=BlockType.PARAGRAPH,
            content=content,
            content_canonical=content.strip(),
            source_file="source.md",
            source_line_start=1,
            source_line_end=1,
            checksum_exact=exact,
            checksum_canonical=canonical,
        )

    @pytest.mark.asyncio
    async def test_write_block_create(self, temp_library_dir, sample_block):
        """Write block to new file."""
        writer = ContentWriter(temp_library_dir, backup_enabled=False)

        result = await writer.write_block(
            block=sample_block,
            destination="test/new_file.md",
            session_id="sess_123",
            position="create",
            mode=ContentMode.STRICT,
        )

        assert result.success
        assert result.verified

        # Verify file was created
        file_path = Path(temp_library_dir) / "test" / "new_file.md"
        assert file_path.exists()

        content = file_path.read_text()
        assert "Test block content" in content
        assert "BLOCK_START" in content

    @pytest.mark.asyncio
    async def test_write_block_append(self, temp_library_dir, sample_block):
        """Append block to existing file."""
        # Create existing file
        test_dir = Path(temp_library_dir) / "test"
        test_dir.mkdir()
        test_file = test_dir / "existing.md"
        test_file.write_text("# Existing File\n\nExisting content.")

        writer = ContentWriter(temp_library_dir, backup_enabled=False)

        result = await writer.write_block(
            block=sample_block,
            destination="test/existing.md",
            session_id="sess_123",
            position="append",
            mode=ContentMode.STRICT,
        )

        assert result.success
        assert result.verified

        content = test_file.read_text()
        assert "Existing content" in content
        assert "Test block content" in content

    @pytest.mark.asyncio
    async def test_write_block_with_backup(self, temp_library_dir, sample_block):
        """Writing creates backup of existing file."""
        # Create existing file
        test_dir = Path(temp_library_dir) / "test"
        test_dir.mkdir()
        test_file = test_dir / "existing.md"
        test_file.write_text("Original content")

        writer = ContentWriter(temp_library_dir, backup_enabled=True)

        result = await writer.write_block(
            block=sample_block,
            destination="test/existing.md",
            session_id="sess_123",
            position="append",
            mode=ContentMode.STRICT,
        )

        assert result.success
        assert result.backup_path is not None

        # Verify backup exists
        backup_path = Path(result.backup_path)
        assert backup_path.exists()
        assert backup_path.read_text() == "Original content"

    @pytest.mark.asyncio
    async def test_create_file(self, temp_library_dir):
        """Create a new library file with title."""
        writer = ContentWriter(temp_library_dir)

        result = await writer.create_file(
            destination="tech/new_topic.md",
            title="New Topic",
            initial_content="Some initial notes.",
        )

        assert result.success

        file_path = Path(temp_library_dir) / "tech" / "new_topic.md"
        assert file_path.exists()

        content = file_path.read_text()
        assert "# New Topic" in content
        assert "Some initial notes" in content

    @pytest.mark.asyncio
    async def test_create_section(self, temp_library_dir):
        """Create a new section in existing file."""
        # Create file first
        test_dir = Path(temp_library_dir) / "test"
        test_dir.mkdir()
        test_file = test_dir / "file.md"
        test_file.write_text("# Main Title\n\nSome content.")

        writer = ContentWriter(temp_library_dir)

        result = await writer.create_section(
            destination="test/file.md",
            section_title="New Section",
        )

        assert result.success

        content = test_file.read_text()
        assert "## New Section" in content

    @pytest.mark.asyncio
    async def test_write_marks_block_verified(self, temp_library_dir, sample_block):
        """Successful write marks block as verified."""
        writer = ContentWriter(temp_library_dir, backup_enabled=False)

        assert not sample_block.integrity_verified
        assert not sample_block.is_executed

        await writer.write_block(
            block=sample_block,
            destination="test/new.md",
            session_id="sess_123",
            position="create",
            mode=ContentMode.STRICT,
        )

        assert sample_block.integrity_verified
        assert sample_block.is_executed


class TestWriterIntegrity:
    """Tests for writer integrity verification."""

    @pytest.mark.asyncio
    async def test_code_block_exact_verification(self, temp_library_dir):
        """Code blocks require exact byte match."""
        content = "```python\nprint('hello')\n```"
        exact, canonical = generate_checksums(content, is_code=True)

        block = ContentBlock(
            id="code_001",
            block_type=BlockType.CODE_BLOCK,
            content=content,
            content_canonical=content,
            source_file="source.md",
            source_line_start=1,
            source_line_end=3,
            checksum_exact=exact,
            checksum_canonical=canonical,
        )

        writer = ContentWriter(temp_library_dir, backup_enabled=False)

        result = await writer.write_block(
            block=block,
            destination="test/code.md",
            session_id="sess_123",
            position="create",
            mode=ContentMode.STRICT,
        )

        assert result.success
        assert result.verified

    @pytest.mark.asyncio
    async def test_refinement_mode_always_verifies(self, temp_library_dir):
        """REFINEMENT mode doesn't enforce checksums."""
        content = "Test content"
        # Use wrong checksums intentionally
        block = ContentBlock(
            id="block_001",
            block_type=BlockType.PARAGRAPH,
            content=content,
            content_canonical=content,
            source_file="source.md",
            source_line_start=1,
            source_line_end=1,
            checksum_exact="wrongchecksum___",
            checksum_canonical="wrongchecksum___",
        )

        writer = ContentWriter(temp_library_dir, backup_enabled=False)

        result = await writer.write_block(
            block=block,
            destination="test/ref.md",
            session_id="sess_123",
            position="create",
            mode=ContentMode.REFINEMENT,
        )

        # Should succeed in refinement mode
        assert result.success
