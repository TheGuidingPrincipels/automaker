# Phase 3: Knowledge Hub Sync

> **Status**: Planning
> **Estimated Duration**: 1 week
> **Prerequisites**: Phase 1 (User Foundation)
> **Blocks**: Phase 5 (Deploy)

## Objective

Enable real-time synchronization of the Knowledge Hub across all users. After this phase:

- Knowledge created by User A appears for User B within seconds
- All knowledge entries have user attribution (`createdBy`)
- Agents can store and retrieve shared learnings
- Frontend Knowledge Hub uses real API data (not mock data)

## What This Phase DOES

- Connects frontend Knowledge Hub to existing backend API
- Adds WebSocket events for knowledge changes
- Implements query invalidation for real-time updates
- Adds `createdBy` attribution to all knowledge entities
- Creates React Query hooks for knowledge data

## What This Phase DOES NOT Do

| Excluded Feature         | Handled In |
| ------------------------ | ---------- |
| User registration/login  | Phase 1    |
| Per-user API keys        | Phase 2    |
| OAuth authentication     | Phase 4    |
| Knowledge access control | Future     |
| Conflict resolution      | Future     |

---

## Current State Analysis

### Backend Status: COMPLETE

The backend Knowledge Hub is fully implemented:

- **Types**: `libs/types/src/knowledge.ts` (Blueprint, KnowledgeEntry, Learning)
- **Service**: `apps/server/src/services/knowledge-service.ts` (full CRUD)
- **Routes**: `apps/server/src/routes/knowledge/index.ts` (REST API)
- **Storage**: `apps/server/src/lib/team-storage.ts` (file-based)

### Frontend Status: MOCK DATA

The frontend uses hardcoded mock data instead of API calls:

- `apps/ui/src/components/views/knowledge-hub-page/index.tsx` - hardcoded counts
- `apps/ui/src/components/views/knowledge-section-page/index.tsx` - MOCK_BLUEPRINTS, etc.

### Missing for Multi-User

1. No WebSocket events for knowledge changes
2. No `createdBy` attribution
3. Frontend not connected to API
4. No query invalidation hooks

---

## Technical Specification

### 1. Add Knowledge Event Types

**File to Modify**: `libs/types/src/event.ts`

Add to the EventType union (around line 50):

```typescript
export type EventType =
  // ... existing types ...
  | 'knowledge:blueprint-created'
  | 'knowledge:blueprint-updated'
  | 'knowledge:blueprint-deleted'
  | 'knowledge:entry-created'
  | 'knowledge:entry-updated'
  | 'knowledge:entry-deleted'
  | 'knowledge:learning-created'
  | 'knowledge:learning-updated'
  | 'knowledge:learning-deleted';
```

Add event payload types:

```typescript
export interface KnowledgeChangeEvent {
  type: EventType;
  collection: 'blueprints' | 'entries' | 'learnings';
  entityId: string;
  userId?: string;
  userName?: string;
  timestamp: string;
  data?: unknown; // The created/updated entity
}
```

### 2. Update Knowledge Service to Emit Events

**File to Modify**: `apps/server/src/services/knowledge-service.ts`

**Add EventEmitter support**:

```typescript
import type { EventEmitter } from '../lib/events';

export class KnowledgeService {
  private events: EventEmitter | null = null;

  setEventEmitter(events: EventEmitter): void {
    this.events = events;
  }

  private emitKnowledgeEvent(
    type: EventType,
    collection: 'blueprints' | 'entries' | 'learnings',
    entityId: string,
    userId?: string,
    data?: unknown
  ): void {
    if (!this.events) return;

    this.events.emit(type, {
      collection,
      entityId,
      userId,
      timestamp: new Date().toISOString(),
      data,
    });
  }

  // ... existing methods ...
}
```

**Add event emission to CRUD methods**:

```typescript
// In createBlueprint (around line 95)
async createBlueprint(input: CreateBlueprintInput, userId?: string): Promise<Blueprint> {
  const blueprint = await this.storage.create('blueprints', {
    ...input,
    createdBy: userId,  // ADD attribution
  });

  this.emitKnowledgeEvent(
    'knowledge:blueprint-created',
    'blueprints',
    blueprint.id,
    userId,
    blueprint
  );

  return blueprint;
}

// In updateBlueprint
async updateBlueprint(id: string, updates: UpdateBlueprintInput, userId?: string): Promise<Blueprint | null> {
  const blueprint = await this.storage.update('blueprints', id, {
    ...updates,
    updatedBy: userId,  // ADD attribution
  });

  if (blueprint) {
    this.emitKnowledgeEvent(
      'knowledge:blueprint-updated',
      'blueprints',
      id,
      userId,
      blueprint
    );
  }

  return blueprint;
}

// In deleteBlueprint
async deleteBlueprint(id: string, userId?: string): Promise<boolean> {
  const deleted = await this.storage.delete('blueprints', id);

  if (deleted) {
    this.emitKnowledgeEvent(
      'knowledge:blueprint-deleted',
      'blueprints',
      id,
      userId
    );
  }

  return deleted;
}
```

