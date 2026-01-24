# Sub-Plan F-2: API Client & Types Integration (Knowledge Library)

> **Prerequisites**: Sub-Plan F-1 (Backend Setup) complete, including the “Upload-first session” and “New file Overview metadata” backend contract updates.
> **Execution Location**: Automaker repository (`/Users/ruben/Documents/GitHub/automaker/`)
> **AI-Library Location**: `2.ai-library/` within automaker repository
> **Effort**: Medium (2-4 hours)
> **Next**: Sub-Plan F-3 (UI Components)

---

## Scope (V1)

Implement the **upload-only** ingestion workflow (one markdown file per session). Pasted content / append-to-session is deferred to a later plan to avoid breaking changes.

**Important**: This plan assumes Sub-Plan F-1 has implemented the required backend contract updates (upload-first sessions, persisted uploads, create-file Title+Overview metadata, and library file validation fields).

---

## Goal

Create:

1. Shared TypeScript types for the Knowledge Library API
2. A typed API client for the UI
3. TanStack Query hooks for server state
4. A small Zustand store for UI-only state

This must be compatible with Sub-Plan F-3’s UI requirements:

- Upload-first session flow (drag/drop or file picker)
- Explicit cleanup approvals (checkbox decisions)
- Explicit routing approvals (after all blocks resolved)
- Create-file UX requires **Title** + **`## Overview` (exact, case-sensitive)** with **50–250 chars** (trimmed, whitespace-normalized)
- Library files missing valid `## Overview` show red badge + errors (but routing into them is allowed)
- If Knowledge Library API is offline, show “Knowledge Library disconnected” (non-fatal)
- Input Mode includes a chat transcript + user “guidance” messages to influence planning (not ingestion)
  - Guidance is required for routing, optional for cleanup (easy to include in both)
  - Claude “questions” are supported via WS `question` events + user `answer` commands

---

## Step 1: Environment Variables & Typings

### 1.1 Add env var (local)

Add to `apps/ui/.env` (create if needed):

```bash
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8001
```

### 1.2 Add env var typings (required)

Update `apps/ui/src/vite-env.d.ts` to include:

- `VITE_KNOWLEDGE_LIBRARY_API?: string`

### 1.3 Decide on `.env.example`

If you want `apps/ui/.env.example` committed, update `apps/ui/.gitignore` to allow it (currently `.env*` is ignored).

---

## Step 2: Create Shared Types (Mirror Backend Schemas)

Create `libs/types/src/knowledge-library.ts` with shapes matching `2.ai-library/src/api/schemas.py` and the additional create-file metadata rules.

**Note:** this repo uses NodeNext-style `.js` specifiers in exports (see `libs/types/src/index.ts`). Keep the export style consistent.

