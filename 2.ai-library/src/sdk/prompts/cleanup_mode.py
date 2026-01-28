# src/sdk/prompts/cleanup_mode.py
"""
System prompt for cleanup/structuring plan generation.

The cleanup phase identifies:
- Blocks that may be candidates for discard (user decides)
- Blocks that may need restructuring
- Overall document organization suggestions
"""

from typing import List, Dict, Any, Optional


CLEANUP_SYSTEM_PROMPT = """You are a knowledge librarian assistant analyzing a document for extraction into a personal knowledge library.

Your task is to analyze the provided document blocks and suggest a cleanup plan. The user will make final decisions on all suggestions.

## Your Role

1. **Identify Discard Candidates**: Flag content that may not belong in a permanent knowledge library:
   - Temporary notes, reminders, or time-sensitive content
   - Duplicate information
   - Placeholder text or incomplete thoughts
   - Personal todos that have been completed

2. **Preserve by Default**: When in doubt, suggest KEEP. The user can always discard later.

3. **Never Auto-Discard**: Nothing is discarded without explicit user approval.

## Confidence Guidelines

Use these specific confidence levels based on evidence strength:

- **0.9-1.0 (Strong evidence)**: Explicit markers like dates ("reminder for 2023-01-15"), keywords ("TODO", "DRAFT", "temporary", "delete this"), or clearly time-sensitive content
- **0.7-0.9 (Moderate evidence)**: Contextual clues suggest status (informal tone, incomplete sentences, references to specific past events)
- **0.5-0.7 (Weak evidence)**: Uncertain - content could reasonably go either way, limited context available
- **Below 0.5 (Very uncertain)**: Default to KEEP suggestion - better to preserve than lose

Always explain the reasoning behind your confidence level in the suggestion_reason field.

## Output Format

Return a JSON object with the following structure. IMPORTANT: You MUST provide an analysis for EVERY block ID listed in the input.

```json
{
  "cleanup_items": [
    {
      "block_id": "block_001",
      "suggested_disposition": "keep",
      "suggestion_reason": "Contains valuable technical information about X (high confidence: permanent reference material)",
      "confidence": 0.9
    },
    {
      "block_id": "block_002",
      "suggested_disposition": "discard",
      "suggestion_reason": "Appears to be a temporary reminder dated 2023 (moderate confidence: explicit date reference suggests time-sensitivity)",
      "confidence": 0.7
    }
  ],
  "overall_notes": "Document contains 4 blocks. 3 appear to be valuable knowledge content. 1 may be a temporary note."
}
```

## Rules

- CRITICAL: Provide analysis for EVERY block in the input - do not omit any blocks
- Always provide a reason for each suggestion that explains your confidence level
- Use "keep" as default unless there's clear evidence for "discard"
- Confidence should reflect how certain you are (0.0 to 1.0) - see guidelines above
- Never modify content - only classify it
- Be conservative - it's better to keep something than lose valuable information
- If content is truncated, base your analysis on available content and note any limitations
"""

# Content preview limit - increased from 300 to 800 for better AI context
CONTENT_PREVIEW_LIMIT = 800


def build_cleanup_prompt(
    blocks: List[Dict[str, Any]],
    source_file: str,
    content_mode: str = "strict",
    conversation_history: str = "",
    pending_questions: Optional[List[str]] = None,
) -> str:
    """
    Build the user prompt for cleanup plan generation.

    Args:
        blocks: List of block dictionaries with id, content, type, heading_path
        source_file: Name of the source file
        content_mode: "strict" or "refinement"

    Returns:
        Formatted prompt string
    """
    block_descriptions = []

    for block in blocks:
        heading = " > ".join(block.get("heading_path", [])) or "(no heading)"
        content_length = len(block["content"])
        is_truncated = content_length > CONTENT_PREVIEW_LIMIT
        preview = block["content"][:CONTENT_PREVIEW_LIMIT]
        if is_truncated:
            preview += "..."

        # Include content length metadata to help AI understand context limitations
        truncation_note = "(truncated)" if is_truncated else "(full)"
        block_descriptions.append(
            f"### Block {block['id']}\n"
            f"- Type: {block['type']}\n"
            f"- Heading Path: {heading}\n"
            f"- Content Length: {content_length} chars {truncation_note}\n"
            f"- Content:\n```\n{preview}\n```\n"
        )

    blocks_text = "\n".join(block_descriptions)

    prompt = f"""Analyze this document for cleanup.

## Source File
{source_file}

## Content Mode
{content_mode.upper()} - {"No modifications allowed to content" if content_mode == "strict" else "Minor formatting fixes allowed"}

## Document Blocks

{blocks_text}
"""

    if conversation_history:
        prompt += f"""
## Conversation History
{conversation_history}
"""

    if pending_questions:
        questions_text = "\n".join(f"- {q}" for q in pending_questions)
        prompt += f"""
## Pending Questions
{questions_text}
"""

    prompt += """
## Instructions

Analyze each block and provide your cleanup suggestions as JSON. Remember:
- Default to "keep" unless there's a clear reason to suggest discard
- Provide clear reasoning for each suggestion
- The user makes all final decisions

Return your analysis as a valid JSON object.
"""

    return prompt
