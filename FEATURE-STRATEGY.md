# Feature Development Strategy

This document provides comprehensive guidelines for adding new major features to the Automaker codebase. It ensures clean separation between features, maintainable architecture, and easy integration of external functionality.

> **For LLMs**: Read this document when implementing new major features. The essential rules are in `CLAUDE.md` - this document provides the detailed context and examples.

## Philosophy

### Core Principles

1. **Feature-First Organization**: Organize by business domain, not by technical layer
2. **Clean Boundaries**: Each feature should be self-contained with clear public APIs
3. **Minimal Coupling**: Features communicate through well-defined interfaces, not shared state
4. **Easy Integration**: Structure allows easy addition of features from external repositories
5. **Vertical Slices**: Each feature contains all layers (UI → API → Database) for that domain

### What This Achieves

- **Isolation**: Changes to one feature don't break others
- **Discoverability**: All code for a feature lives together
- **Portability**: Features can be extracted or migrated independently
- **Collaboration**: Multiple developers can work on different features without conflicts

---

## Feature Structure

### Directory Layout

New major features MUST follow this structure:

```
apps/ui/src/features/{feature-name}/
├── components/           # UI components for this feature
│   ├── FeatureGallery.tsx
│   ├── FeatureDetail.tsx
│   └── FeatureCard.tsx
├── hooks/                # Feature-specific React hooks
│   ├── use-{feature}.ts
│   └── use-{feature}-detail.ts
├── routes/               # TanStack Router route files
│   ├── {feature}.tsx           # Layout route
│   ├── {feature}.index.tsx     # Gallery/list page
│   └── {feature}.$id.tsx       # Detail page
├── dialogs/              # Feature-specific modals
│   ├── Create{Feature}Dialog.tsx
│   └── Edit{Feature}Dialog.tsx
├── api.ts                # API client functions for this feature
├── store.ts              # Feature-specific Zustand store (if needed)
├── types.ts              # Feature-specific types (re-exports from @automaker/types)
├── constants.ts          # Feature constants and config
└── index.ts              # Public API - exports only what others need

apps/server/src/features/{feature-name}/
├── routes.ts             # Express route definitions
├── service.ts            # Business logic
├── storage.ts            # Data access layer
├── validation.ts         # Request validation (Zod schemas)
├── types.ts              # Server-side types (if not in @automaker/types)
└── index.ts              # Public exports
```

### Public API Pattern

Every feature MUST export through `index.ts`. Internal files are private.

```typescript
// apps/ui/src/features/templates/index.ts

// Components - only export what's needed by routes
export { TemplatesGallery } from './components/TemplatesGallery';
export { TemplateDetail } from './components/TemplateDetail';

// Hooks - for use in other features if needed
export { useTemplates, useTemplate } from './hooks/use-templates';

// Types - re-export for convenience
export type { Template, CreateTemplateInput } from './types';

// DO NOT export:
// - Internal components (TemplateCard, etc.)
// - Private hooks
// - Implementation details
```

### Server Integration

```typescript
// apps/server/src/features/templates/index.ts

export { createTemplatesRoutes } from './routes';
export { TemplatesService } from './service';

// Register in apps/server/src/index.ts:
import { createTemplatesRoutes } from './features/templates';
app.use('/api/templates', createTemplatesRoutes(teamStorage));
```

---

## Implementation Guide

### Step 1: Define Types

Start by adding types to `libs/types/src/`. This ensures type safety across frontend and backend.

```typescript
// libs/types/src/template.ts

export interface Template {
  id: string;
  name: string;
  description: string;
  content: string;
  category: TemplateCategoryType;
  tags?: string[];
  isArchived?: boolean;
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
}

export type TemplateCategoryType = 'prompt' | 'workflow' | 'configuration' | 'custom';

export interface CreateTemplateInput {
  name: string;
  description: string;
  content: string;
  category: TemplateCategoryType;
  tags?: string[];
}

export interface UpdateTemplateInput {
  name?: string;
  description?: string;
  content?: string;
  category?: TemplateCategoryType;
  tags?: string[];
}
```

Then export from the package index:

```typescript
// libs/types/src/index.ts
export * from './template';
```

### Step 2: Create Backend Service

Follow the established service pattern from SYSTEMS feature.

