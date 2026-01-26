"""
Unit tests for validation service in confidence scoring system.

Tests input validation, score bounds checking, and data completeness analysis.
"""

from datetime import datetime

from services.confidence.models import ConceptData, Error, ErrorCode, Success
from services.confidence.validation import (
    check_data_completeness,
    validate_concept_id,
    validate_score,
    validate_timestamp,
)


def test_validate_concept_id_with_valid_id_returns_success():
    """Valid concept ID should pass validation"""
    result = validate_concept_id("concept-123")
    assert isinstance(result, Success)
    assert result.value == "concept-123"


def test_validate_concept_id_with_empty_string_returns_error():
    """Empty concept ID should fail validation"""
    result = validate_concept_id("")
    assert isinstance(result, Error)
    assert result.code == ErrorCode.VALIDATION_ERROR
    assert "empty" in result.message.lower()


def test_validate_concept_id_with_whitespace_only_returns_error():
    """Whitespace-only concept ID should fail validation"""
    result = validate_concept_id("   ")
    assert isinstance(result, Error)
    assert result.code == ErrorCode.VALIDATION_ERROR
    assert "empty" in result.message.lower()


def test_validate_concept_id_with_too_long_string_returns_error():
    """Concept ID >255 chars should fail validation"""
    long_id = "x" * 256
    result = validate_concept_id(long_id)
    assert isinstance(result, Error)
    assert "255" in result.message


def test_validate_score_with_valid_range_returns_success():
    """Score in [0.0, 1.0] should pass validation"""
    result = validate_score(0.75)
    assert isinstance(result, Success)
    assert result.value == 0.75


def test_validate_score_with_boundary_values_returns_success():
    """Boundary values 0.0 and 1.0 should pass validation"""
    result_zero = validate_score(0.0)
    assert isinstance(result_zero, Success)
    assert result_zero.value == 0.0

    result_one = validate_score(1.0)
    assert isinstance(result_one, Success)
    assert result_one.value == 1.0


def test_validate_score_with_negative_value_returns_error():
    """Negative score should fail validation"""
    result = validate_score(-0.5)
    assert isinstance(result, Error)
    assert result.code == ErrorCode.VALIDATION_ERROR
    assert "0.0" in result.message and "1.0" in result.message


def test_validate_score_with_value_above_1_returns_error():
    """Score >1.0 should fail validation"""
    result = validate_score(1.5)
    assert isinstance(result, Error)
    assert result.code == ErrorCode.VALIDATION_ERROR
    assert "0.0" in result.message and "1.0" in result.message


def test_validate_score_with_custom_label_includes_label_in_error():
    """Custom label should appear in error message"""
    result = validate_score(-0.5, label="Retention Score")
    assert isinstance(result, Error)
    assert "Retention Score" in result.message


def test_validate_timestamp_with_valid_iso8601_returns_datetime():
    """Valid ISO 8601 timestamp should parse correctly"""
    result = validate_timestamp("2025-11-03T10:30:00Z")
    assert isinstance(result, Success)
    assert result.value.year == 2025
    assert result.value.month == 11
    assert result.value.day == 3
    assert result.value.hour == 10


def test_validate_timestamp_with_iso8601_without_z_returns_success():
    """ISO 8601 timestamp without Z should parse correctly"""
    result = validate_timestamp("2025-11-03T10:30:00")
    assert isinstance(result, Success)
    assert result.value.year == 2025


def test_validate_timestamp_with_invalid_format_returns_error():
    """Invalid timestamp format should fail validation"""
    result = validate_timestamp("invalid-date")
    assert isinstance(result, Error)
    assert result.code == ErrorCode.INVALID_FORMAT
    assert "invalid" in result.message.lower() or "format" in result.message.lower()


def test_validate_timestamp_with_none_returns_error():
    """None timestamp should fail validation"""
    result = validate_timestamp(None)
    assert isinstance(result, Error)
    assert result.code == ErrorCode.INVALID_FORMAT


