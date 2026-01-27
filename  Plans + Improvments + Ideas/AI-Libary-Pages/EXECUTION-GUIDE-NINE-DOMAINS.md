# Execution Guide: Nine Core Domains Feature

## Overview

This guide coordinates the implementation of the Nine Core Domains feature for the Knowledge Library. The feature introduces a domain-centric browsing experience where documents are organized into nine predefined knowledge areas with visual representations.

## Nine Core Domains

| # | Domain | Slug | Primary Topics |
|---|--------|------|----------------|
| 1 | Coding & Development | `coding-development` | Programming, APIs, frameworks |
| 2 | AI & LLMs | `ai-llms` | Machine learning, prompts, agents |
| 3 | Productivity | `productivity` | Time management, workflows |
| 4 | Learning | `learning` | Memory, retention, mind maps |
| 5 | Business | `business` | Strategy, sales, entrepreneurship |
| 6 | Health | `health` | Exercise, nutrition, sleep |
| 7 | Mindset | `mindset` | Psychology, personal growth |
| 8 | Marketing | `marketing` | Copywriting, funnels, content |
| 9 | Video & Content | `video-content` | Video production, editing |

## Sub-Plan Overview

### Sub-Plan 1: Domain Types and Configuration
**Complexity:** Low
**Dependencies:** None
**Files Created/Modified:**
- `libs/types/src/knowledge-library.ts` (modify)
- `apps/ui/src/config/domains.ts` (create)
- `apps/ui/src/lib/domain-utils.ts` (create)

**Deliverables:**
- TypeScript types for domains
- Static domain configuration
- Category-to-domain mapping utilities

### Sub-Plan 2: Domain Gallery UI
**Complexity:** Medium
**Dependencies:** Sub-Plan 1
**Files Created/Modified:**
- `apps/ui/src/store/knowledge-library-store.ts` (modify)
- `apps/ui/src/components/views/knowledge-library/index.tsx` (modify)
- `apps/ui/src/components/views/knowledge-library/components/domain-gallery/` (create)
- `apps/ui/src/components/views/knowledge-library/components/library-mode/` (create)
- `apps/ui/src/components/views/knowledge-library/components/domain-detail/` (create - placeholder)

**Deliverables:**
- Domain Gallery with 3x3 card grid
- Domain Card component
- Navigation state management
- Placeholder Domain Detail View

### Sub-Plan 3: Domain Detail View and Page Gallery
**Complexity:** Medium
**Dependencies:** Sub-Plans 1 & 2
**Files Created/Modified:**
- `apps/ui/src/components/views/knowledge-library/components/domain-detail/index.tsx` (replace)
- `apps/ui/src/components/views/knowledge-library/components/domain-detail/page-card.tsx` (create)
- `apps/ui/src/components/views/knowledge-library/components/domain-detail/page-gallery.tsx` (create)

**Deliverables:**
- Full Domain Detail View
- Page Card component
- Page Gallery with search/filter
- Content Viewer integration

### Sub-Plan 4: Automatic Image Generation
**Complexity:** Medium-High
**Dependencies:** Sub-Plans 1-3 (can run in parallel after Sub-Plan 2)
**Files Created/Modified:**
- `libs/types/src/settings.ts` (modify - add gemini to credentials)
- `apps/server/src/services/settings-service.ts` (modify)
- `apps/server/src/services/image-generation-service.ts` (create)
- `apps/server/src/lib/team-storage.ts` (modify - add collections)
- `apps/server/src/routes/generated-media/index.ts` (create)
- `apps/server/src/index.ts` (modify - register routes)
- `apps/ui/src/hooks/queries/use-generated-images.ts` (create)
- Domain Card and Page Card components (modify)

**Deliverables:**
- Gemini API key in credentials storage
- Image generation service using Gemini API
- Team storage integration for generated images
- API endpoints for image generation and serving
- Auto-generation when title + overview exist
- Image display in Domain and Page cards
- Caching and reuse of generated images

---

## Execution Order

```
┌─────────────────────────────────────┐
│       Sub-Plan 1: Types & Config    │
│    (Can be executed independently)   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Sub-Plan 2: Domain Gallery     │
│     (Requires Sub-Plan 1 types)     │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────────────┐
│  Sub-Plan 3  │ │     Sub-Plan 4       │
│ Detail View  │ │  Image Generation    │
│  & Pages     │ │  (Backend + API)     │
└──────────────┘ └──────────────────────┘
```

