# Sub-Plan 1: Domain Types and Configuration (Nine Core Domains)

**Plan ID:** `SUBPLAN-1-DOMAIN-TYPES-AND-CONFIG`

## Objective

Create the foundational shared types, UI configuration, and mapping utilities for the **nine core knowledge domains**. This establishes the domain data model and deterministic category→domain mapping that Sub-Plans 2–3 will depend on.

## Intent lock (must NOT change)

This is **frontend-only domain layering**: do **not** change backend APIs, storage, taxonomy generation, or persistence. Domains are derived from existing `category` path strings returned by the Knowledge Library API.

## Non-goals

- No backend changes (Python AI-Library) and no API contract changes
- No UI implementation (Domain Gallery / Domain Detail are Sub-Plans 2–3)
- No “uncategorized domain” ID (fallback is a default domain ID, not a synthetic 10th domain)

## Prerequisites

- Node + dependencies installed (repo uses npm workspaces)
- Access to edit:
  - `libs/types/src/knowledge-library.ts`
  - `libs/types/src/index.ts`
  - `apps/ui/src/config/`
  - `apps/ui/src/lib/`
- **Testing note (repo reality):** UI unit tests must be run with `--root apps/ui` because root Vitest config does not include UI.

## Deliverables

1. Domain types added to `libs/types/src/knowledge-library.ts` and exported from `@automaker/types`
2. Domain configuration at `apps/ui/src/config/domains.ts`
3. Domain mapping/statistics utilities at `apps/ui/src/lib/domain-utils.ts`
4. **Mandatory** unit tests at `apps/ui/src/lib/domain-utils.test.ts` (TDD: red → green)

---

## Minimal Execution Packet (read/run only these)

- Read: `EXECUTION-GUIDE-NINE-DOMAINS.md`
- Read: `libs/types/src/knowledge-library.ts`
- Read: `libs/types/src/index.ts`
- Read: `apps/ui/vitest.config.ts`
- Run (types build): `npm run build -w @automaker/types`
- Run (UI unit test): `npx vitest run --root apps/ui -c vitest.config.ts src/lib/domain-utils.test.ts`

---

## Step 0 (TDD): Add failing unit tests (RED)

**Purpose:** Lock the domain mapping + stats contract before implementation.

**File:** `apps/ui/src/lib/domain-utils.test.ts` (NEW FILE)

**Command:**  
`npx vitest run --root apps/ui -c vitest.config.ts src/lib/domain-utils.test.ts`

**Expected result:** The test run fails (e.g., module not found for `@/config/domains` or `@/lib/domain-utils`, or failing assertions).

**Done when:** You can show an explicit failing test output (no silent pass).

