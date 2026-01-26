# ADR 001: Data Access Patterns

## Status

Accepted

## Context

The MCP Knowledge Server uses event sourcing with dual storage (Neo4j for graph queries + ChromaDB for semantic search). Multiple data access patterns have emerged organically, and we need clear guidelines on when to use each.

### Current Patterns

| Pattern                     | Location                                            | Purpose                                   |
| --------------------------- | --------------------------------------------------- | ----------------------------------------- |
| Repository + Event Sourcing | `services/repository.py`                            | All write operations (CRUD)               |
| Confidence DataAccessLayer  | `services/confidence/data_access.py`                | Specialized aggregate queries for scoring |
| Direct Service Calls        | `tools/search_tools.py`, `tools/analytics_tools.py` | Read-only queries                         |

## Decision

### Architecture: CQRS (Command Query Responsibility Segregation)

We adopt a CQRS-inspired pattern where **writes** and **reads** follow different paths:

```
WRITES (Commands)
─────────────────
Tool → DualStorageRepository → EventStore → Outbox → Projections
                                                      ├── Neo4jProjection
                                                      └── ChromaDBProjection

READS (Queries)
───────────────
Tool → Service (Neo4j/ChromaDB) → Response
```

### Write Operations

**All writes MUST go through the Repository using event sourcing:**

```python
# Correct: Use repository for writes
repository.create_concept(concept_data)  # → ConceptCreated event
repository.update_concept(id, updates)   # → ConceptUpdated event
repository.delete_concept(id)            # → ConceptDeleted event
```

This ensures:

- Event history is preserved (audit trail)
- Both projections (Neo4j, ChromaDB) stay synchronized
- Outbox pattern handles eventual consistency
- Optimistic locking prevents conflicts

**Never write directly to Neo4j or ChromaDB services for concept data.**

### Read Operations

**Reads can bypass the repository and query storage directly:**

1. **Semantic Search** → Query `chromadb_service` directly
   - Use for: similarity search, embedding-based queries
   - Example: `search_concepts_semantic()` in `tools/search_tools.py`

2. **Graph/Filtered Queries** → Query `neo4j_service` directly
   - Use for: exact search, hierarchy, analytics, relationship traversal
   - Example: `search_concepts_exact()`, `list_hierarchy()`

3. **Single Concept Fetch** → Either `repository.get_concept()` or `neo4j_service`
   - Repository method provides consistency guarantee
   - Direct query acceptable for read-only tools

### Confidence Service DataAccessLayer

The confidence service (`services/confidence/data_access.py`) maintains its own `DataAccessLayer` because:

1. **Specialized Aggregate Queries**: Runs graph traversal and aggregation queries not needed elsewhere
2. **Background Worker Context**: Runs in async background workers
3. **Session Management**: Uses `AsyncNeo4jSessionAdapter` for async compatibility

**Important**: DataAccessLayer does NOT create its own Neo4j connections. It receives a shared Neo4jService instance wrapped in an async adapter.

This is acceptable as a specialized read layer but should not be used for general queries.

## Consequences

### Positive

- Clear separation between writes (repository) and reads (direct service)
- Event sourcing provides audit trail and eventual consistency
- Flexible read patterns for different query types

### Negative

- New developers must understand which pattern to use
- Confidence DataAccessLayer creates some code separation

### Mitigations

- This ADR documents the patterns
- Docstrings in repository and tools reference this ADR
- New features should follow these patterns

## References

- `services/repository.py` - DualStorageRepository with event sourcing
- `services/confidence/data_access.py` - Specialized DataAccessLayer
- `tools/search_tools.py` - Read patterns for search
- `tools/analytics_tools.py` - Read patterns for analytics
