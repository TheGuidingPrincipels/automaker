# Plan Audit Report

## Findings (ordered by severity)

### Critical

- **F1 (Critical)** — Cleanup system prompts lack an explicit “never echo secrets” rule.
  - What: The plan requires prompts to avoid quoting credentials/tokens/keys in `suggestion_reason` / signal details. The current mode prompts do not include that instruction.
  - Impact (ties to Pi): Risk of leaking sensitive content into API responses/UI; violates P3 and P21.
  - Evidence:
    - Prompt module contains the mode prompts but no explicit secrets rule: `2.ai-library/src/sdk/prompts/cleanup_mode.py:25`.
    - A direct search shows no “secret/credentials/token/api key” guidance in the prompt rules (only a non-guidance mention of “keywords”): `2.ai-library/src/sdk/prompts/cleanup_mode.py:128`.
  - Suggested fix: Add a consistent “Never Echo Secrets” rule to each mode system prompt; optionally add server-side sanitization in `2.ai-library/src/sdk/client.py:365` to redact secret-like strings if the model echoes them.

### High

- **F2 (High)** — Prompt factory and prompt builder silently fall back to Balanced mode.
  - What: `get_cleanup_system_prompt` returns Balanced for unknown `mode`, and the user prompt builder also falls back to Balanced for unknown `cleanup_mode`.
  - Impact (ties to Pi): Violates the plan’s “NO silent fallbacks” rule and weakens the “invalid cleanup_mode must be rejected” criterion (P3, P4, P22).
  - Evidence: `2.ai-library/src/sdk/prompts/cleanup_mode.py:318` and `2.ai-library/src/sdk/prompts/cleanup_mode.py:392`.
  - Suggested fix: Replace `.get(..., CLEANUP_SYSTEM_PROMPT_BALANCED)` fallbacks with explicit `raise ValueError(...)`, or remove fallback entirely if upstream validation guarantees correctness.

- **F3 (High)** — Mode confidence thresholds are defined but not enforced server-side (recommended guardrail missing).
  - What: `CleanupModeSetting.confidence_threshold` exists, but `ClaudeCodeClient.generate_cleanup_plan` does not use it to downgrade low-confidence discard suggestions.
  - Impact (ties to Pi): Mode semantics can drift; plan’s “safety + determinism” guardrail is not met (P11, P1).
  - Evidence: threshold exists at `2.ai-library/src/models/cleanup_mode_setting.py:18`, but item construction applies no threshold check at `2.ai-library/src/sdk/client.py:365`.
  - Suggested fix: In `2.ai-library/src/sdk/client.py`, if the model suggests `discard` but `confidence < cleanup_mode.confidence_threshold`, downgrade to `keep` and explicitly annotate `suggestion_reason` (no silent behavior changes).

- **F4 (High)** — `apps/ui` cannot import `KLCleanupMode` from the `@automaker/types` that `tsc` resolves in this environment.
  - What: UI code imports `KLCleanupMode`, but the `@automaker/types` package resolved by `apps/ui`’s TypeScript compiler does not export it.
  - Impact (ties to Pi): Blocks UI compilation of the cleanup-mode plumbing (P13, P15, P16).
  - Evidence:
    - Import site: `apps/ui/src/lib/knowledge-library-api.ts:13` (line 21).
    - `npm run typecheck --workspace=apps/ui` fails with: `apps/ui/src/lib/knowledge-library-api.ts(21,3): error TS2305: Module '"@automaker/types"' has no exported member 'KLCleanupMode'.`
    - The installed package being picked up by `tsc` contains no `KLCleanupMode`: `/Users/ruben/Documents/GitHub/automaker/node_modules/@automaker/types/dist/index.d.ts` (no matches for `KLCleanupMode`).
  - Suggested fix: Ensure `apps/ui` resolves `@automaker/types` to this worktree’s package (reinstall/link from this worktree and rebuild `@automaker/types`), then re-run `npm run typecheck --workspace=apps/ui`.

### Medium

- **F5 (Medium)** — REST invalid `cleanup_mode` returns 400 instead of plan’s 422 validation behavior.
  - What: REST endpoint validates `cleanup_mode` manually and raises `HTTP_400_BAD_REQUEST` for invalid values.
  - Impact (ties to Pi): Contract mismatch vs plan (“REST 422 / WebSocket error event”) (P6, P22).
  - Evidence: `2.ai-library/src/api/routes/sessions.py:304` and `2.ai-library/src/api/routes/sessions.py:333`.
  - Suggested fix: Type the query param as `CleanupModeSetting` in the endpoint signature (FastAPI validation → 422) or return 422 explicitly.

