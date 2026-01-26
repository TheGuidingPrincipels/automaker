"""
Tokenizer constants for English and German text processing.

This module contains all the constants used by the tokenization engine
including abbreviations, punctuation sets, and timing multipliers.
"""

# Tokenizer version - increment when logic changes
TOKENIZER_VERSION = "1.0.0"

# Languages supported in v1
SUPPORTED_LANGUAGES = {"en", "de"}

# -----------------------------------------------------------------------------
# Sentence and Punctuation Detection
# -----------------------------------------------------------------------------

# Sentence-ending punctuation (ASCII ellipsis "..." is covered via '.')
SENTENCE_ENDERS = {'.', '!', '?', '\u2026'}  # \u2026 = …

# Major pause punctuation (2.5x delay)
MAJOR_PAUSE_PUNCTUATION = {'.', '!', '?', ':'}

# Ellipsis should be treated as a major pause (even when inside quotes)
ELLIPSIS_STRINGS = {"...", "\u2026"}  # \u2026 = …

# Minor pause punctuation (1.5x delay)
MINOR_PAUSE_PUNCTUATION = {',', ';', '\u2014', '\u2013'}  # em dash, en dash

# -----------------------------------------------------------------------------
# Timing Multipliers
# -----------------------------------------------------------------------------

# Long word threshold (characters) for additional delay
LONG_WORD_THRESHOLD = 8
LONG_WORD_MULTIPLIER = 1.2

# Delay multipliers for punctuation
MAJOR_PAUSE_MULTIPLIER = 2.5
MINOR_PAUSE_MULTIPLIER = 1.5

# Abbreviation periods should NOT get a major pause; treat as minor.
ABBREVIATION_PERIOD_MULTIPLIER = MINOR_PAUSE_MULTIPLIER

# Break delays (in multiples of base word duration)
PARAGRAPH_BREAK_MULTIPLIER = 3.0
HEADING_BREAK_MULTIPLIER = 3.5

# -----------------------------------------------------------------------------
# Brackets and Quotes
# -----------------------------------------------------------------------------

# Brackets that can wrap punctuation, e.g. `"Hello!"`, `(word.)`
BRACKET_OPENERS = {'(', '[', '{'}
BRACKET_CLOSERS = {')', ']', '}'}

# Opening quotes (appear before word)
# " ' „ « » ‹ ‚ ' "
OPENING_QUOTES = {
    '"',        # ASCII double quote
    "'",        # ASCII single quote
    '\u201e',   # „ double low-9 quotation mark (German opening)
    '\u00ab',   # « left-pointing double angle quotation mark
    '\u00bb',   # » right-pointing double angle quotation mark
    '\u2039',   # ‹ single left-pointing angle quotation mark
    '\u201a',   # ‚ single low-9 quotation mark
    '\u2018',   # ' left single quotation mark
    '\u201c',   # " left double quotation mark
}

# Closing quotes (appear after word)
# " ' " " » « › '
CLOSING_QUOTES = {
    '"',        # ASCII double quote
    "'",        # ASCII single quote
    '\u201c',   # " left double quotation mark (can be closing in some contexts)
    '\u201d',   # " right double quotation mark
    '\u00bb',   # » right-pointing double angle quotation mark
    '\u00ab',   # « left-pointing double angle quotation mark (closing in some languages)
    '\u203a',   # › single right-pointing angle quotation mark
    '\u2019',   # ' right single quotation mark
}

# All quote characters
ALL_QUOTES = OPENING_QUOTES | CLOSING_QUOTES

# Characters to ignore when looking for terminal punctuation
TRAILING_CLOSERS = ALL_QUOTES | BRACKET_CLOSERS

# -----------------------------------------------------------------------------
# Abbreviations
# -----------------------------------------------------------------------------

# Common abbreviations that don't end sentences (English)
# Stored lowercase for case-insensitive matching
ENGLISH_ABBREVIATIONS = {
    # Titles
    'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr',
    # Common
    'vs', 'etc', 'inc', 'ltd', 'dept', 'est', 'vol', 'rev',
    # Military/titles
    'gen', 'col', 'lt', 'sgt', 'capt', 'cmdr',
    # Months
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    # Ordinals and addresses
    'st', 'nd', 'rd', 'th', 'ave', 'blvd', 'ln',
    # Latin abbreviations
    'e.g', 'i.e', 'cf', 'al', 'approx', 'fig', 'no', 'nos',
}

# Common abbreviations (German)
GERMAN_ABBREVIATIONS = {
    # Titles
    'dr', 'prof', 'hr', 'fr', 'herr', 'frau',
    # Common German abbreviations
    'bzw', 'usw', 'etc', 'vgl', 'ca', 'z.b', 'u.a', 'd.h', 's.o', 's.u',
    'nr', 'str', 'tel', 'inkl', 'exkl', 'ggf', 'evtl', 'bzgl',
    # Months (German)
    'jan', 'feb', 'mar', 'apr', 'mai', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dez',
}

# Combined abbreviations by language
# German includes English abbreviations for mixed-language text
ABBREVIATIONS = {
    'en': ENGLISH_ABBREVIATIONS,
    'de': ENGLISH_ABBREVIATIONS | GERMAN_ABBREVIATIONS,
}

# -----------------------------------------------------------------------------
# Paragraph and Heading Detection
# -----------------------------------------------------------------------------

# Paragraph detection patterns
PARAGRAPH_MARKERS = ['\n\n', '\r\n\r\n']

# Heading detection (Markdown-style)
HEADING_PATTERN = r'^#{1,6}\s+'
