# Knowledge Library Cleanup AI Decision Criteria Improvements

**Status:** Ready for Implementation
**Priority:** High
**Impact:** Better AI recommendations for what content to keep vs discard
**Date Added:** 2026-01-26
**Related Upstream:** Not applicable (AI Library feature)
**Depends On:** Plan 003 (UI Improvements) should be implemented first for best results

## Summary

Improve the AI decision-making prompt for cleanup recommendations. The current prompt is overly conservative ("keep everything by default") and doesn't provide actionable signals for discard recommendations. This plan introduces structured discard criteria, signal detection, and removes the excessive conservatism while maintaining user safety.

## Problem Statement

### Current Issues

1. **Excessive conservatism**: Prompt explicitly says "preserve by default", "be conservative", resulting in "keep" for almost everything
2. **Vague criteria**: Only 4 generic discard criteria (temporary notes, duplicates, placeholders, completed todos)
3. **No signal detection**: AI doesn't identify specific patterns that indicate content should be discarded
4. **Missing source awareness**: No criteria for external-source-only content without user commentary
5. **No content type awareness**: Doesn't distinguish between reference material, original analysis, ephemeral content

### Current Prompt Criteria (lines 20-24)

```
1. **Identify Discard Candidates**: Flag content that may not belong in a permanent knowledge library:
   - Temporary notes, reminders, or time-sensitive content
   - Duplicate information
   - Placeholder text or incomplete thoughts
   - Personal todos that have been completed
```

### Impact

- AI suggests "keep" for 90%+ of content regardless of actual value
- Users must manually identify discard candidates
- "AI recommendation" provides little decision-making value
- Time-sensitive content (meeting notes, dated tasks) not flagged

## Solution Design

### New Decision Framework

```
DISCARD SIGNALS (suggest discard when multiple signals present):
├── Time-Sensitive Content
│   • Specific dates/times in the past
│   • Meeting links (Zoom, Teams, Google Meet)
│   • "Today", "Tomorrow", "This week" references
│   • Calendar-specific content
│
├── Completed/Stale Items
│   • Checked todo items [x]
│   • "Done", "Completed", "Finished" markers
│   • Old version numbers superseded by newer content
│   • Resolved issues or bugs
│
├── Ephemeral References
│   • Temporary URLs (bit.ly, short links, session tokens)
│   • One-time passwords or temporary credentials
│   • Draft/WIP markers with no substantive content
│   • "Scratch" or "temp" in titles
│
├── Structural Noise
│   • Empty sections with only headers
│   • Placeholder text ("TODO", "TBD", "Insert here", "Lorem ipsum")
│   • Boilerplate templates without customization
│   • Auto-generated content with no user additions
│
└── Source-Only Content (NEW)
    • Content that is purely quoted/copied from external sources
    • No user commentary, analysis, or synthesis
    • Better accessed at original source
    • Unattributed copy-paste without context

KEEP SIGNALS (strong indicators to preserve):
├── Original Analysis
│   • User's own insights, conclusions, opinions
│   • Synthesized information from multiple sources
│   • Personal notes with context
│
├── Reference Material
│   • Technical documentation with examples
│   • Reusable code snippets
│   • Best practices and patterns
│   • How-to guides and tutorials
│
├── Curated Collections
│   • Organized lists of resources
│   • Bookmarks with descriptions
│   • Reading lists with notes
│
└── Evergreen Content
    • Information that doesn't expire
    • Concepts and principles
    • Historical records worth preserving
```

### Signal Detection in Response

The AI should identify specific signals found in each block:

```json
{
  "cleanup_items": [
    {
      "block_id": "block_002",
      "suggested_disposition": "discard",
      "suggestion_reason": "Time-sensitive task list with completed items and expired meeting link",
      "confidence": 0.85,
      "signals_detected": [
        { "type": "time_sensitive", "detail": "Monday 9am PST (past date)" },
        { "type": "completed_items", "detail": "2 of 3 checkboxes marked done" },
        { "type": "ephemeral_link", "detail": "Zoom meeting URL" }
      ]
    }
  ]
}
```

## Implementation Plan

### Phase 1: Update System Prompt

