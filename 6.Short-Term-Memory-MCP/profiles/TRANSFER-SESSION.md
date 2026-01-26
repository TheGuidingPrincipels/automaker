# Transfer Session Profile

## Role

You transfer concepts from Short-Term Memory MCP to permanent Knowledge MCP storage.

## Required Tools

### Short-Term Memory MCP (4 tools)

| Tool                      | Purpose                  |
| ------------------------- | ------------------------ |
| `get_active_session`      | Check session status     |
| `get_concepts_by_session` | Get all concept data     |
| `mark_concept_stored`     | Link to Knowledge MCP ID |
| `mark_session_complete`   | Finalize session         |

### Optional Short-Term Memory Tools

| Tool                    | Purpose                          |
| ----------------------- | -------------------------------- |
| `check_research_cache`  | Get source URLs for transfer     |
| `get_unstored_concepts` | List only untransferred concepts |

### Knowledge MCP (external)

| Tool             | Purpose                |
| ---------------- | ---------------------- |
| `create_concept` | Create permanent entry |

## Workflow

```
1. CHECK session status:
   get_active_session({"date": "YYYY-MM-DD"})
   → Verify concept_count > 0

2. GET concepts to transfer:
   get_concepts_by_session({
     "session_id": "<session_id>",
     "include_stage_data": false
   })
   → Filter: concepts without knowledge_mcp_id

3. FOR EACH concept:

   a. Get source URLs (optional):
      check_research_cache({"concept_name": "<name>"})
      → Extract source_urls if cached

   b. Create in Knowledge MCP:
      knowledge_mcp.create_concept({
        "name": concept.concept_name,
        "explanation": concept.current_data.explanation,
        "area": concept.current_data.category,
        "source_urls": JSON.stringify(source_urls)  // MUST be string!
      })
      → Save: knowledge_mcp_id

   c. Link back:
      mark_concept_stored({
        "concept_id": "<short-term-id>",
        "knowledge_mcp_id": "<knowledge-mcp-id>"
      })

4. COMPLETE session:
   mark_session_complete({"session_id": "<session_id>"})
   → Returns success OR warning with unstored list

5. REPORT results
```

## Data Mapping

### Short-Term → Knowledge MCP

| Short-Term Field             | Knowledge MCP Field         |
| ---------------------------- | --------------------------- |
| `concept_name`               | `name`                      |
| `current_data.explanation`   | `explanation`               |
| `current_data.category`      | `area` / `topic`            |
| `research_cache.source_urls` | `source_urls` (JSON string) |

### CRITICAL: source_urls Format

```python
# CORRECT - JSON string
source_urls = json.dumps([
    {"url": "https://...", "title": "...", "quality_score": 1.0}
])
knowledge_mcp.create_concept(source_urls=source_urls)

# WRONG - Object
knowledge_mcp.create_concept(source_urls=[{"url": "..."}])
```

## Transfer Data Structure

### Input: Concept from Short-Term Memory

```json
{
  "concept_id": "c-abc123",
  "concept_name": "MCP Protocol",
  "current_data": {
    "explanation": "The MCP Protocol...",
    "category": "APIs/Protocols",
    "key_points": [...]
  }
}
```

### Input: Research Cache (optional)

```json
{
  "cached": true,
  "entry": {
    "explanation": "Extended explanation...",
    "source_urls": [{ "url": "https://...", "title": "...", "quality_score": 1.0 }]
  }
}
```

### Output: Knowledge MCP create_concept call

```json
{
  "name": "MCP Protocol",
  "explanation": "The MCP Protocol...",
  "area": "APIs",
  "topic": "Protocols",
  "source_urls": "[{\"url\":\"https://...\",\"title\":\"...\"}]"
}
```

### Output: mark_concept_stored response

```json
{
  "status": "success",
  "concept_id": "c-abc123",
  "knowledge_mcp_id": "kb-xyz789",
  "stored_at": "2025-01-25T16:00:00.000Z"
}
```

## Error Handling

| Error                           | Cause                | Action                        |
| ------------------------------- | -------------------- | ----------------------------- |
| Knowledge MCP fails             | External service     | Log error, continue with next |
| `mark_session_complete` warning | Unstored concepts    | Report which failed, retry    |
| No cache entry                  | Research cache empty | Transfer without source_urls  |

### Recovery Flow

```
IF transfer fails for a concept:
  1. Log: concept_name, error
  2. Continue with next concept
  3. Report all failures at end
  4. User can retry failed transfers
```

## Session Output

### Success Report

```
Transfer Session Complete
━━━━━━━━━━━━━━━━━━━━━━━━━
Session: 2025-01-25

Transferred: 15/15 concepts
With source URLs: 12/15

Session Status: COMPLETED

All concepts now in Knowledge MCP.
```

### Partial Failure Report

```
Transfer Session Partial
━━━━━━━━━━━━━━━━━━━━━━━━
Session: 2025-01-25

Transferred: 13/15 concepts
Failed: 2

Failed Concepts:
- "Concept A": Knowledge MCP timeout
- "Concept B": Invalid data format

Session Status: WARNING (unstored concepts remain)

Retry failed transfers or investigate errors.
```

## Validation Checklist

Before marking session complete:

- [ ] All concepts have `knowledge_mcp_id`
- [ ] No transfer errors occurred
- [ ] Source URLs included where available

## Quick Reference

### Minimum Transfer (no cache)

```
1. get_concepts_by_session
2. For each:
   - knowledge_mcp.create_concept(name, explanation)
   - mark_concept_stored(concept_id, knowledge_mcp_id)
3. mark_session_complete
```

### Full Transfer (with source URLs)

```
1. get_concepts_by_session
2. For each:
   - check_research_cache → get source_urls
   - knowledge_mcp.create_concept(name, explanation, source_urls=JSON.stringify)
   - mark_concept_stored
3. mark_session_complete
```
