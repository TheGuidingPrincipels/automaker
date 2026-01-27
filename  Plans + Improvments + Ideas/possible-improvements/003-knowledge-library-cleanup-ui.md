# Knowledge Library Cleanup UI Improvements

**Status:** Ready for Implementation
**Priority:** High
**Impact:** Users can see exactly what content will be removed, make informed decisions
**Date Added:** 2026-01-26
**Related Upstream:** Not applicable (AI Library feature)

## Summary

Improve the cleanup review UI in the Knowledge Library to show full block content (expandable), AI confidence percentages, color-coded recommendations, and clearer block boundaries (block type + source line range). Preserve the existing “change my mind” workflow so users can safely revise decisions after initially choosing Keep/Discard. Currently, users see truncated 2-line previews and cannot easily understand what content they're deciding on.

## Design Decisions (to keep this safe + scalable)

1. **Do not embed full block content in the cleanup plan payload.** Instead, fetch full content and boundary metadata from the existing Blocks endpoint (`GET /api/sessions/{session_id}/blocks`) and join by `block_id`. This avoids duplicating large text in session storage and avoids inflating WebSocket streaming payloads.
2. **Confidence is an end-to-end contract.** The cleanup prompt already requests `confidence`, but the backend currently drops it. This plan adds confidence to models/schemas/types and clamps values to `[0.0, 1.0]`.
3. **No workflow regressions.** Keep the current tabbed review experience and the ability to switch decisions in “All” and move items between Keep/Discard tabs.

## Problem Statement

### Current Issues

1. **Content visibility**: Only ~2 lines shown (`line-clamp-2`), users can't see full block
2. **No confidence indicator**: Cleanup prompt requests `confidence`, but backend/SDK drops it so UI cannot display it
3. **AI suggestion not prominent**: Shown as small italic text at bottom
4. **No pre-decision color coding**: Colors only appear after user decides
5. **Recommended action unclear**: Both Keep/Discard buttons have equal visual weight
6. **Block boundaries unclear**: UI doesn’t show block type or source line range, so users can’t tell what the system considers “this block”

### User Impact

- Users must guess what content they're keeping/discarding
- No visual guidance toward AI recommendation
- Decision fatigue from lack of information hierarchy
- Risk of accidentally discarding important content

## Solution Design

### Visual Mockups

#### Enhanced Cleanup Item Card - KEEP Recommendation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📁 Research > API Design > REST Principles                    [Expand ▼]  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ## REST API Best Practices                                          │   │
│  │                                                                      │   │
│  │ REST APIs should follow these core principles:                      │   │
│  │                                                                      │   │
│  │ 1. **Statelessness** - Each request contains all information        │   │
│  │    needed to process it                                             │   │
│  │ 2. **Resource-Based URLs** - Use nouns, not verbs                   │   │
│  │ 3. **HTTP Methods** - GET for reads, POST for creates...            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  🤖 AI Recommendation                              ████████░░  87%   │  │
│  │  ───────────────────────────────────────────────────────────────────  │  │
│  │  ✅ KEEP — Contains valuable technical reference material with       │  │
│  │     concrete examples. This is reusable knowledge worth preserving.  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                       [green background]    │
│                                                                             │
│        ┌─────────────────┐    ┌─────────────────┐                          │
│        │  ✓ Keep         │    │  ✗ Discard      │                          │
│        │  (Recommended)  │    │                 │                          │
│        └─────────────────┘    └─────────────────┘                          │
│         [green, prominent]     [gray, subtle]                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Enhanced Cleanup Item Card - DISCARD Recommendation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📁 Notes > Daily                                              [Expand ▼]  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                [orange/red border]     │ │
│  │ ## TODO for Monday meeting                                             │ │
│  │                                                                        │ │
│  │ - [ ] Review PR #234                                                  │ │
│  │ - [x] Send email to John about deadline                               │ │
│  │ - [x] Update Jira ticket                                              │ │
│  │                                                                        │ │
│  │ Meeting link: https://zoom.us/j/123456789                             │ │
│  │ Time: Monday 9am PST                                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  🤖 AI Recommendation                              ███████░░░  72%   │  │
│  │  ───────────────────────────────────────────────────────────────────  │  │
│  │  🗑️ DISCARD — Time-sensitive task list with completed items.         │  │
│  │                                                                       │  │
│  │  Signals detected:                                                    │  │
│  │  • ⏰ Time-specific content (Monday 9am)                              │  │
│  │  • ✓ Completed checkboxes (2/3 done)                                  │  │
│  │  • 🔗 Ephemeral link (Zoom meeting)                                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                        [red background]     │
│                                                                             │
│        ┌─────────────────┐    ┌─────────────────┐                          │
│        │  ✓ Keep         │    │  ✗ Discard      │                          │
│        │                 │    │  (Recommended)  │                          │
│        └─────────────────┘    └─────────────────┘                          │
│         [gray, subtle]         [red, prominent]                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Model Changes

