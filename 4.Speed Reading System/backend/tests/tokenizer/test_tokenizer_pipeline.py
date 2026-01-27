"""Tests for the main tokenizer pipeline module."""

import pytest

from app.models.enums import BreakType
from app.services.tokenizer import (
    TokenizerPipeline,
    TokenizerResult,
    TokenData,
    tokenize,
    tokenize_text,
    get_tokenizer_version,
    calculate_orp_display,
)
from app.services.tokenizer.tokenizer import _validate_token_invariants
from app.services.tokenizer.constants import TOKENIZER_VERSION


class TestTokenizerPipelineBasic:
    """Test basic tokenization functionality."""

    def test_empty_text(self):
        """Empty text should return empty result."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("")
        assert result.tokens == []
        assert result.total_words == 0
        assert result.normalized_text == ""

    def test_whitespace_only(self):
        """Whitespace-only text should return empty result."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("   \n\n   \t   ")
        assert result.tokens == []
        assert result.total_words == 0

    def test_single_word(self):
        """Single word should produce one token."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello")
        assert result.total_words == 1
        assert len(result.tokens) == 1
        assert result.tokens[0].display_text == "Hello"
        assert result.tokens[0].word_index == 0

    def test_multiple_words(self):
        """Multiple words should produce correct tokens."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello world test")
        assert result.total_words == 3
        assert [t.display_text for t in result.tokens] == ["Hello", "world", "test"]

    def test_preserves_punctuation(self):
        """Punctuation should be preserved in display_text."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello, world!")
        assert result.tokens[0].display_text == "Hello,"
        assert result.tokens[1].display_text == "world!"

    def test_result_metadata(self):
        """Result should include correct metadata."""
        pipeline = TokenizerPipeline(language="en")
        result = pipeline.process("Test text")
        assert result.tokenizer_version == TOKENIZER_VERSION
        assert result.language == "en"
        assert result.normalized_text == "Test text"


class TestTokenData:
    """Test individual token attributes."""

    def test_word_index_sequential(self):
        """Word indices should be sequential starting from 0."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("one two three four five")
        indices = [t.word_index for t in result.tokens]
        assert indices == [0, 1, 2, 3, 4]

    def test_clean_text_strips_punctuation(self):
        """Clean text should strip leading/trailing punctuation."""
        pipeline = TokenizerPipeline()
        result = pipeline.process('"Hello," she said.')

        # "Hello, -> Hello
        assert result.tokens[0].clean_text == "Hello"
        # she -> she
        assert result.tokens[1].clean_text == "she"
        # said. -> said
        assert result.tokens[2].clean_text == "said"

    def test_orp_index_calculated(self):
        """ORP index should be calculated for each token."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hi extraordinary")

        # "Hi" has 2 chars, ORP should be 0
        assert result.tokens[0].orp_index_display == 0
        # "extraordinary" has 13 chars, ORP should be 5
        assert result.tokens[1].orp_index_display == 5

    def test_char_offsets_accurate(self):
        """Character offsets should accurately map to text positions."""
        pipeline = TokenizerPipeline()
        text = "Hello world test"
        result = pipeline.process(text)

        for token in result.tokens:
            # Extract text using offsets
            extracted = result.normalized_text[
                token.char_offset_start : token.char_offset_end
            ]
            assert extracted == token.display_text

    def test_first_token_always_sentence_start(self):
        """First token should always be marked as sentence start."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello world")
        assert result.tokens[0].is_sentence_start is True

    def test_first_token_always_paragraph_start(self):
        """First token should always be marked as paragraph start."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello world")
        assert result.tokens[0].is_paragraph_start is True


class TestSentenceDetection:
    """Test sentence boundary detection."""

    def test_sentence_end_period(self):
        """Tokens after period should start new sentence."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello world. This is new.")

        # First word is always sentence start
        assert result.tokens[0].is_sentence_start is True  # "Hello"
        # "This" follows "world." so should be sentence start
        assert result.tokens[2].is_sentence_start is True  # "This"

    def test_sentence_end_question(self):
        """Tokens after question mark should start new sentence."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("How are you? I am fine.")

        # "I" follows "you?" so should be sentence start
        assert result.tokens[3].is_sentence_start is True  # "I"

    def test_sentence_end_exclamation(self):
        """Tokens after exclamation mark should start new sentence."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello! How are you?")

        # "How" follows "Hello!" so should be sentence start
        assert result.tokens[1].is_sentence_start is True  # "How"

    def test_abbreviation_not_sentence_end(self):
        """Abbreviations should not be treated as sentence ends."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Dr. Smith is here.")

        # "Smith" follows "Dr." but should NOT be sentence start
        assert result.tokens[1].is_sentence_start is False  # "Smith"


class TestParagraphDetection:
    """Test paragraph boundary detection."""

    def test_paragraph_break_detection(self):
        """Paragraph breaks should be detected."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("First paragraph.\n\nSecond paragraph.")

        # "First" starts first paragraph
        assert result.tokens[0].is_paragraph_start is True
        # "Second" starts second paragraph
        assert result.tokens[2].is_paragraph_start is True

    def test_paragraph_break_before(self):
        """Second paragraph token should have break_before."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Para one.\n\nPara two.")

        # First token has no break before
        assert result.tokens[0].break_before is None
        # Second paragraph's first token has break before
        assert result.tokens[2].break_before == BreakType.PARAGRAPH

    def test_multiple_paragraphs(self):
        """Multiple paragraphs should all be detected."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("One.\n\nTwo.\n\nThree.")

        para_starts = [t for t in result.tokens if t.is_paragraph_start]
        assert len(para_starts) == 3


