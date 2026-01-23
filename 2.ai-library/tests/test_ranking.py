"""Tests for composite ranking."""

from datetime import UTC, datetime, timedelta

import pytest

from src.ranking.composite import CompositeRanker, RankedResult, RankingWeights


class TestRankingWeights:
    """Tests for RankingWeights model."""

    def test_default_weights(self):
        """Test default weight values."""
        weights = RankingWeights()

        assert weights.similarity_weight == 0.6
        assert weights.taxonomy_weight == 0.25
        assert weights.recency_weight == 0.15

    def test_validate_weights(self):
        """Test weight validation."""
        valid_weights = RankingWeights(
            similarity_weight=0.6,
            taxonomy_weight=0.25,
            recency_weight=0.15,
        )
        assert valid_weights.validate_weights() is True

        invalid_weights = RankingWeights(
            similarity_weight=0.5,
            taxonomy_weight=0.5,
            recency_weight=0.5,
        )
        assert invalid_weights.validate_weights() is False

    def test_normalize_weights(self):
        """Test weight normalization."""
        weights = RankingWeights(
            similarity_weight=1.0,
            taxonomy_weight=1.0,
            recency_weight=1.0,
        )

        normalized = weights.normalize()

        assert abs(normalized.similarity_weight - 1/3) < 0.01
        assert abs(normalized.taxonomy_weight - 1/3) < 0.01
        assert abs(normalized.recency_weight - 1/3) < 0.01


