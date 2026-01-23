# Sub-Plan B: Smart Routing (Phase 2)

> **Master Plan Reference**: `knowledge-library-master-plan.md`
> **Execution Location**: This repository (`knowledge-library`)
> **Dependencies**: Sub-Plan A (Core Engine) must be completed
> **Next Phase**: Sub-Plan C (Vector/RAG)

---

## Goal

Implement the **planning intelligence** layer (via Claude Code SDK) that turns a parsed source document into:

1. a **CleanupPlan** (discard candidates + optional structuring suggestions), and then
2. a **RoutingPlan** that provides **top-3 destination options per kept block** (file + section + action + confidence),
   so the user can review decisions quickly in the Web UI (Phase 5) with **click-to-accept** controls and a single final approval.

This phase does _not_ execute writes. Execution + verification is Core Engine (Sub-Plan A).

**Key Changes from Original Design:**

- Two-step planning: CleanupPlan → RoutingPlan
- Routing is **manifest-constrained** (model chooses from provided library files/sections + can propose new ones)
- Per-block **top-3 options** with confidence (no typing required to choose)
- Structured re-routing on reject (choose alternative option or custom destination via UI pickers)

---

## Prerequisites from Phase 1

Before starting this phase, ensure the following from Sub-Plan A are complete:

- All core data models implemented (`ContentBlock`, `ExtractionSession`, `CleanupPlan`, `RoutingPlan`, `LibraryFile/Category`)
- Basic SDK client working (single-turn queries)
- Session management (create, load, save)
- Content extraction from markdown files
- Library manifest snapshot generation (files + sections)
- STRICT verification rules defined (code blocks byte-strict; prose canonicalization)

---

## New Capabilities

| Capability                       | Description                                                                                       |
| -------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Cleanup/Structuring Plan**     | Model proposes discard candidates and optional split/format suggestions; user explicitly approves |
| **Top-3 Routing Options**        | For each kept block, model returns 3 destination options with confidence + reasoning              |
| **Manifest-Constrained Routing** | Model chooses from provided files/sections and can propose new pages/sections explicitly          |
| **Click-to-Decide UX**           | User selects options via UI controls (no typing required for normal flow)                         |
| **Structured Re-routing**        | On reject, user picks an alternative option or custom file/section via pickers                    |
| **Refinement-Only Merges**       | Merge proposals (triple-view) are allowed only in refinement mode                                 |

---

## New Components

### Project Structure Additions

```
src/
├── conversation/
│   ├── __init__.py
│   ├── flow.py                   # Planning orchestration + event streaming
│   ├── cleanup_planner.py        # Generate CleanupPlan (discard candidates + structuring suggestions)
│   ├── routing_planner.py        # Generate RoutingPlan (top-3 options per kept block)
│   └── questions.py              # Optional multiple-choice questions for ambiguity
│
├── merge/
│   ├── __init__.py
│   ├── detector.py               # Detect merge candidates
│   ├── proposer.py               # Generate merge proposals
│   └── verifier.py               # Verify merge preserves all info
│
└── library/
    ├── candidates.py             # Lexical candidate finder (Phase 2; vectors in Phase 3)
    └── manifest.py               # Library manifest (from Sub-Plan A)
```

---

## Simplified Extraction Flow

### Complete Extraction Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SIMPLIFIED EXTRACTION FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. INITIALIZE                                                               │
│     └─ Read source document, extract blocks with checksums                   │
│                         │                                                    │
│                         ▼                                                    │
│  2. SCAN LIBRARY                                                             │
│     └─ Build Library Manifest (files + sections + summaries)                 │
│                         │                                                    │
│                         ▼                                                    │
│  3. GENERATE CLEANUP PLAN (Single Pass)                                      │
│     ├─ Propose discard candidates (e.g., meta scores, redundant sources)     │
│     ├─ Propose optional structuring/splitting suggestions                    │
│     └─ Output: CleanupPlan (NO automatic discard)                            │
│                         │                                                    │
│                         ▼                                                    │
│  4. USER REVIEWS CLEANUP (UI)                                                │
│     ├─ Keep/Discard decisions per item (explicit; no silent discard)         │
│     └─ All cleanup items must be decided before routing                      │
│                         │                                                    │
│                         ▼                                                    │
│  5. GENERATE ROUTING PLAN (Single Pass)                                      │
│     ├─ For each kept block, produce TOP-3 destination options + confidence   │
│     ├─ Constrain options using the Library Manifest (avoid hallucinations)   │
│     ├─ Allow explicit proposals for new pages/sections                        │
│     └─ Output: RoutingPlan (per-block options + selections pending)          │
│                         │                                                    │
│                         ▼                                                    │
│  6. USER REVIEWS ROUTING (UI)                                                │
│     ├─ Select 1 of 3 options per block (no typing)                            │
│     ├─ Reject → choose alternative option or custom file/section picker       │
│     └─ All kept blocks must be resolved before approval                      │
│                         │                                                    │
│                         ▼                                                    │
│  7. FINAL APPROVAL (Single Click)                                            │
│     └─ Approve complete plan once everything is resolved                     │
│                         │                                                    │
│                         ▼                                                    │
│  8. EXECUTE + VERIFY (Core Engine)                                           │
│     ├─ Write blocks with markers + read-back verification                     │
│     ├─ STRICT: code byte-strict; prose canonical checksum                     │
│     └─ Report verification results                                           │
│                         │                                                    │
│                         ▼                                                    │
│  9. DELETE SOURCE (Optional)                                                 │
│     └─ Only after 100% verification success                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Planning Flow (`src/conversation/flow.py`)

