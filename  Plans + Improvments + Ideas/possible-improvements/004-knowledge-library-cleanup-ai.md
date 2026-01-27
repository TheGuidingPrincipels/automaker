# Knowledge Library Cleanup AI Decision Criteria Improvements

**Status:** Ready for Implementation
**Priority:** High
**Impact:** Better AI recommendations with user-selectable cleanup modes (Conservative/Balanced/Aggressive)
**Date Added:** 2026-01-26
**Updated:** 2026-01-26 (Added mode-specific prompt architecture)
**Related Upstream:** Not applicable (AI Library feature)
**Depends On:** Plan 003 (UI Improvements) should be implemented first for best results

## Summary

Implement a comprehensive cleanup mode system with three selectable modes (Conservative, Balanced, Aggressive). Each mode has its own optimized prompt that is loaded independently - only the selected mode's prompt is sent to the AI, ensuring token efficiency. The system includes structured discard/keep criteria, signal detection, and a frontend settings UI.

## Problem Statement

### Current Issues

1. **Excessive conservatism**: Prompt explicitly says "preserve by default", resulting in "keep" for almost everything
2. **No user control**: Users cannot adjust how aggressive the cleanup suggestions should be
3. **Vague criteria**: Only 4 generic discard criteria
4. **No signal detection**: AI doesn't identify specific patterns that indicate content should be discarded
5. **Single prompt**: No way to customize behavior for different use cases

### User Needs

- **Conservative users**: Want to preserve most content, only remove obvious noise
- **Balanced users**: Want smart suggestions based on content signals
- **Aggressive users**: Want to actively clean up time-sensitive and ephemeral content

## Solution Design

### Architecture Overview: Mode-Specific Prompt Loading

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TOKEN-EFFICIENT DESIGN                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User selects: "Aggressive" mode                                         │
│                     │                                                    │
│                     ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  get_cleanup_system_prompt("aggressive")                         │    │
│  │                                                                  │    │
│  │  if mode == "conservative":                                      │    │
│  │      return CLEANUP_PROMPT_CONSERVATIVE  ← NOT sent              │    │
│  │  elif mode == "aggressive":                                      │    │
│  │      return CLEANUP_PROMPT_AGGRESSIVE    ← ONLY this sent (~800) │    │
│  │  else:                                                           │    │
│  │      return CLEANUP_PROMPT_BALANCED      ← NOT sent              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Result: Only ~800 tokens sent, NOT ~2400 tokens for all three modes    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Three Cleanup Modes

| Mode             | Behavior                                | Confidence Threshold | Use Case                       |
| ---------------- | --------------------------------------- | -------------------- | ------------------------------ |
| **Conservative** | Only suggest discard for obvious noise  | 0.85+ required       | Preserve everything important  |
| **Balanced**     | Smart suggestions based on all criteria | 0.70+ required       | Default, balanced approach     |
| **Aggressive**   | Actively flag time-sensitive content    | 0.55+ required       | Clean up meeting notes, drafts |

### Decision Framework (35 Total Criteria)

#### DISCARD SIGNALS (20 criteria)

**Category 1: Time-Sensitive Content (5)**
| # | Criterion | Example |
|---|-----------|---------|
| 1 | Past specific dates | "Meeting on Jan 15, 2024" |
| 2 | Ephemeral meeting links | Zoom, Teams, Google Meet URLs |
| 3 | Relative time references | "today", "tomorrow", "this week" |
| 4 | Season/quarter references | "Q4 2024", "this winter" |
| 5 | Event-specific content | Conference notes, past deadlines |

**Category 2: Completed/Stale Items (5)**
| # | Criterion | Example |
|---|-----------|---------|
| 6 | Checked checkboxes | `[x]`, `- [x]`, `✓` |
| 7 | Completion markers | "Done", "Completed", "Resolved" |
| 8 | Old version references | "v1.2.3" when v2.0 exists |
| 9 | Resolved issues | "Fixed in PR #123" |
| 10 | Superseded documentation | "See updated version" |

**Category 3: Ephemeral/Temporary (5)**
| # | Criterion | Example |
|---|-----------|---------|
| 11 | Short/tracking URLs | bit.ly, tinyurl, t.co |
| 12 | Temporary credentials | OTPs, session tokens |
| 13 | Draft markers | "DRAFT", "WIP" without substance |
| 14 | Scratch content | "scratch", "temp", "test" titles |
| 15 | One-time instructions | "Run this once" |

**Category 4: Structural Noise (3)**
| # | Criterion | Example |
|---|-----------|---------|
| 16 | Empty sections | Headers with no content |
| 17 | Placeholder text | "TODO", "TBD", "Lorem ipsum" |
| 18 | Uncustomized templates | Boilerplate with `{placeholder}` |

**Category 5: Source-Only/Low-Value (2)**
| # | Criterion | Example |
|---|-----------|---------|
| 19 | Pure external copy | Quoted content, no commentary |
| 20 | Duplicate content | Near-identical to another block |

#### KEEP SIGNALS (15 criteria)

**Category 1: Original Work (5)**
| # | Criterion | Example |
|---|-----------|---------|
| 1 | Personal insights | "I think...", "My approach..." |
| 2 | Synthesized analysis | Multiple sources combined |
| 3 | Decision documentation | Rationale records |
| 4 | Custom solutions | User-written code |
| 5 | Lessons learned | Retrospective notes |

**Category 2: Reference Value (5)**
| # | Criterion | Example |
|---|-----------|---------|
| 6 | Working code examples | Code with context |
| 7 | Step-by-step guides | Numbered instructions |
| 8 | Command references | CLI commands with explanations |
| 9 | Troubleshooting steps | Problem-solution pairs |
| 10 | Best practices | Patterns, guidelines |

**Category 3: Evergreen Content (5)**
| # | Criterion | Example |
|---|-----------|---------|
| 11 | Conceptual explanations | Definitions, principles |
| 12 | Architecture documentation | System design |
| 13 | Curated resource lists | Bookmarks with descriptions |
| 14 | Historical records | Project milestones |
| 15 | Learning notes | Study notes with annotations |

