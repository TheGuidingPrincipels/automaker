# Sub-Plan F-1: Backend Setup (Standalone Service)

> **Prerequisites**: Sub-Plans A, B, 3A, 3B, D, E must be complete
> **Execution Location**: AI-Library repository (`/Users/ruben/Documents/GitHub/AI-Libary-Hub/AI-Library/`)
> **Effort**: Small (1-2 hours)
> **Next**: Sub-Plan F-2 (API Client & Types)

---

## Goal

Configure the AI-Library Python backend to run as a **standalone service** that the Automaker frontend can call directly. No code copying - the backend stays in this repository.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTOMAKER (React Frontend)                         │
│                           http://localhost:5173                              │
└────────────────────────────┬──────────────────────────────┬─────────────────┘
                             │                              │
                             ▼                              ▼
┌────────────────────────────────────────┐    ┌──────────────────────────────┐
│    Automaker Express Backend           │    │   AI-Library Python Backend  │
│    http://localhost:3001               │    │   http://localhost:8001      │
│                                        │    │                              │
│    • Knowledge Server (existing)       │    │   • /api/sessions/*          │
│    • Learning (existing)               │    │   • /api/library/*           │
│    • Other Automaker features          │    │   • /api/query/*             │
└────────────────────────────────────────┘    └──────────────────────────────┘
```

**Key Principle**: Frontend calls both backends directly. No proxying through Express.

---

## Step 1: Update CORS Configuration

Update `configs/settings.yaml` to allow requests from Automaker frontend:

```yaml
# configs/settings.yaml

api:
  host: ${API_HOST:0.0.0.0}
  port: ${API_PORT:8001}
  cors_origins:
    - http://localhost:5173 # Vite dev server
    - http://localhost:5174 # Vite alt port
    - http://localhost:3000 # Alternative dev port
    - http://127.0.0.1:5173 # Localhost variant
    # Add production origins when deploying:
    # - https://your-app.com
```

---

## Step 2: Verify API Endpoints

Ensure all required endpoints are working. Run the API and test:

```bash
# Terminal 1: Start the API
cd /Users/ruben/Documents/GitHub/AI-Libary-Hub/AI-Library
source .venv/bin/activate  # or create venv if needed
pip install -e ".[dev]"
python run_api.py

# API will be available at http://localhost:8001
```

```bash
# Terminal 2: Test endpoints
# Health check
curl http://localhost:8001/health

# List sessions
curl http://localhost:8001/api/sessions

# Get library structure
curl http://localhost:8001/api/library

# Test query (after Sub-Plan E is done)
curl -X POST http://localhost:8001/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is in my library?"}'
```

---

## Step 3: Create Startup Script

Create `start-api.sh` for easy startup:

```bash
#!/bin/bash
# start-api.sh - Start AI-Library API server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
fi

# Start API
echo "Starting AI-Library API on http://localhost:8001"
python run_api.py
```

Make it executable:

```bash
chmod +x start-api.sh
```

---

## Step 4: Document API Contract

The Automaker frontend will consume these endpoints:

### Session Endpoints (`/api/sessions`)

| Method | Endpoint                                          | Description                     |
| ------ | ------------------------------------------------- | ------------------------------- |
| GET    | `/api/sessions`                                   | List all sessions               |
| POST   | `/api/sessions`                                   | Create new session              |
| GET    | `/api/sessions/{id}`                              | Get session details             |
| DELETE | `/api/sessions/{id}`                              | Delete session                  |
| POST   | `/api/sessions/{id}/upload`                       | Upload source file              |
| POST   | `/api/sessions/{id}/cleanup/generate`             | Generate cleanup plan           |
| GET    | `/api/sessions/{id}/cleanup`                      | Get cleanup plan                |
| POST   | `/api/sessions/{id}/cleanup/decide/{block_id}`    | Decide keep/discard             |
| POST   | `/api/sessions/{id}/cleanup/approve`              | Approve cleanup plan            |
| POST   | `/api/sessions/{id}/plan/generate`                | Generate routing plan           |
| GET    | `/api/sessions/{id}/plan`                         | Get routing plan                |
| POST   | `/api/sessions/{id}/plan/select/{block_id}`       | Select destination              |
| POST   | `/api/sessions/{id}/plan/reject-block/{block_id}` | Reject block                    |
| POST   | `/api/sessions/{id}/execute`                      | Execute session                 |
| POST   | `/api/sessions/{id}/mode`                         | Set content mode                |
| WS     | `/api/sessions/{id}/stream`                       | WebSocket for real-time updates |

### Library Endpoints (`/api/library`)

| Method | Endpoint                    | Description              |
| ------ | --------------------------- | ------------------------ |
| GET    | `/api/library`              | Get library structure    |
| GET    | `/api/library/files/{path}` | Get file content         |
| GET    | `/api/library/search`       | Search library (keyword) |
| POST   | `/api/library/index`        | Trigger re-indexing      |
| GET    | `/api/library/stats`        | Get library statistics   |

### Query Endpoints (`/api/query`) - After Sub-Plan E

| Method | Endpoint                        | Description              |
| ------ | ------------------------------- | ------------------------ |
| POST   | `/api/query/ask`                | RAG query with citations |
| POST   | `/api/query/search`             | Semantic search only     |
| GET    | `/api/query/conversations`      | List conversations       |
| GET    | `/api/query/conversations/{id}` | Get conversation         |
| DELETE | `/api/query/conversations/{id}` | Delete conversation      |

---

## Step 5: Environment Variables (Optional)

For production or custom configurations, support these env vars:

```bash
# .env (optional, for overrides)
API_HOST=0.0.0.0
API_PORT=8001
LIBRARY_PATH=./library
SESSIONS_PATH=./sessions
VECTOR_DB_PATH=./vector_db
EMBEDDING_PROVIDER=mistral  # or openai
```

---

## Acceptance Criteria

- [ ] API starts on port 8001 without errors
- [ ] CORS allows requests from `http://localhost:5173`
- [ ] `/health` endpoint returns success
- [ ] `/api/sessions` endpoint works
- [ ] `/api/library` endpoint works
- [ ] `/api/query/ask` endpoint works (after Sub-Plan E)
- [ ] WebSocket connection works for streaming
- [ ] Startup script created and working

---

## Running the Complete System

After this sub-plan, you can run:

```bash
# Terminal 1: AI-Library Backend
cd /Users/ruben/Documents/GitHub/AI-Libary-Hub/AI-Library
./start-api.sh
# → Running on http://localhost:8001

# Terminal 2: Automaker Backend (existing)
cd /Users/ruben/Documents/GitHub/automaker
npm run dev:server
# → Running on http://localhost:3001

# Terminal 3: Automaker Frontend
cd /Users/ruben/Documents/GitHub/automaker
npm run dev
# → Running on http://localhost:5173
```

---

## Notes for Sub-Plan F-2

The frontend needs to know where the AI-Library API is. This will be configured via environment variable:

```bash
# In automaker/.env
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8001
```

---

_End of Sub-Plan F-1_
