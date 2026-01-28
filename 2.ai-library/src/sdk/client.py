# src/sdk/client.py
"""
Claude Code SDK wrapper for AI-powered decision making.

Provides structured JSON outputs for:
- Cleanup plans (discard suggestions)
- Routing plans (destination options)

File writes are NEVER performed by the SDK - only by our verified writer.
"""

import json
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
try:
    from claude_code_sdk import query, ClaudeCodeOptions
except ModuleNotFoundError as e:  # pragma: no cover
    query = None  # type: ignore[assignment]
    ClaudeCodeOptions = None  # type: ignore[assignment]
    _CLAUDE_CODE_SDK_IMPORT_ERROR = e
else:  # pragma: no cover
    _CLAUDE_CODE_SDK_IMPORT_ERROR = None

from ..utils.async_helpers import _run_sync
from ..utils.validation import normalize_confidence
from ..utils.similarity import find_similar_blocks, group_duplicates, build_similarity_map
from .auth import load_oauth_token

from ..models.cleanup_plan import (
    CleanupPlan,
    CleanupItem,
    CleanupDisposition,
)
from ..models.routing_plan import (
    RoutingPlan,
    BlockRoutingItem,
    BlockDestination,
    PlanSummary,
)
from .prompts.cleanup_mode import CLEANUP_SYSTEM_PROMPT, build_cleanup_prompt, CONTENT_PREVIEW_LIMIT
from .prompts.routing_mode import ROUTING_SYSTEM_PROMPT, build_routing_prompt


logger = logging.getLogger(__name__)


