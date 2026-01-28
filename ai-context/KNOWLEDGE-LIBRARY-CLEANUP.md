# Knowledge Library Cleanup Process - Navigation Guide

> **Purpose**: Context-efficient guide for downstream Claude Code sessions to navigate and understand the Knowledge Library cleanup workflow.

## Quick Reference

| Layer                | Primary Files                                                                  | Purpose                    |
| -------------------- | ------------------------------------------------------------------------------ | -------------------------- |
| **Types**            | `libs/types/src/knowledge-library.ts`                                          | All TypeScript interfaces  |
| **Frontend Hook**    | `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts` | Workflow orchestration     |
| **Frontend Store**   | `apps/ui/src/store/knowledge-library-store.ts`                                 | UI state (Zustand)         |
| **Frontend Queries** | `apps/ui/src/hooks/queries/use-knowledge-library.ts`                           | API hooks (TanStack Query) |
| **Backend Routes**   | `2.ai-library/src/api/routes/sessions.py`                                      | REST + WebSocket endpoints |
| **Backend Manager**  | `2.ai-library/src/session/manager.py`                                          | Session lifecycle logic    |
| **Backend Models**   | `2.ai-library/src/models/cleanup_plan.py`                                      | Cleanup plan structure     |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (React + TypeScript)                              │
│  Port: 3007 (main), connects to AI-Library on 8002          │
├─────────────────────────────────────────────────────────────┤
│  useSessionWorkflow() → manages state machine               │
│  useKnowledgeLibraryStore → UI-only state (Zustand)         │
│  useKL*() hooks → TanStack Query for API calls              │
│  WebSocket → real-time streaming from backend               │
└─────────────────────────────────────────────────────────────┘
                          ↕ REST + WebSocket ↕
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (Python FastAPI)                                   │
│  Port: 8002 (default, via VITE_KNOWLEDGE_LIBRARY_API)       │
├─────────────────────────────────────────────────────────────┤
│  SessionManager → orchestrates cleanup/routing/execution    │
│  ClaudeCodeClient → AI suggestions via SDK                  │
│  ContentWriter → writes blocks to library with verification │
└─────────────────────────────────────────────────────────────┘
```

---

## State Machines

### Frontend WorkflowState

```
idle → file_staged → creating_session → cleanup_generating → cleanup_review
  → routing_generating → routing_review → ready_to_execute → executing → completed
```

**Location**: `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:40-51`

### Backend SessionPhase

```
initialized → parsing → cleanup_plan_ready → routing_plan_ready
  → awaiting_approval → ready_to_execute → executing → verifying → completed
```

**Location**: `2.ai-library/src/models/session.py`

---

## Complete File Map

### Types (shared definitions)

```
libs/types/src/knowledge-library.ts
├── KLContentMode: 'strict' | 'refinement'
├── KLCleanupDisposition: 'keep' | 'discard'
├── KLSessionPhase: session lifecycle states
├── KLCleanupPlanResponse: cleanup plan with items
├── KLCleanupItemResponse: individual block decision
├── KLRoutingPlanResponse: routing plan with blocks
├── KLBlockRoutingItemResponse: routing options per block
├── KLStreamEvent: WebSocket event structure
└── KLStreamCommand: WebSocket commands
```

### Frontend - Workflow Orchestration

```
apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts
├── WorkflowState type (line 40-51)
├── useSessionWorkflow() hook (line 151)
├── handleStreamEvent() - WebSocket handler (line 214)
├── connectWebSocket() - connection management (line 416)
├── startSession() - creates session + uploads (line 562)
├── approveCleanup() - approve & trigger routing (line 670)
├── approveRouting() - approve & enable execute (line 692)
└── execute() - run execution (line 711)
```

### Frontend - UI Store

```
apps/ui/src/store/knowledge-library-store.ts
├── activeView: 'input' | 'library' | 'query'
├── currentSessionId: string | null
├── stagedUpload: { file, fileName } | null
├── sessionTranscript: KLTranscriptEntry[]
├── proposedNewFiles: Record<string, KLProposedNewFile>
├── stageUpload() / clearStagedUpload()
├── addTranscriptEntry() / clearTranscript()
└── resetSession()
```

### Frontend - Query Hooks

```
apps/ui/src/hooks/queries/use-knowledge-library.ts
├── useKLHealth() - backend health check
├── useKLSession(sessionId) - get session
├── useKLCreateSession() - create new session
├── useKLUploadSource() - upload file to session
├── useKLCleanupPlan(sessionId) - get cleanup plan
├── useKLDecideCleanupItem() - set keep/discard
├── useKLApproveCleanupPlan() - approve cleanup
├── useKLRoutingPlan(sessionId) - get routing plan
├── useKLSelectDestination() - select block destination
├── useKLApproveRoutingPlan() - approve routing
└── useKLExecuteSession() - execute session
```

### Frontend - UI Components

```
apps/ui/src/components/views/knowledge-library/
├── index.tsx                    # Main view with tabs
├── hooks/
│   └── use-session-workflow.ts  # Workflow orchestrator
└── components/
    └── input-mode/
        ├── index.tsx            # Input mode container
        ├── plan-review.tsx      # Cleanup/routing phases
        └── components/
            ├── cleanup-review.tsx       # Cleanup decisions UI
            ├── routing-review.tsx       # Routing decisions UI
            ├── control-row.tsx          # Upload, mode toggle
            ├── collapsible-transcript.tsx  # Session transcript
            ├── phase-stepper.tsx        # Progress indicator
            └── sessions-dropdown.tsx    # Session selector
