"""
Unit tests for EmbeddingCache.

Tests cache operations, text normalization, hashing, statistics,
and performance.
"""

import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from services.embedding_cache import CacheStats, EmbeddingCache


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
    """Create an EmbeddingCache instance for testing."""
    return EmbeddingCache(db_path=temp_db)


@pytest.fixture
def sample_embedding():
    """Create a sample 384-dimensional embedding."""
    return [0.1] * 384


class TestEmbeddingCacheInitialization:
    """Test cache initialization."""

    def test_create_cache_default_path(self):
        """Test creating cache with default path."""
        cache = EmbeddingCache()
        assert cache.db_path == "./data/events.db"
        assert cache._cache_hits == 0
        assert cache._cache_misses == 0

    def test_create_cache_custom_path(self, temp_db):
        """Test creating cache with custom path."""
        cache = EmbeddingCache(db_path=temp_db)
        assert cache.db_path == temp_db

    def test_table_created_automatically(self, temp_db):
        """Test that embedding_cache table is created automatically."""
        EmbeddingCache(db_path=temp_db)

        # Verify table exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='embedding_cache'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "embedding_cache"


class TestCacheOperations:
    """Test basic cache operations."""

    def test_store_and_retrieve(self, cache, sample_embedding):
        """Test storing and retrieving an embedding."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # Store
        success = cache.store(text, model, sample_embedding)
        assert success is True

        # Retrieve
        cached = cache.get_cached(text, model)
        assert cached is not None
        assert len(cached) == 384
        assert cached == sample_embedding

    def test_cache_miss(self, cache):
        """Test cache miss for non-existent text."""
        cached = cache.get_cached("non-existent text", "all-MiniLM-L6-v2")
        assert cached is None

    def test_model_specific_caching(self, cache, sample_embedding):
        """Test that cache is model-specific."""
        text = "hello world"
        model1 = "all-MiniLM-L6-v2"
        model2 = "all-mpnet-base-v2"

        embedding1 = sample_embedding
        embedding2 = [0.2] * 384

        # Store for model 1
        cache.store(text, model1, embedding1)

        # Store for model 2
        cache.store(text, model2, embedding2)

        # Retrieve for model 1
        cached1 = cache.get_cached(text, model1)
        assert cached1 == embedding1

        # Retrieve for model 2
        cached2 = cache.get_cached(text, model2)
        assert cached2 == embedding2

    def test_update_existing_entry(self, cache, sample_embedding):
        """Test updating an existing cache entry."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # Store initial embedding
        embedding1 = sample_embedding
        cache.store(text, model, embedding1)

        # Update with new embedding
        embedding2 = [0.5] * 384
        cache.store(text, model, embedding2)

        # Retrieve should get updated embedding
        cached = cache.get_cached(text, model)
        assert cached == embedding2


class TestTextNormalization:
    """Test text normalization and hashing."""

    def test_whitespace_normalization(self, cache, sample_embedding):
        """Test that different whitespace results in same cache hit."""
        model = "all-MiniLM-L6-v2"

        # Store with normal spacing
        cache.store("hello world", model, sample_embedding)

        # Retrieve with extra whitespace
        cached1 = cache.get_cached("hello  world", model)
        assert cached1 is not None

        # Retrieve with leading/trailing whitespace
        cached2 = cache.get_cached("  hello world  ", model)
        assert cached2 is not None

    def test_case_normalization(self, cache, sample_embedding):
        """Test that case differences result in same cache hit."""
        model = "all-MiniLM-L6-v2"

        # Store with lowercase
        cache.store("hello world", model, sample_embedding)

        # Retrieve with uppercase
        cached1 = cache.get_cached("HELLO WORLD", model)
        assert cached1 is not None

        # Retrieve with mixed case
        cached2 = cache.get_cached("Hello World", model)
        assert cached2 is not None

    def test_empty_text_handling(self, cache, sample_embedding):
        """Test handling of empty text."""
        model = "all-MiniLM-L6-v2"

        # Store empty text
        success = cache.store("", model, sample_embedding)
        assert success is True

        # Retrieve empty text
        cached = cache.get_cached("", model)
        assert cached is not None

    def test_hash_computation(self, cache):
        """Test that hash computation is consistent."""
        text1 = "hello world"
        text2 = "HELLO WORLD"

        # Both should produce the same hash after normalization
        normalized1 = cache._normalize_text(text1)
        normalized2 = cache._normalize_text(text2)
        hash1 = cache._compute_hash(normalized1)
        hash2 = cache._compute_hash(normalized2)

        assert hash1 == hash2


