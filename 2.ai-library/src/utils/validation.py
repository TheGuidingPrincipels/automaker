"""Validation utilities for AI-Library models."""

import logging
import math
from typing import Any


def normalize_confidence(
    value: Any, *, default: float = 0.5, log: logging.Logger | None = None
) -> float:
    """Normalize a confidence value to a finite float within [0.0, 1.0].

    Args:
        value: Raw confidence value (may be any type)
        default: Default value if value is None or invalid
        log: Optional logger for debug messages

    Returns:
        Float clamped between 0.0 and 1.0
    """
    if value is None:
        if log:
            log.debug("Confidence missing; defaulting to %s", default)
        return default

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        if log:
            log.debug("Invalid confidence %r; defaulting to %s", value, default)
        return default

    if not math.isfinite(confidence):
        if log:
            log.debug("Non-finite confidence %r; defaulting to %s", value, default)
        return default

    return max(0.0, min(1.0, confidence))