Apply the same pattern to `KnowledgeEntry` and `Learning` methods.

### 3. Update Knowledge Types for Attribution

**File to Modify**: `libs/types/src/knowledge.ts`

Add attribution fields to base types:

```typescript
export interface Blueprint {
  id: string;
  name: string;
  description: string;
  category: string;
  content: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  createdBy?: string; // ADD
  updatedBy?: string; // ADD
}

export interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  source?: string;
  createdAt: string;
  updatedAt: string;
  createdBy?: string; // ADD
  updatedBy?: string; // ADD
}

export interface Learning {
  id: string;
  title: string;
  problem: string;
  solution: string;
  context?: string;
  outcome?: string;
  tags: string[];
  projectPath?: string;
  featureId?: string;
  agentSessionId?: string;
  createdAt: string;
  updatedAt: string;
  createdBy?: string; // ADD - 'agent' or user ID
  updatedBy?: string; // ADD
}
```

### 4. Wire EventEmitter in Server

**File to Modify**: `apps/server/src/index.ts`

Around where services are initialized:

```typescript
import { getKnowledgeService } from './services/knowledge-service';

// After events emitter is created
const knowledgeService = getKnowledgeService();
knowledgeService.setEventEmitter(events);
```

### 5. Update Knowledge Routes to Pass UserId

**File to Modify**: `apps/server/src/routes/knowledge/index.ts`

```typescript
import type { AuthenticatedRequest } from '@automaker/types';

// POST /api/knowledge/blueprints
router.post('/blueprints', async (req: AuthenticatedRequest, res) => {
  const userId = req.user?.id;
  const blueprint = await knowledgeService.createBlueprint(req.body, userId);
  res.json(blueprint);
});

// PUT /api/knowledge/blueprints/:id
router.put('/blueprints/:id', async (req: AuthenticatedRequest, res) => {
  const userId = req.user?.id;
  const blueprint = await knowledgeService.updateBlueprint(req.params.id, req.body, userId);
  res.json(blueprint);
});

// DELETE /api/knowledge/blueprints/:id
router.delete('/blueprints/:id', async (req: AuthenticatedRequest, res) => {
  const userId = req.user?.id;
  await knowledgeService.deleteBlueprint(req.params.id, userId);
  res.json({ success: true });
});
```

Apply same pattern to entries and learnings routes.

### 6. Frontend Query Keys

**File to Modify**: `apps/ui/src/lib/query-keys.ts`

Add knowledge query keys (around line 244):

```typescript
export const queryKeys = {
  // ... existing keys ...

  knowledge: {
    /** Stats for all knowledge types */
    stats: () => ['knowledge', 'stats'] as const,

    /** All blueprints */
    blueprints: () => ['knowledge', 'blueprints'] as const,
    /** Single blueprint */
    blueprint: (id: string) => ['knowledge', 'blueprints', id] as const,

    /** All knowledge entries */
    entries: () => ['knowledge', 'entries'] as const,
    /** Single entry */
    entry: (id: string) => ['knowledge', 'entries', id] as const,

    /** All learnings */
    learnings: () => ['knowledge', 'learnings'] as const,
    /** Single learning */
    learning: (id: string) => ['knowledge', 'learnings', id] as const,

    /** Search results */
    search: (query: string, section?: string) => ['knowledge', 'search', query, section] as const,
  },
};
```

### 7. Frontend Query Hooks

