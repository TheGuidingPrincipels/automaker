# Session 2: Tokenization Engine

## Overview

**Duration**: ~4-6 hours
**Goal**: Build the core text processing pipeline: normalization, tokenization, ORP calculation, and delay multiplier logic with full test coverage.

**Deliverable**: A tested tokenization module that can process English and German text into structured tokens ready for RSVP display.

---

## Prerequisites

- Session 1 completed (database models, Pydantic schemas exist)
- Backend server running

---

## Locked Decisions (v1)

- Markdown ingestion is **best-effort plain text**: strip formatting (links, emphasis, images), keep readable text for speed reading.
- Abbreviation periods (e.g., `Dr.`, `bzw.`) get a **minor** pause multiplier, and **do not** start a new sentence.
- Em/en dashes (`—`, `–`) and ellipsis (`…`, `...`) stay attached to neighboring words (no standalone punctuation tokens).
- No silent fallbacks: tokenizer errors are explicit and test-covered.

## Core Invariants

- `clean_text` is a substring of `display_text` (case-insensitive).
- `display_text == normalized_text[char_offset_start:char_offset_end]`.
- `break_before` is never set for the first token (`word_index == 0`).
- The first token of every paragraph/heading has `is_paragraph_start == True`.

---

## Objectives & Acceptance Criteria

| #   | Objective                   | Acceptance Criteria                                                                                            |
| --- | --------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 1   | Text normalization          | Whitespace normalized; paragraph boundaries preserved; Markdown converted to best-effort plain text            |
| 2   | Tokenization                | Text split into words; punctuation/dashes/ellipsis attached to neighboring words                               |
| 3   | ORP calculation             | Each token has correct `orp_index_display`                                                                     |
| 4   | Delay multipliers           | Punctuation (including inside closing quotes/brackets), abbreviations, and long words have correct multipliers |
| 5   | Sentence detection          | `is_sentence_start` correctly identifies sentence boundaries (not fooled by abbreviations)                     |
| 6   | Paragraph/heading detection | `break_before` and `is_paragraph_start` set correctly                                                          |
| 7   | German support              | German punctuation „" »« handled correctly                                                                     |
| 8   | Determinism & invariants    | No silent fallbacks; invariants validated in unit tests                                                        |
| 9   | Performance sanity          | Tokenize 20,000 words within a reasonable time locally (track with a benchmark test)                           |
| 10  | Unit tests                  | >90% coverage on tokenizer module                                                                              |

---

## File Structure

```
backend/
├── app/
│   └── services/
│       └── tokenizer/
│           ├── __init__.py
│           ├── normalizer.py       # Text normalization + MD plain-text conversion
│           ├── tokenizer.py        # Main tokenization logic
│           ├── orp.py              # ORP calculation
│           ├── timing.py           # Delay multiplier logic
│           ├── sentence.py         # Sentence boundary detection
│           └── constants.py        # Abbreviations, punctuation sets
└── tests/
    └── tokenizer/
        ├── __init__.py
        ├── test_normalizer.py
        ├── test_tokenizer.py
        ├── test_orp.py
        ├── test_timing.py
        ├── test_sentence.py
        ├── test_golden.py
        └── test_benchmark.py
```

---

## Implementation Details

### 0. TDD Execution Order (Required)

Follow this order so you stay compliant with the repo rules:

1. Write the tests first (start with `test_normalizer.py`, `test_timing.py`, `test_sentence.py`, then `test_tokenizer.py`, then `test_golden.py`).
2. Run `pytest` and confirm the new tests fail (red).
3. Implement the minimal code to make them pass (green).
4. Refactor only after green; keep golden tests stable.

### 1. Constants (`services/tokenizer/constants.py`)

