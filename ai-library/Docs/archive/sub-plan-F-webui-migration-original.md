# Sub-Plan F: Web UI + Migration (Phase 5)

> **Master Plan Reference**: `knowledge-library-master-plan.md`
> **Execution Location**: `/Users/ruben/Documents/GitHub/automaker` (different repository)
> **Dependencies**: Sub-Plans A-E must be completed in `knowledge-library` first
> **This is the FINAL phase**

---

## Goal

1. **Migrate** the complete backend from `knowledge-library` to the `automaker` repository
2. **Integrate** the Knowledge Library UI into the existing React/TypeScript application

### Key UI Changes

- **Single plan review screen** showing ALL blocks at once
- **Per-block Accept/Reject/Custom controls** for routing decisions
- **Mode toggle** (Strict/Refinement) at session level
- **AI re-routing** when none of the top-3 options fit (structured feedback; no typing required)
- **Verification results display** after execution with checksum status

---

## Prerequisites

Before starting this phase, ensure ALL of the following are complete in the `knowledge-library` repository:

- [ ] **Sub-Plan A**: Core Engine - All models, session management, strict verification
- [ ] **Sub-Plan B**: Smart Routing - Conversation flow, merge verification
- [ ] **Sub-Plan C**: Vector/RAG - Embeddings, ChromaDB, semantic search
- [ ] **Sub-Plan D**: REST API - FastAPI endpoints, WebSocket streaming
- [ ] **Sub-Plan E**: Query Mode - RAG query engine, citations

**Verification**: Run these commands in `knowledge-library`:

```bash
# All tests should pass
pytest

# API should start
python run_api.py

# Optional: sanity-check via API instead of CLI
curl http://localhost:8001/health
```

---

## Part 1: Backend Migration

### Step 1.1: Create Backend Directory in Automaker

```bash
cd /Users/ruben/Documents/GitHub/automaker

# Create dedicated backend folder
mkdir -p backend/knowledge-library
```

### Step 1.2: Copy Backend Code

```bash
# Copy from knowledge-library to automaker
cp -r /Users/ruben/Documents/GitHub/Info-Adding-Sec./src \
      /Users/ruben/Documents/GitHub/automaker/backend/knowledge-library/

cp -r /Users/ruben/Documents/GitHub/Info-Adding-Sec./configs \
      /Users/ruben/Documents/GitHub/automaker/backend/knowledge-library/

cp /Users/ruben/Documents/GitHub/Info-Adding-Sec./pyproject.toml \
   /Users/ruben/Documents/GitHub/automaker/backend/knowledge-library/

cp /Users/ruben/Documents/GitHub/Info-Adding-Sec./run_api.py \
   /Users/ruben/Documents/GitHub/automaker/backend/knowledge-library/
```

### Step 1.3: Update Paths in Configuration

Update `backend/knowledge-library/configs/settings.yaml`:

```yaml
# configs/settings.yaml - Updated paths for automaker integration

library:
  path: ${LIBRARY_PATH:../../data/knowledge-library} # Relative to backend folder
  index_file: _index.yaml

sessions:
  path: ${SESSIONS_PATH:../../data/sessions}
  auto_save: true

vector:
  path: ${VECTOR_DB_PATH:../../data/vector_db}
  chunk_size: 500
  chunk_overlap: 50

api:
  host: ${API_HOST:0.0.0.0}
  port: ${API_PORT:8001} # Different port to avoid conflicts
  cors_origins:
    - http://localhost:3000
    - http://localhost:5173
    - http://localhost:5174
```

### Step 1.4: Create Data Directories

```bash
cd /Users/ruben/Documents/GitHub/automaker

mkdir -p data/knowledge-library
mkdir -p data/sessions
mkdir -p data/vector_db
```

### Step 1.5: Verify Backend Works in New Location

```bash
cd /Users/ruben/Documents/GitHub/automaker/backend/knowledge-library

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Test API
python run_api.py

# In another terminal, test endpoint
curl http://localhost:8001/health
```

### Resulting Directory Structure

```
automaker/
├── backend/
│   └── knowledge-library/
│       ├── src/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── models/
│       │   ├── extraction/
│       │   ├── sdk/
│       │   ├── execution/
│       │   ├── session/
│       │   ├── library/
│       │   ├── vector/
│       │   ├── conversation/
│       │   ├── merge/
│       │   ├── query/
│       │   └── api/
│       ├── configs/
│       │   └── settings.yaml
│       ├── pyproject.toml
│       └── run_api.py
│
├── data/
│   ├── knowledge-library/      # Library markdown files
│   ├── sessions/               # Session state
│   └── vector_db/              # ChromaDB storage
│
├── src/                        # Existing React frontend
│   ├── routes/
│   │   └── knowledge-library/  # NEW: Knowledge Library routes
│   ├── components/
│   ├── hooks/
│   ├── stores/
│   └── lib/
│
└── package.json
```

---

## Part 2: Frontend Integration

### Existing Tech Stack (from master plan)

| Layer      | Technology                    |
| ---------- | ----------------------------- |
| Framework  | React 19 + TypeScript 5.9     |
| Build      | Vite 7 + @vitejs/plugin-react |
| Routing    | TanStack Router (file-based)  |
| Styling    | Tailwind CSS 4                |
| Components | Radix UI + shadcn/ui          |
| State      | Zustand + TanStack Query      |
| Desktop    | Electron (optional)           |

