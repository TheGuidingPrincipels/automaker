# Sub-Plan F-1: Backend Setup (Standalone Service)

> **Prerequisites**: Sub-Plans A, B, 3A, 3B, D, E must be complete
> **Execution Location**: Automaker repository (`/Users/ruben/Documents/GitHub/automaker/2.ai-library/`)
> **Effort**: Small (1-2 hours)
> **Next**: Sub-Plan F-2 (API Client & Types)

---

## Goal

Configure the AI-Library Python backend to run as a **standalone service** that the Automaker frontend can call directly. The AI-Library code lives inside the automaker monorepo at `2.ai-library/`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTOMAKER (React Frontend)                         │
│                           http://localhost:3007                              │
└────────────────────────────┬──────────────────────────────────────┬─────────┘
                             │                              │
                             ▼                              ▼
┌────────────────────────────────────────┐    ┌──────────────────────────────┐
│    Automaker Express Backend           │    │   AI-Library Python Backend  │
│    http://localhost:3008               │    │   http://localhost:8001      │
│                                        │    │                              │
│    • Knowledge Server (existing)       │    │   • /api/sessions/*          │
│    • Learning (existing)               │    │   • /api/library/*           │
│    • Other Automaker features          │    │   • /api/query/*             │
└────────────────────────────────────────┘    └──────────────────────────────┘
                                                            │
                                                            ▼
                                              ┌──────────────────────────────┐
                                              │   Qdrant Vector Database     │
                                              │   http://localhost:6333      │
                                              │   (Docker container)         │
                                              └──────────────────────────────┘
```

**Key Principle**: Frontend calls both backends directly. No proxying through Express.

---

## Step 0: Prerequisites (Docker & Qdrant)

### Install Docker

```bash
# macOS (if not already installed)
brew install --cask docker

# Start Docker Desktop
open -a Docker

# Verify Docker is running
docker --version
```

### Start Qdrant Vector Database

```bash
# Pull and run Qdrant (first time)
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Verify Qdrant is running
curl http://localhost:6333/collections
# Expected: {"result":{"collections":[]},"status":"ok","time":...}
```

**Restart Qdrant after system reboot:**

```bash
docker start qdrant
```

### Set Environment Variables

Create `2.ai-library/.env`:

```bash
# Required: Mistral API key for embeddings
MISTRAL_API_KEY=your-mistral-api-key-here

# Optional: Override defaults
# API_HOST=0.0.0.0
# API_PORT=8001
```

Or export directly:

```bash
export MISTRAL_API_KEY=your-mistral-api-key-here
```

---

## Step 1: Update CORS Configuration

Update `2.ai-library/configs/settings.yaml` to use port 8001 and allow frontend requests:

```yaml
# configs/settings.yaml

api:
  host: 0.0.0.0
  port: 8001
  cors_origins:
    - http://localhost:3007 # Automaker Vite dev server
    - http://localhost:5173 # Vite alternate port
    - http://localhost:5174 # Vite alt port
    - http://127.0.0.1:3007 # Localhost variant
    # Add production origins when deploying:
    # - https://your-app.com
  debug: false
```

---

## Step 2: Create Python Virtual Environment

```bash
# Navigate to AI-Library directory
cd /Users/ruben/Documents/GitHub/automaker/2.ai-library

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"
```

---

## Step 3: Create Startup Script

Create `2.ai-library/start-api.sh`:

```bash
#!/bin/bash
# start-api.sh - Start AI-Library API server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for required environment variables
if [ -z "$MISTRAL_API_KEY" ]; then
    echo "ERROR: MISTRAL_API_KEY environment variable is not set"
    echo "Please set it in .env or export it directly"
    exit 1
fi

# Check if Qdrant is running
if ! curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo "WARNING: Qdrant is not running on localhost:6333"
    echo "Start it with: docker start qdrant"
    echo "Or first time: docker run -d --name qdrant -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant:latest"
    exit 1
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
fi

# Start API on port 8001
echo "Starting AI-Library API on http://localhost:8001"
echo "  - Swagger UI: http://localhost:8001/docs"
echo "  - Health: http://localhost:8001/health"
python run_api.py --port 8001
```

Make it executable:

```bash
chmod +x 2.ai-library/start-api.sh
```

---

## Step 4: Verify API Endpoints

```bash
# Terminal 1: Start the API
cd /Users/ruben/Documents/GitHub/automaker/2.ai-library
./start-api.sh

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

# Test query (RAG)
curl -X POST http://localhost:8001/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is in my library?"}'
```

---

## Step 5: Document API Contract

The Automaker frontend will consume these endpoints:

### Session Endpoints (`/api/sessions`)

| Method | Endpoint                                          | Description                                                          |
| ------ | ------------------------------------------------- | -------------------------------------------------------------------- |
| GET    | `/api/sessions`                                   | List all sessions                                                    |
| POST   | `/api/sessions`                                   | Create new session (supports empty session for upload-first UI)      |
| GET    | `/api/sessions/{id}`                              | Get session details                                                  |
| DELETE | `/api/sessions/{id}`                              | Delete session                                                       |
| POST   | `/api/sessions/{id}/upload`                       | Upload source file                                                   |
| GET    | `/api/sessions/{id}/blocks`                       | Get parsed blocks                                                    |
| POST   | `/api/sessions/{id}/cleanup/generate`             | Generate cleanup plan (use `?use_ai=true` for AI suggestions)        |
| GET    | `/api/sessions/{id}/cleanup`                      | Get cleanup plan                                                     |
| POST   | `/api/sessions/{id}/cleanup/decide/{block_id}`    | Decide keep/discard                                                  |
| POST   | `/api/sessions/{id}/cleanup/approve`              | Approve cleanup plan                                                 |
| POST   | `/api/sessions/{id}/plan/generate`                | Generate routing plan (use `?use_ai=true&use_candidate_finder=true`) |
| GET    | `/api/sessions/{id}/plan`                         | Get routing plan                                                     |
| POST   | `/api/sessions/{id}/plan/select/{block_id}`       | Select destination                                                   |
| POST   | `/api/sessions/{id}/plan/reject-block/{block_id}` | Reject block                                                         |
| POST   | `/api/sessions/{id}/plan/approve`                 | Approve routing plan (required before execute)                       |
| POST   | `/api/sessions/{id}/execute`                      | Execute session                                                      |
| POST   | `/api/sessions/{id}/mode`                         | Set content mode                                                     |
| WS     | `/api/sessions/{id}/stream`                       | WebSocket for real-time updates                                      |

### Library Endpoints (`/api/library`)

| Method | Endpoint                                      | Description                                                        |
| ------ | --------------------------------------------- | ------------------------------------------------------------------ |
| GET    | `/api/library`                                | Get library structure (includes file validity + validation errors) |
| GET    | `/api/library/files/{file_path:path}`         | Get file metadata                                                  |
| GET    | `/api/library/files/{file_path:path}/content` | Get file content                                                   |
| GET    | `/api/library/search`                         | Search library (keyword)                                           |
| POST   | `/api/library/index`                          | Trigger re-indexing                                                |
| GET    | `/api/library/index/stats`                    | Get index statistics                                               |

### Query Endpoints (`/api/query`)

| Method | Endpoint                        | Description                 |
| ------ | ------------------------------- | --------------------------- |
| POST   | `/api/query/ask`                | RAG query with citations    |
| POST   | `/api/query/search`             | Semantic search (JSON body) |
| GET    | `/api/query/conversations`      | List conversations          |
| GET    | `/api/query/conversations/{id}` | Get conversation            |
| DELETE | `/api/query/conversations/{id}` | Delete conversation         |

---

### Required V1 Contract Updates (Must implement before F-2/F-3)

The current backend code does **not** fully match the upload-first + create-file-metadata requirements. Implement these backend contract updates before starting Sub-Plan F-2 or F-3.

#### A) Upload-first sessions (create empty session → upload)

Required behavior:

- `POST /api/sessions` must allow creating an **empty** session (no `source_path`).
- `POST /api/sessions/{id}/upload` attaches and parses the uploaded markdown file for that session.

Implementation notes:

- Update `2.ai-library/src/api/schemas.py`:
  - `CreateSessionRequest.source_path` must be `Optional[str]` (can be `null` / omitted).
- Update `2.ai-library/src/api/routes/sessions.py`:
  - `create_session()` must handle “no `source_path`” by creating the session without parsing.
- Update `2.ai-library/src/session/manager.py`:
  - Allow creating a session without parsing (e.g., `source_path: Optional[str] = None`).

#### B) Persist uploaded source files (no temp delete)

Required behavior:

- Uploaded files must be persisted on disk under a session-owned folder (example: `2.ai-library/sessions/uploads/{session_id}/source.md`).
- The source file must remain available for the session lifetime (at minimum until session deletion; optionally until explicit “cleanup” after verification).
- No silent deletion: if cleanup is done, it must be explicit and reflected in the session state/log.

Implementation notes:

- Update `2.ai-library/src/api/routes/sessions.py` `/upload`:
  - Save into a session-owned location and **do not** unlink in `finally`.
  - Set `session.source.file_path` to the persisted path.
- Update `DELETE /api/sessions/{id}` to also remove persisted uploads (best-effort, but do not hide errors; return a clear error if cleanup fails unexpectedly).

#### C) Create-file requires Title + `## Overview` (50–250 chars)

Required behavior:

- Any routing option with `action === "create_file"` must include:
  - `proposed_file_title`
  - `proposed_file_overview` (50–250 chars after trim + whitespace normalization)
- The UI must be allowed to override those values at selection time.
- The title/overview must be decided **once per destination file** (if multiple blocks create/append to the same new file in a single session).
- Execution must write new files in this format:

```
# Title

## Overview
<overview text>
```

Implementation notes:

- Update `2.ai-library/src/models/routing_plan.py`:
  - Add `proposed_file_overview` to `BlockDestination`.
  - Add fields to persist UI overrides for file title/overview **per destination file** (recommended: `RoutingPlan.new_files[dest_file] = { title, overview }`).
- Update `2.ai-library/src/api/schemas.py`:
  - Add `proposed_file_overview` to `DestinationOptionResponse`.
  - Extend `SelectDestinationRequest` to accept title/overview overrides for `create_file` (per-block request, but backend must reconcile to the per-file metadata map).
- Update `2.ai-library/src/api/routes/sessions.py`:
  - In `execute_session()`, require title + overview for `create_file` and pass both to the writer.
- Update `2.ai-library/src/execution/writer.py`:
  - Extend `create_file()` to accept `overview` and write the `## Overview` section.

#### D) Library file validation fields for UI badges

Required behavior:

- Library file metadata must include:
  - `overview` (string | null)
  - `is_valid` (boolean)
  - `validation_errors` (string[])
- Invalid means:
  - Missing H1 title at top (`# Title` first line), OR
  - Missing **case-sensitive** `## Overview`, OR
  - Overview length outside 50–250 chars (after trim + whitespace normalization)
- Invalid files must still be returned by `/api/library` (UI shows red badge), and routing into them is allowed.

Implementation notes:

- Update `2.ai-library/src/models/library.py` + `2.ai-library/src/library/scanner.py` to extract/validate the Overview block.
- Update `2.ai-library/src/api/schemas.py` `LibraryFileResponse` to expose the validation fields.
- Update `2.ai-library/src/library/manifest.py` if you want the routing context to include overview validity hints (optional for V1).

#### E) WebSocket stream contract (for Input Mode chat transcript)

Required behavior:

- `WS /api/sessions/{id}/stream` must emit events that the UI can display as a transcript/log.
- Each event should include a timestamp (ISO string) and a stable `event_type` union.

Implementation notes:

- Use `2.ai-library/src/api/schemas.py` `StreamEvent` as the canonical JSON shape, and ensure `2.ai-library/src/api/routes/sessions.py` actually sends the `timestamp`.

#### F) Session “chat” messages (user → Claude context)

Required behavior:

- The Input Mode UI must let the user send short guidance messages (not ingestion) to influence AI planning, especially **routing**, e.g.:
  - “These blocks should go into `docs/auth.md`”
  - “Focus routing to existing sections; avoid creating new files”
- Messages do **not** need to be persisted long-term, but must apply for the current session while the user is working.

Recommended implementation (WebSocket, keeps UI simple):

- Extend `WS /api/sessions/{id}/stream` to accept:
  - `{ "command": "user_message", "message": "<text>" }`
- Backend appends that message to session state (example: `session.conversation_history`) and echoes an event:
  - `event_type: "user_message"`
  - `data: { message: "<text>" }`
- When generating prompts, include the latest user messages as “User guidance”:
  - Required: include in **routing** prompts
  - Optional (simple + helpful): include in **cleanup** prompts too

#### G) Session “question/answer” (Claude asks, user answers, continue)

Required behavior:

- During cleanup/routing generation, Claude may emit a request for more context.
- The backend must surface this to the UI as one or more `question` events, and pause progress until answered.
- The user provides an answer, and the workflow continues normally.

Recommended implementation (simple, re-run generation):

1. Update cleanup/routing prompts to allow a “question response” shape:
   - If the model cannot decide safely, it returns:
     - `{ "questions": [{ "question_id": "...", "message": "..." }, ...] }`
     - (Multiple questions are allowed.)
2. Backend detects `questions`:
   - Stores them in `session.pending_questions`
   - Emits `event_type: "question"` for each one (include `question_id` + `message`)
   - Does **not** mark the plan as ready
3. UI answers over WebSocket:
   - `{ "command": "answer", "question_id": "...", "message": "<answer>" }`
4. Backend stores answers in session state (append to `session.conversation_history`) and clears the matching pending question.
5. Once all pending questions are answered, UI (or backend) re-triggers generation (`generate_cleanup` / `generate_routing`) using the updated session context.

## Required Library File Standard (for UI + Routing Quality)

All new library files created by the system must include:

1. An H1 title as the first line (`# Title`)
2. A **case-sensitive** `## Overview` section
3. The overview text must be a short description (50–250 chars) after:
   - trimming, and
   - collapsing internal whitespace to single spaces (normalize)
   - (No strict markdown validation required)

**Existing library files** that do not meet this standard are considered **invalid**:

- They must still appear in the library structure response (so the UI can show a red badge + errors).
- Routing into invalid files is allowed, but the UI should warn users when selecting an invalid destination.

This requires the library scanner/manifest to extract:

- `overview` (string | null)
- `is_valid` (boolean)
- `validation_errors` (string[])

---

## Step 6: Environment Variables (Optional)

For production or custom configurations, support these env vars:

```bash
# .env (optional, for overrides)
API_HOST=0.0.0.0
API_PORT=8001
LIBRARY_PATH=./library
SESSIONS_PATH=./sessions
MISTRAL_API_KEY=your-mistral-api-key

# For OpenAI embeddings instead of Mistral:
# OPENAI_API_KEY=sk-...
```

---

## Data Migration Safety

### Source of Truth: Markdown Files

```
2.ai-library/library/
├── _index.yaml           ← Library manifest
├── docs/*.md             ← Your knowledge content
└── guides/*.md           ← Your guides
```

**Critical**: The `library/` folder contains your source content. Vector embeddings in Qdrant can ALWAYS be regenerated from these files.

### Migration to Hetzner

When deploying to Hetzner VM, choose one of these approaches:

| Method                 | When to Use              | Command                                    |
| ---------------------- | ------------------------ | ------------------------------------------ |
| **Regenerate Vectors** | First migration (safest) | Copy `library/` → run `index --all`        |
| **Snapshot Migration** | Large library (faster)   | Export Qdrant snapshot → restore on server |
| **Direct Migration**   | Network accessible       | Use `qdrant-client.migrate()`              |

**Recommended**: Commit `library/` to git. On Hetzner, regenerate vectors from source.

### Backup Before Migration

```bash
# Backup library content (source of truth)
tar -czf library-backup.tar.gz 2.ai-library/library/

# Optional: Create Qdrant snapshot
curl -X POST http://localhost:6333/collections/knowledge_library/snapshots
```

---

## Acceptance Criteria

- [ ] Docker installed and running
- [ ] Qdrant container running on port 6333
- [ ] Python virtual environment created
- [ ] API starts on port 8001 without errors
- [ ] CORS allows requests from `http://localhost:3007`
- [ ] `/health` endpoint returns success
- [ ] `/api/sessions` endpoint works
- [ ] `/api/library` endpoint works
- [ ] `/api/query/ask` endpoint works
- [ ] WebSocket connection works for streaming (including `user_message` and `answer`)
- [ ] Startup script created and working

---

## Running the Complete System

After this sub-plan, you can run:

```bash
# Terminal 1: Qdrant (if not already running)
docker start qdrant

# Terminal 2: AI-Library Backend
cd /Users/ruben/Documents/GitHub/automaker/2.ai-library
./start-api.sh
# → Running on http://localhost:8001

# Terminal 3: Automaker Backend
cd /Users/ruben/Documents/GitHub/automaker
npm run dev:server
# → Running on http://localhost:3008

# Terminal 4: Automaker Frontend
cd /Users/ruben/Documents/GitHub/automaker
npm run dev
# → Running on http://localhost:3007

# Open browser: http://localhost:3007/knowledge-hub
```

---

## Notes for Sub-Plan F-2

The frontend needs to know where the AI-Library API is. This will be configured via environment variable:

```bash
# In apps/ui/.env
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8001
```

---

_End of Sub-Plan F-1_
