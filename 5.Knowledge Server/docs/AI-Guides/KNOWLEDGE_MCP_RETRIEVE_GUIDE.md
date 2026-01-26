# Knowledge MCP Server - Retrieving Concepts Guide

**Purpose**: How to search and browse concepts in the knowledge base
**Version**: 1.0 | **Estimated Tokens**: ~700

---

## Your Role

Before storing any new concept, you MUST search the knowledge base to:

1. **Check if concept already exists** (avoid duplicates)
2. **Find related concepts** to link with new ones
3. **Understand existing knowledge structure**

---

## Tools Overview

| Tool                         | Purpose                  | Use When                           |
| ---------------------------- | ------------------------ | ---------------------------------- |
| `search_concepts_semantic`   | Find by meaning          | Don't know exact name, exploring   |
| `search_concepts_exact`      | Filter by metadata       | Know area/topic, precise filtering |
| `list_hierarchy`             | View knowledge structure | See what areas/topics exist        |
| `get_concept`                | Get single concept       | Have concept_id                    |
| `get_related_concepts`       | Find connected concepts  | Explore relationships              |
| `get_prerequisites`          | Get learning path        | Build dependency chain             |
| `get_concepts_by_confidence` | Filter by quality        | Find concepts to improve           |
| `get_recent_concepts`        | Recent activity          | See latest additions               |

---

## search_concepts_semantic

**Primary search tool.** Finds concepts by meaning using AI embeddings.

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
      "concept_id": "uuid-123",
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
| Score | Meaning | Action |
|-------|---------|--------|
| > 0.7 | High match | Likely exists, don't create duplicate |
| 0.5-0.7 | Moderate match | Related concept, consider relationship |
| < 0.5 | Weak match | Different concept, safe to create new |

**Examples:**

```
# Basic search
search_concepts_semantic(query="how to iterate in Python")

# With filters
search_concepts_semantic(query="machine learning basics", area="AI", min_confidence=70)
```

---

## search_concepts_exact

Filter by exact metadata values. Use when you know specific attributes.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Case-insensitive partial match |
| `area` | string | Exact match |
| `topic` | string | Exact match |
| `subtopic` | string | Exact match |
| `min_confidence` | float | Minimum score (0-100) |
| `limit` | int | Default: 20, max: 100 |

**Returns:** Same structure as semantic search.

**Examples:**

```
# All Python concepts
search_concepts_exact(area="Programming", topic="Python")

# Find by partial name
search_concepts_exact(name="loop")

# High confidence concepts only
search_concepts_exact(area="Programming", min_confidence=80)
```

---

## list_hierarchy

View complete knowledge structure with concept counts.

**Parameters:** None

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

**Use for:** Understanding what exists before creating new concepts, ensuring consistent naming.

---

## get_concept

Retrieve a single concept by ID.

**Parameters:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `concept_id` | string | Yes | - |
| `include_history` | bool | No | false |

**Returns:**

```json
{
  "success": true,
  "concept": {
    "concept_id": "uuid-123",
    "name": "Python List Comprehensions",
    "explanation": "A concise syntax...",
    "area": "Programming",
    "topic": "Python",
    "subtopic": "Data Structures",
    "confidence_score": 85.0,
    "created_at": "2024-01-15T10:30:00Z",
    "last_modified": "2024-01-20T14:22:00Z"
  }
}
```

---

## get_related_concepts

Find concepts connected through relationships.

**Parameters:**
| Parameter | Type | Default | Options |
|-----------|------|---------|---------|
| `concept_id` | string | Required | - |
| `relationship_type` | string | all | prerequisite, relates_to, includes |
| `direction` | string | "outgoing" | outgoing, incoming, both |
| `max_depth` | int | 1 | 1-5 |

**Direction meanings:**

- `outgoing`: "What does this concept lead to?"
- `incoming`: "What leads to this concept?"
- `both`: "What's connected in any direction?"

**Returns:**

```json
{
  "success": true,
  "concept_id": "uuid-123",
  "related": [
    {
      "concept_id": "uuid-456",
      "name": "Generator Expressions",
      "relationship_type": "relates_to",
      "strength": 1.0,
      "distance": 1
    }
  ],
  "total": 3
}
```

---

## get_prerequisites

Get the learning path (prerequisite chain) for a concept.

**Parameters:**
| Parameter | Type | Default | Range |
|-----------|------|---------|-------|
| `concept_id` | string | Required | - |
| `max_depth` | int | 5 | 1-10 |

**Returns:** Concepts ordered from deepest prerequisite to target (learning order).

```json
{
  "success": true,
  "concept_id": "uuid-advanced-topic",
  "chain": [
    { "concept_id": "uuid-1", "name": "Basic Concept", "depth": 3 },
    { "concept_id": "uuid-2", "name": "Intermediate Concept", "depth": 2 },
    { "concept_id": "uuid-3", "name": "Pre-requisite", "depth": 1 }
  ],
  "total": 3
}
```

---

## get_concepts_by_confidence

Filter concepts by confidence score range.

**Parameters:**
| Parameter | Type | Default |
|-----------|------|---------|
| `min_confidence` | float | 0 |
| `max_confidence` | float | 100 |
| `limit` | int | 20 (max: 50) |
| `sort_order` | string | "asc" |

**Sort order:**

- `"asc"`: Lowest confidence first (find concepts needing improvement)
- `"desc"`: Highest confidence first (find well-established concepts)

**Example:**

```
# Find concepts that need work
get_concepts_by_confidence(min_confidence=0, max_confidence=50, sort_order="asc")
```

---

## get_recent_concepts

Get recently created or modified concepts.

**Parameters:**
| Parameter | Type | Default | Range |
|-----------|------|---------|-------|
| `days` | int | 7 | 1-365 |
| `limit` | int | 20 | 1-100 |

---

## Decision Tree: Which Search Tool?

```
Need to find a concept?
│
├─ Know the exact area/topic? → search_concepts_exact
│
├─ Searching by meaning/description? → search_concepts_semantic
│
├─ Want to see all areas/topics? → list_hierarchy
│
├─ Have concept_id already? → get_concept
│
├─ Want to explore connections? → get_related_concepts
│
├─ Building a learning path? → get_prerequisites
│
└─ Looking for low-quality concepts? → get_concepts_by_confidence
```

---

## Common Patterns

**Check if concept exists before creating:**

```
results = search_concepts_semantic(query="machine learning basics", limit=10)
# If any result has similarity > 0.7, concept likely exists
```

**Find all concepts in a topic:**

```
search_concepts_exact(area="Programming", topic="Python", limit=50)
```

**Explore what's related to a concept:**

```
get_related_concepts(concept_id="uuid", direction="both", max_depth=2)
```

**Get learning path for advanced topic:**

```
get_prerequisites(concept_id="uuid-advanced", max_depth=5)
```

**Find concepts needing improvement:**

```
get_concepts_by_confidence(max_confidence=50, sort_order="asc", limit=20)
```

---

## Error Handling

**Success:**

```json
{ "success": true, "results": [...], "total": 5 }
```

**Not Found:**

```json
{ "success": false, "message": "Concept not found", "error": { "type": "not_found" } }
```

**No Results:**

```json
{ "success": true, "results": [], "total": 0, "message": "Found" }
```

---

_End of Retrieve Guide - See Store Guide for creating and linking concepts_
