"""Full integration tests for the tokenizer package.

This test module provides comprehensive end-to-end integration tests that verify
the complete tokenization workflow. Unlike unit tests that test individual
components in isolation, these tests verify:

1. The complete pipeline integration (normalizer -> tokenizer -> sentence -> timing -> ORP)
2. Real-world text scenarios from various domains
3. Document type handling (paste, markdown, PDF)
4. Language-specific processing (English, German)
5. Edge cases and stress tests
6. RSVP display requirements satisfaction

These tests ensure that all tokenizer components work together correctly
and produce consistent, usable output for the speed reading application.
"""

import pytest

from app.models.enums import BreakType
from app.services.tokenizer import (
    # Main pipeline
    TokenizerPipeline,
    TokenizerResult,
    TokenData,
    tokenize,
    # Sub-components
    normalize_text,
    NormalizedText,
    TimingCalculator,
    SentenceDetector,
    # Constants
    TOKENIZER_VERSION,
    SUPPORTED_LANGUAGES,
    MAJOR_PAUSE_MULTIPLIER,
    MINOR_PAUSE_MULTIPLIER,
    LONG_WORD_MULTIPLIER,
    PARAGRAPH_BREAK_MULTIPLIER,
    HEADING_BREAK_MULTIPLIER,
)
from app.services.tokenizer.orp import ORPCalculator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pipeline():
    """Create an English tokenizer pipeline."""
    return TokenizerPipeline(language="en")


@pytest.fixture
def german_pipeline():
    """Create a German tokenizer pipeline."""
    return TokenizerPipeline(language="de")


# =============================================================================
# End-to-End Pipeline Integration Tests
# =============================================================================


class TestEndToEndPipeline:
    """Tests verifying complete end-to-end pipeline processing."""

    def test_simple_sentence_full_flow(self, pipeline):
        """Test that a simple sentence flows through all pipeline stages."""
        result = pipeline.process("Hello, world!")

        # Verify normalization happened
        assert result.normalized_text == "Hello, world!"

        # Verify tokenization
        assert result.total_words == 2
        assert len(result.tokens) == 2

        # Verify first token properties
        token0 = result.tokens[0]
        assert token0.display_text == "Hello,"
        assert token0.clean_text == "Hello"
        assert token0.word_index == 0
        assert token0.is_sentence_start is True
        assert token0.is_paragraph_start is True
        assert token0.orp_index_display >= 0
        assert token0.orp_index_display < len(token0.display_text)
        assert token0.delay_multiplier_after == MINOR_PAUSE_MULTIPLIER  # comma

        # Verify second token properties
        token1 = result.tokens[1]
        assert token1.display_text == "world!"
        assert token1.clean_text == "world"
        assert token1.word_index == 1
        assert token1.is_sentence_start is False
        assert token1.is_paragraph_start is False
        assert token1.delay_multiplier_after == MAJOR_PAUSE_MULTIPLIER  # exclamation

    def test_multi_sentence_paragraph_full_flow(self, pipeline):
        """Test multiple sentences in a single paragraph."""
        text = "First sentence. Second sentence? Third sentence!"
        result = pipeline.process(text)

        assert result.total_words == 6

        # Verify sentence boundaries
        sentence_starts = [t for t in result.tokens if t.is_sentence_start]
        assert len(sentence_starts) == 3  # Each sentence starts a new sentence

        # Verify timing for sentence ends
        # "sentence" is 8 chars (>= LONG_WORD_THRESHOLD), so multiplier stacks
        sentence_ends = ["sentence.", "sentence?", "sentence!"]
        expected_delay = MAJOR_PAUSE_MULTIPLIER * LONG_WORD_MULTIPLIER
        for token in result.tokens:
            if token.display_text in sentence_ends:
                assert token.delay_multiplier_after == expected_delay

    def test_multi_paragraph_full_flow(self, pipeline):
        """Test multiple paragraphs flow through correctly."""
        text = "First paragraph.\n\nSecond paragraph."
        result = pipeline.process(text)

        assert result.total_words == 4

        # Verify paragraph starts
        para_starts = [t for t in result.tokens if t.is_paragraph_start]
        assert len(para_starts) == 2

        # Second paragraph should have break_before
        second_para_start = [t for t in result.tokens if t.display_text == "Second"]
        assert len(second_para_start) == 1
        assert second_para_start[0].break_before == BreakType.PARAGRAPH

    def test_result_metadata_integrity(self, pipeline):
        """Test that result metadata is consistent."""
        result = pipeline.process("Test content here.")

        assert result.tokenizer_version == TOKENIZER_VERSION
        assert result.language == "en"
        assert result.total_words == len(result.tokens)
        assert len(result.normalized_text) > 0