### Backend: Add `confidence` field (no `full_content` on cleanup items)

**File:** `2.ai-library/src/models/cleanup_plan.py`

```python
class CleanupItem(BaseModel):
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str

    # Model suggestion (never executed automatically)
    suggested_disposition: str = CleanupDisposition.KEEP
    suggestion_reason: str = ""
    confidence: float = 0.5  # NEW: AI confidence score (0.0-1.0), clamped

    # User decision
    final_disposition: Optional[str] = None
```

**File:** `2.ai-library/src/api/schemas.py`

```python
class CleanupItemResponse(BaseModel):
    block_id: str
    heading_path: List[str]
    content_preview: str
    suggested_disposition: str
    suggestion_reason: str
    confidence: float  # NEW (0.0-1.0)
    final_disposition: Optional[str] = None
```

### Frontend: TypeScript Types

**File:** `libs/types/src/knowledge-library.ts`

```typescript
export interface KLCleanupItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  suggested_disposition: KLCleanupDisposition;
  suggestion_reason: string;
  confidence: number; // NEW: 0.0 to 1.0 (clamped)
  final_disposition: KLCleanupDisposition | null;
}
```

### UI data source for “full content” + block boundaries (no new backend fields needed)

- Use `GET /api/sessions/{session_id}/blocks` (already implemented) to obtain, per block:
  - `content` (full text)
  - `block_type`
  - `source_line_start` / `source_line_end`
- Join this data to cleanup items by `block_id` in the UI.

## Implementation Plan

### Phase 1: Backend confidence propagation (keep payloads small)

#### Step 1.1: Update CleanupItem model

**File:** `2.ai-library/src/models/cleanup_plan.py`

Add a `confidence` field (default 0.5) and validate/clamp to `[0.0, 1.0]`:

```python
class CleanupItem(BaseModel):
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str

    # Model suggestion
    suggested_disposition: str = CleanupDisposition.KEEP
    suggestion_reason: str = ""
    confidence: float = 0.5  # Default confidence (clamped to 0.0-1.0)

    # User decision
    final_disposition: Optional[str] = None
```

#### Step 1.2: Update API schema

**File:** `2.ai-library/src/api/schemas.py`

Update `CleanupItemResponse`:

```python
class CleanupItemResponse(BaseModel):
    """Response for a cleanup item."""
    block_id: str
    heading_path: List[str]
    content_preview: str
    suggested_disposition: str
    suggestion_reason: str
    confidence: float = 0.5  # NEW
    final_disposition: Optional[str] = None

    @classmethod
    def from_item(cls, item: CleanupItem) -> "CleanupItemResponse":
        return cls(
            block_id=item.block_id,
            heading_path=item.heading_path,
            content_preview=item.content_preview,
            suggested_disposition=item.suggested_disposition,
            suggestion_reason=item.suggestion_reason,
            confidence=item.confidence,  # NEW
            final_disposition=item.final_disposition,
        )
```

#### Step 1.3: Update SDK client to capture confidence

**File:** `2.ai-library/src/sdk/client.py`

In `generate_cleanup_plan()`, extract confidence from AI response:

```python
if item_data:
    suggested_disposition = item_data.get(
        "suggested_disposition", CleanupDisposition.KEEP
    )
    suggestion_reason = item_data.get("suggestion_reason", "")
    confidence = item_data.get("confidence", 0.5)  # NEW
else:
    suggested_disposition = CleanupDisposition.KEEP
    suggestion_reason = "Default: keep all content (model omitted this block)"
    confidence = 0.5  # Low confidence for omitted blocks

items.append(
    CleanupItem(
        block_id=block_id,
        heading_path=block.get("heading_path", []),
        content_preview=block["content"][:200],
        suggested_disposition=suggested_disposition,
        suggestion_reason=suggestion_reason,
        confidence=confidence,  # NEW
    )
)
```

**Normalization rules (avoid silent fallbacks):**

- Coerce `confidence` to a float, clamp to `[0.0, 1.0]`.
- If `confidence` is missing or invalid (NaN/string/out of range), default to `0.5` and emit a debug log entry (so prompt/LLM issues are visible during tuning).

### Phase 2: Frontend Type Updates

#### Step 2.1: Update TypeScript interface

**File:** `libs/types/src/knowledge-library.ts`