## Parallel Execution Options

**Option A: Sequential (Recommended for single session)**
1. Execute Sub-Plan 1 completely
2. Execute Sub-Plan 2 completely
3. Execute Sub-Plan 3 completely
4. Execute Sub-Plan 4 completely

**Option B: Two parallel tracks (Recommended for multiple sessions)**
- Track 1: Sub-Plans 1 → 2 → 3 (UI Foundation + Gallery + Detail)
- Track 2: Sub-Plan 4 (Backend image generation - can start after Sub-Plan 2)

**Option C: Maximum parallelism (3 sessions)**
- Session 1: Sub-Plan 1 (Types & Config)
- Session 2: Sub-Plan 2 + 3 (UI Components) - waits for Session 1
- Session 3: Sub-Plan 4 (Image Generation) - waits for Session 1

---

## File Structure After Implementation

```
apps/ui/src/
├── config/
│   └── domains.ts                        # Domain configuration
├── lib/
│   └── domain-utils.ts                   # Mapping utilities
├── hooks/queries/
│   └── use-generated-images.ts           # Image generation hooks (Sub-Plan 4)
├── store/
│   └── knowledge-library-store.ts        # Updated with domain state
└── components/views/knowledge-library/
    ├── index.tsx                         # Updated to use LibraryMode
    └── components/
        ├── domain-gallery/
        │   ├── index.tsx                 # Domain Gallery
        │   └── domain-card.tsx           # Domain Card (with image support)
        ├── domain-detail/
        │   ├── index.tsx                 # Domain Detail View
        │   ├── page-card.tsx             # Page Card (with image support)
        │   └── page-gallery.tsx          # Page Gallery
        ├── library-mode/
        │   └── index.tsx                 # Mode switcher
        └── library-browser/              # Existing (kept as reference)
            ├── index.tsx
            ├── file-viewer.tsx           # Reused in domain-detail
            └── ...

apps/server/src/
├── services/
│   ├── settings-service.ts               # Updated with Gemini key support
│   └── image-generation-service.ts       # NEW: Image generation (Sub-Plan 4)
├── routes/
│   └── generated-media/
│       └── index.ts                      # NEW: Image API routes (Sub-Plan 4)
└── lib/
    └── team-storage.ts                   # Updated with image collections

libs/types/src/
├── knowledge-library.ts                  # Updated with domain types
└── settings.ts                           # Updated with gemini credentials

TEAM_DATA_DIR/ (transferable storage)
├── domain-images/                        # Generated domain images
│   └── {domainId}/
│       ├── metadata.json
│       └── thumbnail-{timestamp}.png
└── page-images/                          # Generated page images
    └── {pageId}/
        ├── metadata.json
        └── thumbnail-{timestamp}.png
```

---

## Testing Checklist

### Sub-Plan 1 Verification
- [ ] Types compile without errors (`npm run build:packages`)
- [ ] Domain configuration exports correctly
- [ ] Mapping utilities work for various paths

### Sub-Plan 2 Verification
- [ ] Domain Gallery displays 9 cards in 3x3 grid
- [ ] Cards show correct icons, names, descriptions
- [ ] Hover effects work
- [ ] Click navigates to placeholder detail view
- [ ] Back button returns to gallery
- [ ] Responsive grid adapts to screen size

### Sub-Plan 3 Verification
- [ ] Domain Detail shows correct header with domain info
- [ ] Page Gallery displays domain pages
- [ ] Search filters pages correctly
- [ ] Category filter works
- [ ] Sort options work
- [ ] Clicking page shows content viewer
- [ ] Content viewer toggle works
- [ ] Back navigation returns to gallery
- [ ] Empty states display correctly

### Sub-Plan 4 Verification
- [ ] Gemini API key can be stored in credentials.json
- [ ] `getGeminiApiKey()` returns key from storage or env
- [ ] Image generation service initializes with valid API key
- [ ] Images generated from title + overview prompts
- [ ] Images stored in team storage (`domain-images/`, `page-images/`)
- [ ] Metadata JSON saved alongside images
- [ ] Images served via `/api/generated-media/:entityType/:entityId/:filename`
- [ ] Domain cards display generated images
- [ ] Page cards display generated images
- [ ] Caching works (same input = no regeneration)
- [ ] Error handling when API key missing
- [ ] Loading states during generation

