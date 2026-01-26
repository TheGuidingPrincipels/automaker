# MCP Knowledge Server - LLM Integration Guide

**Version**: 1.0
**Purpose**: Token-efficient guide for downstream LLMs to understand and use the MCP Knowledge Server
**Token Count**: ~2,000 tokens

---

## System Overview

The MCP Knowledge Server is a production-grade event-sourced knowledge management system with 16 MCP tools for concept storage, semantic search, and graph-based navigation.

### Core Architecture

**Event Sourcing**: All changes flow through 5 immutable event types (ConceptCreated, ConceptUpdated, ConceptDeleted, RelationshipCreated, RelationshipDeleted) stored in SQLite. Events are append-only with optimistic locking via version numbers. This provides complete audit trails and replay capability.

**Dual Storage**:

- **Neo4j** (graph database): Handles relationship traversal, shortest paths, prerequisite chains, hierarchical aggregations, and metadata queries
- **ChromaDB** (vector database): Handles semantic similarity search using 384-dimensional embeddings from sentence-transformers (all-MiniLM-L6-v2)

**Data Flow**: User action → Pydantic validation → Event creation → SQLite EventStore (source of truth) → Dual projection via Outbox pattern → Neo4j (graph node/edge) + ChromaDB (vector + metadata) → Success response

**Consistency**: Eventual consistency with 1-5 minute window. Three-layer defense: (1) Compensation Manager for immediate rollback on partial failures, (2) Outbox retry (3 attempts), (3) Consistency Checker for periodic reconciliation.

---

## The 16 MCP Tools

### 1. Server Operations

**ping()**

- Test server connectivity
- Returns: health status, timestamp
- Storage: None (read-only)

**get_server_stats()**

- Retrieve metrics: event_count, outbox_pending, outbox_failed
- Returns: operational statistics
- Storage: Queries SQLite event store and outbox

### 2. Concept CRUD

**create_concept(name, explanation, area?, topic?, subtopic?, certainty_score?, examples?, prerequisites?)**

- Create new concept with dual-storage projection
- Required: name (1-200 chars), explanation (min 1 char)
- Optional: area/topic/subtopic (max 100 chars), certainty_score (0-100), examples, prerequisites
- Returns: concept_id (UUID)
- Storage: SQLite event → Neo4j node → ChromaDB vector
- Generates 384-dim embedding from `name + ". " + explanation`

**get_concept(concept_id, include_history?)**

- Retrieve concept by UUID
- Returns: Full concept object with metadata
- Storage: Reads from Neo4j projection

**update_concept(concept_id, ...partial_fields)**

- Partial update with automatic embedding regeneration if name/explanation changes
- All fields optional except concept_id
- Returns: updated_fields list
- Storage: Event store write → Dual projection update

**delete_concept(concept_id)**

- Soft-delete (Neo4j: marks deleted, ChromaDB: hard delete, EventStore: preserved)
- Returns: Success confirmation
- Storage: Neo4j soft delete flag + ChromaDB removal

### 3. Search Operations

**search_concepts_semantic(query, limit?, min_certainty?, area?, topic?, subtopic?)**

- Natural language semantic search using cosine similarity
- query: Required natural language text
- limit: Max 50, default 10
- Returns: Results with similarity scores (0-1), metadata
- Storage: ChromaDB vector search with metadata filtering
- Performance: P95 <200ms (cached <1ms)

**search_concepts_exact(name?, area?, topic?, subtopic?, min_certainty?, max_certainty?, limit?)**

- Structured metadata-based search with exact/partial matching
- All parameters optional
- name: Case-insensitive CONTAINS matching
- limit: Max 100, default 20
- Returns: Full concept metadata sorted by created_at DESC
- Storage: Neo4j with indexed queries
- Performance: P95 <50ms

**get_recent_concepts(days?, limit?)**

- Time-based retrieval of recently modified concepts
- days: 1-365, default 7
- limit: Max 100, default 10
- Returns: Concepts sorted by last_modified DESC
- Storage: Neo4j with timestamp filter

### 4. Relationship Management

**create_relationship(source_concept_id, target_concept_id, relationship_type, strength?, description?)**

- Create directed edge between concepts
- relationship_type: "prerequisite" | "relates_to" | "includes"
- strength: 0.0-1.0, default 1.0
- Returns: relationship_id
- Storage: Event store → Neo4j edge (PREREQUISITE, RELATES_TO, or CONTAINS)
- Validates both concepts exist, prevents duplicates

**delete_relationship(relationship_id)**

- Remove relationship (hard delete in Neo4j, preserved in EventStore)
- Returns: Success confirmation

**get_related_concepts(concept_id, direction?, relationship_type?, max_depth?, limit?)**

- Graph traversal to find connected concepts
- direction: "outgoing" | "incoming" | "both" (default: "both")
- max_depth: 1-5, default 2
- limit: Max 50
- Returns: Related concepts with distance (hop count)
- Storage: Neo4j variable-length pattern matching

