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
    """Type of structural break in the text.

    Used to indicate paragraph and heading boundaries for RSVP timing.
    """

    PARAGRAPH = "paragraph"
    HEADING = "heading"