- **F6 (Medium)** — `CleanupModeSetting` name collision/inconsistent semantics between Python and TypeScript settings.
  - What: Python `CleanupModeSetting` is the 3-mode selector; `libs/types/src/settings.ts` defines `CleanupModeSetting` with `manual|auto` and different thresholds.
  - Impact (ties to Pi): Confusing API surface; increases risk of importing the wrong concept/thresholds when wiring UI/backend (P1).
  - Evidence: `2.ai-library/src/models/cleanup_mode_setting.py:6` vs `libs/types/src/settings.ts:117`.
  - Suggested fix: Rename the TS type (e.g., `KLCleanupAutomationSetting`) or move it into a clearly scoped module; align naming so “cleanup mode” (prompt behavior) and “automation mode” (auto-accept policy) are distinct.

### Low

- **F7 (Low)** — Prompt content preview limit increased to 800 chars, which may reduce token efficiency.
  - What: Prompt builder uses `CONTENT_PREVIEW_LIMIT = 800`.
  - Impact (ties to Pi): Higher token usage per block; could undermine the plan’s “token-efficient design” intent (P4, P23).
  - Evidence: `2.ai-library/src/sdk/prompts/cleanup_mode.py:325`.
  - Suggested fix: Lower to 300 (as in the plan example) or make configurable per mode/session.

## Plan Coverage Matrix

- **P1 — Create `CleanupModeSetting` enum (Python) with thresholds + descriptions**
  - Status: Implemented
  - Evidence: `2.ai-library/src/models/cleanup_mode_setting.py:6`
  - Notes: Includes `confidence_threshold` and `description` properties.

- **P2 — Export `CleanupModeSetting` from models package**
  - Status: Implemented
  - Evidence: `2.ai-library/src/models/__init__.py:7`
  - Notes: Exported via `__all__`.

- **P3 — Three mode-specific cleanup prompts + token-efficient prompt factory (no silent fallbacks)**
  - Status: Partial
  - Evidence: `2.ai-library/src/sdk/prompts/cleanup_mode.py:25`
  - Notes: Prompts exist, but factory/builder include silent fallbacks (F2) and no explicit “never echo secrets” rule (F1).

- **P4 — User prompt builder includes mode context + bounded previews**
  - Status: Partial
  - Evidence: `2.ai-library/src/sdk/prompts/cleanup_mode.py:333`
  - Notes: Builder includes mode context, but uses silent fallback (F2) and preview limit is 800 chars (F7).

- **P5 — API schemas include `cleanup_mode` + `signals_detected` (small payloads)**
  - Status: Implemented
  - Evidence: `2.ai-library/src/api/schemas.py:174`
  - Notes: Uses `content_preview` only; signals are exposed via `signals_detected`.

- **P6 — REST cleanup generation accepts `cleanup_mode` and rejects invalid values (422)**
  - Status: Partial
  - Evidence: `2.ai-library/src/api/routes/sessions.py:304`
  - Notes: Invalid values are rejected, but as HTTP 400 (F5), not 422.

- **P7 — WebSocket `generate_cleanup` accepts `cleanup_mode` and rejects invalid values with error event**
  - Status: Implemented
  - Evidence: `2.ai-library/src/api/routes/sessions.py:1016`
  - Notes: Covered by WebSocket tests.

- **P8 — Session manager threads `cleanup_mode` through streaming generation**
  - Status: Implemented
  - Evidence: `2.ai-library/src/session/manager.py:386`
  - Notes: Passed to `PlanningFlow.generate_cleanup_plan`.

- **P9 — PlanningFlow threads `cleanup_mode` to SDK + includes mode in event payloads**
  - Status: Implemented
  - Evidence: `2.ai-library/src/conversation/flow.py:68`
  - Notes: Covered by `2.ai-library/tests/test_planning_flow.py:273`.

- **P10 — SDK client uses selected mode prompt + returns plan with `cleanup_mode` + signals**
  - Status: Implemented
  - Evidence: `2.ai-library/src/sdk/client.py:291`
  - Notes: Parses signals from AI response under `signals` and maps into `signals_detected`.

- **P11 — Server-side confidence threshold guardrail (downgrade low-confidence discard)**
  - Status: Missing
  - Evidence: `2.ai-library/src/models/cleanup_mode_setting.py:18`
  - Notes: Threshold exists but is not applied in `2.ai-library/src/sdk/client.py:365` (F3).

- **P12 — Cleanup models include `cleanup_mode`, confidence, and `signals_detected`**
  - Status: Implemented
  - Evidence: `2.ai-library/src/models/cleanup_plan.py:75`
  - Notes: Model also includes AI-analysis tracking + duplicate detection.

- **P13 — Shared TS types include cleanup mode + signals + WS payload typing**
  - Status: Partial
  - Evidence: `libs/types/src/knowledge-library.ts:130`
  - Notes: Source types are present; however `apps/ui`’s current typecheck resolves an `@automaker/types` without `KLCleanupMode` (F4).

- **P14 — UI store persists `cleanupMode` and exposes setter**
  - Status: Implemented
  - Evidence: `apps/ui/src/store/knowledge-library-store.ts:356`
  - Notes: Includes persist migration and utility config.

- **P15 — UI API client passes `cleanup_mode` in REST request**
  - Status: Implemented
  - Evidence: `apps/ui/src/lib/knowledge-library-api.ts:329`
  - Notes: Uses `params: { use_ai, cleanup_mode }`.

