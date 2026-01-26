# Short-Term Memory MCP - Complete API Reference

**Version:** 1.0.0
**Total Tools:** 22
**Last Updated:** 2025-10-10

## Table of Contents

- [Overview](#overview)
- [Tool Categories](#tool-categories)
- [Session Management](#session-management)
- [Concept Tracking](#concept-tracking)
- [Stage Data Management](#stage-data-management)
- [Storage Integration](#storage-integration)
- [Session Completion](#session-completion)
- [Code Teacher Support](#code-teacher-support)
- [Knowledge Graph](#knowledge-graph)
- [Monitoring & Production](#monitoring--production)
- [Error Codes Reference](#error-codes-reference)
- [Usage Examples](#usage-examples)

---

## Overview

The Short-Term Memory MCP provides 22 tools organized into 5 tiers for comprehensive concept lifecycle management. All tools return JSON-serializable dictionaries with consistent error handling.

### Tool Organization

| Tier   | Purpose                 | Tool Count | Phase   |
| ------ | ----------------------- | ---------- | ------- |
| Tier 1 | Critical Pipeline Tools | 9          | Phase 2 |
| Tier 2 | Reliability Tools       | 3          | Phase 4 |
| Tier 3 | Code Teacher Support    | 3          | Phase 5 |
| Tier 4 | Knowledge Graph         | 4          | Phase 6 |
| Tier 5 | Production Monitoring   | 3          | Phase 7 |

### Response Format

All tools return responses in this format:

```json
{
  "status": "success" | "error" | "warning",
  "message": "Human-readable message",
  // ... tool-specific fields
}
```

---

## Tool Categories

### Tier 1: Critical Pipeline Tools (Phase 2)

1. `initialize_daily_session` - Create new learning session
2. `get_active_session` - Get today's session with stats
3. `store_concepts_from_research` - Bulk concept insertion
4. `get_concepts_by_session` - Query concepts with filters
5. `update_concept_status` - Move through pipeline stages
6. `store_stage_data` - Save stage-specific data
7. `get_stage_data` - Retrieve stage data
8. `mark_concept_stored` - Link to Knowledge MCP
9. `get_unstored_concepts` - Find incomplete transfers

### Tier 2: Reliability Tools (Phase 4)

10. `mark_session_complete` - Complete session with validation
11. `clear_old_sessions` - Manual cleanup of old data
12. `get_concepts_by_status` - Filter by pipeline status

### Tier 3: Code Teacher Support (Phase 5)

13. `get_todays_concepts` - Full concept list (cached)
14. `get_todays_learning_goals` - Lightweight goals query (cached)
15. `search_todays_concepts` - Search by name/content (cached)

### Tier 4: Knowledge Graph (Phase 6)

16. `add_concept_question` - Track user questions
17. `get_concept_page` - Complete concept view with timeline
18. `add_concept_relationship` - Build concept relationships
19. `get_related_concepts` - Query relationship graph

### Tier 5: Production Monitoring (Phase 7)

20. `health_check` - System health status
21. `get_system_metrics` - Performance metrics
22. `get_error_log` - Recent error entries

---

## Session Management

### initialize_daily_session

Create a new daily learning session.

**Parameters:**

- `learning_goal` (str, required): What you want to learn today
- `building_goal` (str, required): What you want to build today
- `date` (str, optional): Session date (YYYY-MM-DD), defaults to today

**Returns:**

```json
{
  "status": "success",
  "message": "Session 2025-10-10 created successfully",
  "session_id": "2025-10-10",
  "cleaned_old_sessions": 2
}
```

**Example:**

```python
result = await initialize_daily_session(
    learning_goal="Learn React Hooks",
    building_goal="Build todo app"
)
```

**Notes:**

- Session ID is the date (YYYY-MM-DD)
- Automatically cleans sessions older than 7 days
- Returns warning if session already exists

---

### get_active_session

Get today's active session with concept statistics.

**Parameters:**

- `date` (str, optional): Session date (YYYY-MM-DD), defaults to today

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-10",
  "date": "2025-10-10",
  "learning_goal": "Learn React Hooks",
  "building_goal": "Build todo app",
  "session_status": "in_progress",
  "concept_count": 25,
  "concepts_by_status": {
    "identified": 0,
    "chunked": 0,
    "encoded": 25,
    "evaluated": 0,
    "stored": 0
  }
}
```

**Example:**

```python
# Get today's session
result = await get_active_session()

# Get specific date
result = await get_active_session(date="2025-10-09")
```

---

## Concept Tracking

### store_concepts_from_research

Store all concepts identified in Research session (bulk operation).

**Parameters:**

- `session_id` (str, required): Session ID (YYYY-MM-DD)
- `concepts` (list[dict], required): List of concept dictionaries

**Concept Format:**

```json
{
  "concept_id": "uuid-optional",
  "concept_name": "React useState Hook",
  "data": {
    "definition": "Hook for adding state to functional components",
    "area": "Frontend",
    "topic": "React",
    "subtopic": "Hooks"
  }
}
```

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-10",
  "concepts_created": 25,
  "concept_ids": ["uuid-1", "uuid-2", ...]
}
```

**Example:**

```python
concepts = [
    {
        "concept_name": "useState Hook",
        "data": {"definition": "State management hook", "area": "Frontend"}
    },
    # ... more concepts
]
result = await store_concepts_from_research(session_id="2025-10-10", concepts=concepts)
```

**Notes:**

- Generates UUIDs if not provided
- Atomic transaction (all or nothing)
- Initial status: "identified"
- Maximum 25 concepts per call (configurable via BATCH_SIZE)

---

### get_concepts_by_session

Get all concepts for a session, optionally filtered by status.

**Parameters:**

- `session_id` (str, required): Session ID
- `status_filter` (str, optional): Filter by status (identified/chunked/encoded/evaluated/stored)
- `include_stage_data` (bool, optional): Include stage-by-stage data, defaults to False

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-10",
  "count": 25,
  "concepts": [
    {
      "concept_id": "uuid-1",
      "concept_name": "useState Hook",
      "current_status": "encoded",
      "current_data": {...},
      "user_questions": [],
      "stage_data": {  // if include_stage_data=True
        "aim": {...},
        "shoot": {...}
      }
    }
  ]
}
```

**Example:**

```python
# All concepts
result = await get_concepts_by_session(session_id="2025-10-10")

# Filter by status
result = await get_concepts_by_session(
    session_id="2025-10-10",
    status_filter="encoded"
)

# Include stage data
result = await get_concepts_by_session(
    session_id="2025-10-10",
    include_stage_data=True
)
```

---

### update_concept_status

Update a concept's status and timestamp.

**Parameters:**

- `concept_id` (str, required): Concept ID
- `new_status` (str, required): New status (chunked/encoded/evaluated/stored)
- `timestamp` (str, optional): ISO format timestamp, defaults to now

**Status Progression:**

```
identified → chunked → encoded → evaluated → stored
```

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "previous_status": "chunked",
  "new_status": "encoded",
  "timestamp": "2025-10-10T12:34:56"
}
```

**Example:**

```python
result = await update_concept_status(
    concept_id="uuid-1",
    new_status="chunked"
)
```

---

## Stage Data Management

### store_stage_data

Store stage-specific data (UPSERT operation).

**Parameters:**

- `concept_id` (str, required): Concept ID
- `stage` (str, required): Stage name (research/aim/shoot/skin)
- `data` (dict, required): Stage-specific data

**Stage Data Examples:**

**AIM (Chunking):**

```json
{
  "chunk_name": "State Hooks",
  "questions": ["Why use hooks?", "How do hooks work?"],
  "priority": "high"
}
```

**SHOOT (Encoding):**

```json
{
  "self_explanation": "useState lets you add state to functional components...",
  "difficulty": 3,
  "analogies": ["Like a light switch"],
  "examples": ["Counter app"]
}
```

**SKIN (Evaluation):**

```json
{
  "understanding_level": 4,
  "confidence": "high",
  "gaps": [],
  "reviewed": true
}
```

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "stage": "aim",
  "message": "Stage data stored successfully"
}
```

**Example:**

```python
result = await store_stage_data(
    concept_id="uuid-1",
    stage="aim",
    data={
        "chunk_name": "State Hooks",
        "questions": ["Why?", "How?"]
    }
)
```

**Notes:**

- UPSERT behavior: creates or updates
- Can be called multiple times per stage
- Data merged with existing stage data

---

### get_stage_data

Retrieve stage-specific data for a concept.

**Parameters:**

- `concept_id` (str, required): Concept ID
- `stage` (str, required): Stage name (research/aim/shoot/skin)

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "stage": "aim",
  "data": {
    "chunk_name": "State Hooks",
    "questions": ["Why?", "How?"]
  },
  "created_at": "2025-10-10T12:34:56"
}
```

**Example:**

```python
result = await get_stage_data(concept_id="uuid-1", stage="aim")
```

---

## Storage Integration

### mark_concept_stored

Mark concept as stored in Knowledge MCP.

**Parameters:**

- `concept_id` (str, required): Concept ID
- `knowledge_mcp_id` (str, required): ID from Knowledge MCP

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "concept_name": "useState Hook",
  "knowledge_mcp_id": "perm-uuid-1",
  "stored_at": "2025-10-10T12:34:56"
}
```

**Example:**

```python
result = await mark_concept_stored(
    concept_id="uuid-1",
    knowledge_mcp_id="perm-uuid-1"
)
```

**Notes:**

- Updates status to "stored"
- Sets stored_at timestamp
- Links short-term to long-term storage

---

### get_unstored_concepts

Get all concepts not yet stored in Knowledge MCP.

**Parameters:**

- `session_id` (str, required): Session ID

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-10",
  "unstored_count": 3,
  "unstored_concepts": [
    {
      "concept_id": "uuid-1",
      "concept_name": "useState Hook",
      "current_status": "evaluated"
    }
  ]
}
```

**Example:**

```python
result = await get_unstored_concepts(session_id="2025-10-10")
```

**Use Case:** Verify all concepts transferred before completing session

---

## Session Completion

### mark_session_complete

Mark session as complete after all concepts stored.

**Parameters:**

- `session_id` (str, required): Session ID

**Returns:**

**Success:**

```json
{
  "status": "success",
  "session_id": "2025-10-10",
  "message": "Session marked as completed"
}
```

**Warning (incomplete):**

```json
{
  "status": "warning",
  "message": "Cannot complete session: 3 concepts not stored",
  "session_id": "2025-10-10",
  "unstored_count": 3,
  "unstored_concepts": [...]
}
```

**Example:**

```python
result = await mark_session_complete(session_id="2025-10-10")
```

**Notes:**

- Validates all concepts stored
- Prevents data loss
- Idempotent operation

---

### clear_old_sessions

Manual cleanup of sessions older than specified days.

**Parameters:**

- `days_to_keep` (int, optional): Days of data to retain, defaults to 7

**Returns:**

```json
{
  "status": "success",
  "days_to_keep": 7,
  "cutoff_date": "2025-10-03",
  "sessions_deleted": 5,
  "message": "Deleted 5 sessions older than 2025-10-03"
}
```

**Example:**

```python
# Use default 7 days
result = await clear_old_sessions()

# Custom retention
result = await clear_old_sessions(days_to_keep=14)
```

**Notes:**

- CASCADE delete (removes concepts and stage data)
- Automatic cleanup runs on session creation
- Manual cleanup for custom retention periods

---

### get_concepts_by_status

Get concepts filtered by status (convenience wrapper).

**Parameters:**

- `session_id` (str, required): Session ID
- `status` (str, required): Status to filter by

**Returns:**
Same as `get_concepts_by_session` with status_filter

**Example:**

```python
result = await get_concepts_by_status(
    session_id="2025-10-10",
    status="encoded"
)
```

---

## Code Teacher Support

### get_todays_concepts

Get all concepts from today's session (cached 5 minutes).

**Parameters:** None

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-10",
  "date": "2025-10-10",
  "concept_count": 25,
  "concepts": [...],
  "concepts_by_status": {...},
  "cache_hit": true
}
```

**Example:**

```python
result = await get_todays_concepts()
```

**Cache:**

- TTL: 5 minutes
- Key: "todays_concepts"
- Automatic invalidation

---

### get_todays_learning_goals

Get today's learning and building goals (cached 5 minutes).

**Parameters:** None

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-10",
  "date": "2025-10-10",
  "learning_goal": "Learn React Hooks",
  "building_goal": "Build todo app",
  "cache_hit": false
}
```

**Example:**

```python
result = await get_todays_learning_goals()
```

---

### search_todays_concepts

Search today's concepts by name or content (cached per query).

**Parameters:**

- `search_term` (str, required): Search term (case-insensitive)

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-10",
  "search_term": "hook",
  "result_count": 5,
  "concepts": [...],
  "cache_hit": true
}
```

**Example:**

```python
result = await search_todays_concepts(search_term="useState")
```

**Search:**

- Case-insensitive
- Searches concept_name and current_data JSON
- Cached per unique search term

---

## Knowledge Graph

### add_concept_question

Track user question about a concept.

**Parameters:**

- `concept_id` (str, required): Concept ID
- `question` (str, required): User's question
- `session_stage` (str, required): Stage when asked (research/aim/shoot/skin)

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "concept_name": "useState Hook",
  "question_added": "How does useState work internally?",
  "total_questions": 3
}
```

**Example:**

```python
result = await add_concept_question(
    concept_id="uuid-1",
    question="How does useState work internally?",
    session_stage="shoot"
)
```

---

### get_concept_page

Get complete concept view with timeline and all data.

**Parameters:**

- `concept_id` (str, required): Concept ID

**Returns:**

```json
{
  "status": "success",
  "concept": {
    "concept_id": "uuid-1",
    "concept_name": "useState Hook",
    "current_status": "stored",
    "session_id": "2025-10-10",
    "knowledge_mcp_id": "perm-uuid-1",
    "current_data": {...},
    "user_questions": [...],
    "timeline": [
      {"stage": "identified", "timestamp": "2025-10-10T10:00:00"},
      {"stage": "chunked", "timestamp": "2025-10-10T11:00:00"},
      {"stage": "encoded", "timestamp": "2025-10-10T12:00:00"},
      {"stage": "evaluated", "timestamp": "2025-10-10T13:00:00"},
      {"stage": "stored", "timestamp": "2025-10-10T14:00:00"}
    ],
    "stage_data": {
      "aim": {...},
      "shoot": {...},
      "skin": {...}
    }
  }
}
```

**Example:**

```python
result = await get_concept_page(concept_id="uuid-1")
```

---

### add_concept_relationship

Build relationship between two concepts.

**Parameters:**

- `concept_id` (str, required): Source concept ID
- `related_concept_id` (str, required): Target concept ID
- `relationship_type` (str, required): Type (prerequisite/related/similar/builds_on)

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "concept_name": "useState Hook",
  "related_to": {
    "concept_id": "uuid-2",
    "concept_name": "useEffect Hook",
    "relationship_type": "related"
  },
  "total_relationships": 3
}
```

**Example:**

```python
result = await add_concept_relationship(
    concept_id="uuid-1",
    related_concept_id="uuid-2",
    relationship_type="prerequisite"
)
```

**Relationship Types:**

- `prerequisite` - Must learn before
- `related` - Connected topics
- `similar` - Similar concepts
- `builds_on` - Extends concept

---

### get_related_concepts

Query concept relationships.

**Parameters:**

- `concept_id` (str, required): Concept ID
- `relationship_type` (str, optional): Filter by type

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "concept_name": "useState Hook",
  "relationship_filter": "prerequisite",
  "related_count": 2,
  "related_concepts": [
    {
      "concept_id": "uuid-2",
      "concept_name": "React Components",
      "relationship_type": "prerequisite",
      "current_status": "stored",
      "session_id": "2025-10-09"
    }
  ]
}
```

**Example:**

```python
# All relationships
result = await get_related_concepts(concept_id="uuid-1")

# Filter by type
result = await get_related_concepts(
    concept_id="uuid-1",
    relationship_type="prerequisite"
)
```

---

## Monitoring & Production

### health_check

Check system health and database status.

**Parameters:** None

**Returns:**

```json
{
  "status": "success",
  "overall_status": "healthy",
  "timestamp": "2025-10-10T12:34:56",
  "response_time_ms": 12.34,
  "components": {
    "database": {
      "status": "healthy",
      "connection": "active",
      "integrity": "ok",
      "size_bytes": 123456,
      "db_path": "/path/to/db"
    },
    "cache": {
      "status": "operational",
      "size": 5,
      "ttl_seconds": 300
    }
  }
}
```

**Example:**

```python
result = await health_check()
if result["overall_status"] != "healthy":
    print("System degraded!")
```

**Performance:** <50ms (target), ~12ms (actual)

---

### get_system_metrics

Get comprehensive system metrics.

**Parameters:** None

**Returns:**

```json
{
  "status": "success",
  "timestamp": "2025-10-10T12:34:56",
  "database": {
    "size_bytes": 123456,
    "size_mb": 0.12,
    "sessions": 3,
    "concepts": 75,
    "stage_data_entries": 300
  },
  "operations": {
    "reads": 150,
    "writes": 75,
    "queries": 225,
    "errors": 0
  },
  "performance": {
    "read_times": {
      "count": 150,
      "avg_ms": 0.5,
      "min_ms": 0.1,
      "max_ms": 2.0
    },
    "write_times": {...},
    "query_times": {...}
  },
  "cache": {
    "entries": 5,
    "ttl_seconds": 300
  }
}
```

**Example:**

```python
result = await get_system_metrics()
print(f"Database size: {result['database']['size_mb']} MB")
print(f"Total concepts: {result['database']['concepts']}")
print(f"Average query time: {result['performance']['query_times']['avg_ms']} ms")
```

**Performance:** <100ms (target), ~20ms (actual)

---

### get_error_log

Get recent error log entries.

**Parameters:**

- `limit` (int, optional): Max errors to return (1-100), defaults to 10
- `error_type` (str, optional): Filter by error type

**Returns:**

```json
{
  "status": "success",
  "timestamp": "2025-10-10T12:34:56",
  "filter": {
    "limit": 10,
    "error_type": "DatabaseError"
  },
  "error_count": 2,
  "errors": [
    {
      "timestamp": "2025-10-10T12:30:00",
      "error_type": "DatabaseError",
      "message": "Connection timeout",
      "context": {
        "operation": "query",
        "duration_ms": 5001
      }
    }
  ]
}
```

**Example:**

```python
# Get last 10 errors
result = await get_error_log()

# Get last 50 DatabaseErrors
result = await get_error_log(limit=50, error_type="DatabaseError")
```

**Performance:** <50ms for 50 errors

---

## Error Codes Reference

### Common Error Codes

| Code                | Description               | Cause                 | Solution                    |
| ------------------- | ------------------------- | --------------------- | --------------------------- |
| `SESSION_NOT_FOUND` | Session doesn't exist     | Invalid session_id    | Create session first        |
| `CONCEPT_NOT_FOUND` | Concept doesn't exist     | Invalid concept_id    | Verify concept ID           |
| `INVALID_STATUS`    | Invalid status value      | Typo in status        | Use valid status            |
| `INVALID_STAGE`     | Invalid stage value       | Typo in stage         | Use research/aim/shoot/skin |
| `UPDATE_FAILED`     | Database update failed    | Database issue        | Check database health       |
| `DATABASE_ERROR`    | Database operation failed | Connection/lock issue | Restart, check logs         |

### Error Response Format

```json
{
  "status": "error",
  "error_code": "SESSION_NOT_FOUND",
  "message": "Session 2025-10-10 not found"
}
```

### Handling Errors

```python
result = await initialize_daily_session(learning_goal="...", building_goal="...")

if result["status"] == "error":
    error_code = result.get("error_code")
    if error_code == "SESSION_NOT_FOUND":
        # Handle missing session
        pass
    else:
        # Handle other errors
        print(f"Error: {result['message']}")
```

---

## Usage Examples

### Complete Daily Workflow

```python
# 1. Initialize session
session = await initialize_daily_session(
    learning_goal="Learn React Hooks",
    building_goal="Build todo app"
)
session_id = session["session_id"]

# 2. Store concepts from Research
concepts = [
    {"concept_name": "useState", "data": {...}},
    {"concept_name": "useEffect", "data": {...}},
    # ... 25 total concepts
]
await store_concepts_from_research(session_id, concepts)

# 3. AIM Session - Chunk concepts
concepts_result = await get_concepts_by_session(session_id)
for concept in concepts_result["concepts"]:
    # Store AIM data
    await store_stage_data(
        concept["concept_id"],
        "aim",
        {"chunk_name": "State Hooks", "questions": [...]}
    )
    # Update status
    await update_concept_status(concept["concept_id"], "chunked")

# 4. SHOOT Session - Encode concepts
encoded_concepts = await get_concepts_by_status(session_id, "chunked")
for concept in encoded_concepts["concepts"]:
    await store_stage_data(
        concept["concept_id"],
        "shoot",
        {"self_explanation": "...", "difficulty": 3}
    )
    await update_concept_status(concept["concept_id"], "encoded")

# 5. SKIN Session - Evaluate
for concept in await get_concepts_by_status(session_id, "encoded")["concepts"]:
    await store_stage_data(
        concept["concept_id"],
        "skin",
        {"understanding_level": 4, "confidence": "high"}
    )
    await update_concept_status(concept["concept_id"], "evaluated")

# 6. Transfer to Knowledge MCP
for concept in await get_concepts_by_status(session_id, "evaluated")["concepts"]:
    # Transfer to permanent storage
    knowledge_id = transfer_to_knowledge_mcp(concept)
    await mark_concept_stored(concept["concept_id"], knowledge_id)

# 7. Complete session
await mark_session_complete(session_id)
```

### Code Teacher Integration

```python
# At start of coding session
concepts = await get_todays_concepts()
print(f"Today's focus: {concepts['concept_count']} concepts")

# During coding
search_result = await search_todays_concepts("useState")
print(f"Found {search_result['result_count']} related concepts")

# Quick goal reminder
goals = await get_todays_learning_goals()
print(f"Learning: {goals['learning_goal']}")
```

### Monitoring

```python
# Health check at session start
health = await health_check()
if health["overall_status"] != "healthy":
    print("Warning: System degraded")
    print(f"Response time: {health['response_time_ms']}ms")

# Weekly metrics review
metrics = await get_system_metrics()
print(f"Database: {metrics['database']['size_mb']} MB")
print(f"Total concepts: {metrics['database']['concepts']}")
print(f"Avg query: {metrics['performance']['query_times']['avg_ms']}ms")

# Check for errors
errors = await get_error_log(limit=20)
if errors["error_count"] > 0:
    print(f"Found {errors['error_count']} recent errors")
    for error in errors["errors"]:
        print(f"  {error['error_type']}: {error['message']}")
```

---

## Performance Characteristics

| Operation         | Target | Actual | Notes                     |
| ----------------- | ------ | ------ | ------------------------- |
| Health Check      | <50ms  | ~12ms  | Includes DB + cache check |
| Batch Insert (25) | <100ms | ~2.5ms | Atomic transaction        |
| Query Session     | <50ms  | ~0.1ms | With indexes              |
| Update Status     | <20ms  | <1ms   | Single concept            |
| Complete Pipeline | <5s    | ~0.02s | 25 concepts, all stages   |
| Cache Hit         | <1ms   | <1ms   | In-memory lookup          |
| Cache Miss        | <50ms  | ~10ms  | Query + cache             |

---

## Support & Resources

### Documentation

- [Production Guide](Production-Guide.md) - Deployment & operations
- [System Plan](System-Plan.md) - Complete implementation plan
- [Integration Testing](Integration-Testing.md) - Test workflows
- [Code Teacher API](Code-Teacher-API.md) - Detailed Code Teacher docs
- [Future Features API](Future-Features-API.md) - Knowledge graph docs

### Quick Reference

- **Total Tools**: 22
- **Test Coverage**: 159 tests, 100% pass rate
- **Database**: SQLite with WAL mode
- **Cache**: 5-minute TTL
- **Retention**: 7-day auto-cleanup

---

**End of API Reference**