---

### Step 2.1: Create Route Structure

Create the following route files:

```
src/routes/
└── knowledge-library/
    ├── index.tsx                 # Library home (mode selection)
    ├── input/
    │   ├── index.tsx             # Start extraction
    │   └── $sessionId.tsx        # Active extraction session
    ├── output/
    │   └── index.tsx             # Query interface
    └── browse/
        ├── index.tsx             # Browse library
        └── $path.tsx             # View specific file
```

### Step 2.2: API Client Setup

Create `src/lib/knowledge-library-api.ts`:

```typescript
// src/lib/knowledge-library-api.ts

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

  // ============== Sessions ==============

  async createSession(libraryPath?: string) {
    return this.request<SessionResponse>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ library_path: libraryPath || './library' }),
    });
  }

  async getSession(sessionId: string) {
    return this.request<SessionResponse>(`/api/sessions/${sessionId}`);
  }

  async listSessions(limit = 20) {
    return this.request<SessionListResponse>(`/api/sessions?limit=${limit}`);
  }

  async deleteSession(sessionId: string) {
    return this.request(`/api/sessions/${sessionId}`, { method: 'DELETE' });
  }

  async uploadSource(sessionId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  }

  // ============== Cleanup + Plan ==============
  // New workflow: CleanupPlan (keep/discard) + RoutingPlan (top-3 option selection).
  // See Step 2.8 for the full set of cleanup/plan endpoints added to this client.

  // ============== Execution ==============

  async executeSession(sessionId: string, deleteSource = false) {
    return this.request<ExecuteResponse>(`/api/sessions/${sessionId}/execute`, {
      method: 'POST',
      body: JSON.stringify({ delete_source: deleteSource }),
    });
  }

  // ============== Library ==============

  async getLibraryStructure() {
    return this.request<LibraryStructure>('/api/library');
  }

  async getFile(path: string) {
    return this.request(`/api/library/files/${encodeURIComponent(path)}`);
  }

  async searchLibrary(query: string, limit = 10) {
    return this.request<SearchResponse>(
      `/api/library/search?q=${encodeURIComponent(query)}&limit=${limit}`
    );
  }

  // ============== Query ==============

  async queryLibrary(question: string, conversationId?: string): Promise<QueryResponse> {
    return this.request('/api/query/ask', {
      method: 'POST',
      body: JSON.stringify({
        question,
        conversation_id: conversationId,
      }),
    });
  }

  async semanticSearch(query: string, limit = 10) {
    return this.request<SearchResponse>(
      `/api/query/search?query=${encodeURIComponent(query)}&limit=${limit}`,
      { method: 'POST' }
    );
  }

  // ============== WebSocket ==============

  connectToSession(sessionId: string): WebSocket {
    const wsUrl = this.baseUrl.replace('http', 'ws');
    return new WebSocket(`${wsUrl}/api/sessions/${sessionId}/stream`);
  }
}

export const knowledgeLibraryApi = new KnowledgeLibraryAPI();
export default knowledgeLibraryApi;

// ============== Types ==============

export interface SessionResponse {
  id: string;
  phase: string;
  content_mode: 'strict' | 'refinement';
  created_at: string;
  updated_at: string;
  source_file: string | null;
  total_blocks: number;
  resolved_blocks: number; // resolved = kept+selected OR discarded (approved)
  cleanup_approved: boolean;
  cleanup_pending: number;
  routing_pending: number;
  can_execute: boolean;
  pending_questions: number;
}

export interface SessionListResponse {
  sessions: SessionResponse[];
  total: number;
}

// CleanupPlanResponse and RoutingPlanResponse types are defined in Step 2.8 (plan endpoints).

export interface ExecuteResponse {
  success: boolean;
  log: string[];
  source_deleted: boolean;
  errors: string[];
}

export interface LibraryStructure {
  root_path: string;
  categories: LibraryCategory[];
  total_files: number;
  total_blocks: number;
}

export interface LibraryCategory {
  name: string;
  path: string;
  description: string;
  files: LibraryFile[];
  subcategories: LibraryCategory[];
}

export interface LibraryFile {
  path: string;
  category: string;
  title: string;
  sections: string[];
  last_modified: string;
  block_count: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface SearchResult {
  content: string;
  file_path: string;
  section: string;
  similarity: number;
  chunk_id: string;
}

export interface QueryResponse {
  answer: string;
  sources: SourceInfo[];
  confidence: number;
  conversation_id: string;
  related_topics: string[];
}

export interface SourceInfo {
  file: string;
  section: string;
  excerpt: string;
}
```

### Step 2.3: TanStack Query Hooks

Create `src/hooks/use-knowledge-library.ts`:

