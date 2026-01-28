# Skills Specification

## Transfer Memory Profile

**Total Skills:** 7
**Downstream Consumer:** `/create-skill`

---

## Architecture Overview

### System Components

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│   Short-Term Memory MCP     │     │      Knowledge MCP          │
│   (Working Memory Layer)    │────▶│   (Permanent Storage)       │
│                             │     │                             │
│  - Daily sessions           │     │  - Neo4j (graph/relations)  │
│  - Concept pipeline         │     │  - ChromaDB (embeddings)    │
│  - Research cache           │     │  - Event sourcing           │
│  - 7-day retention          │     │  - Permanent storage        │
└─────────────────────────────┘     └─────────────────────────────┘
```

### Data Flow

```
1. Research → STM concepts table (concept_name, status, current_data)
2. Research → STM research_cache table (explanation, source_urls)
3. Transfer → Knowledge MCP (combined data from both tables)
4. Post-transfer → Mark as stored (link IDs)
5. Cleanup → Wait for session expiry (cascade delete)
```

---

## Skill: stm-retrieval-guide

### User's Intent

> "Get concepts from Short-Term Memory correctly with all required data for transfer."

### Summary

| Attribute   | Value                                                      |
| ----------- | ---------------------------------------------------------- |
| **Purpose** | Retrieve concepts and research data from Short-Term Memory |
| **Used By** | transfer-agent, validation-agent                           |
| **Type**    | Reference Guide                                            |

### Skill Content

This skill provides instructions for retrieving complete concept data from Short-Term Memory MCP.

### CRITICAL: Data Lives in TWO Locations

**Concepts are split across two tables:**

| Data           | Table          | Field                          |
| -------------- | -------------- | ------------------------------ |
| `concept_name` | concepts       | `concept_name`                 |
| `concept_id`   | concepts       | `concept_id`                   |
| `status`       | concepts       | `current_status`               |
| `area`         | concepts       | `current_data.area` (JSON)     |
| `topic`        | concepts       | `current_data.topic` (JSON)    |
| `subtopic`     | concepts       | `current_data.subtopic` (JSON) |
| `explanation`  | research_cache | `explanation`                  |
| `source_urls`  | research_cache | `source_urls`                  |

**You MUST query both tables to get complete concept data.**

### Retrieval Tools

#### get_unstored_concepts (Primary)

Use this to get concepts ready for transfer.

```
Parameters:
  session_id: string (required) - Format: "YYYY-MM-DD"

Returns:
  {
    "status": "success",
    "session_id": "2024-01-15",
    "unstored_count": 5,
    "concepts": [
      {
        "concept_id": "uuid-...",
        "concept_name": "Python asyncio",
        "current_status": "evaluated",
        "current_data": {
          "area": "coding-development",    // May be null!
          "topic": "Python",               // May be null!
          "subtopic": "async"              // May be null
        },
        "knowledge_mcp_id": null           // null = not transferred
      }
    ]
  }
```

#### check_research_cache (Required for Explanation)

**ALWAYS call this for each concept to get explanation and source_urls.**

```
Parameters:
  concept_name: string (required) - Exact concept name

Returns:
  {
    "cached": true,
    "entry": {
      "concept_name": "Python asyncio",
      "explanation": "Detailed explanation text...",
      "source_urls": [
        {
          "url": "https://docs.python.org/3/library/asyncio.html",
          "title": "asyncio documentation",
          "quality_score": 1.0,
          "domain_category": "official"
        }
      ],
      "last_researched_at": "2024-01-15T10:30:00Z"
    },
    "cache_age_seconds": 3600
  }

  // If not cached:
  {
    "cached": false,
    "entry": null,
    "cache_age_seconds": null
  }
```

#### get_concept_page (Full View)

Use for detailed concept information including relationships.

```
Parameters:
  concept_id: string (required)

Returns:
  {
    "status": "success",
    "concept_id": "uuid-...",
    "concept_name": "Python asyncio",
    "session_id": "2024-01-15",
    "current_status": "evaluated",
    "knowledge_mcp_id": null,
    "timeline": [...],
    "stage_data": {...},
    "user_questions": [...],
    "relationships": [
      {
        "related_concept_id": "uuid-456",
        "related_concept_name": "Python coroutines",
        "relationship_type": "prerequisite"
      }
    ],
    "current_data": {...}
  }
```

### Complete Retrieval Workflow

```
# Step 1: Get all unstored concepts for today's session
concepts = get_unstored_concepts(session_id="2024-01-15")