class TestCompositeRanker:
    """Tests for CompositeRanker."""

    @pytest.fixture
    def ranker(self):
        """Create a ranker with default weights."""
        return CompositeRanker()

    @pytest.fixture
    def sample_results(self):
        """Create sample search results."""
        now = datetime.now(UTC)
        return [
            {
                "id": "content-1",
                "score": 0.95,
                "payload": {
                    "taxonomy_path": "technical/programming/python",
                    "created_at": (now - timedelta(days=7)).isoformat(),
                },
            },
            {
                "id": "content-2",
                "score": 0.85,
                "payload": {
                    "taxonomy_path": "technical/programming",
                    "created_at": (now - timedelta(days=30)).isoformat(),
                },
            },
            {
                "id": "content-3",
                "score": 0.70,
                "payload": {
                    "taxonomy_path": "technical/architecture",
                    "created_at": (now - timedelta(days=1)).isoformat(),
                },
            },
        ]

    def test_rank_basic(self, ranker, sample_results):
        """Test basic ranking functionality."""
        ranked = ranker.rank(sample_results)

        assert len(ranked) == 3
        # Results should be sorted by composite score
        assert ranked[0].composite_score >= ranked[1].composite_score
        assert ranked[1].composite_score >= ranked[2].composite_score

    def test_rank_with_taxonomy_path(self, ranker, sample_results):
        """Test ranking with query taxonomy path."""
        ranked = ranker.rank(
            sample_results,
            query_taxonomy_path="technical/programming/python",
        )

        # Content-1 should rank highest (exact taxonomy match + high similarity)
        assert ranked[0].content_id == "content-1"
        assert ranked[0].taxonomy_score == 1.0

    def test_taxonomy_score_exact_match(self, ranker):
        """Test taxonomy scoring for exact match."""
        score = ranker._compute_taxonomy_score(
            "technical/programming/python",
            "technical/programming/python",
        )
        assert score == 1.0

    def test_taxonomy_score_parent_match(self, ranker):
        """Test taxonomy scoring when result is parent."""
        score = ranker._compute_taxonomy_score(
            "technical/programming/python",
            "technical/programming",
        )
        # Result is more general (parent of query)
        assert 0.4 < score < 0.8

    def test_taxonomy_score_child_match(self, ranker):
        """Test taxonomy scoring when result is child."""
        score = ranker._compute_taxonomy_score(
            "technical/programming",
            "technical/programming/python",
        )
        # Result is more specific (child of query)
        assert 0.6 < score < 1.0

    def test_taxonomy_score_sibling_match(self, ranker):
        """Test taxonomy scoring for siblings."""
        score = ranker._compute_taxonomy_score(
            "technical/programming/python",
            "technical/programming/rust",
        )
        # Siblings (same parent)
        assert 0.3 < score < 0.7

    def test_taxonomy_score_different_branch(self, ranker):
        """Test taxonomy scoring for different branches."""
        score = ranker._compute_taxonomy_score(
            "technical/programming",
            "domain/business",
        )
        # Different top-level categories
        assert score == 0.0

    def test_taxonomy_score_none_paths(self, ranker):
        """Test taxonomy scoring with None paths."""
        assert ranker._compute_taxonomy_score(None, "technical") == 0.0
        assert ranker._compute_taxonomy_score("technical", "") == 0.0

    def test_recency_score_new_content(self, ranker):
        """Test recency scoring for new content."""
        now = datetime.now(UTC)
        score = ranker._compute_recency_score(
            now.isoformat(), None, now
        )
        # Very recent should be close to 1.0
        assert score > 0.95

    def test_recency_score_old_content(self, ranker):
        """Test recency scoring for old content."""
        now = datetime.now(UTC)
        old_date = now - timedelta(days=90)
        score = ranker._compute_recency_score(
            old_date.isoformat(), None, now
        )
        # 90 days with 30-day half-life: 0.5^3 = 0.125
        assert 0.1 < score < 0.2

    def test_recency_score_half_life(self, ranker):
        """Test recency scoring at exactly half-life."""
        now = datetime.now(UTC)
        half_life_ago = now - timedelta(days=30)  # Default half-life is 30 days
        score = ranker._compute_recency_score(
            half_life_ago.isoformat(), None, now
        )
        # At half-life, score should be 0.5
        assert abs(score - 0.5) < 0.01

    def test_recency_score_updated_at_preferred(self, ranker):
        """Test that updated_at is used over created_at."""
        now = datetime.now(UTC)
        old_created = now - timedelta(days=60)
        recent_updated = now - timedelta(days=5)

        score = ranker._compute_recency_score(
            old_created.isoformat(),
            recent_updated.isoformat(),
            now,
        )

        # Should use the recent updated date
        assert score > 0.8

    def test_recency_score_no_timestamp(self, ranker):
        """Test recency scoring when no timestamp available."""
        now = datetime.now(UTC)
        score = ranker._compute_recency_score(None, None, now)
        # Default for unknown age
        assert score == 0.5

    def test_score_breakdown(self, ranker, sample_results):
        """Test that score breakdown is included."""
        ranked = ranker.rank(sample_results)

        for result in ranked:
            assert "similarity_weighted" in result.score_breakdown
            assert "taxonomy_weighted" in result.score_breakdown
            assert "recency_weighted" in result.score_breakdown

    def test_rerank_with_boost(self, ranker, sample_results):
        """Test re-ranking with boost factors."""
        ranked = ranker.rank(sample_results)

        # Boost content-3 significantly
        boost_factors = {"content-3": 2.0}
        reranked = ranker.rerank(ranked, boost_factors)

        # content-3 should now be first (with capped score)
        assert reranked[0].content_id == "content-3"
        assert reranked[0].composite_score == 1.0  # Capped at 1.0

    def test_explain_ranking(self, ranker, sample_results):
        """Test ranking explanation."""
        ranked = ranker.rank(sample_results)

        explanation = ranker.explain_ranking(ranked[0])

        assert "Composite Score" in explanation
        assert "Similarity" in explanation
        assert "Taxonomy" in explanation
        assert "Recency" in explanation

    def test_custom_weights(self):
        """Test ranker with custom weights."""
        # Weight heavily towards recency
        weights = RankingWeights(
            similarity_weight=0.2,
            taxonomy_weight=0.2,
            recency_weight=0.6,
        )
        ranker = CompositeRanker(weights)

        now = datetime.now(UTC)
        results = [
            {
                "id": "old-high-sim",
                "score": 0.95,
                "payload": {
                    "created_at": (now - timedelta(days=60)).isoformat(),
                },
            },
            {
                "id": "new-low-sim",
                "score": 0.5,
                "payload": {
                    "created_at": now.isoformat(),
                },
            },
        ]

        ranked = ranker.rank(results)

        # New content should win despite lower similarity
        assert ranked[0].content_id == "new-low-sim"

    def test_set_weights(self, ranker):
        """Test updating weights."""
        new_weights = RankingWeights(
            similarity_weight=0.5,
            taxonomy_weight=0.3,
            recency_weight=0.2,
        )

        ranker.set_weights(new_weights)
        current = ranker.get_weights()

        assert current.similarity_weight == 0.5
        assert current.taxonomy_weight == 0.3
        assert current.recency_weight == 0.2


class TestRankedResult:
    """Tests for RankedResult model."""

    def test_create_ranked_result(self):
        """Test creating a ranked result."""
        result = RankedResult(
            content_id="test-1",
            composite_score=0.85,
            similarity_score=0.9,
            taxonomy_score=0.8,
            recency_score=0.7,
            payload={"title": "Test Content"},
            score_breakdown={
                "similarity_weighted": 0.54,
                "taxonomy_weighted": 0.2,
                "recency_weighted": 0.105,
            },
        )

        assert result.content_id == "test-1"
        assert result.composite_score == 0.85
        assert result.payload["title"] == "Test Content"
