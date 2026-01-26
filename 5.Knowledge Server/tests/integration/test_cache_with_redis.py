"""
Integration tests for CacheManager with real Redis instance.

Tests cache operations against actual Redis server (requires Redis running).
"""

import asyncio
from datetime import datetime

import pytest
import redis.asyncio as redis

from services.confidence.cache_manager import CacheManager
from services.confidence.config import CacheConfig
from services.confidence.models import RelationshipData, ReviewData


@pytest.fixture
async def redis_client():
    """Provide real Redis client for integration testing"""
    try:
        # Use DB 15 for tests to avoid conflicts
        client = redis.Redis(
            host="localhost", port=6379, db=15, decode_responses=True, socket_connect_timeout=2
        )
        # Test connection
        await client.ping()
        yield client
        # Cleanup
        await client.flushdb()
        await client.close()
    except (redis.ConnectionError, redis.TimeoutError) as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.fixture
def cache_config():
    """Test cache configuration"""
    config = CacheConfig()
    config.REDIS_DB = 15  # Use test database
    return config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_score_cache_roundtrip(redis_client, cache_config):
    """Store and retrieve score from real Redis"""
    cache = CacheManager(redis_client, cache_config)

    await cache.set_cached_score("test-c1", 0.88)
    retrieved = await cache.get_cached_score("test-c1")

    assert retrieved == 0.88


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_ttl_expiration(redis_client, cache_config):
    """Score should expire after TTL"""
    cache = CacheManager(redis_client, cache_config)

    # Set with 1 second TTL
    await cache.set_cached_score("test-c2", 0.75, ttl=1)

    # Immediate retrieval should work
    assert await cache.get_cached_score("test-c2") == 0.75

    # Wait for expiration
    await asyncio.sleep(2)

    # Should be expired
    assert await cache.get_cached_score("test-c2") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalidation_removes_keys(redis_client, cache_config):
    """Invalidation should remove all cached data"""
    cache = CacheManager(redis_client, cache_config)

    # Cache score and relationships
    await cache.set_cached_score("test-c3", 0.90)
    await cache.set_cached_relationships(
        "test-c3",
        RelationshipData(
            total_relationships=5,
            relationship_types={"RELATES_TO": 5},
            connected_concept_ids=["c1", "c2", "c3", "c4", "c5"],
        ),
    )

    # Verify cached
    assert await cache.get_cached_score("test-c3") == 0.90
    assert await cache.get_cached_relationships("test-c3") is not None

    # Invalidate
    await cache.invalidate_concept_cache("test-c3")

    # Verify removed
    assert await cache.get_cached_score("test-c3") is None
    assert await cache.get_cached_relationships("test-c3") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_cache_operations(redis_client, cache_config):
    """Multiple concurrent operations should not interfere"""
    cache = CacheManager(redis_client, cache_config)

    # Concurrent writes
    await asyncio.gather(
        cache.set_cached_score("c1", 0.1),
        cache.set_cached_score("c2", 0.2),
        cache.set_cached_score("c3", 0.3),
        cache.set_cached_score("c4", 0.4),
        cache.set_cached_score("c5", 0.5),
    )

    # Concurrent reads
    scores = await asyncio.gather(
        cache.get_cached_score("c1"),
        cache.get_cached_score("c2"),
        cache.get_cached_score("c3"),
        cache.get_cached_score("c4"),
        cache.get_cached_score("c5"),
    )

    assert scores == [0.1, 0.2, 0.3, 0.4, 0.5]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_relationship_data_roundtrip(redis_client, cache_config):
    """RelationshipData should serialize/deserialize correctly"""
    cache = CacheManager(redis_client, cache_config)

    relationship_data = RelationshipData(
        total_relationships=10,
        relationship_types={"RELATES_TO": 6, "DEPENDS_ON": 4},
        connected_concept_ids=["c1", "c2", "c3", "c4", "c5"],
    )

    await cache.set_cached_relationships("test-c6", relationship_data)
    retrieved = await cache.get_cached_relationships("test-c6")

    assert retrieved.total_relationships == 10
    assert retrieved.relationship_types["RELATES_TO"] == 6
    assert retrieved.relationship_types["DEPENDS_ON"] == 4
    assert len(retrieved.connected_concept_ids) == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_data_roundtrip(redis_client, cache_config):
    """ReviewData with datetime should serialize/deserialize correctly"""
    cache = CacheManager(redis_client, cache_config)

    now = datetime.now()
    review_data = ReviewData(last_reviewed_at=now, days_since_review=7, review_count=5)

    await cache.set_cached_review_history("test-c7", review_data)
    retrieved = await cache.get_cached_review_history("test-c7")

    assert retrieved.days_since_review == 7
    assert retrieved.review_count == 5
    # Datetime comparison (allow microsecond differences)
    assert abs((retrieved.last_reviewed_at - now).total_seconds()) < 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_selective_invalidation_score_only(redis_client, cache_config):
    """Should invalidate only score cache, preserve calculation cache"""
    cache = CacheManager(redis_client, cache_config)

    # Cache both
    await cache.set_cached_score("test-c8", 0.85)
    await cache.set_cached_relationships(
        "test-c8",
        RelationshipData(
            total_relationships=3,
            relationship_types={"RELATES_TO": 3},
            connected_concept_ids=["c1", "c2", "c3"],
        ),
    )

    # Invalidate score only
    await cache.invalidate_concept_cache("test-c8", invalidate_score=True, invalidate_calc=False)

    # Score should be gone
    assert await cache.get_cached_score("test-c8") is None
    # Relationships should still be there
    assert await cache.get_cached_relationships("test-c8") is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check_with_live_redis(redis_client, cache_config):
    """Health check should return True for live Redis"""
    cache = CacheManager(redis_client, cache_config)

    is_healthy = await cache.health_check()

    assert is_healthy is True
