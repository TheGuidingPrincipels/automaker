# Session 5 (REVISED): Speed Reading Integration into Automaker

## Overview

**Goal**: Integrate the Speed Reading (DeepRead) system into the existing Automaker frontend as a sibling page to Knowledge Hub in the Systems section.

**Key Differences from Original Plan**:

- ❌ NOT a standalone application
- ✅ Integrated into existing Automaker UI
- ✅ Uses Automaker's existing router, components, and patterns
- ✅ Python backend kept separate (proxied through Automaker server)
- ✅ SQLite storage (no PostgreSQL required)
- ✅ Web-only v1 (no packaged Electron support)

---

## 🚨 CRITICAL: Code Organization Rule

> **READ THE MAIN README FIRST**: `4.Speed Reading System/README.md`

### Backend Code Location

**ALL backend code, database models, schemas, and services MUST be stored in `4.Speed Reading System/backend/`.**

This ensures the Speed Reading System can be exported as a standalone feature.

| ✅ Store in `4.Speed Reading System/` | ⚠️ Minimal changes in Automaker  |
| ------------------------------------- | -------------------------------- |
| Python FastAPI application            | Route files (just imports)       |
| SQLAlchemy models                     | UI components (frontend only)    |
| Pydantic schemas                      | React hooks (API calls)          |
| Database migrations                   | TypeScript types (mirror Python) |
| Tokenization/NLP services             | Proxy route (no logic)           |
| All business logic                    | Sidebar nav entry                |

