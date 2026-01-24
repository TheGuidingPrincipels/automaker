"""Enums for database models."""

from enum import Enum


class SourceType(str, Enum):
    """Enum for document source types."""

    PASTE = "paste"
    MARKDOWN = "md"
    PDF = "pdf"


class Language(str, Enum):
    """Enum for document language."""

    ENGLISH = "en"
    GERMAN = "de"


class BreakType(str, Enum):
    """Enum for break types before a token."""

    PARAGRAPH = "paragraph"
    HEADING = "heading"
