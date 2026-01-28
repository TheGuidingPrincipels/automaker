# Sub-Plan 2: Domain Gallery UI Component

**Plan ID:** `SUBPLAN-2-DOMAIN-GALLERY-UI`

## Objective

Create the visual Domain Gallery that displays the nine knowledge domains in a 3x3 grid layout with icons/gradients and statistics (domain/page images are handled in Sub-Plan 4). Users click a domain card to navigate to its detail view.

## Intent lock (must NOT change)

This is **frontend-only domain navigation layering**: do **not** change backend APIs, storage, taxonomy generation, or persistence. Domains are derived from existing `category` path strings returned by the Knowledge Library API.

## Non-goals

- No backend changes
- No page/domain image rendering or generation (handled in **Sub-Plan 4**)
- No full Domain Detail implementation (handled in **Sub-Plan 3**)

## Prerequisites

- **Sub-Plan 1 completed**: Domain types and configuration exist
- Working knowledge of React, Tailwind CSS, and shadcn/ui components
- Understanding of the existing Knowledge Library UI patterns
- **Repo testing reality:** UI unit tests + typecheck run under the UI workspace (`--root apps/ui` or `--workspace=apps/ui`)

## Preflight (Sub-Plan 1 Gate — STOP if failing)

This sub-plan is only executable **after Sub-Plan 1 has been implemented in code** (not just written).

**Required files must exist:**

- `apps/ui/src/config/domains.ts`
- `apps/ui/src/lib/domain-utils.ts`

**Required exports must resolve (compile-time):**

- `@/config/domains`: `getDomainById`
- `@/lib/domain-utils`: `getDomainsWithStats`
- `@automaker/types`: `KLDomainId`, `KLDomainWithStats`

**Quick checks (run from repo root):**

```bash
test -f "apps/ui/src/config/domains.ts"
test -f "apps/ui/src/lib/domain-utils.ts"
npm run typecheck --workspace=apps/ui
```

**Stop condition:** If any check fails, STOP and execute Sub-Plan 1 first.

## Deliverables

1. Domain Gallery component with 3x3 responsive grid
2. Domain Card component with icon/gradient, title, description, and stats
3. Updated Knowledge Library “Library” tab to render `LibraryMode` (Domains default) while keeping `LibraryBrowser` accessible
4. Updated Zustand store for domain navigation state

---

## Step 1: Update Knowledge Library Store

**File:** `apps/ui/src/store/knowledge-library-store.ts`

Add domain navigation state **repo-aligned** (this store has separate `KnowledgeLibraryState`, `KnowledgeLibraryActions`, and a typed `initialState` object).

1. Add the type import near the top of the file (with other imports):

```typescript
import type { KLDomainId } from '@automaker/types';
```

2. Add to `KnowledgeLibraryState` (place near “Library browser state”):

```typescript
/** Currently selected domain (null = show domain gallery view) */
selectedDomainId: KLDomainId | null;
```

3. Add to `KnowledgeLibraryActions`:

```typescript
  /** Domain navigation actions */
  setSelectedDomainId: (domainId: KLDomainId | null) => void;
  clearSelectedDomain: () => void;
```

4. Add to `initialState`:

```typescript
  selectedDomainId: null,
```

5. Implement the actions inside the store body (near other “Library browser actions”):

```typescript
  setSelectedDomainId: (domainId) => {
    // Prevent stale file selection when entering domain views (Sub-Plan 3 uses selectedFilePath)
    set({ selectedDomainId: domainId, selectedFilePath: null });
  },

  clearSelectedDomain: () => {
    set({ selectedDomainId: null, selectedFilePath: null });
  },
```

6. Update `resetSession()` to clear `selectedDomainId` (resetting a session clears session work and domain selection):

```typescript
  resetSession: () =>
    set({
      // ... existing resets ...
      selectedDomainId: null,
    }),
```

7. Persistence: do **not** add `selectedDomainId` to `partialize` (it should not persist). The existing `partialize` already persists only `activeView` + `currentSessionId`.

```typescript
partialize: (state) => ({
  activeView: state.activeView,
  currentSessionId: state.currentSessionId,
}),
```

8. Update store unit tests (required, targeted):

**File:** `apps/ui/src/store/knowledge-library-store.test.ts`

- In the `beforeEach` store reset object, add `selectedDomainId: null` to keep tests deterministic.
- In the “persists only activeView and currentSessionId” test, set `selectedDomainId` and keep the expected persisted object unchanged.

---

