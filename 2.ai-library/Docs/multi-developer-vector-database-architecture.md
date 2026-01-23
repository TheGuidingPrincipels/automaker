# Multi-Developer Vector Database Architecture

> **Version**: 1.0
> **Last Updated**: 2026-01-23
> **Status**: Planning / Implementation Guide

This document describes the architecture, workflows, and operational procedures for running the AI-Library Knowledge System with multiple developers accessing a shared vector database on a dedicated Hetzner virtual machine.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Component Details](#3-component-details)
4. [Data Flow](#4-data-flow)
5. [Local Development Workflow](#5-local-development-workflow)
6. [Production Deployment](#6-production-deployment)
7. [Migration Process](#7-migration-process)
8. [Configuration Reference](#8-configuration-reference)
9. [Operational Procedures](#9-operational-procedures)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

### 1.1 Purpose

Enable multiple developers to simultaneously access, store, and retrieve information from a shared vector database, with each developer running their own Claude Code instance while sharing the same knowledge base.

### 1.2 Key Design Decisions

| Decision               | Choice                      | Rationale                                                    |
| ---------------------- | --------------------------- | ------------------------------------------------------------ |
| **Vector Database**    | Qdrant (self-hosted Docker) | Cost-effective for large datasets, full control, low latency |
| **Data Model**         | Shared Knowledge Base       | Collaborative knowledge, all developers contribute and query |
| **Authentication**     | Per-developer OAuth tokens  | Each developer uses their own Claude subscription            |
| **Embedding Provider** | Mistral AI (shared API key) | Single API key for all embedding operations                  |
| **Deployment**         | Hetzner VM with Docker      | Dedicated infrastructure, predictable costs                  |

### 1.3 What This Enables

- Multiple developers querying the same knowledge base simultaneously
- Concurrent read/write operations without conflicts
- Shared library content that grows with team contributions
- Individual Claude Code sessions with personal OAuth tokens
- Zero data loss during development-to-production migration

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HETZNER VIRTUAL MACHINE                             │
│                                                                             │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│   │  Developer 1    │  │  Developer 2    │  │  Developer N    │            │
│   │  Claude Code    │  │  Claude Code    │  │  Claude Code    │            │
│   │  (OAuth A)      │  │  (OAuth B)      │  │  (OAuth N)      │            │
│   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
│            │                    │                    │                      │
│            └────────────────────┼────────────────────┘                      │
│                                 │                                           │
│                                 ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    AI-Library API (FastAPI)                          │  │
│   │                    0.0.0.0:8000                                       │  │
│   │                                                                       │  │
│   │   • Handles concurrent requests (async)                              │  │
│   │   • Singleton connections (thread-safe)                              │  │
│   │   • Shared MISTRAL_API_KEY for embeddings                           │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                 │                                           │
│                                 ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Qdrant Vector Database                            │  │
│   │                    localhost:6333 (Docker)                           │  │
│   │                                                                       │  │
│   │   Collection: knowledge_library                                       │  │
│   │   • Vectors: 1024 dimensions (Mistral embeddings)                    │  │
│   │   • Distance: Cosine similarity                                       │  │
│   │   • Concurrent access: Native support                                 │  │
│   │   • Persistence: Docker volume                                        │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Shared Filesystem                                 │  │
│   │                                                                       │  │
│   │   /app/library/           ← Shared knowledge (markdown files)       │  │
│   │   /app/configs/           ← Shared configuration                    │  │
│   │   /app/sessions/          ← Session storage                         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Network Architecture

```
Internet
    │
    ▼
┌───────────────────┐
│  Hetzner Firewall │
│  (UFW/iptables)   │
│                   │
│  Allowed:         │
│  • SSH (22)       │
│  • API (8000)*    │
│  • Qdrant (6333)* │
│                   │
│  * Developer IPs  │
│    only           │
└─────────┬─────────┘
          │
          ▼
┌─────────────────────────────────────┐
│         Docker Network              │
│                                     │
│  ┌───────────┐    ┌───────────┐    │
│  │  api      │◄──▶│  qdrant   │    │
│  │  :8000    │    │  :6333    │    │
│  └───────────┘    └───────────┘    │
│                                     │
└─────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 Qdrant Vector Database

**Role**: Stores and retrieves vector embeddings for semantic search.

**Configuration**:

```yaml
# Docker deployment
image: qdrant/qdrant:latest
ports:
  - '6333:6333' # REST API
  - '6334:6334' # gRPC (optional, faster)
volumes:
  - qdrant_storage:/qdrant/storage
environment:
  - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
```

**Collection Schema**:

```
Collection: knowledge_library
├── Vector Config
│   ├── Size: 1024 (Mistral) or 1536/3072 (OpenAI)
│   └── Distance: COSINE
│
├── Payload Indexes
│   ├── content_type (KEYWORD)
│   ├── taxonomy.full_path (KEYWORD)
│   ├── taxonomy.level1 (KEYWORD)
│   ├── taxonomy.level2 (KEYWORD)
│   ├── file_path (KEYWORD)
│   ├── content_hash (KEYWORD)
│   ├── classification.confidence (FLOAT)
│   ├── created_at (DATETIME)
│   └── updated_at (DATETIME)
│
└── Point Structure
    ├── id: UUID
    ├── vector: List[float] (1024 dims)
    └── payload: ContentPayload (JSON)
```

**Concurrency**: Qdrant handles concurrent read/write operations natively. No application-level locking required.

### 3.2 AI-Library API (FastAPI)

**Role**: Orchestrates queries, embeddings, and RAG operations.

**Key Components**:

| Component         | File                     | Purpose                |
| ----------------- | ------------------------ | ---------------------- |
| QueryEngine       | `src/query/engine.py`    | RAG orchestration      |
| Retriever         | `src/query/retriever.py` | Search, dedupe, rerank |
| SemanticSearch    | `src/vector/search.py`   | Vector search wrapper  |
| QdrantVectorStore | `src/vector/store.py`    | Qdrant client          |
| ClaudeCodeClient  | `src/sdk/client.py`      | Claude API integration |

**Singleton Pattern**: All database connections use thread-safe singletons with `anyio.Lock()`:

```python
async def get_vector_store(config: ConfigDep) -> QdrantVectorStore:
    global _vector_store
    if _vector_store is None:
        async with _get_vector_store_lock():
            if _vector_store is None:
                _vector_store = QdrantVectorStore(...)
                await _vector_store.initialize()
    return _vector_store
```

### 3.3 Embedding Provider (Mistral)

**Role**: Converts text to vector embeddings.

**Flow**:

```
Text Content
    │
    ▼
EmbeddingProviderFactory.create("mistral")
    │
    ▼
MistralEmbeddingProvider.embed(texts)
    │
    ▼
POST https://api.mistral.ai/v1/embeddings
Headers:
  - Authorization: Bearer {MISTRAL_API_KEY}
Body:
  {"model": "mistral-embed", "input": texts}
    │
    ▼
Response: List[List[float]] (1024 dims each)
```

**API Key Resolution** (priority order):

1. `config.api_key` (direct value in settings.yaml)
2. `config.api_key_env_var` (custom environment variable)
3. `MISTRAL_API_KEY` (default environment variable)

**Batching**: 100 texts per API call for efficiency.

### 3.4 Claude Code SDK

**Role**: Each developer's Claude Code instance for interactive queries.

**Authentication**: Individual OAuth tokens per developer.

**Integration Points**:

- Direct CLI usage: `claude` command
- API queries via QueryEngine
- RAG context provided from vector search

---

## 4. Data Flow

### 4.1 Storing Information (Indexing)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ INDEXING FLOW                                                           │
│                                                                          │
│  Markdown File (library/docs/example.md)                                │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ LibraryIndexer.index_file()                                      │   │
│  │                                                                   │   │
│  │  1. Read file content                                            │   │
│  │  2. Calculate MD5 checksum (skip if unchanged)                   │   │
│  │  3. Extract chunks at section headers/paragraphs                 │   │
│  │  4. Generate UUIDs for each chunk                                │   │
│  │  5. Remove old vectors for this file                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ QdrantVectorStore.add_contents_batch()                           │   │
│  │                                                                   │   │
│  │  For each batch of 100 chunks:                                   │   │
│  │    1. Extract text content                                       │   │
│  │    2. Call Mistral API for embeddings                           │   │
│  │    3. Create PointStruct with vector + payload                  │   │
│  │    4. Upsert to Qdrant collection                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│       ▼                                                                  │
│  Qdrant: knowledge_library collection updated                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Retrieving Information (RAG Query)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ RAG QUERY FLOW                                                          │
│                                                                          │
│  User Question: "How do I implement authentication?"                    │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [1] RETRIEVE                                                     │   │
│  │                                                                   │   │
│  │  a) Embed question via Mistral API                              │   │
│  │     → Vector: [0.123, 0.456, ..., 0.789] (1024 dims)           │   │
│  │                                                                   │   │
│  │  b) Search Qdrant (cosine similarity)                           │   │
│  │     → Top 10 matching chunks with scores                        │   │
│  │                                                                   │   │
│  │  c) Deduplicate by MD5 fingerprint                              │   │
│  │                                                                   │   │
│  │  d) Re-rank using composite score:                              │   │
│  │     score = similarity + length_bonus + section_bonus + terms   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [2] AUGMENT                                                      │   │
│  │                                                                   │   │
│  │  Format context for LLM:                                         │   │
│  │  ───────────────────────                                         │   │
│  │  [1] Source: docs/api.md (Section: Authentication)              │   │
│  │  Learn how to authenticate using OAuth tokens...                 │   │
│  │                                                                   │   │
│  │  ---                                                             │   │
│  │                                                                   │   │
│  │  [2] Source: docs/security.md (Section: JWT)                    │   │
│  │  JWT (JSON Web Tokens) provide...                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [3] GENERATE                                                     │   │
│  │                                                                   │   │
│  │  System Prompt: OUTPUT_SYSTEM_PROMPT                            │   │
│  │  • Use ONLY provided context                                     │   │
│  │  • Cite sources as [source: path/to/file.md]                    │   │
│  │  • Be honest about gaps                                          │   │
│  │                                                                   │   │
│  │  User Prompt:                                                    │   │
│  │  • Conversation history (last 5 turns)                          │   │
│  │  • Formatted library context                                     │   │
│  │  • Current question                                              │   │
│  │                                                                   │   │
│  │  → Claude generates answer with citations                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [4] RESPOND                                                      │   │
│  │                                                                   │   │
│  │  Extract [source: file.md] citations                            │   │
│  │  Calculate confidence (similarity × 0.7 + diversity × 0.2 +     │   │
│  │                        coverage × 0.1)                          │   │
│  │  Save conversation turn                                          │   │
│  │                                                                   │   │
│  │  → {answer, sources, confidence, conversation_id}               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Concurrent Access Pattern

```
Time ──────────────────────────────────────────────────────────────────────▶

Developer A        Developer B        Developer C        Qdrant
    │                  │                  │                │
    │── Query ────────────────────────────────────────────▶│
    │                  │                  │                │
    │                  │── Index file ───────────────────▶│
    │                  │                  │                │ (handled
    │                  │                  │── Query ──────▶│  concurrently)
    │                  │                  │                │
    │◀─ Results ───────────────────────────────────────────│
    │                  │                  │                │
    │                  │◀─ Index OK ───────────────────────│
    │                  │                  │                │
    │                  │                  │◀─ Results ─────│
    │                  │                  │                │

All operations execute concurrently without blocking each other.
Qdrant and AsyncQdrantClient handle thread safety internally.
```

---

## 5. Local Development Workflow

### 5.1 Initial Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd AI-Libary-Hub/AI-Library

# 2. Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Start Qdrant locally
docker run -d -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant

# 5. Set environment variables
export MISTRAL_API_KEY=your-mistral-api-key
export ANTHROPIC_AUTH_TOKEN=your-claude-oauth-token

# 6. Verify Qdrant is running
curl http://localhost:6333/collections
# Expected: {"result":{"collections":[]},"status":"ok","time":0.000123}

# 7. Index your library
python -m src.cli index --all

# 8. Start the API server
uvicorn src.api.main:app --reload --port 8000
```

### 5.2 Daily Development

```bash
# Start services (if not running)
docker start qdrant  # Or docker run if first time

# Start API
uvicorn src.api.main:app --reload --port 8000

# Use Claude Code
claude  # Interactive mode

# Test queries
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I implement authentication?"}'
```

### 5.3 Adding Content to Library

```bash
# 1. Add markdown file to library
cp my-document.md library/docs/

# 2. Re-index (incremental - only new/changed files)
python -m src.cli index --all

# 3. Verify indexing
curl http://localhost:6333/collections/knowledge_library
# Check "points_count" increased
```

---

## 6. Production Deployment

### 6.1 Hetzner VM Setup

```bash
# 1. Create Hetzner Cloud VM (recommended specs)
#    - CPX21 or higher (4 vCPU, 8GB RAM)
#    - Ubuntu 22.04 LTS
#    - 80GB+ SSD (depending on data size)

# 2. SSH into server
ssh root@your-hetzner-ip

# 3. Update system
apt update && apt upgrade -y

# 4. Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker

# 5. Install Docker Compose
apt install docker-compose-plugin

# 6. Create application directory
mkdir -p /app
cd /app

# 7. Clone repository
git clone <repository-url> .
cd AI-Library
```

### 6.2 Docker Compose Configuration

Create `/app/docker-compose.yml`:

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - '127.0.0.1:6333:6333' # Only local access
      - '127.0.0.1:6334:6334' # gRPC
    volumes:
      - qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:6333/healthz']
      interval: 30s
      timeout: 10s
      retries: 3

  api:
    build:
      context: ./AI-Library
      dockerfile: Dockerfile
    container_name: ai-library-api
    restart: unless-stopped
    ports:
      - '0.0.0.0:8000:8000'
    environment:
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - QDRANT_URL=qdrant
      - QDRANT_PORT=6333
      - QDRANT_API_KEY=${QDRANT_API_KEY}
    depends_on:
      qdrant:
        condition: service_healthy
    volumes:
      - ./AI-Library/library:/app/library
      - ./AI-Library/sessions:/app/sessions
      - ./AI-Library/configs:/app/configs
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:8000/health']
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  qdrant_storage:
    driver: local
```

### 6.3 Environment Configuration

Create `/app/.env`:

```bash
# Qdrant authentication (generate secure random key)
QDRANT_API_KEY=your-secure-random-api-key-here

# Mistral embedding API (shared across all developers)
MISTRAL_API_KEY=your-mistral-api-key

# Optional: API configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### 6.4 Production Settings

Update `/app/AI-Library/configs/settings.yaml`:

```yaml
# Vector store - production configuration
vector:
  url: ${QDRANT_URL:-qdrant}
  port: ${QDRANT_PORT:-6333}
  api_key: ${QDRANT_API_KEY:-}
  collection_name: knowledge_library

# API - bind to all interfaces
api:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - http://localhost:3000
    - http://localhost:5173
    - https://your-domain.com
  debug: false

# Embeddings
embeddings:
  provider: mistral
  model: mistral-embed
```

### 6.5 Firewall Configuration

```bash
# Install UFW
apt install ufw

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH
ufw allow ssh

# Allow API access from specific IPs (developers)
ufw allow from <developer1-ip> to any port 8000
ufw allow from <developer2-ip> to any port 8000
# ... add more developers

# Optional: Allow Qdrant direct access (if needed)
# ufw allow from <developer1-ip> to any port 6333

# Enable firewall
ufw enable
```

### 6.6 Start Production Services

```bash
# Start all services
docker compose up -d

# Verify services
docker compose ps
docker compose logs -f

# Index library (first time)
docker compose exec api python -m src.cli index --all
```

---

## 7. Migration Process

### 7.1 Data Inventory

Before migration, identify what needs to be transferred:

| Data              | Location                | Required     | Notes                 |
| ----------------- | ----------------------- | ------------ | --------------------- |
| Library content   | `library/**/*.md`       | **YES**      | Source of truth       |
| Settings          | `configs/settings.yaml` | **YES**      | Update for production |
| Taxonomy          | `configs/taxonomy.yaml` | **YES**      | Category definitions  |
| Vector embeddings | Qdrant                  | **OPTIONAL** | Can regenerate        |
| Sessions          | `sessions/*.json`       | **OPTIONAL** | Only if needed        |
| Centroids cache   | `data/centroids/`       | **NO**       | Auto-regenerated      |

### 7.2 Migration Options

#### Option A: Regenerate Vectors (Recommended for First Migration)

```bash
# On production server

# 1. Copy library and configs
scp -r library/ root@production:/app/AI-Library/
scp -r configs/ root@production:/app/AI-Library/

# 2. Start services
docker compose up -d

# 3. Index library (regenerate all vectors)
docker compose exec api python -m src.cli index --all

# Result: Fresh vectors generated from markdown source
```

**Advantages**:

- Simple and reliable
- No snapshot compatibility concerns
- Vectors optimized for production Qdrant version

**Disadvantages**:

- Uses Mistral API quota for re-embedding
- Takes longer for large libraries

#### Option B: Snapshot Migration (Faster for Large Libraries)

```bash
# On LOCAL machine

# 1. Create snapshot
python -c "
from qdrant_client import QdrantClient
client = QdrantClient('localhost', port=6333)
snapshot = client.create_snapshot('knowledge_library')
print(f'Created: {snapshot.name}')
"

# 2. Download snapshot
curl -o snapshot.snapshot \
  "http://localhost:6333/collections/knowledge_library/snapshots/{snapshot_name}"

# 3. Transfer to production
scp snapshot.snapshot root@production:/tmp/

# On PRODUCTION server

# 4. Recover from snapshot
python -c "
from qdrant_client import QdrantClient
client = QdrantClient('localhost', port=6333, api_key='your-key')
client.recover_from_snapshot(
    collection_name='knowledge_library',
    location='file:///tmp/snapshot.snapshot'
)
print('Recovery complete')
"
```

#### Option C: Direct Migration (If Network Accessible)

```python
# migration_script.py
from qdrant_client import QdrantClient
from qdrant_client.migrate import migrate

local_client = QdrantClient("localhost", port=6333)
prod_client = QdrantClient(
    "production-host",
    port=6333,
    api_key="production-api-key"
)

migrate(
    source_client=local_client,
    dest_client=prod_client,
    collection_names=["knowledge_library"],
    recreate_on_collision=True,
    batch_size=100
)

print("Migration complete!")
```

### 7.3 Verification Checklist

After migration, verify:

```bash
# 1. Check collection exists
curl http://localhost:6333/collections/knowledge_library

# 2. Verify point count
curl http://localhost:6333/collections/knowledge_library | jq '.result.points_count'

# 3. Test search
curl -X POST http://localhost:8000/api/query/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "n_results": 5}'

# 4. Test full RAG
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What topics are in the library?"}'
```

---

## 8. Configuration Reference

### 8.1 Environment Variables

| Variable               | Required | Default     | Description                          |
| ---------------------- | -------- | ----------- | ------------------------------------ |
| `MISTRAL_API_KEY`      | Yes      | -           | Mistral AI API key for embeddings    |
| `QDRANT_URL`           | No       | `localhost` | Qdrant server URL                    |
| `QDRANT_PORT`          | No       | `6333`      | Qdrant server port                   |
| `QDRANT_API_KEY`       | No       | -           | Qdrant authentication key            |
| `ANTHROPIC_AUTH_TOKEN` | Yes\*    | -           | Claude OAuth token (\*per developer) |
| `API_HOST`             | No       | `127.0.0.1` | API bind address                     |
| `API_PORT`             | No       | `8000`      | API port                             |

### 8.2 Settings File (settings.yaml)

```yaml
# Library settings
library:
  path: ./library
  index_file: _index.yaml

# Session settings
sessions:
  path: ./sessions
  auto_save: true

# SDK settings (Claude)
sdk:
  model: claude-opus-4-5-20251101
  max_turns: 6
  auth_token_env_var: ANTHROPIC_AUTH_TOKEN

# Vector store
vector:
  url: ${QDRANT_URL:-localhost}
  port: ${QDRANT_PORT:-6333}
  api_key: ${QDRANT_API_KEY:-}
  collection_name: knowledge_library

# Embeddings
embeddings:
  provider: mistral
  model: mistral-embed

# Chunking
chunking:
  min_tokens: 512
  max_tokens: 2048
  overlap_tokens: 128
  strategy: semantic

# API
api:
  host: ${API_HOST:-127.0.0.1}
  port: ${API_PORT:-8000}
  cors_origins:
    - http://localhost:3000
    - http://localhost:5173
  debug: false
```

---

## 9. Operational Procedures

### 9.1 Adding a New Developer

```bash
# 1. Get developer's public SSH key
# 2. Add to authorized_keys
echo "ssh-rsa AAAA... developer@email" >> ~/.ssh/authorized_keys

# 3. Add IP to firewall
ufw allow from <developer-ip> to any port 8000

# 4. Developer sets up their environment
export ANTHROPIC_AUTH_TOKEN=their-personal-token
# Note: Mistral key is shared via the API server
```

### 9.2 Updating Library Content

```bash
# 1. Add/modify markdown files in library/
# 2. Commit and push changes
git add library/
git commit -m "Add new documentation"
git push

# 3. On server: pull and re-index
git pull
docker compose exec api python -m src.cli index --all
```

### 9.3 Backup Procedures

```bash
# Daily backup script (/app/backup.sh)
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/backups

# 1. Backup library (source of truth)
tar -czf $BACKUP_DIR/library-$DATE.tar.gz library/

# 2. Backup Qdrant snapshot
docker compose exec -T qdrant curl -X POST \
  "http://localhost:6333/collections/knowledge_library/snapshots"

# 3. Copy latest snapshot
SNAPSHOT=$(docker compose exec -T qdrant curl -s \
  "http://localhost:6333/collections/knowledge_library/snapshots" \
  | jq -r '.result[-1].name')
docker compose exec -T qdrant cat "/qdrant/snapshots/$SNAPSHOT" \
  > $BACKUP_DIR/qdrant-$DATE.snapshot

# 4. Backup configs
tar -czf $BACKUP_DIR/configs-$DATE.tar.gz configs/

# 5. Clean old backups (keep 7 days)
find $BACKUP_DIR -mtime +7 -delete

echo "Backup completed: $DATE"
```

### 9.4 Monitoring

```bash
# Check service health
docker compose ps
docker compose logs --tail=100

# Check Qdrant status
curl http://localhost:6333/collections/knowledge_library | jq

# Check API health
curl http://localhost:8000/health

# Monitor resource usage
docker stats
```

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Qdrant Connection Failed

```
Error: Vector store unavailable: Connection refused
```

**Solution**:

```bash
# Check Qdrant is running
docker ps | grep qdrant

# Start if not running
docker compose up -d qdrant

# Check logs
docker compose logs qdrant
```

#### Embedding API Error

```
Error: Mistral API key not found
```

**Solution**:

```bash
# Verify environment variable
echo $MISTRAL_API_KEY

# Set if missing
export MISTRAL_API_KEY=your-key

# Restart API
docker compose restart api
```

#### Out of Memory

```
Error: Qdrant killed (OOM)
```

**Solution**:

```yaml
# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G # Increase from 4G
```

### 10.2 Performance Tuning

```yaml
# For large libraries (>100k chunks)
vector:
  # Use gRPC for faster operations
  prefer_grpc: true

# For high concurrency
api:
  workers: 4 # Match CPU cores
```

### 10.3 Recovery Procedures

#### Restore from Backup

```bash
# 1. Stop services
docker compose down

# 2. Restore library
tar -xzf /backups/library-20260123.tar.gz -C /app/

# 3. Start Qdrant only
docker compose up -d qdrant

# 4. Recover from snapshot
docker compose exec qdrant curl -X POST \
  "http://localhost:6333/collections/knowledge_library/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d '{"location": "file:///qdrant/snapshots/snapshot-name"}'

# 5. Start remaining services
docker compose up -d
```

---

## Appendix A: File Structure

```
/app/
├── docker-compose.yml
├── .env
│
└── AI-Library/
    ├── Dockerfile
    ├── pyproject.toml
    │
    ├── configs/
    │   ├── settings.yaml
    │   └── taxonomy.yaml
    │
    ├── library/                  # Source of truth
    │   ├── _index.yaml
    │   ├── docs/
    │   │   └── *.md
    │   └── guides/
    │       └── *.md
    │
    ├── sessions/
    │   └── conversations/
    │
    ├── src/
    │   ├── api/
    │   ├── query/
    │   ├── vector/
    │   └── sdk/
    │
    └── data/
        └── centroids/
```

---

## Appendix B: API Endpoints

| Endpoint             | Method | Description           |
| -------------------- | ------ | --------------------- |
| `/api/query/ask`     | POST   | RAG-based Q&A         |
| `/api/query/search`  | POST   | Semantic search       |
| `/api/query/similar` | POST   | Find similar content  |
| `/api/library/index` | POST   | Trigger indexing      |
| `/api/library/stats` | GET    | Collection statistics |
| `/health`            | GET    | Health check          |

---

## Appendix C: Glossary

| Term            | Definition                                                            |
| --------------- | --------------------------------------------------------------------- |
| **Embedding**   | A vector representation of text (1024 dimensions for Mistral)         |
| **RAG**         | Retrieval-Augmented Generation - combining search with LLM generation |
| **Chunk**       | A segment of content extracted from a markdown file                   |
| **Collection**  | A Qdrant container for vectors (like a database table)                |
| **Payload**     | Metadata stored alongside vectors in Qdrant                           |
| **OAuth Token** | Personal authentication credential for Claude Code                    |
