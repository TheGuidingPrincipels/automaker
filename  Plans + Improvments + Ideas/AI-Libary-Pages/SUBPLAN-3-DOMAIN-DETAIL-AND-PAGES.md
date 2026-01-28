# Sub-Plan 3: Domain Detail View and Page Gallery

**Plan ID:** `SUBPLAN-3-DOMAIN-DETAIL-AND-PAGES`

## Objective

Create the full Domain Detail View that displays all pages (files) within a selected domain. Users can browse pages in a grid layout, search within the domain, and click through to view page content.

## Intent lock (must NOT change)

This is **frontend-only domain detail layering**: do **not** change backend APIs, storage, taxonomy generation, or persistence. Domains and pages are derived from existing `category` + `file` metadata returned by the Knowledge Library API.

## Non-goals

- No backend changes (Python AI-Library) and no API contract changes
- No image generation/upload (handled in **Sub-Plan 4**); this plan only renders placeholders when `imageUrl` is missing
- No new persistence for domain/page metadata (UI derives everything from existing API responses)

## Prerequisites

- **Sub-Plan 1 completed**: Domain types and configuration exist
- **Sub-Plan 2 completed**: Domain Gallery UI is functional
- Working knowledge of React, Tailwind CSS, and shadcn/ui components

## Assumptions (Sub-Plan 1 + 2 are already implemented in code)

These artifacts/exports are assumed to exist when executing this plan:

- `apps/ui/src/config/domains.ts`: `getDomainById`
- `apps/ui/src/lib/domain-utils.ts`: `getPageCardsForDomain`
- `@automaker/types`: `KLDomainId`, `KLPageCard`, `KLLibraryFileResponse`, `KLLibraryCategoryResponse`
- `apps/ui/src/store/knowledge-library-store.ts`: `selectedDomainId`, `clearSelectedDomain`, `selectedFilePath`, `setSelectedFilePath`
- Placeholder exists to replace: `apps/ui/src/components/views/knowledge-library/components/domain-detail/index.tsx`

## Deliverables

1. Full Domain Detail View with header, search, and page gallery
2. Page Card component with image placeholder, title, and overview
3. Page Content Viewer integration (reuse existing FileViewer)
4. Domain statistics and category filtering
5. Explicit loading/error UI (no silent fallbacks)
6. Unit tests for page gallery filter/sort utilities (TDD: red → green)

---

## Step 0 (TDD): Add Page Gallery filter/sort unit tests (RED)

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-detail/page-gallery.utils.test.ts` (NEW FILE)

**Command:**  
`npx vitest run --root apps/ui -c vitest.config.ts src/components/views/knowledge-library/components/domain-detail/page-gallery.utils.test.ts`

**Expected result:** Test run fails initially (module not found, or failing assertions). Do not “green” this by removing assertions.

```ts
import { describe, expect, it } from 'vitest';

import type { KLPageCard } from '@automaker/types';
import { getDisplayedPages } from './page-gallery.utils';

const makePage = (overrides: Partial<KLPageCard>): KLPageCard => ({
  path: overrides.path ?? 'x.md',
  title: overrides.title ?? 'Title',
  overview: overrides.overview ?? null,
  category: overrides.category ?? 'technical/programming',
  domainId: overrides.domainId ?? 'coding-development',
  blockCount: overrides.blockCount ?? 1,
  lastModified: overrides.lastModified ?? '2024-01-01T00:00:00Z',
  imageUrl: overrides.imageUrl,
});

