"""
Sentence boundary detection for RSVP reading.

This module provides robust sentence boundary detection that handles:
- Standard sentence-ending punctuation (. ! ?)
- Abbreviations (Mr., Dr., etc.) that don't end sentences
- Punctuation inside quotes and brackets
- Ellipsis (... and Unicode …)
- Unicode sentence terminators

The SentenceDetector class provides methods for:
- Finding sentence boundaries in token lists
- Finding the start of a sentence containing a given position
- Checking if a token ends a sentence
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from .constants import (
    ABBREVIATIONS,
    ELLIPSIS_STRINGS,
    SENTENCE_ENDERS,
    TRAILING_CLOSERS,
)


@dataclass
class SentenceBoundary:
    """Represents a sentence boundary in a token list.

    Attributes:
        token_index: The index of the token that ends the sentence.
        boundary_type: The type of boundary ('terminal', 'ellipsis', or 'break').
        punctuation: The punctuation character(s) that ended the sentence.
    """

    token_index: int
    boundary_type: str  # 'terminal', 'ellipsis', 'break'
    punctuation: Optional[str] = None


class SentenceDetector:
    """
    Detect sentence boundaries in tokenized text.

    This class provides methods for finding sentence endings in a list of
    tokens, handling common edge cases like abbreviations and quoted text.

    Example usage:
        >>> detector = SentenceDetector(language="en")
        >>> tokens = ["Hello", "world.", "How", "are", "you?"]
        >>> boundaries = detector.find_boundaries(tokens)
        >>> [b.token_index for b in boundaries]
        [1, 4]

        >>> detector.is_sentence_end("world.")
        True
        >>> detector.is_sentence_end("Mr.")
        False
    """

    # Regex to match sentence-ending punctuation at end of word
    # Handles punctuation followed by optional trailing closers
    _SENTENCE_END_PATTERN = re.compile(
        r'[.!?](?:["\'\)\]\}»«›‹])*$'
    )

    # Regex to detect ellipsis patterns
    _ELLIPSIS_PATTERN = re.compile(r'\.{3}|…')

    def __init__(self, language: str = "en") -> None:
        """
        Initialize the sentence detector.

        Args:
            language: Language code for abbreviation detection ('en' or 'de').
                     Defaults to 'en'.
        """
        self.language = language
        self._abbreviations: Set[str] = ABBREVIATIONS.get(
            language, ABBREVIATIONS["en"]
        )

    def find_boundaries(
        self,
        tokens: List[str],
        *,
        paragraph_break_indices: Optional[List[int]] = None,
    ) -> List[SentenceBoundary]:
        """
        Find all sentence boundaries in a list of tokens.

        Args:
            tokens: List of word tokens.
            paragraph_break_indices: Optional list of token indices where
                                    paragraphs start. These are implicit
                                    sentence boundaries.

        Returns:
            List of SentenceBoundary objects indicating where sentences end.

        Examples:
            >>> detector = SentenceDetector()
            >>> tokens = ["Hello.", "How", "are", "you?"]
            >>> boundaries = detector.find_boundaries(tokens)
            >>> [(b.token_index, b.boundary_type) for b in boundaries]
            [(0, 'terminal'), (3, 'terminal')]
        """
        boundaries: List[SentenceBoundary] = []
        para_breaks = set(paragraph_break_indices or [])

        for i, token in enumerate(tokens):
            # Check for paragraph break (implicit sentence boundary)
            # A paragraph break BEFORE a token means the PREVIOUS token
            # ended a sentence (if there was one)
            if i in para_breaks and i > 0:
                # Only add if the previous token didn't already end a sentence
                if not boundaries or boundaries[-1].token_index != i - 1:
                    boundaries.append(SentenceBoundary(
                        token_index=i - 1,
                        boundary_type="break",
                    ))

            # Check for sentence-ending punctuation
            boundary = self._check_sentence_end(token, i, tokens)
            if boundary:
                boundaries.append(boundary)

        return boundaries

    def find_boundary_indices(
        self,
        tokens: List[str],
        *,
        paragraph_break_indices: Optional[List[int]] = None,
    ) -> List[int]:
        """
        Find token indices that end sentences.

        This is a convenience method that returns just the indices
        without the full SentenceBoundary objects.

        Args:
            tokens: List of word tokens.
            paragraph_break_indices: Optional list of token indices where
                                    paragraphs start.

        Returns:
            List of token indices where sentences end.

        Examples:
            >>> detector = SentenceDetector()
            >>> tokens = ["Hello.", "How", "are", "you?"]
            >>> detector.find_boundary_indices(tokens)
            [0, 3]
        """
        boundaries = self.find_boundaries(
            tokens,
            paragraph_break_indices=paragraph_break_indices,
        )
        return [b.token_index for b in boundaries]

    def is_sentence_end(
        self,
        token: str,
        *,
        next_token: Optional[str] = None,
        is_abbreviation: Optional[bool] = None,
    ) -> bool:
        """
        Check if a token ends a sentence.

        Args:
            token: The token to check.
            next_token: The token following this one (for context).
                       If provided and starts lowercase, the current
                       token is less likely to end a sentence.
            is_abbreviation: Override abbreviation detection if known.

        Returns:
            True if the token ends a sentence.

        Examples:
            >>> detector = SentenceDetector()
            >>> detector.is_sentence_end("word.")
            True
            >>> detector.is_sentence_end("Mr.")
            False
            >>> detector.is_sentence_end("Mr.", is_abbreviation=False)
            True
        """
        if not token:
            return False

        # Check for ellipsis
        if self._has_ellipsis(token):
            return True

        # Get terminal punctuation
        terminal = self._get_terminal_punctuation(token)
        if not terminal or terminal not in SENTENCE_ENDERS:
            return False

        # Check if this is an abbreviation
        if is_abbreviation is None:
            is_abbrev = self._is_abbreviation(token)
        else:
            is_abbrev = is_abbreviation

        if is_abbrev:
            return False

        # If we have context about the next token, use it
        if next_token:
            # If next token starts with lowercase, this might not be
            # a sentence boundary (but could still be, e.g., quoted speech)
            first_char = self._get_first_letter(next_token)
            if first_char and first_char.islower():
                # Could still be sentence end if followed by certain patterns
                # For now, we trust the punctuation
                pass

        return True

    def find_sentence_start(
        self,
        tokens: List[str],
        position: int,
    ) -> int:
        """
        Find the start of the sentence containing the given position.

        Args:
            tokens: List of word tokens.
            position: Current token position (0-indexed).

        Returns:
            Index of the first token in the sentence.

        Examples:
            >>> detector = SentenceDetector()
            >>> tokens = ["Hello.", "How", "are", "you?"]
            >>> detector.find_sentence_start(tokens, 3)
            1
            >>> detector.find_sentence_start(tokens, 0)
            0
        """
        if position <= 0:
            return 0

        # Walk backwards to find sentence end before this position
        for i in range(position - 1, -1, -1):
            if self.is_sentence_end(tokens[i]):
                return i + 1

        return 0

    def find_sentence_end(
        self,
        tokens: List[str],
        position: int,
    ) -> int:
        """
        Find the end of the sentence containing the given position.

        Args:
            tokens: List of word tokens.
            position: Current token position (0-indexed).

        Returns:
            Index of the last token in the sentence.

        Examples:
            >>> detector = SentenceDetector()
            >>> tokens = ["Hello.", "How", "are", "you?"]
            >>> detector.find_sentence_end(tokens, 1)
            3
            >>> detector.find_sentence_end(tokens, 0)
            0
        """
        if position >= len(tokens):
            return len(tokens) - 1

        # Walk forward to find sentence end at or after this position
        for i in range(position, len(tokens)):
            if self.is_sentence_end(tokens[i]):
                return i

        return len(tokens) - 1

    def get_sentence_range(
        self,
        tokens: List[str],
        position: int,
    ) -> Tuple[int, int]:
        """
        Get the start and end indices of the sentence containing position.

        Args:
            tokens: List of word tokens.
            position: Current token position (0-indexed).

        Returns:
            Tuple of (start_index, end_index) for the sentence.

        Examples:
            >>> detector = SentenceDetector()
            >>> tokens = ["Hello.", "How", "are", "you?"]
            >>> detector.get_sentence_range(tokens, 2)
            (1, 3)
        """
        start = self.find_sentence_start(tokens, position)
        end = self.find_sentence_end(tokens, position)
        return (start, end)

    def split_into_sentences(
        self,
        tokens: List[str],
    ) -> List[List[str]]:
        """
        Split a token list into sentences.

        Args:
            tokens: List of word tokens.

        Returns:
            List of token lists, one per sentence.

        Examples:
            >>> detector = SentenceDetector()
            >>> tokens = ["Hello.", "How", "are", "you?"]
            >>> detector.split_into_sentences(tokens)
            [['Hello.'], ['How', 'are', 'you?']]
        """
        if not tokens:
            return []

        sentences: List[List[str]] = []
        boundaries = self.find_boundary_indices(tokens)

        if not boundaries:
            return [tokens]

        start = 0
        for boundary_idx in boundaries:
            end = boundary_idx + 1
            if start < end <= len(tokens):
                sentences.append(tokens[start:end])
            start = end

        # Handle any remaining tokens after last boundary
        if start < len(tokens):
            sentences.append(tokens[start:])

        return sentences

    def _check_sentence_end(
        self,
        token: str,
        index: int,
        tokens: List[str],
    ) -> Optional[SentenceBoundary]:
        """
        Check if a token ends a sentence and return boundary info.

        Args:
            token: The token to check.
            index: Index of the token in the list.
            tokens: Full list of tokens (for context).

        Returns:
            SentenceBoundary if this token ends a sentence, None otherwise.
        """
        # Check for ellipsis first
        if self._has_ellipsis(token):
            ellipsis = "..." if "..." in token else "…"
            return SentenceBoundary(
                token_index=index,
                boundary_type="ellipsis",
                punctuation=ellipsis,
            )

        # Get next token for context (if available)
        next_token = tokens[index + 1] if index + 1 < len(tokens) else None

        if self.is_sentence_end(token, next_token=next_token):
            punct = self._get_terminal_punctuation(token)
            return SentenceBoundary(
                token_index=index,
                boundary_type="terminal",
                punctuation=punct,
            )

        return None

    def _get_terminal_punctuation(self, token: str) -> Optional[str]:
        """
        Get the terminal punctuation character, ignoring trailing closers.

        Args:
            token: The token to check.

        Returns:
            The terminal punctuation character, or None if no punctuation.
        """
        if not token:
            return None

        # Strip trailing closers to find actual punctuation
        idx = len(token) - 1
        while idx >= 0 and token[idx] in TRAILING_CLOSERS:
            idx -= 1

        if idx < 0:
            return None

        char = token[idx]
        if char in SENTENCE_ENDERS:
            return char

        return None

    def _has_ellipsis(self, token: str) -> bool:
        """
        Check if a token contains an ellipsis.

        Args:
            token: The token to check.

        Returns:
            True if the token contains an ellipsis.
        """
        for ellipsis in ELLIPSIS_STRINGS:
            if ellipsis in token:
                return True
        return False

    def _is_abbreviation(self, token: str) -> bool:
        """
        Check if a token is a known abbreviation.

        Args:
            token: The token to check.

        Returns:
            True if the token is an abbreviation.
        """
        # Strip punctuation and trailing closers
        clean = token.rstrip(".")
        for char in TRAILING_CLOSERS:
            clean = clean.rstrip(char)

        return clean.lower() in self._abbreviations

    def _get_first_letter(self, token: str) -> Optional[str]:
        """
        Get the first alphabetic character of a token.

        Args:
            token: The token to examine.

        Returns:
            The first letter, or None if no letters found.
        """
        for char in token:
            if char.isalpha():
                return char
        return None


# Convenience functions for simple use cases


def find_sentence_boundaries(
    tokens: List[str],
    language: str = "en",
) -> List[int]:
    """
    Find token indices that end sentences.

    This is a convenience function that creates a SentenceDetector
    and returns boundary indices.

    Args:
        tokens: List of word tokens.
        language: Language code ('en' or 'de').

    Returns:
        List of token indices where sentences end.

    Examples:
        >>> tokens = ["Hello", "world.", "How", "are", "you?"]
        >>> find_sentence_boundaries(tokens)
        [1, 4]
    """
    detector = SentenceDetector(language=language)
    return detector.find_boundary_indices(tokens)


def is_sentence_end(
    token: str,
    language: str = "en",
) -> bool:
    """
    Check if a token ends a sentence.

    This is a convenience function that creates a SentenceDetector
    and checks a single token.

    Args:
        token: The token to check.
        language: Language code ('en' or 'de').

    Returns:
        True if the token ends a sentence.

    Examples:
        >>> is_sentence_end("world.")
        True
        >>> is_sentence_end("Mr.")
        False
    """
    detector = SentenceDetector(language=language)
    return detector.is_sentence_end(token)


def find_sentence_start(
    tokens: List[str],
    position: int,
    language: str = "en",
) -> int:
    """
    Find the start of the sentence containing the given position.

    Args:
        tokens: List of word tokens.
        position: Current token position.
        language: Language code ('en' or 'de').

    Returns:
        Index of the first token in the sentence.

    Examples:
        >>> tokens = ["Hello.", "How", "are", "you?"]
        >>> find_sentence_start(tokens, 3)
        1
    """
    detector = SentenceDetector(language=language)
    return detector.find_sentence_start(tokens, position)


def find_sentence_end(
    tokens: List[str],
    position: int,
    language: str = "en",
) -> int:
    """
    Find the end of the sentence containing the given position.

    Args:
        tokens: List of word tokens.
        position: Current token position.
        language: Language code ('en' or 'de').

    Returns:
        Index of the last token in the sentence.

    Examples:
        >>> tokens = ["Hello.", "How", "are", "you?"]
        >>> find_sentence_end(tokens, 1)
        3
    """
    detector = SentenceDetector(language=language)
    return detector.find_sentence_end(tokens, position)


def split_into_sentences(
    tokens: List[str],
    language: str = "en",
) -> List[List[str]]:
    """
    Split a token list into sentences.

    Args:
        tokens: List of word tokens.
        language: Language code ('en' or 'de').

    Returns:
        List of token lists, one per sentence.

    Examples:
        >>> tokens = ["Hello.", "How", "are", "you?"]
        >>> split_into_sentences(tokens)
        [['Hello.'], ['How', 'are', 'you?']]
    """
    detector = SentenceDetector(language=language)
    return detector.split_into_sentences(tokens)
