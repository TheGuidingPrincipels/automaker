# Sub-Plan F-2: API Client & Types Integration

> **Prerequisites**: Sub-Plan F-1 (Backend Setup) complete
> **Execution Location**: Automaker repository (`/Users/ruben/Documents/GitHub/automaker/`)
> **AI-Library Location**: `2.ai-library/` within automaker repository
> **Effort**: Medium (2-4 hours)
> **Next**: Sub-Plan F-3 (UI Components)

---

## Goal

Create TypeScript types, API client, TanStack Query hooks, and Zustand store for the Automaker frontend to communicate with the AI-Library backend.

---

## Step 1: Add Environment Variable

Add to `apps/ui/.env` (create if doesn't exist):

```bash
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8001
```

Update `apps/ui/.env.example`:

```bash
# AI-Library (Knowledge Library) API
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8001
```

---

## Step 2: Create Types

Create `libs/types/src/knowledge-library.ts`:

```typescript
// libs/types/src/knowledge-library.ts
// Types for AI-Library (Knowledge Library) API integration

// ============== Enums ==============

export type ContentMode = 'strict' | 'refinement';
export type SessionPhase =
  | 'created'
  | 'source_uploaded'
  | 'parsing'
  | 'cleanup_plan_ready'
  | 'routing_plan_ready'
  | 'ready_to_execute'
  | 'executing'
  | 'verifying'
  | 'completed'
  | 'failed';

export type CleanupDisposition = 'keep' | 'discard';
export type BlockStatus = 'pending' | 'selected' | 'rejected';

// ============== Session ==============

export interface KLSession {
  id: string;
  phase: SessionPhase;
  content_mode: ContentMode;
  created_at: string;
  updated_at: string;
  source_file: string | null;
  total_blocks: number;
  resolved_blocks: number;
  cleanup_approved: boolean;
  cleanup_pending: number;
  routing_pending: number;
  can_execute: boolean;
}

export interface KLSessionListResponse {
  sessions: KLSession[];
  total: number;
}

// ============== Cleanup Plan ==============

export interface KLCleanupItem {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  suggested_disposition: CleanupDisposition;
  suggestion_reason: string;
  final_disposition: CleanupDisposition | null;
}

export interface KLCleanupPlan {
  session_id: string;
  source_file: string;
  items: KLCleanupItem[];
  pending_count: number;
  all_decided: boolean;
  approved: boolean;
}

// ============== Routing Plan ==============

export interface KLDestinationOption {
  destination_file: string;
  destination_section: string | null;
  action: string;
  confidence: number;
  reasoning: string;
  proposed_file_title?: string | null;
  proposed_section_title?: string | null;
}

export interface KLBlockRouting {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  options: KLDestinationOption[];
  selected_option_index: number | null;
  custom_destination_file: string | null;
  custom_destination_section: string | null;
  custom_action: string | null;
  status: BlockStatus;
}

export interface KLMergePreview {
  merge_id: string;
  block_id: string;
  existing_content: string;
  existing_location: string;
  new_content: string;
  proposed_merge: string;
  merge_reasoning: string;
}

export interface KLPlanSummary {
  total_blocks: number;
  blocks_to_new_files: number;
  blocks_to_existing_files: number;
  blocks_requiring_merge: number;
  estimated_actions: number;
}

export interface KLRoutingPlan {
  session_id: string;
  content_mode: ContentMode;
  source_file: string;
  blocks: KLBlockRouting[];
  merge_previews: KLMergePreview[];
  summary: KLPlanSummary;
  pending_count: number;
  accepted_count: number;
  all_resolved: boolean;
}

// ============== Execution ==============

export interface KLExecuteResponse {
  success: boolean;
  blocks_written: number;
  blocks_verified: number;
  checksums_matched: number;
  refinements_applied: number;
  log: string[];
  source_deleted: boolean;
  errors: string[];
}

// ============== Library ==============

export interface KLLibraryFile {
  path: string;
  category: string;
  title: string;
  sections: string[];
  last_modified: string;
  block_count: number;
}

export interface KLLibraryCategory {
  name: string;
  path: string;
  description: string;
  files: KLLibraryFile[];
  subcategories: KLLibraryCategory[];
}

export interface KLLibraryStructure {
  root_path: string;
  categories: KLLibraryCategory[];
  total_files: number;
  total_blocks: number;
}

export interface KLSearchResult {
  content: string;
  file_path: string;
  section: string;
  similarity: number;
  chunk_id: string;
}

export interface KLSearchResponse {
  query: string;
  results: KLSearchResult[];
  total: number;
}

// ============== Query (RAG) ==============

export interface KLSourceInfo {
  file: string;
  section: string;
  excerpt: string;
}

export interface KLQueryResponse {
  answer: string;
  sources: KLSourceInfo[];
  confidence: number;
  conversation_id: string;
  related_topics: string[];
}

export interface KLConversationTurn {
  question: string;
  answer: string;
  sources: KLSourceInfo[];
  timestamp: string;
}

export interface KLConversation {
  id: string;
  created_at: string;
  turns: KLConversationTurn[];
}

// ============== Request Types ==============

export interface KLCreateSessionInput {
  library_path?: string;
}

export interface KLCleanupDecisionInput {
  disposition: CleanupDisposition;
}

export interface KLSelectDestinationInput {
  option_index?: number;
  custom_destination_file?: string;
  custom_destination_section?: string | null;
  custom_action?: string;
}

export interface KLSetModeInput {
  mode: ContentMode;
}

export interface KLQueryInput {
  question: string;
  conversation_id?: string;
  n_chunks?: number;
  min_similarity?: number;
}

export interface KLExecuteInput {
  delete_source?: boolean;
}
```

Export from `libs/types/src/index.ts`:

```typescript
// Add to existing exports
export * from './knowledge-library';
```

---

## Step 3: Create API Client

Create `apps/ui/src/lib/knowledge-library-api.ts`:

```typescript
// apps/ui/src/lib/knowledge-library-api.ts

import type {
  KLSession,
  KLSessionListResponse,
  KLCleanupPlan,
  KLRoutingPlan,
  KLExecuteResponse,
  KLLibraryStructure,
  KLSearchResponse,
  KLQueryResponse,
  KLConversation,
  KLCreateSessionInput,
  KLCleanupDecisionInput,
  KLSelectDestinationInput,
  KLSetModeInput,
  KLQueryInput,
  KLExecuteInput,
} from '@automaker/types';

const API_BASE = import.meta.env.VITE_KNOWLEDGE_LIBRARY_API || 'http://localhost:8001';

class KnowledgeLibraryAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  // ============== Health ==============

  async healthCheck(): Promise<{ status: string }> {
    return this.request('/health');
  }

  // ============== Sessions ==============

  async listSessions(limit = 20): Promise<KLSessionListResponse> {
    return this.request(`/api/sessions?limit=${limit}`);
  }

  async getSession(sessionId: string): Promise<KLSession> {
    return this.request(`/api/sessions/${sessionId}`);
  }

  async createSession(input?: KLCreateSessionInput): Promise<KLSession> {
    return this.request('/api/sessions', {
      method: 'POST',
      body: JSON.stringify(input || {}),
    });
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.request(`/api/sessions/${sessionId}`, { method: 'DELETE' });
  }

  async uploadSource(sessionId: string, file: File): Promise<KLSession> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Upload failed');
    }
    return response.json();
  }

  // ============== Cleanup Plan ==============

  async generateCleanupPlan(sessionId: string): Promise<KLCleanupPlan> {
    return this.request(`/api/sessions/${sessionId}/cleanup/generate`, {
      method: 'POST',
    });
  }

  async getCleanupPlan(sessionId: string): Promise<KLCleanupPlan> {
    return this.request(`/api/sessions/${sessionId}/cleanup`);
  }

  async decideCleanupItem(
    sessionId: string,
    blockId: string,
    input: KLCleanupDecisionInput
  ): Promise<void> {
    await this.request(`/api/sessions/${sessionId}/cleanup/decide/${blockId}`, {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async approveCleanupPlan(sessionId: string): Promise<void> {
    await this.request(`/api/sessions/${sessionId}/cleanup/approve`, {
      method: 'POST',
    });
  }

  // ============== Routing Plan ==============

  async generateRoutingPlan(sessionId: string): Promise<KLRoutingPlan> {
    return this.request(`/api/sessions/${sessionId}/plan/generate`, {
      method: 'POST',
    });
  }

  async getRoutingPlan(sessionId: string): Promise<KLRoutingPlan> {
    return this.request(`/api/sessions/${sessionId}/plan`);
  }

  async selectBlockDestination(
    sessionId: string,
    blockId: string,
    input: KLSelectDestinationInput
  ): Promise<void> {
    await this.request(`/api/sessions/${sessionId}/plan/select/${blockId}`, {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async rejectBlock(sessionId: string, blockId: string): Promise<void> {
    await this.request(`/api/sessions/${sessionId}/plan/reject-block/${blockId}`, {
      method: 'POST',
    });
  }

  async setContentMode(sessionId: string, input: KLSetModeInput): Promise<void> {
    await this.request(`/api/sessions/${sessionId}/mode`, {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  // ============== Execution ==============

  async executeSession(sessionId: string, input?: KLExecuteInput): Promise<KLExecuteResponse> {
    return this.request(`/api/sessions/${sessionId}/execute`, {
      method: 'POST',
      body: JSON.stringify(input || {}),
    });
  }

  // ============== Library ==============

  async getLibraryStructure(): Promise<KLLibraryStructure> {
    return this.request('/api/library');
  }

  async getFile(path: string): Promise<{ content: string; metadata: any }> {
    return this.request(`/api/library/files/${encodeURIComponent(path)}`);
  }

  async searchLibrary(query: string, limit = 10): Promise<KLSearchResponse> {
    return this.request(`/api/library/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  async triggerIndex(): Promise<{ status: string }> {
    return this.request('/api/library/index', { method: 'POST' });
  }

  // ============== Query (RAG) ==============

  async queryLibrary(input: KLQueryInput): Promise<KLQueryResponse> {
    return this.request('/api/query/ask', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async semanticSearch(query: string, limit = 10): Promise<KLSearchResponse> {
    return this.request(`/api/query/search?query=${encodeURIComponent(query)}&limit=${limit}`, {
      method: 'POST',
    });
  }

  async listConversations(limit = 20): Promise<KLConversation[]> {
    return this.request(`/api/query/conversations?limit=${limit}`);
  }

  async getConversation(conversationId: string): Promise<KLConversation> {
    return this.request(`/api/query/conversations/${conversationId}`);
  }

  async deleteConversation(conversationId: string): Promise<void> {
    await this.request(`/api/query/conversations/${conversationId}`, {
      method: 'DELETE',
    });
  }

  // ============== WebSocket ==============

  connectToSession(sessionId: string): WebSocket {
    const wsUrl = this.baseUrl.replace('http', 'ws');
    return new WebSocket(`${wsUrl}/api/sessions/${sessionId}/stream`);
  }
}

export const knowledgeLibraryApi = new KnowledgeLibraryAPI();
export default knowledgeLibraryApi;
```

---

## Step 4: Create TanStack Query Hooks

Create `apps/ui/src/hooks/queries/use-knowledge-library.ts`:

```typescript
// apps/ui/src/hooks/queries/use-knowledge-library.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeLibraryApi } from '@/lib/knowledge-library-api';
import type {
  KLCleanupDecisionInput,
  KLSelectDestinationInput,
  KLSetModeInput,
  KLQueryInput,
  ContentMode,
} from '@automaker/types';

// ============== Query Keys ==============

export const klKeys = {
  all: ['knowledge-library'] as const,
  health: () => [...klKeys.all, 'health'] as const,
  sessions: () => [...klKeys.all, 'sessions'] as const,
  session: (id: string) => [...klKeys.all, 'session', id] as const,
  cleanup: (id: string) => [...klKeys.all, 'cleanup', id] as const,
  plan: (id: string) => [...klKeys.all, 'plan', id] as const,
  library: () => [...klKeys.all, 'library'] as const,
  file: (path: string) => [...klKeys.all, 'file', path] as const,
  search: (query: string) => [...klKeys.all, 'search', query] as const,
  conversations: () => [...klKeys.all, 'conversations'] as const,
  conversation: (id: string) => [...klKeys.all, 'conversation', id] as const,
};

// ============== Health ==============

export function useKLHealth() {
  return useQuery({
    queryKey: klKeys.health(),
    queryFn: () => knowledgeLibraryApi.healthCheck(),
    retry: 1,
    staleTime: 30000,
  });
}

// ============== Sessions ==============

export function useKLSessions(limit = 20) {
  return useQuery({
    queryKey: klKeys.sessions(),
    queryFn: () => knowledgeLibraryApi.listSessions(limit),
  });
}

export function useKLSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: klKeys.session(sessionId!),
    queryFn: () => knowledgeLibraryApi.getSession(sessionId!),
    enabled: !!sessionId,
    refetchInterval: 2000, // Poll for updates during active sessions
  });
}