### Integration Verification
- [ ] Full flow: Domains → Pages → Content → Back
- [ ] State persists correctly (activeView only)
- [ ] No console errors
- [ ] Dark/light mode compatible
- [ ] Images persist across application restarts
- [ ] Images transferable (copy TEAM_DATA_DIR to new deployment)

---

## Agent Instructions

### For Sub-Plan 1 Agent

```
TASK: Implement Sub-Plan 1 - Domain Types and Configuration

READ: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1/SUBPLAN-1-DOMAIN-TYPES-AND-CONFIG.md

CONTEXT:
- Working directory: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
- Port configuration: UI=3017, Server=3018
- Package building: npm run build:packages

DELIVERABLES:
1. Add domain types to libs/types/src/knowledge-library.ts
2. Create apps/ui/src/config/domains.ts
3. Create apps/ui/src/lib/domain-utils.ts
4. Verify with npm run build:packages

DO NOT:
- Modify UI components (that's Sub-Plan 2)
- Create placeholder files for other sub-plans
```

### For Sub-Plan 2 Agent

```
TASK: Implement Sub-Plan 2 - Domain Gallery UI

PREREQUISITE: Sub-Plan 1 must be completed first

READ: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1/SUBPLAN-2-DOMAIN-GALLERY-UI.md

CONTEXT:
- Working directory: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
- Reference existing UI: apps/ui/src/components/views/systems-page/index.tsx

DELIVERABLES:
1. Update knowledge-library-store.ts with domain navigation state
2. Create domain-gallery/ components
3. Create library-mode/ switcher
4. Create placeholder domain-detail/ view
5. Update knowledge-library/index.tsx
6. Verify visually at http://localhost:3017

DO NOT:
- Implement full domain detail view (that's Sub-Plan 3)
- Modify type definitions (already done in Sub-Plan 1)
```

### For Sub-Plan 3 Agent

```
TASK: Implement Sub-Plan 3 - Domain Detail View and Page Gallery

PREREQUISITE: Sub-Plans 1 & 2 must be completed first

READ: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1/SUBPLAN-3-DOMAIN-DETAIL-AND-PAGES.md

CONTEXT:
- Working directory: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
- Reuse FileViewer from: components/library-browser/file-viewer.tsx

DELIVERABLES:
1. Replace placeholder domain-detail/index.tsx
2. Create page-card.tsx
3. Create page-gallery.tsx
4. Verify full navigation flow at http://localhost:3017

DO NOT:
- Modify domain configuration
- Change the domain gallery
```

### For Sub-Plan 4 Agent

```
TASK: Implement Sub-Plan 4 - Automatic Image Generation with Imagen 3.0

PREREQUISITE:
- Sub-Plan 2 should be completed (for card components to update)
- GCP project with Vertex AI enabled (see setup instructions in sub-plan)

READ: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1/SUBPLAN-4-IMAGE-GENERATION.md

CONTEXT:
- Working directory: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
- Credentials storage: data/credentials.json
- Team storage: DATA_DIR/team/
- Image generation: Google Imagen 3.0 via Vertex AI (NOT Gemini API)
- Required package: @google-cloud/vertexai (NOT @google/generative-ai)
- Auth: GOOGLE_CLOUD_PROJECT + GOOGLE_APPLICATION_CREDENTIALS env vars

DELIVERABLES:
1. Install @google-cloud/vertexai package
2. Update libs/types/src/settings.ts with googleCloud credentials section
3. Update apps/server/src/services/settings-service.ts with GCP credential methods
4. Create apps/server/src/services/image-generation-service.ts using Vertex AI
5. Update apps/server/src/lib/team-storage.ts with domain-images/page-images collections
6. Create apps/server/src/routes/generated-media/index.ts
7. Register routes in apps/server/src/index.ts
8. Create apps/ui/src/hooks/queries/use-generated-images.ts
9. Update domain-card.tsx and page-card.tsx with image support
10. Verify with: curl http://localhost:3018/api/generated-media/status

IMPORTANT NOTES:
- Gemini API (@google/generative-ai) does NOT support image generation
- Must use Vertex AI with Imagen 3.0 model: 'imagen-3.0-generate-001'
- Requires GCP service account, not simple API key
- Test GCP auth before implementing: gcloud auth application-default print-access-token

DO NOT:
- Use @google/generative-ai for image generation (it won't work)
- Change domain configuration or types
- Modify the gallery layout
```

