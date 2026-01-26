# Plan Audit Report

## Findings (ordered by severity)

### Critical

- None.

### High

- F1 (High) What: Cleanup keep/discard controls are present but have no handlers, and the decide-cleanup mutation is never used, so items cannot be finalized and cleanup approval can remain blocked. Impact: P31, P16, P17. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:294`, `apps/ui/src/hooks/queries/use-knowledge-library.ts:222`. Suggested fix: wire Keep/Discard buttons to `useKLDecideCleanupItem`, update state, and refresh the cleanup plan after decisions.
- F2 (High) What: Routing destination options render as buttons without selection or reject actions, so blocks cannot be resolved or approved. Impact: P32, P33, P16, P17, P35. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:457`, `apps/ui/src/hooks/queries/use-knowledge-library.ts:300`, `apps/ui/src/hooks/queries/use-knowledge-library.ts:318`. Suggested fix: connect option buttons to `useKLSelectDestination`, add reject action with `useKLRejectBlock`, and reflect selected option state.
- F3 (High) What: Required create-file Title/Overview workflow, grouping, and invalid-destination warnings are absent; store validation exists but is unused. Impact: P3, P16, P4. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:343`, `apps/ui/src/store/knowledge-library-store.ts:51`. Suggested fix: add Proposed New Files panel and grouping UI, wire Title/Overview inputs to store validation, and block routing approval until valid.
- F4 (High) What: After answering Claude questions, the workflow does not re-trigger cleanup/routing generation, so sessions can stall. Impact: P13. Evidence: `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:466`. Suggested fix: when pending questions drop to zero, send `generate_cleanup` or `generate_routing` based on the session phase.

### Medium

- F5 (Medium) What: No Strict/Refinement mode toggle is rendered even though a mode mutation exists. Impact: P15, P34. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:8`, `apps/ui/src/hooks/queries/use-knowledge-library.ts:176`. Suggested fix: add a mode toggle component that calls `useKLSetMode` and display the current mode.
- F6 (Medium) What: Session list UI for existing sessions is missing, so users cannot select prior sessions. Impact: P29. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx:49`. Suggested fix: add a session list component that uses `useKLSessions` and loads selected sessions.
- F7 (Medium) What: Query answers are rendered as plain text and confidence is not passed through, so markdown formatting and confidence display are missing. Impact: P42, P44, P23. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx:33`, `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:89`. Suggested fix: render answers with markdown and pass `response.confidence` into `AnswerCard`.
- F8 (Medium) What: Invalid file validation errors are not shown; only an "Invalid" badge appears and file metadata is never fetched in the viewer. Impact: P4, P20. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx:62`, `apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx:11`. Suggested fix: fetch metadata for selected files and surface validation errors in the viewer and/or list.

### Low

- F9 (Low) What: The UI never shows the explicit "Knowledge Library disconnected" message required by the plan. Impact: P5. Evidence: `apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx:60`. Suggested fix: add an offline banner or status text with the required copy.
- F10 (Low) What: The semantic search toggle does not change search behavior; the filter is always local keyword filtering. Impact: P21. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:31`, `apps/ui/src/components/views/knowledge-library/components/library-browser/search-bar.tsx:42`. Suggested fix: wire semantic search mode to `useKLSemanticSearch` and use its results.

## Plan Coverage Matrix

