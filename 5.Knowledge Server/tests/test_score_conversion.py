"""Tests for confidence score clamping (0-100 range validation)."""

import pytest
from tools.concept_tools import _clamp_confidence_score


class TestScoreClamping:
    """Test confidence score validation and clamping to 0-100 range."""

    def test_clamp_valid_scores(self):
        """Test valid scores in 0-100 range are preserved."""
        assert _clamp_confidence_score(0.0) == 0.0
        assert _clamp_confidence_score(50.0) == 50.0
        assert _clamp_confidence_score(63.4) == 63.4
        assert _clamp_confidence_score(100.0) == 100.0

    def test_clamp_boundary_values(self):
        """Test boundary values at 0 and 100."""
        assert _clamp_confidence_score(0.0) == 0.0
        assert _clamp_confidence_score(100.0) == 100.0
        assert _clamp_confidence_score(0.001) == 0.001
        assert _clamp_confidence_score(99.999) == 99.999

    def test_clamp_out_of_range_high(self):
        """Test out-of-range high values are capped to 100."""
        assert _clamp_confidence_score(150.0) == 100.0
        assert _clamp_confidence_score(101.0) == 100.0
        assert _clamp_confidence_score(1000.0) == 100.0

    def test_clamp_out_of_range_low(self):
        """Test out-of-range low values return 0."""
        assert _clamp_confidence_score(-5.0) == 0.0
        assert _clamp_confidence_score(-0.1) == 0.0

    def test_clamp_invalid_input(self):
        """Test invalid inputs return 0."""
        assert _clamp_confidence_score(None) == 0.0
        assert _clamp_confidence_score("invalid") == 0.0
        assert _clamp_confidence_score([]) == 0.0
