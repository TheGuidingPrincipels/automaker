# Scoped Code Audit — 4.Speed Reading System/sessions/README.md

This audit focuses on whether the Session 5 “Frontend Foundation” plan was fully carried into the Session 5 “REVISED: Automaker integration” plan, and whether the revised plan is executable within the current Automaker repo layout and runtime constraints.

## Critical findings

- **[Build/Dependencies] Revised backend proxy design is not buildable as written**
  - **Evidence:** `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:726`, `1.apps/server/package.json:26`, `1.apps/server/src/index.ts:26`
  - **Impact:** The plan imports `http-proxy-middleware`, but `@automaker/server` does not depend on it; additionally, server code uses explicit ESM `.js` import specifiers, while the plan’s registration snippet does not. This blocks implementation as written and risks runtime import failures.
  - **Recommendation:** Either (a) implement the DeepRead proxy without `http-proxy-middleware` using Node’s built-in `fetch` + explicit header/body forwarding, or (b) explicitly add the dependency and update the plan to match Automaker’s ESM import conventions (`./routes/deepread/index.js` style) and body handling requirements (see next finding).

- **[Runtime/Proxy Correctness] Current server middleware stack will break proxying (JSON bodies consumed; multipart uploads rejected)**
  - **Evidence:** `1.apps/server/src/index.ts:279`, `1.apps/server/src/index.ts:389`, `1.apps/server/src/middleware/require-json-content-type.ts:29`, `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:576`
  - **Impact:** `express.json()` runs globally before routes; naïve proxy middleware commonly fails to forward POST/PATCH JSON bodies because the stream is already consumed. Separately, `requireJsonContentType` rejects non-JSON POSTs, so `/api/deepread/documents/from-file` (multipart/form-data) cannot work through the Automaker server at all without an exception.
  - **Recommendation:** Update the revised plan to explicitly handle both cases:
    - JSON endpoints: forward using `fetch(DEEPREAD_BACKEND_URL + '/api/...', { method, headers, body: JSON.stringify(req.body) })`.
    - Multipart upload endpoint(s): add a _narrow_ exception in `requireJsonContentType` for `POST /api/deepread/documents/from-file` and stream the raw request body through to the Python backend (do not parse in Express).

- **[Auth/Execution] Frontend upload uses raw `fetch` and will fail in Electron and some web auth modes**
  - **Evidence:** `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:581`, `1.apps/ui/src/lib/api-fetch.ts:1`, `1.apps/ui/src/lib/api-fetch.ts:32`
  - **Impact:** Automaker’s authenticated API calls rely on headers (`X-API-Key` for Electron, `X-Session-Token` for web token auth). The revised plan’s upload call uses raw `fetch` with only `credentials: 'include'`, which will not include these headers and can fail immediately under Electron (401/403) and undermines Automaker’s stated “use api-fetch, not raw fetch” rule.
  - **Recommendation:** Add a dedicated `apiUpload` (multipart) helper that:
    - Reuses `getServerUrlSync()` for correct base URL in all modes,
    - Adds auth headers without forcing `Content-Type: application/json`,
    - Sends `FormData` as the body (letting the browser set multipart boundaries).

- **[Build/API Mismatch] Revised plan references `apiPatch`, but Automaker UI does not provide it**
  - **Evidence:** `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:552`, `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:643`, `1.apps/ui/src/lib/api-fetch.ts:109`
  - **Impact:** Implementing the revised plan as written will fail TypeScript compilation because `apiPatch` is not exported by `1.apps/ui/src/lib/api-fetch.ts`.
  - **Recommendation:** Update the revised plan to either (a) call `apiFetch(endpoint, 'PATCH', ...)` directly, or (b) add an `apiPatch` helper to `api-fetch.ts` (and document how to use it for JSON vs multipart).

- **[UX/Requirement Gap] “Fullscreen reader” is not achievable without root layout changes**
  - **Evidence:** `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:50`, `1.apps/ui/src/routes/__root.tsx:853`
  - **Impact:** Automaker’s root layout renders the sidebar for all authenticated routes except login/setup/dashboard. A reader route under `/speed-reading/reader/...` will still render the sidebar and streamer panel unless the root layout is updated, contradicting the plan’s “ReaderPage (fullscreen)” intent.
  - **Recommendation:** Add a root-layout conditional (similar to the dashboard/login logic) to render `/speed-reading/reader/*` in a full-screen mode with no sidebar/streamer panel, and ensure this mode still shows Toaster + sandbox dialog behavior as desired.