```ts
// libs/types/src/knowledge-library.ts

// ============== Core ==============
export type ContentMode = 'strict' | 'refinement';
export type CleanupDisposition = 'keep' | 'discard';
export type BlockStatus = 'pending' | 'selected' | 'rejected';

export type SessionPhase =
  | 'initialized'
  | 'parsing'
  | 'cleanup_plan_ready'
  | 'routing_plan_ready'
  | 'awaiting_approval'
  | 'ready_to_execute'
  | 'executing'
  | 'verifying'
  | 'completed'
  | 'error';

export interface KLSuccessResponse {
  success: boolean;
  message?: string | null;
}

// ============== Sessions ==============

export interface KLCreateSessionRequest {
  // V1: upload-only. Create empty session for upload-first flow.
  library_path?: string | null;
  content_mode?: ContentMode | null;

  // Optional (server-local). Kept for backwards compatibility if used.
  source_path?: string | null;
}

export interface KLSessionResponse {
  id: string;
  phase: SessionPhase;
  created_at: string;
  updated_at: string;
  content_mode: ContentMode;
  library_path: string;
  source_file: string | null;

  total_blocks: number;
  kept_blocks: number;
  discarded_blocks: number;

  has_cleanup_plan: boolean;
  has_routing_plan: boolean;
  cleanup_approved: boolean;
  routing_approved: boolean;
  can_execute: boolean;

  errors: string[];
}

export interface KLSessionListResponse {
  sessions: KLSessionResponse[];
  total: number;
}

// ============== Blocks ==============

export interface KLBlockResponse {
  id: string;
  block_type: string;
  content: string;
  content_preview: string;
  heading_path: string[];
  source_file: string;
  source_line_start: number;
  source_line_end: number;
  checksum_exact: string;
  checksum_canonical: string;
  is_executed: boolean;
  integrity_verified: boolean;
}

export interface KLBlockListResponse {
  blocks: KLBlockResponse[];
  total: number;
}

// ============== Cleanup ==============

export interface KLCleanupItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  suggested_disposition: CleanupDisposition;
  suggestion_reason: string;
  final_disposition: CleanupDisposition | null;
}

export interface KLCleanupPlanResponse {
  session_id: string;
  source_file: string;
  created_at: string;
  items: KLCleanupItemResponse[];
  all_decided: boolean;
  approved: boolean;
  approved_at: string | null;
  pending_count: number;
  total_count: number;
}

export interface KLCleanupDecisionRequest {
  disposition: CleanupDisposition;
}

// ============== Routing ==============

export interface KLDestinationOptionResponse {
  destination_file: string;
  destination_section: string | null;
  action: string;
  confidence: number;
  reasoning: string;

  // Create-section
  proposed_section_title?: string | null;

  // Create-file (REQUIRED when action === "create_file")
  proposed_file_title?: string | null;
  proposed_file_overview?: string | null; // 50–250 chars (trim+normalize)
}

export interface KLBlockRoutingItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  options: KLDestinationOptionResponse[];
  selected_option_index: number | null;
  custom_destination_file: string | null;
  custom_destination_section: string | null;
  custom_action: string | null;
  status: BlockStatus;

  // If a create-file option was selected, allow UI to override metadata:
  override_file_title?: string | null;
  override_file_overview?: string | null;

  // If user chose custom create-file:
  custom_file_title?: string | null;
  custom_file_overview?: string | null;
}

export interface KLMergePreviewResponse {
  merge_id: string;
  block_id: string;
  existing_content: string;
  existing_location: string;
  new_content: string;
  proposed_merge: string;
  merge_reasoning: string;
}

export interface KLPlanSummaryResponse {
  total_blocks: number;
  blocks_to_new_files: number;
  blocks_to_existing_files: number;
  blocks_requiring_merge: number;
  estimated_actions: number;
}

export interface KLRoutingPlanResponse {
  session_id: string;
  source_file: string;
  content_mode: ContentMode;
  created_at: string;
  blocks: KLBlockRoutingItemResponse[];
  merge_previews: KLMergePreviewResponse[];
  summary: KLPlanSummaryResponse | null;
  all_blocks_resolved: boolean;
  approved: boolean;
  approved_at: string | null;
  pending_count: number;
  accepted_count: number;
}

export interface KLSelectDestinationRequest {
  option_index?: number | null;
  custom_file?: string | null;
  custom_section?: string | null;
  custom_action?: string | null;

  // REQUIRED when selecting a create_file option (UI editable fields)
  override_file_title?: string | null;
  override_file_overview?: string | null;

  // REQUIRED when custom_action === "create_file"
  custom_file_title?: string | null;
  custom_file_overview?: string | null;
}

export interface KLSetModeRequest {
  mode: ContentMode;
}

// ============== Execution ==============

export interface KLWriteResultResponse {
  block_id: string;
  destination_file: string;
  success: boolean;
  checksum_verified: boolean;
  error?: string | null;
}

export interface KLExecuteResponse {
  session_id: string;
  success: boolean;
  total_blocks: number;
  blocks_written: number;
  blocks_failed: number;
  all_verified: boolean;
  results: KLWriteResultResponse[];
  errors: string[];
}

// ============== Library ==============

export interface KLLibraryFileResponse {
  path: string;
  category: string;
  title: string;
  sections: string[];
  last_modified: string;
  block_count: number;

  // Overview metadata
  overview: string | null;
  is_valid: boolean;
  validation_errors: string[];
}

export interface KLLibraryCategoryResponse {
  name: string;
  path: string;
  description: string;
  files: KLLibraryFileResponse[];
  subcategories: KLLibraryCategoryResponse[];
}

export interface KLLibraryStructureResponse {
  categories: KLLibraryCategoryResponse[];
  total_files: number;
  total_sections: number;
}

export interface KLLibraryFileContentResponse {
  content: string;
  path: string;
}

export interface KLLibrarySearchResult {
  file_path: string;
  file_title: string;
  section: string;
  category: string;
}

export interface KLLibrarySearchResponse {
  results: KLLibrarySearchResult[];
  query: string;
  total: number;
}

export interface KLIndexResponse {
  status: string;
  files_indexed: number;
  details?: string[] | null;
}

// ============== Query (RAG + Semantic) ==============

export interface KLSemanticSearchRequest {
  query: string;
  n_results?: number;
  min_similarity?: number;
  filter_taxonomy?: string | null;
  filter_content_type?: string | null;
}

export interface KLSemanticSearchResult {
  content: string;
  file_path: string;
  section: string;
  similarity: number;
  chunk_id: string;
  taxonomy_path?: string | null;
  content_type?: string | null;
}

export interface KLSemanticSearchResponse {
  results: KLSemanticSearchResult[];
  query: string;
  total: number;
}

export interface KLAskRequest {
  question: string;
  max_sources?: number;
  conversation_id?: string | null;
}

export interface KLAskSourceInfo {
  file_path: string;
  section?: string | null;
  similarity?: number | null;
}

export interface KLAskResponse {
  answer: string;
  sources: KLAskSourceInfo[];
  confidence: number;
  conversation_id?: string | null;
  related_topics: string[];
}

export interface KLConversationTurn {
  role: string;
  content: string;
  timestamp: string;
  sources: string[];
}

export interface KLConversation {
  id: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
  turns: KLConversationTurn[];
}

export interface KLConversationListResponse {
  conversations: KLConversation[];
  total: number;
}

// ============== Streaming (WebSocket) ==============

export type KLStreamEventType =
  | 'connected'
  | 'pong'
  | 'progress'
  | 'cleanup_started'
  | 'cleanup_ready'
  | 'routing_started'
  | 'routing_ready'
  | 'candidate_search'
  | 'user_message'
  | 'question'
  | 'error'
  | string; // forward-compatible

export interface KLStreamEvent {
  event_type: KLStreamEventType;
  session_id: string;
  data: {
    // Human-readable text suitable for the Input Mode “chat transcript”
    message?: string;

    // Optional progress indicator (backend currently sends null)
    progress?: number | null;

    // Event payload (e.g., cleanup_plan / routing_plan model_dump)
    data?: unknown;

    // Optional initial connect info
    phase?: string;

    // Optional (future) question flow
    question_id?: string;
  };

  // Preferred: include timestamp (ISO string). Current backend messages may omit this until F-1 is applied.
  timestamp?: string;
}

export type KLStreamCommand =
  | 'generate_cleanup'
  | 'generate_routing'
  | 'ping'
  | 'user_message'
  | 'answer';

export interface KLStreamCommandRequest {
  command: KLStreamCommand;

  // user_message
  message?: string;

  // answer (future)
  question_id?: string;
}
```