```typescript
// apps/server/src/features/templates/service.ts

import { createLogger } from '@automaker/utils';
import type { Template, CreateTemplateInput, UpdateTemplateInput } from '@automaker/types';
import { TeamStorageService } from '../../lib/team-storage';

const logger = createLogger('TemplatesService');

export class TemplatesService {
  constructor(private teamStorage: TeamStorageService) {}

  async list(filters?: { category?: string; includeArchived?: boolean }): Promise<Template[]> {
    logger.info('Listing templates', { filters });

    const templates = await this.teamStorage.list<Template>('templates');

    return templates.filter((t) => {
      if (!filters?.includeArchived && t.isArchived) return false;
      if (filters?.category && t.category !== filters.category) return false;
      return true;
    });
  }

  async get(id: string): Promise<Template | null> {
    return this.teamStorage.get<Template>('templates', id);
  }

  async create(input: CreateTemplateInput): Promise<Template> {
    const template: Template = {
      id: crypto.randomUUID(),
      ...input,
      isArchived: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    await this.teamStorage.save('templates', template.id, template);
    logger.info('Created template', { id: template.id, name: template.name });
    return template;
  }

  async update(id: string, input: UpdateTemplateInput): Promise<Template | null> {
    const existing = await this.get(id);
    if (!existing) return null;

    const updated: Template = {
      ...existing,
      ...input,
      updatedAt: new Date().toISOString(),
    };

    await this.teamStorage.save('templates', id, updated);
    logger.info('Updated template', { id });
    return updated;
  }

  async delete(id: string): Promise<boolean> {
    const existing = await this.get(id);
    if (!existing) return false;

    await this.teamStorage.delete('templates', id);
    logger.info('Deleted template', { id });
    return true;
  }

  async duplicate(id: string): Promise<Template | null> {
    const existing = await this.get(id);
    if (!existing) return null;

    return this.create({
      name: `${existing.name} (Copy)`,
      description: existing.description,
      content: existing.content,
      category: existing.category,
      tags: existing.tags,
    });
  }
}
```

### Step 3: Create Backend Routes

```typescript
// apps/server/src/features/templates/routes.ts

import { Router } from 'express';
import { TeamStorageService } from '../../lib/team-storage';
import { TemplatesService } from './service';

export function createTemplatesRoutes(teamStorage: TeamStorageService): Router {
  const router = Router();
  const service = new TemplatesService(teamStorage);

  // GET /api/templates
  router.get('/', async (req, res) => {
    const { category, includeArchived } = req.query;
    const templates = await service.list({
      category: category as string | undefined,
      includeArchived: includeArchived === 'true',
    });
    res.json(templates);
  });

  // GET /api/templates/:id
  router.get('/:id', async (req, res) => {
    const template = await service.get(req.params.id);
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    res.json(template);
  });

  // POST /api/templates
  router.post('/', async (req, res) => {
    const template = await service.create(req.body);
    res.status(201).json(template);
  });

  // PUT /api/templates/:id
  router.put('/:id', async (req, res) => {
    const template = await service.update(req.params.id, req.body);
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    res.json(template);
  });

  // DELETE /api/templates/:id
  router.delete('/:id', async (req, res) => {
    const deleted = await service.delete(req.params.id);
    if (!deleted) {
      return res.status(404).json({ error: 'Template not found' });
    }
    res.status(204).send();
  });

  // POST /api/templates/:id/duplicate
  router.post('/:id/duplicate', async (req, res) => {
    const template = await service.duplicate(req.params.id);
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    res.status(201).json(template);
  });

  return router;
}
```

### Step 4: Create Frontend API Client

```typescript
// apps/ui/src/features/templates/api.ts

import type { Template, CreateTemplateInput, UpdateTemplateInput } from '@automaker/types';

const API_BASE = '/api/templates';

export const templatesApi = {
  async list(filters?: { category?: string }): Promise<Template[]> {
    const params = new URLSearchParams();
    if (filters?.category) params.set('category', filters.category);

    const url = params.toString() ? `${API_BASE}?${params}` : API_BASE;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch templates');
    return res.json();
  },

  async get(id: string): Promise<Template> {
    const res = await fetch(`${API_BASE}/${id}`);
    if (!res.ok) throw new Error('Template not found');
    return res.json();
  },

  async create(input: CreateTemplateInput): Promise<Template> {
    const res = await fetch(API_BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!res.ok) throw new Error('Failed to create template');
    return res.json();
  },

  async update(id: string, input: UpdateTemplateInput): Promise<Template> {
    const res = await fetch(`${API_BASE}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!res.ok) throw new Error('Failed to update template');
    return res.json();
  },

  async delete(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete template');
  },

  async duplicate(id: string): Promise<Template> {
    const res = await fetch(`${API_BASE}/${id}/duplicate`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to duplicate template');
    return res.json();
  },
};
```

### Step 5: Create Frontend Hooks

```typescript
// apps/ui/src/features/templates/hooks/use-templates.ts

