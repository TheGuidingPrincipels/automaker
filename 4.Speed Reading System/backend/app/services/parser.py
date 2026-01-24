"""Markdown parser service for processing markdown files."""

import re
from typing import Optional


class MarkdownParser:
    """Service for parsing and cleaning markdown text for reading."""

    # Patterns to remove/transform
    PATTERNS = {
        # Remove images: ![alt](url)
        'images': re.compile(r'!\[([^\]]*)\]\([^)]+\)'),

        # Convert links to just text: [text](url) -> text
        'links': re.compile(r'\[([^\]]+)\]\([^)]+\)'),

        # Remove code blocks (fenced)
        'code_blocks': re.compile(r'```[\s\S]*?```'),

        # Remove inline code but keep text: `code` -> code
        'inline_code': re.compile(r'`([^`]+)`'),

        # Remove headers markers but keep text: ## Header -> Header
        'headers': re.compile(r'^#{1,6}\s*', re.MULTILINE),

        # Remove bold/italic markers: **text** or *text* -> text
        'bold_italic': re.compile(r'\*{1,2}([^*]+)\*{1,2}'),

        # Remove horizontal rules
        'hr': re.compile(r'^[-*_]{3,}\s*$', re.MULTILINE),

        # Remove blockquote markers but keep text: > text -> text
        'blockquotes': re.compile(r'^>\s*', re.MULTILINE),

        # Remove list markers but keep text: - item or * item -> item
        'list_markers': re.compile(r'^[\s]*[-*+]\s+', re.MULTILINE),

        # Remove numbered list markers: 1. item -> item
        'numbered_lists': re.compile(r'^[\s]*\d+\.\s+', re.MULTILINE),
    }

    def parse(self, markdown_text: str) -> str:
        """
        Parse and clean markdown text for RSVP reading.

        Removes formatting markers while preserving readable text.

        Args:
            markdown_text: Raw markdown text.

        Returns:
            Cleaned plain text suitable for reading.
        """
        text = markdown_text

        # Remove code blocks first (they can contain other patterns)
        text = self.PATTERNS['code_blocks'].sub('', text)

        # Remove images (keep alt text would be confusing)
        text = self.PATTERNS['images'].sub('', text)

        # Convert links to just their text
        text = self.PATTERNS['links'].sub(r'\1', text)

        # Remove inline code markers, keep content
        text = self.PATTERNS['inline_code'].sub(r'\1', text)

        # Remove header markers
        text = self.PATTERNS['headers'].sub('', text)

        # Remove bold/italic markers
        text = self.PATTERNS['bold_italic'].sub(r'\1', text)

        # Remove horizontal rules
        text = self.PATTERNS['hr'].sub('', text)

        # Remove blockquote markers
        text = self.PATTERNS['blockquotes'].sub('', text)

        # Remove list markers
        text = self.PATTERNS['list_markers'].sub('', text)
        text = self.PATTERNS['numbered_lists'].sub('', text)

        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 newlines
        text = re.sub(r' +', ' ', text)  # Single spaces

        return text.strip()

    def extract_title(self, markdown_text: str) -> Optional[str]:
        """
        Extract a title from markdown (first H1 header).

        Args:
            markdown_text: Raw markdown text.

        Returns:
            The title if found, None otherwise.
        """
        # Look for first # header
        match = re.search(r'^#\s+(.+)$', markdown_text, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Fallback: first non-empty line
        for line in markdown_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                return line[:100]  # Limit title length

        return None