# Step 2: For each concept, get the research data
FOR each concept in concepts.concepts:

    # Get explanation and source_urls from research cache
    cache = check_research_cache(concept_name=concept.concept_name)

    IF cache.cached:
        concept.explanation = cache.entry.explanation
        concept.source_urls = cache.entry.source_urls
    ELSE:
        # No research cache - explanation must come from stage_data
        # or the concept cannot be transferred
        stage_data = get_stage_data(concept_id=concept.concept_id, stage="shoot")
        IF stage_data.status == "success":
            concept.explanation = stage_data.data.explanation
            concept.source_urls = stage_data.data.source_urls
        ELSE:
            ADD to errors: "No explanation available for {concept_name}"

    # Extract area/topic from current_data
    concept.area = concept.current_data.area      # May be null
    concept.topic = concept.current_data.topic    # May be null
    concept.subtopic = concept.current_data.subtopic
```

### Concept Status Values

| Status       | Meaning             | Transferable? |
| ------------ | ------------------- | ------------- |
| `identified` | Just discovered     | No            |
| `chunked`    | Broken into pieces  | No            |
| `encoded`    | Vector embedded     | No            |
| `evaluated`  | Ready for review    | Yes           |
| `stored`     | Already transferred | No (skip)     |

### Session Format

Sessions are identified by date string: `"YYYY-MM-DD"`

- Today's session: Use current date
- Get active session: `get_active_session()` returns session_id

### Error Handling

| Error Code          | Meaning             | Action                       |
| ------------------- | ------------------- | ---------------------------- |
| `SESSION_NOT_FOUND` | No session for date | Create session or check date |
| `CONCEPT_NOT_FOUND` | Invalid concept_id  | Re-query concepts            |
| `INVALID_STATUS`    | Bad status value    | Use enum values only         |

---

## Skill: stm-marking-guide

### User's Intent

> "Mark concepts as stored after successful transfer to Knowledge MCP."

### Summary

| Attribute   | Value                                            |
| ----------- | ------------------------------------------------ |
| **Purpose** | Link STM concepts to permanent Knowledge MCP IDs |
| **Used By** | transfer-agent                                   |
| **Type**    | Reference Guide                                  |

### Skill Content

After successfully creating a concept in Knowledge MCP, you MUST mark it as stored in Short-Term Memory.

### mark_concept_stored

```
Parameters:
  concept_id: string (required) - STM concept ID
  knowledge_mcp_id: string (required) - ID returned by Knowledge MCP create_concept

Returns:
  {
    "status": "success",
    "concept_id": "stm-uuid-123",
    "knowledge_mcp_id": "knowledge-uuid-456",
    "stored_at": "2024-01-15T14:30:00Z"
  }
```

### Post-Transfer Workflow

```
# After successful Knowledge MCP create_concept:
IF knowledge_response.success:

    # Mark as stored in STM
    mark_result = mark_concept_stored(
        concept_id=stm_concept.concept_id,
        knowledge_mcp_id=knowledge_response.data.concept_id
    )

    IF mark_result.status == "success":
        LOG "Transferred: {concept_name} -> {knowledge_mcp_id}"
    ELSE:
        LOG "Warning: Transfer succeeded but marking failed"
        # The concept exists in Knowledge MCP but STM thinks it's not transferred
        # On next run, duplicate detection will catch this
```

### mark_session_complete (After All Transfers)

When all concepts in a session are transferred:

```
Parameters:
  session_id: string (required)

Returns (all stored):
  {
    "status": "success",
    "session_id": "2024-01-15",
    "total_concepts": 10,
    "completed_at": "2024-01-15T16:00:00Z"
  }

Returns (some unstored - WARNING):
  {
    "status": "warning",
    "message": "Session has unstored concepts",
    "unstored_count": 2,
    "unstored_concepts": [...]
  }
```

---

## Skill: stm-cleanup-guide

### User's Intent

> "Clean up Short-Term Memory after transfer without losing data."

### Summary

| Attribute   | Value                                          |
| ----------- | ---------------------------------------------- |
| **Purpose** | Understand cleanup limitations and workarounds |
| **Used By** | transfer-agent, cleanup-agent                  |
| **Type**    | Reference Guide                                |

### CRITICAL: No Individual Concept Deletion

**The Short-Term Memory MCP has NO tool to delete individual concepts.**

There is no `delete_concept(concept_id)` tool. This is by design - concepts flow through a pipeline and are cleaned up in batches when sessions expire.

### Available Cleanup Options

#### Option 1: Wait for Auto-Cleanup (Recommended)

Sessions are automatically deleted after 7 days when a new session is created.

```
# Nothing to do - just mark concepts as stored
# They will be cleaned up automatically
```

#### Option 2: Manual Session Cleanup

Delete entire sessions (all concepts in session are CASCADE deleted):

```
Parameters:
  days_to_keep: int (required, minimum 1)

