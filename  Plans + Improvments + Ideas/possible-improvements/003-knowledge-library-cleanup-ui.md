# Knowledge Library Cleanup UI Improvements

**Status:** Ready for Implementation
**Priority:** High
**Impact:** Users can see exactly what content will be removed, make informed decisions
**Date Added:** 2026-01-26
**Related Upstream:** Not applicable (AI Library feature)

## Summary

Improve the cleanup review UI in the Knowledge Library to show full block content, AI confidence percentages, color-coded recommendations, and clearer visual distinction between keep/discard suggestions. Currently, users see truncated 2-line previews and cannot easily understand what content they're deciding on.

## Problem Statement

### Current Issues

1. **Content visibility**: Only ~2 lines shown (`line-clamp-2`), users can't see full block
2. **No confidence indicator**: Backend returns confidence scores but UI ignores them
3. **AI suggestion not prominent**: Shown as small italic text at bottom
4. **No pre-decision color coding**: Colors only appear after user decides
5. **Recommended action unclear**: Both Keep/Discard buttons have equal visual weight
6. **Block boundaries unclear**: Users can't understand what exactly constitutes "this block"

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

### Backend: Add `confidence` field

**File:** `2.ai-library/src/models/cleanup_plan.py`

```python
class CleanupItem(BaseModel):
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str
    full_content: str = ""  # NEW: Full block content for display

    # Model suggestion (never executed automatically)
    suggested_disposition: str = CleanupDisposition.KEEP
    suggestion_reason: str = ""
    confidence: float = 0.8  # NEW: AI confidence score (0.0-1.0)

    # User decision
    final_disposition: Optional[str] = None
```

**File:** `2.ai-library/src/api/schemas.py`

```python
class CleanupItemResponse(BaseModel):
    block_id: str
    heading_path: List[str]
    content_preview: str
    full_content: str  # NEW
    suggested_disposition: str
    suggestion_reason: str
    confidence: float  # NEW
    final_disposition: Optional[str] = None
```

### Frontend: TypeScript Types

**File:** `libs/types/src/knowledge-library.ts`

```typescript
export interface KLCleanupItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  full_content: string; // NEW
  suggested_disposition: KLCleanupDisposition;
  suggestion_reason: string;
  confidence: number; // NEW: 0.0 to 1.0
  final_disposition: KLCleanupDisposition | null;
}
```

## Implementation Plan

### Phase 1: Backend Data Enhancement

#### Step 1.1: Update CleanupItem model

**File:** `2.ai-library/src/models/cleanup_plan.py`

Add `confidence` and `full_content` fields:

```python
class CleanupItem(BaseModel):
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str
    full_content: str = ""  # Full content for UI display

    # Model suggestion
    suggested_disposition: str = CleanupDisposition.KEEP
    suggestion_reason: str = ""
    confidence: float = 0.8  # Default confidence

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
    full_content: str = ""  # NEW
    suggested_disposition: str
    suggestion_reason: str
    confidence: float = 0.8  # NEW
    final_disposition: Optional[str] = None

    @classmethod
    def from_item(cls, item: CleanupItem) -> "CleanupItemResponse":
        return cls(
            block_id=item.block_id,
            heading_path=item.heading_path,
            content_preview=item.content_preview,
            full_content=item.full_content,  # NEW
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
    confidence = item_data.get("confidence", 0.8)  # NEW
else:
    suggested_disposition = CleanupDisposition.KEEP
    suggestion_reason = "Default: keep all content (model omitted this block)"
    confidence = 0.5  # Low confidence for omitted blocks

items.append(
    CleanupItem(
        block_id=block_id,
        heading_path=block.get("heading_path", []),
        content_preview=block["content"][:200],
        full_content=block["content"],  # NEW: Full content
        suggested_disposition=suggested_disposition,
        suggestion_reason=suggestion_reason,
        confidence=confidence,  # NEW
    )
)
```

### Phase 2: Frontend Type Updates

#### Step 2.1: Update TypeScript interface

**File:** `libs/types/src/knowledge-library.ts`

```typescript
/** Single cleanup item */
export interface KLCleanupItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  full_content: string; // NEW: Full block content
  suggested_disposition: KLCleanupDisposition;
  suggestion_reason: string;
  confidence: number; // NEW: AI confidence (0.0 to 1.0)
  final_disposition: KLCleanupDisposition | null;
}
```

### Phase 3: UI Component Enhancements

#### Step 3.1: Create ConfidenceBar component

**File:** `apps/ui/src/components/views/knowledge-library/components/input-mode/components/confidence-bar.tsx`

```tsx
import { cn } from '@/lib/utils';

interface ConfidenceBarProps {
  confidence: number; // 0.0 to 1.0
  disposition: 'keep' | 'discard';
}

export function ConfidenceBar({ confidence, disposition }: ConfidenceBarProps) {
  const percentage = Math.round(confidence * 100);
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

Replace the existing `CleanupItemCard` function:

```tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SkeletonPulse } from '@/components/ui/skeleton';
import { CheckCircle2, Trash2, Loader2, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AIRecommendationBox } from './ai-recommendation-box';
import { ContentPreviewBox } from './content-preview-box';
import type { useKLCleanupPlan } from '@/hooks/queries/use-knowledge-library';

