# src/extraction/canonicalize.py
"""
STRICT prose canonicalization rules.

Canonicalization v1 rules:
- Prose: Normalize whitespace/line-wraps/blank lines; preserve words/sentences
- Code blocks: Canonical form == exact form (byte-strict)
"""

import re


def canonicalize_prose_v1(content: str) -> str:
    """
    Canonicalize prose content using v1 rules.

    Rules:
    - Normalize all whitespace sequences to single spaces
    - Trim leading/trailing whitespace
    - Preserve words and sentences exactly
    - Code blocks are returned unchanged (they are byte-strict)

    Args:
        content: The raw content to canonicalize

    Returns:
        Canonicalized content string
    """
    if not content:
        return ""

    # Code blocks are byte-strict - return as-is
    if is_code_block(content):
        # Code blocks are byte-strict - return as-is
        return content

    # For prose: normalize whitespace while preserving words
    # 1. Replace all whitespace sequences (including newlines) with single space
    normalized = re.sub(r'\s+', ' ', content)

    # 2. Trim leading/trailing whitespace
    normalized = normalized.strip()

    return normalized


def is_code_block(content: str) -> bool:
    """Check if content is a code block."""
    if not content or not content.strip():
        return False

    lines = content.split("\n")
    first_nonempty = next((line for line in lines if line.strip()), "")

    # Fenced code blocks (allow up to 3 leading spaces)
    if first_nonempty.lstrip().startswith("```"):
        return True

    # Indented code blocks: all non-empty lines are indented 4+ spaces or a tab
    nonempty_lines = [line for line in lines if line.strip()]
    return bool(nonempty_lines) and all(
        line.startswith("    ") or line.startswith("\t") for line in nonempty_lines
    )