This replaces incremental, CLI-driven routing with an SDK-first planning pipeline:

1. `generate_cleanup_plan(...)` → `CleanupPlan` (discard candidates + structuring suggestions)
2. user approves cleanup decisions in UI
3. `generate_routing_plan(...)` → `RoutingPlan` (top-3 options per kept block)
4. user selects destinations in UI (no typing)

Phase 2 uses a **manifest + lexical candidate finder**. Vector/RAG improves candidate quality in Phase 3.

```python
# src/conversation/flow.py

from dataclasses import dataclass
from typing import AsyncIterator
import json

from ..models.session import ExtractionSession, SessionPhase
from ..models.cleanup_plan import CleanupPlan, CleanupItem, CleanupDisposition
from ..models.routing_plan import RoutingPlan, BlockRoutingItem, BlockDestination, PlanSummary
from ..sdk.client import SDKClient
from ..library.manifest import LibraryManifestBuilder
from ..library.candidates import CandidateFinder


@dataclass
class PlanEvent:
    type: str  # "progress" | "cleanup_ready" | "routing_ready" | "error"
    data: dict


class PlanningFlow:
    def __init__(self, sdk: SDKClient, manifest: LibraryManifestBuilder, candidates: CandidateFinder):
        self.sdk = sdk
        self.manifest = manifest
        self.candidates = candidates

    async def generate_cleanup_plan(self, session: ExtractionSession) -> AsyncIterator[PlanEvent]:
        yield PlanEvent("progress", {"message": "Building cleanup prompt..."})

        # Build prompt using extracted blocks + heading paths
        prompt = self._build_cleanup_prompt(session)
        raw = await self.sdk.query(prompt)
        data = json.loads(raw)

        plan = CleanupPlan(
            session_id=session.id,
            source_file=session.source.file_path if session.source else "",
            items=[
                CleanupItem(**item)
                for item in data.get("items", [])
            ],
        )

        session.cleanup_plan = plan
        session.phase = SessionPhase.CLEANUP_PLAN_READY
        yield PlanEvent("cleanup_ready", {"plan": plan.model_dump()})

    async def generate_routing_plan(self, session: ExtractionSession) -> AsyncIterator[PlanEvent]:
        if not session.cleanup_plan or not session.cleanup_plan.approved:
            raise ValueError("Cleanup plan must be approved before routing")

        yield PlanEvent("progress", {"message": "Building library manifest..."})
        session.library_manifest = await self.manifest.build(session.library_path)

        kept_blocks = self._get_kept_blocks(session)
        yield PlanEvent("progress", {"message": f"Finding candidates for {len(kept_blocks)} blocks..."})

        # Precompute constrained candidates (Phase 2 = lexical; Phase 3 adds vectors)
        block_candidates = {
            b.id: await self.candidates.top_candidates(session.library_manifest, b)
            for b in kept_blocks
        }

        # Single-pass prompt for all kept blocks (batch if too large)
        prompt = self._build_routing_prompt(session, kept_blocks, block_candidates)
        raw = await self.sdk.query(prompt)
        data = json.loads(raw)

        plan = RoutingPlan(
            session_id=session.id,
            source_file=session.source.file_path if session.source else "",
            content_mode=session.content_mode.value,
            blocks=[
                BlockRoutingItem(**item)
                for item in data.get("blocks", [])
            ],
        )
        plan.summary = self._create_summary(plan)

        session.routing_plan = plan
        session.phase = SessionPhase.ROUTING_PLAN_READY
        yield PlanEvent("routing_ready", {"plan": plan.model_dump()})

    def _create_summary(self, plan: RoutingPlan) -> PlanSummary:
        # Summary uses chosen actions only after user selection; here we provide rough estimates.
        return PlanSummary(
            total_blocks=len(plan.blocks),
            blocks_to_new_files=0,
            blocks_to_existing_files=0,
            blocks_requiring_merge=len(plan.merge_previews),
            estimated_actions=len(plan.blocks),
        )
```

### 2. Prompt Contracts (Cleanup + Routing)

This system works best when Claude is constrained to strict JSON contracts so the UI can render decisions as buttons/radios (no typing required in the normal flow).

