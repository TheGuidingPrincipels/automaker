# System Architecture Documentation

# Complete Architecture Reference

**Version:** 1.0
**Status:** Production Ready
**Last Updated:** 2025-10-27

---

## Table of Contents

1. [Overview](#overview)
2. [Architectural Patterns](#architectural-patterns)
3. [System Components](#system-components)
4. [Data Flow](#data-flow)
5. [Service Layer](#service-layer)
6. [Projection Layer](#projection-layer)
7. [Error Handling & Recovery](#error-handling--recovery)
8. [Deployment Architecture](#deployment-architecture)

---

## Overview

The MCP Knowledge Management Server employs a sophisticated **event-sourced architecture** with **CQRS (Command Query Responsibility Segregation)** to achieve:

- **Strong Consistency:** Event store as single source of truth
- **Eventual Consistency:** Read models (Neo4j, ChromaDB) updated asynchronously
- **Complete Audit Trail:** Every state change captured as immutable event
- **Scalability:** Separate read/write paths for independent optimization
- **Reliability:** Outbox pattern ensures guaranteed delivery

### Core Principles

1. **Event Sourcing:** All writes create immutable events
2. **CQRS:** Separate models for commands (writes) and queries (reads)
3. **Dual Storage:** Graph database (Neo4j) + Vector database (ChromaDB)
4. **Outbox Pattern:** Reliable async event publishing
5. **Saga Pattern:** Automatic compensation on failures

---

## Architectural Patterns

### 1. Event Sourcing

**Purpose:** Capture all state changes as immutable events

```
Operation (Create Concept)
    ↓
ConceptCreated Event
    ↓
Event Store (append-only log)
    ↓
Projections (build read models)
```

**Benefits:**

- Complete audit trail
- Time-travel capabilities (reconstruct state at any point)
- Event replay for debugging
- Natural audit log for compliance

**Implementation:** `services/event_store.py`, `models/events.py`

---

### 2. CQRS (Command Query Responsibility Segregation)

**Write Side (Commands):**

```
MCP Tool (create_concept)
    ↓
DualStorageRepository
    ↓
Event Store (SQLite)
    ↓
Outbox Entries
```

**Read Side (Queries):**

```
MCP Tool (search_concepts_semantic)
    ↓
ChromaDB Service (direct query)
    ↓
Return results
```

**Key Insight:** Writes go through event store, reads go directly to optimized read models.

**Source:** `services/repository.py`

---

### 3. Outbox Pattern

**Purpose:** Reliable event publishing to projections

```
1. Event written to event store (ACID)
2. Outbox entries created (same transaction)
3. Background processor reads outbox
4. Projects events to Neo4j/ChromaDB
5. Marks outbox entries as processed
```

**Guarantees:**

- At-least-once delivery
- No lost events
- Automatic retry on failure

**Implementation:** `services/outbox.py`

---

### 4. Saga Pattern (Compensation)

**Purpose:** Automatic rollback on projection failures

```
Create Concept
    ↓
Event Store ✓
    ↓
Neo4j Projection ✓
    ↓
ChromaDB Projection ✗ (FAILED)
    ↓
Compensation: Delete from Neo4j
    ↓
Mark operation as failed
```

**Implementation:** `services/compensation.py`

---

## System Components

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Client (Claude)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ Model Context Protocol
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    FastMCP Server Layer                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  16 MCP Tools (concept_tools, search_tools, etc.)   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ DualStorageRepository (orchestration)                 │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ EventStore │ Outbox │ EmbeddingService │ Cache        │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            ↓                         ↓
┌──────────────────────┐  ┌──────────────────────┐
│  Projection Layer    │  │  Projection Layer    │
│  ┌────────────────┐  │  │  ┌────────────────┐  │
│  │ Neo4jProjection│  │  │  │ChromaDBProjectn│  │
│  └────────────────┘  │  │  └────────────────┘  │
└──────────┬───────────┘  └──────────┬───────────┘
           │                         │
           ↓                         ↓
┌──────────────────────┐  ┌──────────────────────┐
│   Neo4j Database     │  │  ChromaDB Collection │
│   (Graph Storage)    │  │  (Vector Storage)    │
└──────────────────────┘  └──────────────────────┘
```

---

### Component Responsibilities

| Component                 | Responsibility                             | File Location                        |
| ------------------------- | ------------------------------------------ | ------------------------------------ |
| **FastMCP Server**        | MCP protocol handling, tool registration   | `mcp_server.py`                      |
| **Tool Modules**          | Input validation, MCP tool implementations | `tools/*.py`                         |
| **DualStorageRepository** | Orchestrate writes to both storage systems | `services/repository.py`             |
| **EventStore**            | Persist events, event retrieval            | `services/event_store.py`            |
| **Outbox**                | Reliable event publishing queue            | `services/outbox.py`                 |
| **EmbeddingService**      | Generate concept embeddings                | `services/embedding_service.py`      |
| **EmbeddingCache**        | Cache embeddings for performance           | `services/embedding_cache.py`        |
| **Neo4jService**          | Neo4j connection, query execution          | `services/neo4j_service.py`          |
| **ChromaDbService**       | ChromaDB connection, vector operations     | `services/chromadb_service.py`       |
| **Neo4jProjection**       | Project events to graph database           | `projections/neo4j_projection.py`    |
| **ChromaDBProjection**    | Project events to vector database          | `projections/chromadb_projection.py` |
| **CompensationManager**   | Rollback on failures                       | `services/compensation.py`           |
| **ConsistencyChecker**    | Validate dual storage consistency          | `services/consistency_checker.py`    |

---

## Data Flow

### Write Operation (Create Concept)

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: MCP Tool Invocation                                 │
└─────────────────────────────────────────────────────────────┘
  create_concept(name="Python For Loops", explanation="...")
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Input Validation (Pydantic)                         │
└─────────────────────────────────────────────────────────────┘
  ConceptCreate.model_validate(...)
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Repository Orchestration                            │
└─────────────────────────────────────────────────────────────┘
  repository.create_concept(concept_data)
      │
      ├─> Generate concept_id (UUID)
      ├─> Generate embedding (384-dim vector)
      └─> Check embedding cache first
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Event Creation                                      │
└─────────────────────────────────────────────────────────────┘
  event = ConceptCreated(
      aggregate_id=concept_id,
      event_data={name, explanation, area, ...},
      version=1
  )
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Event Store Persistence (SQLite ACID)               │
└─────────────────────────────────────────────────────────────┘
  event_store.append_event(event)
      │
      └─> INSERT INTO events (event_id, event_type, ...)
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Outbox Entries                                      │
└─────────────────────────────────────────────────────────────┘
  outbox.add_to_outbox(event_id, "neo4j")
  outbox.add_to_outbox(event_id, "chromadb")
      │
      └─> INSERT INTO outbox (outbox_id, event_id, projection_name, status="pending")
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Neo4j Projection                                    │
└─────────────────────────────────────────────────────────────┘
  neo4j_projection.project_event(event)
      │
      ├─> CREATE (c:Concept {...})
      ├─> CREATE (a:Area {...}) IF NOT EXISTS
      ├─> CREATE (t:Topic {...}) IF NOT EXISTS
      └─> CREATE (c)-[:BELONGS_TO]->(a), (c)-[:BELONGS_TO]->(t)
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: ChromaDB Projection                                 │
└─────────────────────────────────────────────────────────────┘
  chromadb_projection.project_event(event)
      │
      └─> collection.add(
              ids=[concept_id],
              embeddings=[embedding],
              metadatas=[{name, area, topic, ...}],
              documents=[explanation]
          )
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 9: Mark Outbox Processed                               │
└─────────────────────────────────────────────────────────────┘
  outbox.mark_processed(outbox_id_neo4j)
  outbox.mark_processed(outbox_id_chromadb)
      │
      └─> UPDATE outbox SET status="processed"
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 10: Return Success                                     │
└─────────────────────────────────────────────────────────────┘
  return {"success": True, "concept_id": concept_id}
```

**Source:** `services/repository.py:129-220`

---

### Read Operation (Semantic Search)

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: MCP Tool Invocation                                 │
└─────────────────────────────────────────────────────────────┘
  search_concepts_semantic(query="python loops", limit=10)
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Generate Query Embedding                            │
└─────────────────────────────────────────────────────────────┘
  embedding_service.generate_embedding(query)
      │
      ├─> Check embedding_cache (SQLite)
      └─> If not cached: sentence_transformers encode
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Vector Similarity Search                            │
└─────────────────────────────────────────────────────────────┘
  collection.query(
      query_embeddings=[query_embedding],
      n_results=10,
      include=["metadatas", "distances"]
  )
      │
      └─> HNSW index search (cosine similarity)
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Format Results                                      │
└─────────────────────────────────────────────────────────────┘
  results = [{
      concept_id, name, similarity,
      area, topic, certainty_score
  }, ...]
            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Return Results                                      │
└─────────────────────────────────────────────────────────────┘
  return {"success": True, "results": results, "total": len(results)}
```

**Key Insight:** Reads bypass the event store entirely for performance.

**Source:** `tools/search_tools.py:30-177`

---

## Service Layer

### DualStorageRepository

**Purpose:** Orchestrate writes to both Neo4j and ChromaDB

```python
class DualStorageRepository:
    def __init__(
        self,
        event_store: EventStore,
        outbox: Outbox,
        neo4j_projection: Neo4jProjection,
        chromadb_projection: ChromaDBProjection,
        embedding_service: EmbeddingService,
        embedding_cache: Optional[EmbeddingCache],
        compensation_manager: Optional[CompensationManager]
    ):
        ...
```

**Key Methods:**

- `create_concept(concept_data) → (success, error, concept_id)`
- `update_concept(concept_id, updates) → (success, error, concept_id)`
- `delete_concept(concept_id) → (success, error)`
- `get_concept(concept_id) → concept_dict`

**Source:** `services/repository.py:45-88`

---

### EventStore

**Purpose:** Append-only event log with ACID guarantees

```python
class EventStore:
    def append_event(self, event: Event) -> bool
    def get_events_by_aggregate(self, aggregate_id: str) → List[Event]
    def get_events_by_type(self, event_type: str) → List[Event]
    def count_events(self, event_type: Optional[str] = None) → int
```

**Transaction Safety:**

```python
with connection:  # Automatic transaction
    cursor.execute("INSERT INTO events ...")
    connection.commit()
```

**Source:** `services/event_store.py`

---

### EmbeddingService

**Purpose:** Generate concept embeddings for semantic search

```python
class EmbeddingService:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimensions: int = 384

    def generate_embedding(self, text: str) → List[float]:
        ...

    def batch_generate_embeddings(self, texts: List[str]) → List[List[float]]:
        ...
```

**Caching Strategy:**

```python
text_hash = hashlib.sha256(text.encode()).hexdigest()
cached = embedding_cache.get(text_hash, model_name)
if cached:
    return cached
else:
    embedding = model.encode(text)
    embedding_cache.set(text_hash, model_name, embedding)
    return embedding
```

**Source:** `services/embedding_service.py:82-153`

---

## Projection Layer

### Neo4jProjection

**Purpose:** Transform events into graph nodes and relationships

```python
class Neo4jProjection(BaseProjection):
    def project_event(self, event: Event) → bool:
        handler_map = {
            "ConceptCreated": self._handle_concept_created,
            "ConceptUpdated": self._handle_concept_updated,
            "ConceptDeleted": self._handle_concept_deleted,
            "RelationshipCreated": self._handle_relationship_created,
            "RelationshipDeleted": self._handle_relationship_deleted,
        }
        handler = handler_map.get(event.event_type)
        return handler(event)
```

**Event Handlers:**

- `_handle_concept_created`: Create Concept, Area, Topic nodes + BELONGS_TO edges
- `_handle_concept_updated`: Update Concept properties
- `_handle_concept_deleted`: Set `deleted=true` flag
- `_handle_relationship_created`: Create typed relationship edge
- `_handle_relationship_deleted`: Delete relationship edge

**Source:** `projections/neo4j_projection.py:43-87`

---

### ChromaDBProjection

**Purpose:** Transform events into vector embeddings

```python
class ChromaDBProjection(BaseProjection):
    def project_event(self, event: Event) → bool:
        handler_map = {
            "ConceptCreated": self._handle_concept_created,
            "ConceptUpdated": self._handle_concept_updated,
            "ConceptDeleted": self._handle_concept_deleted,
        }
        handler = handler_map.get(event.event_type)
        return handler(event)
```

**Event Handlers:**

- `_handle_concept_created`: Add vector to collection
- `_handle_concept_updated`: Update vector if explanation changed
- `_handle_concept_deleted`: Remove vector from collection

**Note:** Relationship events do NOT affect ChromaDB (relationships not stored in vectors).

**Source:** `projections/chromadb_projection.py:41-91`

---

## Error Handling & Recovery

### 3-Layer Defense Strategy

```
Layer 1: Input Validation (Pydantic)
    ↓ (validation_error)
Layer 2: Business Logic Validation
    ↓ (concept_not_found, invalid_input)
Layer 3: Database Error Handling
    ↓ (database_error, internal_error)
```

**Source:** `tools/responses.py`

---

### Projection Failure Handling

**Scenario:** Neo4j succeeds, ChromaDB fails

```
1. Event written to event store ✓
2. Neo4j projection succeeds ✓
3. ChromaDB projection fails ✗
   │
   ├─> Outbox entry remains "pending"
   ├─> Automatic retry (max 3 attempts)
   │
   ├─> If all retries fail:
   │   └─> Compensation: Delete from Neo4j
   │
   └─> Mark outbox as "failed"
```

**Recovery:**

```bash
# Manual replay from event store
python scripts/replay_events.py --from-date="2025-10-27"
```

---

### Consistency Checking

**Purpose:** Detect and report discrepancies between Neo4j and ChromaDB

```python
checker = ConsistencyChecker(neo4j_service, chromadb_service, event_store)
report = checker.check_consistency()

if report["status"] == "inconsistent":
    # report["discrepancies"] contains details
    # - Missing in Neo4j but in ChromaDB
    # - Missing in ChromaDB but in Neo4j
    # - Metadata mismatches
```

**Source:** `services/consistency_checker.py`

---

## Deployment Architecture

### Single-Node Deployment (Production)

```
┌────────────────────────────────────────────────────────────┐
│                     Host Machine                           │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  MCP Server Process (Python 3.11)                   │ │
│  │  - FastMCP                                           │ │
│  │  - Tool modules                                      │ │
│  │  - Service layer                                     │ │
│  │  Port: stdio (MCP protocol)                         │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  SQLite Database (data/events.db)                   │ │
│  │  - Event store                                       │ │
│  │  - Outbox                                            │ │
│  │  - Embedding cache                                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Neo4j (Docker Container)                           │ │
│  │  - Port: 7687 (bolt)                                │ │
│  │  - Port: 7474 (HTTP)                                │ │
│  │  - Volume: ./data/neo4j                             │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  ChromaDB (Embedded)                                │ │
│  │  - Persist directory: data/chroma/                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Sentence-Transformers (Local)                      │ │
│  │  - Model: all-MiniLM-L6-v2                          │ │
│  │  - Cache: ~/.cache/huggingface/                     │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

---

### Resource Requirements

| Component  | CPU         | Memory  | Disk     | Notes           |
| ---------- | ----------- | ------- | -------- | --------------- |
| MCP Server | 1 core      | 500MB   | -        | Python process  |
| Neo4j      | 2 cores     | 2GB     | 1GB+     | Graph database  |
| ChromaDB   | 1 core      | 1GB     | 500MB+   | Vector database |
| Embeddings | 2 cores     | 2GB     | 500MB    | Model loading   |
| **Total**  | **4 cores** | **4GB** | **2GB+** | Minimum         |

**Recommended:** 4 cores, 8GB RAM, 10GB disk

---

### Configuration

**Environment Variables** (`.env`):

```bash
# Server
MCP_SERVER_NAME=knowledge-server
LOG_LEVEL=INFO

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure-password>

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./data/chroma

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_CACHE_DIR=./data/embeddings

# Event Store
EVENT_STORE_PATH=./data/events.db

# Performance
MAX_BATCH_SIZE=50
CACHE_TTL_SECONDS=300
```

**Source:** `config.py`

---

### Startup Sequence

```
1. Load environment variables (.env)
2. Initialize event store (SQLite)
3. Initialize outbox (SQLite)
4. Connect to Neo4j (with retry)
5. Connect to ChromaDB
6. Load embedding model (sentence-transformers)
7. Initialize embedding cache
8. Initialize projections
9. Initialize repository
10. Register MCP tools
11. Start FastMCP server
```

**Source:** `mcp_server.py:43-211`

---

## Performance Characteristics

### Write Operations

| Operation           | P50   | P95   | P99   | Notes                               |
| ------------------- | ----- | ----- | ----- | ----------------------------------- |
| create_concept      | 100ms | 250ms | 500ms | Includes embedding generation       |
| update_concept      | 80ms  | 200ms | 400ms | Re-embedding if explanation changed |
| delete_concept      | 50ms  | 100ms | 200ms | Soft delete (flag update)           |
| create_relationship | 30ms  | 80ms  | 150ms | Graph edge creation                 |

### Read Operations

| Operation         | P50   | P95   | P99   | Notes                     |
| ----------------- | ----- | ----- | ----- | ------------------------- |
| get_concept       | 10ms  | 30ms  | 60ms  | Neo4j lookup              |
| search_semantic   | 150ms | 400ms | 800ms | ChromaDB HNSW search      |
| search_exact      | 20ms  | 60ms  | 120ms | Neo4j Cypher query        |
| get_prerequisites | 50ms  | 150ms | 300ms | Graph traversal (depth 3) |

**Benchmark Source:** `docs/TOOL_API_REFERENCE.md:138-150`

---

**Document Version:** 1.0
**Generated:** 2025-10-27
**Evidence Base:** Complete codebase analysis (services/, projections/, mcp_server.py)