Returns:
  {
    "status": "success",
    "cutoff_date": "2024-01-08",
    "sessions_deleted": 3,
    "concepts_deleted": 45
  }
```

**WARNING:** This deletes ALL concepts in sessions older than `days_to_keep`, including:

- Stored concepts (already transferred)
- Unstored concepts (NOT YET transferred - DATA LOSS!)

### Safe Cleanup Workflow

```
# Step 1: Ensure ALL concepts are transferred first
unstored = get_unstored_concepts(session_id)
IF unstored.unstored_count > 0:
    ABORT "Cannot cleanup - {unstored_count} concepts not transferred"

# Step 2: Mark session complete
mark_session_complete(session_id)

# Step 3: (Optional) Clear old sessions
# Only use if you need to free space immediately
# Otherwise, let auto-cleanup handle it
clear_old_sessions(days_to_keep=7)
```

### What Gets Deleted vs Preserved

| Data             | On Session Delete | Notes                       |
| ---------------- | ----------------- | --------------------------- |
| Concepts         | CASCADE deleted   | All concepts in session     |
| Stage data       | CASCADE deleted   | All stage data for concepts |
| Research cache   | **PRESERVED**     | Independent of sessions     |
| Domain whitelist | **PRESERVED**     | Independent of sessions     |

### Research Cache Cleanup (Separate)

The research cache persists across sessions for reuse. It is NOT automatically cleaned.

To manually clear research cache (rarely needed):

- No MCP tool available
- Requires direct database access

---

## Skill: knowledge-mcp-store-guide

### User's Intent

> "Ensure that we only store truly new concepts, link new concepts to related existing ones."

### Summary

| Attribute   | Value                                                    |
| ----------- | -------------------------------------------------------- |
| **Purpose** | Embedded knowledge for storing concepts in Knowledge MCP |
| **Used By** | transfer-agent                                           |
| **Type**    | Reference Guide                                          |

### Skill Content

This skill provides precise instructions for creating and updating concepts in Knowledge MCP.

### create_concept Parameters

| Parameter     | Type   | Required | Constraints                 |
| ------------- | ------ | -------- | --------------------------- |
| `name`        | string | **Yes**  | 1-200 chars, non-empty      |
| `explanation` | string | **Yes**  | Non-empty                   |
| `area`        | string | **Yes**  | 1-100 chars, use predefined |
| `topic`       | string | **Yes**  | 1-100 chars                 |
| `subtopic`    | string | No       | Max 100 chars               |
| `source_urls` | string | No       | JSON array string format    |

**CRITICAL: `area` and `topic` are REQUIRED. The API will reject concepts without them.**

### Predefined Areas (13 Total)

Use these area slugs. Custom areas are allowed but generate warnings.

| Slug                 | Display Label        |
| -------------------- | -------------------- |
| `coding-development` | Coding & Development |
| `ai-llms`            | AI & LLMs            |
| `productivity`       | Productivity         |
| `learning`           | Learning             |
| `business`           | Business             |
| `health`             | Health               |
| `mindset`            | Mindset              |
| `marketing`          | Marketing            |
| `video-content`      | Video & Content      |
| `spirituality`       | Spirituality         |
| `philosophy`         | Philosophy           |
| `history`            | History              |
| `physics`            | Physics              |

### source_urls JSON Format (CRITICAL)

**Must be a JSON string, NOT a JavaScript object.**

```json
"[{\"url\": \"https://example.com\", \"title\": \"Page Title\", \"quality_score\": 0.9, \"domain_category\": \"official\"}]"
```

Source URL object fields:
| Field | Required | Type | Values |
|-------|----------|------|--------|
| `url` | Yes | string | Full URL |
| `title` | No | string | Page title |
| `quality_score` | No | float | 0.0-1.0 |
| `domain_category` | No | string | "official", "in_depth", "authoritative" |

### update_concept Parameters

| Parameter     | Type   | Required |
| ------------- | ------ | -------- |
| `concept_id`  | string | Yes      |
| `name`        | string | No       |
| `explanation` | string | No       |
| `area`        | string | No       |
| `topic`       | string | No       |
| `subtopic`    | string | No       |
| `source_urls` | string | No       |

**At least ONE field must be provided for update.**

### create_relationship Parameters

| Parameter           | Type   | Required          |
| ------------------- | ------ | ----------------- |
| `source_id`         | string | Yes               |
| `target_id`         | string | Yes               |
| `relationship_type` | string | Yes               |
| `strength`          | float  | No (default: 1.0) |
| `notes`             | string | No                |

### Relationship Types

| Type           | Meaning                              |
| -------------- | ------------------------------------ |
| `prerequisite` | Source must be learned before target |
| `relates_to`   | Concepts are associated              |
| `includes`     | Source contains target               |
| `contains`     | Source contains target (alias)       |

### Merge Strategy

When merging a new concept into an existing one (duplicate detected):

1. **Explanation Merging:**

   ```
   Updated explanation = existing_explanation + "\n\n---\n\nAdditional Information:\n" + new_explanation
   ```

   - Never replace entirely - preserve existing information
   - Clearly demarcate new additions

2. **source_urls Merging:**
   - Parse existing source_urls JSON string
   - Parse new source_urls JSON string
   - Combine arrays
   - Deduplicate by URL
   - Re-serialize to JSON string

3. **Fields to Update:**
   - `explanation` (merged)
   - `source_urls` (combined)
   - Do NOT change: `name`, `area`, `topic` (use existing)

### Success Response

```json
{
  "success": true,
  "message": "Created",
  "data": {
    "concept_id": "uuid-string",
    "warnings": ["Area 'custom' is not a predefined area..."]
  }
}
```

### Error Response Patterns

**Duplicate Detected:**

```json
{
  "success": false,
  "message": "The provided input is invalid.",
  "error": {
    "type": "validation_error",
    "message": "Concept already exists with same name/area/topic. Existing concept_id: abc-123",
    "field": "name",
    "details": {
      "invalid_value": "{\"existing_concept_id\": \"abc-123\"}"
    }
  }
}
```

**Missing Required Field:**

```json
{
  "success": false,
  "message": "The provided input is invalid.",
  "error": {
    "type": "validation_error",
    "message": "area: field required"
  }
}
```

### Duplicate Detection

The Knowledge Server performs automatic duplicate detection:

- Uniqueness constraint: `name + area + topic` combination
- If duplicate exists, returns validation_error with existing concept_id

---

## Skill: knowledge-mcp-retrieve-guide

### User's Intent

> "Check for existing concepts before creating duplicates."

### Summary

| Attribute   | Value                                                              |
| ----------- | ------------------------------------------------------------------ |
| **Purpose** | Embedded knowledge for searching and retrieving from Knowledge MCP |
| **Used By** | validation-agent, categorization-agent, verification-agent         |
| **Type**    | Reference Guide                                                    |

### Skill Content

This skill provides instructions for searching and retrieving concepts from Knowledge MCP.

### search_concepts_semantic Parameters

| Parameter        | Type   | Required | Default         |
| ---------------- | ------ | -------- | --------------- |
| `query`          | string | Yes      | -               |
| `limit`          | int    | No       | 10 (max 50)     |
| `min_confidence` | float  | No       | - (0-100 scale) |
| `area`           | string | No       | -               |
| `topic`          | string | No       | -               |

**Note: `min_confidence` uses 0-100 scale, not 0-1.**

### Similarity Score Interpretation (UPDATED)

| Score     | Meaning          | Action                                   |
| --------- | ---------------- | ---------------------------------------- |
| >= 0.95   | Almost certain   | Duplicate - merge into existing          |
| 0.90-0.95 | Very likely      | Duplicate - merge into existing          |
| 0.85-0.90 | Likely duplicate | Present to user for decision             |
| 0.70-0.85 | Related concept  | Create new, consider adding relationship |
| < 0.70    | Different        | Safe to create new                       |

**Duplicate Threshold: 0.85** (similarity scores above this trigger duplicate handling)

### Semantic Search Response

```json
{
  "success": true,
  "message": "Found",
  "data": {
    "results": [
      {
        "concept_id": "uuid-123",
        "name": "Python Async Programming",
        "similarity": 0.87,
        "area": "coding-development",
        "topic": "Python",
        "confidence_score": 85.0
      }
    ],
    "total": 1
  }
}
```

### search_concepts_exact Parameters

| Parameter        | Type   | Default                               |
| ---------------- | ------ | ------------------------------------- |
| `name`           | string | None (case-insensitive partial match) |
| `area`           | string | None (exact match)                    |
| `topic`          | string | None (exact match)                    |
| `subtopic`       | string | None (exact match)                    |
| `min_confidence` | float  | None (0-100 scale)                    |
| `limit`          | int    | 20 (max 100)                          |

### list_hierarchy Response Structure

```json
{
  "success": true,
  "message": "Hierarchy contains 13 areas with 150 concepts",
  "data": {
    "areas": [
      {
        "name": "philosophy",
        "label": "Philosophy",
        "description": "...",
        "is_predefined": true,
        "concept_count": 45,
        "topics": [
          {
            "name": "Stoicism",
            "concept_count": 20,
            "subtopics": [{ "name": "Virtues", "concept_count": 8 }]
          }
        ]
      }
    ],
    "total_concepts": 150
  }
}
```

### get_concept Parameters

| Parameter         | Type   | Required            |
| ----------------- | ------ | ------------------- |
| `concept_id`      | string | Yes                 |
| `include_history` | bool   | No (default: false) |

### get_related_concepts Parameters

| Parameter           | Type   | Default    |
| ------------------- | ------ | ---------- |
| `concept_id`        | string | required   |
| `relationship_type` | string | None (all) |
| `direction`         | string | "outgoing" |
| `max_depth`         | int    | 1 (max 5)  |

### Agent-Specific Usage

**validation-agent:**

```
# For each concept to validate:
search_query = concept_name + " " + first_100_chars(explanation)
results = search_concepts_semantic(query=search_query, limit=5)