---

## Implementation Plan

### Phase 1: Create Cleanup Mode Enum

#### Step 1.1: Create CleanupMode enum

**File:** `2.ai-library/src/models/cleanup_mode_setting.py` (NEW FILE)

```python
"""Cleanup mode settings for AI-assisted cleanup."""

from enum import Enum


class CleanupModeSetting(str, Enum):
    """User-selectable cleanup aggressiveness modes."""

    CONSERVATIVE = "conservative"
    """Only suggest discard for obvious noise. High confidence required (0.85+)."""

    BALANCED = "balanced"
    """Smart suggestions based on all criteria. Default mode. (0.70+ confidence)"""

    AGGRESSIVE = "aggressive"
    """Actively flag time-sensitive and ephemeral content. (0.55+ confidence)"""

    @property
    def confidence_threshold(self) -> float:
        """Minimum confidence required to suggest discard."""
        thresholds = {
            CleanupModeSetting.CONSERVATIVE: 0.85,
            CleanupModeSetting.BALANCED: 0.70,
            CleanupModeSetting.AGGRESSIVE: 0.55,
        }
        return thresholds[self]

    @property
    def description(self) -> str:
        """Human-readable description of the mode."""
        descriptions = {
            CleanupModeSetting.CONSERVATIVE: "Keep more - only suggest discard for obvious noise",
            CleanupModeSetting.BALANCED: "Balanced - smart suggestions based on content signals",
            CleanupModeSetting.AGGRESSIVE: "Discard more - actively flag time-sensitive content",
        }
        return descriptions[self]
```

#### Step 1.2: Export from models

**File:** `2.ai-library/src/models/__init__.py`

Add to exports:

```python
from .cleanup_mode_setting import CleanupModeSetting
```

---

### Phase 2: Create Three Mode-Specific Prompts

#### Step 2.1: Rewrite cleanup_mode.py with three prompts

**File:** `2.ai-library/src/sdk/prompts/cleanup_mode.py`

````python
"""
System prompts for cleanup/structuring plan generation.

This module provides THREE separate prompts for different cleanup modes:
- CONSERVATIVE: Keep more, only discard obvious noise
- BALANCED: Smart suggestions based on all criteria (default)
- AGGRESSIVE: Actively flag time-sensitive content

IMPORTANT: Only ONE prompt is sent per request for token efficiency.
"""

from typing import List, Dict, Any, Optional


# =============================================================================
# CONSERVATIVE MODE PROMPT (~800 tokens)
# Only suggest discard for obvious noise. High confidence required.
# =============================================================================

CLEANUP_PROMPT_CONSERVATIVE = """You are a knowledge librarian assistant analyzing a document for extraction into a personal knowledge library.

Your task is to analyze document blocks and suggest a cleanup plan. You are in CONSERVATIVE mode - preserve content by default, only flag obvious noise for discard.

## Conservative Mode Rules

1. **Preserve by Default**: When in doubt, suggest KEEP
2. **High Confidence Required**: Only suggest discard with 0.85+ confidence
3. **Obvious Noise Only**: Flag for discard only when clearly non-valuable:
   - Empty sections with only headers (no content)
   - Pure placeholder text: "TODO", "TBD", "FIXME", "Lorem ipsum"
   - 100% completed todo lists (all items checked off)
   - Uncustomized boilerplate templates
4. **Never Echo Secrets**: If a block contains credentials/tokens/keys, do NOT quote them verbatim in `suggestion_reason` or `signals_detected.detail` — describe at a high level (e.g., "contains an API key")

## Do NOT Suggest Discard For

- Meeting notes (even dated ones) - user may want to keep
- Partially completed todo lists
- Content with any user commentary or analysis
- Anything with potential reference value

## Output Format

Return JSON:
```json
{
  "cleanup_items": [
    {
      "block_id": "block_001",
      "suggested_disposition": "keep",
      "suggestion_reason": "Contains user notes - preserving in conservative mode",
      "confidence": 0.95,
      "signals_detected": [
        {"type": "original_work", "detail": "User's own notes"}
      ]
    }
  ],
  "overall_notes": "Conservative mode: Preserving most content. Only flagging obvious noise."
}
````

## Confidence Guidelines (Conservative)

- 0.95+ = Definitely discard (empty placeholder only)
- 0.85-0.95 = Likely discard (pure noise, no value)
- Below 0.85 = Suggest KEEP (preserve when uncertain)
  """

# =============================================================================

# BALANCED MODE PROMPT (~900 tokens)

# Smart suggestions based on all criteria. Default mode.

# =============================================================================

CLEANUP_PROMPT_BALANCED = """You are a knowledge librarian assistant analyzing a document for extraction into a personal knowledge library.

Your task is to analyze document blocks and suggest a cleanup plan. You are in BALANCED mode - provide smart suggestions based on content signals.

## Balanced Mode Rules

1. **Evaluate All Signals**: Consider both discard and keep signals
2. **Multiple Signals Required**: Suggest discard when 2+ discard signals present
3. **Confidence Threshold**: 0.70+ required to suggest discard
4. **Explain Reasoning**: Always cite specific signals detected
5. **Never Echo Secrets**: If a block contains credentials/tokens/keys, do NOT quote them verbatim in `suggestion_reason` or `signals_detected.detail`

## Discard Signals (flag when multiple present)

### Time-Sensitive Content

- Specific past dates ("Meeting on Jan 15, 2024")
- Meeting links (Zoom, Teams, Google Meet URLs)
- Relative time ("today", "tomorrow", "this week")

### Completed/Stale Items

- Checked checkboxes: `[x]` or `- [x]`
- Completion markers: "Done", "Completed", "Resolved"
- Old version references superseded by newer content

### Ephemeral References

- Short URLs (bit.ly, tinyurl)
- Temporary tokens, one-time codes
- Draft/WIP markers with no substance

### Structural Noise

- Empty sections (headers only)
- Placeholder text: "TODO", "TBD", "FIXME"
- Uncustomized boilerplate

## Keep Signals (preserve when present)

- Original analysis or insights
- Working code examples
- Reference documentation
- Evergreen concepts
- User commentary on any content

## Output Format

Return JSON:

```json
{
  "cleanup_items": [
    {
      "block_id": "block_001",
      "suggested_disposition": "discard",
      "suggestion_reason": "Time-sensitive meeting notes with completed items",
      "confidence": 0.78,
      "signals_detected": [
        { "type": "time_sensitive", "detail": "Meeting dated 2024-01-10" },
        { "type": "completed_items", "detail": "3 of 4 items checked" }
      ]
    }
  ],
  "overall_notes": "Document has 5 blocks. 3 valuable reference material, 2 time-sensitive."
}
```

## Confidence Guidelines (Balanced)

- 0.85+ = Very confident (clear signals)
- 0.70-0.85 = Confident (multiple signals)
- 0.50-0.70 = Uncertain (suggest keep)
- Below 0.50 = Default keep
  """

