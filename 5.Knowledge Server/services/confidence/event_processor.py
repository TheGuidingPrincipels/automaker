"""Event processor for the confidence scoring system."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime

from services.confidence.cache_manager import CacheManager
from services.confidence.models import Error
from services.confidence.retention_calculator import RetentionCalculator
from services.confidence.scheduler import Priority, RecalculationScheduler


logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], Awaitable[None]]


class EventProcessor:
    """Simple observer-pattern event processor with typed handlers."""

    def __init__(
        self,
        cache_manager: CacheManager,
        scheduler: RecalculationScheduler,
        retention_calculator: RetentionCalculator,
        *,
        register_default_handlers: bool = True,
    ) -> None:
        self.cache_manager = cache_manager
        self.scheduler = scheduler
        self.retention_calculator = retention_calculator

        self.handlers: defaultdict[str, list[EventHandler]] = defaultdict(list)

        if register_default_handlers:
            self._register_builtin_handlers()

    # Public API -----------------------------------------------------------------
    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register an asynchronous handler for the supplied event type."""
        if not event_type:
            raise ValueError("event_type cannot be empty")
        if not callable(handler):
            raise TypeError("handler must be awaitable")

        self.handlers[event_type].append(handler)
        logger.debug("Registered handler for event type %s", event_type)

    async def emit(self, event: dict) -> None:
        """Emit event to all registered handlers."""
        event_type = event.get("type")
        if not event_type:
            logger.warning("Event missing 'type' field, ignoring")
            return

        handlers = self.handlers.get(event_type, [])
        if not handlers:
            logger.debug("No handlers registered for event type %s", event_type)
            return

        # Ensure event has timestamp for auditing
        event.setdefault("timestamp", datetime.utcnow().isoformat())

        logger.info(
            "Processing event %s for concept %s",
            event_type,
            event.get("concept_id"),
        )

        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error("Handler error for %s: %s", event_type, exc, exc_info=True)

    async def process_event(self, event: dict) -> None:
        """
        Process event after validating required structure.

        Raises:
            ValueError: if required fields are missing
        """
        self._validate_event(event)
        await self.emit(event)

    # Internal helpers -----------------------------------------------------------
    def _register_builtin_handlers(self) -> None:
        """Register builtin handlers for core event types."""
        self.register_handler("concept.updated", self._handle_concept_updated)
        self.register_handler("relationship.created", self._handle_relationship_changed)
        self.register_handler("relationship.deleted", self._handle_relationship_changed)
        self.register_handler("review.completed", self._handle_review_completed)

    @staticmethod
    def _validate_event(event: dict) -> None:
        required_fields = ("type", "concept_id")
        missing = [field for field in required_fields if field not in event]
        if missing:
            raise ValueError(f"Event missing required fields: {', '.join(missing)}")

    # Builtin handlers -----------------------------------------------------------
    async def _handle_concept_updated(self, event: dict) -> None:
        concept_id = event["concept_id"]

        await self.cache_manager.invalidate_concept_cache(concept_id)
        await self.scheduler.schedule_recalculation(concept_id, priority=Priority.MEDIUM)

        logger.info("Queued recalculation for updated concept %s", concept_id)

    async def _handle_relationship_changed(self, event: dict) -> None:
        concept_id = event["concept_id"]
        related_concept_id = event.get("related_concept_id")

        if not related_concept_id:
            logger.warning("Relationship event missing related_concept_id; event: %s", event)
            return

        await self.cache_manager.invalidate_concept_cache(
            concept_id,
            invalidate_score=False,
            invalidate_calc=True,
        )
        await self.cache_manager.invalidate_concept_cache(
            related_concept_id,
            invalidate_score=False,
            invalidate_calc=True,
        )

        await self.scheduler.schedule_recalculation(concept_id, priority=Priority.HIGH)
        await self.scheduler.schedule_recalculation(related_concept_id, priority=Priority.HIGH)

        logger.info(
            "Queued recalculation for relationship %s ↔ %s",
            concept_id,
            related_concept_id,
        )

    async def _handle_review_completed(self, event: dict) -> None:
        concept_id = event["concept_id"]

        update_result = await self.retention_calculator.update_retention_tau(concept_id)
        if isinstance(update_result, Error):
            logger.error(
                "Retention tau update failed for %s: %s",
                concept_id,
                update_result.message,
            )

        await self.cache_manager.invalidate_score_cache(concept_id)
        await self.scheduler.schedule_recalculation(concept_id, priority=Priority.LOW)

        logger.info("Processed review completion for %s", concept_id)
