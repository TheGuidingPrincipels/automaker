# Session System Prompts Guide

## Overview

This guide provides system prompts and workflows for different session stages in the Short-Term Memory MCP pipeline.

## Pipeline Stages

The SHOOT learning pipeline consists of four stages:

1. **S**COUR - Research and identify concepts
2. **H**ONE - AIM at learning goals
3. **O**UTLINE - SHOOT for understanding
4. **O**RGANIZE - SKIN and store knowledge
5. **T**RANSFER - Move to Knowledge MCP

Each stage has specific tools and workflows.

## RESEARCH Stage (SCOUR)

### Objective

Identify new concepts from research, documentation, or learning materials.

### Tools Available

- `initialize_daily_session` - Start the day's session
- `get_active_session` - Check current session
- `store_concepts_from_research` - Bulk store identified concepts

### Workflow

```python
# 1. Initialize daily session
session = await mcp.initialize_daily_session(
    learning_goal="Learn Python async programming",
    building_goal="Build async web scraper"
)

# 2. Research and identify concepts
# (Manual research or automated extraction)
concepts = [
    {"name": "python asyncio", "data": {"source": "Python docs"}},
    {"name": "async/await syntax", "data": {"source": "Tutorial"}},
    {"name": "event loop", "data": {"source": "Documentation"}}
]

# 3. Store identified concepts
result = await mcp.store_concepts_from_research(
    session_id=session["session_id"],
    concepts=concepts
)

# Result: 3 concepts stored with status "identified"
```

### System Prompt

```
You are in the RESEARCH stage (SCOUR) of the SHOOT learning pipeline.

Your task:
1. Research the topic: {topic}
2. Identify key concepts to learn
3. Store concepts in Short-Term Memory MCP

Use these tools:
- initialize_daily_session (if no session exists)
- store_concepts_from_research (bulk store)

For each concept, provide:
- concept_name: Clear, specific name
- data: Metadata (source, context, etc.)

Store all concepts at once using bulk operation.
```

## AIM Stage (HONE)

### Objective

Refine concepts, add questions, establish relationships.

### Tools Available

- `get_concepts_by_session` - List session concepts
- `get_concepts_by_status` - Filter by status
- `add_concept_question` - Add user questions
- `add_concept_relationship` - Link related concepts
- `update_concept_status` - Update to "chunked"

### Workflow

```python
# 1. Get identified concepts
concepts = await mcp.get_concepts_by_status(
    session_id="2025-01-10",
    status="identified"
)

# 2. Add questions for concepts
for concept in concepts["concepts"]:
    await mcp.add_concept_question(
        concept_id=concept["concept_id"],
        question="How does this work?",
        session_stage="aim"
    )

# 3. Add relationships
await mcp.add_concept_relationship(
    concept_id=concepts["concepts"][0]["concept_id"],
    related_concept_id=concepts["concepts"][1]["concept_id"],
    relationship_type="prerequisite"  # or: related, similar, builds_on
)

# 4. Update status when ready
await mcp.update_concept_status(
    concept_id=concept["concept_id"],
    new_status="chunked"
)
```

### System Prompt

```
You are in the AIM stage (HONE) of the SHOOT learning pipeline.

Your task:
1. Review identified concepts
2. Add clarifying questions
3. Establish relationships between concepts
4. Mark concepts as "chunked" when ready

Use these tools:
- get_concepts_by_status (status="identified")
- add_concept_question (for each concept)
- add_concept_relationship (link related concepts)
- update_concept_status (new_status="chunked")

Relationship types:
- prerequisite: Concept A needed before B
- related: Concepts are related
- similar: Alternative approaches
- builds_on: Concept builds on another
```

## SHOOT Stage (OUTLINE) - WITH CACHE

### Objective

Research concepts deeply using Context7, with caching to prevent duplicate research.

### Tools Available

- `check_research_cache` - Check if concept already researched
- `trigger_research` - Research new concept (Context7)
- `update_research_cache` - Cache research results
- `store_stage_data` - Store SHOOT data
- `update_concept_status` - Update to "encoded"

