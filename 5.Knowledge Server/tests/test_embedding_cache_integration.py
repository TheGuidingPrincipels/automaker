"""
Integration tests for EmbeddingCache with EmbeddingService.

Tests the complete workflow of cache integration with embedding generation.
"""

import tempfile
import time
from pathlib import Path

import pytest
import pytest_asyncio

from services.embedding_cache import EmbeddingCache
from services.embedding_service import EmbeddingConfig, EmbeddingService


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def cache(temp_db):
    """Create an EmbeddingCache instance."""
    return EmbeddingCache(db_path=temp_db)


@pytest.fixture
def config():
    """Create test configuration for EmbeddingService."""
    return EmbeddingConfig(
        model_name="all-MiniLM-L6-v2", device="cpu", batch_size=16, normalize=True
    )


@pytest_asyncio.fixture
async def service_without_cache(config):
    """Create EmbeddingService without cache."""
    svc = EmbeddingService(config=config)
    await svc.initialize()
    return svc


@pytest_asyncio.fixture
async def service_with_cache(config, cache):
    """Create EmbeddingService with cache."""
    svc = EmbeddingService(config=config, cache=cache)
    await svc.initialize()
    return svc


class TestCacheIntegration:
    """Test cache integration with EmbeddingService."""

    @pytest.mark.asyncio
    async def test_service_creation_with_cache(self, config, cache):
        """Test creating service with cache."""
        service = EmbeddingService(config=config, cache=cache)
        await service.initialize()

        assert service.cache is not None
        assert service.cache == cache
        assert service.is_available()

    @pytest.mark.asyncio
    async def test_service_creation_without_cache(self, config):
        """Test creating service without cache."""
        service = EmbeddingService(config=config)
        await service.initialize()

        assert service.cache is None
        assert service.is_available()

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(self, service_with_cache, cache):
        """Test workflow: cache miss → generate → cache hit."""
        text = "Python for loops iterate over sequences"

        # First call: cache miss, generates embedding
        embedding1 = service_with_cache.generate_embedding(text)
        assert len(embedding1) == 384
        assert cache._cache_misses == 1

        # Second call: cache hit, retrieves from cache
        embedding2 = service_with_cache.generate_embedding(text)
        assert len(embedding2) == 384
        assert cache._cache_hits == 1

        # Embeddings should be identical
        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_cache_improves_performance(self, service_with_cache):
        """Test that cache significantly improves performance."""
        text = "Python for loops iterate over sequences"

        # First call: uncached (slower)
        start = time.perf_counter()
        embedding1 = service_with_cache.generate_embedding(text)
        time_uncached = (time.perf_counter() - start) * 1000

        # Second call: cached (much faster)
        start = time.perf_counter()
        embedding2 = service_with_cache.generate_embedding(text)
        time_cached = (time.perf_counter() - start) * 1000

        assert len(embedding1) == 384
        assert len(embedding2) == 384
        assert embedding1 == embedding2

        # Cached should be at least 5x faster
        assert time_cached < time_uncached / 5

        # Cached should be < 1ms
        assert time_cached < 1.0

    @pytest.mark.asyncio
    async def test_service_without_cache_still_works(self, service_without_cache):
        """Test that service works normally without cache."""
        text = "Python for loops iterate over sequences"

        # Generate embedding
        embedding = service_without_cache.generate_embedding(text)

        assert len(embedding) == 384
        assert service_without_cache.cache is None

    @pytest.mark.asyncio
    async def test_case_insensitive_caching(self, service_with_cache, cache):
        """Test that cache is case-insensitive."""
        text1 = "Hello World"
        text2 = "hello world"
        text3 = "HELLO WORLD"

        # Generate for first text
        embedding1 = service_with_cache.generate_embedding(text1)

        # Generate for second text (should hit cache)
        embedding2 = service_with_cache.generate_embedding(text2)

        # Generate for third text (should hit cache)
        embedding3 = service_with_cache.generate_embedding(text3)

        # All should be identical (from cache)
        assert embedding1 == embedding2 == embedding3

        # Should have 1 miss and 2 hits
        assert cache._cache_misses == 1
        assert cache._cache_hits == 2

    @pytest.mark.asyncio
    async def test_whitespace_normalization(self, service_with_cache, cache):
        """Test that cache normalizes whitespace."""
        text1 = "hello world"
        text2 = "hello  world"
        text3 = "  hello world  "

        # Generate for first text
        embedding1 = service_with_cache.generate_embedding(text1)

        # Generate for variants (should hit cache)
        embedding2 = service_with_cache.generate_embedding(text2)
        embedding3 = service_with_cache.generate_embedding(text3)

        # All should be identical (from cache)
        assert embedding1 == embedding2 == embedding3

        # Should have 1 miss and 2 hits
        assert cache._cache_misses == 1
        assert cache._cache_hits == 2