```python
"""
Tokenizer constants for English and German text processing.
"""

# Tokenizer version - increment when logic changes
TOKENIZER_VERSION = "1.0.0"

# Languages supported in v1
SUPPORTED_LANGUAGES = {"en", "de"}

# Sentence-ending punctuation (ASCII ellipsis "..." is covered via '.')
SENTENCE_ENDERS = {'.', '!', '?', '…'}

# Major pause punctuation (2.5x delay)
MAJOR_PAUSE_PUNCTUATION = {'.', '!', '?', ':'}

# Ellipsis should be treated as a major pause (even when inside quotes)
ELLIPSIS_STRINGS = {"...", "…"}

# Minor pause punctuation (1.5x delay)
MINOR_PAUSE_PUNCTUATION = {',', ';', '—', '–'}

# Long word threshold (characters) for additional delay
LONG_WORD_THRESHOLD = 8
LONG_WORD_MULTIPLIER = 1.2

# Delay multipliers
MAJOR_PAUSE_MULTIPLIER = 2.5
MINOR_PAUSE_MULTIPLIER = 1.5

# Abbreviation periods should NOT get a major pause; treat as minor.
ABBREVIATION_PERIOD_MULTIPLIER = MINOR_PAUSE_MULTIPLIER

# Break delays (in multiples of base word duration)
PARAGRAPH_BREAK_MULTIPLIER = 3.0
HEADING_BREAK_MULTIPLIER = 3.5

# Brackets that can wrap punctuation, e.g. `"Hello!"`, `(word.)`
BRACKET_OPENERS = {'(', '[', '{'}
BRACKET_CLOSERS = {')', ']', '}'}

# Opening quotes (appear before word)
OPENING_QUOTES = {'"', "'", '„', '«', '»', '‹', '‚', '‘', '“'}

# Closing quotes (appear after word)
CLOSING_QUOTES = {'"', "'", '“', '”', '»', '«', '›', '’'}

# All quote characters
ALL_QUOTES = OPENING_QUOTES | CLOSING_QUOTES

# Characters to ignore when looking for terminal punctuation
TRAILING_CLOSERS = ALL_QUOTES | BRACKET_CLOSERS

# Common abbreviations that don't end sentences (English)
ENGLISH_ABBREVIATIONS = {
    'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr', 'vs', 'etc', 'inc', 'ltd',
    'dept', 'est', 'vol', 'rev', 'gen', 'col', 'lt', 'sgt', 'capt', 'cmdr',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    'st', 'nd', 'rd', 'th', 'ave', 'blvd', 'rd', 'ln',
    'e.g', 'i.e', 'cf', 'al', 'approx', 'fig', 'no', 'nos',
}

# Common abbreviations (German)
GERMAN_ABBREVIATIONS = {
    'dr', 'prof', 'hr', 'fr', 'herr', 'frau',
    'bzw', 'usw', 'etc', 'vgl', 'ca', 'z.b', 'u.a', 'd.h', 's.o', 's.u',
    'nr', 'str', 'tel', 'inkl', 'exkl', 'ggf', 'evtl', 'bzgl',
    'jan', 'feb', 'mär', 'apr', 'mai', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dez',
}

# Combined abbreviations by language
ABBREVIATIONS = {
    'en': ENGLISH_ABBREVIATIONS,
    'de': ENGLISH_ABBREVIATIONS | GERMAN_ABBREVIATIONS,
}

# Paragraph detection patterns
PARAGRAPH_MARKERS = ['\n\n', '\r\n\r\n']

# Heading detection (Markdown-style)
HEADING_PATTERN = r'^#{1,6}\s+'
```

### 2. Text Normalizer (`services/tokenizer/normalizer.py`)

````python
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

@dataclass
class NormalizedText:
    """Result of text normalization."""
    text: str
    paragraph_breaks: list[int]  # Character positions where blocks start (paragraphs + headings)
    heading_positions: list[tuple[int, int]]  # (char_pos, heading_level)

@dataclass(frozen=True)
class _Block:
    kind: Literal["paragraph", "heading"]
    text: str
    heading_level: int | None = None

def normalize_text(raw_text: str, source_type: str = "paste") -> NormalizedText:
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

    # Normalize line endings first
    text = raw_text.replace('\r\n', '\n').replace('\r', '\n')

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
    """
    # Join hyphenated line breaks (common in PDFs)
    # "exam-\nple" -> "example"
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    # Join lines that don't end with sentence punctuation
    # (likely mid-sentence line breaks from PDF columns)
    lines = text.split('\n')
    joined_lines = []
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
            if buffer and buffer[-1] not in '.!?:':
                buffer += " " + line
            else:
                joined_lines.append(buffer)
                buffer = line
        else:
            buffer = line

    if buffer:
        joined_lines.append(buffer)

    return '\n'.join(joined_lines)

def _plain_text_to_blocks(text: str) -> list[_Block]:
    """
    Convert plain text into paragraph blocks.
    """
    paragraphs = re.split(r'\n\s*\n', text)
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
    lines = text.split('\n')
    blocks: list[_Block] = []
    current_para: list[str] = []

    fence_re = re.compile(r'^\s*(```|~~~)')
    heading_re = re.compile(r'^\s*(#{1,6})\s+(.+?)\s*$')
    list_re = re.compile(r'^\s*(?:[-*+]|(\d+)\.)\s+(.+?)\s*$')
    hr_re = re.compile(r'^\s*(?:-{3,}|\*{3,}|_{3,})\s*$')

    in_fenced_code = False

    def flush_paragraph() -> None:
        nonlocal current_para
        if not current_para:
            return

        raw = ' '.join(current_para)
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
        if line.lstrip().startswith('>'):
            line = re.sub(r'^\s*>\s?', '', line)

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
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Inline code (keep content)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Basic emphasis / strong / strike (best effort, non-nested)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)

    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    return text.strip()

def _normalize_block_whitespace(text: str) -> str:
    """
    Normalize whitespace inside a single block.
    """
    text = text.replace('\n', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
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
            parts.append('\n\n')
            offset += 2

        paragraph_breaks.append(offset)

        if block.kind == "heading" and block.heading_level is not None:
            heading_positions.append((offset, block.heading_level))

        parts.append(block_text)
        offset += len(block_text)
        first = False

    return ''.join(parts), paragraph_breaks, heading_positions
````

### 3. ORP Calculator (`services/tokenizer/orp.py`)

```python
"""
Optimal Recognition Point (ORP) calculation.

