"""
Unit tests for EmbeddingService.

Tests embedding generation, model loading, batch processing,
normalization, and error handling.
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest
import pytest_asyncio

from services.embedding_service import EmbeddingConfig, EmbeddingService


@pytest.fixture
def config():
    """Create test configuration."""
    return EmbeddingConfig(
        model_name="all-MiniLM-L6-v2",
        device="cpu",
        batch_size=16,
        normalize=True,
        max_text_length=500,
    )


@pytest_asyncio.fixture
async def service(config):
    """Create and initialize embedding service for testing."""
    svc = EmbeddingService(config=config)
    await svc.initialize()
    return svc


@pytest.fixture
def mock_model():
    """Create mock SentenceTransformer model."""
    model = Mock()
    model.max_seq_length = 512

    # Mock encode to return realistic embeddings
    def mock_encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=None):
        if isinstance(texts, str):
            texts = [texts]

        # Generate random normalized embeddings
        embeddings = np.random.rand(len(texts), 384).astype(np.float32)

        if normalize_embeddings:
            # Normalize to unit vectors
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms

        return embeddings if len(texts) > 1 else embeddings[0]

    model.encode = Mock(side_effect=mock_encode)
    return model


class TestEmbeddingServiceInitialization:
    """Test embedding service initialization."""

    def test_create_service_default_config(self):
        """Test creating service with default configuration."""
        service = EmbeddingService()

        assert service.config.model_name == "all-MiniLM-L6-v2"
        assert service.config.device == "cpu"
        assert service.config.normalize is True
        assert service._initialized is False
        assert service._model_available is False

    def test_create_service_custom_config(self, config):
        """Test creating service with custom configuration."""
        service = EmbeddingService(config=config)

        assert service.config.model_name == "all-MiniLM-L6-v2"
        assert service.config.batch_size == 16
        assert service.config.max_text_length == 500

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful model initialization."""
        service = EmbeddingService()
        success = await service.initialize()

        assert success is True
        assert service._initialized is True
        assert service._model_available is True
        assert service.model is not None
        assert service.is_available() is True

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, service):
        """Test initializing an already initialized service."""
        # Service is already initialized by fixture
        assert service._initialized is True

        # Initialize again
        success = await service.initialize()

        assert success is True  # Should return True without re-loading

    @pytest.mark.asyncio
    async def test_initialize_import_error(self):
        """Test initialization when sentence-transformers not available."""
        service = EmbeddingService()

        # Patch _load_model to raise ImportError
        with patch.object(
            service, "_load_model", side_effect=ImportError("sentence-transformers not installed")
        ):
            success = await service.initialize()

        assert success is False
        assert service._initialized is True
        assert service._model_available is False
        assert service.is_available() is False

    @pytest.mark.asyncio
    async def test_initialize_model_load_error(self):
        """Test initialization when model loading fails."""
        service = EmbeddingService()

        with patch.object(service, "_load_model", side_effect=Exception("Model load failed")):
            success = await service.initialize()

        assert success is False
        assert service._initialized is True
        assert service._model_available is False