```typescript
// src/hooks/use-knowledge-library.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeLibraryApi } from '@/lib/knowledge-library-api';
import type { SessionResponse, QueryResponse } from '@/lib/knowledge-library-api';

// ============== Session Hooks ==============

export function useSessions(limit = 20) {
  return useQuery({
    queryKey: ['knowledge-library', 'sessions'],
    queryFn: () => knowledgeLibraryApi.listSessions(limit),
  });
}

export function useSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['knowledge-library', 'session', sessionId],
    queryFn: () => knowledgeLibraryApi.getSession(sessionId!),
    enabled: !!sessionId,
    refetchInterval: 2000, // Poll for updates
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (libraryPath?: string) => knowledgeLibraryApi.createSession(libraryPath),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['knowledge-library', 'sessions'],
      });
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => knowledgeLibraryApi.deleteSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['knowledge-library', 'sessions'],
      });
    },
  });
}

export function useUploadSource(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => knowledgeLibraryApi.uploadSource(sessionId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['knowledge-library', 'session', sessionId],
      });
    },
  });
}

// ============== Cleanup + Plan Hooks ==============
// Category/Recommendation/Merge hooks are removed in the plan-based workflow.
// Use cleanup + routing plan hooks defined in Step 2.9:
// - useCleanupPlan / useDecideCleanupItem / useApproveCleanupPlan
// - useRoutingPlan / useSelectBlockDestination / useRejectBlock
// Merge previews (refinement mode) come from the routing plan response.

// ============== Execution Hook ==============

export function useExecuteSession(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (deleteSource: boolean = false) =>
      knowledgeLibraryApi.executeSession(sessionId, deleteSource),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['knowledge-library', 'session', sessionId],
      });
      queryClient.invalidateQueries({
        queryKey: ['knowledge-library', 'library'],
      });
    },
  });
}

// ============== Library Hooks ==============

export function useLibraryStructure() {
  return useQuery({
    queryKey: ['knowledge-library', 'library', 'structure'],
    queryFn: () => knowledgeLibraryApi.getLibraryStructure(),
  });
}

export function useLibraryFile(path: string | undefined) {
  return useQuery({
    queryKey: ['knowledge-library', 'library', 'file', path],
    queryFn: () => knowledgeLibraryApi.getFile(path!),
    enabled: !!path,
  });
}

export function useLibrarySearch(query: string, enabled = true) {
  return useQuery({
    queryKey: ['knowledge-library', 'library', 'search', query],
    queryFn: () => knowledgeLibraryApi.searchLibrary(query),
    enabled: enabled && query.length > 2,
  });
}

// ============== Query Hooks ==============

export function useQueryLibrary() {
  return useMutation({
    mutationFn: ({ question, conversationId }: { question: string; conversationId?: string }) =>
      knowledgeLibraryApi.queryLibrary(question, conversationId),
  });
}

export function useSemanticSearch() {
  return useMutation({
    mutationFn: ({ query, limit = 10 }: { query: string; limit?: number }) =>
      knowledgeLibraryApi.semanticSearch(query, limit),
  });
}
```

### Step 2.4: Zustand Store

Create `src/stores/knowledge-library.ts`:

```typescript
// src/stores/knowledge-library.ts

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  SessionResponse,
  MergePreviewResponse,
  QueryResponse,
} from '@/lib/knowledge-library-api';

interface KnowledgeLibraryState {
  // Current session
  currentSessionId: string | null;

  // UI state
  selectedBlockId: string | null;
  mergeDialogOpen: boolean;
  selectedMerge: MergePreviewResponse | null;

  // Query mode state
  currentConversationId: string | null;
  queryHistory: QueryResponse[];

  // Actions
  setCurrentSession: (sessionId: string | null) => void;
  selectBlock: (blockId: string | null) => void;
  openMergeDialog: (merge: MergePreviewResponse) => void;
  closeMergeDialog: () => void;
  setConversation: (conversationId: string | null) => void;
  addQueryResult: (result: QueryResponse) => void;
  clearQueryHistory: () => void;
}

export const useKnowledgeLibraryStore = create<KnowledgeLibraryState>()(
  devtools(
    persist(
      (set) => ({
        // Initial state
        currentSessionId: null,
        selectedBlockId: null,
        mergeDialogOpen: false,
        selectedMerge: null,
        currentConversationId: null,
        queryHistory: [],

        // Actions
        setCurrentSession: (sessionId) => set({ currentSessionId: sessionId }),

        selectBlock: (blockId) => set({ selectedBlockId: blockId }),

        openMergeDialog: (merge) => set({ mergeDialogOpen: true, selectedMerge: merge }),

        closeMergeDialog: () => set({ mergeDialogOpen: false, selectedMerge: null }),

        setConversation: (conversationId) => set({ currentConversationId: conversationId }),

        addQueryResult: (result) =>
          set((state) => ({
            queryHistory: [...state.queryHistory, result],
            currentConversationId: result.conversation_id,
          })),

        clearQueryHistory: () => set({ queryHistory: [], currentConversationId: null }),
      }),
      {
        name: 'knowledge-library-storage',
        partialize: (state) => ({
          currentSessionId: state.currentSessionId,
          currentConversationId: state.currentConversationId,
        }),
      }
    )
  )
);
```

### Step 2.5: Key UI Components

#### Recommendation Card (Deprecated)

This UI was part of the old incremental recommendation workflow. It is replaced by:

- `PlanReviewScreen.tsx` + `BlockCard.tsx` (top-3 option selection)
- `CleanupColumn.tsx` (explicit keep/discard)

#### Merge Dialog (`src/components/knowledge-library/merge-dialog.tsx`)