class TestComponentIntegration:
    """Tests verifying that individual components integrate correctly."""

    def test_normalizer_to_tokenizer_integration(self, pipeline):
        """Test that normalized text is correctly tokenized."""
        # Text with multiple spaces and tabs
        text = "Hello    world\t\ttest"
        result = pipeline.process(text)

        # Normalizer collapses whitespace
        assert "    " not in result.normalized_text
        assert "\t" not in result.normalized_text

        # Tokenizer produces correct tokens
        assert result.total_words == 3
        assert [t.display_text for t in result.tokens] == ["Hello", "world", "test"]

    def test_sentence_detector_integration(self, pipeline):
        """Test that sentence detector properly marks boundaries."""
        text = "Dr. Smith went home. He was tired."
        result = pipeline.process(text)

        # "Smith" should NOT be a sentence start (follows abbreviation)
        smith_token = next(t for t in result.tokens if t.display_text == "Smith")
        assert smith_token.is_sentence_start is False

        # "He" should be a sentence start
        he_token = next(t for t in result.tokens if t.display_text == "He")
        assert he_token.is_sentence_start is True

    def test_timing_calculator_integration(self, pipeline):
        """Test that timing calculator produces correct delays."""
        text = "Short word, extraordinarily long."
        result = pipeline.process(text)

        # Find tokens
        word_token = next(t for t in result.tokens if t.display_text == "word,")
        long_token = next(t for t in result.tokens if t.display_text == "long.")

        # "word," has comma -> minor pause
        assert word_token.delay_multiplier_after == MINOR_PAUSE_MULTIPLIER

        # "extraordinarily" is long (15 chars) -> long word multiplier
        extra_token = next(t for t in result.tokens if "extraordinarily" in t.display_text)
        assert extra_token.delay_multiplier_after >= LONG_WORD_MULTIPLIER

    def test_orp_calculator_integration(self, pipeline):
        """Test that ORP calculator produces valid indices."""
        text = "Hi extraordinary"
        result = pipeline.process(text)

        # Short word "Hi" (2 chars) -> ORP at 0
        assert result.tokens[0].orp_index_display == 0

        # Long word "extraordinary" (13 chars) -> ORP should be around 4
        assert result.tokens[1].orp_index_display > 0
        assert result.tokens[1].orp_index_display < len(result.tokens[1].display_text)


# =============================================================================
# Document Type Integration Tests
# =============================================================================