FOR each result in results:
    IF result.similarity >= 0.85:
        FLAG as duplicate
        RECORD existing_concept_id = result.concept_id
```

**categorization-agent:**

```
# Get hierarchy to find valid areas/topics
hierarchy = list_hierarchy()

# Find similar concepts for area/topic hints
similar = search_concepts_semantic(query=concept.explanation, limit=10)

# Use similar concepts' areas/topics as recommendations
FOR each result in similar:
    WEIGHT area by result.similarity
    WEIGHT topic by result.similarity
```

**verification-agent:**

```
# After creating concept, verify it exists
created = get_concept(concept_id=returned_id)
ASSERT created.name == expected_name
```

---

## Skill: validation-skill

### User's Intent

> "Make sure all concepts are at least related to an area... a topic parameter is also required for storing."

### Summary

| Attribute   | Value                                                       |
| ----------- | ----------------------------------------------------------- |
| **Purpose** | Pre-transfer validation rules and duplicate detection logic |
| **Used By** | validation-agent                                            |
| **Type**    | Procedural Guide                                            |

### Skill Content

This skill provides validation rules for checking concepts before transfer.

### Required Field Validation

| Field          | Required               | Validation Rule                        |
| -------------- | ---------------------- | -------------------------------------- |
| `concept_name` | Yes                    | Non-empty string, max 200 chars        |
| `explanation`  | Yes                    | Non-empty string (from research_cache) |
| `area`         | **Yes (for transfer)** | Non-empty string, max 100 chars        |
| `topic`        | **Yes (for transfer)** | Non-empty string, max 100 chars        |

**Both `area` AND `topic` are REQUIRED by Knowledge MCP. Concepts without them cannot be transferred.**

### Validation Algorithm

```
FOR each concept from get_unstored_concepts():

    # Step 0: Get research data
    cache = check_research_cache(concept.concept_name)
    IF NOT cache.cached:
        ADD to errors: "No explanation available"
        CONTINUE

    concept.explanation = cache.entry.explanation
    concept.source_urls = cache.entry.source_urls

    # Step 1: Field Validation
    IF concept.concept_name is empty OR null:
        ADD to errors: "Missing concept name"
        CONTINUE

    IF concept.explanation is empty OR null:
        ADD to errors: "Missing explanation"
        CONTINUE

    # Step 2: Duplicate Detection (UPDATED THRESHOLD: 0.85)
    search_query = concept.concept_name + " " + first_100_chars(concept.explanation)
    results = search_concepts_semantic(query=search_query, limit=5)

    FOR each result in results:
        IF result.similarity >= 0.85:
            ADD to duplicates: {
                short_term_concept: concept,
                existing_concept: result,
                similarity: result.similarity,
                recommendation: determine_recommendation(result.similarity)
            }
            MARK concept as has_duplicate
            BREAK

    IF has_duplicate:
        CONTINUE

    # Step 3: Categorization Check
    # Extract from current_data JSON
    area = concept.current_data.area
    topic = concept.current_data.topic

    IF area is empty OR null:
        ADD "area" to concept.missing

    IF topic is empty OR null:
        ADD "topic" to concept.missing

    IF concept.missing is not empty:
        ADD to uncategorized
        CONTINUE

    # Step 4: Mark as Valid
    ADD to valid_concepts