```

### Backend - API Routes

```
2.ai-library/src/api/routes/sessions.py
├── POST /sessions                          # Create session (line 57)
├── POST /sessions/{id}/upload              # Upload file (line 146)
├── GET /sessions/{id}                      # Get session (line 105)
├── GET /sessions/{id}/blocks               # Get parsed blocks (line 281)
├── GET /sessions/{id}/cleanup              # Get cleanup plan (line 345)
├── POST /sessions/{id}/cleanup/decide/{block_id}  # Set decision (line 362)
├── POST /sessions/{id}/cleanup/approve     # Approve cleanup (line 394)
├── GET /sessions/{id}/plan                 # Get routing plan (line 458)
├── POST /sessions/{id}/plan/select/{block_id}    # Select destination (line 475)
├── POST /sessions/{id}/plan/approve        # Approve routing (line 558)
├── POST /sessions/{id}/execute             # Execute session (line 655)
└── WebSocket /sessions/{id}/stream         # Real-time updates (line 932)
```

### Backend - Session Manager

```
2.ai-library/src/session/manager.py
├── create_session()              # Create + parse (line 38)
├── generate_cleanup_plan()       # Default cleanup plan (line 91)
├── set_cleanup_decision()        # Record user decision (line 138)
├── approve_cleanup_plan()        # Approve cleanup (line 163)
├── generate_routing_plan()       # Default routing plan (line 186)
├── select_destination()          # Record destination (line 243)
├── approve_plan()                # Approve routing (line 305)
├── generate_cleanup_plan_with_ai()  # AI-powered cleanup (line 385)
└── generate_routing_plan_with_ai()  # AI-powered routing (line 429)
```

### Backend - Models

```
2.ai-library/src/models/
├── session.py          # ExtractionSession, SessionPhase, PendingQuestion
├── cleanup_plan.py     # CleanupPlan, CleanupItem, CleanupDisposition
├── routing_plan.py     # RoutingPlan, BlockRoutingItem, BlockDestination
├── content.py          # SourceDocument, ContentBlock, BlockType
└── content_mode.py     # ContentMode (STRICT, REFINEMENT)
```

### Backend - Execution

```
2.ai-library/src/execution/
├── writer.py           # ContentWriter.write_block(), checksum verification
└── markers.py          # Block markers in library files
```

### Backend - AI Integration

```
2.ai-library/src/sdk/
├── client.py           # ClaudeCodeClient for AI suggestions
├── auth.py             # OAuth token loading
└── prompts/
    ├── cleanup_mode.py # Cleanup AI prompts
    └── routing_mode.py # Routing AI prompts
```

---

## Key Data Flows

### 1. Cleanup Decision Flow

```
User clicks Keep/Discard
  → cleanup-review.tsx: onClick handler
    → useKLDecideCleanupItem().mutateAsync({blockId, disposition})
      → POST /sessions/{id}/cleanup/{block_id}/decide
        → SessionManager.set_cleanup_decision()
          → CleanupItem.final_disposition = disposition
            → SessionStorage.save()
