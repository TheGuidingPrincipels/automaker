# Investigation Report: Nine Core Domains for Knowledge Library

## Executive Summary

This investigation explores implementing a nine-domain organizational structure for the Knowledge Library feature in Automaker. The goal is to provide users with a visually appealing, domain-centric browsing experience where documents are categorized into predefined knowledge areas with associated imagery.

## Current Architecture Analysis

### 1. Knowledge Library Frontend Structure

**Location:** `apps/ui/src/components/views/knowledge-library/`

The current Knowledge Library has three tabs:
- **Input Mode** - Document upload and AI processing
- **Library Browser** - Three-column layout (categories | files | content)
- **Query Mode** - RAG-based Q&A interface

**Current Library Browser Layout:**
```
┌────────────────────────────────────────────────────┐
│ Search Bar (keyword/semantic toggle)               │
├──────────────┬──────────────┬─────────────────────┤
│ Categories   │ Files        │ Content Viewer      │
│ (Tree View)  │ (List View)  │ (Markdown)          │
│ w-64 (256px) │ w-80 (320px) │ flex-1 (remaining)  │
└──────────────┴──────────────┴─────────────────────┘
```

**Key Files:**
- `apps/ui/src/components/views/knowledge-library/index.tsx` - Main container with tabs
- `apps/ui/src/components/views/knowledge-library/components/library-browser/index.tsx` - Current browser
- `apps/ui/src/routes/knowledge-hub.$section.tsx` - Route handler
- `apps/ui/src/store/knowledge-library-store.ts` - Zustand state

### 2. Type System

**Location:** `libs/types/src/knowledge-library.ts`

Current category structure:
```typescript
interface KLLibraryCategoryResponse {
  name: string;               // Display name
  path: string;               // Hierarchical path (e.g., "technical/programming")
  description: string;        // Category description
  files: KLLibraryFileResponse[];
  subcategories: KLLibraryCategoryResponse[];  // Recursive
}

interface KLLibraryFileResponse {
  path: string;
  category: string;           // Single category path
  title: string;
  sections: string[];
  last_modified: string;
  block_count: number;
  overview: string | null;    // 50-250 char summary
  is_valid: boolean;
  validation_errors: string[];
}
```

**No existing domain concept** - categories are dynamically created via AI routing.

### 3. Python AI-Library Backend

**Location:** `2.ai-library/`

The AI-Library handles:
- Document parsing and block extraction
- Cleanup plan generation (keep/discard decisions)
- Routing plan generation (where to save content)
- Taxonomy management with AI-proposed categories

**Taxonomy Schema** (`2.ai-library/src/taxonomy/schema.py`):
```python
class TaxonomyNode(BaseModel):
    name: str              # Category name (slug format)
    description: str       # Human-readable description
    locked: bool           # If true, only humans can modify
    level: int             # Depth level (1-10)
    parent_path: str | None
    children: dict[str, TaxonomyNode]
    status: CategoryStatus  # ACTIVE | PROPOSED | DEPRECATED
    content_count: int
    centroid_vector: list[float] | None  # For semantic matching
```

### 4. Image Handling

**Current State:** No image generation capability exists. The codebase has:
- `apps/ui/src/lib/image-utils.ts` - File upload/validation utilities
- `apps/ui/src/components/ui/feature-image-upload.tsx` - Drag-drop image upload
- No AI image generation integration
- No domain/page image storage

### 5. Reference UI Patterns

**Systems Page Grid** (`apps/ui/src/components/views/systems-page/index.tsx`):
```tsx
<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
  {systems.map((system) => (
    <SystemCard key={system.id} system={system} onClick={...} />
  ))}
</div>
```

**System Card Pattern**:
```tsx
<Card className="group cursor-pointer hover:border-primary/50 transition-all">
  {/* Icon/Image Area */}
  <div className="h-32 bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center border-b">
    <Icon className="h-12 w-12 text-primary/60" />
  </div>
  <CardHeader>...</CardHeader>
  <CardContent>...</CardContent>
</Card>
```

---

## Proposed Nine Core Domains

Based on user requirements:

| ID | Domain Name | Slug | Keywords/Topics |
|----|-------------|------|-----------------|
| 1 | Coding & Development | `coding-development` | Software, programming, APIs, frameworks, debugging |
| 2 | AI & LLMs | `ai-llms` | Machine learning, prompts, agents, neural networks |
| 3 | Productivity | `productivity` | Time management, workflows, efficiency, effectiveness |
| 4 | Learning | `learning` | Learning strategies, retention, mind maps, spacing |
| 5 | Business | `business` | Entrepreneurship, strategy, sales, tactics |
| 6 | Health | `health` | Exercise, nutrition, sleep, wellness |
| 7 | Mindset | `mindset` | Psychology, personal improvement, positive thinking |
| 8 | Marketing | `marketing` | Copywriting, sales funnels, content strategy |
| 9 | Video & Content Creation | `video-content` | Video production, content creation, editing |

---

## Architecture Design

### New Component Hierarchy

```
KnowledgeLibrary (existing)
├── InputMode (existing)
├── LibraryMode (NEW - replaces LibraryBrowser)
│   ├── DomainGallery (NEW)
│   │   └── DomainCard (NEW) x 9
│   └── DomainDetailView (NEW)
│       ├── DomainHeader (NEW)
│       └── PageGallery (NEW)
│           └── PageCard (NEW) x N
└── QueryMode (existing)
```