```

### Duplicate Recommendation Logic (UPDATED)

```
FUNCTION determine_recommendation(similarity):
    IF similarity >= 0.95:
        RETURN "merge"   # Almost certainly same concept
    ELSE IF similarity >= 0.90:
        RETURN "merge"   # Very likely same concept
    ELSE:  # 0.85 - 0.90
        RETURN "review"  # User should decide
```

### Error Categories

| Category        | Meaning                                 | User Action Required          |
| --------------- | --------------------------------------- | ----------------------------- |
| `errors`        | Cannot transfer - missing critical data | Fix in source or skip         |
| `duplicates`    | Potential existing concept (>= 0.85)    | Merge / Skip / Create Anyway  |
| `uncategorized` | Missing area and/or topic               | Main agent assigns area/topic |
| `valid`         | Ready to transfer                       | None                          |

### Output Structure

```json
{
  "summary": {
    "total": 15,
    "valid": 10,
    "duplicates": 3,
    "uncategorized": 2,
    "errors": 0
  },
  "valid_concepts": [
    {
      "concept_id": "stm-uuid",
      "concept_name": "...",
      "explanation": "...",
      "area": "philosophy",
      "topic": "Stoicism",
      "source_urls": [...]
    }
  ],
  "duplicates": [
    {
      "short_term_concept": { /* full STM concept data */ },
      "existing_concept": { /* full Knowledge MCP concept */ },
      "similarity": 0.92,
      "recommendation": "merge"
    }
  ],
  "uncategorized": [
    {
      "concept_id": "...",
      "concept_name": "...",
      "explanation": "...",
      "missing": ["area", "topic"]
    }
  ],
  "errors": [
    {
      "concept_id": "...",
      "concept_name": "...",
      "error": "No explanation available"
    }
  ]
}
```

---

## Skill: categorization-skill

### User's Intent

> "The user gets three possible areas starting with the most likely one, and also to each area three possible topics."

### Summary

| Attribute   | Value                                               |
| ----------- | --------------------------------------------------- |
| **Purpose** | Algorithm for generating area/topic recommendations |
| **Used By** | categorization-agent                                |
| **Type**    | Algorithmic Guide                                   |

### Skill Content

This skill provides the algorithm for recommending areas and topics for uncategorized concepts.

### Knowledge Server Predefined Areas (13 Total)

**These are the ONLY predefined areas. Use these slugs.**

| Slug                 | Label                | Description                                                |
| -------------------- | -------------------- | ---------------------------------------------------------- |
| `coding-development` | Coding & Development | Programming, APIs, frameworks, development tools           |
| `ai-llms`            | AI & LLMs            | Artificial intelligence, machine learning, language models |
| `productivity`       | Productivity         | Efficiency, workflow, time management                      |
| `learning`           | Learning             | Education, study techniques, knowledge acquisition         |
| `business`           | Business             | Entrepreneurship, management, finance                      |
| `health`             | Health               | Physical health, nutrition, exercise                       |
| `mindset`            | Mindset              | Mental models, psychology, self-improvement                |
| `marketing`          | Marketing            | Promotion, advertising, growth                             |
| `video-content`      | Video & Content      | Content creation, video production                         |
| `spirituality`       | Spirituality         | Meditation, mindfulness, consciousness                     |
| `philosophy`         | Philosophy           | Ethics, logic, metaphysics, ancient wisdom                 |
| `history`            | History              | Historical events, figures, analysis                       |
| `physics`            | Physics              | Physical sciences, cosmology                               |

### Recommendation Algorithm

```
FUNCTION generate_recommendations(concept, hierarchy):

    # Step 1: Semantic Search for Similar Concepts
    similar = search_concepts_semantic(
        query = concept.concept_name + " " + concept.explanation,
        limit = 10
    )

    # Step 2: Count Area/Topic Frequency in Similar Concepts
    area_scores = {}
    topic_scores = {}  # Nested: area -> topic -> score

    FOR each result in similar:
        weight = result.similarity
        area = result.area
        topic = result.topic

        area_scores[area] += weight
        IF area not in topic_scores:
            topic_scores[area] = {}
        topic_scores[area][topic] += weight

    # Step 3: Keyword Analysis Against Predefined Areas
    keywords = extract_keywords(concept.explanation)

    FOR each area in PREDEFINED_AREAS:
        keyword_match_score = count_keyword_matches(keywords, area.label)
        area_scores[area.slug] += keyword_match_score * 0.5

    # Step 4: Normalize and Rank
    total_area_score = sum(area_scores.values())
    IF total_area_score > 0:
        FOR each area in area_scores:
            area_scores[area] /= total_area_score

    ranked_areas = sort_by_score(area_scores, descending=True)[:3]

    # Step 5: Build Recommendations
    recommendations = []

    FOR each area in ranked_areas:
        area_rec = {
            "area": area.slug,
            "area_label": area.label,
            "confidence": area.score,
            "reason": generate_reason(area, concept),
            "topic_recommendations": []
        }

        # Get top 3 topics for this area
        area_topics = topic_scores.get(area.slug, {})
        ranked_topics = sort_by_score(area_topics, descending=True)[:3]

        FOR each topic in ranked_topics:
            topic_rec = {
                "topic": topic.name,
                "confidence": topic.score,
                "reason": generate_topic_reason(topic, concept)
            }
            area_rec.topic_recommendations.append(topic_rec)

        # If less than 3 topics, suggest from similar concepts
        WHILE len(area_rec.topic_recommendations) < 3:
            # Add topic suggestions based on concept content
            suggested_topic = suggest_topic_from_keywords(concept, area)
            area_rec.topic_recommendations.append(suggested_topic)

        recommendations.append(area_rec)

    # Step 6: Handle Low Confidence (Custom Area)
    IF max(area_scores.values()) < 0.5:
        # Suggest using best-fit predefined area with custom topic
        best_area = ranked_areas[0]
        recommendations[0].note = "Low confidence - consider if topic is accurate"

    RETURN recommendations
