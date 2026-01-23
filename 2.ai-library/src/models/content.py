# src/models/content.py

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class BlockType(str, Enum):
    HEADER_SECTION = "header_section"
    PARAGRAPH = "paragraph"
    LIST = "list"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    TABLE = "table"


class ContentBlock(BaseModel):
    """
    A semantic unit of content extracted from a source document.

    STRICT rules:
    - Code blocks are byte-for-byte strict (exact checksum must match on read-back).
    - Prose blocks preserve words/sentences; whitespace/line wrapping may change.
      This is enforced via a canonical form + canonical checksum.
    """

    id: str                              # e.g., "block_001"
    block_type: BlockType

    # Content
    content: str                         # Exact extracted content (verbatim)
    content_canonical: str               # Canonicalized form for STRICT prose verification
    canonicalization_version: str = "v1"

    # Source tracking
    source_file: str
    source_line_start: int
    source_line_end: int
    heading_path: list[str] = Field(default_factory=list)  # e.g., ["STEP 2", "Alignment Validation", "Critical Findings"]

    # Integrity checksums (16-char SHA-256 prefixes for readability in logs/UI)
    # 16 hex chars = 64 bits of entropy, sufficient for collision resistance in this context
    checksum_exact: str = Field(
        min_length=16,
        max_length=16,
        description="First 16 chars of SHA-256 hash of exact content bytes",
    )
    checksum_canonical: str = Field(
        min_length=16,
        max_length=16,
        description="First 16 chars of SHA-256 hash of canonicalized content (prose only)",
    )

    # Pipeline status
    integrity_verified: bool = False      # True after successful write verification
    is_executed: bool = False             # Has been written to library

    @classmethod
    def from_source(cls, content: str, **kwargs) -> "ContentBlock":
        """Create block with automatic checksums (exact + canonical)."""
        import hashlib
        canonical = kwargs.pop("content_canonical")
        return cls(
            content=content,
            checksum_exact=hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
            checksum_canonical=hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16],
            content_canonical=canonical,
            **kwargs
        )


class SourceDocument(BaseModel):
    """A document being processed for extraction."""

    file_path: str
    checksum_exact: str               # For detecting changes (exact bytes)
    total_blocks: int
    blocks: list[ContentBlock]