- **[DX/Bootstrapping] Speed Reading “Quick Start” instructions don’t match current repo workspace wiring**
  - **Evidence:** `4.Speed Reading System/README.md:162`, `package.json:8`, `start-automaker.sh:72`
  - **Impact:** Speed Reading docs say “npm run dev” from repo root, but root workspace/scripts reference `apps/*` paths and `apps/ui/package.json`. In this repo snapshot, the actual app directories are under `1.apps/`. New contributors following the docs can hit immediate startup failures.
  - **Recommendation:** Update the plan/docs to state the _actual_ way Automaker is started in this repo (e.g., “run server from `1.apps/server`, UI from `1.apps/ui`”), or standardize folder naming/workspaces so `npm run dev` works as documented.

## Major findings

- **[Feature Parity] Some “frontend foundation” elements from the original plan are not explicitly carried into the revised plan**
  - **Evidence:** `4.Speed Reading System/sessions/SESSION-05-frontend-foundation.md:592`, `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:662`
  - **Impact:** The original foundation plan establishes reader playback state and UI “reader mode” state early. The revised plan’s store only covers reader settings. If later sessions don’t clearly reintroduce these responsibilities, the integrated implementation can drift from the original behavior expectations (e.g., consistent “reader mode” toggling, playback state ownership).
  - **Recommendation:** Decide and document where playback state and “reader mode” live in the integrated version (Zustand store vs component-local state). If deferred to Session 7, explicitly reference that in Session 5 revised and include placeholder state to keep the architecture consistent.

- **[Feature Completeness] Revised Session 5 doesn’t include minimal placeholder implementations for referenced hooks/components**
  - **Evidence:** `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:334`, `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:790`
  - **Impact:** The revised plan imports hooks/components that must exist for the UI build to succeed (e.g., `useRecentSessions`, `SpeedReadingHeader`, `RecentSessions`, `SpeedReadingImport`, `SpeedReadingPreview`, `SpeedReadingReader`). If implementers follow the plan literally, they can easily end up with missing modules and a broken build.
  - **Recommendation:** Add a “Compilation-first” checklist to Session 5 revised: create stubs for all referenced modules, then fill them in. Include at least minimal hook implementations (React Query calls) so the initial `/speed-reading` page renders.

- **[Shortcut Integration] Adding `speedReading` requires changes in more than `libs/types/src/settings.ts`**
  - **Evidence:** `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:231`, `1.apps/ui/src/store/app-store.ts:326`, `libs/types/src/settings.ts:665`
  - **Impact:** Automaker’s runtime shortcut configuration comes from the UI store defaults/merging behavior; updating only the shared types default may not actually surface the shortcut in the UI (and won’t appear in the keyboard map unless updated).
  - **Recommendation:** Update the revised plan to explicitly list all required touch points: `libs/types/src/settings.ts`, `1.apps/ui/src/store/app-store.ts`, and any UI shortcut display mapping (e.g., keyboard map).

## Minor findings

- **[Naming Consistency] “DeepRead” vs “Speed Reading” vs `/api/deepread`**
  - **Evidence:** `4.Speed Reading System/sessions/README.md:6`, `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md:56`
  - **Impact:** Mixed naming increases cognitive load and makes later extraction harder (repo-wide grep becomes noisy).
  - **Recommendation:** Pick a canonical internal identifier (e.g., `deepread` for API + folder/package name, “Speed Reading” for UI label) and document the mapping once.

- **[Ports/Environments] Multiple ports and launch modes need a single source of truth**
  - **Evidence:** `1.apps/ui/vite.config.mts:22`, `1.apps/server/src/index.ts:113`, `4.Speed Reading System/README.md:155`
  - **Impact:** The plan assumes a running Python service at `8001` and Automaker server at `3008`. Without a unified dev runner, it’s easy to start services inconsistently and think “integration is broken” when it’s just a port/env mismatch.
  - **Recommendation:** Add a small “dev orchestration” section (even if only documented) that specifies exact commands, ports, and env vars for the three-process setup (UI, server, Python backend).

## Viability assessment

- What’s viable now
  - Automaker already uses React 19, TanStack Router, TanStack Query, Tailwind 4, shadcn/ui-style components, Zustand, and a centralized authenticated fetch utility; the revised plan’s overall integration direction matches the existing stack.
- Key assumptions & constraints
  - The Python backend runs as a separate process and is reachable from the Automaker server.
  - `/api/deepread/*` is intended to be protected by Automaker auth, even though the Python backend itself likely has no auth.
  - Automaker’s current security middleware (`requireJsonContentType`) cannot remain “as-is” if file upload is required.
- Biggest blockers / unknowns (and how to validate)
  - Proxy viability with current server middleware ordering: prototype a minimal JSON-forwarding + multipart-forwarding proxy route and verify POST/PATCH bodies arrive correctly at the Python service.
  - Fullscreen reader UX: validate that `/speed-reading/reader/...` truly hides sidebar/streamer panel and still behaves correctly with auth + sandbox dialog flows.
  - Packaging/deployment: if this must work in the Electron packaged app, decide how the Python backend is shipped/started (or whether this feature is “dev-only” initially).

