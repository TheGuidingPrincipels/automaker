"""Unit tests for retention calculator."""

import math
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from services.confidence.models import Error, ErrorCode, ReviewData, Success
from services.confidence.retention_calculator import RetentionCalculator
from services.confidence.tau_event_emitter import TauEventEmitterProtocol


@pytest.fixture
def mock_data_access():
    dal = Mock()
    dal.get_review_history = AsyncMock()
    dal.get_concept_tau = AsyncMock(return_value=Success(7))
    return dal


@pytest.fixture
def mock_cache():
    cache = Mock()
    cache.get_cached_review_history = AsyncMock(return_value=None)
    cache.set_cached_review_history = AsyncMock()
    cache.invalidate_concept_cache = AsyncMock()
    return cache


@pytest.fixture
def mock_tau_emitter():
    """Mock tau event emitter that returns Success by default."""
    emitter = Mock(spec=TauEventEmitterProtocol)
    emitter.emit_tau_updated = Mock(return_value=Success(10))
    return emitter


@pytest.mark.asyncio
async def test_retention_at_t_zero_returns_one(mock_data_access, mock_cache):
    mock_data_access.get_review_history.return_value = Success(
        ReviewData(
            last_reviewed_at=datetime.now(),
            days_since_review=0,
            review_count=1,
        )
    )

    calculator = RetentionCalculator(mock_data_access, mock_cache)
    result = await calculator.calculate_retention_score("concept-1")

    assert isinstance(result, Success)
    assert result.value == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_retention_at_tau_matches_e_inverse(mock_data_access, mock_cache):
    mock_data_access.get_review_history.return_value = Success(
        ReviewData(
            last_reviewed_at=datetime.now() - timedelta(days=7),
            days_since_review=7,
            review_count=2,
        )
    )

    calculator = RetentionCalculator(mock_data_access, mock_cache, tau=7)
    result = await calculator.calculate_retention_score("concept-1")

    assert isinstance(result, Success)
    assert result.value == pytest.approx(math.exp(-1), abs=0.01)


@pytest.mark.asyncio
async def test_retention_after_long_duration_is_low(mock_data_access, mock_cache):
    mock_data_access.get_review_history.return_value = Success(
        ReviewData(
            last_reviewed_at=datetime.now() - timedelta(days=30),
            days_since_review=30,
            review_count=0,
        )
    )

    calculator = RetentionCalculator(mock_data_access, mock_cache, tau=7)
    result = await calculator.calculate_retention_score("concept-1")

    assert isinstance(result, Success)
    assert result.value == pytest.approx(math.exp(-30 / 7), abs=0.01)
    assert result.value < 0.02


@pytest.mark.asyncio
async def test_retention_uses_custom_tau(mock_data_access, mock_cache):
    mock_data_access.get_review_history.return_value = Success(
        ReviewData(
            last_reviewed_at=datetime.now() - timedelta(days=20),
            days_since_review=20,
            review_count=3,
        )
    )
    mock_data_access.get_concept_tau.return_value = Success(20)

    calculator = RetentionCalculator(mock_data_access, mock_cache, tau=20)
    result = await calculator.calculate_retention_score("concept-1")

    assert isinstance(result, Success)
    assert result.value == pytest.approx(math.exp(-1), abs=0.01)


@pytest.mark.asyncio
async def test_retention_returns_error_when_lookup_fails(mock_data_access, mock_cache):
    mock_data_access.get_review_history.return_value = Error(
        "Concept missing",
        ErrorCode.NOT_FOUND,
    )

    calculator = RetentionCalculator(mock_data_access, mock_cache)
    result = await calculator.calculate_retention_score("missing")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_update_tau_applies_multiplier(mock_data_access, mock_cache, mock_tau_emitter):
    """Test that tau update applies the configured multiplier and emits an event."""
    mock_data_access.get_concept_tau.return_value = Success(7)
    mock_tau_emitter.emit_tau_updated.return_value = Success(10)

    calculator = RetentionCalculator(
        mock_data_access,
        mock_cache,
        tau_multiplier=1.5,
        tau_event_emitter=mock_tau_emitter,
    )

    result = await calculator.update_retention_tau("concept-1")

    # Verify event emitter was called with correct values
    # 7 * 1.5 = 10.5, rounded to 10
    mock_tau_emitter.emit_tau_updated.assert_called_once_with(
        concept_id="concept-1",
        new_tau=10,
        previous_tau=7,
    )
    assert isinstance(result, Success)
    assert result.value == 10


@pytest.mark.asyncio
async def test_update_tau_caps_at_max(mock_data_access, mock_cache, mock_tau_emitter):
    """Test that tau update caps at max_tau and emits an event."""
    mock_data_access.get_concept_tau.return_value = Success(85)
    mock_tau_emitter.emit_tau_updated.return_value = Success(90)

    calculator = RetentionCalculator(
        mock_data_access,
        mock_cache,
        tau_multiplier=2.0,
        max_tau=90,
        tau_event_emitter=mock_tau_emitter,
    )

    result = await calculator.update_retention_tau("concept-1")

    # Verify event emitter was called with capped value
    # 85 * 2.0 = 170, capped at 90
    mock_tau_emitter.emit_tau_updated.assert_called_once_with(
        concept_id="concept-1",
        new_tau=90,
        previous_tau=85,
    )
    assert isinstance(result, Success)
    assert result.value == 90


@pytest.mark.asyncio
async def test_update_tau_returns_default_when_review_not_completed(mock_data_access, mock_cache):
    mock_data_access.get_concept_tau.return_value = Success(14)

    calculator = RetentionCalculator(mock_data_access, mock_cache)
    result = await calculator.update_retention_tau("concept-1", review_completed=False)

    assert isinstance(result, Success)
    assert result.value == 14


@pytest.mark.asyncio
async def test_cached_review_history_is_used(mock_data_access, mock_cache):
    cached = ReviewData(
        last_reviewed_at=datetime.now(),
        days_since_review=5,
        review_count=2,
    )
    mock_cache.get_cached_review_history.return_value = cached

    calculator = RetentionCalculator(mock_data_access, mock_cache)
    result = await calculator.calculate_retention_score("concept-1")

    mock_data_access.get_review_history.assert_not_awaited()
    assert isinstance(result, Success)
    assert result.value == pytest.approx(math.exp(-5 / calculator.default_tau), abs=0.01)


@pytest.mark.asyncio
async def test_update_tau_propagates_errors(mock_data_access, mock_cache, mock_tau_emitter):
    """Test that errors from the event emitter are propagated."""
    mock_data_access.get_concept_tau.return_value = Success(7)
    mock_tau_emitter.emit_tau_updated.return_value = Error("fail", ErrorCode.DATABASE_ERROR)

    calculator = RetentionCalculator(
        mock_data_access,
        mock_cache,
        tau_event_emitter=mock_tau_emitter,
    )
    result = await calculator.update_retention_tau("concept-1")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.DATABASE_ERROR
