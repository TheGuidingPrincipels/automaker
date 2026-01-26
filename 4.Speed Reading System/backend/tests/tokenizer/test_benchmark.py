"""
Performance benchmark tests for the Speed Reading System.

These tests serve as sanity checks to ensure performance doesn't regress
significantly. They test the tokenization pipeline, ORP calculator, and
timing calculator with various input sizes.

Run with:
    pytest -m benchmark -v
    pytest tests/tokenizer/test_benchmark.py -v --benchmark-only  # If using pytest-benchmark
"""

import time
from typing import Callable, TypeVar

import pytest

from app.services.tokenizer.orp import ORPCalculator
from app.services.tokenizer import TokenizerPipeline, tokenize
from app.services.tokenizer.normalizer import normalize_text
from app.services.tokenizer.sentence import SentenceDetector
from app.services.tokenizer.text_utils import clean_word
from app.services.tokenizer.timing import (
    TimingCalculator,
    calculate_base_duration_ms,
    estimate_reading_time_ms,
)

pytestmark = pytest.mark.benchmark


# =============================================================================
# Test Fixtures and Utilities
# =============================================================================


T = TypeVar("T")


def measure_time(func: Callable[[], T], iterations: int = 1) -> tuple[T, float]:
    """
    Measure the execution time of a function.

    Args:
        func: Function to measure.
        iterations: Number of times to run the function.

    Returns:
        Tuple of (result, total_time_in_seconds).
    """
    start = time.perf_counter()
    result = None
    for _ in range(iterations):
        result = func()
    end = time.perf_counter()
    return result, end - start


@pytest.fixture
def short_text() -> str:
    """Short text sample (~50 words)."""
    return (
        "The quick brown fox jumps over the lazy dog. This is a simple sentence "
        "for testing purposes. It contains various words of different lengths, "
        "including some punctuation! How does it perform? Let's find out, shall we?"
    )


@pytest.fixture
def medium_text() -> str:
    """Medium text sample (~500 words)."""
    paragraph = (
        "The quick brown fox jumps over the lazy dog. This sentence contains "
        "various words of different lengths and complexities. Performance testing "
        "requires diverse input to accurately measure processing capabilities. "
        "We include punctuation, abbreviations like Dr. Smith and Mrs. Jones, "
        "and even some extraordinarily long words for comprehensive coverage. "
    )
    return (paragraph * 10).strip()


@pytest.fixture
def long_text() -> str:
    """Long text sample (~5000 words)."""
    paragraph = (
        "The quick brown fox jumps over the lazy dog. This sentence contains "
        "various words of different lengths and complexities. Performance testing "
        "requires diverse input to accurately measure processing capabilities. "
        "We include punctuation, abbreviations like Dr. Smith and Mrs. Jones, "
        "and even some extraordinarily long words for comprehensive coverage. "
        "Natural language processing benefits from real-world text samples. "
        "Speed reading systems must handle various text structures efficiently. "
        "Paragraphs, sentences, and headings all require proper detection. "
    )
    return (paragraph * 62).strip()  # ~5000 words


@pytest.fixture
def very_long_text() -> str:
    """Very long text sample (~50000 words)."""
    paragraph = (
        "The quick brown fox jumps over the lazy dog. This sentence contains "
        "various words of different lengths and complexities. Performance testing "
        "requires diverse input to accurately measure processing capabilities. "
        "We include punctuation, abbreviations like Dr. Smith and Mrs. Jones, "
        "and even some extraordinarily long words for comprehensive coverage. "
        "Natural language processing benefits from real-world text samples. "
        "Speed reading systems must handle various text structures efficiently. "
        "Paragraphs, sentences, and headings all require proper detection. "
    )
    return (paragraph * 625).strip()  # ~50000 words


@pytest.fixture
def markdown_text() -> str:
    """Markdown text sample with headings and formatting."""
    return """# Main Heading

This is an introductory paragraph with **bold** and *italic* text.
We also have [links](https://example.com) and `inline code`.

## Second Section

Here's a list:
- First item with some text
- Second item with more content
- Third item including numbers 123

### Subsection

More content here with various punctuation! What do you think?
This paragraph has multiple sentences. Each one is processed.

## Another Section

Final paragraph with abbreviations like Dr. Smith, Mr. Jones, etc.
The tokenizer should handle all of these correctly.
"""


@pytest.fixture
def pipeline() -> TokenizerPipeline:
    """Create a tokenizer pipeline."""
    return TokenizerPipeline(language="en")


