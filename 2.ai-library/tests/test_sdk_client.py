# tests/test_sdk_client.py
"""Tests for Claude Code SDK wrapper behaviors."""

import pytest

from src.sdk.client import ClaudeCodeClient, SDKResponse
from src.utils.validation import normalize_confidence
from src.models.cleanup_plan import CleanupDisposition


@pytest.mark.asyncio
async def test_query_passes_model_into_options(monkeypatch):
    """Configured model must be passed into ClaudeCodeOptions."""
    import os
    import src.sdk.client as sdk_client

    # Set OAuth token to allow query to proceed
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "test-token")

    captured: dict = {}

    class DummyOptions:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    async def dummy_query(*, prompt, options):
        if False:  # pragma: no cover
            yield prompt, options

    monkeypatch.setattr(sdk_client, "ClaudeCodeOptions", DummyOptions)
    monkeypatch.setattr(sdk_client, "query", dummy_query)

    client = ClaudeCodeClient(model="claude-test-model")
    await client._query("system", "user")

    assert captured.get("model") == "claude-test-model"


@pytest.mark.asyncio
async def test_generate_cleanup_plan_fills_missing_blocks(monkeypatch):
    """Cleanup plan must include all blocks even if the model omits some."""
    blocks = [
        {"id": "block_001", "type": "paragraph", "content": "Alpha", "heading_path": ["H1"]},
        {"id": "block_002", "type": "paragraph", "content": "Bravo", "heading_path": ["H2"]},
        {"id": "block_003", "type": "paragraph", "content": "Charlie", "heading_path": []},
    ]

    async def fake_query(self, system_prompt, user_prompt):
        return SDKResponse(
            success=True,
            data={
                "cleanup_items": [
                    {
                        "block_id": "block_002",
                        "suggested_disposition": "keep",
                        "suggestion_reason": "Looks good",
                    }
                ]
            },
        )

    monkeypatch.setattr(ClaudeCodeClient, "_query", fake_query)

    client = ClaudeCodeClient()
    plan = await client.generate_cleanup_plan(
        session_id="sess_123",
        source_file="source.md",
        blocks=blocks,
        content_mode="strict",
    )

    assert [i.block_id for i in plan.items] == ["block_001", "block_002", "block_003"]

    missing = next(i for i in plan.items if i.block_id == "block_001")
    assert missing.suggested_disposition == CleanupDisposition.KEEP
    assert "Default" in missing.suggestion_reason
    assert missing.heading_path == ["H1"]
    assert missing.content_preview == "Alpha"


@pytest.mark.asyncio
async def test_generate_cleanup_plan_propagates_and_normalizes_confidence(monkeypatch):
    """Cleanup plan should propagate AI confidence and normalize invalid values."""
    blocks = [
        {"id": "block_001", "type": "paragraph", "content": "Alpha", "heading_path": ["H1"]},
        {"id": "block_002", "type": "paragraph", "content": "Bravo", "heading_path": ["H2"]},
        {"id": "block_003", "type": "paragraph", "content": "Charlie", "heading_path": []},
        {"id": "block_004", "type": "paragraph", "content": "Delta", "heading_path": []},
        {"id": "block_005", "type": "paragraph", "content": "Echo", "heading_path": []},
        {"id": "block_006", "type": "paragraph", "content": "Foxtrot", "heading_path": []},
    ]

    async def fake_query(self, system_prompt, user_prompt):
        return SDKResponse(
            success=True,
            data={
                "cleanup_items": [
                    {
                        "block_id": "block_001",
                        "suggested_disposition": "discard",
                        "suggestion_reason": "Noisy",
                        "confidence": 0.9,
                    },
                    {
                        "block_id": "block_002",
                        "suggested_disposition": "keep",
                        "suggestion_reason": "Fine",
                        "confidence": 1.5,  # Above max
                    },
                    {
                        "block_id": "block_003",
                        "suggested_disposition": "keep",
                        "suggestion_reason": "Fine",
                        "confidence": -0.25,  # Below min
                    },
                    {
                        "block_id": "block_004",
                        "suggested_disposition": "keep",
                        "suggestion_reason": "Fine",
                        "confidence": None,  # Missing
                    },
                    {
                        "block_id": "block_005",
                        "suggested_disposition": "keep",
                        "suggestion_reason": "Fine",
                        "confidence": "invalid",  # Invalid type
                    },
                    {
                        "block_id": "block_006",
                        "suggested_disposition": "keep",
                        "suggestion_reason": "Fine",
                        "confidence": float("nan"),  # Non-finite
                    },
                ]
            },
        )

    monkeypatch.setattr(ClaudeCodeClient, "_query", fake_query)

    client = ClaudeCodeClient()
    plan = await client.generate_cleanup_plan(
        session_id="sess_123",
        source_file="source.md",
        blocks=blocks,
        content_mode="strict",
    )

    item_by_id = {i.block_id: i for i in plan.items}
    assert item_by_id["block_001"].confidence == 0.9
    assert item_by_id["block_002"].confidence == 1.0
    assert item_by_id["block_003"].confidence == 0.0
    assert item_by_id["block_004"].confidence == 0.5
    assert item_by_id["block_005"].confidence == 0.5
    assert item_by_id["block_006"].confidence == 0.5


