"""Fast tier classification using embedding centroid comparison."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import numpy as np

from src.taxonomy.schema import ClassificationResult
from src.utils.math import cosine_similarity

if TYPE_CHECKING:
    from src.taxonomy.centroids import CentroidManager
    from src.taxonomy.manager import TaxonomyManager

logger = logging.getLogger(__name__)


class FastTierClassifier:
    """Fast classification using pre-computed category centroids.

    This tier provides sub-100ms classification by comparing content
    embeddings against cached category centroids using cosine similarity.
    """

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager,
        centroid_manager: CentroidManager,
    ):
        """Initialize fast tier classifier.

        Args:
            taxonomy_manager: Manager for taxonomy operations.
            centroid_manager: Manager for category centroids.
        """
        self.taxonomy_manager = taxonomy_manager
        self.centroid_manager = centroid_manager

    def classify(
        self,
        embedding: np.ndarray | list[float],
        top_k: int = 5,
    ) -> ClassificationResult:
        """Classify content based on embedding similarity to centroids.

        Args:
            embedding: Content embedding vector.
            top_k: Number of top category matches to return.

        Returns:
            ClassificationResult with primary path and alternatives.
        """
        start_time = time.perf_counter()

        # Find nearest category centroids
        matches = self.centroid_manager.find_nearest_categories(
            embedding, top_k=top_k
        )

        processing_time_ms = (time.perf_counter() - start_time) * 1000

        if not matches:
            # No centroids available - cannot classify
            return ClassificationResult(
                primary_path="uncategorized",
                primary_confidence=0.0,
                alternatives=[],
                tier_used="fast",
                processing_time_ms=processing_time_ms,
            )

        primary_path, primary_confidence = matches[0]
        alternatives = matches[1:] if len(matches) > 1 else []

        logger.debug(
            "Fast tier classified to %s (confidence: %.3f) in %.2fms",
            primary_path,
            primary_confidence,
            processing_time_ms,
        )

        return ClassificationResult(
            primary_path=primary_path,
            primary_confidence=primary_confidence,
            alternatives=alternatives,
            tier_used="fast",
            processing_time_ms=processing_time_ms,
        )

    def get_confidence_for_path(
        self,
        embedding: np.ndarray | list[float],
        path: str,
    ) -> float:
        """Get classification confidence for a specific path.

        Args:
            embedding: Content embedding vector.
            path: Taxonomy path to check.

        Returns:
            Cosine similarity score (0.0 to 1.0).
        """
        centroid = self.centroid_manager.get_centroid(path)
        if centroid is None:
            return 0.0

        query_vec = np.array(embedding)
        return cosine_similarity(query_vec, centroid)

    def is_ready(self) -> bool:
        """Check if fast tier is ready (has centroids loaded)."""
        return self.centroid_manager.centroid_count > 0

    def get_category_coverage(self) -> dict[str, bool]:
        """Get which categories have centroids.

        Returns:
            Dict mapping category paths to whether they have centroids.
        """
        all_paths = self.taxonomy_manager.get_all_paths()
        return {path: self.centroid_manager.has_centroid(path) for path in all_paths}
