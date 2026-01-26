"""Tests for the text normalizer module."""
import pytest
from app.services.tokenizer import normalize_text, NormalizedText


class TestBasicNormalization:
    """Test basic whitespace and text normalization."""

    def test_empty_text(self):
        """Empty string should return empty result."""
        result = normalize_text("")
        assert result.text == ""
        assert result.paragraph_breaks == []
        assert result.heading_positions == []

    def test_basic_whitespace(self):
        """Multiple spaces should be collapsed to single space."""
        text = "Hello    world"
        result = normalize_text(text)
        assert result.text == "Hello world"

    def test_leading_trailing_whitespace(self):
        """Leading and trailing whitespace should be trimmed."""
        text = "   Hello world   "
        result = normalize_text(text)
        assert result.text == "Hello world"

    def test_tab_normalization(self):
        """Tabs should be converted to spaces."""
        text = "Hello\tworld"
        result = normalize_text(text)
        assert result.text == "Hello world"

    def test_line_ending_normalization(self):
        """Windows and Mac line endings should be converted to Unix style."""
        text = "Hello\r\nworld\rtest"
        result = normalize_text(text)
        # Single newlines become spaces within a paragraph
        assert result.text == "Hello world test"


class TestParagraphDetection:
    """Test paragraph boundary detection."""

    def test_preserves_paragraphs(self):
        """Double newlines should preserve paragraph breaks."""
        text = "First paragraph.\n\nSecond paragraph."
        result = normalize_text(text)
        assert "\n\n" in result.text
        assert len(result.paragraph_breaks) == 2

    def test_paragraph_breaks_positions(self):
        """Paragraph breaks should record correct character positions."""
        text = "First.\n\nSecond."
        result = normalize_text(text)
        # First paragraph starts at 0
        assert result.paragraph_breaks[0] == 0
        # Second paragraph starts after "First.\n\n"
        assert result.paragraph_breaks[1] == len("First.") + 2

    def test_multiple_paragraphs(self):
        """Multiple paragraphs should be detected correctly."""
        text = "Para one.\n\nPara two.\n\nPara three."
        result = normalize_text(text)
        assert len(result.paragraph_breaks) == 3

    def test_excessive_blank_lines(self):
        """Multiple blank lines should be normalized to double newline."""
        text = "First.\n\n\n\nSecond."
        result = normalize_text(text)
        # Multiple blank lines should still result in single paragraph break
        assert result.text.count("\n\n") == 1


class TestPdfNormalization:
    """Test PDF-specific text cleanup."""

    def test_pdf_hyphen_join(self):
        """Hyphenated line breaks in PDFs should be joined."""
        text = "exam-\nple"
        result = normalize_text(text, source_type="pdf")
        assert "example" in result.text

    def test_pdf_mid_sentence_join(self):
        """Mid-sentence line breaks in PDFs should be joined."""
        text = "This is a\nsentence that continues."
        result = normalize_text(text, source_type="pdf")
        assert result.text == "This is a sentence that continues."

    def test_pdf_sentence_end_preserved(self):
        """Lines ending with punctuation should not be joined."""
        text = "First sentence.\nSecond sentence."
        result = normalize_text(text, source_type="pdf")
        # After the period, we don't join; these become separate lines initially
        # But they're in the same paragraph, so they get joined with space
        assert "First sentence." in result.text
        assert "Second sentence." in result.text

    def test_pdf_paragraph_break_preserved(self):
        """Blank lines in PDFs should still create paragraph breaks."""
        text = "First paragraph.\n\nSecond paragraph."
        result = normalize_text(text, source_type="pdf")
        assert "\n\n" in result.text
        assert len(result.paragraph_breaks) == 2

    def test_pdf_multiple_hyphenations(self):
        """Multiple hyphenated words should all be joined."""
        text = "under-\nstanding and learn-\ning"
        result = normalize_text(text, source_type="pdf")
        assert "understanding" in result.text
        assert "learning" in result.text


