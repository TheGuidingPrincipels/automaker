# Coding Navigation System

Quick reference for Automaker's autonomous coding pipeline. Use this to locate code and understand execution flow.

---

## Entry Points

| Action           | UI File                                                                  | API Endpoint                    | Server Handler                                           |
| ---------------- | ------------------------------------------------------------------------ | ------------------------------- | -------------------------------------------------------- |
| Add Feature      | `apps/ui/src/components/views/board-view/dialogs/add-feature-dialog.tsx` | `POST /api/features/create`     | `apps/server/src/routes/features/routes/create.ts`       |
| Click "Make"     | `apps/ui/.../board-view/components/kanban-card/card-actions.tsx:328`     | `POST /api/autoMode/runFeature` | `apps/server/src/routes/auto-mode/routes/run-feature.ts` |
| Drag to Progress | `apps/ui/.../board-view/hooks/use-board-drag-drop.ts:194`                | Same as above                   | Same as above                                            |
| Start Auto-Loop  | Board header toggle                                                      | `POST /api/autoMode/start`      | `apps/server/src/routes/auto-mode/routes/start.ts`       |

---

## Core Services

| Service             | Location                                        | Purpose                                           |
| ------------------- | ----------------------------------------------- | ------------------------------------------------- |
| **AutoModeService** | `apps/server/src/services/auto-mode-service.ts` | Feature execution orchestration (4,700+ lines)    |
| **AgentService**    | `apps/server/src/services/agent-service.ts`     | Session management, message streaming (970 lines) |
| **FeatureLoader**   | `apps/server/src/services/feature-loader.ts`    | Feature persistence, loading                      |
| **ClaudeProvider**  | `apps/server/src/providers/claude-provider.ts`  | Claude SDK wrapper (481 lines)                    |
| **ProviderFactory** | `apps/server/src/providers/provider-factory.ts` | Multi-provider routing                            |

---

## Execution Flow (Quick Reference)

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

---

## Key File Locations

### Planning System

- **Prompts**: `libs/prompts/src/defaults.ts:35-274`
- **Plan parsing**: `auto-mode-service.ts` → `parseTasksFromSpec()`, `parseTaskLine()`
- **Approval endpoint**: `apps/server/src/routes/auto-mode/routes/approve-plan.ts`
- **Approval UI**: `apps/ui/.../board-view/dialogs/plan-approval-dialog.tsx`

### Session Management

- **Session storage**: `data/agent-sessions/{sessionId}.json`
- **Metadata**: `data/sessions-metadata.json`
- **SDK session ID**: Stored in metadata for conversation continuity

### Event System

- **Event emitter**: `apps/server/src/lib/events.ts`
- **WebSocket setup**: `apps/server/src/index.ts:440-543`
- **Client handler**: `apps/ui/src/lib/http-api-client.ts:748-890`

### Output & Logging

- **Agent output**: `.automaker/features/{featureId}/agent-output.md`
- **Logger utility**: `libs/utils/src/logger.ts`
- **Terminal service**: `apps/server/src/services/terminal-service.ts`

---

## Data Structures

### Feature (key fields)

```typescript
Feature {
  id, title, description, status,
  branchName,      // null = main, string = worktree
  model,           // claude-opus-4-5, etc.
  planningMode,    // 'skip' | 'lite' | 'spec' | 'full'
  planSpec: {
    status,        // 'pending'|'generating'|'generated'|'approved'|'rejected'
    tasks[],       // ParsedTask[]
    tasksCompleted, tasksTotal
  }
}
```

### Event Types

- `auto-mode:event` → `auto_mode_started`, `auto_mode_feature_start`, `auto_mode_feature_complete`, `auto_mode_idle`
- `agent:stream` → `started`, `stream`, `tool_use`, `complete`, `error`
- `feature:*` → `created`, `started`, `completed`, `progress`

---

## Dependency Resolution

**File**: `libs/dependency-resolver/src/resolver.ts`

Algorithm: Topological sort (Kahn's) + priority ordering

```
feature.dependencies[] → areDependenciesSatisfied() → loadPendingFeatures()
```

---

## Provider Support

| Provider | Model Prefix             | CLI/SDK          |
| -------- | ------------------------ | ---------------- |
| Claude   | `claude-*`, bare aliases | Claude Agent SDK |
| Cursor   | `cursor-*`               | cursor-agent CLI |
| Codex    | `codex-*`                | Codex CLI        |
| Gemini   | `gemini-*`               | gemini-cli       |

**Resolution**: `libs/model-resolver/src/index.ts`

---

## Quick Debug Paths

| Issue                  | Check First                                                |
| ---------------------- | ---------------------------------------------------------- |
| Feature not starting   | `auto-mode-service.ts` → `checkWorktreeCapacity()`         |
| Plan not generating    | `auto-mode-service.ts` → `getPlanningPromptPrefix()`       |
| Events not reaching UI | `lib/events.ts`, WebSocket in `index.ts:440+`              |
| Session not resuming   | `agent-service.ts` → `loadSession()`, check `sdkSessionId` |
| Wrong worktree         | `routes/worktree/routes/create.ts`, feature.branchName     |

---

## Environment Variables

| Var                          | Purpose                                 |
| ---------------------------- | --------------------------------------- |
| `ANTHROPIC_API_KEY`          | Claude API auth                         |
| `DATA_DIR`                   | Global data storage (default: `./data`) |
| `LOG_LEVEL`                  | Logger verbosity                        |
| `AUTOMAKER_DEBUG_RAW_OUTPUT` | Save raw agent output                   |
| `AUTOMAKER_MOCK_AGENT`       | CI testing mode                         |
