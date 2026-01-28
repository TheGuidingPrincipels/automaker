# Session Cleanup Workflow

Detailed guide for the Knowledge Library session cleanup workflow.

## Overview

The session cleanup workflow transforms unstructured markdown documents into organized knowledge library entries through a multi-phase approval process.

## Workflow Phases

```
1. Upload     → Parse markdown into blocks
2. Cleanup    → AI suggests keep/discard per block
3. Review     → User approves/adjusts decisions
4. Routing    → AI suggests destinations per block
5. Select     → User selects/customizes destinations
6. Execute    → Write blocks to library with checksums
```

## State Machine

### States

| State                | Description                       |
| -------------------- | --------------------------------- |
| `idle`               | No session, waiting for file      |
| `file_staged`        | File selected, ready to start     |
| `creating_session`   | Creating session + uploading      |
| `cleanup_generating` | AI generating cleanup suggestions |
| `cleanup_review`     | User reviewing keep/discard       |
| `routing_generating` | AI generating routing options     |
| `routing_review`     | User selecting destinations       |
| `ready_to_execute`   | All decisions made                |
| `executing`          | Writing to library                |
| `completed`          | Success                           |
| `error`              | Failure                           |

### Transitions

```
idle
  │ stageFile(file)
  ▼
file_staged
  │ startSession()
  │   ├─ POST /sessions (create)
  │   ├─ POST /sessions/{id}/upload
  │   ├─ Connect WebSocket
  │   └─ Send 'generate_cleanup' command
  ▼
creating_session
  │ 'cleanup_started' WebSocket event
  ▼
cleanup_generating
  │ 'cleanup_ready' WebSocket event
  ▼
cleanup_review
  │ approveCleanup()
  │   ├─ POST /sessions/{id}/cleanup/approve
  │   └─ Send 'generate_routing' command
  ▼
routing_generating
  │ 'routing_ready' WebSocket event
  ▼
routing_review
  │ approveRouting()
  │   └─ POST /sessions/{id}/plan/approve
  ▼
ready_to_execute
  │ execute()
  │   └─ POST /sessions/{id}/execute
  ▼
executing
  │ Response received
  ├───────────────┬────────────────┐
  ▼               ▼                │
completed      error              │
                  │                │
                  └── User fixes ──┘
```

## Cleanup Phase Details

### What Happens

1. Backend parses markdown into blocks (headings, paragraphs, code, etc.)
2. AI analyzes each block for relevance
3. Returns suggestions with confidence scores
4. Identifies duplicate/similar blocks

### Cleanup Item Structure

```typescript
CleanupItem {
  block_id: string
  heading_path: string[]       // Breadcrumb path
  content_preview: string      // First ~200 chars
  suggested_disposition: "keep" | "discard"
  suggestion_reason: string    // AI explanation
  confidence: number           // 0.0-1.0
  final_disposition: "keep" | "discard" | null  // User decision
  ai_analyzed: boolean
  similar_block_ids: string[]  // Duplicates
  similarity_score: number
}
```

### User Actions

| Action        | API Call                          | Effect                      |
| ------------- | --------------------------------- | --------------------------- |
| Keep block    | `POST /cleanup/decide/{block_id}` | Set disposition="keep"      |
| Discard block | `POST /cleanup/decide/{block_id}` | Set disposition="discard"   |
| Approve plan  | `POST /cleanup/approve`           | Transition to routing phase |

### Confidence Thresholds

| Confidence | Meaning                           |
| ---------- | --------------------------------- |
| 0.9-1.0    | Very confident, likely correct    |
| 0.7-0.9    | Confident, may need review        |
| 0.5-0.7    | Uncertain, needs user decision    |
| <0.5       | Low confidence, definitely review |

## Routing Phase Details

### What Happens

1. For each kept block, AI suggests 3 destination options
2. Each option includes: file, section, action, confidence
3. User selects preferred option or provides custom destination

### Routing Item Structure