```ts
import { describe, expect, it } from 'vitest';

import { KNOWLEDGE_DOMAINS, getDomainById } from '@/config/domains';
import {
  filterDomainFiles,
  getDomainsWithStats,
  getPageCardsForDomain,
  mapCategoryToDomain,
} from '@/lib/domain-utils';
import type { KLLibraryFileResponse } from '@automaker/types';

const makeFile = (overrides: Partial<KLLibraryFileResponse>): KLLibraryFileResponse => ({
  path: overrides.path ?? 'x.md',
  category: overrides.category ?? 'technical/programming',
  title: overrides.title ?? 'Title',
  sections: overrides.sections ?? [],
  last_modified: overrides.last_modified ?? '2024-01-01T00:00:00',
  block_count: overrides.block_count ?? 1,
  overview: overrides.overview ?? null,
  is_valid: overrides.is_valid ?? true,
  validation_errors: overrides.validation_errors ?? [],
});

describe('domains config', () => {
  it('defines exactly 9 domains with unique id and order', () => {
    expect(KNOWLEDGE_DOMAINS).toHaveLength(9);

    const ids = new Set(KNOWLEDGE_DOMAINS.map((d) => d.id));
    expect(ids.size).toBe(9);

    const orders = new Set(KNOWLEDGE_DOMAINS.map((d) => d.order));
    expect(orders.size).toBe(9);
  });

  it('getDomainById returns a domain for valid ids', () => {
    expect(getDomainById('coding-development')?.name).toBeTruthy();
    expect(getDomainById('ai-llms')?.name).toBeTruthy();
  });
});

describe('domain-utils', () => {
  it('maps taxonomy-style category paths to the correct domain ids', () => {
    expect(mapCategoryToDomain('technical/programming')).toBe('coding-development');
    expect(mapCategoryToDomain('technical/ai_ml')).toBe('ai-llms');
    expect(mapCategoryToDomain('domain/finance')).toBe('business');
    expect(mapCategoryToDomain('domain/healthcare')).toBe('health');
    expect(mapCategoryToDomain('process/project_management')).toBe('productivity');
    expect(mapCategoryToDomain('reference/tutorials')).toBe('learning');
  });

  it('computes domain stats from files', () => {
    const files = [
      makeFile({ path: 'a.md', category: 'technical/programming', block_count: 2 }),
      makeFile({ path: 'b.md', category: 'technical/ai_ml', block_count: 5 }),
      makeFile({ path: 'c.md', category: 'domain/business', block_count: 3 }),
    ];

    const stats = getDomainsWithStats(files);

    const coding = stats.find((d) => d.id === 'coding-development');
    const ai = stats.find((d) => d.id === 'ai-llms');
    const business = stats.find((d) => d.id === 'business');

    expect(coding?.fileCount).toBe(1);
    expect(coding?.totalBlocks).toBe(2);

    expect(ai?.fileCount).toBe(1);
    expect(ai?.totalBlocks).toBe(5);

    expect(business?.fileCount).toBe(1);
    expect(business?.totalBlocks).toBe(3);
  });

  it('creates page cards for a domain and can filter by query', () => {
    const files = [
      makeFile({
        path: 'tech/a.md',
        category: 'technical/programming',
        title: 'JavaScript Basics',
        overview: 'Intro to JS',
      }),
      makeFile({
        path: 'ai/b.md',
        category: 'technical/ai_ml',
        title: 'Embeddings',
        overview: 'Vector search',
      }),
    ];

    const pages = getPageCardsForDomain(files, 'coding-development');
    expect(pages).toHaveLength(1);
    expect(pages[0]?.domainId).toBe('coding-development');

    const filtered = filterDomainFiles(files, 'coding-development', 'javascript');
    expect(filtered).toHaveLength(1);
  });
});
```

---

## Step 1: Add Domain Types (shared package)

**Purpose:** Add the domain model types to `@automaker/types` so Sub-Plans 2–3 can import them consistently.

**File:** `libs/types/src/knowledge-library.ts`

**Important placement (no guessing):** Insert this section **immediately before** the `// Query (RAG + Semantic Search)` header.

**Command:**  
`npm run build -w @automaker/types`

**Expected result:** Types package builds successfully (exit code 0).

**Done when:** Build passes and the new types can be imported from `@automaker/types`.

```ts
// ============================================================================
// Domain Types (Nine Core Domains - frontend-only)
// ============================================================================

/** Available knowledge domain identifiers */
export type KLDomainId =
  | 'coding-development'
  | 'ai-llms'
  | 'productivity'
  | 'learning'
  | 'business'
  | 'health'
  | 'mindset'
  | 'marketing'
  | 'video-content';

/** Domain definition */
export interface KLDomain {
  /** Unique domain identifier */
  id: KLDomainId;
  /** Display name */
  name: string;
  /** Brief description (2-3 sentences) */
  description: string;
  /** Lucide icon name */
  icon: string;
  /** Tailwind gradient classes for card background */
  gradientClasses: string;
  /** Keywords for classification and fallback matching */
  keywords: string[];
  /** Category path prefixes that map to this domain */
  pathPrefixes: string[];
  /** Order for display (1-9) */
  order: number;
  /** Optional custom image URL (overrides default) */
  imageUrl?: string;
}

/** Domain with runtime statistics */
export interface KLDomainWithStats extends KLDomain {
  /** Number of files in this domain */
  fileCount: number;
  /** Number of categories in this domain */
  categoryCount: number;
  /** Total blocks across all files */
  totalBlocks: number;
}

/** Page (file) card for display in domain view */
export interface KLPageCard {
  /** File path (unique identifier) */
  path: string;
  /** Display title */
  title: string;
  /** Short overview text */
  overview: string | null;
  /** Category path within domain */
  category: string;
  /** Domain this page belongs to */
  domainId: KLDomainId;
  /** Number of content blocks */
  blockCount: number;
  /** Last modification date */
  lastModified: string;
  /** Optional page image URL */
  imageUrl?: string;
}
```