class TestCacheClearing:
    """Test cache clearing operations."""

    def test_clear_specific_model(self, cache, sample_embedding):
        """Test clearing cache for a specific model."""
        text = "hello world"
        model1 = "all-MiniLM-L6-v2"
        model2 = "all-mpnet-base-v2"

        # Store for both models
        cache.store(text, model1, sample_embedding)
        cache.store(text, model2, sample_embedding)

        # Clear model 1
        deleted = cache.clear_cache(model1)
        assert deleted == 1

        # Model 1 should be cleared
        cached1 = cache.get_cached(text, model1)
        assert cached1 is None

        # Model 2 should still exist
        cached2 = cache.get_cached(text, model2)
        assert cached2 is not None

    def test_clear_entire_cache(self, cache, sample_embedding):
        """Test clearing entire cache."""
        model = "all-MiniLM-L6-v2"

        # Store multiple entries
        cache.store("text 1", model, sample_embedding)
        cache.store("text 2", model, sample_embedding)
        cache.store("text 3", model, sample_embedding)

        # Clear entire cache
        deleted = cache.clear_cache()
        assert deleted == 3

        # All should be cleared
        assert cache.get_cached("text 1", model) is None
        assert cache.get_cached("text 2", model) is None
        assert cache.get_cached("text 3", model) is None

    def test_clear_empty_cache(self, cache):
        """Test clearing an empty cache."""
        deleted = cache.clear_cache()
        assert deleted == 0


