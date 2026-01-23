"""Response formatter for RAG query engine.

Handles citation extraction and response formatting.
"""

import re
from dataclasses import dataclass


@dataclass
class ParsedResponse:
    """A parsed LLM response with extracted citations."""

    answer: str
    sources: list[str]


class ResponseFormatter:
    """Formats and parses RAG responses with citation extraction."""

    # Pattern to match citations like [source: path/to/file.md]
    # Handles: [source: file], [file: file], [source:file]
    CITATION_PATTERN = re.compile(r"\[\s*(?:source|file):\s*([^\]]+)\]", re.IGNORECASE)

    def parse_response(self, raw_response: str) -> ParsedResponse:
        """Parse an LLM response and extract citations.

        Args:
            raw_response: The raw response text from the LLM

        Returns:
            ParsedResponse with cleaned answer and extracted sources
        """
        # Find all citations
        citations = self.CITATION_PATTERN.findall(raw_response)

        # Clean and deduplicate sources
        sources = []
        seen: set[str] = set()
        for citation in citations:
            clean_source = citation.strip()
            if clean_source and clean_source not in seen:
                seen.add(clean_source)
                sources.append(clean_source)

        # Remove citation markers from the answer
        cleaned_answer = self.CITATION_PATTERN.sub("", raw_response)

        # Clean up extra whitespace
        cleaned_answer = re.sub(r"\s+", " ", cleaned_answer).strip()
        cleaned_answer = re.sub(r"\s+\.", ".", cleaned_answer)
        cleaned_answer = re.sub(r"\s+,", ",", cleaned_answer)

        return ParsedResponse(answer=cleaned_answer, sources=sources)

    def format_sources_section(self, sources: list[str]) -> str:
        """Format a sources section for display.

        Args:
            sources: List of source file paths

        Returns:
            Formatted markdown sources section
        """
        if not sources:
            return ""

        lines = ["", "---", "**Sources:**"]
        for source in sources:
            lines.append(f"- `{source}`")

        return "\n".join(lines)

    def format_full_response(
        self,
        answer: str,
        sources: list[str],
        confidence: float,
    ) -> str:
        """Format a complete response with answer, sources, and confidence.

        Args:
            answer: The main answer text
            sources: List of source file paths
            confidence: Confidence score (0.0-1.0)

        Returns:
            Formatted markdown response
        """
        parts = [answer]

        if sources:
            parts.append(self.format_sources_section(sources))

        # Add confidence indicator
        if confidence < 0.5:
            parts.append(
                "\n*Note: Limited source material found. "
                "This answer may be incomplete.*"
            )

        return "\n".join(parts)

    def format_no_results_response(self, query: str) -> str:
        """Format a response when no relevant content is found.

        Args:
            query: The original query

        Returns:
            Formatted response explaining no results were found
        """
        return (
            f"I couldn't find any relevant information in the library "
            f'for your question: "{query}"\n\n'
            "This could mean:\n"
            "- The topic isn't covered in your current library\n"
            "- The question might need to be rephrased\n"
            "- The relevant content uses different terminology\n\n"
            "Try rephrasing your question or adding more context."
        )

    def format_context_for_llm(
        self,
        chunks: list[tuple[str, str, str | None]],
    ) -> str:
        """Format retrieved chunks as context for the LLM.

        Args:
            chunks: List of (content, source_file, section) tuples

        Returns:
            Formatted context string for LLM prompt
        """
        if not chunks:
            return "No relevant content found in the library."

        context_parts = []
        for i, (content, source, section) in enumerate(chunks, 1):
            header = f"[{i}] Source: {source}"
            if section:
                header += f" (Section: {section})"

            context_parts.append(f"{header}\n{content}")

        return "\n\n---\n\n".join(context_parts)
