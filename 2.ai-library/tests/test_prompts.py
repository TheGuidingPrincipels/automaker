# tests/test_prompts.py
"""Tests for SDK prompt builders."""

import pytest

from src.models.cleanup_mode_setting import CleanupModeSetting
from src.sdk.prompts.cleanup_mode import (
    CLEANUP_SYSTEM_PROMPT_CONSERVATIVE,
    CLEANUP_SYSTEM_PROMPT_BALANCED,
    CLEANUP_SYSTEM_PROMPT_AGGRESSIVE,
    CONTENT_PREVIEW_LIMIT,
    build_cleanup_prompt,
    get_cleanup_system_prompt,
)
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


def test_cleanup_prompts_include_never_echo_secrets_rule():
    """All cleanup prompts must include a 'Never echo secrets' rule."""
    prompts = (
        CLEANUP_SYSTEM_PROMPT_CONSERVATIVE,
        CLEANUP_SYSTEM_PROMPT_BALANCED,
        CLEANUP_SYSTEM_PROMPT_AGGRESSIVE,
    )

    for prompt in prompts:
        assert "Never echo secrets" in prompt


def test_get_cleanup_system_prompt_rejects_unknown_mode():
    """Unknown cleanup modes must raise errors (no silent fallback)."""
    with pytest.raises(ValueError):
        get_cleanup_system_prompt("invalid")  # type: ignore[arg-type]


def test_build_cleanup_prompt_rejects_unknown_mode():
    """Prompt builder must reject unknown cleanup modes."""
    blocks = [
        {
            "id": "block_001",
            "type": "paragraph",
            "content": "Example content",
            "heading_path": ["H1"],
        }
    ]

    with pytest.raises(ValueError):
        build_cleanup_prompt(
            blocks=blocks,
            source_file="source.md",
            content_mode="strict",
            cleanup_mode="invalid",  # type: ignore[arg-type]
        )


def test_build_cleanup_prompt_truncates_preview():
    """Prompt builder must truncate previews at CONTENT_PREVIEW_LIMIT."""
    content = ("A" * CONTENT_PREVIEW_LIMIT) + "ENDMARKER"
    blocks = [
        {
            "id": "block_001",
            "type": "paragraph",
            "content": content,
            "heading_path": [],
        }
    ]

    prompt = build_cleanup_prompt(
        blocks=blocks,
        source_file="source.md",
        content_mode="strict",
        cleanup_mode=CleanupModeSetting.BALANCED,
    )

    assert f"{'A' * CONTENT_PREVIEW_LIMIT}..." in prompt
    assert "ENDMARKER" not in prompt