@pytest.mark.asyncio
async def test_generate_cleanup_plan_omitted_block_defaults_confidence_and_reason(monkeypatch):
    """Blocks omitted by the model should default to 0.5 confidence with an omitted reason."""
    blocks = [
        {"id": "block_001", "type": "paragraph", "content": "Alpha", "heading_path": ["H1"]},
        {"id": "block_002", "type": "paragraph", "content": "Bravo", "heading_path": ["H2"]},
    ]

    async def fake_query(self, system_prompt, user_prompt):
        return SDKResponse(
            success=True,
            data={
                "cleanup_items": [
                    {
                        "block_id": "block_001",
                        "suggested_disposition": "keep",
                        "suggestion_reason": "Looks good",
                        "confidence": 0.8,
                    }
                ]
            },
        )

    monkeypatch.setattr(ClaudeCodeClient, "_query", fake_query)

    client = ClaudeCodeClient()
    plan = await client.generate_cleanup_plan(
        session_id="sess_123",
        source_file="source.md",
        blocks=blocks,
        content_mode="strict",
    )

    omitted = next(i for i in plan.items if i.block_id == "block_002")
    assert omitted.confidence == 0.5
    assert "omitted" in omitted.suggestion_reason.lower()


@pytest.mark.asyncio
async def test_generate_routing_plan_fills_missing_blocks(monkeypatch):
    """Routing plan must include all blocks even if the model omits some."""
    blocks = [
        {"id": "block_001", "type": "paragraph", "content": "Alpha", "heading_path": ["H1"]},
        {"id": "block_002", "type": "paragraph", "content": "Bravo", "heading_path": ["H2"]},
    ]

    async def fake_query(self, system_prompt, user_prompt):
        return SDKResponse(
            success=True,
            data={
                "routing_items": [
                    {
                        "block_id": "block_002",
                        "options": [
                            {
                                "destination_file": "library/test.md",
                                "destination_section": "Section",
                                "action": "append",
                                "confidence": 0.9,
                                "reasoning": "Fits well",
                            }
                        ],
                    }
                ],
                "summary": {
                    "total_blocks": 2,
                    "blocks_to_new_files": 0,
                    "blocks_to_existing_files": 1,
                    "blocks_requiring_merge": 0,
                    "estimated_actions": 2,
                },
            },
        )

    monkeypatch.setattr(ClaudeCodeClient, "_query", fake_query)

    client = ClaudeCodeClient()
    plan = await client.generate_routing_plan(
        session_id="sess_123",
        source_file="source.md",
        blocks=blocks,
        library_context={},
        content_mode="strict",
    )

    assert [b.block_id for b in plan.blocks] == ["block_001", "block_002"]

    missing = next(b for b in plan.blocks if b.block_id == "block_001")
    assert missing.options == []
    assert missing.heading_path == ["H1"]
    assert missing.content_preview == "Alpha"


