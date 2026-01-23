# tests/test_extraction.py
"""Tests for extraction module."""

import pytest
from pathlib import Path

from src.extraction.canonicalize import canonicalize_prose_v1, is_code_block
from src.extraction.checksums import (
    generate_checksum,
    generate_checksums,
    verify_checksum,
    verify_canonical_checksum,
)
from src.extraction.parser import MarkdownParser, parse_markdown_file
from src.extraction.integrity import ContentIntegrity, IntegrityError
from src.models.content import BlockType, ContentBlock
from src.models.content_mode import ContentMode


class TestCanonicalize:
    """Tests for canonicalization functions."""

    def test_canonicalize_prose_normalizes_whitespace(self):
        """Prose canonicalization normalizes whitespace."""
        content = "Hello   world\n\nThis is  a   test"
        result = canonicalize_prose_v1(content)
        assert result == "Hello world This is a test"

    def test_canonicalize_prose_preserves_words(self):
        """Canonicalization preserves all words."""
        content = "The quick brown fox jumps over the lazy dog"
        result = canonicalize_prose_v1(content)
        assert "quick" in result
        assert "brown" in result
        assert "fox" in result

    def test_canonicalize_prose_trims_whitespace(self):
        """Canonicalization trims leading/trailing whitespace."""
        content = "   Hello world   "
        result = canonicalize_prose_v1(content)
        assert result == "Hello world"

    def test_canonicalize_code_block_unchanged(self):
        """Code blocks are returned unchanged."""
        content = "```python\nprint('hello')\n```"
        result = canonicalize_prose_v1(content)
        assert result == content

    def test_canonicalize_indented_code_block_unchanged(self):
        """Indented code blocks are returned unchanged (byte-strict)."""
        content = "    def hello():\n        return 'world'\n"
        result = canonicalize_prose_v1(content)
        assert result == content

    def test_is_code_block_fenced(self):
        """Detect fenced code blocks."""
        assert is_code_block("```python\ncode\n```")
        assert not is_code_block("Regular paragraph")

    def test_is_code_block_indented(self):
        """Detect indented (4-space) code blocks."""
        assert is_code_block("    print('hi')\n    print('bye')")

    def test_empty_content(self):
        """Handle empty content."""
        assert canonicalize_prose_v1("") == ""
        assert canonicalize_prose_v1("   ") == ""


class TestChecksums:
    """Tests for checksum functions."""

    def test_generate_checksum_length(self):
        """Checksums are 16 characters."""
        checksum = generate_checksum("test content")
        assert len(checksum) == 16

    def test_generate_checksum_deterministic(self):
        """Same content produces same checksum."""
        content = "test content"
        checksum1 = generate_checksum(content)
        checksum2 = generate_checksum(content)
        assert checksum1 == checksum2

    def test_generate_checksum_different_content(self):
        """Different content produces different checksums."""
        checksum1 = generate_checksum("content A")
        checksum2 = generate_checksum("content B")
        assert checksum1 != checksum2

    def test_generate_checksums_code(self):
        """Code block checksums: canonical == exact."""
        content = "```python\nprint('hello')\n```"
        exact, canonical = generate_checksums(content, is_code=True)
        assert exact == canonical

    def test_generate_checksums_prose(self):
        """Prose checksums differ when whitespace differs."""
        content = "Hello   world"
        exact, canonical = generate_checksums(content, is_code=False)
        # Exact captures the original whitespace
        # Canonical normalizes it
        assert exact != canonical

    def test_verify_checksum(self):
        """Verify checksum matches content."""
        content = "test content"
        checksum = generate_checksum(content)
        assert verify_checksum(content, checksum)
        assert not verify_checksum("different content", checksum)

    def test_verify_canonical_checksum(self):
        """Verify canonical checksum allows whitespace changes."""
        original = "Hello   world"
        modified = "Hello world"

        _, canonical = generate_checksums(original, is_code=False)
        assert verify_canonical_checksum(modified, canonical)