Export from `libs/types/src/index.ts` using the same style as the file (NodeNext `.js` specifiers). Example:

```ts
export * from './knowledge-library.js';
```

---

## Step 3: Create API Client

Create `apps/ui/src/lib/knowledge-library-api.ts`.

### 3.1 Non-fatal “disconnected” behavior (required)

When `fetch()` throws a connection error (TypeError / failed to fetch), throw a Knowledge-Library-specific error so the app does **not** treat it as “Automaker server offline”.

### 3.2 Endpoints (must match backend)

- Health: `GET /health`
- Sessions:
  - `GET /api/sessions`
  - `POST /api/sessions` (create empty session; upload-first)
  - `POST /api/sessions/{id}/upload`
  - `GET /api/sessions/{id}`
  - `DELETE /api/sessions/{id}`
  - `GET /api/sessions/{id}/blocks`
  - Cleanup:
    - `POST /api/sessions/{id}/cleanup/generate?use_ai=true`
    - `GET /api/sessions/{id}/cleanup`
    - `POST /api/sessions/{id}/cleanup/decide/{block_id}`
    - `POST /api/sessions/{id}/cleanup/approve`
  - Routing:
    - `POST /api/sessions/{id}/plan/generate?use_ai=true&use_candidate_finder=true`
    - `GET /api/sessions/{id}/plan`
    - `POST /api/sessions/{id}/plan/select/{block_id}` (includes create-file title+overview overrides)
    - `POST /api/sessions/{id}/plan/reject-block/{block_id}`
    - `POST /api/sessions/{id}/plan/approve` (required before execute)
  - Mode:
    - `POST /api/sessions/{id}/mode`
  - Execute:
    - `POST /api/sessions/{id}/execute`
  - WebSocket:
    - `WS /api/sessions/{id}/stream`
- Library:
  - `GET /api/library`
  - `GET /api/library/files/{file_path:path}` (metadata)
  - `GET /api/library/files/{file_path:path}/content` (content)
  - `GET /api/library/search?query=...` (keyword)
  - `POST /api/library/index` and `GET /api/library/index/stats`
- Query:
  - `POST /api/query/search` (semantic, JSON body)
  - `POST /api/query/ask`
  - `GET /api/query/conversations` (returns `{ conversations, total }`)
  - `GET /api/query/conversations/{id}`
  - `DELETE /api/query/conversations/{id}`