@dataclass
class SDKResponse:
    """Response from Claude Code SDK."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None
    error: Optional[str] = None


class ClaudeCodeClient:
    """
    Client for Claude Code SDK interactions.

    Uses SDK for structured JSON responses only.
    All file operations are performed by our verified writer.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        max_turns: int = 6,
    ):
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-opus-4-5-20251101")
        self.max_turns = max_turns

        # Load and validate OAuth token (with fallback to credentials.json)
        self._auth_token = load_oauth_token()
        if not self._auth_token:
            logger.error(
                "OAuth token not available - AI suggestions will fail. "
                "Set ANTHROPIC_AUTH_TOKEN env var or authenticate via automaker."
            )

    def _build_sdk_env(self) -> Dict[str, str]:
        """
        Build environment for SDK subprocess, prioritizing OAuth authentication.

        This matches Automaker's buildEnv() behavior (claude-provider.ts:88-256):
        - Pass through OAuth tokens for CLI's internal OAuth flow
        - Explicitly clear ANTHROPIC_API_KEY to prevent it from overriding OAuth
        - Pass through essential system variables

        Returns:
            Environment dictionary to pass to ClaudeCodeOptions
        """
        env: Dict[str, str] = {}

        # Pass through OAuth token if available (CLI handles OAuth internally)
        oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
        if oauth_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
            logger.debug("SDK env: CLAUDE_CODE_OAUTH_TOKEN set (CLI will handle OAuth)")

        # Pass through explicit auth token if set
        auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
        if auth_token:
            env["ANTHROPIC_AUTH_TOKEN"] = auth_token
            logger.debug("SDK env: ANTHROPIC_AUTH_TOKEN set")

        # CRITICAL: Explicitly clear API key to prevent it from overriding OAuth
        # Even if it's set in parent environment, we don't want SDK to use it
        # Setting to empty string overrides any inherited value
        env["ANTHROPIC_API_KEY"] = ""

        # Pass through essential system variables
        for var in ["PATH", "HOME", "SHELL", "TERM", "USER", "LANG", "LC_ALL",
                    "TMPDIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME"]:
            value = os.environ.get(var)
            if value:
                env[var] = value

        return env

    async def query_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> SDKResponse:
        """Send a text query to Claude Code SDK.

        Public method for queries expecting plain text responses (not JSON).

        Args:
            system_prompt: System instructions
            user_prompt: User message

        Returns:
            SDKResponse with raw_response containing the text
        """
        return await self._query(system_prompt, user_prompt, expect_json=False)

    async def _query(
        self,
        system_prompt: str,
        user_prompt: str,
        expect_json: bool = True,
    ) -> SDKResponse:
        """
        Send a query to Claude Code SDK.

        Args:
            system_prompt: System instructions
            user_prompt: User message

        Returns:
            SDKResponse with parsed data or error
        """
        if query is None or ClaudeCodeOptions is None:
            raise RuntimeError(
                "claude-code-sdk is required to use ClaudeCodeClient; "
                "install project dependencies to enable AI planning."
            ) from _CLAUDE_CODE_SDK_IMPORT_ERROR

        # Check auth before attempting query
        # Accept either:
        # 1. ANTHROPIC_AUTH_TOKEN set (explicit token)
        # 2. CLAUDE_CODE_OAUTH_TOKEN set (CLI handles OAuth internally)
        # 3. Our auth token marker indicating CLI OAuth mode
        has_auth = (
            os.getenv("ANTHROPIC_AUTH_TOKEN")
            or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
            or self._auth_token == "__CLI_HANDLES_OAUTH__"
        )
        if not has_auth:
            error_msg = (
                "No OAuth authentication available. "
                "Set CLAUDE_CODE_OAUTH_TOKEN environment variable "
                "or authenticate via 'claude login'."
            )
            logger.error("SDK query failed: %s", error_msg)
            return SDKResponse(success=False, error=error_msg)

        try:
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.max_turns,
                model=self.model,
                env=self._build_sdk_env(),
            )

            response_text = ""
            async for message in query(
                prompt=user_prompt,
                options=options,
            ):
                # SDK returns AssistantMessage objects with content lists
                # containing TextBlock objects that have .text attributes
                content = getattr(message, "content", None)
                if isinstance(content, list):
                    for block in content:
                        # Extract text from TextBlock objects (skip ThinkingBlock, etc.)
                        if hasattr(block, "text"):
                            response_text += block.text

            # Try to extract JSON from response if expected
            data = None
            error = None

            if expect_json:
                data = self._extract_json(response_text)
                if not data:
                    error = "Could not parse JSON from response"
            
            if not expect_json or data:
                return SDKResponse(
                    success=True if not error else False,
                    data=data,
                    raw_response=response_text,
                    error=error,
                )
            else:
                 return SDKResponse(
                    success=False,
                    raw_response=response_text,
                    error=error,
                )

        except Exception as e:
            logger.error("SDK query failed: %s", str(e))
            return SDKResponse(
                success=False,
                error=str(e),
            )

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text using safe parsing."""
        # 1. Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Try to find markdown code blocks (```json or just ```)
        # We iterate to find a block that contains valid JSON
        current_pos = 0
        while True:
            start_marker = text.find("```", current_pos)
            if start_marker == -1:
                break
            
            # Find end of the line (start of content)
            newline_pos = text.find("\n", start_marker)
            if newline_pos == -1:
                break # Malformed block
            
            content_start = newline_pos + 1
            
            # Find end marker
            end_marker = text.find("```", content_start)
            if end_marker == -1:
                break
            
            candidate = text[content_start:end_marker].strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # This block wasn't valid JSON, continue searching
                current_pos = end_marker + 3
                continue

        # 3. Fallback: Find the first '{' and the last '}'
        # This is a heuristic that works for most single-object responses
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(text[start_idx : end_idx + 1])
            except json.JSONDecodeError:
                pass

        return None

    async def generate_cleanup_plan(
        self,
        session_id: str,
        source_file: str,
        blocks: List[Dict[str, Any]],
        content_mode: str = "strict",
        conversation_history: str = "",
        pending_questions: Optional[List[str]] = None,
    ) -> CleanupPlan:
        """
        Generate a cleanup plan using Claude Code SDK.

        Args:
            session_id: Current session ID
            source_file: Source file path
            blocks: List of block dictionaries
            content_mode: "strict" or "refinement"

        Returns:
            CleanupPlan with AI suggestions
        """
        # Run duplicate detection before AI analysis
        similarities = find_similar_blocks(blocks, threshold=0.75)
        duplicate_groups = group_duplicates(similarities)
        similarity_map = build_similarity_map(similarities)

        user_prompt = build_cleanup_prompt(
            blocks=blocks,
            source_file=source_file,
            content_mode=content_mode,
            conversation_history=conversation_history,
            pending_questions=pending_questions,
        )

        response = await self._query(CLEANUP_SYSTEM_PROMPT, user_prompt)

        # Track generation status for transparency
        ai_generated = response.success and response.data is not None
        generation_error: Optional[str] = None

        if not response.success:
            generation_error = response.error
            logger.warning(
                "Cleanup AI generation failed: %s. Using default keep-all suggestions.",
                response.error,
            )

        block_map = {b["id"]: b for b in blocks}
        suggested_by_block_id: dict[str, dict[str, Any]] = {}

        if response.success and response.data:
            for item_data in response.data.get("cleanup_items", []):
                block_id = item_data.get("block_id")
                if block_id in block_map:
                    suggested_by_block_id[block_id] = item_data

        # Always return one item per input block (no silent drops)
        items = []
        for block in blocks:
            block_id = block["id"]
            content = block.get("content", "")
            content_length = len(content)
            is_truncated = content_length > CONTENT_PREVIEW_LIMIT

            # Get similarity data for this block
            similar_ids, max_similarity = similarity_map.get(block_id, ([], None))

            item_data = suggested_by_block_id.get(block_id)
            if item_data:
                # AI provided analysis for this block
                suggested_disposition = item_data.get(
                    "suggested_disposition", CleanupDisposition.KEEP
                )
                suggestion_reason = item_data.get("suggestion_reason", "")
                confidence = normalize_confidence(item_data.get("confidence"), log=logger)
                ai_analyzed = True
            else:
                # AI omitted this block - use defaults
                suggested_disposition = CleanupDisposition.KEEP
                suggestion_reason = (
                    "Default: keep all content (AI omitted this block from analysis)"
                    if response.success
                    else "Default: keep all content (AI analysis unavailable)"
                )
                confidence = 0.5
                ai_analyzed = False
                if response.success:
                    logger.debug(
                        "Cleanup item omitted for block %s; defaulting confidence to 0.5",
                        block_id,
                    )

            items.append(
                CleanupItem(
                    block_id=block_id,
                    heading_path=block.get("heading_path", []),
                    content_preview=content[:200],
                    suggested_disposition=suggested_disposition,
                    suggestion_reason=suggestion_reason,
                    confidence=confidence,
                    # AI analysis tracking
                    ai_analyzed=ai_analyzed,
                    content_truncated=is_truncated,
                    original_content_length=content_length,
                    # Duplicate detection
                    similar_block_ids=similar_ids,
                    similarity_score=max_similarity,
                )
            )

        return CleanupPlan(
            session_id=session_id,
            source_file=source_file,
            items=items,
            ai_generated=ai_generated,
            generation_error=generation_error,
            duplicate_groups=duplicate_groups,
        )

    async def generate_routing_plan(
        self,
        session_id: str,
        source_file: str,
        blocks: List[Dict[str, Any]],
        library_context: Dict[str, Any],
        content_mode: str = "strict",
        conversation_history: str = "",
        pending_questions: Optional[List[str]] = None,
    ) -> RoutingPlan:
        """
        Generate a routing plan using Claude Code SDK.

        Args:
            session_id: Current session ID
            source_file: Source file path
            blocks: List of kept block dictionaries
            library_context: Library structure/manifest
            content_mode: "strict" or "refinement"

        Returns:
            RoutingPlan with AI suggestions
        """
        user_prompt = build_routing_prompt(
            blocks=blocks,
            library_context=library_context,
            source_file=source_file,
            content_mode=content_mode,
            conversation_history=conversation_history,
            pending_questions=pending_questions,
        )

        response = await self._query(ROUTING_SYSTEM_PROMPT, user_prompt)

        # Log routing generation failures for transparency
        if not response.success:
            logger.warning(
                "Routing AI generation failed: %s. Returning empty routing options.",
                response.error,
            )

        block_map = {b["id"]: b for b in blocks}
        routing_by_block_id: dict[str, BlockRoutingItem] = {}
        summary = None

        if response.success and response.data:
            for item_data in response.data.get("routing_items", []):
                block_id = item_data.get("block_id")
                if block_id not in block_map:
                    continue

                options = []
                for opt in item_data.get("options", [])[:3]:  # Max 3 options
                    options.append(
                        BlockDestination(
                            destination_file=opt.get("destination_file", ""),
                            destination_section=opt.get("destination_section"),
                            action=opt.get("action", "append"),
                            confidence=normalize_confidence(opt.get("confidence"), log=logger),
                            reasoning=opt.get("reasoning", ""),
                            proposed_file_title=opt.get("proposed_file_title"),
                            proposed_file_overview=opt.get("proposed_file_overview"),
                            proposed_section_title=opt.get("proposed_section_title"),
                        )
                    )

                routing_by_block_id[block_id] = BlockRoutingItem(
                    block_id=block_id,
                    heading_path=block_map[block_id].get("heading_path", []),
                    content_preview=block_map[block_id]["content"][:200],
                    options=options,
                    status="pending",
                )

            # Parse summary
            if "summary" in response.data:
                s = response.data["summary"]
                summary = PlanSummary(
                    total_blocks=len(blocks),
                    blocks_to_new_files=s.get("blocks_to_new_files", 0),
                    blocks_to_existing_files=s.get("blocks_to_existing_files", 0),
                    blocks_requiring_merge=s.get("blocks_requiring_merge", 0),
                    estimated_actions=s.get("estimated_actions", len(blocks)),
                )

        # Always return one routing item per input block (no silent drops)
        routing_items = []
        for block in blocks:
            block_id = block["id"]
            item = routing_by_block_id.get(block_id)
            if item is None:
                routing_items.append(
                    BlockRoutingItem(
                        block_id=block_id,
                        heading_path=block.get("heading_path", []),
                        content_preview=block["content"][:200],
                        options=[],
                        status="pending",
                    )
                )
            else:
                routing_items.append(item)

        return RoutingPlan(
            session_id=session_id,
            source_file=source_file,
            content_mode=content_mode,
            blocks=routing_items,
            summary=summary or PlanSummary(
                total_blocks=len(blocks),
                blocks_to_new_files=0,
                blocks_to_existing_files=0,
                blocks_requiring_merge=0,
                estimated_actions=len(blocks),
            ),
        )





class ClaudeSDKClient:
    """Synchronous wrapper for simple text completions."""

    def __init__(
        self,
        model: Optional[str] = None,
        max_turns: int = 6,
        system_prompt: Optional[str] = None,
    ):
        self._client = ClaudeCodeClient(model=model, max_turns=max_turns)
        self._system_prompt = system_prompt or "You are a helpful assistant."

    async def complete_async(self, prompt: str) -> str:
        response = await self._client._query(
            self._system_prompt, 
            prompt,
            expect_json=False
        )
        if response.raw_response:
            return response.raw_response
        if response.error:
            raise RuntimeError(response.error)
        raise RuntimeError("ClaudeCodeClient returned empty response")

    def complete(self, prompt: str) -> str:
        return _run_sync(self.complete_async(prompt))
