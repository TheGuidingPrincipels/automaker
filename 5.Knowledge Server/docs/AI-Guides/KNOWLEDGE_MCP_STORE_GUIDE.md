# Knowledge MCP Server - Storing Concepts Guide

**Purpose**: How to store new concepts in the knowledge base
**Version**: 1.0 | **Estimated Tokens**: ~800

---

## Your Role

You assist the user in storing **new concepts** they want to learn. Before storing any concept:

1. **Search existing concepts first** (see Retrieval Guide)
2. **Only store genuinely new concepts** not already in the knowledge base
3. **Link new concepts** to related existing ones via relationships

---

## Tools Overview

| Tool                  | Purpose                        |
| --------------------- | ------------------------------ |
| `create_concept`      | Store a new concept            |
| `update_concept`      | Modify an existing concept     |
| `create_relationship` | Link two concepts together     |
| `delete_concept`      | Remove a concept (soft delete) |
| `delete_relationship` | Remove a relationship          |

---

## create_concept

Creates a new concept in the knowledge base.

**Parameters:**
| Parameter | Type | Required | Constraints | Example |
|-----------|------|----------|-------------|---------|
| `name` | string | Yes | 1-200 chars | "Python List Comprehensions" |
| `explanation` | string | Yes | Non-empty | "A concise way to create lists..." |
| `area` | string | No | Max 100 chars | "Programming" |
| `topic` | string | No | Max 100 chars | "Python" |
| `subtopic` | string | No | Max 100 chars | "Data Structures" |
| `source_urls` | string | No | JSON array | See format below |

**Hierarchy**: `area` → `topic` → `subtopic` (broadest to most specific)

**source_urls JSON format:**

```json
"[{\"url\": \"https://docs.python.org/3/tutorial/\", \"title\": \"Python Tutorial\", \"quality_score\": 0.9, \"domain_category\": \"official\"}]"
```

Fields in each source object:

- `url` (required): The source URL
- `title` (optional): Page title
- `quality_score` (optional): 0.0-1.0
- `domain_category` (optional): `"official"`, `"in_depth"`, or `"authoritative"`

**Returns:**

```json
{
  "success": true,
  "concept_id": "uuid-string",
  "message": "Created"
}
```

**Important**: `confidence_score` is calculated automatically. Do NOT provide it as a parameter.

**Example:**

```
create_concept(
  name="Python List Comprehensions",
  explanation="A concise syntax for creating lists by iterating over iterables with optional filtering. Format: [expression for item in iterable if condition]. More readable and often faster than equivalent for loops.",
  area="Programming",
  topic="Python",
  subtopic="Data Structures",
  source_urls='[{"url": "https://docs.python.org/3/tutorial/datastructures.html", "title": "Python Data Structures", "domain_category": "official"}]'
)
```

---

## update_concept

Updates an existing concept. Only provided fields are updated.

**Parameters:**
| Parameter | Type | Required |
|-----------|------|----------|
| `concept_id` | string | Yes |
| `name` | string | No |
| `explanation` | string | No |
| `area` | string | Yes |
| `topic` | string | Yes |
| `subtopic` | string | No |
| `source_urls` | string | No |

**Returns:**

```json
{
  "success": true,
  "updated_fields": ["explanation", "source_urls"],
  "message": "Updated"
}
```

**Example:**

```
update_concept(
  concept_id="uuid-123",
  explanation="Updated explanation with more detail...",
  source_urls='[{"url": "https://newurl.com", "title": "Better Source"}]'
)
```

---

## create_relationship

Links two concepts together. Creates directed relationships.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_id` | string | Yes | Source concept UUID |
| `target_id` | string | Yes | Target concept UUID |
| `relationship_type` | string | Yes | See types below |
| `strength` | float | No | 0.0-1.0, default: 1.0 |
| `notes` | string | No | Description of relationship |

**Relationship Types:**

| Type           | Meaning                              | Use Case                               |
| -------------- | ------------------------------------ | -------------------------------------- |
| `prerequisite` | Source must be learned before target | Learning paths, dependencies           |
| `relates_to`   | Concepts are associated              | Related topics, see-also links         |
| `includes`     | Source contains target               | Hierarchical containment, parent-child |

**Returns:**

```json
{
  "success": true,
  "relationship_id": "rel-abc123",
  "message": "Relationship created"
}
```

**Examples:**

```
# Learning dependency: must know Python basics before list comprehensions
create_relationship(
  source_id="uuid-python-basics",
  target_id="uuid-list-comprehensions",
  relationship_type="prerequisite",
  notes="Understanding basic Python syntax is required"
)

# Related topics
create_relationship(
  source_id="uuid-list-comprehensions",
  target_id="uuid-generator-expressions",
  relationship_type="relates_to",
  notes="Similar syntax but different memory behavior"
)

# Hierarchical: Python includes List Comprehensions
create_relationship(
  source_id="uuid-python-language",
  target_id="uuid-list-comprehensions",
  relationship_type="includes"
)
```

---

## delete_concept

Soft-deletes a concept (marks as deleted, preserves in event store).

**Parameters:** `concept_id` (required)

**Returns:**

```json
{
  "success": true,
  "concept_id": "uuid-123",
  "message": "Deleted"
}
```

---

## delete_relationship

Removes a relationship between concepts.

**Parameters:**
| Parameter | Type | Required |
|-----------|------|----------|
| `source_id` | string | Yes |
| `target_id` | string | Yes |
| `relationship_type` | string | Yes |

---

## Workflow: Store New Concept

```
Step 1: ALWAYS search first (see Retrieval Guide)
        search_concepts_semantic(query="<concept>", limit=10)
        ↓
Step 2: Evaluate search results
        - similarity > 0.7 → Concept exists, don't create
        - similarity 0.5-0.7 → Related concept, consider relationship only
        - similarity < 0.5 → New concept, proceed to create
        ↓
Step 3: Check existing hierarchy
        list_hierarchy()  → Use existing area/topic names for consistency
        ↓
Step 4: Create the concept
        create_concept(name, explanation, area, topic, subtopic, source_urls)
        ↓
Step 5: Link to related concepts
        create_relationship(source_id, target_id, relationship_type)
```

---

## Best Practices

1. **Always search before creating** - Duplicates waste storage and confuse retrieval
2. **Use consistent hierarchy** - Check `list_hierarchy()` for existing area/topic names
3. **Write quality explanations** - Detailed explanations improve auto-calculated confidence
4. **Add source URLs** - Improves concept credibility and confidence score
5. **Create relationships** - Well-connected concepts are easier to discover
6. **Use meaningful notes** - Document why relationships exist

---

## Confidence Score (Auto-Calculated)

The system automatically calculates confidence scores (0-100) based on:

- **Explanation quality** (depth and completeness)
- **Relationship density** (connections to other concepts)
- **Metadata richness** (tags, sources, examples)

Higher confidence = better established concept. You cannot set this manually.

---

## Error Handling

**Success:**

```json
{ "success": true, "message": "Created", "concept_id": "uuid" }
```

**Validation Error:**

```json
{
  "success": false,
  "message": "Name cannot be empty",
  "error": { "type": "validation_error", "field": "name" }
}
```

**Duplicate Detected:**

```json
{
  "success": false,
  "message": "Concept already exists with same name/area/topic",
  "error": {
    "type": "validation_error",
    "field": "name",
    "invalid_value": { "existing_concept_id": "uuid" }
  }
}
```

---

_End of Store Guide - See Retrieval Guide for searching and browsing concepts_