@pytest.fixture
def orp_calculator() -> ORPCalculator:
    """Create an ORP calculator."""
    return ORPCalculator(language="en")


@pytest.fixture
def timing_calculator() -> TimingCalculator:
    """Create a timing calculator."""
    return TimingCalculator(language="en")


# =============================================================================
# Tokenization Pipeline Benchmarks
# =============================================================================


class TestTokenizationPerformance:
    """Benchmark tests for the tokenization pipeline."""

    def test_short_text_tokenization_speed(self, pipeline: TokenizerPipeline, short_text: str):
        """Short text should tokenize in under 10ms."""
        result, elapsed = measure_time(lambda: pipeline.process(short_text))

        assert result.total_words > 0
        assert elapsed < 0.010, f"Short text took {elapsed:.4f}s (expected < 0.010s)"

    def test_medium_text_tokenization_speed(self, pipeline: TokenizerPipeline, medium_text: str):
        """Medium text (~500 words) should tokenize in under 50ms."""
        result, elapsed = measure_time(lambda: pipeline.process(medium_text))

        assert result.total_words >= 400
        assert elapsed < 0.050, f"Medium text took {elapsed:.4f}s (expected < 0.050s)"

    def test_long_text_tokenization_speed(self, pipeline: TokenizerPipeline, long_text: str):
        """Long text (~5000 words) should tokenize in under 500ms."""
        result, elapsed = measure_time(lambda: pipeline.process(long_text))

        assert result.total_words >= 4000
        assert elapsed < 0.500, f"Long text took {elapsed:.4f}s (expected < 0.500s)"

    def test_very_long_text_tokenization_speed(
        self, pipeline: TokenizerPipeline, very_long_text: str
    ):
        """Very long text (~50000 words) should tokenize in under 5 seconds."""
        result, elapsed = measure_time(lambda: pipeline.process(very_long_text))

        assert result.total_words >= 40000
        assert elapsed < 5.0, f"Very long text took {elapsed:.4f}s (expected < 5.0s)"

    def test_markdown_processing_speed(self, pipeline: TokenizerPipeline, markdown_text: str):
        """Markdown text should process in under 20ms."""
        result, elapsed = measure_time(lambda: pipeline.process(markdown_text, source_type="md"))

        assert result.total_words > 0
        # Verify markdown was processed (headings detected)
        heading_tokens = [t for t in result.tokens if t.break_before is not None]
        assert len(heading_tokens) > 0

        assert elapsed < 0.020, f"Markdown took {elapsed:.4f}s (expected < 0.020s)"

    def test_repeated_tokenization_consistency(
        self, pipeline: TokenizerPipeline, medium_text: str
    ):
        """Repeated tokenization should have consistent performance."""
        times = []
        for _ in range(10):
            _, elapsed = measure_time(lambda: pipeline.process(medium_text))
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Average should be reasonable
        assert avg_time < 0.050, f"Average time {avg_time:.4f}s exceeded 0.050s"

        # Max time shouldn't be more than 3x average (no major outliers)
        assert max_time < avg_time * 3, f"Max time {max_time:.4f}s > 3x average {avg_time:.4f}s"


# =============================================================================
# ORP Calculator Benchmarks
# =============================================================================


class TestORPCalculatorPerformance:
    """Benchmark tests for ORP calculation."""

    def test_single_word_orp_speed(self, orp_calculator: ORPCalculator):
        """Single word ORP calculation should be nearly instant."""
        words = ["hello", "world", "extraordinary", "a", "the", "internationalization"]

        for word in words:
            _, elapsed = measure_time(lambda w=word: orp_calculator.calculate(w), iterations=1000)
            per_call = elapsed / 1000
            assert per_call < 0.0001, f"ORP for '{word}' took {per_call:.6f}s per call"

    def test_display_text_orp_speed(self, orp_calculator: ORPCalculator):
        """ORP for display text with punctuation should be fast."""
        display_texts = [
            "Hello,",
            "world!",
            '"Quoted"',
            "(parenthetical)",
            "word...",
            "Mr.",
        ]

        for text in display_texts:
            _, elapsed = measure_time(
                lambda t=text: orp_calculator.calculate_for_display(
                    t, clean_word(t)
                ),
                iterations=1000,
            )
            per_call = elapsed / 1000
            assert per_call < 0.0001, f"ORP for '{text}' took {per_call:.6f}s per call"

    def test_bulk_orp_calculation(self, orp_calculator: ORPCalculator, medium_text: str):
        """Bulk ORP calculation for many words should be efficient."""
        words = medium_text.split()

        def calculate_all():
            return [
                orp_calculator.calculate_for_display(w, clean_word(w))
                for w in words
            ]

        results, elapsed = measure_time(calculate_all)

        assert len(results) == len(words)
        per_word = elapsed / len(words)
        assert per_word < 0.0001, f"Bulk ORP took {per_word:.6f}s per word"

    def test_delay_multiplier_speed(self, orp_calculator: ORPCalculator):
        """Delay multiplier calculation should be fast."""
        words = ["hello", "world.", "test,", "Dr.", "extraordinary!", '"Hello!"']

        for word in words:
            _, elapsed = measure_time(
                lambda w=word: orp_calculator.calculate_delay_multiplier(w), iterations=1000
            )
            per_call = elapsed / 1000
            assert per_call < 0.0001, f"Delay for '{word}' took {per_call:.6f}s per call"