### Workflow (Session 005 - With Cache)

```python
from short_term_mcp.session_handlers import shoot_stage_handler

# 1. Get concepts ready for research
concepts = await mcp.get_concepts_by_status(
    session_id="2025-01-10",
    status="chunked"
)

# 2. Run SHOOT stage handler (handles caching automatically)
concept_names = [c["concept_name"] for c in concepts["concepts"]]
results = await shoot_stage_handler(concept_names, db)

# Results include:
# - Cache hits (explanation from cache, fast)
# - Cache misses (new research, slower)
# - Cache statistics logged

# 3. Store SHOOT data for each concept
for i, result in enumerate(results):
    concept = concepts["concepts"][i]

    # Store research data
    await mcp.store_stage_data(
        concept_id=concept["concept_id"],
        stage="shoot",
        data={
            "explanation": result["explanation"],
            "source_urls": result["source_urls"],
            "cache_status": result["status"]  # "cache_hit" or "cache_miss"
        }
    )

    # Update status
    await mcp.update_concept_status(
        concept_id=concept["concept_id"],
        new_status="encoded"
    )

# 4. Check cache statistics in logs
# Example: "Cache statistics: 7 hits, 3 misses (70.0% hit rate)"
```

### Manual Workflow (Lower Level)

```python
# If not using shoot_stage_handler, can use tools directly:

for concept in concepts["concepts"]:
    concept_name = concept["concept_name"]

    # Check cache first
    cache = await mcp.check_research_cache(concept_name)

    if cache["cached"]:
        # Use cached result
        print(f"Cache HIT: {concept_name}")
        explanation = cache["entry"]["explanation"]
        source_urls = cache["entry"]["source_urls"]
    else:
        # Research and update cache
        print(f"Cache MISS: {concept_name}")
        research = await mcp.trigger_research(
            concept_name=concept_name,
            research_prompt=f"Explain {concept_name} in detail"
        )
        explanation = research["explanation"]
        source_urls = research["source_urls"]

        # Update cache for future use
        await mcp.update_research_cache(
            concept_name=concept_name,
            explanation=explanation,
            source_urls=source_urls
        )

    # Store SHOOT data
    await mcp.store_stage_data(
        concept_id=concept["concept_id"],
        stage="shoot",
        data={
            "explanation": explanation,
            "source_urls": source_urls
        }
    )
```

### System Prompt (Session 005)

```
You are in the SHOOT stage (OUTLINE) of the SHOOT learning pipeline.

Your task:
1. Research each concept deeply using Context7
2. Use cache to prevent duplicate research
3. Store research results with source URLs
4. Update concept status to "encoded"

Use these tools:
- check_research_cache (check cache first - ALWAYS)
- trigger_research (if cache miss)
- update_research_cache (after research)
- store_stage_data (stage="shoot")
- update_concept_status (new_status="encoded")

IMPORTANT: ALWAYS check cache before researching!
Expected cache hit rate: 40-60%

Workflow:
1. check_research_cache(concept_name)
2. If cached: Use cached explanation and URLs
3. If not cached:
   a. trigger_research(concept_name, prompt)
   b. update_research_cache(concept_name, explanation, source_urls)
4. store_stage_data(concept_id, "shoot", data)
5. update_concept_status(concept_id, "encoded")

Cache benefits:
- <100ms cache hits vs >500ms research
- Consistent explanations across sessions
- Source URLs with quality scores
```

## SKIN Stage (ORGANIZE)

### Objective

Evaluate understanding, store final data.

### Tools Available

- `get_concepts_by_status` - Get encoded concepts
- `store_stage_data` - Store SKIN evaluation data
- `update_concept_status` - Update to "evaluated"

### Workflow