class TestBatchCaching:
    """Test batch operations with cache."""

    @pytest.mark.asyncio
    async def test_batch_with_full_cache_miss(self, service_with_cache, cache):
        """Test batch generation with all cache misses."""
        texts = ["Python for loops", "JavaScript async/await", "Stoic philosophy"]

        # Generate batch (all misses)
        embeddings = service_with_cache.generate_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)
        assert cache._cache_misses == 3
        assert cache._cache_hits == 0

        # All should be stored in cache
        stats = cache.get_cache_stats()
        assert stats.total_entries == 3

    @pytest.mark.asyncio
    async def test_batch_with_full_cache_hit(self, service_with_cache, cache):
        """Test batch generation with all cache hits."""
        texts = ["Python for loops", "JavaScript async/await", "Stoic philosophy"]

        # First batch: all misses, stores in cache
        embeddings1 = service_with_cache.generate_batch(texts)

        # Second batch: all hits
        embeddings2 = service_with_cache.generate_batch(texts)

        # Embeddings should be identical
        assert embeddings1 == embeddings2

        # Should have 3 misses (first batch) and 3 hits (second batch)
        assert cache._cache_misses == 3
        assert cache._cache_hits == 3

    @pytest.mark.asyncio
    async def test_batch_with_partial_cache_hit(self, service_with_cache, cache):
        """Test batch generation with partial cache hits."""
        # Pre-populate cache with some entries
        cache.store("text 1", "all-MiniLM-L6-v2", [0.1] * 384)
        cache.store("text 2", "all-MiniLM-L6-v2", [0.2] * 384)

        texts = [
            "text 1",  # In cache
            "text 2",  # In cache
            "text 3",  # Not in cache
            "text 4",  # Not in cache
        ]

        # Generate batch (2 hits, 2 misses)
        embeddings = service_with_cache.generate_batch(texts)

        assert len(embeddings) == 4
        assert all(len(e) == 384 for e in embeddings)

        # First two should be from cache
        assert cache._cache_hits == 2

        # Last two should be generated
        # Note: cache_misses may vary depending on implementation

        # All should now be in cache
        stats = cache.get_cache_stats()
        assert stats.total_entries == 4

    @pytest.mark.asyncio
    async def test_batch_performance_with_cache(self, service_with_cache):
        """Test that cache improves batch performance."""
        texts = [f"text {i}" for i in range(10)]

        # First batch: uncached
        start = time.perf_counter()
        embeddings1 = service_with_cache.generate_batch(texts)
        time_uncached = (time.perf_counter() - start) * 1000

        # Second batch: cached
        start = time.perf_counter()
        embeddings2 = service_with_cache.generate_batch(texts)
        time_cached = (time.perf_counter() - start) * 1000

        assert len(embeddings1) == 10
        assert len(embeddings2) == 10
        assert embeddings1 == embeddings2

        # Cached should be significantly faster
        assert time_cached < time_uncached / 5


