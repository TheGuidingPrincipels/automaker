"""Tests for ORP (Optimal Recognition Point) calculator."""

import pytest

from app.services.tokenizer.orp import ORPCalculator
from app.services.tokenizer.constants import (
    LONG_WORD_MULTIPLIER,
    LONG_WORD_THRESHOLD,
    MAJOR_PAUSE_MULTIPLIER,
    MINOR_PAUSE_MULTIPLIER,
)
from app.services.tokenizer.text_utils import (
    get_terminal_punctuation,
    get_clean_word_length,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def calculator():
    """Create an English ORP calculator."""
    return ORPCalculator(language="en")


@pytest.fixture
def german_calculator():
    """Create a German ORP calculator."""
    return ORPCalculator(language="de")


# =============================================================================
# ORP Calculation Tests
# =============================================================================


class TestORPCalculation:
    """Tests for basic ORP calculation."""

    @pytest.mark.parametrize(
        "word,expected_orp",
        [
            # Empty and single character
            ("", 0),
            ("a", 0),
            ("I", 0),
            # Two characters
            ("to", 0),
            ("at", 0),
            # Three characters
            ("the", 1),
            ("and", 1),
            # Four characters
            ("word", 1),
            ("test", 1),
            # Five characters
            ("hello", 1),
            ("world", 1),
            # Six characters
            ("system", 2),
            ("reader", 2),
            # Seven characters
            ("reading", 2),
            ("display", 2),
            # Eight characters
            ("computer", 3),
            ("optimize", 3),
            # Nine characters
            ("algorithm", 3),
            ("determine", 3),
            # Ten characters
            ("processing", 4),
            ("understand", 4),
            # Eleven characters
            ("information", 4),
            ("recognition", 4),
            # Twelve characters
            ("distribution", 4),
            ("professional", 4),
            # Thirteen+ characters
            ("implementation", 5),
            ("extraordinarily", 6),
            ("internationalization", 8),
        ],
    )
    def test_orp_by_word_length(self, calculator, word, expected_orp):
        """Test ORP calculation follows the lookup table for various word lengths."""
        assert calculator.calculate(word) == expected_orp

    def test_orp_never_exceeds_word_length(self, calculator):
        """Test that ORP index never exceeds word length."""
        for length in range(1, 50):
            word = "a" * length
            orp = calculator.calculate(word)
            assert orp < length, f"ORP {orp} >= length {length}"

    def test_orp_scales_for_long_words(self, calculator):
        """Test that ORP scales with word length for long words."""
        very_long_word = "a" * 100
        assert calculator.calculate(very_long_word) == int(len(very_long_word) * 0.4)


# =============================================================================
# ORP for Display Text Tests
# =============================================================================


class TestORPForDisplay:
    """Tests for ORP calculation with display text (including punctuation)."""

    @pytest.mark.parametrize(
        "display_text,clean_text,expected_orp",
        [
            # Simple words (no punctuation)
            ("hello", "hello", 1),
            ("world", "world", 1),
            # Trailing punctuation - ORP calculated on core word
            ("Hello,", "Hello", 1),  # "Hello" (5 chars) -> ORP at 1
            ("world.", "world", 1),  # "world" (5 chars) -> ORP at 1
            ("question?", "question", 3),  # "question" (8 chars) -> ORP at 3
            ("exclaim!", "exclaim", 2),  # "exclaim" (7 chars) -> ORP at 2
            # Leading punctuation/quotes - adds offset to ORP
            ('"Hello', "Hello", 2),  # quote(1) + "Hello" ORP(1) = 2
            ("'world", "world", 2),  # quote(1) + "world" ORP(1) = 2
            ("(test)", "test", 2),  # paren(1) + "test" ORP(1) = 2
            # Both leading and trailing
            ('"Hello!"', "Hello", 2),  # quote(1) + "Hello" ORP(1) = 2
            ("'world,'", "world", 2),  # quote(1) + "world" ORP(1) = 2
            ("(test.)", "test", 2),  # paren(1) + "test" ORP(1) = 2
            # Complex cases
            ('("nested")', "nested", 4),  # 2 chars offset + "nested" (6 chars) ORP(2) = 4
            ("...ellipsis", "ellipsis", 6),  # 3 chars offset + "ellipsis" (8 chars) ORP(3) = 6
            # All punctuation
            ("...", "", 0),
            ("!!!", "", 0),
            ('"""', "", 0),
        ],
    )
    def test_orp_for_display(self, calculator, display_text, clean_text, expected_orp):
        """Test ORP calculation handles punctuation in display text."""
        assert calculator.calculate_for_display(display_text, clean_text) == expected_orp

    def test_empty_display_text(self, calculator):
        """Test ORP for empty display text."""
        assert calculator.calculate_for_display("", "") == 0

    def test_clean_text_not_found_raises(self, calculator):
        """Test that mismatched clean_text raises an error."""
        with pytest.raises(ValueError, match="clean_text"):
            calculator.calculate_for_display("Hello", "World")


# =============================================================================
# Delay Multiplier Tests
# =============================================================================


class TestDelayMultiplier:
    """Tests for delay multiplier calculation."""

    def test_no_punctuation_normal_word(self, calculator):
        """Test that words without punctuation have multiplier of 1.0."""
        assert calculator.calculate_delay_multiplier("hello") == 1.0
        assert calculator.calculate_delay_multiplier("world") == 1.0

    @pytest.mark.parametrize(
        "word,expected_multiplier",
        [
            # Major pause punctuation (using short words to avoid long word bonus)
            ("word.", MAJOR_PAUSE_MULTIPLIER),
            ("test!", MAJOR_PAUSE_MULTIPLIER),
            ("what?", MAJOR_PAUSE_MULTIPLIER),
            ("say:", MAJOR_PAUSE_MULTIPLIER),
            # Minor pause punctuation
            ("word,", MINOR_PAUSE_MULTIPLIER),
            ("clause;", MINOR_PAUSE_MULTIPLIER),
            # Em dash and en dash
            ("word\u2014", MINOR_PAUSE_MULTIPLIER),  # em dash
            ("word\u2013", MINOR_PAUSE_MULTIPLIER),  # en dash
        ],
    )
    def test_punctuation_multipliers(self, calculator, word, expected_multiplier):
        """Test delay multipliers for various punctuation."""
        assert calculator.calculate_delay_multiplier(word) == expected_multiplier

    @pytest.mark.parametrize(
        "word",
        [
            "...",
            "word...",
            "word\u2026",  # Unicode ellipsis
            'word..."',
        ],
    )
    def test_ellipsis_major_pause(self, calculator, word):
        """Test that ellipsis gets major pause."""
        multiplier = calculator.calculate_delay_multiplier(word)
        assert multiplier >= MAJOR_PAUSE_MULTIPLIER

    @pytest.mark.parametrize(
        "word",
        [
            "extraordinary",  # 13 chars
            "implementation",  # 14 chars
            "internationalization",  # 20 chars
        ],
    )
    def test_long_word_multiplier(self, calculator, word):
        """Test that long words get additional delay multiplier."""
        assert len(word) >= LONG_WORD_THRESHOLD
        multiplier = calculator.calculate_delay_multiplier(word)
        assert multiplier == LONG_WORD_MULTIPLIER

    def test_long_word_with_punctuation_stacks(self, calculator):
        """Test that long word multiplier stacks with punctuation multiplier."""
        # Long word with major pause punctuation
        word = "extraordinary."
        expected = MAJOR_PAUSE_MULTIPLIER * LONG_WORD_MULTIPLIER
        assert calculator.calculate_delay_multiplier(word) == expected

        # Long word with minor pause punctuation
        word = "extraordinary,"
        expected = MINOR_PAUSE_MULTIPLIER * LONG_WORD_MULTIPLIER
        assert calculator.calculate_delay_multiplier(word) == expected

    def test_empty_word(self, calculator):
        """Test delay multiplier for empty word."""
        assert calculator.calculate_delay_multiplier("") == 1.0


# =============================================================================
# Abbreviation Tests
# =============================================================================


class TestAbbreviations:
    """Tests for abbreviation detection and handling."""

    @pytest.mark.parametrize(
        "abbrev",
        [
            "Mr.",
            "Mrs.",
            "Dr.",
            "Prof.",
            "etc.",
            "vs.",
            "Inc.",
            "Ltd.",
            "Jan.",
            "Feb.",
        ],
    )
    def test_english_abbreviations_minor_pause(self, calculator, abbrev):
        """Test that English abbreviations get minor pause instead of major."""
        multiplier = calculator.calculate_delay_multiplier(abbrev)
        # Should be minor pause, not major
        assert multiplier == MINOR_PAUSE_MULTIPLIER

    @pytest.mark.parametrize(
        "abbrev",
        [
            "Dr.",
            "Prof.",
            "Hr.",
            "Fr.",
            "bzw.",
            "usw.",
            "z.B.",
            "d.h.",
        ],
    )
    def test_german_abbreviations_minor_pause(self, german_calculator, abbrev):
        """Test that German abbreviations get minor pause."""
        multiplier = german_calculator.calculate_delay_multiplier(abbrev)
        assert multiplier == MINOR_PAUSE_MULTIPLIER

    def test_non_abbreviation_gets_major_pause(self, calculator):
        """Test that non-abbreviations with period get major pause."""
        multiplier = calculator.calculate_delay_multiplier("word.")
        assert multiplier == MAJOR_PAUSE_MULTIPLIER

    def test_abbreviation_override(self, calculator):
        """Test that abbreviation detection can be overridden."""
        # Force treat "word." as abbreviation
        multiplier = calculator.calculate_delay_multiplier("word.", is_abbrev_override=True)
        assert multiplier == MINOR_PAUSE_MULTIPLIER

        # Force treat "Mr." as non-abbreviation
        multiplier = calculator.calculate_delay_multiplier("Mr.", is_abbrev_override=False)
        assert multiplier == MAJOR_PAUSE_MULTIPLIER


# =============================================================================
# Terminal Punctuation Tests
# =============================================================================


class TestTerminalPunctuation:
    """Tests for terminal punctuation detection."""

    @pytest.mark.parametrize(
        "word,expected",
        [
            ("hello", None),
            ("world.", "."),
            ("question?", "?"),
            ("exclaim!", "!"),
            ("clause:", ":"),
            ("comma,", ","),
            ("semi;", ";"),
            # With trailing quotes/brackets
            ('word."', "."),
            ("word!'", "!"),
            ('word?")', "?"),
            ("word,]", ","),
            # Ellipsis
            ("word...", "..."),
            ("word\u2026", "\u2026"),
        ],
    )
    def test_get_terminal_punctuation(self, calculator, word, expected):
        """Test terminal punctuation detection."""
        result = get_terminal_punctuation(word)
        assert result == expected

    def test_empty_word_no_terminal(self, calculator):
        """Test that empty word has no terminal punctuation."""
        assert get_terminal_punctuation("") is None


# =============================================================================
# Split for Display Tests
# =============================================================================


class TestSplitForDisplay:
    """Tests for splitting words for ORP display."""

    @pytest.mark.parametrize(
        "word,expected_split",
        [
            # Basic words
            ("a", ("", "a", "")),
            ("to", ("", "t", "o")),
            ("the", ("t", "h", "e")),
            ("word", ("w", "o", "rd")),
            ("hello", ("h", "e", "llo")),
            ("reading", ("re", "a", "ding")),
            ("algorithm", ("alg", "o", "rithm")),
            # Empty
            ("", ("", "", "")),
        ],
    )
    def test_split_for_display(self, calculator, word, expected_split):
        """Test word splitting for ORP display."""
        before, orp_char, after = calculator.split_for_display(word)
        assert (before, orp_char, after) == expected_split

    def test_split_preserves_full_word(self, calculator):
        """Test that split parts reassemble to original word."""
        words = ["hello", "world", "reading", "algorithm", "test"]
        for word in words:
            before, orp_char, after = calculator.split_for_display(word)
            assert before + orp_char + after == word


# =============================================================================
# Calculate Pause Tests (Legacy)
# =============================================================================


class TestCalculatePause:
    """Tests for legacy calculate_pause method."""

    @pytest.mark.parametrize(
        "word,expected_pause",
        [
            # Sentence endings
            ("sentence.", 150.0),
            ("exclaim!", 150.0),
            ("question?", 150.0),
            # Clause breaks
            ("clause:", 100.0),
            ("semi;", 100.0),
            # Comma
            ("comma,", 50.0),
            # Normal words
            ("hello", 0.0),
            ("world", 0.0),
            # Long words (>10 chars)
            ("extraordinary", 30.0),
            # Empty
            ("", 0.0),
        ],
    )
    def test_calculate_pause(self, calculator, word, expected_pause):
        """Test legacy pause calculation."""
        assert calculator.calculate_pause(word) == expected_pause


# =============================================================================
# Process Token Tests
# =============================================================================


class TestProcessToken:
    """Tests for the convenience process_token method."""

    def test_process_token_basic(self, calculator):
        """Test basic token processing."""
        orp_index, delay = calculator.process_token("hello")
        assert orp_index == 1
        assert delay == 1.0

    def test_process_token_with_punctuation(self, calculator):
        """Test token processing with punctuation."""
        orp_index, delay = calculator.process_token("Hello,")
        assert orp_index == 1
        assert delay == MINOR_PAUSE_MULTIPLIER

    def test_process_token_sentence_end(self, calculator):
        """Test token processing at sentence end."""
        orp_index, delay = calculator.process_token("end.")
        assert orp_index == 1
        assert delay == MAJOR_PAUSE_MULTIPLIER

    def test_process_token_with_quotes(self, calculator):
        """Test token processing with quotes."""
        orp_index, delay = calculator.process_token('"Hello!"')
        assert orp_index == 2  # ORP on 'l' at index 2
        assert delay >= MAJOR_PAUSE_MULTIPLIER


# =============================================================================
# Language Support Tests
# =============================================================================


class TestLanguageSupport:
    """Tests for language-specific behavior."""

    def test_default_language_is_english(self):
        """Test that default language is English."""
        calc = ORPCalculator()
        assert calc.language == "en"

    def test_german_language(self):
        """Test German language initialization."""
        calc = ORPCalculator(language="de")
        assert calc.language == "de"

    def test_unknown_language_falls_back_to_english(self):
        """Test that unknown language falls back to English abbreviations."""
        calc = ORPCalculator(language="fr")
        # Should still work with English abbreviations
        assert calc.calculate_delay_multiplier("Mr.") == MINOR_PAUSE_MULTIPLIER

    def test_german_has_additional_abbreviations(self):
        """Test that German includes German-specific abbreviations."""
        en_calc = ORPCalculator(language="en")
        de_calc = ORPCalculator(language="de")

        # "bzw." is German-only
        # For English, it's not recognized as abbreviation -> major pause
        en_multiplier = en_calc.calculate_delay_multiplier("bzw.")
        assert en_multiplier == MAJOR_PAUSE_MULTIPLIER

        # For German, it's recognized as abbreviation -> minor pause
        de_multiplier = de_calc.calculate_delay_multiplier("bzw.")
        assert de_multiplier == MINOR_PAUSE_MULTIPLIER


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    @pytest.mark.parametrize(
        "word",
        [
            "123",
            "456789",
            "12345678901234567890",
        ],
    )
    def test_numeric_strings(self, calculator, word):
        """Test ORP calculation for numeric strings."""
        orp = calculator.calculate(word)
        assert 0 <= orp < len(word)

    @pytest.mark.parametrize(
        "word",
        [
            "word123",
            "123word",
            "word123word",
        ],
    )
    def test_mixed_alphanumeric(self, calculator, word):
        """Test ORP calculation for mixed alphanumeric strings."""
        orp = calculator.calculate(word)
        assert 0 <= orp < len(word)

    def test_unicode_characters(self, calculator):
        """Test ORP calculation handles unicode characters."""
        # German word with umlaut
        orp = calculator.calculate("Größe")
        assert 0 <= orp < len("Größe")

        # French with accents
        orp = calculator.calculate("café")
        assert 0 <= orp < len("café")

    def test_single_punctuation(self, calculator):
        """Test single punctuation character handling."""
        assert calculator.calculate_for_display(".", "") == 0
        assert calculator.calculate_for_display("!", "") == 0
        assert calculator.calculate_for_display(",", "") == 0

    @pytest.mark.parametrize(
        "word",
        [
            "word)",
            "word]",
            "word}",
            'word"',
            "word'",
        ],
    )
    def test_trailing_brackets_and_quotes(self, calculator, word):
        """Test that trailing brackets/quotes don't affect ORP."""
        # ORP should be calculated on "word" (4 chars) -> index 1
        orp = calculator.calculate_for_display(word, "word")
        assert orp == 1

    def test_clean_word_length_calculation(self, calculator):
        """Test clean word length calculation via text_utils."""
        # "hello" without punctuation
        assert get_clean_word_length("hello") == 5
        # With punctuation
        assert get_clean_word_length("hello.") == 5
        assert get_clean_word_length('"hello"') == 5
        assert get_clean_word_length("(hello!)") == 5
        # All punctuation
        assert get_clean_word_length("...") == 0
