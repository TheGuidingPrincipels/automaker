"""
Main tokenization pipeline for RSVP reading.

This module provides the TokenizerPipeline class that orchestrates the complete
tokenization process for text input, producing Token objects ready for RSVP display.

Pipeline stages:
1. Text normalization (whitespace, markdown stripping, PDF cleanup)
2. Word tokenization with structural awareness (paragraphs, headings)
3. Sentence boundary detection
4. ORP (Optimal Recognition Point) calculation
5. Timing/delay multiplier calculation

Example usage:
    >>> pipeline = TokenizerPipeline(language="en")
    >>> result = pipeline.process("Hello world. This is a test.")
    >>> for token in result.tokens:
    ...     print(f"{token.display_text} (ORP: {token.orp_index_display})")
"""

import re
from dataclasses import dataclass
from typing import List, Literal, Optional

from .types import BreakType
from app.services.tokenizer.constants import (
    ALL_QUOTES,
    BRACKET_CLOSERS,
    BRACKET_OPENERS,
    TOKENIZER_VERSION,
)
from app.services.tokenizer.orp import ORPCalculator
from app.services.tokenizer.normalizer import normalize_text
from app.services.tokenizer.sentence import SentenceDetector
from app.services.tokenizer.timing import TimingCalculator

_PUNCTUATION_CHARS = ".,!?;:…—–"
_LEADING_CHARS = "".join(sorted(ALL_QUOTES | BRACKET_OPENERS))
_TRAILING_CHARS = "".join(sorted(ALL_QUOTES | BRACKET_CLOSERS))
_STRIP_CHARS = "".join(ALL_QUOTES | BRACKET_OPENERS | BRACKET_CLOSERS) + _PUNCTUATION_CHARS
_WORD_PATTERN = re.compile(
    rf"[{re.escape(_LEADING_CHARS)}]*"
    rf"[\w]+(?:[\'’\-.][\w]+)*"
    rf"(?:\.{{3}}|[{re.escape(_PUNCTUATION_CHARS)}])*"
    rf"[{re.escape(_TRAILING_CHARS)}]*",
    re.UNICODE,
)


@dataclass
class TokenData:
    """Data class representing a single token for RSVP display.

    This is a lightweight data container that mirrors the Token database model
    but can be used without database dependencies.

    Attributes:
        word_index: 0-based index of this token in the document.
        display_text: The text to display (includes punctuation, quotes).
        clean_text: The text without leading/trailing punctuation.
        orp_index_display: Index of the ORP character in display_text.
        delay_multiplier_after: Multiplier for display duration (1.0 = normal).
        break_before: Type of structural break before this token, if any.
        is_sentence_start: Whether this token starts a new sentence.
        is_paragraph_start: Whether this token starts a new paragraph.
        char_offset_start: Starting character offset in normalized text.
        char_offset_end: Ending character offset in normalized text (exclusive).
    """

    word_index: int
    display_text: str
    clean_text: str
    orp_index_display: int
    delay_multiplier_after: float = 1.0
    break_before: Optional[BreakType] = None
    is_sentence_start: bool = False
    is_paragraph_start: bool = False
    char_offset_start: Optional[int] = None
    char_offset_end: Optional[int] = None


@dataclass
class TokenizerResult:
    """Result of tokenization pipeline.

    Attributes:
        tokens: List of TokenData objects ready for RSVP display.
        normalized_text: The normalized text that was tokenized.
        total_words: Total number of tokens/words.
        tokenizer_version: Version of the tokenizer used.
        language: Language code used for processing.
    """

    tokens: List[TokenData]
    normalized_text: str
    total_words: int
    tokenizer_version: str
    language: str