```typescript
BlockRoutingItem {
  block_id: string
  heading_path: string[]
  content_preview: string
  options: DestinationOption[]  // 3 options
  selected_option_index: number | null
  custom_destination_file: string | null
  custom_destination_section: string | null
  custom_action: string | null
  status: "pending" | "selected" | "rejected"
}

DestinationOption {
  destination_file: string
  destination_section: string
  action: "create_file" | "create_section" | "append" | "insert_before" | "insert_after" | "merge"
  confidence: number
  reasoning: string
  proposed_file_title: string | null
  proposed_file_overview: string | null
}
```

### User Actions

| Action             | API Call                       | Effect                    |
| ------------------ | ------------------------------ | ------------------------- |
| Select option      | `POST /plan/select/{block_id}` | Set selected_option_index |
| Custom destination | `POST /plan/select/{block_id}` | Set custom*destination*\* |
| Reject block       | `POST /plan/select/{block_id}` | Set status="rejected"     |
| Approve plan       | `POST /plan/approve`           | Transition to execute     |

### Actions Explained

| Action           | When Used                             |
| ---------------- | ------------------------------------- |
| `create_file`    | Destination file doesn't exist        |
| `create_section` | File exists but section doesn't       |
| `append`         | Add to end of existing section        |
| `insert_before`  | Insert before specific content        |
| `insert_after`   | Insert after specific content         |
| `merge`          | Combine with similar existing content |

## Content Modes

### STRICT Mode

- Creates new files/sections only
- Never merges with existing content
- Cleaner but more fragmented

### REFINEMENT Mode

- Can merge with existing content
- Shows merge previews
- Better for updating existing knowledge

Toggle with `POST /sessions/{id}/mode`.

## Pending Questions

AI may ask clarifying questions during generation:

```typescript
PendingQuestion {
  id: string
  question: string
}
```

**Handling**:

1. WebSocket sends `question` event
2. UI shows question to user
3. User provides answer
4. Call `answerQuestion(id, answer)`
5. WebSocket sends `answer` command
6. AI continues with answer context

## Execution

### What Happens

1. For each selected block:
   - Write to destination file/section
   - Calculate checksum
   - Verify write succeeded
2. Return results per block

### Result Structure

```typescript
WriteResult {
  block_id: string
  destination_file: string
  success: boolean
  checksum_verified: boolean
  error: string | null
}
```

## Error Handling

### During Generation

If AI encounters error:

1. WebSocket sends `error` event
2. State transitions to `error`
3. User can retry or cancel

### During Execution

If write fails:

1. Block marked as failed in results
2. Other blocks still processed
3. Summary shows partial success

### Recovery

From any error state:

1. Fix underlying issue
2. Call `reset()` or `selectSession()`
3. Resume from appropriate phase

## WebSocket Events

### Commands (Client → Server)

```javascript
// Start cleanup generation
ws.send(JSON.stringify({ command: 'generate_cleanup' }));

// Start routing generation
ws.send(JSON.stringify({ command: 'generate_routing' }));

// Send user message
ws.send(
  JSON.stringify({
    command: 'user_message',
    message: 'Focus on technical content',
  })
);

// Answer pending question
ws.send(
  JSON.stringify({
    command: 'answer',
    question_id: 'q1',
    answer: 'Yes, include both',
  })
);
```

### Events (Server → Client)

```javascript
// Cleanup started
{ type: 'cleanup_started' }

// Cleanup ready
{ type: 'cleanup_ready' }

// Routing started
{ type: 'routing_started' }

// Routing ready
{ type: 'routing_ready' }

// Question from AI
{ type: 'question', id: 'q1', question: 'Should I include...' }

// Error
{ type: 'error', message: 'Failed to...' }
```

## Key Files

| File                                        | Purpose                    |
| ------------------------------------------- | -------------------------- |
| `apps/ui/.../hooks/use-session-workflow.ts` | State machine (~808 lines) |
| `apps/ui/.../components/cleanup-review.tsx` | Cleanup review UI          |
| `apps/ui/.../components/routing-review.tsx` | Routing review UI          |
| `2.ai-library/src/api/routes/sessions.py`   | API endpoints              |
| `2.ai-library/src/session/manager.py`       | Session lifecycle          |
| `2.ai-library/src/models/cleanup_plan.py`   | Cleanup models             |
| `2.ai-library/src/models/routing_plan.py`   | Routing models             |