export function useKLCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (libraryPath?: string) =>
      knowledgeLibraryApi.createSession({ library_path: libraryPath }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.sessions() });
    },
  });
}

export function useKLDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => knowledgeLibraryApi.deleteSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.sessions() });
    },
  });
}

export function useKLUploadSource(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => knowledgeLibraryApi.uploadSource(sessionId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.session(sessionId) });
    },
  });
}

// ============== Cleanup Plan ==============

export function useKLCleanupPlan(sessionId: string | undefined) {
  return useQuery({
    queryKey: klKeys.cleanup(sessionId!),
    queryFn: () => knowledgeLibraryApi.getCleanupPlan(sessionId!),
    enabled: !!sessionId,
  });
}

export function useKLGenerateCleanupPlan(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => knowledgeLibraryApi.generateCleanupPlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.cleanup(sessionId) });
      queryClient.invalidateQueries({ queryKey: klKeys.session(sessionId) });
    },
  });
}

export function useKLDecideCleanupItem(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ blockId, disposition }: { blockId: string; disposition: 'keep' | 'discard' }) =>
      knowledgeLibraryApi.decideCleanupItem(sessionId, blockId, { disposition }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.cleanup(sessionId) });
    },
  });
}

export function useKLApproveCleanupPlan(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => knowledgeLibraryApi.approveCleanupPlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.cleanup(sessionId) });
      queryClient.invalidateQueries({ queryKey: klKeys.session(sessionId) });
    },
  });
}

