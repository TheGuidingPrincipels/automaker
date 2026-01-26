# Subscription-Based Multi-Agent CLI Architecture

> [!IMPORTANT]
> **Core Objective**: Enable a system of **dedicated agents** (Planner, Verifier, Tester, Coder) that execute purely via **CLI tools** (Claude, Codex, Gemini) to leverage existing user subscriptions and **avoid direct API costs**.

## 1. Executive Summary

We are building an orchestration layer that sits _on top_ of local CLI tools. Instead of the `server` making API calls to OpenAI/Anthropic/Google directly (which incurs per-token costs), the server will spawn local CLI processes (`codex exec`, `claude`, `gemini prompt`) that are authenticated via the user's personal accounts.

This system will allow:

- **Zero API Cost**: Usage bills to the user's flat-rate subscriptions (ChatGPT Plus, Gemini Advanced, Claude Pro).
- **Dedicated Agents**: Specialized "personas" (e.g., "Plan Verifier") with unique system prompts and tools.
- **Hot-Swappable Models**: Easy reconfiguration of which agent uses which CLI via the UI.
- **Automated Orchestration**: A pipeline that flows from Plan -> Verification -> Testing -> Implementation automatically.

---

## 2. The Vision: "The Dream System"

### 2.1 The 6-Agent Pipeline

We aim to implement a sophisticated assembly line where each agent performs a specific role using a dedicated CLI model best suited for the task.

1.  **Master Planner (Agent A)**
    - **Role**: Analyzes the User Request + Project Context. Creates the `MASTER_PLAN.md`.
    - **Recommended CLI**: `claude` (Anthropic Opus) for high-level reasoning.
    - **Output**: High-level strategy and feature breakdown.

2.  **Sub-Planner (Agent B)**
    - **Role**: Takes one item from the Master Plan. Breaks it down into atomic, executable steps (Context-Window safe).
    - **Recommended CLI**: `claude` or `gemini` (Pro 1.5) for large context handling.
    - **Output**: `DETAILED_PLAN_FEATURE_X.md`.

3.  **Plan Verifier (Agent C)**
    - **Role**: adversarial reviewer. Checks the detailed plan for logic gaps, missed dependencies, or security risks.
    - **Recommended CLI**: `gemini` (Flash/Pro) or `gpt-4o` (Codex) for fast critique.
    - **Output**: `VERIFICATION_REPORT.md` (Pass/Fail).

4.  **Test Writer (Agent D)**
    - **Role**: Writes the Red/Fail tests based _only_ on the verified plan.
    - **Recommended CLI**: `codex` (GPT-5/4) for precise code generation.
    - **Output**: `tests/feature_x.test.ts` + `TEST_SPECS.md`.

5.  **Code Implementer (Agent E)**
    - **Role**: Writes the implementation code to pass the tests.
    - **Recommended CLI**: `claude` (Sonnet 3.5) or `codex` (GPT-4o) for coding capability.
    - **Output**: Modified source files.

6.  **Reviewer/Integrator (Agent F)**
    - **Role**: Runs the tests, checks for linting errors, and summarizes the cycle.
    - **Recommended CLI**: `gemini` (Fast) for quick summary.
    - **Output**: Update to `MEMORY.md`.

---

## 3. Technical Architecture

### 3.1 The Orchestrator Core (`MultiAgentService`)

A new service layer that manages the _flow_ between agents. It does not run prompts itself; it coordinates them.

- **State Machine**: Tracks the status of the current "Job" (e.g., `PLANNING`, `VERIFYING`, `BLOCKED_ON_USER`).
- **Functionality**:
  1.  **Job Trigger**: Receives a `job_request`.
  2.  **Profile Lookup**: Reads `agent-profiles.json` to find the correct agent configuration for the current step.
  3.  **Prompt Assembly**: Combines the _Agent System Prompt_ + _Task Input_ (e.g., content of `PLAN.md`).
  4.  **CLI Dispatch**: Calls `CliProvider` to spawn the process.
  5.  **Artifact Monitoring**: Watches for the creation of specific output files (defined in the profile).
  6.  **Loop/Transition**: decisions logic (If `VERIFICATION_REPORT` says "Approved" -> Start `TestWriter`).

### 3.2 The CLI Provider Layer (`CliProvider`)

A unified abstraction for all CLI interaction. This is the "Driver" layer.

- **`CliProvider` (Base Class)**: Handles process spawning, stream parsing, timeout management, and signal handling.
- **`GeminiProvider`**: Wraps `gemini prompt`. Auth verification via `~/.gemini/credentials`.
- **`ClaudeCliProvider`**: Wraps `claude` (Claude Code). Auth verification via `~/.anthropic/credentials`.
- **`CodexProvider`**: Wraps `codex exec`. Auth verification via `~/.config/codex`.

**Tooling Bridge**:

- _Problem_: CLIs running in a child process cannot "natively" call a JavaScript function in our server (like `sendTelegramMessage`).
- _Solution_: **Standardized Tool Output**.
  - Agents are instructed (via System Prompt) to output tool calls in a specific XML/JSON format:
    ```xml
    <tool_call>
        <name>ask_user</name>
        <params>{"question": "..."}</params>
    </tool_call>
    ```
  - The `CliProvider` **stream parser** detects this pattern.
  - It **pauses** the CLI (or captures the output and doesn't feed it back yet).
  - It executes the actual server-side code (e.g., sends the Telegram message).
  - It feeds the result back to the CLI's `stdin` (simulating the tool output).

### 3.3 The Configuration Layer (Frontend Editable)

All agent behaviors are defined in `agent-profiles.json`. The Frontend will have a "Workflow Editor" to modify this JSON visually.

**Config Schema (`agent-profiles.json`)**:

```json
{
  "agents": {
    "plan_verifier": {
      "name": "Plan Verifier",
      "description": "Reviews detailed plans for logical errors.",
      "model_config": {
        "provider": "gemini",
        "model_id": "gemini-1.5-pro",
        "cli_path": "gemini"
      },
      "system_prompt_path": ".automaker/prompts/plan_verifier.md",
      "tools": ["read_file", "write_file", "ask_user"],
      "input_artifact": "DETAILED_PLAN.md",
      "output_artifact": "VERIFICATION_REPORT.md",
      "next_steps": {
        "success": "test_writer",
        "failure": "master_planner"
      }
    }
  }
}
```

- **Frontend Capabilities**:
  - Edit System Prompts (Markdown Editor).
  - Switch Models (Dropdown of detected CLIs).
  - Toggle Tools (Checkbox list).
  - Define "Next Steps" (Graph/Flowchart connection).

### 3.4 The Memory Layer (Write-Access)

Leverages `memory-loader.ts`.

- **Input**: When an agent starts, `MultiAgentService` uses `loadRelevantMemory()` to inject relevant past learnings into the prompt.
- **Output**: When an agent finishes, it can optionally emit a `<learning>` block or write to `learning_output.md`.
- **Processing**: The server parses this and uses `appendLearning()` (with file locking) to safely update `docs/memory/`.

---

## 4. User Interaction & Feedback Loop (Telegram)

To allow the autonomous system to run 24/7 but still get user input when stuck, we integrate a dedicated "User Comms" channel.

### 4.1 The `ask_user` Tool

A server-side tool available to all agents.

- **Trigger**: Agent encounters ambiguity or needs approval (e.g., "Verification failed, need clarification on Requirement A").
- **Action**: Agent outputs tool call: `ask_user("Should I prioritize performance or readability?")`.

### 4.2 The Interaction Flow

1.  **Block**: The Orchestrator detects the `ask_user` call. It sets the Job Status to `BLOCKED_ON_USER`.
2.  **Notify**:
    - **Server**: Sends a POST request to the configured Telegram Bot API.
    - **User Device**: User receives a Telegram message: _"🤖 Plan Verifier needs help: Should I prioritize performance or readability?"_
3.  **Response**:
    - User replies on Telegram: _"Performance, strictly."_
    - **Server**: Webhook receives the message. Matches it to the blocked Job ID.
4.  **Resume**:
    - Orchestrator feeds _"Performance, strictly"_ back into the CLI process as the Tool Result.
    - Job Status returns to `RUNNING`.
    - Agent generates the next tokens based on the answer.

---

## 5. Implementation Roadmap

### Phase 1: Core Infrastructure (The Foundation)

1.  **`CliProvider` Extraction**: Refactor `CodexProvider` into specific `CliProvider`, `GeminiProvider`, `ClaudeCliProvider` classes.
2.  **`MultiAgentService`**: Implement the basic state machine (Start -> Run CLI -> Finish).
3.  **`agent-profiles.json`**: Create the initial schema.

### Phase 2: Orchestration Logic (The Flow)

1.  **Artifact Handlers**: Implement the logic to watch file systems for inputs/outputs.
2.  **Pipeline Logic**: Implement the linked-list logic (Agent A -> Agent B).
3.  **Memory Hook**: Connect `loadRelevantMemory` to the generic agent prompt builder.

### Phase 3: Advanced Features (The "Dream")

1.  **Frontend Editor**: Build the React views to edit `agent-profiles.json`.
2.  **Telegram Bot**: Set up the `bot-service.ts` and the `ask_user` tool bridge.
3.  **Full 6-Agent Pipeline**: Write the 6 specific system prompts and verify the full end-to-end flow.

## 6. Verification Plan

- **CLI Persistence**: Validated (Login once, run forever).
- **Process Isolation**: Validated (Spawn/Kill works).
- **Orchestration**: Will be verified by a "Hello World" chain (Agent A writes "Hello", Agent B adds " World").