---

## Rollback Plan

If issues occur, the feature can be rolled back by:

1. Revert the Knowledge Library main component to use `LibraryBrowser` directly:
   ```tsx
   <TabsContent value="library" className="h-full m-0">
     <LibraryBrowser />
   </TabsContent>
   ```

2. Remove domain-related state from the store (if needed)

3. The existing `LibraryBrowser` component remains unchanged and functional

---

## Future Phases (Out of Scope)

### Phase 5: Backend Domain Integration
- Domain classification in AI-Library Python backend
- Taxonomy updates for predefined domains
- API endpoints for domain statistics
- AI-assisted category-to-domain mapping

### Phase 6: Advanced Image Features
- Multiple image sizes (thumbnail, banner, full)
- Image style selection (abstract, realistic, minimalist)
- Manual image override/upload
- Batch regeneration UI

### Phase 7: Domain Analytics
- Page count tracking per domain
- Popular domains dashboard
- Content gap analysis
- Domain health indicators

---

## Support Files

- `INVESTIGATION-NINE-DOMAINS.md` - Full investigation report
- `SUBPLAN-1-DOMAIN-TYPES-AND-CONFIG.md` - Types implementation
- `SUBPLAN-2-DOMAIN-GALLERY-UI.md` - Gallery UI implementation
- `SUBPLAN-3-DOMAIN-DETAIL-AND-PAGES.md` - Detail view implementation
- `SUBPLAN-4-IMAGE-GENERATION.md` - Automatic image generation

All files located in: `/Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1/`

---

## Credential Storage Reference

### Current Credential Locations

| Credential | Storage Location | Env Variable |
|------------|------------------|--------------|
| Mistral API Key | Environment only | `MISTRAL_API_KEY` |
| Claude OAuth Token | `credentials.json` + env | `ANTHROPIC_AUTH_TOKEN` |
| Gemini API Key | `credentials.json` + env | `GEMINI_API_KEY` |
| **Google Cloud Project** | `credentials.json` + env | `GOOGLE_CLOUD_PROJECT` |
| **GCP Service Account** | File path or `credentials.json` | `GOOGLE_APPLICATION_CREDENTIALS` |

### Credentials File Structure

```json
// data/credentials.json
{
  "version": 1,
  "apiKeys": {
    "anthropic": "",
    "anthropic_oauth_token": "",
    "google": "",
    "openai": "",
    "gemini": ""
  },
  "googleCloud": {
    "projectId": "your-gcp-project-id",
    "serviceAccountKey": "base64-encoded-service-account-json"
  }
}
```

### Google Cloud Setup for Imagen 3.0

**Important:** Google's image generation model (Imagen 3.0) requires Vertex AI, which needs:
1. A Google Cloud Platform (GCP) account with billing enabled
2. Vertex AI API enabled in your project
3. A service account with `roles/aiplatform.user` permission

```bash
# Quick setup commands
gcloud auth login
gcloud projects create automaker-images
gcloud config set project automaker-images
gcloud services enable aiplatform.googleapis.com
gcloud iam service-accounts create automaker-imagen
gcloud projects add-iam-policy-binding automaker-images \
  --member="serviceAccount:automaker-imagen@automaker-images.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
gcloud iam service-accounts keys create ~/automaker-imagen-key.json \
  --iam-account=automaker-imagen@automaker-images.iam.gserviceaccount.com
```

### Image Storage Location

Generated images are stored in team storage for easy transfer:

```
TEAM_DATA_DIR/
├── domain-images/{domainId}/
│   ├── metadata.json
│   └── thumbnail-{timestamp}.png
└── page-images/{pageId}/
    ├── metadata.json
    └── thumbnail-{timestamp}.png
```

To transfer images to a new deployment, copy the entire `TEAM_DATA_DIR` directory.