---

## Step 2: Export Types from Package (repo-aligned)

**Purpose:** Ensure the new domain types are exported from `@automaker/types`.

**File:** `libs/types/src/index.ts`

**Instruction (no guessing):** Add `KLDomainId`, `KLDomain`, `KLDomainWithStats`, `KLPageCard` to the existing Knowledge Library export block:

> `export type { ... } from './knowledge-library.js';`

**Command:**  
`npm run build -w @automaker/types`

**Expected result:** Types build succeeds (exit code 0).

**Done when:** Build passes and imports resolve.

---

## Step 3: Create Domain Configuration (UI runtime config)

**Purpose:** Provide the runtime domain list (9 entries) and lookup helpers used by Sub-Plans 2–3.

**File:** `apps/ui/src/config/domains.ts` (NEW FILE)

**Notes:**
- Include taxonomy-style prefixes (e.g., `technical/ai_ml`, `process/project_management`) and legacy prefixes.
- **Do not** add an `UNCATEGORIZED_DOMAIN` constant (it creates identity ambiguity). Domain fallback is handled in `domain-utils.ts`.

**Expected result:** `@/config/domains` exports `KNOWLEDGE_DOMAINS`, `getDomainById`, `getAllDomainIds`, `getDomainsSorted`.

```ts
import type { KLDomain, KLDomainId } from '@automaker/types';

export const KNOWLEDGE_DOMAINS: KLDomain[] = [
  {
    id: 'coding-development',
    name: 'Coding & Development',
    description:
      'Everything related to software development, programming languages, APIs, frameworks, and development tools. From beginner tutorials to advanced architecture patterns.',
    icon: 'Code',
    gradientClasses: 'from-blue-500/20 to-blue-600/10',
    keywords: [
      'programming',
      'coding',
      'software',
      'development',
      'api',
      'framework',
      'library',
      'debugging',
      'testing',
      'git',
      'database',
      'backend',
      'frontend',
      'devops',
      'algorithms',
    ],
    // Includes broad technical fallbacks; correctness is ensured by longest-prefix-wins.
    pathPrefixes: [
      'technical/programming',
      'technical/architecture',
      'technical/devops',
      'technical/data',
      'process/development',
      'process/quality',
      'reference/apis',
      'reference/standards',
      // legacy/custom
      'coding',
      'development',
      'programming',
      'software',
      'technical',
      'engineering',
      'devops',
      'data',
      'api',
    ],
    order: 1,
  },
  {
    id: 'ai-llms',
    name: 'AI & LLMs',
    description:
      'Artificial intelligence, large language models, machine learning, prompt engineering, and AI agents. Stay current with the rapidly evolving AI landscape.',
    icon: 'Brain',
    gradientClasses: 'from-purple-500/20 to-purple-600/10',
    keywords: [
      'ai',
      'artificial intelligence',
      'llm',
      'large language model',
      'machine learning',
      'deep learning',
      'neural network',
      'prompt',
      'agent',
      'gpt',
      'claude',
      'transformer',
      'embedding',
      'rag',
    ],
    pathPrefixes: ['technical/ai_ml', 'ai', 'llm', 'machine-learning', 'artificial-intelligence', 'ml', 'rag'],
    order: 2,
  },
  {
    id: 'productivity',
    name: 'Productivity',
    description:
      'Time management, workflows, efficiency systems, and effectiveness strategies. Optimize your work and achieve more with less effort.',
    icon: 'Zap',
    gradientClasses: 'from-amber-500/20 to-amber-600/10',
    keywords: [
      'productivity',
      'efficiency',
      'time management',
      'workflow',
      'automation',
      'habits',
      'focus',
      'organization',
      'task management',
      'project management',
      'gtd',
      'pomodoro',
    ],
    pathPrefixes: ['process/project_management', 'productivity', 'workflow', 'time-management', 'project-management'],
    order: 3,
  },
  {
    id: 'learning',
    name: 'Learning',
    description:
      'Learning strategies, memory techniques, encoding methods, mind maps, and retention optimization. Master the art of learning effectively.',
    icon: 'GraduationCap',
    gradientClasses: 'from-emerald-500/20 to-emerald-600/10',
    keywords: [
      'learning',
      'memory',
      'retention',
      'spaced repetition',
      'mind map',
      'encoding',
      'study',
      'education',
      'skill acquisition',
      'deliberate practice',
      'flashcards',
      'tutorial',
      'tutorials',
    ],
    pathPrefixes: ['reference/tutorials', 'learning', 'education', 'study', 'tutorials'],
    order: 4,
  },
  {
    id: 'business',
    name: 'Business',
    description:
      'Business strategy, entrepreneurship, sales tactics, and organizational management. Build and grow successful ventures.',
    icon: 'Briefcase',
    gradientClasses: 'from-slate-500/20 to-slate-600/10',
    keywords: [
      'business',
      'entrepreneurship',
      'startup',
      'strategy',
      'sales',
      'management',
      'leadership',
      'finance',
      'investment',
      'revenue',
      'growth',
    ],
    pathPrefixes: ['domain/business', 'domain/finance', 'business', 'finance', 'sales', 'strategy'],
    order: 5,
  },
  {
    id: 'health',
    name: 'Health',
    description:
      'Physical wellness, exercise routines, nutrition science, sleep optimization, and overall health improvement. Take care of your body and mind.',
    icon: 'Heart',
    gradientClasses: 'from-red-500/20 to-red-600/10',
    keywords: [
      'health',
      'healthcare',
      'fitness',
      'exercise',
      'nutrition',
      'sleep',
      'wellness',
      'diet',
      'workout',
      'recovery',
      'energy',
      'longevity',
    ],
    pathPrefixes: ['domain/healthcare', 'health', 'healthcare', 'fitness', 'nutrition', 'sleep'],
    order: 6,
  },
  {
    id: 'mindset',
    name: 'Mindset',
    description:
      'Psychology, personal development, positive thinking, and mental frameworks. Develop a growth mindset and emotional intelligence.',
    icon: 'Lightbulb',
    gradientClasses: 'from-yellow-500/20 to-yellow-600/10',
    keywords: [
      'mindset',
      'psychology',
      'personal development',
      'growth mindset',
      'motivation',
      'resilience',
      'emotional intelligence',
      'self-improvement',
      'mental models',
      'habits',
    ],
    pathPrefixes: ['mindset', 'psychology', 'personal-development', 'self-improvement', 'mental'],
    order: 7,
  },
  {
    id: 'marketing',
    name: 'Marketing',
    description:
      'Content strategy, copywriting, sales funnels, digital marketing, and audience growth. Connect with your audience and drive conversions.',
    icon: 'Megaphone',
    gradientClasses: 'from-pink-500/20 to-pink-600/10',
    keywords: [
      'marketing',
      'copywriting',
      'sales funnel',
      'advertising',
      'branding',
      'seo',
      'social media',
      'content marketing',
      'conversion',
      'audience',
    ],
    pathPrefixes: ['marketing', 'copywriting', 'advertising', 'branding', 'seo'],
    order: 8,
  },
  {
    id: 'video-content',
    name: 'Video & Content Creation',
    description:
      'Video production, content creation, editing techniques, and multimedia storytelling. Create compelling content that engages and inspires.',
    icon: 'Video',
    gradientClasses: 'from-orange-500/20 to-orange-600/10',
    keywords: [
      'video',
      'content creation',
      'editing',
      'youtube',
      'production',
      'streaming',
      'podcast',
      'animation',
      'storytelling',
      'multimedia',
    ],
    pathPrefixes: ['video', 'content', 'media', 'production', 'youtube', 'streaming'],
    order: 9,
  },
];

export function getDomainById(id: KLDomainId): KLDomain | undefined {
  return KNOWLEDGE_DOMAINS.find((d) => d.id === id);
}

export function getAllDomainIds(): KLDomainId[] {
  return KNOWLEDGE_DOMAINS.map((d) => d.id);
}

export function getDomainsSorted(): KLDomain[] {
  return [...KNOWLEDGE_DOMAINS].sort((a, b) => a.order - b.order);
}
```