#### 2.1 Cleanup Prompt → `CleanupPlan`

**Model input (minimum):**

- blocks with `{block_id, heading_path, block_type, content_preview}`
- cleanup policy: default keep; discard requires explicit user approval

**Expected JSON response (example):**

```json
{
  "items": [
    {
      "block_id": "block_004",
      "heading_path": ["COMBINED VERDICT"],
      "content_preview": "### VERDICT: COMPLETE ...",
      "suggested_disposition": "discard",
      "suggestion_reason": "Meta scoreboard; not durable knowledge."
    }
  ],
  "questions": [
    {
      "id": "q_001",
      "question": "Discard the Scores/Verdict/Confidence summary?",
      "options": ["Keep", "Discard"],
      "block_ids": ["block_004"]
    }
  ]
}
```

Rules:

- The model may _suggest_ discards, but the engine must treat everything as **keep** until the user explicitly discards in UI.

#### 2.2 Routing Prompt → `RoutingPlan` (Top-3 Options)

**Model input (minimum):**

- kept blocks with `{block_id, heading_path, block_type, content_preview}`
- library manifest snapshot (paths + sections + short summaries)
- per-block candidate destinations (Phase 2 lexical; Phase 3 vectors)
- allowed actions based on `content_mode` (STRICT forbids `merge`)

**Expected JSON response (example):**

```json
{
  "blocks": [
    {
      "block_id": "block_001",
      "heading_path": ["STEP 2", "Alignment Validation"],
      "content_preview": "### Original Intent ...",
      "options": [
        {
          "destination_file": "library/blueprints/specs-and-plans.md",
          "destination_section": "Implementation Plan Schema",
          "action": "append",
          "confidence": 0.9,
          "reasoning": "Directly defines schema fields."
        },
        {
          "destination_file": "library/systems/ace.md",
          "destination_section": "Spec Standards",
          "action": "append",
          "confidence": 0.6,
          "reasoning": "Related but broader."
        },
        {
          "destination_file": "library/notes/inbox.md",
          "destination_section": null,
          "action": "create_section",
          "confidence": 0.5,
          "reasoning": "Fallback if uncertain."
        }
      ]
    }
  ],
  "questions": []
}
```

Hard constraints:

- For existing destinations, `destination_file`/`destination_section` must be from the provided manifest.
- For new pages/sections, use `create_file`/`create_section` and include proposed titles (fields in `BlockDestination`).

### 3. Rejection / Re-routing (No Typing)

When a user rejects the top option for a block:

- choose option #2 or #3, or
- choose a custom `{file, section, action}` using manifest pickers, or
- answer a model question via multiple-choice buttons (no free-text required).

## Appendix: Legacy Phase Handlers (Deprecated)

The following legacy incremental handlers are **deprecated** (kept here only for historical reference). The current design uses `PlanningFlow` + prompt contracts above.

| File                                 | Reason                                                                                   |
| ------------------------------------ | ---------------------------------------------------------------------------------------- |
| `src/conversation/category_phase.py` | Deprecated; categories are implicit in routing destinations + new page/section proposals |
| `src/conversation/routing_phase.py`  | Deprecated; replaced by `routing_planner.py` top-3 option generation                     |
| `src/conversation/refinement.py`     | Deprecated; refinement is handled via option selection + (optional) question prompts     |

### 2. Category Phase Handler (`src/conversation/category_phase.py`)

````python
# src/conversation/category_phase.py

from typing import AsyncIterator
import json

from ..models.session import ExtractionSession
from ..models.library import CategoryProposal
from ..sdk.client import SDKClient
from .flow import ConversationEvent


CATEGORY_PROPOSAL_PROMPT = """
You are analyzing content to propose organizational categories for a knowledge library.

## Source Document Content

{source_content}

## Existing Library Structure

{library_structure}

## Your Task

Based on the content blocks extracted from the source document, propose categories
for organizing this information. Consider:

1. What logical groupings exist in the content?
2. Do any categories already exist in the library that could hold this content?
3. Should new categories be created?

## Response Format

Respond with a JSON object:
```json
{{
  "categories": [
    {{
      "id": "cat_001",
      "name": "category-name",
      "folder_path": "library/parent-folder",
      "file_name": "category-name.md",
      "description": "What belongs in this category",
      "proposed_sections": ["Section 1", "Section 2"],
      "matching_block_ids": ["block_001", "block_002"]
    }}
  ],
  "questions": [
    {{
      "id": "q_001",
      "question": "Should X be grouped with Y or kept separate?",
      "options": ["Group together", "Keep separate"],
      "context": "Blocks 3 and 7 both discuss authentication but from different angles"
    }}
  ]
}}
````

If you need clarification before proposing categories, include questions.
Every block must be assigned to exactly one category.
"""

