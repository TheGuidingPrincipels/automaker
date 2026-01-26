# Unified Agent Orchestration Framework

> Simple, reusable framework for chaining agents (SDK + CLI)

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION FRAMEWORK OVERVIEW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   USER: "Implement feature X"                                               │
│              │                                                              │
│              ▼                                                              │
│   ┌─────────────────────┐                                                   │
│   │  PIPELINE EXECUTOR  │  ← The "conductor" that manages everything        │
│   └──────────┬──────────┘                                                   │
│              │                                                              │
│              │ runs steps one by one (or in parallel)                       │
│              ▼                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  STEP 1: Scout (Codex CLI)                                          │   │
│   │  ├─ Runs the agent                                                  │   │
│   │  ├─ Waits for stream to end                                         │   │
│   │  ├─ Checks: success or failure?                                     │   │
│   │  └─ Stores output in context                                        │   │
│   └───────────────────────────────┬─────────────────────────────────────┘   │
│                                   │                                         │
│              [SUCCESS] ───────────┴───────────── [FAILURE]                  │
│                  │                                    │                     │
│                  ▼                                    ▼                     │
│   ┌────────────────────────┐           ┌────────────────────────┐          │
│   │  STEP 2: Planner       │           │  RECOVERY AGENT        │          │
│   │  (Gemini CLI)          │           │  (Claude Haiku)        │          │
│   │  Reads scout's output  │           │  Diagnoses failure     │          │
│   └────────────────────────┘           └────────────────────────┘          │
│              │                                                              │
│              ▼                                                              │
│   ┌────────────────────────┐                                                │
│   │  STEP 3: Implementer   │                                                │
│   │  (Claude Sonnet)       │                                                │
│   │  Reads plan            │                                                │
│   └────────────────────────┘                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### 1. The Pipeline

A **pipeline** is a list of steps that run in order. Each step is an agent.

```typescript
interface Pipeline {
  id: string;
  name: string;
  steps: PipelineStep[];
  onFailure?: 'stop' | 'continue' | 'recovery'; // What to do when a step fails
  recoveryAgent?: AgentConfig; // Agent to call on failure
}
```

### 2. The Step

A **step** defines one agent's work:

```typescript
interface PipelineStep {
  id: string;
  name: string;
  agent: AgentConfig; // Which agent to run
  input: InputConfig; // Where does input come from?
  output: OutputConfig; // Where does output go?
  onSuccess?: string; // Next step ID on success
  onFailure?: string; // Next step ID on failure (self-healing)
  timeout?: number; // Max time for this step
  retries?: number; // How many times to retry on failure
}
```

### 3. The Agent Config

An **agent** can be SDK-based OR CLI-based - the framework doesn't care:

```typescript
interface AgentConfig {
  // Identity
  name: string;
  model: string; // e.g., "claude-sonnet", "codex-gpt-5.2", "gemini-2.0-flash"

  // Behavior
  systemPrompt: string; // What this agent does
  tools?: string[]; // Which tools it can use
  mcpServers?: string[]; // Which MCP servers it can access

  // Limits
  maxTurns?: number; // Max back-and-forth with tools
  thinkingLevel?: string; // For Claude: extended thinking budget
  reasoningEffort?: string; // For Codex: reasoning level
}
```

### 4. The Context (Shared Memory)

Steps communicate through a **context object** - like a shared whiteboard:

```typescript
interface PipelineContext {
  // The original user request
  input: string;

  // Output from each completed step
  stepOutputs: Map<string, StepOutput>;

  // Any variables for template interpolation
  variables: Map<string, unknown>;

  // Working directory
  cwd: string;

  // Abort controller for cancellation
  abortController: AbortController;
}

interface StepOutput {
  stepId: string;
  agentName: string;
  success: boolean;
  output: string; // The agent's response text
  error?: string; // If failed, why?
  tokenUsage?: TokenUsage; // How many tokens used
  duration: number; // How long it took (ms)
}
```

---

## The Pipeline Executor

This is the "brain" that runs everything:

```typescript
class PipelineExecutor {
  private providers: ProviderFactory;
  private events: EventEmitter;

  /**
   * Execute a complete pipeline
   */
  async *execute(
    pipeline: Pipeline,
    initialInput: string,
    cwd: string
  ): AsyncGenerator<PipelineEvent> {
    // 1. Initialize context (the shared whiteboard)
    const context: PipelineContext = {
      input: initialInput,
      stepOutputs: new Map(),
      variables: new Map([['input', initialInput]]),
      cwd,
      abortController: new AbortController(),
    };

    yield { type: 'pipeline_started', pipelineId: pipeline.id };

    // 2. Run through steps
    let currentStepId = pipeline.steps[0]?.id;

    while (currentStepId) {
      const step = pipeline.steps.find((s) => s.id === currentStepId);
      if (!step) break;

      yield { type: 'step_started', stepId: step.id, stepName: step.name };

      try {
        // 3. Execute the step
        const result = await this.executeStep(step, context);

        // 4. Store output in context
        context.stepOutputs.set(step.id, result);
        if (step.output.variable) {
          context.variables.set(step.output.variable, result.output);
        }

        yield {
          type: 'step_completed',
          stepId: step.id,
          success: result.success,
          output: result.output,
        };

        // 5. Determine next step
        if (result.success) {
          currentStepId = step.onSuccess ?? this.getNextStep(pipeline, step.id);
        } else {
          // Handle failure
          if (step.onFailure) {
            // Self-healing: go to recovery step
            currentStepId = step.onFailure;
          } else if (pipeline.onFailure === 'continue') {
            // Skip and continue
            currentStepId = this.getNextStep(pipeline, step.id);
          } else if (pipeline.onFailure === 'recovery' && pipeline.recoveryAgent) {
            // Run global recovery agent
            await this.runRecoveryAgent(pipeline.recoveryAgent, result.error, context);
            currentStepId = null; // Stop after recovery
          } else {
            // Stop the pipeline
            currentStepId = null;
          }
        }
      } catch (error) {
        yield { type: 'step_error', stepId: step.id, error: error.message };
        currentStepId = null;
      }
    }

    yield { type: 'pipeline_completed', success: true };
  }

  /**
   * Execute a single step
   */
  private async executeStep(step: PipelineStep, context: PipelineContext): Promise<StepOutput> {
    const startTime = Date.now();

    // 1. Build the prompt (with variable substitution)
    const prompt = this.buildPrompt(step.input, context);

    // 2. Build system prompt (with context injection)
    const systemPrompt = this.buildSystemPrompt(step.agent, context);

    // 3. Get the right provider (SDK or CLI)
    const provider = this.providers.getProviderForModel(step.agent.model);
    const bareModel = stripProviderPrefix(step.agent.model);

    // 4. Build execute options
    const options: ExecuteOptions = {
      prompt,
      model: bareModel,
      cwd: context.cwd,
      systemPrompt,
      allowedTools: step.agent.tools,
      mcpServers: this.resolveMcpServers(step.agent.mcpServers),
      abortController: context.abortController,
      maxTurns: step.agent.maxTurns,
      thinkingLevel: step.agent.thinkingLevel,
      reasoningEffort: step.agent.reasoningEffort,
    };

    // 5. Run the agent and collect output
    let output = '';
    let success = true;
    let error: string | undefined;

    try {
      // THE KEY PART: Stream the agent's response
      for await (const msg of provider.executeQuery(options)) {
        // Accumulate text from assistant messages
        if (msg.type === 'assistant' && msg.message?.content) {
          for (const block of msg.message.content) {
            if (block.type === 'text') {
              output += block.text;
              // Emit progress for real-time UI updates
              this.events.emit('step_progress', {
                stepId: step.id,
                text: block.text,
              });
            }
          }
        }

        // Check for success signal
        if (msg.type === 'result' && msg.subtype === 'success') {
          success = true;
        }

        // Check for error signal
        if (msg.type === 'error') {
          success = false;
          error = msg.error;
        }
      }
      // Stream ended - agent is done!
    } catch (err) {
      success = false;
      error = err.message;
    }

    return {
      stepId: step.id,
      agentName: step.agent.name,
      success,
      output,
      error,
      duration: Date.now() - startTime,
    };
  }

  /**
   * Build prompt with variable substitution
   * Replaces {{variableName}} with actual values
   */
  private buildPrompt(inputConfig: InputConfig, context: PipelineContext): string {
    let prompt = inputConfig.template;

    // Replace {{variable}} patterns
    prompt = prompt.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
      if (varName === 'input') {
        return context.input;
      }
      const value = context.variables.get(varName);
      return value !== undefined ? String(value) : match;
    });

    return prompt;
  }

  /**
   * Build system prompt with optional context from previous steps
   */
  private buildSystemPrompt(agent: AgentConfig, context: PipelineContext): string {
    let systemPrompt = agent.systemPrompt;

    // Optionally inject previous step outputs
    if (context.stepOutputs.size > 0) {
      systemPrompt += '\n\n## Context from Previous Steps\n\n';
      for (const [stepId, output] of context.stepOutputs) {
        if (output.success) {
          systemPrompt += `### ${output.agentName}\n${output.output}\n\n`;
        }
      }
    }

    return systemPrompt;
  }
}
```

---

## How This Unified Framework Works

### The Magic: Both SDK and CLI look the same to the executor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        THE UNIFIED INTERFACE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   PipelineExecutor says: "Run this agent with this prompt"                  │
│              │                                                              │
│              ▼                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     provider.executeQuery(options)                  │   │
│   │                                                                     │   │
│   │   Returns: AsyncGenerator<ProviderMessage>                          │   │
│   │                                                                     │   │
│   │   The executor doesn't care HOW messages are generated.             │   │
│   │   It just iterates until the stream ends.                           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│              │                                                              │
│     ┌────────┴────────┐                                                     │
│     ▼                 ▼                                                     │
│  ┌──────────┐    ┌──────────┐                                               │
│  │ Claude   │    │ CLI      │                                               │
│  │ Provider │    │ Provider │                                               │
│  └────┬─────┘    └────┬─────┘                                               │
│       │               │                                                     │
│       ▼               ▼                                                     │
│   SDK library    spawn process                                              │
│   yields msgs    parse JSONL                                                │
│                  yield msgs                                                 │
│                                                                             │
│   BOTH end up yielding the SAME format:                                     │
│   {type: 'assistant', message: {content: [{type: 'text', text: '...'}]}}   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Key Insight

**Both SDK and CLI providers return an `AsyncGenerator<ProviderMessage>`**

This means the executor can use the exact same code:

```typescript
for await (const msg of provider.executeQuery(options)) {
  // Handle message
}
// When this loop exits, the agent is DONE
```

The provider handles all the complexity:

- **Claude SDK**: Wraps the SDK's native stream
- **CLI Provider**: Spawns process, parses JSONL, yields normalized messages

---

## Self-Healing Flow

When a step fails, we can automatically run a recovery agent:

```
Step 1 (Scout) fails
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│  RECOVERY AGENT (Claude Haiku)                            │
│                                                           │
│  System Prompt:                                           │
│  "An agent failed. Diagnose the issue and suggest fixes." │
│                                                           │
│  Input:                                                   │
│  "Step 'Scout' failed with error: {error}                 │
│   Original task was: {input}                              │
│   Agent config: {agentConfig}"                            │
│                                                           │
│  Output:                                                  │
│  "The error occurred because... Try these alternatives:   │
│   1. Use a different model                                │
│   2. Simplify the task                                    │
│   3. ..."                                                 │
└───────────────────────────────────────────────────────────┘
        │
        ▼
  Pipeline can:
  - Stop and report diagnosis
  - Retry with modified parameters
  - Skip to next step with partial context