#### Step 1.1: Replace CLEANUP_SYSTEM_PROMPT

**File:** `2.ai-library/src/sdk/prompts/cleanup_mode.py`

Replace the entire `CLEANUP_SYSTEM_PROMPT` constant:

````python
CLEANUP_SYSTEM_PROMPT = """You are a knowledge librarian assistant analyzing a document for extraction into a personal knowledge library.

Your task is to analyze the provided document blocks and suggest a cleanup plan. The user will make final decisions on all suggestions.

## Your Role

Evaluate each block to determine if it should be preserved in a permanent knowledge library or flagged for potential discard. Provide clear reasoning and confidence scores.

## Discard Signals

Flag content for DISCARD when you detect multiple of these signals:

### 1. Time-Sensitive Content
- Specific dates/times that have passed ("Monday 9am", "2024-01-15")
- Meeting links (Zoom, Teams, Google Meet, WebEx URLs)
- References to "today", "tomorrow", "this week", "next meeting"
- Calendar-specific content that won't be relevant later

### 2. Completed/Stale Items
- Checked todo items: `[x]` or `- [x]`
- Completion markers: "Done", "Completed", "Finished", "Resolved"
- Old version references when newer versions exist
- Issues or bugs marked as fixed/closed

### 3. Ephemeral References
- Short/temporary URLs (bit.ly, tinyurl, goo.gl)
- Session tokens, temporary passwords, one-time codes
- Draft/WIP markers with no substantive content
- Files/sections with "scratch", "temp", "draft" in the name

### 4. Structural Noise
- Empty sections containing only headers
- Placeholder text: "TODO", "TBD", "FIXME", "Insert here", "Lorem ipsum"
- Boilerplate templates that haven't been customized
- Auto-generated content with no user modifications

### 5. Source-Only Content
- Content that is purely copied from external sources
- No user commentary, analysis, or synthesis added
- Content that would be better accessed at the original source
- Unattributed quotes without context or reflection

## Keep Signals

Preserve content when you detect these positive signals:

### Original Work
- User's own insights, analysis, or conclusions
- Synthesized information combining multiple sources
- Personal notes that add context or interpretation
- Custom code, configurations, or solutions

### Reference Value
- Technical documentation with working examples
- Reusable code snippets or commands
- Best practices, patterns, or guidelines
- How-to guides and troubleshooting steps

### Evergreen Content
- Concepts and principles that don't expire
- Historical information worth preserving
- Curated resource lists with descriptions

## Output Format

Return a JSON object with this structure:

```json
{
  "cleanup_items": [
    {
      "block_id": "block_001",
      "suggested_disposition": "keep",
      "suggestion_reason": "Contains original technical analysis with working code examples",
      "confidence": 0.92,
      "signals_detected": [
        {"type": "original_work", "detail": "User's implementation notes"},
        {"type": "reference_value", "detail": "Includes tested code snippet"}
      ]
    },
    {
      "block_id": "block_002",
      "suggested_disposition": "discard",
      "suggestion_reason": "Time-sensitive meeting notes with completed action items",
      "confidence": 0.78,
      "signals_detected": [
        {"type": "time_sensitive", "detail": "Meeting dated 2024-01-10"},
        {"type": "completed_items", "detail": "3 of 4 action items checked off"},
        {"type": "ephemeral_link", "detail": "Contains Zoom meeting link"}
      ]
    }
  ],
  "overall_notes": "Document contains 5 blocks. 3 appear to be valuable reference material. 2 are time-sensitive meeting notes that may not need permanent storage."
}
````

## Decision Guidelines

1. **Balanced approach**: Neither keep everything nor discard aggressively
2. **Multiple signals**: Suggest discard only when 2+ discard signals are present
3. **Explain reasoning**: Always explain which signals led to the suggestion
4. **Confidence reflects certainty**:
   - 0.9+ = Very confident (clear signals, obvious decision)
   - 0.7-0.9 = Confident (signals present, reasonable certainty)
   - 0.5-0.7 = Uncertain (mixed signals, user should decide)
   - Below 0.5 = Default to keep
5. **User decides**: Remember that all decisions are suggestions - the user has final say
6. **When uncertain**: If signals are mixed, suggest keep with moderate confidence and note the uncertainty
   """

