# Short-Term Memory MCP - API Documentation

**Version:** 0.2.0
**Status:** Phase 2 Complete
**Last Updated:** 2025-10-10

## Overview

The Short-Term Memory MCP provides 9 tools for managing daily learning concepts through a 5-stage pipeline (Research → AIM → SHOOT → SKIN → Storage). All concepts are automatically cleaned up after 7 days.

## Table of Contents

- [Session Management Tools](#session-management-tools)
- [Concept Management Tools](#concept-management-tools)
- [Stage Data Tools](#stage-data-tools)
- [Storage Integration Tools](#storage-integration-tools)
- [Error Handling](#error-handling)
- [Performance Characteristics](#performance-characteristics)
- [Complete Workflow Example](#complete-workflow-example)

---

## Session Management Tools

### 1. initialize_daily_session

Initialize a new daily learning session with goals.

**Parameters:**

- `learning_goal` (string, required): What you want to learn today
- `building_goal` (string, required): What you want to build today
- `date` (string, optional): Session date in `YYYY-MM-DD` format (defaults to today)

**Returns:**

```json
{
  "status": "success",
  "message": "Session 2025-10-09 created successfully",
  "session_id": "2025-10-09",
  "cleaned_old_sessions": 2
}
```

**Behavior:**

- Session ID is always the date (YYYY-MM-DD format)
- Automatically deletes sessions older than 7 days
- Returns warning if session already exists for that date

**Example:**

```python
result = await initialize_daily_session(
    learning_goal="Learn React Hooks and state management",
    building_goal="Build a todo app with useState and useEffect",
    date="2025-10-09"
)
```

---

### 2. get_active_session

Retrieve today's session with concept statistics.

**Parameters:**

- `date` (string, optional): Session date in `YYYY-MM-DD` format (defaults to today)

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-09",
  "date": "2025-10-09",
  "learning_goal": "Learn React Hooks",
  "building_goal": "Build todo app",
  "session_status": "in_progress",
  "concept_count": 25,
  "concepts_by_status": {
    "identified": 15,
    "chunked": 5,
    "encoded": 3,
    "evaluated": 2,
    "stored": 0
  }
}
```

**Use Cases:**

- Check session progress
- See how many concepts are at each stage
- Resume an interrupted session
- Verify all concepts processed

**Example:**

```python
# Get today's session
result = await get_active_session()

# Get specific date
result = await get_active_session(date="2025-10-09")
```

---

## Concept Management Tools

### 3. store_concepts_from_research

Bulk store all concepts identified during Research session.

**Parameters:**

- `session_id` (string, required): Session ID (YYYY-MM-DD)
- `concepts` (list[dict], required): List of concept dictionaries

**Concept Dictionary Structure:**

```json
{
  "concept_name": "useState Hook",
  "concept_id": "optional-uuid", // Auto-generated if not provided
  "data": {
    "definition": "React Hook for adding state",
    "area": "Frontend",
    "topic": "React",
    "subtopic": "Hooks",
    "resources": ["https://react.dev/useState"],
    "knowledge_status": "new"
  }
}
```

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-09",
  "concepts_created": 25,
  "concept_ids": ["uuid-1", "uuid-2", "..."]
}
```

**Performance:** Batch insert of 25 concepts: ~2.5ms

**Example:**

```python
concepts = [
    {
        "concept_name": "useState Hook",
        "data": {"definition": "...", "area": "Frontend"}
    },
    {
        "concept_name": "useEffect Hook",
        "data": {"definition": "...", "area": "Frontend"}
    }
]

result = await store_concepts_from_research(
    session_id="2025-10-09",
    concepts=concepts
)
```

---

### 4. get_concepts_by_session

Query all concepts for a session with optional filtering.

**Parameters:**

- `session_id` (string, required): Session ID
- `status_filter` (string, optional): Filter by status (`identified`, `chunked`, `encoded`, `evaluated`, `stored`)
- `include_stage_data` (bool, optional): Include stage-by-stage data (default: false)

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-09",
  "count": 25,
  "concepts": [
    {
      "concept_id": "uuid-1",
      "concept_name": "useState Hook",
      "current_status": "chunked",
      "current_data": { "definition": "..." },
      "identified_at": "2025-10-09T10:00:00",
      "chunked_at": "2025-10-09T11:30:00",
      "encoded_at": null,
      "knowledge_mcp_id": null,
      "stage_data": {
        // Only if include_stage_data=true
        "aim": { "chunk_name": "State Management", "questions": ["..."] },
        "shoot": { "self_explanation": "...", "analogies": ["..."] }
      }
    }
  ]
}
```

**Performance:** Query 25 concepts: ~0.1ms

**Example:**

```python
# Get all concepts
all_concepts = await get_concepts_by_session("2025-10-09")

# Get only concepts ready for SHOOT session
chunked = await get_concepts_by_session(
    session_id="2025-10-09",
    status_filter="chunked"
)

# Get with full stage data for review
with_data = await get_concepts_by_session(
    session_id="2025-10-09",
    include_stage_data=True
)
```

---

### 5. update_concept_status

Update a concept's progress status through the pipeline.

**Parameters:**

- `concept_id` (string, required): Concept ID
- `new_status` (string, required): New status (`chunked`, `encoded`, `evaluated`, `stored`)
- `timestamp` (string, optional): ISO timestamp (defaults to now)

**Valid Status Transitions:**

```
identified → chunked    (after AIM session)
chunked → encoded       (after SHOOT session)
encoded → evaluated     (after SKIN session)
evaluated → stored      (after transferring to Knowledge MCP)
```

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "previous_status": "identified",
  "new_status": "chunked",
  "timestamp": "2025-10-09T11:30:00"
}
```

**Automatic Timestamp Fields:**

- `chunked` → updates `chunked_at`
- `encoded` → updates `encoded_at`
- `evaluated` → updates `evaluated_at`
- `stored` → updates `stored_at`

**Example:**

```python
# After AIM session processes a concept
result = await update_concept_status(
    concept_id="uuid-1",
    new_status="chunked"
)
```

---

## Stage Data Tools

### 6. store_stage_data

Store stage-specific data for a concept (UPSERT behavior).

**Parameters:**

- `concept_id` (string, required): Concept ID
- `stage` (string, required): Stage name (`research`, `aim`, `shoot`, `skin`)
- `data` (dict, required): Stage-specific data dictionary

**Stage Data Structures:**

**AIM Stage:**

```json
{
  "chunk_name": "State Management",
  "questions": ["Why is this important?", "How does it relate to X?"],
  "priority": "high"
}
```

**SHOOT Stage:**

```json
{
  "self_explanation": "useState is like a light switch...",
  "difficulty": 3,
  "analogies": ["Light switch", "Variable storage"],
  "examples": ["Counter app", "Form input handling"]
}
```

**SKIN Stage:**

```json
{
  "evaluation": "understood",
  "confidence": 8,
  "gaps": ["Need more practice with complex state"],
  "next_steps": ["Build example app"]
}
```

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "stage": "aim",
  "data_id": 42
}
```

**UPSERT Behavior:** If data already exists for this concept+stage, it's updated rather than creating duplicate.

**Example:**

```python
# Store AIM data
await store_stage_data(
    concept_id="uuid-1",
    stage="aim",
    data={
        "chunk_name": "State Hooks",
        "questions": ["Why?", "How?"],
        "priority": "high"
    }
)

# Update same stage (UPSERT)
await store_stage_data(
    concept_id="uuid-1",
    stage="aim",
    data={
        "chunk_name": "State Hooks",
        "questions": ["Why?", "How?", "When?"],  # Added question
        "priority": "critical"  # Updated priority
    }
)
```

---

### 7. get_stage_data

Retrieve stage-specific data for a concept.

**Parameters:**

- `concept_id` (string, required): Concept ID
- `stage` (string, required): Stage name (`research`, `aim`, `shoot`, `skin`)

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "stage": "aim",
  "data": {
    "chunk_name": "State Management",
    "questions": ["Why?", "How?"]
  },
  "created_at": "2025-10-09T11:30:00"
}
```

**Not Found Response:**

```json
{
  "status": "not_found",
  "message": "No data found for concept uuid-1 at stage aim"
}
```

**Example:**

```python
# Get AIM data for review
aim_data = await get_stage_data(
    concept_id="uuid-1",
    stage="aim"
)

if aim_data['status'] == 'success':
    questions = aim_data['data']['questions']
```

---

## Storage Integration Tools

### 8. mark_concept_stored

Link a concept to its permanent Knowledge MCP ID and mark as stored.

**Parameters:**

- `concept_id` (string, required): Short-term concept ID
- `knowledge_mcp_id` (string, required): Permanent Knowledge MCP ID

**Returns:**

```json
{
  "status": "success",
  "concept_id": "uuid-1",
  "knowledge_mcp_id": "perm-knowledge-12345",
  "stored_at": "2025-10-09T18:00:00"
}
```

**Automatic Actions:**

1. Sets `current_status` to `stored`
2. Updates `stored_at` timestamp
3. Links to `knowledge_mcp_id`

**Example:**

```python
# After transferring concept to Knowledge MCP
result = await mark_concept_stored(
    concept_id="uuid-1",
    knowledge_mcp_id="perm-knowledge-12345"
)
```

---

### 9. get_unstored_concepts

Find all concepts that haven't been transferred to Knowledge MCP yet.

**Parameters:**

- `session_id` (string, required): Session ID

**Returns:**

```json
{
  "status": "success",
  "session_id": "2025-10-09",
  "unstored_count": 3,
  "concepts": [
    {
      "concept_id": "uuid-1",
      "concept_name": "useState Hook",
      "current_status": "evaluated",
      "current_data": {"..."},
      "knowledge_mcp_id": null
    }
  ]
}
```

**Use Cases:**

- Verify all concepts stored before ending session
- Find incomplete transfers
- Resume interrupted storage process

**Example:**

```python
# Check for unstored concepts
result = await get_unstored_concepts("2025-10-09")

if result['unstored_count'] > 0:
    for concept in result['concepts']:
        # Transfer to Knowledge MCP
        knowledge_id = await transfer_to_knowledge_mcp(concept)
        await mark_concept_stored(concept['concept_id'], knowledge_id)
```

---

## Error Handling

All tools return structured error responses:

### Common Error Codes

**SESSION_NOT_FOUND**

```json
{
  "status": "error",
  "error_code": "SESSION_NOT_FOUND",
  "message": "Session 2025-10-09 not found"
}
```

**CONCEPT_NOT_FOUND**

```json
{
  "status": "error",
  "error_code": "CONCEPT_NOT_FOUND",
  "message": "Concept uuid-1 not found"
}
```

**INVALID_STATUS**

```json
{
  "status": "error",
  "error_code": "INVALID_STATUS",
  "message": "Invalid status: invalid_value"
}
```

**INVALID_STAGE**

```json
{
  "status": "error",
  "error_code": "INVALID_STAGE",
  "message": "Invalid stage: invalid_value"
}
```

### Best Practices

1. **Always check `status` field** before processing results
2. **Handle warnings** (e.g., duplicate sessions)
3. **Verify session exists** before storing concepts
4. **Check unstored concepts** before completing session

---

## Performance Characteristics

All performance targets significantly exceeded:

| Operation                       | Target | Actual  | Status          |
| ------------------------------- | ------ | ------- | --------------- |
| Batch insert 25 concepts        | <100ms | ~2.5ms  | ✅ 97% faster   |
| Query session concepts          | <50ms  | ~0.1ms  | ✅ 99.8% faster |
| Update concept status           | <20ms  | ~0.05ms | ✅ 99.7% faster |
| Complete pipeline (25 concepts) | <5s    | ~0.02s  | ✅ 99.6% faster |

**Optimization Features:**

- SQLite WAL mode for concurrent access
- 7 database indexes for query performance
- Transaction batching for bulk operations
- Automatic vacuum for database maintenance

---

## Complete Workflow Example

Here's a full day's workflow using all 9 tools:

```python
from short_term_mcp.tools_impl import *

# ============================================
# RESEARCH SESSION (Morning)
# ============================================

# 1. Initialize session
session = await initialize_daily_session(
    learning_goal="Learn React Hooks comprehensively",
    building_goal="Build a todo app with hooks",
    date="2025-10-09"
)
session_id = session['session_id']

# 2. Store identified concepts
concepts = [
    {
        "concept_name": "useState Hook",
        "data": {
            "definition": "React Hook for adding state to functional components",
            "area": "Frontend",
            "topic": "React",
            "subtopic": "Hooks"
        }
    },
    # ... 24 more concepts
]

result = await store_concepts_from_research(session_id, concepts)
concept_ids = result['concept_ids']

# ============================================
# AIM SESSION (Late Morning)
# ============================================

# 3. Get concepts ready for AIM
concepts = await get_concepts_by_session(session_id, status_filter="identified")

# 4. Process each through AIM
for concept in concepts['concepts']:
    # Store AIM data (chunking + questions)
    await store_stage_data(
        concept_id=concept['concept_id'],
        stage="aim",
        data={
            "chunk_name": "State Management",
            "questions": ["Why important?", "How relate to X?"]
        }
    )

    # Mark as chunked
    await update_concept_status(concept['concept_id'], "chunked")

# ============================================
# SHOOT SESSION (Afternoon)
# ============================================

# 5. Get concepts ready for SHOOT
concepts = await get_concepts_by_session(session_id, status_filter="chunked")

# 6. Process each through SHOOT
for concept in concepts['concepts']:
    # Store SHOOT data (self-explanation + encoding)
    await store_stage_data(
        concept_id=concept['concept_id'],
        stage="shoot",
        data={
            "self_explanation": "useState is like a light switch...",
            "difficulty": 3,
            "analogies": ["Light switch"],
            "examples": ["Counter app"]
        }
    )

    # Mark as encoded
    await update_concept_status(concept['concept_id'], "encoded")

# ============================================
# SKIN SESSION (Evening)
# ============================================

# 7. Get concepts ready for SKIN
concepts = await get_concepts_by_session(session_id, status_filter="encoded")

# 8. Process each through SKIN
for concept in concepts['concepts']:
    # Store SKIN data (evaluation)
    await store_stage_data(
        concept_id=concept['concept_id'],
        stage="skin",
        data={
            "evaluation": "understood",
            "confidence": 8,
            "gaps": ["Need more practice"],
            "next_steps": ["Build example"]
        }
    )

    # Mark as evaluated
    await update_concept_status(concept['concept_id'], "evaluated")

# ============================================
# STORAGE SESSION (End of Day)
# ============================================

# 9. Get concepts ready for storage
unstored = await get_unstored_concepts(session_id)

print(f"Need to store {unstored['unstored_count']} concepts")

# 10. Transfer each to Knowledge MCP
for concept in unstored['concepts']:
    # Get full data for transfer
    full_concept = await get_concepts_by_session(
        session_id,
        include_stage_data=True
    )

    # Transfer to Knowledge MCP (your implementation)
    knowledge_id = await transfer_to_knowledge_mcp(full_concept)

    # Link back to short-term
    await mark_concept_stored(concept['concept_id'], knowledge_id)

# ============================================
# VERIFICATION
# ============================================

# Check session completion
session_stats = await get_active_session(session_id)
print(f"Session complete: {session_stats['concepts_by_status']}")

# Verify all stored
unstored = await get_unstored_concepts(session_id)
assert unstored['unstored_count'] == 0, "Not all concepts stored!"

print("✅ All concepts processed and stored!")
```

---

## Integration with Claude Desktop

To use this MCP server with Claude Desktop, add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "short-term-memory": {
      "command": "python",
      "args": ["-m", "short_term_mcp.server"],
      "cwd": "/Users/ruben/Documents/GitHub/Short-Term-Memory-MCP"
    }
  }
}
```

Then restart Claude Desktop to load the tools.

---

## Support & Development

- **Repository:** `/Users/ruben/Documents/GitHub/Short-Term-Memory-MCP/`
- **Database:** `/Users/ruben/Documents/GitHub/Short-Term-Memory-MCP/data/short_term_memory.db`
- **Test Suite:** 24 tests, all passing
- **Coverage:** >95%
- **Status:** Phase 2 Complete ✅

For issues or questions, see [System-Plan.md](System-Plan.md) for development roadmap.