```

---

## Example: Feature Implementation Pipeline

```typescript
const featurePipeline: Pipeline = {
  id: 'feature-implementation',
  name: 'Feature Implementation',
  onFailure: 'recovery',

  recoveryAgent: {
    name: 'Recovery Specialist',
    model: 'claude-haiku',
    systemPrompt: 'Diagnose why the previous agent failed and suggest fixes.',
  },

  steps: [
    // Step 1: Scout the codebase (use cheap CLI model)
    {
      id: 'scout',
      name: 'Scout Codebase',
      agent: {
        name: 'Scout',
        model: 'codex-gpt-5.2', // Free tier CLI
        systemPrompt: `You are a code scout. Investigate the codebase to understand:
- Where similar features are implemented
- What patterns are used
- What files would need to change

Report your findings clearly.`,
        tools: ['Read', 'Glob', 'Grep'],
      },
      input: {
        template: 'Investigate how to implement: {{input}}',
      },
      output: {
        variable: 'scoutFindings',
      },
      onSuccess: 'planner',
      onFailure: 'scout-recovery', // Self-healing
    },

    // Step 1b: Recovery for scout (if it fails)
    {
      id: 'scout-recovery',
      name: 'Scout Recovery',
      agent: {
        name: 'Scout Recovery',
        model: 'claude-haiku',
        systemPrompt: 'The scout agent failed. Try a simpler investigation approach.',
        tools: ['Read', 'Glob'],
      },
      input: {
        template: 'Simple investigation for: {{input}}',
      },
      output: {
        variable: 'scoutFindings',
      },
      onSuccess: 'planner',
    },

    // Step 2: Create a plan (use Gemini for planning)
    {
      id: 'planner',
      name: 'Create Plan',
      agent: {
        name: 'Planner',
        model: 'gemini-2.0-flash', // Good at planning
        systemPrompt: `You are a technical planner. Based on the scout's findings,
create a detailed implementation plan with:
- Specific files to modify
- Step-by-step changes
- Potential risks`,
      },
      input: {
        template: `Create an implementation plan for: {{input}}

Scout's findings:
{{scoutFindings}}`,
      },
      output: {
        variable: 'plan',
      },
      onSuccess: 'validator',
    },

    // Step 3: Validate the plan (use Claude for reasoning)
    {
      id: 'validator',
      name: 'Validate Plan',
      agent: {
        name: 'Validator',
        model: 'claude-haiku',
        systemPrompt: `You are a plan validator. Check for:
- Missing steps
- Potential bugs
- Security issues
- Performance concerns

Either approve the plan or list required changes.`,
      },
      input: {
        template: `Validate this plan:
{{plan}}

For task: {{input}}`,
      },
      output: {
        variable: 'validation',
      },
      onSuccess: 'implementer',
    },

    // Step 4: Implement (use Claude Sonnet for coding)
    {
      id: 'implementer',
      name: 'Implement',
      agent: {
        name: 'Implementer',
        model: 'claude-sonnet', // Best for coding
        systemPrompt: `You are an expert developer. Implement the validated plan.
Write clean, well-documented code.`,
        tools: ['Read', 'Write', 'Edit', 'Bash'],
        maxTurns: 50,
      },
      input: {
        template: `Implement this feature: {{input}}

Plan:
{{plan}}

Validation notes:
{{validation}}`,
      },
      output: {
        variable: 'implementation',
      },
    },
  ],
};
```

---

## Pipeline Events (for UI updates)

```typescript
type PipelineEvent =
  | { type: 'pipeline_started'; pipelineId: string }
  | { type: 'step_started'; stepId: string; stepName: string }
  | { type: 'step_progress'; stepId: string; text: string }
  | { type: 'step_completed'; stepId: string; success: boolean; output: string }
  | { type: 'step_error'; stepId: string; error: string }
  | { type: 'recovery_started'; agentName: string }
  | { type: 'pipeline_completed'; success: boolean };
```

These events stream to the frontend via WebSocket, so users see real-time progress.

---

## Summary: Why This Design Works

| Feature                  | How It's Achieved                                               |
| ------------------------ | --------------------------------------------------------------- |
| **Mixed SDK + CLI**      | Both implement same `AsyncGenerator<ProviderMessage>` interface |
| **Completion detection** | `for await` loop exits when stream ends                         |
| **Success/failure**      | Check `msg.type === 'result'` vs `msg.type === 'error'`         |
| **Context passing**      | Shared `PipelineContext` with `variables` Map                   |
| **Self-healing**         | `onFailure` property points to recovery step                    |
| **Real-time updates**    | Events emitted during streaming                                 |
| **Reusable framework**   | Same executor works with any agent config                       |

---

## Next Steps

1. **Implement PipelineExecutor class** in `apps/server/src/services/`
2. **Add Gemini CLI provider** following existing patterns
3. **Create Memory MCP server** for richer context sharing
4. **Build Pipeline Builder UI** for visual pipeline creation
