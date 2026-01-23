"""Two-tier classification service orchestrator."""

from __future__ import annotations

import logging
import asyncio
from typing import TYPE_CHECKING

import numpy as np

from src.classification.fast_tier import FastTierClassifier
from src.classification.llm_tier import LLMTierClassifier
from src.taxonomy.schema import ClassificationResult

if TYPE_CHECKING:
    from src.sdk.client import ClaudeSDKClient
    from src.taxonomy.centroids import CentroidManager
    from src.taxonomy.manager import TaxonomyManager
    from src.vector.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class ClassificationService:
    """Two-tier classification service.

    Uses fast embedding-based classification first, falling back to
    LLM classification when confidence is below threshold.
    """

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager,
        centroid_manager: CentroidManager,
        embedding_service: EmbeddingService | None = None,
        sdk_client: ClaudeSDKClient | None = None,
        confidence_threshold: float | None = None,
    ):
        """Initialize classification service.

        Args:
            taxonomy_manager: Manager for taxonomy operations.
            centroid_manager: Manager for category centroids.
            embedding_service: Service for generating embeddings.
            sdk_client: Claude SDK client for LLM tier.
            confidence_threshold: Threshold below which LLM tier is used.
                                 If None, uses taxonomy config value.
        """
        self.taxonomy_manager = taxonomy_manager
        self.centroid_manager = centroid_manager
        self._embedding_service = embedding_service
        self._sdk_client = sdk_client

        # Get threshold from config or use provided value
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
        elif taxonomy_manager.config is not None:
            self.confidence_threshold = (
                taxonomy_manager.config.classification.fast_tier_confidence_threshold
            )
        else:
            self.confidence_threshold = 0.75

        # Initialize tier classifiers
        self.fast_tier = FastTierClassifier(taxonomy_manager, centroid_manager)
        self.llm_tier = LLMTierClassifier(taxonomy_manager, sdk_client)

    @property
    def embedding_service(self) -> EmbeddingService:
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from src.vector.embeddings import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def classify(
        self,
        title: str,
        content: str,
        embedding: np.ndarray | list[float] | None = None,
        force_llm: bool = False,
    ) -> ClassificationResult:
        """Classify content into taxonomy category.

        Args:
            title: Content title.
            content: Full content text.
            embedding: Pre-computed embedding (optional, will compute if not provided).
            force_llm: If True, skip fast tier and use LLM directly.

        Returns:
            ClassificationResult with classification and metadata.
        """
        # Generate embedding if not provided
        if embedding is None:
            # Combine title and content for embedding
            combined_text = f"{title}\n\n{content}"
            embedding = self.embedding_service.embed(combined_text)

        # Fast tier first (unless forced to LLM)
        if not force_llm and self.fast_tier.is_ready():
            fast_result = self.fast_tier.classify(embedding)

            # Check if confidence is sufficient
            if fast_result.primary_confidence >= self.confidence_threshold:
                logger.debug(
                    "Fast tier accepted (confidence %.3f >= threshold %.3f)",
                    fast_result.primary_confidence,
                    self.confidence_threshold,
                )
                return fast_result

            logger.debug(
                "Fast tier confidence %.3f below threshold %.3f, escalating to LLM",
                fast_result.primary_confidence,
                self.confidence_threshold,
            )

        # LLM tier for complex cases
        llm_result = self.llm_tier.classify(title, content)

        # Handle new category proposals
        if llm_result.new_category_proposed is not None:
            proposal = llm_result.new_category_proposed
            try:
                proposed = self.taxonomy_manager.propose_category(proposal)
                logger.info(
                    "New category proposed: %s (status: %s)",
                    proposed.path,
                    proposed.status,
                )
            except ValueError as e:
                logger.warning("Category proposal rejected: %s", e)
                llm_result.new_category_proposed = None

        return llm_result

    async def classify_async(
        self,
        title: str,
        content: str,
        embedding: np.ndarray | list[float] | None = None,
        force_llm: bool = False,
    ) -> ClassificationResult:
        """Classify content into taxonomy category (async).

        Args:
            title: Content title.
            content: Full content text.
            embedding: Pre-computed embedding (optional, will compute if not provided).
            force_llm: If True, skip fast tier and use LLM directly.

        Returns:
            ClassificationResult with classification and metadata.
        """
        if embedding is None:
            combined_text = f"{title}\n\n{content}"
            if hasattr(self.embedding_service, "embed_async"):
                embedding = await self.embedding_service.embed_async(combined_text)
            else:
                embedding = await asyncio.to_thread(
                    self.embedding_service.embed, combined_text
                )

        if not force_llm and self.fast_tier.is_ready():
            fast_result = self.fast_tier.classify(embedding)

            if fast_result.primary_confidence >= self.confidence_threshold:
                logger.debug(
                    "Fast tier accepted (confidence %.3f >= threshold %.3f)",
                    fast_result.primary_confidence,
                    self.confidence_threshold,
                )
                return fast_result

            logger.debug(
                "Fast tier confidence %.3f below threshold %.3f, escalating to LLM",
                fast_result.primary_confidence,
                self.confidence_threshold,
            )

        llm_result = await self.llm_tier.classify_async(title, content)

        if llm_result.new_category_proposed is not None:
            proposal = llm_result.new_category_proposed
            try:
                proposed = self.taxonomy_manager.propose_category(proposal)
                logger.info(
                    "New category proposed: %s (status: %s)",
                    proposed.path,
                    proposed.status,
                )
            except ValueError as e:
                logger.warning("Category proposal rejected: %s", e)
                llm_result.new_category_proposed = None

        return llm_result

    def classify_batch(
        self,
        items: list[tuple[str, str, np.ndarray | list[float] | None]],
    ) -> list[ClassificationResult]:
        """Classify multiple items.

        Args:
            items: List of (title, content, embedding) tuples.

        Returns:
            List of ClassificationResults in same order.
        """
        results = []
        for title, content, embedding in items:
            result = self.classify(title, content, embedding)
            results.append(result)
        return results

    def reclassify(
        self,
        content_id: str,
        title: str,
        content: str,
        current_path: str,
    ) -> ClassificationResult | None:
        """Reclassify content and check if it should move.

        Args:
            content_id: ID of content being reclassified.
            title: Content title.
            content: Full content.
            current_path: Current taxonomy path.

        Returns:
            New ClassificationResult if classification changed, None otherwise.
        """
        result = self.classify(title, content)

        # Check if classification has changed significantly
        if result.primary_path == current_path:
            return None

        # Check if new path is significantly better
        if result.primary_confidence < self.confidence_threshold:
            # Not confident enough to move
            return None

        logger.info(
            "Content %s should move from %s to %s (confidence: %.3f)",
            content_id,
            current_path,
            result.primary_path,
            result.primary_confidence,
        )

        return result

    def get_classification_stats(self) -> dict:
        """Get classification service statistics.

        Returns:
            Dictionary with service stats.
        """
        return {
            "fast_tier_ready": self.fast_tier.is_ready(),
            "centroid_count": self.centroid_manager.centroid_count,
            "confidence_threshold": self.confidence_threshold,
            "taxonomy_paths": len(self.taxonomy_manager.get_all_paths()),
            "category_coverage": self.fast_tier.get_category_coverage(),
        }

    def validate_path(self, path: str) -> bool:
        """Check if a taxonomy path is valid.

        Args:
            path: Taxonomy path to validate.

        Returns:
            True if path exists in taxonomy.
        """
        return self.taxonomy_manager.validate_path(path)