### State Management

Extend `knowledge-library-store.ts`:
```typescript
interface KnowledgeLibraryState {
  // Existing...
  activeView: 'input' | 'library' | 'query';

  // New domain navigation
  selectedDomainId: string | null;  // null = show gallery
  domainImages: Record<string, string>;  // domainId -> image URL
}
```

### Data Flow

1. **Library tab selected** → Show DomainGallery (3x3 grid)
2. **Domain card clicked** → Set `selectedDomainId`, show DomainDetailView
3. **Back button** → Clear `selectedDomainId`, return to gallery
4. **Page card clicked** → Navigate to file content (existing flow)

---

## Implementation Approach Options

### Option A: Frontend-Only Domain Mapping (Recommended for Phase 1)

**Approach:** Define domains as a static configuration in the frontend. Map existing library categories to domains using path prefixes.

**Pros:**
- Quick implementation
- No backend changes required
- Reversible/adjustable easily

**Cons:**
- Limited AI integration for new categories
- Manual mapping maintenance

**Implementation:**
```typescript
// domains-config.ts
export const CORE_DOMAINS: Domain[] = [
  {
    id: 'coding-development',
    name: 'Coding & Development',
    description: 'Software, programming, APIs, and development tools',
    icon: 'Code',
    color: 'from-blue-500/20 to-blue-600/10',
    pathPrefixes: ['coding', 'development', 'programming', 'software', 'api'],
  },
  // ... 8 more domains
];
```

### Option B: Backend Domain Integration

**Approach:** Add domains as first-class entities in the AI-Library taxonomy system.

**Pros:**
- AI can suggest domain classification
- Centralized configuration
- Better for multi-user scenarios

**Cons:**
- Requires Python backend changes
- More complex migration

### Option C: Hybrid Approach (Recommended for Phase 2)

**Approach:** Static domain definitions with AI-assisted category-to-domain mapping.

---

## Image Generation Strategy

### Option 1: Pre-defined Static Images

Use high-quality stock images or pre-generated AI images stored as static assets.

**Implementation:**
```
apps/ui/src/assets/domains/
├── coding-development.jpg
├── ai-llms.jpg
├── productivity.jpg
└── ...
```

### Option 2: AI Image Generation (Future)

Integrate with image generation API (DALL-E, Midjourney, Stable Diffusion).

**Considerations:**
- API costs
- Generation latency
- Caching strategy
- Content moderation

### Option 3: Unsplash/Stock API Integration

Use Unsplash API or similar for dynamic, relevant images.

```typescript
// Example Unsplash integration
const getdomainImage = async (domain: string) => {
  const response = await fetch(
    `https://api.unsplash.com/search/photos?query=${domain}&per_page=1`
  );
  return response.json();
};
```

---

## Key Files to Modify

### Frontend

| File | Changes |
|------|---------|
| `libs/types/src/knowledge-library.ts` | Add `Domain` type, `DomainId` enum |
| `apps/ui/src/store/knowledge-library-store.ts` | Add domain navigation state |
| `apps/ui/src/components/views/knowledge-library/index.tsx` | Update library tab content |
| NEW: `apps/ui/src/components/views/knowledge-library/components/domain-gallery/` | Domain gallery components |
| NEW: `apps/ui/src/components/views/knowledge-library/components/domain-detail/` | Domain detail view |
| NEW: `apps/ui/src/config/domains.ts` | Domain configuration |

### Backend (Phase 2)

| File | Changes |
|------|---------|
| `2.ai-library/src/taxonomy/schema.py` | Add domain-level classification |
| `2.ai-library/src/sdk/prompts/routing_mode.py` | Domain-aware routing prompts |
| `2.ai-library/src/api/routes/library.py` | Domain filtering endpoints |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Category-domain mapping conflicts | Medium | Provide "Uncategorized" fallback domain |
| Image loading performance | Low | Use optimized WebP, lazy loading |
| User confusion about domain vs category | Medium | Clear UI labels, tooltips |
| Breaking existing library navigation | High | Keep existing browser as fallback mode |

---

## Testing Strategy

1. **Unit Tests:**
   - Domain configuration validation
   - Category-to-domain mapping logic
   - State management transitions

2. **E2E Tests:**
   - Domain gallery renders 9 cards in 3x3 grid
   - Domain navigation works correctly
   - Page gallery shows filtered content
   - Back navigation returns to gallery

3. **Visual Tests:**
   - Image loading and fallbacks
   - Responsive grid layouts
   - Dark/light mode compatibility

---

## Estimated Effort

| Phase | Scope | Complexity |
|-------|-------|------------|
| **Phase 1** | Static domain config + Gallery UI | Medium |
| **Phase 2** | Domain detail view + Page gallery | Medium |
| **Phase 3** | Image integration (static/stock) | Low |
| **Phase 4** | Backend domain integration | High |
| **Phase 5** | AI image generation | Medium-High |

---

## Conclusion

The nine-domain structure is achievable with a phased approach. Phase 1 focuses on frontend-only changes with static configuration, providing immediate value while laying groundwork for backend integration in later phases.

The recommended approach is:
1. **Start with Option A** (frontend-only) for quick delivery
2. **Implement static images** for visual appeal
3. **Evolve to Option C** (hybrid) as the system matures

This allows for iterative improvement while delivering immediate user value.
