# MCP Knowledge Server - Startup Guide

This guide explains how to start and run the MCP Knowledge Server, including all required services.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Desktop                          │
│                          │                                  │
│            Spawns via claude_desktop_config.json            │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MCP Knowledge Server                    │   │
│  │              (mcp_server.py)                        │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │ Neo4j    │  │ ChromaDB │  │ SQLite Event     │  │   │
│  │  │ Service  │  │ Service  │  │ Store            │  │   │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │   │
│  └───────┼─────────────┼─────────────────┼────────────┘   │
│          │             │                 │                 │
└──────────┼─────────────┼─────────────────┼─────────────────┘
           │             │                 │
           ▼             ▼                 ▼
    ┌──────────┐  ┌──────────────┐  ┌──────────────┐
    │  Docker  │  │ ./data/chroma│  │./data/events │
    │  Neo4j   │  │ (local dir)  │  │   .db        │
    │ Container│  └──────────────┘  └──────────────┘
    │ :7687    │
    └──────────┘
```

**Services:**
| Service | Type | Port | Storage |
|---------|------|------|---------|
| Neo4j | Docker container | 7687 (Bolt), 7474 (HTTP) | Docker volume |
| ChromaDB | File-based | N/A | `./data/chroma/` |
| Event Store | SQLite | N/A | `./data/events.db` |
| Redis | Optional (local) | 6379 | In-memory |

---

## Prerequisites

- **Docker Desktop** - For Neo4j container
- **Python 3.11+** - Server runtime
- **uv** (recommended) or pip - Package management

---

## Quick Start

### Option 1: Using Startup Script (Recommended)

```bash
./scripts/start_mcp_server.sh
```

This script automatically:

1. Starts Neo4j container if not running
2. Starts Redis container (optional, for confidence scoring)
3. Creates data directories
4. Initializes event store if first run
5. Activates virtual environment
6. Starts MCP server

### Option 2: Manual Startup

```bash
# 1. Start Neo4j
docker-compose up -d

# 2. Wait for healthy status
docker-compose ps  # Should show "healthy"

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Start MCP server
PYTHONPATH=. python mcp_server.py
```

---

## First-Time Setup

### 1. Clone and Install

```bash
git clone https://github.com/TheGuidingPrincipels/mcp-knowledge-server.git
cd mcp-knowledge-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
# OR: pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env - set Neo4j password
# Default: NEO4J_PASSWORD=password
```

### 3. Start Neo4j

```bash
docker-compose up -d
```

### 4. Initialize Databases (One-Time)

```bash
python scripts/init_database.py    # SQLite event store
python scripts/init_neo4j.py       # Neo4j schema
python scripts/init_chromadb.py    # ChromaDB collection
```

### 5. Verify Setup

```bash
# Test Neo4j connection
docker exec mcp-knowledge-neo4j cypher-shell -u neo4j -p password "RETURN 1"

# Run full startup
./scripts/start_mcp_server.sh
```

---

## Claude Desktop Integration

### Configuration

Copy or merge `claude_desktop_config.example.json` into your Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "knowledge-server": {
      "command": "/path/to/mcp-knowledge-server/.venv/bin/python",
      "args": ["/path/to/mcp-knowledge-server/mcp_server.py"],
      "cwd": "/path/to/mcp-knowledge-server",
      "env": {
        "PYTHONPATH": "/path/to/mcp-knowledge-server",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}
```

**Important:** Replace `/path/to/mcp-knowledge-server` with your actual path.

### Before Opening Claude Desktop

Neo4j must be running before Claude Desktop starts. The Docker container is configured with `restart: unless-stopped`, so after your first `docker-compose up -d`, it will automatically restart on system boot.

**Verify Neo4j is running:**

```bash
docker ps | grep neo4j
```

---

## Auto-Start Configuration

### Neo4j Auto-Starts After Boot

The `docker-compose.yml` includes `restart: unless-stopped`, which means:

- After first `docker-compose up -d`, Neo4j auto-starts on system boot
- Survives Docker Desktop restarts
- Only stops if explicitly stopped with `docker-compose down`

### Verify Auto-Start

```bash
# Restart Docker Desktop, then:
docker ps | grep mcp-knowledge-neo4j

# Should show container running
```

---

## Stopping Services

```bash
# Stop MCP server
Ctrl+C

# Stop Neo4j (will not auto-restart until next docker-compose up)
docker-compose down

# Stop Neo4j and DELETE all data (CAUTION!)
docker-compose down -v
```

---

## Troubleshooting

### Neo4j Connection Failed

**Error:** `ServiceUnavailable: Unable to connect to localhost:7687`

**Solution:**

```bash
# Check if Neo4j is running
docker ps | grep neo4j

# If not running, start it
docker-compose up -d

# Check health
docker-compose ps
```

### Neo4j Authentication Failed

**Error:** `AuthError: The client is unauthorized`

**Solution:**

```bash
# Verify password in .env matches Docker
cat .env | grep NEO4J_PASSWORD
# Should be: NEO4J_PASSWORD=password

# Verify Docker uses same password
docker exec mcp-knowledge-neo4j cypher-shell -u neo4j -p password "RETURN 1"
```

### ChromaDB Initialization Failed

**Error:** `No such file or directory: './data/chroma'`

**Solution:**

```bash
mkdir -p data/chroma data/embeddings
python scripts/init_chromadb.py
```

### Event Store Missing

**Error:** `Event store missing; initializing...`

**Solution:**

```bash
python scripts/init_database.py
```

### Python Dependencies Missing

**Error:** `ModuleNotFoundError: No module named 'fastmcp'`

**Solution:**

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Health Checks

### Check All Services

```bash
# Neo4j
docker exec mcp-knowledge-neo4j cypher-shell -u neo4j -p password "RETURN 1"

# MCP Server (when running)
# Use Claude Desktop and call any knowledge server tool

# Full system test
PYTHONPATH=. python scripts/test_all_tools.py
```

### Neo4j Browser UI

Access Neo4j's web interface at: http://localhost:7474

- Username: `neo4j`
- Password: `password`

---

## Environment Variables

| Variable                   | Default                                  | Description           |
| -------------------------- | ---------------------------------------- | --------------------- |
| `NEO4J_URI`                | `bolt://localhost:7687`                  | Neo4j connection URI  |
| `NEO4J_USER`               | `neo4j`                                  | Neo4j username        |
| `NEO4J_PASSWORD`           | `password`                               | Neo4j password        |
| `CHROMA_PERSIST_DIRECTORY` | `./data/chroma`                          | ChromaDB storage path |
| `EVENT_STORE_PATH`         | `./data/events.db`                       | SQLite database path  |
| `EMBEDDING_MODEL`          | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model       |
| `LOG_LEVEL`                | `INFO`                                   | Logging verbosity     |

---

## Related Files

- `docker-compose.yml` - Neo4j container configuration
- `.env` - Environment configuration
- `claude_desktop_config.example.json` - Claude Desktop config template
- `scripts/start_mcp_server.sh` - Full startup script
- `scripts/init_*.py` - Database initialization scripts