# =============================================================================

# AGGRESSIVE MODE PROMPT (~900 tokens)

# Actively flag time-sensitive and ephemeral content.

# =============================================================================

CLEANUP_PROMPT_AGGRESSIVE = """You are a knowledge librarian assistant analyzing a document for extraction into a personal knowledge library.

Your task is to analyze document blocks and suggest a cleanup plan. You are in AGGRESSIVE mode - actively identify content that may not need permanent storage.

## Aggressive Mode Rules

1. **Active Cleanup**: Proactively flag time-sensitive and ephemeral content
2. **Single Strong Signal**: One clear discard signal is sufficient
3. **Lower Threshold**: 0.55+ confidence can trigger discard suggestion
4. **Focus on Evergreen**: Prioritize keeping only timeless, reusable content
5. **Never Echo Secrets**: If a block contains credentials/tokens/keys, do NOT quote them verbatim in `suggestion_reason` or `signals_detected.detail`

## Actively Flag for Discard

### Time-Sensitive (single signal sufficient)

- ANY specific dates in the past
- ANY meeting links (Zoom, Teams, etc.)
- ANY relative time references
- Meeting notes, standup notes, sprint notes

### Completed Items (single signal sufficient)

- Todo lists with ANY checked items
- Content marked "Done" or "Completed"
- Closed issues or resolved bugs

### Ephemeral Content

- Draft/WIP content
- Scratch notes
- Temporary URLs or tokens
- One-time setup instructions

### Low-Value Content

- Content copied from external sources without commentary
- Auto-generated content
- Boilerplate and templates

## Preserve Only When

- Original analysis or user insights present
- Working, tested code examples
- Evergreen reference documentation
- Content user explicitly created (not copied)

## Output Format

Return JSON:

```json
{
  "cleanup_items": [
    {
      "block_id": "block_001",
      "suggested_disposition": "discard",
      "suggestion_reason": "Meeting notes - time-sensitive content",
      "confidence": 0.65,
      "signals_detected": [{ "type": "time_sensitive", "detail": "Contains meeting date" }]
    }
  ],
  "overall_notes": "Aggressive cleanup: Flagging all time-sensitive content for review."
}
```

## Confidence Guidelines (Aggressive)

- 0.75+ = Definitely discard
- 0.55-0.75 = Likely discard (single strong signal)
- Below 0.55 = Suggest keep (need at least some signal)
  """

# =============================================================================

# PROMPT FACTORY FUNCTION

# =============================================================================

def get_cleanup_system_prompt(cleanup_mode: str = "balanced") -> str:
"""
Return the appropriate system prompt for the selected cleanup mode.

    IMPORTANT: Only ONE prompt is returned, ensuring token efficiency.
    The unused prompts are NOT included in the API call.

    Args:
        cleanup_mode: One of "conservative", "balanced", "aggressive"

    Returns:
        The system prompt string for the selected mode (~800-900 tokens)
    """
    mode = cleanup_mode.lower()

    if mode == "conservative":
        return CLEANUP_PROMPT_CONSERVATIVE
    if mode == "balanced":
        return CLEANUP_PROMPT_BALANCED
    if mode == "aggressive":
        return CLEANUP_PROMPT_AGGRESSIVE

    # NO silent fallbacks: invalid modes must surface as errors
    raise ValueError(f"Unknown cleanup_mode: {cleanup_mode!r}")

# =============================================================================

# USER PROMPT BUILDER

# =============================================================================

def build_cleanup_prompt(
blocks: List[Dict[str, Any]],
source_file: str,
content_mode: str = "strict",
cleanup_mode: str = "balanced",
conversation_history: str = "",
pending_questions: Optional[List[str]] = None,
) -> str:
"""
Build the user prompt for cleanup plan generation.

    Args:
        blocks: List of block dictionaries with id, content, type, heading_path
        source_file: Name of the source file
        content_mode: "strict" or "refinement" (content handling)
        cleanup_mode: "conservative", "balanced", or "aggressive"
        conversation_history: Previous conversation context
        pending_questions: Questions to address

    Returns:
        Formatted prompt string
    """
    block_descriptions = []

    for block in blocks:
        heading = " > ".join(block.get("heading_path", [])) or "(no heading)"
        # Keep previews bounded to control token cost (align with current system defaults)
        preview = block["content"][:300]
        if len(block["content"]) > 300:
            preview += "..."

        block_descriptions.append(
            f"### Block {block['id']}\n"
            f"- Type: {block['type']}\n"
            f"- Heading Path: {heading}\n"
            f"- Content Preview:\n```\n{preview}\n```\n"
        )

    blocks_text = "\n".join(block_descriptions)

    # Mode-specific instruction emphasis
    mode_instructions = {
        "conservative": "Remember: CONSERVATIVE mode - preserve content by default, high confidence required for discard suggestions.",
        "balanced": "Remember: BALANCED mode - evaluate all signals, suggest discard when multiple signals present.",
        "aggressive": "Remember: AGGRESSIVE mode - actively flag time-sensitive and ephemeral content.",
    }
    normalized_mode = cleanup_mode.lower()
    if normalized_mode not in mode_instructions:
        # NO silent fallbacks: invalid modes must surface as errors
        raise ValueError(f"Unknown cleanup_mode: {cleanup_mode!r}")
    mode_instruction = mode_instructions[normalized_mode]

    prompt = f"""Analyze this document for cleanup.

## Source File

{source_file}

## Content Mode

{content_mode.upper()} - {"No modifications allowed" if content_mode == "strict" else "Minor formatting allowed"}

## Cleanup Mode

{cleanup_mode.upper()} - {mode_instruction}

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

    prompt += f"""