```

### Output Structure

```json
{
  "concept_id": "stm-uuid-123",
  "concept_name": "Amor Fati",
  "explanation_snippet": "The Stoic concept of loving one's fate...",
  "missing": ["area", "topic"],
  "area_recommendations": [
    {
      "area": "philosophy",
      "area_label": "Philosophy",
      "confidence": 0.95,
      "reason": "Concept directly discusses Stoic philosophy principles",
      "topic_recommendations": [
        {
          "topic": "Stoicism",
          "confidence": 0.98,
          "reason": "Amor Fati is a core Stoic concept from Marcus Aurelius"
        },
        {
          "topic": "Ethics",
          "confidence": 0.7,
          "reason": "Related to acceptance and virtue ethics"
        },
        {
          "topic": "Ancient Philosophy",
          "confidence": 0.6,
          "reason": "Historical context of Hellenistic philosophy"
        }
      ]
    },
    {
      "area": "mindset",
      "area_label": "Mindset",
      "confidence": 0.6,
      "reason": "Concept relates to mental attitudes and acceptance",
      "topic_recommendations": [...]
    },
    {
      "area": "spirituality",
      "area_label": "Spirituality",
      "confidence": 0.4,
      "reason": "Touches on acceptance and inner peace",
      "topic_recommendations": [...]
    }
  ]
}
```

### Confidence Calibration

| Confidence | Meaning        | User Experience         |
| ---------- | -------------- | ----------------------- |
| > 0.8      | Strong match   | Auto-select recommended |
| 0.5 - 0.8  | Moderate match | Present options         |
| < 0.5      | Weak match     | Warn about uncertainty  |

---

## Complete Transfer Workflow

### End-to-End Process

```
# =====================================================
# PHASE 1: RETRIEVAL (stm-retrieval-guide)
# =====================================================

