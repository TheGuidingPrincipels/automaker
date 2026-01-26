"""Asynchronous scheduler for confidence score recalculations."""

from __future__ import annotations

import heapq
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any

from redis.asyncio import Redis

from services.confidence.cache_manager import CacheManager
from services.confidence.composite_calculator import CompositeCalculator
from services.confidence.models import Error


logger = logging.getLogger(__name__)


class Priority(Enum):
    """Priority levels for recalculation scheduling."""

    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class QueueEntry:
    """Internal representation of a queue entry."""

    priority: int
    timestamp: float
    concept_id: str

    def as_tuple(self) -> tuple[int, float, str]:
        """Return value suitable for heap operations."""
        return (self.priority, self.timestamp, self.concept_id)


class RecalculationScheduler:
    """Manage queued recalculations with Redis-backed locking."""

    def __init__(
        self,
        composite_calculator: CompositeCalculator,
        cache_manager: CacheManager,
        redis_client: Redis,
        *,
        batch_window_seconds: float = 5.0,
        lock_timeout: int = 10,
    ) -> None:
        self.calculator = composite_calculator
        self.cache = cache_manager
        self.redis = redis_client
        self.batch_window_seconds = batch_window_seconds
        self.lock_timeout = lock_timeout

        self._queue: list[tuple[int, float, str]] = []
        self._pending: dict[str, QueueEntry] = {}

    async def schedule_recalculation(
        self,
        concept_id: str,
        priority: Priority = Priority.MEDIUM,
    ) -> None:
        """
        Add concept to recalculation queue with deduplication.

        If the concept is already queued with a lower priority (higher numeric value),
        the priority is upgraded.
        """
        if not concept_id:
            logger.warning("Attempted to schedule recalculation with empty concept_id")
            return

        timestamp = time.time()
        priority_value = priority.value

        existing = self._pending.get(concept_id)
        if existing:
            if priority_value >= existing.priority:
                logger.debug(
                    "Concept %s already queued with priority %s; skipping duplicate",
                    concept_id,
                    Priority(existing.priority).name,
                )
                return
            logger.debug(
                "Upgrading priority for %s from %s to %s",
                concept_id,
                Priority(existing.priority).name,
                priority.name,
            )

        entry = QueueEntry(priority_value, timestamp, concept_id)
        self._pending[concept_id] = entry
        heapq.heappush(self._queue, entry.as_tuple())
        logger.info("Scheduled recalculation for %s (priority: %s)", concept_id, priority.name)

    async def get_queue_size(self) -> int:
        """Return number of pending concepts (deduplicated)."""
        return len(self._pending)

    async def clear_queue(self) -> None:
        """Clear all pending recalculations (testing helper)."""
        self._queue.clear()
        self._pending.clear()

    async def process_queue(self) -> None:
        """
        Process queued recalculations.

        Concepts are processed in priority order with batching inside the configured window.
        """
        while self._queue:
            priority_value, timestamp, concept_id = heapq.heappop(self._queue)

            # Skip stale entries (e.g., replaced due to priority upgrade)
            entry = self._pending.get(concept_id)
            if not entry or (entry.priority, entry.timestamp) != (priority_value, timestamp):
                continue

            # Prepare batch for same priority within time window
            batch_cutoff = timestamp + self.batch_window_seconds
            batch = [concept_id]
            del self._pending[concept_id]

            while self._queue:
                next_priority, next_timestamp, next_concept_id = self._queue[0]
                next_entry = self._pending.get(next_concept_id)

                # Clean up stale entries
                if not next_entry or (next_entry.priority, next_entry.timestamp) != (
                    next_priority,
                    next_timestamp,
                ):
                    heapq.heappop(self._queue)
                    continue

                if next_priority != priority_value or next_timestamp > batch_cutoff:
                    break

                heapq.heappop(self._queue)
                batch.append(next_concept_id)
                del self._pending[next_concept_id]

            for concept in batch:
                await self.process_recalculation(concept)

    @asynccontextmanager
    async def concept_lock(self, concept_id: str) -> Any:
        """
        Acquire distributed lock for concept recalculation using Redis SETNX.

        Yields True if lock acquired, False otherwise.
        """
        lock_key = f"confidence:lock:{concept_id}"
        lock_value = str(uuid.uuid4())
        acquired = False
        try:
            acquired = await self.redis.set(
                lock_key,
                lock_value,
                nx=True,
                ex=self.lock_timeout,
            )
            if acquired:
                logger.debug("Acquired lock for %s", concept_id)
                yield True
            else:
                logger.debug("Lock already held for %s", concept_id)
                yield False
        finally:
            if acquired:
                release_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                try:
                    await self.redis.eval(release_script, 1, lock_key, lock_value)
                    logger.debug("Released lock for %s", concept_id)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Failed to release lock for %s: %s", concept_id, exc)

    async def process_recalculation(self, concept_id: str) -> None:
        """Recalculate confidence score with distributed locking."""
        async with self.concept_lock(concept_id) as acquired:
            if not acquired:
                logger.warning("Skipping recalculation for %s (lock held)", concept_id)
                return

            try:
                result = await self.calculator.calculate_composite_score(concept_id)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Recalculation failed for %s: %s", concept_id, exc, exc_info=True)
                return

            if isinstance(result, Error):
                logger.error(
                    "Composite calculation returned error for %s: %s",
                    concept_id,
                    result.message,
                )
                return

            try:
                await self.cache.set_cached_score(concept_id, result.value)
                logger.info("Updated cached score for %s", concept_id)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to cache recalculated score for %s: %s", concept_id, exc)