## Instructions

Analyze each block and provide cleanup suggestions as JSON.

{mode_instruction}

Include for each block:

- block_id
- suggested_disposition ("keep" or "discard")
- suggestion_reason (specific, citing detected signals)
- confidence (0.0 to 1.0)
- signals_detected (array of {{"type": "...", "detail": "..."}})

Return valid JSON matching the format shown in the system prompt.
"""

    return prompt

````

#### Step 2.2: Update prompts __init__.py

**File:** `2.ai-library/src/sdk/prompts/__init__.py`

```python
"""SDK prompts for AI operations."""

from .cleanup_mode import (
    CLEANUP_PROMPT_CONSERVATIVE,
    CLEANUP_PROMPT_BALANCED,
    CLEANUP_PROMPT_AGGRESSIVE,
    get_cleanup_system_prompt,
    build_cleanup_prompt,
)
from .routing_mode import ROUTING_SYSTEM_PROMPT, build_routing_prompt
from .output_mode import OUTPUT_SYSTEM_PROMPT

__all__ = [
    # Cleanup prompts (mode-specific)
    "CLEANUP_PROMPT_CONSERVATIVE",
    "CLEANUP_PROMPT_BALANCED",
    "CLEANUP_PROMPT_AGGRESSIVE",
    "get_cleanup_system_prompt",
    "build_cleanup_prompt",
    # Other prompts
    "ROUTING_SYSTEM_PROMPT",
    "build_routing_prompt",
    "OUTPUT_SYSTEM_PROMPT",
]
````

---

### Phase 3: Update Backend Call Chain (Streaming + REST + WebSocket)

#### Step 3.1: Update API Schema

**File:** `2.ai-library/src/api/schemas.py`

Update response schemas (keep payloads small; do NOT embed full block content in cleanup plan payloads — rely on `GET /api/sessions/{session_id}/blocks` per Plan 003):

```python
class DetectedSignalResponse(BaseModel):
    """Response for a detected signal."""
    type: str
    detail: str


class CleanupItemResponse(BaseModel):
    """Response for a cleanup item."""
    block_id: str
    heading_path: List[str]
    content_preview: str
    suggested_disposition: str
    suggestion_reason: str
    confidence: float = 0.8
    signals_detected: List[DetectedSignalResponse] = Field(default_factory=list)
    final_disposition: Optional[str] = None

    @classmethod
    def from_item(cls, item) -> "CleanupItemResponse":
        from ..models.cleanup_plan import CleanupItem
        return cls(
            block_id=item.block_id,
            heading_path=item.heading_path,
            content_preview=item.content_preview,
            suggested_disposition=item.suggested_disposition,
            suggestion_reason=item.suggestion_reason,
            confidence=getattr(item, 'confidence', 0.8),
            signals_detected=[
                DetectedSignalResponse(type=s.type, detail=s.detail)
                for s in getattr(item, 'signals_detected', [])
            ],
            final_disposition=item.final_disposition,
        )


class CleanupPlanResponse(BaseModel):
    """Response with cleanup plan."""
    session_id: str
    source_file: str
    created_at: datetime
    overall_notes: str = ""
    cleanup_mode: str = "balanced"  # NEW: Include mode in response
    items: List[CleanupItemResponse]
    all_decided: bool
    approved: bool
    approved_at: Optional[datetime] = None
    pending_count: int
    total_count: int

    @classmethod
    def from_plan(cls, plan) -> "CleanupPlanResponse":
        pending_count = sum(1 for item in plan.items if item.final_disposition is None)
        return cls(
            session_id=plan.session_id,
            source_file=plan.source_file,
            created_at=plan.created_at,
            overall_notes=getattr(plan, 'overall_notes', ''),
            cleanup_mode=getattr(plan, 'cleanup_mode', 'balanced'),
            items=[CleanupItemResponse.from_item(item) for item in plan.items],
            all_decided=plan.all_decided,
            approved=plan.approved,
            approved_at=plan.approved_at,
            pending_count=pending_count,
            total_count=len(plan.items),
        )
```

#### Step 3.2: Update API Endpoint

**File:** `2.ai-library/src/api/routes/sessions.py`

Keep the current REST contract (`use_ai` query param), add `cleanup_mode` as a validated query param, and preserve the existing streaming generator architecture.

```python
from ..schemas import CleanupPlanResponse
from ...models.cleanup_mode_setting import CleanupModeSetting

@router.post("/{session_id}/cleanup/generate", response_model=CleanupPlanResponse)
async def generate_cleanup_plan(
    session_id: str,
    manager: SessionManagerDep,
    use_ai: bool = False,
    cleanup_mode: CleanupModeSetting = CleanupModeSetting.BALANCED,
):
    """
    Generate a cleanup plan for the session.

    Args:
        session_id: Session identifier
        use_ai: If true, generate AI suggestions (still user-approved)
        cleanup_mode: "conservative" | "balanced" | "aggressive"
    """
    if use_ai:
        # AI generation streams PlanEvents; REST endpoint consumes events and returns final state
        async for _event in manager.generate_cleanup_plan_with_ai(
            session_id=session_id,
            cleanup_mode=cleanup_mode,
        ):
            pass
    else:
        await manager.generate_cleanup_plan(session_id)

    session = await manager.get_session(session_id)
    if not session or not session.cleanup_plan:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cleanup plan",
        )

    return CleanupPlanResponse.from_plan(session.cleanup_plan)
```

#### Step 3.3: Update Session Manager

**File:** `2.ai-library/src/session/manager.py`

Update the AI cleanup method to accept `cleanup_mode` and preserve the existing `AsyncIterator[PlanEvent]` streaming design (do not `await` generators).

```python
async def generate_cleanup_plan_with_ai(
    self,
    session_id: str,
    cleanup_mode: CleanupModeSetting = CleanupModeSetting.BALANCED,  # NEW PARAMETER
) -> AsyncIterator:
    """
    Generate cleanup plan using AI with the specified mode.

    Args:
        session_id: Session identifier
        cleanup_mode: "conservative" | "balanced" | "aggressive"
    """
    from ..conversation.flow import PlanningFlow, PlanEvent, PlanEventType

    session = await self.storage.load(session_id)
    if not session:
        yield PlanEvent(
            type=PlanEventType.ERROR,
            message=f"Session not found: {session_id}",
        )
        return

    flow = PlanningFlow(library_path=session.library_path)

    async for event in flow.generate_cleanup_plan(session, cleanup_mode=cleanup_mode):
        yield event

        # If cleanup is ready, update session
        if event.type == PlanEventType.CLEANUP_READY and event.data:
            plan_data = event.data.get("cleanup_plan")
            if plan_data:
                cleanup_plan = CleanupPlan.model_validate(plan_data)
                session.cleanup_plan = cleanup_plan
                session.phase = SessionPhase.CLEANUP_PLAN_READY
                await self.storage.save(session)
```

#### Step 3.4: Update Planning Flow

**File:** `2.ai-library/src/conversation/flow.py`

Update the generate_cleanup_plan method to accept `cleanup_mode` and pass it to the SDK client while preserving the existing `AsyncIterator[PlanEvent]` flow.

```python
async def generate_cleanup_plan(
    self,
    session: ExtractionSession,
    cleanup_mode: CleanupModeSetting = CleanupModeSetting.BALANCED,  # NEW PARAMETER
) -> AsyncIterator[PlanEvent]:
    """
    Generate cleanup plan using AI.

    Args:
        session: The extraction session
        cleanup_mode: "conservative" | "balanced" | "aggressive"
    """
    # Get blocks from session
    blocks = [
        {
            "id": block.id,
            "type": block.block_type.value,
            "content": block.content,
            "heading_path": block.heading_path,
        }
        for block in session.source.blocks
    ]

    # Call SDK client with cleanup_mode
    cleanup_plan = await self.sdk_client.generate_cleanup_plan(
        session_id=session.id,
        source_file=session.source.file_path,
        blocks=blocks,
        content_mode=session.content_mode.value,
        cleanup_mode=cleanup_mode,  # Pass mode to SDK
    )

    yield PlanEvent(
        type=PlanEventType.CLEANUP_READY,
        message="Cleanup plan ready",
        data={"cleanup_plan": cleanup_plan.model_dump()},
    )
```

#### Step 3.5: Update SDK Client

**File:** `2.ai-library/src/sdk/client.py`

Update imports and generate_cleanup_plan method:

**Recommended guardrail (safety + determinism):** after parsing the model JSON, enforce the mode’s confidence threshold server-side. If the model suggests `discard` but `confidence < CleanupModeSetting(confidence_threshold)`, downgrade to `keep` and _explicitly annotate_ `suggestion_reason` (so there is no silent behavior change).

```python
# Update imports (around line 35)
from .prompts.cleanup_mode import get_cleanup_system_prompt, build_cleanup_prompt

# Update method (around line 198)
async def generate_cleanup_plan(
    self,
    session_id: str,
    source_file: str,
    blocks: List[Dict[str, Any]],
    content_mode: str = "strict",
    cleanup_mode: str = "balanced",  # NEW PARAMETER
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
        cleanup_mode: "conservative", "balanced", or "aggressive"

    Returns:
        CleanupPlan with AI suggestions
    """
    # Get the mode-specific system prompt (only ONE prompt is sent in the request)
    system_prompt = get_cleanup_system_prompt(cleanup_mode)

    # Build user prompt with mode context
    user_prompt = build_cleanup_prompt(
        blocks=blocks,
        source_file=source_file,
        content_mode=content_mode,
        cleanup_mode=cleanup_mode,
        conversation_history=conversation_history,
        pending_questions=pending_questions,
    )

    # Query AI with the selected mode's prompt
    response = await self._query(system_prompt, user_prompt)

    # Parse response (rest of method unchanged)
    block_map = {b["id"]: b for b in blocks}
    suggested_by_block_id: dict[str, dict[str, Any]] = {}
    overall_notes = ""

    if response.success and response.data:
        overall_notes = response.data.get("overall_notes", "")
        for item_data in response.data.get("cleanup_items", []):
            block_id = item_data.get("block_id")
            if block_id in block_map:
                suggested_by_block_id[block_id] = item_data

    # Build items for all blocks
    items = []
    for block in blocks:
        block_id = block["id"]
        item_data = suggested_by_block_id.get(block_id)

        if item_data:
            suggested_disposition = item_data.get(
                "suggested_disposition", CleanupDisposition.KEEP
            )
            suggestion_reason = item_data.get("suggestion_reason", "")
            confidence = item_data.get("confidence", 0.8)

            # Parse signals_detected
            signals_detected = []
            for signal in item_data.get("signals_detected", []):
                signals_detected.append(
                    DetectedSignal(
                        type=signal.get("type", "unknown"),
                        detail=signal.get("detail", "")
                    )
                )
        else:
            suggested_disposition = CleanupDisposition.KEEP
            suggestion_reason = (
                "Default: keep (model omitted this block)"
                if response.success
                else "Default: keep"
            )
            confidence = 0.5
            signals_detected = []

        items.append(
            CleanupItem(
                block_id=block_id,
                heading_path=block.get("heading_path", []),
                content_preview=block["content"][:200],
                suggested_disposition=suggested_disposition,
                suggestion_reason=suggestion_reason,
                confidence=confidence,
                signals_detected=signals_detected,
            )
        )

    return CleanupPlan(
        session_id=session_id,
        source_file=source_file,
        cleanup_mode=cleanup_mode,
        overall_notes=overall_notes,
        items=items,
    )
