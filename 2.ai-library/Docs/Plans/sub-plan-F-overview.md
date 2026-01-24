# Sub-Plan F: Web UI Integration (Overview)

> **This document replaces**: `sub-plan-F-webui-migration.md` (archived)
> **Prerequisites**: Sub-Plans A, B, 3A, 3B, D, **E (Query Mode)**

---

## Summary

Sub-Plan F integrates the AI-Library backend into the Automaker frontend, replacing the "Blueprints" section with a new "Knowledge Library" section.

**Key Architecture Decision**: The AI-Library Python backend runs as a **standalone service**. The Automaker frontend calls it directly. No code copying or proxying through Express.

---

## Execution Order

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXECUTION SEQUENCE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [PREREQUISITE] Sub-Plan E: Query Mode                                      │
│       ↓                                                                      │
│  Sub-Plan F-1: Backend Setup          (~1-2 hours)                          │
│       ↓         Configure standalone Python service                          │
│  Sub-Plan F-2: API Client & Types     (~2-4 hours)                          │
│       ↓         Create TypeScript integration layer                          │
│  Sub-Plan F-3: UI Components          (~8-16 hours)                         │
│                 Replace Blueprints with Knowledge Library UI                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Sub-Plans

| Plan    | Document                          | Scope                                             | Location                         |
| ------- | --------------------------------- | ------------------------------------------------- | -------------------------------- |
| **F-1** | `sub-plan-F1-backend-setup.md`    | Configure AI-Library as standalone service        | `2.ai-library/` in automaker     |
| **F-2** | `sub-plan-F2-api-client-types.md` | TypeScript types, API client, hooks, store        | Automaker `libs/` and `apps/ui/` |
| **F-3** | `sub-plan-F3-ui-components.md`    | Replace Blueprints section with Knowledge Library | Automaker `apps/ui/`             |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTOMAKER (React Frontend)                         │
│                           http://localhost:3007                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Knowledge Hub                                     ││
│  │  ┌───────────────────┐  ┌──────────────────┐  ┌─────────────────────┐   ││
│  │  │ Knowledge Library │  │ Knowledge Server │  │      Learning       │   ││
│  │  │ (AI-Library)      │  │ (Existing)       │  │    (Existing)       │   ││
│  │  └────────┬──────────┘  └────────┬─────────┘  └──────────┬──────────┘   ││
│  └───────────│──────────────────────│───────────────────────│──────────────┘│
└──────────────│──────────────────────│───────────────────────│───────────────┘
               │                      │                       │
               ▼                      └───────────┬───────────┘
┌──────────────────────────────┐                  │
│   AI-Library Python Backend  │                  ▼
│   http://localhost:8001      │    ┌──────────────────────────────┐
│                              │    │   Automaker Express Backend  │
│   • Session management       │    │   http://localhost:3008      │
│   • Extraction pipeline      │    │                              │
│   • Library browsing         │    │   • Knowledge Server storage │
│   • Query/RAG (Sub-Plan E)   │    │   • Learning storage         │
│                              │    │   • Other Automaker features │
│   (SEPARATE SERVICE)         │    │                              │
└──────────────────────────────┘    └──────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Qdrant Vector Database     │
│   http://localhost:6333      │
│   (Docker container)         │
└──────────────────────────────┘
```

---

## What Each Plan Delivers

### F-1: Backend Setup

- CORS configuration for Automaker frontend
- Startup script for AI-Library API
- API endpoint documentation
- Health check verification
- Backend contract updates required for the UI:
  - Upload-first sessions (create empty session, then upload)
  - Persistent uploads (source file must remain accessible to the system)
  - Library file validation + `## Overview` metadata

### F-2: API Client & Types

- TypeScript types matching AI-Library API schemas
- API client class (`knowledgeLibraryApi`)
- TanStack Query hooks (`useKLSession`, `useKLLibrary`, etc.)
- Zustand store for UI state
- Non-fatal offline behavior (“Knowledge Library disconnected”)

### F-3: UI Components

- Main container with tab navigation (Input / Library / Query)
- Input Mode (V1): upload-first ingestion (one markdown file per session), plan review, block cards, execution
- Library Browser: Category tree, file viewer, keyword + semantic search, invalid file badges
- Query Mode: Chat interface, answer cards with citations
- Integration with existing Automaker UI patterns
- New file creation requires:
  - `# Title`
  - case-sensitive `## Overview` (50–250 chars after trim + whitespace normalization)

---

## Running the Complete System

After all F sub-plans are complete:

```bash
# Terminal 1: Qdrant Vector Database (if not already running)
docker start qdrant
# → Running on http://localhost:6333

# Terminal 2: AI-Library Backend (from automaker/2.ai-library/)
cd /Users/ruben/Documents/GitHub/automaker/2.ai-library
./start-api.sh
# → Running on http://localhost:8001

# Terminal 3: Automaker Backend (from automaker/)
cd /Users/ruben/Documents/GitHub/automaker
npm run dev:server
# → Running on http://localhost:3008

# Terminal 4: Automaker Frontend (from automaker/)
cd /Users/ruben/Documents/GitHub/automaker
npm run dev
# → Running on http://localhost:3007

# Open browser: http://localhost:3007/knowledge-hub
# Click "Knowledge Library" section
```

---

## Key Differences from Original Plan

| Aspect       | Original `sub-plan-F-webui-migration.md` | New Split Plans               |
| ------------ | ---------------------------------------- | ----------------------------- |
| Structure    | Single 1,800-line document               | 3 focused documents           |
| Backend      | Copy code to Automaker                   | Keep separate, run as service |
| Integration  | Proxy through Express                    | Frontend calls API directly   |
| Code style   | Full implementations                     | Architecture + key examples   |
| Dependencies | Sub-Plans A-E                            | Sub-Plans A-E (E was missing) |

---

## Archived Files

The original plan has been moved to:

```
Docs/archive/sub-plan-F-webui-migration-original.md
```

---

_End of Sub-Plan F Overview_
