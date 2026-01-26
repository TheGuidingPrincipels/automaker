# Frontend Architecture Reference

> **Token-efficient context summary for downstream Claude sessions**  
> Last updated: 2026-01-20

---

## Tech Stack

| Layer      | Technology                          |
| ---------- | ----------------------------------- |
| Framework  | **React 19** + **TypeScript 5.9**   |
| Build      | **Vite 7** + `@vitejs/plugin-react` |
| Routing    | **TanStack Router** (file-based)    |
| Styling    | **Tailwind CSS 4**                  |
| Components | **Radix UI** + **shadcn/ui**        |
| State      | **Zustand** + **TanStack Query**    |
| Desktop    | **Electron** (optional)             |

---

## Key Paths

```
apps/ui/
├── src/
│   ├── routes/           # TanStack file-based routes
│   ├── components/
│   │   ├── views/        # Page components (per-route)
│   │   ├── ui/           # shadcn primitives
│   │   └── layout/       # Sidebar, navigation
│   ├── lib/              # Utils, API clients
│   ├── store/            # Zustand stores
│   ├── hooks/            # Custom hooks
│   └── routeTree.gen.ts  # Auto-generated route tree
libs/types/src/           # Shared TypeScript types
```

---

## Adding New Routes

### Pattern: File-based routing with TanStack Router

1. **Create route file** in `apps/ui/src/routes/`:
   - Simple: `mypage.tsx` → `/mypage`
   - Nested layout: `parent.tsx` (with `<Outlet />`) + `parent.child.tsx`
   - Dynamic param: `parent.$paramId.tsx` → `/parent/:paramId`

2. **Create view component** in `apps/ui/src/components/views/mypage/`:

   ```
   mypage/
   ├── index.tsx           # Main component export
   └── components/         # Sub-components (header, etc.)
   ```

3. **Route file template**:

   ```tsx
   import { createFileRoute } from '@tanstack/react-router';
   import { MyPage } from '@/components/views/mypage';

   export const Route = createFileRoute('/mypage')({
     component: MyPage,
   });
   ```

4. **Add to sidebar** (optional): Edit `apps/ui/src/components/layout/sidebar/hooks/use-navigation.ts`:
   - Add to `shortcuts` interface
   - Add `NavItem` to appropriate section in `navSections`

---

## Systems Section

### Current Structure

- **Route**: `/systems` → `systems-page/index.tsx`
- **Detail**: `/systems/$systemId` → `system-detail-page/index.tsx`
- **Types**: `libs/types/src/system.ts` (`System`, `SystemAgent`, etc.)

### Adding a Built-in System

1. Add entry to `BUILT_IN_SYSTEMS` array in `systems-page/index.tsx`:

   ```tsx
   {
     id: 'my-new-system',
     name: 'My System',
     description: '...',
     status: 'active',
     agents: [
       { id: 'agent1', name: 'Agent 1', role: 'analyzer', order: 1 },
     ],
     workflow: [],
     icon: 'FileSearch', // Lucide icon name
     category: 'Development',
     tags: ['tag1', 'tag2'],
     isBuiltIn: true,
     createdAt: '2024-01-01T00:00:00Z',
     updatedAt: '2024-01-01T00:00:00Z',
   }
   ```

2. Add matching entry to `MOCK_SYSTEMS` in `system-detail-page/index.tsx`

3. (Optional) Add to `BuiltInSystemId` type in `libs/types/src/system.ts`

### Icon Map (available icons)

`FileSearch`, `Bug`, `LayoutList`, `Users`, `Zap`, `Workflow`

---

## Knowledge Hub Section

### Current Structure

- **Hub index**: `/knowledge-hub` → `knowledge-hub-page/index.tsx`
- **Section view**: `/knowledge-hub/$section` → `knowledge-section-page/index.tsx`
- **Types**: `libs/types/src/knowledge.ts`

### Section IDs (from `KnowledgeSection` type)

- `blueprints` - Guidelines and processes
- `knowledge-server` - Company knowledge storage
- `learning` - Agent learnings

### Adding a New Section

1. **Update type** in `libs/types/src/knowledge.ts`:

   ```tsx
   export type KnowledgeSection = 'knowledge-library' | 'knowledge-server' | 'learning';
   ```

2. **Add section config** in `knowledge-hub-page/index.tsx` (`SECTIONS` array):

   ```tsx
   {
     id: 'knowledge-library',
     name: 'Knowledge Library',
     description: '...',
     icon: SomeIcon,
     itemCount: 0,
     color: 'from-amber-500/20 to-amber-600/10',
     features: ['Feature 1', 'Feature 2'],
   }
   ```

3. **Add section handling** in `knowledge-section-page/index.tsx`:
   - Add to `SECTION_CONFIG` map
   - Add mock data array (e.g., `MOCK_LIBRARY_ITEMS`)
   - Add render logic in the component

### Replacing Blueprints with Library

To replace blueprints entirely:

1. Change section ID from `'blueprints'` to `'library'` in all files
2. Update `KnowledgeSection` type
3. Update or replace `Blueprint` type with `LibraryItem` type
4. Update UI components and mock data

---

## Type Definitions

### Core Types Location: `libs/types/src/`

| File              | Key Types                                                     |
| ----------------- | ------------------------------------------------------------- |
| `system.ts`       | `System`, `SystemAgent`, `SystemAgentRole`, `BuiltInSystemId` |
| `knowledge.ts`    | `KnowledgeSection`, `Blueprint`, `KnowledgeEntry`, `Learning` |
| `custom-agent.ts` | `CustomAgent`, `CustomAgentModelConfig`                       |

### Adding New Types

1. Create/edit file in `libs/types/src/`
2. Export from `libs/types/src/index.ts`
3. Run `npm run build -w @automaker/types`

---

## Component Patterns

### View Component Structure

```tsx
export function MyPage() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col h-full">
      <MyPageHeader {...props} />

      <div className="flex-1 overflow-auto p-6">{/* Content */}</div>
    </div>
  );
}
```

### Card Component Pattern (Gallery pages)

```tsx
<Card className="group cursor-pointer hover:border-primary/50">
  <div className="h-32 bg-gradient-to-br from-primary/10">
    <Icon className="..." />
  </div>
  <CardHeader>
    <CardTitle>{title}</CardTitle>
  </CardHeader>
  <CardContent>
    <CardDescription>{description}</CardDescription>
  </CardContent>
</Card>
```

---

## Quick Reference

### Run Dev Server

```bash
npm run dev:web  # Web only
npm run dev:electron  # Electron app
```

### Build Types After Changes

```bash
npm run build:packages
```

### Route Auto-Generation

Route tree regenerates automatically on file changes in `src/routes/`.

---

## Library Feature (Planned)

> Replacing "Blueprints" in Knowledge Hub

### Proposed Changes

1. **Type**: Create `LibraryItem` type or rename `Blueprint`
2. **Section ID**: `'library'` replaces `'blueprints'`
3. **UI**: Update `SECTIONS` config in knowledge-hub-page
4. **Content**: New mock data structure for library items

### Files to Modify

- `libs/types/src/knowledge.ts`
- `apps/ui/src/components/views/knowledge-hub-page/index.tsx`
- `apps/ui/src/components/views/knowledge-section-page/index.tsx`
