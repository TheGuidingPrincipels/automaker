# src/merge/proposer.py
"""
Merge proposal generation using AI.

Creates proposed merged content that combines source block with
existing library content, preserving all information.
"""

import json
from dataclasses import dataclass
from typing import Dict, Any, Optional

from ..sdk.client import ClaudeCodeClient
from .detector import MergeCandidate


@dataclass
class MergeProposal:
    """A proposed merge of source block with existing content."""
    merge_id: str                    # Unique ID for this merge proposal
    block_id: str                    # Source block ID
    target_file: str                 # Target file path
    target_section: Optional[str]    # Target section (if applicable)
    original_content: str            # Original existing content
    source_content: str              # Source block content
    proposed_merged: str             # AI-generated merged content
    merge_strategy: str              # "append" | "prepend" | "interleave" | "restructure"
    reasoning: str                   # Explanation of merge approach


MERGE_SYSTEM_PROMPT = """You are a content merger that combines related content while preserving ALL information.

Your task is to merge a source block with existing library content. You MUST:
1. Preserve EVERY piece of information from both sources
2. Remove redundancy only if the exact same information appears in both
3. Maintain consistent structure and formatting
4. Organize content logically

CRITICAL: Never lose any information. If in doubt, keep both versions.

Output JSON format:
{
    "proposed_merged": "The merged content preserving all information",
    "merge_strategy": "append|prepend|interleave|restructure",
    "reasoning": "Explanation of how content was merged"
}"""


def build_merge_prompt(
    source_content: str,
    existing_content: str,
    context: Dict[str, Any],
) -> str:
    """Build prompt for merge proposal."""
    return f"""Merge the following source content with the existing library content.

## Existing Library Content
File: {context.get('target_file', 'unknown')}
Section: {context.get('target_section', 'N/A')}

```
{existing_content}
```

## Source Content to Merge
Block ID: {context.get('block_id', 'unknown')}

```
{source_content}
```

## Shared Concepts
{', '.join(context.get('overlap_phrases', []))}

Create a merged version that preserves ALL information from both sources.
Remove redundancy ONLY for exact duplicates.

Return JSON with proposed_merged, merge_strategy, and reasoning."""


class MergeProposer:
    """
    Generates merge proposals using AI.

    Takes merge candidates from MergeDetector and creates
    proposed merged content for user review.
    """

    def __init__(self, sdk_client: Optional[ClaudeCodeClient] = None):
        """
        Initialize the merge proposer.

        Args:
            sdk_client: Claude Code SDK client (creates default if None)
        """
        self.sdk_client = sdk_client or ClaudeCodeClient()

    async def create_merge_proposal(
        self,
        candidate: MergeCandidate,
        source_block: Dict[str, Any],
        full_target_content: str,
    ) -> MergeProposal:
        """
        Create a merge proposal for a candidate.

        Args:
            candidate: The merge candidate from detector
            source_block: Source block dictionary
            full_target_content: Full content of the target file/section

        Returns:
            MergeProposal with AI-generated merged content
        """
        import uuid

        merge_id = str(uuid.uuid4())[:8]
        source_content = source_block.get("content", "")

        # Build context for prompt
        context = {
            "block_id": candidate.block_id,
            "target_file": candidate.target_file,
            "target_section": candidate.target_section,
            "overlap_phrases": candidate.overlap_phrases,
        }

        # Generate merge using SDK
        prompt = build_merge_prompt(source_content, full_target_content, context)

        response = await self.sdk_client._query(MERGE_SYSTEM_PROMPT, prompt)

        if response.success and response.data:
            proposed = response.data.get("proposed_merged", "")
            strategy = response.data.get("merge_strategy", "append")
            reasoning = response.data.get("reasoning", "")
        else:
            # Fallback: simple append
            proposed = f"{full_target_content}\n\n---\n\n{source_content}"
            strategy = "append"
            reasoning = "Fallback: AI generation failed, using simple append"

        return MergeProposal(
            merge_id=merge_id,
            block_id=candidate.block_id,
            target_file=candidate.target_file,
            target_section=candidate.target_section,
            original_content=full_target_content,
            source_content=source_content,
            proposed_merged=proposed,
            merge_strategy=strategy,
            reasoning=reasoning,
        )

    async def create_batch_proposals(
        self,
        candidates: list[MergeCandidate],
        source_blocks: Dict[str, Dict[str, Any]],
        target_contents: Dict[str, str],
    ) -> list[MergeProposal]:
        """
        Create merge proposals for multiple candidates.

        Args:
            candidates: List of merge candidates
            source_blocks: Dictionary mapping block_id to block dict
            target_contents: Dictionary mapping target file/section to content

        Returns:
            List of MergeProposal objects
        """
        proposals = []

        for candidate in candidates:
            source_block = source_blocks.get(candidate.block_id, {})

            # Build target key
            if candidate.target_section:
                target_key = f"{candidate.target_file}#{candidate.target_section}"
            else:
                target_key = candidate.target_file

            target_content = target_contents.get(target_key, candidate.target_content)

            proposal = await self.create_merge_proposal(
                candidate=candidate,
                source_block=source_block,
                full_target_content=target_content,
            )
            proposals.append(proposal)

        return proposals
