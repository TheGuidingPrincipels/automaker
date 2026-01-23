# tests/test_formatter.py
"""Tests for the ResponseFormatter module."""

import pytest

from src.query.formatter import ResponseFormatter, ParsedResponse


class TestResponseFormatter:
    """Tests for ResponseFormatter class."""

    @pytest.fixture
    def formatter(self):
        """Create a ResponseFormatter instance."""
        return ResponseFormatter()

    def test_parse_response_single_citation(self, formatter):
        """Test parsing response with single citation."""
        raw = "The answer is 42 [source: guide/answer.md] and that's it."

        result = formatter.parse_response(raw)

        assert "42" in result.answer
        assert "[source:" not in result.answer
        assert result.sources == ["guide/answer.md"]

    def test_parse_response_multiple_citations(self, formatter):
        """Test parsing response with multiple citations."""
        raw = (
            "Point A [source: file1.md] and Point B [source: file2.md] "
            "with another reference [source: file3.md]."
        )

        result = formatter.parse_response(raw)

        assert len(result.sources) == 3
        assert "file1.md" in result.sources
        assert "file2.md" in result.sources
        assert "file3.md" in result.sources

    def test_parse_response_duplicate_citations(self, formatter):
        """Test that duplicate citations are deduplicated."""
        raw = (
            "First [source: same.md] and second [source: same.md] "
            "and third [source: same.md]."
        )

        result = formatter.parse_response(raw)

        assert len(result.sources) == 1
        assert result.sources == ["same.md"]

    def test_parse_response_no_citations(self, formatter):
        """Test parsing response with no citations."""
        raw = "Just a plain answer without any source references."

        result = formatter.parse_response(raw)

        assert result.answer == raw
        assert result.sources == []

    def test_parse_response_case_insensitive(self, formatter):
        """Test that citation parsing is case insensitive."""
        raw = "A [SOURCE: file1.md] and B [Source: file2.md] and C [source: file3.md]."

        result = formatter.parse_response(raw)

        assert len(result.sources) == 3

    def test_parse_response_whitespace_handling(self, formatter):
        """Test handling of whitespace in citations."""
        raw = "Test [source:  file.md ] with spaces."

        result = formatter.parse_response(raw)

        assert "file.md" in result.sources

    def test_parse_response_cleans_extra_whitespace(self, formatter):
        """Test that extra whitespace is cleaned from answer."""
        raw = "Multiple   spaces   and [source: x.md]  cleaned up."

        result = formatter.parse_response(raw)

        assert "  " not in result.answer

    def test_format_sources_section_empty(self, formatter):
        """Test formatting empty sources list."""
        result = formatter.format_sources_section([])

        assert result == ""

    def test_format_sources_section_single(self, formatter):
        """Test formatting single source."""
        result = formatter.format_sources_section(["docs/guide.md"])

        assert "**Sources:**" in result
        assert "`docs/guide.md`" in result

    def test_format_sources_section_multiple(self, formatter):
        """Test formatting multiple sources."""
        sources = ["file1.md", "file2.md", "file3.md"]

        result = formatter.format_sources_section(sources)

        assert "**Sources:**" in result
        assert "`file1.md`" in result
        assert "`file2.md`" in result
        assert "`file3.md`" in result

    def test_format_full_response(self, formatter):
        """Test formatting full response."""
        result = formatter.format_full_response(
            answer="The answer is here.",
            sources=["source.md"],
            confidence=0.8,
        )

        assert "The answer is here." in result
        assert "**Sources:**" in result
        assert "`source.md`" in result

    def test_format_full_response_low_confidence(self, formatter):
        """Test formatting response with low confidence."""
        result = formatter.format_full_response(
            answer="Uncertain answer.",
            sources=["source.md"],
            confidence=0.3,
        )

        assert "may be incomplete" in result

    def test_format_full_response_high_confidence(self, formatter):
        """Test formatting response with high confidence."""
        result = formatter.format_full_response(
            answer="Confident answer.",
            sources=["source.md"],
            confidence=0.9,
        )

        assert "may be incomplete" not in result

    def test_format_no_results_response(self, formatter):
        """Test formatting no results response."""
        result = formatter.format_no_results_response("What is X?")

        assert "What is X?" in result
        assert "couldn't find" in result
        assert "rephras" in result.lower()

    def test_format_context_for_llm_empty(self, formatter):
        """Test formatting empty context."""
        result = formatter.format_context_for_llm([])

        assert "No relevant content found" in result

    def test_format_context_for_llm_single_chunk(self, formatter):
        """Test formatting single chunk."""
        chunks = [("Content here", "file.md", "Section A")]

        result = formatter.format_context_for_llm(chunks)

        assert "[1]" in result
        assert "file.md" in result
        assert "Section A" in result
        assert "Content here" in result

    def test_format_context_for_llm_multiple_chunks(self, formatter):
        """Test formatting multiple chunks."""
        chunks = [
            ("First content", "file1.md", "Section 1"),
            ("Second content", "file2.md", None),
            ("Third content", "file3.md", "Section 3"),
        ]

        result = formatter.format_context_for_llm(chunks)

        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" in result
        assert "file1.md" in result
        assert "file2.md" in result
        assert "file3.md" in result
        assert "Section 1" in result
        assert "Section 3" in result

    def test_format_context_for_llm_no_section(self, formatter):
        """Test formatting chunk without section."""
        chunks = [("Content", "file.md", None)]

        result = formatter.format_context_for_llm(chunks)

        assert "Section:" not in result
        assert "file.md" in result


class TestParsedResponse:
    """Tests for ParsedResponse dataclass."""

    def test_parsed_response_creation(self):
        """Test creating ParsedResponse."""
        pr = ParsedResponse(
            answer="Test answer",
            sources=["source1.md", "source2.md"],
        )

        assert pr.answer == "Test answer"
        assert len(pr.sources) == 2

    def test_parsed_response_empty_sources(self):
        """Test ParsedResponse with no sources."""
        pr = ParsedResponse(
            answer="Answer without sources",
            sources=[],
        )

        assert pr.sources == []
