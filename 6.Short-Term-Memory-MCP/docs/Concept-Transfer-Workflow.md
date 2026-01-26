# Concept Transfer Workflow

## Overview

This document describes the workflow for transferring concepts from Short-Term Memory MCP to Knowledge MCP with research source URLs.

## Architecture

```
┌─────────────────────────────────────┐
│   Short-Term Memory MCP             │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ Research     │  │  Concepts   │ │
│  │ Cache        │  │  (Session)  │ │
│  │              │  │             │ │
│  │ • concept    │  │ • metadata  │ │
│  │ • explanation│  │ • status    │ │
│  │ • URLs       │  │ • stage data│ │
│  │ • scores     │  │             │ │
│  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────┘
           │
           │ Transfer (Session 5 LLM)
           ↓
┌─────────────────────────────────────┐
│   Knowledge MCP                     │
│                                     │
│  ┌────────────────────────────────┐ │
│  │  Concept Node (Neo4j)          │ │
│  │                                │ │
│  │  • name                        │ │
│  │  • explanation                 │ │
│  │  • area/topic/subtopic         │ │
│  │  • source_urls (JSON)          │ │
│  │    - url                       │ │
│  │    - title                     │ │
│  │    - quality_score             │ │
│  │    - domain_category           │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Session 5 LLM Workflow

The Session 5 LLM has access to **both MCP servers** and orchestrates the transfer:

### Step 1: List Unstored Concepts

```python
# Get concepts that haven't been transferred yet
unstored = await short_term_mcp.get_unstored_concepts(session_id="2025-01-10")

# Example response:
{
    "status": "success",
    "unstored_count": 3,
    "concepts": [
        {
            "concept_id": "c1",
            "concept_name": "python asyncio",
            "current_status": "evaluated",
            "knowledge_mcp_id": null
        },
        # ... more concepts
    ]
}
```

### Step 2: Check Research Cache

For each concept, check if research cache has source URLs:

```python
cache = await short_term_mcp.check_research_cache("python asyncio")

# Example response:
{
    "cached": true,
    "entry": {
        "concept_name": "python asyncio",
        "explanation": "Asynchronous programming in Python using the asyncio library...",
        "source_urls": [
            {
                "url": "https://docs.python.org/3/library/asyncio.html",
                "title": "asyncio — Asynchronous I/O",
                "quality_score": 1.0,
                "domain_category": "official"
            },
            {
                "url": "https://realpython.com/async-io-python/",
                "title": "Async IO in Python: A Complete Walkthrough",
                "quality_score": 0.8,
                "domain_category": "in_depth"
            }
        ],
        "last_researched_at": "2025-01-10T14:30:00",
        "cache_age_seconds": 120
    }
}
```

### Step 3: Transfer to Knowledge MCP

Transfer concept with URLs to Knowledge MCP:

```python
import json

# Serialize source URLs to JSON string (Knowledge MCP expects JSON string)
urls_json = json.dumps(cache["entry"]["source_urls"])

# Create concept in Knowledge MCP with source URLs
knowledge_concept = await knowledge_mcp.create_concept(
    name="python asyncio",
    explanation=cache["entry"]["explanation"],
    area="programming",
    topic="python",
    subtopic="async",
    source_urls=urls_json  # Optional parameter (backward compatible)
)

# Example response:
{
    "concept_id": "knowledge-concept-abc123",
    "name": "python asyncio",
    "explanation": "...",
    "source_urls": "[{...}]"  # Stored as JSON string
}
```

### Step 4: Mark Concept as Stored

Update Short-Term MCP to mark concept as transferred:

```python
result = await short_term_mcp.mark_concept_stored(
    concept_id="c1",
    knowledge_mcp_id=knowledge_concept["concept_id"]
)

# Example response:
{
    "status": "success",
    "concept_id": "c1",
    "knowledge_mcp_id": "knowledge-concept-abc123",
    "stored_at": "2025-01-10T14:35:00"
}
```

**Note**: The cache entry is NOT automatically deleted when marking as stored. Cache cleanup is managed separately to prevent duplicate research across sessions.

## Complete Transfer Code Example

```python
import json

# Get unstored concepts from today's session
session_id = "2025-01-10"
unstored_result = await short_term_mcp.get_unstored_concepts(session_id)

print(f"Transferring {unstored_result['unstored_count']} concepts...")

