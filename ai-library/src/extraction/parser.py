# src/extraction/parser.py
"""
Markdown parsing and block extraction.

Parses markdown documents into semantic ContentBlocks with:
- Header tracking (heading_path stack)
- Code block detection (atomic, byte-accurate)
- Prose block extraction (paragraphs, lists, blockquotes, tables)
- Line number tracking for source mapping
- Unique block ID generation
"""

import re
import hashlib
from typing import List, Optional, Tuple
from pathlib import Path
import anyio

from ..models.content import BlockType, ContentBlock, SourceDocument
from .canonicalize import canonicalize_prose_v1
from .checksums import generate_checksums

# Maximum file size for markdown parsing (1 MB)
MAX_MARKDOWN_FILE_SIZE = 1024 * 1024


class MarkdownParser:
    """Parse markdown documents into semantic content blocks."""

    def __init__(self, source_file: str):
        self.source_file = source_file
        self.blocks: List[ContentBlock] = []
        self.heading_stack: List[Tuple[int, str]] = []  # (level, text)
        self.block_counter = 0

    def _generate_block_id(self) -> str:
        """Generate unique block ID."""
        self.block_counter += 1
        return f"block_{self.block_counter:03d}"

    def _get_heading_path(self) -> List[str]:
        """Get current heading path as list of strings."""
        return [text for _, text in self.heading_stack]

    def _update_heading_stack(self, level: int, text: str) -> None:
        """Update heading stack when encountering a new header."""
        # Remove headings at same or deeper level
        while self.heading_stack and self.heading_stack[-1][0] >= level:
            self.heading_stack.pop()
        self.heading_stack.append((level, text))

    def _detect_block_type(self, lines: List[str]) -> BlockType:
        """Detect the type of a content block."""
        first_nonempty = next((line for line in lines if line.strip()), "")

        # Code block (fenced)
        if first_nonempty.lstrip().startswith("```"):
            return BlockType.CODE_BLOCK

        # Indented code block
        nonempty_lines = [line for line in lines if line.strip()]
        if nonempty_lines and all(
            line.startswith("    ") or line.startswith("\t") for line in nonempty_lines
        ):
            return BlockType.CODE_BLOCK

        stripped = first_nonempty.strip()

        # Blockquote
        if stripped.startswith(">"):
            return BlockType.BLOCKQUOTE

        # List (ordered or unordered)
        if re.match(r'^[\-\*\+]\s', stripped) or re.match(r'^\d+\.\s', stripped):
            return BlockType.LIST

        # Table
        if any("|" in line and re.search(r'\|[\-:]+\|', line) for line in lines):
            return BlockType.TABLE

        # Header section (starts with #)
        if stripped.startswith("#"):
            return BlockType.HEADER_SECTION

        # Default to paragraph
        return BlockType.PARAGRAPH

    def _create_block(
        self,
        content: str,
        line_start: int,
        line_end: int,
        block_type: Optional[BlockType] = None,
    ) -> ContentBlock:
        """Create a ContentBlock with checksums."""
        if block_type is None:
            block_type = self._detect_block_type(content.split("\n"))

        is_code = block_type == BlockType.CODE_BLOCK
        canonical = content if is_code else canonicalize_prose_v1(content)
        checksum_exact, checksum_canonical = generate_checksums(content, is_code=is_code)

        return ContentBlock(
            id=self._generate_block_id(),
            block_type=block_type,
            content=content,
            content_canonical=canonical,
            source_file=self.source_file,
            source_line_start=line_start,
            source_line_end=line_end,
            heading_path=self._get_heading_path(),
            checksum_exact=checksum_exact,
            checksum_canonical=checksum_canonical,
        )

    def parse(self, content: str) -> List[ContentBlock]:
        """
        Parse markdown content into blocks.

        Strategy:
        1. Split into lines and track line numbers
        2. Identify code blocks (fenced) as atomic units
        3. Identify headers and update heading stack
        4. Group consecutive non-header, non-code content into blocks
        """
        lines = content.split("\n")
        self.blocks = []
        self.heading_stack = []
        self.block_counter = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            line_num = i + 1  # 1-indexed

            # Check for fenced code block
            if line.strip().startswith("```"):
                code_start = i
                code_lines = [line]
                i += 1

                # Find closing fence
                while i < len(lines):
                    code_lines.append(lines[i])
                    if lines[i].strip().startswith("```") and i > code_start:
                        i += 1
                        break
                    i += 1

                code_content = "\n".join(code_lines)
                block = self._create_block(
                    code_content,
                    code_start + 1,
                    i,
                    BlockType.CODE_BLOCK,
                )
                self.blocks.append(block)
                continue

            # Check for indented code block (atomic)
            if (line.startswith("    ") or line.startswith("\t")) and line.strip():
                code_start = i
                code_lines = []

                while i < len(lines):
                    current = lines[i]
                    if current.strip() == "" or current.startswith("    ") or current.startswith("\t"):
                        code_lines.append(current)
                        i += 1
                        continue
                    break

                code_content = "\n".join(code_lines)
                block = self._create_block(
                    code_content,
                    code_start + 1,
                    i,
                    BlockType.CODE_BLOCK,
                )
                self.blocks.append(block)
                continue

            # Check for header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2).strip()
                self._update_heading_stack(level, text)

                # Include header as part of the next block's context
                # but don't create a separate block for just the header
                i += 1
                continue

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Collect content block (paragraph, list, blockquote, table)
            block_start = i
            block_lines = []

            # Determine initial block type
            initial_type = self._detect_block_type([line])

            while i < len(lines):
                current_line = lines[i]

                # Stop at headers
                if re.match(r'^#{1,6}\s+', current_line):
                    break

                # Stop at fenced code blocks
                if current_line.strip().startswith("```"):
                    break

                # Stop at empty line for paragraphs (but not for lists)
                if not current_line.strip():
                    if initial_type not in (BlockType.LIST, BlockType.BLOCKQUOTE):
                        break
                    # For lists, check if next non-empty line continues the list
                    peek = i + 1
                    while peek < len(lines) and not lines[peek].strip():
                        peek += 1
                    if peek < len(lines):
                        next_type = self._detect_block_type([lines[peek]])
                        if next_type != initial_type:
                            break
                    else:
                        break

                block_lines.append(current_line)
                i += 1

            if block_lines:
                block_content = "\n".join(block_lines)
                block = self._create_block(
                    block_content,
                    block_start + 1,
                    i,
                    initial_type,
                )
                self.blocks.append(block)

        return self.blocks


async def parse_markdown_file(file_path: str) -> SourceDocument:
    """
    Parse a markdown file into a SourceDocument with blocks.

    Args:
        file_path: Path to the markdown file

    Returns:
        SourceDocument with extracted blocks
    """
    path = anyio.Path(file_path)

    # Check file size
    stat = await path.stat()
    if stat.st_size > MAX_MARKDOWN_FILE_SIZE:
        raise ValueError(
            f"File size {stat.st_size} exceeds {MAX_MARKDOWN_FILE_SIZE // (1024 * 1024)}MB limit"
        )

    content = await path.read_text()

    # Generate document checksum
    doc_checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    # Parse blocks
    parser = MarkdownParser(file_path)
    blocks = parser.parse(content)

    return SourceDocument(
        file_path=file_path,
        checksum_exact=doc_checksum,
        total_blocks=len(blocks),
        blocks=blocks,
    )
