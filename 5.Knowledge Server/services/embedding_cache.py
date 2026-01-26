"""
Embedding Cache Service.

Provides persistent SQLite-based caching for embedding vectors to avoid
recomputation and improve performance for repeated text.
"""

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """
    Statistics about cache performance.

    Attributes:
        total_entries: Total number of cached embeddings
        cache_hits: Number of successful cache retrievals
        cache_misses: Number of cache misses (not found)
        hit_rate: Percentage of cache hits (0-100)
    """

    total_entries: int
    cache_hits: int
    cache_misses: int
    hit_rate: float


class EmbeddingCache:
    """
    Persistent cache for embedding vectors using SQLite.

    Features:
    - SHA256 hashing for consistent cache keys
    - Text normalization before hashing
    - Model-aware caching (separate cache per model)
    - Cache hit/miss tracking
    - Performance <1ms for cache retrieval

    Example:
        ```python
        cache = EmbeddingCache(db_path="./data/events.db")

        # Store embedding
        embedding = [0.1, 0.2, 0.3, ...]
        cache.store("hello world", "all-MiniLM-L6-v2", embedding)

        # Retrieve from cache
        cached = cache.get_cached("hello world", "all-MiniLM-L6-v2")
        if cached:
            print("Cache hit!")
        ```
    """

    def __init__(self, db_path: str = "./data/events.db") -> None:
        """
        Initialize embedding cache.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._cache_hits = 0
        self._cache_misses = 0

        # Ensure database and table exist
        self._ensure_db_exists()

        logger.info(f"EmbeddingCache initialized with database: {db_path}")

    def _ensure_db_exists(self) -> None:
        """Ensure database and embedding_cache table exist."""
        db_path = Path(self.db_path)

        if not db_path.exists():
            logger.warning(
                f"Database not found at {self.db_path}. " f"Run scripts/init_database.py first."
            )
            # Create directory if needed
            db_path.parent.mkdir(parents=True, exist_ok=True)

        # Verify table exists or create it
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    text_hash TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (text_hash, model_name)
                )
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_text_hash
                ON embedding_cache(text_hash)
            """
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to ensure database exists: {e}")

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text before hashing for consistent cache keys.

        Normalization steps:
        - Strip leading/trailing whitespace
        - Collapse multiple whitespace to single space
        - Convert to lowercase for case-insensitive matching

        Args:
            text: Input text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Normalize whitespace
        normalized = " ".join(text.split())

        # Convert to lowercase for case-insensitive matching
        normalized = normalized.lower()

        return normalized

    def _compute_hash(self, text: str) -> str:
        """
        Compute SHA256 hash of text for cache key.

        Args:
            text: Input text (should be normalized)

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_cached(self, text: str, model_name: str) -> list[float] | None:
        """
        Retrieve cached embedding for text and model.

        Args:
            text: Text to retrieve embedding for
            model_name: Model name used to generate embedding

        Returns:
            Cached embedding as list of floats, or None if not cached

        Example:
            ```python
            embedding = cache.get_cached("hello world", "all-MiniLM-L6-v2")
            if embedding:
                print(f"Cache hit! Got {len(embedding)}-dim embedding")
            else:
                print("Cache miss, need to generate")
            ```
        """
        # Normalize text and compute hash
        normalized = self._normalize_text(text)
        text_hash = self._compute_hash(normalized)

        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT embedding
                FROM embedding_cache
                WHERE text_hash = ? AND model_name = ?
                """,
                (text_hash, model_name),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                self._cache_hits += 1
                embedding = json.loads(row[0])
                logger.debug(
                    f"Cache HIT: text_hash={text_hash[:8]}..., "
                    f"model={model_name}, dim={len(embedding)}"
                )
                return embedding
            else:
                self._cache_misses += 1
                logger.debug(f"Cache MISS: text_hash={text_hash[:8]}..., " f"model={model_name}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}. Returning None.", exc_info=True)
            self._cache_misses += 1
            return None

    def store(self, text: str, model_name: str, embedding: list[float]) -> bool:
        """
        Store embedding in cache.

        Args:
            text: Original text
            model_name: Model name used to generate embedding
            embedding: Embedding vector to store

        Returns:
            True if stored successfully, False otherwise

        Example:
            ```python
            embedding = [0.1, 0.2, 0.3, ...]
            success = cache.store("hello world", "all-MiniLM-L6-v2", embedding)
            if success:
                print("Stored in cache")
            ```
        """
        # Normalize text and compute hash
        normalized = self._normalize_text(text)
        text_hash = self._compute_hash(normalized)

        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()

            # Serialize embedding as JSON
            embedding_json = json.dumps(embedding)

            # Use INSERT OR REPLACE to handle duplicates
            cursor.execute(
                """
                INSERT OR REPLACE INTO embedding_cache
                (text_hash, model_name, embedding, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (text_hash, model_name, embedding_json, datetime.now()),
            )

            conn.commit()
            conn.close()

            logger.debug(
                f"Cache STORE: text_hash={text_hash[:8]}..., "
                f"model={model_name}, dim={len(embedding)}"
            )

            return True

        except Exception as e:
            logger.error(f"Error storing in cache: {e}.", exc_info=True)
            return False

    def clear_cache(self, model_name: str | None = None) -> int:
        """
        Clear cached embeddings.

        Args:
            model_name: If provided, only clear cache for this model.
                       If None, clear entire cache.

        Returns:
            Number of entries deleted

        Example:
            ```python
            # Clear cache for specific model
            deleted = cache.clear_cache("all-MiniLM-L6-v2")
            print(f"Deleted {deleted} entries")

            # Clear entire cache
            deleted = cache.clear_cache()
            print(f"Deleted {deleted} entries")
            ```
        """
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()

            if model_name:
                cursor.execute("DELETE FROM embedding_cache WHERE model_name = ?", (model_name,))
                deleted = cursor.rowcount
                logger.info(f"Cleared cache for model '{model_name}': {deleted} entries")
            else:
                cursor.execute("DELETE FROM embedding_cache")
                deleted = cursor.rowcount
                logger.info(f"Cleared entire cache: {deleted} entries")

            conn.commit()
            conn.close()

            return deleted

        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
            return 0

    def get_cache_stats(self) -> CacheStats:
        """
        Get cache performance statistics.

        Returns:
            CacheStats with metrics about cache performance

        Example:
            ```python
            stats = cache.get_cache_stats()
            print(f"Total entries: {stats.total_entries}")
            print(f"Hit rate: {stats.hit_rate:.1f}%")
            ```
        """
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM embedding_cache")
            total_entries = cursor.fetchone()[0]

            conn.close()

            # Calculate hit rate
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0

            return CacheStats(
                total_entries=total_entries,
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
                hit_rate=hit_rate,
            )

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}", exc_info=True)
            return CacheStats(
                total_entries=0,
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
                hit_rate=0.0,
            )

    def get_cached_with_hash(self, text: str, model_name: str) -> tuple[list[float] | None, str]:
        """
        Retrieve cached embedding and return the hash.

        Useful for debugging or when you need the hash for other purposes.

        Args:
            text: Text to retrieve embedding for
            model_name: Model name used to generate embedding

        Returns:
            Tuple of (embedding or None, text_hash)
        """
        normalized = self._normalize_text(text)
        text_hash = self._compute_hash(normalized)
        embedding = self.get_cached(text, model_name)
        return (embedding, text_hash)
