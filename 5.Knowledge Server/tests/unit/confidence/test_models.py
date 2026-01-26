"""
Unit tests for Pydantic data models in confidence scoring system.

Tests data model validation, constraints, and computed properties.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from services.confidence.models import CompletenessReport, ConceptData, RelationshipData, ReviewData


def test_concept_data_with_valid_fields_creates_instance():
    """Valid concept data should create ConceptData instance"""
    data = ConceptData(
        id="c1",
        name="Test Concept",
        explanation="Test explanation",
        created_at=datetime.now(),
        tags=["tag1"],
        examples=["example1"],
    )
    assert data.id == "c1"
    assert data.name == "Test Concept"
    assert data.explanation == "Test explanation"


def test_concept_data_with_empty_explanation_raises_validation_error():
    """Empty explanation should fail validation"""
    with pytest.raises(ValidationError) as exc:
        ConceptData(id="c1", name="Test", explanation="", created_at=datetime.now())
    assert "explanation cannot be empty" in str(exc.value).lower()


def test_concept_data_with_whitespace_explanation_raises_validation_error():
    """Whitespace-only explanation should fail validation"""
    with pytest.raises(ValidationError) as exc:
        ConceptData(id="c1", name="Test", explanation="   ", created_at=datetime.now())
    assert "explanation cannot be empty" in str(exc.value).lower()


def test_concept_data_with_missing_id_raises_validation_error():
    """Missing required field should fail validation"""
    with pytest.raises(ValidationError):
        ConceptData(name="Test", explanation="Test", created_at=datetime.now())


def test_relationship_data_unique_connections_removes_duplicates():
    """unique_connections property should deduplicate concept IDs"""
    data = RelationshipData(
        total_relationships=5,
        relationship_types={"RELATES_TO": 3, "DEPENDS_ON": 2},
        connected_concept_ids=["c2", "c3", "c2", "c4", "c3"],  # Duplicates
    )
    assert data.unique_connections == 3  # c2, c3, c4
    assert set(data.connected_concept_ids) == {"c2", "c3", "c4"}


def test_relationship_data_with_negative_total_raises_validation_error():
    """Negative total_relationships should fail validation"""
    with pytest.raises(ValidationError):
        RelationshipData(total_relationships=-1, relationship_types={}, connected_concept_ids=[])


def test_review_data_with_negative_days_raises_validation_error():
    """Negative days_since_review should fail validation"""
    with pytest.raises(ValidationError):
        ReviewData(last_reviewed_at=datetime.now(), days_since_review=-5, review_count=0)


def test_review_data_with_negative_review_count_raises_validation_error():
    """Negative review_count should fail validation"""
    with pytest.raises(ValidationError):
        ReviewData(last_reviewed_at=datetime.now(), days_since_review=10, review_count=-1)


def test_completeness_report_with_invalid_metadata_score_raises_error():
    """metadata_score outside [0.0, 1.0] should fail validation"""
    with pytest.raises(ValidationError):
        CompletenessReport(
            has_explanation=True,
            has_tags=True,
            has_examples=True,
            has_relationships=True,
            metadata_score=1.5,  # Invalid: > 1.0
        )


def test_completeness_report_with_valid_fields_creates_instance():
    """Valid completeness report should create instance"""
    report = CompletenessReport(
        has_explanation=True,
        has_tags=True,
        has_examples=False,
        has_relationships=True,
        metadata_score=0.75,
    )
    assert report.has_explanation is True
    assert report.has_tags is True
    assert report.has_examples is False
    assert report.metadata_score == 0.75
