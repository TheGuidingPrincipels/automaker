# Database Schema Documentation

# Complete Schema Reference for All Storage Systems

**Version:** 1.0
**Status:** Production Ready
**Last Updated:** 2025-10-27

---

## Table of Contents

1. [Overview](#overview)
2. [SQLite Event Store](#sqlite-event-store)
3. [Neo4j Graph Database](#neo4j-graph-database)
4. [ChromaDB Vector Store](#chromadb-vector-store)
5. [Schema Relationships](#schema-relationships)

---

## Overview

The MCP Knowledge Server uses a **tri-storage architecture** for different data concerns:

| Database     | Purpose                        | Technology | Persistence                             |
| ------------ | ------------------------------ | ---------- | --------------------------------------- |
| **SQLite**   | Event sourcing, audit trail    | Relational | File-based (`data/events.db`)           |
| **Neo4j**    | Graph relationships, hierarchy | Graph      | Network service (bolt://localhost:7687) |
| **ChromaDB** | Semantic search, embeddings    | Vector     | Directory (`data/chroma/`)              |

### Data Flow

```
Write Operation
├─> SQLite Event Store (source of truth)
├─> Outbox (reliable delivery)
└─> Projections
    ├─> Neo4j (graph structure)
    └─> ChromaDB (vector embeddings)
```

---

## SQLite Event Store

**Database File:** `data/events.db`
**Purpose:** Event sourcing system with CQRS pattern
**Initialization:** `scripts/init_database.py`

### Table 1: events

**Purpose:** Immutable event log (append-only)

```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    event_data TEXT NOT NULL,        -- JSON serialized
    metadata TEXT,                    -- JSON serialized
    version INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Fields

| Field            | Type     | Constraints | Description                                                          |
| ---------------- | -------- | ----------- | -------------------------------------------------------------------- |
| `event_id`       | TEXT     | PRIMARY KEY | UUID, globally unique event identifier                               |
| `event_type`     | TEXT     | NOT NULL    | Event class name (ConceptCreated, ConceptUpdated, etc.)              |
| `aggregate_id`   | TEXT     | NOT NULL    | ID of the entity this event applies to (concept_id, relationship_id) |
| `aggregate_type` | TEXT     | NOT NULL    | Entity type (Concept, Relationship)                                  |
| `event_data`     | TEXT     | NOT NULL    | JSON payload with event-specific data                                |
| `metadata`       | TEXT     | NULL        | Optional JSON metadata (user_id, client_info, etc.)                  |
| `version`        | INTEGER  | NOT NULL    | Version number for optimistic locking                                |
| `created_at`     | DATETIME | DEFAULT NOW | Event timestamp                                                      |

#### Indexes

```sql
CREATE INDEX idx_aggregate ON events(aggregate_id, version);
CREATE INDEX idx_created_at ON events(created_at);
CREATE INDEX idx_event_type ON events(event_type);
CREATE UNIQUE INDEX idx_aggregate_version ON events(aggregate_id, version);
```

#### Event Types

| Event Type            | Aggregate Type | Purpose                               |
| --------------------- | -------------- | ------------------------------------- |
| `ConceptCreated`      | Concept        | New concept created                   |
| `ConceptUpdated`      | Concept        | Concept properties updated            |
| `ConceptDeleted`      | Concept        | Concept soft-deleted                  |
| `RelationshipCreated` | Relationship   | Relationship between concepts created |
| `RelationshipDeleted` | Relationship   | Relationship deleted                  |

**Source:** `models/events.py:109-176`

#### Example Row

```json
{
  "event_id": "evt-d4e5f6a7-b8c9-4d3e-2f1a-0b9c8d7e6f5a",
  "event_type": "ConceptCreated",
  "aggregate_id": "concept-001",
  "aggregate_type": "Concept",
  "event_data": "{\"name\":\"Python For Loops\",\"explanation\":\"For loops iterate...\",\"area\":\"Programming\"}",
  "metadata": null,
  "version": 1,
  "created_at": "2025-10-27T10:00:00.000Z"
}
```

---

### Table 2: outbox

**Purpose:** Reliable event publishing to projections (outbox pattern)

```sql
CREATE TABLE outbox (
    outbox_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    projection_name TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    last_attempt DATETIME,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(event_id)
);
```

#### Fields

| Field             | Type     | Constraints  | Description                         |
| ----------------- | -------- | ------------ | ----------------------------------- |
| `outbox_id`       | TEXT     | PRIMARY KEY  | UUID, unique outbox entry ID        |
| `event_id`        | TEXT     | NOT NULL, FK | References events.event_id          |
| `projection_name` | TEXT     | NOT NULL     | Target projection (neo4j, chromadb) |
| `status`          | TEXT     | NOT NULL     | pending \| processed \| failed      |
| `attempts`        | INTEGER  | DEFAULT 0    | Retry count                         |
| `last_attempt`    | DATETIME | NULL         | Last processing attempt timestamp   |
| `error_message`   | TEXT     | NULL         | Error details if failed             |
| `created_at`      | DATETIME | DEFAULT NOW  | Outbox entry creation time          |

#### Indexes

```sql
CREATE INDEX idx_status ON outbox(status, projection_name);
CREATE INDEX idx_event ON outbox(event_id);
```

#### Status Values

| Status      | Description                     |
| ----------- | ------------------------------- |
| `pending`   | Awaiting projection processing  |
| `processed` | Successfully projected          |
| `failed`    | Projection failed after retries |

**Source:** `services/outbox.py`

---

### Table 3: consistency_snapshots

**Purpose:** Track consistency check results between Neo4j and ChromaDB

```sql
CREATE TABLE consistency_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    neo4j_count INTEGER,
    chromadb_count INTEGER,
    discrepancies TEXT,              -- JSON serialized
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT
);
```

#### Fields

| Field            | Type     | Description                      |
| ---------------- | -------- | -------------------------------- |
| `snapshot_id`    | TEXT     | UUID, unique snapshot identifier |
| `neo4j_count`    | INTEGER  | Total concepts in Neo4j          |
| `chromadb_count` | INTEGER  | Total concepts in ChromaDB       |
| `discrepancies`  | TEXT     | JSON array of inconsistencies    |
| `checked_at`     | DATETIME | Check timestamp                  |
| `status`         | TEXT     | consistent \| inconsistent       |

#### Index

```sql
CREATE INDEX idx_checked_at ON consistency_snapshots(checked_at);
```

**Source:** `services/consistency_checker.py`

---

### Table 4: embedding_cache

**Purpose:** Persistent cache for generated embeddings (performance optimization)

```sql
CREATE TABLE embedding_cache (
    text_hash TEXT NOT NULL,
    model_name TEXT NOT NULL,
    embedding TEXT NOT NULL,         -- JSON array of floats
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (text_hash, model_name)
);
```

#### Fields

| Field        | Type     | Constraints    | Description                |
| ------------ | -------- | -------------- | -------------------------- |
| `text_hash`  | TEXT     | PK (composite) | SHA-256 hash of input text |
| `model_name` | TEXT     | PK (composite) | Embedding model identifier |
| `embedding`  | TEXT     | NOT NULL       | JSON array of 384 floats   |
| `created_at` | DATETIME | DEFAULT NOW    | Cache entry creation time  |

#### Indexes

```sql
CREATE INDEX idx_text_hash ON embedding_cache(text_hash);
CREATE INDEX idx_cache_created_at ON embedding_cache(created_at);
```

**Source:** `services/embedding_cache.py`

---

## Neo4j Graph Database

**Connection:** `bolt://localhost:7687`
**Purpose:** Graph relationships and hierarchy navigation
**Initialization:** `scripts/init_neo4j.py`

### Node Labels

#### 1. Concept

**Purpose:** Core entity representing a knowledge concept

```cypher
(:Concept {
  concept_id: String!,           // UUID, UNIQUE constraint
  name: String!,
  explanation: String!,
  area: String?,
  topic: String?,
  subtopic: String?,
  certainty_score: Float,        // 0-100
  created_at: DateTime!,
  last_modified: DateTime!,
  deleted: Boolean               // Soft delete flag
})
```

**Constraints:**

- `concept_id_unique`: UNIQUE constraint on `concept_id`

**Indexes:**

- `concept_name_idx`: Index on `name`
- `concept_certainty_idx`: Index on `certainty_score`
- `concept_created_idx`: Index on `created_at`
- `concept_modified_idx`: Index on `last_modified`
- `concept_area_topic_idx`: Composite index on `(area, topic)`

**Source:** `projections/neo4j_projection.py:102-150`

---

#### 2. Area

**Purpose:** Top-level organizational node (e.g., "Programming", "Mathematics")

```cypher
(:Area {
  area_id: String!,              // UUID, UNIQUE constraint
  name: String!
})
```

**Constraints:**

- `area_id_unique`: UNIQUE constraint on `area_id`

---

#### 3. Topic

**Purpose:** Mid-level organizational node within an area (e.g., "Python", "Algebra")

```cypher
(:Topic {
  topic_id: String!,             // UUID, UNIQUE constraint
  name: String!
})
```

**Constraints:**

- `topic_id_unique`: UNIQUE constraint on `topic_id`

---

#### 4. Subtopic

**Purpose:** Fine-grained organizational node (e.g., "For Loops", "Quadratic Equations")

```cypher
(:Subtopic {
  subtopic_id: String!,          // UUID, UNIQUE constraint
  name: String!
})
```

**Constraints:**

- `subtopic_id_unique`: UNIQUE constraint on `subtopic_id`

---

### Relationship Types

#### 1. BELONGS_TO

**Direction:** Concept → Area / Topic → Area / Subtopic → Topic

**Purpose:** Organizational hierarchy

```cypher
(:Concept)-[:BELONGS_TO]->(:Area)
(:Concept)-[:BELONGS_TO]->(:Topic)
(:Topic)-[:BELONGS_TO]->(:Area)
```

**Properties:** None

---

#### 2. HAS_SUBTOPIC

**Direction:** Topic → Subtopic

**Purpose:** Topic-to-subtopic hierarchy

```cypher
(:Topic)-[:HAS_SUBTOPIC]->(:Subtopic)
```

**Properties:** None

---

#### 3. PREREQUISITE

**Direction:** Source Concept → Target Concept

**Purpose:** Learning path, dependency chain

```cypher
(:Concept)-[:PREREQUISITE {
  relationship_id: String!,
  strength: Float!,              // 0.0-1.0
  description: String?,
  created_at: DateTime!
}]->(:Concept)
```

**Properties:**

- `relationship_id`: UUID
- `strength`: Relationship strength (0.0-1.0)
- `description`: Optional notes
- `created_at`: Timestamp

**Meaning:** Source concept is a prerequisite for target concept

---

#### 4. RELATES_TO

**Direction:** Source Concept → Target Concept

**Purpose:** General semantic relationship

```cypher
(:Concept)-[:RELATES_TO {
  relationship_id: String!,
  strength: Float!,
  description: String?,
  created_at: DateTime!
}]->(:Concept)
```

**Properties:** Same as PREREQUISITE

**Meaning:** Concepts are semantically related

---

#### 5. INCLUDES

**Direction:** Parent Concept → Child Concept

**Purpose:** Hierarchical containment

```cypher
(:Concept)-[:INCLUDES {
  relationship_id: String!,
  strength: Float!,
  description: String?,
  created_at: DateTime!
}]->(:Concept)
```

**Properties:** Same as PREREQUISITE

**Meaning:** Parent concept includes/contains child concept

---

### Schema Statistics

| Component              | Count                      | Status       |
| ---------------------- | -------------------------- | ------------ |
| **Node Labels**        | 4                          | ✅ Complete  |
| **Relationship Types** | 5                          | ✅ Complete  |
| **Constraints**        | 4                          | ✅ Enforced  |
| **Indexes**            | 5 (single) + 1 (composite) | ✅ Optimized |

**Source:** `scripts/init_neo4j.py:96-180`

---

### Example Cypher Queries

#### Create Concept Node

```cypher
CREATE (c:Concept {
  concept_id: $concept_id,
  name: $name,
  explanation: $explanation,
  area: $area,
  topic: $topic,
  subtopic: $subtopic,
  certainty_score: $certainty_score,
  created_at: datetime(),
  last_modified: datetime(),
  deleted: false
})
```

#### Find Prerequisites

```cypher
MATCH path = (c:Concept {concept_id: $concept_id})<-[:PREREQUISITE*1..3]-(prereq:Concept)
WHERE (c.deleted IS NULL OR c.deleted = false)
  AND (prereq.deleted IS NULL OR prereq.deleted = false)
RETURN prereq.concept_id, prereq.name, length(path) AS depth
ORDER BY depth
```

#### Shortest Path Between Concepts

```cypher
MATCH path = shortestPath(
  (start:Concept {concept_id: $start_id})-[*..5]-(end:Concept {concept_id: $end_id})
)
RETURN nodes(path), relationships(path)
```

---

## ChromaDB Vector Store

**Storage:** `data/chroma/` directory
**Purpose:** Semantic similarity search using vector embeddings
**Initialization:** `scripts/init_chromadb.py`

### Collection: concepts

**Embedding Dimensions:** 384 (sentence-transformers/all-MiniLM-L6-v2)
**Distance Function:** Cosine similarity
**Indexing:** HNSW (Hierarchical Navigable Small World)

#### Schema

```python
{
  "ids": ["concept_id"],           // UUID string
  "embeddings": [[float × 384]],   // 384-dimensional vector
  "metadatas": [{                   // Associated metadata
    "name": str,
    "area": str | None,
    "topic": str | None,
    "subtopic": str | None,
    "certainty_score": float,
    "created_at": str              // ISO 8601
  }],
  "documents": [str]               // Concept explanation (full text)
}
```

#### Fields

| Field        | Type              | Description                                |
| ------------ | ----------------- | ------------------------------------------ |
| `ids`        | List[str]         | Concept IDs (matches Neo4j concept_id)     |
| `embeddings` | List[List[float]] | 384-dim vectors from sentence-transformers |
| `metadatas`  | List[Dict]        | Filterable metadata for hybrid search      |
| `documents`  | List[str]         | Original concept explanations              |

#### Metadata Schema

```typescript
{
  name: string; // Concept name
  area: string | null; // Subject area
  topic: string | null; // Topic
  subtopic: string | null; // Subtopic
  certainty_score: number; // 0-100
  created_at: string; // ISO 8601 timestamp
}
```

**Source:** `projections/chromadb_projection.py:108-160`

---

### Query Examples

#### Semantic Search

```python
collection.query(
    query_embeddings=[query_vector],    # 384-dim vector
    n_results=10,
    include=["metadatas", "distances"],
    where={"area": "Programming"}       # Optional metadata filter
)
```

#### Hybrid Search (Semantic + Metadata)

```python
collection.query(
    query_embeddings=[query_vector],
    n_results=10,
    where={
        "$and": [
            {"area": "Programming"},
            {"certainty_score": {"$gte": 70}}
        ]
    }
)
```

---

## Schema Relationships

### Data Synchronization

```
Event Store (SQLite)
  │
  ├─> events table (source of truth)
  │
  └─> outbox table (reliable delivery)
        │
        ├─> Neo4j Projection
        │     │
        │     ├─> Concept nodes (graph structure)
        │     └─> Relationship edges (PREREQUISITE, RELATES_TO, etc.)
        │
        └─> ChromaDB Projection
              │
              └─> Concept vectors (semantic search)
```

### Consistency Guarantees

| Property        | Guarantee              | Mechanism                     |
| --------------- | ---------------------- | ----------------------------- |
| **Event Store** | ACID                   | SQLite transactions           |
| **Outbox**      | At-least-once delivery | Retry logic + status tracking |
| **Neo4j**       | Eventual consistency   | Outbox pattern + idempotency  |
| **ChromaDB**    | Eventual consistency   | Outbox pattern + idempotency  |

**Source:** `services/repository.py:129-220`

---

### Entity ID Mapping

All three databases use the same `concept_id` for correlation:

```
SQLite events.aggregate_id
         ↓
Neo4j (:Concept {concept_id})
         ↓
ChromaDB ids[0]
```

This enables:

- Joining data across databases
- Consistency checking
- Audit trail reconstruction

---

## Migration & Initialization

### First-Time Setup

```bash
# 1. Initialize SQLite event store
python scripts/init_database.py

# 2. Initialize Neo4j schema
python scripts/init_neo4j.py

# 3. Initialize ChromaDB collection
python scripts/init_chromadb.py
```

### Schema Verification

```bash
# SQLite
sqlite3 data/events.db ".schema"

# Neo4j
SHOW CONSTRAINTS;
SHOW INDEXES;

# ChromaDB
collection = client.get_collection("concepts")
collection.count()
```

---

## Performance Considerations

### SQLite

- **Write Performance:** ~10,000 events/sec (append-only)
- **Read Performance:** Fast with proper indexing
- **Size:** ~1KB per event (average)

### Neo4j

- **Graph Traversal:** O(depth) for relationship queries
- **Indexes:** Sub-millisecond lookups on indexed properties
- **Constraint Checks:** Automatic uniqueness enforcement

### ChromaDB

- **HNSW Search:** O(log n) approximate search
- **Embedding Size:** 384 floats × 4 bytes = 1.5KB per concept
- **Indexing:** Sub-second for 10K concepts

---

**Document Version:** 1.0
**Generated:** 2025-10-27
**Evidence Base:** `scripts/init_database.py`, `scripts/init_neo4j.py`, `projections/`, `models/events.py`
**Total Tables:** 4 (SQLite) + 4 (Neo4j node types) + 1 (ChromaDB collection)