// ============== Routing Plan ==============

export function useKLRoutingPlan(sessionId: string | undefined) {
  return useQuery({
    queryKey: klKeys.plan(sessionId!),
    queryFn: () => knowledgeLibraryApi.getRoutingPlan(sessionId!),
    enabled: !!sessionId,
    refetchInterval: 2000,
  });
}

export function useKLGenerateRoutingPlan(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => knowledgeLibraryApi.generateRoutingPlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.plan(sessionId) });
      queryClient.invalidateQueries({ queryKey: klKeys.session(sessionId) });
    },
  });
}

export function useKLSelectDestination(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ blockId, ...input }: { blockId: string } & KLSelectDestinationInput) =>
      knowledgeLibraryApi.selectBlockDestination(sessionId, blockId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.plan(sessionId) });
    },
  });
}

export function useKLRejectBlock(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (blockId: string) => knowledgeLibraryApi.rejectBlock(sessionId, blockId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.plan(sessionId) });
    },
  });
}

export function useKLSetContentMode(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mode: ContentMode) => knowledgeLibraryApi.setContentMode(sessionId, { mode }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.plan(sessionId) });
      queryClient.invalidateQueries({ queryKey: klKeys.session(sessionId) });
    },
  });
}

// ============== Execution ==============

export function useKLExecuteSession(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (deleteSource = false) =>
      knowledgeLibraryApi.executeSession(sessionId, { delete_source: deleteSource }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.session(sessionId) });
      queryClient.invalidateQueries({ queryKey: klKeys.library() });
    },
  });
}

