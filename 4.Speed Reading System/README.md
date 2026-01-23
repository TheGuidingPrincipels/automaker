# Speed Reading System (DeepRead)

An RSVP (Rapid Serial Visual Presentation) speed reading application integrated into Automaker.

---

## 🚨 CRITICAL: Code Organization Principles for LLMs

> **READ THIS BEFORE IMPLEMENTING ANY CODE**

### Self-Contained Architecture

The Speed Reading System is designed to be **exportable as a standalone feature**. To enable this:

**ALL backend code, database schemas, models, and services MUST be stored within this folder (`4.Speed Reading System/`).**

### What Goes WHERE

#### ✅ Store INSIDE `4.Speed Reading System/`

| Category             | Location                | Examples                                       |
| -------------------- | ----------------------- | ---------------------------------------------- |
| **Python Backend**   | `backend/`              | FastAPI app, routes, services                  |
| **Database Models**  | `backend/app/models/`   | SQLAlchemy models, Alembic migrations          |
| **Database Schemas** | `backend/app/schemas/`  | Pydantic request/response schemas              |
| **API Services**     | `backend/app/services/` | Tokenizer, ORP calculator, parser              |
| **Backend Config**   | `backend/`              | requirements.txt, pyproject.toml, .env.example |
| **Database Files**   | `backend/data/`         | SQLite database file (gitignored)              |
| **Session Plans**    | `sessions/`             | Implementation session documents               |
| **Documentation**    | Root of this folder     | README, architecture docs                      |

```
4.Speed Reading System/
├── README.md                    # This file
├── Idea.md                      # Original concept document
├── sessions/                    # Implementation session plans
│   ├── SESSION-01-*.md
│   ├── SESSION-02-*.md
│   └── ...
├── backend/                     # ⭐ ALL BACKEND CODE HERE
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Settings/configuration
│   │   ├── database.py          # Database connection
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── document.py
│   │   │   └── session.py
│   │   ├── schemas/             # Pydantic schemas
│   │   │   ├── document.py
│   │   │   └── session.py
│   │   ├── services/            # Business logic
│   │   │   ├── tokenizer.py
│   │   │   ├── orp.py
│   │   │   └── parser.py
│   │   └── routes/              # API endpoints
│   │       ├── documents.py
│   │       ├── sessions.py
│   │       └── health.py
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Backend tests
│   ├── data/                    # SQLite DB storage (gitignored)
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic.ini
│   └── run.py                   # Entry point
└── docs/                        # Additional documentation
```

#### ⚠️ Minimal Integration in Automaker (ONLY what's necessary)

These are the **ONLY** files that should be modified/created in the main Automaker codebase:

| File                                              | Purpose           | Notes                                   |
| ------------------------------------------------- | ----------------- | --------------------------------------- |
| `1.apps/ui/src/routes/speed-reading*.tsx`         | Route definitions | Minimal - just imports components       |
| `1.apps/ui/src/components/views/speed-reading-*/` | UI components     | Frontend only, no backend logic         |
| `1.apps/ui/src/hooks/speed-reading/`              | React hooks       | API calls, state management             |
| `1.apps/ui/src/lib/speed-reading/`                | Types, API client | TypeScript types mirror backend schemas |
| `1.apps/ui/src/store/speed-reading-store.ts`      | Zustand store     | Reader settings persistence             |
| `1.apps/server/src/routes/deepread/index.ts`      | **Proxy only**    | Just forwards to Python backend         |
| `libs/types/src/settings.ts`                      | Keyboard shortcut | Add `speedReading: string`              |
| `use-navigation.ts`                               | Sidebar item      | Add nav entry                           |

### ❌ Do NOT Do This

```
❌ DON'T create database models in libs/types/
❌ DON'T create backend services in apps/server/src/services/
❌ DON'T store Speed Reading business logic in Automaker's Express server
❌ DON'T mix Speed Reading database with Automaker's team-storage
❌ DON'T create Alembic migrations outside this folder
```

### ✅ Do This Instead