class TestMarkdownNormalization:
    """Test Markdown-specific normalization."""

    def test_markdown_headings(self):
        """Markdown headings should be detected and converted to plain text."""
        text = "# Heading\n\nContent"
        result = normalize_text(text, source_type="md")
        assert len(result.heading_positions) == 1
        assert result.heading_positions[0][1] == 1  # Level 1

    def test_markdown_heading_levels(self):
        """Different heading levels should be detected correctly."""
        text = "# H1\n\n## H2\n\n### H3"
        result = normalize_text(text, source_type="md")
        assert len(result.heading_positions) == 3
        assert result.heading_positions[0][1] == 1
        assert result.heading_positions[1][1] == 2
        assert result.heading_positions[2][1] == 3

    def test_markdown_strips_formatting(self):
        """Markdown formatting should be stripped."""
        text = "# Heading\n\nThis is **bold** and [a link](https://example.com)."
        result = normalize_text(text, source_type="md")
        assert result.text == "Heading\n\nThis is bold and a link."

    def test_markdown_strips_bold(self):
        """Bold text markers should be removed."""
        text = "This is **bold** text."
        result = normalize_text(text, source_type="md")
        assert result.text == "This is bold text."

    def test_markdown_strips_italic(self):
        """Italic text markers should be removed."""
        text = "This is *italic* text."
        result = normalize_text(text, source_type="md")
        assert result.text == "This is italic text."

    def test_markdown_strips_underscore_emphasis(self):
        """Underscore emphasis should be removed."""
        text = "This is __bold__ and _italic_ text."
        result = normalize_text(text, source_type="md")
        assert result.text == "This is bold and italic text."

    def test_markdown_strips_strikethrough(self):
        """Strikethrough should be removed."""
        text = "This is ~~strikethrough~~ text."
        result = normalize_text(text, source_type="md")
        assert result.text == "This is strikethrough text."

    def test_markdown_links_keep_text(self):
        """Links should be converted to just their text."""
        text = "Click [here](https://example.com) for more."
        result = normalize_text(text, source_type="md")
        assert result.text == "Click here for more."

    def test_markdown_images_keep_alt(self):
        """Images should be converted to their alt text."""
        text = "See ![my image](https://example.com/img.png) here."
        result = normalize_text(text, source_type="md")
        assert result.text == "See my image here."

    def test_markdown_images_empty_alt(self):
        """Images with empty alt text should be removed."""
        text = "See ![]( https://example.com/img.png) here."
        result = normalize_text(text, source_type="md")
        assert result.text == "See here."

    def test_markdown_inline_code(self):
        """Inline code should have backticks removed but content kept."""
        text = "Run the `print()` function."
        result = normalize_text(text, source_type="md")
        assert result.text == "Run the print() function."

    def test_markdown_drops_fenced_code_blocks(self):
        """Fenced code blocks should be completely removed."""
        text = "Intro\n\n```python\nprint('no')\n```\n\nOutro"
        result = normalize_text(text, source_type="md")
        assert "print" not in result.text
        assert "Intro" in result.text
        assert "Outro" in result.text

    def test_markdown_drops_tilde_code_blocks(self):
        """Tilde-fenced code blocks should also be removed."""
        text = "Intro\n\n~~~\ncode here\n~~~\n\nOutro"
        result = normalize_text(text, source_type="md")
        assert "code here" not in result.text

    def test_markdown_horizontal_rule(self):
        """Horizontal rules should be removed."""
        text = "Above\n\n---\n\nBelow"
        result = normalize_text(text, source_type="md")
        assert "---" not in result.text
        assert "Above" in result.text
        assert "Below" in result.text

    def test_markdown_unordered_list(self):
        """Unordered list items should become separate paragraphs."""
        text = "List:\n\n- Item one\n- Item two"
        result = normalize_text(text, source_type="md")
        assert "Item one" in result.text
        assert "Item two" in result.text

    def test_markdown_ordered_list(self):
        """Ordered list items should become separate paragraphs."""
        text = "List:\n\n1. First\n2. Second"
        result = normalize_text(text, source_type="md")
        assert "First" in result.text
        assert "Second" in result.text
        # Numbers should be stripped
        assert "1." not in result.text

    def test_markdown_blockquote(self):
        """Blockquotes should have marker removed but content kept."""
        text = "> This is a quote."
        result = normalize_text(text, source_type="md")
        assert result.text == "This is a quote."

    def test_markdown_nested_blockquote(self):
        """Nested blockquotes should have markers removed."""
        text = "> Level one\n> > Level two"
        result = normalize_text(text, source_type="md")
        # Both should be cleaned, content preserved
        assert "Level one" in result.text
        assert "Level two" in result.text

    def test_markdown_html_tags_removed(self):
        """HTML tags should be stripped."""
        text = "This is <b>bold</b> text."
        result = normalize_text(text, source_type="md")
        assert result.text == "This is bold text."