# =============================================================================
# Timing Calculator Benchmarks
# =============================================================================


class TestTimingCalculatorPerformance:
    """Benchmark tests for timing calculations."""

    def test_timing_calculation_speed(self, timing_calculator: TimingCalculator):
        """Individual timing calculations should be very fast."""
        words = ["hello", "world.", "test,", "Dr.", "extraordinary!"]

        for word in words:
            _, elapsed = measure_time(
                lambda w=word: timing_calculator.calculate_delay(w), iterations=1000
            )
            per_call = elapsed / 1000
            assert per_call < 0.0001, f"Timing for '{word}' took {per_call:.6f}s per call"

    def test_total_delay_calculation_speed(self, timing_calculator: TimingCalculator):
        """Total delay calculation with break types should be fast."""
        test_cases = [
            ("hello", None),
            ("world.", "paragraph"),
            ("Section", "heading"),
        ]

        for word, break_type in test_cases:
            _, elapsed = measure_time(
                lambda w=word, bt=break_type: timing_calculator.calculate_total_delay(
                    w, break_type=bt
                ),
                iterations=1000,
            )
            per_call = elapsed / 1000
            assert per_call < 0.0001, f"Total delay took {per_call:.6f}s per call"

    def test_reading_time_estimation_speed(self):
        """Reading time estimation should be instant."""
        word_counts = [100, 1000, 10000, 100000]

        for count in word_counts:
            _, elapsed = measure_time(
                lambda c=count: estimate_reading_time_ms(c, 300), iterations=1000
            )
            per_call = elapsed / 1000
            assert per_call < 0.0001, f"Estimation for {count} words took {per_call:.6f}s"


# =============================================================================
# Normalization Benchmarks
# =============================================================================


class TestNormalizationPerformance:
    """Benchmark tests for text normalization."""

    def test_plain_text_normalization_speed(self, medium_text: str):
        """Plain text normalization should be fast."""
        _, elapsed = measure_time(lambda: normalize_text(medium_text, source_type="paste"))

        assert elapsed < 0.010, f"Plain text normalization took {elapsed:.4f}s"

    def test_markdown_normalization_speed(self, markdown_text: str):
        """Markdown normalization should be reasonably fast."""
        _, elapsed = measure_time(lambda: normalize_text(markdown_text, source_type="md"))

        assert elapsed < 0.010, f"Markdown normalization took {elapsed:.4f}s"

    def test_pdf_normalization_speed(self, medium_text: str):
        """PDF normalization should handle artifacts efficiently."""
        # Simulate PDF-like text with line breaks
        pdf_text = medium_text.replace(". ", ".\n").replace("ing ", "ing-\n")

        _, elapsed = measure_time(lambda: normalize_text(pdf_text, source_type="pdf"))

        assert elapsed < 0.020, f"PDF normalization took {elapsed:.4f}s"


# =============================================================================
# Sentence Detection Benchmarks
# =============================================================================