# 1.1 Get today's session
session = get_active_session()
session_id = session.session_id

# 1.2 Get unstored concepts
unstored = get_unstored_concepts(session_id=session_id)

# 1.3 Enrich each concept with research data
FOR each concept in unstored.concepts:
    cache = check_research_cache(concept_name=concept.concept_name)
    IF cache.cached:
        concept.explanation = cache.entry.explanation
        concept.source_urls = cache.entry.source_urls
    ELSE:
        MARK concept as error: "No research data"

# =====================================================
# PHASE 2: VALIDATION (validation-skill)
# =====================================================

# 2.1 Validate required fields
# 2.2 Check for duplicates (threshold: 0.85)
# 2.3 Identify uncategorized concepts

validation_result = validate_concepts(enriched_concepts)

# =====================================================
# PHASE 3: CATEGORIZATION (categorization-skill)
# =====================================================

# 3.1 For uncategorized concepts, generate recommendations
FOR each concept in validation_result.uncategorized:
    recommendations = generate_recommendations(concept, list_hierarchy())
    # Main agent assigns area/topic from recommendations

# =====================================================
# PHASE 4: TRANSFER (knowledge-mcp-store-guide)
# =====================================================

# 4.1 Handle duplicates (merge or skip)
FOR each duplicate in validation_result.duplicates:
    IF duplicate.recommendation == "merge":
        # Merge explanation and source_urls into existing
        merged_explanation = existing.explanation + "\n\n---\n\n" + new.explanation
        merged_urls = deduplicate_urls(existing.source_urls + new.source_urls)

        update_concept(
            concept_id=duplicate.existing_concept.concept_id,
            explanation=merged_explanation,
            source_urls=JSON.stringify(merged_urls)
        )

        # Mark STM concept as stored with existing ID
        mark_concept_stored(
            concept_id=duplicate.short_term_concept.concept_id,
            knowledge_mcp_id=duplicate.existing_concept.concept_id
        )

