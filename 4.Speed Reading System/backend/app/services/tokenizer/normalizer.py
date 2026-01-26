"""
Text normalization for consistent tokenization.

Key behavior:
- Normalizes whitespace (preserving paragraph boundaries)
- Best-effort PDF cleanup
- Markdown -> best-effort plain text (strip formatting; keep readable content)
- Produces structural markers whose offsets match the returned `text`
"""
import re
from dataclasses import dataclass
from typing import Literal

# Maximum input size: 10MB / ~10 million characters
MAX_INPUT_SIZE = 10_000_000


@dataclass
class NormalizedText:
    """Result of text normalization."""

    text: str
    paragraph_breaks: list[int]  # Character positions where blocks start (paragraphs + headings)
    heading_positions: list[tuple[int, int]]  # (char_pos, heading_level)


@dataclass(frozen=True)
class _Block:
    """Internal representation of a text block."""

    kind: Literal["paragraph", "heading"]
    text: str
    heading_level: int | None = None


def normalize_text(raw_text: str, source_type: Literal["paste", "md", "pdf"] = "paste") -> NormalizedText:
    """
    Normalize text for tokenization.

    - Normalizes whitespace (preserving paragraph boundaries)
    - Handles line endings
    - For Markdown: strips formatting to plain text (best effort)
    - Special handling for PDF artifacts

    Args:
        raw_text: The input text
        source_type: "paste", "md", or "pdf"

    Returns:
        NormalizedText with cleaned text and structural markers
    """
    if not raw_text:
        return NormalizedText(text="", paragraph_breaks=[], heading_positions=[])

    if len(raw_text) > MAX_INPUT_SIZE:
        raise ValueError(
            f"Input text exceeds maximum size of {MAX_INPUT_SIZE:,} characters "
            f"(got {len(raw_text):,} characters)"
        )

    # Normalize line endings first
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    if source_type == "pdf":
        text = _normalize_pdf_text(text)

    if source_type == "md":
        blocks = _markdown_to_blocks(text)
    else:
        blocks = _plain_text_to_blocks(text)

    normalized_text, paragraph_breaks, heading_positions = _finalize_blocks(blocks)

    return NormalizedText(
        text=normalized_text,
        paragraph_breaks=paragraph_breaks,
        heading_positions=heading_positions,
    )


def _normalize_pdf_text(text: str) -> str:
    """
    Handle common PDF extraction artifacts.

    - Joins hyphenated line breaks (e.g., "exam-\\nple" -> "example")
    - Joins lines that don't end with sentence punctuation (likely mid-sentence breaks)
    """
    # Join hyphenated line breaks (common in PDFs)
    # "exam-\nple" -> "example"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Join lines that don't end with sentence punctuation
    # (likely mid-sentence line breaks from PDF columns)
    lines = text.split("\n")
    joined_lines: list[str] = []
    buffer = ""

    for line in lines:
        line = line.strip()
        if not line:
            if buffer:
                joined_lines.append(buffer)
                buffer = ""
            joined_lines.append("")  # Preserve paragraph break
            continue

        if buffer:
            # Check if previous line ended mid-sentence
            if buffer and buffer[-1] not in ".!?:":
                buffer += " " + line
            else:
                joined_lines.append(buffer)
                buffer = line
        else:
            buffer = line

    if buffer:
        joined_lines.append(buffer)

    return "\n".join(joined_lines)


def _plain_text_to_blocks(text: str) -> list[_Block]:
    """
    Convert plain text into paragraph blocks.

    Paragraphs are separated by blank lines (one or more).
    """
    paragraphs = re.split(r"\n\s*\n", text)
    blocks: list[_Block] = []

    for para in paragraphs:
        if para.strip():
            blocks.append(_Block(kind="paragraph", text=para))

    return blocks


def _markdown_to_blocks(text: str) -> list[_Block]:
    """
    Convert Markdown into best-effort plain-text blocks.

    v1 rules:
    - Strip formatting (emphasis, links, images, inline code markers)
    - Drop fenced code blocks entirely
    - Headings become heading blocks (used for `break_before="heading"`)
    - List items become separate paragraph blocks
    """
    lines = text.split("\n")
    blocks: list[_Block] = []
    current_para: list[str] = []

    fence_re = re.compile(r"^\s*(```|~~~)")
    heading_re = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
    list_re = re.compile(r"^\s*(?:[-*+]|(\d+)\.)\s+(.+?)\s*$")
    hr_re = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")

    in_fenced_code = False

    def flush_paragraph() -> None:
        nonlocal current_para
        if not current_para:
            return

        raw = " ".join(current_para)
        clean = _strip_markdown_inline(raw)
        if clean:
            blocks.append(_Block(kind="paragraph", text=clean))
        current_para = []

    for line in lines:
        if fence_re.match(line):
            in_fenced_code = not in_fenced_code
            continue

        if in_fenced_code:
            continue

        if hr_re.match(line):
            flush_paragraph()
            continue

        if not line.strip():
            flush_paragraph()
            continue

        heading_match = heading_re.match(line)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            heading_text = _strip_markdown_inline(heading_match.group(2))
            if heading_text:
                blocks.append(_Block(kind="heading", text=heading_text, heading_level=level))
            continue

        list_match = list_re.match(line)
        if list_match:
            flush_paragraph()
            item_text = _strip_markdown_inline(list_match.group(2))
            if item_text:
                blocks.append(_Block(kind="paragraph", text=item_text))
            continue

        # Blockquotes: keep content, drop the marker
        if line.lstrip().startswith(">"):
            line = re.sub(r"^\s*>\s?", "", line)

        current_para.append(line)

    flush_paragraph()
    return blocks


def _strip_markdown_inline(text: str) -> str:
    """
    Best-effort Markdown inline cleanup:
    - Images: ![alt](url) -> alt
    - Links: [text](url) -> text
    - Inline code: `code` -> code
    - Emphasis: **text** / *text* / __text__ / _text_ -> text
    - Strikethrough: ~~text~~ -> text
    - HTML tags removed
    """
    # Images and links
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Inline code (keep content)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Basic emphasis / strong / strike (best effort, non-nested)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)

    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    return text.strip()


def _normalize_block_whitespace(text: str) -> str:
    """
    Normalize whitespace inside a single block.

    Converts all newlines to spaces and collapses multiple spaces.
    """
    text = text.replace("\n", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _finalize_blocks(blocks: list[_Block]) -> tuple[str, list[int], list[tuple[int, int]]]:
    """
    Normalize blocks and compute structural markers whose offsets match the returned text.

    Returns:
        (normalized_text, paragraph_breaks, heading_positions)
    """
    parts: list[str] = []
    paragraph_breaks: list[int] = []
    heading_positions: list[tuple[int, int]] = []

    offset = 0
    first = True

    for block in blocks:
        block_text = _normalize_block_whitespace(block.text)
        if not block_text:
            continue

        if not first:
            parts.append("\n\n")
            offset += 2

        paragraph_breaks.append(offset)

        if block.kind == "heading" and block.heading_level is not None:
            heading_positions.append((offset, block.heading_level))

        parts.append(block_text)
        offset += len(block_text)
        first = False

    return "".join(parts), paragraph_breaks, heading_positions
