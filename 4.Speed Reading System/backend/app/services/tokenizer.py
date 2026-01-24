"""Tokenizer service for splitting text into reading tokens."""

import re
from typing import List, Tuple


class Tokenizer:
    """Service for tokenizing text for RSVP reading."""

    # Sentence-ending punctuation
    SENTENCE_END = re.compile(r'[.!?]$')

    # Paragraph boundaries (double newlines)
    PARAGRAPH_SPLIT = re.compile(r'\n\s*\n')

    def tokenize(self, text: str) -> List[str]:
        """
        Split text into tokens (words) for RSVP display.

        Args:
            text: The input text to tokenize.

        Returns:
            List of word tokens.
        """
        # Normalize whitespace
        text = text.strip()

        # Split on whitespace
        tokens = text.split()

        return tokens

    def get_sentence_boundaries(self, tokens: List[str]) -> List[int]:
        """
        Find token indices that end sentences.

        Args:
            tokens: List of word tokens.

        Returns:
            List of indices where sentences end.
        """
        boundaries = []
        for i, token in enumerate(tokens):
            if self.SENTENCE_END.search(token):
                boundaries.append(i)
        return boundaries

    def find_sentence_start(self, tokens: List[str], position: int) -> int:
        """
        Find the start of the sentence containing the given position.

        Args:
            tokens: List of word tokens.
            position: Current token position.

        Returns:
            Index of the first token in the sentence.
        """
        if position <= 0:
            return 0

        # Walk backwards to find sentence end before this position
        for i in range(position - 1, -1, -1):
            if self.SENTENCE_END.search(tokens[i]):
                return i + 1
        return 0

    def count_words(self, text: str) -> int:
        """
        Count the number of words in text.

        Args:
            text: Input text.

        Returns:
            Word count.
        """
        return len(self.tokenize(text))