**The Automaker Express server is ONLY a proxy - no Speed Reading business logic should exist there.**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Automaker Frontend                           │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  TanStack Router                                                ││
│  │  /speed-reading → SpeedReadingPage                              ││
│  │  /speed-reading/import → ImportPage                             ││
│  │  /speed-reading/preview/$docId → PreviewPage                    ││
│  │  /speed-reading/reader/$sessionId → ReaderPage (fullscreen)     ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Automaker Express Server (Port 3008)                           ││
│  │  /api/deepread/* → Proxy to Python backend                      ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Speed Reading Python Backend (Port 8001)                           │
│  FastAPI + SQLite + spaCy NLP                                       │
│  /api/documents, /api/sessions, /api/tokens                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Structure (What to Create)

### Frontend Files (`apps/ui/src/`)

```
routes/
├── speed-reading.tsx                    # Layout route with Outlet
├── speed-reading.index.tsx              # Home page (recent sessions + import)
├── speed-reading.import.tsx             # Import document page
├── speed-reading.preview.$documentId.tsx # Document preview
└── speed-reading.reader.$sessionId.tsx  # Fullscreen reader

components/views/speed-reading-page/
├── index.tsx                            # Main export (SpeedReadingPage)
├── components/
│   ├── speed-reading-header.tsx         # Page header
│   ├── recent-sessions.tsx              # Session list
│   └── session-card.tsx                 # Individual session card
├── dialogs/
│   └── delete-session-dialog.tsx        # Confirm delete

components/views/speed-reading-import/
├── index.tsx                            # Import page
├── components/
│   ├── import-form.tsx                  # Tabs: paste/upload
│   ├── text-input.tsx                   # Paste text area
│   ├── file-upload.tsx                  # Drag-drop upload
│   └── language-select.tsx              # EN/DE selector

components/views/speed-reading-preview/
├── index.tsx                            # Preview page
├── components/
│   ├── preview-header.tsx               # Title + back + controls
│   ├── preview-text.tsx                 # Virtualized text display
│   ├── preview-word.tsx                 # Clickable word component
│   ├── progress-scrubber.tsx            # Position slider
│   └── start-controls.tsx               # WPM settings + Start button

components/views/speed-reading-reader/
├── index.tsx                            # Fullscreen reader overlay
├── components/
│   ├── word-display.tsx                 # ORP-aligned word rendering
│   ├── orp-text.tsx                     # Text with ORP highlight
│   ├── reader-controls.tsx              # Auto-hiding controls overlay
│   ├── playback-controls.tsx            # Play/Pause/Rewind
│   ├── wpm-control.tsx                  # WPM slider
│   ├── ramp-control.tsx                 # Ramp toggle + duration
│   └── reader-progress.tsx              # Progress bar + scrubber

hooks/
├── speed-reading/
│   ├── use-documents.ts                 # Document query hooks
│   ├── use-sessions.ts                  # Session query hooks
│   ├── use-playback-engine.ts           # Timing loop + state
│   ├── use-token-cache.ts               # Token prefetching
│   ├── use-playback-history.ts          # History ring buffer
│   ├── use-auto-save.ts                 # Progress auto-save
│   ├── use-auto-hide.ts                 # Controls auto-hide
│   └── use-ramp.ts                      # WPM ramp calculation

lib/
├── speed-reading/
│   ├── api.ts                           # API client functions
│   ├── types.ts                         # TypeScript types
│   ├── timing.ts                        # Duration calculations
│   ├── ramp.ts                          # Ramp formula
│   └── query-keys.ts                    # React Query keys

store/
└── speed-reading-store.ts               # Zustand store for reader settings
```

### Backend Files (Automaker Server - `apps/server/src/`)

```
routes/
└── deepread/
    └── index.ts                         # Proxy to Python backend

lib/
└── deepread-proxy.ts                    # HTTP proxy configuration
```

### Python Backend (Separate Service - `4.Speed Reading System/backend/`)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app
│   ├── config.py                        # Settings
│   ├── database.py                      # SQLite connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py                  # SQLAlchemy models
│   │   └── session.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── document.py                  # Pydantic schemas
│   │   └── session.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tokenizer.py                 # NLP tokenization
│   │   ├── orp.py                       # ORP calculation
│   │   └── parser.py                    # Markdown parsing (PDF deferred)
│   └── routes/
│       ├── __init__.py
│       ├── documents.py                 # Document endpoints
│       ├── sessions.py                  # Session endpoints
│       └── health.py                    # Health check
├── alembic/                             # DB migrations
├── requirements.txt
├── pyproject.toml
└── run.py                               # Entry point
```

---

## Implementation Details

### 1. Add to Sidebar Navigation

**File**: `apps/ui/src/components/layout/sidebar/hooks/use-navigation.ts`

Add to the Systems section:

```typescript
{
  label: 'Systems',
  items: [
    {
      id: 'agents',
      label: 'Agents',
      icon: Cpu,
      shortcut: shortcuts.agents,
    },
    {
      id: 'systems',
      label: 'Systems',
      icon: Workflow,
      shortcut: shortcuts.systems,
    },
    {
      id: 'knowledge-hub',
      label: 'Knowledge Hub',
      icon: BookOpenCheck,
      shortcut: shortcuts.knowledgeHub,
    },
    // ADD THIS:
    {
      id: 'speed-reading',
      label: 'Speed Reading',
      icon: Zap, // or BookOpen, Eye, etc.
      shortcut: shortcuts.speedReading,
    },
  ],
}
```

### 2. Add Keyboard Shortcut

**File**: `libs/types/src/settings.ts`

Add to `KeyboardShortcuts` interface:

```typescript
interface KeyboardShortcuts {
  // ... existing shortcuts ...
  /** Open speed reading page */
  speedReading: string;
}
```

Add to `DEFAULT_KEYBOARD_SHORTCUTS`:

```typescript
export const DEFAULT_KEYBOARD_SHORTCUTS: KeyboardShortcuts = {
  // ... existing shortcuts ...
  speedReading: 'Shift+R',
};
```

Update `UseNavigationProps` shortcuts type accordingly.

### 3. Create Route Files

#### Layout Route (`speed-reading.tsx`)

```typescript
import { createFileRoute, Outlet } from '@tanstack/react-router';

function SpeedReadingLayout() {
  return <Outlet />;
}

export const Route = createFileRoute('/speed-reading')({
  component: SpeedReadingLayout,
});
```

#### Index Route (`speed-reading.index.tsx`)

```typescript
import { createFileRoute } from '@tanstack/react-router';
import { SpeedReadingPage } from '@/components/views/speed-reading-page';

