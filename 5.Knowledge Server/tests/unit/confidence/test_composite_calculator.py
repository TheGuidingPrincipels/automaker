"""Unit tests for composite confidence calculator."""

from unittest.mock import AsyncMock, Mock

import pytest

from services.confidence.composite_calculator import CompositeCalculator
from services.confidence.models import Error, ErrorCode, Success


@pytest.fixture
def mock_understanding_calculator():
    calc = Mock()
    calc.calculate_understanding_score = AsyncMock()
    return calc


@pytest.fixture
def mock_retention_calculator():
    calc = Mock()
    calc.calculate_retention_score = AsyncMock()
    return calc


@pytest.mark.asyncio
async def test_composite_uses_sixty_forty_weights(
    mock_understanding_calculator, mock_retention_calculator
):
    mock_understanding_calculator.calculate_understanding_score.return_value = Success(0.8)
    mock_retention_calculator.calculate_retention_score.return_value = Success(0.5)

    calculator = CompositeCalculator(mock_understanding_calculator, mock_retention_calculator)
    result = await calculator.calculate_composite_score("concept-1")

    assert isinstance(result, Success)
    assert result.value == pytest.approx(0.68, abs=0.01)


@pytest.mark.asyncio
async def test_composite_handles_low_retention(
    mock_understanding_calculator, mock_retention_calculator
):
    mock_understanding_calculator.calculate_understanding_score.return_value = Success(1.0)
    mock_retention_calculator.calculate_retention_score.return_value = Success(0.1)

    calculator = CompositeCalculator(mock_understanding_calculator, mock_retention_calculator)
    result = await calculator.calculate_composite_score("concept-1")

    assert isinstance(result, Success)
    assert result.value == pytest.approx(0.64, abs=0.01)


@pytest.mark.asyncio
async def test_composite_propagates_understanding_errors(
    mock_understanding_calculator, mock_retention_calculator
):
    mock_understanding_calculator.calculate_understanding_score.return_value = Error(
        "db error",
        ErrorCode.DATABASE_ERROR,
    )

    calculator = CompositeCalculator(mock_understanding_calculator, mock_retention_calculator)
    result = await calculator.calculate_composite_score("concept-1")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.DATABASE_ERROR


@pytest.mark.asyncio
async def test_composite_propagates_retention_errors(
    mock_understanding_calculator, mock_retention_calculator
):
    mock_understanding_calculator.calculate_understanding_score.return_value = Success(0.7)
    mock_retention_calculator.calculate_retention_score.return_value = Error(
        "missing",
        ErrorCode.NOT_FOUND,
    )

    calculator = CompositeCalculator(mock_understanding_calculator, mock_retention_calculator)
    result = await calculator.calculate_composite_score("concept-1")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.NOT_FOUND
