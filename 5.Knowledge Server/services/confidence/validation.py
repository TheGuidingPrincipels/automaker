"""
Validation service for confidence scoring system.

Provides input validation, bounds checking, and data completeness analysis.
"""

from datetime import datetime

from services.confidence.models import (
    CompletenessReport,
    ConceptData,
    Error,
    ErrorCode,
    Success,
)


def validate_concept_id(concept_id: str) -> Success | Error:
    """
    Validate concept ID format.

    Args:
        concept_id: Concept identifier to validate

    Returns:
        Success(concept_id) if valid
        Error(VALIDATION_ERROR) if invalid
    """
    if not concept_id or concept_id.strip() == "":
        return Error("Concept ID cannot be empty", ErrorCode.VALIDATION_ERROR)

    if len(concept_id) > 255:
        return Error("Concept ID cannot exceed 255 characters", ErrorCode.VALIDATION_ERROR)

    return Success(concept_id)


def validate_score(score: float, label: str = "Score") -> Success | Error:
    """
    Validate score in [0.0, 1.0] range.

    Args:
        score: Score value to validate
        label: Label for error messages (default: "Score")

    Returns:
        Success(score) if valid
        Error(VALIDATION_ERROR) if invalid
    """
    if not isinstance(score, (int, float)):
        return Error(f"{label} must be numeric", ErrorCode.VALIDATION_ERROR)

    if score < 0.0 or score > 1.0:
        return Error(
            f"{label} must be in range [0.0, 1.0], got {score}",
            ErrorCode.VALIDATION_ERROR,
        )

    return Success(float(score))


def validate_timestamp(timestamp: str) -> Success | Error:
    """
    Validate and parse ISO 8601 timestamp.

    Args:
        timestamp: ISO 8601 formatted timestamp string

    Returns:
        Success(datetime) if valid
        Error(INVALID_FORMAT) if invalid
    """
    if timestamp is None:
        return Error(
            "Timestamp cannot be None. Expected ISO 8601.",
            ErrorCode.INVALID_FORMAT,
            details={"error": "NoneType provided"},
        )

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return Success(dt)
    except (ValueError, AttributeError) as e:
        return Error(
            f"Invalid timestamp format: {timestamp}. Expected ISO 8601.",
            ErrorCode.INVALID_FORMAT,
            details={"error": str(e)},
        )


def check_data_completeness(concept_data: ConceptData) -> CompletenessReport:
    """
    Analyze data completeness for confidence calculation.

    Metadata score calculation:
    - has_explanation: 0.3 (always true due to Pydantic validation)
    - has_tags: 0.2
    - has_examples: 0.2
    - has_taxonomy: 0.3 (area, topic, or subtopic filled)

    Args:
        concept_data: ConceptData instance to analyze

    Returns:
        CompletenessReport with completeness metrics and metadata_score
    """
    has_explanation = bool(concept_data.explanation and concept_data.explanation.strip())
    has_tags = bool(concept_data.tags and len(concept_data.tags) > 0)
    has_examples = bool(concept_data.examples and len(concept_data.examples) > 0)

    # Check if any taxonomy fields are filled (area, topic, or subtopic)
    has_taxonomy = bool(
        (concept_data.area and concept_data.area.strip())
        or (concept_data.topic and concept_data.topic.strip())
        or (concept_data.subtopic and concept_data.subtopic.strip())
    )

    # Calculate metadata score (weighted)
    metadata_score = 0.0
    if has_explanation:
        metadata_score += 0.3
    if has_tags:
        metadata_score += 0.2
    if has_examples:
        metadata_score += 0.2
    if has_taxonomy:
        metadata_score += 0.3

    return CompletenessReport(
        has_explanation=has_explanation,
        has_tags=has_tags,
        has_examples=has_examples,
        has_relationships=False,  # Will be set by data_access layer
        metadata_score=metadata_score,
    )