**Important**: for `{file_path:path}` routes, do NOT `encodeURIComponent()` the entire path (it encodes `/`). Encode per path-segment:

```ts
const encodePath = (p: string) => p.split('/').map(encodeURIComponent).join('/');
```

### 3.3 WebSocket helpers (required for Input Mode transcript)

Add a small helper in `knowledgeLibraryApi`:

- `getSessionStreamUrl(sessionId)`:
  - Convert base URL `http(s)://...` → `ws(s)://...`
  - Append `/api/sessions/{id}/stream`
- `openSessionStream(sessionId, handlers)`:
  - Creates a `WebSocket`
  - Parses messages as `KLStreamEvent`
  - Never triggers Automaker global “server offline” UX; treat failures as Knowledge Library disconnected

Also add a small helper for chat guidance messages:

- `sendUserMessage(ws, message)`:
  - sends `{ command: "user_message", message }`
  - UI should also append the user message locally to the transcript immediately (optimistic)

---

## Step 4: Create TanStack Query Hooks

Create `apps/ui/src/hooks/queries/use-knowledge-library.ts`.

Required hooks for F-3:

- `useKLHealth()`
- `useKLSessions()`, `useKLSession(id)`
- `useKLCreateSession()`, `useKLUploadSource(sessionId)`
- `useKLBlocks(sessionId)`
- `useKLGenerateCleanupPlan(sessionId)`, `useKLCleanupPlan(sessionId)`, `useKLDecideCleanupItem(sessionId)`, `useKLApproveCleanupPlan(sessionId)`
- `useKLGenerateRoutingPlan(sessionId)`, `useKLRoutingPlan(sessionId)`
- `useKLSelectDestination(sessionId)`, `useKLRejectBlock(sessionId)`, `useKLApproveRoutingPlan(sessionId)`
- `useKLExecuteSession(sessionId)`
- Library:
  - `useKLLibrary()`
  - `useKLFileMetadata(path)`
  - `useKLFileContent(path)`
  - `useKLLibraryKeywordSearch(query)`
- Semantic:
  - `useKLSemanticSearch()` (mutation) and/or query hook

Streaming (WebSocket) is not a TanStack Query concern. Add a dedicated hook:

- `useKLSessionStream(sessionId)` (new file recommended: `apps/ui/src/hooks/streams/use-kl-session-stream.ts`)
  - Manages `WebSocket` lifecycle + reconnection strategy
  - Exposes `events` (for transcript), `isConnected`, and `send(command)`
  - Exposes `pendingQuestions` (derived from one or more `question` events) so the UI can render an “Answer” affordance

Query keys must include parameters (e.g. `limit`, `path`, `query`) to avoid cache collisions.

---

## Step 5: Create Zustand Store (UI-only State)

Create `apps/ui/src/store/knowledge-library-store.ts`.

Required UI state for the upload-first workflow:

- `activeView` (if using tabs)
- `currentSessionId`
- `stagedUpload: { file: File; fileName: string } | null` (do NOT persist File objects)
- `selectedBlockId`
- `proposedNewFiles: Record<string, { title: string; overview: string; isValid: boolean; errors: string[] }>`
- `sessionTranscript: Array<{ id: string; role: 'system' | 'assistant' | 'user'; content: string; timestamp?: string; level?: 'info' | 'error' }>`
- `draftUserMessage: string` (Input Mode “chat” input value)
- `activeRoutingGroupKey: string | null` (for grouping blocks by proposed destination file)

Persist only stable primitives (`activeView`, `currentSessionId`) as needed.

---

## Acceptance Criteria

- [ ] `VITE_KNOWLEDGE_LIBRARY_API` works and is typed in `apps/ui/src/vite-env.d.ts`
- [ ] Types match backend schemas and include create-file `title + overview` metadata
- [ ] Client hits the correct endpoints and supports upload-first session flow
- [ ] `create_file` selections enforce required `Title` + `## Overview` (50–250 chars)
- [ ] Hooks cover blocks + cleanup + routing approval + execution
- [ ] WebSocket stream can drive an Input Mode transcript/log (`connected`, progress, ready, error)
- [ ] WebSocket supports user guidance + question/answer (`user_message`, `question`, `answer`)
- [ ] Knowledge Library offline shows “disconnected” (non-fatal), not global “server offline”

---

## Notes for Sub-Plan F-3

F-3’s “Proposed New Files” panel depends on:

- Routing plan options including `proposed_file_title` + `proposed_file_overview`
- `plan/select/{block_id}` accepting `override_file_title/overview` and `custom_file_title/overview`
- Library file metadata including `overview`, `is_valid`, and `validation_errors` for red badges

---

_End of Sub-Plan F-2_
