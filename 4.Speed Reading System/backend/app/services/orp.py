"""ORP (Optimal Recognition Point) calculator for RSVP reading."""

from typing import Tuple


class ORPCalculator:
    """
    Calculate the Optimal Recognition Point for words.

    The ORP is the character position in a word where the eye naturally
    focuses for fastest recognition. Research suggests this is typically
    about 1/3 into the word, adjusted for word length.
    """

    # ORP position by word length (0-indexed)
    # Based on RSVP research for optimal fixation points
    ORP_TABLE = {
        1: 0,   # 1 char: focus on char 0
        2: 0,   # 2 chars: focus on char 0
        3: 1,   # 3 chars: focus on char 1
        4: 1,   # 4 chars: focus on char 1
        5: 1,   # 5 chars: focus on char 1
        6: 2,   # 6 chars: focus on char 2
        7: 2,   # 7 chars: focus on char 2
        8: 2,   # 8 chars: focus on char 2
        9: 3,   # 9 chars: focus on char 3
        10: 3,  # 10 chars: focus on char 3
        11: 3,  # 11 chars: focus on char 3
        12: 4,  # 12 chars: focus on char 4
        13: 4,  # 13+ chars: focus on char 4
    }

    def calculate(self, word: str) -> int:
        """
        Calculate the ORP index for a word.

        Args:
            word: The word to calculate ORP for.

        Returns:
            The 0-indexed position of the ORP character.
        """
        length = len(word)

        if length == 0:
            return 0

        if length <= 13:
            return self.ORP_TABLE.get(length, 0)

        # For very long words, use ~1/4 position
        return min(4, length - 1)

    def calculate_pause(self, word: str) -> float:
        """
        Calculate any extra pause needed after a word.

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
        if last_char in '.!?':
            return 150.0

        # Clause breaks get a medium pause
        if last_char in ':;':
            return 100.0

        # Commas get a short pause
        if last_char == ',':
            return 50.0

        # Long words get a slight pause for cognitive processing
        if len(word) > 10:
            return 30.0

        return 0.0

    def split_for_display(self, word: str) -> Tuple[str, str, str]:
        """
        Split a word into three parts for ORP display.

        Args:
            word: The word to split.

        Returns:
            Tuple of (before_orp, orp_char, after_orp).
        """
        if not word:
            return ("", "", "")

        orp_index = self.calculate(word)

        before = word[:orp_index]
        orp_char = word[orp_index] if orp_index < len(word) else ""
        after = word[orp_index + 1:] if orp_index + 1 < len(word) else ""

        return (before, orp_char, after)