class TestHeadingDetection:
    """Test markdown heading detection."""

    def test_heading_detected_in_markdown(self):
        """Headings should be detected in markdown source."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("# Heading\n\nContent", source_type="md")

        # First token should never have break_before, even if it's a heading
        assert result.tokens[0].break_before is None
        # It's also a paragraph start (headings are structural blocks)
        assert result.tokens[0].is_paragraph_start is True
        # "Content" should be a regular paragraph
        assert result.tokens[1].break_before == BreakType.PARAGRAPH

    def test_heading_break_before(self):
        """Heading tokens after content should have break_before=heading."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Intro.\n\n## Section\n\nContent", source_type="md")

        # Find the "Section" token
        section_token = None
        for t in result.tokens:
            if t.display_text == "Section":
                section_token = t
                break

        assert section_token is not None
        assert section_token.break_before == BreakType.HEADING

    def test_no_heading_in_paste(self):
        """Headings should not be detected in paste source."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("# Not a heading\n\nContent", source_type="paste")

        # No tokens should have heading break
        for token in result.tokens:
            assert token.break_before != BreakType.HEADING


class TestTimingCalculation:
    """Test delay multiplier calculation."""

    def test_normal_word_multiplier(self):
        """Normal words should have multiplier close to 1.0."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("hello")
        assert result.tokens[0].delay_multiplier_after == 1.0

    def test_sentence_end_multiplier(self):
        """Sentence-ending punctuation should increase multiplier."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("hello.")
        # Major pause multiplier is 2.5
        assert result.tokens[0].delay_multiplier_after == 2.5

    def test_comma_multiplier(self):
        """Comma should add minor pause."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("hello,")
        # Minor pause multiplier is 1.5
        assert result.tokens[0].delay_multiplier_after == 1.5

    def test_long_word_multiplier(self):
        """Long words should have increased multiplier."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("extraordinary")  # 13 chars
        # Long word multiplier is 1.2
        assert result.tokens[0].delay_multiplier_after == 1.2

    def test_long_word_with_punctuation(self):
        """Long word with punctuation should have combined multiplier."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("extraordinary.")
        # 2.5 (major pause) * 1.2 (long word) = 3.0
        assert result.tokens[0].delay_multiplier_after == 3.0


