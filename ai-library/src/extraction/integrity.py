# src/extraction/integrity.py
"""
Content integrity verification for write operations.

Verification rules:
- CODE_BLOCK: exact byte checksum must match
- STRICT prose: canonical checksum must match (whitespace/line wraps allowed)
- REFINEMENT: canonical/exact checksums are recorded, not enforced
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

from ..models.content import ContentBlock, BlockType
from ..models.content_mode import ContentMode
from .canonicalize import canonicalize_prose_v1


class IntegrityError(Exception):
    """Raised when content integrity verification fails."""
    pass


@dataclass
class ContentIntegrity:
    """
    Track integrity through write + read-back verification.

    Verification rules:
    - CODE_BLOCK: exact byte checksum must match.
    - STRICT prose: canonical checksum must match (whitespace/line wraps allowed).
    - REFINEMENT: canonical/exact checksums are recorded, not enforced (merge verification happens later).
    """

    block_id: str
    expected_exact: str
    expected_canonical: str
    written_content: Optional[str] = None
    written_exact: Optional[str] = None
    written_canonical: Optional[str] = None
    verified: bool = False

    @classmethod
    def from_block(cls, block: ContentBlock) -> "ContentIntegrity":
        """Create integrity tracker from an extracted block."""
        return cls(
            block_id=block.id,
            expected_exact=block.checksum_exact,
            expected_canonical=block.checksum_canonical,
        )

    @staticmethod
    def _hash(content: str) -> str:
        """Generate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def verify_write(self, block: ContentBlock, mode: ContentMode, written_content: str) -> bool:
        """Verify written content matches expected content under the active mode."""
        self.written_content = written_content
        self.written_exact = self._hash(written_content)
        self.written_canonical = self._hash(canonicalize_prose_v1(written_content))

        if mode == ContentMode.REFINEMENT:
            self.verified = True
            return True

        if block.block_type == BlockType.CODE_BLOCK:
            self.verified = (self.expected_exact == self.written_exact)
        else:
            self.verified = (self.expected_canonical == self.written_canonical)
        return self.verified

    def assert_integrity(self) -> None:
        """Raise if integrity check failed."""
        if not self.verified:
            raise IntegrityError(
                f"Content integrity check FAILED!\n"
                f"Block: {self.block_id}\n"
                f"Expected exact:     {self.expected_exact}\n"
                f"Expected canonical: {self.expected_canonical}\n"
                f"Written exact:      {self.written_exact}\n"
                f"Written canonical:  {self.written_canonical}\n"
                f"Content may have been modified."
            )