class CategoryPhaseHandler:
"""Handles the category proposal phase of extraction."""

    def __init__(self, sdk_client: SDKClient):
        self.sdk = sdk_client

    async def propose_categories(
        self,
        session: ExtractionSession,
    ) -> AsyncIterator[ConversationEvent]:
        """
        Generate category proposals for the source content.
        """
        # Build context for the model
        source_content = self._format_source_content(session)
        library_structure = self._format_library_structure(session)

        prompt = CATEGORY_PROPOSAL_PROMPT.format(
            source_content=source_content,
            library_structure=library_structure,
        )

        # Query SDK
        response = await self.sdk.query(prompt)

        # Parse response
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            yield ConversationEvent("error", {
                "message": "Failed to parse category proposals from model"
            })
            return

        # Process categories
        for cat_data in data.get("categories", []):
            proposal = CategoryProposal(**cat_data)
            session.category_proposals.append(proposal)
            yield ConversationEvent("proposal", {
                "type": "category",
                "proposal": proposal.model_dump()
            })

        # Process questions
        for question in data.get("questions", []):
            session.pending_questions.append(question)
            yield ConversationEvent("question", {"question": question})

    def _format_source_content(self, session: ExtractionSession) -> str:
        """Format source blocks for the prompt."""
        if not session.source:
            return "(No source document)"

        lines = []
        for block in session.source.blocks:
            lines.append(f"[{block.id}] ({block.block_type.value})")
            if block.header:
                lines.append(f"  Header: {block.header}")
            lines.append(f"  Content: {block.content[:200]}...")
            lines.append("")

        return "\n".join(lines)

    def _format_library_structure(self, session: ExtractionSession) -> str:
        """Format existing library structure for the prompt."""
        if not session.existing_categories:
            return "(Empty library - no existing categories)"

        return "\n".join(f"- {cat}" for cat in session.existing_categories)

````

### 3. Routing Phase Handler (`src/conversation/routing_phase.py`)

```python
# src/conversation/routing_phase.py

from typing import AsyncIterator
import json

from ..models.session import ExtractionSession
from ..models.recommendation import Recommendation, ActionType, MergeProposal
from ..sdk.client import SDKClient
from ..merge.detector import MergeDetector
from .flow import ConversationEvent


ROUTING_PROMPT = """
You are routing content blocks to their destinations in a knowledge library.

## Approved Categories

{categories}

## Content Blocks to Route

{blocks}

## Existing Library Content (for merge detection)

{existing_content}

## Your Task

For each content block, decide:
1. Which category/file it belongs to
2. Whether to create a new section or append to existing
3. Whether it should be merged with existing similar content
4. Your confidence level (0.0 to 1.0)

## Response Format

```json
{{
  "recommendations": [
    {{
      "id": "rec_001",
      "block_id": "block_001",
      "action": "append",
      "target_file": "library/tech/auth.md",
      "target_section": "Token Validation",
      "reasoning": "This content discusses JWT validation which fits the auth category",
      "confidence": 0.95
    }}
  ],
  "merge_proposals": [
    {{
      "id": "merge_001",
      "block_id": "block_003",
      "recommendation_id": "rec_003",
      "existing_content": "Current content in library...",
      "existing_location": "library/tech/auth.md#Token Validation",
      "new_content": "New content from source...",
      "proposed_merge": "Merged content combining both...",
      "merge_reasoning": "Both discuss token validation, merged to avoid duplication"
    }}
  ]
}}
````

## Action Types

- create_file: Create a new file
- create_section: Create a new section in existing file
- append: Add to end of existing section
- insert_before: Insert before specific content
- insert_after: Insert after specific content
- merge: Combine with existing similar content

