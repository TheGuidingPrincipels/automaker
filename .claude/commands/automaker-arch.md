# Automaker Architecture

Detailed architecture reference for the Automaker codebase.

## Server Architecture

**Location**: `apps/server/src/`

| Directory    | Purpose                                                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------------ |
| `routes/`    | Express route handlers by feature (agent, features, auto-mode, worktree, custom-agents, systems, knowledge)        |
| `services/`  | Business logic: AgentService, AutoModeService, FeatureLoader, TerminalService, CustomAgentsService, SystemsService |
| `providers/` | AI provider abstraction (Claude via Claude Agent SDK, Cursor, Codex, Gemini)                                       |
| `lib/`       | Utilities: events.ts, auth.ts, team-storage.ts, sdk-options.ts                                                     |

**Core Services**:

| Service         | File                           | Purpose                                       |
| --------------- | ------------------------------ | --------------------------------------------- |
| AutoModeService | `auto-mode-service.ts`         | Feature execution orchestration (~4700 lines) |
| AgentService    | `agent-service.ts`             | Session management, message streaming         |
| FeatureLoader   | `feature-loader.ts`            | Feature persistence, loading                  |
| ClaudeProvider  | `providers/claude-provider.ts` | Claude SDK wrapper                            |

## Frontend Architecture

**Location**: `apps/ui/src/`

| Directory           | Purpose                                                                      |
| ------------------- | ---------------------------------------------------------------------------- |
| `routes/`           | TanStack Router file-based routing                                           |
| `components/views/` | Board, settings, terminal, agents, systems, knowledge-hub, knowledge-library |
| `store/`            | Zustand stores: app-store.ts, setup-store.ts, knowledge-library-store.ts     |
| `hooks/`            | React hooks including queries (use-knowledge-library.ts)                     |
| `lib/`              | API client (http-api-client.ts), utilities                                   |

## SYSTEMS Feature (Agents, Systems, Knowledge Hub)

### Types (`libs/types/src/`)

- `custom-agent.ts` - CustomAgent, tools, MCP servers, model config
- `system.ts` - System, workflow steps, agents, execution
- `knowledge.ts` - Blueprint, KnowledgeEntry, Learning

### Team Storage

**File**: `apps/server/src/lib/team-storage.ts`

- File-based shared storage for multi-user deployment
- Collections: agents, systems, blueprints, knowledge-entries, learnings
- Uses `TEAM_DATA_DIR` env var (defaults to `DATA_DIR/team`)

### Routes (UI)

| File                         | URL                       | Purpose                                              |
| ---------------------------- | ------------------------- | ---------------------------------------------------- |
| `agents.tsx`                 | `/agents`                 | Custom agent management                              |
| `systems.tsx`                | `/systems`                | Systems layout                                       |
| `systems.index.tsx`          | `/systems`                | Gallery of multi-agent systems                       |
| `systems.$systemId.tsx`      | `/systems/:id`            | System detail (Overview, Agents, Workflow, Run tabs) |
| `knowledge-hub.tsx`          | `/knowledge-hub`          | Knowledge hub layout                                 |
| `knowledge-hub.index.tsx`    | `/knowledge-hub`          | Gallery (Blueprints, Knowledge Server, Learning)     |
| `knowledge-hub.$section.tsx` | `/knowledge-hub/:section` | Section detail                                       |

### Views (`apps/ui/src/components/views/`)

- `agents-page/` - Agent gallery, CRUD, create dialog
- `systems-page/` - System gallery with 4 built-in systems
- `system-detail-page/` - Tabbed detail view
- `knowledge-hub-page/` - Section cards
- `knowledge-section-page/` - Dynamic section content

### Backend Services (`apps/server/src/services/`)

- `custom-agents-service.ts` - CRUD + duplicate, archive, activate
- `systems-service.ts` - CRUD + run execution, 4 built-in systems
- `knowledge-service.ts` - Blueprints, entries, learnings + search

### Backend Routes (`apps/server/src/routes/`)

- `custom-agents/index.ts` - REST API for agents
- `systems/index.ts` - REST API + `/run` endpoint
- `knowledge/index.ts` - REST API for all knowledge types + search

## Data Storage

### Per-Project (`.automaker/`)

```
.automaker/
├── features/{featureId}/     # Feature data
│   ├── feature.json
│   ├── agent-output.md
│   └── images/
├── context/                  # Context files for AI agents
├── memory/                   # Learnings from past work
├── settings.json             # Project settings
├── spec.md                   # Project specification
└── analysis.json             # Structure analysis
```

### Global (`DATA_DIR`, default `./data`)

```
data/
├── settings.json             # Global settings, profiles
├── credentials.json          # API keys
├── sessions-metadata.json    # Chat session metadata
├── agent-sessions/           # Conversation histories
└── team/                     # SYSTEMS feature data
```

## Event System

**Event emitter**: `apps/server/src/lib/events.ts`
**WebSocket**: `apps/server/src/index.ts:440-543`
**Client**: `apps/ui/src/lib/http-api-client.ts:748-890`

**Event types**:

- `auto-mode:event` → started, feature_start, feature_complete, idle
- `agent:stream` → started, stream, tool_use, complete, error
- `feature:*` → created, started, completed, progress

## Execution Flow

```
UI: handleStartImplementation()
  → api.autoMode.runFeature(projectPath, featureId)
  → POST /auto-mode/run-feature
  → AutoModeService.executeFeature()
  → Find/create worktree (if branchName)
  → Load context (CLAUDE.md, memory)
  → ProviderFactory.getProviderForModel()
  → provider.executeQuery() [async generator]
  → Stream events via WebSocket
  → Save to agent-output.md
  → Update feature status
```

## Provider Support

| Provider | Model Prefix | CLI/SDK          |
| -------- | ------------ | ---------------- |
| Claude   | `claude-*`   | Claude Agent SDK |
| Cursor   | `cursor-*`   | cursor-agent CLI |
| Codex    | `codex-*`    | Codex CLI        |
| Gemini   | `gemini-*`   | gemini-cli       |

## Quick Debug Paths

| Issue                  | Check First                                                |
| ---------------------- | ---------------------------------------------------------- |
| Feature not starting   | `auto-mode-service.ts` → `checkWorktreeCapacity()`         |
| Plan not generating    | `auto-mode-service.ts` → `getPlanningPromptPrefix()`       |
| Events not reaching UI | `lib/events.ts`, WebSocket in `index.ts:440+`              |
| Session not resuming   | `agent-service.ts` → `loadSession()`, check `sdkSessionId` |
| Wrong worktree         | `routes/worktree/routes/create.ts`, feature.branchName     |

## Keyboard Shortcuts

- `Shift+A` - Open Agents page
- `Shift+Y` - Open Systems page
- `Shift+K` - Open Knowledge Hub