export const Route = createFileRoute('/speed-reading/')({
  component: SpeedReadingPage,
});
```

#### Import Route (`speed-reading.import.tsx`)

```typescript
import { createFileRoute } from '@tanstack/react-router';
import { SpeedReadingImport } from '@/components/views/speed-reading-import';

export const Route = createFileRoute('/speed-reading/import')({
  component: SpeedReadingImport,
});
```

#### Preview Route (`speed-reading.preview.$documentId.tsx`)

```typescript
import { createFileRoute } from '@tanstack/react-router';
import { SpeedReadingPreview } from '@/components/views/speed-reading-preview';

export const Route = createFileRoute('/speed-reading/preview/$documentId')({
  component: SpeedReadingPreview,
});
```

#### Reader Route (`speed-reading.reader.$sessionId.tsx`)

```typescript
import { createFileRoute } from '@tanstack/react-router';
import { SpeedReadingReader } from '@/components/views/speed-reading-reader';

export const Route = createFileRoute('/speed-reading/reader/$sessionId')({
  component: SpeedReadingReader,
});
```

### 4. Create Main Page Component

**File**: `components/views/speed-reading-page/index.tsx`

```typescript
/**
 * Speed Reading Page - Home view with recent sessions and import CTA
 *
 * Similar pattern to KnowledgeHubPage:
 * - Header with icon, title, description
 * - Recent sessions list (last 7 days)
 * - Stats cards
 * - CTA to import new document
 */

import { useNavigate } from '@tanstack/react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Zap, Clock, BookOpen, Plus, Play, Trash2 } from 'lucide-react';
import { useRecentSessions, useDeleteSession } from '@/hooks/speed-reading/use-sessions';
import { SpeedReadingHeader } from './components/speed-reading-header';
import { RecentSessions } from './components/recent-sessions';