class TestGermanText:
    """Test German-specific text handling."""

    def test_german_quotes(self):
        """German quotation marks should be preserved."""
        text = '„Hallo Welt"'
        result = normalize_text(text)
        assert result.text == '„Hallo Welt"'

    def test_german_guillemets(self):
        """German guillemets should be preserved."""
        text = "»Guten Tag«"
        result = normalize_text(text)
        assert result.text == "»Guten Tag«"

    def test_german_umlauts(self):
        """German umlauts should be preserved."""
        text = "Über die Brücke"
        result = normalize_text(text)
        assert result.text == "Über die Brücke"

    def test_german_sharp_s(self):
        """German sharp s (eszett) should be preserved."""
        text = "Große Straße"
        result = normalize_text(text)
        assert result.text == "Große Straße"


class TestStructuralMarkers:
    """Test that structural markers have correct offsets."""

    def test_paragraph_breaks_match_text(self):
        """Paragraph break positions should match actual positions in text."""
        text = "First para.\n\nSecond para.\n\nThird para."
        result = normalize_text(text)

        # Verify each paragraph break position points to the start of a paragraph
        for pos in result.paragraph_breaks:
            # The character at this position should be a letter (start of paragraph)
            assert result.text[pos].isalpha(), f"Position {pos} is not start of paragraph"

    def test_heading_positions_match_text(self):
        """Heading positions should match actual positions in text."""
        text = "# First Heading\n\nContent\n\n## Second Heading"
        result = normalize_text(text, source_type="md")

        for pos, level in result.heading_positions:
            # The text at this position should be the heading text
            heading_start = result.text[pos:]
            # Should start with a letter (the heading content)
            assert heading_start[0].isalpha(), f"Position {pos} is not start of heading"

    def test_first_paragraph_at_zero(self):
        """First paragraph should always start at position 0."""
        text = "Some text here."
        result = normalize_text(text)
        assert result.paragraph_breaks[0] == 0

    def test_first_heading_at_zero(self):
        """If document starts with heading, it should be at position 0."""
        text = "# Heading\n\nContent"
        result = normalize_text(text, source_type="md")
        if result.heading_positions:
            assert result.heading_positions[0][0] == 0


class TestEdgeCases:
    """Test edge cases and special inputs."""

    def test_only_whitespace(self):
        """Text with only whitespace should return empty result."""
        text = "   \n\n   \t   "
        result = normalize_text(text)
        assert result.text == ""
        assert result.paragraph_breaks == []

    def test_single_character(self):
        """Single character should be handled correctly."""
        result = normalize_text("a")
        assert result.text == "a"
        assert result.paragraph_breaks == [0]

    def test_unicode_preservation(self):
        """Unicode characters should be preserved."""
        text = "Hello 世界! Emoji: 🎉"
        result = normalize_text(text)
        assert "世界" in result.text
        assert "🎉" in result.text

    def test_mixed_line_endings(self):
        """Mixed line endings should all be normalized."""
        text = "Line1\nLine2\r\nLine3\rLine4"
        result = normalize_text(text)
        # All should become single paragraph with spaces
        assert "Line1 Line2 Line3 Line4" == result.text

    def test_very_long_text(self):
        """Long text should be handled without issues."""
        text = "word " * 10000
        result = normalize_text(text)
        assert len(result.text) > 0
        assert result.paragraph_breaks == [0]


