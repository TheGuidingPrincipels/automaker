"""
Advanced edge case tests for EmbeddingService.

Tests extreme scenarios, memory leaks, threading, resource cleanup,
and edge cases not covered by standard unit tests.
"""

import asyncio
import gc
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

import numpy as np
import pytest
import pytest_asyncio

from services.embedding_service import EmbeddingConfig, EmbeddingService


@pytest_asyncio.fixture
async def service():
    """Create and initialize embedding service."""
    svc = EmbeddingService()
    await svc.initialize()
    return svc


class TestExtremeEdgeCases:
    """Test extreme edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_extremely_long_text_10k_chars(self, service):
        """Test with 10,000 character text."""
        long_text = "a" * 10000

        embedding = service.generate_embedding(long_text)

        # Should handle gracefully (truncate and process)
        assert len(embedding) == 384
        assert not all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_extremely_long_text_100k_chars(self, service):
        """Test with 100,000 character text."""
        long_text = "b" * 100000

        embedding = service.generate_embedding(long_text)

        # Should handle gracefully
        assert len(embedding) == 384
        assert not all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_unicode_emoji_text(self, service):
        """Test with unicode emoji characters."""
        emoji_text = "🐍 Python for loops 🔄 iterate over sequences 📝"

        embedding = service.generate_embedding(emoji_text)

        assert len(embedding) == 384
        assert not all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_unicode_multilingual_text(self, service):
        """Test with multilingual unicode text."""
        multilingual = "Python 파이썬 パイソン Питон للحلقات बन्द चक्र"

        embedding = service.generate_embedding(multilingual)

        assert len(embedding) == 384
        assert not all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_special_characters_only(self, service):
        """Test with only special characters."""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"

        embedding = service.generate_embedding(special)

        # Should return embedding for special chars
        assert len(embedding) == 384

    @pytest.mark.asyncio
    async def test_null_bytes_in_text(self, service):
        """Test with null bytes in text."""
        null_text = "Python\x00for\x00loops"

        # Should handle without crashing
        embedding = service.generate_embedding(null_text)

        assert len(embedding) == 384

    @pytest.mark.asyncio
    async def test_control_characters(self, service):
        """Test with various control characters."""
        control_text = "Python\x01\x02\x03for\x04\x05loops"

        embedding = service.generate_embedding(control_text)

        assert len(embedding) == 384

    @pytest.mark.asyncio
    async def test_repeated_whitespace_combinations(self, service):
        """Test various whitespace combinations."""
        whitespace_variants = [
            "   ",  # spaces
            "\t\t\t",  # tabs
            "\n\n\n",  # newlines
            "\r\r\r",  # carriage returns
            " \t\n\r ",  # mixed
            "\u00a0\u00a0",  # non-breaking spaces
        ]

        for ws in whitespace_variants:
            embedding = service.generate_embedding(ws)
            # Should return zero vector for whitespace-only
            assert all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_empty_string_variants(self, service):
        """Test various empty string representations."""
        empty_variants = ["", None, "   ", "\n", "\t", "\r\n"]

        for variant in empty_variants:
            if variant is None:
                # Skip None for direct call
                continue
            embedding = service.generate_embedding(variant)
            assert len(embedding) == 384

    @pytest.mark.asyncio
    async def test_very_large_batch_1000_items(self, service):
        """Test batch with 1000 items."""
        texts = [f"concept {i}" for i in range(1000)]

        start = time.time()
        embeddings = service.generate_batch(texts)
        elapsed = time.time() - start

        assert len(embeddings) == 1000
        assert all(len(e) == 384 for e in embeddings)

        # Should complete in reasonable time (< 10 seconds)
        assert elapsed < 10.0, f"Batch took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_batch_with_mixed_lengths(self, service):
        """Test batch with extremely varied text lengths."""
        texts = [
            "short",
            "a" * 100,
            "b" * 1000,
            "c" * 10000,
            "",
            "   ",
            "normal text here",
            "d" * 50000,
        ]

        embeddings = service.generate_batch(texts)

        assert len(embeddings) == 8
        assert all(len(e) == 384 for e in embeddings)

    @pytest.mark.asyncio
    async def test_batch_all_empty_strings(self, service):
        """Test batch with all empty strings."""
        texts = ["", "  ", "\n", "\t", "   \n\t   "] * 10

        embeddings = service.generate_batch(texts)

        assert len(embeddings) == 50
        # All should be zero vectors
        assert all(all(x == 0.0 for x in e) for e in embeddings)


class TestMemoryLeaks:
    """Test for memory leaks and resource management."""

    @pytest.mark.asyncio
    async def test_repeated_embedding_generation_memory(self, service):
        """Test for memory leaks during repeated embedding generation."""
        import tracemalloc

        # Start memory tracking
        tracemalloc.start()
        gc.collect()

        # Get baseline
        initial_snapshot = tracemalloc.take_snapshot()

        # Generate many embeddings
        for i in range(1000):
            embedding = service.generate_embedding(f"test text number {i}")
            assert len(embedding) == 384

        gc.collect()

        # Get final snapshot
        final_snapshot = tracemalloc.take_snapshot()

        # Check memory growth
        top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")

        # Get total memory increase
        total_increase = sum(stat.size_diff for stat in top_stats)

        # Should not grow excessively (allow 10MB for caching)
        assert (
            total_increase < 10 * 1024 * 1024
        ), f"Memory grew by {total_increase / 1024 / 1024:.2f} MB"

        tracemalloc.stop()

    @pytest.mark.asyncio
    async def test_batch_processing_memory_cleanup(self, service):
        """Test memory cleanup during batch processing."""
        import tracemalloc

        tracemalloc.start()
        gc.collect()

        initial_snapshot = tracemalloc.take_snapshot()

        # Process multiple large batches
        for batch_num in range(10):
            texts = [f"batch {batch_num} text {i}" for i in range(100)]
            embeddings = service.generate_batch(texts)
            assert len(embeddings) == 100
            # Explicitly delete to encourage cleanup
            del embeddings
            gc.collect()

        final_snapshot = tracemalloc.take_snapshot()
        top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")
        total_increase = sum(stat.size_diff for stat in top_stats)

        # Memory should not grow significantly (allow 20MB)
        assert (
            total_increase < 20 * 1024 * 1024
        ), f"Memory grew by {total_increase / 1024 / 1024:.2f} MB"

        tracemalloc.stop()

    @pytest.mark.asyncio
    async def test_service_object_size(self, service):
        """Test that service object doesn't grow unexpectedly."""
        initial_size = sys.getsizeof(service)

        # Generate many embeddings
        for i in range(100):
            service.generate_embedding(f"text {i}")

        final_size = sys.getsizeof(service)

        # Service object size should not grow
        assert final_size == initial_size, f"Service size grew from {initial_size} to {final_size}"


