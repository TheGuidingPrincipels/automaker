# MCP Tools Reference

# Complete API Documentation for 17 Tools

**Version:** 1.1
**Status:** Production Ready
**Tool Count:** 17 tools across 5 categories
**Last Updated:** 2025-11-12

---

## Table of Contents

1. [Overview](#overview)
2. [Tool Categories](#tool-categories)
3. [System Tools (3)](#system-tools)
4. [Concept CRUD Tools (4)](#concept-crud-tools)
5. [Search Tools (3)](#search-tools)
6. [Relationship Tools (5)](#relationship-tools)
7. [Analytics Tools (2)](#analytics-tools)
8. [Error Response Format](#error-response-format)
9. [Service Availability & Troubleshooting](#service-availability--troubleshooting)
10. [Common Patterns](#common-patterns)

---

## Overview

The MCP Knowledge Management Server exposes 17 MCP tools via the FastMCP framework. All tools are async, follow consistent error handling patterns, and return standardized JSON responses.

### Service Dependency Protection

All tools are protected by the `@requires_services` decorator which validates that required backend services (Neo4j, ChromaDB, etc.) are initialized before execution. If a service is unavailable, tools return a clear error message instead of crashing.

### Response Format Standards

**Success Response:**

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "...": "...operation-specific fields..."
}
```

**Error Response:**

```json
{
  "success": false,
  "error": "error_type",
  "message": "Human-readable error description"
}
```

### Error Types

- `validation_error`: Invalid input parameters (400)
- `concept_not_found`: Concept ID doesn't exist (404)
- `relationship_not_found`: Relationship not found (404)
- `service_unavailable`: Required service not initialized (503)
- `database_error`: Database operation failed (500)
- `internal_error`: Unexpected server error (500)

**Source:** `tools/responses.py`

---

## Tool Categories

| Category      | Count | Primary Database | Purpose                                |
| ------------- | ----- | ---------------- | -------------------------------------- |
| System        | 3     | SQLite / None    | Health checks, statistics, diagnostics |
| Concept CRUD  | 4     | Neo4j + ChromaDB | Create, Read, Update, Delete concepts  |
| Search        | 3     | Neo4j / ChromaDB | Find concepts by criteria              |
| Relationships | 5     | Neo4j            | Manage concept relationships           |
| Analytics     | 2     | Neo4j            | Hierarchies and aggregations           |

---

## System Tools

### 1. ping

**Purpose:** Test server connectivity and health status

**Location:** `mcp_server.py:238-252`

#### Parameters

None

#### Returns

```typescript
{
  status: 'ok';
  message: string;
  server_name: string;
  timestamp: string; // ISO 8601 format
}
```

#### Example

```python
result = await ping()
```

**Response:**

```json
{
  "status": "ok",
  "message": "MCP Knowledge Server is running",
  "server_name": "knowledge-server",
  "timestamp": "2025-10-27T14:23:45.123456"
}
```

#### Notes

- Always succeeds if server is running
- No authentication required
- Lightweight (<5ms response time)

---

### 2. get_server_stats

**Purpose:** Get event store and system statistics

**Location:** `mcp_server.py:256-286`

#### Parameters

None

#### Returns

```typescript
{
  success: boolean;
  event_store: {
    total_events: number;
    concept_events: number;
  }
  outbox: {
    pending: number;
    processed: number;
    failed: number;
  }
  status: 'healthy' | 'error';
}
```

#### Example

```python
result = await get_server_stats()
```

**Response:**

```json
{
  "success": true,
  "event_store": {
    "total_events": 1543,
    "concept_events": 987
  },
  "outbox": {
    "pending": 0,
    "processed": 3086,
    "failed": 0
  },
  "status": "healthy"
}
```

#### Use Cases

- Monitoring system health
- Tracking event processing
- Debugging outbox issues

---

### 3. get_tool_availability

**Purpose:** Diagnostic tool to check which MCP tools are available based on service initialization status

**Location:** `mcp_server.py:378-438`

**Service Dependencies:** None (always available)

#### Parameters

None

#### Returns

```typescript
{
  success: boolean;
  available: string[];        // List of available tool names
  unavailable: string[];      // List of unavailable tool names
  total_tools: number;       // Total count (17)
  service_status: {          // Detailed service initialization status
    concept_tools: {
      repository: boolean;
      confidence_service: boolean;
    };
    search_tools: {
      neo4j_service: boolean;
      chromadb_service: boolean;
      embedding_service: boolean;
    };
    relationship_tools: {
      neo4j_service: boolean;
      event_store: boolean;
      outbox: boolean;
    };
    analytics_tools: {
      neo4j_service: boolean;
    };
  };
}
```

#### Example

```python
result = await get_tool_availability()
```

**Response (All Services Available):**

```json
{
  "success": true,
  "available": [
    "create_concept",
    "create_relationship",
    "delete_concept",
    "delete_relationship",
    "get_concept",
    "get_concept_chain",
    "get_concepts_by_certainty",
    "get_prerequisites",
    "get_recent_concepts",
    "get_related_concepts",
    "get_server_stats",
    "list_hierarchy",
    "ping",
    "search_concepts_exact",
    "search_concepts_semantic",
    "update_concept"
  ],
  "unavailable": [],
  "total_tools": 16,
  "service_status": {
    "concept_tools": {
      "repository": true,
      "confidence_service": true
    },
    "search_tools": {
      "neo4j_service": true,
      "chromadb_service": true,
      "embedding_service": true
    },
    "relationship_tools": {
      "neo4j_service": true,
      "event_store": true,
      "outbox": true
    },
    "analytics_tools": {
      "neo4j_service": true
    }
  }
}
```

**Response (Some Services Unavailable):**

```json
{
  "success": true,
  "available": ["ping", "get_server_stats"],
  "unavailable": ["create_concept", "get_concept", "search_concepts_semantic", "..."],
  "total_tools": 16,
  "service_status": {
    "concept_tools": {
      "repository": false,
      "confidence_service": false
    },
    "search_tools": {
      "neo4j_service": false,
      "chromadb_service": false,
      "embedding_service": false
    }
  }
}
```

#### Use Cases

- **Troubleshooting:** When MCP tools aren't responding, use this to identify which services failed to initialize
- **Health Monitoring:** Verify all services are properly initialized after server startup
- **Debugging:** Identify which specific service is causing tool unavailability
- **Status Dashboards:** Build monitoring dashboards showing real-time tool availability

#### Notes

- This tool has no service dependencies and is always available (even if other services fail)
- Returns `success: true` even when services are unavailable (the unavailability is reported in the data)
- Tool lists are sorted alphabetically for easy scanning
- The `get_server_stats` and `ping` tools are always in the `available` list

#### Related

- See [Service Availability & Troubleshooting](#service-availability--troubleshooting) for more details
- See `tools/service_utils.py` for implementation

---

## Concept CRUD Tools

### 4. create_concept

**Purpose:** Create a new concept in the knowledge base

**Location:** `tools/concept_tools.py:75-166`

#### Parameters

```typescript
{
  name: string;              // Required, 1-200 chars
  explanation: string;       // Required, detailed explanation
  area?: string;             // Optional, max 100 chars (e.g., "Programming")
  topic?: string;            // Optional, max 100 chars (e.g., "Python")
  subtopic?: string;         // Optional, max 100 chars (e.g., "For Loops")
  certainty_score?: number;  // Optional, 0-100
}
```

#### Returns

```typescript
{
  success: boolean;
  concept_id: string; // UUID
  message: string;
}
```

#### Example

```python
result = await create_concept(
    name="Python For Loops",
    explanation="For loops iterate over sequences like lists, tuples, and strings. Syntax: for item in sequence: ...",
    area="Programming",
    topic="Python",
    subtopic="Control Flow",
    certainty_score=90
)
```

**Response:**

```json
{
  "success": true,
  "concept_id": "d4e5f6a7-b8c9-4d3e-2f1a-0b9c8d7e6f5a",
  "message": "Created"
}
```

#### Error Scenarios

- **validation_error**: Empty name/explanation, invalid certainty_score
- **database_error**: Neo4j or ChromaDB connection failure
- **internal_error**: Embedding generation failure

#### Processing Flow

1. Validate inputs (Pydantic)
2. Generate embedding for explanation text
3. Create ConceptCreated event
4. Store in event store
5. Project to Neo4j (graph node)
6. Project to ChromaDB (vector embedding)

---

### 5. get_concept

**Purpose:** Retrieve a concept by its ID

**Location:** `tools/concept_tools.py:169-243`

#### Parameters

```typescript
{
  concept_id: string;         // Required, UUID
  include_history?: boolean;  // Optional, default: false
}
```

#### Returns

```typescript
{
  success: boolean;
  concept: {
    concept_id: string;
    name: string;
    explanation: string;
    area: string | null;
    topic: string | null;
    subtopic: string | null;
    certainty_score: number;
    created_at: string;       // ISO 8601
    last_modified: string;    // ISO 8601
    explanation_history?: Array<{
      explanation: string;
      timestamp: string;
    }>;
  } | null;
  message: string;
}
```

#### Example

```python
result = await get_concept(
    concept_id="d4e5f6a7-b8c9-4d3e-2f1a-0b9c8d7e6f5a",
    include_history=True
)
```

**Response:**

```json
{
  "success": true,
  "concept": {
    "concept_id": "d4e5f6a7-b8c9-4d3e-2f1a-0b9c8d7e6f5a",
    "name": "Python For Loops",
    "explanation": "For loops iterate over sequences...",
    "area": "Programming",
    "topic": "Python",
    "subtopic": "Control Flow",
    "certainty_score": 90,
    "created_at": "2025-10-27T10:00:00.000Z",
    "last_modified": "2025-10-27T10:00:00.000Z",
    "explanation_history": [
      {
        "explanation": "For loops iterate over sequences...",
        "timestamp": "2025-10-27T10:00:00.000Z"
      }
    ]
  },
  "message": "Found"
}
```

#### Error Scenarios

- **concept_not_found**: concept_id doesn't exist or is deleted

#### Notes

- History is excluded by default for token efficiency
- Include history only when needed for audit trail review

---

### 6. update_concept

**Purpose:** Update an existing concept's properties

**Location:** `tools/concept_tools.py:246-362`

#### Parameters

```typescript
{
  concept_id: string;         // Required, UUID
  explanation?: string;       // Optional, new explanation
  name?: string;              // Optional, new name (1-200 chars)
  area?: string;              // Optional, new area
  topic?: string;             // Optional, new topic
  subtopic?: string;          // Optional, new subtopic
  certainty_score?: number;   // Optional, new score (0-100)
}
```

#### Returns

```typescript
{
  success: boolean;
  concept_id: string;
  message: string;
}
```

#### Example

```python
result = await update_concept(
    concept_id="d4e5f6a7-b8c9-4d3e-2f1a-0b9c8d7e6f5a",
    explanation="UPDATED: For loops in Python iterate over...",
    certainty_score=95
)
```

**Response:**

```json
{
  "success": true,
  "concept_id": "d4e5f6a7-b8c9-4d3e-2f1a-0b9c8d7e6f5a",
  "message": "Updated"
}
```

#### Error Scenarios

- **concept_not_found**: concept_id doesn't exist
- **validation_error**: Invalid parameter values
- **database_error**: Projection failure

#### Notes

- Only provided fields are updated (partial update)
- Explanation changes trigger re-embedding
- Old explanation preserved in history
- Optimistic locking with version checking

---

### 7. delete_concept

**Purpose:** Soft-delete a concept (preserves audit trail)

**Location:** `tools/concept_tools.py:365-450`

#### Parameters

```typescript
{
  concept_id: string; // Required, UUID
}
```

#### Returns

```typescript
{
  success: boolean;
  concept_id: string;
  message: string;
}
```

#### Example

```python
result = await delete_concept(
    concept_id="d4e5f6a7-b8c9-4d3e-2f1a-0b9c8d7e6f5a"
)
```

**Response:**

```json
{
  "success": true,
  "concept_id": "d4e5f6a7-b8c9-4d3e-2f1a-0b9c8d7e6f5a",
  "message": "Deleted"
}
```

#### Error Scenarios

- **concept_not_found**: concept_id doesn't exist

#### Notes

- **Soft Delete:** Concept marked as deleted, not removed
- Event sourcing allows complete recovery
- Related relationships remain intact
- Deleted concepts excluded from searches by default

---

## Search Tools

### 8. search_concepts_semantic

**Purpose:** Semantic similarity search using vector embeddings

**Location:** `tools/search_tools.py:30-177`

#### Parameters

```typescript
{
  query: string;              // Required, natural language query
  limit?: number;             // Optional, 1-50, default: 10
  min_certainty?: number;     // Optional, filter 0-100
  area?: string;              // Optional, filter by area
  topic?: string;             // Optional, filter by topic
}
```

#### Returns

```typescript
{
  success: boolean;
  results: Array<{
    concept_id: string;
    name: string;
    similarity: number; // 0-1 (1 = most similar)
    area: string | null;
    topic: string | null;
    certainty_score: number;
  }>;
  total: number;
  message: string;
}
```

#### Example

```python
result = await search_concepts_semantic(
    query="How do I loop through items in Python?",
    limit=5,
    min_certainty=70
)
```

**Response:**

```json
{
  "success": true,
  "results": [
    {
      "concept_id": "d4e5f6a7-...",
      "name": "Python For Loops",
      "similarity": 0.9234,
      "area": "Programming",
      "topic": "Python",
      "certainty_score": 90
    },
    {
      "concept_id": "a1b2c3d4-...",
      "name": "Python While Loops",
      "similarity": 0.8567,
      "area": "Programming",
      "topic": "Python",
      "certainty_score": 85
    }
  ],
  "total": 2,
  "message": "Found"
}
```

#### Algorithm

1. Generate embedding for query (sentence-transformers)
2. Perform cosine similarity search in ChromaDB
3. Apply metadata filters (area, topic)
4. Post-filter by min_certainty
5. Sort by similarity descending

#### Performance

- **P50:** <200ms (10 results)
- **P95:** <500ms (10 results)
- Uses HNSW indexing for fast retrieval

---

### 9. search_concepts_exact

**Purpose:** Exact/filtered search using metadata criteria

**Location:** `tools/search_tools.py:180-326`

#### Parameters

```typescript
{
  name?: string;              // Optional, case-insensitive CONTAINS
  area?: string;              // Optional, exact match
  topic?: string;             // Optional, exact match
  subtopic?: string;          // Optional, exact match
  min_certainty?: number;     // Optional, filter 0-100
  limit?: number;             // Optional, 1-100, default: 20
}
```

#### Returns

```typescript
{
  success: boolean;
  results: Array<{
    concept_id: string;
    name: string;
    area: string | null;
    topic: string | null;
    subtopic: string | null;
    certainty_score: number;
    created_at: string;
  }>;
  total: number;
  message: string;
}
```

#### Example

```python
result = await search_concepts_exact(
    name="loop",
    area="Programming",
    topic="Python",
    limit=10
)
```

**Response:**

```json
{
  "success": true,
  "results": [
    {
      "concept_id": "d4e5f6a7-...",
      "name": "Python For Loops",
      "area": "Programming",
      "topic": "Python",
      "subtopic": "Control Flow",
      "certainty_score": 90,
      "created_at": "2025-10-27T10:00:00.000Z"
    }
  ],
  "total": 1,
  "message": "Found 1 concepts matching criteria"
}
```

#### Notes

- Name matching uses case-insensitive CONTAINS
- Area/topic/subtopic use exact matching
- Results sorted by created_at DESC
- Uses Neo4j Cypher queries

---

### 10. get_recent_concepts

**Purpose:** Retrieve recently created concepts

**Location:** `tools/search_tools.py:328-410`

#### Parameters

```typescript
{
  limit?: number;  // Optional, 1-50, default: 20
}
```

#### Returns

```typescript
{
  success: boolean;
  results: Array<{
    concept_id: string;
    name: string;
    area: string | null;
    topic: string | null;
    created_at: string;
  }>;
  total: number;
  message: string;
}
```

#### Example

```python
result = await get_recent_concepts(limit=10)
```

**Response:**

```json
{
  "success": true,
  "results": [
    {
      "concept_id": "d4e5f6a7-...",
      "name": "Python For Loops",
      "area": "Programming",
      "topic": "Python",
      "created_at": "2025-10-27T10:00:00.000Z"
    }
  ],
  "total": 1,
  "message": "Found"
}
```

#### Use Cases

- Review recent additions
- Track knowledge base growth
- Quick access to latest concepts

---

## Relationship Tools

### 11. create_relationship

**Purpose:** Create a directed relationship between two concepts

**Location:** `tools/relationship_tools.py:34-254`

#### Parameters

```typescript
{
  source_id: string;              // Required, source concept ID
  target_id: string;              // Required, target concept ID
  relationship_type: string;      // Required, one of: "prerequisite", "relates_to", "includes"
  strength?: number;              // Optional, 0.0-1.0, default: 1.0
  notes?: string;                 // Optional, description
}
```

#### Returns

```typescript
{
  success: boolean;
  relationship_id: string;
  message: string;
}
```

#### Example

```python
result = await create_relationship(
    source_id="d4e5f6a7-...",
    target_id="a1b2c3d4-...",
    relationship_type="prerequisite",
    strength=1.0,
    notes="Must understand functions before learning decorators"
)
```

**Response:**

```json
{
  "success": true,
  "relationship_id": "rel-a1b2c3d4e5f6",
  "message": "Relationship created"
}
```

#### Relationship Types

| Type           | Direction | Use Case              |
| -------------- | --------- | --------------------- |
| `prerequisite` | A → B     | B requires A first    |
| `relates_to`   | A → B     | A is related to B     |
| `includes`     | A → B     | A contains/includes B |

#### Error Scenarios

- **concept_not_found**: source_id or target_id doesn't exist
- **validation_error**: Invalid relationship_type, duplicate relationship
- **database_error**: Projection failure

#### Notes

- Relationships are directed (A → B)
- Duplicate detection prevents redundant edges
- Stored in Neo4j as graph edges
- Event sourced for audit trail

---

### 12. delete_relationship

**Purpose:** Remove a relationship between concepts

**Location:** `tools/relationship_tools.py:257-395`

#### Parameters

```typescript
{
  source_id: string; // Required, source concept ID
  target_id: string; // Required, target concept ID
  relationship_type: string; // Required, exact type to delete
}
```

#### Returns

```typescript
{
  success: boolean;
  relationship_id: string;
  message: string;
}
```

#### Example

```python
result = await delete_relationship(
    source_id="d4e5f6a7-...",
    target_id="a1b2c3d4-...",
    relationship_type="prerequisite"
)
```

**Response:**

```json
{
  "success": true,
  "relationship_id": "rel-a1b2c3d4e5f6",
  "message": "Relationship deleted"
}
```

---

### 13. get_related_concepts

**Purpose:** Find concepts related to a given concept

**Location:** `tools/relationship_tools.py:398-563`

#### Parameters

```typescript
{
  concept_id: string;                          // Required, center concept ID
  direction?: "incoming" | "outgoing" | "both"; // Optional, default: "both"
  relationship_type?: string;                  // Optional, filter by type
  limit?: number;                              // Optional, 1-50, default: 20
}
```

#### Returns

```typescript
{
  success: boolean;
  results: Array<{
    concept_id: string;
    name: string;
    relationship_type: string;
    direction: 'incoming' | 'outgoing';
    strength: number;
  }>;
  total: number;
  message: string;
}
```

#### Example

```python
result = await get_related_concepts(
    concept_id="d4e5f6a7-...",
    direction="outgoing",
    relationship_type="prerequisite",
    limit=10
)
```

**Response:**

```json
{
  "success": true,
  "results": [
    {
      "concept_id": "a1b2c3d4-...",
      "name": "Python Functions",
      "relationship_type": "PREREQUISITE",
      "direction": "outgoing",
      "strength": 1.0
    }
  ],
  "total": 1,
  "message": "Found 1 related concepts"
}
```

---

### 14. get_prerequisites

**Purpose:** Find prerequisite chain for a concept (learning path)

**Location:** `tools/relationship_tools.py:566-672`

#### Parameters

```typescript
{
  concept_id: string;  // Required, target concept ID
  depth?: number;      // Optional, max depth, 1-5, default: 3
}
```

#### Returns

```typescript
{
  success: boolean;
  prerequisites: Array<{
    concept_id: string;
    name: string;
    depth: number; // Distance from root
  }>;
  total: number;
  message: string;
}
```

#### Example

```python
result = await get_prerequisites(
    concept_id="d4e5f6a7-...",
    depth=3
)
```

**Response:**

```json
{
  "success": true,
  "prerequisites": [
    {
      "concept_id": "a1b2c3d4-...",
      "name": "Variables",
      "depth": 1
    },
    {
      "concept_id": "b2c3d4e5-...",
      "name": "Functions",
      "depth": 2
    },
    {
      "concept_id": "c3d4e5f6-...",
      "name": "Python For Loops",
      "depth": 3
    }
  ],
  "total": 3,
  "message": "Found 3 prerequisites"
}
```

#### Use Cases

- Build learning paths
- Identify knowledge gaps
- Prerequisite validation

---

### 15. get_concept_chain

**Purpose:** Find shortest path between two concepts

**Location:** `tools/relationship_tools.py:675-850`

#### Parameters

```typescript
{
  start_concept_id: string;    // Required, starting concept
  end_concept_id: string;      // Required, target concept
  max_depth?: number;          // Optional, 1-10, default: 5
}
```

#### Returns

```typescript
{
  success: boolean;
  path: Array<{
    concept_id: string;
    name: string;
    relationship_to_next: string | null;
  }>;
  length: number; // Number of edges (relationships) in path
  message: string;
}
```

#### Understanding Path Length

**IMPORTANT:** The `length` field represents the **number of relationships (edges)** in the path, not the number of concepts (nodes). This follows standard graph theory conventions.

**Formula:** `length = number_of_concepts - 1`

**Examples:**

- Path with 3 concepts [A, B, C] has **length = 2** (two edges: A→B, B→C)
- Path with 2 concepts [A, B] has **length = 1** (one edge: A→B)
- Path with 1 concept [A] has **length = 0** (no edges: same start/end concept)

#### Example

```python
result = await get_concept_chain(
    start_concept_id="d4e5f6a7-...",
    end_concept_id="z9y8x7w6-...",
    max_depth=5
)
```

**Response:**

```json
{
  "success": true,
  "path": [
    {
      "concept_id": "d4e5f6a7-...",
      "name": "Python Variables",
      "relationship_to_next": "PREREQUISITE"
    },
    {
      "concept_id": "a1b2c3d4-...",
      "name": "Python Functions",
      "relationship_to_next": "PREREQUISITE"
    },
    {
      "concept_id": "z9y8x7w6-...",
      "name": "Python Decorators",
      "relationship_to_next": null
    }
  ],
  "length": 3,
  "message": "Found path of length 3"
}
```

#### Algorithm

- Uses Neo4j's shortestPath() function
- Bidirectional BFS for efficiency
- Returns first path found (not all paths)

---

## Analytics Tools

### 16. list_hierarchy

**Purpose:** Get complete knowledge hierarchy with concept counts

**Location:** `tools/analytics_tools.py:35-197`

#### Parameters

None

#### Returns

```typescript
{
  success: boolean;
  areas: Array<{
    name: string;
    concept_count: number;
    topics: Array<{
      name: string;
      concept_count: number;
      subtopics: Array<{
        name: string;
        concept_count: number;
      }>;
    }>;
  }>;
  total_concepts: number;
  message: string;
}
```

#### Example

```python
result = await list_hierarchy()
```

**Response:**

```json
{
  "success": true,
  "areas": [
    {
      "name": "Programming",
      "concept_count": 150,
      "topics": [
        {
          "name": "Python",
          "concept_count": 75,
          "subtopics": [
            {
              "name": "Control Flow",
              "concept_count": 15
            },
            {
              "name": "Data Structures",
              "concept_count": 20
            }
          ]
        }
      ]
    }
  ],
  "total_concepts": 150,
  "message": "Hierarchy contains 1 areas with 150 concepts"
}
```

#### Notes

- Results cached for 5 minutes
- Concepts without area/topic/subtopic grouped under "Uncategorized"/"General"
- Useful for navigation and organization

---

### 17. get_concepts_by_certainty

**Purpose:** Filter concepts by confidence score range

**Location:** `tools/analytics_tools.py:200-322`

#### Parameters

```typescript
{
  min_certainty?: number;  // Optional, 0-100, default: 0
  max_certainty?: number;  // Optional, 0-100, default: 100
  limit?: number;          // Optional, 1-50, default: 20
}
```

#### Returns

```typescript
{
  success: boolean;
  results: Array<{
    concept_id: string;
    name: string;
    area: string | null;
    topic: string | null;
    subtopic: string | null;
    certainty_score: number;
    created_at: string;
  }>;
  total: number;
  message: string;
}
```

#### Example

```python
# Find low-certainty concepts needing review
result = await get_concepts_by_certainty(
    min_certainty=0,
    max_certainty=50,
    limit=20
)
```

**Response:**

```json
{
  "success": true,
  "results": [
    {
      "concept_id": "d4e5f6a7-...",
      "name": "Quantum Computing Basics",
      "area": "Computer Science",
      "topic": "Quantum",
      "subtopic": null,
      "certainty_score": 30,
      "created_at": "2025-10-27T10:00:00.000Z"
    }
  ],
  "total": 1,
  "message": "Found 1 concepts with certainty between 0 and 50"
}
```

#### Use Cases

- **Low certainty (0-50):** Concepts needing review/validation
- **Medium certainty (50-80):** Concepts needing refinement
- **High certainty (80-100):** Well-established concepts

#### Notes

- Results sorted by certainty_score ascending (lowest first)
- Helps identify knowledge gaps

---

## Error Response Format

All tools follow a consistent error response structure:

```typescript
{
  success: false;
  error: string;              // Error type (see below)
  message: string;            // Human-readable description
  details?: {                 // Optional additional context
    field?: string;
    invalid_value?: any;
    resource_id?: string;
  }
}
```

### Error Type Reference

| Error Type               | HTTP Equivalent | Description                      |
| ------------------------ | --------------- | -------------------------------- |
| `validation_error`       | 400             | Invalid input parameters         |
| `invalid_input`          | 400             | Malformed data                   |
| `missing_required`       | 400             | Required field missing           |
| `concept_not_found`      | 404             | Concept ID doesn't exist         |
| `relationship_not_found` | 404             | Relationship doesn't exist       |
| `path_not_found`         | 404             | No path between concepts         |
| `service_unavailable`    | 503             | Required service not initialized |
| `neo4j_error`            | 500             | Graph database error             |
| `chromadb_error`         | 500             | Vector database error            |
| `embedding_error`        | 500             | Embedding generation failed      |
| `database_error`         | 500             | Generic database error           |
| `internal_error`         | 500             | Unexpected server error          |

**Source:** `tools/responses.py`

---

## Service Availability & Troubleshooting

### Overview

All MCP tools (except `ping` and `get_tool_availability`) depend on backend services being properly initialized. If services fail during startup, tools will return `service_unavailable` errors instead of crashing.

### Service Dependencies by Tool Category

**Concept Tools** (create_concept, get_concept, update_concept, delete_concept):

- Requires: `repository` (unified Neo4j + ChromaDB interface)
- Optional: `confidence_service` (automated scoring)

**Search Tools**:

- `search_concepts_semantic`: Requires `embedding_service`, `chromadb_service`
- `search_concepts_exact`: Requires `neo4j_service`
- `get_recent_concepts`: Requires `neo4j_service`

**Relationship Tools** (create_relationship, delete_relationship):

- Requires: `neo4j_service`, `event_store`, `outbox`

**Relationship Tools** (get_related_concepts, get_prerequisites, get_concept_chain):

- Requires: `neo4j_service`

**Analytics Tools** (list_hierarchy, get_concepts_by_certainty):

- Requires: `neo4j_service`

### Troubleshooting Steps

#### Step 1: Check Tool Availability

```python
# Use the diagnostic tool to see which services are initialized
result = await get_tool_availability()

print(f"Available tools: {result['available']}")
print(f"Unavailable tools: {result['unavailable']}")
print(f"Service status: {result['service_status']}")
```

#### Step 2: Identify Failed Services

Look at the `service_status` object to identify which services are `false`:

```json
{
  "concept_tools": {
    "repository": false, // ← This service failed
    "confidence_service": true
  },
  "search_tools": {
    "neo4j_service": false, // ← This service failed
    "chromadb_service": true,
    "embedding_service": true
  }
}
```

#### Step 3: Check Service Logs

```bash
# Check MCP server logs for initialization errors
tail -f logs/mcp_server.log | grep -E "(ERROR|WARN|Failed to initialize)"

# Common issues:
# - Neo4j connection refused → Check Neo4j is running on bolt://localhost:7687
# - ChromaDB initialization failed → Check CHROMA_PERSIST_DIRECTORY permissions
# - Embedding service unavailable → Check EMBEDDING_MODEL path and cache directory
```

#### Step 4: Verify Service Configuration

```bash
# Check environment variables
grep -E "(NEO4J|CHROMA|EMBEDDING)" .env

# Verify Neo4j is running
docker ps | grep neo4j

# Test Neo4j connection
echo "MATCH (n) RETURN count(n)" | cypher-shell -u neo4j -p $NEO4J_PASSWORD
```

### Service Unavailable Error Example

When a tool is called before services initialize, you'll receive:

```json
{
  "success": false,
  "error_type": "service_unavailable",
  "error": "Required service not initialized. MCP server may still be starting up. (repository not initialized)"
}
```

**Solution:** Wait for server initialization to complete (usually 5-10 seconds) or check logs for service startup failures.

### Implementation Details

The `@requires_services` decorator (defined in `tools/service_utils.py`) protects all tools from null pointer errors by validating service availability before execution. This ensures:

1. **Graceful degradation:** Tools return clear error messages instead of crashing
2. **Diagnostic clarity:** Error messages specify which service is missing
3. **Partial availability:** Some tools remain usable even if others are unavailable

---

## Common Patterns

### Token Efficiency

All tools optimize for minimal token usage:

- Exclude optional fields by default (e.g., `explanation_history`)
- Use concise field names (`concept_id` not `concept_identifier`)
- Omit null fields where appropriate

### Async Operations

All tool functions are `async def`, enabling:

- Concurrent execution
- Non-blocking I/O
- Efficient resource usage

### Event Sourcing

Write operations (create/update/delete) follow this pattern:

1. Validate inputs (Pydantic)
2. Create domain event
3. Append to event store (SQLite)
4. Add to outbox for projections
5. Project to read models (Neo4j, ChromaDB)
6. Return response

### Soft Deletes

Deleted concepts are marked, not removed:

- `deleted = true` flag in Neo4j
- Event history preserved
- Excluded from searches automatically
- Recoverable via event replay

---

**Document Version:** 1.1
**Generated:** 2025-11-12
**Total Tools Documented:** 17
**Evidence Base:** Direct code analysis from `mcp_server.py` and `tools/` directory
**Changes in v1.1:**

- Added `get_tool_availability` diagnostic tool
- Added `service_unavailable` error type
- Added "Service Availability & Troubleshooting" section
- Updated all tools with `@requires_services` decorator documentation
