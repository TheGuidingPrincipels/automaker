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

__all__ = [
    # Type definitions
    "BreakType",
    # Main pipeline (primary API)
    "TokenizerPipeline",
    "TokenizerResult",
    "TokenData",
    "tokenize",
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