def _validate_token_invariants(normalized_text: str, token: "TokenData") -> None:
    """
    Validate tokenizer invariants and raise explicit errors on violations.

    Args:
        normalized_text: The normalized source text.
        token: TokenData to validate.
    """
    if token.word_index == 0 and token.break_before is not None:
        raise ValueError("break_before must be None for the first token")

    if token.char_offset_start is None or token.char_offset_end is None:
        raise ValueError("char_offset values must be set for all tokens")

    extracted = normalized_text[token.char_offset_start:token.char_offset_end]
    if extracted != token.display_text:
        raise ValueError(
            "char_offset mismatch: "
            f"expected {token.display_text!r}, got {extracted!r}"
        )

    if token.clean_text and token.clean_text.casefold() not in token.display_text.casefold():
        raise ValueError(
            "clean_text not found in display_text: "
            f"clean_text={token.clean_text!r} display_text={token.display_text!r}"
        )

    if token.display_text:
        if not (0 <= token.orp_index_display < len(token.display_text)):
            raise ValueError(
                f"orp_index out of bounds: orp_index={token.orp_index_display}"
            )
    elif token.orp_index_display != 0:
        raise ValueError(f"orp_index out of bounds: orp_index={token.orp_index_display}")


@dataclass
class _TokenPosition:
    """Internal class for tracking token positions during processing."""

    word_index: int
    display_text: str
    clean_text: str
    char_start: int
    char_end: int