describe('page-gallery.utils', () => {
  it('filters by search query across title/overview/category (case-insensitive)', () => {
    const pages = [
      makePage({
        title: 'JavaScript Basics',
        overview: 'Intro',
        category: 'technical/programming',
      }),
      makePage({ title: 'Embeddings', overview: 'Vector search', category: 'technical/ai_ml' }),
    ];

    const result = getDisplayedPages(pages, {
      searchQuery: 'javascript',
      sortBy: 'title',
      categoryFilter: null,
    });

    expect(result).toHaveLength(1);
    expect(result[0]?.title).toBe('JavaScript Basics');
  });

  it('filters by category when categoryFilter is set', () => {
    const pages = [
      makePage({ title: 'A', category: 'technical/programming' }),
      makePage({ title: 'B', category: 'technical/ai_ml' }),
    ];

    const result = getDisplayedPages(pages, {
      searchQuery: '',
      sortBy: 'title',
      categoryFilter: 'technical/ai_ml',
    });

    expect(result).toHaveLength(1);
    expect(result[0]?.title).toBe('B');
  });

  it('sorts by blocks (desc) and by date (desc)', () => {
    const pages = [
      makePage({ title: 'A', blockCount: 2, lastModified: '2024-01-01T00:00:00Z' }),
      makePage({ title: 'B', blockCount: 5, lastModified: '2024-02-01T00:00:00Z' }),
    ];

    const byBlocks = getDisplayedPages(pages, {
      searchQuery: '',
      sortBy: 'blocks',
      categoryFilter: null,
    });
    expect(byBlocks.map((p) => p.title)).toEqual(['B', 'A']);

    const byDate = getDisplayedPages(pages, {
      searchQuery: '',
      sortBy: 'date',
      categoryFilter: null,
    });
    expect(byDate.map((p) => p.title)).toEqual(['B', 'A']);
  });
});
```

---

## Step 1: Create Page Card Component

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-detail/page-card.tsx` (NEW FILE)

```tsx
/**
 * Page Card - Visual card representing a knowledge page within a domain
 *
 * Displays page title, overview, category, and metadata.
 * Clickable to view page content.
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileText, Clock, Layers, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KLPageCard } from '@automaker/types';

interface PageCardProps {
  page: KLPageCard;
  onClick: () => void;
  isSelected?: boolean;
}

export function PageCard({ page, onClick, isSelected }: PageCardProps) {
  // Format the last modified date
  const formattedDate = page.lastModified
    ? new Date(page.lastModified).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : 'Unknown';

  // Get category display name (last part of path)
  const categoryName = page.category.split('/').pop() || page.category;

  return (
    <Card
      className={cn(
        'group cursor-pointer transition-all overflow-hidden',
        isSelected ? 'border-primary shadow-md' : 'hover:border-primary/50 hover:shadow-md'
      )}
      onClick={onClick}
      data-testid={`page-card-${page.path}`}
    >
      {/* Image/Placeholder Area */}
      <div className="h-32 bg-gradient-to-br from-muted/50 to-muted flex items-center justify-center relative">
        {page.imageUrl ? (
          <img src={page.imageUrl} alt={page.title} className="w-full h-full object-cover" />
        ) : (
          <FileText className="h-12 w-12 text-muted-foreground/40" />
        )}

        {/* Arrow indicator on hover */}
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="bg-background/80 backdrop-blur-sm rounded-full p-1.5">
            <ArrowRight className="h-4 w-4 text-primary" />
          </div>
        </div>

        {/* Category badge */}
        <div className="absolute bottom-2 left-2">
          <Badge variant="secondary" className="bg-background/80 backdrop-blur-sm text-xs">
            {categoryName}
          </Badge>
        </div>
      </div>

      <CardHeader className="pb-2">
        <CardTitle className="text-base line-clamp-1 group-hover:text-primary transition-colors">
          {page.title}
        </CardTitle>
      </CardHeader>

      <CardContent>
        {/* Overview */}
        {page.overview ? (
          <CardDescription className="line-clamp-2 text-sm mb-3">{page.overview}</CardDescription>
        ) : (
          <CardDescription className="line-clamp-2 text-sm mb-3 italic text-muted-foreground/60">
            No overview available
          </CardDescription>
        )}

        {/* Metadata */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Layers className="h-3 w-3" />
            <span>{page.blockCount} blocks</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{formattedDate}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Step 2: Create Page Gallery Component

### Step 2a: Add filter/sort utilities (GREEN)

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-detail/page-gallery.utils.ts` (NEW FILE)

