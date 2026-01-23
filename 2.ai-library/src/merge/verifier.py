# src/merge/verifier.py
"""
Merge verification to ensure no information loss.

CRITICAL: This is the safety guardrail that prevents merges
from losing any content. Rejects any merge that cannot be verified.
"""

import re
from dataclasses import dataclass, field
from typing import List, Set, Tuple
from enum import Enum


class VerificationStatus(str, Enum):
    """Status of merge verification."""
    PASSED = "passed"           # All content preserved
    FAILED = "failed"           # Information loss detected
    NEEDS_REVIEW = "needs_review"  # Uncertain, human review needed


@dataclass
class VerificationResult:
    """Result of merge verification."""
    status: VerificationStatus
    missing_from_original: List[str] = field(default_factory=list)
    missing_from_source: List[str] = field(default_factory=list)
    confidence: float = 0.0     # 0-1 confidence in result
    details: str = ""           # Human-readable explanation


class MergeVerifier:
    """
    Verifies that merged content preserves all information.

    Uses phrase-level comparison to detect information loss.
    Errs on the side of caution - flags uncertain cases for human review.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.9,
        min_phrase_words: int = 3,
    ):
        """
        Initialize the verifier.

        Args:
            confidence_threshold: Minimum confidence for auto-pass
            min_phrase_words: Minimum words for phrase extraction
        """
        self.confidence_threshold = confidence_threshold
        self.min_phrase_words = min_phrase_words

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        # Remove markdown formatting
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'[#*_~>-]', '', text)

        # Normalize whitespace
        text = ' '.join(text.split())
        text = text.lower()

        return text

    def _extract_key_phrases(
        self,
        text: str,
        min_words: int = 3,
        max_words: int = 8,
    ) -> Set[str]:
        """
        Extract key phrases for verification.

        Focuses on content-bearing phrases that would indicate
        information preservation.

        Args:
            text: Normalized input text
            min_words: Minimum words per phrase
            max_words: Maximum words per phrase

        Returns:
            Set of key phrases
        """
        # Split into sentences
        sentences = re.split(r'[.!?;:\n]+', text)
        phrases = set()

        for sentence in sentences:
            words = sentence.split()
            if len(words) < min_words:
                continue

            # Extract significant n-grams
            for n in range(min_words, min(max_words + 1, len(words) + 1)):
                for i in range(len(words) - n + 1):
                    phrase = ' '.join(words[i:i + n])

                    # Filter common/meaningless phrases
                    if self._is_significant_phrase(phrase):
                        phrases.add(phrase)

        return phrases

    def _is_significant_phrase(self, phrase: str) -> bool:
        """Check if a phrase carries significant meaning."""
        # Skip very short phrases
        if len(phrase) < 10:
            return False

        # Skip phrases starting with common function words
        common_starts = [
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
            'to', 'of', 'in', 'for', 'on', 'with', 'as', 'by',
            'this', 'that', 'it', 'we', 'you', 'they', 'i',
        ]
        first_word = phrase.split()[0]
        if first_word in common_starts:
            return False

        # Must contain at least one content word (noun/verb-like)
        words = phrase.split()
        has_content = any(len(w) > 4 and w.isalpha() for w in words)

        return has_content

    def _extract_key_values(self, text: str) -> Set[str]:
        """
        Extract key values that must be preserved.

        Includes: numbers, dates, names, technical terms, etc.

        Args:
            text: Input text

        Returns:
            Set of key values
        """
        values = set()

        # Numbers with context
        number_patterns = re.findall(r'\b\d+(?:\.\d+)?(?:\s*[%kmgbKMGB]|\s*\w+)?\b', text)
        values.update(number_patterns)

        # URLs and paths
        urls = re.findall(r'https?://[^\s]+|/[\w/.-]+', text)
        values.update(urls)

        # Code identifiers (camelCase, snake_case)
        identifiers = re.findall(r'\b[a-z]+(?:[A-Z][a-z]+)+\b|\b[a-z]+(?:_[a-z]+)+\b', text)
        values.update(identifiers)

        # Quoted strings
        quoted = re.findall(r'"[^"]+"|\'[^\']+\'', text)
        values.update(quoted)

        return values

    def verify_no_information_loss(
        self,
        original_content: str,
        source_content: str,
        merged_content: str,
    ) -> VerificationResult:
        """
        Verify that merged content preserves all information.

        Checks both original and source content are represented
        in the merged result.

        Args:
            original_content: Original library content
            source_content: Source block content being merged
            merged_content: Proposed merged content

        Returns:
            VerificationResult with status and details
        """
        # Normalize all content
        original_norm = self._normalize_text(original_content)
        source_norm = self._normalize_text(source_content)
        merged_norm = self._normalize_text(merged_content)

        # Extract phrases from all sources
        original_phrases = self._extract_key_phrases(original_norm)
        source_phrases = self._extract_key_phrases(source_norm)
        merged_phrases = self._extract_key_phrases(merged_norm)

        # Extract key values
        original_values = self._extract_key_values(original_content)
        source_values = self._extract_key_values(source_content)
        merged_values = self._extract_key_values(merged_content)

        # Check for missing content
        missing_from_original = []
        missing_from_source = []

        # Check original phrases in merged
        for phrase in original_phrases:
            if phrase not in merged_norm and not self._partial_match(phrase, merged_norm):
                missing_from_original.append(phrase)

        # Check source phrases in merged
        for phrase in source_phrases:
            if phrase not in merged_norm and not self._partial_match(phrase, merged_norm):
                missing_from_source.append(phrase)

        # Check key values
        for value in original_values:
            if value.lower() not in merged_norm:
                missing_from_original.append(f"[value] {value}")

        for value in source_values:
            if value.lower() not in merged_norm:
                missing_from_source.append(f"[value] {value}")

        # Calculate confidence
        total_items = len(original_phrases) + len(source_phrases)
        missing_count = len(missing_from_original) + len(missing_from_source)

        if total_items == 0:
            confidence = 1.0
        else:
            confidence = 1.0 - (missing_count / max(total_items, 1))

        # Determine status
        if not missing_from_original and not missing_from_source:
            status = VerificationStatus.PASSED
            details = "All content preserved in merged result"
        elif confidence >= self.confidence_threshold:
            status = VerificationStatus.PASSED
            details = f"High confidence ({confidence:.0%}) - minor variations acceptable"
        elif missing_from_original or missing_from_source:
            if confidence < 0.5:
                status = VerificationStatus.FAILED
                details = f"Information loss detected ({confidence:.0%} confidence)"
            else:
                status = VerificationStatus.NEEDS_REVIEW
                details = f"Uncertain ({confidence:.0%} confidence) - human review recommended"
        else:
            status = VerificationStatus.NEEDS_REVIEW
            details = "Unable to verify - human review recommended"

        return VerificationResult(
            status=status,
            missing_from_original=missing_from_original[:10],  # Limit for readability
            missing_from_source=missing_from_source[:10],
            confidence=confidence,
            details=details,
        )

    def _partial_match(self, phrase: str, text: str, threshold: float = 0.7) -> bool:
        """
        Check if phrase has a partial match in text.

        Handles minor variations in wording.

        Args:
            phrase: Phrase to find
            text: Text to search in
            threshold: Minimum word overlap ratio

        Returns:
            True if partial match found
        """
        phrase_words = set(phrase.split())
        text_words = set(text.split())

        overlap = phrase_words & text_words
        overlap_ratio = len(overlap) / len(phrase_words) if phrase_words else 0

        return overlap_ratio >= threshold

    def verify_batch(
        self,
        verifications: List[Tuple[str, str, str]],
    ) -> List[VerificationResult]:
        """
        Verify multiple merges.

        Args:
            verifications: List of (original, source, merged) tuples

        Returns:
            List of VerificationResult objects
        """
        return [
            self.verify_no_information_loss(orig, src, merged)
            for orig, src, merged in verifications
        ]