class TokenizerPipeline:
    """
    Main tokenization pipeline for RSVP text processing.

    This class orchestrates the complete tokenization workflow, combining:
    - Text normalization (whitespace, markdown, PDF artifacts)
    - Word tokenization with structural awareness
    - Sentence boundary detection
    - ORP calculation for optimal focus point
    - Timing calculation for display duration

    Example usage:
        >>> pipeline = TokenizerPipeline(language="en")
        >>> result = pipeline.process(
        ...     "Hello world. This is a test.",
        ...     source_type="paste"
        ... )
        >>> print(f"Tokenized {result.total_words} words")

        # Access individual tokens
        >>> for token in result.tokens[:5]:
        ...     print(f"{token.word_index}: {token.display_text}")
    """

    def __init__(self, language: str = "en") -> None:
        """
        Initialize the tokenizer pipeline.

        Args:
            language: Language code for abbreviation and sentence detection.
                     Supported: 'en' (English), 'de' (German).
                     Defaults to 'en'.
        """
        self.language = language
        self._orp_calculator = ORPCalculator(language=language)
        self._timing_calculator = TimingCalculator(language=language)
        self._sentence_detector = SentenceDetector(language=language)

    def process(
        self,
        raw_text: str,
        source_type: Literal["paste", "md", "pdf"] = "paste",
    ) -> TokenizerResult:
        """
        Process raw text through the complete tokenization pipeline.

        This is the main entry point for tokenization. It:
        1. Normalizes the text (whitespace, formatting, source-specific cleanup)
        2. Splits into word tokens while tracking character offsets
        3. Identifies paragraph and heading boundaries
        4. Detects sentence boundaries
        5. Calculates ORP and timing for each token

        Args:
            raw_text: The input text to tokenize.
            source_type: Type of source document:
                        - "paste": Plain text (default)
                        - "md": Markdown (strips formatting)
                        - "pdf": PDF text (handles extraction artifacts)

        Returns:
            TokenizerResult containing all tokens and metadata.

        Example:
            >>> pipeline = TokenizerPipeline()
            >>> result = pipeline.process("Hello, world!")
            >>> len(result.tokens)
            2
            >>> result.tokens[0].display_text
            'Hello,'
        """
        # Stage 1: Normalize text
        normalized = normalize_text(raw_text, source_type=source_type)

        if not normalized.text.strip():
            return TokenizerResult(
                tokens=[],
                normalized_text="",
                total_words=0,
                tokenizer_version=TOKENIZER_VERSION,
                language=self.language,
            )

        # Stage 2: Tokenize into words with positions
        token_positions = self._tokenize_with_positions(normalized.text)

        if not token_positions:
            return TokenizerResult(
                tokens=[],
                normalized_text=normalized.text,
                total_words=0,
                tokenizer_version=TOKENIZER_VERSION,
                language=self.language,
            )

        # Stage 3: Map structural breaks (paragraphs, headings) to tokens
        paragraph_token_indices = self._map_char_positions_to_tokens(
            normalized.paragraph_breaks,
            token_positions,
        )
        heading_token_map = self._map_headings_to_tokens(
            normalized.heading_positions,
            token_positions,
        )

        # Stage 4: Detect sentence boundaries
        display_texts = [tp.display_text for tp in token_positions]
        sentence_boundaries = self._sentence_detector.find_boundary_indices(
            display_texts,
            paragraph_break_indices=list(paragraph_token_indices),
        )

        # Build set of sentence start indices (token after each boundary + first token)
        sentence_start_indices = {0}  # First token always starts a sentence
        for boundary_idx in sentence_boundaries:
            next_idx = boundary_idx + 1
            if next_idx < len(token_positions):
                sentence_start_indices.add(next_idx)

        # Stage 5: Build final tokens with all attributes
        tokens: List[TokenData] = []

        for i, tp in enumerate(token_positions):
            # Determine break type before this token
            break_before: Optional[BreakType] = None
            if i in heading_token_map and i > 0:
                break_before = BreakType.HEADING
            elif i in paragraph_token_indices and i > 0:
                # First token doesn't have a "break before" - it's just the start
                break_before = BreakType.PARAGRAPH

            # Calculate timing - include break type for proper delays
            delay_multiplier = self._timing_calculator.calculate_total_delay(
                tp.display_text,
                break_type=break_before.value if break_before else None,
            )

            # Calculate ORP
            orp_index = self._orp_calculator.calculate_for_display(
                tp.display_text,
                tp.clean_text,
            )

            # Extract clean text (without leading/trailing punctuation)
            clean_text = tp.clean_text

            # Determine structural flags
            is_paragraph_start = i in paragraph_token_indices
            is_sentence_start = i in sentence_start_indices

            token = TokenData(
                word_index=i,
                display_text=tp.display_text,
                clean_text=clean_text,
                orp_index_display=orp_index,
                delay_multiplier_after=delay_multiplier,
                break_before=break_before,
                is_sentence_start=is_sentence_start,
                is_paragraph_start=is_paragraph_start,
                char_offset_start=tp.char_start,
                char_offset_end=tp.char_end,
            )
            _validate_token_invariants(normalized.text, token)
            tokens.append(token)

        return TokenizerResult(
            tokens=tokens,
            normalized_text=normalized.text,
            total_words=len(tokens),
            tokenizer_version=TOKENIZER_VERSION,
            language=self.language,
        )

    def _tokenize_with_positions(
        self,
        text: str,
    ) -> List[_TokenPosition]:
        """
        Split text into word tokens while tracking character positions.

        This tokenizer uses a regex-based extractor that keeps punctuation
        attached to neighboring words and avoids standalone punctuation tokens.

        Args:
            text: The normalized text to tokenize.

        Returns:
            List of _TokenPosition objects with word and offset information.
        """
        tokens: List[_TokenPosition] = []

        for match in _WORD_PATTERN.finditer(text):
            display_text = match.group(0)
            clean_text = self._extract_clean_text(display_text)
            if not clean_text:
                continue

            tokens.append(
                _TokenPosition(
                    word_index=len(tokens),
                    display_text=display_text,
                    clean_text=clean_text,
                    char_start=match.start(),
                    char_end=match.end(),
                )
            )

        return tokens

    def _map_char_positions_to_tokens(
        self,
        char_positions: List[int],
        tokens: List[_TokenPosition],
    ) -> set[int]:
        """
        Map character positions (e.g., paragraph starts) to token indices.

        Given a list of character positions and the token list, finds which
        token index each character position falls within.

        Args:
            char_positions: List of character positions in the text.
            tokens: List of token positions from tokenization.

        Returns:
            Set of token indices that correspond to the character positions.
        """
        if not tokens or not char_positions:
            return set()

        result = set()
        token_idx = 0

        for char_pos in sorted(char_positions):
            # Find the token that contains or starts at this position
            while token_idx < len(tokens):
                tp = tokens[token_idx]
                if tp.char_start >= char_pos:
                    # This token starts at or after the position
                    result.add(token_idx)
                    break
                elif tp.char_start <= char_pos < tp.char_end:
                    # Position is within this token
                    result.add(token_idx)
                    break
                token_idx += 1

            # If we exhausted tokens, the position might be at the end
            # In that case, don't add anything

        return result

    def _map_headings_to_tokens(
        self,
        heading_positions: List[tuple[int, int]],
        tokens: List[_TokenPosition],
    ) -> dict[int, int]:
        """
        Map heading positions to token indices with heading levels.

        Args:
            heading_positions: List of (char_pos, heading_level) tuples.
            tokens: List of token positions from tokenization.

        Returns:
            Dict mapping token index to heading level.
        """
        if not tokens or not heading_positions:
            return {}

        result: dict[int, int] = {}
        token_idx = 0

        for char_pos, level in sorted(heading_positions, key=lambda x: x[0]):
            # Reset token index for each heading to handle non-sequential positions
            search_idx = token_idx

            while search_idx < len(tokens):
                tp = tokens[search_idx]
                if tp.char_start >= char_pos:
                    result[search_idx] = level
                    token_idx = search_idx  # Optimize next search
                    break
                elif tp.char_start <= char_pos < tp.char_end:
                    result[search_idx] = level
                    token_idx = search_idx
                    break
                search_idx += 1

        return result

    def _extract_clean_text(self, display_text: str) -> str:
        """
        Extract clean text from display text by removing leading/trailing punctuation.

        Args:
            display_text: The token text as displayed.

        Returns:
            The text with leading/trailing punctuation and quotes removed.
        """
        if not display_text:
            return ""

        result = display_text.strip()
        result = result.lstrip(_STRIP_CHARS)
        result = result.rstrip(_STRIP_CHARS)
        return result

    def count_words(self, text: str) -> int:
        """
        Count the number of words in text without full tokenization.

        This is a lightweight method for getting word count without
        the overhead of full token processing.

        Args:
            text: The text to count words in.

        Returns:
            Number of words in the text.
        """
        return len(text.split())

    def get_token_at_position(
        self,
        tokens: List[TokenData],
        char_position: int,
    ) -> Optional[TokenData]:
        """
        Find the token containing a given character position.

        Useful for mapping cursor positions to tokens.

        Args:
            tokens: List of tokens from process().
            char_position: Character position in the normalized text.

        Returns:
            The TokenData at that position, or None if not found.
        """
        for token in tokens:
            if (
                token.char_offset_start is not None
                and token.char_offset_end is not None
                and token.char_offset_start <= char_position < token.char_offset_end
            ):
                return token
        return None

    def find_sentence_start(
        self,
        tokens: List[TokenData],
        position: int,
    ) -> int:
        """
        Find the start token index of the sentence containing the given position.

        Args:
            tokens: List of tokens from process().
            position: Token index to find the sentence start for.

        Returns:
            Token index of the first token in the sentence.
        """
        if position <= 0:
            return 0

        # Walk backwards to find a token that starts a sentence
        for i in range(position, -1, -1):
            if i < len(tokens) and tokens[i].is_sentence_start:
                return i

        return 0

    def find_paragraph_start(
        self,
        tokens: List[TokenData],
        position: int,
    ) -> int:
        """
        Find the start token index of the paragraph containing the given position.

        Args:
            tokens: List of tokens from process().
            position: Token index to find the paragraph start for.

        Returns:
            Token index of the first token in the paragraph.
        """
        if position <= 0:
            return 0

        # Walk backwards to find a token that starts a paragraph
        for i in range(position, -1, -1):
            if i < len(tokens) and tokens[i].is_paragraph_start:
                return i

        return 0


# Convenience function for simple use cases
def tokenize(
    text: str,
    source_type: Literal["paste", "md", "pdf"] = "paste",
    language: str = "en",
) -> TokenizerResult:
    """
    Tokenize text using the default pipeline configuration.

    This is a convenience function that creates a TokenizerPipeline
    and processes the text in one call.

    Args:
        text: The input text to tokenize.
        source_type: Type of source ("paste", "md", or "pdf").
        language: Language code ('en' or 'de').

    Returns:
        TokenizerResult with all processed tokens.

    Example:
        >>> result = tokenize("Hello, world!")
        >>> print(result.total_words)
        2
    """
    pipeline = TokenizerPipeline(language=language)
    return pipeline.process(text, source_type=source_type)