import { useState, useEffect, useCallback } from 'react';
import type { Template, CreateTemplateInput, UpdateTemplateInput } from '@automaker/types';
import { templatesApi } from '../api';

export function useTemplates(filters?: { category?: string }) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchTemplates = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await templatesApi.list(filters);
      setTemplates(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [filters?.category]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const create = async (input: CreateTemplateInput) => {
    const template = await templatesApi.create(input);
    setTemplates((prev) => [...prev, template]);
    return template;
  };

  const update = async (id: string, input: UpdateTemplateInput) => {
    const template = await templatesApi.update(id, input);
    setTemplates((prev) => prev.map((t) => (t.id === id ? template : t)));
    return template;
  };

  const remove = async (id: string) => {
    await templatesApi.delete(id);
    setTemplates((prev) => prev.filter((t) => t.id !== id));
  };

  return {
    templates,
    isLoading,
    error,
    refetch: fetchTemplates,
    create,
    update,
    remove,
  };
}

export function useTemplate(id: string) {
  const [template, setTemplate] = useState<Template | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        setIsLoading(true);
        const data = await templatesApi.get(id);
        setTemplate(data);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e : new Error('Unknown error'));
      } finally {
        setIsLoading(false);
      }
    }
    fetch();
  }, [id]);

  return { template, isLoading, error };
}
```

### Step 6: Create Frontend Components

```typescript
// apps/ui/src/features/templates/components/TemplatesGallery.tsx

import { useTemplates } from '../hooks/use-templates';
import { TemplateCard } from './TemplateCard';

export function TemplatesGallery() {
  const { templates, isLoading, error, create, remove } = useTemplates();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {templates.map((template) => (
        <TemplateCard
          key={template.id}
          template={template}
          onDelete={() => remove(template.id)}
        />
      ))}
    </div>
  );
}
```

### Step 7: Create Routes

```typescript
// apps/ui/src/features/templates/routes/templates.tsx

import { createFileRoute, Outlet } from '@tanstack/react-router';

export const Route = createFileRoute('/templates')({
  component: TemplatesLayout,
});

function TemplatesLayout() {
  return (
    <div className="flex flex-col h-full">
      <Outlet />
    </div>
  );
}
```

```typescript
// apps/ui/src/features/templates/routes/templates.index.tsx

import { createFileRoute } from '@tanstack/react-router';
import { TemplatesGallery } from '../components/TemplatesGallery';
import { TemplatesHeader } from '../components/TemplatesHeader';

export const Route = createFileRoute('/templates/')({
  component: TemplatesPage,
});

function TemplatesPage() {
  return (
    <>
      <TemplatesHeader />
      <TemplatesGallery />
    </>
  );
}
```

---

## Integration Checklist

When adding a new major feature, complete this checklist:

### Types

- [ ] Create type file in `libs/types/src/{feature}.ts`
- [ ] Define main entity interface with required fields (id, createdAt, updatedAt)
- [ ] Define CreateInput and UpdateInput types
- [ ] Export from `libs/types/src/index.ts`
- [ ] Run `npm run build:packages` to ensure types compile

### Backend

- [ ] Create feature directory: `apps/server/src/features/{feature}/`
- [ ] Implement service with CRUD + domain operations
- [ ] Implement routes using service
- [ ] Add input validation (optional but recommended)
- [ ] Register routes in `apps/server/src/index.ts`
- [ ] Test with `npm run test:server`

### Frontend

- [ ] Create feature directory: `apps/ui/src/features/{feature}/`
- [ ] Implement API client (`api.ts`)
- [ ] Implement hooks (`hooks/use-{feature}.ts`)
- [ ] Implement components (`components/`)
- [ ] Create routes (`routes/`)
- [ ] Copy route files to `apps/ui/src/routes/` (TanStack Router requirement)
- [ ] Add navigation item in `use-navigation.ts`
- [ ] Test with `npm run dev:web`

### Documentation

- [ ] Add feature section to CLAUDE.md (if major feature)
- [ ] Add keyboard shortcut if applicable (`libs/types/src/settings.ts`)

---

## Anti-Patterns to Avoid

### DON'T: Mix features in global state

```typescript
// ❌ BAD - Adding to global app-store
// apps/ui/src/store/app-store.ts
interface AppState {
  templates: Template[];        // Don't add here!
  selectedTemplateId: string;   // Don't add here!
}

