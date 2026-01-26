# ADR 002: Delete Semantics

## Status

Accepted

## Context

Deleting a concept requires removing it from both Neo4j (graph database) and ChromaDB (vector database). These storage systems have different capabilities and constraints for handling deletions.

### Problem

- Neo4j supports property-based filtering efficiently
- ChromaDB is optimized for vector similarity, not metadata filtering
- We need to preserve audit trails for compliance
- Deleted concepts should not appear in search results

## Decision

### Neo4j: Soft Delete

When a concept is deleted from Neo4j:

```cypher
MATCH (c:Concept {concept_id: $id})
SET c.deleted = true, c.deleted_at = datetime()
```

**Rationale:**

- Preserves graph relationships for audit purposes
- Allows potential restoration if needed
- Maintains referential integrity
- Query filters exclude deleted nodes by default

**Query Pattern:**

```cypher
-- Always include this filter in queries
WHERE (c.deleted IS NULL OR c.deleted = false)
```

### ChromaDB: Hard Delete

When a concept is deleted from ChromaDB:

```python
collection.delete(ids=[concept_id])
```

**Rationale:**

- Vector embeddings cannot be efficiently "soft deleted"
- ChromaDB doesn't support efficient metadata-based filtering for large datasets
- Deleted embeddings would still be included in similarity calculations
- Storage efficiency (vectors are large)

### Event Store: Full History

The EventStore preserves all events regardless of deletion:

```
ConceptCreated → ConceptUpdated → ConceptDeleted
```

**Rationale:**

- Complete audit trail
- Enables event replay for debugging
- Supports future undo/restore functionality

## Implementation

### Delete Flow

```
delete_concept(id)
    ├── EventStore: Append ConceptDeleted event
    ├── Neo4j: SET deleted=true (soft delete)
    └── ChromaDB: DELETE document (hard delete)
```

### Query Behavior

| Storage    | Query Type          | Includes Deleted?  |
| ---------- | ------------------- | ------------------ |
| Neo4j      | Standard queries    | No (filtered)      |
| Neo4j      | Audit/admin queries | Yes (explicit)     |
| ChromaDB   | Semantic search     | No (hard deleted)  |
| EventStore | Event replay        | Yes (full history) |

## Consequences

### Positive

- Deleted concepts don't appear in search results
- Graph structure preserved for audit
- Full event history maintained
- Efficient vector storage (no deleted embeddings)

### Negative

- Inconsistent deletion semantics between stores
- Cannot restore ChromaDB embeddings (must regenerate)
- Soft-deleted Neo4j nodes consume storage

### Mitigations

- Document the difference clearly (this ADR)
- Restoration would regenerate embeddings from concept data
- Periodic cleanup job could archive old soft-deleted nodes

## References

- `services/repository.py` - Delete implementation
- `projections/neo4j_projection.py` - Soft delete handler
- `projections/chromadb_projection.py` - Hard delete handler