class TestPasteSourceType:
    """Test paste source type explicitly."""

    def test_paste_is_default(self):
        """Paste should be the default source type."""
        text = "Hello world"
        result_default = normalize_text(text)
        result_paste = normalize_text(text, source_type="paste")
        assert result_default.text == result_paste.text
        assert result_default.paragraph_breaks == result_paste.paragraph_breaks
        assert result_default.heading_positions == result_paste.heading_positions

    def test_paste_no_heading_detection(self):
        """Paste source should not detect markdown headings."""
        text = "# Not a heading\n\nRegular text"
        result = normalize_text(text, source_type="paste")
        # No heading detection for paste source
        assert result.heading_positions == []
        # The # should be preserved
        assert "#" in result.text

    def test_paste_preserves_markdown_formatting(self):
        """Paste source should preserve markdown-like formatting."""
        text = "This is **bold** and _italic_"
        result = normalize_text(text, source_type="paste")
        assert "**bold**" in result.text
        assert "_italic_" in result.text

    def test_paste_preserves_links(self):
        """Paste source should preserve link syntax."""
        text = "Visit [example](https://example.com)"
        result = normalize_text(text, source_type="paste")
        assert "[example](https://example.com)" in result.text

    def test_paste_handles_windows_line_endings(self):
        """Paste source should normalize Windows line endings."""
        text = "Line one\r\nLine two\r\n\r\nNew paragraph"
        result = normalize_text(text, source_type="paste")
        assert "\r" not in result.text
        assert len(result.paragraph_breaks) == 2


class TestMdSourceAdditional:
    """Additional markdown source tests."""

    def test_md_handles_plus_list_marker(self):
        """Markdown should handle + as list marker."""
        text = "+ Item one\n+ Item two"
        result = normalize_text(text, source_type="md")
        assert "Item one" in result.text
        assert "Item two" in result.text
        assert "+" not in result.text

    def test_md_handles_asterisk_list_marker(self):
        """Markdown should handle * as list marker."""
        text = "* Item one\n* Item two"
        result = normalize_text(text, source_type="md")
        assert "Item one" in result.text
        assert "Item two" in result.text

    def test_md_heading_with_formatting(self):
        """Markdown heading with inline formatting should be cleaned."""
        text = "# **Bold** Heading"
        result = normalize_text(text, source_type="md")
        assert result.heading_positions == [(0, 1)]
        assert "Bold Heading" in result.text
        assert "**" not in result.text

    def test_md_heading_with_link(self):
        """Markdown heading with link should have link text extracted."""
        text = "## Heading with [Link](url)"
        result = normalize_text(text, source_type="md")
        assert "Heading with Link" in result.text
        assert "](url)" not in result.text

    def test_md_empty_heading_ignored(self):
        """Empty heading should be ignored."""
        text = "#  \n\nContent"
        result = normalize_text(text, source_type="md")
        # Empty heading should not create a heading position
        assert all(pos[1] != 1 or result.text[pos[0]] != " " for pos in result.heading_positions)

    def test_md_list_item_with_formatting(self):
        """List items with formatting should be cleaned."""
        text = "- **Bold** item\n- _Italic_ item"
        result = normalize_text(text, source_type="md")
        assert "Bold item" in result.text
        assert "Italic item" in result.text
        assert "**" not in result.text
        assert "_" not in result.text

    def test_md_asterisk_horizontal_rule(self):
        """Asterisk horizontal rules should be removed."""
        text = "Above\n\n***\n\nBelow"
        result = normalize_text(text, source_type="md")
        assert "***" not in result.text
        assert "Above" in result.text
        assert "Below" in result.text

    def test_md_underscore_horizontal_rule(self):
        """Underscore horizontal rules should be removed."""
        text = "Above\n\n___\n\nBelow"
        result = normalize_text(text, source_type="md")
        assert "___" not in result.text

    def test_md_code_block_with_language(self):
        """Code blocks with language specifier should be dropped."""
        text = "Text\n\n```javascript\nconst x = 1;\n```\n\nMore text"
        result = normalize_text(text, source_type="md")
        assert "const" not in result.text
        assert "javascript" not in result.text
        assert "Text" in result.text
        assert "More text" in result.text

    def test_md_multiline_paragraph(self):
        """Multiple lines without blank line should form single paragraph."""
        text = "Line one\nLine two\nLine three"
        result = normalize_text(text, source_type="md")
        # All should be combined into one paragraph
        assert len(result.paragraph_breaks) == 1
        assert "Line one Line two Line three" in result.text

    def test_md_h6_heading(self):
        """H6 heading should be detected."""
        text = "###### Smallest heading"
        result = normalize_text(text, source_type="md")
        assert len(result.heading_positions) == 1
        assert result.heading_positions[0][1] == 6

    def test_md_only_blockquote(self):
        """Only blockquote marker should result in empty."""
        text = ">"
        result = normalize_text(text, source_type="md")
        # Single > with nothing should be stripped/empty
        assert result.text == ""


