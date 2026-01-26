"""
Two-tier Redis cache for confidence scoring system.

Provides score cache (short TTL) and calculation cache (long TTL)
with graceful degradation and selective invalidation.

Includes distributed locking to prevent race conditions during
cache invalidation and score recalculation.
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional
from redis.asyncio import Redis
from services.confidence.models import RelationshipData, ReviewData
from services.confidence.config import CacheConfig
from datetime import datetime

from redis.asyncio import Redis

from services.confidence.config import CacheConfig
from services.confidence.models import RelationshipData, ReviewData


logger = logging.getLogger(__name__)


class CacheManager:
    """Two-tier Redis cache for confidence calculations"""

    # Default lock timeout for distributed locking (seconds)
    DEFAULT_LOCK_TIMEOUT = 10

    # Lock key prefix
    LOCK_KEY_PREFIX = "confidence:lock:"

    def __init__(self, redis_client: Redis, config: CacheConfig = None, *, lock_timeout: int = None):
        """
        Initialize cache manager.

        Args:
            redis_client: Redis async client instance
            config: Cache configuration (uses defaults if None)
            lock_timeout: Timeout for distributed locks in seconds (default: 10)
        """
        self.redis = redis_client
        self.config = config or CacheConfig()
        self.lock_timeout = lock_timeout or self.DEFAULT_LOCK_TIMEOUT

    # Score cache methods
    async def get_cached_score(self, concept_id: str) -> float | None:
        """
        Retrieve cached confidence score.

        Args:
            concept_id: Concept identifier

        Returns:
            Cached score if found, None otherwise
        """
        try:
            key = f"{self.config.SCORE_KEY_PREFIX}{concept_id}"
            value = await self.redis.get(key)

            if value is None:
                logger.debug(f"Score cache miss: {concept_id}")
                return None

            logger.debug(f"Score cache hit: {concept_id}")
            return float(value)

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None  # Graceful degradation

    async def set_cached_score(self, concept_id: str, score: float, ttl: int | None = None):
        """
        Store confidence score in cache.

        Args:
            concept_id: Concept identifier
            score: Confidence score (0.0-1.0)
            ttl: Time-to-live in seconds (uses config default if None)
        """
        try:
            key = f"{self.config.SCORE_KEY_PREFIX}{concept_id}"
            ttl = ttl or self.config.SCORE_CACHE_TTL

            await self.redis.set(key, score, ex=ttl)
            logger.debug(f"Cached score: {concept_id} = {score} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            # Don't raise - caching is optional

    # Calculation cache methods
    async def get_cached_relationships(self, concept_id: str) -> RelationshipData | None:
        """
        Retrieve cached relationship data.

        Args:
            concept_id: Concept identifier

        Returns:
            RelationshipData if cached, None otherwise
        """
        try:
            key = f"{self.config.CALC_RELATIONSHIP_PREFIX}{concept_id}"
            value = await self.redis.get(key)

            if value is None:
                logger.debug(f"Relationship cache miss: {concept_id}")
                return None

            data = json.loads(value)
            logger.debug(f"Relationship cache hit: {concept_id}")
            return RelationshipData(**data)

        except Exception as e:
            logger.error(f"Cache get relationships error: {e}")
            return None

    async def set_cached_relationships(
        self, concept_id: str, data: RelationshipData, ttl: int | None = None
    ):
        """
        Store relationship data in cache.

        Args:
            concept_id: Concept identifier
            data: Relationship data to cache
            ttl: Time-to-live in seconds (uses config default if None)
        """
        try:
            key = f"{self.config.CALC_RELATIONSHIP_PREFIX}{concept_id}"
            ttl = ttl or self.config.CALC_CACHE_TTL

            # Serialize to JSON
            value = json.dumps(
                {
                    "total_relationships": data.total_relationships,
                    "relationship_types": data.relationship_types,
                    "connected_concept_ids": data.connected_concept_ids,
                }
            )

            await self.redis.set(key, value, ex=ttl)
            logger.debug(f"Cached relationships: {concept_id} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache set relationships error: {e}")

    async def get_cached_review_history(self, concept_id: str) -> ReviewData | None:
        """
        Retrieve cached review history.

        Args:
            concept_id: Concept identifier

        Returns:
            ReviewData if cached, None otherwise
        """
        try:
            key = f"{self.config.CALC_REVIEW_PREFIX}{concept_id}"
            value = await self.redis.get(key)

            if value is None:
                logger.debug(f"Review cache miss: {concept_id}")
                return None

            data = json.loads(value)
            # Parse datetime from ISO string
            data["last_reviewed_at"] = datetime.fromisoformat(data["last_reviewed_at"])
            logger.debug(f"Review cache hit: {concept_id}")
            return ReviewData(**data)

        except Exception as e:
            logger.error(f"Cache get review error: {e}")
            return None

    async def set_cached_review_history(
        self, concept_id: str, data: ReviewData, ttl: int | None = None
    ):
        """
        Store review history in cache.

        Args:
            concept_id: Concept identifier
            data: Review data to cache
            ttl: Time-to-live in seconds (uses config default if None)
        """
        try:
            key = f"{self.config.CALC_REVIEW_PREFIX}{concept_id}"
            ttl = ttl or self.config.CALC_CACHE_TTL

            value = json.dumps(
                {
                    "last_reviewed_at": data.last_reviewed_at.isoformat(),
                    "days_since_review": data.days_since_review,
                    "review_count": data.review_count,
                }
            )

            await self.redis.set(key, value, ex=ttl)
            logger.debug(f"Cached review history: {concept_id} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache set review error: {e}")

    # Invalidation methods
    async def invalidate_concept_cache(
        self, concept_id: str, invalidate_score: bool = True, invalidate_calc: bool = True
    ):
        """
        Selectively invalidate cache entries for concept.

        Args:
            concept_id: Concept to invalidate
            invalidate_score: Clear score cache (default: True)
            invalidate_calc: Clear calculation cache (default: True)
        """
        try:
            keys_to_delete = []

            if invalidate_score:
                keys_to_delete.append(f"{self.config.SCORE_KEY_PREFIX}{concept_id}")

            if invalidate_calc:
                keys_to_delete.append(f"{self.config.CALC_RELATIONSHIP_PREFIX}{concept_id}")
                keys_to_delete.append(f"{self.config.CALC_REVIEW_PREFIX}{concept_id}")

            if keys_to_delete:
                deleted_count = await self.redis.delete(*keys_to_delete)
                logger.info(f"Invalidated {deleted_count} cache keys for {concept_id}")

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def invalidate_score_cache(self, concept_id: str):
        """
        Convenience method to invalidate only score cache.

        Args:
            concept_id: Concept to invalidate
        """
        await self.invalidate_concept_cache(
            concept_id, invalidate_score=True, invalidate_calc=False
        )

    # Health check
    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is available, False otherwise
        """
        try:
            await self.redis.ping()
            logger.debug("Redis health check: OK")
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    # Distributed locking
    @asynccontextmanager
    async def concept_lock(self, concept_id: str) -> Any:
        """
        Acquire distributed lock for concept operations using Redis SETNX.

        This prevents race conditions during cache invalidation and score
        recalculation by ensuring only one operation runs at a time for
        a given concept.

        Usage:
            async with cache.concept_lock(concept_id) as acquired:
                if acquired:
                    # Perform invalidate -> calculate -> persist atomically
                    await invalidate()
                    result = await calculate()
                    await persist(result)
                else:
                    # Lock held by another process, skip or retry
                    pass

        Args:
            concept_id: The concept to lock

        Yields:
            True if lock was acquired, False if lock is held by another process
        """
        lock_key = f"{self.LOCK_KEY_PREFIX}{concept_id}"
        lock_value = str(uuid.uuid4())
        acquired = False

        # Try to acquire lock
        try:
            acquired = await self.redis.set(
                lock_key,
                lock_value,
                nx=True,
                ex=self.lock_timeout,
            )
        except Exception as e:
            logger.error(f"Error acquiring lock for {concept_id}: {e}")
            acquired = False

        if acquired:
            logger.debug(f"Acquired lock for concept {concept_id}")
        else:
            logger.debug(f"Lock already held for concept {concept_id}")

        try:
            yield bool(acquired)
        finally:
            if acquired:
                # Use Lua script for atomic check-and-delete to avoid deleting
                # a lock acquired by another process after ours expired
                release_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                try:
                    await self.redis.eval(release_script, 1, lock_key, lock_value)
                    logger.debug(f"Released lock for concept {concept_id}")
                except Exception as e:
                    logger.warning(f"Failed to release lock for {concept_id}: {e}")
