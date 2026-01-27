"""
Tokenizer package for RSVP text processing.

This package contains modules for tokenizing text for speed reading,
including:
- tokenizer: Main TokenizerPipeline class (primary entry point)
- base: Legacy Tokenizer class (backward compatibility)
- constants: Abbreviations, punctuation sets, and timing multipliers
- normalizer: Text normalization and Markdown/PDF conversion
- timing: Delay multiplier calculations for RSVP timing
- sentence: Sentence boundary detection

Primary usage:
    >>> from app.services.tokenizer import TokenizerPipeline, tokenize
    >>> pipeline = TokenizerPipeline(language="en")
    >>> result = pipeline.process("Hello world.")
    >>> # Or use convenience function:
    >>> result = tokenize("Hello world.")
"""

from typing import Literal

# Import type definitions
from .types import BreakType

# Import the main pipeline classes (primary API)
from .tokenizer import TokenizerPipeline, TokenizerResult, TokenData, tokenize

# Import the Tokenizer class for backward compatibility
from .base import Tokenizer

# Import normalizer functions and classes
from .normalizer import normalize_text, NormalizedText

# Import ORP calculator
from .orp import ORPCalculator

# Import timing calculator and utility functions
from .timing import (
    TimingCalculator,
    calculate_base_duration_ms,
    calculate_word_duration_ms,
    estimate_reading_time_ms,
    estimate_reading_time_formatted,
)

# Import sentence boundary detection
from .sentence import (
    SentenceDetector,
    SentenceBoundary,
    find_sentence_boundaries,
    is_sentence_end,
    find_sentence_start,
    find_sentence_end,
    split_into_sentences,
)

# Import all constants
from .constants import (
    # Version
    TOKENIZER_VERSION,
    SUPPORTED_LANGUAGES,
    # Sentence detection
    SENTENCE_ENDERS,
    # Punctuation sets
    MAJOR_PAUSE_PUNCTUATION,
    MINOR_PAUSE_PUNCTUATION,
    ELLIPSIS_STRINGS,
    # Timing multipliers
    LONG_WORD_THRESHOLD,
    LONG_WORD_MULTIPLIER,
    MAJOR_PAUSE_MULTIPLIER,
    MINOR_PAUSE_MULTIPLIER,
    ABBREVIATION_PERIOD_MULTIPLIER,
    PARAGRAPH_BREAK_MULTIPLIER,
    HEADING_BREAK_MULTIPLIER,
    # Brackets and quotes
    BRACKET_OPENERS,
    BRACKET_CLOSERS,
    OPENING_QUOTES,
    CLOSING_QUOTES,
    ALL_QUOTES,
    TRAILING_CLOSERS,
    # Abbreviations
    ENGLISH_ABBREVIATIONS,
    GERMAN_ABBREVIATIONS,
    ABBREVIATIONS,
    # Structural patterns
    PARAGRAPH_MARKERS,
    HEADING_PATTERN,
)


def get_tokenizer_version() -> str:
    """Return the current tokenizer version string."""
    return TOKENIZER_VERSION


def tokenize_text(
    text: str,
    *,
    source_type: Literal["paste", "md", "pdf"] = "paste",
    language: str = "en",
) -> tuple[str, list[TokenData]]:
    """
    Tokenize text and return (normalized_text, tokens).

    This is a thin compatibility wrapper used by Session 3+ plans.
    """
    result = tokenize(text, source_type=source_type, language=language)
    return result.normalized_text, result.tokens


def calculate_orp_display(
    display_text: str,
    clean_text: str,
    language: str = "en",
) -> int:
    """Calculate ORP index within display_text for the given clean_text."""
    calculator = ORPCalculator(language=language)
    return calculator.calculate_for_display(display_text, clean_text)


__all__ = [
    # Type definitions
    "BreakType",
    # Main pipeline (primary API)
    "TokenizerPipeline",
    "TokenizerResult",
    "TokenData",
    "tokenize",
    # Session 2 public API (referenced by Session 3+)
    "tokenize_text",
    "get_tokenizer_version",
    "calculate_orp_display",
    # Legacy tokenizer class (backward compatibility)
    "Tokenizer",
    # Normalizer
    "normalize_text",
    "NormalizedText",
    # Timing
    "TimingCalculator",
    "ORPCalculator",
    "calculate_base_duration_ms",
    "calculate_word_duration_ms",
    "estimate_reading_time_ms",
    "estimate_reading_time_formatted",
    # Sentence detection
    "SentenceDetector",
    "SentenceBoundary",
    "find_sentence_boundaries",
    "is_sentence_end",
    "find_sentence_start",
    "find_sentence_end",
    "split_into_sentences",
    # Version
    "TOKENIZER_VERSION",
    "SUPPORTED_LANGUAGES",
    # Sentence detection
    "SENTENCE_ENDERS",
    # Punctuation sets
    "MAJOR_PAUSE_PUNCTUATION",
    "MINOR_PAUSE_PUNCTUATION",
    "ELLIPSIS_STRINGS",
    # Timing multipliers
    "LONG_WORD_THRESHOLD",
    "LONG_WORD_MULTIPLIER",
    "MAJOR_PAUSE_MULTIPLIER",
    "MINOR_PAUSE_MULTIPLIER",
    "ABBREVIATION_PERIOD_MULTIPLIER",
    "PARAGRAPH_BREAK_MULTIPLIER",
    "HEADING_BREAK_MULTIPLIER",
    # Brackets and quotes
    "BRACKET_OPENERS",
    "BRACKET_CLOSERS",
    "OPENING_QUOTES",
    "CLOSING_QUOTES",
    "ALL_QUOTES",
    "TRAILING_CLOSERS",
    # Abbreviations
    "ENGLISH_ABBREVIATIONS",
    "GERMAN_ABBREVIATIONS",
    "ABBREVIATIONS",
    # Structural patterns
    "PARAGRAPH_MARKERS",
    "HEADING_PATTERN",
]