**File to Create**: `apps/ui/src/hooks/queries/use-knowledge.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../../lib/query-keys';
import type { Blueprint, KnowledgeEntry, Learning } from '@automaker/types';

const API_BASE = '/api/knowledge';

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) throw new Error(`Failed to fetch ${url}`);
  return res.json();
}

// Stats
export function useKnowledgeStats() {
  return useQuery({
    queryKey: queryKeys.knowledge.stats(),
    queryFn: () =>
      fetchJson<{
        blueprints: number;
        entries: number;
        learnings: number;
      }>(`${API_BASE}/stats`),
  });
}

// Blueprints
export function useBlueprints() {
  return useQuery({
    queryKey: queryKeys.knowledge.blueprints(),
    queryFn: () => fetchJson<Blueprint[]>(`${API_BASE}/blueprints`),
  });
}

export function useBlueprint(id: string) {
  return useQuery({
    queryKey: queryKeys.knowledge.blueprint(id),
    queryFn: () => fetchJson<Blueprint>(`${API_BASE}/blueprints/${id}`),
    enabled: !!id,
  });
}

// Knowledge Entries
export function useKnowledgeEntries() {
  return useQuery({
    queryKey: queryKeys.knowledge.entries(),
    queryFn: () => fetchJson<KnowledgeEntry[]>(`${API_BASE}/entries`),
  });
}

export function useKnowledgeEntry(id: string) {
  return useQuery({
    queryKey: queryKeys.knowledge.entry(id),
    queryFn: () => fetchJson<KnowledgeEntry>(`${API_BASE}/entries/${id}`),
    enabled: !!id,
  });
}

// Learnings
export function useLearnings() {
  return useQuery({
    queryKey: queryKeys.knowledge.learnings(),
    queryFn: () => fetchJson<Learning[]>(`${API_BASE}/learnings`),
  });
}

export function useLearning(id: string) {
  return useQuery({
    queryKey: queryKeys.knowledge.learning(id),
    queryFn: () => fetchJson<Learning>(`${API_BASE}/learnings/${id}`),
    enabled: !!id,
  });
}

// Search
export function useKnowledgeSearch(query: string, section?: string) {
  return useQuery({
    queryKey: queryKeys.knowledge.search(query, section),
    queryFn: () =>
      fetchJson<{
        blueprints?: Blueprint[];
        entries?: KnowledgeEntry[];
        learnings?: Learning[];
      }>(
        `${API_BASE}/search?q=${encodeURIComponent(query)}${section ? `&section=${section}` : ''}`
      ),
    enabled: query.length > 0,
  });
}
```

### 8. Frontend Mutation Hooks

**File to Create**: `apps/ui/src/hooks/mutations/use-knowledge-mutations.ts`

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../lib/query-keys';
import type {
  Blueprint,
  KnowledgeEntry,
  Learning,
  CreateBlueprintInput,
  UpdateBlueprintInput,
  CreateKnowledgeEntryInput,
  UpdateKnowledgeEntryInput,
  CreateLearningInput,
  UpdateLearningInput,
} from '@automaker/types';

const API_BASE = '/api/knowledge';

async function postJson<T>(url: string, data: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to POST ${url}`);
  return res.json();
}

async function putJson<T>(url: string, data: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to PUT ${url}`);
  return res.json();
}

async function deleteRequest(url: string): Promise<void> {
  const res = await fetch(url, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!res.ok) throw new Error(`Failed to DELETE ${url}`);
}

// Blueprint mutations
export function useCreateBlueprint() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateBlueprintInput) =>
      postJson<Blueprint>(`${API_BASE}/blueprints`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.blueprints() });
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.stats() });
    },
  });
}

export function useUpdateBlueprint() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: UpdateBlueprintInput }) =>
      putJson<Blueprint>(`${API_BASE}/blueprints/${id}`, updates),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.blueprints() });
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.blueprint(id) });
    },
  });
}