export function SpeedReadingPage() {
  const navigate = useNavigate();
  const { data: sessions, isLoading } = useRecentSessions(7);

  const handleImport = () => {
    navigate({ to: '/speed-reading/import' });
  };

  const handleContinue = (sessionId: string, documentId: string) => {
    navigate({
      to: '/speed-reading/reader/$sessionId',
      params: { sessionId }
    });
  };

  const totalSessions = sessions?.length ?? 0;
  const totalWordsRead = sessions?.reduce((sum, s) => {
    return sum + Math.floor((s.last_known_percent / 100) * s.total_words);
  }, 0) ?? 0;

  return (
    <div className="flex flex-col h-full">
      <SpeedReadingHeader sessionCount={totalSessions} />

      <div className="flex-1 overflow-auto p-6">
        {/* Introduction + CTA */}
        <div className="max-w-3xl mb-8">
          <h2 className="text-2xl font-semibold mb-2">Speed Reading with RSVP</h2>
          <p className="text-muted-foreground mb-4">
            Read faster using Rapid Serial Visual Presentation. Words appear one at a time
            at your chosen speed, with ORP (Optimal Recognition Point) alignment for
            maximum comprehension.
          </p>
          <Button onClick={handleImport} size="lg">
            <Plus className="h-5 w-5 mr-2" />
            Import New Document
          </Button>
        </div>

        {/* Recent Sessions */}
        <RecentSessions
          sessions={sessions ?? []}
          isLoading={isLoading}
          onContinue={handleContinue}
        />

        {/* Quick Stats */}
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                  <Clock className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{totalSessions}</p>
                  <p className="text-sm text-muted-foreground">Recent Sessions</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                  <BookOpen className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{totalWordsRead.toLocaleString()}</p>
                  <p className="text-sm text-muted-foreground">Words Read</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10">
                  <Zap className="h-5 w-5 text-purple-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">RSVP</p>
                  <p className="text-sm text-muted-foreground">Reading Mode</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
```

### 5. API Client and Types

**File**: `lib/speed-reading/types.ts`

```typescript
// Document types
export type SourceType = 'paste' | 'md'; // PDF deferred (see 4.Speed Reading System/docs/FUTURE-PDF-UPLOAD.md)
export type Language = 'en' | 'de';

export interface DocumentMeta {
  id: string;
  title: string;
  source_type: SourceType;
  language: Language;
  total_words: number;
  tokenizer_version: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentPreview {
  id: string;
  title: string;
  preview_text: string;
  total_words: number;
  anchors: Anchor[];
}

export interface Anchor {
  word_index: number;
  type: 'paragraph' | 'heading';
  preview: string;
}

// Token types
export type BreakType = 'paragraph' | 'heading' | null;

export interface Token {
  word_index: number;
  display_text: string;
  orp_index_display: number;
  delay_multiplier_after: number;
  break_before: BreakType;
  is_sentence_start: boolean;
  is_paragraph_start: boolean;
}

export interface TokenChunk {
  document_id: string;
  total_words: number;
  range_start: number;
  range_end: number;
  tokens: Token[];
}

// Session types
export interface Session {
  id: string;
  document_id: string;
  target_wpm: number;
  ramp_enabled: boolean;
  ramp_seconds: number;
  ramp_start_wpm: number | null;
  current_word_index: number;
  last_known_percent: number;
  created_at: string;
  updated_at: string;
  expires_at: string;
}

export interface SessionListItem {
  id: string;
  document_id: string;
  document_title: string;
  total_words: number;
  last_known_percent: number;
  updated_at: string;
  expires_at: string;
}

// Request types
export interface CreateDocumentFromTextRequest {
  title?: string;
  language: Language;
  source_type?: SourceType;
  original_filename?: string;
  text: string;
}

export interface CreateSessionRequest {
  document_id: string;
  start_word_index?: number;
  target_wpm?: number;
  ramp_enabled?: boolean;
  ramp_seconds?: number;
}

export interface UpdateProgressRequest {
  current_word_index: number;
  last_known_percent: number;
  target_wpm?: number;
  ramp_enabled?: boolean;
}

export interface ResolveStartRequest {
  approx_word_index: number;
  prefer?: 'sentence' | 'paragraph' | 'heading';
  direction?: 'backward' | 'forward' | 'nearest';
  window?: number;
}

export interface ResolveStartResult {
  resolved_word_index: number;
  reason: 'sentence_start' | 'paragraph_start' | 'heading_start' | 'exact';
}
```

**File**: `lib/speed-reading/api.ts`

```typescript
import { apiFetch, apiGet, apiPost, apiDelete } from '@/lib/api-fetch';
import type {
  DocumentMeta,
  DocumentPreview,
  TokenChunk,
  Session,
  SessionListItem,
  CreateDocumentFromTextRequest,
  CreateSessionRequest,
  UpdateProgressRequest,
  ResolveStartRequest,
  ResolveStartResult,
  Language,
} from './types';

const BASE = '/api/deepread';

const apiPatchJson = async <T>(endpoint: string, body: unknown): Promise<T> => {
  const response = await apiFetch(endpoint, 'PATCH', { body });
  return response.json() as Promise<T>;
};

// Documents API
export const documentsApi = {
  createFromText: (data: CreateDocumentFromTextRequest) =>
    apiPost<{ success: boolean; document: DocumentMeta }>(`${BASE}/documents/from-text`, data).then(
      (r) => r.document
    ),

  getDocument: (documentId: string) =>
    apiGet<{ success: boolean; document: DocumentMeta }>(`${BASE}/documents/${documentId}`).then(
      (r) => r.document
    ),

  getPreview: (documentId: string) =>
    apiGet<{ success: boolean; preview: DocumentPreview }>(
      `${BASE}/documents/${documentId}/preview`
    ).then((r) => r.preview),

  getTokens: (documentId: string, start = 0, limit = 500) =>
    apiGet<{ success: boolean; chunk: TokenChunk }>(
      `${BASE}/documents/${documentId}/tokens?start=${start}&limit=${limit}`
    ).then((r) => r.chunk),

  resolveStart: (documentId: string, data: ResolveStartRequest) =>
    apiPost<{ success: boolean; result: ResolveStartResult }>(
      `${BASE}/documents/${documentId}/resolve-start`,
      data
    ).then((r) => r.result),

  deleteDocument: (documentId: string) =>
    apiDelete<{ success: boolean }>(`${BASE}/documents/${documentId}`),
};

// Sessions API
export const sessionsApi = {
  create: (data: CreateSessionRequest) =>
    apiPost<{ success: boolean; session: Session }>(`${BASE}/sessions`, data).then(
      (r) => r.session
    ),

  getRecent: (days = 7) =>
    apiGet<{ success: boolean; sessions: SessionListItem[] }>(
      `${BASE}/sessions/recent?days=${days}`
    ).then((r) => r.sessions),

  getLatestForDocument: (documentId: string) =>
    apiGet<{ success: boolean; session: Session | null }>(
      `${BASE}/sessions/document/${documentId}/latest`
    ).then((r) => r.session),

  getSession: (sessionId: string) =>
    apiGet<{ success: boolean; session: Session }>(`${BASE}/sessions/${sessionId}`).then(
      (r) => r.session
    ),

  updateProgress: (sessionId: string, data: UpdateProgressRequest) =>
    apiPatchJson<{ success: boolean; session: Session }>(
      `${BASE}/sessions/${sessionId}/progress`,
      data
    ).then((r) => r.session),

  deleteSession: (sessionId: string) =>
    apiDelete<{ success: boolean }>(`${BASE}/sessions/${sessionId}`),
};
```

### 6. Zustand Store for Reader Settings

**File**: `store/speed-reading-store.ts`

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ReaderSettings {
  targetWpm: number;
  rampEnabled: boolean;
  rampSeconds: number;
}

interface SpeedReadingState {
  // Settings (persisted)
  settings: ReaderSettings;

  // Actions
  setTargetWpm: (wpm: number) => void;
  setRampEnabled: (enabled: boolean) => void;
  setRampSeconds: (seconds: number) => void;
  resetSettings: () => void;
}

const DEFAULT_SETTINGS: ReaderSettings = {
  targetWpm: 300,
  rampEnabled: true,
  rampSeconds: 30,
};

export const useSpeedReadingStore = create<SpeedReadingState>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,

      setTargetWpm: (wpm) =>
        set((state) => ({
          settings: {
            ...state.settings,
            targetWpm: Math.max(100, Math.min(1500, wpm)),
          },
        })),

      setRampEnabled: (enabled) =>
        set((state) => ({
          settings: { ...state.settings, rampEnabled: enabled },
        })),

      setRampSeconds: (seconds) =>
        set((state) => ({
          settings: {
            ...state.settings,
            rampSeconds: Math.max(0, Math.min(60, seconds)),
          },
        })),

      resetSettings: () => set({ settings: DEFAULT_SETTINGS }),
    }),
    {
      name: 'automaker-speed-reading-settings',
      partialize: (state) => ({ settings: state.settings }),
    }
  )
);
```

### 7. Backend Proxy Route

**File**: `apps/server/src/routes/deepread/index.ts`

```typescript
import { Router, type Request, type Response } from 'express';
import { createLogger } from '@automaker/utils';

const logger = createLogger('deepread-proxy');

const DEEPREAD_BACKEND_URL = process.env.DEEPREAD_BACKEND_URL || 'http://localhost:8001';

export function createDeepreadRoutes(): Router {
  const router = Router();

  // Health check for the proxy
  router.get('/health', async (_req: Request, res: Response) => {
    try {
      const response = await fetch(`${DEEPREAD_BACKEND_URL}/api/health`);
      const data = await response.json();
      res.json({ success: true, backend: data });
    } catch (error) {
      logger.error(`DeepRead backend health check failed at ${DEEPREAD_BACKEND_URL}/api/health:`, error);
      res.status(503).json({
        success: false,
        error: 'DeepRead backend unavailable',
      });
    }
  });

  /**
   * JSON-only proxy (v1)
   *
   * v1 intentionally avoids multipart file uploads; `.md` files are read in the browser and sent as text JSON.
   * This keeps the Automaker server security middleware intact and makes cloud deployment simpler.
   */
  router.all('/*', async (req: Request, res: Response) => {
    try {
      const upstreamPath = req.originalUrl.replace(/^\\/api\\/deepread/, '/api');
      const upstreamUrl = `${DEEPREAD_BACKEND_URL}${upstreamPath}`;

      const headers: Record<string, string> = {};
      const contentType = req.headers['content-type'];
      if (typeof contentType === 'string') headers['content-type'] = contentType;

      const hasBody = !['GET', 'HEAD'].includes(req.method.toUpperCase());
      const body = hasBody ? JSON.stringify(req.body ?? {}) : undefined;

      const upstreamResponse = await fetch(upstreamUrl, {
        method: req.method,
        headers,
        body,
      });

      const responseText = await upstreamResponse.text();
      const upstreamContentType = upstreamResponse.headers.get('content-type');
      if (upstreamContentType) res.setHeader('content-type', upstreamContentType);

      res.status(upstreamResponse.status).send(responseText);
    } catch (error) {
      logger.error('DeepRead proxy error:', error);
      res.status(502).json({
        success: false,
        error: 'Failed to connect to Speed Reading backend',
      });
    }
  });

  return router;
}
```

Register in main server (`apps/server/src/index.ts`):

```typescript
import { createDeepreadRoutes } from './routes/deepread';

// ... existing routes ...
app.use('/api/deepread', createDeepreadRoutes());
```

---

## Session 5 Deliverables

After completing Session 5 (REVISED), you will have:

1. ✅ Route files for `/speed-reading/*` paths
2. ✅ Main page component following Knowledge Hub pattern
3. ✅ Sidebar navigation with Shift+R shortcut
4. ✅ API client types and functions
5. ✅ Zustand store for reader settings
6. ✅ Backend proxy route to Python service
7. ✅ Placeholder components for import, preview, reader

---

## What Remains (Sessions 6-9)

| Session | Focus                 | Status                                                         |
| ------- | --------------------- | -------------------------------------------------------------- |
| **6**   | Import & Preview UI   | Full components for import form, preview with virtualized text |
| **7**   | Reader Engine         | Playback timing loop, token cache, ORP display, ramp           |
| **8**   | Reader Controls       | Auto-hiding controls, keyboard shortcuts, WPM/ramp UI          |
| **9**   | Session Persistence   | Auto-save, resume, recent sessions list                        |
| **10**  | Deployment (Deferred) | Docker, Hetzner setup - do later                               |

---

## Python Backend Setup (Prerequisite)

The Python backend from Sessions 1-4 should already be running. Key endpoints:

```
POST /api/documents/from-text     - Create document from text
GET  /api/documents/{id}          - Get document metadata
GET  /api/documents/{id}/preview  - Get preview text
GET  /api/documents/{id}/tokens   - Get token chunk
POST /api/documents/{id}/resolve-start - Snap to sentence start

POST /api/sessions                - Create reading session
GET  /api/sessions/recent         - List recent sessions
GET  /api/sessions/{id}           - Get session details
PATCH /api/sessions/{id}/progress - Update progress
DELETE /api/sessions/{id}         - Delete session
```

**Start the Python backend:**

```bash
cd "4.Speed Reading System/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Verification Checklist

- [ ] `/speed-reading` route loads the main page
- [ ] Speed Reading appears in sidebar under Systems
- [ ] Shift+R keyboard shortcut navigates to page
- [ ] API proxy forwards to Python backend
- [ ] Health check endpoint works
- [ ] Navigation between sub-routes works
- [ ] Reader settings persist in localStorage

---

## Next Steps

1. **Implement Session 5** - Create all the route and component files
2. **Verify Python backend** - Ensure Sessions 1-4 are complete
3. **Continue to Session 6** - Import & Preview UI
4. **Session 7** - Reader Engine (most complex part)
5. **Sessions 8-9** - Controls and persistence

The key architectural change is that **everything uses Automaker's existing infrastructure** - no duplicate routing, state management, or API client setup needed.
