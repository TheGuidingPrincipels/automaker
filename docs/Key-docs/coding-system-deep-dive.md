# Automaker Coding System - Deep Dive

A comprehensive explanation of how Automaker's autonomous AI coding pipeline works, from clicking "Make" to completed feature.

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [Starting a Feature: UI to Server](#2-starting-a-feature-ui-to-server)
3. [The AutoModeService: The Brain](#3-the-automodeservice-the-brain)
4. [Planning System: How Plans Are Created](#4-planning-system-how-plans-are-created)
5. [Task Execution: Breaking Down the Work](#5-task-execution-breaking-down-the-work)
6. [AI Providers: Claude, Codex, and More](#6-ai-providers-claude-codex-and-more)
7. [Worktrees: Isolated Development](#7-worktrees-isolated-development)
8. [Session Management: Memory & Context](#8-session-management-memory--context)
9. [Event System: Real-Time Updates](#9-event-system-real-time-updates)
10. [Logging & Output: Where Everything Goes](#10-logging--output-where-everything-goes)
11. [Auto-Mode Loop: Running Multiple Features](#11-auto-mode-loop-running-multiple-features)
12. [Dependency Resolution: Smart Ordering](#12-dependency-resolution-smart-ordering)
13. [Complete Flow Diagram](#13-complete-flow-diagram)

---

## 1. The Big Picture

Automaker is an autonomous AI development studio. Think of it as a factory that takes feature requests and turns them into working code, with AI agents doing the actual implementation.

**The core workflow:**

```
User writes feature → AI plans the work → User approves plan → AI executes tasks → Code is complete
```

**Key components:**

1. **Kanban Board (UI)** - Where you manage features visually
2. **AutoModeService (Server)** - The orchestrator that runs everything
3. **AI Providers** - Claude, Codex, Gemini that do the actual coding
4. **Worktrees** - Git branches where each feature is built in isolation
5. **Event System** - Real-time updates flowing from server to UI

---

## 2. Starting a Feature: UI to Server

### What happens when you click "Make" or drag a feature to "In Progress"

**Step 1: User Action in the UI**

When you click the "Make" button on a feature card or drag it to the "In Progress" column, the UI executes this sequence:

```
File: apps/ui/src/components/views/board-view/hooks/use-board-actions.ts

handleStartImplementation(feature):
  1. Check concurrency - Is the worktree already running too many features?
  2. Check dependencies - Are all required features completed?
  3. Update local state - Immediately mark as "in_progress" (optimistic update)
  4. Persist to server - Save the status change to disk
  5. Call API - Request the server to start execution
```

**Step 2: API Call to Server**

The UI calls `api.autoMode.runFeature(projectPath, featureId, useWorktrees)`:

```
POST /api/autoMode/runFeature
{
  projectPath: "/Users/you/your-project",
  featureId: "feature-123-abc",
  useWorktrees: true
}
```

**Step 3: Server Receives Request**

```
File: apps/server/src/routes/auto-mode/routes/run-feature.ts

1. Validate the request
2. Check worktree capacity (max concurrent features)
3. If capacity available:
   - Call AutoModeService.executeFeature() in background
   - Return 202 Accepted immediately (non-blocking)
4. If at capacity:
   - Return 429 Too Many Requests
```

The key insight: **The server returns immediately** while the feature executes in the background. This is why you see real-time updates - the work happens asynchronously.

---

## 3. The AutoModeService: The Brain

This is the heart of Automaker's coding system, located at:

```
apps/server/src/services/auto-mode-service.ts (4,700+ lines)
```

### What It Does

The AutoModeService orchestrates everything:

- Loading feature details
- Resolving which worktree to use
- Building prompts for the AI
- Streaming responses back to the UI
- Saving output to files
- Managing plan approvals
- Running multiple features concurrently

### The executeFeature() Method

This is the main entry point when a feature starts:

```typescript
async executeFeature(projectPath, featureId, useWorktrees, isAutoMode):
  1. Load the feature from .automaker/features/{featureId}/feature.json
  2. Check if there's already a plan waiting for approval
  3. Find or create the worktree if feature has a branchName
  4. Load context files (CLAUDE.md, memory, etc.)
  5. Build the prompt (including planning prefix if needed)
  6. Call runAgent() to execute
  7. Update feature status on completion
```

### The runAgent() Method

This is where the AI actually runs:

```typescript
async runAgent(workDir, featureId, prompt, abortController, projectPath):
  1. Get the right provider (Claude, Codex, etc.) based on model
  2. Build execution options (system prompt, allowed tools, MCP servers)
  3. Create async stream via provider.executeQuery()
  4. For each message in stream:
     - TEXT: Emit as 'auto_mode_progress' event
     - TOOL_USE: Log tool invocation, emit event
     - COMPLETE: Mark as done
     - ERROR: Handle failure
  5. Save output to agent-output.md
  6. Return final response
```

---

## 4. Planning System: How Plans Are Created

Before an AI starts coding, it can first create a plan. This is controlled by the `planningMode` setting.

### Planning Modes

| Mode     | What It Does                                    | Needs Approval? |
| -------- | ----------------------------------------------- | --------------- |
| **skip** | Jump straight to coding                         | No              |
| **lite** | Quick 3-7 task outline                          | Optional        |
| **spec** | Detailed specification with acceptance criteria | Yes             |
| **full** | Comprehensive SDD with phases, risks, metrics   | Yes             |

### How Plans Are Generated

```
File: libs/prompts/src/defaults.ts

The system injects a planning prompt BEFORE your feature description:

"You are an AI assistant. Before implementing, analyze the codebase and create
a plan following this exact format:

- [ ] T001: Task description | File: path/to/file
- [ ] T002: Another task | File: another/file

When done planning, output: [SPEC_GENERATED]"
```

### The Approval Flow

1. AI generates plan and outputs `[SPEC_GENERATED]` marker
2. System detects marker, extracts plan content
3. Feature status changes to "awaiting approval"
4. User sees plan in the Plan Approval Dialog
5. User can:
   - **Approve** → Execution continues with tasks
   - **Request Changes** → AI regenerates with feedback
   - **Reject** → Feature goes back to backlog

### Task Parsing

The system parses tasks from the generated plan:

```
File: auto-mode-service.ts → parseTasksFromSpec()

Looks for: - [ ] T001: Description | File: path/to/file

Creates:
{
  id: "T001",
  description: "Description",
  filePath: "path/to/file",
  status: "pending"
}
```

---

## 5. Task Execution: Breaking Down the Work

When a plan has multiple tasks, each task gets its own focused AI call.

### Task-by-Task Execution

```
For each task in parsedTasks:
  1. Build task-specific prompt:
     "You are implementing task T001 of 5.
      Task: Create user model
      File: src/models/user.ts

      Full plan for context: [plan content]

      Focus ONLY on this task."

  2. Spawn dedicated agent call for this task
  3. Stream output, emit events
  4. Mark task complete
  5. Update progress: tasksCompleted++
  6. Move to next task
```

### Progress Tracking

The feature's `planSpec` tracks progress:

```typescript
feature.planSpec = {
  status: 'approved',
  content: 'Full plan text...',
  tasks: [
    { id: 'T001', description: '...', status: 'completed' },
    { id: 'T002', description: '...', status: 'in_progress' },
    { id: 'T003', description: '...', status: 'pending' },
  ],
  tasksCompleted: 1,
  tasksTotal: 3,
  currentTaskId: 'T002',
};
```

---

## 6. AI Providers: Claude, Codex, and More

Automaker supports multiple AI providers through a factory pattern.

### Provider Architecture

```
File: apps/server/src/providers/provider-factory.ts

Provider Registry:
├── Claude (priority 0) - Default for claude-* models
├── Cursor (priority 10) - For cursor-* models
├── Codex (priority 5) - For codex-* models
├── OpenCode (priority 3)
└── Gemini (priority 4)
```

### How Providers Work

All providers implement the same interface:

```typescript
interface Provider {
  executeQuery(options): AsyncGenerator<ProviderMessage>;
  detectInstallation(): Promise<InstallationStatus>;
  getAvailableModels(): ModelDefinition[];
  getName(): string;
}
```

### Claude Provider (The Main One)

```
File: apps/server/src/providers/claude-provider.ts

Uses the official Claude Agent SDK (@anthropic-ai/claude-agent-sdk):
- Handles authentication (API key or OAuth token)
- Supports extended thinking (thinkingLevel)
- Supports vision (image inputs)
- Supports MCP servers
- Manages SDK session IDs for conversation continuity
```

### Model Resolution

Model names are resolved to full IDs:

```
haiku → claude-haiku-4-5
sonnet → claude-sonnet-4-20250514
opus → claude-opus-4-5-20251101
```

---

## 7. Worktrees: Isolated Development

Each feature can run in its own isolated git worktree, protecting your main branch.

### What's a Worktree?

A git worktree is like a parallel checkout of your repo. You can have:

- Main branch at `/your-project`
- Feature branch at `/your-project/../.worktrees/feature-auth`

Both exist simultaneously, with changes isolated to each.

### How Worktrees Are Used

```
When feature.branchName is set:
  1. System checks if worktree exists: git worktree list --porcelain
  2. If not: git worktree add .worktrees/{branch} -b {branch}
  3. AI runs in that worktree's directory
  4. Changes only affect that branch
  5. When done, you can merge via PR
```

### Worktree Capacity

Each worktree has its own concurrency limit (default: 3 features).

```
Main worktree: 2 features running (capacity: 3) → Can start 1 more
Feature worktree: 1 feature running (capacity: 3) → Can start 2 more
```

---

## 8. Session Management: Memory & Context

### How Sessions Work

Every AI conversation is a "session" with persistent history.

```
Storage:
├── data/agent-sessions/{sessionId}.json  → Conversation messages
└── data/sessions-metadata.json           → Session metadata
```

### Session Structure

```typescript
Session {
  messages: [
    { role: "user", content: "Implement login...", timestamp: "..." },
    { role: "assistant", content: "I'll create...", timestamp: "..." }
  ],
  sdkSessionId: "claude-sdk-123",  // For conversation continuity
  workingDirectory: "/path/to/project",
  model: "claude-opus-4-5"
}
```

### SDK Session ID: The Key to Continuity

The Claude SDK maintains its own session internally. Automaker captures and stores the `sdkSessionId`:

1. First message → SDK returns a session_id
2. Automaker saves it to metadata
3. Next request → Automaker passes sdkSessionId back
4. SDK resumes the same conversation context

This allows conversations to continue across server restarts.

### Context Window Management

**Token Budgets for Thinking:**

```typescript
THINKING_TOKEN_BUDGET = {
  none: undefined,
  low: 1024,
  medium: 10000,
  high: 16000,
  ultrathink: 32000,
};
```

**Manual Truncation:**

- Large diffs truncated to 10,000 characters
- Very large files truncated to avoid token limits
- No automatic context window management - relies on SDK

---

## 9. Event System: Real-Time Updates

This is how you see live progress in the UI.

### Event Flow Architecture

```
Server (EventEmitter)
    ↓ emit('agent:stream', { content: "..." })
WebSocket (/api/events)
    ↓ JSON message
UI (HttpApiClient)
    ↓ callback distribution
React Components
    ↓ setState()
Visual Update
```

### Event Types

**Auto-Mode Events:**

- `auto_mode_started` - Loop started
- `auto_mode_feature_start` - Feature beginning
- `auto_mode_progress` - Text streaming
- `auto_mode_feature_complete` - Feature done
- `auto_mode_idle` - Backlog empty
- `auto_mode_error` - Something failed

**Agent Events:**

- `started` - Agent initialized
- `stream` - Partial text output
- `tool_use` - Agent using a tool (Read, Write, Bash, etc.)
- `complete` - Agent finished

### WebSocket Setup

```
File: apps/server/src/index.ts (lines 440-543)

Two WebSocket servers:
1. /api/events → All system events (features, agent, auto-mode)
2. /api/terminal/ws → Terminal I/O (PTY streams)
```

---

## 10. Logging & Output: Where Everything Goes

### Agent Output Files

Every feature's AI output is saved:

```
.automaker/features/{featureId}/
├── feature.json        → Feature metadata
├── agent-output.md     → Full agent response (markdown)
└── images/             → Any uploaded images
```

### Agent Output Format

```markdown
I'll implement the user authentication feature.

Let me first analyze the existing codebase:

🔧 Tool: Bash
Input: {
"command": "find src -name '\*.ts'",
"description": "Find TypeScript files"
}

Found the following files...

🔧 Tool: Read
Input: {
"file_path": "src/routes/index.ts"
}

Now I'll create the auth middleware:

🔧 Tool: Write
Input: {
"file_path": "src/middleware/auth.ts",
"content": "..."
}
```

### Logging Utility

```
File: libs/utils/src/logger.ts

const logger = createLogger('AgentService');
logger.info('Session started', sessionId);
logger.error('Connection failed', error);

Output: [INFO] [AgentService] Session started abc123
```

---

## 11. Auto-Mode Loop: Running Multiple Features

When you turn on Auto-Mode, a background loop continuously processes features.

### How the Loop Works

```
File: auto-mode-service.ts → runAutoLoopForProject()

While running:
  1. Check if at capacity (maxConcurrency reached?)
  2. Load pending features for this worktree
  3. Sort by dependencies (topological sort)
  4. Filter to only features with satisfied dependencies
  5. Pick next feature
  6. Execute it (non-blocking, in background)
  7. Sleep 2 seconds
  8. Repeat

When no pending features:
  → Emit 'auto_mode_idle'
  → Continue checking (features might be added)
```

### Per-Worktree Execution

Auto-mode runs separately for each worktree:

```
Main worktree loop → Processes features with branchName=null
Feature-X loop → Processes features with branchName="feature-x"
```

### Failure Handling

```
Track failures over last 60 seconds:
- 3 consecutive failures → Auto-pause
- 'quota_exhausted' error → Immediate pause
- 'rate_limit' error → Immediate pause

User must manually restart after pause.
```

---

## 12. Dependency Resolution: Smart Ordering

Features can depend on other features. Automaker ensures dependencies complete first.

### How Dependencies Work

```typescript
feature = {
  id: 'feature-auth',
  dependencies: ['feature-user-model', 'feature-database'],
};
```

This feature won't start until both dependencies are in 'completed' or 'verified' status.

### The Algorithm

```
File: libs/dependency-resolver/src/resolver.ts

Uses Kahn's Algorithm (Topological Sort):
1. Build dependency graph
2. Find features with no dependencies (in-degree = 0)
3. Process those first
4. Remove them from graph, recalculate
5. Repeat until all processed

Within same dependency level:
- Sort by priority (1 = high, 2 = medium, 3 = low)
```

### Dependency Checks in Auto-Mode

```typescript
areDependenciesSatisfied(feature, allFeatures):
  For each dependency ID:
    Find the dependency feature
    Check its status:
      - 'completed' → Satisfied
      - 'verified' → Satisfied
      - 'in_progress' → Maybe wait (setting dependent)
      - Other → Not satisfied

  Return true only if ALL satisfied
```

---

## 13. Complete Flow Diagram

Here's the entire system flow from button click to completion:

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Kanban Board]                                                     │
│       │                                                             │
│       ├── Click "Make" Button ─────────────────────────────┐        │
│       │   (card-actions.tsx:328)                           │        │
│       │                                                    │        │
│       └── Drag to "In Progress" ───────────────────────────┤        │
│           (use-board-drag-drop.ts:194)                     │        │
│                                                            ▼        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ handleStartImplementation()                                   │   │
│  │ ├── Check concurrency limits                                  │   │
│  │ ├── Check dependency status                                   │   │
│  │ ├── Update local state (optimistic)                          │   │
│  │ ├── Persist to server                                         │   │
│  │ └── Call api.autoMode.runFeature()                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ POST /api/autoMode/runFeature
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                              SERVER                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Route Handler: run-feature.ts]                                    │
│       │                                                             │
│       ├── Validate request                                          │
│       ├── Check worktree capacity                                   │
│       └── Call AutoModeService.executeFeature() (background)        │
│                         │                                           │
│                         ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ AutoModeService.executeFeature()                              │   │
│  │                                                                │   │
│  │ 1. Load feature from .automaker/features/{id}/feature.json    │   │
│  │ 2. Find/create worktree (if branchName set)                   │   │
│  │ 3. Load context files (CLAUDE.md, memory)                     │   │
│  │ 4. Check planning mode → inject planning prompt               │   │
│  │ 5. Call runAgent()                                            │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                         │                                           │
│                         ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ AutoModeService.runAgent()                                    │   │
│  │                                                                │   │
│  │ 1. Get provider: ProviderFactory.getProviderForModel()        │   │
│  │ 2. Build ExecuteOptions (prompt, model, cwd, tools)          │   │
│  │ 3. Call provider.executeQuery() → AsyncGenerator              │   │
│  │                                                                │   │
│  │    ┌─ For each message in stream: ─────────────────────────┐  │   │
│  │    │                                                        │  │   │
│  │    │  TEXT → emit('auto_mode_progress', { content })       │  │   │
│  │    │  TOOL_USE → log tool, emit('tool_use', { tool })      │  │   │
│  │    │  COMPLETE → break loop                                 │  │   │
│  │    │  ERROR → handle failure                                │  │   │
│  │    │                                                        │  │   │
│  │    └────────────────────────────────────────────────────────┘  │   │
│  │                                                                │   │
│  │ 4. Save output to agent-output.md                             │   │
│  │ 5. Update feature status                                      │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                         │                                           │
│                         ▼                                           │
│  [If Planning Mode != 'skip']                                       │
│       │                                                             │
│       ├── AI generates plan                                         │
│       ├── System detects [SPEC_GENERATED] marker                   │
│       ├── Parse tasks from plan                                     │
│       ├── If requirePlanApproval:                                   │
│       │       │                                                     │
│       │       ├── Emit 'plan_approval_required'                     │
│       │       ├── Wait for user approval ◄───────────────────┐      │
│       │       │                           (Plan Dialog)      │      │
│       │       ├── User approves ─────────────────────────────┘      │
│       │       └── Continue execution                                │
│       │                                                             │
│       └── Execute each task in sequence                             │
│           ├── Task T001 → runAgent() → emit events                 │
│           ├── Task T002 → runAgent() → emit events                 │
│           └── Task T003 → runAgent() → emit events                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ WebSocket Events
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         EVENT STREAMING                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Server EventEmitter]                                              │
│       │                                                             │
│       └── events.emit('agent:stream', { type, content, ... })      │
│                         │                                           │
│                         ▼                                           │
│  [WebSocket Server /api/events]                                     │
│       │                                                             │
│       └── ws.send(JSON.stringify({ type, payload }))               │
│                         │                                           │
│                         ▼                                           │
│  [UI WebSocket Client]                                              │
│       │                                                             │
│       └── this.eventCallbacks.get(type).forEach(cb => cb(payload)) │
│                         │                                           │
│                         ▼                                           │
│  [React Components]                                                 │
│       │                                                             │
│       ├── Agent Output Modal: Display streaming text                │
│       ├── Kanban Card: Show progress indicator                      │
│       ├── Terminal View: Show live output                           │
│       └── Board View: Update feature status                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ On Completion
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          COMPLETION                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Feature status → 'waiting_approval'                             │
│  2. Output saved to .automaker/features/{id}/agent-output.md       │
│  3. User reviews changes in UI                                      │
│  4. User clicks "Verify" → status → 'verified'                     │
│  5. User can then:                                                  │
│     ├── Create PR (if worktree)                                     │
│     ├── Commit changes                                              │
│     └── Complete/Archive feature                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary

Automaker's coding system is a sophisticated pipeline that:

1. **Starts in the UI** - User actions trigger API calls
2. **Routes through AutoModeService** - The central orchestrator
3. **Optionally plans first** - AI creates structured task lists
4. **Executes via providers** - Claude SDK or other AI tools
5. **Runs in worktrees** - Isolated git branches for safety
6. **Streams everything** - Real-time WebSocket updates
7. **Persists results** - Session history and agent output saved
8. **Handles dependencies** - Smart ordering of features
9. **Supports concurrency** - Multiple features in parallel

The result is an autonomous coding factory that can implement features with minimal human intervention, while keeping you informed every step of the way.