// ============== Library ==============

export function useKLLibrary() {
  return useQuery({
    queryKey: klKeys.library(),
    queryFn: () => knowledgeLibraryApi.getLibraryStructure(),
  });
}

export function useKLFile(path: string | undefined) {
  return useQuery({
    queryKey: klKeys.file(path!),
    queryFn: () => knowledgeLibraryApi.getFile(path!),
    enabled: !!path,
  });
}

export function useKLSearch(query: string, enabled = true) {
  return useQuery({
    queryKey: klKeys.search(query),
    queryFn: () => knowledgeLibraryApi.searchLibrary(query),
    enabled: enabled && query.length > 2,
  });
}

// ============== Query (RAG) ==============

export function useKLQueryLibrary() {
  return useMutation({
    mutationFn: (input: KLQueryInput) => knowledgeLibraryApi.queryLibrary(input),
  });
}

export function useKLConversations(limit = 20) {
  return useQuery({
    queryKey: klKeys.conversations(),
    queryFn: () => knowledgeLibraryApi.listConversations(limit),
  });
}

export function useKLConversation(conversationId: string | undefined) {
  return useQuery({
    queryKey: klKeys.conversation(conversationId!),
    queryFn: () => knowledgeLibraryApi.getConversation(conversationId!),
    enabled: !!conversationId,
  });
}

