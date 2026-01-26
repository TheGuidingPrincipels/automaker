"""
Shared text processing utilities for the tokenizer package.

These functions provide common operations used by multiple modules
(ORPCalculator, TimingCalculator, SentenceDetector).
"""

from typing import Optional, Set

from .constants import (
    ALL_QUOTES,
    BRACKET_CLOSERS,
    BRACKET_OPENERS,
    ELLIPSIS_STRINGS,
    MAJOR_PAUSE_PUNCTUATION,
    MINOR_PAUSE_PUNCTUATION,
    TRAILING_CLOSERS,
)

# Characters to strip when cleaning words
_PUNCTUATION_CHARS = ".,!?;:…—–"
_STRIP_CHARS = "".join(ALL_QUOTES | BRACKET_OPENERS | BRACKET_CLOSERS) + _PUNCTUATION_CHARS


def get_terminal_punctuation(word: str) -> Optional[str]:
    """
    Get the terminal punctuation character, ignoring trailing quotes/brackets.

    Args:
        word: The word to check.

    Returns:
        The terminal punctuation character (or ellipsis string), or None if no punctuation.

    Examples:
        >>> get_terminal_punctuation("hello.")
        '.'
        >>> get_terminal_punctuation('said."')
        '.'
        >>> get_terminal_punctuation("hello")
        None
        >>> get_terminal_punctuation("wait...")
        '...'
    """
    if not word:
        return None

    # Check for ellipsis first (multi-character)
    for ellipsis in ELLIPSIS_STRINGS:
        if word.endswith(ellipsis):
            return ellipsis
        # Also check inside trailing closers
        stripped = word.rstrip("".join(TRAILING_CLOSERS))
        if stripped.endswith(ellipsis):
            return ellipsis

    # Strip trailing closers (quotes, brackets) to find actual punctuation
    idx = len(word) - 1
    while idx >= 0 and word[idx] in TRAILING_CLOSERS:
        idx -= 1

    if idx < 0:
        return None

    char = word[idx]
    if char in MAJOR_PAUSE_PUNCTUATION or char in MINOR_PAUSE_PUNCTUATION:
        return char

    return None


def is_abbreviation(word: str, abbreviations: Set[str]) -> bool:
    """
    Check if a word is a known abbreviation.

    Args:
        word: The word to check.
        abbreviations: Set of known abbreviations (lowercase, without periods).

    Returns:
        True if the word is an abbreviation.

    Examples:
        >>> abbrevs = {"mr", "dr", "etc"}
        >>> is_abbreviation("Mr.", abbrevs)
        True
        >>> is_abbreviation("Hello.", abbrevs)
        False
    """
    # Strip punctuation and convert to lowercase
    clean = word.rstrip(".")
    for char in TRAILING_CLOSERS:
        clean = clean.rstrip(char)

    return clean.lower() in abbreviations


def clean_word(word: str) -> str:
    """
    Remove leading/trailing punctuation and quotes from a word.

    Args:
        word: The word to clean.

    Returns:
        Word without surrounding punctuation/quotes/brackets.

    Examples:
        >>> clean_word('"Hello,"')
        'Hello'
        >>> clean_word("(word)")
        'word'
    """
    if not word:
        return ""

    result = word.strip()
    result = result.lstrip(_STRIP_CHARS)
    result = result.rstrip(_STRIP_CHARS)
    return result


def get_clean_word_length(word: str) -> int:
    """
    Get the length of a word without leading/trailing punctuation.

    Args:
        word: The word to measure.

    Returns:
        Length of the cleaned word.

    Examples:
        >>> get_clean_word_length("hello")
        5
        >>> get_clean_word_length('"Hello,"')
        5
    """
    return len(clean_word(word))
