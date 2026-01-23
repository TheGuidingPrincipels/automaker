# src/execution/markers.py
"""
Tracking markers for idempotent operations.

Wraps content with HTML comments containing metadata for:
- Source tracking (original file, block ID)
- Checksum verification
- Idempotent re-execution
"""

import re
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class BlockMarker:
    """Marker metadata for a content block."""

    block_id: str
    source_file: str
    session_id: str
    checksum: str
    written_at: str

    def to_start_marker(self) -> str:
        """Generate the start marker comment."""
        return (
            f"<!-- BLOCK_START id={self.block_id} "
            f"source={self.source_file} "
            f"session={self.session_id} "
            f"checksum={self.checksum} "
            f"written={self.written_at} -->"
        )

    def to_end_marker(self) -> str:
        """Generate the end marker comment."""
        return f"<!-- BLOCK_END id={self.block_id} -->"

    @classmethod
    def create(
        cls,
        block_id: str,
        source_file: str,
        session_id: str,
        checksum: str,
    ) -> "BlockMarker":
        """Create a new marker with current timestamp."""
        return cls(
            block_id=block_id,
            source_file=source_file,
            session_id=session_id,
            checksum=checksum,
            written_at=datetime.now().isoformat(),
        )

    def wrap_content(self, content: str) -> str:
        """Wrap content with start and end markers."""
        return f"{self.to_start_marker()}\n{content}\n{self.to_end_marker()}"


class MarkerParser:
    """Parse markers from existing content."""

    # Regex patterns for marker detection
    START_PATTERN = re.compile(
        r'<!-- BLOCK_START '
        r'id=([^\s]+) '
        r'source=([^\s]+) '
        r'session=([^\s]+) '
        r'checksum=([^\s]+) '
        r'written=([^\s]+) -->'
    )
    END_PATTERN = re.compile(r'<!-- BLOCK_END id=([^\s]+) -->')

    @classmethod
    def find_markers(cls, content: str) -> List[BlockMarker]:
        """
        Find all block markers in content.

        Args:
            content: The content to search

        Returns:
            List of BlockMarker objects found
        """
        markers = []

        for match in cls.START_PATTERN.finditer(content):
            markers.append(
                BlockMarker(
                    block_id=match.group(1),
                    source_file=match.group(2),
                    session_id=match.group(3),
                    checksum=match.group(4),
                    written_at=match.group(5),
                )
            )

        return markers

    @classmethod
    def extract_block_content(
        cls, content: str, block_id: str
    ) -> Optional[str]:
        """
        Extract the content of a specific block by ID.

        Args:
            content: The full document content
            block_id: The block ID to find

        Returns:
            The block content without markers, or None if not found
        """
        # Find the start marker
        start_pattern = re.compile(
            rf'<!-- BLOCK_START id={re.escape(block_id)} [^>]+ -->\n'
        )
        end_pattern = re.compile(
            rf'\n<!-- BLOCK_END id={re.escape(block_id)} -->'
        )

        start_match = start_pattern.search(content)
        if not start_match:
            return None

        end_match = end_pattern.search(content, start_match.end())
        if not end_match:
            return None

        return content[start_match.end():end_match.start()]

    @classmethod
    def block_exists(cls, content: str, block_id: str) -> bool:
        """
        Check if a block with the given ID already exists.

        Args:
            content: The document content
            block_id: The block ID to check

        Returns:
            True if the block exists
        """
        pattern = rf'<!-- BLOCK_START id={re.escape(block_id)} '
        return bool(re.search(pattern, content))

    @classmethod
    def remove_markers(cls, content: str) -> str:
        """
        Remove all block markers from content.

        Args:
            content: Content with markers

        Returns:
            Content with markers removed
        """
        # Remove start markers
        content = cls.START_PATTERN.sub('', content)

        # Remove end markers
        content = cls.END_PATTERN.sub('', content)

        # Clean up extra blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()