- P1 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-hub-page/index.tsx:31`, `apps/ui/src/components/views/knowledge-library/index.tsx:33`, `apps/ui/src/routes/knowledge-hub.$section.tsx:13`. Notes: Knowledge Library replaces Blueprints in hub and routes.
- P2 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/dropzone-overlay.tsx:74`, `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx:350`. Notes: Single markdown file enforced; no paste ingestion UI.
- P3 — Status: Partial. Evidence: `apps/ui/src/store/knowledge-library-store.ts:51`. Notes: Validation exists in store but no UI to collect Title/Overview or enforce in routing.
- P4 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx:92`. Notes: Invalid badge shown, but no inline error details or routing warnings.
- P5 — Status: Missing. Evidence: `apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx:60`. Notes: No "Knowledge Library disconnected" copy observed.
- P6 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-hub-page/index.tsx:31`, `apps/ui/src/components/views/knowledge-hub-page/index.tsx:129`. Notes: Card exists but count is not from `useKLLibrary`.
- P7 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-hub-page/index.tsx:134`, `apps/ui/src/routes/knowledge-hub.$section.tsx:13`. Notes: Navigation uses knowledge-library route.
- P8 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/index.tsx:10`, `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:1`. Notes: Core structure exists but several specified subcomponents are missing (view-tabs, merge-dialog, plan-review subcomponents).
- P9 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/index.tsx:21`. Notes: Header + tabs + views wired.
- P10 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx:49`, `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx:117`. Notes: Top review and bottom dock layout present.
- P11 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:402`, `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:423`. Notes: Session creation, upload, WS, generate_cleanup flow present.
- P12 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:447`, `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx:314`. Notes: Guidance messages send `user_message` and append transcript.
- P13 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:288`, `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:466`. Notes: Questions handled, but no re-trigger after all answers.
- P14 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/dropzone-overlay.tsx:74`, `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx:346`. Notes: Full-page overlay and dock upload with no auto-start.
- P15 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:56`. Notes: Phases shown, but no mode toggle or 3-column block review layout.
- P16 — Status: Missing. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:343`. Notes: No grouping, new file panel, or validation enforcement.
- P17 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:294`, `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:457`. Notes: Cards render but actions (select/reject/merge) are not wired.
- P18 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/category-tree.tsx:18`, `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:165`.
- P19 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx:94`. Notes: Markdown rendering exists but no syntax highlighting library.
- P20 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx:114`. Notes: Invalid badge present, but no error list or viewer warnings.
- P21 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/search-bar.tsx:42`, `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:74`. Notes: Toggle UI exists; semantic mode not implemented.
- P22 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:61`, `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:181`.
- P23 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx:33`, `apps/ui/src/components/views/knowledge-library/components/query-mode/source-citation.tsx:22`. Notes: Sources link, but markdown/confidence missing.
- P24 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/conversation-list.tsx:21`, `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:40`. Notes: Conversation list exists; local messages are not persisted.
- P25 — Status: Implemented. Evidence: `apps/ui/src/routes/knowledge-hub.$section.tsx:13`.
- P26 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-hub-page/index.tsx:31`.
- P27 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-hub-page/index.tsx:134`, `apps/ui/src/routes/knowledge-hub.$section.tsx:13`.
- P28 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/index.tsx:33`.
- P29 — Status: Missing. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx:49`. Notes: No session list rendered.
- P30 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx:170`, `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:402`.
- P31 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:294`. Notes: Keep/Discard buttons exist but no handlers.
- P32 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:457`. Notes: Options displayed but not selectable.
- P33 — Status: Missing. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:457`. Notes: No onClick to select destination.
- P34 — Status: Missing. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:8`. Notes: No mode toggle component.
- P35 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:377`, `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:508`. Notes: Routing approval gated; execute button shows when phase ready only.
- P36 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/execution-status.tsx:80`. Notes: Shows counts/errors but no verification status.
- P37 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/category-tree.tsx:18`.
- P38 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/category-tree.tsx:81`, `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:108`.
- P39 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx:94`.
- P40 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:74`.
- P41 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:61`.
- P42 — Status: Missing. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx:33`. Notes: No markdown rendering.
- P43 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/source-citation.tsx:22`.
- P44 — Status: Missing. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:89`. Notes: Confidence not passed to AnswerCard.
- P45 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/conversation-list.tsx:21`, `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:40`.
- P46 — Status: Implemented. Evidence: `apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx:88`, `apps/ui/src/components/views/knowledge-library/index.tsx:24`.
- P47 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:124`, `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx:41`.
- P48 — Status: Partial. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:113`, `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:177`, `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:275`.
- P49 — Status: Unverifiable. Evidence: `./start-api.sh` failed with "no such file or directory" (see Verification Results).
- P50 — Status: Unverifiable. Evidence: `npm run dev` failed with permission error (see Verification Results).
- P51 — Status: Unverifiable. Evidence: Dev server not running due to P50 failure.
- P52 — Status: Unverifiable. Evidence: Dev server not running due to P50 failure.
- P53 — Status: Unverifiable. Evidence: Dev server not running due to P50 failure.
- P54 — Status: Unverifiable. Evidence: Dev server not running due to P50 failure.