```ts
import type { KLPageCard } from '@automaker/types';

export type SortOption = 'title' | 'date' | 'blocks';

interface PageGalleryFilters {
  searchQuery: string;
  sortBy: SortOption;
  categoryFilter: string | null;
}

export const getDisplayedPages = (
  pages: KLPageCard[],
  { searchQuery, sortBy, categoryFilter }: PageGalleryFilters
): KLPageCard[] => {
  let result = [...pages];

  // Apply search filter
  const trimmed = searchQuery.trim();
  if (trimmed) {
    const query = trimmed.toLowerCase();
    result = result.filter(
      (page) =>
        page.title.toLowerCase().includes(query) ||
        page.overview?.toLowerCase().includes(query) ||
        page.category.toLowerCase().includes(query)
    );
  }

  // Apply category filter
  if (categoryFilter) {
    result = result.filter((page) => page.category === categoryFilter);
  }

  // Apply sorting
  switch (sortBy) {
    case 'title':
      result.sort((a, b) => a.title.localeCompare(b.title));
      break;
    case 'date':
      result.sort((a, b) => {
        const dateA = new Date(a.lastModified || 0).getTime();
        const dateB = new Date(b.lastModified || 0).getTime();
        return dateB - dateA; // Newest first
      });
      break;
    case 'blocks':
      result.sort((a, b) => b.blockCount - a.blockCount); // Most blocks first
      break;
  }

  return result;
};
```

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-detail/page-gallery.tsx` (NEW FILE)

```tsx
/**
 * Page Gallery - Grid of page cards within a domain
 *
 * Displays pages in a 3-column responsive grid with search filtering.
 */

import { useMemo, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, Filter, SortAsc, FileText, X } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { PageCard } from './page-card';
import { getDisplayedPages, type SortOption } from './page-gallery.utils';
import type { KLPageCard } from '@automaker/types';

interface PageGalleryProps {
  pages: KLPageCard[];
  onPageSelect: (path: string) => void;
  selectedPagePath: string | null;
}

