"""
Embedding Generation Service.

Provides semantic embedding generation using either:
- sentence-transformers (local inference)
- Mistral API (cloud-based, higher quality)

Enables vector similarity search in ChromaDB.
"""

import asyncio
import contextlib
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np


logger = logging.getLogger(__name__)

# Import EmbeddingCache (optional dependency)
try:
    from services.embedding_cache import EmbeddingCache

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logger.warning("EmbeddingCache not available")


@dataclass
class EmbeddingConfig:
    """
    Configuration for embedding service.

    Attributes:
        model_name: Name of embedding model to use
            - For sentence-transformers: "all-MiniLM-L6-v2", "all-mpnet-base-v2", etc.
            - For mistral: "mistral-embed"
        backend: Embedding backend ("sentence-transformers" or "mistral")
        device: Device for local model inference ('cpu' or 'cuda')
        batch_size: Default batch size for batch processing
        normalize: Whether to normalize embeddings to unit vectors
        max_text_length: Maximum text length in characters (truncated beyond this)
        mistral_api_key_env: Environment variable name for Mistral API key
    """

    model_name: str = "all-MiniLM-L6-v2"
    backend: Literal["sentence-transformers", "mistral"] = "sentence-transformers"
    device: str = "cpu"
    batch_size: int = 32
    normalize: bool = True
    max_text_length: int = 8000  # Mistral supports up to 8192 tokens
    mistral_api_key_env: str = "MISTRAL_API_KEY"