class TestConcurrency:
    """Test concurrent access and threading issues."""

    @pytest.mark.asyncio
    async def test_concurrent_single_embeddings(self, service):
        """Test concurrent single embedding generation."""

        def generate_embedding(text):
            return service.generate_embedding(text)

        # Generate 50 embeddings concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(generate_embedding, f"concurrent text {i}") for i in range(50)
            ]

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # All should succeed
        assert len(results) == 50
        assert all(len(e) == 384 for e in results)
        assert all(not all(x == 0.0 for x in e) for e in results)

    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self, service):
        """Test concurrent batch processing."""

        def process_batch(batch_id):
            texts = [f"batch {batch_id} text {i}" for i in range(20)]
            return service.generate_batch(texts)

        # Process 10 batches concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_batch, i) for i in range(10)]

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # All batches should succeed
        assert len(results) == 10
        assert all(len(batch) == 20 for batch in results)
        assert all(all(len(e) == 384 for e in batch) for batch in results)

    @pytest.mark.asyncio
    async def test_race_condition_initialization(self):
        """Test race conditions during initialization."""
        services = [EmbeddingService() for _ in range(5)]

        async def init_service(svc):
            return await svc.initialize()

        # Initialize all concurrently
        results = await asyncio.gather(*[init_service(s) for s in services])

        # All should initialize successfully
        assert all(results)
        assert all(s.is_available() for s in services)

    @pytest.mark.asyncio
    async def test_thread_safety_model_access(self, service):
        """Test thread safety of model access."""
        errors = []

        def access_model():
            try:
                for _ in range(10):
                    embedding = service.generate_embedding("test")
                    assert len(embedding) == 384
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_model) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0, f"Errors: {errors}"


class TestResourceCleanup:
    """Test resource cleanup and graceful degradation."""

    @pytest.mark.asyncio
    async def test_model_deletion_behavior(self):
        """Test behavior when model is deleted."""
        service = EmbeddingService()
        await service.initialize()

        # Delete the model
        service.model = None
        service._model_available = False

        # Should fall back to zero vectors
        embedding = service.generate_embedding("test")
        assert all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_service_reinitialization(self):
        """Test reinitializing service multiple times."""
        service = EmbeddingService()

        # Initialize multiple times
        for i in range(5):
            result = await service.initialize()
            assert result is True
            assert service.is_available()

            # Generate embedding to verify it works
            embedding = service.generate_embedding(f"test {i}")
            assert len(embedding) == 384

    @pytest.mark.asyncio
    async def test_partial_initialization_failure_recovery(self):
        """Test recovery from partial initialization failure."""
        service = EmbeddingService()

        # Simulate partial failure during first init
        with patch.object(service, "_load_model", side_effect=Exception("Partial failure")):
            result1 = await service.initialize()
            assert result1 is False
            assert not service.is_available()

        # Now initialize properly (remove the mock)
        result2 = await service.initialize()

        # Should still be unavailable (can't re-init after failure)
        assert result2 is False
        assert not service.is_available()