export function useKLDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) => knowledgeLibraryApi.deleteConversation(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: klKeys.conversations() });
    },
  });
}
```

---

## Step 5: Create Zustand Store

Create `apps/ui/src/store/knowledge-library-store.ts`:

```typescript
// apps/ui/src/store/knowledge-library-store.ts

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { KLMergePreview, KLQueryResponse } from '@automaker/types';

// ============== Types ==============

type KLView = 'input' | 'library' | 'query';

interface KnowledgeLibraryState {
  // Active view
  activeView: KLView;
  setActiveView: (view: KLView) => void;

  // Current session (for input mode)
  currentSessionId: string | null;
  setCurrentSession: (sessionId: string | null) => void;

  // Block selection
  selectedBlockId: string | null;
  selectBlock: (blockId: string | null) => void;

  // Merge dialog
  mergeDialogOpen: boolean;
  selectedMerge: KLMergePreview | null;
  openMergeDialog: (merge: KLMergePreview) => void;
  closeMergeDialog: () => void;

  // Library browser
  selectedFilePath: string | null;
  setSelectedFile: (path: string | null) => void;

  // Query mode
  currentConversationId: string | null;
  queryHistory: KLQueryResponse[];
  setConversation: (conversationId: string | null) => void;
  addQueryResult: (result: KLQueryResponse) => void;
  clearQueryHistory: () => void;

  // Search
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

// ============== Store ==============

export const useKnowledgeLibraryStore = create<KnowledgeLibraryState>()(
  devtools(
    persist(
      (set) => ({
        // Active view
        activeView: 'library',
        setActiveView: (view) => set({ activeView: view }),

        // Current session
        currentSessionId: null,
        setCurrentSession: (sessionId) => set({ currentSessionId: sessionId }),

        // Block selection
        selectedBlockId: null,
        selectBlock: (blockId) => set({ selectedBlockId: blockId }),

        // Merge dialog
        mergeDialogOpen: false,
        selectedMerge: null,
        openMergeDialog: (merge) => set({ mergeDialogOpen: true, selectedMerge: merge }),
        closeMergeDialog: () => set({ mergeDialogOpen: false, selectedMerge: null }),

        // Library browser
        selectedFilePath: null,
        setSelectedFile: (path) => set({ selectedFilePath: path }),

        // Query mode
        currentConversationId: null,
        queryHistory: [],
        setConversation: (conversationId) => set({ currentConversationId: conversationId }),
        addQueryResult: (result) =>
          set((state) => ({
            queryHistory: [...state.queryHistory, result],
            currentConversationId: result.conversation_id,
          })),
        clearQueryHistory: () => set({ queryHistory: [], currentConversationId: null }),

        // Search
        searchQuery: '',
        setSearchQuery: (query) => set({ searchQuery: query }),
      }),
      {
        name: 'knowledge-library-storage',
        partialize: (state) => ({
          currentSessionId: state.currentSessionId,
          currentConversationId: state.currentConversationId,
          activeView: state.activeView,
        }),
      }
    ),
    { name: 'KnowledgeLibraryStore' }
  )
);
```

---

## Acceptance Criteria

- [ ] Environment variable `VITE_KNOWLEDGE_LIBRARY_API` configured
- [ ] TypeScript types created in `libs/types/src/knowledge-library.ts`
- [ ] Types exported from `libs/types/src/index.ts`
- [ ] API client created in `apps/ui/src/lib/knowledge-library-api.ts`
- [ ] TanStack Query hooks created
- [ ] Zustand store created
- [ ] Health check hook works: `useKLHealth()` returns `{ status: 'healthy' }`
- [ ] Sessions can be listed: `useKLSessions()` returns sessions array

---

## Testing the Integration

After implementing, test the connection:

```typescript
// In a React component or test file
import { useKLHealth, useKLLibrary } from '@/hooks/queries/use-knowledge-library';

function TestConnection() {
  const health = useKLHealth();
  const library = useKLLibrary();

  if (health.isLoading) return <div>Checking API connection...</div>;
  if (health.error) return <div>API not available: {health.error.message}</div>;

  return (
    <div>
      <p>API Status: {health.data?.status}</p>
      <p>Library Files: {library.data?.total_files ?? 'Loading...'}</p>
    </div>
  );
}
```

---

## Notes for Sub-Plan F-3

The UI components will use:

- `useKnowledgeLibraryStore()` for local UI state
- `useKL*` hooks for server state
- Types from `@automaker/types` for type safety

---

_End of Sub-Plan F-2_
