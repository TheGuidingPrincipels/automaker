# tests/test_prompts.py
"""Tests for SDK prompt builders."""

from src.sdk.prompts.routing_mode import build_routing_prompt


def test_routing_prompt_includes_block_candidates():
    """Routing prompt should include CandidateFinder hints when provided."""
    blocks = [
        {
            "id": "block_001",
            "type": "paragraph",
            "content": "JWT tokens must be validated on every request.",
            "heading_path": ["Authentication"],
        }
    ]
    library_context = {
        "summary": {},
        "categories": [],
        "block_candidates": {
            "block_001": [
                {
                    "file_path": "tech/authentication.md",
                    "section": "JWT Tokens",
                    "score": 0.91,
                    "match_reasons": ["TF-IDF: 0.42"],
                }
            ]
        },
    }

    prompt = build_routing_prompt(
        blocks=blocks,
        library_context=library_context,
        source_file="source.md",
        content_mode="strict",
    )

    assert "block_candidates" not in prompt.lower()
    assert "tech/authentication.md" in prompt