```

#### Step 3.6: Update WebSocket Command Handling (PRIMARY GENERATION PATH)

**File:** `2.ai-library/src/api/routes/sessions.py`

The UI triggers cleanup generation via WebSocket (`generate_cleanup`). Parse `cleanup_mode` from the incoming command payload and pass it through the chain. Invalid modes must surface as an `error` event (no silent fallback to Balanced).

```python
# At top of file:
from ...models.cleanup_mode_setting import CleanupModeSetting

# Inside session_stream loop
if command == "generate_cleanup":
    cleanup_mode_raw = message.get("cleanup_mode", "balanced")
    try:
        cleanup_mode = CleanupModeSetting(cleanup_mode_raw)
    except ValueError:
        await _send_stream_event(
            websocket,
            "error",
            session_id,
            {"message": f"Invalid cleanup_mode: {cleanup_mode_raw!r}"},
        )
        continue

    async for event in manager.generate_cleanup_plan_with_ai(
        session_id,
        cleanup_mode=cleanup_mode,
    ):
        ...
```

---

### Phase 4: Update Data Models

#### Step 4.1: Update CleanupPlan model

**File:** `2.ai-library/src/models/cleanup_plan.py`

```python
from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CleanupDisposition(str, Enum):
    KEEP = "keep"
    DISCARD = "discard"


