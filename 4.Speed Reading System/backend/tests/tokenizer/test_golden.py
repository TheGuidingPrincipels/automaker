"""Golden tests for the tokenizer pipeline with fixed expected outputs.

These tests verify that the tokenizer produces EXACT expected outputs for
known inputs. They serve as regression tests to ensure that any changes
to the tokenizer don't unintentionally alter its behavior.

Golden tests are different from unit tests in that they:
1. Test the complete output structure, not just specific attributes
2. Use fixed, hardcoded expected values
3. Catch any drift in tokenizer behavior
4. Serve as living documentation of expected behavior

If a golden test fails after intentional changes, the expected values
should be updated after careful review.
"""

import pytest

from app.models.enums import BreakType
from app.services.tokenizer import (
    TokenizerPipeline,
    TokenizerResult,
    TokenData,
    tokenize,
    TOKENIZER_VERSION,
    MAJOR_PAUSE_MULTIPLIER,
    MINOR_PAUSE_MULTIPLIER,
    LONG_WORD_MULTIPLIER,
)


# =============================================================================
# Helper Functions for Golden Test Assertions
# =============================================================================


def assert_token_matches(
    token: TokenData,
    expected: dict,
    msg_prefix: str = "",
) -> None:
    """Assert that a token matches all expected values.

    Args:
        token: The actual TokenData object.
        expected: Dict of expected attribute values.
        msg_prefix: Optional prefix for error messages.
    """
    for key, expected_value in expected.items():
        actual_value = getattr(token, key)
        assert actual_value == expected_value, (
            f"{msg_prefix}Token attribute '{key}' mismatch: "
            f"expected {expected_value!r}, got {actual_value!r}"
        )


def assert_tokens_match(
    tokens: list[TokenData],
    expected_list: list[dict],
    check_all_fields: bool = False,
) -> None:
    """Assert that a list of tokens matches expected values.

    Args:
        tokens: The actual list of TokenData objects.
        expected_list: List of dicts with expected values.
        check_all_fields: If True, verify ALL fields match, not just those specified.
    """
    assert len(tokens) == len(expected_list), (
        f"Token count mismatch: expected {len(expected_list)}, got {len(tokens)}"
    )

    for i, (token, expected) in enumerate(zip(tokens, expected_list)):
        assert_token_matches(token, expected, f"Token {i}: ")


# =============================================================================
# Basic Tokenization Golden Tests
# =============================================================================


