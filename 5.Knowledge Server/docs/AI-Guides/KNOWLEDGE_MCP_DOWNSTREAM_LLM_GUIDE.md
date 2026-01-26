# Knowledge MCP Server - Downstream LLM Guide

**Purpose**: Token-efficient reference for LLMs to store and retrieve concepts
**Version**: 1.0 | **Tools**: 14 MCP tools | **Estimated Tokens**: ~1,500

---

## Your Role

You assist the user in researching and identifying **new concepts** to learn. Before researching any concept:

1. **Search existing concepts** to avoid duplicates
2. **Only store genuinely new concepts** not already in the knowledge base
3. **Link new concepts** to related existing ones via relationships

---

## Quick Reference: Essential Tools

| Task                     | Tool                       | When to Use                            |
| ------------------------ | -------------------------- | -------------------------------------- |
| Check if concept exists  | `search_concepts_semantic` | Before creating any concept            |
| Find by exact metadata   | `search_concepts_exact`    | Filter by area/topic/name              |
| Create new concept       | `create_concept`           | Only after confirming it doesn't exist |
| Link concepts            | `create_relationship`      | Connect related concepts               |
| View knowledge structure | `list_hierarchy`           | Understand what areas/topics exist     |

---

## CRITICAL: Before Storing Any Concept

**Always search first to prevent duplicates:**

```
1. search_concepts_semantic(query="<concept name or description>", limit=10)
2. If no matches found with similarity > 0.7, proceed to create
3. If similar concept exists, either:
   - Skip creation (it already exists)
   - Update existing concept if new info is better
   - Create relationship to existing concept if it's related but distinct
```

---

## Storing Concepts

### create_concept

Creates a new concept in the knowledge base.

**Parameters:**
| Parameter | Type | Required | Constraints | Example |
|-----------|------|----------|-------------|---------|
| `name` | string | Yes | 1-200 chars | "Python List Comprehensions" |
| `explanation` | string | Yes | Non-empty | "A concise way to create lists..." |
| `area` | string | No | Max 100 chars | "Programming" |
| `topic` | string | No | Max 100 chars | "Python" |
| `subtopic` | string | No | Max 100 chars | "Data Structures" |
| `source_urls` | string | No | JSON array | `'[{"url": "https://...", "title": "..."}]'` |

**Hierarchy**: `area` → `topic` → `subtopic` (broadest to most specific)

**source_urls JSON format:**

```json
[
  {
    "url": "https://docs.python.org/3/tutorial/datastructures.html",
    "title": "Python Data Structures Tutorial",
    "quality_score": 0.9,
    "domain_category": "official"
  }
]
```

**domain_category options**: `"official"`, `"in_depth"`, `"authoritative"`

**Returns:**

```json
{
  "success": true,
  "concept_id": "uuid-string",
  "message": "Created"
}
```

**Note**: `confidence_score` is calculated automatically based on concept quality (explanation depth, relationships, metadata completeness). Do NOT provide it as a parameter.

---

### update_concept

Updates an existing concept (partial updates supported).

**Parameters:**
| Parameter | Type | Required |
|-----------|------|----------|
| `concept_id` | string | Yes |
| `name` | string | No |
| `explanation` | string | No |
| `area` | string | No |
| `topic` | string | No |
| `subtopic` | string | No |
| `source_urls` | string | No |

**Returns:** `{ "success": true, "updated_fields": ["explanation"], "message": "Updated" }`

---

### create_relationship