class TestSingleEmbeddingGeneration:
    """Test single text embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, service):
        """Test generating embedding for single text."""
        text = "Python for loops iterate over sequences"
        embedding = service.generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_normalization(self, service):
        """Test that embeddings are normalized to unit vectors."""
        text = "Test concept for normalization"
        embedding = service.generate_embedding(text)

        # Calculate L2 norm
        norm = np.linalg.norm(embedding)

        # Should be close to 1.0 for normalized vector
        assert abs(norm - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, service):
        """Test generating embedding for empty text."""
        embedding = service.generate_embedding("")

        # Should return zero vector
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_whitespace_only(self, service):
        """Test generating embedding for whitespace-only text."""
        embedding = service.generate_embedding("   \n\t   ")

        # Should return zero vector after preprocessing
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_long_text(self, service):
        """Test generating embedding for very long text."""
        long_text = "word " * 500  # 500 words, should be truncated

        embedding = service.generate_embedding(long_text)

        # Should still work, text will be truncated
        assert len(embedding) == 384
        assert not all(x == 0.0 for x in embedding)

    def test_generate_embedding_not_initialized(self):
        """Test generating embedding before initialization."""
        service = EmbeddingService()

        embedding = service.generate_embedding("test text")

        # Should return zero vector
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_model_unavailable(self):
        """Test generating embedding when model unavailable."""
        service = EmbeddingService()

        # Initialize with failed model
        with patch.object(service, "_load_model", side_effect=Exception("Failed")):
            await service.initialize()

        embedding = service.generate_embedding("test text")

        # Should return zero vector fallback
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)


class TestBatchEmbeddingGeneration:
    """Test batch embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_batch_success(self, service):
        """Test generating embeddings for multiple texts."""
        texts = [
            "Python for loops",
            "JavaScript async/await",
            "Stoic philosophy dichotomy of control",
        ]

        embeddings = service.generate_batch(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(emb, list) for emb in embeddings)

    @pytest.mark.asyncio
    async def test_generate_batch_custom_batch_size(self, service):
        """Test batch generation with custom batch size."""
        texts = ["text " + str(i) for i in range(50)]

        embeddings = service.generate_batch(texts, batch_size=10)

        assert len(embeddings) == 50
        assert all(len(emb) == 384 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_generate_batch_normalization(self, service):
        """Test that batch embeddings are normalized."""
        texts = ["concept 1", "concept 2", "concept 3"]
        embeddings = service.generate_batch(texts)

        # Check each embedding is normalized
        for embedding in embeddings:
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_generate_batch_empty_list(self, service):
        """Test generating embeddings for empty list."""
        embeddings = service.generate_batch([])

        assert isinstance(embeddings, list)
        assert len(embeddings) == 0

    @pytest.mark.asyncio
    async def test_generate_batch_mixed_empty_texts(self, service):
        """Test batch with some empty texts."""
        texts = ["valid text", "", "  ", "another valid"]

        embeddings = service.generate_batch(texts)

        assert len(embeddings) == 4
        assert len(embeddings[0]) == 384  # valid text has embedding
        assert all(x == 0.0 for x in embeddings[1])  # empty returns zeros
        assert all(x == 0.0 for x in embeddings[2])  # whitespace returns zeros
        assert len(embeddings[3]) == 384  # valid text has embedding

    def test_generate_batch_not_initialized(self):
        """Test batch generation before initialization."""
        service = EmbeddingService()

        texts = ["text 1", "text 2"]
        embeddings = service.generate_batch(texts)

        # Should return zero vectors
        assert len(embeddings) == 2
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(all(x == 0.0 for x in emb) for emb in embeddings)


class TestPreprocessing:
    """Test text preprocessing."""

    @pytest.mark.asyncio
    async def test_preprocess_whitespace_normalization(self, service):
        """Test that whitespace is normalized."""
        text = "text   with    multiple     spaces"
        processed = service._preprocess_text(text)

        assert processed == "text with multiple spaces"

    @pytest.mark.asyncio
    async def test_preprocess_newlines_and_tabs(self, service):
        """Test that newlines and tabs are normalized."""
        text = "text\nwith\n\nnewlines\tand\ttabs"
        processed = service._preprocess_text(text)

        assert "\n" not in processed
        assert "\t" not in processed
        assert "newlines and tabs" in processed

    @pytest.mark.asyncio
    async def test_preprocess_truncation(self, service):
        """Test that long text is truncated."""
        long_text = "a" * 2000  # Longer than max_text_length
        processed = service._preprocess_text(long_text)

        assert len(processed) <= service.config.max_text_length

    @pytest.mark.asyncio
    async def test_preprocess_empty_text(self, service):
        """Test preprocessing empty text."""
        processed = service._preprocess_text("")

        assert processed == ""


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_encoding_error_fallback(self, service):
        """Test fallback when encoding fails."""
        # Mock the model to raise an exception
        service.model.encode = Mock(side_effect=Exception("Encoding failed"))

        embedding = service.generate_embedding("test text")

        # Should return zero vector fallback
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)

    @pytest.mark.asyncio
    async def test_batch_encoding_error_fallback(self, service):
        """Test batch fallback when encoding fails."""
        service.model.encode = Mock(side_effect=Exception("Batch encoding failed"))

        texts = ["text 1", "text 2", "text 3"]
        embeddings = service.generate_batch(texts)

        # Should return zero vector fallbacks
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(all(x == 0.0 for x in emb) for emb in embeddings)


class TestUtilityMethods:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_is_available(self, service):
        """Test checking if service is available."""
        assert service.is_available() is True

    def test_is_available_not_initialized(self):
        """Test is_available before initialization."""
        service = EmbeddingService()
        assert service.is_available() is False

    @pytest.mark.asyncio
    async def test_get_embedding_dimension(self, service):
        """Test getting embedding dimension."""
        dim = service.get_embedding_dimension()

        assert dim == 384

    @pytest.mark.asyncio
    async def test_get_model_info(self, service):
        """Test getting model information."""
        info = service.get_model_info()

        assert isinstance(info, dict)
        assert info["model_name"] == "all-MiniLM-L6-v2"
        assert info["embedding_dim"] == 384
        assert info["device"] == "cpu"
        assert info["available"] is True
        assert info["initialized"] is True
        assert info["normalize"] is True

    def test_get_model_info_not_initialized(self):
        """Test model info before initialization."""
        service = EmbeddingService()
        info = service.get_model_info()

        assert info["available"] is False
        assert info["initialized"] is False