```
✅ DO keep all Python code in 4.Speed Reading System/backend/
✅ DO keep all database schemas/models in the backend folder
✅ DO use Automaker's Express server ONLY as a proxy
✅ DO mirror TypeScript types from Python schemas (don't duplicate logic)
✅ DO keep the frontend components in Automaker (they're just UI)
```

---

## Why This Matters

1. **Exportability**: The Speed Reading System can be extracted and run independently
2. **Clear Boundaries**: Easy to understand what belongs where
3. **Maintainability**: Backend changes are isolated to one location
4. **Testing**: Backend can be tested independently of Automaker
5. **Deployment Flexibility**: Can deploy backend separately if needed

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Automaker Frontend (React)                    │
│  - Routes: /speed-reading/*                                      │
│  - Components: Import, Preview, Reader UI                        │
│  - Hooks: API calls, playback engine                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Automaker Express Server (Port 3008)                │
│  - /api/deepread/* → PROXY ONLY (no business logic)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│     Speed Reading Python Backend (Port 8001)    [THIS FOLDER]   │
│  - FastAPI application                                           │
│  - SQLite database                                               │
│  - Tokenization, ORP calculation                                 │
│  - Document parsing (MD, PDF)                                    │
│  - Session management                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Start the Python Backend

```bash
cd "4.Speed Reading System/backend"
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Start Automaker (will proxy to backend)

```bash
# From automaker root
npm run dev
```

### 3. Access Speed Reading

- Navigate to `/speed-reading` in Automaker
- Or press `Shift+R` keyboard shortcut

---

## Implementation Sessions

| Session | Focus                                  | Status                                        |
| ------- | -------------------------------------- | --------------------------------------------- |
| 1-4     | Python Backend (API, DB, tokenization) | See original sessions                         |
| 5       | Frontend Foundation & Integration      | `SESSION-05-REVISED-automaker-integration.md` |
| 6       | Import & Preview UI                    | `SESSION-06-REVISED-import-preview.md`        |
| 7       | Reader Engine                          | `SESSION-07-REVISED-reader-engine.md`         |
| 8       | Reader Controls                        | `SESSION-08-REVISED-reader-controls.md`       |
| 9       | Session Persistence                    | `SESSION-09-REVISED-session-persistence.md`   |
| 10      | Deployment (Deferred)                  | `SESSION-10-integration-deployment.md`        |

---

## API Endpoints (Backend)

All endpoints are prefixed with `/api` and proxied through Automaker at `/api/deepread/*`.

### Documents

- `POST /api/documents/from-text` - Create from pasted text
- `POST /api/documents/from-file` - Create from uploaded file
- `GET /api/documents/{id}` - Get document metadata
- `GET /api/documents/{id}/preview` - Get preview text
- `GET /api/documents/{id}/tokens` - Get token chunk
- `POST /api/documents/{id}/resolve-start` - Snap to sentence/paragraph start

### Sessions

- `POST /api/sessions` - Create reading session
- `GET /api/sessions/recent` - List recent sessions (7 days)
- `GET /api/sessions/{id}` - Get session details
- `PATCH /api/sessions/{id}/progress` - Update progress
- `DELETE /api/sessions/{id}` - Delete session

### Health

- `GET /api/health` - Health check

---

## Environment Variables

### Backend (`backend/.env`)

```env
DATABASE_URL=sqlite:///./data/deepread.db
DEBUG=true
MAX_DOCUMENT_WORDS=20000
CHUNK_SIZE=500
SESSION_EXPIRY_DAYS=7
```

### Automaker Integration

```env
DEEPREAD_BACKEND_URL=http://localhost:8001
```

---

## Testing

### Backend Tests

```bash
cd "4.Speed Reading System/backend"
pytest tests/
```

### E2E Tests (via Playwright)

```bash
# From automaker root
npm run test -- --grep "speed-reading"
```

---

## Future: Standalone Export

To export Speed Reading as a standalone application:

1. Copy entire `4.Speed Reading System/` folder
2. Add a simple frontend (or use the React components)
3. Remove Automaker proxy dependency
4. Deploy backend directly

The backend is fully independent and requires no Automaker code to run.