class TestErrorTracing:
    """Test error handling with detailed traces."""

    @pytest.mark.asyncio
    async def test_model_encode_exception_trace(self, service):
        """Test exception trace when model.encode fails."""
        # Mock encode to raise detailed exception
        original_encode = service.model.encode

        def failing_encode(*args, **kwargs):
            raise ValueError("Custom encoding error with context")

        service.model.encode = failing_encode

        # Should log error and return zero vector
        embedding = service.generate_embedding("test")

        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)

        # Restore
        service.model.encode = original_encode

    @pytest.mark.asyncio
    async def test_batch_encoding_partial_failure(self, service):
        """Test batch encoding with partial failures."""
        call_count = [0]
        original_encode = service.model.encode

        def sometimes_failing_encode(texts, **kwargs):
            call_count[0] += 1
            # Fail on certain calls
            if call_count[0] % 3 == 0:
                raise RuntimeError("Intermittent failure")
            return original_encode(texts, **kwargs)

        service.model.encode = sometimes_failing_encode

        # Try batch processing
        texts = ["text 1", "text 2", "text 3"]
        embeddings = service.generate_batch(texts)

        # Should handle failure gracefully
        assert len(embeddings) == 3

        # Restore
        service.model.encode = original_encode


class TestPerformanceBoundaries:
    """Test performance at boundaries."""

    @pytest.mark.asyncio
    async def test_minimum_batch_size_performance(self, service):
        """Test performance with batch_size=1."""
        texts = [f"text {i}" for i in range(50)]

        start = time.time()
        embeddings = service.generate_batch(texts, batch_size=1)
        elapsed = time.time() - start

        assert len(embeddings) == 50
        # Even with batch_size=1, should complete reasonably (< 5s)
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_maximum_batch_size_performance(self, service):
        """Test performance with very large batch_size."""
        texts = [f"text {i}" for i in range(100)]

        start = time.time()
        embeddings = service.generate_batch(texts, batch_size=1000)
        elapsed = time.time() - start

        assert len(embeddings) == 100
        # Should be fast with large batch size
        assert elapsed < 3.0

    @pytest.mark.asyncio
    async def test_single_vs_batch_performance_comparison(self, service):
        """Compare single vs batch performance."""
        texts = [f"text {i}" for i in range(50)]

        # Single processing
        start = time.time()
        [service.generate_embedding(t) for t in texts]
        single_time = time.time() - start

        # Batch processing
        start = time.time()
        service.generate_batch(texts)
        batch_time = time.time() - start

        # Batch should be significantly faster
        assert (
            batch_time < single_time / 2
        ), f"Batch ({batch_time:.3f}s) not faster than single ({single_time:.3f}s)"


class TestNumericalStability:
    """Test numerical stability and edge cases."""

    @pytest.mark.asyncio
    async def test_normalization_numerical_stability(self, service):
        """Test normalization doesn't cause numerical issues."""
        # Generate many embeddings and check norms
        texts = [f"concept {i}" for i in range(100)]
        embeddings = service.generate_batch(texts)

        for i, embedding in enumerate(embeddings):
            norm = np.linalg.norm(embedding)
            # Should be very close to 1.0
            assert 0.99 < norm < 1.01, f"Embedding {i} has norm {norm}"

    @pytest.mark.asyncio
    async def test_consistent_results_same_input(self, service):
        """Test that same input produces consistent results."""
        text = "Python for loops iterate over sequences"

        # Generate same embedding multiple times
        embeddings = [service.generate_embedding(text) for _ in range(10)]

        # All should be identical (or very close due to floating point)
        first = embeddings[0]
        for emb in embeddings[1:]:
            assert np.allclose(emb, first, rtol=1e-5)

    @pytest.mark.asyncio
    async def test_batch_consistency_with_single(self, service):
        """Test batch and single generation produce same results."""
        texts = ["concept A", "concept B", "concept C"]

        # Generate via single
        single_embeddings = [service.generate_embedding(t) for t in texts]

        # Generate via batch
        batch_embeddings = service.generate_batch(texts)

        # Should match closely
        for single, batch in zip(single_embeddings, batch_embeddings, strict=False):
            assert np.allclose(single, batch, rtol=1e-5)


class TestConfigurationEdgeCases:
    """Test edge cases in configuration."""

    @pytest.mark.asyncio
    async def test_zero_max_text_length(self):
        """Test with max_text_length=0."""
        config = EmbeddingConfig(max_text_length=0)
        service = EmbeddingService(config=config)
        await service.initialize()

        embedding = service.generate_embedding("This should be truncated")

        # Should return zero vector (empty after truncation)
        assert all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_very_large_max_text_length(self):
        """Test with extremely large max_text_length."""
        config = EmbeddingConfig(max_text_length=1000000)
        service = EmbeddingService(config=config)
        await service.initialize()

        text = "word " * 10000  # 50k chars
        embedding = service.generate_embedding(text)

        # Should handle without issues
        assert len(embedding) == 384
        assert not all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_negative_batch_size(self):
        """Test with negative batch_size."""
        config = EmbeddingConfig(batch_size=-1)
        service = EmbeddingService(config=config)
        await service.initialize()

        texts = ["text 1", "text 2"]

        # Should handle gracefully (use default or raise error)
        try:
            embeddings = service.generate_batch(texts)
            # If it succeeds, verify results
            assert len(embeddings) == 2
        except ValueError:
            # Acceptable to raise error for invalid batch size
            pass