- **P16 — Query hook exposes cleanup-mode option**
  - Status: Implemented
  - Evidence: `apps/ui/src/hooks/queries/use-knowledge-library.ts:248`
  - Notes: Mutation accepts `{ cleanupMode }`.

- **P17 — Cleanup mode selector UI exists and is shown before session start**
  - Status: Implemented
  - Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/components/control-row.tsx:168`
  - Notes: Selector appears when a file is staged (pre-session).

- **P18 — Signal badges UI exists and is rendered on cleanup item cards**
  - Status: Implemented
  - Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx:219`
  - Notes: Badges render when `signals_detected` is present.

- **P19 — Workflow passes `cleanup_mode` via WebSocket (start + regeneration)**
  - Status: Implemented
  - Evidence: `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:563`
  - Notes: Included in `startSession` and question-answer regeneration.

- **P20 — Acceptance: selected mode persists across refresh**
  - Status: Implemented
  - Evidence: `apps/ui/src/store/knowledge-library-store.ts:356`
  - Notes: Persist `partialize` includes `cleanupMode`.

- **P21 — Acceptance: signals are detected and displayed in UI**
  - Status: Partial
  - Evidence: `2.ai-library/src/api/schemas.py:193`
  - Notes: Data model + UI display are wired; actual detection quality depends on AI outputs and prompt guidance (F1), so end-to-end behavior is not fully verifiable here.

- **P22 — Acceptance: invalid cleanup_mode rejected (REST 422 / WebSocket error) with no silent fallback**
  - Status: Partial
  - Evidence: `2.ai-library/src/api/routes/sessions.py:333`
  - Notes: WebSocket rejection works; REST uses 400 not 422 (F5); prompt factory includes silent fallback (F2).

- **P23 — Acceptance: only selected prompt sent (~800–900 tokens; not ~2400)**
  - Status: Unverifiable
  - Evidence: `2.ai-library/src/sdk/client.py:330`
  - Notes: Code selects a single system prompt, but token counts and actual runtime payload sizes require measurement in a live run.

- **P24 — Prompt quality tests (meeting notes/partial todos/reference docs behave per mode)**
  - Status: Unverifiable
  - Evidence: `2.ai-library/src/sdk/prompts/cleanup_mode.py:25`
  - Notes: Requires running the model against fixture documents.

## Code Structure & Logic Review (Baseline Targets)

### Created files (baseline)

- **`2.ai-library/src/models/cleanup_mode_setting.py`**
  - Purpose: Defines the three user-selectable cleanup modes and their thresholds/descriptions.
  - Key components: `CleanupModeSetting` enum + `confidence_threshold`/`description` properties (`2.ai-library/src/models/cleanup_mode_setting.py:6`).
  - Integration points: Imported by API routes and planning chain (`2.ai-library/src/api/routes/sessions.py:318`, `2.ai-library/src/conversation/flow.py:18`).
  - Risks/flaws: Threshold is currently not enforced server-side (F3).

- **`apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-mode-selector.tsx`**
  - Purpose: UI popover selector for Conservative/Balanced/Aggressive mode.
  - Key components: `CleanupModeSelector` component + option list from store config (`apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-mode-selector.tsx:32`).
  - Integration points: Rendered in control row before session start (`apps/ui/src/components/views/knowledge-library/components/input-mode/components/control-row.tsx:168`).
  - Risks/flaws: Depends on store-exported config (`apps/ui/src/store/knowledge-library-store.ts:414`); ensure this aligns with backend thresholds.

- **`apps/ui/src/components/views/knowledge-library/components/input-mode/components/signal-badges.tsx`**
  - Purpose: Visualize detected AI signals as badges with tooltips.
  - Key components: `SignalBadges` and `CompactSignalBadges` + `signalTypeStyles` mapping (`apps/ui/src/components/views/knowledge-library/components/input-mode/components/signal-badges.tsx:39`).
  - Integration points: Rendered on cleanup item cards (`apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx:219`).
  - Risks/flaws: Mapping includes signal types not currently enumerated in backend (falls back to default style); repeated `TooltipProvider` per badge may be heavier than needed.

### Modified files (baseline)

- **`2.ai-library/src/api/routes/sessions.py`** (source)
  - Purpose: REST + WebSocket endpoints for sessions, including cleanup generation.
  - Key components: REST `POST /{session_id}/cleanup/generate` now accepts `cleanup_mode` and converts to enum (`2.ai-library/src/api/routes/sessions.py:304`).
  - Integration points: Calls `SessionManager.generate_cleanup_plan_with_ai(..., cleanup_mode=...)` (`2.ai-library/src/api/routes/sessions.py:340`) and mirrors logic in WebSocket stream handler (`2.ai-library/src/api/routes/sessions.py:1016`).
  - Risks/flaws: REST invalid mode uses 400 not 422 (F5).