// ✅ GOOD - Feature-specific state
// apps/ui/src/features/templates/store.ts
interface TemplatesState {
  templates: Template[];
  selectedId: string | null;
}

export const useTemplatesStore = create<TemplatesState>(...);
```

### DON'T: Import across feature boundaries without using public API

```typescript
// ❌ BAD - Direct import of internal component
import { TemplateCard } from '../templates/components/TemplateCard';

// ✅ GOOD - Import from public API
import { TemplatesGallery } from '../templates';
// Or if TemplateCard needs to be shared, export it from index.ts
```

### DON'T: Create cross-feature dependencies

```typescript
// ❌ BAD - Template service calling Systems service
class TemplatesService {
  constructor(
    private teamStorage: TeamStorageService,
    private systemsService: SystemsService // Cross-feature dependency!
  ) {}
}

// ✅ GOOD - Use events or keep features independent
class TemplatesService {
  constructor(private teamStorage: TeamStorageService) {}
}
```

### DON'T: Add routes directly to existing directories

```typescript
// ❌ BAD - Adding to existing views folder
apps/ui/src/components/views/templates-page/

// ✅ GOOD - Feature-first organization
apps/ui/src/features/templates/components/
```

---

## Reference: SYSTEMS Feature Structure

The SYSTEMS feature (Agents, Systems, Knowledge Hub) serves as the canonical example. Study these files:

**Types:**

- `libs/types/src/custom-agent.ts`
- `libs/types/src/system.ts`
- `libs/types/src/knowledge.ts`

**Backend:**

- `apps/server/src/services/custom-agents-service.ts`
- `apps/server/src/services/systems-service.ts`
- `apps/server/src/routes/custom-agents/index.ts`
- `apps/server/src/routes/systems/index.ts`

**Frontend (current structure - to be migrated to features/):**

- `apps/ui/src/components/views/agents-page/`
- `apps/ui/src/components/views/systems-page/`
- `apps/ui/src/routes/agents.tsx`
- `apps/ui/src/routes/systems.tsx`

---

## Migrating Features from External Repositories

When integrating a feature built in a separate repository:

### 1. Audit Dependencies

```bash
# In the external repo
cat package.json | jq '.dependencies, .devDependencies'

# Check for conflicts with automaker
diff <(jq -r '.dependencies | keys[]' external/package.json) \
     <(jq -r '.dependencies | keys[]' automaker/package.json)
```

### 2. Extract Types First

Move type definitions to `@automaker/types`. This ensures compatibility.

### 3. Create Feature Directory

Follow the structure in this document. Don't try to fit external code into existing directories.

### 4. Adapt API Layer

External features likely have different API patterns. Create an adapter:

```typescript
// apps/server/src/features/external-feature/adapter.ts

import { ExternalFeatureClient } from './external-client';
import type { Template } from '@automaker/types';

// Adapt external API to internal interface
export async function adaptExternalToTemplate(external: ExternalType): Promise<Template> {
  return {
    id: external.uuid,
    name: external.title,
    description: external.desc ?? '',
    content: external.body,
    category: mapCategory(external.type),
    createdAt: external.created,
    updatedAt: external.modified,
  };
}
```

### 5. Test Incrementally

- Test backend service independently
- Test API routes with Postman/curl
- Test frontend components with mock data
- Integration test with real backend

---

## Summary

**Key Rules:**

1. All new features go in `apps/*/src/features/{feature-name}/`
2. Export public API through `index.ts`
3. Types live in `@automaker/types`
4. Services use `TeamStorageService` for persistence
5. Don't add to global app-store - use feature-specific state
6. Follow the SYSTEMS feature as the template

**Benefits:**

- Clean separation enables parallel development
- Feature-first organization improves discoverability
- Consistent patterns reduce cognitive load
- External features integrate cleanly