```typescript
// src/components/knowledge-library/merge-dialog.tsx

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { MergePreviewResponse } from '@/lib/knowledge-library-api';

interface MergeDialogProps {
  merge: MergePreviewResponse;
  open: boolean;
  onClose: () => void;
  onDecide: (decision: string, editedContent?: string) => void;
}

export function MergeDialog({
  merge,
  open,
  onClose,
  onDecide,
}: MergeDialogProps) {
  const [editedContent, setEditedContent] = useState(merge.proposed_merge);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>Verify Merge: {merge.merge_id}</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="compare" className="mt-4">
          <TabsList>
            <TabsTrigger value="compare">Compare</TabsTrigger>
            <TabsTrigger value="edit">Edit Merged</TabsTrigger>
          </TabsList>

          <TabsContent value="compare" className="grid grid-cols-3 gap-4">
            <div>
              <h4 className="font-medium mb-2 text-blue-600">Existing</h4>
              <pre className="p-3 bg-blue-50 rounded text-sm whitespace-pre-wrap max-h-64 overflow-auto">
                {merge.existing_content}
              </pre>
            </div>
            <div>
              <h4 className="font-medium mb-2 text-yellow-600">New</h4>
              <pre className="p-3 bg-yellow-50 rounded text-sm whitespace-pre-wrap max-h-64 overflow-auto">
                {merge.new_content}
              </pre>
            </div>
            <div>
              <h4 className="font-medium mb-2 text-green-600">Proposed Merge</h4>
              <pre className="p-3 bg-green-50 rounded text-sm whitespace-pre-wrap max-h-64 overflow-auto">
                {merge.proposed_merge}
              </pre>
            </div>
          </TabsContent>

          <TabsContent value="edit">
            <Textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              className="min-h-[300px] font-mono"
              placeholder="Edit the merged content..."
            />
          </TabsContent>
        </Tabs>

        <p className="text-sm text-muted-foreground mt-4">
          <strong>Reasoning:</strong> {merge.merge_reasoning}
        </p>

        <DialogFooter className="gap-2 mt-4">
          <Button variant="outline" onClick={() => onDecide('separate')}>
            Keep Separate
          </Button>
          <Button variant="outline" onClick={() => onDecide('reject')}>
            Reject
          </Button>
          <Button onClick={() => onDecide('edit', editedContent)}>
            Save Edited
          </Button>
          <Button variant="default" onClick={() => onDecide('approve')}>
            Approve as Proposed
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

#### Query Interface (`src/components/knowledge-library/query-interface.tsx`)

```typescript
// src/components/knowledge-library/query-interface.tsx

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useQueryLibrary } from '@/hooks/use-knowledge-library';
import { useKnowledgeLibraryStore } from '@/stores/knowledge-library';
import type { QueryResponse } from '@/lib/knowledge-library-api';