- **`2.ai-library/src/api/schemas.py`** (schema)
  - Purpose: API response models for blocks, cleanup plans, routing plans.
  - Key components: `DetectedSignalResponse` + `signals_detected` on `CleanupItemResponse` (`2.ai-library/src/api/schemas.py:163`), `cleanup_mode` on `CleanupPlanResponse` (`2.ai-library/src/api/schemas.py:227`).
  - Integration points: Returned by REST endpoints and used by UI query hooks/types.
  - Risks/flaws: Uses `getattr` for backward compatibility; ensure callers rely on `cleanup_mode` consistently.

- **`2.ai-library/src/conversation/flow.py`** (source)
  - Purpose: Orchestrates cleanup + routing generation with async event streaming.
  - Key components: `generate_cleanup_plan(..., cleanup_mode=...)` threads mode and emits it in event data (`2.ai-library/src/conversation/flow.py:68`).
  - Integration points: Called by `SessionManager.generate_cleanup_plan_with_ai` (`2.ai-library/src/session/manager.py:420`).
  - Risks/flaws: Exceptions collapse into an `ERROR` PlanEvent; consider preserving structured error codes.

- **`2.ai-library/src/models/__init__.py`** (source)
  - Purpose: Central export surface for model package.
  - Key components: Exports `CleanupModeSetting` (`2.ai-library/src/models/__init__.py:7`).
  - Integration points: Used across API, planning, and SDK layers.
  - Risks/flaws: None.

- **`2.ai-library/src/models/cleanup_plan.py`** (source)
  - Purpose: Cleanup plan + item models used through the backend and serialized to UI.
  - Key components: `DetectedSignal`, `signals_detected` on `CleanupItem` (`2.ai-library/src/models/cleanup_plan.py:75`), `cleanup_mode` on `CleanupPlan` (`2.ai-library/src/models/cleanup_plan.py:115`).
  - Integration points: Parsed from AI response in SDK client and exposed via API schemas.
  - Risks/flaws: `CleanupDisposition` fields are typed as `str`; consider using the Enum type consistently to tighten validation.

- **`2.ai-library/src/sdk/client.py`** (source)
  - Purpose: Claude Code SDK wrapper that generates cleanup/routing plans and normalizes model output.
  - Key components: `generate_cleanup_plan(..., cleanup_mode=CleanupModeSetting)` (`2.ai-library/src/sdk/client.py:291`), selects system prompt per mode (`2.ai-library/src/sdk/client.py:330`), parses per-block `signals` into `signals_detected` (`2.ai-library/src/sdk/client.py:375`), and sets `cleanup_mode=cleanup_mode.value` in the returned plan (`2.ai-library/src/sdk/client.py:422`).
  - Integration points: Called from PlanningFlow; output becomes API payload.
  - Risks/flaws: Mode thresholds aren’t enforced server-side (F3); model may echo secrets without prompt guidance (F1).

- **`2.ai-library/src/sdk/prompts/__init__.py`** (source)
  - Purpose: Export prompt constants/builders for SDK use.
  - Key components: Exports mode-specific cleanup system prompts and factory (`2.ai-library/src/sdk/prompts/__init__.py:3`).
  - Integration points: Imported by SDK client.
  - Risks/flaws: None.

- **`2.ai-library/src/sdk/prompts/cleanup_mode.py`** (source)
  - Purpose: Mode-specific system prompts + prompt builder for cleanup.
  - Key components: Three system prompts, `get_cleanup_system_prompt` (`2.ai-library/src/sdk/prompts/cleanup_mode.py:296`), `CONTENT_PREVIEW_LIMIT = 800` (`2.ai-library/src/sdk/prompts/cleanup_mode.py:325`), `build_cleanup_prompt` (`2.ai-library/src/sdk/prompts/cleanup_mode.py:333`).
  - Integration points: Used by SDK client to build prompt and pick system prompt for the selected mode.
  - Risks/flaws: Silent fallbacks to Balanced (F2); no explicit “never echo secrets” rule (F1); preview limit may inflate token usage (F7).

- **`2.ai-library/src/session/manager.py`** (source)
  - Purpose: Session lifecycle and orchestration API consumed by REST/WebSocket routes.
  - Key components: `generate_cleanup_plan_with_ai(..., cleanup_mode=...)` (`2.ai-library/src/session/manager.py:386`) passes mode into PlanningFlow.
  - Integration points: Called from REST and WebSocket routes.
  - Risks/flaws: None apparent; preserves async streaming pattern.

- **`2.ai-library/tests/test_planning_flow.py`** (test)
  - Purpose: Contract tests for PlanningFlow streaming and parameter threading.
  - Key components: Tests that `cleanup_mode` is passed and included in event payloads (`2.ai-library/tests/test_planning_flow.py:273`).
  - Integration points: Validates planning chain behavior.
  - Risks/flaws: Not runnable here (pytest missing).

