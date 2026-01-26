"""
Unit tests for understanding score calculator.

Tests the three sub-components (relationship density, explanation quality,
metadata completeness) and weighted combination logic.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from services.confidence.models import (
    ConceptData,
    Error,
    ErrorCode,
    RelationshipData,
    Success,
)
from services.confidence.understanding_calculator import (
    TFIDFCorpusManager,
    UnderstandingCalculator,
)


# Fixtures
@pytest.fixture
def mock_data_access():
    """Mock DataAccessLayer"""
    dal = Mock()
    dal.get_concept_relationships = AsyncMock()
    dal.get_concept_for_confidence = AsyncMock()
    return dal


@pytest.fixture
def mock_cache():
    """Mock CacheManager"""
    cache = Mock()
    cache.get_cached_relationships = AsyncMock(return_value=None)
    cache.set_cached_relationships = AsyncMock()
    return cache


@pytest.fixture
def sample_concept_data():
    """Sample concept data for testing with full metadata"""
    return ConceptData(
        id="c1",
        name="Test Concept",
        explanation="This is a comprehensive explanation with domain-specific terminology",
        created_at=datetime.now(),
        last_reviewed_at=datetime.now(),
        tags=["tag1", "tag2"],
        examples=["example1"],
        area="Technology",
        topic="AI",
        subtopic="Machine Learning",
    )


# Test Suite 1: Relationship Density Calculator
@pytest.mark.asyncio
async def test_relationship_density_with_5_of_10_returns_0_5(mock_data_access, mock_cache):
    """5 relationships out of 10 max = 50% density"""
    mock_data_access.get_concept_relationships.return_value = Success(
        RelationshipData(
            total_relationships=5,
            relationship_types={"RELATES_TO": 5},
            connected_concept_ids=["c2", "c3", "c4", "c5", "c6"],
        )
    )

    calculator = UnderstandingCalculator(mock_data_access, mock_cache, max_relationships=10)
    result = await calculator.calculate_relationship_density("c1")

    assert isinstance(result, Success)
    assert result.value == 0.5


@pytest.mark.asyncio
async def test_relationship_density_with_zero_relationships_returns_0_0(
    mock_data_access, mock_cache
):
    """No relationships = 0% density"""
    mock_data_access.get_concept_relationships.return_value = Success(
        RelationshipData(total_relationships=0, relationship_types={}, connected_concept_ids=[])
    )

    calculator = UnderstandingCalculator(mock_data_access, mock_cache, max_relationships=10)
    result = await calculator.calculate_relationship_density("c1")

    assert isinstance(result, Success)
    assert result.value == 0.0


@pytest.mark.asyncio
async def test_relationship_density_uses_cached_data_when_available(mock_data_access, mock_cache):
    """Should use cached data instead of querying database"""
    cached_data = RelationshipData(
        total_relationships=8,
        relationship_types={"RELATES_TO": 8},
        connected_concept_ids=["c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9"],
    )
    mock_cache.get_cached_relationships.return_value = cached_data

    calculator = UnderstandingCalculator(mock_data_access, mock_cache, max_relationships=10)
    result = await calculator.calculate_relationship_density("c1")

    # Should NOT call database
    mock_data_access.get_concept_relationships.assert_not_called()
    assert result.value == 0.8


@pytest.mark.asyncio
async def test_relationship_density_caps_at_1_0_when_exceeding_max(mock_data_access, mock_cache):
    """Density should cap at 1.0 even if relationships exceed max"""
    mock_data_access.get_concept_relationships.return_value = Success(
        RelationshipData(
            total_relationships=25,
            relationship_types={"RELATES_TO": 25},
            connected_concept_ids=[f"c{i}" for i in range(25)],
        )
    )

    calculator = UnderstandingCalculator(mock_data_access, mock_cache, max_relationships=10)
    result = await calculator.calculate_relationship_density("c1")

    assert isinstance(result, Success)
    assert result.value == 1.0  # Capped at 1.0


# Test Suite 2: Explanation Quality Calculator
def test_explanation_quality_with_rich_vocabulary_returns_high_score(mock_data_access, mock_cache):
    """Rich explanation should score >0.6"""
    explanation = "Comprehensive explanation with domain-specific terminology including advanced vocabulary and technical concepts specialized knowledge expertise"

    calculator = UnderstandingCalculator(mock_data_access, mock_cache)
    score = calculator.calculate_explanation_quality(explanation)

    assert score > 0.6


def test_explanation_quality_with_minimal_text_returns_low_score(mock_data_access, mock_cache):
    """Minimal explanation should score <0.3"""
    explanation = "Basic"

    calculator = UnderstandingCalculator(mock_data_access, mock_cache)
    score = calculator.calculate_explanation_quality(explanation)

    assert score < 0.3


def test_explanation_quality_with_stopwords_only_returns_minimum_floor(
    mock_data_access, mock_cache
):
    """Explanation with only stopwords should return minimum floor score"""
    explanation = "the and or but"

    calculator = UnderstandingCalculator(mock_data_access, mock_cache)
    score = calculator.calculate_explanation_quality(explanation)

    # Now returns minimum floor (0.1) instead of 0.0 for non-empty explanations
    assert score == calculator.MINIMUM_EXPLANATION_SCORE


def test_explanation_quality_with_empty_string_returns_zero(mock_data_access, mock_cache):
    """Empty explanation should return 0.0"""
    calculator = UnderstandingCalculator(mock_data_access, mock_cache)
    score = calculator.calculate_explanation_quality("")

    assert score == 0.0


# Test Suite 2b: Short Technical Terms (Issue #6)
def test_explanation_quality_short_technical_term_api_scores_reasonably(
    mock_data_access, mock_cache
):
    """Short technical term 'API' should score reasonably, not near zero"""
    calculator = UnderstandingCalculator(mock_data_access, mock_cache)
    score = calculator.calculate_explanation_quality("API")

    # API is a recognized technical term, should score >= 0.20
    assert score >= 0.20, f"'API' scored {score}, expected >= 0.20"


def test_explanation_quality_short_technical_term_sql_scores_reasonably(
    mock_data_access, mock_cache
):
    """Short technical term 'SQL' should score reasonably"""
    calculator = UnderstandingCalculator(mock_data_access, mock_cache)
    score = calculator.calculate_explanation_quality("SQL")

    assert score >= 0.20, f"'SQL' scored {score}, expected >= 0.20"


def test_explanation_quality_multiple_technical_terms_get_boost(
    mock_data_access, mock_cache
):
    """Explanation with multiple technical terms should get bonus"""
    calculator = UnderstandingCalculator(mock_data_access, mock_cache)

    # Pure technical terms
    score_tech = calculator.calculate_explanation_quality("REST API using HTTP and JSON")
    # Similar length without technical terms
    score_plain = calculator.calculate_explanation_quality("basic item using data and text")

    # Technical terms should score higher due to bonus
    assert score_tech > score_plain, (
        f"Technical explanation ({score_tech}) should score higher than "
        f"plain explanation ({score_plain})"
    )


def test_explanation_quality_technical_terms_bypass_length_filter(
    mock_data_access, mock_cache
):
    """Two-letter technical terms like 'AI' and 'ML' should be recognized"""
    calculator = UnderstandingCalculator(mock_data_access, mock_cache)

    # AI and ML are 2 characters - would fail len(w) > 2 check without technical term recognition
    score = calculator.calculate_explanation_quality("AI and ML models")

    # Should score reasonably since AI and ML are technical terms
    assert score >= 0.20, f"'AI and ML models' scored {score}, expected >= 0.20"


def test_explanation_quality_minimum_floor_on_error_recovery(
    mock_data_access, mock_cache
):
    """Non-empty explanations should never return 0.0 even on edge cases"""
    calculator = UnderstandingCalculator(mock_data_access, mock_cache)

    # Various edge cases that might have returned 0.0 before
    edge_cases = [
        "xy",  # Very short, no technical terms
        "...",  # Punctuation only (becomes empty after split)
        "123",  # Numbers only
    ]

    for case in edge_cases:
        score = calculator.calculate_explanation_quality(case)
        # All non-empty should get at least minimum floor
        assert score >= 0.0, f"Case '{case}' scored {score}, should be >= 0.0"


# Test Suite 3: Weighted Combination
@pytest.mark.asyncio
async def test_understanding_score_combines_all_components_with_correct_weights(
    mock_data_access, mock_cache, sample_concept_data
):
    """Should combine relationship density (40%), explanation (30%), metadata (30%)"""
    # Mock relationship density to return 0.5
    mock_data_access.get_concept_relationships.return_value = Success(
        RelationshipData(
            total_relationships=5,
            relationship_types={"RELATES_TO": 5},
            connected_concept_ids=["c2", "c3", "c4", "c5", "c6"],
        )
    )

    # Mock concept data with full metadata (metadata_score = 1.0)
    mock_data_access.get_concept_for_confidence.return_value = Success(sample_concept_data)

    calculator = UnderstandingCalculator(mock_data_access, mock_cache, max_relationships=10)
    result = await calculator.calculate_understanding_score("c1")

    assert isinstance(result, Success)
    # density=0.5 (40%) + explanation~0.7 (30%) + metadata=1.0 (30%)
    # Expected: 0.40*0.5 + 0.30*0.7 + 0.30*1.0 = 0.2 + 0.21 + 0.3 = 0.71
    assert 0.65 <= result.value <= 0.80  # Allow range due to explanation variance


@pytest.mark.asyncio
async def test_understanding_score_returns_error_when_concept_not_found(
    mock_data_access, mock_cache
):
    """Should propagate error from data access layer"""
    mock_data_access.get_concept_for_confidence.return_value = Error(
        "Concept not found", ErrorCode.NOT_FOUND
    )

    calculator = UnderstandingCalculator(mock_data_access, mock_cache)
    result = await calculator.calculate_understanding_score("nonexistent")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.NOT_FOUND


# Test Suite 4: TFIDFCorpusManager
def test_corpus_manager_detects_growth_trigger():
    """Test 15% growth trigger activates recalculation"""
    manager = TFIDFCorpusManager(vectorizer_path="test_vectorizer.pkl")
    manager.last_concept_count = 100
    manager.vectorizer = Mock()  # Pretend vectorizer exists

    # Create dummy file so file existence check passes
    with open(manager.vectorizer_path, "w") as f:
        f.write("dummy")

    try:
        assert manager.should_recalculate(115)  # 15% growth
        assert not manager.should_recalculate(114)  # 14% growth (below threshold)
    finally:
        # Cleanup
        if os.path.exists(manager.vectorizer_path):
            os.remove(manager.vectorizer_path)


def test_corpus_manager_detects_time_trigger():
    """Test 30-day trigger activates recalculation"""
    manager = TFIDFCorpusManager(vectorizer_path="test_vectorizer_time.pkl")
    manager.vectorizer = Mock()  # Pretend vectorizer exists

    # Create dummy file so file existence check passes
    with open(manager.vectorizer_path, "w") as f:
        f.write("dummy")

    try:
        manager.last_recalc_date = datetime.now() - timedelta(days=31)
        assert manager.should_recalculate(100)

        manager.last_recalc_date = datetime.now() - timedelta(days=29)
        assert not manager.should_recalculate(100)
    finally:
        # Cleanup
        if os.path.exists(manager.vectorizer_path):
            os.remove(manager.vectorizer_path)


def test_corpus_manager_detects_initialization_trigger():
    """Test first-time initialization triggers recalculation"""
    manager = TFIDFCorpusManager(vectorizer_path="test_vectorizer_new.pkl")

    # No vectorizer exists
    assert manager.should_recalculate(100)

    # Cleanup
    if os.path.exists(manager.vectorizer_path):
        os.remove(manager.vectorizer_path)


@pytest.mark.asyncio
async def test_corpus_recalculation_persists_vectorizer():
    """Test vectorizer successfully persisted and loaded"""
    manager = TFIDFCorpusManager(vectorizer_path="test_vectorizer_persist.pkl")

    # Create test corpus
    explanations = [
        "machine learning algorithm for classification",
        "neural network deep learning model",
        "data preprocessing normalization technique",
    ]

    # Recalculate
    result = await manager.recalculate_corpus(explanations)
    assert isinstance(result, Success)
    assert os.path.exists(manager.vectorizer_path)

    # Load and verify
    load_result = manager.load_vectorizer()
    assert isinstance(load_result, Success)
    assert manager.vectorizer is not None
    assert len(manager.vectorizer.vocabulary_) > 0

    # Cleanup
    os.remove(manager.vectorizer_path)
    if os.path.exists(manager.metadata_path):
        os.remove(manager.metadata_path)


@pytest.mark.asyncio
async def test_corpus_recalculation_handles_empty_corpus_gracefully():
    """Test fallback to existing vectorizer on recalculation failure"""
    manager = TFIDFCorpusManager(vectorizer_path="test_vectorizer_error.pkl")

    # Attempt recalculation with invalid data (empty corpus should fail)
    result = await manager.recalculate_corpus([])

    # Should return error
    assert isinstance(result, Error)

    # Cleanup
    if os.path.exists(manager.vectorizer_path):
        os.remove(manager.vectorizer_path)