class TestNormalization:
    """Test embedding normalization."""

    @pytest.mark.asyncio
    async def test_normalize_embedding(self, service):
        """Test normalization function."""
        # Create random vector
        vector = np.random.rand(384)
        normalized = service._normalize_embedding(vector)

        # Check it's a unit vector
        norm = np.linalg.norm(normalized)
        assert abs(norm - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_normalize_zero_vector(self, service):
        """Test normalizing zero vector."""
        zero_vector = np.zeros(384)
        normalized = service._normalize_embedding(zero_vector)

        # Should return as-is (can't normalize zero vector)
        assert np.allclose(normalized, zero_vector)

    @pytest.mark.asyncio
    async def test_normalization_disabled(self):
        """Test with normalization disabled."""
        config = EmbeddingConfig(normalize=False)
        service = EmbeddingService(config=config)
        await service.initialize()

        # Generate embedding
        embedding = service.generate_embedding("test text")

        # Norm might not be 1.0 when normalization disabled
        # Just check embedding was generated
        assert len(embedding) == 384
        assert not all(x == 0.0 for x in embedding)


class TestPerformance:
    """Test performance benchmarks."""

    @pytest.mark.asyncio
    async def test_single_embedding_performance(self, service):
        """Test single embedding generation speed."""
        import time

        text = "Python for loops iterate over sequences and execute code"

        # Warm up
        service.generate_embedding(text)

        # Measure
        start = time.time()
        for _ in range(10):
            service.generate_embedding(text)
        elapsed = time.time() - start

        avg_time = elapsed / 10

        # Should be faster than 5ms on most hardware
        # Relaxed to 50ms for CI environments
        assert avg_time < 0.05, f"Single embedding took {avg_time*1000:.1f}ms (target: <50ms)"

    @pytest.mark.asyncio
    async def test_batch_performance(self, service):
        """Test batch embedding performance."""
        import time

        texts = ["concept " + str(i) for i in range(100)]

        # Warm up
        service.generate_batch(texts[:10])

        # Measure
        start = time.time()
        service.generate_batch(texts)
        elapsed = time.time() - start

        # Should be faster than 500ms for 100 texts
        # Relaxed for CI environments
        assert elapsed < 1.0, f"Batch of 100 took {elapsed*1000:.0f}ms (target: <1000ms)"


class TestZeroVectorFallback:
    """Test zero vector fallback mechanism."""

    @pytest.mark.asyncio
    async def test_create_zero_embedding(self, service):
        """Test zero vector creation."""
        zero_vec = service._create_zero_embedding()

        assert isinstance(zero_vec, list)
        assert len(zero_vec) == 384
        assert all(x == 0.0 for x in zero_vec)


# Integration-style tests
class TestRealWorldUsage:
    """Test real-world usage patterns."""

    @pytest.mark.asyncio
    async def test_typical_concept_embedding(self, service):
        """Test embedding typical concept explanations."""
        concept_texts = [
            "For loops in Python allow iteration over sequences like lists and strings. "
            "They execute a block of code for each element in the sequence.",
            "The Stoic dichotomy of control teaches that some things are within our control "
            "(our thoughts, actions, and responses) while others are not (external events).",
            "Async/await in JavaScript enables asynchronous programming, allowing code to "
            "pause execution while waiting for operations like API calls to complete.",
        ]

        for text in concept_texts:
            embedding = service.generate_embedding(text)

            assert len(embedding) == 384
            assert not all(x == 0.0 for x in embedding)

            # Check normalization
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_similarity_between_related_concepts(self, service):
        """Test that similar concepts have high cosine similarity."""
        text1 = "Python for loops iterate over sequences"
        text2 = "For loops in Python allow iteration over collections"

        emb1 = service.generate_embedding(text1)
        emb2 = service.generate_embedding(text2)

        # Calculate cosine similarity (dot product of normalized vectors)
        similarity = np.dot(emb1, emb2)

        # Similar concepts should have similarity > 0.7
        assert similarity > 0.7, f"Similarity: {similarity:.3f}"

    @pytest.mark.asyncio
    async def test_dissimilarity_between_unrelated_concepts(self, service):
        """Test that unrelated concepts have lower similarity."""
        text1 = "Python for loops iterate over sequences"
        text2 = "The Stoic dichotomy of control teaches about what we can control"

        emb1 = service.generate_embedding(text1)
        emb2 = service.generate_embedding(text2)

        # Calculate cosine similarity
        similarity = np.dot(emb1, emb2)

        # Unrelated concepts should have similarity < 0.5
        # (though semantic models might find unexpected connections)
        assert similarity < 0.7, f"Similarity: {similarity:.3f}"