IMPORTANT: Every block MUST have a recommendation. No block can be left unrouted.
"""

class RoutingPhaseHandler:
"""Handles the routing phase of extraction."""

    def __init__(self, sdk_client: SDKClient):
        self.sdk = sdk_client
        self.merge_detector = MergeDetector()

    async def propose_routing(
        self,
        session: ExtractionSession,
    ) -> AsyncIterator[ConversationEvent]:
        """
        Generate routing recommendations for all blocks.
        """
        # Build context
        categories = self._format_categories(session)
        blocks = self._format_blocks(session)
        existing_content = await self._get_existing_content(session)

        prompt = ROUTING_PROMPT.format(
            categories=categories,
            blocks=blocks,
            existing_content=existing_content,
        )

        # Query SDK
        response = await self.sdk.query(prompt)

        # Parse response
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            yield ConversationEvent("error", {
                "message": "Failed to parse routing recommendations from model"
            })
            return

        # Process recommendations
        for rec_data in data.get("recommendations", []):
            rec_data["action"] = ActionType(rec_data["action"])
            recommendation = Recommendation(
                **rec_data,
                content_preview=self._get_block_preview(session, rec_data["block_id"])
            )
            session.recommendations.append(recommendation)

            # Mark block as resolved
            self._mark_block_resolved(session, rec_data["block_id"])

            yield ConversationEvent("proposal", {
                "type": "recommendation",
                "recommendation": recommendation.model_dump()
            })

        # Process merge proposals
        for merge_data in data.get("merge_proposals", []):
            merge = MergeProposal(**merge_data)
            session.merge_proposals.append(merge)

            yield ConversationEvent("proposal", {
                "type": "merge",
                "merge": merge.model_dump()
            })

        # Verify all blocks are routed
        unrouted = self._get_unrouted_blocks(session)
        if unrouted:
            yield ConversationEvent("warning", {
                "message": f"{len(unrouted)} blocks not routed",
                "block_ids": unrouted
            })

    def _format_categories(self, session: ExtractionSession) -> str:
        """Format approved categories."""
        lines = []
        for cat in session.category_proposals:
            if cat.approved:
                lines.append(f"- {cat.name}: {cat.folder_path}/{cat.file_name}")
                lines.append(f"  Description: {cat.description}")
                if cat.proposed_sections:
                    lines.append(f"  Sections: {', '.join(cat.proposed_sections)}")
        return "\n".join(lines)

    def _format_blocks(self, session: ExtractionSession) -> str:
        """Format blocks for routing."""
        if not session.source:
            return ""

        lines = []
        for block in session.source.blocks:
            if not block.is_resolved:
                lines.append(f"[{block.id}] ({block.block_type.value})")
                lines.append(f"  {block.content}")
                lines.append("")

        return "\n".join(lines)

    async def _get_existing_content(self, session: ExtractionSession) -> str:
        """Get relevant existing content for merge detection."""
        # This will be enhanced with vector search in Phase 3
        # For now, just note that the library path exists
        return f"(Library at: {session.library_path})"

    def _get_block_preview(self, session: ExtractionSession, block_id: str) -> str:
        """Get preview text for a block."""
        if not session.source:
            return ""

        for block in session.source.blocks:
            if block.id == block_id:
                return block.content[:200]

        return ""

    def _mark_block_resolved(self, session: ExtractionSession, block_id: str) -> None:
        """Mark a block as resolved."""
        if not session.source:
            return

        for block in session.source.blocks:
            if block.id == block_id:
                block.is_resolved = True
                break

    def _get_unrouted_blocks(self, session: ExtractionSession) -> list[str]:
        """Get list of blocks that haven't been routed."""
        if not session.source:
            return []

        return [
            block.id for block in session.source.blocks
            if not block.is_resolved
        ]

````

### 4. Refinement Handler (`src/conversation/refinement.py`)

```python
# src/conversation/refinement.py

from typing import AsyncIterator
import json

from ..models.session import ExtractionSession
from ..models.recommendation import Recommendation, ActionType
from ..sdk.client import SDKClient
from .flow import ConversationEvent


REFINEMENT_PROMPT = """
The user has rejected a routing recommendation. Please provide an alternative.

## Rejected Recommendation

Block ID: {block_id}
Original Target: {original_target}
Original Action: {original_action}
User Feedback: {feedback}

## Block Content

{block_content}

## Available Categories

{categories}

## Your Task

Provide an alternative routing recommendation that addresses the user's feedback.
Consider:
1. The user's specific concerns
2. Alternative locations that might be more appropriate
3. Whether a new category should be suggested

## Response Format

```json
{{
  "recommendation": {{
    "id": "{new_id}",
    "block_id": "{block_id}",
    "action": "append",
    "target_file": "alternative/path.md",
    "target_section": "Alternative Section",
    "reasoning": "Based on user feedback, this location is better because...",
    "confidence": 0.85
  }},
  "follow_up_question": null
}}
````