class TestBasicGoldenCases:
    """Golden tests for basic tokenization scenarios."""

    def test_golden_single_word(self):
        """Golden test: single word tokenization."""
        result = tokenize("Hello")

        assert result.total_words == 1
        assert result.normalized_text == "Hello"
        assert result.tokenizer_version == TOKENIZER_VERSION
        assert result.language == "en"

        expected_tokens = [
            {
                "word_index": 0,
                "display_text": "Hello",
                "clean_text": "Hello",
                "orp_index_display": 1,  # 5 chars -> ORP at index 1
                "delay_multiplier_after": 1.0,
                "break_before": None,
                "is_sentence_start": True,
                "is_paragraph_start": True,
                "char_offset_start": 0,
                "char_offset_end": 5,
            }
        ]

        assert_tokens_match(result.tokens, expected_tokens)

    def test_golden_two_words(self):
        """Golden test: two word tokenization."""
        result = tokenize("Hello world")

        assert result.total_words == 2
        assert result.normalized_text == "Hello world"

        expected_tokens = [
            {
                "word_index": 0,
                "display_text": "Hello",
                "clean_text": "Hello",
                "orp_index_display": 1,
                "delay_multiplier_after": 1.0,
                "is_sentence_start": True,
                "is_paragraph_start": True,
                "char_offset_start": 0,
                "char_offset_end": 5,
            },
            {
                "word_index": 1,
                "display_text": "world",
                "clean_text": "world",
                "orp_index_display": 1,
                "delay_multiplier_after": 1.0,
                "is_sentence_start": False,
                "is_paragraph_start": False,
                "char_offset_start": 6,
                "char_offset_end": 11,
            },
        ]

        assert_tokens_match(result.tokens, expected_tokens)

    def test_golden_simple_sentence(self):
        """Golden test: simple sentence with period."""
        result = tokenize("Hello world.")

        assert result.total_words == 2
        assert result.normalized_text == "Hello world."

        expected_tokens = [
            {
                "word_index": 0,
                "display_text": "Hello",
                "clean_text": "Hello",
                "orp_index_display": 1,
                "delay_multiplier_after": 1.0,
                "is_sentence_start": True,
                "is_paragraph_start": True,
            },
            {
                "word_index": 1,
                "display_text": "world.",
                "clean_text": "world",
                "orp_index_display": 1,
                "delay_multiplier_after": MAJOR_PAUSE_MULTIPLIER,  # 2.5
                "is_sentence_start": False,
                "is_paragraph_start": False,
            },
        ]

        assert_tokens_match(result.tokens, expected_tokens)

    def test_golden_sentence_with_comma(self):
        """Golden test: sentence with comma."""
        result = tokenize("Hello, world!")

        assert result.total_words == 2

        expected_tokens = [
            {
                "word_index": 0,
                "display_text": "Hello,",
                "clean_text": "Hello",
                "orp_index_display": 1,
                "delay_multiplier_after": MINOR_PAUSE_MULTIPLIER,  # 1.5
                "is_sentence_start": True,
            },
            {
                "word_index": 1,
                "display_text": "world!",
                "clean_text": "world",
                "orp_index_display": 1,
                "delay_multiplier_after": MAJOR_PAUSE_MULTIPLIER,  # 2.5
                "is_sentence_start": False,
            },
        ]

        assert_tokens_match(result.tokens, expected_tokens)


# =============================================================================
# ORP Calculation Golden Tests
# =============================================================================


class TestORPGoldenCases:
    """Golden tests for ORP (Optimal Recognition Point) calculations."""

    def test_golden_orp_by_word_length(self):
        """Golden test: ORP positions for various word lengths."""
        # Test words of different lengths with their expected ORP indices
        test_cases = [
            ("a", 0),           # 1 char -> 0
            ("Hi", 0),          # 2 chars -> 0
            ("The", 1),         # 3 chars -> 1
            ("word", 1),        # 4 chars -> 1
            ("Hello", 1),       # 5 chars -> 1
            ("worlds", 2),      # 6 chars -> 2
            ("reading", 2),     # 7 chars -> 2
            ("sentence", 3),    # 8 chars -> 3
            ("important", 3),   # 9 chars -> 3
            ("everything", 4),  # 10 chars -> 4
            ("recognition", 4), # 11 chars -> 4
            ("particularly", 4),  # 12 chars -> 4
            ("extraordinary", 5), # 13 chars -> 5
            ("supercalifragilisticexpialidocious", 13),  # 34 chars -> 13
        ]

        for word, expected_orp in test_cases:
            result = tokenize(word)
            actual_orp = result.tokens[0].orp_index_display
            assert actual_orp == expected_orp, (
                f"ORP mismatch for '{word}' (len={len(word)}): "
                f"expected {expected_orp}, got {actual_orp}"
            )

    def test_golden_orp_with_leading_punctuation(self):
        """Golden test: ORP calculation skips leading punctuation."""
        result = tokenize('"Hello')

        # "Hello has 6 chars, but ORP should be based on "Hello" (5 chars)
        # ORP for 5 chars is 1, plus 1 for the leading quote = 2
        assert result.tokens[0].orp_index_display == 2

    def test_golden_orp_with_trailing_punctuation(self):
        """Golden test: ORP calculation ignores trailing punctuation."""
        result = tokenize("Hello!")

        # "Hello!" has 6 chars, but ORP based on "Hello" (5 chars) = 1
        assert result.tokens[0].orp_index_display == 1

    def test_golden_orp_quoted_word(self):
        """Golden test: ORP for fully quoted word."""
        result = tokenize('"world"')

        # "world" has 7 chars total, but core word is "world" (5 chars)
        # ORP for 5 chars is 1, plus 1 for leading quote = 2
        assert result.tokens[0].orp_index_display == 2