```python
# 1. Get encoded concepts
concepts = await mcp.get_concepts_by_status(
    session_id="2025-01-10",
    status="encoded"
)

# 2. Evaluate each concept
for concept in concepts["concepts"]:
    # Get SHOOT data
    shoot_data = await mcp.get_stage_data(
        concept_id=concept["concept_id"],
        stage="shoot"
    )

    # Evaluate understanding
    evaluation = {
        "understanding_level": "high",  # high, medium, low
        "confidence_score": 0.85,
        "questions_answered": 2,
        "areas_for_review": []
    }

    # Store SKIN data
    await mcp.store_stage_data(
        concept_id=concept["concept_id"],
        stage="skin",
        data=evaluation
    )

    # Update status
    await mcp.update_concept_status(
        concept_id=concept["concept_id"],
        new_status="evaluated"
    )
```

### System Prompt

```
You are in the SKIN stage (ORGANIZE) of the SHOOT learning pipeline.

Your task:
1. Evaluate understanding of each concept
2. Store evaluation data
3. Mark concepts as "evaluated"

Use these tools:
- get_concepts_by_status (status="encoded")
- get_stage_data (stage="shoot") - review research
- store_stage_data (stage="skin") - store evaluation
- update_concept_status (new_status="evaluated")

Evaluation criteria:
- Understanding level: high, medium, low
- Confidence score: 0.0-1.0
- Questions answered vs remaining
- Areas needing more review
```

## TRANSFER Stage

### Objective

Transfer concepts from Short-Term Memory to Knowledge MCP with source URLs.

### Tools Available

- `get_unstored_concepts` - List concepts not yet transferred
- `check_research_cache` - Get source URLs
- `mark_concept_stored` - Mark as transferred
- Knowledge MCP: `create_concept` (with source_urls parameter)

### Workflow (Session 005)

```python
import json

# 1. Get unstored concepts
unstored = await short_term_mcp.get_unstored_concepts(
    session_id="2025-01-10"
)

print(f"Transferring {unstored['unstored_count']} concepts...")

# 2. Transfer each concept
for concept in unstored["concepts"]:
    concept_name = concept["concept_name"]

    # Check cache for source URLs
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
            source_urls=urls_json  # NEW in Session 005
        )

        print(f"✓ {concept_name} ({len(cache['entry']['source_urls'])} URLs)")
    else:
        # Transfer WITHOUT source URLs (fallback)
        knowledge_concept = await knowledge_mcp.create_concept(
            name=concept_name,
            explanation=concept.get("explanation", ""),
            area=concept.get("area"),
            topic=concept.get("topic"),
            subtopic=concept.get("subtopic")
        )

        print(f"✓ {concept_name} (no URLs)")

    # 3. Mark as stored
    await short_term_mcp.mark_concept_stored(
        concept_id=concept["concept_id"],
        knowledge_mcp_id=knowledge_concept["concept_id"]
    )

# 4. Complete session
await short_term_mcp.mark_session_complete(session_id="2025-01-10")
```

### System Prompt (Session 005)

```
You are in the TRANSFER stage of the SHOOT learning pipeline.

Your task:
1. Transfer concepts from Short-Term Memory to Knowledge MCP
2. Include source URLs with quality scores
3. Mark concepts as stored
4. Complete the session

You have access to BOTH MCP servers:
- short_term_mcp: Temporary storage, research cache
- knowledge_mcp: Permanent storage (Neo4j, ChromaDB)

Use these tools:
- short_term_mcp.get_unstored_concepts(session_id)
- short_term_mcp.check_research_cache(concept_name)
- knowledge_mcp.create_concept(..., source_urls=json_string)
- short_term_mcp.mark_concept_stored(concept_id, knowledge_mcp_id)
- short_term_mcp.mark_session_complete(session_id)

Workflow:
1. get_unstored_concepts → List concepts to transfer
2. For each concept:
   a. check_research_cache → Get URLs
   b. create_concept (Knowledge MCP) → With URLs if cached
   c. mark_concept_stored → Link Short-Term to Knowledge
3. mark_session_complete → Finish session

IMPORTANT: Always check cache for URLs!
Knowledge MCP source_urls parameter is optional (backward compatible).

URL format (JSON string):
[
  {
    "url": "https://docs.python.org",
    "title": "Python Docs",
    "quality_score": 1.0,
    "domain_category": "official"
  }
]

Error handling:
- If cache miss: Transfer without URLs (graceful fallback)
- If Knowledge MCP fails: Log error, continue with next concept
- If mark_stored fails: Log error, concept will retry next time
```

