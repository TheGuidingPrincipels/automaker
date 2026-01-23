# DeepRead Session Plans

This directory contains 10 detailed implementation sessions for building the DeepRead RSVP speed-reading application.

## v1 Scope (Web-only)

- **Inputs**: paste text, upload `.md` (read in the browser and sent via `POST /api/documents/from-text`)
- **PDF upload**: deferred (see `../docs/FUTURE-PDF-UPLOAD.md`)

## Overview

| Session | Focus                                                                | Duration | Deliverable                                       |
| ------- | -------------------------------------------------------------------- | -------- | ------------------------------------------------- |
| **1**   | [Foundation & Schema](./SESSION-01-foundation-schema.md)             | 3-4 hrs  | FastAPI skeleton, database models, Docker Compose |
| **2**   | [Tokenization Engine](./SESSION-02-tokenization-engine.md)           | 3-4 hrs  | Text normalization, tokenizer, ORP calculation    |
| **3**   | [Document Ingestion API](./SESSION-03-document-ingestion-api.md)     | 3-4 hrs  | Text ingestion endpoint (`from-text`)             |
| **4**   | [Sessions & Navigation API](./SESSION-04-sessions-navigation-api.md) | 2-3 hrs  | Session CRUD, resolve-start, cleanup task         |
| **5**   | [Frontend Foundation](./SESSION-05-frontend-foundation.md)           | 3-4 hrs  | React 19 setup, routing, state, dark theme        |
| **6**   | [Import & Preview UI](./SESSION-06-import-preview-ui.md)             | 3-4 hrs  | Import form, virtualized preview, word selection  |
| **7**   | [Reader Engine](./SESSION-07-reader-engine.md)                       | 4 hrs    | RSVP display, playback loop, token caching        |
| **8**   | [Reader Controls](./SESSION-08-reader-controls.md)                   | 3-4 hrs  | Play/pause, rewind, WPM, keyboard shortcuts       |
| **9**   | [Session Persistence](./SESSION-09-session-persistence.md)           | 2-3 hrs  | Auto-save, resume, recent sessions                |
| **10**  | [Integration & Deployment](./SESSION-10-integration-deployment.md)   | 4 hrs    | E2E tests, Docker, Hetzner deployment             |

**Total estimated time: ~30-35 hours**

## Session Dependencies

```
Session 1 (Foundation)
    ↓
Session 2 (Tokenizer)
    ↓
Session 3 (Documents API)
    ↓
Session 4 (Sessions API)  ←── Backend Complete
    ↓
Session 5 (Frontend Setup)
    ↓
Session 6 (Import/Preview)
    ↓
Session 7 (Reader Engine)
    ↓
Session 8 (Reader Controls)
    ↓
Session 9 (Persistence)
    ↓
Session 10 (Deployment)  ←── Project Complete
```

## Technology Stack

### Backend

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 + Alembic
- SQLite (v1)

### Frontend

- React 19
- TypeScript 5.9
- Vite 7
- TanStack Router + Query
- Tailwind CSS 4
- shadcn/ui
- Zustand

### Infrastructure

- Docker + Docker Compose
- Nginx (reverse proxy)
- Let's Encrypt (SSL)
- Hetzner Cloud

## Key Architecture Decisions

1. **Chunked token retrieval** - Backend stores all tokens; frontend fetches chunks on demand
2. **Time-based rewind** - Uses playback history ring buffer, not word-based calculation
3. **Linear ramp** - WPM increases from 50% to target over configurable duration
4. **Monospace ORP** - v1 uses monospace font for accurate ORP alignment
5. **Multi-user ready** - `user_id` columns present but nullable for future auth
6. **20,000 word limit** - Prioritizes speed over large document support

## Quick Start

### Starting a Session

1. Read the session document fully before starting
2. Ensure all prerequisites are met
3. Follow the implementation details in order
4. Complete the verification checklist before moving on

### Session Document Structure

Each session includes:

- **Overview** - Goal, duration, deliverable
- **Prerequisites** - What must exist before starting
- **Objectives** - Specific acceptance criteria
- **File Structure** - What files will be created
- **Implementation Details** - Code with explanations
- **Testing Requirements** - Tests to validate work
- **Verification Checklist** - Final checks
- **Context for Next Session** - What to carry forward

## API Reference (After Session 4)

```
Health:
  GET  /api/health

Documents:
  POST /api/documents/from-text
  GET  /api/documents/{id}
  GET  /api/documents/{id}/preview
  GET  /api/documents/{id}/tokens
  POST /api/documents/{id}/resolve-start
  DELETE /api/documents/{id}

Sessions:
  POST   /api/sessions
  GET    /api/sessions/recent
  GET    /api/sessions/document/{id}/latest
  GET    /api/sessions/{id}
  PATCH  /api/sessions/{id}/progress
  DELETE /api/sessions/{id}
```

## Keyboard Shortcuts (After Session 8)

| Key       | Action             |
| --------- | ------------------ |
| Space     | Play / Pause       |
| ←         | Rewind 10 seconds  |
| Shift + ← | Rewind 30 seconds  |
| ↑         | Increase WPM (+25) |
| ↓         | Decrease WPM (-25) |
| R         | Toggle ramp mode   |
| H         | Show/hide controls |
| Escape    | Exit reader        |

## Definition of Done (v1)

From the original plan:

1. ✅ Paste or upload `.md` with EN/DE selection → document created (**PDF deferred**)
2. ✅ Preview shows full text; click word to set start
3. ✅ Reader mode blacks out interface; ORP-aligned RSVP works with rhythm pauses
4. ✅ Play/Pause is instant
5. ✅ Rewind by 10/15/30s works reliably (including with ramp + WPM changes)
6. ✅ Scrub to 50% starts near sentence start
7. ✅ Progress saves and resumes; recent sessions visible for 7 days