## Code Structure & Logic Review (Baseline Targets)

### Created files (baseline)

- `apps/ui/src/components/shared/session-transcript.tsx` — Purpose: shared transcript UI. Key components: `SessionTranscript`, `EntryAvatar`, `EntryBubble`. Integration: `ScrollArea`, `lucide-react`. Risks/flaws: duplicates input-mode transcript and appears unused. Evidence: `apps/ui/src/components/shared/session-transcript.tsx:216`, `apps/ui/src/components/views/knowledge-library/components/input-mode/session-transcript.tsx:18`.
- `apps/ui/src/components/ui/connection-status.tsx` — Purpose: generic API health indicator using `useApiHealth`. Key components: badge/card variants. Integration: `useApiHealth`. Risks/flaws: not referenced in baseline targets. Evidence: `apps/ui/src/components/ui/connection-status.tsx:108`.
- `apps/ui/src/components/ui/dropzone-overlay.tsx` — Purpose: generic dropzone overlay with validation and error toast. Key components: `DropzoneOverlay`. Integration: `formatFileSize`. Risks/flaws: not referenced in baseline targets. Evidence: `apps/ui/src/components/ui/dropzone-overlay.tsx:55`.
- `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx` — Purpose: bottom dock with start/cancel, transcript, question answers, upload. Key components: start button, transcript list, pending question input, upload area. Integration: workflow actions + `ScrollArea`. Risks/flaws: none noted. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx:161`, `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx:269`, `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx:346`.
- `apps/ui/src/components/views/knowledge-library/components/input-mode/dropzone-overlay.tsx` — Purpose: full-page drag/drop overlay constrained to a single markdown file. Key components: drag handlers and validation. Integration: used by InputMode. Risks/flaws: none noted. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/dropzone-overlay.tsx:54`, `apps/ui/src/components/views/knowledge-library/components/input-mode/dropzone-overlay.tsx:74`.
- `apps/ui/src/components/views/knowledge-library/components/input-mode/empty-state.tsx` — Purpose: empty state with file picker and workflow steps. Integration: `useKnowledgeLibraryStore.stageUpload`. Risks/flaws: none noted. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/empty-state.tsx:14`, `apps/ui/src/components/views/knowledge-library/components/input-mode/empty-state.tsx:18`.
- `apps/ui/src/components/views/knowledge-library/components/input-mode/execution-status.tsx` — Purpose: execution summary and errors. Integration: `useKLSession`. Risks/flaws: "View Library" action is stubbed. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/execution-status.tsx:27`, `apps/ui/src/components/views/knowledge-library/components/input-mode/execution-status.tsx:153`.
- `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx` — Purpose: Input Mode orchestration. Integration: `useSessionWorkflow`, `PlanReview`, `ControlDock`. Risks/flaws: none noted. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx:16`, `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx:65`.
- `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx` — Purpose: cleanup/routing review UI. Integration: `useKLCleanupPlan`, `useKLRoutingPlan`. Risks/flaws: decision buttons not wired. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:88`, `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:294`, `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx:457`.
- `apps/ui/src/components/views/knowledge-library/components/input-mode/session-transcript.tsx` — Purpose: transcript list with auto-scroll. Integration: `ScrollArea`. Risks/flaws: unused duplicate component. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/session-transcript.tsx:18`.
- `apps/ui/src/components/views/knowledge-library/components/input-mode/staged-upload.tsx` — Purpose: staged file card with Start/Clear. Integration: `Button`, `Card`. Risks/flaws: not used in current flow. Evidence: `apps/ui/src/components/views/knowledge-library/components/input-mode/staged-upload.tsx:19`.
- `apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx` — Purpose: Knowledge Library health badge. Integration: `useKLHealth`. Risks/flaws: missing required offline copy. Evidence: `apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx:50`.
- `apps/ui/src/components/views/knowledge-library/components/library-browser/category-tree.tsx` — Purpose: collapsible category tree. Integration: `KLLibraryCategoryResponse`. Risks/flaws: none noted. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/category-tree.tsx:18`.
- `apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx` — Purpose: file list with metadata badges. Integration: `KLLibraryFileResponse`. Risks/flaws: validation errors not displayed. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx:62`, `apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx:114`.
- `apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx` — Purpose: render file content with custom markdown. Integration: `ScrollArea`. Risks/flaws: no metadata/validation errors; no syntax highlighting library. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx:94`, `apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx:106`.
- `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx` — Purpose: three-column browser with search. Integration: `useKLLibrary`, `useKLFileContent`, store. Risks/flaws: semantic search toggle not wired. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:31`, `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx:74`.
- `apps/ui/src/components/views/knowledge-library/components/library-browser/search-bar.tsx` — Purpose: keyword/semantic toggle UI. Integration: `Input`, `Button`. Risks/flaws: toggle not wired to search logic. Evidence: `apps/ui/src/components/views/knowledge-library/components/library-browser/search-bar.tsx:42`.
- `apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx` — Purpose: answer card with sources/related topics. Integration: `SourceCitation`. Risks/flaws: plain text rendering; confidence not used. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx:33`, `apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx:44`.
- `apps/ui/src/components/views/knowledge-library/components/query-mode/chat-interface.tsx` — Purpose: chat scroll container. Integration: `ScrollArea`. Risks/flaws: not used by QueryMode. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/chat-interface.tsx:20`.
- `apps/ui/src/components/views/knowledge-library/components/query-mode/conversation-list.tsx` — Purpose: conversation history sidebar. Integration: conversation props. Risks/flaws: none noted. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/conversation-list.tsx:21`.
- `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx` — Purpose: query workflow with conversation list and message rendering. Integration: `useKLAsk`, `useKLConversations`, `AnswerCard`. Risks/flaws: local state resets; confidence not passed. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:40`, `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx:89`.
- `apps/ui/src/components/views/knowledge-library/components/query-mode/source-citation.tsx` — Purpose: link sources to Library view. Integration: `useKnowledgeLibraryStore`. Risks/flaws: none noted. Evidence: `apps/ui/src/components/views/knowledge-library/components/query-mode/source-citation.tsx:22`.
- `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts` — Purpose: session lifecycle orchestration with WebSocket and actions. Integration: `knowledgeLibraryApi`, React Query hooks, store. Risks/flaws: missing re-trigger after questions answered. Evidence: `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:402`, `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts:466`.
- `apps/ui/src/components/views/knowledge-library/index.tsx` — Purpose: Knowledge Library container with header and tabs. Integration: `KLConnectionStatus`, `Tabs`, store. Risks/flaws: none noted. Evidence: `apps/ui/src/components/views/knowledge-library/index.tsx:21`, `apps/ui/src/components/views/knowledge-library/index.tsx:33`.
- `apps/ui/src/hooks/queries/use-api-health.ts` — Purpose: core API health query. Integration: `useQuery`, `queryKeys.health`. Risks/flaws: none noted. Evidence: `apps/ui/src/hooks/queries/use-api-health.ts:44`, `apps/ui/src/hooks/queries/use-api-health.ts:71`.
- `apps/ui/tests/features/knowledge-library.spec.ts` — Purpose: Playwright E2E tests for navigation and tabs. Integration: test utils. Risks/flaws: depends on running dev server. Evidence: `apps/ui/tests/features/knowledge-library.spec.ts:26`, `apps/ui/tests/features/knowledge-library.spec.ts:54`.

### Modified files (baseline)

- `apps/ui/src/components/shared/index.ts` — Purpose: shared exports; adds SessionTranscript. Integration: barrel export. Risks/flaws: none noted. Evidence: `apps/ui/src/components/shared/index.ts:13`.
- `apps/ui/src/components/views/knowledge-hub-page/index.tsx` — Purpose: Knowledge Hub cards and navigation. Integration: `useKLHealth`. Risks/flaws: Knowledge Library count not sourced from API; offline copy not explicit. Evidence: `apps/ui/src/components/views/knowledge-hub-page/index.tsx:31`, `apps/ui/src/components/views/knowledge-hub-page/index.tsx:129`.
- `apps/ui/src/hooks/queries/index.ts` — Purpose: query hook barrel export for KL and API health hooks. Integration: `use-knowledge-library`. Risks/flaws: none noted. Evidence: `apps/ui/src/hooks/queries/index.ts:110`.
- `apps/ui/src/hooks/queries/use-knowledge-library.ts` — Purpose: KL React Query hooks for health, sessions, plans, library, query. Integration: `knowledgeLibraryApi`. Risks/flaws: none noted. Evidence: `apps/ui/src/hooks/queries/use-knowledge-library.ts:191`, `apps/ui/src/hooks/queries/use-knowledge-library.ts:300`.
- `apps/ui/src/lib/query-keys.ts` — Purpose: query key factory updates with KL keys. Integration: React Query key usage. Risks/flaws: none noted. Evidence: `apps/ui/src/lib/query-keys.ts:291`.
- `apps/ui/src/routes/knowledge-hub.$section.tsx` — Purpose: route handler for Knowledge Hub sections; routes knowledge-library to `KnowledgeLibrary`. Integration: TanStack Router. Risks/flaws: assumes `KnowledgeSectionPage` reads params internally. Evidence: `apps/ui/src/routes/knowledge-hub.$section.tsx:9`.
- `docs/Key-docs/FRONTEND_ARCHITECTURE.md` — Purpose: architecture reference. Risks/flaws: still references `blueprints` as a section ID. Evidence: `docs/Key-docs/FRONTEND_ARCHITECTURE.md:116`, `docs/Key-docs/FRONTEND_ARCHITECTURE.md:126`.
- `libs/types/src/knowledge.ts` — Purpose: Knowledge Hub type definitions; adds knowledge-library section. Risks/flaws: blueprint types remain (may conflict with "replace blueprints" intent). Evidence: `libs/types/src/knowledge.ts:13`, `libs/types/src/knowledge.ts:16`.

## Verification Results

- Command: `./start-api.sh` — Result: blocked (missing file). Output: `zsh:1: no such file or directory: ./start-api.sh`.
- Command: `npm run dev` — Result: failed (permission error writing ~/.automaker_launcher_history). Output: `start-automaker.sh: line 957: /Users/ruben/.automaker_launcher_history: Operation not permitted`.
- Test artifacts: none detected.

## Uncommitted Changes Summary (Baseline)

- git status summary (baseline): 8 modified files and 26 untracked files (Knowledge Library UI, hooks, tests).
- diffstat summary (baseline): 8 files changed, 147 insertions(+), 34 deletions(-).
- baseline created files: `apps/ui/src/components/shared/session-transcript.tsx`, `apps/ui/src/components/ui/connection-status.tsx`, `apps/ui/src/components/ui/dropzone-overlay.tsx`, `apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx`, `apps/ui/src/components/views/knowledge-library/components/input-mode/dropzone-overlay.tsx`, `apps/ui/src/components/views/knowledge-library/components/input-mode/empty-state.tsx`, `apps/ui/src/components/views/knowledge-library/components/input-mode/execution-status.tsx`, `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx`, `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx`, `apps/ui/src/components/views/knowledge-library/components/input-mode/session-transcript.tsx`, `apps/ui/src/components/views/knowledge-library/components/input-mode/staged-upload.tsx`, `apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx`, `apps/ui/src/components/views/knowledge-library/components/library-browser/category-tree.tsx`, `apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx`, `apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx`, `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx`, `apps/ui/src/components/views/knowledge-library/components/library-browser/search-bar.tsx`, `apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx`, `apps/ui/src/components/views/knowledge-library/components/query-mode/chat-interface.tsx`, `apps/ui/src/components/views/knowledge-library/components/query-mode/conversation-list.tsx`, `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx`, `apps/ui/src/components/views/knowledge-library/components/query-mode/source-citation.tsx`, `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts`, `apps/ui/src/components/views/knowledge-library/index.tsx`, `apps/ui/src/hooks/queries/use-api-health.ts`, `apps/ui/tests/features/knowledge-library.spec.ts`.
- baseline changed files: `apps/ui/src/components/shared/index.ts`, `apps/ui/src/components/views/knowledge-hub-page/index.tsx`, `apps/ui/src/hooks/queries/index.ts`, `apps/ui/src/hooks/queries/use-knowledge-library.ts`, `apps/ui/src/lib/query-keys.ts`, `apps/ui/src/routes/knowledge-hub.$section.tsx`, `docs/Key-docs/FRONTEND_ARCHITECTURE.md`, `libs/types/src/knowledge.ts`.

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

- T1 (High) Linked findings: F1. Linked plan items: P31, P16, P17. Files: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx`. Steps: wire Keep/Discard buttons to `useKLDecideCleanupItem`, update item state, and refresh cleanup plan; add visual feedback for decisions. Acceptance: cleanup decisions persist and Approve Cleanup enables once all items decided. Verification: `./start-api.sh`, `npm run dev`, manual cleanup flow in Input Mode.
- T2 (High) Linked findings: F2. Linked plan items: P32, P33, P16, P17, P35. Files: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx`. Steps: add selection handlers using `useKLSelectDestination`, add reject action using `useKLRejectBlock`, and reflect selected options in UI. Acceptance: routing options can be selected/rejected and routing approval is reachable. Verification: `./start-api.sh`, `npm run dev`, manual routing flow.
- T3 (High) Linked findings: F3. Linked plan items: P3, P16, P4. Files: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx`, `apps/ui/src/store/knowledge-library-store.ts`. Steps: implement Proposed New Files panel with Title/Overview inputs, group blocks by destination, and validate Title/Overview length/format; block approval until valid. Acceptance: create_file proposals require valid Title/Overview and approval is gated. Verification: `./start-api.sh`, `npm run dev`, manual routing with create_file proposals.
- T4 (High) Linked findings: F4. Linked plan items: P13. Files: `apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts`. Steps: after answering all pending questions, detect current phase and send `generate_cleanup` or `generate_routing`; add transcript entry for re-trigger. Acceptance: question flow resumes generation after all answers. Verification: `./start-api.sh`, `npm run dev`, manual question flow.
- T5 (Medium) Linked findings: F5. Linked plan items: P15, P34. Files: `apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx`. Steps: add Strict/Refinement toggle UI using `useKLSetMode` and display current mode. Acceptance: mode toggle changes session mode and is reflected in UI. Verification: `./start-api.sh`, `npm run dev`, manual toggle in plan review.
- T6 (Medium) Linked findings: F6. Linked plan items: P29. Files: `apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx` (and new session list component). Steps: add a session list using `useKLSessions`, allow selecting a session to resume review. Acceptance: existing sessions are visible and selectable. Verification: `./start-api.sh`, `npm run dev`, manual session list.
- T7 (Medium) Linked findings: F7. Linked plan items: P42, P44, P23. Files: `apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx`, `apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx`. Steps: render answers with markdown and pass `response.confidence` into AnswerCard. Acceptance: markdown is rendered and confidence appears. Verification: `./start-api.sh`, `npm run dev`, manual query flow.
- T8 (Medium) Linked findings: F8. Linked plan items: P4, P20. Files: `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx`, `apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx`, `apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx`. Steps: fetch file metadata, show validation errors and invalid warnings in viewer/list. Acceptance: invalid files display error details. Verification: `./start-api.sh`, `npm run dev`, manual library browse.
- T9 (Low) Linked findings: F9. Linked plan items: P5. Files: `apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx`, `apps/ui/src/components/views/knowledge-library/index.tsx`. Steps: add explicit offline banner or status text "Knowledge Library disconnected" when API offline. Acceptance: offline message is visible but non-fatal. Verification: `npm run dev`, manual API-down test.
- T10 (Low) Linked findings: F10. Linked plan items: P21. Files: `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx`. Steps: wire semantic mode to `useKLSemanticSearch` and swap displayed results based on mode. Acceptance: semantic search returns different results than keyword. Verification: `./start-api.sh`, `npm run dev`, manual semantic search.