## Step 2: Create Domain Card Component

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-gallery/domain-card.tsx` (NEW FILE)

```tsx
/**
 * Domain Card - Visual card representing a knowledge domain
 *
 * Displays domain icon/image, name, description, and statistics.
 * Clickable to navigate to domain detail view.
 */

import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { LucideIcon } from 'lucide-react';
import { ArrowRight, FileText, Folder } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KLDomainWithStats } from '@automaker/types';

interface DomainCardProps {
  domain: KLDomainWithStats;
  onClick: () => void;
}

// Repo-aligned icon resolver (avoids needing `React.ComponentType` typing)
const getIconComponent = (iconName?: string): LucideIcon => {
  if (iconName && iconName in LucideIcons) {
    return (LucideIcons as unknown as Record<string, LucideIcon>)[iconName];
  }
  return Folder;
};

export function DomainCard({ domain, onClick }: DomainCardProps) {
  // NOTE: Domain image URLs are handled in Sub-Plan 4; this card uses icon + gradient only.
  const IconComponent = useMemo(() => getIconComponent(domain.icon), [domain.icon]);

  return (
    <Card
      className="group cursor-pointer hover:border-primary/50 hover:shadow-lg transition-all overflow-hidden"
      onClick={onClick}
      data-testid={`domain-card-${domain.id}`}
    >
      {/* Header gradient with icon */}
      <div
        className={cn(
          'h-32 bg-gradient-to-br flex items-center justify-center relative',
          domain.gradientClasses
        )}
      >
        {/* Main icon */}
        <IconComponent className="h-16 w-16 text-primary/60 group-hover:text-primary group-hover:scale-110 transition-all" />

        {/* Arrow indicator on hover */}
        <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <ArrowRight className="h-5 w-5 text-primary/70" />
        </div>

        {/* File count badge */}
        {domain.fileCount > 0 && (
          <div className="absolute bottom-3 right-3">
            <Badge variant="secondary" className="bg-background/80 backdrop-blur-sm">
              {domain.fileCount} {domain.fileCount === 1 ? 'page' : 'pages'}
            </Badge>
          </div>
        )}
      </div>

      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg line-clamp-1">{domain.name}</CardTitle>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <CardDescription className="line-clamp-2 text-sm mb-3">
          {domain.description}
        </CardDescription>

        {/* Statistics */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5" />
            <span>{domain.fileCount} pages</span>
          </div>
          <div className="flex items-center gap-1">
            <Folder className="h-3.5 w-3.5" />
            <span>{domain.categoryCount} categories</span>
          </div>
        </div>

        {/* Sample keywords */}
        {domain.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {domain.keywords.slice(0, 3).map((keyword) => (
              <Badge key={keyword} variant="outline" className="text-xs px-1.5 py-0">
                {keyword}
              </Badge>
            ))}
            {domain.keywords.length > 3 && (
              <Badge variant="outline" className="text-xs px-1.5 py-0 text-muted-foreground">
                +{domain.keywords.length - 3}
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## Step 3: Create Domain Gallery Component

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-gallery/index.tsx` (NEW FILE)

```tsx
/**
 * Domain Gallery - 3x3 grid of knowledge domain cards
 *
 * Primary view when Library tab is selected. Shows all nine domains
 * with their statistics and visual representations.
 */

import { useMemo } from 'react';
import { useKLLibrary } from '@/hooks/queries/use-knowledge-library';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import { DomainCard } from './domain-card';
import { Spinner } from '@/components/ui/spinner';
import { AlertCircle, Library } from 'lucide-react';
import { getDomainsWithStats } from '@/lib/domain-utils';
import type { KLDomainId, KLDomainWithStats, KLLibraryFileResponse } from '@automaker/types';

export function DomainGallery() {
  const { data: library, isLoading, isError, error } = useKLLibrary();
  const { setSelectedDomainId } = useKnowledgeLibraryStore();

  // Flatten all files from categories
  const allFiles = useMemo(() => {
    if (!library) return [];
    const files: KLLibraryFileResponse[] = [];

    const collectFiles = (categories: typeof library.categories) => {
      for (const cat of categories) {
        for (const file of cat.files) {
          files.push(file);
        }
        if (cat.subcategories) {
          collectFiles(cat.subcategories);
        }
      }
    };

    collectFiles(library.categories);
    return files;
  }, [library]);

  // Calculate domain statistics
  const domainsWithStats: KLDomainWithStats[] = useMemo(() => {
    return getDomainsWithStats(allFiles);
  }, [allFiles]);

  // Handle domain click
  const handleDomainClick = (domainId: KLDomainId) => {
    setSelectedDomainId(domainId);
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-4" />
          <p className="text-muted-foreground">Loading library...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Failed to load library</h3>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : 'Unable to connect to Knowledge Library API'}
          </p>
        </div>
      </div>
    );
  }

  // Calculate totals
  const totalFiles = domainsWithStats.reduce((sum, d) => sum + d.fileCount, 0);
  const totalBlocks = domainsWithStats.reduce((sum, d) => sum + d.totalBlocks, 0);

  return (
    <div className="h-full overflow-auto p-6">
      {/* Introduction */}
      <div className="max-w-3xl mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Library className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold">Knowledge Domains</h2>
            <p className="text-sm text-muted-foreground">
              {totalFiles} pages • {totalBlocks} content blocks
            </p>
          </div>
        </div>
        <p className="text-muted-foreground">
          Browse your knowledge library organized by domain. Click a domain to explore its pages and
          content.
        </p>
      </div>

      {/* Domain Cards Grid - 3 columns */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3" data-testid="domain-gallery-grid">
        {domainsWithStats.map((domain) => (
          <DomainCard
            key={domain.id}
            domain={domain}
            onClick={() => handleDomainClick(domain.id)}
          />
        ))}
      </div>

      {/* Empty state if no content */}
      {totalFiles === 0 && (
        <div className="mt-8 text-center py-8 border rounded-lg bg-muted/20">
          <Library className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Your library is empty</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Upload documents in the Input tab to populate your knowledge library. Content will be
            automatically organized into these domains.
          </p>
        </div>
      )}
    </div>
  );
}

// Export components
export { DomainCard } from './domain-card';
```

---

## Step 4: Create Library Mode Container

**File:** `apps/ui/src/components/views/knowledge-library/components/library-mode/index.tsx` (NEW FILE)

```tsx
/**
 * Library Mode - Container for library browsing views
 *
 * Provides two sub-views:
 * - Domains: DomainGallery / DomainDetailView (default)
 * - Browse: existing LibraryBrowser
 */

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import { DomainGallery } from '../domain-gallery';
import { DomainDetailView } from '../domain-detail';
import { LibraryBrowser } from '../library-browser';

type LibraryModeTab = 'domains' | 'browse';

export function LibraryMode() {
  const { selectedDomainId } = useKnowledgeLibraryStore();
  const [tab, setTab] = useState<LibraryModeTab>('domains');

  return (
    <Tabs
      value={tab}
      onValueChange={(v) => setTab(v as LibraryModeTab)}
      className="h-full flex flex-col"
    >
      {/* Keep LibraryBrowser accessible */}
      <TabsList className="mx-4 mt-3 mb-2 shrink-0">
        <TabsTrigger value="domains">Domains</TabsTrigger>
        <TabsTrigger value="browse">Browse</TabsTrigger>
      </TabsList>

      <div className="flex-1 min-h-0 overflow-hidden">
        <TabsContent value="domains" className="h-full m-0">
          {selectedDomainId ? <DomainDetailView domainId={selectedDomainId} /> : <DomainGallery />}
        </TabsContent>
        <TabsContent value="browse" className="h-full m-0">
          <LibraryBrowser />
        </TabsContent>
      </div>
    </Tabs>
  );
}
```

---

## Step 5: Create Placeholder Domain Detail View

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-detail/index.tsx` (NEW FILE)

This is a placeholder that will be fully implemented in Sub-Plan 3.

```tsx
/**
 * Domain Detail View - Shows pages within a selected domain
 *
 * This is a placeholder component. Full implementation in Sub-Plan 3.
 */

import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import { getDomainById } from '@/config/domains';
import type { KLDomainId } from '@automaker/types';

interface DomainDetailViewProps {
  domainId: KLDomainId;
}

export function DomainDetailView({ domainId }: DomainDetailViewProps) {
  const { clearSelectedDomain } = useKnowledgeLibraryStore();
  const domain = getDomainById(domainId);

  if (!domain) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Domain not found</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with back button */}
      <div className="flex items-center gap-4 p-4 border-b">
        <Button variant="ghost" size="icon" onClick={clearSelectedDomain} className="shrink-0">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h2 className="text-xl font-semibold">{domain.name}</h2>
          <p className="text-sm text-muted-foreground">{domain.description}</p>
        </div>
      </div>

      {/* Placeholder content - will be replaced in Sub-Plan 3 */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">
            Page gallery will be implemented in Sub-Plan 3
          </p>
          <Button variant="outline" onClick={clearSelectedDomain}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Domains
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

## Step 6: Update Knowledge Library Main Component

**File:** `apps/ui/src/components/views/knowledge-library/index.tsx`

Replace the Library tab content with the new LibraryMode component.

Find the imports section and add:

```typescript
import { LibraryMode } from './components/library-mode';
```

Find the `TabsContent` where `value="library"` and replace its child component:

```tsx
{
  /* Replace this: */
}
<TabsContent value="library" className="h-full m-0">
  <LibraryBrowser />
</TabsContent>;

{
  /* With this: */
}
<TabsContent value="library" className="h-full m-0">
  <LibraryMode />
</TabsContent>;
```

After this change, `LibraryBrowser` should be imported/used by `LibraryMode` (Browse tab). Remove the `LibraryBrowser` import from `knowledge-library/index.tsx` if it becomes unused.

---

## Step 7: Create Index Exports

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-gallery/index.tsx`

Already created above. Ensure it exports both components.

**File:** `apps/ui/src/components/views/knowledge-library/components/library-mode/index.tsx`

Already created above.

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-detail/index.tsx`

Already created above.

---

## Visual Design Reference

The domain cards follow the existing SystemCard pattern:

```
┌─────────────────────────────────────┐
│                                     │
│     ┌─────────┐      [Pages: 42]   │  <- Gradient background
│     │  ICON   │                     │     with icon
│     └─────────┘                     │
│                                     │
├─────────────────────────────────────┤
│ Domain Name                         │  <- CardHeader
│ [Active] [Built-in]                 │
├─────────────────────────────────────┤
│ Brief description of the domain    │  <- CardContent
│ that spans two lines maximum...     │
│                                     │
│ 📄 42 pages • 📁 5 categories       │  <- Statistics
│                                     │
│ [coding] [api] [javascript] +5      │  <- Keywords
└─────────────────────────────────────┘
```

Grid layout:

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Coding & │  │ AI &     │  │ Product- │
│ Dev      │  │ LLMs     │  │ ivity    │
└──────────┘  └──────────┘  └──────────┘

┌──────────┐  ┌──────────┐  ┌──────────┐
│ Learning │  │ Business │  │ Health   │
│          │  │          │  │          │
└──────────┘  └──────────┘  └──────────┘

┌──────────┐  ┌──────────┐  ┌──────────┐
│ Mindset  │  │ Market-  │  │ Video &  │
│          │  │ ing      │  │ Content  │
└──────────┘  └──────────┘  └──────────┘
```

---

## Verification

After completing these steps:

0. **Automated checks (required):**
   - `npm run typecheck --workspace=apps/ui` → pass condition: exit code 0
   - `npx vitest run --root apps/ui -c vitest.config.ts src/store/knowledge-library-store.test.ts` → pass condition: exit code 0

1. **Visual Check:**
   - Navigate to Knowledge Hub → Knowledge Library
   - Verify 9 domain cards appear in a 3x3 grid
   - Verify cards have correct icons, names, and descriptions
   - Verify hover effects work correctly

2. **Navigation Check:**
   - Click a domain card
   - Verify the placeholder detail view appears
   - Click "Back to Domains" button
   - Verify return to gallery view

3. **Responsive Check:**
   - Resize window to verify responsive grid (3 cols → 2 cols → 1 col)

4. **State Check:**
   - Refresh page while on a domain detail view
   - Verify user returns to gallery (state not persisted)

---

## Rollback plan

To revert safely:

1. Revert changes in:
   - `apps/ui/src/store/knowledge-library-store.ts`
   - `apps/ui/src/store/knowledge-library-store.test.ts`
   - `apps/ui/src/components/views/knowledge-library/index.tsx`
2. Delete new UI components created by this plan:
   - `apps/ui/src/components/views/knowledge-library/components/domain-gallery/`
   - `apps/ui/src/components/views/knowledge-library/components/library-mode/`
   - `apps/ui/src/components/views/knowledge-library/components/domain-detail/`
3. Re-run:
   - `npm run typecheck --workspace=apps/ui` (pass: exit code 0)
   - `npx vitest run --root apps/ui -c vitest.config.ts src/store/knowledge-library-store.test.ts` (pass: exit code 0)

## Next Steps

After completing this sub-plan:

- **Sub-Plan 3:** Domain Detail View and Page Gallery (complete implementation)
