# tests/test_sdk_client.py
"""Tests for Claude Code SDK wrapper behaviors."""

import pytest

from src.sdk.client import ClaudeCodeClient, SDKResponse
from src.models.cleanup_plan import CleanupDisposition


@pytest.mark.asyncio
async def test_query_passes_model_into_options(monkeypatch):
    """Configured model must be passed into ClaudeCodeOptions."""
    import src.sdk.client as sdk_client

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