## Session Completion

### Objective

Mark session as complete when all concepts transferred.

### Workflow

```python
# Mark session complete
result = await mcp.mark_session_complete(session_id="2025-01-10")

if result["status"] == "success":
    print(f"Session complete: {result['total_concepts']} concepts")
elif result["status"] == "warning":
    print(f"Warning: {result['unstored_count']} concepts not yet stored")
    # Transfer remaining concepts before completing
```

## Code Teacher Integration

### Objective

Provide context awareness for Code Teacher during sessions.

### Tools Available

- `get_todays_concepts` - All concepts from today (cached)
- `get_todays_learning_goals` - Today's goals (cached)
- `search_todays_concepts` - Search concepts by name/content

### Workflow

```python
# Code Teacher checks learning context
goals = await mcp.get_todays_learning_goals()

print(f"Today's goals:")
print(f"  Learning: {goals['learning_goal']}")
print(f"  Building: {goals['building_goal']}")
print(f"  Progress: {goals['concept_count']} concepts")

# Search for specific concept
results = await mcp.search_todays_concepts(search_term="async")

print(f"Found {results['match_count']} matches for 'async'")
```

### System Prompt

```
You are Code Teacher with access to today's learning context.

Use these tools to provide context-aware assistance:
- get_todays_learning_goals → Today's goals and progress
- get_todays_concepts → All concepts being learned
- search_todays_concepts → Find specific concepts

When helping with code:
1. Check today's learning goals
2. Search for related concepts
3. Provide assistance aligned with learning objectives

Example:
User asks about Python asyncio.
1. search_todays_concepts("asyncio")
2. If found: "I see you're learning asyncio today!"
3. Provide help aligned with their learning goal
```

## Monitoring & Maintenance

### Health Checks

```python
# Check system health
health = await mcp.health_check()
print(f"Status: {health['overall_status']}")
print(f"Response time: {health['response_time_ms']}ms")

# Get metrics
metrics = await mcp.get_system_metrics()
print(f"Database size: {metrics['database']['size_mb']} MB")
print(f"Concepts: {metrics['database']['concepts']}")
```

### Cleanup

```python
# Clear old sessions (auto-cleanup runs on session creation)
result = await mcp.clear_old_sessions(days_to_keep=7)
print(f"Deleted {result['sessions_deleted']} old sessions")
```

## Quick Reference

### Status Flow

```
identified → chunked → encoded → evaluated → stored
   ↓          ↓         ↓          ↓          ↓
RESEARCH    AIM      SHOOT      SKIN    TRANSFER
```

### Stage Tools Matrix

| Stage    | Primary Tools                                                 | Status Change        |
| -------- | ------------------------------------------------------------- | -------------------- |
| RESEARCH | store_concepts_from_research                                  | → identified         |
| AIM      | add_concept_question, add_concept_relationship                | identified → chunked |
| SHOOT    | check_research_cache, trigger_research, update_research_cache | chunked → encoded    |
| SKIN     | store_stage_data(stage="skin")                                | encoded → evaluated  |
| TRANSFER | get_unstored_concepts, mark_concept_stored                    | evaluated → stored   |

### Cache Workflow (Session 005)

```
┌──────────────────────┐
│ Check Cache          │
│ check_research_cache │
└──────┬───────────────┘
       │
       ├─ Cached ────────→ Use cached explanation + URLs
       │                   (Fast: <100ms)
       │
       └─ Not Cached ────→ trigger_research
                           ↓
                           update_research_cache
                           (Slow: >500ms, but cached for next time)
```

## Related Documentation

- [PRD-Short-Term-Memory-MCP.md](PRD-Short-Term-Memory-MCP.md) - System architecture
- [Concept-Transfer-Workflow.md](docs/Concept-Transfer-Workflow.md) - Transfer details
- [TROUBLESHOOTING-GUIDE.md](TROUBLESHOOTING-GUIDE.md) - Debug guide