class TestSentenceDetectionPerformance:
    """Benchmark tests for sentence boundary detection."""

    def test_sentence_detection_speed(self, medium_text: str):
        """Sentence detection should be efficient."""
        detector = SentenceDetector(language="en")
        words = medium_text.split()

        _, elapsed = measure_time(lambda: detector.find_boundary_indices(words))

        assert elapsed < 0.010, f"Sentence detection took {elapsed:.4f}s"

    def test_sentence_detection_with_abbreviations(self):
        """Sentence detection with many abbreviations should be efficient."""
        detector = SentenceDetector(language="en")
        text = (
            "Dr. Smith met Mr. Jones at Inc. headquarters. "
            "Prof. Brown from Ltd. spoke with Mrs. Davis. "
        ) * 50
        words = text.split()

        _, elapsed = measure_time(lambda: detector.find_boundary_indices(words))

        assert elapsed < 0.020, f"Abbreviation-heavy detection took {elapsed:.4f}s"


# =============================================================================
# Memory and Scaling Tests
# =============================================================================


class TestScalingBehavior:
    """Tests to verify performance scales reasonably with input size."""

    def test_linear_scaling(self, pipeline: TokenizerPipeline):
        """Tokenization should scale roughly linearly with input size."""
        base_text = "The quick brown fox jumps over the lazy dog. " * 10

        sizes = [1, 2, 4, 8]
        times = []

        for multiplier in sizes:
            text = base_text * multiplier
            _, elapsed = measure_time(lambda t=text: pipeline.process(t))
            times.append(elapsed)

        # Check that doubling input doesn't more than triple time
        # (accounting for some overhead)
        for i in range(1, len(times)):
            ratio = times[i] / times[i - 1] if times[i - 1] > 0 else 0
            assert ratio < 3.0, (
                f"Scaling from {sizes[i - 1]}x to {sizes[i]}x: "
                f"time ratio was {ratio:.2f} (expected < 3.0)"
            )

    def test_pipeline_reuse(self, pipeline: TokenizerPipeline, medium_text: str):
        """Reusing pipeline should not degrade performance."""
        first_times = []
        for _ in range(5):
            _, elapsed = measure_time(lambda: pipeline.process(medium_text))
            first_times.append(elapsed)

        # Process many more times
        for _ in range(100):
            pipeline.process(medium_text)

        later_times = []
        for _ in range(5):
            _, elapsed = measure_time(lambda: pipeline.process(medium_text))
            later_times.append(elapsed)

        avg_first = sum(first_times) / len(first_times)
        avg_later = sum(later_times) / len(later_times)

        # Later times should not be significantly worse
        assert avg_later < avg_first * 2, (
            f"Performance degraded: first avg {avg_first:.4f}s, "
            f"later avg {avg_later:.4f}s"
        )


# =============================================================================
# Convenience Function Benchmark
# =============================================================================


class TestConvenienceFunctionPerformance:
    """Benchmark tests for the tokenize() convenience function."""

    def test_convenience_function_overhead(self, medium_text: str):
        """Convenience function should have minimal overhead vs pipeline."""
        pipeline = TokenizerPipeline()

        # Direct pipeline usage
        _, pipeline_time = measure_time(
            lambda: pipeline.process(medium_text), iterations=10
        )

        # Convenience function (creates new pipeline each time)
        _, convenience_time = measure_time(
            lambda: tokenize(medium_text), iterations=10
        )

        # Convenience function may have some overhead, but should be reasonable
        # (within 5x due to pipeline creation overhead)
        assert convenience_time < pipeline_time * 5, (
            f"Convenience overhead too high: {convenience_time:.4f}s vs "
            f"pipeline {pipeline_time:.4f}s"
        )


# =============================================================================
# Throughput Tests
# =============================================================================


class TestThroughput:
    """Tests measuring words-per-second throughput."""

    def test_tokenization_throughput(self, pipeline: TokenizerPipeline, long_text: str):
        """Measure tokenization throughput in words per second."""
        result, elapsed = measure_time(lambda: pipeline.process(long_text))

        words_per_second = result.total_words / elapsed if elapsed > 0 else 0

        # Should process at least 10,000 words per second
        assert words_per_second >= 10000, (
            f"Throughput {words_per_second:.0f} words/sec (expected >= 10000)"
        )

    def test_orp_throughput(self, orp_calculator: ORPCalculator, long_text: str):
        """Measure ORP calculation throughput."""
        words = long_text.split()

        def calculate_all():
            return [
                orp_calculator.calculate_for_display(w, clean_word(w))
                for w in words
            ]

        _, elapsed = measure_time(calculate_all)

        words_per_second = len(words) / elapsed if elapsed > 0 else 0

        # Should process at least 100,000 words per second
        assert words_per_second >= 100000, (
            f"ORP throughput {words_per_second:.0f} words/sec (expected >= 100000)"
        )