class EmbeddingService:
    """
    Service for generating semantic embeddings from text.

    Supports two backends:
    - sentence-transformers: Local inference with models like all-MiniLM-L6-v2 (384 dims)
    - mistral: Mistral API with mistral-embed model (1024 dims)

    Features:
    - Async model loading to prevent blocking
    - Single and batch embedding generation
    - Automatic normalization for cosine similarity
    - Graceful degradation if model unavailable
    - Thread-safe model initialization

    Example:
        ```python
        # Using Mistral API
        config = EmbeddingConfig(backend="mistral", model_name="mistral-embed")
        service = EmbeddingService(config)
        await service.initialize()

        # Single embedding
        embedding = service.generate_embedding("Python for loops")

        # Batch processing
        embeddings = service.generate_batch([
            "concept 1 text",
            "concept 2 text"
        ])
        ```
    """

    # Global lock for async-safe model initialization
    _model_load_locks: dict = {}
    _lock_dict_lock = threading.Lock()
    _global_initialization_lock = threading.Lock()
    _shared_model = None
    _shared_model_config: EmbeddingConfig | None = None

    # Embedding dimensions by model
    EMBEDDING_DIMS = {
        "mistral-embed": 1024,
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
    }

    @classmethod
    @contextlib.asynccontextmanager
    async def _global_initialization_guard(cls):
        """Async context manager guarding initialization across threads."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, cls._global_initialization_lock.acquire)
        try:
            yield
        finally:
            cls._global_initialization_lock.release()

    @classmethod
    def _get_model_load_lock(cls) -> asyncio.Lock:
        """Get or create the model load lock for the current event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)

            if loop_id not in cls._model_load_locks:
                with cls._lock_dict_lock:
                    if loop_id not in cls._model_load_locks:
                        cls._model_load_locks[loop_id] = asyncio.Lock()

            return cls._model_load_locks[loop_id]
        except RuntimeError:
            raise RuntimeError("_get_model_load_lock() must be called from async context")

    def __init__(
        self, config: EmbeddingConfig | None = None, cache: Optional["EmbeddingCache"] = None
    ) -> None:
        """
        Initialize embedding service.

        Args:
            config: Configuration for embedding generation.
                   Uses defaults if not provided.
            cache: Optional EmbeddingCache for persistent caching.
        """
        self.config = config or EmbeddingConfig()
        self.model = None
        self._mistral_client = None
        self._initialized = False
        self._model_available = False

        # Set embedding dimension based on model
        self._embedding_dim = self.EMBEDDING_DIMS.get(
            self.config.model_name,
            1024 if self.config.backend == "mistral" else 384
        )
        self.cache = cache

        logger.info(
            f"EmbeddingService created with model: {self.config.model_name}, "
            f"backend: {self.config.backend}, "
            f"dimensions: {self._embedding_dim}, "
            f"cache: {'enabled' if cache else 'disabled'}"
        )

    async def initialize(self) -> bool:
        """
        Initialize the embedding model/client asynchronously.

        Returns:
            True if model/client loaded successfully, False otherwise
        """
        if self._initialized:
            logger.debug("EmbeddingService already initialized")
            return self._model_available

        # Reuse cached model if compatible (sentence-transformers only)
        if (
            self.config.backend == "sentence-transformers"
            and EmbeddingService._shared_model is not None
            and EmbeddingService._shared_model_config == self.config
            and self._is_default_loader()
        ):
            logger.debug("Reusing cached embedding model instance")
            self.model = EmbeddingService._shared_model
            self._model_available = True
            self._initialized = True
            return True

        lock = self._get_model_load_lock()
        async with lock, self._global_initialization_guard():
            if self._initialized:
                logger.debug("EmbeddingService already initialized (double-check)")
                return self._model_available

            try:
                if self.config.backend == "mistral":
                    await self._initialize_mistral()
                else:
                    await self._initialize_sentence_transformers()

                self._model_available = True
                self._initialized = True

                logger.info(
                    f"Embedding service initialized successfully. "
                    f"Backend: {self.config.backend}, Dimensions: {self._embedding_dim}"
                )

                return True

            except Exception as e:
                logger.error(
                    f"Failed to initialize embedding service: {e}. "
                    f"Service will operate in degraded mode.",
                    exc_info=True,
                )
                self._model_available = False
                self._initialized = True
                return False

    async def _initialize_mistral(self) -> None:
        """Initialize Mistral API client."""
        from mistralai import Mistral

        api_key = os.environ.get(self.config.mistral_api_key_env)
        if not api_key:
            raise ValueError(
                f"Mistral API key not found. Set {self.config.mistral_api_key_env} environment variable."
            )

        self._mistral_client = Mistral(api_key=api_key)

        # Test the connection with a small embedding
        logger.info(f"Initializing Mistral embedding client with model: {self.config.model_name}")

        loop = asyncio.get_event_loop()
        test_result = await loop.run_in_executor(
            None,
            lambda: self._mistral_client.embeddings.create(
                model=self.config.model_name,
                inputs=["test"]
            )
        )

        if test_result and test_result.data:
            actual_dim = len(test_result.data[0].embedding)
            self._embedding_dim = actual_dim
            logger.info(f"Mistral API connection verified. Embedding dimensions: {actual_dim}")

    async def _initialize_sentence_transformers(self) -> None:
        """Initialize sentence-transformers model."""
        logger.info(
            f"Loading embedding model: {self.config.model_name} "
            f"on device: {self.config.device}"
        )

        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(None, self._load_model)

        EmbeddingService._shared_model = self.model
        EmbeddingService._shared_model_config = self.config

    def _load_model(self):
        """Load the sentence-transformers model (blocking operation)."""
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(self.config.model_name, device=self.config.device)
        logger.debug(
            f"Model loaded: {self.config.model_name}, max_seq_length: {model.max_seq_length}"
        )
        return model

    def _is_default_loader(self) -> bool:
        """Check if using default _load_model implementation."""
        loader = self._load_model
        func = getattr(loader, "__func__", None)
        return func is EmbeddingService._load_model

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text before embedding generation."""
        if not text:
            return ""

        # Normalize whitespace
        text = " ".join(text.split())

        # Truncate if too long
        if len(text) > self.config.max_text_length:
            text = text[: self.config.max_text_length]
            logger.debug(f"Text truncated to {self.config.max_text_length} characters")

        return text

    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding to unit vector."""
        if not self.config.normalize:
            return embedding

        norm = np.linalg.norm(embedding)
        if norm == 0:
            logger.warning("Zero-norm embedding encountered, returning as-is")
            return embedding

        return embedding / norm

    def _create_zero_embedding(self) -> list[float]:
        """Create a zero vector as fallback."""
        logger.debug("Creating zero-vector fallback embedding")
        return [0.0] * self._embedding_dim

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed (concept explanation, description, etc.)

        Returns:
            Embedding as list of floats (dimension depends on model).
            Returns zero vector if model unavailable or error occurs.
        """
        if not self._initialized:
            logger.error("EmbeddingService not initialized. Call initialize() before using.")
            return self._create_zero_embedding()

        if not self._model_available:
            logger.warning("Model not available, returning zero-vector fallback")
            return self._create_zero_embedding()

        try:
            # Check cache first if available
            if self.cache:
                cached = self.cache.get_cached(text, self.config.model_name)
                if cached:
                    logger.debug(f"Cache HIT for text_len={len(text)}")
                    return cached

            # Preprocess text
            processed_text = self._preprocess_text(text)

            if not processed_text:
                logger.warning("Empty text provided, returning zero vector")
                return self._create_zero_embedding()

            # Generate embedding based on backend
            if self.config.backend == "mistral":
                embedding_list = self._generate_mistral_embedding(processed_text)
            else:
                embedding_list = self._generate_st_embedding(processed_text)

            # Store in cache if available
            if self.cache:
                self.cache.store(text, self.config.model_name, embedding_list)
                logger.debug(f"Stored embedding in cache for text_len={len(text)}")

            logger.debug(
                f"Generated embedding: dim={len(embedding_list)}, text_len={len(processed_text)}"
            )

            return embedding_list

        except Exception as e:
            logger.error(
                f"Error generating embedding: {e}. Returning zero-vector fallback.",
                exc_info=True,
            )
            return self._create_zero_embedding()

    def _generate_mistral_embedding(self, text: str) -> list[float]:
        """Generate embedding using Mistral API."""
        if not self._mistral_client:
            raise RuntimeError("Mistral client not initialized")

        result = self._mistral_client.embeddings.create(
            model=self.config.model_name,
            inputs=[text]
        )

        if not result or not result.data:
            raise RuntimeError("Mistral API returned empty result")

        embedding = result.data[0].embedding

        # Normalize if configured
        if self.config.normalize:
            embedding = np.array(embedding)
            embedding = self._normalize_embedding(embedding)
            return embedding.tolist()

        return embedding

    def _generate_st_embedding(self, text: str) -> list[float]:
        """Generate embedding using sentence-transformers."""
        if not self.model:
            raise RuntimeError("Sentence-transformers model not loaded")

        embedding = self.model.encode(
            text, normalize_embeddings=self.config.normalize, show_progress_bar=False
        )

        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)

        return embedding.tolist()

    def generate_batch(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing. Uses config default if None.

        Returns:
            List of embeddings (one per input text).
        """
        if not self._initialized:
            logger.error("EmbeddingService not initialized. Call initialize() before using.")
            return [self._create_zero_embedding() for _ in texts]

        if not self._model_available:
            logger.warning("Model not available, returning zero-vector fallbacks")
            return [self._create_zero_embedding() for _ in texts]

        if not texts:
            logger.warning("Empty text list provided")
            return []

        try:
            # Check cache for each text if available
            results = []
            uncached_texts = []
            uncached_indices = []

            if self.cache:
                for i, text in enumerate(texts):
                    cached = self.cache.get_cached(text, self.config.model_name)
                    if cached:
                        results.append(cached)
                    else:
                        results.append(None)
                        uncached_texts.append(text)
                        uncached_indices.append(i)

                logger.debug(
                    f"Batch cache check: {len(texts) - len(uncached_texts)} hits, "
                    f"{len(uncached_texts)} misses"
                )
            else:
                uncached_texts = texts
                uncached_indices = list(range(len(texts)))
                results = [None] * len(texts)

            # Process uncached texts
            if uncached_texts:
                processed_texts = []
                empty_indices = []

                for i, text in enumerate(uncached_texts):
                    processed = self._preprocess_text(text)
                    if not processed:
                        empty_indices.append(i)
                        processed_texts.append("placeholder")
                    else:
                        processed_texts.append(processed)

                # Generate embeddings based on backend
                if self.config.backend == "mistral":
                    embeddings_list = self._generate_mistral_batch(processed_texts)
                else:
                    embeddings_list = self._generate_st_batch(processed_texts, batch_size)

                # Replace empty text embeddings with zero vectors
                for idx in empty_indices:
                    embeddings_list[idx] = self._create_zero_embedding()

                # Insert generated embeddings into results and cache them
                for i, orig_idx in enumerate(uncached_indices):
                    embedding = embeddings_list[i]
                    results[orig_idx] = embedding

                    if self.cache:
                        self.cache.store(uncached_texts[i], self.config.model_name, embedding)

                logger.debug(
                    f"Generated {len(embeddings_list)} new embeddings "
                    f"({len(empty_indices)} zero vectors)"
                )

            return results

        except Exception as e:
            logger.error(
                f"Error generating batch embeddings: {e}. Returning zero-vector fallbacks.",
                exc_info=True,
            )
            return [self._create_zero_embedding() for _ in texts]

    def _generate_mistral_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate batch embeddings using Mistral API."""
        if not self._mistral_client:
            raise RuntimeError("Mistral client not initialized")

        result = self._mistral_client.embeddings.create(
            model=self.config.model_name,
            inputs=texts
        )

        if not result or not result.data:
            raise RuntimeError("Mistral API returned empty result")

        embeddings = []
        for item in result.data:
            embedding = item.embedding
            if self.config.normalize:
                embedding = np.array(embedding)
                embedding = self._normalize_embedding(embedding)
                embedding = embedding.tolist()
            embeddings.append(embedding)

        return embeddings

    def _generate_st_batch(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        """Generate batch embeddings using sentence-transformers."""
        if not self.model:
            raise RuntimeError("Sentence-transformers model not loaded")

        actual_batch_size = batch_size or self.config.batch_size

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=self.config.normalize,
            batch_size=actual_batch_size,
            show_progress_bar=len(texts) > 100,
        )

        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        return embeddings.tolist()

    def is_available(self) -> bool:
        """Check if embedding model is available and ready."""
        return self._initialized and self._model_available

    def get_embedding_dimension(self) -> int:
        """Get the dimensionality of generated embeddings."""
        return self._embedding_dim

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.config.model_name,
            "backend": self.config.backend,
            "embedding_dim": self._embedding_dim,
            "device": self.config.device if self.config.backend == "sentence-transformers" else "api",
            "available": self._model_available,
            "initialized": self._initialized,
            "normalize": self.config.normalize,
            "batch_size": self.config.batch_size,
        }

    def health_check(self) -> dict:
        """Perform health check on embedding service."""
        return {
            "service": "embedding",
            "status": "healthy" if self._model_available else "degraded",
            "initialized": self._initialized,
            "model_available": self._model_available,
            "model_name": self.config.model_name,
            "backend": self.config.backend,
            "embedding_dimension": self._embedding_dim,
            "device": self.config.device if self.config.backend == "sentence-transformers" else "api",
            "details": {
                "normalize": self.config.normalize,
                "batch_size": self.config.batch_size,
                "max_text_length": self.config.max_text_length,
            },
        }