class SignalType(str, Enum):
    """Types of signals detected in content."""
    # Discard signals
    TIME_SENSITIVE = "time_sensitive"
    COMPLETED_ITEMS = "completed_items"
    EPHEMERAL_LINK = "ephemeral_link"
    STRUCTURAL_NOISE = "structural_noise"
    SOURCE_ONLY = "source_only"
    # Keep signals
    ORIGINAL_WORK = "original_work"
    REFERENCE_VALUE = "reference_value"
    EVERGREEN = "evergreen"
    CURATED_COLLECTION = "curated_collection"


class DetectedSignal(BaseModel):
    """A signal detected in the content."""
    type: str
    detail: str


class CleanupItem(BaseModel):
    """Single item in cleanup plan."""
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str

    # Model suggestion
    suggested_disposition: str = CleanupDisposition.KEEP
    suggestion_reason: str = ""
    confidence: float = 0.8
    signals_detected: List[DetectedSignal] = Field(default_factory=list)

    # User decision
    final_disposition: Optional[str] = None


class CleanupPlan(BaseModel):
    """Complete cleanup plan for a session."""
    session_id: str
    source_file: str
    created_at: datetime = Field(default_factory=datetime.now)
    overall_notes: str = ""
    cleanup_mode: str = "balanced"

    items: List[CleanupItem] = Field(default_factory=list)

    approved: bool = False
    approved_at: Optional[datetime] = None

    @property
    def all_decided(self) -> bool:
        return all(
            i.final_disposition in (CleanupDisposition.KEEP, CleanupDisposition.DISCARD)
            for i in self.items
        )
```

---

### Phase 5: Frontend Implementation

#### Step 5.1: Update TypeScript Types

**File:** `libs/types/src/knowledge-library.ts`

```typescript
// Add cleanup mode type
export type KLCleanupMode = 'conservative' | 'balanced' | 'aggressive';

/** Signal detected in cleanup analysis */
export interface KLDetectedSignal {
  type: string;
  detail: string;
}

/** Single cleanup item */
export interface KLCleanupItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  suggested_disposition: KLCleanupDisposition;
  suggestion_reason: string;
  confidence: number;
  signals_detected: KLDetectedSignal[];
  final_disposition: KLCleanupDisposition | null;
}

/** Cleanup plan response */
export interface KLCleanupPlanResponse {
  session_id: string;
  source_file: string;
  created_at: string;
  overall_notes: string;
  cleanup_mode: KLCleanupMode;
  items: KLCleanupItemResponse[];
  all_decided: boolean;
  approved: boolean;
  approved_at: string | null;
  pending_count: number;
  total_count: number;
}

/** WebSocket command request (extend existing type) */
export interface KLStreamCommandRequest {
  command: KLStreamCommand;

  /** NEW: for generate_cleanup */
  cleanup_mode?: KLCleanupMode;

  /** Existing command payloads */
  message?: string;
  question_id?: string;
  answer?: string;
}
```

#### Step 5.2: Update Zustand Store

**File:** `apps/ui/src/store/knowledge-library-store.ts`

Add cleanup mode to state:

```typescript
import type { KLCleanupMode } from '@automaker/types';

// Add to state interface (around line 118)
interface KnowledgeLibraryState {
  // ... existing fields ...

  // Cleanup settings
  cleanupMode: KLCleanupMode;
}

// Add to actions interface (around line 167)
interface KnowledgeLibraryActions {
  // ... existing actions ...

  setCleanupMode: (mode: KLCleanupMode) => void;
}

// Add to initial state (around line 185)
const initialState: KnowledgeLibraryState = {
  // ... existing fields ...
  cleanupMode: 'balanced',
};

// Add action implementation in store (around line 320)
setCleanupMode: (mode) => set({ cleanupMode: mode }),

// Add to persist partialize (around line 330)
partialize: (state) => ({
  activeView: state.activeView,
  currentSessionId: state.currentSessionId,
  cleanupMode: state.cleanupMode,  // NEW: Persist cleanup mode
}),
```

#### Step 5.3: Update API Client

**File:** `apps/ui/src/lib/knowledge-library-api.ts`

```typescript
import type { KLCleanupMode } from '@automaker/types';

