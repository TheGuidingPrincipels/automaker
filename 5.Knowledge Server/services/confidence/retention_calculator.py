"""Retention score calculator using an exponential decay model."""

from __future__ import annotations

import logging
import math

from services.confidence.cache_manager import CacheManager
from services.confidence.config import ConfidenceConfig
from services.confidence.data_access import DataAccessLayer
from services.confidence.models import Error, ErrorCode, ReviewData, Success
from services.confidence.tau_event_emitter import (
    NoOpTauEventEmitter,
    TauEventEmitterProtocol,
)


logger = logging.getLogger(__name__)


class RetentionCalculator:
    """Calculate retention score using a simplified FSRS exponential decay model."""

    def __init__(
        self,
        data_access: DataAccessLayer,
        cache_manager: CacheManager,
        *,
        tau: Optional[int] = None,
        tau_multiplier: Optional[float] = None,
        max_tau: Optional[int] = None,
        tau_event_emitter: Optional[TauEventEmitterProtocol] = None,
    ) -> None:
        config = ConfidenceConfig()

        self.data_access = data_access
        self.cache = cache_manager
        self.default_tau = tau or config.DEFAULT_TAU_DAYS
        self.tau_multiplier = tau_multiplier or config.TAU_MULTIPLIER
        self.max_tau = max_tau or config.MAX_TAU_DAYS
        # Event emitter for tau updates (uses event sourcing pattern)
        # If not provided, uses NoOp emitter which logs a warning
        self._tau_emitter = tau_event_emitter or NoOpTauEventEmitter()

    async def calculate_retention_score(
        self,
        concept_id: str,
        tau: int | None = None,
    ) -> Success | Error:
        """Calculate retention score using exponential decay e^(-(days / τ))."""

        try:
            review_data = await self._get_review_history(concept_id)
            if isinstance(review_data, Error):
                return review_data

            tau_value = tau if tau is not None else await self._resolve_tau(concept_id)
            if isinstance(tau_value, Error):
                return tau_value
            tau_value = max(1, int(tau_value))
            days = max(0, review_data.days_since_review)

            retention_score = math.exp(-(days / tau_value))
            retention_score = max(0.0, min(1.0, retention_score))

            logger.debug(
                "Retention score computed",
                extra={
                    "concept_id": concept_id,
                    "days_since_review": days,
                    "tau": tau_value,
                    "retention_score": retention_score,
                },
            )

            return Success(retention_score)

        except Exception as exc:  # pragma: no cover - defensive catch
            logger.error("Retention score calculation error: %s", exc, exc_info=True)
            return Error(
                f"Failed to calculate retention score: {exc}",
                ErrorCode.DATABASE_ERROR,
            )

    async def update_retention_tau(
        self,
        concept_id: str,
        *,
        review_completed: bool = True,
    ) -> Union[Success, Error]:
        """
        Update tau parameter after a review interaction.

        Uses the event sourcing pattern: emits a ConceptTauUpdated event
        which is processed by the Neo4j projection.

        Args:
            concept_id: The concept to update
            review_completed: Whether a review was actually completed

        Returns:
            Success with the new tau value
            Error if the update failed
        """

        if not review_completed:
            # No update required; return current or default tau for consistency
            current = await self.data_access.get_concept_tau(concept_id)
            return current if isinstance(current, Success) else Success(self.default_tau)

        try:
            # Get current tau value (for calculating new value and audit trail)
            current_tau_result = await self.data_access.get_concept_tau(concept_id)
            if isinstance(current_tau_result, Error):
                current_tau = self.default_tau
            else:
                current_tau = current_tau_result.value

            # Calculate new tau value
            new_tau = max(1, int(round(current_tau * self.tau_multiplier)))
            new_tau = min(new_tau, self.max_tau)

            # Emit event through the event sourcing pipeline
            # This replaces the direct write to data_access
            emit_result = self._tau_emitter.emit_tau_updated(
                concept_id=concept_id,
                new_tau=new_tau,
                previous_tau=current_tau,
            )

            if isinstance(emit_result, Error):
                return emit_result

            # Invalidate review cache to ensure fresh calculations next time
            try:
                await self.cache.invalidate_concept_cache(
                    concept_id,
                    invalidate_score=False,
                    invalidate_calc=True,
                )
            except Exception as cache_exc:  # pragma: no cover - optional
                logger.warning(
                    "Failed to invalidate review cache for %s: %s",
                    concept_id,
                    cache_exc,
                )

            logger.debug(
                "Updated retention tau via event sourcing",
                extra={
                    "concept_id": concept_id,
                    "previous_tau": current_tau,
                    "new_tau": new_tau,
                },
            )

            return Success(new_tau)

        except Exception as exc:  # pragma: no cover - defensive catch
            logger.error("Tau update error: %s", exc, exc_info=True)
            return Error(
                f"Failed to update tau: {exc}",
                ErrorCode.DATABASE_ERROR,
            )

    async def _get_review_history(self, concept_id: str) -> ReviewData | Error:
        """Retrieve review history using cache with graceful degradation."""

        cached = await self.cache.get_cached_review_history(concept_id)
        if cached:
            return cached

        result = await self.data_access.get_review_history(concept_id)
        if isinstance(result, Error):
            return result

        review_data = result.value
        try:
            await self.cache.set_cached_review_history(concept_id, review_data)
        except Exception as cache_exc:  # pragma: no cover - optional
            logger.warning(
                "Failed to cache review history for %s: %s",
                concept_id,
                cache_exc,
            )

        return review_data

    async def _resolve_tau(self, concept_id: str) -> int | Error:
        tau_result = await self.data_access.get_concept_tau(concept_id)
        if isinstance(tau_result, Error):
            if tau_result.code == ErrorCode.NOT_FOUND:
                return tau_result
            return self.default_tau
        return tau_result.value