---

## Step 4: Create Domain Mapping Utilities (correctness-critical)

**Purpose:** Provide deterministic mapping + stats used by Sub-Plans 2–3. Must not misclassify nested taxonomy paths (e.g., `technical/ai_ml`).

**File:** `apps/ui/src/lib/domain-utils.ts` (NEW FILE)

**Mapping rules (must implement exactly):**
1. Normalize paths by lowercasing and converting `_`/spaces to `-`
2. **Longest prefix wins** (tie-break by smallest `order`)
3. Keyword substring match fallback
4. Default domain fallback: `coding-development`

**Command (GREEN gate):**  
`npx vitest run --root apps/ui -c vitest.config.ts src/lib/domain-utils.test.ts`

**Expected result:** All tests pass (exit code 0).

```ts
import type { KLDomainId, KLDomainWithStats, KLLibraryFileResponse, KLPageCard } from '@automaker/types';
import { KNOWLEDGE_DOMAINS } from '@/config/domains';

const DEFAULT_DOMAIN_ID: KLDomainId = 'coding-development';

const normalize = (value: string): string => value.trim().toLowerCase().replace(/[_\s]+/g, '-');

type PrefixMatcher = { domainId: KLDomainId; order: number; prefix: string };

const PREFIX_MATCHERS: PrefixMatcher[] = KNOWLEDGE_DOMAINS.flatMap((d) =>
  d.pathPrefixes
    .map((p) => normalize(p))
    .filter(Boolean)
    .map((prefix) => ({ domainId: d.id, order: d.order, prefix }))
).sort((a, b) => b.prefix.length - a.prefix.length || a.order - b.order);

const matchesPrefix = (path: string, prefix: string): boolean => {
  if (path === prefix) return true;
  if (!path.startsWith(prefix)) return false;
  const next = path[prefix.length];
  return next === '/' || next === '-' || next === undefined;
};

export function mapCategoryToDomain(categoryPath: string): KLDomainId {
  const path = normalize(categoryPath);

  if (path) {
    for (const m of PREFIX_MATCHERS) {
      if (matchesPrefix(path, m.prefix)) return m.domainId;
    }

    for (const d of KNOWLEDGE_DOMAINS) {
      for (const keyword of d.keywords) {
        const k = normalize(keyword);
        if (k && path.includes(k)) return d.id;
      }
    }
  }

  return DEFAULT_DOMAIN_ID;
}

export function mapFileToDomain(file: KLLibraryFileResponse): KLDomainId {
  return mapCategoryToDomain(file.category);
}

export function fileToPageCard(file: KLLibraryFileResponse): KLPageCard {
  return {
    path: file.path,
    title: file.title,
    overview: file.overview,
    category: file.category,
    domainId: mapFileToDomain(file),
    blockCount: file.block_count,
    lastModified: file.last_modified,
    imageUrl: undefined, // populated in Sub-Plan 4
  };
}

export function calculateDomainStats(
  files: KLLibraryFileResponse[]
): Map<KLDomainId, { fileCount: number; totalBlocks: number; categories: Set<string> }> {
  const stats = new Map<KLDomainId, { fileCount: number; totalBlocks: number; categories: Set<string> }>();

  for (const d of KNOWLEDGE_DOMAINS) {
    stats.set(d.id, { fileCount: 0, totalBlocks: 0, categories: new Set() });
  }

  for (const file of files) {
    const id = mapFileToDomain(file);
    const s = stats.get(id);
    if (!s) continue;
    s.fileCount += 1;
    s.totalBlocks += file.block_count;
    s.categories.add(file.category);
  }

  return stats;
}

export function getDomainsWithStats(files: KLLibraryFileResponse[]): KLDomainWithStats[] {
  const stats = calculateDomainStats(files);

  return KNOWLEDGE_DOMAINS.map((d) => {
    const s = stats.get(d.id) ?? { fileCount: 0, totalBlocks: 0, categories: new Set<string>() };
    return { ...d, fileCount: s.fileCount, categoryCount: s.categories.size, totalBlocks: s.totalBlocks };
  }).sort((a, b) => a.order - b.order);
}

export function getFilesForDomain(files: KLLibraryFileResponse[], domainId: KLDomainId): KLLibraryFileResponse[] {
  return files.filter((f) => mapFileToDomain(f) === domainId);
}

export function getPageCardsForDomain(files: KLLibraryFileResponse[], domainId: KLDomainId): KLPageCard[] {
  return getFilesForDomain(files, domainId).map(fileToPageCard);
}

export function filterDomainFiles(
  files: KLLibraryFileResponse[],
  domainId: KLDomainId,
  searchQuery: string
): KLLibraryFileResponse[] {
  const domainFiles = getFilesForDomain(files, domainId);
  const query = searchQuery.trim().toLowerCase();
  if (!query) return domainFiles;

  return domainFiles.filter(
    (f) =>
      f.title.toLowerCase().includes(query) ||
      f.path.toLowerCase().includes(query) ||
      f.category.toLowerCase().includes(query) ||
      f.overview?.toLowerCase().includes(query)
  );
}
```