````

### Phase 2: Update User Prompt Builder

#### Step 2.1: Enhance build_cleanup_prompt function

**File:** `2.ai-library/src/sdk/prompts/cleanup_mode.py`

Update the instructions section:

```python
def build_cleanup_prompt(
    blocks: List[Dict[str, Any]],
    source_file: str,
    content_mode: str = "strict",
    conversation_history: str = "",
    pending_questions: Optional[List[str]] = None,
) -> str:
    """
    Build the user prompt for cleanup plan generation.
    """
    block_descriptions = []

    for block in blocks:
        heading = " > ".join(block.get("heading_path", [])) or "(no heading)"
        # Show more content for better analysis (500 chars instead of 300)
        preview = block["content"][:500]
        if len(block["content"]) > 500:
            preview += "..."

        block_descriptions.append(
            f"### Block {block['id']}\n"
            f"- Type: {block['type']}\n"
            f"- Heading Path: {heading}\n"
            f"- Content Preview:\n```\n{preview}\n```\n"
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

Analyze each block for cleanup suitability:

1. **Identify signals**: Look for both discard signals (time-sensitive, completed items, ephemeral, noise, source-only) and keep signals (original work, reference value, evergreen)

2. **Make balanced recommendations**: Don't default to "keep everything" - actually evaluate each block's long-term value

3. **Provide specific reasoning**: Cite the actual signals you detected (e.g., "contains dated meeting link from 2024-01-10")

4. **Set appropriate confidence**:
   - High confidence (0.8+) when signals are clear
   - Medium confidence (0.6-0.8) when signals exist but not overwhelming
   - Lower confidence (0.5-0.6) when uncertain - lean toward keep

5. **List detected signals**: Include the `signals_detected` array for each item

Return your analysis as a valid JSON object matching the specified format.
"""

    return prompt
````

### Phase 3: Update Data Models for Signals

#### Step 3.1: Add SignalDetected model

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
    type: str  # SignalType value
    detail: str


class CleanupItem(BaseModel):
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str
    full_content: str = ""

    # Model suggestion
    suggested_disposition: str = CleanupDisposition.KEEP
    suggestion_reason: str = ""
    confidence: float = 0.8
    signals_detected: List[DetectedSignal] = Field(default_factory=list)  # NEW

    # User decision
    final_disposition: Optional[str] = None


class CleanupPlan(BaseModel):
    session_id: str
    source_file: str
    created_at: datetime = Field(default_factory=datetime.now)
    overall_notes: str = ""  # NEW: AI summary

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

#### Step 3.2: Update API schemas

**File:** `2.ai-library/src/api/schemas.py`

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
    full_content: str = ""
    suggested_disposition: str
    suggestion_reason: str
    confidence: float = 0.8
    signals_detected: List[DetectedSignalResponse] = []  # NEW
    final_disposition: Optional[str] = None

    @classmethod
    def from_item(cls, item: CleanupItem) -> "CleanupItemResponse":
        return cls(
            block_id=item.block_id,
            heading_path=item.heading_path,
            content_preview=item.content_preview,
            full_content=item.full_content,
            suggested_disposition=item.suggested_disposition,
            suggestion_reason=item.suggestion_reason,
            confidence=item.confidence,
            signals_detected=[
                DetectedSignalResponse(type=s.type, detail=s.detail)
                for s in item.signals_detected
            ],
            final_disposition=item.final_disposition,
        )


class CleanupPlanResponse(BaseModel):
    """Response with cleanup plan."""
    session_id: str
    source_file: str
    created_at: datetime
    overall_notes: str = ""  # NEW
    items: List[CleanupItemResponse]
    all_decided: bool
    approved: bool
    approved_at: Optional[datetime] = None
    pending_count: int
    total_count: int

    @classmethod
    def from_plan(cls, plan: CleanupPlan) -> "CleanupPlanResponse":
        pending_count = sum(
            1 for item in plan.items
            if item.final_disposition is None
        )
        return cls(
            session_id=plan.session_id,
            source_file=plan.source_file,
            created_at=plan.created_at,
            overall_notes=plan.overall_notes,  # NEW
            items=[CleanupItemResponse.from_item(item) for item in plan.items],
            all_decided=plan.all_decided,
            approved=plan.approved,
            approved_at=plan.approved_at,
            pending_count=pending_count,
            total_count=len(plan.items),
        )
```