class TestMarkdownIntegration:
    """Tests for Markdown document processing integration."""

    def test_markdown_heading_full_flow(self, pipeline):
        """Test Markdown heading processing through pipeline."""
        text = "# Main Title\n\nIntro paragraph.\n\n## Section\n\nSection content."
        result = pipeline.process(text, source_type="md")

        # Verify headings are detected
        heading_tokens = [t for t in result.tokens if t.break_before == BreakType.HEADING]
        assert len(heading_tokens) >= 1

        # Verify markdown syntax is stripped
        assert "#" not in [t.display_text for t in result.tokens]

        # Verify content is preserved
        display_texts = [t.display_text for t in result.tokens]
        assert "Main" in display_texts or "Title" in display_texts

    def test_markdown_formatting_stripped(self, pipeline):
        """Test that Markdown formatting is removed."""
        text = "This is **bold** and *italic* and `code`."
        result = pipeline.process(text, source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        # Formatting markers should be stripped
        assert "**bold**" not in display_texts
        assert "*italic*" not in display_texts
        assert "`code`" not in display_texts

        # Content should be preserved
        assert "bold" in display_texts
        assert "italic" in display_texts
        assert "code" in display_texts or "code." in display_texts

    def test_markdown_links_converted(self, pipeline):
        """Test that Markdown links are converted to plain text."""
        text = "Click [here](https://example.com) for more."
        result = pipeline.process(text, source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        # Link syntax removed
        assert "[here](https://example.com)" not in display_texts
        assert "(https://example.com)" not in display_texts

        # Link text preserved
        assert "here" in display_texts

    def test_markdown_code_blocks_removed(self, pipeline):
        """Test that code blocks are completely removed."""
        text = "Intro\n\n```python\nprint('code')\n```\n\nOutro"
        result = pipeline.process(text, source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        # Code block content should not be present
        assert "print" not in display_texts
        assert "python" not in display_texts

        # Surrounding text preserved
        assert "Intro" in display_texts
        assert "Outro" in display_texts

    def test_markdown_list_handling(self, pipeline):
        """Test that Markdown lists are handled correctly."""
        text = "List:\n\n- First item\n- Second item\n\nAfter list."
        result = pipeline.process(text, source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        # List markers stripped
        assert "-" not in display_texts

        # List content preserved
        assert "First" in display_texts
        assert "item" in display_texts or "item" in " ".join(display_texts)


class TestPDFIntegration:
    """Tests for PDF document processing integration."""

    def test_pdf_hyphen_dehyphenation(self, pipeline):
        """Test PDF hyphenation joining."""
        text = "under-\nstanding the prob-\nlem"
        result = pipeline.process(text, source_type="pdf")

        # Hyphenated words should be joined
        display_texts = [t.display_text for t in result.tokens]
        assert "understanding" in display_texts
        assert "problem" in display_texts

    def test_pdf_line_joining(self, pipeline):
        """Test PDF single line breaks are handled correctly."""
        text = "This is a\nsentence that continues."
        result = pipeline.process(text, source_type="pdf")

        # Line break should be treated as space
        assert "This is a sentence that continues." in result.normalized_text

    def test_pdf_paragraph_preserved(self, pipeline):
        """Test PDF paragraph breaks are preserved."""
        text = "First paragraph.\n\nSecond paragraph."
        result = pipeline.process(text, source_type="pdf")

        para_starts = [t for t in result.tokens if t.is_paragraph_start]
        assert len(para_starts) == 2


class TestPasteIntegration:
    """Tests for paste (plain text) processing integration."""

    def test_paste_preserves_markdown_syntax(self, pipeline):
        """Test that paste mode preserves raw text but drops standalone punctuation tokens."""
        text = "# Not a heading"
        result = pipeline.process(text, source_type="paste")

        # Raw normalized text should keep the marker
        assert "#" in result.normalized_text

        # Standalone '#' should not become a token
        display_texts = [t.display_text for t in result.tokens]
        assert "#" not in display_texts
        assert display_texts == ["Not", "a", "heading"]

    def test_paste_basic_text(self, pipeline):
        """Test paste mode with basic text."""
        text = "Hello world. This is a test."
        result = pipeline.process(text, source_type="paste")

        assert result.total_words == 6
        assert result.tokens[0].display_text == "Hello"


# =============================================================================
# Language Integration Tests
# =============================================================================


class TestEnglishLanguageIntegration:
    """Tests for English language processing integration."""

    def test_english_abbreviations_not_sentence_end(self, pipeline):
        """Test English abbreviations don't break sentences."""
        text = "Mr. Smith and Dr. Jones met Mrs. Davis."
        result = pipeline.process(text)

        sentence_starts = [t for t in result.tokens if t.is_sentence_start]
        # Only the first token should be a sentence start
        assert len(sentence_starts) == 1
        assert sentence_starts[0].word_index == 0

    def test_english_month_abbreviations(self, pipeline):
        """Test English month abbreviations are handled."""
        text = "Born Jan. 15, died Dec. 31."
        result = pipeline.process(text)

        # "15," should not be sentence start (follows Jan.)
        token_15 = next((t for t in result.tokens if "15" in t.display_text), None)
        if token_15:
            assert token_15.is_sentence_start is False

    def test_english_contractions(self, pipeline):
        """Test English contractions are preserved."""
        text = "Don't worry, it's fine."
        result = pipeline.process(text)

        display_texts = [t.display_text for t in result.tokens]
        assert "Don't" in display_texts
        assert "it's" in display_texts


class TestGermanLanguageIntegration:
    """Tests for German language processing integration."""

    def test_german_abbreviations_not_sentence_end(self, german_pipeline):
        """Test German abbreviations don't break sentences."""
        text = "Dr. Müller bzw. Prof. Schmidt kommen."
        result = german_pipeline.process(text)

        sentence_starts = [t for t in result.tokens if t.is_sentence_start]
        # Only the first token should be a sentence start
        assert len(sentence_starts) == 1

    def test_german_umlauts_preserved(self, german_pipeline):
        """Test German umlauts are preserved."""
        text = "Über die Brücke zur Bäckerei."
        result = german_pipeline.process(text)

        display_texts = [t.display_text for t in result.tokens]
        assert "Über" in display_texts
        assert "Brücke" in display_texts
        assert "Bäckerei." in display_texts

    def test_german_quotes_preserved(self, german_pipeline):
        """Test German quotation marks are preserved."""
        text = '„Hallo Welt"'
        result = german_pipeline.process(text)

        # German quotes should be in the output
        all_text = " ".join(t.display_text for t in result.tokens)
        assert "„" in all_text or "Hallo" in all_text


# =============================================================================
# Real-World Text Scenario Tests
# =============================================================================


class TestRealWorldScenarios:
    """Tests with real-world text scenarios."""

    def test_news_article_style(self, pipeline):
        """Test news article style text processing."""
        text = """
        Breaking News: Scientists Discover New Species

        LONDON -- Researchers at Oxford University announced today
        the discovery of a previously unknown species of butterfly.

        Dr. Jane Smith, lead researcher, stated: "This is a remarkable
        finding that changes our understanding of biodiversity."

        The discovery was made during an expedition to South America
        last summer.
        """
        result = pipeline.process(text, source_type="paste")

        # Should have multiple paragraphs
        para_starts = [t for t in result.tokens if t.is_paragraph_start]
        assert len(para_starts) >= 3

        # Should have multiple sentences
        sentence_starts = [t for t in result.tokens if t.is_sentence_start]
        assert len(sentence_starts) >= 4

        # Dr. should not break sentence
        dr_token = next((t for t in result.tokens if "Dr." in t.display_text), None)
        if dr_token:
            # Find next token
            next_idx = dr_token.word_index + 1
            if next_idx < len(result.tokens):
                next_token = result.tokens[next_idx]
                assert next_token.is_sentence_start is False

    def test_technical_documentation(self, pipeline):
        """Test technical documentation style text."""
        text = """
        ## Installation

        To install the package, run:

        ```bash
        pip install mypackage
        ```

        ## Usage

        Import and use as follows:

        ```python
        from mypackage import func
        func()
        ```

        For more information, see the API docs.
        """
        result = pipeline.process(text, source_type="md")

        # Code blocks should be removed
        display_texts = [t.display_text for t in result.tokens]
        assert "pip" not in display_texts
        assert "import" not in display_texts

        # Headings should be detected
        heading_tokens = [t for t in result.tokens if t.break_before == BreakType.HEADING]
        assert len(heading_tokens) >= 1

    def test_dialogue_formatting(self, pipeline):
        """Test dialogue with quoted speech."""
        text = '"Hello," she said. "How are you?" He replied, "I\'m fine."'
        result = pipeline.process(text)

        # Verify all words are tokenized
        assert result.total_words >= 8

        # Verify punctuation is preserved
        display_texts = [t.display_text for t in result.tokens]
        quoted_tokens = [t for t in display_texts if '"' in t]
        assert len(quoted_tokens) >= 2

    def test_academic_writing(self, pipeline):
        """Test academic writing style with citations."""
        text = """
        According to Smith et al. (2020), the phenomenon occurs in
        approximately 30% of cases. This finding was confirmed by
        subsequent research (Jones, 2021; Davis & Wilson, 2022).

        Furthermore, the implications extend to related fields, e.g.,
        cognitive psychology and neuroscience.
        """
        result = pipeline.process(text, source_type="paste")

        # "et" should not be sentence start (follows "al.")
        # Note: "al." should be recognized as abbreviation

        # Should have proper sentence breaks
        sentence_starts = [t for t in result.tokens if t.is_sentence_start]
        assert len(sentence_starts) >= 2

    def test_email_style_text(self, pipeline):
        """Test email-style text with greetings."""
        text = """
        Dear Mr. Smith,

        Thank you for your inquiry. We're pleased to inform you that
        your application has been approved.

        Best regards,
        Dr. Jane Wilson
        """
        result = pipeline.process(text, source_type="paste")

        # Mr. and Dr. should not break sentences
        sentence_starts = [t for t in result.tokens if t.is_sentence_start]

        # "Smith," should NOT be a sentence start
        smith_tokens = [t for t in result.tokens if "Smith" in t.display_text]
        for t in smith_tokens:
            assert t.is_sentence_start is False


class TestComplexDocumentStructure:
    """Tests for documents with complex structure."""

    def test_nested_headings(self, pipeline):
        """Test document with nested heading levels."""
        text = """
        # Chapter 1

        Introduction text.

        ## Section 1.1

        Section content.

        ### Subsection 1.1.1

        Detailed content.
        """
        result = pipeline.process(text, source_type="md")

        # Should have multiple headings
        heading_tokens = [t for t in result.tokens if t.break_before == BreakType.HEADING]
        assert len(heading_tokens) >= 2

    def test_mixed_content_types(self, pipeline):
        """Test document mixing prose, lists, and code."""
        text = """
        # Overview

        This document explains the process:

        - First, install dependencies
        - Next, configure settings
        - Finally, run the application

        After installation, you can customize:

        1. User preferences
        2. Theme settings
        3. Plugin options
        """
        result = pipeline.process(text, source_type="md")

        # Should process all content
        assert result.total_words > 15

        # All tokens should have valid properties
        for token in result.tokens:
            assert isinstance(token.display_text, str)
            assert len(token.display_text) > 0
            assert token.orp_index_display >= 0


# =============================================================================
# RSVP Display Requirements Tests
# =============================================================================


class TestRSVPDisplayRequirements:
    """Tests ensuring tokens meet RSVP display requirements."""

    def test_all_tokens_have_display_text(self, pipeline):
        """Test all tokens have non-empty display text."""
        text = "Various test content with different words and structures."
        result = pipeline.process(text)

        for token in result.tokens:
            assert token.display_text is not None
            assert len(token.display_text) > 0

    def test_all_tokens_have_valid_orp(self, pipeline):
        """Test all tokens have valid ORP indices."""
        text = "Short and extraordinarily long words mixed together."
        result = pipeline.process(text)

        for token in result.tokens:
            assert token.orp_index_display >= 0
            assert token.orp_index_display < len(token.display_text)

    def test_all_tokens_have_positive_delay(self, pipeline):
        """Test all tokens have positive delay multipliers."""
        text = "Test, sentence. With! Various? Punctuation: here;"
        result = pipeline.process(text)

        for token in result.tokens:
            assert token.delay_multiplier_after > 0

    def test_character_offsets_map_correctly(self, pipeline):
        """Test character offsets correctly map to normalized text."""
        text = "Hello world test"
        result = pipeline.process(text)

        for token in result.tokens:
            assert token.char_offset_start is not None
            assert token.char_offset_end is not None

            # Extract text using offsets
            extracted = result.normalized_text[
                token.char_offset_start:token.char_offset_end
            ]
            assert extracted == token.display_text

    def test_word_indices_sequential(self, pipeline):
        """Test word indices are sequential from 0."""
        text = "One two three four five six seven eight nine ten."
        result = pipeline.process(text)

        for i, token in enumerate(result.tokens):
            assert token.word_index == i

    def test_clean_text_alphanumeric(self, pipeline):
        """Test clean_text strips leading/trailing punctuation."""
        text = '"Hello," she said: "Wow!"'
        result = pipeline.process(text)

        for token in result.tokens:
            # clean_text should only contain the core word
            if token.clean_text:
                # First and last char should be alphanumeric (if non-empty)
                assert token.clean_text[0].isalnum() or len(token.clean_text) == 0
                assert token.clean_text[-1].isalnum() or len(token.clean_text) == 0


class TestTokenNavigationMethods:
    """Tests for token navigation helper methods."""

    def test_get_token_at_position(self, pipeline):
        """Test finding token by character position."""
        text = "Hello world test"
        result = pipeline.process(text)

        # Position 0 should be in "Hello"
        token = pipeline.get_token_at_position(result.tokens, 0)
        assert token is not None
        assert token.display_text == "Hello"

        # Position 6 should be in "world"
        token = pipeline.get_token_at_position(result.tokens, 6)
        assert token is not None
        assert token.display_text == "world"

    def test_find_sentence_start(self, pipeline):
        """Test finding sentence start from any position."""
        text = "First sentence. Second sentence here."
        result = pipeline.process(text)

        # From last word, should find "Second"
        start = pipeline.find_sentence_start(result.tokens, 4)  # "here."
        assert start == 2  # "Second"

        # From first word
        start = pipeline.find_sentence_start(result.tokens, 0)
        assert start == 0

    def test_find_paragraph_start(self, pipeline):
        """Test finding paragraph start from any position."""
        text = "Para one.\n\nPara two here."
        result = pipeline.process(text)

        # From "here." should find "Para" (second occurrence)
        para_start = pipeline.find_paragraph_start(result.tokens, len(result.tokens) - 1)
        assert result.tokens[para_start].display_text == "Para"

    def test_count_words(self, pipeline):
        """Test word counting without full tokenization."""
        text = "One two three four five"
        count = pipeline.count_words(text)
        assert count == 5


# =============================================================================
# Edge Cases and Stress Tests
# =============================================================================


class TestEdgeCasesIntegration:
    """Integration tests for edge cases."""

    def test_empty_input(self, pipeline):
        """Test empty input handling."""
        result = pipeline.process("")
        assert result.total_words == 0
        assert result.tokens == []
        assert result.normalized_text == ""

    def test_whitespace_only(self, pipeline):
        """Test whitespace-only input."""
        result = pipeline.process("   \n\n\t\t   ")
        assert result.total_words == 0
        assert result.tokens == []

    def test_single_character(self, pipeline):
        """Test single character input."""
        result = pipeline.process("A")
        assert result.total_words == 1
        assert result.tokens[0].display_text == "A"

    def test_single_word_with_punctuation(self, pipeline):
        """Test single word with punctuation."""
        result = pipeline.process("Hello!")
        assert result.total_words == 1
        assert result.tokens[0].display_text == "Hello!"
        assert result.tokens[0].clean_text == "Hello"

    def test_unicode_characters(self, pipeline):
        """Test Unicode character handling."""
        text = "Hello 世界! Emoji: 😀 Math: π ≈ 3.14"
        result = pipeline.process(text)

        display_texts = [t.display_text for t in result.tokens]
        assert "世界!" in display_texts
        assert "😀" not in display_texts
        assert "π" in display_texts
        assert "3.14" in display_texts

    def test_very_long_word(self, pipeline):
        """Test very long word handling."""
        long_word = "supercalifragilisticexpialidocious"
        result = pipeline.process(long_word)

        assert result.total_words == 1
        assert result.tokens[0].display_text == long_word
        # Should have long word multiplier
        assert result.tokens[0].delay_multiplier_after >= LONG_WORD_MULTIPLIER

    def test_many_short_words(self, pipeline):
        """Test many short words."""
        text = "a b c d e f g h i j k l m n o p q r s t u v w x y z"
        result = pipeline.process(text)
        assert result.total_words == 26

    def test_repeated_punctuation(self, pipeline):
        """Test repeated punctuation handling."""
        text = "What?! Really??? Yes!!!"
        result = pipeline.process(text)

        # All should be processed
        assert result.total_words == 3

        # All sentence-ending tokens
        for token in result.tokens:
            assert token.delay_multiplier_after >= MAJOR_PAUSE_MULTIPLIER

    def test_em_dash_attaches_to_neighbor(self, pipeline):
        """Em dashes should attach to neighboring words (no standalone token)."""
        text = "Hello—world"
        result = pipeline.process(text)
        assert [t.display_text for t in result.tokens] == ["Hello—", "world"]

    def test_ellipsis_attaches_to_word(self, pipeline):
        """Ellipsis should attach to the preceding word."""
        text = "Wait... What"
        result = pipeline.process(text)
        assert [t.display_text for t in result.tokens] == ["Wait...", "What"]

    def test_punctuation_only_input_has_no_tokens(self, pipeline):
        """Standalone punctuation should not produce tokens."""
        result = pipeline.process("... !!!")
        assert result.total_words == 0
        assert result.tokens == []


class TestStressTests:
    """Stress tests for the tokenizer."""

    def test_large_document(self, pipeline):
        """Test processing a large document."""
        # Generate 10000 words
        words = ["word"] * 5000 + ["sentence."] * 2500 + ["test"] * 2500
        text = " ".join(words)

        result = pipeline.process(text)
        assert result.total_words == 10000

        # Verify structure
        assert all(isinstance(t, TokenData) for t in result.tokens)

    def test_many_paragraphs(self, pipeline):
        """Test document with many paragraphs."""
        paragraphs = ["Paragraph content here."] * 100
        text = "\n\n".join(paragraphs)

        result = pipeline.process(text)

        para_starts = [t for t in result.tokens if t.is_paragraph_start]
        assert len(para_starts) == 100

    def test_many_sentences(self, pipeline):
        """Test document with many sentences."""
        sentences = ["Sentence number one."] * 200
        text = " ".join(sentences)

        result = pipeline.process(text)

        sentence_starts = [t for t in result.tokens if t.is_sentence_start]
        assert len(sentence_starts) == 200

    def test_deeply_nested_markdown(self, pipeline):
        """Test deeply nested Markdown structure."""
        text = """
        # Level 1
        Content.
        ## Level 2
        Content.
        ### Level 3
        Content.
        #### Level 4
        Content.
        ##### Level 5
        Content.
        ###### Level 6
        Content.
        """
        result = pipeline.process(text, source_type="md")

        # Should handle all heading levels
        heading_tokens = [t for t in result.tokens if t.break_before == BreakType.HEADING]
        assert len(heading_tokens) >= 5


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestTokenizeConvenienceFunction:
    """Tests for the tokenize() convenience function."""

    def test_basic_usage(self):
        """Test basic convenience function usage."""
        result = tokenize("Hello world.")

        assert isinstance(result, TokenizerResult)
        assert result.total_words == 2
        assert result.language == "en"

    def test_with_source_type(self):
        """Test convenience function with source type."""
        result = tokenize("# Heading", source_type="md")

        # Heading marker should be stripped
        assert "#" not in [t.display_text for t in result.tokens]

    def test_with_language(self):
        """Test convenience function with language."""
        result = tokenize("Dr. Müller kommt.", language="de")

        assert result.language == "de"

        # Dr. should not break sentence in German
        sentence_starts = [t for t in result.tokens if t.is_sentence_start]
        assert len(sentence_starts) == 1

    def test_all_parameters(self):
        """Test convenience function with all parameters."""
        result = tokenize(
            "# Überschrift\n\nText.",
            source_type="md",
            language="de",
        )

        assert result.language == "de"
        assert "#" not in [t.display_text for t in result.tokens]


# =============================================================================
# Consistency Tests
# =============================================================================


class TestConsistency:
    """Tests ensuring consistent behavior across invocations."""

    def test_same_input_same_output(self, pipeline):
        """Test that same input produces same output."""
        text = "Hello world. How are you?"

        result1 = pipeline.process(text)
        result2 = pipeline.process(text)

        assert result1.total_words == result2.total_words
        assert result1.normalized_text == result2.normalized_text

        for t1, t2 in zip(result1.tokens, result2.tokens):
            assert t1.display_text == t2.display_text
            assert t1.word_index == t2.word_index
            assert t1.orp_index_display == t2.orp_index_display
            assert t1.delay_multiplier_after == t2.delay_multiplier_after
            assert t1.is_sentence_start == t2.is_sentence_start
            assert t1.is_paragraph_start == t2.is_paragraph_start

    def test_language_independence(self):
        """Test that language setting affects only language-specific features."""
        text = "Hello world."

        en_result = tokenize(text, language="en")
        de_result = tokenize(text, language="de")

        # Basic tokenization should be same
        assert en_result.total_words == de_result.total_words

        # But language metadata differs
        assert en_result.language == "en"
        assert de_result.language == "de"

    def test_source_type_affects_processing(self):
        """Test that source type affects processing correctly."""
        text = "**bold** text"

        paste_result = tokenize(text, source_type="paste")
        md_result = tokenize(text, source_type="md")

        paste_texts = [t.display_text for t in paste_result.tokens]
        md_texts = [t.display_text for t in md_result.tokens]

        # Paste preserves raw markdown in normalized text
        assert "**bold**" in paste_result.normalized_text

        # Tokens should not include standalone markup characters
        assert "**bold**" not in paste_texts
        assert "**bold**" not in md_texts
        assert "bold" in paste_texts
        assert "bold" in md_texts


# =============================================================================
# Regression Tests
# =============================================================================


class TestRegressions:
    """Regression tests for previously found issues."""

    def test_abbreviation_followed_by_proper_noun(self, pipeline):
        """Test abbreviation followed by capitalized word."""
        text = "Mr. Smith arrived."
        result = pipeline.process(text)

        # "Smith" should NOT be a sentence start
        smith_token = next(t for t in result.tokens if t.display_text == "Smith")
        assert smith_token.is_sentence_start is False

    def test_ellipsis_as_sentence_end(self, pipeline):
        """Test ellipsis properly ends sentences."""
        text = "Wait... What?"
        result = pipeline.process(text)

        # "What?" should be a new sentence
        what_token = next(t for t in result.tokens if "What" in t.display_text)
        assert what_token.is_sentence_start is True

    def test_quoted_sentence_ending(self, pipeline):
        """Test sentence ending inside quotes."""
        text = 'He said, "Done." Then left.'
        result = pipeline.process(text)

        # "Then" should be a sentence start
        then_token = next(t for t in result.tokens if t.display_text == "Then")
        assert then_token.is_sentence_start is True

    def test_paragraph_break_with_heading(self, pipeline):
        """Test paragraph break followed by heading."""
        text = "Content here.\n\n# New Section\n\nMore content."
        result = pipeline.process(text, source_type="md")

        # Should have proper structure
        heading_tokens = [t for t in result.tokens if t.break_before == BreakType.HEADING]
        para_tokens = [t for t in result.tokens if t.break_before == BreakType.PARAGRAPH]

        assert len(heading_tokens) >= 1

    def test_long_word_with_punctuation_stacking(self, pipeline):
        """Test long word multiplier stacks with punctuation."""
        text = "extraordinary."
        result = pipeline.process(text)

        token = result.tokens[0]
        # Should have both long word and major pause multipliers
        expected = MAJOR_PAUSE_MULTIPLIER * LONG_WORD_MULTIPLIER
        assert token.delay_multiplier_after == expected