# =============================================================================
# Timing/Delay Multiplier Golden Tests
# =============================================================================


class TestTimingGoldenCases:
    """Golden tests for delay multiplier calculations."""

    def test_golden_timing_no_punctuation(self):
        """Golden test: word without punctuation has 1.0 delay."""
        result = tokenize("hello")
        assert result.tokens[0].delay_multiplier_after == 1.0

    def test_golden_timing_period(self):
        """Golden test: period gives major pause (2.5)."""
        result = tokenize("hello.")
        assert result.tokens[0].delay_multiplier_after == MAJOR_PAUSE_MULTIPLIER

    def test_golden_timing_exclamation(self):
        """Golden test: exclamation gives major pause (2.5)."""
        result = tokenize("hello!")
        assert result.tokens[0].delay_multiplier_after == MAJOR_PAUSE_MULTIPLIER

    def test_golden_timing_question(self):
        """Golden test: question mark gives major pause (2.5)."""
        result = tokenize("hello?")
        assert result.tokens[0].delay_multiplier_after == MAJOR_PAUSE_MULTIPLIER

    def test_golden_timing_comma(self):
        """Golden test: comma gives minor pause (1.5)."""
        result = tokenize("hello,")
        assert result.tokens[0].delay_multiplier_after == MINOR_PAUSE_MULTIPLIER

    def test_golden_timing_semicolon(self):
        """Golden test: semicolon gives minor pause (1.5)."""
        result = tokenize("hello;")
        assert result.tokens[0].delay_multiplier_after == MINOR_PAUSE_MULTIPLIER

    def test_golden_timing_colon(self):
        """Golden test: colon gives major pause (2.5)."""
        result = tokenize("hello:")
        assert result.tokens[0].delay_multiplier_after == MAJOR_PAUSE_MULTIPLIER

    def test_golden_timing_long_word(self):
        """Golden test: long word (8+ chars) gets long word multiplier (1.2)."""
        result = tokenize("extraordinary")  # 13 chars
        assert result.tokens[0].delay_multiplier_after == LONG_WORD_MULTIPLIER

    def test_golden_timing_long_word_with_period(self):
        """Golden test: long word with period stacks multipliers."""
        result = tokenize("extraordinary.")  # 13 chars + period

        # 2.5 (major pause) * 1.2 (long word) = 3.0
        expected = MAJOR_PAUSE_MULTIPLIER * LONG_WORD_MULTIPLIER
        assert result.tokens[0].delay_multiplier_after == expected

    def test_golden_timing_short_word_boundary(self):
        """Golden test: 7-char word (below threshold) has no long word multiplier."""
        result = tokenize("reading")  # 7 chars, below 8-char threshold
        assert result.tokens[0].delay_multiplier_after == 1.0

    def test_golden_timing_exact_threshold(self):
        """Golden test: exactly 8-char word gets long word multiplier."""
        result = tokenize("sentence")  # exactly 8 chars
        assert result.tokens[0].delay_multiplier_after == LONG_WORD_MULTIPLIER


# =============================================================================
# Sentence Detection Golden Tests
# =============================================================================