## Performance & scalability

- Hot paths / I/O / algorithmic concerns
  - Token chunk retrieval and caching strategy will dominate perceived performance once Session 7+ is implemented.
  - Proxy implementation should stream responses and avoid buffering large uploads in memory.
- “Low effort” wins vs “high effort” work
  - Low effort: local token-chunk caching in React Query (infinite staleTime for immutable chunks) and conservative chunk sizes.
  - High effort: background prefetching, adaptive chunk sizes, and precise rewind/history buffers (later sessions).
- Any obvious profiling targets
  - Reader playback loop timing accuracy and React re-render frequency in reader mode.

## Security review

- Threats relevant to this area
  - CSRF risk if allowing non-JSON POSTs while relying on cookie auth.
  - File upload abuse (large files, malicious PDFs, content-type spoofing).
  - SSRF-like proxy misuse if proxy target URL is configurable without validation.
- Input validation / injection / authz/authn / secrets / data exposure
  - Keep `/api/deepread/*` behind Automaker auth (recommended).
  - Constrain `DEEPREAD_BACKEND_URL` to a safe allowlist (e.g., only localhost in dev) if it will ever be configurable.
  - Enforce file type/size limits (preferably at Python backend, plus defense-in-depth at proxy).
- Supply-chain / dependency risks
  - Avoid introducing proxy middleware dependencies unless necessary; a small, explicit proxy implementation reduces attack surface.

## Reliability & operations

- Timeouts, retries, backoff, circuit breakers (if applicable)
  - Add explicit timeouts on proxy `fetch` requests to Python backend to prevent hanging UI calls.
  - Use simple retry/backoff for idempotent GETs (health, preview, tokens) but not for uploads.
- Logging/metrics/tracing gaps
  - Proxy should log upstream status codes and latency (at least at debug level) to make failures diagnosable.
- Failure modes & recovery
  - If Python backend is down, UI should show a clear “Speed Reading backend unavailable” state and guide the user to start it.

## Test coverage & quality gates

- What’s covered vs missing
  - No tests exist yet for the Speed Reading routes/proxy, since the feature is not implemented.
- Suggested tests (unit/integration/e2e) scoped to this area
  - UI: Playwright test that `/speed-reading` loads and Shift+R navigates correctly.
  - Server: unit/integration test for `/api/deepread/health` returning 503 when backend is down and 200 when up.
  - Server: test that multipart upload is not blocked by `requireJsonContentType` _only_ for the deepread upload route.
- Suggested CI gates (lint/typecheck/static analysis) scoped to this area
  - Typecheck UI after adding new routes/components.
  - Server unit tests for proxy route.

## Recommendations roadmap

- **P0 (must fix)**:
  - Make the proxy approach compatible with `express.json` + `requireJsonContentType` and confirm upload + JSON requests work end-to-end.
  - Replace raw upload `fetch` with an authenticated multipart helper.
  - Fix `apiPatch` usage to match the repo’s actual API utilities.
  - Add root-layout support for true fullscreen reader mode.
- **P1 (should fix)**:
  - Update keyboard shortcut plumbing in both shared settings types and UI store defaults (+ keyboard map).
  - Add “compiles first” placeholder module checklist to Session 5 revised.
  - Clarify and standardize dev startup commands (UI/server/python) for this repo layout.
- **P2 (nice to have)**:
  - Decide on a canonical naming scheme and apply consistently.
  - Add basic proxy latency/status logging + timeouts.

## Appendix

- Scope definition: `DEPTH=2`, `MAX_FILES=60`, `MAX_CALLERS=20`, `RUN_TESTS=0`
- Files reviewed:
  - `4.Speed Reading System/sessions/README.md`
  - `4.Speed Reading System/sessions/SESSION-05-frontend-foundation.md`
  - `4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md`
  - `4.Speed Reading System/README.md`
  - `1.apps/ui/src/lib/api-fetch.ts`
  - `1.apps/ui/src/routes/__root.tsx`
  - `1.apps/ui/src/store/app-store.ts`
  - `1.apps/ui/vite.config.mts`
  - `1.apps/server/package.json`
  - `1.apps/server/src/index.ts`
  - `1.apps/server/src/middleware/require-json-content-type.ts`
  - `start-automaker.sh`
  - `package.json`
- Commands run (high level):
  - `ls`, `rg`, `sed`, `nl`, `wc`
- Notes:
  - Goal: ensure revised Session 5 covers the original frontend foundation objectives and is executable in the existing Automaker stack while keeping Speed Reading exportable later.