// Update generateCleanupPlan method (around line 323)
async generateCleanupPlan(
  sessionId: string,
  useAi = true,
  cleanupMode: KLCleanupMode = 'balanced'
): Promise<KLCleanupPlanResponse> {
  return request<KLCleanupPlanResponse>(
    `/api/sessions/${sessionId}/cleanup/generate`,
    {
      method: 'POST',
      params: { use_ai: useAi, cleanup_mode: cleanupMode },
    }
  );
}
```

#### Step 5.4: Update Query Hook

**File:** `apps/ui/src/hooks/queries/use-knowledge-library.ts`

```typescript
import type { KLCleanupMode } from '@automaker/types';

// Update useKLGenerateCleanupPlan (around line 198)
export function useKLGenerateCleanupPlan(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      useAi = true,
      cleanupMode = 'balanced',
    }: {
      useAi?: boolean;
      cleanupMode?: KLCleanupMode;
    }) => knowledgeLibraryApi.generateCleanupPlan(sessionId, useAi, cleanupMode),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.cleanupPlan(sessionId),
      });
    },
  });
}
```

#### Step 5.5: Create CleanupModeSelector Component

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-mode-selector.tsx` (NEW)

```tsx
import type { ElementType } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Shield, Scale, Zap } from 'lucide-react';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import type { KLCleanupMode } from '@automaker/types';

const MODES: Array<{
  value: KLCleanupMode;
  label: string;
  icon: ElementType;
  description: string;
  color: string;
}> = [
  {
    value: 'conservative',
    label: 'Conservative',
    icon: Shield,
    description: 'Keep more - only discard obvious noise',
    color: 'text-blue-600 hover:bg-blue-50 border-blue-200',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    icon: Scale,
    description: 'Smart suggestions based on content signals',
    color: 'text-green-600 hover:bg-green-50 border-green-200',
  },
  {
    value: 'aggressive',
    label: 'Aggressive',
    icon: Zap,
    description: 'Discard more - flag time-sensitive content',
    color: 'text-orange-600 hover:bg-orange-50 border-orange-200',
  },
];

export function CleanupModeSelector() {
  const { cleanupMode, setCleanupMode } = useKnowledgeLibraryStore();

  return (
    <TooltipProvider>
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-lg">
        <span className="text-xs text-muted-foreground px-2">Cleanup:</span>
        {MODES.map((mode) => {
          const Icon = mode.icon;
          const isActive = cleanupMode === mode.value;

          return (
            <Tooltip key={mode.value}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    'h-7 px-2 text-xs',
                    isActive && `${mode.color} bg-background border`
                  )}
                  onClick={() => setCleanupMode(mode.value)}
                >
                  <Icon className="h-3.5 w-3.5 mr-1" />
                  {mode.label}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p className="font-medium">{mode.label}</p>
                <p className="text-xs text-muted-foreground">{mode.description}</p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}
```

#### Step 5.6: Create SignalBadges Component

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/signal-badges.tsx` (NEW)

```tsx
import type { ElementType } from 'react';
import { Badge } from '@/components/ui/badge';
import {
  Clock,
  CheckSquare,
  Link2,
  FileX,
  Quote,
  Lightbulb,
  BookOpen,
  Leaf,
  Library,
} from 'lucide-react';
import type { KLDetectedSignal } from '@automaker/types';

const SIGNAL_CONFIG: Record<
  string,
  { icon: ElementType; label: string; variant: 'default' | 'destructive' | 'secondary' }
> = {
  // Discard signals
  time_sensitive: { icon: Clock, label: 'Time-sensitive', variant: 'destructive' },
  completed_items: { icon: CheckSquare, label: 'Completed', variant: 'destructive' },
  ephemeral_link: { icon: Link2, label: 'Ephemeral', variant: 'destructive' },
  structural_noise: { icon: FileX, label: 'Noise', variant: 'destructive' },
  source_only: { icon: Quote, label: 'Source only', variant: 'destructive' },
  // Keep signals
  original_work: { icon: Lightbulb, label: 'Original', variant: 'default' },
  reference_value: { icon: BookOpen, label: 'Reference', variant: 'default' },
  evergreen: { icon: Leaf, label: 'Evergreen', variant: 'default' },
  curated_collection: { icon: Library, label: 'Curated', variant: 'default' },
};

interface SignalBadgesProps {
  signals: KLDetectedSignal[];
}

export function SignalBadges({ signals }: SignalBadgesProps) {
  if (!signals.length) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {signals.map((signal, idx) => {
        const config = SIGNAL_CONFIG[signal.type] || {
          icon: FileX,
          label: signal.type,
          variant: 'secondary' as const,
        };
        const Icon = config.icon;

        return (
          <Badge
            key={idx}
            variant={config.variant}
            className="text-xs py-0.5"
            title={signal.detail}
          >
            <Icon className="h-3 w-3 mr-1" />
            {config.label}
          </Badge>
        );
      })}
    </div>
  );
}
```

**Integrate into cleanup review UI**

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx`

Render badges on each cleanup item card (so the acceptance criterion “Signals are detected and displayed in UI” is actually met):

```tsx
import { SignalBadges } from './signal-badges';

// ...
<SignalBadges signals={item.signals_detected} />;
```

#### Step 5.7: Add CleanupModeSelector to Control Dock

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx`

Add the selector to the control dock (around line 167):

```tsx
import { CleanupModeSelector } from './components/cleanup-mode-selector';

// In the left column (pre-session UI), render above the Start button so the user
// can choose the mode before generation begins:
{!hasActiveSession ? (
  <div className="space-y-3">
    <CleanupModeSelector />
    {/* existing Start Session UI */}
  </div>
) : (
  /* existing active-session UI */
)}
```

#### Step 5.8: Update Workflow to Use Cleanup Mode

**File:** `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts`

Update to pass cleanup mode whenever the UI triggers cleanup generation (initial start + auto-regeneration after answering questions):

```typescript
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';

