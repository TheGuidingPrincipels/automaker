# Current Execution Architecture Guide

> Generated from comprehensive codebase investigation on 2026-01-21

This document details how plan/feature execution currently works in Automaker, including model selection, CLI integration, and the orchestration mechanisms.

## Table of Contents

1. [Overview](#overview)
2. [Feature Execution Flow](#feature-execution-flow)
3. [Provider Architecture](#provider-architecture)
4. [CLI Integration Patterns](#cli-integration-patterns)
5. [SYSTEMS Feature (Multi-Agent Infrastructure)](#systems-feature)
6. [Event System](#event-system)
7. [Auto-Mode Orchestration](#auto-mode-orchestration)
8. [Key Files Reference](#key-files-reference)

---

## Overview

Automaker is an autonomous AI development studio that executes features (tasks) through AI agents. The architecture supports:

- **Multiple AI Providers**: Claude (via SDK), Codex CLI, Cursor CLI, OpenCode CLI
- **Isolated Execution**: Each feature runs in a git worktree
- **Real-time Streaming**: WebSocket-based event streaming to UI
- **Dependency Resolution**: Topological sort ensures proper execution order
- **SYSTEMS Infrastructure**: Types defined for multi-agent workflows (execution NOT implemented)

---

## Feature Execution Flow

### 1. Feature Creation

```
Frontend                    Server                      Storage
   │                          │                            │
   │  POST /api/features/create                            │
   ├─────────────────────────>│                            │
   │                          │  FeatureLoader.create()    │
   │                          ├───────────────────────────>│
   │                          │                            │
   │                          │  Write feature.json        │
   │                          │  .automaker/features/{id}/ │
   │<─────────────────────────┤                            │
```

**Storage Location**: `.automaker/features/{featureId}/feature.json`

**Key Fields**:

```typescript
interface Feature {
  id: string;
  title?: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'verified';
  dependencies?: string[];
  branchName?: string;
  model?: string;
  planSpec?: PlanSpec;
}
```

### 2. Execution Triggers

| Trigger    | Endpoint                             | Use Case                         |
| ---------- | ------------------------------------ | -------------------------------- |
| Manual Run | `POST /api/auto-mode/run-feature`    | Single feature execution         |
| Auto Mode  | `POST /api/auto-mode/start`          | Continuous background processing |
| Resume     | `POST /api/auto-mode/resume-feature` | Continue interrupted execution   |

### 3. Execution Pipeline

```
executeFeature() flow:
1. Add to runningFeatures Map
2. Load feature & check for existing context
3. Determine work directory (main repo or worktree)
4. Update status: 'in_progress'
5. Load context files (CLAUDE.md, project context)
6. Build prompt from feature description
7. runAgent() - execute via provider
8. Execute pipeline steps (if configured)
9. Update status: 'verified' or 'waiting_approval'
```

**File**: `apps/server/src/services/auto-mode-service.ts` (lines 1065-1401)

---

## Provider Architecture

### Provider Factory Pattern

The system routes models to appropriate providers via a registry-based factory:

```typescript
// Registration pattern
registerProvider('claude', {
  factory: () => new ClaudeProvider(),
  canHandleModel: (model) => model.startsWith('claude-'),
  priority: 0, // Default fallback
});

registerProvider('codex', {
  factory: () => new CodexProvider(),
  canHandleModel: isCodexModel,
  priority: 5,
});

registerProvider('cursor', {
  factory: () => new CursorProvider(),
  canHandleModel: isCursorModel,
  priority: 10, // Checked first
});

registerProvider('opencode', {
  factory: () => new OpencodeProvider(),
  canHandleModel: isOpencodeModel,
  priority: 3,
});
```

**File**: `apps/server/src/providers/provider-factory.ts`

### Model Routing

```
Input: "codex-gpt-5.2"
  │
  ▼
ProviderFactory.getProviderForModel()
  │
  ├─ Check providers by priority (descending)
  ├─ cursor (priority 10): canHandleModel? No
  ├─ codex (priority 5): canHandleModel? Yes ✓
  │
  ▼
Returns: CodexProvider instance

stripProviderPrefix("codex-gpt-5.2") → "gpt-5.2"
```

### Provider Interface

```typescript
abstract class BaseProvider {
  abstract getName(): string;
  abstract executeQuery(options: ExecuteOptions): AsyncGenerator<ProviderMessage>;
  abstract detectInstallation(): Promise<InstallationStatus>;
  abstract getAvailableModels(): ModelDefinition[];
}
```

### ExecuteOptions

```typescript
interface ExecuteOptions {
  prompt: string | ContentBlock[];
  model: string; // Bare model ID (no prefix)
  cwd: string;
  systemPrompt?: string;
  maxTurns?: number;
  allowedTools?: string[];
  mcpServers?: Record<string, McpServerConfig>;
  abortController?: AbortController;
  conversationHistory?: ConversationMessage[];
  thinkingLevel?: ThinkingLevel; // Claude extended thinking
  reasoningEffort?: ReasoningEffort; // Codex reasoning
  agents?: Record<string, AgentDefinition>; // Subagents
}
```

### ProviderMessage Format

All providers yield the same message format (matches Claude SDK):

```typescript
interface ProviderMessage {
  type: 'assistant' | 'user' | 'error' | 'result';
  subtype?: 'success' | 'error' | 'error_max_turns';
  session_id?: string;
  message?: { role: string; content: ContentBlock[] };
  result?: string;
  error?: string;
}
```

---

## CLI Integration Patterns

### CliProvider Base Class

For CLI-based AI tools (Codex, Cursor, OpenCode), there's an abstract base class:

```typescript
abstract class CliProvider extends BaseProvider {
  abstract getCliName(): string;
  abstract getSpawnConfig(): CliSpawnConfig;
  abstract buildCliArgs(options: ExecuteOptions): string[];
  abstract normalizeEvent(event: unknown): ProviderMessage | null;
}
```

**File**: `apps/server/src/providers/cli-provider.ts`

### Spawn Configuration

```typescript
interface CliSpawnConfig {
  windowsStrategy: 'wsl' | 'npx' | 'direct' | 'cmd';
  npxPackage?: string;
  wslDistribution?: string;
  commonPaths: Record<string, string[]>; // Platform -> paths
}
```

### JSONL Streaming

CLI tools that output JSON lines use the streaming utility:

```typescript
import { spawnJSONLProcess } from '@automaker/platform';

for await (const event of spawnJSONLProcess({
  command: 'codex',
  args: ['--json', '-'],
  cwd: workingDirectory,
  stdinData: prompt,
  abortController,
})) {
  yield normalizeEvent(event);
}
```

**File**: `libs/platform/src/subprocess.ts`

### Adding a New CLI Provider

1. Create `apps/server/src/providers/{name}-provider.ts`
2. Extend `CliProvider` base class
3. Implement:
   - `getCliName()`: CLI executable name
   - `getSpawnConfig()`: Platform paths and strategies
   - `buildCliArgs()`: Convert ExecuteOptions to CLI args
   - `normalizeEvent()`: Convert CLI output to ProviderMessage
4. Register in `provider-factory.ts`:
   ```typescript
   registerProvider('gemini', {
     factory: () => new GeminiProvider(),
     canHandleModel: isGeminiModel,
     priority: 4,
   });
   ```
5. Add prefix utilities in `libs/types/src/provider-utils.ts`

---

## SYSTEMS Feature

> **CRITICAL**: The SYSTEMS types and UI exist, but **execution is NOT implemented**.
> `systems-service.run()` returns a placeholder.

### CustomAgent Type

```typescript
interface CustomAgent {
  id: string;
  name: string;
  description: string;
  systemPrompt: string;
  status: 'draft' | 'active' | 'archived';
  modelConfig: {
    model: ModelId;
    thinkingLevel?: ThinkingLevel;
    reasoningEffort?: ReasoningEffort;
    maxTokens?: number;
    temperature?: number;
  };
  tools: CustomAgentTool[];
  mcpServers: CustomAgentMCPServer[];
}
```

**File**: `libs/types/src/custom-agent.ts`

### System Type

```typescript
interface System {
  id: string;
  name: string;
  description: string;
  agents: SystemAgent[]; // Agents in this system
  workflow: SystemWorkflowStep[]; // Workflow definition
  variables?: Record<string, unknown>; // System-level state
}

interface SystemAgent {
  id: string;
  customAgentId?: string; // Reference to CustomAgent
  name: string;
  role:
    | 'orchestrator'
    | 'researcher'
    | 'analyzer'
    | 'implementer'
    | 'reviewer'
    | 'validator'
    | 'custom';
  systemPromptOverride?: string;
  modelConfigOverride?: CustomAgentModelConfig;
  order?: number; // Execution order
}
```

**File**: `libs/types/src/system.ts`

### Workflow Step Types

```typescript
type WorkflowStepType =
  | 'agent' // Execute an agent
  | 'conditional' // Branch based on condition
  | 'parallel' // Execute multiple steps concurrently
  | 'sequential' // Execute steps in order
  | 'loop' // Repeat until condition
  | 'human_review' // Wait for approval
  | 'transform'; // Transform data between steps

interface SystemWorkflowStep {
  id: string;
  type: WorkflowStepType;
  name: string;
  agentId?: string;
  inputTemplate?: string; // e.g., "Analyze: {{researcher.output}}"
  outputVariable?: string; // Name for downstream steps
  condition?: WorkflowStepCondition;
  children?: SystemWorkflowStep[]; // For parallel/sequential/loop
  trueBranch?: SystemWorkflowStep[];
  falseBranch?: SystemWorkflowStep[];
}
```

### Variable Interpolation Pattern

The type system supports variable interpolation between steps:

```
Step 1 (researcher):
  inputTemplate: "{{system.input}}"
  outputVariable: "findings"

Step 2 (analyzer):
  inputTemplate: "Analyze these:\n\n{{findings}}"
  outputVariable: "analysis"

Step 3 (summarizer):
  inputTemplate: "Summarize:\n\nFindings: {{findings}}\nAnalysis: {{analysis}}"
```

### Built-in Systems (Defined but Not Executable)

| System                   | Agents                                                     | Purpose              |
| ------------------------ | ---------------------------------------------------------- | -------------------- |
| Research System          | Researcher → Analyzer → Summarizer                         | Multi-agent research |
| Code Review System       | Security Reviewer → Performance Analyst → Quality Checker  | Code review pipeline |
| Feature Planning System  | Requirements Analyzer → Technical Architect → Task Planner | Feature planning     |
| Bug Investigation System | Bug Reproducer → Root Cause Analyst → Fix Proposer         | Bug diagnosis        |

**File**: `apps/server/src/services/systems-service.ts`

### Current Execution (Placeholder)

```typescript
async run(input: RunSystemInput): Promise<SystemExecution> {
  // TODO: Implement actual system execution with agent coordination
  // For now, return a mock execution
  execution.status = 'completed';
  execution.output = `Placeholder output. Real execution coming soon.`;
  return execution;
}
```

---

## Event System

### Event Emitter Pattern

```typescript
// libs/events.ts
function createEventEmitter(): EventEmitter {
  const subscribers = new Set<EventCallback>();
  return {
    emit(type: EventType, payload: unknown) {
      for (const callback of subscribers) {
        callback(type, payload);
      }
    },
    subscribe(callback: EventCallback) {
      subscribers.add(callback);
      return () => subscribers.delete(callback);
    },
  };
}
```

### WebSocket Broadcasting

All events are broadcast to all connected WebSocket clients:

```typescript
// index.ts
wss.on('connection', (ws) => {
  const unsubscribe = events.subscribe((type, payload) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type, payload }));
    }
  });
  ws.on('close', () => unsubscribe());
});
```

### Event Types

| Category     | Events                                                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Auto-Mode    | `auto_mode_started`, `auto_mode_stopped`, `auto_mode_idle`, `auto_mode_feature_start`, `auto_mode_feature_complete`, `auto_mode_progress`, `auto_mode_error` |
| Pipeline     | `pipeline_step_started`, `pipeline_step_complete`                                                                                                            |
| Planning     | `plan_approval_required`, `plan_approved`, `plan_rejected`                                                                                                   |
| Agent Runner | `started`, `message`, `stream`, `tool_use`, `complete`, `error`                                                                                              |

### Event Hook Service

Post-completion callbacks for extensibility:

```typescript
// Subscribes to events and triggers hooks
class EventHookService {
  handleAutoModeEvent(payload) {
    switch (payload.type) {
      case 'auto_mode_feature_complete':
        this.executeHooksForTrigger(payload.passes ? 'feature_success' : 'feature_error', context);
        break;
    }
  }
}
```

**Supported triggers**: `feature_created`, `feature_success`, `feature_error`, `auto_mode_complete`, `auto_mode_error`

---

## Auto-Mode Orchestration

### Polling-Based Auto-Loop

```
while (isRunning && !aborted) {
    1. Count running features for this worktree
    2. If at capacity → sleep 5s, continue
    3. Load pending features (with dependency resolution)
    4. If no pending → emit idle, sleep 10s, continue
    5. Find next unstarted feature
    6. Execute in background
    7. Sleep 2s
}
```

**File**: `apps/server/src/services/auto-mode-service.ts` (lines 635-729)

### Dependency Resolution

Uses Kahn's algorithm for topological sort with priority awareness:

```typescript
const { orderedFeatures, circularDependencies, missingDependencies } =
  resolveDependencies(pendingFeatures);
```

**File**: `libs/dependency-resolver/src/resolver.ts`

### Concurrency Control

- Per-project/worktree concurrency limits
- Default: `DEFAULT_MAX_CONCURRENCY` from settings
- Tracks running features in memory: `Map<featureId, RunningFeature>`

### Failure Handling

```typescript
const CONSECUTIVE_FAILURE_THRESHOLD = 3;
const FAILURE_WINDOW_MS = 60000; // 1 minute

// Auto-pause after 3 failures in 1 minute
if (failures.length >= CONSECUTIVE_FAILURE_THRESHOLD) {
  emitAutoModeEvent('auto_mode_paused_failures', { failureCount });
  stopAutoLoopForProject(projectPath, branchName);
}
```

### State Persistence

Execution state saved for server restart recovery:

```json
{
  "version": 1,
  "autoLoopWasRunning": true,
  "maxConcurrency": 3,
  "projectPath": "/path/to/project",
  "branchName": null,
  "runningFeatureIds": ["feature-123"],
  "savedAt": "2026-01-21T12:00:00Z"
}
```

**Location**: `.automaker/execution-state.json`

---

## Key Files Reference

### Core Services

| File                                                | Purpose                              |
| --------------------------------------------------- | ------------------------------------ |
| `apps/server/src/services/auto-mode-service.ts`     | Main orchestration (4500+ lines)     |
| `apps/server/src/services/agent-service.ts`         | Chat/Agent Runner execution          |
| `apps/server/src/services/feature-loader.ts`        | Feature CRUD operations              |
| `apps/server/src/services/systems-service.ts`       | SYSTEMS CRUD (execution placeholder) |
| `apps/server/src/services/custom-agents-service.ts` | CustomAgent CRUD                     |

### Provider Layer

| File                                             | Purpose                       |
| ------------------------------------------------ | ----------------------------- |
| `apps/server/src/providers/base-provider.ts`     | Abstract provider interface   |
| `apps/server/src/providers/provider-factory.ts`  | Provider registry and routing |
| `apps/server/src/providers/cli-provider.ts`      | Base class for CLI providers  |
| `apps/server/src/providers/claude-provider.ts`   | Claude SDK integration        |
| `apps/server/src/providers/codex-provider.ts`    | Codex CLI integration         |
| `apps/server/src/providers/cursor-provider.ts`   | Cursor CLI integration        |
| `apps/server/src/providers/opencode-provider.ts` | OpenCode CLI integration      |

### Types

| File                             | Purpose                   |
| -------------------------------- | ------------------------- |
| `libs/types/src/feature.ts`      | Feature type definitions  |
| `libs/types/src/custom-agent.ts` | CustomAgent types         |
| `libs/types/src/system.ts`       | System and workflow types |
| `libs/types/src/provider.ts`     | Provider interfaces       |
| `libs/types/src/event.ts`        | Event type definitions    |

### Infrastructure

| File                                       | Purpose                |
| ------------------------------------------ | ---------------------- |
| `libs/platform/src/subprocess.ts`          | CLI spawning utilities |
| `libs/dependency-resolver/src/resolver.ts` | Topological sort       |
| `libs/model-resolver/src/resolver.ts`      | Model alias resolution |
| `apps/server/src/lib/events.ts`            | Event emitter factory  |
| `apps/server/src/lib/sdk-options.ts`       | SDK options builder    |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AUTOMAKER ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────┐     ┌─────────────────────────┐   │
│  │   Frontend  │────>│   REST API      │────>│     Auto-Mode Service   │   │
│  │  (React UI) │<────│   /api/*        │     │   (Orchestration)       │   │
│  └──────┬──────┘     └─────────────────┘     └───────────┬─────────────┘   │
│         │                                                │                 │
│         │ WebSocket                                      │                 │
│         │                                                ▼                 │
│  ┌──────▼──────┐     ┌─────────────────┐     ┌─────────────────────────┐   │
│  │   Event     │<────│   EventEmitter  │<────│    Feature Execution    │   │
│  │   Stream    │     │   (pub-sub)     │     │                         │   │
│  └─────────────┘     └─────────────────┘     └───────────┬─────────────┘   │
│                                                          │                 │
│                      ┌───────────────────────────────────┼─────────────┐   │
│                      │         Provider Factory          │             │   │
│                      │    (Model → Provider routing)     │             │   │
│                      └───────────────────────────────────┼─────────────┘   │
│                                                          │                 │
│         ┌────────────────┬──────────────┬───────────────┼───────────┐     │
│         ▼                ▼              ▼               ▼           │     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│     │
│  │   Claude     │ │   Codex      │ │   Cursor     │ │  OpenCode    ││     │
│  │   Provider   │ │   Provider   │ │   Provider   │ │  Provider    ││     │
│  │   (SDK)      │ │   (CLI)      │ │   (CLI)      │ │  (CLI)       ││     │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘│     │
│         │                │              │               │           │     │
│         ▼                ▼              ▼               ▼           │     │
│  ┌──────────────────────────────────────────────────────────────────┘     │
│  │                        AI MODELS / CLIs                                │
│  │  Claude API    Codex CLI     Cursor CLI     OpenCode CLI              │
│  └────────────────────────────────────────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Next Steps for Multi-Agent Orchestration

The SYSTEMS types provide a foundation, but execution needs implementation. Key areas:

1. **Implement `systems-service.run()`** - Execute workflow steps
2. **Add Memory/Context Sharing** - MCP server or shared state mechanism
3. **Implement Variable Interpolation** - `{{step.output}}` pattern
4. **Add Gemini CLI Provider** - Follow CLI provider pattern
5. **Create Workflow Step Executor** - Handle conditional, parallel, loop steps
6. **Add Inter-Agent Events** - `system:step-completed`, `system:agent-handoff`

See `docs/architecture/multi-agent-orchestration-vision.md` for the full design proposal.
