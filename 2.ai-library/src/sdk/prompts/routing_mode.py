# src/sdk/prompts/routing_mode.py
"""
System prompt for routing plan generation.

The routing phase determines where each kept block should be placed in the library.
Provides top-3 destination options per block for user selection.
"""

from typing import List, Dict, Any


ROUTING_SYSTEM_PROMPT = """You are a knowledge librarian assistant routing content blocks to their appropriate locations in a personal knowledge library.

Your task is to analyze each content block and suggest the top 3 most appropriate destinations in the library.

## Your Role

1. **Analyze Content**: Understand what each block contains and its topic/domain
2. **Match to Library**: Find the best existing files/sections or suggest new ones
3. **Provide Options**: Give exactly 3 destination options per block, ranked by fit

## Library Structure

The library is organized by categories (folders) containing markdown files with sections.
- Categories: Top-level folders for broad topics
- Files: Markdown files for specific topics within a category
- Sections: H2 headers within files for subtopics

## Output Format

Return a JSON object with the following structure:

```json
{
  "routing_items": [
    {
      "block_id": "block_001",
      "options": [
        {
          "destination_file": "tech/authentication.md",
          "destination_section": "JWT Tokens",
          "action": "append",
          "confidence": 0.9,
          "reasoning": "Block discusses JWT token validation, fits well in existing auth section"
        },
        {
          "destination_file": "tech/authentication.md",
          "destination_section": null,
          "action": "create_section",
          "proposed_section_title": "Token Validation",
          "confidence": 0.75,
          "reasoning": "Could create a new section for token validation specifics"
        },
        {
          "destination_file": "tech/security.md",
          "destination_section": null,
          "action": "create_file",
          "proposed_file_title": "Security Best Practices",
          "confidence": 0.6,
          "reasoning": "Could start a new security-focused file"
        }
      ]
    }
  ],
  "summary": {
    "total_blocks": 4,
    "blocks_to_existing_files": 3,
    "blocks_to_new_files": 1,
    "estimated_actions": 4
  }
}
```

## Action Types

- `append`: Add to end of existing file or section
- `create_file`: Create a new file (provide proposed_file_title)
- `create_section`: Create a new section in existing file (provide proposed_section_title)
- `insert_before`: Insert before a specific section
- `insert_after`: Insert after a specific section

## Rules

- Always provide exactly 3 options per block
- First option should be the best match
- Confidence should decrease for less ideal options
- Never suggest merging in STRICT mode
- Consider semantic relevance, not just keyword matching
- If library is empty, suggest logical new file structures
"""


def build_routing_prompt(
    blocks: List[Dict[str, Any]],
    library_context: Dict[str, Any],
    source_file: str,
    content_mode: str = "strict",
) -> str:
    """
    Build the user prompt for routing plan generation.

    Args:
        blocks: List of kept block dictionaries
        library_context: Library manifest/structure info
        source_file: Name of the source file
        content_mode: "strict" or "refinement"

    Returns:
        Formatted prompt string
    """
    # Format blocks
    block_candidates_by_id: Dict[str, Any] = library_context.get("block_candidates") or {}
    block_descriptions = []
    for block in blocks:
        heading = " > ".join(block.get("heading_path", [])) or "(no heading)"
        preview = block["content"][:500]
        if len(block["content"]) > 500:
            preview += "..."

        candidates = block_candidates_by_id.get(block["id"]) or []
        candidate_lines = []
        for c in candidates[:3]:
            file_path = c.get("file_path") or c.get("path") or ""
            section = c.get("section")
            score = c.get("score")

            line = f"  - {file_path}"
            if section:
                line += f" → {section}"
            if isinstance(score, (int, float)):
                line += f" (score {score:.2f})"
            candidate_lines.append(line)

        candidates_text = ""
        if candidate_lines:
            candidates_text = (
                "- Candidate Destinations (hints):\n"
                + "\n".join(candidate_lines)
                + "\n"
            )

        block_descriptions.append(
            f"### Block {block['id']}\n"
            f"- Type: {block['type']}\n"
            f"- Heading Path: {heading}\n"
            f"{candidates_text}"
            f"- Content:\n```\n{preview}\n```\n"
        )

    blocks_text = "\n".join(block_descriptions)

    # Format library context
    if library_context.get("categories"):
        library_text = _format_library_context(library_context)
    else:
        library_text = "The library is currently empty. Suggest a logical structure for new files."

    prompt = f"""Route these content blocks to appropriate library locations.

## Source File
{source_file}

## Content Mode
{content_mode.upper()} - {"No merging or rewriting allowed" if content_mode == "strict" else "Minor formatting allowed, merges possible with user approval"}

## Current Library Structure

{library_text}

## Blocks to Route

{blocks_text}

## Instructions

For each block, provide exactly 3 destination options ranked by fit.
Consider:
1. Semantic relevance to existing content
2. Logical organization
3. Whether new files/sections would better serve the content

Return your routing plan as a valid JSON object.
"""

    return prompt


def _format_library_context(context: Dict[str, Any]) -> str:
    """Format library context for the prompt."""
    lines = []
    summary = context.get("summary", {})

    lines.append(f"Total Categories: {summary.get('total_categories', 0)}")
    lines.append(f"Total Files: {summary.get('total_files', 0)}")
    lines.append(f"Total Sections: {summary.get('total_sections', 0)}")
    lines.append("")

    def format_category(cat: Dict[str, Any], indent: int = 0) -> List[str]:
        result = []
        prefix = "  " * indent
        result.append(f"{prefix}- **{cat['name']}/** ({cat['path']})")

        for file in cat.get("files", []):
            result.append(f"{prefix}  - {file['title']} ({file.get('path', 'unknown')})")
            for section in file.get("sections", []):
                result.append(f"{prefix}    - ## {section}")

        for subcat in cat.get("subcategories", []):
            result.extend(format_category(subcat, indent + 1))

        return result

    for category in context.get("categories", []):
        lines.extend(format_category(category))

    return "\n".join(lines)