If you need clarification, include a follow_up_question instead of a recommendation.
"""

class RefinementHandler:
"""Handles refinement of rejected recommendations."""

    def __init__(self, sdk_client: SDKClient):
        self.sdk = sdk_client

    async def refine_recommendation(
        self,
        session: ExtractionSession,
        item_id: str,
        feedback: str,
    ) -> AsyncIterator[ConversationEvent]:
        """
        Generate a refined recommendation based on user feedback.
        """
        # Find the rejected recommendation
        original = None
        for rec in session.recommendations:
            if rec.id == item_id:
                original = rec
                break

        if not original:
            yield ConversationEvent("error", {
                "message": f"Recommendation {item_id} not found"
            })
            return

        # Get block content
        block_content = self._get_block_content(session, original.block_id)

        # Build prompt
        prompt = REFINEMENT_PROMPT.format(
            block_id=original.block_id,
            original_target=original.target_file,
            original_action=original.action.value,
            feedback=feedback,
            block_content=block_content,
            categories=self._format_categories(session),
            new_id=f"rec_{len(session.recommendations):03d}",
        )

        # Query SDK
        response = await self.sdk.query(prompt)

        # Parse response
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            yield ConversationEvent("error", {
                "message": "Failed to parse refined recommendation"
            })
            return

        if data.get("follow_up_question"):
            session.pending_questions.append({
                "id": f"q_{len(session.pending_questions):03d}",
                "question": data["follow_up_question"],
                "context": f"Regarding block {original.block_id}"
            })
            yield ConversationEvent("question", {
                "question": data["follow_up_question"]
            })
        elif data.get("recommendation"):
            rec_data = data["recommendation"]
            rec_data["action"] = ActionType(rec_data["action"])
            new_rec = Recommendation(
                **rec_data,
                content_preview=block_content[:200],
                alternatives=[{
                    "id": original.id,
                    "target": original.target_file,
                    "rejected_reason": feedback
                }]
            )

            # Replace old recommendation
            session.recommendations = [
                r for r in session.recommendations if r.id != item_id
            ]
            session.recommendations.append(new_rec)

            yield ConversationEvent("proposal", {
                "type": "recommendation",
                "recommendation": new_rec.model_dump(),
                "replaces": item_id
            })

    def _get_block_content(self, session: ExtractionSession, block_id: str) -> str:
        """Get content for a specific block."""
        if not session.source:
            return ""

        for block in session.source.blocks:
            if block.id == block_id:
                return block.content

        return ""

    def _format_categories(self, session: ExtractionSession) -> str:
        """Format available categories."""
        lines = []
        for cat in session.category_proposals:
            if cat.approved:
                lines.append(f"- {cat.name}: {cat.folder_path}/{cat.file_name}")
        return "\n".join(lines)

````

## Refinement-Mode Merge Support (Optional in Phase 2)

STRICT mode forbids rewrites/merges. Merge support is only used when the user switches the session to **REFINEMENT** and explicitly approves merge proposals (triple-view).

### 5. Merge Detector (`src/merge/detector.py`)

```python
# src/merge/detector.py

from typing import Optional
from dataclasses import dataclass

from ..models.content import ContentBlock
from ..models.library import LibraryFile


@dataclass
class MergeCandidate:
    """A potential merge between new and existing content."""
    block_id: str
    existing_file: str
    existing_section: str
    existing_content: str
    similarity_score: float


class MergeDetector:
    """
    Detects when new content should be merged with existing library content.

    In Phase 2, this uses simple text matching.
    In Phase 3, this will be enhanced with vector similarity search.
    """

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def find_merge_candidates(
        self,
        block: ContentBlock,
        existing_files: list[LibraryFile],
        existing_content: dict[str, str],  # file_path -> content
    ) -> list[MergeCandidate]:
        """
        Find existing content that might be merge candidates for a block.
        """
        candidates = []

        for file in existing_files:
            file_content = existing_content.get(file.path, "")
            if not file_content:
                continue

            # Simple keyword overlap detection (Phase 3 will use vectors)
            similarity = self._calculate_similarity(
                block.normalized_content,
                file_content
            )

            if similarity >= self.similarity_threshold:
                # Find the most relevant section
                section = self._find_relevant_section(
                    block.normalized_content,
                    file_content,
                    file.sections
                )

                candidates.append(MergeCandidate(
                    block_id=block.id,
                    existing_file=file.path,
                    existing_section=section or "General",
                    existing_content=self._extract_section_content(
                        file_content, section
                    ),
                    similarity_score=similarity,
                ))

        return sorted(candidates, key=lambda c: c.similarity_score, reverse=True)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using keyword overlap.
        This is a placeholder - Phase 3 will use vector similarity.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def _find_relevant_section(
        self,
        block_content: str,
        file_content: str,
        sections: list[str],
    ) -> Optional[str]:
        """Find the most relevant section in a file."""
        if not sections:
            return None

        best_section = None
        best_score = 0.0

        for section in sections:
            # Extract section content
            section_content = self._extract_section_content(file_content, section)
            score = self._calculate_similarity(block_content, section_content)

            if score > best_score:
                best_score = score
                best_section = section

        return best_section

    def _extract_section_content(
        self,
        file_content: str,
        section: Optional[str],
    ) -> str:
        """Extract content for a specific section."""
        if not section:
            return file_content[:500]  # Return start of file

        # Simple section extraction (find header and content until next header)
        lines = file_content.split("\n")
        in_section = False
        section_lines = []

        for line in lines:
            if line.startswith("#") and section.lower() in line.lower():
                in_section = True
                continue
            elif line.startswith("#") and in_section:
                break
            elif in_section:
                section_lines.append(line)

        return "\n".join(section_lines) if section_lines else file_content[:500]
````

### 6. Merge Proposer (`src/merge/proposer.py`)

```python
# src/merge/proposer.py

from typing import Optional
import json

from ..models.recommendation import MergeProposal
from ..sdk.client import SDKClient
from .detector import MergeCandidate


MERGE_PROPOSAL_PROMPT = """
You need to merge new content with existing library content.

## Existing Content (in library)