2. Machine-readable YAML

```yaml
fix_plan:
  source_plan_file: '</Users/ruben/Documents/GitHub/automaker/.worktrees/dev-improvements/2.ai-library/Docs/Plans/sub-plan-F3-ui-components.md>'
  baseline:
    created_files:
      - 'apps/ui/src/components/shared/session-transcript.tsx'
      - 'apps/ui/src/components/ui/connection-status.tsx'
      - 'apps/ui/src/components/ui/dropzone-overlay.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/control-dock.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/dropzone-overlay.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/empty-state.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/execution-status.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/session-transcript.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/input-mode/staged-upload.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/library-browser/category-tree.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/library-browser/search-bar.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/query-mode/chat-interface.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/query-mode/conversation-list.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx'
      - 'apps/ui/src/components/views/knowledge-library/components/query-mode/source-citation.tsx'
      - 'apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts'
      - 'apps/ui/src/components/views/knowledge-library/index.tsx'
      - 'apps/ui/src/hooks/queries/use-api-health.ts'
      - 'apps/ui/tests/features/knowledge-library.spec.ts'
    changed_files:
      - 'apps/ui/src/components/shared/index.ts'
      - 'apps/ui/src/components/views/knowledge-hub-page/index.tsx'
      - 'apps/ui/src/hooks/queries/index.ts'
      - 'apps/ui/src/hooks/queries/use-knowledge-library.ts'
      - 'apps/ui/src/lib/query-keys.ts'
      - 'apps/ui/src/routes/knowledge-hub.$section.tsx'
      - 'docs/Key-docs/FRONTEND_ARCHITECTURE.md'
      - 'libs/types/src/knowledge.ts'
  findings:
    - id: 'F1'
      severity: 'High'
      summary: 'Cleanup decisions not wired'
    - id: 'F2'
      severity: 'High'
      summary: 'Routing selection/reject not wired'
    - id: 'F3'
      severity: 'High'
      summary: 'Create-file Title/Overview workflow missing'
    - id: 'F4'
      severity: 'High'
      summary: 'Question-answer flow missing re-trigger'
    - id: 'F5'
      severity: 'Medium'
      summary: 'Mode toggle missing'
    - id: 'F6'
      severity: 'Medium'
      summary: 'Session list missing'
    - id: 'F7'
      severity: 'Medium'
      summary: 'Answer markdown/confidence missing'
    - id: 'F8'
      severity: 'Medium'
      summary: 'Invalid file errors not shown'
    - id: 'F9'
      severity: 'Low'
      summary: 'Offline message copy missing'
    - id: 'F10'
      severity: 'Low'
      summary: 'Semantic search toggle not wired'
  tasks:
    - id: 'T1'
      priority: 'High'
      linked_findings: ['F1']
      linked_plan_items: ['P31', 'P16', 'P17']
      files:
        ['apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx']
      steps:
        - 'Wire Keep/Discard buttons to useKLDecideCleanupItem'
        - 'Refresh cleanup plan after decision'
        - 'Show visual state for decided items'
      acceptance:
        - 'Cleanup decisions persist and Approve Cleanup enables when all decided'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: complete cleanup decisions in Input Mode'
    - id: 'T2'
      priority: 'High'
      linked_findings: ['F2']
      linked_plan_items: ['P32', 'P33', 'P16', 'P17', 'P35']
      files:
        ['apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx']
      steps:
        - 'Wire routing option buttons to useKLSelectDestination'
        - 'Add reject action using useKLRejectBlock'
        - 'Reflect selection state per block'
      acceptance:
        - 'Routing options can be selected/rejected and approval is reachable'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: complete routing review'
    - id: 'T3'
      priority: 'High'
      linked_findings: ['F3']
      linked_plan_items: ['P3', 'P16', 'P4']
      files:
        [
          'apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx',
          'apps/ui/src/store/knowledge-library-store.ts',
        ]
      steps:
        - 'Add Proposed New Files panel with Title/Overview inputs'
        - 'Group blocks by destination and validate create_file inputs'
        - 'Block routing approval until all proposed files are valid'
      acceptance:
        - 'create_file proposals require valid Title/Overview before approval'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: verify create_file validation'
    - id: 'T4'
      priority: 'High'
      linked_findings: ['F4']
      linked_plan_items: ['P13']
      files: ['apps/ui/src/components/views/knowledge-library/hooks/use-session-workflow.ts']
      steps:
        - 'Track pending questions and current phase'
        - 'When pending questions reach zero, send generate_cleanup or generate_routing'
        - 'Add transcript entry for re-trigger'
      acceptance:
        - 'Workflow resumes automatically after all questions answered'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: answer question flow'
    - id: 'T5'
      priority: 'Medium'
      linked_findings: ['F5']
      linked_plan_items: ['P15', 'P34']
      files:
        ['apps/ui/src/components/views/knowledge-library/components/input-mode/plan-review.tsx']
      steps:
        - 'Add Strict/Refinement toggle UI'
        - 'Use useKLSetMode to update session mode'
      acceptance:
        - 'Mode toggle updates and displays session mode'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: toggle mode in Plan Review'
    - id: 'T6'
      priority: 'Medium'
      linked_findings: ['F6']
      linked_plan_items: ['P29']
      files: ['apps/ui/src/components/views/knowledge-library/components/input-mode/index.tsx']
      steps:
        - 'Add session list UI using useKLSessions'
        - 'Allow selecting a session to resume'
      acceptance:
        - 'Existing sessions are visible and selectable'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: select existing session'
    - id: 'T7'
      priority: 'Medium'
      linked_findings: ['F7']
      linked_plan_items: ['P42', 'P44', 'P23']
      files:
        [
          'apps/ui/src/components/views/knowledge-library/components/query-mode/index.tsx',
          'apps/ui/src/components/views/knowledge-library/components/query-mode/answer-card.tsx',
        ]
      steps:
        - 'Render answers with markdown'
        - 'Pass response.confidence to AnswerCard'
      acceptance:
        - 'Answers show markdown formatting and confidence'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: submit query and confirm rendering'
    - id: 'T8'
      priority: 'Medium'
      linked_findings: ['F8']
      linked_plan_items: ['P4', 'P20']
      files:
        [
          'apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx',
          'apps/ui/src/components/views/knowledge-library/components/library-browser/file-viewer.tsx',
          'apps/ui/src/components/views/knowledge-library/components/library-browser/file-list.tsx',
        ]
      steps:
        - 'Fetch file metadata for selected files'
        - 'Display validation errors and invalid warnings'
      acceptance:
        - 'Invalid files show error details in viewer/list'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: open invalid file'
    - id: 'T9'
      priority: 'Low'
      linked_findings: ['F9']
      linked_plan_items: ['P5']
      files:
        [
          'apps/ui/src/components/views/knowledge-library/components/kl-connection-status.tsx',
          'apps/ui/src/components/views/knowledge-library/index.tsx',
        ]
      steps:
        - 'Add explicit offline banner or status text'
      acceptance:
        - 'Displays "Knowledge Library disconnected" when offline'
      verification:
        - 'npm run dev'
        - 'Manual: API down state'
    - id: 'T10'
      priority: 'Low'
      linked_findings: ['F10']
      linked_plan_items: ['P21']
      files: ['apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx']
      steps:
        - 'Wire semantic mode to useKLSemanticSearch and update results'
      acceptance:
        - 'Semantic search mode changes results'
      verification:
        - './start-api.sh'
        - 'npm run dev'
        - 'Manual: semantic search'
```
