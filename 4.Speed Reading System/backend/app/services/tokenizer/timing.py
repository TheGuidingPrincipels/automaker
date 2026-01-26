"""
Timing and delay multiplier calculations for RSVP reading.

This module provides the TimingCalculator class for computing delay
multipliers based on word properties like length, punctuation, and
structural breaks (paragraphs, headings).

The delay multiplier determines how long to display a token relative
to the base word duration (derived from WPM setting).
"""

from typing import Optional, Set

from .constants import (
    ABBREVIATIONS,
    ELLIPSIS_STRINGS,
    HEADING_BREAK_MULTIPLIER,
    LONG_WORD_MULTIPLIER,
    LONG_WORD_THRESHOLD,
    MAJOR_PAUSE_MULTIPLIER,
    MAJOR_PAUSE_PUNCTUATION,
    MINOR_PAUSE_MULTIPLIER,
    MINOR_PAUSE_PUNCTUATION,
    PARAGRAPH_BREAK_MULTIPLIER,
)
from .text_utils import (
    get_clean_word_length,
    get_terminal_punctuation,
    is_abbreviation,
)


class TimingCalculator:
    """
    Calculate delay multipliers for RSVP word display timing.

    The delay multiplier controls how long each word is displayed relative
    to the base reading speed. A multiplier of 1.0 means normal duration,
    while higher values (e.g., 2.5) mean longer display times.

    Factors that affect timing:
    - Terminal punctuation (major pause: . ! ? : minor pause: , ; - -)
    - Word length (long words need more processing time)
    - Abbreviations (periods in abbreviations get reduced pause)
    - Structural breaks (paragraph/heading transitions)

    Example usage:
        >>> calc = TimingCalculator(language="en")
        >>> calc.calculate_delay("hello")
        1.0
        >>> calc.calculate_delay("sentence.")
        2.5
        >>> calc.calculate_delay("word,")
        1.5
        >>> calc.calculate_delay("extraordinarily")  # 15 chars
        1.2
    """

    def __init__(self, language: str = "en") -> None:
        """
        Initialize the timing calculator.

        Args:
            language: Language code for abbreviation detection ('en' or 'de').
                     Defaults to 'en'.
        """
        self.language = language
        self._abbreviations: Set[str] = ABBREVIATIONS.get(
            language, ABBREVIATIONS["en"]
        )

    def calculate_delay(
        self,
        word: str,
        *,
        is_abbreviation_override: Optional[bool] = None,
    ) -> float:
        """
        Calculate the delay multiplier for a word.

        The delay multiplier determines how long to display this word
        relative to the base WPM rate.

        Args:
            word: The word to calculate delay for.
            is_abbreviation_override: Override abbreviation detection if known.
                                     If None, abbreviation status is auto-detected.

        Returns:
            Delay multiplier (1.0 = normal, >1.0 = longer display time).

        Examples:
            >>> calc = TimingCalculator()
            >>> calc.calculate_delay("hello")
            1.0
            >>> calc.calculate_delay("world.")
            2.5
            >>> calc.calculate_delay("word,")
            1.5
        """
        if not word:
            return 1.0

        multiplier = 1.0

        # Check for terminal punctuation
        terminal = get_terminal_punctuation(word)

        if terminal:
            # Check if this is an abbreviation
            if is_abbreviation_override is None:
                is_abbrev = is_abbreviation(word, self._abbreviations)
            else:
                is_abbrev = is_abbreviation_override

            if terminal in ELLIPSIS_STRINGS:
                # Ellipsis gets major pause
                multiplier = max(multiplier, MAJOR_PAUSE_MULTIPLIER)
            elif terminal in MAJOR_PAUSE_PUNCTUATION:
                if is_abbrev and terminal == ".":
                    # Abbreviation period gets minor pause instead
                    multiplier = max(multiplier, MINOR_PAUSE_MULTIPLIER)
                else:
                    multiplier = max(multiplier, MAJOR_PAUSE_MULTIPLIER)
            elif terminal in MINOR_PAUSE_PUNCTUATION:
                multiplier = max(multiplier, MINOR_PAUSE_MULTIPLIER)

        # Check for long words (additional cognitive load)
        clean_length = get_clean_word_length(word)
        if clean_length >= LONG_WORD_THRESHOLD:
            # Long word multiplier stacks with punctuation
            multiplier *= LONG_WORD_MULTIPLIER

        return multiplier

    def calculate_break_delay(
        self,
        break_type: Optional[str],
    ) -> float:
        """
        Calculate the delay multiplier for structural breaks.

        These are delays inserted BEFORE a token that starts a new
        paragraph or heading section.

        Args:
            break_type: The type of break ("paragraph", "heading", or None).

        Returns:
            Delay multiplier for the break (1.0 = no additional delay).

        Examples:
            >>> calc = TimingCalculator()
            >>> calc.calculate_break_delay("paragraph")
            3.0
            >>> calc.calculate_break_delay("heading")
            3.5
            >>> calc.calculate_break_delay(None)
            1.0
        """
        if break_type == "heading":
            return HEADING_BREAK_MULTIPLIER
        elif break_type == "paragraph":
            return PARAGRAPH_BREAK_MULTIPLIER
        return 1.0

    def calculate_total_delay(
        self,
        word: str,
        *,
        break_type: Optional[str] = None,
        is_abbreviation_override: Optional[bool] = None,
    ) -> float:
        """
        Calculate the total delay multiplier including break delays.

        This combines the word delay (punctuation, length) with any
        structural break delay (paragraph, heading) for a complete
        timing value.

        Args:
            word: The word to calculate delay for.
            break_type: Type of break before this word ("paragraph", "heading", or None).
            is_abbreviation_override: Override abbreviation detection if known.

        Returns:
            Total delay multiplier combining word and break factors.

        Examples:
            >>> calc = TimingCalculator()
            >>> calc.calculate_total_delay("Hello", break_type="paragraph")
            3.0  # paragraph break
            >>> calc.calculate_total_delay("end.", break_type=None)
            2.5  # sentence end
        """
        word_delay = self.calculate_delay(word, is_abbreviation_override=is_abbreviation_override)
        break_delay = self.calculate_break_delay(break_type)

        # For breaks, use the maximum of break delay and word delay
        # (don't stack them, as that would create excessive pauses)
        return max(word_delay, break_delay)