export function PageGallery({ pages, onPageSelect, selectedPagePath }: PageGalleryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('title');
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set<string>();
    for (const page of pages) {
      cats.add(page.category);
    }
    return Array.from(cats).sort();
  }, [pages]);

  // Filter and sort pages
  const displayedPages = useMemo(() => {
    return getDisplayedPages(pages, { searchQuery, sortBy, categoryFilter });
  }, [pages, searchQuery, sortBy, categoryFilter]);

  const clearFilters = () => {
    setSearchQuery('');
    setCategoryFilter(null);
  };

  const hasFilters = searchQuery.trim() || categoryFilter;

  return (
    <div className="flex flex-col h-full">
      {/* Search and Filter Bar */}
      <div className="flex items-center gap-3 p-4 border-b">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search pages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Category Filter */}
        {categories.length > 1 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <Filter className="h-4 w-4" />
                {categoryFilter ? categoryFilter.split('/').pop() : 'Category'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Filter by Category</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setCategoryFilter(null)}>
                All Categories
              </DropdownMenuItem>
              {categories.map((category) => (
                <DropdownMenuItem key={category} onClick={() => setCategoryFilter(category)}>
                  {category.split('/').pop()}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Sort */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <SortAsc className="h-4 w-4" />
              Sort
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setSortBy('title')}>
              By Title {sortBy === 'title' && '✓'}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSortBy('date')}>
              By Date {sortBy === 'date' && '✓'}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSortBy('blocks')}>
              By Content Size {sortBy === 'blocks' && '✓'}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Clear filters */}
        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear
          </Button>
        )}
      </div>

      {/* Active filters display */}
      {hasFilters && (
        <div className="flex items-center gap-2 px-4 py-2 bg-muted/50 border-b">
          <span className="text-xs text-muted-foreground">Filters:</span>
          {searchQuery && (
            <Badge variant="secondary" className="text-xs">
              Search: "{searchQuery}"
            </Badge>
          )}
          {categoryFilter && (
            <Badge variant="secondary" className="text-xs">
              Category: {categoryFilter.split('/').pop()}
            </Badge>
          )}
          <span className="text-xs text-muted-foreground">
            ({displayedPages.length} of {pages.length} pages)
          </span>
        </div>
      )}

      {/* Page Grid */}
      <div className="flex-1 overflow-auto p-6">
        {displayedPages.length > 0 ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3" data-testid="page-gallery-grid">
            {displayedPages.map((page) => (
              <PageCard
                key={page.path}
                page={page}
                onClick={() => onPageSelect(page.path)}
                isSelected={page.path === selectedPagePath}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
              <FileText className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">
              {hasFilters ? 'No matching pages' : 'No pages yet'}
            </h3>
            <p className="text-muted-foreground mb-4 max-w-sm">
              {hasFilters
                ? 'Try adjusting your search or filters'
                : 'Upload documents in the Input tab to add pages to this domain'}
            </p>
            {hasFilters && (
              <Button variant="outline" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## Step 3: Update Domain Detail View

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-detail/index.tsx`

Replace the placeholder with the full implementation:

```tsx
/**
 * Domain Detail View - Full view showing pages within a selected domain
 *
 * Includes domain header, page gallery, and content viewer panel.
 * Supports two layouts:
 * - Gallery-only: When no page is selected
 * - Split view: Gallery + content viewer when a page is selected
 */

import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { Spinner } from '@/components/ui/spinner';
import {
  ArrowLeft,
  FileText,
  Folder,
  PanelRightClose,
  PanelRight,
  AlertCircle,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { cn } from '@/lib/utils';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import {
  useKLLibrary,
  useKLFileContent,
  useKLFileMetadata,
} from '@/hooks/queries/use-knowledge-library';
import { useIsMobile } from '@/hooks/use-media-query';
import { getDomainById } from '@/config/domains';
import { getPageCardsForDomain } from '@/lib/domain-utils';
import { PageGallery } from './page-gallery';
import { FileViewer } from '../library-browser/file-viewer';
import type {
  KLDomainId,
  KLLibraryCategoryResponse,
  KLLibraryFileResponse,
} from '@automaker/types';

interface DomainDetailViewProps {
  domainId: KLDomainId;
}

export function DomainDetailView({ domainId }: DomainDetailViewProps) {
  const { clearSelectedDomain, selectedFilePath, setSelectedFilePath } = useKnowledgeLibraryStore();
  const { data: library, isLoading, isError, error } = useKLLibrary();
  const isMobile = useIsMobile();
  const [showViewer, setShowViewer] = useState(true);

  // Get file content when a file is selected
  const fileContentQuery = useKLFileContent(selectedFilePath ?? undefined);
  const fileMetadataQuery = useKLFileMetadata(selectedFilePath ?? undefined);

  // Get domain config
  const domain = getDomainById(domainId);

  // Repo-aligned icon resolver (avoids needing `React.ComponentType` typing)
  const getIconComponent = (iconName?: string): LucideIcon => {
    if (iconName && iconName in LucideIcons) {
      return (LucideIcons as unknown as Record<string, LucideIcon>)[iconName];
    }
    return Folder;
  };

  const IconComponent = useMemo(() => getIconComponent(domain?.icon), [domain?.icon]);

  // Flatten all files from categories
  const allFiles = useMemo(() => {
    if (!library) return [];
    const files: KLLibraryFileResponse[] = [];

    const collectFiles = (categories: KLLibraryCategoryResponse[]) => {
      for (const cat of categories) {
        for (const file of cat.files) {
          files.push(file);
        }
        collectFiles(cat.subcategories);
      }
    };

    collectFiles(library.categories);
    return files;
  }, [library]);

  // Get pages for this domain
  const pageCards = useMemo(() => {
    return getPageCardsForDomain(allFiles, domainId);
  }, [allFiles, domainId]);

  // Get unique categories count
  const categoryCount = useMemo(() => {
    const cats = new Set(pageCards.map((p) => p.category));
    return cats.size;
  }, [pageCards]);

  if (!domain) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Domain not found</p>
          <Button variant="outline" onClick={clearSelectedDomain}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Domains
          </Button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-4" />
          <p className="text-muted-foreground">Loading domain pages...</p>
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
          <p className="text-sm text-muted-foreground mb-4">
            {error instanceof Error ? error.message : 'Unable to connect to Knowledge Library API'}
          </p>
          <Button variant="outline" onClick={clearSelectedDomain}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Domains
          </Button>
        </div>
      </div>
    );
  }

  // Handle page selection
  const handlePageSelect = (path: string) => {
    setSelectedFilePath(path);
    setShowViewer(true);
  };

  // Close content viewer
  const handleCloseViewer = () => {
    setSelectedFilePath(null);
    setShowViewer(false);
  };

  const handleToggleViewer = () => {
    if (!selectedFilePath) return;
    if (showViewer) {
      // On mobile, “hide viewer” behaves like “close” (clears selection) to keep UX simple.
      if (isMobile) {
        handleCloseViewer();
      } else {
        setShowViewer(false);
      }
      return;
    }
    setShowViewer(true);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Domain Header */}
      <div className={cn('border-b shrink-0')}>
        <div
          className={cn('h-24 bg-gradient-to-br flex items-center px-6', domain.gradientClasses)}
        >
          {/* Back button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={clearSelectedDomain}
            className="shrink-0 mr-4 bg-background/50 hover:bg-background/80"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>

          {/* Domain info */}
          <div className="flex items-center gap-4 flex-1">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-background/50">
              <IconComponent className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{domain.name}</h1>
              <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                <div className="flex items-center gap-1">
                  <FileText className="h-4 w-4" />
                  <span>{pageCards.length} pages</span>
                </div>
                <div className="flex items-center gap-1">
                  <Folder className="h-4 w-4" />
                  <span>{categoryCount} categories</span>
                </div>
              </div>
            </div>
          </div>

          {/* Toggle viewer button */}
          {selectedFilePath && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleToggleViewer}
              className="shrink-0 bg-background/50 hover:bg-background/80"
            >
              {showViewer ? (
                <PanelRightClose className="h-5 w-5" />
              ) : (
                <PanelRight className="h-5 w-5" />
              )}
            </Button>
          )}
        </div>

        {/* Domain description */}
        <div className="px-6 py-3 bg-muted/30">
          <p className="text-sm text-muted-foreground">{domain.description}</p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Page Gallery */}
        <div className={cn('flex-1 overflow-hidden', selectedFilePath && showViewer && 'border-r')}>
          <PageGallery
            pages={pageCards}
            onPageSelect={handlePageSelect}
            selectedPagePath={selectedFilePath}
          />
        </div>

        {/* Content Viewer (desktop split panel) */}
        {selectedFilePath && showViewer && !isMobile && (
          <div className="w-[500px] overflow-hidden flex flex-col shrink-0">
            <div className="flex items-center justify-between p-3 border-b bg-muted/30">
              <h3 className="text-sm font-medium truncate">
                {fileMetadataQuery.data?.title || 'Loading...'}
              </h3>
              <Button variant="ghost" size="icon" onClick={handleCloseViewer} className="h-8 w-8">
                <LucideIcons.X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-hidden">
              <FileViewer
                filePath={selectedFilePath}
                content={fileContentQuery.data?.content ?? null}
                isLoading={fileContentQuery.isLoading}
                error={fileContentQuery.error}
                metadata={fileMetadataQuery.data ?? null}
              />
            </div>
          </div>
        )}

        {/* Content Viewer (mobile sheet) */}
        <Sheet
          open={!!selectedFilePath && showViewer && isMobile}
          onOpenChange={(open) => !open && handleCloseViewer()}
        >
          <SheetContent side="right" className="p-0 w-[90vw] sm:max-w-sm">
            <div className="h-full overflow-hidden flex flex-col">
              <div className="flex items-center justify-between p-3 border-b bg-muted/30">
                <h3 className="text-sm font-medium truncate">
                  {fileMetadataQuery.data?.title || 'Loading...'}
                </h3>
              </div>
              <div className="flex-1 overflow-hidden">
                <FileViewer
                  filePath={selectedFilePath}
                  content={fileContentQuery.data?.content ?? null}
                  isLoading={fileContentQuery.isLoading}
                  error={fileContentQuery.error}
                  metadata={fileMetadataQuery.data ?? null}
                />
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </div>
  );
}

// Export components
export { PageCard } from './page-card';
export { PageGallery } from './page-gallery';
```

---

## Step 4: Update Store for File Path Handling

Ensure the store properly handles clearing the file path when navigating back to the domain gallery. In `apps/ui/src/store/knowledge-library-store.ts`, confirm that `clearSelectedDomain` clears `selectedFilePath`:

```typescript
clearSelectedDomain: () => {
  set({ selectedDomainId: null, selectedFilePath: null });
},
```

---

## Visual Design Reference

### Domain Detail View Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ [←]  🧠 AI & LLMs                              [Toggle Viewer]     │
│      📄 42 pages • 📁 5 categories                                  │
├─────────────────────────────────────────────────────────────────────┤
│ Artificial intelligence, large language models, machine learning... │
├─────────────────────────────────────────────────────────────────────┤
│ [🔍 Search pages...         ] [Category ▼] [Sort ▼] [Clear]        │
├────────────────────────────────────────────┬────────────────────────┤
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  │  Page Title           │
│ │ Page 1   │  │ Page 2   │  │ Page 3   │  │  ─────────────        │
│ │          │  │          │  │          │  │  Content preview      │
│ └──────────┘  └──────────┘  └──────────┘  │  with markdown        │
│                                            │  rendering...         │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  │                        │
│ │ Page 4   │  │ Page 5   │  │ Page 6   │  │                        │
│ │          │  │          │  │          │  │                        │
│ └──────────┘  └──────────┘  └──────────┘  │                        │
└────────────────────────────────────────────┴────────────────────────┘
        Page Gallery (scrollable)              Content Viewer
```

### Page Card Layout

```
┌─────────────────────────────────────┐
│                               [→]   │
│     ┌─────────────────────┐         │  <- Image or placeholder
│     │                     │         │
│     │    📄 (icon)        │         │
│     │                     │         │
│     └─────────────────────┘         │
│ [category-name]                     │
├─────────────────────────────────────┤
│ Page Title                          │  <- CardHeader
├─────────────────────────────────────┤
│ Overview text that spans maximum    │  <- CardContent
│ two lines with truncation...        │
│                                     │
│ 📦 15 blocks • 🕐 Jan 15, 2024      │  <- Metadata
└─────────────────────────────────────┘
```

---

## Verification

After completing these steps:

### Automated (fast)

Run UI unit tests (including the new page gallery utils tests):

```bash
npx vitest run --root apps/ui -c vitest.config.ts
```

**Pass condition:** Exit code 0.

### Manual UI

1. **Gallery View:**
   - Navigate to Knowledge Library → select a domain
   - Verify page cards display in 3-column grid
   - Verify search filters pages correctly
   - Verify category filter works
   - Verify sort options work

2. **Content Viewer:**
   - Click a page card
   - Verify content viewer panel appears
   - Verify file content loads correctly
   - Verify close button works
   - Verify toggle button shows/hides viewer

3. **Navigation:**
   - Click back button
   - Verify return to domain gallery
   - Verify selected file is cleared

4. **Empty States:**
   - Test with empty domain (no pages)
   - Test with no search results
   - Verify appropriate messages display

5. **Responsive:**
   - Resize window
   - Verify grid adjusts (3 → 2 → 1 columns)
   - Verify on small screens the page viewer opens as a slide-over (Sheet) instead of a split panel

---

## Future Enhancements (Not in Scope)

- Page image generation/upload
- Drag-and-drop page reordering
- Bulk page operations
- Domain statistics dashboard
- Export domain content

---

## Integration Notes

### FileViewer Reuse

The FileViewer component from `library-browser/file-viewer.tsx` is reused for content display. Ensure the import path is correct:

```typescript
import { FileViewer } from '../library-browser/file-viewer';
```

### Query Hook Usage

The component uses existing hooks:

- `useKLLibrary()` - Fetches library structure
- `useKLFileContent(path)` - Fetches file content
- `useKLFileMetadata(path)` - Fetches file metadata

These hooks should already be available in `@/hooks/queries/use-knowledge-library`.

### Responsive Viewer (mobile)

Mobile behavior uses the existing media query hook and Sheet component:

- `useIsMobile()` from `@/hooks/use-media-query`
- `Sheet`/`SheetContent` from `@/components/ui/sheet`

---

## Completion Checklist

- [ ] Page Card component created and styled
- [ ] Page Gallery component with search/filter
- [ ] Page Gallery filter/sort utils + unit tests
- [ ] Domain Detail View with header and split layout
- [ ] Content Viewer integration working
- [ ] Explicit loading/error UI present for library load failures
- [ ] Back navigation to domain gallery
- [ ] File selection state management
- [ ] Empty states for no pages/no results
- [ ] Responsive grid layout
- [ ] Viewer responsive behavior (desktop split + mobile sheet)