**get_prerequisites(concept_id, max_depth?)**

- Traverse PREREQUISITE relationships for learning path
- max_depth: 1-10, default 5
- Returns: Ordered chain (deepest-first for learning sequence)
- Storage: Neo4j incoming PREREQUISITE traversal

**get_concept_chain(start_concept_id, end_concept_id, relationship_type?)**

- Find shortest path between two concepts
- Returns: Ordered path array, length (hop count)
- Storage: Neo4j shortestPath algorithm
- Returns empty if no path exists

### 5. Analytics Operations

**list_hierarchy()**

- Generate nested taxonomy: areas → topics → subtopics with counts
- Parameters: None
- Returns: Full hierarchy with concept counts at all levels
- Storage: Neo4j aggregation with 5-minute cache
- Performance: P95 <300ms uncached, <5ms cached

**get_concepts_by_certainty(min_certainty?, max_certainty?, limit?, order?)**

- Filter concepts by certainty score range
- min/max_certainty: 0-100, defaults 0/100
- order: "asc" | "desc", default "asc"
- limit: Max 100, default 50
- Returns: Concepts sorted by certainty_score
- Storage: Neo4j with certainty_score index

---

## Data Schemas

### Concept Schema

**Required**:

- name (string, 1-200 chars, trimmed)
- explanation (string, min 1 char, trimmed)

**Optional**:

- area, topic, subtopic (strings, max 100 chars each)
- certainty_score (float, 0-100, user-provided confidence level)
- examples (string, usage examples)
- prerequisites (string, human-readable description)

**Auto-Generated**:

- concept_id (UUID)
- created_at (ISO 8601 timestamp)
- last_modified (ISO 8601 timestamp)
- version (integer, starts at 1)

**Embeddings**: Generated from `name + ". " + explanation` using all-MiniLM-L6-v2 (384 dimensions). Metadata (area, topic, subtopic, certainty_score) NOT embedded, stored separately for filtering.

### Relationship Schema

**Three Types**:

1. **prerequisite**: Source must be learned before target (directed dependency)
   - Neo4j: `(source)-[:PREREQUISITE]->(target)`
   - Use for: Learning paths, curriculum design

2. **relates_to**: Concepts are related but no ordering (bidirectional association)
   - Neo4j: `(concept)-[:RELATES_TO]->(concept)`
   - Use for: Discovering related topics

3. **includes** (stored as CONTAINS): Hierarchical containment
   - Neo4j: `(parent)-[:CONTAINS]->(child)`
   - Use for: Taxonomies, hierarchical organization

**Required**:

- source_concept_id (UUID, must exist)
- target_concept_id (UUID, must exist)
- relationship_type (one of three above)

**Optional**:

- strength (float, 0.0-1.0, default 1.0)
- description (string, human-readable explanation)

**Auto-Generated**:

- relationship_id (format: `rel-{12chars}`)
- created_at (ISO 8601 timestamp)

**Validation**: Duplicate prevention (same source + target + type), both concepts must exist and not be deleted.

---

## Search & Retrieval Guide

### Decision Tree: Which Search Tool?

**Use semantic search** when:

- Searching by meaning/concept (e.g., "how to iterate" finds "for loops")
- Exploring unfamiliar domains without knowing terminology
- Discovery-oriented queries without specific metadata
- Finding conceptually similar content with different wording

**Use exact search** when:

- Filtering by known metadata (area="Programming", topic="Python")
- Finding by partial name match (case-insensitive)
- Combining multiple filters (area + topic + certainty_score)
- Need high-confidence concepts only (min_certainty filter)

**Use graph navigation** when:

- Building learning paths (get_prerequisites)
- Exploring relationships (get_related_concepts)
- Finding connections between concepts (get_concept_chain)

### Semantic Search Details

**How it works**: Query text → 384-dim embedding → ChromaDB HNSW search → Cosine similarity → Results

**Similarity scores**:

- 0.7-1.0: High similarity (strongly related)
- 0.5-0.7: Moderate similarity (somewhat related)
- 0.3-0.5: Low similarity (weakly related)
- 0.0-0.3: Very low similarity (unrelated)

**Best practices**:

```python
# Good: Natural language
search_concepts_semantic("How to loop through items in Python?")

# Better: Add metadata filter
search_concepts_semantic("async patterns", area="Programming")

# Best: Combine with certainty
search_concepts_semantic("ML algorithms", min_certainty=80)
```

### Graph Traversal Patterns

**Direction semantics**:

- `outgoing`: "What depends on this?" (forward dependencies)
- `incoming`: "What does this depend on?" (prerequisites)
- `both`: "What's connected?" (all relationships)

**Multi-hop traversal**: max_depth parameter controls how many relationship hops to traverse (1-5 for related_concepts, 1-10 for prerequisites).