# 4.2 Create new concepts
FOR each concept in validation_result.valid_concepts:
    result = create_concept(
        name=concept.concept_name,
        explanation=concept.explanation,
        area=concept.area,           # REQUIRED
        topic=concept.topic,         # REQUIRED
        subtopic=concept.subtopic,
        source_urls=JSON.stringify(concept.source_urls)
    )

    IF result.success:
        mark_concept_stored(
            concept_id=concept.concept_id,
            knowledge_mcp_id=result.data.concept_id
        )

# 4.3 Create relationships
FOR each concept with relationships:
    FOR each relationship in concept.relationships:
        create_relationship(
            source_id=concept.knowledge_mcp_id,
            target_id=find_knowledge_mcp_id(relationship.related_concept_name),
            relationship_type=relationship.relationship_type
        )

# =====================================================
# PHASE 5: CLEANUP (stm-cleanup-guide)
# =====================================================

# 5.1 Mark session complete (after ALL concepts transferred)
unstored_check = get_unstored_concepts(session_id)
IF unstored_check.unstored_count == 0:
    mark_session_complete(session_id)

# 5.2 Cleanup happens automatically after 7 days
# OR manually: clear_old_sessions(days_to_keep=7)
```

---

## Summary Table

| Skill                        | Used By                                                    | Purpose                                               |
| ---------------------------- | ---------------------------------------------------------- | ----------------------------------------------------- |
| stm-retrieval-guide          | transfer-agent                                             | Get concepts from STM with research data              |
| stm-marking-guide            | transfer-agent                                             | Link STM concepts to Knowledge MCP IDs                |
| stm-cleanup-guide            | transfer-agent, cleanup-agent                              | Understand cleanup limitations (no individual delete) |
| knowledge-mcp-store-guide    | transfer-agent                                             | Create/update/relationship APIs, source_urls format   |
| knowledge-mcp-retrieve-guide | validation-agent, categorization-agent, verification-agent | Search APIs, similarity thresholds (0.85), hierarchy  |
| validation-skill             | validation-agent                                           | Validation algorithm, duplicate detection (>= 0.85)   |
| categorization-skill         | categorization-agent                                       | Recommendation algorithm using predefined areas (13)  |

---

## Quick Reference

### Key Thresholds

| Threshold                 | Value     | Purpose                      |
| ------------------------- | --------- | ---------------------------- |
| Duplicate similarity      | >= 0.85   | Flag as potential duplicate  |
| Auto-merge similarity     | >= 0.90   | Recommend automatic merge    |
| Relationship similarity   | 0.70-0.85 | Suggest relationship instead |
| Categorization confidence | < 0.5     | Warn about weak match        |
| STM retention             | 7 days    | Auto-cleanup period          |

### Error Handling

| Error                    | Source        | Resolution                   |
| ------------------------ | ------------- | ---------------------------- |
| "Missing explanation"    | STM           | Check research_cache         |
| "area: field required"   | Knowledge MCP | Assign area before transfer  |
| "topic: field required"  | Knowledge MCP | Assign topic before transfer |
| "Concept already exists" | Knowledge MCP | Merge or skip                |
| "SESSION_NOT_FOUND"      | STM           | Create session first         |

### Tool Quick Reference

| Task               | STM Tool                | Knowledge MCP Tool         |
| ------------------ | ----------------------- | -------------------------- |
| Get ready concepts | `get_unstored_concepts` | -                          |
| Get explanation    | `check_research_cache`  | -                          |
| Check duplicates   | -                       | `search_concepts_semantic` |
| Get hierarchy      | -                       | `list_hierarchy`           |
| Create concept     | -                       | `create_concept`           |
| Merge concept      | -                       | `update_concept`           |
| Mark transferred   | `mark_concept_stored`   | -                          |
| Create relation    | -                       | `create_relationship`      |
| Cleanup            | `clear_old_sessions`    | -                          |