class TestCacheStatistics:
    """Test cache statistics tracking."""

    def test_cache_hit_tracking(self, cache, sample_embedding):
        """Test that cache hits are tracked correctly."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # Store
        cache.store(text, model, sample_embedding)

        # Initial stats
        initial_hits = cache._cache_hits

        # Hit the cache
        cache.get_cached(text, model)

        # Verify hit count increased
        assert cache._cache_hits == initial_hits + 1

    def test_cache_miss_tracking(self, cache):
        """Test that cache misses are tracked correctly."""
        initial_misses = cache._cache_misses

        # Try to get non-existent entry
        cache.get_cached("non-existent", "all-MiniLM-L6-v2")

        # Verify miss count increased
        assert cache._cache_misses == initial_misses + 1

    def test_cache_stats(self, cache, sample_embedding):
        """Test get_cache_stats method."""
        model = "all-MiniLM-L6-v2"

        # Store 3 entries
        cache.store("text 1", model, sample_embedding)
        cache.store("text 2", model, sample_embedding)
        cache.store("text 3", model, sample_embedding)

        # Hit cache twice
        cache.get_cached("text 1", model)
        cache.get_cached("text 2", model)

        # Miss once
        cache.get_cached("text 4", model)

        # Get stats
        stats = cache.get_cache_stats()

        assert isinstance(stats, CacheStats)
        assert stats.total_entries == 3
        assert stats.cache_hits == 2
        assert stats.cache_misses == 1
        assert stats.hit_rate == pytest.approx(66.67, rel=0.1)

    def test_cache_stats_empty_cache(self, cache):
        """Test stats for empty cache."""
        stats = cache.get_cache_stats()

        assert stats.total_entries == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.hit_rate == 0.0


class TestPerformance:
    """Test cache performance."""

    def test_retrieval_performance(self, cache, sample_embedding):
        """Test that cache retrieval is fast (<1ms target)."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # Store
        cache.store(text, model, sample_embedding)

        # Measure retrieval time
        start = time.perf_counter()
        cached = cache.get_cached(text, model)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        assert cached is not None
        assert elapsed < 1.0  # Should be < 1ms

    def test_storage_performance(self, cache, sample_embedding):
        """Test that cache storage is reasonably fast."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # Measure storage time
        start = time.perf_counter()
        success = cache.store(text, model, sample_embedding)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        assert success is True
        assert elapsed < 10.0  # Should be < 10ms

    def test_batch_retrieval_performance(self, cache, sample_embedding):
        """Test performance of multiple cache retrievals."""
        model = "all-MiniLM-L6-v2"

        # Store 100 entries
        for i in range(100):
            cache.store(f"text {i}", model, sample_embedding)

        # Measure batch retrieval time
        start = time.perf_counter()
        for i in range(100):
            cache.get_cached(f"text {i}", model)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        # Should be < 100ms total (< 1ms per retrieval)
        assert elapsed < 100.0


class TestErrorHandling:
    """Test error handling in cache operations."""

    def test_invalid_embedding_format(self, cache):
        """Test storing invalid embedding format."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # Try to store invalid embedding (not a list)
        cache.store(text, model, "invalid")
        # Should handle gracefully (may fail or succeed depending on JSON serialization)

    def test_corrupted_database_retrieval(self, cache, sample_embedding):
        """Test retrieval from cache with corrupted data."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # Store valid embedding
        cache.store(text, model, sample_embedding)

        # Manually corrupt the database entry
        conn = sqlite3.connect(cache.db_path, check_same_thread=False)
        cursor = conn.cursor()

        # Find the entry and corrupt it
        normalized = cache._normalize_text(text)
        text_hash = cache._compute_hash(normalized)

        cursor.execute(
            "UPDATE embedding_cache SET embedding = ? WHERE text_hash = ?",
            ("corrupted_json", text_hash),
        )
        conn.commit()
        conn.close()

        # Try to retrieve (should handle gracefully)
        cached = cache.get_cached(text, model)
        # Should return None or handle error gracefully
        assert cached is None or isinstance(cached, list)


class TestCacheWorkflow:
    """Test complete cache workflows."""

    def test_cache_miss_generate_store_hit(self, cache, sample_embedding):
        """Test the complete workflow: miss → generate → store → hit."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # First access: cache miss
        cached = cache.get_cached(text, model)
        assert cached is None
        assert cache._cache_misses == 1

        # Generate and store
        success = cache.store(text, model, sample_embedding)
        assert success is True

        # Second access: cache hit
        cached = cache.get_cached(text, model)
        assert cached is not None
        assert cached == sample_embedding
        assert cache._cache_hits == 1

    def test_multiple_texts_workflow(self, cache, sample_embedding):
        """Test workflow with multiple texts."""
        model = "all-MiniLM-L6-v2"
        texts = ["text 1", "text 2", "text 3"]

        # Store all texts
        for text in texts:
            cache.store(text, model, sample_embedding)

        # Retrieve all texts
        for text in texts:
            cached = cache.get_cached(text, model)
            assert cached is not None
            assert cached == sample_embedding

        # Check stats
        stats = cache.get_cache_stats()
        assert stats.total_entries == 3
        assert stats.cache_hits == 3
        assert stats.hit_rate == 100.0

    def test_cache_with_hash_retrieval(self, cache, sample_embedding):
        """Test get_cached_with_hash utility method."""
        text = "hello world"
        model = "all-MiniLM-L6-v2"

        # Store
        cache.store(text, model, sample_embedding)

        # Retrieve with hash
        cached, text_hash = cache.get_cached_with_hash(text, model)

        assert cached is not None
        assert cached == sample_embedding
        assert isinstance(text_hash, str)
        assert len(text_hash) == 64  # SHA256 produces 64-char hex string