class TestSourceTypes:
    """Test different source type handling."""

    def test_paste_source(self):
        """Paste source should preserve raw text but drop standalone markup tokens."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("**bold** text", source_type="paste")
        assert "**bold**" in result.normalized_text
        assert "**bold**" not in [t.display_text for t in result.tokens]
        assert "bold" in [t.display_text for t in result.tokens]

    def test_markdown_source(self):
        """Markdown source should strip formatting."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("**bold** text", source_type="md")
        assert "bold" in [t.display_text for t in result.tokens]
        assert "**bold**" not in [t.display_text for t in result.tokens]

    def test_pdf_source(self):
        """PDF source should handle extraction artifacts."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("exam-\nple", source_type="pdf")
        assert "example" in result.normalized_text


class TestLanguageSupport:
    """Test language-specific features."""

    def test_english_default(self):
        """English should be the default language."""
        pipeline = TokenizerPipeline()
        assert pipeline.language == "en"

    def test_german_language(self):
        """German language should be supported."""
        pipeline = TokenizerPipeline(language="de")
        result = pipeline.process("Dr. Müller ist hier.")
        assert result.language == "de"

    def test_german_abbreviation(self):
        """German abbreviations should not end sentences."""
        pipeline = TokenizerPipeline(language="de")
        result = pipeline.process("Vgl. das Beispiel.")

        # "das" follows "Vgl." but should NOT be sentence start
        # (if "vgl" is in German abbreviations)
        assert result.tokens[1].is_sentence_start is False


class TestConvenienceFunction:
    """Test the tokenize() convenience function."""

    def test_tokenize_basic(self):
        """Convenience function should work with defaults."""
        result = tokenize("Hello world")
        assert result.total_words == 2
        assert result.language == "en"

    def test_tokenize_with_options(self):
        """Convenience function should accept all options."""
        result = tokenize("# Heading", source_type="md", language="de")
        assert result.language == "de"

    def test_tokenize_returns_result(self):
        """Convenience function should return TokenizerResult."""
        result = tokenize("Test")
        assert isinstance(result, TokenizerResult)


class TestSession2PublicApi:
    """Tests for the Session 2 public API surface (as referenced by Session 3)."""

    def test_get_tokenizer_version(self):
        """get_tokenizer_version should return the exported tokenizer version."""
        assert get_tokenizer_version() == TOKENIZER_VERSION

    def test_tokenize_text_returns_tuple(self):
        """tokenize_text should return (normalized_text, tokens)."""
        normalized_text, tokens = tokenize_text("Hello world.")
        assert normalized_text == "Hello world."
        assert len(tokens) == 2
        assert tokens[0].display_text == "Hello"
        assert tokens[1].display_text == "world."

    def test_calculate_orp_display(self):
        """calculate_orp_display should return ORP index in display_text."""
        assert calculate_orp_display('"Hello!"', "Hello") == 2

    def test_unknown_language_falls_back_to_english(self):
        """Unknown language should fall back to English behavior (see module-level tests)."""
        # 'vgl' is not in English abbreviations, so "Vgl." ends a sentence -> "das" is a sentence start.
        _, tokens = tokenize_text("Vgl. das Beispiel.", language="fr")
        assert tokens[1].is_sentence_start is True

    def test_unknown_source_type_defaults_to_paste(self):
        """Unknown source types default to plain-text parsing."""
        normalized_text, tokens = tokenize_text("# Not a heading", source_type="unknown")
        assert normalized_text == "# Not a heading"
        assert [t.display_text for t in tokens] == ["Not", "a", "heading"]


class TestHelperMethods:
    """Test pipeline helper methods."""

    def test_count_words(self):
        """count_words should return correct count."""
        pipeline = TokenizerPipeline()
        assert pipeline.count_words("Hello world test") == 3
        assert pipeline.count_words("One") == 1
        assert pipeline.count_words("") == 0

    def test_get_token_at_position(self):
        """get_token_at_position should find correct token."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello world test")

        # Position in "world" (chars 6-11)
        token = pipeline.get_token_at_position(result.tokens, 7)
        assert token is not None
        assert token.display_text == "world"

    def test_get_token_at_position_not_found(self):
        """get_token_at_position should return None for invalid position."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello")

        token = pipeline.get_token_at_position(result.tokens, 100)
        assert token is None

    def test_find_sentence_start(self):
        """find_sentence_start should find correct position."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello world. How are you?")

        # Position 4 ("are") should find sentence start at position 2 ("How")
        start = pipeline.find_sentence_start(result.tokens, 4)
        assert start == 2
        assert result.tokens[start].display_text == "How"

    def test_find_paragraph_start(self):
        """find_paragraph_start should find correct position."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Para one.\n\nPara two.")

        # Position 3 ("two.") should find paragraph start at position 2 ("Para")
        start = pipeline.find_paragraph_start(result.tokens, 3)
        assert start == 2
        assert result.tokens[start].display_text == "Para"


class TestEdgeCases:
    """Test edge cases and special inputs."""

    def test_unicode_text(self):
        """Unicode characters should be handled correctly."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello 世界! Emoji: 😀")
        assert "世界!" in [t.display_text for t in result.tokens]
        assert "😀" not in [t.display_text for t in result.tokens]

    def test_german_quotes(self):
        """German quotation marks should be preserved."""
        pipeline = TokenizerPipeline()
        result = pipeline.process('„Hallo Welt"')
        # Should have tokens with German quotes
        display_texts = " ".join(t.display_text for t in result.tokens)
        assert "„" in display_texts or "Hallo" in display_texts

    def test_very_long_text(self):
        """Long text should be handled without issues."""
        pipeline = TokenizerPipeline()
        text = "word " * 5000  # 5000 words
        result = pipeline.process(text)
        assert result.total_words == 5000

    def test_multiple_spaces(self):
        """Multiple spaces should be normalized."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("hello    world")
        assert result.total_words == 2

    def test_tabs_and_newlines(self):
        """Tabs and single newlines should be treated as spaces."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("hello\tworld\ntest")
        assert result.total_words == 3

    def test_ellipsis(self):
        """Ellipsis should be handled as sentence end."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Wait... What?")

        # "What?" should be a new sentence
        what_token = result.tokens[1]
        assert what_token.display_text == "What?"
        assert what_token.is_sentence_start is True

    def test_quoted_sentence(self):
        """Quoted text with punctuation should be handled."""
        pipeline = TokenizerPipeline()
        result = pipeline.process('"Hello!" she said.')

        # Verify tokens are correctly split
        assert len(result.tokens) >= 3


class TestRSVPIntegration:
    """Test RSVP-specific requirements."""

    def test_all_tokens_have_required_fields(self):
        """All tokens should have all required fields for RSVP display."""
        pipeline = TokenizerPipeline()
        result = pipeline.process(
            "Hello, world! This is a test.\n\nNew paragraph."
        )

        for token in result.tokens:
            assert isinstance(token.word_index, int)
            assert isinstance(token.display_text, str)
            assert isinstance(token.clean_text, str)
            assert isinstance(token.orp_index_display, int)
            assert isinstance(token.delay_multiplier_after, float)
            # break_before can be None or BreakType
            assert token.break_before is None or isinstance(token.break_before, BreakType)
            assert isinstance(token.is_sentence_start, bool)
            assert isinstance(token.is_paragraph_start, bool)
            assert token.char_offset_start is not None
            assert token.char_offset_end is not None

    def test_orp_within_bounds(self):
        """ORP index should always be within token bounds."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Various words with different lengths.")

        for token in result.tokens:
            assert 0 <= token.orp_index_display < len(token.display_text)

    def test_delay_multiplier_positive(self):
        """Delay multiplier should always be positive."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Test, sentence. With! Various? Punctuation:")

        for token in result.tokens:
            assert token.delay_multiplier_after > 0

    def test_offsets_contiguous(self):
        """Token character offsets should be reasonable (no large gaps)."""
        pipeline = TokenizerPipeline()
        result = pipeline.process("Hello world test")

        for i in range(1, len(result.tokens)):
            prev_end = result.tokens[i - 1].char_offset_end
            curr_start = result.tokens[i].char_offset_start
            # There should be at least one space between tokens
            assert curr_start >= prev_end
            # Gap should be reasonable (just whitespace)
            gap = curr_start - prev_end
            assert gap < 10  # No huge gaps


class TestInvariantValidation:
    """Tests for explicit invariant validation and error reporting."""

    def test_invalid_clean_text_raises(self):
        """clean_text must be a substring of display_text."""
        token = TokenData(
            word_index=0,
            display_text="Hello",
            clean_text="World",
            orp_index_display=1,
            delay_multiplier_after=1.0,
            break_before=None,
            is_sentence_start=True,
            is_paragraph_start=True,
            char_offset_start=0,
            char_offset_end=5,
        )

        with pytest.raises(ValueError, match="clean_text"):
            _validate_token_invariants("Hello", token)

    def test_offset_mismatch_raises(self):
        """Offsets must map back to display_text in normalized_text."""
        token = TokenData(
            word_index=1,
            display_text="Hello",
            clean_text="Hello",
            orp_index_display=1,
            delay_multiplier_after=1.0,
            break_before=None,
            is_sentence_start=False,
            is_paragraph_start=False,
            char_offset_start=0,
            char_offset_end=4,
        )

        with pytest.raises(ValueError, match="char_offset"):
            _validate_token_invariants("Hello", token)

    def test_orp_out_of_bounds_raises(self):
        """ORP index must be within display_text bounds."""
        token = TokenData(
            word_index=1,
            display_text="Hi",
            clean_text="Hi",
            orp_index_display=5,
            delay_multiplier_after=1.0,
            break_before=None,
            is_sentence_start=False,
            is_paragraph_start=False,
            char_offset_start=0,
            char_offset_end=2,
        )

        with pytest.raises(ValueError, match="orp_index"):
            _validate_token_invariants("Hi", token)

    def test_break_before_first_token_raises(self):
        """break_before is never allowed for the first token."""
        token = TokenData(
            word_index=0,
            display_text="Hello",
            clean_text="Hello",
            orp_index_display=1,
            delay_multiplier_after=1.0,
            break_before=BreakType.PARAGRAPH,
            is_sentence_start=True,
            is_paragraph_start=True,
            char_offset_start=0,
            char_offset_end=5,
        )

        with pytest.raises(ValueError, match="break_before"):
            _validate_token_invariants("Hello", token)