The ORP is the character position within a word where the eye should focus
for fastest recognition. Research suggests this is approximately:
- 35% into the word for short words (≤5 chars)
- 40% into the word for longer words

For display, we need to account for any leading punctuation/quotes.
"""

def calculate_orp(clean_text: str) -> int:
    """
    Calculate the ORP index for a clean word (no punctuation).

    Args:
        clean_text: The word without surrounding punctuation

    Returns:
        Zero-based index of the ORP character
    """
    length = len(clean_text)

    if length == 0:
        return 0
    if length == 1:
        return 0
    if length == 2:
        return 0  # Focus on first char for 2-letter words
    if length <= 5:
        # ~35% for short words
        return max(0, int(length * 0.35))
    else:
        # ~40% for longer words
        return max(0, int(length * 0.4))

def calculate_orp_display(display_text: str, clean_text: str) -> int:
    """
    Calculate ORP index in display_text, accounting for leading punctuation.

    Args:
        display_text: The word as it will be displayed (with punctuation)
        clean_text: The word without punctuation (used for ORP calculation)

    Returns:
        Zero-based index in display_text where ORP falls
    """
    # Calculate ORP in clean text
    clean_orp = calculate_orp(clean_text)

    if not clean_text:
        return 0

    # Find where clean_text starts in display_text (case-insensitive).
    # No silent fallback: if this fails, tokenizer invariants were violated.
    start_offset = display_text.casefold().find(clean_text.casefold())
    if start_offset == -1:
        raise ValueError(
            f"clean_text not found in display_text: clean_text={clean_text!r} display_text={display_text!r}"
        )

    return start_offset + clean_orp

# Precomputed ORP positions for common word lengths (optimization)
ORP_TABLE = {
    1: 0,
    2: 0,
    3: 1,
    4: 1,
    5: 1,
    6: 2,
    7: 2,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 4,
    13: 5,
    14: 5,
    15: 6,
}

def calculate_orp_fast(length: int) -> int:
    """
    Fast ORP lookup using precomputed table.
    """
    if length in ORP_TABLE:
        return ORP_TABLE[length]
    # For very long words
    return int(length * 0.4)
```

### 4. Timing Logic (`services/tokenizer/timing.py`)

```python
"""
Delay multiplier calculation for RSVP timing.

