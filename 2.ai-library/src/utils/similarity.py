# src/utils/similarity.py
"""
Duplicate detection utilities using text similarity.

Uses shingling (n-gram sets) and Jaccard similarity for comparing content.
No external dependencies - pure Python implementation.
"""

import re
from typing import Dict, List, Tuple, Any
from collections import defaultdict


def normalize_text(content: str) -> str:
    """
    Normalize text for comparison.

    - Lowercase
    - Remove extra whitespace
    - Strip punctuation except for code-significant characters
    """
    # Lowercase
    text = content.lower()
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def compute_shingles(text: str, n: int = 3) -> set:
    """
    Compute n-gram shingles for text.

    Args:
        text: Normalized text to shingle
        n: Size of shingles (default 3 words)

    Returns:
        Set of n-gram shingles
    """
    words = text.split()
    if len(words) < n:
        # For very short texts, use character-level shingles
        return set(text[i:i+n] for i in range(max(1, len(text) - n + 1)))
    return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """
    Compute Jaccard similarity coefficient between two sets.

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not set_a and not set_b:
        return 1.0  # Both empty = identical
    if not set_a or not set_b:
        return 0.0  # One empty, one not = no similarity
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def find_similar_blocks(
    blocks: List[Dict[str, Any]],
    threshold: float = 0.75,
    min_content_length: int = 50,
) -> List[Tuple[str, str, float]]:
    """
    Find pairs of similar blocks above the similarity threshold.

    Args:
        blocks: List of block dictionaries with 'id' and 'content' keys
        threshold: Minimum Jaccard similarity to consider as similar (default 0.75)
        min_content_length: Minimum content length to consider for comparison

    Returns:
        List of (block_id_1, block_id_2, similarity_score) tuples, sorted by score descending
    """
    # Precompute normalized text and shingles for each block
    block_shingles: Dict[str, set] = {}
    for block in blocks:
        block_id = block.get("id", "")
        content = block.get("content", "")

        # Skip very short content that would produce unreliable similarity scores
        if len(content) < min_content_length:
            continue

        normalized = normalize_text(content)
        shingles = compute_shingles(normalized)
        block_shingles[block_id] = shingles

    # Compare all pairs
    similar_pairs: List[Tuple[str, str, float]] = []
    block_ids = list(block_shingles.keys())

    for i, id_a in enumerate(block_ids):
        for id_b in block_ids[i + 1:]:
            similarity = jaccard_similarity(block_shingles[id_a], block_shingles[id_b])
            if similarity >= threshold:
                similar_pairs.append((id_a, id_b, similarity))

    # Sort by similarity descending
    similar_pairs.sort(key=lambda x: x[2], reverse=True)
    return similar_pairs


def group_duplicates(
    similarities: List[Tuple[str, str, float]]
) -> List[List[str]]:
    """
    Group related blocks into duplicate clusters using union-find.

    Args:
        similarities: List of (block_id_1, block_id_2, score) from find_similar_blocks

    Returns:
        List of groups, where each group is a list of block IDs that are similar to each other
    """
    if not similarities:
        return []

    # Union-Find implementation
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])  # Path compression
        return parent[x]

    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Union all similar pairs
    for id_a, id_b, _ in similarities:
        union(id_a, id_b)

    # Group by root parent
    groups_dict: Dict[str, List[str]] = defaultdict(list)
    for block_id in parent:
        root = find(block_id)
        groups_dict[root].append(block_id)

    # Convert to list of groups, filtering out singletons
    groups = [sorted(group) for group in groups_dict.values() if len(group) > 1]

    # Sort groups by size descending
    groups.sort(key=len, reverse=True)
    return groups


def build_similarity_map(
    similarities: List[Tuple[str, str, float]]
) -> Dict[str, Tuple[List[str], float]]:
    """
    Build a map from block_id to (list of similar block IDs, max similarity score).

    Args:
        similarities: List of (block_id_1, block_id_2, score) from find_similar_blocks

    Returns:
        Dict mapping block_id -> (similar_block_ids, max_score)
    """
    similarity_data: Dict[str, Dict[str, float]] = defaultdict(dict)

    for id_a, id_b, score in similarities:
        # Track both directions
        similarity_data[id_a][id_b] = max(similarity_data[id_a].get(id_b, 0), score)
        similarity_data[id_b][id_a] = max(similarity_data[id_b].get(id_a, 0), score)

    result: Dict[str, Tuple[List[str], float]] = {}
    for block_id, similar in similarity_data.items():
        similar_ids = list(similar.keys())
        max_score = max(similar.values()) if similar else 0.0
        result[block_id] = (similar_ids, max_score)

    return result
