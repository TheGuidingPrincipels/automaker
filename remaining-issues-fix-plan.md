# Plan: Fix Remaining Issues (Pytest + apps/ui Typecheck)

## Context

Two blockers remain from the last execution report:

1. **Python tests appeared “blocked”** because `python3 -m pytest ...` used the system Python, not the AI-Library venv.
2. **`npm run typecheck --workspace=apps/ui` fails** due to a combination of:
   - missing workspace dependencies (e.g. `react-resizable-panels` not installed in the current `node_modules`)
   - missing generated file `apps/ui/src/routeTree.gen.ts` (gitignored + not generated before `tsc`)
   - real TypeScript type errors across UI code

## Goals

- Make Python test verification reliable and reproducible.
- Make `npm run typecheck --workspace=apps/ui` pass.
- Verify everything via repeatable commands.
- **No breaking changes** (no API/behavior changes unless required to fix correctness bugs; prefer type-only fixes).

## Non-Goals

- No UI redesigns or feature additions.
- No package-manager migration unless explicitly approved (see “Decision” below).
- No broad refactors; keep diffs tight and localized.

## Decision (Needed Before Execution)

### Package manager for the monorepo

Recommended: **use npm** for installs, because:

- repo has `package-lock.json`
- root scripts use `npm run ...`
- `.npmrc` explicitly documents npm behavior (platform optional deps)

If you prefer **pnpm**, we must add and maintain `pnpm-workspace.yaml` and ensure installs/linking work consistently (higher risk of breaking changes).

## Context7 Verification Checkpoints (Before Implementation)

- **TanStack Router route generation:** verify the current `@tanstack/router-cli` / `tsr generate` usage via Context7 before adding deps/scripts (avoid deprecated commands).
- **Any new/uncertain library APIs:** if a fix requires using or changing an external library API (React Query, TanStack Router, Electron typings, etc.), stop and verify via Context7 first.

## Plan (Tasks)

### T1 — Make Python test runs deterministic (no “pytest missing” false negatives)

**Goal:** ensure the correct interpreter is used for AI-Library tests.

**Steps:**

- Use the AI-Library venv explicitly for verification:
  - `2.ai-library/.venv/bin/python -m pytest -q 2.ai-library/tests`
- (Optional but recommended) Add a small repo script to enforce this consistently (fail fast with a clear error if `.venv` is missing).

**Acceptance:**

- Running the venv command above executes pytest and does not error with “No module named pytest”.

---

### T2 — Restore a valid workspace install (dependencies present + workspaces linked)

**Goal:** get a consistent install state where UI dependencies actually exist on disk.

**Steps (npm path):**

- Remove the current install output (it appears to be pnpm-isolated and missing workspace deps):
  - `rm -rf node_modules apps/*/node_modules libs/*/node_modules`
- Reinstall with npm at repo root:
  - `npm install`
- Build workspace packages (so UI sees up-to-date `@automaker/*` outputs):
  - `npm run build:packages`

**Acceptance:**

- `npm ls --depth=0` no longer shows `UNMET DEPENDENCY` for workspace packages.
- `npm ls react-resizable-panels --workspace=apps/ui` shows `react-resizable-panels@...` installed.

---

### T3 — Ensure TanStack Router route tree exists before `tsc` (no missing `routeTree.gen.ts`)

**Goal:** make `apps/ui/src/routeTree.gen.ts` generated as part of `typecheck`.

**Steps:**

- (Context7) Verify current TanStack Router CLI usage for route generation (`tsr generate`) before wiring scripts.
- Add `@tanstack/router-cli` as a dev dependency for the UI workspace.
- Add scripts in `apps/ui/package.json`:
  - `generate-routes`: `tsr generate`
  - update `typecheck`: `npm run generate-routes && tsc --noEmit`
- Run `npm run typecheck --workspace=apps/ui` and confirm it generates `apps/ui/src/routeTree.gen.ts`.

**Acceptance:**

- `apps/ui/src/routeTree.gen.ts` is generated during typecheck.
- The previous error `Cannot find module '../routeTree.gen'` is gone.

---

### T4 — Remove the temporary TS path override for `@automaker/types` (avoid hidden divergence)

**Goal:** avoid relying on `tsconfig.json` path mapping that bypasses the actual workspace package resolution.

**Steps:**

- After T2 is complete, remove the `@automaker/types` `paths` override from `apps/ui/tsconfig.json`.
- Re-run `npm run typecheck --workspace=apps/ui` to ensure `KLCleanupMode` is still resolved correctly via the workspace package.

**Acceptance:**

- UI still typechecks with the real workspace `@automaker/types` resolution (no `KLCleanupMode` missing export regression).

---

### T5 — Fix remaining `apps/ui` TypeScript errors without breaking behavior

**Goal:** resolve remaining compiler errors with minimal behavior changes.

**Approach:**

- Run `npm run typecheck --workspace=apps/ui` and fix errors in descending order of:
  1. missing deps / missing generated files (should be handled by T2/T3)
  2. invalid handler signatures / incorrect callback wiring (low-risk fixes)
  3. unsafe `unknown` usage / incorrect narrowing
  4. actual logic/typing mismatches (fix with tight diffs + tests where feasible)

**Known “first fixes” (from current output):**

- `apps/ui/src/components/ui/git-diff-panel.tsx`: wrap React Query `refetch` functions in `() => void refetch()` instead of passing them as DOM event handlers.
- `apps/ui/src/lib/electron.ts`: update `createMockWorktreeAPI()` to implement required `WorktreeAPI` members (e.g. `addRemote`).
- `apps/ui/src/utils/router.ts`: should stop failing once `routeTree.gen.ts` is generated (T3).
- `apps/ui/src/components/views/terminal-view.tsx`: `react-resizable-panels` missing should be resolved by install (T2).

**Acceptance:**

- `npm run typecheck --workspace=apps/ui` exits 0.

## Verification (Must Pass)

Python (AI-Library):

- `2.ai-library/.venv/bin/python -m pytest -q 2.ai-library/tests`

Node (repo root):

- `npm run test:packages`
- `npm run typecheck --workspace=apps/ui`
- (Optional but recommended) `npm run build --workspace=apps/ui`

## Rollback / Safety

- Keep changes isolated and mechanical; prefer type-level fixes.
- Avoid changing public contracts (API payloads, event names, etc.). If unavoidable, document and add coverage.
- For any runtime behavior change, add focused tests or preserve prior behavior behind an explicit, documented decision.
