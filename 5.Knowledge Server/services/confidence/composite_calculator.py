"""Composite confidence score calculator."""

from __future__ import annotations

import logging

from services.confidence.config import ConfidenceConfig
from services.confidence.models import Error, ErrorCode, Success
from services.confidence.retention_calculator import RetentionCalculator
from services.confidence.understanding_calculator import UnderstandingCalculator


logger = logging.getLogger(__name__)


class CompositeCalculator:
    """Combine understanding and retention scores into a composite score."""

    def __init__(
        self,
        understanding_calculator: UnderstandingCalculator,
        retention_calculator: RetentionCalculator,
    ) -> None:
        config = ConfidenceConfig()

        self.understanding_calc = understanding_calculator
        self.retention_calc = retention_calculator
        self.understanding_weight = config.UNDERSTANDING_WEIGHT
        self.retention_weight = config.RETENTION_WEIGHT

    async def calculate_composite_score(self, concept_id: str) -> Success | Error:
        """Calculate composite score with weighted combination of sub-scores."""

        try:
            understanding_result = await self.understanding_calc.calculate_understanding_score(
                concept_id
            )
            if isinstance(understanding_result, Error):
                return understanding_result

            retention_result = await self.retention_calc.calculate_retention_score(concept_id)
            if isinstance(retention_result, Error):
                return retention_result

            composite_score = (
                self.understanding_weight * understanding_result.value
                + self.retention_weight * retention_result.value
            )

            # Defensive clamp: Component scores are already [0,1], but weights
            # may not sum to exactly 1.0 due to misconfiguration. This ensures
            # the composite score remains valid regardless of weight settings.
            composite_score = max(0.0, min(1.0, composite_score))

            logger.debug(
                "Composite score calculated",
                extra={
                    "concept_id": concept_id,
                    "understanding": understanding_result.value,
                    "retention": retention_result.value,
                    "composite": composite_score,
                },
            )

            return Success(composite_score)

        except Exception as exc:  # pragma: no cover - defensive catch
            logger.error("Composite score calculation error: %s", exc, exc_info=True)
            return Error(
                f"Failed to calculate composite score: {exc}",
                ErrorCode.DATABASE_ERROR,
            )
