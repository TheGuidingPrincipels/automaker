"""Composite ranking combining multiple signals."""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RankingWeights(BaseModel):
    """Configurable weights for ranking signals."""

    similarity_weight: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Weight for vector similarity"
    )
    taxonomy_weight: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for taxonomy match"
    )
    recency_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Weight for recency"
    )

    # Recency decay parameters
    recency_half_life_days: float = Field(
        default=30.0, ge=1.0, description="Half-life for recency decay in days"
    )

    def validate_weights(self) -> bool:
        """Check that weights sum to ~1.0."""
        total = self.similarity_weight + self.taxonomy_weight + self.recency_weight
        return abs(total - 1.0) < 0.01

    def normalize(self) -> RankingWeights:
        """Normalize weights to sum to 1.0."""
        total = self.similarity_weight + self.taxonomy_weight + self.recency_weight
        if total == 0:
            return RankingWeights()
        return RankingWeights(
            similarity_weight=self.similarity_weight / total,
            taxonomy_weight=self.taxonomy_weight / total,
            recency_weight=self.recency_weight / total,
            recency_half_life_days=self.recency_half_life_days,
        )


class RankedResult(BaseModel):
    """A search result with composite score."""

    content_id: str
    composite_score: float = Field(ge=0.0, le=1.0)
    similarity_score: float = Field(ge=0.0, le=1.0)
    taxonomy_score: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    payload: dict[str, Any] = Field(default_factory=dict)

    # Debug info
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class CompositeRanker:
    """Ranks search results using multiple signals.

    Combines:
    - Vector similarity (semantic match)
    - Taxonomy overlap (category match)
    - Recency (freshness of content)
    """

    def __init__(self, weights: RankingWeights | None = None):
        """Initialize ranker with weights.

        Args:
            weights: Ranking weights. Uses defaults if not provided.
        """
        self.weights = (weights or RankingWeights()).normalize()

    def rank(
        self,
        results: list[dict[str, Any]],
        query_taxonomy_path: str | None = None,
        now: datetime | None = None,
    ) -> list[RankedResult]:
        """Rank search results using composite scoring.

        Args:
            results: Raw search results with similarity scores.
            query_taxonomy_path: Taxonomy path of the query (for taxonomy scoring).
            now: Current time for recency calculation. Defaults to UTC now.

        Returns:
            List of RankedResults sorted by composite score (descending).
        """
        if now is None:
            now = datetime.now(UTC)

        ranked_results = []

        for result in results:
            ranked = self._score_result(result, query_taxonomy_path, now)
            ranked_results.append(ranked)

        # Sort by composite score descending
        ranked_results.sort(key=lambda r: r.composite_score, reverse=True)

        return ranked_results

    def _score_result(
        self,
        result: dict[str, Any],
        query_taxonomy_path: str | None,
        now: datetime,
    ) -> RankedResult:
        """Compute composite score for a single result.

        Args:
            result: Raw search result.
            query_taxonomy_path: Query taxonomy path.
            now: Current time.

        Returns:
            RankedResult with scores.
        """
        # Extract data from result
        content_id = result.get("id", result.get("content_id", "unknown"))
        payload = result.get("payload", {})

        # Similarity score (from vector search)
        similarity_score = float(result.get("score", result.get("similarity", 0.0)))

        # Taxonomy score
        result_taxonomy = payload.get("taxonomy_path", "")
        taxonomy_score = self._compute_taxonomy_score(
            query_taxonomy_path, result_taxonomy
        )

        # Recency score
        created_at = payload.get("created_at")
        updated_at = payload.get("updated_at")
        recency_score = self._compute_recency_score(
            created_at, updated_at, now
        )

        # Compute composite score
        composite_score = (
            self.weights.similarity_weight * similarity_score
            + self.weights.taxonomy_weight * taxonomy_score
            + self.weights.recency_weight * recency_score
        )

        return RankedResult(
            content_id=content_id,
            composite_score=composite_score,
            similarity_score=similarity_score,
            taxonomy_score=taxonomy_score,
            recency_score=recency_score,
            payload=payload,
            score_breakdown={
                "similarity_weighted": self.weights.similarity_weight * similarity_score,
                "taxonomy_weighted": self.weights.taxonomy_weight * taxonomy_score,
                "recency_weighted": self.weights.recency_weight * recency_score,
            },
        )

    def _compute_taxonomy_score(
        self,
        query_path: str | None,
        result_path: str,
    ) -> float:
        """Compute taxonomy overlap score.

        Scoring logic:
        - Full match: 1.0
        - Parent match (result is more specific): 0.8
        - Child match (result is more general): 0.6
        - Sibling match (same parent): 0.4
        - Different branch at level 1: 0.1
        - No match: 0.0

        Args:
            query_path: Taxonomy path from query.
            result_path: Taxonomy path of result.

        Returns:
            Overlap score from 0.0 to 1.0.
        """
        if not query_path or not result_path:
            return 0.0

        query_parts = query_path.strip("/").split("/")
        result_parts = result_path.strip("/").split("/")

        # Full match
        if query_parts == result_parts:
            return 1.0

        # Find common prefix length
        common_length = 0
        for q, r in zip(query_parts, result_parts):
            if q == r:
                common_length += 1
            else:
                break

        if common_length == 0:
            # Different top-level categories
            return 0.0

        max_length = max(len(query_parts), len(result_parts))

        # Score based on overlap ratio
        base_score = common_length / max_length

        # Adjust based on relationship
        if len(result_parts) > len(query_parts) and common_length == len(query_parts):
            # Result is more specific (child of query)
            return 0.6 + 0.4 * base_score
        elif len(query_parts) > len(result_parts) and common_length == len(result_parts):
            # Result is more general (parent of query)
            return 0.4 + 0.4 * base_score
        elif common_length == len(query_parts) - 1 == len(result_parts) - 1:
            # Siblings (same parent)
            return 0.3 + 0.3 * base_score

        return base_score

    def _compute_recency_score(
        self,
        created_at: str | datetime | None,
        updated_at: str | datetime | None,
        now: datetime,
    ) -> float:
        """Compute recency score using exponential decay.

        Uses half-life decay: score = 0.5^(age / half_life)

        Args:
            created_at: Creation timestamp.
            updated_at: Last update timestamp (preferred if available).
            now: Current time.

        Returns:
            Recency score from 0.0 to 1.0.
        """
        # Use most recent timestamp
        timestamp = updated_at or created_at
        if timestamp is None:
            return 0.5  # Default for unknown age

        # Parse timestamp if string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                return 0.5

        # Normalize timezone handling for comparison
        # Both must be naive or both must be aware
        if hasattr(timestamp, "tzinfo") and timestamp.tzinfo is not None:
            # Timestamp is timezone-aware
            if now.tzinfo is None:
                # Make now timezone-aware (assume UTC)
                now = now.replace(tzinfo=UTC)
        else:
            # Timestamp is naive
            if now.tzinfo is not None:
                # Make now naive
                now = now.replace(tzinfo=None)

        # Calculate age in days
        age = now - timestamp
        age_days = age.total_seconds() / (24 * 3600)

        if age_days < 0:
            # Future timestamp - treat as very recent
            return 1.0

        # Exponential decay: score = 0.5^(age / half_life)
        half_life = self.weights.recency_half_life_days
        score = math.pow(0.5, age_days / half_life)

        return min(1.0, max(0.0, score))

    def rerank(
        self,
        results: list[RankedResult],
        boost_factors: dict[str, float] | None = None,
    ) -> list[RankedResult]:
        """Re-rank results with additional boost factors.

        Args:
            results: Already ranked results.
            boost_factors: Map of content_id to boost multiplier (e.g., 1.2 for 20% boost).

        Returns:
            Re-ranked results.
        """
        if not boost_factors:
            return results

        for result in results:
            boost = boost_factors.get(result.content_id, 1.0)
            result.composite_score = min(1.0, result.composite_score * boost)

        results.sort(key=lambda r: r.composite_score, reverse=True)
        return results

    def explain_ranking(self, result: RankedResult) -> str:
        """Generate human-readable explanation of ranking.

        Args:
            result: Ranked result to explain.

        Returns:
            Explanation string.
        """
        parts = [
            f"Composite Score: {result.composite_score:.3f}",
            f"  - Similarity: {result.similarity_score:.3f} (weight: {self.weights.similarity_weight:.2f})",
            f"  - Taxonomy: {result.taxonomy_score:.3f} (weight: {self.weights.taxonomy_weight:.2f})",
            f"  - Recency: {result.recency_score:.3f} (weight: {self.weights.recency_weight:.2f})",
        ]
        return "\n".join(parts)

    def get_weights(self) -> RankingWeights:
        """Get current ranking weights."""
        return self.weights

    def set_weights(self, weights: RankingWeights) -> None:
        """Update ranking weights.

        Args:
            weights: New weights (will be normalized).
        """
        self.weights = weights.normalize()