Location: {existing_location}

```

{existing_content}

```

## New Content (from source document)

```

{new_content}

````

## Your Task

Create a merged version that:
1. Preserves ALL information from both sources
2. Eliminates redundancy
3. Maintains logical flow
4. Uses consistent formatting

## Response Format

```json
{{
  "proposed_merge": "The merged content here...",
  "merge_reasoning": "Explanation of how content was combined"
}}
````

CRITICAL: Do NOT lose any information. The merge must contain everything from both sources.
"""

class MergeProposer:
"""Creates merge proposals combining new and existing content."""

    def __init__(self, sdk_client: SDKClient):
        self.sdk = sdk_client

    async def create_merge_proposal(
        self,
        merge_id: str,
        recommendation_id: str,
        candidate: MergeCandidate,
        new_content: str,
    ) -> Optional[MergeProposal]:
        """
        Create a merge proposal for a detected merge candidate.
        """
        prompt = MERGE_PROPOSAL_PROMPT.format(
            existing_location=f"{candidate.existing_file}#{candidate.existing_section}",
            existing_content=candidate.existing_content,
            new_content=new_content,
        )

        response = await self.sdk.query(prompt)

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return None

        return MergeProposal(
            id=merge_id,
            block_id=candidate.block_id,
            recommendation_id=recommendation_id,
            existing_content=candidate.existing_content,
            existing_location=f"{candidate.existing_file}#{candidate.existing_section}",
            new_content=new_content,
            proposed_merge=data["proposed_merge"],
            merge_reasoning=data["merge_reasoning"],
        )

````

### 7. Merge Verifier (`src/merge/verifier.py`)

```python
# src/merge/verifier.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class VerificationResult:
    """Result of merge verification."""
    is_valid: bool
    missing_from_existing: list[str]  # Content that was in existing but not in merge
    missing_from_new: list[str]       # Content that was in new but not in merge
    warnings: list[str]


class MergeVerifier:
    """
    Verifies that merge proposals preserve all information.

    **CRITICAL GUARDRAIL**: If ANY information would be lost, the merge is
    REJECTED and flagged for user attention.
    """

    def verify_no_information_loss(
        self,
        existing_content: str,
        new_content: str,
        proposed_merge: str,
    ) -> VerificationResult:
        """
        STRICT verification that merge preserves ALL information.

        This is a critical guardrail - if ANY information would be lost,
        the merge is REJECTED and flagged for user attention.
        """
        existing_phrases = self._extract_key_phrases(existing_content)
        new_phrases = self._extract_key_phrases(new_content)
        merge_phrases = self._extract_key_phrases(proposed_merge)

        missing_from_existing = []
        for phrase in existing_phrases:
            if not self._phrase_present(phrase, merge_phrases):
                missing_from_existing.append(phrase)

        missing_from_new = []
        for phrase in new_phrases:
            if not self._phrase_present(phrase, merge_phrases):
                missing_from_new.append(phrase)

        # STRICT: Any missing content = invalid merge
        is_valid = len(missing_from_existing) == 0 and len(missing_from_new) == 0

        if not is_valid:
            warnings = [
                "MERGE REJECTED: Would lose information",
                f"Missing from existing: {missing_from_existing}",
                f"Missing from new: {missing_from_new}",
            ]
        else:
            warnings = []

        return VerificationResult(
            is_valid=is_valid,
            missing_from_existing=missing_from_existing,
            missing_from_new=missing_from_new,
            warnings=warnings,
        )

    def verify_merge(
        self,
        existing_content: str,
        new_content: str,
        proposed_merge: str,
    ) -> VerificationResult:
        """
        Verify that the proposed merge contains all content from both sources.
        Alias for verify_no_information_loss for backwards compatibility.
        """
        return self.verify_no_information_loss(existing_content, new_content, proposed_merge)

    def _extract_key_phrases(self, content: str) -> list[str]:
        """Extract key phrases for comparison."""
        # Split into sentences/phrases
        phrases = []

        # Split by newlines and periods
        for line in content.split("\n"):
            line = line.strip()
            if len(line) > 20:  # Ignore very short lines
                phrases.append(line.lower())

        return phrases

    def _phrase_present(self, phrase: str, phrase_list: list[str]) -> bool:
        """Check if a phrase (or close variant) is present in the list."""
        # Normalize
        phrase_words = set(phrase.split())

        for candidate in phrase_list:
            candidate_words = set(candidate.split())

            # Check for significant overlap
            overlap = phrase_words & candidate_words
            if len(overlap) >= len(phrase_words) * 0.7:
                return True

        return False
````

---

## Merge Verification UI (Web UI in Phase 5)

Primary UX is the Web UI (Sub-Plan F). A CLI-style merge viewer can exist as optional developer tooling, but the product path is UI-based.

### Merge Verification Display

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MERGE VERIFICATION: merge_001                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Block: block_007 → library/tech/authentication.md                           │
│  Section: Token Validation                                                   │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│  EXISTING CONTENT (currently in library):                                    │
│  ───────────────────────────────────────────────────────────────────────    │
│  Tokens should be validated on every request to ensure they haven't          │
│  expired or been tampered with.                                              │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│  NEW CONTENT (from source document):                                         │
│  ───────────────────────────────────────────────────────────────────────    │
│  JWT validation must include:                                                │
│  - Expiry check (exp claim)                                                  │
│  - Signature verification                                                    │
│  - Issuer validation (iss claim)                                             │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│  PROPOSED MERGE:                                                             │
│  ───────────────────────────────────────────────────────────────────────    │
│  Tokens should be validated on every request to ensure they haven't          │
│  expired or been tampered with. JWT validation must include:                 │
│  - Expiry check (exp claim)                                                  │
│  - Signature verification                                                    │
│  - Issuer validation (iss claim)                                             │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                              │
│  Options:                                                                    │
│    [A] Approve merge as proposed                                             │
│    [E] Edit merged content                                                   │
│    [S] Keep separate (append instead of merge)                               │
│    [R] Reject (discuss further)                                              │
│                                                                              │
│  Choice: _                                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### CLI Commands for Merge Verification

Add to `src/cli.py`:

```python
async def cmd_merge(args: argparse.Namespace) -> int:
    """Review and decide on merge proposals."""
    config = load_config()
    manager = SessionManager(config)

    session = await manager.load_session(args.session_id)

    # Find the merge proposal
    merge = None
    for m in session.merge_proposals:
        if m.id == args.merge_id:
            merge = m
            break

    if not merge:
        print(f"✗ Merge {args.merge_id} not found")
        return 1

    # Display triple view
    print_merge_verification(merge)

    # Get user decision
    if args.approve:
        merge.decision = "approve"
    elif args.edit:
        # Open editor for user to modify
        edited = edit_content(merge.proposed_merge)
        merge.decision = "edit"
        merge.user_edited_merge = edited
    elif args.separate:
        merge.decision = "separate"
    elif args.reject:
        merge.decision = "reject"
    else:
        # Interactive mode
        choice = input("Choice [A/E/S/R]: ").strip().upper()
        if choice == "A":
            merge.decision = "approve"
        elif choice == "E":
            edited = edit_content(merge.proposed_merge)
            merge.decision = "edit"
            merge.user_edited_merge = edited
        elif choice == "S":
            merge.decision = "separate"
        elif choice == "R":
            merge.decision = "reject"

    await manager.save_session(session)
    print(f"✓ Merge decision recorded: {merge.decision}")

    return 0


def print_merge_verification(merge: MergeProposal) -> None:
    """Print the triple-view merge verification UI."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.columns import Columns

    console = Console()

    console.print(Panel(
        f"Block: {merge.block_id} → {merge.existing_location}",
        title=f"MERGE VERIFICATION: {merge.id}",
    ))

    console.print("\n[bold]EXISTING CONTENT[/bold] (currently in library):")
    console.print(Panel(merge.existing_content, border_style="blue"))

    console.print("\n[bold]NEW CONTENT[/bold] (from source document):")
    console.print(Panel(merge.new_content, border_style="yellow"))

    console.print("\n[bold]PROPOSED MERGE[/bold]:")
    console.print(Panel(merge.proposed_merge, border_style="green"))

    console.print("\n[bold]Reasoning:[/bold]", merge.merge_reasoning)

    console.print("\nOptions:")
    console.print("  [A] Approve merge as proposed")
    console.print("  [E] Edit merged content")
    console.print("  [S] Keep separate (append instead of merge)")
    console.print("  [R] Reject (discuss further)")
```

---

## Acceptance Criteria

- [ ] CleanupPlan generation working (discard candidates + optional structuring suggestions)
- [ ] Cleanup decisions are explicit (no automatic discard)
- [ ] RoutingPlan generation working with top-3 options per kept block
- [ ] Routing options are constrained by Library Manifest (no hallucinated destinations)
- [ ] User can resolve blocks without typing (choose option #1/#2/#3 or custom picker)
- [ ] All-blocks-resolved gate enforced before plan approval (and before execution in Sub-Plan A)
- [ ] Refinement-mode merge support is optional and rejects merges that would lose information

---

## Notes for Downstream Session

1. **UI-first decisions**: Default decision flow is click-based (top-3 options + pickers); free-text is optional only for edge cases
2. **Phase 3 Enhancement**: Candidate finding and merge detection improve with vector similarity in Phase 3
3. **All Blocks Must Resolve**: This is a hard constraint - the system must not allow execution until every single block has a routing decision
4. **User Agency**: Always present alternatives and allow user to override model proposals (including new pages/sections)
5. **Idempotency**: Design for resumable sessions - user can stop and continue later

---

_End of Sub-Plan B_
