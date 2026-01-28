# Skills Specification

## Transfer Memory Profile

**Total Skills:** 4
**Downstream Consumer:** `/create-skill`

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

This skill embeds the Knowledge MCP Store Guide documentation, providing the transfer-agent with precise instructions for:

1. **Creating Concepts** (`create_concept`)
2. **Updating Concepts** (`update_concept`)
3. **Creating Relationships** (`create_relationship`)

### Key Information to Include

#### create_concept Parameters

| Parameter     | Type   | Required | Constraints       |
| ------------- | ------ | -------- | ----------------- |
| `name`        | string | Yes      | 1-200 chars       |
| `explanation` | string | Yes      | Non-empty         |
| `area`        | string | No       | Max 100 chars     |
| `topic`       | string | No       | Max 100 chars     |
| `subtopic`    | string | No       | Max 100 chars     |
| `source_urls` | string | No       | JSON array format |

#### source_urls JSON Format (CRITICAL)

```json
"[{\"url\": \"https://example.com\", \"title\": \"Page Title\", \"quality_score\": 0.9, \"domain_category\": \"official\"}]"
```

**Important:** Must be a JSON string, not an object.

#### update_concept Parameters

| Parameter     | Type   | Required |
| ------------- | ------ | -------- |
| `concept_id`  | string | Yes      |
| `name`        | string | No       |
| `explanation` | string | No       |
| `area`        | string | Yes      |
| `topic`       | string | Yes      |
| `subtopic`    | string | No       |
| `source_urls` | string | No       |

#### create_relationship Parameters

| Parameter           | Type   | Required          |
| ------------------- | ------ | ----------------- |
| `source_id`         | string | Yes               |
| `target_id`         | string | Yes               |
| `relationship_type` | string | Yes               |
| `strength`          | float  | No (default: 1.0) |
| `notes`             | string | No                |

#### Relationship Types

| Type           | Meaning                              |
| -------------- | ------------------------------------ |
| `prerequisite` | Source must be learned before target |
| `relates_to`   | Concepts are associated              |
| `includes`     | Source contains target               |

### Merge Strategy

When merging a new concept into an existing one:

1. **Explanation Merging:**

   ```
   Updated explanation = existing_explanation + "\n\n---\n\nAdditional Information:\n" + new_explanation
   ```

   - Never replace entirely - preserve existing information
   - Clearly demarcate new additions

2. **source_urls Merging:**
   - Parse existing source_urls (if any)
   - Add new source_urls
   - Deduplicate by URL
   - Re-serialize to JSON string

3. **Fields to Update:**
   - explanation (merged)
   - source_urls (combined)
   - Do NOT change: name, area, topic (use existing)

### Error Response Patterns

**Success:**

```json
{ "success": true, "concept_id": "uuid", "message": "Created" }
```

**Duplicate Detected:**

```json
{
  "success": false,
  "message": "Concept already exists",
  "error": { "type": "validation_error", "field": "name" }
}
```

### Notes for Skill Creator

- Embed the complete KNOWLEDGE_MCP_STORE_GUIDE.md content
- Emphasize the source_urls JSON string format (common error)
- Include merge strategy as explicit guidance
- Relationship type mapping table is essential

---

## Skill: knowledge-mcp-retrieve-guide

### User's Intent

> "We need to ensure that we only store truly new concepts... link new concepts to related existing ones."

### Summary

| Attribute   | Value                                                              |
| ----------- | ------------------------------------------------------------------ |
| **Purpose** | Embedded knowledge for searching and retrieving from Knowledge MCP |
| **Used By** | validation-agent, categorization-agent, verification-agent         |
| **Type**    | Reference Guide                                                    |

### Skill Content

This skill embeds the Knowledge MCP Retrieve Guide documentation, providing agents with precise instructions for:

1. **Semantic Search** (`search_concepts_semantic`)
2. **Exact Search** (`search_concepts_exact`)
3. **Hierarchy Browsing** (`list_hierarchy`)
4. **Concept Retrieval** (`get_concept`)
5. **Relationship Queries** (`get_related_concepts`, `get_prerequisites`)

### Key Information to Include

#### search_concepts_semantic Parameters

| Parameter        | Type   | Required | Default     |
| ---------------- | ------ | -------- | ----------- |
| `query`          | string | Yes      | -           |
| `limit`          | int    | No       | 10 (max 50) |
| `min_confidence` | float  | No       | -           |
| `area`           | string | No       | -           |
| `topic`          | string | No       | -           |

#### Similarity Score Interpretation

| Score   | Meaning        | Action                                  |
| ------- | -------------- | --------------------------------------- |
| > 0.7   | High match     | Likely duplicate - present to user      |
| 0.5-0.7 | Moderate match | Related concept - consider relationship |
| < 0.5   | Weak match     | Different concept - safe to create      |

#### list_hierarchy Response Structure

```json
{
  "success": true,
  "areas": [
    {
      "name": "Philosophy",
      "concept_count": 45,
      "topics": [
        {
          "name": "Stoicism",
          "concept_count": 20,
          "subtopics": [...]
        }
      ]
    }
  ],
  "total_concepts": 150
}
```

