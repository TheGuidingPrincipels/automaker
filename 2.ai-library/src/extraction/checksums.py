# src/extraction/checksums.py
"""
SHA-256 checksum generation for content integrity verification.

Uses 16-character SHA-256 prefixes for readability.
Two checksums per block:
- checksum_exact: Hash of exact bytes
- checksum_canonical: Hash of canonicalized form
"""

import hashlib
from typing import Tuple

from .canonicalize import canonicalize_prose_v1


def generate_checksum(content: str) -> str:
    """
    Generate a 16-character SHA-256 prefix checksum.

    Args:
        content: The content to hash

    Returns:
        16-character hex string (first 16 chars of SHA-256)
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def generate_checksums(content: str, is_code: bool = False) -> Tuple[str, str]:
    """
    Generate both exact and canonical checksums for content.

    Args:
        content: The content to hash
        is_code: If True, canonical == exact (code blocks are byte-strict)

    Returns:
        Tuple of (checksum_exact, checksum_canonical)
    """
    checksum_exact = generate_checksum(content)

    if is_code:
        # Code blocks: canonical form == exact form
        checksum_canonical = checksum_exact
    else:
        # Prose: canonical form normalizes whitespace
        canonical_content = canonicalize_prose_v1(content)
        checksum_canonical = generate_checksum(canonical_content)

    return checksum_exact, checksum_canonical


def verify_checksum(content: str, expected: str) -> bool:
    """
    Verify that content matches an expected checksum.

    Args:
        content: The content to verify
        expected: The expected 16-character checksum

    Returns:
        True if checksums match
    """
    actual = generate_checksum(content)
    return actual == expected


def verify_canonical_checksum(content: str, expected: str) -> bool:
    """
    Verify that canonicalized content matches an expected checksum.

    Args:
        content: The content to verify (will be canonicalized)
        expected: The expected 16-character checksum

    Returns:
        True if canonical checksums match
    """
    canonical = canonicalize_prose_v1(content)
    actual = generate_checksum(canonical)
    return actual == expected
