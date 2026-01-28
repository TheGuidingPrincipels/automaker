# Adding New Features

Guide for implementing new major features using Feature-First Architecture.

## Quick Rules

1. **Create dedicated directories** for each new feature:

   ```
   apps/ui/src/features/{feature-name}/
   apps/server/src/features/{feature-name}/
   ```

2. **Types go in shared package**: `libs/types/src/{feature}.ts`

3. **DO NOT** add feature state to global `app-store.ts` - create feature-specific stores

4. **Export through `index.ts`** - internal files are private to the feature

## Feature Structure

### Frontend (`apps/ui/src/features/{feature-name}/`)

```
features/{feature-name}/
├── components/          # React components
│   ├── {Feature}Page.tsx
│   ├── {Feature}List.tsx
│   └── {Feature}Dialog.tsx
├── hooks/               # React hooks
│   ├── use-{feature}.ts
│   └── use-{feature}-mutations.ts
├── store.ts             # Zustand store (if needed)
├── api.ts               # API client functions
└── index.ts             # Public exports
```

### Backend (`apps/server/src/features/{feature-name}/`)

```
features/{feature-name}/
├── routes.ts            # Express route handlers
├── service.ts           # Business logic
├── storage.ts           # Data access layer
└── index.ts             # Public exports
```

### Types (`libs/types/src/{feature}.ts`)

```typescript
// Example: libs/types/src/my-feature.ts
export interface MyFeature {
  id: string;
  name: string;
  // ...
}

export interface CreateMyFeatureRequest {
  name: string;
  // ...
}

// Export from libs/types/src/index.ts
export * from './my-feature';
```

## Canonical Reference: SYSTEMS Feature

Use these files as templates:

### Types

- `libs/types/src/custom-agent.ts` - Complex type with nested objects
- `libs/types/src/system.ts` - Type with enum states and workflow
- `libs/types/src/knowledge.ts` - Multiple related types

### Services

- `apps/server/src/services/custom-agents-service.ts` - CRUD + special operations
- `apps/server/src/services/systems-service.ts` - CRUD + execution logic

### Routes

- `apps/server/src/routes/custom-agents/index.ts` - REST API pattern
- `apps/server/src/routes/systems/index.ts` - REST API + special endpoints

### UI Components

- `apps/ui/src/components/views/agents-page/` - Gallery + CRUD pattern
- `apps/ui/src/components/views/systems-page/` - Gallery with built-ins

## Integration Checklist

### 1. Create Types

```bash
# Create type file
touch libs/types/src/{feature}.ts

# Export from index
echo "export * from './{feature}';" >> libs/types/src/index.ts

# Rebuild types package
npm run build:packages
```

### 2. Create Backend

```bash
mkdir -p apps/server/src/features/{feature}
touch apps/server/src/features/{feature}/{routes,service,storage,index}.ts
```

Register routes in `apps/server/src/index.ts`:

```typescript
import { featureRoutes } from './features/{feature}';
app.use('/api/{feature}', featureRoutes);
```

### 3. Create Frontend

```bash
mkdir -p apps/ui/src/features/{feature}/{components,hooks}
touch apps/ui/src/features/{feature}/{api,store,index}.ts
```

### 4. Add Route

Create route file in `apps/ui/src/routes/{feature}.tsx`:

```typescript
import { createFileRoute } from '@tanstack/react-router';
import { FeaturePage } from '../features/{feature}';

export const Route = createFileRoute('/{feature}')({
  component: FeaturePage,
});
```

### 5. Add Navigation

Update navigation in `apps/ui/src/components/layout/` if needed.

## Anti-Patterns to Avoid

- Adding feature state to `app-store.ts` - use feature-specific store
- Putting components in `components/views/` - use `features/` directory
- Importing internal files - only import from `index.ts`
- Mixing concerns - keep service/routes/components separate
- Tight coupling - features should be self-contained

## Full Guide

See `FEATURE-STRATEGY.md` in the repo root for complete documentation.