---

## Verification + Acceptance Criteria

Run these exact commands (in this order):

1. **Types build:** `npm run build -w @automaker/types`  
   - Pass condition: exit code 0
2. **Unit tests (domain mapping):** `npx vitest run --root apps/ui -c vitest.config.ts src/lib/domain-utils.test.ts`  
   - Pass condition: exit code 0

Acceptance checklist:

- [ ] `KNOWLEDGE_DOMAINS` has exactly 9 entries with unique `id` + `order`
- [ ] `mapCategoryToDomain('technical/ai_ml') === 'ai-llms'` (no misclassification)
- [ ] `getDomainsWithStats()` returns sorted by `order`
- [ ] Downstream imports exist:
  - `@/config/domains`: `KNOWLEDGE_DOMAINS`, `getDomainById`
  - `@/lib/domain-utils`: `getDomainsWithStats`, `getPageCardsForDomain`
  - `@automaker/types`: `KLDomainId`, `KLDomain`, `KLDomainWithStats`, `KLPageCard`

---

## Rollback plan

To revert safely:

1. Remove the “Domain Types” section added to `libs/types/src/knowledge-library.ts`
2. Remove the four added exports from `libs/types/src/index.ts`
3. Delete new UI files:
   - `apps/ui/src/config/domains.ts`
   - `apps/ui/src/lib/domain-utils.ts`
   - `apps/ui/src/lib/domain-utils.test.ts`
4. Re-run: `npm run build -w @automaker/types`

---

## Handoff Manifest (for Sub-Plans 2–3)

**New/changed files:**
- `libs/types/src/knowledge-library.ts` — adds domain types
- `libs/types/src/index.ts` — exports domain types from `./knowledge-library.js`
- `apps/ui/src/config/domains.ts` — runtime domain config + lookup helpers
- `apps/ui/src/lib/domain-utils.ts` — mapping + stats utilities
- `apps/ui/src/lib/domain-utils.test.ts` — unit test contract

**Public interfaces (downstream assumes these exist):**
- Types: `KLDomainId`, `KLDomain`, `KLDomainWithStats`, `KLPageCard`
- Runtime: `getDomainById`, `getDomainsWithStats`, `getPageCardsForDomain`

**Verification commands (copy/paste):**
- `npm run build -w @automaker/types`
- `npx vitest run --root apps/ui -c vitest.config.ts src/lib/domain-utils.test.ts`

---

## Next Steps

After completing this sub-plan:
- **Sub-Plan 2:** Domain Gallery UI Component
- **Sub-Plan 3:** Domain Detail View and Page Gallery