def calculate_base_duration_ms(wpm: int) -> float:
    """
    Calculate the base word display duration from WPM (words per minute).

    Args:
        wpm: Target reading speed in words per minute.

    Returns:
        Base duration in milliseconds for one word.

    Raises:
        ValueError: If wpm is not positive.

    Examples:
        >>> calculate_base_duration_ms(300)
        200.0
        >>> calculate_base_duration_ms(600)
        100.0
    """
    if wpm <= 0:
        raise ValueError(f"WPM must be positive, got {wpm}")

    # 60,000 ms per minute / words per minute = ms per word
    return 60_000.0 / wpm


def calculate_word_duration_ms(
    base_duration_ms: float,
    delay_multiplier: float,
) -> float:
    """
    Calculate the actual display duration for a word.

    Args:
        base_duration_ms: Base duration in milliseconds (from WPM).
        delay_multiplier: Multiplier for this word (from TimingCalculator).

    Returns:
        Actual display duration in milliseconds.

    Examples:
        >>> calculate_word_duration_ms(200.0, 1.0)
        200.0
        >>> calculate_word_duration_ms(200.0, 2.5)
        500.0
    """
    return base_duration_ms * delay_multiplier


def estimate_reading_time_ms(
    word_count: int,
    wpm: int,
    average_multiplier: float = 1.15,
) -> float:
    """
    Estimate total reading time for a document.

    The average multiplier accounts for punctuation pauses and long words.
    Based on typical English text, the average multiplier is around 1.15.

    Args:
        word_count: Number of words in the document.
        wpm: Target reading speed in words per minute.
        average_multiplier: Average delay multiplier across all words.
                          Defaults to 1.15 (typical for English prose).

    Returns:
        Estimated reading time in milliseconds.

    Examples:
        >>> estimate_reading_time_ms(300, 300)  # 300 words at 300 WPM
        69000.0  # ~69 seconds with typical pauses
        >>> estimate_reading_time_ms(300, 300, 1.0)  # No pauses
        60000.0  # exactly 60 seconds
    """
    base_duration = calculate_base_duration_ms(wpm)
    return word_count * base_duration * average_multiplier


def estimate_reading_time_formatted(
    word_count: int,
    wpm: int,
    average_multiplier: float = 1.15,
) -> str:
    """
    Estimate total reading time and return as formatted string.

    Args:
        word_count: Number of words in the document.
        wpm: Target reading speed in words per minute.
        average_multiplier: Average delay multiplier across all words.

    Returns:
        Formatted string like "5 min" or "1 hr 23 min".

    Examples:
        >>> estimate_reading_time_formatted(1500, 300)
        "6 min"
        >>> estimate_reading_time_formatted(18000, 300)
        "1 hr 9 min"
    """
    total_ms = estimate_reading_time_ms(word_count, wpm, average_multiplier)
    total_seconds = total_ms / 1000
    total_minutes = int(total_seconds / 60)

    if total_minutes < 60:
        return f"{max(1, total_minutes)} min"

    hours = total_minutes // 60
    minutes = total_minutes % 60

    if minutes == 0:
        return f"{hours} hr"

    return f"{hours} hr {minutes} min"
