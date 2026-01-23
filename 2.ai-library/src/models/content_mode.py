# src/models/content_mode.py

from enum import Enum


class ContentMode(str, Enum):
    """Content handling mode for extraction."""
    STRICT = "strict"           # Preserve words/sentences; whitespace/line wraps may change; no merges/rewrites
    REFINEMENT = "refinement"   # Optional rewrites/merges with user verification (triple-view)

    @property
    def allows_modifications(self) -> bool:
        return self == ContentMode.REFINEMENT

    @property
    def description(self) -> str:
        if self == ContentMode.STRICT:
            return "Strict - preserve words/sentences; code blocks are byte-strict; no merges/rewrites"
        return "Refinement - optional formatting/merges with user verification (no information loss)"