export function QueryInterface() {
  const [question, setQuestion] = useState('');
  const { currentConversationId, queryHistory, addQueryResult } =
    useKnowledgeLibraryStore();

  const queryMutation = useQueryLibrary();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    try {
      const result = await queryMutation.mutateAsync({
        question,
        conversationId: currentConversationId || undefined,
      });
      addQueryResult(result);
      setQuestion('');
    } catch (error) {
      console.error('Query failed:', error);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Conversation History */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {queryHistory.map((result, index) => (
          <QueryResultCard key={index} result={result} />
        ))}

        {queryMutation.isPending && (
          <div className="text-center text-muted-foreground">
            Searching your library...
          </div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your knowledge library..."
            className="flex-1"
          />
          <Button type="submit" disabled={queryMutation.isPending}>
            Ask
          </Button>
        </div>
      </form>
    </div>
  );
}

function QueryResultCard({ result }: { result: QueryResponse }) {
  return (
    <Card>
      <CardContent className="pt-4">
        {/* Confidence Badge */}
        <div className="flex justify-between items-start mb-2">
          <Badge variant="outline">
            {Math.round(result.confidence * 100)}% confident
          </Badge>
        </div>

        {/* Answer */}
        <div className="prose prose-sm max-w-none">
          <p className="whitespace-pre-wrap">{result.answer}</p>
        </div>

        {/* Sources */}
        {result.sources.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <h4 className="text-sm font-medium mb-2">Sources:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              {result.sources.map((source, i) => (
                <li key={i}>
                  <a
                    href={`/knowledge-library/browse/${encodeURIComponent(source.file)}`}
                    className="text-blue-600 hover:underline"
                  >
                    {source.file}
                  </a>
                  {source.section && ` (${source.section})`}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Related Topics */}
        {result.related_topics.length > 0 && (
          <div className="mt-2 flex gap-1 flex-wrap">
            {result.related_topics.map((topic, i) => (
              <Badge key={i} variant="secondary" className="text-xs">
                {topic}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Step 2.6: Environment Configuration

Add to `.env`:

```bash
# Knowledge Library API
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8001
```

---

### Step 2.7: Plan Review Components (NEW)

The plan review screen is the core UI for the extraction workflow.
It displays ALL blocks on a single screen with per-block controls.

#### Component Structure

```
src/components/knowledge-library/plan-review/
├── PlanReviewScreen.tsx       # Main container
├── ChatPanel.tsx              # Embedded Claude Code chat (left/right side panel)
├── ModeToggle.tsx             # Strict/Refinement switch
├── CleanupColumn.tsx          # Keep/Discard decisions (explicit)
├── RoutingColumn.tsx          # Top-3 options per kept block
├── BlockCard.tsx              # Block content + routing options + selection controls
├── CustomDestinationDialog.tsx # Picker for custom file/section/action (no typing)
├── MergePreviewDialog.tsx     # Triple-view merge preview
├── PlanSummary.tsx            # Stats: X/Y resolved, etc.
├── ExecuteButton.tsx          # Disabled until all resolved
└── VerificationResults.tsx    # Post-execution status
```

#### PlanReviewScreen.tsx

```tsx
import { useEffect, useState } from 'react';
import { useParams } from '@tanstack/react-router';
import {
  useSession,
  useCleanupPlan,
  useRoutingPlan,
  useGenerateCleanupPlan,
  useGenerateRoutingPlan,
  useApproveCleanupPlan,
  useExecuteSession,
} from '@/hooks/use-knowledge-library';
import { ModeToggle } from './ModeToggle';
import { ChatPanel } from './ChatPanel';
import { CleanupColumn } from './CleanupColumn';
import { RoutingColumn } from './RoutingColumn';
import { PlanSummary } from './PlanSummary';
import { ExecuteButton } from './ExecuteButton';
import { VerificationResults } from './VerificationResults';

export function PlanReviewScreen() {
  const { sessionId } = useParams({ from: '/knowledge-library/input/$sessionId' });
  const { data: session } = useSession(sessionId);
  const { data: cleanup } = useCleanupPlan(sessionId);
  const { data: plan } = useRoutingPlan(sessionId);
  const generateCleanup = useGenerateCleanupPlan(sessionId);
  const generatePlan = useGenerateRoutingPlan(sessionId);
  const approveCleanup = useApproveCleanupPlan(sessionId);
  const executeMutation = useExecuteSession(sessionId);

  const [executionResults, setExecutionResults] = useState(null);

  useEffect(() => {
    if (!cleanup && !generateCleanup.isPending) generateCleanup.mutate();
  }, [cleanup, generateCleanup]);

  useEffect(() => {
    if (cleanup?.approved && !plan && !generatePlan.isPending) generatePlan.mutate();
  }, [cleanup?.approved, plan, generatePlan]);

  if (!cleanup) return <div>Generating cleanup plan...</div>;
  if (!plan && cleanup.approved) return <div>Generating routing plan...</div>;

  const handleExecute = async () => {
    const results = await executeMutation.mutateAsync(false);
    setExecutionResults(results);
  };

  if (executionResults) {
    return <VerificationResults results={executionResults} />;
  }

  return (
    <div className="container mx-auto py-6">
      <div className="grid grid-cols-[1fr_420px] gap-6">
        <div className="space-y-6">
          <h1 className="text-2xl font-bold">Review Extraction Plan</h1>

          <div className="flex justify-between items-center">
            <ModeToggle sessionId={sessionId} currentMode={session?.content_mode ?? 'strict'} />
            {plan ? <PlanSummary plan={plan} /> : null}
          </div>

          {/* Step 1: Cleanup (explicit keep/discard) */}
          <CleanupColumn sessionId={sessionId} cleanup={cleanup} />

          {/* Approve cleanup to unlock routing plan generation */}
          {!cleanup.approved ? (
            <div className="flex justify-end">
              <button
                className="btn"
                disabled={!cleanup.all_decided}
                onClick={() => approveCleanup.mutate()}
              >
                Approve cleanup
              </button>
            </div>
          ) : null}

          {/* Step 2: Routing (top-3 options per kept block) */}
          {plan ? <RoutingColumn sessionId={sessionId} plan={plan} /> : null}

          <div className="flex justify-end">
            <ExecuteButton
              disabled={!plan?.all_resolved}
              pending={plan?.pending_count ?? 0}
              total={plan?.blocks.length ?? 0}
              onExecute={handleExecute}
              isLoading={executeMutation.isPending}
            />
          </div>
        </div>

        {/* Chat on the side (left/right configurable) */}
        <ChatPanel sessionId={sessionId} />
      </div>
    </div>
  );
}
```

#### BlockCard.tsx

```tsx
import { useState } from 'react';
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useSelectBlockDestination, useRejectBlock } from '@/hooks/use-knowledge-library';
import { CustomDestinationDialog } from './CustomDestinationDialog';
import type { BlockRoutingItem } from '@/lib/knowledge-library-api';

interface BlockCardProps {
  sessionId: string;
  block: BlockRoutingItem;
  hasMerge: boolean;
  onViewMerge?: () => void;
}

export function BlockCard({ sessionId, block, hasMerge, onViewMerge }: BlockCardProps) {
  const [showCustomDialog, setShowCustomDialog] = useState(false);

  const selectMutation = useSelectBlockDestination(sessionId);
  const rejectMutation = useRejectBlock(sessionId);

  const isSelected = block.status === 'selected';

  const handleSelect = (optionIndex: number) => {
    selectMutation.mutate({ block_id: block.block_id, option_index: optionIndex });
  };

  return (
    <>
      <Card className={isSelected ? 'border-green-500 bg-green-50' : ''}>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Block {block.block_id}</span>
            </div>
            <Badge variant="outline">{block.heading_path?.join(' › ')}</Badge>
          </div>
        </CardHeader>

        <CardContent className="space-y-2">
          <p className="mt-2 text-sm line-clamp-3 bg-muted p-2 rounded">{block.content_preview}</p>

          {/* Top-3 routing options (click-to-select) */}
          <div className="space-y-2">
            {block.options.map((opt, idx) => (
              <button
                key={idx}
                className="w-full text-left border rounded p-3 hover:bg-muted"
                onClick={() => handleSelect(idx)}
              >
                <div className="flex justify-between gap-4">
                  <div className="font-medium">
                    {opt.destination_file}
                    {opt.destination_section ? ` > ${opt.destination_section}` : ''}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {Math.round(opt.confidence * 100)}%
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">{opt.reasoning}</div>
              </button>
            ))}
          </div>
        </CardContent>

        <CardFooter className="gap-2">
          {hasMerge && onViewMerge && (
            <Button variant="outline" size="sm" onClick={onViewMerge}>
              View Merge
            </Button>
          )}

          <Button variant="outline" size="sm" onClick={() => setShowCustomDialog(true)}>
            Custom destination...
          </Button>

          <Button
            variant="destructive"
            size="sm"
            onClick={() => rejectMutation.mutate(block.block_id)}
            disabled={isSelected}
          >
            Reject
          </Button>
        </CardFooter>
      </Card>

      <CustomDestinationDialog
        open={showCustomDialog}
        onOpenChange={setShowCustomDialog}
        block={block}
      />
    </>
  );
}
```

#### ModeToggle.tsx

```tsx
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { useSetContentMode } from '@/hooks/use-knowledge-library';

interface ModeToggleProps {
  sessionId: string;
  currentMode: 'strict' | 'refinement';
}

export function ModeToggle({ sessionId, currentMode }: ModeToggleProps) {
  const setModeMutation = useSetContentMode(sessionId);

  return (
    <div className="flex items-center gap-4 p-4 bg-muted rounded-lg">
      <span className="font-medium">Content Mode:</span>

      <RadioGroup
        value={currentMode}
        onValueChange={(v) => setModeMutation.mutate(v as 'strict' | 'refinement')}
        className="flex gap-4"
      >
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="strict" id="strict" />
          <Label htmlFor="strict" className="cursor-pointer">
            <span className="font-medium">Strict</span>
            <span className="text-xs text-muted-foreground ml-2">
              Preserve words/sentences; code blocks byte-strict; no merges
            </span>
          </Label>
        </div>

        <div className="flex items-center space-x-2">
          <RadioGroupItem value="refinement" id="refinement" />
          <Label htmlFor="refinement" className="cursor-pointer">
            <span className="font-medium">Refinement</span>
            <span className="text-xs text-muted-foreground ml-2">
              Optional merges/formatting with user verification (no info loss)
            </span>
          </Label>
        </div>
      </RadioGroup>
    </div>
  );
}
```

#### VerificationResults.tsx

```tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { CheckCircle, XCircle } from 'lucide-react';
import type { ExecuteResponse } from '@/lib/knowledge-library-api';

export function VerificationResults({ results }: { results: ExecuteResponse }) {
  return (
    <Card className={results.success ? 'border-green-500' : 'border-red-500'}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {results.success ? (
            <>
              <CheckCircle className="text-green-500" />
              Extraction Complete
            </>
          ) : (
            <>
              <XCircle className="text-red-500" />
              Extraction Failed
            </>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">Blocks Written</p>
            <p className="text-3xl font-bold">{results.blocks_written}</p>
          </div>

          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">Verified</p>
            <p className="text-3xl font-bold">{results.blocks_verified}</p>
          </div>

          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">Checksums OK</p>
            <p className="text-3xl font-bold">{results.checksums_matched}</p>
          </div>

          {results.refinements_applied > 0 && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">Refinements</p>
              <p className="text-3xl font-bold">{results.refinements_applied}</p>
            </div>
          )}
        </div>

        {results.errors.length > 0 && (
          <Alert variant="destructive" className="mt-4">
            <AlertTitle>Errors Occurred</AlertTitle>
            <AlertDescription>
              <ul className="list-disc list-inside">
                {results.errors.map((error, i) => (
                  <li key={i}>{error}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {results.log.length > 0 && (
          <div className="mt-4">
            <h4 className="font-medium mb-2">Execution Log</h4>
            <pre className="bg-muted p-4 rounded text-xs max-h-48 overflow-auto">
              {results.log.join('\n')}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

#### CustomDestinationDialog.tsx

```tsx
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useLibraryStructure, useSelectBlockDestination } from '@/hooks/use-knowledge-library';
import type { BlockRoutingItem } from '@/lib/knowledge-library-api';

interface CustomDestinationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  block: BlockRoutingItem;
}

export function CustomDestinationDialog({
  open,
  onOpenChange,
  block,
}: CustomDestinationDialogProps) {
  const { data: library } = useLibraryStructure();
  const selectMutation = useSelectBlockDestination(block.session_id);

  const [destinationFile, setDestinationFile] = useState<string>('');
  const [destinationSection, setDestinationSection] = useState<string>('');
  const [action, setAction] = useState<string>('append');

  const handleSubmit = () => {
    selectMutation.mutate({
      block_id: block.block_id,
      custom_destination_file: destinationFile,
      custom_destination_section: destinationSection || null,
      custom_action: action,
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Custom Destination for Block {block.block_id}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Select an existing file/section from your library (no typing required). For creating new
            pages/sections, prefer the model-provided top-3 options.
          </p>

          <Select value={destinationFile} onValueChange={setDestinationFile}>
            <SelectTrigger>
              <SelectValue placeholder="Choose file" />
            </SelectTrigger>
            <SelectContent>
              {library?.files.map((f) => (
                <SelectItem key={f.path} value={f.path}>
                  {f.path}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={destinationSection} onValueChange={setDestinationSection}>
            <SelectTrigger>
              <SelectValue placeholder="Choose section (optional)" />
            </SelectTrigger>
            <SelectContent>
              {(library?.sectionsByFile[destinationFile] ?? []).map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={action} onValueChange={setAction}>
            <SelectTrigger>
              <SelectValue placeholder="Action" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="append">append</SelectItem>
              <SelectItem value="create_section">create_section</SelectItem>
              <SelectItem value="insert_before">insert_before</SelectItem>
              <SelectItem value="insert_after">insert_after</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!destinationFile}>
            Apply destination
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

---

### Step 2.8: Updated API Client (Plan Endpoints)

Add to `src/lib/knowledge-library-api.ts`:

```typescript
// ============== Cleanup + Plan Endpoints (NEW) ==============

async generateCleanupPlan(sessionId: string) {
  return this.request<CleanupPlanResponse>(`/api/sessions/${sessionId}/cleanup/generate`, {
    method: 'POST',
  });
}

async getCleanupPlan(sessionId: string) {
  return this.request<CleanupPlanResponse>(`/api/sessions/${sessionId}/cleanup`);
}

async decideCleanupItem(sessionId: string, blockId: string, disposition: 'keep' | 'discard') {
  return this.request(`/api/sessions/${sessionId}/cleanup/decide/${blockId}`, {
    method: 'POST',
    body: JSON.stringify({ disposition }),
  });
}

async approveCleanupPlan(sessionId: string) {
  return this.request(`/api/sessions/${sessionId}/cleanup/approve`, {
    method: 'POST',
  });
}

async generateRoutingPlan(sessionId: string) {
  return this.request<RoutingPlanResponse>(`/api/sessions/${sessionId}/plan/generate`, {
    method: 'POST',
  });
}

async getRoutingPlan(sessionId: string) {
  return this.request<RoutingPlanResponse>(`/api/sessions/${sessionId}/plan`);
}

async selectBlockDestination(
  sessionId: string,
  blockId: string,
  payload: {
    option_index?: number;
    custom_destination_file?: string;
    custom_destination_section?: string | null;
    custom_action?: string;
  }
) {
  return this.request(`/api/sessions/${sessionId}/plan/select/${blockId}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

async rejectBlock(sessionId: string, blockId: string) {
  return this.request(`/api/sessions/${sessionId}/plan/reject-block/${blockId}`, {
    method: 'POST',
  });
}

async rerouteBlock(
  sessionId: string,
  blockId: string,
  payload: {
    reason_code: string;
    prefer_file?: string;
    prefer_section?: string | null;
  }
) {
  return this.request<RerouteResponse>(`/api/sessions/${sessionId}/plan/reroute-block/${blockId}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

async approvePlan(sessionId: string) {
  return this.request(`/api/sessions/${sessionId}/plan/approve`, {
    method: 'POST',
  });
}

async setContentMode(sessionId: string, mode: 'strict' | 'refinement') {
  return this.request(`/api/sessions/${sessionId}/mode`, {
    method: 'POST',
    body: JSON.stringify({ mode }),
  });
}


// ============== Types (Add to existing types) ==============

export interface CleanupPlanResponse {
  session_id: string;
  source_file: string;
  items: CleanupItem[];
  pending_count: number;
  all_decided: boolean;
  approved: boolean;
}

export interface CleanupItem {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  suggested_disposition: 'keep' | 'discard';
  suggestion_reason: string;
  final_disposition: 'keep' | 'discard' | null;
}

export interface RoutingPlanResponse {
  session_id: string;
  content_mode: 'strict' | 'refinement';
  source_file: string;
  blocks: BlockRoutingItem[];
  merge_previews: MergePreviewResponse[];
  summary: PlanSummaryResponse;
  pending_count: number;
  accepted_count: number;
  all_resolved: boolean;
}

export interface DestinationOption {
  destination_file: string;
  destination_section: string | null;
  action: string;
  confidence: number;
  reasoning: string;
  proposed_file_title?: string | null;
  proposed_section_title?: string | null;
}

export interface BlockRoutingItem {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  options: DestinationOption[];
  selected_option_index: number | null;
  custom_destination_file: string | null;
  custom_destination_section: string | null;
  custom_action: string | null;
  status: 'pending' | 'selected' | 'rejected';
}

export interface MergePreviewResponse {
  merge_id: string;
  block_id: string;
  existing_content: string;
  existing_location: string;
  new_content: string;
  proposed_merge: string;
  merge_reasoning: string;
}

export interface PlanSummaryResponse {
  total_blocks: number;
  blocks_to_new_files: number;
  blocks_to_existing_files: number;
  blocks_requiring_merge: number;
  estimated_actions: number;
}

export interface RerouteResponse {
  success: boolean;
  block: BlockRoutingItem;
  message: string;
}

// Update ExecuteResponse with verification fields
export interface ExecuteResponse {
  success: boolean;
  blocks_written: number;
  blocks_verified: number;
  checksums_matched: number;
  refinements_applied: number;
  log: string[];
  source_deleted: boolean;
  errors: string[];
}
```

---

### Step 2.9: Updated Hooks (Plan Hooks)

Add to `src/hooks/use-knowledge-library.ts`:

```typescript
// ============== Cleanup + Plan Hooks (NEW) ==============

export function useCleanupPlan(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['knowledge-library', 'cleanup', sessionId],
    queryFn: () => knowledgeLibraryApi.getCleanupPlan(sessionId!),
    enabled: !!sessionId,
  });
}

export function useDecideCleanupItem(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ blockId, disposition }: { blockId: string; disposition: 'keep' | 'discard' }) =>
      knowledgeLibraryApi.decideCleanupItem(sessionId, blockId, disposition),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'cleanup', sessionId] });
    },
  });
}

export function useApproveCleanupPlan(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => knowledgeLibraryApi.approveCleanupPlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'cleanup', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'plan', sessionId] });
    },
  });
}

export function useGenerateCleanupPlan(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => knowledgeLibraryApi.generateCleanupPlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'cleanup', sessionId] });
    },
  });
}

export function useGenerateRoutingPlan(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => knowledgeLibraryApi.generateRoutingPlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'plan', sessionId] });
    },
  });
}

export function useRoutingPlan(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['knowledge-library', 'plan', sessionId],
    queryFn: () => knowledgeLibraryApi.getRoutingPlan(sessionId!),
    enabled: !!sessionId,
    refetchInterval: 2000,
  });
}

export function useSelectBlockDestination(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      block_id,
      option_index,
      custom_destination_file,
      custom_destination_section,
      custom_action,
    }: {
      block_id: string;
      option_index?: number;
      custom_destination_file?: string;
      custom_destination_section?: string | null;
      custom_action?: string;
    }) =>
      knowledgeLibraryApi.selectBlockDestination(sessionId, block_id, {
        option_index,
        custom_destination_file,
        custom_destination_section,
        custom_action,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'plan', sessionId] });
    },
  });
}

export function useRejectBlock(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (blockId: string) => knowledgeLibraryApi.rejectBlock(sessionId, blockId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'plan', sessionId] });
    },
  });
}

export function useRerouteBlock(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      block_id,
      reason_code,
      prefer_file,
      prefer_section,
    }: {
      block_id: string;
      reason_code: string;
      prefer_file?: string;
      prefer_section?: string | null;
    }) =>
      knowledgeLibraryApi.rerouteBlock(sessionId, block_id, {
        reason_code,
        prefer_file,
        prefer_section,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'plan', sessionId] });
    },
  });
}

export function useSetContentMode(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mode: 'strict' | 'refinement') =>
      knowledgeLibraryApi.setContentMode(sessionId, mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'plan', sessionId] });
    },
  });
}

export function useApprovePlan(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => knowledgeLibraryApi.approvePlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'plan', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-library', 'session', sessionId] });
    },
  });
}
```

---

## Acceptance Criteria

### Part 1: Migration

- [ ] Backend copied to `automaker/backend/knowledge-library/`
- [ ] Configuration updated with correct paths
- [ ] Data directories created
- [ ] Backend starts and passes health check
- [ ] Cleanup + Routing plan endpoints functional in new location

### Part 2: Frontend

- [ ] Route structure added (`/knowledge-library/*`)
- [ ] API client implemented (including plan endpoints)
- [ ] TanStack Query hooks working (including plan hooks)
- [ ] Zustand store created
- [ ] Session creation UI
- [ ] Document upload component
- [ ] **Single plan review screen showing all blocks**
- [ ] **ModeToggle component (Strict/Refinement)**
- [ ] **CleanupColumn: explicit Keep/Discard decisions**
- [ ] **RoutingColumn: top-3 destination options with confidence**
- [ ] **BlockCard: click-to-select option + custom destination picker**
- [ ] **AI re-routing returns refreshed top-3 options (optional edge case)**
- [ ] **ExecuteButton disabled until all blocks resolved**
- [ ] **VerificationResults shows checksum status**
- [ ] Merge verification dialog (MergePreviewDialog) with triple-view
- [ ] Library browser
- [ ] Query interface with conversation history
- [ ] Search integration
- [ ] Source citations with links

---

## Running the Complete System

### Terminal 1: Backend API

```bash
cd /Users/ruben/Documents/GitHub/automaker/backend/knowledge-library
source .venv/bin/activate
python run_api.py
# API running at http://localhost:8001
```

### Terminal 2: Frontend Dev Server

```bash
cd /Users/ruben/Documents/GitHub/automaker
npm run dev
# Frontend running at http://localhost:5173
```

### Access the App

- **Knowledge Library Home**: http://localhost:5173/knowledge-library
- **Input Mode**: http://localhost:5173/knowledge-library/input
- **Query Mode**: http://localhost:5173/knowledge-library/output
- **Browse Library**: http://localhost:5173/knowledge-library/browse
- **API Docs**: http://localhost:8001/docs

---

## Notes for Downstream Session

1. **Two Repositories**: After this phase, code exists in both repos - keep `knowledge-library` as the canonical backend source, `automaker` as the deployed version
2. **CORS**: The backend is configured to accept requests from common dev server ports - update if needed
3. **WebSocket**: Real-time updates during extraction use WebSocket - ensure proxy is configured if behind nginx
4. **Environment Variables**: Set `VITE_KNOWLEDGE_LIBRARY_API` in production to point to the deployed backend
5. **Styling**: Components use shadcn/ui - ensure it's properly set up in the automaker project

---

## Future Enhancements (Post-Phase 6)

From the master plan:

- Cloud storage migration (S3/GCS)
- Multi-user support with authentication
- Advanced query features (suggestions, knowledge graph)
- Import/export (Notion, Obsidian integration)

---

_End of Sub-Plan F - Final Phase_
