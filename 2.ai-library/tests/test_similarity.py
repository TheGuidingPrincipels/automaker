# tests/test_similarity.py
"""Tests for duplicate detection utilities."""

import pytest
from src.utils.similarity import (
    normalize_text,
    compute_shingles,
    jaccard_similarity,
    find_similar_blocks,
    group_duplicates,
    build_similarity_map,
)


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_lowercase(self):
        assert normalize_text("Hello World") == "hello world"

    def test_collapse_whitespace(self):
        assert normalize_text("hello    world") == "hello world"
        assert normalize_text("hello\n\nworld") == "hello world"
        assert normalize_text("hello\t\tworld") == "hello world"

    def test_strip_leading_trailing(self):
        assert normalize_text("  hello world  ") == "hello world"

    def test_combined(self):
        assert normalize_text("  Hello   WORLD  \n") == "hello world"


class TestComputeShingles:
    """Tests for compute_shingles function."""

    def test_basic_shingles(self):
        text = "one two three four five"
        shingles = compute_shingles(text, n=3)
        # Should have 3 shingles: (one, two, three), (two, three, four), (three, four, five)
        assert len(shingles) == 3
        assert ("one", "two", "three") in shingles
        assert ("two", "three", "four") in shingles
        assert ("three", "four", "five") in shingles

    def test_short_text_uses_character_shingles(self):
        text = "ab"
        shingles = compute_shingles(text, n=3)
        # Falls back to character-level shingles
        assert isinstance(shingles, set)

    def test_empty_text(self):
        shingles = compute_shingles("", n=3)
        assert isinstance(shingles, set)


class TestJaccardSimilarity:
    """Tests for jaccard_similarity function."""

    def test_identical_sets(self):
        a = {1, 2, 3}
        b = {1, 2, 3}
        assert jaccard_similarity(a, b) == 1.0

    def test_disjoint_sets(self):
        a = {1, 2, 3}
        b = {4, 5, 6}
        assert jaccard_similarity(a, b) == 0.0

    def test_partial_overlap(self):
        a = {1, 2, 3}
        b = {2, 3, 4}
        # intersection: {2, 3} = 2, union: {1, 2, 3, 4} = 4
        assert jaccard_similarity(a, b) == 0.5

    def test_both_empty(self):
        assert jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self):
        assert jaccard_similarity({1, 2}, set()) == 0.0
        assert jaccard_similarity(set(), {1, 2}) == 0.0


class TestFindSimilarBlocks:
    """Tests for find_similar_blocks function."""

    def test_exact_duplicates(self):
        blocks = [
            {"id": "b1", "content": "This is a long content block that should be detected as a duplicate of another block with the same content."},
            {"id": "b2", "content": "This is a long content block that should be detected as a duplicate of another block with the same content."},
        ]
        similarities = find_similar_blocks(blocks, threshold=0.9)
        assert len(similarities) == 1
        assert similarities[0][0] == "b1"
        assert similarities[0][1] == "b2"
        assert similarities[0][2] == 1.0

    def test_near_duplicates(self):
        blocks = [
            {"id": "b1", "content": "This is a long content block about machine learning and artificial intelligence. It discusses neural networks and deep learning algorithms."},
            {"id": "b2", "content": "This is a long content block about machine learning and artificial intelligence. It discusses neural networks and modern learning algorithms."},
        ]
        similarities = find_similar_blocks(blocks, threshold=0.5)
        assert len(similarities) == 1
        assert similarities[0][2] >= 0.5

    def test_distinct_content_not_flagged(self):
        blocks = [
            {"id": "b1", "content": "This block discusses machine learning algorithms and neural network architectures."},
            {"id": "b2", "content": "This block covers database design patterns and SQL optimization techniques."},
        ]
        similarities = find_similar_blocks(blocks, threshold=0.75)
        assert len(similarities) == 0

    def test_short_content_skipped(self):
        blocks = [
            {"id": "b1", "content": "Short"},
            {"id": "b2", "content": "Short"},
        ]
        similarities = find_similar_blocks(blocks, threshold=0.5, min_content_length=50)
        assert len(similarities) == 0

    def test_sorted_by_score_descending(self):
        blocks = [
            {"id": "b1", "content": "This is content A about topic one for testing similarity detection algorithms."},
            {"id": "b2", "content": "This is content A about topic one for testing similarity detection systems."},
            {"id": "b3", "content": "This is content A about topic two for testing something completely different."},
        ]
        similarities = find_similar_blocks(blocks, threshold=0.3)
        if len(similarities) > 1:
            scores = [s[2] for s in similarities]
            assert scores == sorted(scores, reverse=True)


class TestGroupDuplicates:
    """Tests for group_duplicates function."""

    def test_single_pair(self):
        similarities = [("b1", "b2", 0.9)]
        groups = group_duplicates(similarities)
        assert len(groups) == 1
        assert set(groups[0]) == {"b1", "b2"}

    def test_transitive_grouping(self):
        # b1-b2 and b2-b3 should result in one group {b1, b2, b3}
        similarities = [("b1", "b2", 0.9), ("b2", "b3", 0.85)]
        groups = group_duplicates(similarities)
        assert len(groups) == 1
        assert set(groups[0]) == {"b1", "b2", "b3"}

    def test_separate_groups(self):
        similarities = [("b1", "b2", 0.9), ("b3", "b4", 0.85)]
        groups = group_duplicates(similarities)
        assert len(groups) == 2

    def test_empty_input(self):
        groups = group_duplicates([])
        assert groups == []


class TestBuildSimilarityMap:
    """Tests for build_similarity_map function."""

    def test_basic_mapping(self):
        similarities = [("b1", "b2", 0.9)]
        sim_map = build_similarity_map(similarities)

        assert "b1" in sim_map
        assert "b2" in sim_map

        similar_ids, max_score = sim_map["b1"]
        assert "b2" in similar_ids
        assert max_score == 0.9

        similar_ids, max_score = sim_map["b2"]
        assert "b1" in similar_ids
        assert max_score == 0.9

    def test_multiple_similarities(self):
        similarities = [("b1", "b2", 0.9), ("b1", "b3", 0.7)]
        sim_map = build_similarity_map(similarities)

        similar_ids, max_score = sim_map["b1"]
        assert set(similar_ids) == {"b2", "b3"}
        assert max_score == 0.9  # Highest score

    def test_empty_input(self):
        sim_map = build_similarity_map([])
        assert sim_map == {}