// In the hook, get cleanup mode from store
const { cleanupMode } = useKnowledgeLibraryStore();

const sendGenerateCleanup = () => {
  sendWebSocketCommand('generate_cleanup', { cleanup_mode: cleanupMode });
};

// Replace all generate_cleanup sends (startSession + auto-regeneration) with:
sendGenerateCleanup();
```

---

## Files Summary

### Files to Create (NEW)

| File                                                                                                        | Purpose                 |
| ----------------------------------------------------------------------------------------------------------- | ----------------------- |
| `2.ai-library/src/models/cleanup_mode_setting.py`                                                           | CleanupModeSetting enum |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-mode-selector.tsx` | Mode toggle UI          |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/signal-badges.tsx`         | Signal visualization    |

### Files to Modify

| File                                                                                                 | Changes                                                         |
| ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `2.ai-library/src/sdk/prompts/cleanup_mode.py`                                                       | Three mode prompts + factory function                           |
| `2.ai-library/src/sdk/prompts/__init__.py`                                                           | Export new functions                                            |
| `2.ai-library/src/models/cleanup_plan.py`                                                            | Add cleanup_mode + signals_detected (+ confidence via Plan 003) |
| `2.ai-library/src/models/__init__.py`                                                                | Export CleanupModeSetting                                       |
| `2.ai-library/src/api/schemas.py`                                                                    | Add cleanup_mode + signals_detected to responses                |
| `2.ai-library/src/api/routes/sessions.py`                                                            | Thread cleanup_mode through REST + WebSocket                    |
| `2.ai-library/src/session/manager.py`                                                                | Pass cleanup_mode to flow                                       |
| `2.ai-library/src/conversation/flow.py`                                                              | Pass cleanup_mode to SDK                                        |
| `2.ai-library/src/sdk/client.py`                                                                     | Use factory function for prompts                                |
| `libs/types/src/knowledge-library.ts`                                                                | Add cleanup mode + signals + WS payload typing                  |
| `apps/ui/src/store/knowledge-library-store.ts`                                                       | Add cleanupMode state                                           |
| `apps/ui/src/lib/knowledge-library-api.ts`                                                           | Pass cleanupMode in request                                     |
| `apps/ui/src/hooks/queries/use-knowledge-library.ts`                                                 | Update mutation signature                                       |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx`              | Add mode selector                                               |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx` | Render SignalBadges on items                                    |
| `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts`                       | Use cleanupMode                                                 |

---

## Testing Checklist

### Backend Tests

- [ ] CleanupModeSetting enum has correct values and properties
- [ ] get_cleanup_system_prompt returns correct prompt for each mode
- [ ] Conservative mode prompt is ~800 tokens
- [ ] Balanced mode prompt is ~900 tokens
- [ ] Aggressive mode prompt is ~900 tokens
- [ ] Only ONE prompt is sent per request (token efficiency)
- [ ] REST endpoint accepts cleanup_mode as a validated query param (and rejects invalid values with 422)
- [ ] WebSocket generate_cleanup command accepts cleanup_mode and rejects invalid values as an error event
- [ ] Mode flows end-to-end through the generation chain (UI → WebSocket/REST → manager → flow → SDK → prompt factory)
- [ ] Response includes cleanup_mode field

### Prompt Quality Tests

- [ ] Conservative mode: Meeting notes → KEEP (not flagged)
- [ ] Balanced mode: Meeting notes with 2+ signals → DISCARD
- [ ] Aggressive mode: Meeting notes → DISCARD (single signal sufficient)
- [ ] All modes: Reference documentation → KEEP
- [ ] Conservative: Partial todo list → KEEP
- [ ] Aggressive: Partial todo list → DISCARD

### Frontend Tests

- [ ] CleanupModeSelector renders all three modes
- [ ] Selected mode is visually highlighted
- [ ] Mode persists across page refreshes
- [ ] Mode is passed to backend when generating cleanup (WebSocket payload; REST query param if used)
- [ ] SignalBadges render with correct icons and colors

---

## Acceptance Criteria

- [ ] Users can select Conservative, Balanced, or Aggressive mode
- [ ] Selected mode persists in localStorage
- [ ] Only the selected mode's prompt is sent to AI (~800-900 tokens, NOT ~2400)
- [ ] Conservative mode keeps 90%+ content, only obvious noise flagged
- [ ] Balanced mode provides smart suggestions (20-30% discard for mixed docs)
- [ ] Aggressive mode actively flags time-sensitive content (40-50% discard)
- [ ] Signals are detected and displayed in UI
- [ ] Mode is visible in control dock before starting session
- [ ] Invalid cleanup_mode is rejected (REST 422 / WebSocket error event) — no silent fallback to Balanced

---

## Estimated Effort

| Component                          | Effort        |
| ---------------------------------- | ------------- |
| Three mode prompts                 | ~3 hours      |
| Factory function + exports         | ~30 min       |
| Backend call chain (mode plumbing) | ~2 hours      |
| Data models (Python + TypeScript)  | ~1 hour       |
| Frontend store + settings          | ~1.5 hours    |
| Mode selector UI                   | ~1 hour       |
| Signal badges component            | ~1 hour       |
| Integration testing                | ~2 hours      |
| **Total**                          | **~12 hours** |

---

## Dependencies

- **Plan 003** (UI Improvements) should be implemented first
  - Provides confidence bar, content preview box
  - This plan adds mode selector and signal badges on top

---

## Follow-up Work

### Phase 3: Per-Document Mode Memory

Remember which mode was used for each document:

- Persist cleanup_mode with the cleanup plan (and surface it in UI)
- Show "Last used: Aggressive" when re-processing

### Phase 4: Prompt Evaluation Harness (Recommended)

Make the “Conservative keeps ~90% / Aggressive discards ~40–50%” goals measurable:

- Add a small set of representative fixture documents (meeting notes, research notes, mixed docs)
- Run each mode against fixtures and track discard rate + false-positive examples
- Use results to iterate on prompt wording and/or server-side guardrails