#### get_concept Parameters

| Parameter         | Type   | Required            |
| ----------------- | ------ | ------------------- |
| `concept_id`      | string | Yes                 |
| `include_history` | bool   | No (default: false) |

### Agent-Specific Usage

**validation-agent:**

- Use `search_concepts_semantic` with query = concept_name + explanation snippet
- Use limit: 5 to get top matches
- Check similarity scores against 0.7 threshold

**categorization-agent:**

- Use `list_hierarchy` to get all existing areas/topics
- Use `search_concepts_semantic` to find similar concepts
- Reference similar concepts' areas/topics for recommendations

**verification-agent:**

- Use `get_concept` to verify created concepts exist
- Check that returned name matches expected

### Notes for Skill Creator

- Embed the complete KNOWLEDGE_MCP_RETRIEVE_GUIDE.md content
- Highlight the similarity threshold table (0.7 is critical)
- Include decision tree for which search tool to use
- Emphasize that validation-agent needs full explanations from search results

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

This skill provides validation-agent with explicit rules for checking concepts before transfer.

### Required Field Validation

| Field          | Required              | Validation Rule                 |
| -------------- | --------------------- | ------------------------------- |
| `concept_name` | Yes                   | Non-empty string, max 200 chars |
| `explanation`  | Yes                   | Non-empty string                |
| `area`         | Required for transfer | Non-empty string, max 100 chars |
| `topic`        | Required for transfer | Non-empty string, max 100 chars |

### Validation Algorithm

```
FOR each concept:

    # Step 1: Field Validation
    IF concept_name is empty OR null:
        ADD to errors: "Missing concept name"
        CONTINUE to next concept

    IF explanation is empty OR null:
        ADD to errors: "Missing explanation"
        CONTINUE to next concept

    # Step 2: Duplicate Detection
    search_query = concept_name + " " + first_100_chars(explanation)
    results = search_concepts_semantic(query=search_query, limit=5)

    FOR each result in results:
        IF result.similarity > 0.7:
            ADD to duplicates: {
                short_term_concept: concept,
                existing_concept: result,
                similarity: result.similarity,
                recommendation: determine_recommendation(result.similarity)
            }
            MARK concept as has_duplicate
            BREAK

    IF has_duplicate:
        CONTINUE to next concept

    # Step 3: Categorization Check
    IF area is empty OR null:
        ADD "area" to concept.missing

    IF topic is empty OR null:
        ADD "topic" to concept.missing

    IF concept.missing is not empty:
        ADD to uncategorized
        CONTINUE to next concept

    # Step 4: Mark as Valid
    ADD to valid_concepts
```

### Duplicate Recommendation Logic

```
FUNCTION determine_recommendation(similarity):
    IF similarity > 0.9:
        RETURN "merge"  # Almost certainly same concept
    ELSE IF similarity > 0.8:
        RETURN "merge"  # Very likely same concept
    ELSE:  # 0.7 - 0.8
        RETURN "review"  # User should decide
```

### Error Categories

