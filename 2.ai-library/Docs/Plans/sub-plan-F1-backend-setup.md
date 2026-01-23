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

### Query Endpoints (`/api/query`)

| Method | Endpoint                        | Description              |
| ------ | ------------------------------- | ------------------------ |
| POST   | `/api/query/ask`                | RAG query with citations |
| POST   | `/api/query/search`             | Semantic search only     |
| GET    | `/api/query/conversations`      | List conversations       |
| GET    | `/api/query/conversations/{id}` | Get conversation         |
| DELETE | `/api/query/conversations/{id}` | Delete conversation      |

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
- [ ] WebSocket connection works for streaming
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