```

### 2. WebSocket Event Flow

```
Backend generates cleanup plan
  → yield PlanEvent(type=CLEANUP_READY)
    → WebSocket sends: { event_type: 'cleanup_ready', data: {...} }
      → handleStreamEvent() in use-session-workflow.ts
        → setWorkflowState('cleanup_review')
          → queryClient.invalidateQueries(cleanupPlan)
            → CleanupReview re-renders with new data
```

### 3. Execution Flow

```
User clicks Execute
  → execute() in use-session-workflow.ts
    → executeSessionMutation.mutateAsync()
      → POST /sessions/{id}/execute
        → For each block: ContentWriter.write_block()
          → Write to file + calculate checksums
            → Read back + verify checksums
              → Return ExecuteResponse with results
```

---

## Critical Business Rules

1. **Never auto-discard**: All `discard` decisions require explicit user approval
2. **Code blocks are byte-strict**: Fenced code blocks must match exactly
3. **Prose uses canonical checksums**: Whitespace may change but words preserved
4. **Verify all writes**: Read back and compare checksums after every write
5. **Cleanup before routing**: Cleanup plan must be approved before routing
6. **All blocks resolved**: All routing decisions required before execution

---

## Content Modes

| Mode         | Behavior                                                  |
| ------------ | --------------------------------------------------------- |
| `strict`     | Preserve exact content, no merges/rewrites allowed        |
| `refinement` | Allows minor formatting fixes, merge operations supported |

---

## WebSocket Commands

| Command            | Purpose                         |
| ------------------ | ------------------------------- |
| `generate_cleanup` | Trigger cleanup plan generation |
| `generate_routing` | Trigger routing plan generation |
| `user_message`     | Send user guidance message      |
| `answer`           | Answer a pending question       |
| `ping`             | Keep-alive check                |

---

## WebSocket Events

| Event Type        | When Emitted                     |
| ----------------- | -------------------------------- |
| `connected`       | WebSocket connection established |
| `cleanup_started` | Cleanup generation begins        |
| `cleanup_ready`   | Cleanup plan complete            |
| `routing_started` | Routing generation begins        |
| `routing_ready`   | Routing plan complete            |
| `question`        | AI asks for clarification        |
| `error`           | Error occurred                   |
| `progress`        | Progress update                  |

---

## Configuration

### Frontend

```bash
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8002  # AI-Library URL
```

### Backend

```yaml
# 2.ai-library/configs/settings.yaml
LIBRARY_PATH: ./library # Output library location
STORAGE_PATH: ./sessions # Session persistence
CLAUDE_MODEL: claude-sonnet-4 # AI model for suggestions
```

---

## Testing Files

```
apps/ui/src/hooks/queries/use-knowledge-library.test.ts  # Query hook tests
apps/ui/src/hooks/streams/use-kl-session-stream.test.ts  # Stream hook tests
apps/ui/src/store/knowledge-library-store.test.ts        # Store tests
2.ai-library/tests/                                       # Backend tests
```

---

## Related Documentation

- `2.ai-library/CLAUDE.md` - Backend project instructions
- `2.ai-library/SETUP.md` - Backend setup guide
- `6.Short-Term-Memory-MCP/docs/AI-SESSION-CLEANUP.md` - Session cleanup docs
- `6.Short-Term-Memory-MCP/docs/SESSION-CLEANUP-GUIDE.md` - Cleanup guide

---

## Common Tasks Quick Reference

### Adding a new cleanup decision option

1. Update `KLCleanupDisposition` in `libs/types/src/knowledge-library.ts`
2. Update `CleanupDisposition` enum in `2.ai-library/src/models/cleanup_plan.py`
3. Update UI in `cleanup-review.tsx`
4. Update backend validation in `sessions.py`

### Adding a new routing action

1. Update `KLDestinationOptionResponse` in types
2. Update `BlockDestination` in `routing_plan.py`
3. Add handling in `sessions.py` execute endpoint (line 655+)
4. Update `ContentWriter` if new write behavior needed

### Modifying WebSocket events

1. Add event type to `KLStreamEventType` in types
2. Add handling in `handleStreamEvent()` in `use-session-workflow.ts`
3. Emit event from backend in `sessions.py` WebSocket handler

### Changing workflow phases

1. Update `WorkflowState` type in `use-session-workflow.ts`
2. Update phase derivation logic (line 472-507)
3. Update `SessionPhase` enum if backend phase changes
4. Update UI phase displays in `phase-stepper.tsx`