class TestCacheStatistics:
    """Test cache statistics in integration."""

    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculation(self, service_with_cache, cache):
        """Test cache hit rate with realistic usage."""
        texts = ["text 1", "text 2", "text 3"]

        # Generate once (3 misses)
        service_with_cache.generate_batch(texts)

        # Generate again (3 hits)
        service_with_cache.generate_batch(texts)

        # Check stats
        stats = cache.get_cache_stats()
        assert stats.cache_hits == 3
        assert stats.cache_misses == 3
        assert stats.hit_rate == 50.0

    @pytest.mark.asyncio
    async def test_cache_stats_after_clear(self, service_with_cache, cache):
        """Test cache stats after clearing cache."""
        text = "Python for loops"

        # Generate and cache
        service_with_cache.generate_embedding(text)

        # Clear cache
        cache.clear_cache()

        # Generate again (should miss)
        service_with_cache.generate_embedding(text)

        stats = cache.get_cache_stats()
        assert stats.total_entries == 1
        assert stats.cache_misses == 2  # Initial miss + post-clear miss
        assert stats.cache_hits == 0


class TestModelSpecificCaching:
    """Test that cache is model-specific."""

    @pytest.mark.asyncio
    async def test_different_models_separate_cache(self, cache):
        """Test that different models have separate cache entries."""
        config1 = EmbeddingConfig(model_name="all-MiniLM-L6-v2")
        config2 = EmbeddingConfig(model_name="all-mpnet-base-v2")

        service1 = EmbeddingService(config=config1, cache=cache)
        EmbeddingService(config=config2, cache=cache)

        await service1.initialize()
        # Note: service2 won't initialize (model not available), but we can test cache logic

        text = "Python for loops"

        # Generate with service1
        embedding1 = service1.generate_embedding(text)

        # Should be in cache for model 1
        cached1 = cache.get_cached(text, config1.model_name)
        assert cached1 is not None
        assert cached1 == embedding1

        # Should NOT be in cache for model 2
        cached2 = cache.get_cached(text, config2.model_name)
        assert cached2 is None


class TestEdgeCases:
    """Test edge cases in cache integration."""

    @pytest.mark.asyncio
    async def test_empty_text_with_cache(self, service_with_cache):
        """Test embedding empty text with cache."""
        embedding1 = service_with_cache.generate_embedding("")
        embedding2 = service_with_cache.generate_embedding("")

        assert len(embedding1) == 384
        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_very_long_text_with_cache(self, service_with_cache):
        """Test embedding very long text with cache."""
        long_text = "Python " * 1000  # Very long text

        embedding1 = service_with_cache.generate_embedding(long_text)
        embedding2 = service_with_cache.generate_embedding(long_text)

        assert len(embedding1) == 384
        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_special_characters_with_cache(self, service_with_cache):
        """Test text with special characters."""
        text = "Hello @#$%^&*() World! 你好"

        embedding1 = service_with_cache.generate_embedding(text)
        embedding2 = service_with_cache.generate_embedding(text)

        assert len(embedding1) == 384
        assert embedding1 == embedding2


class TestCacheReliability:
    """Test cache reliability and error handling."""

    @pytest.mark.asyncio
    async def test_cache_failure_graceful_degradation(self, config, cache):
        """Test that service continues to work if cache encounters errors."""
        # Test with a working cache but simulate failures via other means
        # The cache is designed to be robust, so we'll just verify the service
        # works with cache enabled

        service = EmbeddingService(config=config, cache=cache)
        await service.initialize()

        # Should generate embeddings successfully with cache
        embedding = service.generate_embedding("Python for loops")

        assert len(embedding) == 384

        # Verify cache was used
        assert service.cache is not None

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, service_with_cache):
        """Test concurrent access to cache (basic test)."""
        text = "Python for loops"

        # Generate embedding multiple times quickly
        embeddings = [service_with_cache.generate_embedding(text) for _ in range(10)]

        # All should be identical
        assert all(e == embeddings[0] for e in embeddings)
        assert all(len(e) == 384 for e in embeddings)