interface CleanupItemCardProps {
  item: NonNullable<ReturnType<typeof useKLCleanupPlan>['data']>['items'][number];
  isDeciding: boolean;
  onDecide: (blockId: string, disposition: 'keep' | 'discard') => void;
}

function CleanupItemCard({ item, isDeciding, onDecide }: CleanupItemCardProps) {
  const isDecided = item.final_disposition !== null;
  const isKeep = item.final_disposition === 'keep';
  const isRecommendKeep = item.suggested_disposition === 'keep';

  return (
    <Card
      className={cn(
        'transition-all',
        isDecided && 'opacity-60',
        !isDecided && !isRecommendKeep && 'border-red-200'
      )}
    >
      <CardContent className="pt-4">
        {/* Header with path and status */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
            <Badge variant="outline" className="text-xs font-normal">
              {item.heading_path.join(' > ') || 'Document Root'}
            </Badge>
          </div>
          {isDecided && (
            <Badge variant={isKeep ? 'default' : 'destructive'} className="text-xs">
              {item.final_disposition === 'keep' ? '✓ Keeping' : '✗ Discarding'}
            </Badge>
          )}
        </div>

        {/* Content preview box */}
        <ContentPreviewBox
          content={item.content_preview}
          fullContent={item.full_content || item.content_preview}
          suggestedDisposition={item.suggested_disposition}
        />

        {/* AI Recommendation */}
        <AIRecommendationBox
          disposition={item.suggested_disposition}
          reason={item.suggestion_reason}
          confidence={item.confidence ?? 0.8}
        />

        {/* Action buttons */}
        {!isDecided && (
          <div className="flex gap-2 mt-4">
            <Button
              variant={isRecommendKeep ? 'default' : 'outline'}
              size="sm"
              className={cn(
                'flex-1',
                isRecommendKeep
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'text-green-600 hover:bg-green-50'
              )}
              onClick={() => onDecide(item.block_id, 'keep')}
              disabled={isDeciding}
            >
              <CheckCircle2 className="h-4 w-4 mr-1" />
              Keep{isRecommendKeep && ' (Recommended)'}
            </Button>
            <Button
              variant={!isRecommendKeep ? 'default' : 'outline'}
              size="sm"
              className={cn(
                'flex-1',
                !isRecommendKeep
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'text-red-600 hover:bg-red-50'
              )}
              onClick={() => onDecide(item.block_id, 'discard')}
              disabled={isDeciding}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Discard{!isRecommendKeep && ' (Recommended)'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ... rest of CleanupReview component remains the same
```

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
        full_content=block.content,  # NEW
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

| File                                                                                                 | Changes                                                |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `2.ai-library/src/models/cleanup_plan.py`                                                            | Add `confidence` and `full_content` fields             |
| `2.ai-library/src/api/schemas.py`                                                                    | Add fields to response schema                          |
| `2.ai-library/src/sdk/client.py`                                                                     | Extract confidence from AI response, pass full content |
| `2.ai-library/src/session/manager.py`                                                                | Set default confidence for non-AI mode                 |
| `libs/types/src/knowledge-library.ts`                                                                | Add TypeScript types                                   |
| `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx` | Complete UI overhaul                                   |

## Testing Checklist

### Backend Tests

- [ ] CleanupItem model accepts confidence field
- [ ] CleanupItemResponse includes confidence in JSON
- [ ] SDK client extracts confidence from AI response
- [ ] Omitted blocks get 0.5 confidence
- [ ] Full content is passed through pipeline

### Frontend Tests

- [ ] ConfidenceBar renders correct percentage
- [ ] ConfidenceBar uses green for keep, red for discard
- [ ] AIRecommendationBox shows correct icon and colors
- [ ] ContentPreviewBox expands/collapses properly
- [ ] CleanupItemCard shows recommended button prominently
- [ ] Decided items show correct status badge

### E2E Tests

- [ ] Upload document and verify cleanup cards display
- [ ] Expand content preview and verify full content shows
- [ ] Click Keep/Discard and verify state updates
- [ ] Verify confidence bar matches AI response

## Acceptance Criteria

- [ ] Users can see full block content (expandable)
- [ ] Confidence percentage displayed as visual bar + number
- [ ] AI recommendation has colored background (green=keep, red=discard)
- [ ] Recommended action button is visually prominent
- [ ] Block boundaries clear with content in bordered box
- [ ] Cards for discard recommendations have red/orange accent

## Dependencies

- None (this plan can be implemented independently)

## Estimated Effort

- Backend changes: ~2 hours
- New UI components: ~3 hours
- Integration & testing: ~2 hours
- **Total: ~7 hours**

## Follow-up Work

After this plan is complete, implement **Plan 004: AI Decision Criteria Improvements** to enhance the quality of AI recommendations shown in this improved UI.
