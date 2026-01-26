"""ORP (Optimal Recognition Point) calculator for RSVP reading."""

from typing import Optional, Set, Tuple

from .constants import (
    ABBREVIATIONS,
    ELLIPSIS_STRINGS,
    LONG_WORD_MULTIPLIER,
    LONG_WORD_THRESHOLD,
    MAJOR_PAUSE_MULTIPLIER,
    MAJOR_PAUSE_PUNCTUATION,
    MINOR_PAUSE_MULTIPLIER,
    MINOR_PAUSE_PUNCTUATION,
)
from .text_utils import (
    clean_word,
    get_clean_word_length,
    get_terminal_punctuation,
    is_abbreviation,
)


class ORPCalculator:
    """
    Calculate the Optimal Recognition Point for words.

    The ORP is the character position in a word where the eye naturally
    focuses for fastest recognition. Research suggests this is typically
    about 35% into short words (<= 5 chars) and ~40% for longer words.

    This class also handles delay multiplier calculations for RSVP timing,
    ensuring proper pauses after punctuation and long words.
    """

    # ORP position by word length (0-indexed)
    ORP_TABLE = {
        1: 0,
        2: 0,
        3: 1,
        4: 1,
        5: 1,
        6: 2,
        7: 2,
        8: 3,
        9: 3,
        10: 4,
        11: 4,
        12: 4,
        13: 5,
        14: 5,
        15: 6,
    }

    def __init__(self, language: str = "en") -> None:
        """
        Initialize the ORP calculator.

        Args:
            language: Language code for abbreviation detection ('en' or 'de').
        """
        self.language = language
        self._abbreviations: Set[str] = ABBREVIATIONS.get(language, ABBREVIATIONS["en"])

    def calculate(self, word: str) -> int:
        """
        Calculate the ORP index for a word.

        The ORP (Optimal Recognition Point) is where the eye naturally
        focuses for fastest word recognition. This is typically slightly
        left of center, around 1/3 into the word.

        Args:
            word: The word to calculate ORP for.

        Returns:
            The 0-indexed position of the ORP character.
        """
        length = len(word)

        if length == 0:
            return 0

        if length in self.ORP_TABLE:
            return self.ORP_TABLE[length]

        # For very long words, use ~40% position
        return max(0, int(length * 0.4))

    def calculate_for_display(self, display_text: str, clean_text: str) -> int:
        """
        Calculate the ORP index for display text that may include punctuation.

        Args:
            display_text: The text as it will be displayed (may include punctuation).
            clean_text: The word without punctuation (used for ORP calculation).

        Returns:
            The 0-indexed position of the ORP character in the display text.
        """
        if not display_text:
            return 0

        if not clean_text:
            return 0

        # Use lower() instead of casefold() to preserve string length
        # casefold() can change length (e.g., "ß" -> "ss")
        start_offset = display_text.lower().find(clean_text.lower())
        if start_offset == -1:
            raise ValueError(
                "clean_text not found in display_text: "
                f"clean_text={clean_text!r} display_text={display_text!r}"
            )

        return start_offset + self.calculate(clean_text)

    def calculate_delay_multiplier(
        self,
        word: str,
        is_abbrev_override: Optional[bool] = None,
    ) -> float:
        """
        Calculate the delay multiplier for a word.

        The delay multiplier determines how long to display this word
        relative to the base WPM rate. Factors include:
        - Terminal punctuation (major pause: . ! ? : minor pause: , ; — –)
        - Word length (long words need more processing time)
        - Abbreviations (periods in abbreviations don't get full pause)

        Args:
            word: The word to calculate delay for.
            is_abbrev_override: Override abbreviation detection if known.

        Returns:
            Delay multiplier (1.0 = normal, >1.0 = longer display time).
        """
        if not word:
            return 1.0

        multiplier = 1.0

        # Check for terminal punctuation
        terminal = get_terminal_punctuation(word)

        if terminal:
            # Check if this is an abbreviation
            if is_abbrev_override is None:
                is_abbrev = is_abbreviation(word, self._abbreviations)
            else:
                is_abbrev = is_abbrev_override

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

    def calculate_pause(self, word: str) -> float:
        """
        Calculate any extra pause needed after a word in milliseconds.

        Note: This method is provided for backward compatibility.
        For token generation, use calculate_delay_multiplier() instead.

        Longer pauses after:
        - Sentence-ending punctuation (. ! ?)
        - Clause breaks (: ; ,)
        - Long words (cognitive load)

        Args:
            word: The word to calculate pause for.

        Returns:
            Extra pause in milliseconds (0.0 for no extra pause).
        """
        if not word:
            return 0.0

        last_char = word[-1]

        # Sentence endings get the longest pause
        if last_char in ".!?":
            return 150.0

        # Clause breaks get a medium pause
        if last_char in ":;":
            return 100.0

        # Commas get a short pause
        if last_char == ",":
            return 50.0

        # Long words get a slight pause for cognitive processing
        if len(word) > 10:
            return 30.0

        return 0.0

    def split_for_display(self, word: str) -> Tuple[str, str, str]:
        """
        Split a word into three parts for ORP display.

        This is useful for UI rendering where the ORP character
        is highlighted differently (e.g., red and bold) from the
        rest of the word.

        Args:
            word: The word to split.

        Returns:
            Tuple of (before_orp, orp_char, after_orp).

        Example:
            >>> calc = ORPCalculator()
            >>> calc.split_for_display("reading")
            ('re', 'a', 'ding')
        """
        if not word:
            return ("", "", "")

        orp_index = self.calculate(word)

        before = word[:orp_index]
        orp_char = word[orp_index] if orp_index < len(word) else ""
        after = word[orp_index + 1:] if orp_index + 1 < len(word) else ""

        return (before, orp_char, after)

    def process_token(
        self,
        display_text: str,
        clean_text: Optional[str] = None,
    ) -> Tuple[int, float]:
        """
        Process a token and return its ORP index and delay multiplier.

        This is a convenience method that calculates both the ORP index
        for display and the delay multiplier in one call.

        Args:
            display_text: The text as it will be displayed.
            clean_text: The text without punctuation (optional, derived if not provided).

        Returns:
            Tuple of (orp_index, delay_multiplier).

        Example:
            >>> calc = ORPCalculator()
            >>> calc.process_token("Hello,")
            (1, 1.5)  # ORP at index 1, 1.5x delay for comma
        """
        if clean_text is None:
            clean_text = clean_word(display_text)

        orp_index = self.calculate_for_display(display_text, clean_text)
        delay_multiplier = self.calculate_delay_multiplier(display_text)

        return (orp_index, delay_multiplier)