class TestNormalizeConfidence:
    """Tests for normalize_confidence helper function."""

    def test_normalize_confidence_valid_range(self):
        """Values within [0.0, 1.0] should be returned unchanged."""
        assert normalize_confidence(0.0) == 0.0
        assert normalize_confidence(0.5) == 0.5
        assert normalize_confidence(1.0) == 1.0
        assert normalize_confidence(0.75) == 0.75

    def test_normalize_confidence_above_max(self):
        """Values above 1.0 should be clamped to 1.0."""
        assert normalize_confidence(1.5) == 1.0
        assert normalize_confidence(2.0) == 1.0
        assert normalize_confidence(100.0) == 1.0

    def test_normalize_confidence_below_min(self):
        """Values below 0.0 should be clamped to 0.0."""
        assert normalize_confidence(-0.5) == 0.0
        assert normalize_confidence(-1.0) == 0.0
        assert normalize_confidence(-100.0) == 0.0

    def test_normalize_confidence_none_returns_default(self):
        """None values should return the default (0.5)."""
        assert normalize_confidence(None) == 0.5
        assert normalize_confidence(None, default=0.7) == 0.7

    def test_normalize_confidence_invalid_type_returns_default(self):
        """Non-numeric types should return the default."""
        assert normalize_confidence("invalid") == 0.5
        assert normalize_confidence({}) == 0.5
        assert normalize_confidence([]) == 0.5

    def test_normalize_confidence_string_number(self):
        """String representations of numbers should be converted."""
        assert normalize_confidence("0.8") == 0.8
        assert normalize_confidence("1.5") == 1.0
        assert normalize_confidence("-0.3") == 0.0

    def test_normalize_confidence_integer(self):
        """Integer values should be handled correctly."""
        assert normalize_confidence(0) == 0.0
        assert normalize_confidence(1) == 1.0
        assert normalize_confidence(2) == 1.0

    def test_normalize_confidence_non_finite_returns_default(self):
        """NaN/inf values should be treated as invalid and return default."""
        assert normalize_confidence(float("nan")) == 0.5
        assert normalize_confidence(float("inf")) == 0.5
        assert normalize_confidence(float("-inf")) == 0.5


@pytest.mark.asyncio
async def test_routing_plan_clamps_confidence(monkeypatch):
    """Routing plan must clamp confidence values from AI response."""
    blocks = [
        {"id": "block_001", "type": "paragraph", "content": "Alpha", "heading_path": ["H1"]},
    ]

    async def fake_query(self, system_prompt, user_prompt):
        return SDKResponse(
            success=True,
            data={
                "routing_items": [
                    {
                        "block_id": "block_001",
                        "options": [
                            {
                                "destination_file": "library/test.md",
                                "action": "append",
                                "confidence": 1.5,  # Above max
                                "reasoning": "High confidence",
                            },
                            {
                                "destination_file": "library/test2.md",
                                "action": "append",
                                "confidence": -0.3,  # Below min
                                "reasoning": "Negative confidence",
                            },
                            {
                                "destination_file": "library/test3.md",
                                "action": "append",
                                "confidence": None,  # Missing
                                "reasoning": "No confidence",
                            },
                        ],
                    }
                ],
            },
        )

    monkeypatch.setattr(ClaudeCodeClient, "_query", fake_query)

    client = ClaudeCodeClient()
    plan = await client.generate_routing_plan(
        session_id="sess_123",
        source_file="source.md",
        blocks=blocks,
        library_context={},
        content_mode="strict",
    )

    block = plan.blocks[0]
    assert len(block.options) == 3
    assert block.options[0].confidence == 1.0  # Clamped from 1.5
    assert block.options[1].confidence == 0.0  # Clamped from -0.3
    assert block.options[2].confidence == 0.5  # Default for None
