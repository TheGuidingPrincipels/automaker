# Multi-Agent Orchestration System Vision

> Living document for the multi-agent pipeline architecture
> Created: 2026-01-21 | Last Updated: 2026-01-21

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Vision](#core-vision)
3. [Current State Assessment](#current-state-assessment)
4. [Proposed Architecture](#proposed-architecture)
5. [Agent Pipeline Patterns](#agent-pipeline-patterns)
6. [Memory MCP Server Design](#memory-mcp-server-design)
7. [CLI Integration Strategy](#cli-integration-strategy)
8. [Frontend System Builder](#frontend-system-builder)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Open Questions](#open-questions)
11. [Research Areas](#research-areas)

---

## Executive Summary

### Goal

Build a **multi-agent orchestration system** that enables:

- Chaining specialized AI agents (using different CLI tools/models)
- Shared memory between agents via MCP server
- Sequential handoffs with context passing
- Blueprint-based system creation through the UI
- Subscription-based cost management (CLI-first approach)

### Key Principles

1. **CLI-First**: Use CLI tools (Codex, Gemini, OpenCode) to leverage subscription models
2. **Memory-Centric**: Agents communicate through a shared memory MCP server
3. **Blueprint-Driven**: Systems are created from reusable blueprints
4. **Event-Orchestrated**: Backend knows when agents finish and triggers next steps
5. **Model-Agnostic**: Any CLI or SDK can be integrated as a provider

---

## Core Vision

### The Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-AGENT PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   USER INPUT                                                                │
│   "Implement feature X with comprehensive testing"                          │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  AGENT 1: SCOUT (Codex CLI / OpenAI SDK)                            │  │
│   │  Role: Investigate codebase, gather information                     │  │
│   │  Model: codex-gpt-5.2 (free tier)                                   │  │
│   │  Output: → Memory MCP: findings, relevant files, patterns           │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                        │
│                     Backend detects completion                              │
│                                   │                                        │
│                                   ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  AGENT 2: PLANNER (Gemini CLI)                                      │  │
│   │  Role: Create detailed implementation plan from scout findings      │  │
│   │  Reads: Memory MCP ← scout findings                                 │  │
│   │  Output: → Memory MCP: sub-tasks, dependencies, approach            │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                        │
│                     Backend detects completion                              │
│                                   │                                        │
│                                   ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  AGENT 3: VALIDATOR (Claude Haiku)                                  │  │
│   │  Role: Validate plan, check for issues, suggest improvements        │  │
│   │  Reads: Memory MCP ← scout findings + plan                          │  │
│   │  Output: → Memory MCP: validated plan, concerns, recommendations    │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                        │
│                     Backend detects completion                              │
│                                   │                                        │
│                                   ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  AGENT 4: IMPLEMENTER (Claude Sonnet)                               │  │
│   │  Role: Execute the validated plan, write code                       │  │
│   │  Reads: Memory MCP ← all previous context                           │  │
│   │  Output: → Code changes + Memory MCP: implementation notes          │  │
│   └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                        │
│                                   ▼                                        │
│                            PIPELINE COMPLETE                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Specialization

| Agent Role  | Typical Model      | CLI Tool          | Responsibility                              |
| ----------- | ------------------ | ----------------- | ------------------------------------------- |
| Scout       | Codex, GPT-4       | Codex CLI, OpenAI | Codebase exploration, information gathering |
| Planner     | Gemini             | Gemini CLI        | Task decomposition, sub-plan creation       |
| Validator   | Claude Haiku       | Claude SDK        | Plan validation, risk assessment            |
| Implementer | Claude Sonnet/Opus | Claude SDK        | Code writing, implementation                |
| Reviewer    | Claude Opus        | Claude SDK        | Code review, quality assurance              |
| Tester      | Codex              | Codex CLI         | Test generation, validation                 |

---

## Current State Assessment

### What We Have

| Component                 | Status       | Location                         |
| ------------------------- | ------------ | -------------------------------- |
| Provider Factory          | ✅ Complete  | `apps/server/src/providers/`     |
| CLI Provider Base         | ✅ Complete  | `providers/cli-provider.ts`      |
| CustomAgent Types         | ✅ Complete  | `libs/types/src/custom-agent.ts` |
| System Types              | ✅ Complete  | `libs/types/src/system.ts`       |
| Workflow Step Types       | ✅ Complete  | `libs/types/src/system.ts`       |
| Event System              | ✅ Complete  | `apps/server/src/lib/events.ts`  |
| Auto-Mode Orchestration   | ✅ Complete  | `services/auto-mode-service.ts`  |
| Systems Service           | ⚠️ Stub      | `services/systems-service.ts`    |
| Workflow Execution        | ❌ Not Built | -                                |
| Memory MCP Server         | ❌ Not Built | -                                |
| Gemini CLI Provider       | ❌ Not Built | -                                |
| Inter-Agent Communication | ❌ Not Built | -                                |

### What We Need

1. **Workflow Execution Engine** - Interpret and execute workflow steps
2. **Memory MCP Server** - Shared context between agents
3. **Agent Completion Detection** - Know when each agent finishes
4. **Context Passing Mechanism** - Transfer findings between agents
5. **Gemini CLI Provider** - Integrate Gemini CLI
6. **System Builder UI** - Visual workflow creation

---

## Proposed Architecture

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     WORKFLOW ENGINE                                 │   │
│   │  - Interprets SystemWorkflowStep[]                                  │   │
│   │  - Handles: agent, conditional, parallel, sequential, loop          │   │
│   │  - Manages step state and transitions                               │   │
│   │  - Emits events for each step lifecycle                             │   │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                              │                                             │
│            ┌─────────────────┼─────────────────┐                           │
│            ▼                 ▼                 ▼                           │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                     │
│   │   Agent     │   │  Condition  │   │  Transform  │                     │
│   │   Executor  │   │  Evaluator  │   │  Processor  │                     │
│   └──────┬──────┘   └─────────────┘   └─────────────┘                     │
│          │                                                                 │
│          ▼                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     AGENT RUNNER                                    │   │
│   │  - Selects provider based on agent config                           │   │
│   │  - Injects memory context via system prompt                         │   │
│   │  - Streams execution to frontend                                    │   │
│   │  - Detects completion and captures output                           │   │
│   └───────────────────────────────────────────────────────────────────────┘ │
│          │                                                                 │
│          ▼                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     MEMORY MCP SERVER                               │   │
│   │  - Stores agent outputs keyed by step/agent ID                      │   │
│   │  - Provides retrieval for downstream agents                         │   │
│   │  - Supports structured and unstructured data                        │   │
│   │  - Optional: vector embeddings for semantic search                  │   │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Workflow Engine Design

```typescript
interface WorkflowEngine {
  // Execute a complete system
  execute(system: System, input: string): AsyncGenerator<WorkflowEvent>;

  // Execute a single step
  executeStep(step: SystemWorkflowStep, context: WorkflowContext): Promise<StepResult>;

  // Step executors by type
  executors: {
    agent: AgentStepExecutor;
    conditional: ConditionalStepExecutor;
    parallel: ParallelStepExecutor;
    sequential: SequentialStepExecutor;
    loop: LoopStepExecutor;
    human_review: HumanReviewStepExecutor;
    transform: TransformStepExecutor;
  };
}

interface WorkflowContext {
  systemId: string;
  executionId: string;
  variables: Map<string, unknown>; // outputVariable → value
  memory: MemoryMcpClient; // Access to memory MCP
  abortController: AbortController;
}

interface StepResult {
  stepId: string;
  status: 'completed' | 'failed' | 'skipped';
  output?: string;
  outputVariable?: string;
  error?: string;
  tokenUsage?: { input: number; output: number };
}
```

### Agent Step Executor

```typescript
class AgentStepExecutor {
  async execute(
    step: SystemWorkflowStep,
    context: WorkflowContext,
    agent: SystemAgent
  ): Promise<StepResult> {
    // 1. Resolve the CustomAgent if referenced
    const customAgent = agent.customAgentId
      ? await this.customAgentsService.get(agent.customAgentId)
      : null;

    // 2. Build prompt with variable interpolation
    const prompt = this.interpolateTemplate(step.inputTemplate, context.variables);

    // 3. Inject memory context into system prompt
    const memoryContext = await context.memory.getContextForAgent(step.agentId);
    const systemPrompt = this.buildSystemPrompt(
      customAgent?.systemPrompt,
      agent.systemPromptOverride,
      memoryContext
    );

    // 4. Determine model and provider
    const modelConfig = agent.modelConfigOverride ?? customAgent?.modelConfig;
    const provider = ProviderFactory.getProviderForModel(modelConfig.model);

    // 5. Execute agent
    const executeOptions: ExecuteOptions = {
      prompt,
      model: stripProviderPrefix(modelConfig.model),
      cwd: this.workingDirectory,
      systemPrompt,
      allowedTools: this.resolveTools(customAgent, agent),
      mcpServers: this.resolveMcpServers(customAgent),
      abortController: context.abortController,
    };

    let output = '';
    for await (const msg of provider.executeQuery(executeOptions)) {
      if (msg.type === 'assistant' && msg.message?.content) {
        for (const block of msg.message.content) {
          if (block.type === 'text') {
            output += block.text;
            this.emitProgress(step, block.text);
          }
        }
      }
    }

    // 6. Store output in memory
    if (step.outputVariable) {
      await context.memory.store({
        key: step.outputVariable,
        value: output,
        metadata: { stepId: step.id, agentId: step.agentId },
      });
      context.variables.set(step.outputVariable, output);
    }

    return { stepId: step.id, status: 'completed', output };
  }

  private interpolateTemplate(template: string, variables: Map<string, unknown>): string {
    // Replace {{variableName}} with actual values
    return template.replace(/\{\{(\w+)\}\}/g, (_, name) => {
      return String(variables.get(name) ?? `{{${name}}}`);
    });
  }
}
```

---

## Agent Pipeline Patterns

### Pattern 1: Sequential Pipeline

The simplest pattern - agents run one after another.

```typescript
const researchSystem: System = {
  name: 'Research Pipeline',
  agents: [
    { id: 'scout', role: 'researcher', modelConfig: { model: 'codex-gpt-5.2' } },
    { id: 'analyzer', role: 'analyzer', modelConfig: { model: 'gemini-2.0-flash' } },
    { id: 'summarizer', role: 'custom', modelConfig: { model: 'claude-haiku' } },
  ],
  workflow: [
    {
      id: 'step-1',
      type: 'agent',
      name: 'Scout Codebase',
      agentId: 'scout',
      inputTemplate: '{{system.input}}',
      outputVariable: 'scoutFindings',
    },
    {
      id: 'step-2',
      type: 'agent',
      name: 'Analyze Findings',
      agentId: 'analyzer',
      inputTemplate: 'Analyze these findings:\n\n{{scoutFindings}}',
      outputVariable: 'analysis',
    },
    {
      id: 'step-3',
      type: 'agent',
      name: 'Summarize',
      agentId: 'summarizer',
      inputTemplate: 'Summarize:\n\nFindings: {{scoutFindings}}\n\nAnalysis: {{analysis}}',
      outputVariable: 'summary',
    },
  ],
};
```

### Pattern 2: Parallel Exploration

Multiple agents explore different aspects simultaneously.

```typescript
workflow: [
  {
    id: 'parallel-exploration',
    type: 'parallel',
    name: 'Explore Multiple Areas',
    children: [
      {
        type: 'agent',
        agentId: 'security-scout',
        inputTemplate: 'Find security concerns in: {{system.input}}',
        outputVariable: 'securityFindings',
      },
      {
        type: 'agent',
        agentId: 'performance-scout',
        inputTemplate: 'Find performance issues in: {{system.input}}',
        outputVariable: 'performanceFindings',
      },
      {
        type: 'agent',
        agentId: 'architecture-scout',
        inputTemplate: 'Analyze architecture of: {{system.input}}',
        outputVariable: 'architectureFindings',
      },
    ],
  },
  {
    type: 'agent',
    agentId: 'synthesizer',
    inputTemplate: `Synthesize findings:
Security: {{securityFindings}}
Performance: {{performanceFindings}}
Architecture: {{architectureFindings}}`,
    outputVariable: 'synthesis',
  },
];
```

### Pattern 3: Conditional Branching

Different paths based on previous agent output.

```typescript
workflow: [
  {
    type: 'agent',
    agentId: 'classifier',
    inputTemplate: 'Classify this task: {{system.input}}',
    outputVariable: 'taskType',
  },
  {
    type: 'conditional',
    name: 'Route by Task Type',
    condition: {
      field: 'taskType',
      operator: 'contains',
      value: 'bug',
    },
    trueBranch: [
      { type: 'agent', agentId: 'bug-investigator', ... },
      { type: 'agent', agentId: 'fix-proposer', ... },
    ],
    falseBranch: [
      { type: 'agent', agentId: 'feature-planner', ... },
      { type: 'agent', agentId: 'implementer', ... },
    ],
  },
];
```

### Pattern 4: Iterative Refinement

Loop until quality threshold met.

```typescript
workflow: [
  {
    type: 'agent',
    agentId: 'implementer',
    inputTemplate: '{{system.input}}',
    outputVariable: 'implementation',
  },
  {
    type: 'loop',
    name: 'Refinement Loop',
    maxIterations: 3,
    children: [
      {
        type: 'agent',
        agentId: 'reviewer',
        inputTemplate: 'Review this implementation:\n\n{{implementation}}',
        outputVariable: 'reviewResult',
      },
      {
        type: 'conditional',
        condition: { field: 'reviewResult', operator: 'contains', value: 'APPROVED' },
        trueBranch: [], // Break loop
        falseBranch: [
          {
            type: 'agent',
            agentId: 'implementer',
            inputTemplate:
              'Improve based on feedback:\n\n{{reviewResult}}\n\nCurrent:\n{{implementation}}',
            outputVariable: 'implementation',
          },
        ],
      },
    ],
  },
];
```

---

## Memory MCP Server Design

### Purpose

Enable agents to share context and findings without passing everything through prompts.

### MCP Server Interface

```typescript
// Memory MCP Server Tools
tools: [
  {
    name: 'memory_store',
    description: 'Store information for later retrieval',
    parameters: {
      key: { type: 'string', description: 'Unique key for this entry' },
      value: { type: 'string', description: 'Content to store' },
      category: { type: 'string', description: 'Category: findings, plans, code, notes' },
      metadata: { type: 'object', description: 'Additional metadata' },
    },
  },
  {
    name: 'memory_retrieve',
    description: 'Retrieve stored information',
    parameters: {
      key: { type: 'string', description: 'Key to retrieve' },
    },
  },
  {
    name: 'memory_search',
    description: 'Search memory by query or category',
    parameters: {
      query: { type: 'string', description: 'Search query' },
      category: { type: 'string', description: 'Filter by category' },
      limit: { type: 'number', description: 'Max results' },
    },
  },
  {
    name: 'memory_list',
    description: 'List all entries by category',
    parameters: {
      category: { type: 'string' },
    },
  },
];
```

### Storage Backend Options

| Option              | Pros                       | Cons                   |
| ------------------- | -------------------------- | ---------------------- |
| File-based JSON     | Simple, no deps            | No vector search       |
| SQLite + FTS        | Full-text search, portable | No semantic search     |
| SQLite + embeddings | Semantic search, portable  | Embedding model needed |
| In-memory Map       | Fastest                    | Lost on restart        |

### Recommended: SQLite with FTS5

```typescript
// Memory store schema
CREATE TABLE memory_entries (
  id TEXT PRIMARY KEY,
  execution_id TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  category TEXT,
  metadata JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  UNIQUE(execution_id, key)
);

CREATE VIRTUAL TABLE memory_fts USING fts5(
  key, value, category,
  content='memory_entries',
  content_rowid='rowid'
);
```

### Integration with Agents

```typescript
// Agent system prompt injection
const memoryContext = await memoryMcp.search({
  query: 'previous findings',
  category: 'findings',
});

const systemPrompt = `
${baseSystemPrompt}

## Context from Previous Agents

${memoryContext.map((e) => `### ${e.key}\n${e.value}`).join('\n\n')}

## Your Task

Store your findings using the memory_store tool with category "findings".
`;
```

---

## CLI Integration Strategy

### Current CLI Providers

| Provider | CLI Tool   | Status             |
| -------- | ---------- | ------------------ |
| Codex    | `codex`    | ✅ Implemented     |
| Cursor   | `cursor`   | ✅ Implemented     |
| OpenCode | `opencode` | ✅ Implemented     |
| Gemini   | `gemini`   | ❌ Not Implemented |

### Adding Gemini CLI Provider

1. **Check Gemini CLI capabilities**:
   - Does it support JSONL output?
   - What authentication method?
   - What command-line interface?

2. **Implementation approach**:

```typescript
// apps/server/src/providers/gemini-provider.ts
import { CliProvider } from './cli-provider';

export class GeminiProvider extends CliProvider {
  getCliName(): string {
    return 'gemini';
  }

  getSpawnConfig(): CliSpawnConfig {
    return {
      windowsStrategy: 'npx',
      npxPackage: '@google/gemini-cli',
      commonPaths: {
        darwin: ['/usr/local/bin', '~/.local/bin'],
        linux: ['/usr/local/bin', '~/.local/bin'],
        win32: ['%LOCALAPPDATA%\\Gemini\\bin'],
      },
    };
  }

  buildCliArgs(options: ExecuteOptions): string[] {
    return [
      '--model',
      options.model,
      '--json',
      '-', // Read from stdin
    ];
  }

  normalizeEvent(event: unknown): ProviderMessage | null {
    // Convert Gemini CLI events to ProviderMessage format
    const e = event as GeminiEvent;
    if (e.type === 'content') {
      return {
        type: 'assistant',
        message: {
          role: 'assistant',
          content: [{ type: 'text', text: e.text }],
        },
      };
    }
    return null;
  }
}
```

3. **Register the provider**:

```typescript
// provider-factory.ts
registerProvider('gemini', {
  factory: () => new GeminiProvider(),
  canHandleModel: (model) => model.startsWith('gemini-'),
  priority: 4,
});
```

---

## Frontend System Builder

### Vision

A visual editor where users can:

1. Drag-and-drop agents onto a canvas
2. Connect agents with arrows to define flow
3. Configure each agent's model, tools, MCP servers
4. Define input/output variables
5. Add conditions and loops
6. Save as reusable blueprints

### Blueprint Concept

```typescript
interface SystemBlueprint {
  id: string;
  name: string;
  description: string;
  category: 'research' | 'development' | 'review' | 'testing' | 'custom';

  // Template agents (user fills in specifics)
  agentTemplates: {
    role: SystemAgentRole;
    suggestedModels: string[];
    suggestedTools: string[];
    promptTemplate: string;
  }[];

  // Workflow structure
  workflowTemplate: SystemWorkflowStep[];

  // Variables that user must provide
  requiredInputs: {
    name: string;
    description: string;
    type: 'string' | 'file' | 'selection';
  }[];
}
```

### Example Blueprint: "Feature Implementation"

```typescript
const featureImplementationBlueprint: SystemBlueprint = {
  id: 'feature-implementation',
  name: 'Feature Implementation Pipeline',
  description: 'Scout → Plan → Validate → Implement → Review',
  category: 'development',

  agentTemplates: [
    {
      role: 'researcher',
      suggestedModels: ['codex-gpt-5.2', 'opencode-deepseek'],
      suggestedTools: ['Read', 'Glob', 'Grep'],
      promptTemplate: 'Investigate the codebase to understand how to implement: {{feature}}',
    },
    {
      role: 'analyzer',
      suggestedModels: ['gemini-2.0-flash', 'claude-haiku'],
      suggestedTools: ['Read'],
      promptTemplate: 'Create an implementation plan based on:\n\n{{scoutFindings}}',
    },
    // ... more templates
  ],

  requiredInputs: [
    { name: 'feature', description: 'Feature to implement', type: 'string' },
    { name: 'testRequired', description: 'Include test generation', type: 'boolean' },
  ],
};
```

---

## Implementation Roadmap

### Phase 1: Foundation (2-3 weeks)

- [ ] Implement `WorkflowEngine` class
- [ ] Implement `AgentStepExecutor` for basic agent execution
- [ ] Implement variable interpolation (`{{variable}}` pattern)
- [ ] Add workflow-related events to event system
- [ ] Update `systems-service.run()` to use WorkflowEngine

### Phase 2: Memory MCP (1-2 weeks)

- [ ] Design Memory MCP server interface
- [ ] Implement SQLite + FTS5 backend
- [ ] Create MCP tools: store, retrieve, search, list
- [ ] Integrate with agent system prompts
- [ ] Add execution-scoped memory isolation

### Phase 3: Additional Step Types (1-2 weeks)

- [ ] Implement `ConditionalStepExecutor`
- [ ] Implement `ParallelStepExecutor`
- [ ] Implement `SequentialStepExecutor`
- [ ] Implement `LoopStepExecutor`
- [ ] Add `HumanReviewStepExecutor` with approval UI

### Phase 4: Gemini Integration (1 week)

- [ ] Research Gemini CLI interface
- [ ] Implement `GeminiProvider`
- [ ] Register in provider factory
- [ ] Add model definitions
- [ ] Test with sample workflows

### Phase 5: UI Enhancement (2-3 weeks)

- [ ] Design System Builder UI mockups
- [ ] Implement visual workflow canvas
- [ ] Add agent configuration panel
- [ ] Implement blueprint management
- [ ] Add execution monitoring view

### Phase 6: Production Hardening (1-2 weeks)

- [ ] Add comprehensive error handling
- [ ] Implement execution state persistence
- [ ] Add retry logic for failed steps
- [ ] Implement execution timeout handling
- [ ] Add token usage tracking and limits

---

## Open Questions

### Technical

1. **Memory persistence scope**: Per-execution only, or persist across executions?
2. **Parallel step failure handling**: Fail all if one fails, or continue others?
3. **Human review timeout**: How long to wait before auto-failing?
4. **Variable type safety**: Should we validate types between steps?

### Product

1. **Blueprint marketplace**: Should users share blueprints?
2. **Cost estimation**: Show estimated token cost before execution?
3. **Execution history**: How much detail to persist?
4. **Real-time collaboration**: Multiple users watching same execution?

### Integration

1. **Gemini CLI auth**: How does authentication work?
2. **Rate limits**: How to handle provider rate limits in pipelines?
3. **MCP server discovery**: How do agents find the memory MCP?

---

## Research Areas

### For Future Sessions

1. **Gemini CLI Investigation**
   - Command-line interface documentation
   - Streaming output format
   - Authentication mechanism
   - Available models and capabilities

2. **Agent Communication Patterns**
   - Blackboard pattern vs direct messaging
   - Event-driven vs polling handoffs
   - Structured vs unstructured context passing

3. **Workflow Engine Best Practices**
   - State machine libraries (XState, etc.)
   - Workflow orchestration patterns (Temporal, etc.)
   - Error recovery strategies

4. **Frontend Visual Workflow Builders**
   - React Flow library capabilities
   - Other workflow canvas libraries
   - Blueprint serialization formats

---

## Appendix: Type Definitions Reference

### From `libs/types/src/system.ts`

```typescript
// Already exists and is well-designed
interface System { ... }
interface SystemAgent { ... }
interface SystemWorkflowStep { ... }
interface WorkflowStepCondition { ... }
interface SystemExecution { ... }
interface SystemStepExecution { ... }
```

### Proposed New Types

```typescript
// Workflow engine types
interface WorkflowEngine { ... }
interface WorkflowContext { ... }
interface StepResult { ... }

// Memory MCP types
interface MemoryEntry {
  id: string;
  executionId: string;
  key: string;
  value: string;
  category: 'findings' | 'plans' | 'code' | 'notes' | 'custom';
  metadata?: Record<string, unknown>;
  createdAt: string;
}

interface MemorySearchOptions {
  query?: string;
  category?: string;
  limit?: number;
  executionId?: string;
}

// Blueprint types
interface SystemBlueprint { ... }
interface AgentTemplate { ... }
interface BlueprintInput { ... }
```

---

## Document History

| Date       | Author                     | Changes                  |
| ---------- | -------------------------- | ------------------------ |
| 2026-01-21 | Claude (via investigation) | Initial document created |

---

> This is a living document. Update as investigation continues and decisions are made.