class TestMarkdownParser:
    """Tests for markdown parsing."""

    def test_parse_paragraphs(self):
        """Parse simple paragraphs."""
        content = "First paragraph.\n\nSecond paragraph."
        parser = MarkdownParser("test.md")
        blocks = parser.parse(content)

        assert len(blocks) == 2
        assert blocks[0].block_type == BlockType.PARAGRAPH
        assert blocks[1].block_type == BlockType.PARAGRAPH

    def test_parse_code_blocks(self):
        """Parse fenced code blocks."""
        content = "```python\nprint('hello')\n```"
        parser = MarkdownParser("test.md")
        blocks = parser.parse(content)

        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.CODE_BLOCK
        assert "print('hello')" in blocks[0].content

    def test_parse_indented_code_block_atomic(self):
        """Parse indented code blocks as atomic, byte-accurate blocks."""
        content = "    line1\n\n    line2"
        parser = MarkdownParser("test.md")
        blocks = parser.parse(content)

        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.CODE_BLOCK
        assert blocks[0].content == content

    def test_parse_lists(self):
        """Parse list blocks."""
        content = "- Item 1\n- Item 2\n- Item 3"
        parser = MarkdownParser("test.md")
        blocks = parser.parse(content)

        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.LIST

    def test_parse_heading_path(self):
        """Track heading path through document."""
        content = """# Main Title

## Section A

Content under Section A.

## Section B

### Subsection B1

Content under Subsection B1.
"""
        parser = MarkdownParser("test.md")
        blocks = parser.parse(content)

        # Find the content under Section A
        section_a_block = next(
            (b for b in blocks if "Content under Section A" in b.content), None
        )
        assert section_a_block is not None
        assert "Main Title" in section_a_block.heading_path
        assert "Section A" in section_a_block.heading_path

        # Find the content under Subsection B1
        subsection_block = next(
            (b for b in blocks if "Content under Subsection B1" in b.content), None
        )
        assert subsection_block is not None
        assert "Main Title" in subsection_block.heading_path
        assert "Section B" in subsection_block.heading_path
        assert "Subsection B1" in subsection_block.heading_path

    def test_parse_generates_unique_ids(self):
        """Each block gets a unique ID."""
        content = "Block 1.\n\nBlock 2.\n\nBlock 3."
        parser = MarkdownParser("test.md")
        blocks = parser.parse(content)

        ids = [b.id for b in blocks]
        assert len(ids) == len(set(ids))  # All unique

    def test_parse_tracks_line_numbers(self):
        """Track source line numbers."""
        content = "Line 1.\n\nLine 3 paragraph."
        parser = MarkdownParser("test.md")
        blocks = parser.parse(content)

        assert blocks[0].source_line_start == 1
        assert blocks[1].source_line_start == 3

    def test_parse_generates_checksums(self):
        """Blocks have valid checksums."""
        content = "Test content here."
        parser = MarkdownParser("test.md")
        blocks = parser.parse(content)

        assert len(blocks[0].checksum_exact) == 16
        assert len(blocks[0].checksum_canonical) == 16


class TestContentIntegrity:
    """Tests for content integrity verification."""

    def test_integrity_from_block(self):
        """Create integrity tracker from block."""
        block = ContentBlock(
            id="block_001",
            block_type=BlockType.PARAGRAPH,
            content="Test content",
            content_canonical="Test content",
            source_file="test.md",
            source_line_start=1,
            source_line_end=1,
            checksum_exact="1234567890123456",
            checksum_canonical="1234567890123456",
        )

        integrity = ContentIntegrity.from_block(block)
        assert integrity.block_id == "block_001"
        assert integrity.expected_exact == "1234567890123456"

    def test_verify_write_strict_prose(self):
        """Verify write in STRICT mode allows whitespace changes for prose."""
        content = "Hello world"
        canonical = canonicalize_prose_v1(content)
        exact, canonical_checksum = generate_checksums(content, is_code=False)

        block = ContentBlock(
            id="block_001",
            block_type=BlockType.PARAGRAPH,
            content=content,
            content_canonical=canonical,
            source_file="test.md",
            source_line_start=1,
            source_line_end=1,
            checksum_exact=exact,
            checksum_canonical=canonical_checksum,
        )

        integrity = ContentIntegrity.from_block(block)

        # Same canonical content should verify
        written = "Hello  world"  # Different whitespace
        result = integrity.verify_write(block, ContentMode.STRICT, written)
        assert result  # Canonical matches

    def test_verify_write_strict_code_requires_exact(self):
        """Verify write in STRICT mode requires exact match for code."""
        content = "```python\nprint('hello')\n```"
        exact, canonical = generate_checksums(content, is_code=True)

        block = ContentBlock(
            id="block_001",
            block_type=BlockType.CODE_BLOCK,
            content=content,
            content_canonical=content,
            source_file="test.md",
            source_line_start=1,
            source_line_end=1,
            checksum_exact=exact,
            checksum_canonical=canonical,
        )

        integrity = ContentIntegrity.from_block(block)

        # Exact match should verify
        result = integrity.verify_write(block, ContentMode.STRICT, content)
        assert result

        # Different content should fail
        result = integrity.verify_write(
            block, ContentMode.STRICT, "```python\nprint('world')\n```"
        )
        assert not result

    def test_verify_write_refinement_always_passes(self):
        """REFINEMENT mode records but doesn't enforce checksums."""
        block = ContentBlock(
            id="block_001",
            block_type=BlockType.PARAGRAPH,
            content="Original",
            content_canonical="Original",
            source_file="test.md",
            source_line_start=1,
            source_line_end=1,
            checksum_exact="1234567890123456",
            checksum_canonical="1234567890123456",
        )

        integrity = ContentIntegrity.from_block(block)

        # Any content passes in refinement mode
        result = integrity.verify_write(
            block, ContentMode.REFINEMENT, "Completely different content"
        )
        assert result

    def test_assert_integrity_raises_on_failure(self):
        """assert_integrity raises IntegrityError on failure."""
        integrity = ContentIntegrity(
            block_id="block_001",
            expected_exact="expected_hash_here",
            expected_canonical="expected_canonical",
            verified=False,
        )

        with pytest.raises(IntegrityError):
            integrity.assert_integrity()


@pytest.mark.asyncio
async def test_parse_markdown_file(tmp_path):
    """Test parsing a complete markdown file."""
    # Create test file
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test Document

## Section 1

This is section 1 content.

## Section 2

- List item 1
- List item 2
"""
    )

    doc = await parse_markdown_file(str(test_file))

    assert doc.file_path == str(test_file)
    assert len(doc.checksum_exact) == 16
    assert doc.total_blocks == len(doc.blocks)
    assert doc.total_blocks >= 2  # At least section content and list