```typescript
/** Single cleanup item */
export interface KLCleanupItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  suggested_disposition: KLCleanupDisposition;
  suggestion_reason: string;
  confidence: number; // NEW: AI confidence (0.0 to 1.0)
  final_disposition: KLCleanupDisposition | null;
}
```

### Phase 3: UI Enhancements (full content via Blocks API + better hierarchy)

#### Step 3.0: Fetch full block content + metadata for cleanup review

**Files to modify:**

- `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx` (add `sessionId` prop, fetch blocks, build lookup map)
- `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx` (pass `sessionId` into `CleanupReview`)

**Implementation notes:**

- Use the existing hook `useKLBlocks(sessionId)` (already available in `apps/ui/src/hooks/queries/use-knowledge-library.ts`).
- Build a lookup map keyed by `block.id` and join by `item.block_id`:
  - `block.content` → full text for expansion
  - `block.block_type`, `source_line_start`, `source_line_end` → boundary clarity

#### Step 3.1: Create ConfidenceBar component

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/confidence-bar.tsx`

```tsx
import { cn } from '@/lib/utils';

interface ConfidenceBarProps {
  confidence: number; // 0.0 to 1.0
  disposition: 'keep' | 'discard';
}

export function ConfidenceBar({ confidence, disposition }: ConfidenceBarProps) {
  const safe = Number.isFinite(confidence) ? Math.min(1, Math.max(0, confidence)) : 0;
  const percentage = Math.round(safe * 100);
  const isKeep = disposition === 'keep';

  const barColor = isKeep ? 'bg-green-500' : 'bg-red-500';

  const trackColor = isKeep ? 'bg-green-100' : 'bg-red-100';

  return (
    <div className="flex items-center gap-2">
      <div className={cn('h-2 w-24 rounded-full', trackColor)}>
        <div
          className={cn('h-2 rounded-full transition-all', barColor)}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={cn('text-sm font-medium', isKeep ? 'text-green-700' : 'text-red-700')}>
        {percentage}%
      </span>
    </div>
  );
}
```

#### Step 3.2: Create AIRecommendationBox component

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/ai-recommendation-box.tsx`

```tsx
import { cn } from '@/lib/utils';
import { ConfidenceBar } from './confidence-bar';
import { Bot, Check, Trash2 } from 'lucide-react';
import type { KLCleanupDisposition } from '@automaker/types';

interface AIRecommendationBoxProps {
  disposition: KLCleanupDisposition;
  reason: string;
  confidence: number;
}

export function AIRecommendationBox({ disposition, reason, confidence }: AIRecommendationBoxProps) {
  const isKeep = disposition === 'keep';

  return (
    <div
      className={cn(
        'rounded-lg p-3 mt-3',
        isKeep ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-muted-foreground">AI Recommendation</span>
        </div>
        <ConfidenceBar confidence={confidence} disposition={disposition} />
      </div>

      <div className="flex items-start gap-2">
        {isKeep ? (
          <Check className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
        ) : (
          <Trash2 className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
        )}
        <div>
          <span className={cn('font-semibold', isKeep ? 'text-green-700' : 'text-red-700')}>
            {isKeep ? 'KEEP' : 'DISCARD'}
          </span>
          <span className="text-sm text-muted-foreground ml-1">— {reason}</span>
        </div>
      </div>
    </div>
  );
}
```

#### Step 3.3: Create ContentPreviewBox component

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/content-preview-box.tsx`

```tsx
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { KLCleanupDisposition } from '@automaker/types';

interface ContentPreviewBoxProps {
  content: string;
  fullContent: string;
  suggestedDisposition: KLCleanupDisposition;
}

export function ContentPreviewBox({
  content,
  fullContent,
  suggestedDisposition,
}: ContentPreviewBoxProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isDiscard = suggestedDisposition === 'discard';
  const hasMoreContent = fullContent.length > content.length;

  const displayContent = isExpanded ? fullContent : content;

  return (
    <div className="relative">
      <div
        className={cn(
          'rounded-md border p-3 font-mono text-sm whitespace-pre-wrap',
          'bg-muted/30',
          isDiscard && 'border-red-200 bg-red-50/30'
        )}
      >
        {displayContent}
        {!isExpanded && hasMoreContent && <span className="text-muted-foreground">...</span>}
      </div>

      {hasMoreContent && (
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-1 right-1 h-6 text-xs"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-3 w-3 mr-1" />
              Collapse
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3 mr-1" />
              Expand
            </>
          )}
        </Button>
      )}
    </div>
  );
}
```

#### Step 3.4: Update CleanupItemCard component

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx`

Enhance the existing `CleanupItemCard` and preserve current behaviors:

- Keep tabbed views (`all/pending/keep/discard`)
- Keep “Switch to …” for decided items in All
- Keep “Move to Keep/Discard” in Keep/Discard tabs
- Add pre-decision accent based on `suggested_disposition`
- Add “Recommended” styling without hiding the alternative action
- Add block boundary metadata (type + line range) from the Blocks API

**Implementation notes (minimal diffs; keep the existing tab logic):**

- Add `sessionId: string` to `CleanupReviewProps` and pass it from `PlanReview`.
- Fetch blocks via `useKLBlocks(sessionId)` and build `blockById` (`Map<string, KLBlockResponse>`).
- Pass the matched `block` into `CleanupItemCard` (e.g., `block={blockById.get(item.block_id)}`).
- Derive full content + boundary label from the block:

```tsx
const fullContent = block?.content ?? item.content_preview;
const boundaryLabel = block
  ? `${block.block_type} • L${block.source_line_start}-L${block.source_line_end}`
  : '—';
```

- Use `ContentPreviewBox` with `fullContent={fullContent}`.
- Use `AIRecommendationBox` with `confidence={item.confidence ?? 0.5}`.
- Keep the existing `renderButtons()` logic for Pending/Keep/Discard/All (no regression).

### Phase 4: Non-AI Mode Fallback

#### Step 4.1: Update session manager default confidence

**File:** `2.ai-library/src/session/manager.py`

In `generate_cleanup_plan()` (non-AI mode), set lower default confidence:

```python
items.append(
    CleanupItem(
        block_id=block_id,
        heading_path=block.heading_path,
        content_preview=block.content[:200],
        suggested_disposition=CleanupDisposition.KEEP,
        suggestion_reason="Default: keep all content",
        confidence=0.5,  # Lower confidence for non-AI default
        final_disposition=None,
    )
)
```

## Files to Create

| File                                                                                                        | Purpose                             |
| ----------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/confidence-bar.tsx`        | Confidence percentage visualization |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/ai-recommendation-box.tsx` | AI suggestion display with colors   |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/content-preview-box.tsx`   | Expandable content display          |

## Files to Modify

| File                                                                                                 | Changes                                     |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| `2.ai-library/src/models/cleanup_plan.py`                                                            | Add `confidence` field (validated/clamped)  |
| `2.ai-library/src/api/schemas.py`                                                                    | Add `confidence` to cleanup item response   |
| `2.ai-library/src/sdk/client.py`                                                                     | Extract + clamp confidence from AI response |
| `2.ai-library/src/session/manager.py`                                                                | Set default confidence for non-AI mode      |
| `libs/types/src/knowledge-library.ts`                                                                | Add `confidence` to cleanup item type       |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx` | UI enhancements (no workflow regressions)   |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx`               | Pass `sessionId` into `CleanupReview`       |

## Testing Checklist

### Backend Tests

- [ ] CleanupItem model accepts confidence field
- [ ] CleanupItemResponse includes confidence in JSON
- [ ] SDK client extracts confidence from AI response
- [ ] Confidence is clamped to `[0.0, 1.0]` for invalid/out-of-range model output
- [ ] Omitted blocks get 0.5 confidence (and a clear “omitted” reason)

### Frontend Tests (Playwright-first; component unit tests optional)

- [ ] Cleanup review renders without truncation (expand shows full content)
- [ ] Confidence is displayed and never overflows/underflows (clamped)
- [ ] AI recommendation has clear icon + color + “Recommended” label
- [ ] Users can revise decisions after initial selection (All + Keep/Discard tabs)
- [ ] Block boundary metadata (type + line range) is visible for clarity

### E2E Tests

- [ ] Upload document and verify cleanup cards display
- [ ] Expand content preview and verify full content shows
- [ ] Click Keep/Discard and verify state updates
- [ ] Verify confidence bar matches AI response
- [ ] Switch decisions after deciding (ensure no workflow regression)

## Acceptance Criteria

- [ ] Users can see full block content (expandable)
- [ ] Confidence percentage displayed as visual bar + number
- [ ] AI recommendation has colored background (green=keep, red=discard)
- [ ] Recommended action button is visually prominent
- [ ] Block boundaries clear with block type + line range visible
- [ ] Cards for discard recommendations have red/orange accent
- [ ] Users can change decisions after initially deciding (safety)

## Dependencies

- None new (uses existing Blocks API endpoint for full content + boundary metadata)

## Estimated Effort

- Backend changes: ~1.5–2 hours
- UI enhancements: ~3–4 hours
- Integration & Playwright E2E: ~1.5–2 hours
- **Total: ~6–8 hours**

## Follow-up Work

After this plan is complete, implement **Plan 004: AI Decision Criteria Improvements** to enhance the quality of AI recommendations shown in this improved UI.