for concept in unstored_result['concepts']:
    concept_name = concept['concept_name']

    # Check research cache for URLs
    cache = await short_term_mcp.check_research_cache(concept_name)

    if cache["cached"]:
        # Transfer WITH source URLs
        urls_json = json.dumps(cache["entry"]["source_urls"])

        knowledge_concept = await knowledge_mcp.create_concept(
            name=concept_name,
            explanation=cache["entry"]["explanation"],
            area=concept.get("area"),
            topic=concept.get("topic"),
            subtopic=concept.get("subtopic"),
            source_urls=urls_json
        )

        await short_term_mcp.mark_concept_stored(
            concept_id=concept["concept_id"],
            knowledge_mcp_id=knowledge_concept["concept_id"]
        )

        print(f"✓ Transferred: {concept_name} ({len(cache['entry']['source_urls'])} URLs)")
    else:
        # Transfer WITHOUT source URLs (graceful fallback)
        knowledge_concept = await knowledge_mcp.create_concept(
            name=concept_name,
            explanation=concept.get("explanation", ""),
            area=concept.get("area"),
            topic=concept.get("topic"),
            subtopic=concept.get("subtopic")
            # source_urls omitted - backward compatible
        )

        await short_term_mcp.mark_concept_stored(
            concept_id=concept["concept_id"],
            knowledge_mcp_id=knowledge_concept["concept_id"]
        )

        print(f"✓ Transferred: {concept_name} (no URLs)")
```

## Error Handling

### Network Errors

```python
try:
    knowledge_concept = await knowledge_mcp.create_concept(...)
except Exception as e:
    print(f"✗ Failed to transfer {concept_name}: {e}")
    # Continue with next concept (don't mark as stored)
    continue
```

### Missing Cache Data

```python
cache = await short_term_mcp.check_research_cache(concept_name)

if not cache["cached"]:
    # Fallback: Transfer without URLs
    # Or: Trigger research first
    print(f"⚠ No cache for {concept_name}, transferring without URLs")
```

### Invalid Source URLs

```python
try:
    urls_json = json.dumps(cache["entry"]["source_urls"])
except Exception as e:
    print(f"⚠ Invalid URLs for {concept_name}: {e}")
    # Transfer without URLs
    urls_json = None
```

## Knowledge MCP Integration

### Extended Tools

Knowledge MCP's `create_concept` and `update_concept` tools have been extended with an optional `source_urls` parameter:

```python
async def create_concept(
    name: str,
    explanation: str,
    area: Optional[str] = None,
    topic: Optional[str] = None,
    subtopic: Optional[str] = None,
    source_urls: Optional[str] = None  # NEW: JSON string
) -> Dict[str, Any]
```

### URL Format

Source URLs must be a JSON string containing an array:

```json
[
  {
    "url": "https://docs.python.org/3/library/asyncio.html",
    "title": "asyncio — Asynchronous I/O",
    "quality_score": 1.0,
    "domain_category": "official"
  },
  {
    "url": "https://realpython.com/async-io-python/",
    "title": "Async IO in Python",
    "quality_score": 0.8,
    "domain_category": "in_depth"
  }
]
```

### Storage

- **Neo4j**: Stored as `source_urls` property on Concept node (JSON string)
- **ChromaDB**: Stored in metadata (JSON string)
- **Event Store**: Stored in `ConceptCreated` event

## Performance Considerations

### Cache Hit Rate

Expected 40-60% cache hit rate across sessions:

- Common concepts (e.g., "python asyncio") cached once, reused many times
- Research cache persists across sessions
- Duplicate research eliminated

### Transfer Speed

- Cache lookup: <100ms
- Knowledge MCP create: ~200-500ms (Neo4j + ChromaDB writes)
- Total per concept: ~300-600ms

For 10 concepts: ~3-6 seconds total transfer time

## Monitoring

### Cache Statistics

```python
# SHOOT stage logs cache statistics
# Example output:
# INFO: Cache statistics: 7 hits, 3 misses (70.0% hit rate)
```

### Transfer Logging

```python
# Log each transfer
print(f"✓ Transferred: {concept_name} ({url_count} URLs)")
print(f"✓ Transferred: {concept_name} (no URLs)")
print(f"✗ Failed to transfer {concept_name}: {error}")
```

## Cache Cleanup

Cache entries are **not** automatically deleted when concepts are marked as stored. This allows:

- Reuse across sessions (40-60% hit rate)
- Faster SHOOT stage for repeated concepts
- Manual cleanup when needed

To manually clear cache:

```bash
# Clear all cache entries
sqlite3 short_term_mcp.db "DELETE FROM research_cache;"

# Clear old entries (>30 days)
sqlite3 short_term_mcp.db "DELETE FROM research_cache WHERE created_at < datetime('now', '-30 days');"
```

## Future Enhancements

1. **Automatic cache expiration**: TTL for cache entries (e.g., 30 days)
2. **Cache versioning**: Track when research was last updated
3. **URL validation**: Verify URLs are still accessible
4. **Batch transfer**: Transfer multiple concepts in parallel
5. **Rollback**: Undo transfer if Knowledge MCP fails partway through

## Related Documentation

- [PRD-Short-Term-Memory-MCP.md](PRD-Short-Term-Memory-MCP.md) - System architecture
- [TROUBLESHOOTING-GUIDE.md](TROUBLESHOOTING-GUIDE.md) - Cache debugging
- [Session-System-Prompts-Guide.md](Session-System-Prompts-Guide.md) - SHOOT stage workflow