Certain words/punctuation require longer display times:
- Sentence-ending punctuation (and ellipsis): 2.5x
- Clause punctuation (comma, semicolon, dashes): 1.5x
- Abbreviations ending in '.' (Dr., bzw., z.B.) get a minor pause (not major)
- Punctuation inside closing quotes/brackets is detected (e.g. `"Hello!"`, `(word.)`)
- Long words (>8 chars): 1.2x (multiplicative with above)
"""

from .constants import (
    ABBREVIATIONS,
    MAJOR_PAUSE_PUNCTUATION,
    MINOR_PAUSE_PUNCTUATION,
    ELLIPSIS_STRINGS,
    TRAILING_CLOSERS,
    ABBREVIATION_PERIOD_MULTIPLIER,
    LONG_WORD_THRESHOLD,
    LONG_WORD_MULTIPLIER,
    MAJOR_PAUSE_MULTIPLIER,
    MINOR_PAUSE_MULTIPLIER,
)

def _strip_trailing_closers(text: str) -> str:
    stripped = text.rstrip()
    while stripped and stripped[-1] in TRAILING_CLOSERS:
        stripped = stripped[:-1]
    return stripped

def _get_terminal_punctuation(display_text: str) -> str | None:
    """
    Return the terminal punctuation for a token, ignoring trailing closers.
    """
    core = _strip_trailing_closers(display_text)
    if not core:
        return None

    # Ellipsis must be checked before '.' because "..." ends with "."
    for ellipsis in ELLIPSIS_STRINGS:
        if core.endswith(ellipsis):
            return ellipsis

    last = core[-1]
    if last in MAJOR_PAUSE_PUNCTUATION or last in MINOR_PAUSE_PUNCTUATION:
        return last

    return None

def _is_abbreviation(clean_text: str, language: str) -> bool:
    if not clean_text:
        return False

    key = clean_text.casefold()
    abbrevs = ABBREVIATIONS.get(language, ABBREVIATIONS["en"])

    if key in abbrevs:
        return True

    # Single letter followed by '.' is usually an initial (A. Smith) → minor pause.
    return len(key) == 1 and key.isalpha()

def calculate_delay_multiplier(display_text: str, clean_text: str, language: str = "en") -> float:
    """
    Calculate the delay multiplier for a token.

    The multiplier is applied to base word duration to determine
    how long to display this word.

    Args:
        display_text: Word with punctuation (for punctuation detection)
        clean_text: Word without punctuation (for length calculation)
        language: "en" or "de" (for abbreviation rules)

    Returns:
        Delay multiplier (1.0 = normal, >1.0 = longer pause)
    """
    multiplier = 1.0

    terminal = _get_terminal_punctuation(display_text)

    if terminal in ELLIPSIS_STRINGS:
        multiplier = MAJOR_PAUSE_MULTIPLIER
    elif terminal in MAJOR_PAUSE_PUNCTUATION:
        multiplier = MAJOR_PAUSE_MULTIPLIER
    elif terminal in MINOR_PAUSE_PUNCTUATION:
        multiplier = MINOR_PAUSE_MULTIPLIER

    # Abbreviation override: periods on abbreviations should NOT be a major pause.
    if terminal == '.' and _is_abbreviation(clean_text, language):
        multiplier = ABBREVIATION_PERIOD_MULTIPLIER

    # Apply long word multiplier (multiplicative)
    if len(clean_text) > LONG_WORD_THRESHOLD:
        multiplier *= LONG_WORD_MULTIPLIER

    return multiplier

def get_break_multiplier(break_type: str | None) -> float:
    """
    Get the blank frame duration multiplier for breaks.

    Args:
        break_type: "paragraph", "heading", or None

    Returns:
        Multiplier for blank frame duration before the word
    """
    from .constants import PARAGRAPH_BREAK_MULTIPLIER, HEADING_BREAK_MULTIPLIER

    if break_type == "paragraph":
        return PARAGRAPH_BREAK_MULTIPLIER
    elif break_type == "heading":
        return HEADING_BREAK_MULTIPLIER
    return 0.0
```

### 5. Sentence Detection (`services/tokenizer/sentence.py`)

```python
"""
Sentence boundary detection for English and German text.

This uses rule-based detection rather than ML to ensure:
- Fast processing
- Deterministic results
- No external dependencies
"""

from .constants import (
    ABBREVIATIONS,
    SENTENCE_ENDERS,
    ALL_QUOTES,
    TRAILING_CLOSERS,
    BRACKET_OPENERS,
)

def is_sentence_end(
    current_word: str,
    next_word: str | None,
    language: str = "en"
) -> bool:
    """
    Determine if current_word ends a sentence.

    Args:
        current_word: The word to check (with punctuation)
        next_word: The following word (for capitalization check), or None
        language: "en" or "de"

    Returns:
        True if this word ends a sentence
    """
    if not current_word:
        return False

    # Strip trailing quotes/brackets to find actual punctuation
    stripped = current_word.rstrip(''.join(TRAILING_CLOSERS))

    if not stripped:
        return False

    last_char = stripped[-1]

    # Must end with sentence-ending punctuation
    if last_char not in SENTENCE_ENDERS:
        return False

    # Check for abbreviations (only for periods)
    if last_char == '.':
        # Get the word without the period
        word_without_punct = stripped[:-1].casefold()
        # Also strip leading punctuation/quotes/brackets
        word_without_punct = word_without_punct.lstrip(''.join(ALL_QUOTES | BRACKET_OPENERS))

        abbrevs = ABBREVIATIONS.get(language, ABBREVIATIONS['en'])
        if word_without_punct in abbrevs:
            return False

        # Single letter followed by period is likely initial (A. Smith)
        if len(word_without_punct) == 1 and word_without_punct.isalpha():
            return False

    # If we have a next word, check if it starts with capital
    # (Strong indicator of sentence start)
    if next_word:
        # Strip leading punctuation/quotes from next word
        next_clean = next_word.lstrip(''.join(ALL_QUOTES | BRACKET_OPENERS))
        if next_clean and next_clean[0].isupper():
            return True
        # Lowercase next word after . is likely not sentence end
        # (unless it's a special case like "i" in English)
        if last_char == '.' and next_clean and next_clean[0].islower():
            # Exception: German nouns are capitalized, so this heuristic
            # works better for English
            if language == "en":
                return False

    # Default: trust the punctuation
    return True

def is_sentence_start(
    word: str,
    prev_word: str | None,
    language: str = "en"
) -> bool:
    """
    Determine if word starts a new sentence.

    This is the inverse check of is_sentence_end on the previous word.

    Args:
        word: The word to check
        prev_word: The previous word, or None (first word)
        language: "en" or "de"

    Returns:
        True if this word starts a sentence
    """
    # First word is always a sentence start
    if prev_word is None:
        return True

    return is_sentence_end(prev_word, word, language)
```

### 6. Main Tokenizer (`services/tokenizer/tokenizer.py`)

```python
"""
Main tokenization pipeline for RSVP reading.