class TestSentenceDetectionGolden:
    """Golden tests for sentence boundary detection."""

    def test_golden_two_sentences(self):
        """Golden test: two sentences separated by period."""
        result = tokenize("Hello world. How are you?")

        assert result.total_words == 5

        expected_sentence_starts = [True, False, True, False, False]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]

        assert actual_sentence_starts == expected_sentence_starts

    def test_golden_abbreviation_not_sentence_end(self):
        """Golden test: abbreviation (Dr.) doesn't end sentence."""
        result = tokenize("Dr. Smith is here.")

        assert result.total_words == 4

        # "Dr." -> "Smith" -> "is" -> "here."
        # Only first token should be sentence start
        expected_sentence_starts = [True, False, False, False]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]

        assert actual_sentence_starts == expected_sentence_starts

    def test_golden_multiple_abbreviations(self):
        """Golden test: multiple abbreviations in one sentence."""
        result = tokenize("Mr. and Mrs. Smith arrived.")

        # All abbreviations should not break the sentence
        expected_sentence_starts = [True, False, False, False, False]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]

        assert actual_sentence_starts == expected_sentence_starts

    def test_golden_ellipsis_ends_sentence(self):
        """Golden test: ellipsis ends a sentence."""
        result = tokenize("Wait... What?")

        assert result.total_words == 2

        # "Wait..." ends sentence, "What?" starts new one
        expected_sentence_starts = [True, True]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]

        assert actual_sentence_starts == expected_sentence_starts

    def test_golden_question_exclamation(self):
        """Golden test: question and exclamation marks end sentences."""
        result = tokenize("Really? Yes! No.")

        expected_sentence_starts = [True, True, True]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]

        assert actual_sentence_starts == expected_sentence_starts


# =============================================================================
# Paragraph Detection Golden Tests
# =============================================================================


class TestParagraphDetectionGolden:
    """Golden tests for paragraph boundary detection."""

    def test_golden_two_paragraphs(self):
        """Golden test: two paragraphs separated by blank line."""
        result = tokenize("First paragraph.\n\nSecond paragraph.")

        assert result.total_words == 4

        # "First" starts para 1, "Second" starts para 2
        expected_paragraph_starts = [True, False, True, False]
        actual_paragraph_starts = [t.is_paragraph_start for t in result.tokens]

        assert actual_paragraph_starts == expected_paragraph_starts

        # Second paragraph should have break_before = PARAGRAPH
        assert result.tokens[0].break_before is None
        assert result.tokens[2].break_before == BreakType.PARAGRAPH

    def test_golden_three_paragraphs(self):
        """Golden test: three paragraphs."""
        result = tokenize("One.\n\nTwo.\n\nThree.")

        expected_paragraph_starts = [True, True, True]
        actual_paragraph_starts = [t.is_paragraph_start for t in result.tokens]

        assert actual_paragraph_starts == expected_paragraph_starts

        # Check break_before values
        assert result.tokens[0].break_before is None
        assert result.tokens[1].break_before == BreakType.PARAGRAPH
        assert result.tokens[2].break_before == BreakType.PARAGRAPH

    def test_golden_paragraph_with_multiple_sentences(self):
        """Golden test: paragraph with multiple sentences maintains structure."""
        result = tokenize("First sentence. Second sentence.\n\nNew paragraph.")

        # "First sentence. Second sentence." = 4 words
        # "New paragraph." = 2 words
        # Total = 6 words
        assert result.total_words == 6

        # Paragraph starts: First (True), sentence. (F), Second (F), sentence. (F), New (True), paragraph. (F)
        expected_paragraph_starts = [True, False, False, False, True, False]
        actual_paragraph_starts = [t.is_paragraph_start for t in result.tokens]
        assert actual_paragraph_starts == expected_paragraph_starts

        # Sentence starts: First (T), sentence. (F), Second (T), sentence. (F), New (T), paragraph. (F)
        expected_sentence_starts = [True, False, True, False, True, False]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]
        assert actual_sentence_starts == expected_sentence_starts


# =============================================================================
# Markdown Processing Golden Tests
# =============================================================================