- **`2.ai-library/tests/test_websocket_stream.py`** (test)
  - Purpose: WebSocket stream contract tests.
  - Key components: Tests cleanup_mode accepted/defaulted/rejected (`2.ai-library/tests/test_websocket_stream.py:120`).
  - Integration points: Validates WS command contract.
  - Risks/flaws: Not runnable here (pytest missing).

- **`apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx`** (source)
  - Purpose: Cleanup review UI for keep/discard decisions.
  - Key components: Renders `SignalBadges` and various AI-analysis indicators (`apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx:219`).
  - Integration points: Uses `signals_detected` from API response types.
  - Risks/flaws: Signals depend on AI output quality and prompt guidance (F1).

- **`apps/ui/src/components/views/knowledge-library/components/input-mode/components/control-row.tsx`** (source)
  - Purpose: Pre-session and active-session control strip (upload/start + mode toggle).
  - Key components: Shows `CleanupModeSelector` pre-session (`apps/ui/src/components/views/knowledge-library/components/input-mode/components/control-row.tsx:168`) and reads/writes `cleanupMode` from store (`apps/ui/src/components/views/knowledge-library/components/input-mode/components/control-row.tsx:65`).
  - Integration points: Drives the selected cleanup mode used by `useSessionWorkflow`.
  - Risks/flaws: None obvious.

- **`apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts`** (source)
  - Purpose: Orchestrates the end-to-end workflow and WebSocket command stream.
  - Key components: Includes `{ cleanup_mode: cleanupMode }` in `generate_cleanup` WebSocket payload (`apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:585`) and regeneration after answering questions (`apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:651`).
  - Integration points: Must match backend WS message parsing (`2.ai-library/src/api/routes/sessions.py:1018`).
  - Risks/flaws: None obvious.

- **`apps/ui/src/hooks/queries/use-knowledge-library.ts`** (source)
  - Purpose: TanStack Query hooks for Knowledge Library backend.
  - Key components: Mutation supports `{ cleanupMode }` and forwards to API client (`apps/ui/src/hooks/queries/use-knowledge-library.ts:248`).
  - Integration points: Relies on `KLCleanupMode` exported from `@automaker/types` (`apps/ui/src/hooks/queries/use-knowledge-library.ts:23`).
  - Risks/flaws: In this environment, `@automaker/types` resolved by UI typecheck lacks `KLCleanupMode` (F4).

- **`apps/ui/src/lib/knowledge-library-api.ts`** (source)
  - Purpose: Typed HTTP/WebSocket client for AI-Library backend.
  - Key components: Imports `KLCleanupMode` from `@automaker/types` (`apps/ui/src/lib/knowledge-library-api.ts:13`) and passes `cleanup_mode` query param (`apps/ui/src/lib/knowledge-library-api.ts:329`).
  - Integration points: Must match REST endpoint query param name (`2.ai-library/src/api/routes/sessions.py:309`).
  - Risks/flaws: Same `KLCleanupMode` export mismatch issue in this environment (F4).

- **`apps/ui/src/store/knowledge-library-store.test.ts`** (test)
  - Purpose: Unit tests for store behavior and persistence.
  - Key components: Verifies `cleanupMode` persisted (`apps/ui/src/store/knowledge-library-store.test.ts:65`) and settable (`apps/ui/src/store/knowledge-library-store.test.ts:696`).
  - Integration points: Depends on vitest, but repo vitest projects exclude `apps/ui` (not executed by `npm run test:packages`).
  - Risks/flaws: Test execution is not currently wired into the repo’s standard test command set.

- **`apps/ui/src/store/knowledge-library-store.ts`** (source)
  - Purpose: Zustand store for Knowledge Library UI state.
  - Key components: Defines `KLCleanupMode` (`apps/ui/src/store/knowledge-library-store.ts:28`), stores `cleanupMode` (`apps/ui/src/store/knowledge-library-store.ts:130`), persists and migrates it (`apps/ui/src/store/knowledge-library-store.ts:356`), and provides mode config utilities (`apps/ui/src/store/knowledge-library-store.ts:414`).
  - Integration points: Used by ControlRow + workflow hook.
  - Risks/flaws: Duplicates cleanup-mode type definition separate from `@automaker/types` (keep aligned).

- **`libs/types/src/index.ts`** (source)
  - Purpose: Barrel export for `@automaker/types`.
  - Key components: Exports `KLCleanupMode` and signal types (`libs/types/src/index.ts:500`).
  - Integration points: Consumed by UI imports (`apps/ui/src/lib/knowledge-library-api.ts:13`).
  - Risks/flaws: In this environment the UI resolves a different installed `@automaker/types` package (F4).

- **`libs/types/src/knowledge-library.ts`** (source)
  - Purpose: Shared contract types for AI-Library feature.
  - Key components: Adds `KLCleanupMode` (`libs/types/src/knowledge-library.ts:130`), `signals_detected` on cleanup items (`libs/types/src/knowledge-library.ts:137`), and `cleanup_mode` on responses/WS commands (`libs/types/src/knowledge-library.ts:192`).
  - Integration points: Must stay aligned with backend schemas (`2.ai-library/src/api/schemas.py:174`).
  - Risks/flaws: None obvious.

