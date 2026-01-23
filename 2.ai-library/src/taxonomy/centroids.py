"""Centroid computation and caching for taxonomy categories."""

from __future__ import annotations

__all__ = ["CentroidManager"]

import json
import logging
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, Coroutine, Any

import numpy as np

from src.utils.math import cosine_similarity

if TYPE_CHECKING:
    from src.taxonomy.manager import TaxonomyManager
    from src.vector.embeddings import EmbeddingService
    from src.vector.store import QdrantVectorStore

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CentroidManager:
    """Manages category centroids for fast-tier classification."""

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager,
        cache_dir: str | Path | None = None,
    ):
        """Initialize centroid manager.

        Args:
            taxonomy_manager: Reference to taxonomy manager.
            cache_dir: Directory to cache centroids. Defaults to data/centroids.
        """
        self.taxonomy_manager = taxonomy_manager
        self.cache_dir = Path(cache_dir) if cache_dir else self._default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache: path -> centroid vector
        self._centroids: dict[str, np.ndarray] = {}
        self._loaded = False

    @staticmethod
    def _default_cache_dir() -> Path:
        """Get default cache directory."""
        return Path(__file__).parent.parent.parent / "data" / "centroids"

    @staticmethod
    def _run_async(coro: "Coroutine[Any, Any, T]") -> T:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "CentroidManager.compute_centroids() cannot run inside an event loop. "
            "Use an async wrapper or call from a sync context."
        )

    def load_centroids(self) -> int:
        """Load cached centroids from disk.

        Returns:
            Number of centroids loaded.
        """
        cache_file = self.cache_dir / "centroids.json"
        if not cache_file.exists():
            logger.info("No cached centroids found at %s", cache_file)
            return 0

        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)

        self._centroids = {path: np.array(vec) for path, vec in data.items()}
        self._loaded = True
        logger.info("Loaded %d centroids from cache", len(self._centroids))
        return len(self._centroids)

    def save_centroids(self) -> None:
        """Save centroids to disk cache."""
        cache_file = self.cache_dir / "centroids.json"

        # Convert numpy arrays to lists for JSON
        data = {path: vec.tolist() for path, vec in self._centroids.items()}

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        logger.info("Saved %d centroids to cache", len(self._centroids))

    def compute_centroids(
        self,
        vector_store: QdrantVectorStore,
        min_samples: int = 3,
    ) -> int:
        """Compute centroids for all categories from indexed content.

        Args:
            vector_store: Vector store to query for category content.
            min_samples: Minimum samples needed to compute centroid.

        Returns:
            Number of centroids computed.
        """
        if self.taxonomy_manager.config is None:
            raise ValueError("Taxonomy not loaded")

        all_paths = self.taxonomy_manager.get_all_paths()
        computed = 0

        for path in all_paths:
            centroid = self._compute_category_centroid(
                path, vector_store, min_samples
            )
            if centroid is not None:
                self._centroids[path] = centroid
                computed += 1
                logger.debug("Computed centroid for %s", path)

        logger.info("Computed %d centroids out of %d categories", computed, len(all_paths))
        return computed

    async def compute_centroids_async(
        self,
        vector_store: QdrantVectorStore,
        min_samples: int = 3,
    ) -> int:
        """Compute centroids for all categories from indexed content (async).

        Args:
            vector_store: Vector store to query for category content.
            min_samples: Minimum samples needed to compute centroid.

        Returns:
            Number of centroids computed.
        """
        if self.taxonomy_manager.config is None:
            raise ValueError("Taxonomy not loaded")

        all_paths = self.taxonomy_manager.get_all_paths()
        computed = 0

        for path in all_paths:
            centroid = await self._compute_category_centroid_async(
                path, vector_store, min_samples
            )
            if centroid is not None:
                self._centroids[path] = centroid
                computed += 1
                logger.debug("Computed centroid for %s", path)

        logger.info("Computed %d centroids out of %d categories", computed, len(all_paths))
        return computed

    def _compute_category_centroid(
        self,
        category_path: str,
        vector_store: QdrantVectorStore,
        min_samples: int,
    ) -> np.ndarray | None:
        """Compute centroid for a single category.

        Args:
            category_path: Taxonomy path for the category.
            vector_store: Vector store to query.
            min_samples: Minimum samples needed.

        Returns:
            Centroid vector or None if insufficient samples.
        """
        return self._run_async(
            self._compute_category_centroid_async(
                category_path,
                vector_store,
                min_samples,
            )
        )

    async def _compute_category_centroid_async(
        self,
        category_path: str,
        vector_store: QdrantVectorStore,
        min_samples: int,
    ) -> np.ndarray | None:
        """Compute centroid for a single category (async).

        Args:
            category_path: Taxonomy path for the category.
            vector_store: Vector store to query.
            min_samples: Minimum samples needed.

        Returns:
            Centroid vector or None if insufficient samples.
        """
        try:
            results = await vector_store.search_by_taxonomy(category_path, limit=1000)
        except Exception as e:
            logger.warning("Failed to query category %s: %s", category_path, e)
            return None

        if len(results) < min_samples:
            return None

        vectors = []
        for result in results:
            if hasattr(result, "vector") and result.vector is not None:
                vectors.append(np.array(result.vector))

        if len(vectors) < min_samples:
            return None

        centroid = np.mean(vectors, axis=0)
        return centroid

    def get_centroid(self, path: str) -> np.ndarray | None:
        """Get centroid for a category path.

        Args:
            path: Taxonomy path.

        Returns:
            Centroid vector or None if not computed.
        """
        return self._centroids.get(path)

    def has_centroid(self, path: str) -> bool:
        """Check if centroid exists for a path."""
        return path in self._centroids

    def find_nearest_categories(
        self,
        embedding: np.ndarray | list[float],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """Find nearest category centroids to an embedding.

        Args:
            embedding: Query embedding vector.
            top_k: Number of top matches to return.

        Returns:
            List of (path, similarity_score) tuples, sorted by similarity.
        """
        if not self._centroids:
            return []

        query_vec = np.array(embedding)
        scores = []

        for path, centroid in self._centroids.items():
            similarity = cosine_similarity(query_vec, centroid)
            scores.append((path, float(similarity)))

        # Sort by similarity (descending)
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def update_centroid_incremental(
        self,
        path: str,
        new_embedding: np.ndarray | list[float],
        current_count: int,
    ) -> None:
        """Incrementally update a centroid with a new embedding.

        Uses running average formula: new_centroid = old_centroid + (new_vec - old_centroid) / new_count

        Args:
            path: Category path.
            new_embedding: New embedding to incorporate.
            current_count: Current content count (after adding new item).
        """
        new_vec = np.array(new_embedding)

        if path not in self._centroids:
            # First item
            self._centroids[path] = new_vec
        else:
            # Incremental update
            old_centroid = self._centroids[path]
            self._centroids[path] = old_centroid + (new_vec - old_centroid) / current_count

    def clear_centroid(self, path: str) -> None:
        """Remove centroid for a category (e.g., when category is deleted)."""
        self._centroids.pop(path, None)

    def get_all_centroids(self) -> dict[str, np.ndarray]:
        """Get all computed centroids."""
        return self._centroids.copy()

    @property
    def centroid_count(self) -> int:
        """Number of computed centroids."""
        return len(self._centroids)