Converts normalized text into a list of Token objects with:
- Display text (with punctuation)
- Clean text (for ORP calculation)
- ORP index
- Delay multiplier
- Sentence/paragraph markers
"""

import re
from dataclasses import dataclass
from typing import Generator

from .normalizer import normalize_text, NormalizedText
from .orp import calculate_orp_display
from .timing import calculate_delay_multiplier
from .sentence import is_sentence_start
from .constants import (
    TOKENIZER_VERSION,
    ALL_QUOTES,
    BRACKET_OPENERS,
    BRACKET_CLOSERS,
)

@dataclass
class TokenData:
    """Intermediate token data before database storage."""
    word_index: int
    display_text: str
    clean_text: str
    orp_index_display: int
    delay_multiplier_after: float
    break_before: str | None  # "paragraph" | "heading" | None
    is_sentence_start: bool
    is_paragraph_start: bool
    char_offset_start: int
    char_offset_end: int

def tokenize_text(
    text: str,
    language: str = "en",
    source_type: str = "paste"
) -> tuple[str, list[TokenData]]:
    """
    Tokenize text into RSVP-ready tokens.

    Args:
        text: Raw input text
        language: "en" or "de"
        source_type: "paste", "md", or "pdf"

    Returns:
        Tuple of (normalized_text, list of TokenData)
    """
    # Step 1: Normalize
    normalized = normalize_text(text, source_type=source_type)

    if not normalized.text:
        return "", []

    # Step 2: Extract words with positions
    words_with_positions = list(_extract_words(normalized.text))

    if not words_with_positions:
        return normalized.text, []

    # Step 3: Build paragraph and heading position sets for fast lookup
    paragraph_char_positions = set(normalized.paragraph_breaks)

    # Map paragraph/heading starts to the break type we want to show *before* that block.
    # Never set a break for the first token.
    break_type_by_char_start: dict[int, str] = {
        pos: "paragraph" for pos in paragraph_char_positions if pos != 0
    }
    for pos, _level in normalized.heading_positions:
        if pos != 0:
            break_type_by_char_start[pos] = "heading"

    # Step 4: Create tokens
    tokens = []
    prev_display_text = None

    for idx, (display_text, clean_text, char_start, char_end) in enumerate(words_with_positions):
        # Determine break_before
        is_para_start = char_start in paragraph_char_positions
        break_before = break_type_by_char_start.get(char_start)

        # Calculate ORP
        orp_index = calculate_orp_display(display_text, clean_text)

        # Calculate delay multiplier
        delay = calculate_delay_multiplier(display_text, clean_text, language=language)

        # Determine sentence start
        # Paragraph/heading starts should be treated as sentence starts for snapping behavior.
        is_sent_start = is_para_start or is_sentence_start(display_text, prev_display_text, language)

        token = TokenData(
            word_index=idx,
            display_text=display_text,
            clean_text=clean_text,
            orp_index_display=orp_index,
            delay_multiplier_after=delay,
            break_before=break_before,
            is_sentence_start=is_sent_start,
            is_paragraph_start=is_para_start,
            char_offset_start=char_start,
            char_offset_end=char_end,
        )
        tokens.append(token)
        prev_display_text = display_text

    return normalized.text, tokens

def _extract_words(text: str) -> Generator[tuple[str, str, int, int], None, None]:
    """
    Extract words from text, preserving punctuation.

    Yields:
        Tuples of (display_text, clean_text, char_start, char_end)
    """
    # Pattern matches words with optional surrounding punctuation
    # This keeps punctuation attached to words
    leading = ''.join(sorted(ALL_QUOTES | BRACKET_OPENERS))
    trailing = ''.join(sorted(ALL_QUOTES | BRACKET_CLOSERS))
    punct = '.,!?;:…—–'

    # Best-effort token pattern:
    # - Attaches quotes/brackets/punctuation to the neighboring word (no standalone punctuation tokens)
    # - Keeps internal connectors like apostrophes, hyphens, and periods (e.g., can't, z.B, 3.14)
    word_pattern = re.compile(
        rf'[{re.escape(leading)}]*'
        rf'[\w]+(?:[\'’\-.][\w]+)*'
        rf'(?:\.{{3}}|[{re.escape(punct)}])*'
        rf'[{re.escape(trailing)}]*',
        re.UNICODE
    )

    for match in word_pattern.finditer(text):
        display_text = match.group(0)
        char_start = match.start()
        char_end = match.end()

        # Clean text: remove punctuation for ORP calculation
        clean_text = _clean_word(display_text)

        if clean_text:  # Only yield if there's actual content
            yield display_text, clean_text, char_start, char_end

def _clean_word(display_text: str) -> str:
    """
    Remove punctuation from word for ORP calculation.
    """
    strip_chars = ''.join(ALL_QUOTES | BRACKET_OPENERS | BRACKET_CLOSERS) + '.,!?;:…—–'
    result = display_text.strip()
    result = result.lstrip(strip_chars)
    result = result.rstrip(strip_chars)
    return result

def get_tokenizer_version() -> str:
    """Return current tokenizer version."""
    return TOKENIZER_VERSION
```

### 7. Module Exports (`services/tokenizer/__init__.py`)

```python
"""
Tokenizer module for RSVP text processing.
"""

from .tokenizer import tokenize_text, TokenData, get_tokenizer_version
from .normalizer import normalize_text, NormalizedText
from .orp import calculate_orp, calculate_orp_display
from .timing import calculate_delay_multiplier, get_break_multiplier
from .sentence import is_sentence_start, is_sentence_end
from .constants import TOKENIZER_VERSION

__all__ = [
    # Main functions
    "tokenize_text",
    "normalize_text",
    "get_tokenizer_version",

    # Data classes
    "TokenData",
    "NormalizedText",

    # Utilities
    "calculate_orp",
    "calculate_orp_display",
    "calculate_delay_multiplier",
    "get_break_multiplier",
    "is_sentence_start",
    "is_sentence_end",

    # Constants
    "TOKENIZER_VERSION",
]
```

---

## Testing Requirements

### Test: Normalizer

````python
# backend/tests/tokenizer/test_normalizer.py
import pytest
from app.services.tokenizer import normalize_text

class TestNormalization:
    def test_basic_whitespace(self):
        text = "Hello    world"
        result = normalize_text(text)
        assert result.text == "Hello world"

    def test_preserves_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph."
        result = normalize_text(text)
        assert "\n\n" in result.text
        assert len(result.paragraph_breaks) == 2

    def test_pdf_hyphen_join(self):
        text = "exam-\nple"
        result = normalize_text(text, source_type="pdf")
        assert "example" in result.text

    def test_markdown_headings(self):
        text = "# Heading\n\nContent"
        result = normalize_text(text, source_type="md")
        assert len(result.heading_positions) == 1
        assert result.heading_positions[0][1] == 1  # Level 1

    def test_markdown_strips_formatting(self):
        text = "# Heading\n\nThis is **bold** and [a link](https://example.com)."
        result = normalize_text(text, source_type="md")
        assert result.text == "Heading\n\nThis is bold and a link."

    def test_markdown_drops_fenced_code_blocks(self):
        text = "Intro\n\n```python\nprint('no')\n```\n\nOutro"
        result = normalize_text(text, source_type="md")
        assert "print" not in result.text

class TestGermanText:
    def test_german_quotes(self):
        text = '„Hallo Welt"'
        result = normalize_text(text)
        assert result.text == '„Hallo Welt"'
````

### Test: ORP Calculation

```python
# backend/tests/tokenizer/test_orp.py
import pytest
from app.services.tokenizer import calculate_orp, calculate_orp_display

class TestORPCalculation:
    @pytest.mark.parametrize("word,expected", [
        ("a", 0),
        ("an", 0),
        ("the", 1),
        ("word", 1),
        ("hello", 1),
        ("reading", 2),
        ("understanding", 5),
    ])
    def test_orp_positions(self, word, expected):
        assert calculate_orp(word) == expected

    def test_orp_with_leading_quote(self):
        display = '"Hello'
        clean = "Hello"
        orp = calculate_orp_display(display, clean)
        # ORP of "Hello" is 1, plus 1 for leading quote = 2
        assert orp == 2

    def test_orp_german_quotes(self):
        display = '„Wort"'
        clean = "Wort"
        orp = calculate_orp_display(display, clean)
        # „ takes 1 char, ORP of "Wort" is 1
        assert orp == 2
```

### Test: Delay Multipliers

```python
# backend/tests/tokenizer/test_timing.py
import pytest
from app.services.tokenizer import calculate_delay_multiplier

class TestDelayMultipliers:
    def test_normal_word(self):
        assert calculate_delay_multiplier("word", "word") == 1.0

    def test_sentence_end(self):
        assert calculate_delay_multiplier("word.", "word") == 2.5

    def test_question_mark(self):
        assert calculate_delay_multiplier("word?", "word") == 2.5

    def test_comma(self):
        assert calculate_delay_multiplier("word,", "word") == 1.5

    def test_abbreviation_period_is_minor_pause(self):
        # Abbreviation periods should not be a major pause
        assert calculate_delay_multiplier("Dr.", "Dr", language="en") == 1.5

    def test_punctuation_inside_quotes(self):
        assert calculate_delay_multiplier('"Hello!"', "Hello") == 2.5

    def test_punctuation_inside_brackets(self):
        assert calculate_delay_multiplier("(Hello.)", "Hello") == 2.5

    def test_em_dash_is_minor_pause(self):
        assert calculate_delay_multiplier("word—", "word") == 1.5

    def test_ellipsis_is_major_pause(self):
        assert calculate_delay_multiplier("word…", "word") == 2.5
        assert calculate_delay_multiplier("word...", "word") == 2.5

    def test_long_word(self):
        # 9 letters > 8 threshold
        mult = calculate_delay_multiplier("wonderful", "wonderful")
        assert mult == 1.2

    def test_long_word_with_period(self):
        # Should be 2.5 * 1.2 = 3.0
        mult = calculate_delay_multiplier("wonderful.", "wonderful")
        assert mult == pytest.approx(3.0)
```

### Test: Sentence Detection

```python
# backend/tests/tokenizer/test_sentence.py
import pytest
from app.services.tokenizer import is_sentence_start, is_sentence_end

class TestSentenceDetection:
    def test_first_word_is_sentence_start(self):
        assert is_sentence_start("The", None) == True

    def test_after_period(self):
        assert is_sentence_end("done.", "The", "en") == True
        assert is_sentence_start("The", "done.") == True

    def test_abbreviation_not_sentence_end(self):
        assert is_sentence_end("Dr.", "Smith", "en") == False
        assert is_sentence_end("Mr.", "Jones", "en") == False

    def test_german_abbreviation(self):
        assert is_sentence_end("bzw.", "das", "de") == False

    def test_question_mark(self):
        assert is_sentence_end("right?", "Yes", "en") == True

    def test_exclamation(self):
        assert is_sentence_end("amazing!", "This", "en") == True

    def test_sentence_end_inside_quotes(self):
        assert is_sentence_end('"Hello!"', "She", "en") == True

    def test_sentence_end_inside_brackets(self):
        assert is_sentence_end("(done.)", "Next", "en") == True

    def test_ellipsis_can_end_sentence(self):
        assert is_sentence_end("wait…", "Next", "en") == True
```

### Test: Full Tokenization

```python
# backend/tests/tokenizer/test_tokenizer.py
import pytest
from app.services.tokenizer import tokenize_text, TokenData

class TestTokenization:
    def test_simple_sentence(self):
        text = "Hello world."
        normalized, tokens = tokenize_text(text)

        assert len(tokens) == 2
        assert tokens[0].display_text == "Hello"
        assert tokens[1].display_text == "world."
        assert tokens[0].is_sentence_start == True
        assert tokens[1].delay_multiplier_after == 2.5

    def test_paragraph_break(self):
        text = "First paragraph.\n\nSecond paragraph."
        normalized, tokens = tokenize_text(text)

        # Find "Second"
        second_token = next(t for t in tokens if "Second" in t.display_text)
        assert second_token.is_paragraph_start == True
        assert second_token.break_before == "paragraph"

    def test_word_indices_sequential(self):
        text = "One two three four five."
        _, tokens = tokenize_text(text)

        indices = [t.word_index for t in tokens]
        assert indices == [0, 1, 2, 3, 4]

    def test_german_text(self):
        text = '„Guten Tag", sagte er.'
        _, tokens = tokenize_text(text, language="de")

        assert len(tokens) > 0
        # First token should have German opening quote
        assert tokens[0].display_text.startswith("„")

    def test_can_tokenize_20k_words(self):
        # Backend enforces a 20k word limit, but tokenizer should still handle it.
        text = "word " * 20000
        _, tokens = tokenize_text(text)

        assert len(tokens) == 20000

    def test_markdown_heading_break(self):
        text = "Intro paragraph.\n\n# Heading\nMore text."
        _, tokens = tokenize_text(text, source_type="md")

        heading_token = next(t for t in tokens if t.display_text == "Heading")
        assert heading_token.is_paragraph_start == True
        assert heading_token.break_before == "heading"

    def test_empty_text(self):
        _, tokens = tokenize_text("")
        assert tokens == []

    def test_char_offsets(self):
        text = "Hello world"
        _, tokens = tokenize_text(text)

        assert tokens[0].char_offset_start == 0
        assert tokens[0].char_offset_end == 5
        assert tokens[1].char_offset_start == 6
        assert tokens[1].char_offset_end == 11

    def test_token_invariants(self):
        text = 'Intro.\n\n# Heading\nMore text.'
        normalized, tokens = tokenize_text(text, source_type="md")

        for t in tokens:
            assert normalized[t.char_offset_start:t.char_offset_end] == t.display_text
            assert t.clean_text.casefold() in t.display_text.casefold()
            assert 0 <= t.orp_index_display < len(t.display_text)
```

### Golden Tests (Fixed Expected Output)

```python
# backend/tests/tokenizer/test_golden.py
"""
Golden tests ensure tokenizer output remains stable.
If these fail after changes, either fix the tokenizer or update the golden output.
"""
import pytest
from app.services.tokenizer import tokenize_text

GOLDEN_ENGLISH = {
    "input": "Dr. Smith said, \"Hello!\" She replied.",
    "expected_tokens": [
        {"display": "Dr.", "is_sentence_start": True, "delay": 1.5},  # abbreviation → minor pause
        {"display": "Smith", "is_sentence_start": False, "delay": 1.0},
        {"display": "said,", "is_sentence_start": False, "delay": 1.5},
        {"display": '"Hello!"', "is_sentence_start": False, "delay": 2.5},
        {"display": "She", "is_sentence_start": True, "delay": 1.0},
        {"display": "replied.", "is_sentence_start": False, "delay": 2.5},
    ]
}

GOLDEN_GERMAN = {
    "input": "Herr Müller fragte: „Wie geht's?“ Sie antwortete.",
    "expected_tokens": [
        {"display": "Herr"},
        {"display": "Müller"},
        {"display": "fragte:"},
        {"display": "„Wie"},
        {"display": "geht's?“"},  # punctuation inside closing quote
        {"display": "Sie"},
        {"display": "antwortete."},
    ],
}

class TestGoldenOutput:
    def test_english_golden(self):
        _, tokens = tokenize_text(GOLDEN_ENGLISH["input"], language="en")

        assert len(tokens) == len(GOLDEN_ENGLISH["expected_tokens"])

        for token, expected in zip(tokens, GOLDEN_ENGLISH["expected_tokens"]):
            assert token.display_text == expected["display"]
            assert token.is_sentence_start == expected["is_sentence_start"]
            assert token.delay_multiplier_after == pytest.approx(expected["delay"], rel=0.1)

    def test_german_golden(self):
        _, tokens = tokenize_text(GOLDEN_GERMAN["input"], language="de")
        assert [t.display_text for t in tokens] == [e["display"] for e in GOLDEN_GERMAN["expected_tokens"]]

        # Ensure punctuation inside closing quotes is recognized for pauses
        q = next(t for t in tokens if "?" in t.display_text)
        assert q.delay_multiplier_after == pytest.approx(2.5)
```

### Optional: Performance Smoke Benchmark

```python
# backend/tests/tokenizer/test_benchmark.py
import time
from app.services.tokenizer import tokenize_text

def test_tokenize_20k_words_benchmark():
    """
    Performance smoke test (non-gating).
    Prints elapsed time so you can track regressions locally.
    """
    text = "word " * 20_000

    start = time.perf_counter()
    _, tokens = tokenize_text(text)
    elapsed = time.perf_counter() - start

    assert len(tokens) == 20_000
    print(f"tokenize_text(20k) took {elapsed:.3f}s")
```

---

## Verification Checklist

- [ ] `normalize_text()` handles paste, markdown, and PDF source types
- [ ] Markdown is converted to best-effort plain text (no `**`, `[]()`, or fenced code blocks)
- [ ] `tokenize_text()` produces correct tokens for sample English text
- [ ] `tokenize_text()` produces correct tokens for sample German text
- [ ] ORP positions are calculated correctly
- [ ] Delay multipliers are correct for punctuation (including inside closing quotes/brackets), abbreviations, and long words
- [ ] Sentence boundaries detected correctly (not fooled by abbreviations)
- [ ] Paragraph breaks marked correctly
- [ ] Heading breaks marked correctly (markdown)
- [ ] Tokenizer invariants are validated (no silent fallbacks)
- [ ] All unit tests pass
- [ ] Golden tests pass

---

## Context for Next Session

**What exists after Session 2:**

- Complete tokenization pipeline in `app/services/tokenizer/`
- Functions: `tokenize_text()`, `normalize_text()`, `calculate_orp_display()`
- TokenData dataclass matching database Token model
- Markdown best-effort plain-text conversion (safe for speed-reading preview)
- Abbreviation-aware timing (periods on abbreviations are minor pauses)
- Comprehensive test suite

**Session 3 will need:**

- `tokenize_text()` function to process uploaded documents
- `TokenData` structure to map to database Token model
- `TOKENIZER_VERSION` for document metadata
