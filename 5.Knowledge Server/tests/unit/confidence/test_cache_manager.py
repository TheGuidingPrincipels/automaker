"""
Unit tests for CacheManager with mocked Redis client.

Tests cache operations, serialization, invalidation, and error handling.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from services.confidence.cache_manager import CacheManager
from services.confidence.config import CacheConfig
from services.confidence.models import RelationshipData, ReviewData


@pytest.fixture
def mock_redis_client():
    """Mock Redis async client"""
    client = Mock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.ping = AsyncMock(return_value=True)
    client.info = AsyncMock(return_value={})
    return client


@pytest.fixture
def cache_config():
    """Test cache configuration"""
    return CacheConfig()


@pytest.mark.asyncio
async def test_get_cached_score_with_cache_hit_returns_score(mock_redis_client, cache_config):
    """Cache hit should return cached score"""
    mock_redis_client.get.return_value = "0.85"

    cache = CacheManager(mock_redis_client, cache_config)
    score = await cache.get_cached_score("c1")

    assert score == 0.85
    mock_redis_client.get.assert_called_once_with("confidence:score:c1")


@pytest.mark.asyncio
async def test_get_cached_score_with_cache_miss_returns_none(mock_redis_client, cache_config):
    """Cache miss should return None"""
    mock_redis_client.get.return_value = None

    cache = CacheManager(mock_redis_client, cache_config)
    score = await cache.get_cached_score("c1")

    assert score is None


@pytest.mark.asyncio
async def test_set_cached_score_stores_value_with_ttl(mock_redis_client, cache_config):
    """Should store score with correct TTL"""
    cache = CacheManager(mock_redis_client, cache_config)
    await cache.set_cached_score("c1", 0.92, ttl=3600)

    mock_redis_client.set.assert_called_once_with("confidence:score:c1", 0.92, ex=3600)


@pytest.mark.asyncio
async def test_set_cached_score_uses_default_ttl(mock_redis_client, cache_config):
    """Should use config default TTL when not specified"""
    cache = CacheManager(mock_redis_client, cache_config)
    await cache.set_cached_score("c1", 0.88)

    # Should use default SCORE_CACHE_TTL from config
    mock_redis_client.set.assert_called_once_with(
        "confidence:score:c1", 0.88, ex=3600  # default from CacheConfig
    )


@pytest.mark.asyncio
async def test_get_cached_relationships_deserializes_json(mock_redis_client, cache_config):
    """Should deserialize RelationshipData from JSON"""
    relationship_json = json.dumps(
        {
            "total_relationships": 5,
            "relationship_types": {"RELATES_TO": 3, "DEPENDS_ON": 2},
            "connected_concept_ids": ["c2", "c3", "c4"],
        }
    )
    mock_redis_client.get.return_value = relationship_json

    cache = CacheManager(mock_redis_client, cache_config)
    data = await cache.get_cached_relationships("c1")

    assert data.total_relationships == 5
    assert data.relationship_types["RELATES_TO"] == 3
    assert len(data.connected_concept_ids) == 3


@pytest.mark.asyncio
async def test_get_cached_relationships_returns_none_on_cache_miss(mock_redis_client, cache_config):
    """Should return None when relationship data not cached"""
    mock_redis_client.get.return_value = None

    cache = CacheManager(mock_redis_client, cache_config)
    data = await cache.get_cached_relationships("c1")

    assert data is None


@pytest.mark.asyncio
async def test_set_cached_relationships_serializes_to_json(mock_redis_client, cache_config):
    """Should serialize RelationshipData to JSON"""
    relationship_data = RelationshipData(
        total_relationships=3,
        relationship_types={"RELATES_TO": 2, "DEPENDS_ON": 1},
        connected_concept_ids=["c2", "c3"],
    )

    cache = CacheManager(mock_redis_client, cache_config)
    await cache.set_cached_relationships("c1", relationship_data)

    # Verify JSON serialization
    call_args = mock_redis_client.set.call_args
    stored_value = call_args[0][1]
    deserialized = json.loads(stored_value)
    assert deserialized["total_relationships"] == 3
    assert deserialized["relationship_types"]["RELATES_TO"] == 2


@pytest.mark.asyncio
async def test_get_cached_review_history_deserializes_datetime(mock_redis_client, cache_config):
    """Should deserialize ReviewData with datetime from ISO string"""
    now = datetime.now()
    review_json = json.dumps(
        {"last_reviewed_at": now.isoformat(), "days_since_review": 5, "review_count": 3}
    )
    mock_redis_client.get.return_value = review_json

    cache = CacheManager(mock_redis_client, cache_config)
    data = await cache.get_cached_review_history("c1")

    assert data.days_since_review == 5
    assert data.review_count == 3
    assert isinstance(data.last_reviewed_at, datetime)


@pytest.mark.asyncio
async def test_set_cached_review_history_serializes_datetime(mock_redis_client, cache_config):
    """Should serialize ReviewData with datetime to ISO string"""
    now = datetime.now()
    review_data = ReviewData(last_reviewed_at=now, days_since_review=5, review_count=3)

    cache = CacheManager(mock_redis_client, cache_config)
    await cache.set_cached_review_history("c1", review_data)

    # Verify datetime serialization
    call_args = mock_redis_client.set.call_args
    stored_value = call_args[0][1]
    deserialized = json.loads(stored_value)
    assert "last_reviewed_at" in deserialized
    # ISO format should be parseable
    datetime.fromisoformat(deserialized["last_reviewed_at"])


@pytest.mark.asyncio
async def test_invalidate_concept_cache_deletes_all_keys(mock_redis_client, cache_config):
    """Should delete score and calculation cache keys"""
    cache = CacheManager(mock_redis_client, cache_config)
    await cache.invalidate_concept_cache("c1")

    # Should delete 3 keys: score, relationships, review
    assert mock_redis_client.delete.call_count == 1
    # Check all keys passed to delete
    call_args = mock_redis_client.delete.call_args[0]
    assert len(call_args) == 3
    assert "confidence:score:c1" in call_args
    assert "confidence:calc:relationships:c1" in call_args
    assert "confidence:calc:review:c1" in call_args


@pytest.mark.asyncio
async def test_invalidate_concept_cache_with_selective_score_only(mock_redis_client, cache_config):
    """Should selectively delete only score cache"""
    cache = CacheManager(mock_redis_client, cache_config)
    await cache.invalidate_concept_cache("c1", invalidate_score=True, invalidate_calc=False)

    # Should delete only score key
    mock_redis_client.delete.assert_called_once()
    call_args = mock_redis_client.delete.call_args[0]
    assert len(call_args) == 1
    assert call_args[0] == "confidence:score:c1"


@pytest.mark.asyncio
async def test_invalidate_concept_cache_with_selective_calc_only(mock_redis_client, cache_config):
    """Should selectively delete only calculation cache"""
    cache = CacheManager(mock_redis_client, cache_config)
    await cache.invalidate_concept_cache("c1", invalidate_score=False, invalidate_calc=True)

    # Should delete 2 calc keys
    call_args = mock_redis_client.delete.call_args[0]
    assert len(call_args) == 2
    assert "confidence:calc:relationships:c1" in call_args
    assert "confidence:calc:review:c1" in call_args


@pytest.mark.asyncio
async def test_invalidate_score_cache_convenience_method(mock_redis_client, cache_config):
    """Convenience method should invalidate only score"""
    cache = CacheManager(mock_redis_client, cache_config)
    await cache.invalidate_score_cache("c1")

    call_args = mock_redis_client.delete.call_args[0]
    assert len(call_args) == 1
    assert call_args[0] == "confidence:score:c1"


@pytest.mark.asyncio
async def test_cache_handles_redis_connection_failure_gracefully(mock_redis_client, cache_config):
    """Redis failure should not raise exception (return None)"""
    mock_redis_client.get.side_effect = Exception("Connection refused")

    cache = CacheManager(mock_redis_client, cache_config)
    score = await cache.get_cached_score("c1")

    assert score is None  # Graceful degradation


@pytest.mark.asyncio
async def test_cache_set_handles_redis_failure_gracefully(mock_redis_client, cache_config):
    """Redis failure on set should not raise exception"""
    mock_redis_client.set.side_effect = Exception("Connection refused")

    cache = CacheManager(mock_redis_client, cache_config)
    # Should not raise exception
    await cache.set_cached_score("c1", 0.85)


@pytest.mark.asyncio
async def test_health_check_returns_true_when_redis_available(mock_redis_client, cache_config):
    """Health check should ping Redis and return True"""
    mock_redis_client.ping.return_value = True

    cache = CacheManager(mock_redis_client, cache_config)
    is_healthy = await cache.health_check()

    assert is_healthy is True
    mock_redis_client.ping.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_returns_false_when_redis_unavailable(mock_redis_client, cache_config):
    """Health check should return False when Redis ping fails"""
    mock_redis_client.ping.side_effect = Exception("Connection refused")

    cache = CacheManager(mock_redis_client, cache_config)
    is_healthy = await cache.health_check()

    assert is_healthy is False


# Tests for concept_lock (distributed locking for race condition prevention)

@pytest.mark.asyncio
async def test_concept_lock_acquires_lock_successfully(mock_redis_client, cache_config):
    """concept_lock should acquire lock and yield True when lock is available"""
    mock_redis_client.set.return_value = True  # SETNX succeeds
    mock_redis_client.eval = AsyncMock(return_value=1)  # Lock release succeeds

    cache = CacheManager(mock_redis_client, cache_config)
    async with cache.concept_lock("concept-123") as acquired:
        assert acquired is True
        # Verify set was called with NX and EX options
        mock_redis_client.set.assert_called_once()
        call_kwargs = mock_redis_client.set.call_args
        assert call_kwargs[1]["nx"] is True  # Only set if not exists
        assert call_kwargs[1]["ex"] == cache.lock_timeout

    # Verify lock was released via Lua script
    mock_redis_client.eval.assert_called_once()


@pytest.mark.asyncio
async def test_concept_lock_fails_when_lock_held(mock_redis_client, cache_config):
    """concept_lock should yield False when another process holds the lock"""
    mock_redis_client.set.return_value = False  # SETNX fails (lock held)

    cache = CacheManager(mock_redis_client, cache_config)
    async with cache.concept_lock("concept-123") as acquired:
        assert acquired is False

    # Verify no release was attempted (lock not acquired)
    mock_redis_client.eval.assert_not_called()


@pytest.mark.asyncio
async def test_concept_lock_uses_correct_key_prefix(mock_redis_client, cache_config):
    """concept_lock should use the LOCK_KEY_PREFIX for lock keys"""
    mock_redis_client.set.return_value = True
    mock_redis_client.eval = AsyncMock(return_value=1)

    cache = CacheManager(mock_redis_client, cache_config)
    async with cache.concept_lock("my-concept-id") as acquired:
        assert acquired is True

    # Check the lock key has the correct prefix
    call_args = mock_redis_client.set.call_args[0]
    lock_key = call_args[0]
    assert lock_key == "confidence:lock:my-concept-id"


@pytest.mark.asyncio
async def test_concept_lock_handles_redis_error_gracefully(mock_redis_client, cache_config):
    """concept_lock should yield False and not raise on Redis errors"""
    mock_redis_client.set.side_effect = Exception("Redis connection failed")

    cache = CacheManager(mock_redis_client, cache_config)
    async with cache.concept_lock("concept-123") as acquired:
        assert acquired is False

    # Should handle error gracefully without raising


@pytest.mark.asyncio
async def test_concept_lock_releases_even_on_exception(mock_redis_client, cache_config):
    """concept_lock should release lock even if exception occurs inside context"""
    mock_redis_client.set.return_value = True
    mock_redis_client.eval = AsyncMock(return_value=1)

    cache = CacheManager(mock_redis_client, cache_config)

    with pytest.raises(ValueError):
        async with cache.concept_lock("concept-123") as acquired:
            assert acquired is True
            raise ValueError("Simulated error inside lock")

    # Lock should still be released
    mock_redis_client.eval.assert_called_once()


@pytest.mark.asyncio
async def test_concept_lock_uses_custom_lock_timeout(mock_redis_client, cache_config):
    """concept_lock should use custom lock_timeout if specified"""
    mock_redis_client.set.return_value = True
    mock_redis_client.eval = AsyncMock(return_value=1)

    cache = CacheManager(mock_redis_client, cache_config, lock_timeout=30)
    async with cache.concept_lock("concept-123") as acquired:
        assert acquired is True

    # Verify the custom timeout was used
    call_kwargs = mock_redis_client.set.call_args[1]
    assert call_kwargs["ex"] == 30


@pytest.mark.asyncio
async def test_concept_lock_lua_script_checks_owner(mock_redis_client, cache_config):
    """concept_lock release should use Lua script to check ownership before delete"""
    mock_redis_client.set.return_value = True
    mock_redis_client.eval = AsyncMock(return_value=1)

    cache = CacheManager(mock_redis_client, cache_config)
    async with cache.concept_lock("concept-123") as acquired:
        assert acquired is True

    # Verify eval was called with the Lua script and correct arguments
    call_args = mock_redis_client.eval.call_args
    lua_script = call_args[0][0]
    assert "redis.call(\"get\", KEYS[1])" in lua_script
    assert "redis.call(\"del\", KEYS[1])" in lua_script
    # Check key count argument (second positional arg)
    assert call_args[0][1] == 1
    # Check the lock key (third arg)
    assert call_args[0][2] == "confidence:lock:concept-123"
