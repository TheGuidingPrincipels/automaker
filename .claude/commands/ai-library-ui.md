# AI Library Frontend

Complete reference for the Knowledge Library UI components.

**Location**: `apps/ui/src/components/views/knowledge-library/`

## Component Structure

```
knowledge-library/
├── index.tsx                    # Main entry, mode toggling
├── components/
│   ├── input-mode/              # Session workflow UI
│   │   ├── index.tsx            # Main container
│   │   ├── components/
│   │   │   ├── control-row.tsx          # File upload, mode, actions
│   │   │   ├── empty-state.tsx          # Idle state UI
│   │   │   ├── plan-review.tsx          # Cleanup/routing container
│   │   │   ├── cleanup-review.tsx       # Keep/discard decisions
│   │   │   ├── routing-review.tsx       # Destination selection
│   │   │   ├── execution-status.tsx     # Post-execution summary
│   │   │   ├── phase-stepper.tsx        # Progress visualization
│   │   │   ├── sessions-dropdown.tsx    # Session selector
│   │   │   └── collapsible-transcript.tsx # Conversation history
│   │   └── plan-review.tsx              # Unified plan review
│   ├── query-mode/              # RAG search interface
│   └── library-browser/         # Library browsing UI
└── hooks/
    └── use-session-workflow.ts  # Master state machine
```

## Key Components

### KnowledgeLibrary (`index.tsx`)

Main view with mode switching between:

- **Input Mode**: Session-based content processing
- **Query Mode**: RAG search
- **Library Browser**: File browsing

### Input Mode Container

Layout: Control row (top) → Review area (middle) → Collapsible transcript (bottom)

**Workflow states**:

```
idle → file_staged → creating_session → cleanup_generating
→ cleanup_review → routing_generating → routing_review
→ ready_to_execute → executing → completed | error
```

### Cleanup Review (`cleanup-review.tsx`)

Displays cleanup plan items with:

- **Tabs**: all, pending, keep, discard
- **Per item**: content preview, confidence bar, AI analysis indicator
- **Actions**: Keep/Discard buttons, approve whole plan
- **Features**: Duplicate detection, similarity scores

### Routing Review (`routing-review.tsx`)

Displays routing options with:

- **3 destination options** per block with confidence scores
- **Custom input** option for manual destination
- **Actions**: Select option, reject block, reroute, approve plan
- **Merge previews** (in refinement mode)

### Phase Stepper (`phase-stepper.tsx`)

Visual progress indicator showing:

- Current phase (highlighted)
- Completed phases (checked)
- Pending phases (dimmed)

### Sessions Dropdown (`sessions-dropdown.tsx`)

Select from existing sessions:

- Lists recent sessions
- Shows session metadata (date, blocks, status)
- Quick actions (delete, resume)

## React Hooks

### Main Workflow Hook

**File**: `hooks/use-session-workflow.ts` (~808 lines)

**Returns**:

```typescript
UseSessionWorkflowResult {
  workflowState: WorkflowState
  sessionId: string | null
  session: SessionResponse
  cleanupPlan: CleanupPlanResponse
  routingPlan: RoutingPlanResponse
  stagedFile: {file: File, fileName: string} | null
  transcript: KLTranscriptEntry[]
  pendingQuestions: PendingQuestion[]
  isConnected: boolean
  isLoading: {creating, uploading, cleanup, routing, executing}
  error: string | null
  actions: {
    stageFile(file: File)
    clearStagedFile()
    startSession()
    sendMessage(message: string)
    answerQuestion(questionId: string, answer: string)
    approveCleanup()
    approveRouting()
    execute()
    cancelSession()
    selectSession(sessionId: string)
    reset()
  }
}
```

### Query Hooks (from `use-knowledge-library.ts`)

| Hook                          | Purpose                   |
| ----------------------------- | ------------------------- |
| `useKLCreateSession()`        | Create session mutation   |
| `useKLUploadSource()`         | Upload file mutation      |
| `useKLSession(id)`            | Get session query         |
| `useKLCleanupPlan(id)`        | Get cleanup plan query    |
| `useKLRoutingPlan(id, phase)` | Get routing plan query    |
| `useKLBlocks(id)`             | Get blocks query          |
| `useKLApproveCleanupPlan(id)` | Approve cleanup mutation  |
| `useKLApproveRoutingPlan(id)` | Approve routing mutation  |
| `useKLExecuteSession(id)`     | Execute mutation          |
| `useKLDeleteSession()`        | Delete session mutation   |
| `useKLSetMode(id)`            | Set content mode mutation |

## Store

**File**: `store/knowledge-library-store.ts`

Zustand store for local UI state:

- Selected session
- View mode (input/query/browser)
- UI preferences

## API Client

**File**: `lib/knowledge-library-api.ts`

Functions for API communication:

```typescript
createSession(request: CreateSessionRequest): Promise<SessionResponse>
uploadSource(sessionId: string, file: File): Promise<void>
getSession(sessionId: string): Promise<SessionResponse>
getCleanupPlan(sessionId: string): Promise<CleanupPlanResponse>
// ... etc
```

## WebSocket Integration

The workflow hook manages WebSocket connection:

1. **Connect** after session created
2. **Listen** for events (cleanup_ready, routing_ready, question, error)
3. **Send** commands (generate_cleanup, generate_routing, answer)
4. **Reconnect** on disconnect during active states

**Event handling flow**:

```
WebSocket event → Update workflow state → Invalidate React Query → UI refresh
```

## State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                          idle                                    │
└─────────────────────────────────────────────────────────────────┘
                              │ stageFile()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       file_staged                               │
└─────────────────────────────────────────────────────────────────┘
                              │ startSession()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    creating_session                             │
│  POST /sessions → POST /upload → Connect WS → send cleanup cmd  │
└─────────────────────────────────────────────────────────────────┘
                              │ 'cleanup_started' event
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   cleanup_generating                            │
└─────────────────────────────────────────────────────────────────┘
                              │ 'cleanup_ready' event
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     cleanup_review                              │
│        User reviews keep/discard decisions                      │
└─────────────────────────────────────────────────────────────────┘
                              │ approveCleanup()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   routing_generating                            │
└─────────────────────────────────────────────────────────────────┘
                              │ 'routing_ready' event
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     routing_review                              │
│        User selects destinations                                │
└─────────────────────────────────────────────────────────────────┘
                              │ approveRouting()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ready_to_execute                              │
└─────────────────────────────────────────────────────────────────┘
                              │ execute()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      executing                                  │
│                POST /execute                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ┌──────────┐        ┌──────────┐
              │completed │        │  error   │
              └──────────┘        └──────────┘
```

## Usage Example

```tsx
import { useSessionWorkflow } from '../hooks/use-session-workflow';

function InputMode() {
  const {
    workflowState,
    cleanupPlan,
    actions: { stageFile, startSession, approveCleanup },
  } = useSessionWorkflow();

  if (workflowState === 'idle') {
    return <FileDropzone onDrop={stageFile} />;
  }

  if (workflowState === 'cleanup_review') {
    return <CleanupReview plan={cleanupPlan} onApprove={approveCleanup} />;
  }
  // ... etc
}
```