class TestMarkdownGolden:
    """Golden tests for Markdown document processing."""

    def test_golden_markdown_heading(self):
        """Golden test: Markdown heading detection and stripping."""
        result = tokenize("# Main Title\n\nContent here.", source_type="md")

        # Heading marker should be stripped
        display_texts = [t.display_text for t in result.tokens]
        assert "#" not in display_texts
        assert "Main" in display_texts
        assert "Title" in display_texts

        # First token should not have break_before even if it's a heading
        assert result.tokens[0].break_before is None

    def test_golden_markdown_bold_stripped(self):
        """Golden test: Markdown bold markers are stripped."""
        result = tokenize("This is **bold** text.", source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        assert "**bold**" not in display_texts
        assert "bold" in display_texts

    def test_golden_markdown_italic_stripped(self):
        """Golden test: Markdown italic markers are stripped."""
        result = tokenize("This is *italic* text.", source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        assert "*italic*" not in display_texts
        assert "italic" in display_texts

    def test_golden_markdown_link_text_preserved(self):
        """Golden test: Markdown link text is preserved, URL removed."""
        result = tokenize("Click [here](https://example.com) please.", source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        assert "here" in display_texts
        assert "(https://example.com)" not in " ".join(display_texts)
        assert "[here]" not in display_texts

    def test_golden_markdown_code_block_removed(self):
        """Golden test: Markdown code blocks are completely removed."""
        text = "Intro\n\n```python\nprint('hello')\n```\n\nOutro"
        result = tokenize(text, source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        assert "print" not in display_texts
        assert "hello" not in display_texts
        assert "python" not in display_texts
        assert "Intro" in display_texts
        assert "Outro" in display_texts

    def test_golden_markdown_inline_code(self):
        """Golden test: Markdown inline code backticks are removed."""
        result = tokenize("Run `command` now.", source_type="md")

        display_texts = [t.display_text for t in result.tokens]

        assert "`command`" not in display_texts
        assert "command" in display_texts


# =============================================================================
# PDF Processing Golden Tests
# =============================================================================


class TestPDFGolden:
    """Golden tests for PDF document processing."""

    def test_golden_pdf_hyphen_joining(self):
        """Golden test: PDF hyphenated words are joined."""
        result = tokenize("under-\nstanding", source_type="pdf")

        assert result.total_words == 1
        assert result.tokens[0].display_text == "understanding"

    def test_golden_pdf_line_joining(self):
        """Golden test: PDF single line breaks become spaces."""
        result = tokenize("This is a\nsentence.", source_type="pdf")

        assert "This is a sentence." in result.normalized_text

    def test_golden_pdf_paragraph_preserved(self):
        """Golden test: PDF double line breaks preserve paragraphs."""
        result = tokenize("Para one.\n\nPara two.", source_type="pdf")

        expected_paragraph_starts = [True, False, True, False]
        actual_paragraph_starts = [t.is_paragraph_start for t in result.tokens]

        assert actual_paragraph_starts == expected_paragraph_starts


# =============================================================================
# Paste (Plain Text) Processing Golden Tests
# =============================================================================


class TestPasteGolden:
    """Golden tests for paste (plain text) processing."""

    def test_golden_paste_preserves_markdown(self):
        """Golden test: paste mode preserves markdown-like characters."""
        result = tokenize("# Not a heading", source_type="paste")

        display_texts = [t.display_text for t in result.tokens]

        # Raw normalized text preserves the marker
        assert "#" in result.normalized_text

        # Standalone '#' should not be tokenized
        assert "#" not in display_texts

    def test_golden_paste_preserves_bold(self):
        """Golden test: paste mode preserves **bold** markers."""
        result = tokenize("This is **bold**", source_type="paste")

        display_texts = [t.display_text for t in result.tokens]

        assert "**bold**" in result.normalized_text
        assert "**bold**" not in display_texts
        assert "bold" in display_texts


# =============================================================================
# German Language Golden Tests
# =============================================================================


class TestGermanGolden:
    """Golden tests for German language processing."""

    def test_golden_german_abbreviation(self):
        """Golden test: German abbreviations don't end sentences."""
        result = tokenize("Dr. Müller ist hier.", language="de")

        # Only first token should be sentence start
        expected_sentence_starts = [True, False, False, False]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]

        assert actual_sentence_starts == expected_sentence_starts

    def test_golden_german_umlauts_preserved(self):
        """Golden test: German umlauts are preserved."""
        result = tokenize("Über die Brücke.", language="de")

        display_texts = [t.display_text for t in result.tokens]

        assert "Über" in display_texts
        assert "Brücke." in display_texts

    def test_golden_german_vgl_abbreviation(self):
        """Golden test: German 'Vgl.' abbreviation doesn't end sentence."""
        result = tokenize("Vgl. das Beispiel.", language="de")

        # "das" should not be sentence start (follows Vgl.)
        expected_sentence_starts = [True, False, False]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]

        assert actual_sentence_starts == expected_sentence_starts


# =============================================================================
# Edge Case Golden Tests
# =============================================================================


class TestEdgeCaseGolden:
    """Golden tests for edge cases."""

    def test_golden_empty_input(self):
        """Golden test: empty input returns empty result."""
        result = tokenize("")

        assert result.total_words == 0
        assert result.tokens == []
        assert result.normalized_text == ""

    def test_golden_whitespace_only(self):
        """Golden test: whitespace-only input returns empty result."""
        result = tokenize("   \n\n\t   ")

        assert result.total_words == 0
        assert result.tokens == []

    def test_golden_single_character(self):
        """Golden test: single character tokenization."""
        result = tokenize("A")

        assert result.total_words == 1
        assert result.tokens[0].display_text == "A"
        assert result.tokens[0].orp_index_display == 0

    def test_golden_unicode_characters(self):
        """Golden test: Unicode characters are preserved."""
        result = tokenize("Hello 世界!")

        display_texts = [t.display_text for t in result.tokens]

        assert "Hello" in display_texts
        assert "世界!" in display_texts

    def test_golden_emoji(self):
        """Golden test: standalone emoji is not tokenized."""
        result = tokenize("Happy 😀 day!")

        display_texts = [t.display_text for t in result.tokens]

        assert "😀" not in display_texts

    def test_golden_very_long_word(self):
        """Golden test: very long word handling."""
        long_word = "supercalifragilisticexpialidocious"  # 34 chars
        result = tokenize(long_word)

        assert result.total_words == 1
        assert result.tokens[0].display_text == long_word
        assert result.tokens[0].orp_index_display == 13
        assert result.tokens[0].delay_multiplier_after == LONG_WORD_MULTIPLIER


# =============================================================================
# Full Document Golden Tests
# =============================================================================


class TestFullDocumentGolden:
    """Golden tests for complete document processing."""

    def test_golden_simple_document(self):
        """Golden test: simple multi-sentence document."""
        text = "Hello world. This is a test. Goodbye!"
        result = tokenize(text)

        assert result.total_words == 7
        assert result.tokenizer_version == TOKENIZER_VERSION
        assert result.language == "en"

        # Verify all display texts
        expected_display_texts = [
            "Hello", "world.", "This", "is", "a", "test.", "Goodbye!"
        ]
        actual_display_texts = [t.display_text for t in result.tokens]
        assert actual_display_texts == expected_display_texts

        # Verify sentence starts
        expected_sentence_starts = [True, False, True, False, False, False, True]
        actual_sentence_starts = [t.is_sentence_start for t in result.tokens]
        assert actual_sentence_starts == expected_sentence_starts

        # Verify word indices are sequential
        expected_indices = list(range(7))
        actual_indices = [t.word_index for t in result.tokens]
        assert actual_indices == expected_indices

    def test_golden_structured_document(self):
        """Golden test: document with paragraphs and structure."""
        text = """First paragraph here.

Second paragraph with more text. And another sentence.

Third and final paragraph."""

        result = tokenize(text)

        # Verify paragraph structure
        para_starts = [t for t in result.tokens if t.is_paragraph_start]
        assert len(para_starts) == 3

        # First token of each paragraph
        para_start_texts = [t.display_text for t in para_starts]
        assert para_start_texts == ["First", "Second", "Third"]

        # Verify break_before values
        first_para_token = next(t for t in result.tokens if t.display_text == "First")
        second_para_token = next(t for t in result.tokens if t.display_text == "Second")
        third_para_token = next(t for t in result.tokens if t.display_text == "Third")

        assert first_para_token.break_before is None
        assert second_para_token.break_before == BreakType.PARAGRAPH
        assert third_para_token.break_before == BreakType.PARAGRAPH

    def test_golden_markdown_document(self):
        """Golden test: complete Markdown document."""
        text = """# Main Title

Introduction paragraph.

## Section One

Content with **bold** and *italic* text.

## Section Two

More content here."""

        result = tokenize(text, source_type="md")

        # Verify no Markdown syntax in output
        all_text = " ".join(t.display_text for t in result.tokens)
        assert "#" not in all_text
        assert "**" not in all_text
        assert "*italic*" not in all_text

        # Verify headings detected
        heading_tokens = [t for t in result.tokens if t.break_before == BreakType.HEADING]
        assert len(heading_tokens) >= 2  # At least Main Title and one section

        # Verify content preserved
        assert "bold" in all_text
        assert "italic" in all_text


# =============================================================================
# Character Offset Golden Tests
# =============================================================================


class TestCharacterOffsetGolden:
    """Golden tests for character offset accuracy."""

    def test_golden_offsets_extract_correct_text(self):
        """Golden test: character offsets correctly map to tokens."""
        text = "Hello world test"
        result = tokenize(text)

        for token in result.tokens:
            extracted = result.normalized_text[
                token.char_offset_start:token.char_offset_end
            ]
            assert extracted == token.display_text, (
                f"Offset mismatch: extracted '{extracted}', "
                f"expected '{token.display_text}'"
            )

    def test_golden_offsets_sequential(self):
        """Golden test: character offsets are non-overlapping and sequential."""
        text = "One two three four five"
        result = tokenize(text)

        for i in range(1, len(result.tokens)):
            prev_end = result.tokens[i - 1].char_offset_end
            curr_start = result.tokens[i].char_offset_start

            assert curr_start > prev_end, (
                f"Overlapping offsets: token {i-1} ends at {prev_end}, "
                f"token {i} starts at {curr_start}"
            )

    def test_golden_specific_offsets(self):
        """Golden test: specific character offsets for known input."""
        text = "Hello world"
        result = tokenize(text)

        # "Hello" is at positions 0-5
        assert result.tokens[0].char_offset_start == 0
        assert result.tokens[0].char_offset_end == 5

        # "world" is at positions 6-11
        assert result.tokens[1].char_offset_start == 6
        assert result.tokens[1].char_offset_end == 11


# =============================================================================
# Consistency Golden Tests
# =============================================================================


class TestConsistencyGolden:
    """Golden tests ensuring consistent behavior."""

    def test_golden_same_input_same_output(self):
        """Golden test: identical input always produces identical output."""
        text = "Test sentence with multiple words."

        result1 = tokenize(text)
        result2 = tokenize(text)

        assert result1.total_words == result2.total_words
        assert result1.normalized_text == result2.normalized_text

        for t1, t2 in zip(result1.tokens, result2.tokens):
            assert t1.word_index == t2.word_index
            assert t1.display_text == t2.display_text
            assert t1.clean_text == t2.clean_text
            assert t1.orp_index_display == t2.orp_index_display
            assert t1.delay_multiplier_after == t2.delay_multiplier_after
            assert t1.is_sentence_start == t2.is_sentence_start
            assert t1.is_paragraph_start == t2.is_paragraph_start
            assert t1.break_before == t2.break_before

    def test_golden_version_matches(self):
        """Golden test: tokenizer version is correctly set."""
        result = tokenize("Test")
        assert result.tokenizer_version == TOKENIZER_VERSION
        assert result.tokenizer_version == "1.0.0"