**Shortest path**: get_concept_chain uses Neo4j's Dijkstra algorithm to find most direct connection. Returns empty array if no path exists.

---

## Reliability & Consistency

### 3-Layer Defense Strategy

**Layer 1: Compensation Manager** (immediate rollback, <1s)

- Triggers on partial failure (one DB succeeds, other fails)
- Immediately rolls back successful write
- Idempotent, safe to call multiple times

**Layer 2: Outbox Pattern** (automatic retry, 1-300s)

- 3 retry attempts per failed projection
- Background worker processes pending outbox entries
- After 3 failures, marked 'failed' (requires manual intervention)

**Layer 3: Consistency Checker** (periodic reconciliation, every 5 min)

- Compares Neo4j vs ChromaDB
- Identifies discrepancies: concepts in one DB only, metadata mismatches
- Reports via consistency_snapshots table

### Error Scenarios

| Scenario       | Neo4j | ChromaDB | Action                          | Recovery Time  |
| -------------- | ----- | -------- | ------------------------------- | -------------- |
| Both succeed   | ✅    | ✅       | None needed                     | 0s (immediate) |
| Neo4j fails    | ❌    | ✅       | Rollback ChromaDB → Retry Neo4j | 1-300s         |
| ChromaDB fails | ✅    | ❌       | Rollback Neo4j → Retry ChromaDB | 1-300s         |
| Both fail      | ❌    | ❌       | Event preserved → Retry both    | 1-300s         |

### Consistency Guarantees for LLMs

**Read-after-write expectations**:

- Immediate reads (<1s): May see partial state during writes
- Delayed reads (>5s): Strong consistency via compensation + retries
- After consistency check (>5min): Guaranteed eventual consistency

**Typical consistency window**: 1-5 minutes

**Monitoring**: Use `get_server_stats()` to check:

- `outbox_pending`: Should be 0-10 normally
- `outbox_failed`: Should be 0 (non-zero requires investigation)

**Recommendation**: Query Neo4j (via get_concept, search_concepts_exact) for authoritative data. ChromaDB (semantic search) may lag by retry window but will converge.

---

## Quick Reference: Tool Selection

| Task                | Tool                      | Why                                |
| ------------------- | ------------------------- | ---------------------------------- |
| Store new knowledge | create_concept            | Event-sourced with dual projection |
| Find by meaning     | search_concepts_semantic  | 384-dim cosine similarity          |
| Find by metadata    | search_concepts_exact     | Indexed Neo4j queries              |
| Build learning path | get_prerequisites         | Incoming PREREQUISITE traversal    |
| Explore connections | get_related_concepts      | Multi-hop graph traversal          |
| Find concept path   | get_concept_chain         | Neo4j shortestPath algorithm       |
| View taxonomy       | list_hierarchy            | Cached aggregation (5min TTL)      |
| Quality audit       | get_concepts_by_certainty | Filter by confidence scores        |
| Link concepts       | create_relationship       | 3 typed relationships              |
| Update knowledge    | update_concept            | Partial updates with re-embedding  |
| Recent activity     | get_recent_concepts       | Time-based filter on last_modified |

---

## Key Implementation Details

**Event Sourcing**: All state changes append-only to SQLite. Current state derived via projections. Complete audit trail, replay capability.

**Idempotency**: All operations safe to retry. Neo4j uses MERGE, ChromaDB delete doesn't fail if missing, compensation checks existence.

**Embedding Cache**: SHA256 hash lookup in SQLite provides 5x performance boost by avoiding redundant model inference.

**Soft vs Hard Delete**: Concepts soft-deleted in Neo4j (preserves graph structure), hard-deleted in ChromaDB (saves storage). Event store always preserved.

**Optimistic Locking**: Version numbers with UNIQUE constraint prevent concurrent modification conflicts.

**Token Efficiency**: Success responses use compact messages, similarity scores rounded to 4 decimals, metadata excluded unless requested, result limits enforced.

---

## Performance Characteristics

| Operation                  | P50   | P95   | Notes                         |
| -------------------------- | ----- | ----- | ----------------------------- |
| create_concept             | 100ms | 300ms | Includes dual projection      |
| get_concept                | 10ms  | 20ms  | Direct Neo4j lookup           |
| search_semantic (cached)   | <1ms  | 10ms  | Embedding cache hit           |
| search_semantic (uncached) | 80ms  | 200ms | Includes embedding generation |
| search_exact               | 20ms  | 50ms  | Uses Neo4j indexes            |
| get_related (1-hop)        | 15ms  | 30ms  | Single pattern match          |
| get_related (3-hop)        | 50ms  | 100ms | Variable-length pattern       |
| list_hierarchy (cached)    | <1ms  | 5ms   | 5-minute TTL cache            |
| list_hierarchy (uncached)  | 150ms | 300ms | Aggregation query             |

---

**End of Guide** - This document contains all essential information for LLM integration with the MCP Knowledge Server.