class TestPdfSourceAdditional:
    """Additional PDF source tests."""

    def test_pdf_question_mark_preserves_break(self):
        """Lines ending with ? should not be joined."""
        text = "Is this a question?\nYes it is."
        result = normalize_text(text, source_type="pdf")
        assert "Is this a question?" in result.text
        assert "Yes it is." in result.text

    def test_pdf_exclamation_preserves_break(self):
        """Lines ending with ! should not be joined."""
        text = "Amazing!\nIndeed."
        result = normalize_text(text, source_type="pdf")
        assert "Amazing!" in result.text

    def test_pdf_colon_preserves_break(self):
        """Lines ending with : should not be joined."""
        text = "Consider:\nThe following."
        result = normalize_text(text, source_type="pdf")
        assert "Consider:" in result.text

    def test_pdf_hyphen_at_word_boundary(self):
        """Hyphen joining only works when surrounded by word characters."""
        text = "some-\nthing"
        result = normalize_text(text, source_type="pdf")
        assert "something" in result.text

    def test_pdf_hyphen_not_mid_word(self):
        """Hyphen with non-word chars should not join."""
        text = "end -\nnew line"
        result = normalize_text(text, source_type="pdf")
        # Should not become "endnew line"
        assert "end" in result.text

    def test_pdf_empty_lines_create_paragraphs(self):
        """Multiple empty lines in PDF should create paragraph break."""
        text = "Para 1\n\n\nPara 2"
        result = normalize_text(text, source_type="pdf")
        assert len(result.paragraph_breaks) == 2

    def test_pdf_leading_whitespace_stripped(self):
        """Leading whitespace on lines should be stripped."""
        text = "   Indented line\n   Another indented"
        result = normalize_text(text, source_type="pdf")
        assert result.text.startswith("Indented")

    def test_pdf_complex_document(self):
        """Test a complex PDF-like document."""
        text = """Introduction to Speed Read-
ing Systems

This chapter discusses the funda-
mentals of rapid reading. Key topics:

1. Eye movements
2. Fixation points
3. Recognition span"""
        result = normalize_text(text, source_type="pdf")
        assert "Reading" in result.text
        assert "fundamentals" in result.text
        # Should have multiple paragraphs
        assert len(result.paragraph_breaks) >= 2


class TestInternalHelpers:
    """Test internal helper behavior through public interface."""

    def test_block_whitespace_normalization(self):
        """Internal whitespace should be collapsed."""
        text = "Hello     world   test"
        result = normalize_text(text)
        assert result.text == "Hello world test"

    def test_empty_blocks_filtered(self):
        """Blocks that become empty after cleaning should be filtered."""
        text = "Content\n\n   \n\nMore content"
        result = normalize_text(text)
        # Middle empty paragraph should not create a break
        assert len(result.paragraph_breaks) == 2

    def test_normalized_text_dataclass(self):
        """NormalizedText should be a proper dataclass."""
        result = normalize_text("Hello")
        assert hasattr(result, "text")
        assert hasattr(result, "paragraph_breaks")
        assert hasattr(result, "heading_positions")

    def test_heading_positions_tuple_structure(self):
        """Heading positions should be (offset, level) tuples."""
        text = "## Level 2\n\n### Level 3"
        result = normalize_text(text, source_type="md")
        for pos in result.heading_positions:
            assert isinstance(pos, tuple)
            assert len(pos) == 2
            assert isinstance(pos[0], int)  # offset
            assert isinstance(pos[1], int)  # level


class TestSourceTypeVariants:
    """Test different source type handling."""

    def test_unknown_source_type_uses_plain_text(self):
        """Unknown source type should default to plain text parsing."""
        text = "# Not a heading"
        result = normalize_text(text, source_type="unknown")
        # Should be treated like paste/plain text
        assert "#" in result.text
        assert result.heading_positions == []

    def test_case_sensitive_source_type(self):
        """Source type should be case sensitive."""
        text = "# Heading"
        result_md = normalize_text(text, source_type="md")
        result_MD = normalize_text(text, source_type="MD")  # uppercase
        # MD (uppercase) should not be recognized as markdown
        assert len(result_md.heading_positions) == 1
        assert len(result_MD.heading_positions) == 0