def test_check_data_completeness_with_all_fields_returns_high_score():
    """Complete data with all fields should return metadata_score = 1.0"""
    concept = ConceptData(
        id="c1",
        name="Complete Concept",
        explanation="Detailed explanation",
        created_at=datetime.now(),
        tags=["tag1", "tag2"],
        examples=["example1"],
        area="Technology",
        topic="AI",
        subtopic="Deep Learning",
    )

    report = check_data_completeness(concept)

    assert report.has_explanation is True
    assert report.has_tags is True
    assert report.has_examples is True
    assert report.metadata_score == 1.0  # 0.3 + 0.2 + 0.2 + 0.3


def test_check_data_completeness_with_missing_tags_returns_lower_score():
    """Missing tags should reduce metadata_score"""
    concept = ConceptData(
        id="c1",
        name="Partial Concept",
        explanation="Has explanation",
        created_at=datetime.now(),
        tags=[],
        examples=["example1"],
        area="Technology",
    )

    report = check_data_completeness(concept)

    assert report.has_explanation is True
    assert report.has_tags is False
    assert report.has_examples is True
    assert report.metadata_score == 0.8  # 0.3 + 0.0 + 0.2 + 0.3


def test_check_data_completeness_with_missing_examples_returns_lower_score():
    """Missing examples should reduce metadata_score"""
    concept = ConceptData(
        id="c1",
        name="Partial Concept",
        explanation="Has explanation",
        created_at=datetime.now(),
        tags=["tag1"],
        examples=[],
        topic="AI",
    )

    report = check_data_completeness(concept)

    assert report.has_explanation is True
    assert report.has_tags is True
    assert report.has_examples is False
    assert report.metadata_score == 0.8  # 0.3 + 0.2 + 0.0 + 0.3


def test_check_data_completeness_with_only_explanation_returns_low_score():
    """Only explanation should return metadata_score = 0.3"""
    concept = ConceptData(
        id="c1",
        name="Minimal Concept",
        explanation="Basic",
        created_at=datetime.now(),
        tags=[],
        examples=[],
    )

    report = check_data_completeness(concept)

    assert report.has_explanation is True
    assert report.has_tags is False
    assert report.has_examples is False
    assert report.metadata_score == 0.3  # 0.3 + 0.0 + 0.0 + 0.0


def test_check_data_completeness_with_taxonomy_area_increases_score():
    """Adding area taxonomy should increase metadata_score"""
    concept = ConceptData(
        id="c1",
        name="Concept with Area",
        explanation="Has explanation",
        created_at=datetime.now(),
        tags=[],
        examples=[],
        area="Technology",
    )

    report = check_data_completeness(concept)

    assert report.has_explanation is True
    assert report.has_tags is False
    assert report.has_examples is False
    assert report.metadata_score == 0.6  # 0.3 + 0.0 + 0.0 + 0.3


def test_check_data_completeness_with_taxonomy_topic_increases_score():
    """Adding topic taxonomy should increase metadata_score"""
    concept = ConceptData(
        id="c1",
        name="Concept with Topic",
        explanation="Has explanation",
        created_at=datetime.now(),
        tags=[],
        examples=[],
        topic="Artificial Intelligence",
    )

    report = check_data_completeness(concept)

    assert report.has_explanation is True
    assert report.metadata_score == 0.6  # 0.3 + 0.0 + 0.0 + 0.3


def test_check_data_completeness_with_taxonomy_subtopic_increases_score():
    """Adding subtopic taxonomy should increase metadata_score"""
    concept = ConceptData(
        id="c1",
        name="Concept with Subtopic",
        explanation="Has explanation",
        created_at=datetime.now(),
        tags=[],
        examples=[],
        subtopic="Deep Learning",
    )

    report = check_data_completeness(concept)

    assert report.has_explanation is True
    assert report.metadata_score == 0.6  # 0.3 + 0.0 + 0.0 + 0.3


def test_check_data_completeness_with_multiple_taxonomy_fields_counts_once():
    """Multiple taxonomy fields (area+topic+subtopic) should count as single taxonomy bonus"""
    concept = ConceptData(
        id="c1",
        name="Concept with Full Taxonomy",
        explanation="Has explanation",
        created_at=datetime.now(),
        tags=[],
        examples=[],
        area="Technology",
        topic="AI",
        subtopic="Deep Learning",
    )

    report = check_data_completeness(concept)

    assert report.has_explanation is True
    assert report.metadata_score == 0.6  # 0.3 + 0.0 + 0.0 + 0.3 (not 0.9)