export function useDeleteBlueprint() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteRequest(`${API_BASE}/blueprints/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.blueprints() });
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.stats() });
    },
  });
}

// Similar mutations for KnowledgeEntry and Learning...
// (Follow same pattern)

export function useCreateKnowledgeEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateKnowledgeEntryInput) =>
      postJson<KnowledgeEntry>(`${API_BASE}/entries`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.entries() });
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.stats() });
    },
  });
}

export function useCreateLearning() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateLearningInput) => postJson<Learning>(`${API_BASE}/learnings`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.learnings() });
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.stats() });
    },
  });
}
```

### 9. WebSocket Query Invalidation Hook

**File to Modify**: `apps/ui/src/hooks/use-query-invalidation.ts`

Add knowledge event handling:

```typescript
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../lib/query-keys';
import { getElectronAPI } from '../lib/electron-api';

export function useKnowledgeQueryInvalidation() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const api = getElectronAPI();

    // Subscribe to knowledge events
    const unsubscribe = api.events.subscribe((event) => {
      if (!event.type.startsWith('knowledge:')) return;

      const { type } = event;

      // Invalidate appropriate queries based on event type
      if (type.includes('blueprint')) {
        queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.blueprints() });
        queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.stats() });
      } else if (type.includes('entry')) {
        queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.entries() });
        queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.stats() });
      } else if (type.includes('learning')) {
        queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.learnings() });
        queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.stats() });
      }
    });

    return unsubscribe;
  }, [queryClient]);
}
```

### 10. Update Knowledge Hub Page

**File to Modify**: `apps/ui/src/components/views/knowledge-hub-page/index.tsx`

Replace hardcoded data with API data:

```typescript
import { useKnowledgeStats } from '../../../hooks/queries/use-knowledge';
import { useKnowledgeQueryInvalidation } from '../../../hooks/use-query-invalidation';

export function KnowledgeHubPage() {
  // Enable real-time sync
  useKnowledgeQueryInvalidation();

  const { data: stats, isLoading } = useKnowledgeStats();

  // REPLACE HARDCODED SECTIONS
  const SECTIONS = [
    {
      id: 'blueprints',
      title: 'Blueprints',
      description: 'Reusable templates and patterns',
      icon: FileCode,
      itemCount: stats?.blueprints ?? 0,  // FROM API
      gradient: 'from-blue-500/20 to-cyan-500/20',
    },
    {
      id: 'knowledge-server',
      title: 'Knowledge Server',
      description: 'Structured knowledge entries',
      icon: Database,
      itemCount: stats?.entries ?? 0,  // FROM API
      gradient: 'from-purple-500/20 to-pink-500/20',
    },
    {
      id: 'learning',
      title: 'Learning',
      description: 'Discovered patterns and solutions',
      icon: Lightbulb,
      itemCount: stats?.learnings ?? 0,  // FROM API
      gradient: 'from-amber-500/20 to-orange-500/20',
    },
  ];

  if (isLoading) {
    return <LoadingState />;
  }

  // ... rest of component
}
```

### 11. Update Knowledge Section Page

**File to Modify**: `apps/ui/src/components/views/knowledge-section-page/index.tsx`

Replace mock data with API hooks:

```typescript
import {
  useBlueprints,
  useKnowledgeEntries,
  useLearnings,
} from '../../../hooks/queries/use-knowledge';
import { useKnowledgeQueryInvalidation } from '../../../hooks/use-query-invalidation';

export function KnowledgeSectionPage({ sectionId }: { sectionId: string }) {
  // Enable real-time sync
  useKnowledgeQueryInvalidation();

  // Fetch data based on section
  const blueprintsQuery = useBlueprints();
  const entriesQuery = useKnowledgeEntries();
  const learningsQuery = useLearnings();

  // Select correct data based on section
  let items: (Blueprint | KnowledgeEntry | Learning)[] = [];
  let isLoading = false;

  if (sectionId === 'blueprints') {
    items = blueprintsQuery.data ?? [];
    isLoading = blueprintsQuery.isLoading;
  } else if (sectionId === 'knowledge-server') {
    items = entriesQuery.data ?? [];
    isLoading = entriesQuery.isLoading;
  } else if (sectionId === 'learning') {
    items = learningsQuery.data ?? [];
    isLoading = learningsQuery.isLoading;
  }

  // REMOVE: const items = MOCK_BLUEPRINTS / MOCK_KNOWLEDGE_ENTRIES / MOCK_LEARNINGS

  if (isLoading) {
    return <LoadingState />;
  }

  // ... rest of component with real data
}
```

---

## Testing Checklist

### Unit Tests

- [ ] KnowledgeService emits events on create/update/delete
- [ ] Events include userId and timestamp
- [ ] Query hooks fetch correct data

### Integration Tests

- [ ] POST `/api/knowledge/blueprints` creates and broadcasts event
- [ ] WebSocket clients receive knowledge events
- [ ] Query invalidation triggers refetch

### Multi-User Tests

- [ ] User A creates blueprint, User B sees it within 5 seconds
- [ ] User B updates entry, User A's view updates
- [ ] Attribution shows correct user name

### E2E Tests

- [ ] Knowledge Hub shows real counts from API
- [ ] Creating blueprint updates count immediately
- [ ] Opening Knowledge Hub in two browsers syncs

---

## Rollback Plan

1. Revert knowledge-hub-page to use hardcoded SECTIONS
2. Revert knowledge-section-page to use MOCK\_\* data
3. Remove event emission from knowledge-service
4. Remove query hooks
5. Remove query invalidation hook

---

## Success Criteria

Phase 3 is complete when:

1. Knowledge Hub shows real counts from API
2. Creating/updating knowledge updates all connected clients
3. `createdBy` shows who created each entry
4. No more mock data in Knowledge Hub frontend
5. Sync happens within 5 seconds of change

---

## Notes for Downstream Phases

### For Phase 4 (OAuth)

- User names will be available from OAuth profiles
- Can display user avatars next to `createdBy`

### For Phase 5 (Deploy)

- WebSocket must be accessible in production
- Consider Redis pub/sub if deploying multiple server instances

### Future: Agent Knowledge Access

- Agents can already access Knowledge Hub via HTTP
- Consider MCP tool for direct agent access
- Learning entries can be created by agents (createdBy: 'agent')