### Phase 4: Update SDK Client

#### Step 4.1: Parse signals from AI response

**File:** `2.ai-library/src/sdk/client.py`

Update `generate_cleanup_plan()`:

```python
async def generate_cleanup_plan(
    self,
    session_id: str,
    source_file: str,
    blocks: List[Dict[str, Any]],
    content_mode: str = "strict",
    conversation_history: str = "",
    pending_questions: Optional[List[str]] = None,
) -> CleanupPlan:
    """Generate a cleanup plan using Claude Code SDK."""
    user_prompt = build_cleanup_prompt(
        blocks=blocks,
        source_file=source_file,
        content_mode=content_mode,
        conversation_history=conversation_history,
        pending_questions=pending_questions,
    )

    response = await self._query(CLEANUP_SYSTEM_PROMPT, user_prompt)

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
                "Default: keep all content (model omitted this block)"
                if response.success
                else "Default: keep all content"
            )
            confidence = 0.5
            signals_detected = []

        items.append(
            CleanupItem(
                block_id=block_id,
                heading_path=block.get("heading_path", []),
                content_preview=block["content"][:200],
                full_content=block["content"],
                suggested_disposition=suggested_disposition,
                suggestion_reason=suggestion_reason,
                confidence=confidence,
                signals_detected=signals_detected,
            )
        )

    return CleanupPlan(
        session_id=session_id,
        source_file=source_file,
        overall_notes=overall_notes,
        items=items,
    )
```

### Phase 5: Frontend Signal Display (Optional Enhancement)

#### Step 5.1: Update TypeScript types

**File:** `libs/types/src/knowledge-library.ts`

```typescript
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
  full_content: string;
  suggested_disposition: KLCleanupDisposition;
  suggestion_reason: string;
  confidence: number;
  signals_detected: KLDetectedSignal[]; // NEW
  final_disposition: KLCleanupDisposition | null;
}

/** Cleanup plan response */
export interface KLCleanupPlanResponse {
  session_id: string;
  source_file: string;
  created_at: string;
  overall_notes: string; // NEW
  items: KLCleanupItemResponse[];
  all_decided: boolean;
  approved: boolean;
  approved_at: string | null;
  pending_count: number;
  total_count: number;
}
```

#### Step 5.2: Create SignalBadges component

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/signal-badges.tsx`

```tsx
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
  { icon: React.ElementType; label: string; variant: 'default' | 'destructive' | 'secondary' }