- **`libs/types/src/settings.ts`** (source)
  - Purpose: Shared settings schema/types for file-based settings storage.
  - Key components: Introduces a settings-level `CleanupModeSetting` type and thresholds (`libs/types/src/settings.ts:105`).
  - Integration points: Not directly used by Knowledge Library UI store in this baseline.
  - Risks/flaws: Name/semantics collide with Python `CleanupModeSetting` and the plan’s meaning of “cleanup mode” (F6).

## Verification Results

- **Command:** `python -m py_compile 2.ai-library/src/sdk/client.py`
  - Result: blocked
  - Key output snippet:
    - `zsh:2: command not found: python`

- **Command:** `python3 -m py_compile 2.ai-library/src/api/routes/sessions.py 2.ai-library/src/api/schemas.py 2.ai-library/src/conversation/flow.py 2.ai-library/src/models/__init__.py 2.ai-library/src/models/cleanup_plan.py 2.ai-library/src/models/cleanup_mode_setting.py 2.ai-library/src/sdk/client.py 2.ai-library/src/sdk/prompts/__init__.py 2.ai-library/src/sdk/prompts/cleanup_mode.py 2.ai-library/src/session/manager.py`
  - Result: pass
  - Key output snippet: (no output)

- **Command:** `python3 -m pytest -q 2.ai-library/tests`
  - Result: blocked
  - Key output snippet:
    - `/opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest`

- **Command:** `npm run test:packages`
  - Result: pass
  - Key output snippet:
    - `Test Files  17 passed (17)`
    - `Tests       519 passed (519)`

- **Command:** `npm run typecheck --workspace=apps/ui`
  - Result: fail
  - Key output snippet (trimmed):
    - `apps/ui/src/lib/knowledge-library-api.ts(21,3): error TS2305: Module '"@automaker/types"' has no exported member 'KLCleanupMode'.`

- **Test artifacts (if any):** None detected in `git status --porcelain=v1` beyond baseline targets.

## Uncommitted Changes Summary (Baseline)

- **git toplevel:** `/Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1`
- **branch:** `feature-1`
- **HEAD:** `35ee692bd15ba212c404ce54b11318f40217b6c6`

- **git status summary (baseline):**
  - Modified (unstaged): 21 files
  - Staged: 0 files
  - Untracked: 3 files

- **diffstat summary (baseline):**
  - `21 files changed, 1082 insertions(+), 41 deletions(-)`

- **baseline created files:**
  - `2.ai-library/src/models/cleanup_mode_setting.py`
  - `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-mode-selector.tsx`
  - `apps/ui/src/components/views/knowledge-library/components/input-mode/components/signal-badges.tsx`

- **baseline changed files:**
  - `2.ai-library/src/api/routes/sessions.py`
  - `2.ai-library/src/api/schemas.py`
  - `2.ai-library/src/conversation/flow.py`
  - `2.ai-library/src/models/__init__.py`
  - `2.ai-library/src/models/cleanup_plan.py`
  - `2.ai-library/src/sdk/client.py`
  - `2.ai-library/src/sdk/prompts/__init__.py`
  - `2.ai-library/src/sdk/prompts/cleanup_mode.py`
  - `2.ai-library/src/session/manager.py`
  - `2.ai-library/tests/test_planning_flow.py`
  - `2.ai-library/tests/test_websocket_stream.py`
  - `apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx`
  - `apps/ui/src/components/views/knowledge-library/components/input-mode/components/control-row.tsx`
  - `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts`
  - `apps/ui/src/hooks/queries/use-knowledge-library.ts`
  - `apps/ui/src/lib/knowledge-library-api.ts`
  - `apps/ui/src/store/knowledge-library-store.test.ts`
  - `apps/ui/src/store/knowledge-library-store.ts`
  - `libs/types/src/index.ts`
  - `libs/types/src/knowledge-library.ts`
  - `libs/types/src/settings.ts`

## User Additions (fill in after audit, before execution)

### Constraints / preferences

-

### Must-not-change areas

-

### Extra acceptance criteria / checks

-

### Notes for the executor

-

## GPT-5.2 Codex Fix Plan (derived from findings)