| Category        | Meaning                                 | User Action Required         |
| --------------- | --------------------------------------- | ---------------------------- |
| `errors`        | Cannot transfer - missing critical data | Fix in source or skip        |
| `duplicates`    | Potential existing concept              | Merge / Skip / Create Anyway |
| `uncategorized` | Missing area and/or topic               | Select from recommendations  |
| `valid`         | Ready to transfer                       | None                         |

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
  "valid_concepts": [...],
  "duplicates": [
    {
      "short_term_concept": { /* full concept data */ },
      "existing_concept": { /* full concept data from Knowledge MCP */ },
      "similarity": 0.85,
      "recommendation": "merge"
    }
  ],
  "uncategorized": [
    {
      "concept_id": "...",
      "concept_name": "...",
      "missing": ["area", "topic"]
    }
  ],
  "errors": [
    {
      "concept_id": "...",
      "error": "Missing explanation"
    }
  ]
}
```

### Notes for Skill Creator

- Emphasize that BOTH area AND topic are required for transfer
- The 0.7 similarity threshold is firm - present all matches above this
- Include full concept data in duplicates (both old and new) for user comparison
- Validation should never silently skip concepts - everything must be categorized

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

This skill provides categorization-agent with the algorithm for recommending areas and topics for uncategorized concepts.

### User's Known Domains

The user has specified interest in these domains (use for baseline matching):

| Domain             | Related Areas                                |
| ------------------ | -------------------------------------------- |
| Philosophy         | Stoicism, Buddhism, Hinduism, Taoism, Ethics |
| Spirituality       | Mindfulness, Meditation, Consciousness       |
| Psychology         | Cognitive, Behavioral, Self-Improvement      |
| Health & Longevity | Nutrition, Exercise, Supplements             |
| Technology         | Coding, AI, Machine Learning, APIs           |
| History            | Historical Figures, Case Studies             |
| Communication      | Storytelling, Public Speaking                |

### Recommendation Algorithm

```
FUNCTION generate_recommendations(concept, hierarchy):

    # Step 1: Semantic Search for Similar Concepts
    similar = search_concepts_semantic(
        query = concept.name + " " + concept.explanation,
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

    # Step 3: Keyword Analysis
    keywords = extract_keywords(concept.explanation)

    FOR each area in hierarchy.areas:
        keyword_match_score = count_keyword_matches(keywords, area.name)
        area_scores[area.name] += keyword_match_score * 0.5

        FOR each topic in area.topics:
            topic_match_score = count_keyword_matches(keywords, topic.name)
            topic_scores[area.name][topic.name] += topic_match_score * 0.5

    # Step 4: Normalize and Rank
    total_area_score = sum(area_scores.values())
    FOR each area in area_scores:
        area_scores[area] /= total_area_score  # Normalize to 0-1

    ranked_areas = sort_by_score(area_scores, descending=True)[:3]

    # Step 5: Build Recommendations
    recommendations = []

    FOR each area in ranked_areas:
        area_rec = {
            "area": area.name,
            "confidence": area.score,
            "reason": generate_reason(area, concept),
            "topic_recommendations": []
        }

        # Get top 3 topics for this area
        area_topics = topic_scores.get(area.name, {})
        ranked_topics = sort_by_score(area_topics, descending=True)[:3]

        FOR each topic in ranked_topics:
            topic_rec = {
                "topic": topic.name,
                "confidence": topic.score,
                "reason": generate_topic_reason(topic, concept)
            }
            area_rec.topic_recommendations.append(topic_rec)

        # If less than 3 topics, add from hierarchy
        WHILE len(area_rec.topic_recommendations) < 3:
            # Add topics from hierarchy that aren't already included
            ...

        recommendations.append(area_rec)

    # Step 6: Check if NEW Area/Topic Needed
    IF max(area_scores.values()) < 0.5:
        # No good match - suggest creating new
        new_area_suggestion = suggest_new_area(concept)
        recommendations.append({
            "area": "NEW: " + new_area_suggestion,
            "confidence": 0.4,
            "reason": "No existing area fits well",
            "topic_recommendations": [
                suggest_new_topics(concept)
            ]
        })

    RETURN recommendations
```

### Reason Generation

For each recommendation, generate a human-readable reason:

```
FUNCTION generate_reason(area, concept):
    # Based on what matched:
    IF semantic_match:
        RETURN f"Similar to existing {area} concepts: {similar_concept_names}"
    ELSE IF keyword_match:
        RETURN f"Concept mentions {matched_keywords} related to {area}"
    ELSE:
        RETURN f"Contextual analysis suggests {area} domain"
```

### Output Structure

```json
{
  "concept_id": "c-abc123",
  "concept_name": "Amor Fati",
  "explanation_snippet": "The Stoic concept of loving one's fate...",
  "missing": ["area", "topic"],
  "area_recommendations": [
    {
      "area": "Philosophy",
      "confidence": 0.95,
      "reason": "Concept directly discusses Stoic philosophy principles",
      "topic_recommendations": [
        {
          "topic": "Stoicism",
          "confidence": 0.98,
          "reason": "Amor Fati is a core Stoic concept"
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
    }
    // ... 2 more areas
  ]
}
```

### Handling "NEW" Suggestions

When suggesting a new area or topic:

1. Prefix with "NEW: " to clearly indicate creation
2. Base suggestion on concept keywords and explanation
3. Keep confidence lower (0.3-0.5) to indicate uncertainty
4. Explain why existing categories don't fit

Example:

```json
{
  "area": "NEW: Cognitive Frameworks",
  "confidence": 0.4,
  "reason": "No existing area captures mental model concepts; suggest new category",
  "topic_recommendations": [
    {
      "topic": "NEW: Mental Models",
      "confidence": 0.45,
      "reason": "Central theme of the concept"
    }
  ]
}
```

### Notes for Skill Creator

- Always provide exactly 3 area recommendations
- Each area must have exactly 3 topic recommendations
- Include NEW suggestions when confidence is low
- Reasons should be specific and actionable
- User's known domains (Philosophy, Spirituality, etc.) can influence weighting
- Confidence scores should be calibrated: >0.8 = strong match, 0.5-0.8 = moderate, <0.5 = weak

---

## Summary Table

| Skill                        | Used By                                                    | Source Material                 | Key Content                                                                |
| ---------------------------- | ---------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------- |
| knowledge-mcp-store-guide    | transfer-agent                                             | KNOWLEDGE_MCP_STORE_GUIDE.md    | create/update/relationship API details, source_urls format, merge strategy |
| knowledge-mcp-retrieve-guide | validation-agent, categorization-agent, verification-agent | KNOWLEDGE_MCP_RETRIEVE_GUIDE.md | search APIs, similarity thresholds, hierarchy structure                    |
| validation-skill             | validation-agent                                           | Custom                          | Validation algorithm, duplicate detection, error categories                |
| categorization-skill         | categorization-agent                                       | Custom                          | Recommendation algorithm, confidence scoring, NEW suggestions              |