> = {
  // Discard signals
  time_sensitive: { icon: Clock, label: 'Time-sensitive', variant: 'destructive' },
  completed_items: { icon: CheckSquare, label: 'Completed', variant: 'destructive' },
  ephemeral_link: { icon: Link2, label: 'Ephemeral link', variant: 'destructive' },
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

#### Step 5.3: Update AIRecommendationBox to show signals

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/ai-recommendation-box.tsx`

Add signals display:

```tsx
import { SignalBadges } from './signal-badges';
import type { KLDetectedSignal } from '@automaker/types';

interface AIRecommendationBoxProps {
  disposition: KLCleanupDisposition;
  reason: string;
  confidence: number;
  signals?: KLDetectedSignal[]; // NEW
}

export function AIRecommendationBox({
  disposition,
  reason,
  confidence,
  signals = [],
}: AIRecommendationBoxProps) {
  // ... existing code ...

  return (
    <div className={cn(/* ... */)}>
      {/* ... existing header and recommendation ... */}

      {/* Show detected signals */}
      {signals.length > 0 && (
        <div className="mt-2 pt-2 border-t border-current/10">
          <p className="text-xs text-muted-foreground mb-1">Signals detected:</p>
          <SignalBadges signals={signals} />
        </div>
      )}
    </div>
  );
}
```

## Files to Modify

| File                                           | Changes                                                   |
| ---------------------------------------------- | --------------------------------------------------------- |
| `2.ai-library/src/sdk/prompts/cleanup_mode.py` | Complete rewrite of system prompt and user prompt builder |
| `2.ai-library/src/models/cleanup_plan.py`      | Add SignalType, DetectedSignal, overall_notes             |
| `2.ai-library/src/api/schemas.py`              | Add DetectedSignalResponse, update CleanupItemResponse    |
| `2.ai-library/src/sdk/client.py`               | Parse signals from AI response                            |
| `libs/types/src/knowledge-library.ts`          | Add KLDetectedSignal type, update interfaces              |

## Files to Create

| File                                                                                                | Purpose                  |
| --------------------------------------------------------------------------------------------------- | ------------------------ |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/signal-badges.tsx` | Visual signal indicators |

## Testing Checklist

### Prompt Quality Tests

- [ ] Upload document with time-sensitive meeting notes → AI suggests discard
- [ ] Upload document with completed todo list → AI suggests discard
- [ ] Upload document with technical reference → AI suggests keep
- [ ] Upload document with placeholder content → AI suggests discard
- [ ] Upload document with original analysis → AI suggests keep
- [ ] Verify mixed documents get balanced recommendations (not all keep)

### Signal Detection Tests

- [ ] Zoom/Teams links detected as ephemeral_link
- [ ] `[x]` checkboxes detected as completed_items
- [ ] Dates in past detected as time_sensitive
- [ ] "TODO", "TBD" detected as structural_noise
- [ ] Code snippets with examples detected as reference_value

### Backend Integration Tests

- [ ] AI response with signals_detected parses correctly
- [ ] Overall notes included in response
- [ ] Confidence scores vary appropriately (not all 0.8)
- [ ] Omitted blocks get low confidence (0.5)

### Frontend Display Tests

- [ ] Signal badges render with correct icons
- [ ] Signal badges have correct colors (red for discard, green for keep)
- [ ] Hovering signal badge shows detail tooltip
- [ ] Overall notes displayed in plan header

## Example Test Documents

### Document 1: Should have mixed recommendations

````markdown
# Project Notes

## Meeting Notes - Jan 15, 2024

- Discussed API changes with team
- Action items:
  - [x] Update schema
  - [x] Review PR #45
  - [ ] Deploy to staging
- Meeting link: https://zoom.us/j/123456789

## API Best Practices

REST endpoints should follow these patterns:

- Use nouns for resources
- HTTP verbs for actions
- Version in URL path

```python
# Example endpoint
GET /api/v1/users/{id}
POST /api/v1/users
```
````

## Scratch Notes

TODO: figure out deployment
TBD: database migration strategy

```

**Expected AI response:**
- Meeting Notes → DISCARD (time_sensitive, completed_items, ephemeral_link)
- API Best Practices → KEEP (reference_value, original_work)
- Scratch Notes → DISCARD (structural_noise)

## Acceptance Criteria

- [ ] AI suggests discard for at least 20-30% of typical mixed documents (vs current ~5%)
- [ ] Discard suggestions include specific signals detected
- [ ] Keep suggestions cite positive signals (not just "default")
- [ ] Confidence scores correlate with signal strength
- [ ] Overall notes provide useful document summary
- [ ] No regression: valuable content still suggested to keep

## Dependencies

- **Plan 003** (UI Improvements) should be implemented first
  - The UI needs to display confidence and signals
  - Without UI changes, improved AI output won't be visible to users

## Estimated Effort

- Prompt engineering: ~2 hours
- Backend model updates: ~2 hours
- SDK client updates: ~1 hour
- Frontend signal display: ~2 hours
- Testing with various documents: ~2 hours
- **Total: ~9 hours**

## Follow-up Work

### Phase 2: Source Detection (Future)

Add logic to detect external sources in content:
- URL extraction from markdown links
- Citation pattern detection
- Quote detection without attribution
- This would enhance the "source_only" signal accuracy

### Phase 3: Learning from User Decisions (Future)

Track patterns in user keep/discard decisions to improve future suggestions:
- If users frequently keep content AI suggested to discard, adjust criteria
- Build per-user preference profiles
- This requires Plan 002 (Multi-User Authentication) first
```