1. Human-readable task list (T#)

- **T1 (Critical)** — Add explicit “Never Echo Secrets” guidance to cleanup prompts and (optionally) server-side sanitization.
  - Linked findings: F1
  - Linked Pi: P3, P21
  - Files: `2.ai-library/src/sdk/prompts/cleanup_mode.py`, `2.ai-library/src/sdk/client.py`
  - Acceptance: Prompts contain a consistent secrets rule; suggestion reasons/signals are sanitized if secrets slip through.
  - Verify: `python3 -m py_compile ...`; `python3 -m pytest -q 2.ai-library/tests` (when pytest is available).

- **T2 (High)** — Remove silent fallbacks for unknown cleanup modes in prompt factory/builder.
  - Linked findings: F2
  - Linked Pi: P3, P4, P22
  - Files: `2.ai-library/src/sdk/prompts/cleanup_mode.py`
  - Acceptance: Unknown mode raises a clear error; no implicit “balanced” fallback on invalid inputs.
  - Verify: `python3 -m py_compile 2.ai-library/src/sdk/prompts/cleanup_mode.py`; run backend tests when available.

- **T3 (High)** — Implement server-side confidence-threshold enforcement for discard suggestions.
  - Linked findings: F3
  - Linked Pi: P11, P1
  - Files: `2.ai-library/src/sdk/client.py`
  - Acceptance: Discard suggestions below `cleanup_mode.confidence_threshold` are downgraded to keep with explicit annotation.
  - Verify: Add/extend unit tests (pytest) + run them; at minimum `python3 -m py_compile 2.ai-library/src/sdk/client.py`.

- **T4 (High)** — Fix workspace type resolution so `apps/ui` sees this worktree’s `@automaker/types` (includes `KLCleanupMode`).
  - Linked findings: F4
  - Linked Pi: P13, P15, P16
  - Files: (likely) workspace install/link config; possibly `apps/ui/tsconfig.json` if a path override is chosen.
  - Acceptance: `npm run typecheck --workspace=apps/ui` no longer fails on missing `KLCleanupMode` export.
  - Verify: `npm run typecheck --workspace=apps/ui`.

- **T5 (Medium)** — Align REST invalid cleanup_mode behavior with plan (422 validation).
  - Linked findings: F5
  - Linked Pi: P6, P22
  - Files: `2.ai-library/src/api/routes/sessions.py`
  - Acceptance: Invalid cleanup_mode yields 422 (or documented contract updated consistently across clients).
  - Verify: Add/extend API tests; run pytest when available.

- **T6 (Medium)** — Rename or scope TS `CleanupModeSetting` (settings) to avoid collision with Knowledge Library mode selector.
  - Linked findings: F6
  - Linked Pi: P1
  - Files: `libs/types/src/settings.ts` (+ any importers)
  - Acceptance: No ambiguous “cleanup mode” concept; thresholds/semantics are clearly separated.
  - Verify: `npm run test:packages`; `npm run typecheck --workspace=apps/ui`.

- **T7 (Low)** — Re-evaluate prompt preview size to preserve token efficiency.
  - Linked findings: F7
  - Linked Pi: P4, P23
  - Files: `2.ai-library/src/sdk/prompts/cleanup_mode.py`
  - Acceptance: Preview limit is bounded per plan goals or is configurable; token usage is measurable.
  - Verify: Unit test for truncation length + prompt-size measurement harness.

2. A machine-readable YAML block:

```yaml
fix_plan:
  source_plan_file: '</Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1/ Plans + Improvments + Ideas/possible-improvements/004-knowledge-library-cleanup-ai.md>'
  baseline:
    created_files:
      - '2.ai-library/src/models/cleanup_mode_setting.py'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-mode-selector.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/components/signal-badges.tsx'
    changed_files:
      - '2.ai-library/src/api/routes/sessions.py'
      - '2.ai-library/src/api/schemas.py'
      - '2.ai-library/src/conversation/flow.py'
      - '2.ai-library/src/models/__init__.py'
      - '2.ai-library/src/models/cleanup_plan.py'
      - '2.ai-library/src/sdk/client.py'
      - '2.ai-library/src/sdk/prompts/__init__.py'
      - '2.ai-library/src/sdk/prompts/cleanup_mode.py'
      - '2.ai-library/src/session/manager.py'
      - '2.ai-library/tests/test_planning_flow.py'
      - '2.ai-library/tests/test_websocket_stream.py'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/components/cleanup-review.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/components/control-row.tsx'
      - 'apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts'
      - 'apps/ui/src/hooks/queries/use-knowledge-library.ts'
      - 'apps/ui/src/lib/knowledge-library-api.ts'
      - 'apps/ui/src/store/knowledge-library-store.test.ts'
      - 'apps/ui/src/store/knowledge-library-store.ts'
      - 'libs/types/src/index.ts'
      - 'libs/types/src/knowledge-library.ts'
      - 'libs/types/src/settings.ts'
  findings:
    - id: 'F1'
      severity: 'Critical'
      summary: 'Cleanup prompts lack explicit secret-echo prevention guidance.'
      linked_plan_items: ['P3', 'P21']
    - id: 'F2'
      severity: 'High'
      summary: 'Prompt factory/builder silently fallback to balanced mode.'
      linked_plan_items: ['P3', 'P4', 'P22']
    - id: 'F3'
      severity: 'High'
      summary: 'Mode confidence thresholds exist but are not enforced server-side.'
      linked_plan_items: ['P1', 'P11']
    - id: 'F4'
      severity: 'High'
      summary: 'apps/ui typecheck cannot import KLCleanupMode from resolved @automaker/types.'
      linked_plan_items: ['P13', 'P15', 'P16']
    - id: 'F5'
      severity: 'Medium'
      summary: 'REST invalid cleanup_mode returns 400 instead of plan’s 422 validation behavior.'
      linked_plan_items: ['P6', 'P22']
    - id: 'F6'
      severity: 'Medium'
      summary: 'CleanupModeSetting name/semantics collide between Python and TS settings.'
      linked_plan_items: ['P1']
    - id: 'F7'
      severity: 'Low'
      summary: 'Prompt preview limit set to 800 chars may reduce token efficiency.'
      linked_plan_items: ['P4', 'P23']
  tasks:
    - id: 'T1'
      priority: 'Critical'
      linked_findings: ['F1']
      linked_plan_items: ['P3', 'P21']
      files:
        - '2.ai-library/src/sdk/prompts/cleanup_mode.py'
        - '2.ai-library/src/sdk/client.py'
      steps:
        - "Add a 'Never Echo Secrets' rule to each mode prompt."
        - 'Optionally sanitize model outputs (suggestion_reason / signal.detail) to redact key-like strings.'
      acceptance:
        - 'Prompts explicitly instruct the model not to quote secrets.'
        - 'API/UI never display raw credentials/tokens if present in source content.'
      verification:
        - 'python3 -m py_compile 2.ai-library/src/sdk/prompts/cleanup_mode.py 2.ai-library/src/sdk/client.py'
        - 'python3 -m pytest -q 2.ai-library/tests'
    - id: 'T2'
      priority: 'High'
      linked_findings: ['F2']
      linked_plan_items: ['P3', 'P4', 'P22']
      files:
        - '2.ai-library/src/sdk/prompts/cleanup_mode.py'
      steps:
        - 'Remove .get(..., balanced) fallbacks in get_cleanup_system_prompt and build_cleanup_prompt.'
        - 'Raise ValueError on unknown mode.'
      acceptance:
        - 'Unknown cleanup mode errors are surfaced explicitly.'
      verification:
        - 'python3 -m py_compile 2.ai-library/src/sdk/prompts/cleanup_mode.py'
        - 'python3 -m pytest -q 2.ai-library/tests'
    - id: 'T3'
      priority: 'High'
      linked_findings: ['F3']
      linked_plan_items: ['P1', 'P11']
      files:
        - '2.ai-library/src/sdk/client.py'
      steps:
        - 'After parsing AI output, compare confidence to cleanup_mode.confidence_threshold.'
        - 'Downgrade discard -> keep when below threshold and append explicit annotation to suggestion_reason.'
      acceptance:
        - 'Discard suggestions below threshold never appear without an explicit override.'
      verification:
        - 'python3 -m py_compile 2.ai-library/src/sdk/client.py'
        - 'python3 -m pytest -q 2.ai-library/tests'
    - id: 'T4'
      priority: 'High'
      linked_findings: ['F4']
      linked_plan_items: ['P13', 'P15', 'P16']
      files:
        - 'apps/ui/tsconfig.json'
        - 'libs/types/dist/index.d.ts'
      steps:
        - 'Ensure @automaker/types resolved by apps/ui includes KLCleanupMode (re-link/reinstall from this worktree).'
        - 'If needed, add a temporary tsconfig paths override to point @automaker/types to the intended build output.'
      acceptance:
        - 'apps/ui can import KLCleanupMode from @automaker/types.'
      verification:
        - 'npm run typecheck --workspace=apps/ui'
    - id: 'T5'
      priority: 'Medium'
      linked_findings: ['F5']
      linked_plan_items: ['P6', 'P22']
      files:
        - '2.ai-library/src/api/routes/sessions.py'
      steps:
        - 'Change cleanup_mode query param type to CleanupModeSetting for FastAPI validation.'
        - 'Update any client expectations/tests for HTTP status code.'
      acceptance:
        - 'Invalid cleanup_mode returns 422 with a clear validation error payload.'
      verification:
        - 'python3 -m pytest -q 2.ai-library/tests'
    - id: 'T6'
      priority: 'Medium'
      linked_findings: ['F6']
      linked_plan_items: ['P1']
      files:
        - 'libs/types/src/settings.ts'
      steps:
        - 'Rename CleanupModeSetting (settings) to avoid collision with Knowledge Library prompt mode selector.'
        - 'Update import sites accordingly.'
      acceptance:
        - 'No ambiguous CleanupModeSetting meaning across codebase.'
      verification:
        - 'npm run test:packages'
    - id: 'T7'
      priority: 'Low'
      linked_findings: ['F7']
      linked_plan_items: ['P4', 'P23']
      files:
        - '2.ai-library/src/sdk/prompts/cleanup_mode.py'
      steps:
        - 'Decide on a lower preview limit or mode-specific preview limits.'
        - 'Add a unit test to assert truncation behavior.'
      acceptance:
        - 'Prompt size is bounded per plan goals and measurable.'
      verification:
        - 'python3 -m py_compile 2.ai-library/src/sdk/prompts/cleanup_mode.py'
```