Links two concepts together.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_id` | string | Yes | Source concept UUID |
| `target_id` | string | Yes | Target concept UUID |
| `relationship_type` | string | Yes | One of: `"prerequisite"`, `"relates_to"`, `"includes"` |
| `strength` | float | No | 0.0-1.0, default: 1.0 |
| `notes` | string | No | Description of relationship |

**Relationship Types:**

- **prerequisite**: Source must be learned before target. Use for learning paths.
- **relates_to**: Concepts are related (bidirectional semantically). Use for related topics.
- **includes**: Parent contains child. Use for hierarchical containment.

**Example:**

```
create_relationship(
  source_id="uuid-python-basics",
  target_id="uuid-list-comprehensions",
  relationship_type="prerequisite",
  notes="Understanding basic Python syntax is required"
)
```

---

## Retrieving Concepts

### search_concepts_semantic

Finds concepts by meaning using embeddings (ChromaDB).

**Parameters:**
| Parameter | Type | Required | Default | Max |
|-----------|------|----------|---------|-----|
| `query` | string | Yes | - | - |
| `limit` | int | No | 10 | 50 |
| `min_confidence` | float | No | - | 100 |
| `area` | string | No | - | - |
| `topic` | string | No | - | - |

**Returns:**

```json
{
  "success": true,
  "results": [
    {
      "concept_id": "uuid",
      "name": "Python For Loops",
      "similarity": 0.8542,
      "area": "Programming",
      "topic": "Python",
      "confidence_score": 85.0
    }
  ],
  "total": 5
}
```

**Similarity Interpretation:**

- 0.7-1.0: High match (likely duplicate or very related)
- 0.5-0.7: Moderate match (related concept)
- < 0.5: Weak match (different concept)

---

### search_concepts_exact

Finds concepts by exact metadata filters (Neo4j).

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Case-insensitive partial match |
| `area` | string | No | Exact match |
| `topic` | string | No | Exact match |
| `subtopic` | string | No | Exact match |
| `min_confidence` | float | No | Filter by score (0-100) |
| `limit` | int | No | Default: 20, max: 100 |

**Use when:** You know the exact area/topic or need structured filtering.

---

### list_hierarchy

Gets the complete knowledge structure with counts.

**Returns:**

```json
{
  "success": true,
  "areas": [
    {
      "name": "Programming",
      "concept_count": 45,
      "topics": [
        {
          "name": "Python",
          "concept_count": 20,
          "subtopics": [{ "name": "Data Structures", "concept_count": 8 }]
        }
      ]
    }
  ],
  "total_concepts": 150
}
```

**Use when:** Understanding what knowledge areas exist before storing new concepts.

---

### get_concept

Retrieves a single concept by ID.

**Parameters:**
| Parameter | Type | Required |
|-----------|------|----------|
| `concept_id` | string | Yes |
| `include_history` | bool | No (default: false) |

---

### get_related_concepts

Finds concepts connected through relationships.

**Parameters:**
| Parameter | Type | Default | Options |
|-----------|------|---------|---------|
| `concept_id` | string | Required | - |
| `relationship_type` | string | all | prerequisite, relates_to, includes |
| `direction` | string | "outgoing" | outgoing, incoming, both |
| `max_depth` | int | 1 | 1-5 |

---

### get_prerequisites

Gets the prerequisite chain for a concept (learning path).

**Parameters:** `concept_id` (required), `max_depth` (1-10, default: 5)

**Returns:** Ordered chain from deepest prerequisite to target.

---

### get_concepts_by_confidence

Filters concepts by confidence score range.

**Parameters:**
| Parameter | Type | Default |
|-----------|------|---------|
| `min_confidence` | float | 0 |
| `max_confidence` | float | 100 |
| `limit` | int | 20 |
| `sort_order` | string | "asc" |

**Use "asc"** to find concepts needing improvement (low confidence first).
**Use "desc"** to find well-established concepts (high confidence first).

---

## Workflow: Research and Store New Concept

```
Step 1: User mentions concept to research
        ↓
Step 2: Search for existing concept
        search_concepts_semantic(query="<concept>", limit=10)
        ↓
Step 3: Evaluate results
        - similarity > 0.7? → Concept likely exists, inform user
        - similarity 0.5-0.7? → Related concept exists, may need relationship
        - similarity < 0.5? → Concept is new, proceed to create
        ↓
Step 4: Check hierarchy for appropriate area/topic
        list_hierarchy()
        ↓
Step 5: Create new concept
        create_concept(
          name="...",
          explanation="...",
          area="...",
          topic="...",
          subtopic="...",
          source_urls='[{"url": "...", "title": "..."}]'
        )
        ↓
Step 6: Link to related concepts
        create_relationship(source_id="...", target_id="...", relationship_type="...")
```

---

## Best Practices

1. **Always search before creating** - Duplicates waste storage and confuse retrieval
2. **Use consistent hierarchy** - Check `list_hierarchy()` for existing area/topic names
3. **Write quality explanations** - Affects auto-calculated confidence score
4. **Add source URLs** - Improves concept credibility and confidence score
5. **Create relationships** - Well-connected concepts have higher confidence scores
6. **Use semantic search for discovery** - It understands meaning, not just keywords
7. **Use exact search for filtering** - When you know specific metadata values

---

## Response Handling

All tools return:

```json
{
  "success": true/false,
  "message": "...",
  "data": { ... }  // or specific fields like "concept_id", "results", etc.
}
```

**On error:**

```json
{
  "success": false,
  "message": "User-friendly error",
  "error": {
    "type": "validation_error|not_found|database_error",
    "message": "Details"
  }
}
```

---

## Common Patterns

**Check if concept exists before creating:**

```
semantic_results = search_concepts_semantic(query="machine learning basics")
if any result has similarity > 0.7:
    inform user concept exists
else:
    create_concept(name="Machine Learning Basics", ...)
```

**Find all Python concepts:**

```
search_concepts_exact(area="Programming", topic="Python", limit=50)
```

**Get learning path for advanced topic:**

```
get_prerequisites(concept_id="uuid-of-advanced-concept", max_depth=5)
```

**Find concepts needing improvement:**

```
get_concepts_by_confidence(min_confidence=0, max_confidence=50, sort_order="asc")
```

---

_End of Guide_
