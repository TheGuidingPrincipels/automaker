# Short-Term Memory MCP: Retrieval & Learning Session Guide

## Document Purpose

This guide provides **exact instructions** for a downstream Claude Code session to retrieve stored concepts and learning data from the Short-Term Memory MCP system. Use this guide for:

- **Learning sessions**: Reviewing and reinforcing stored knowledge
- **Data migration**: Extracting data for transfer to another database
- **Progress tracking**: Understanding learning status and gaps
- **Knowledge integration**: Connecting stored concepts for deeper understanding

---

## Table of Contents

1. [Retrieval Overview](#1-retrieval-overview)
2. [Session Discovery](#2-session-discovery)
3. [Concept Retrieval](#3-concept-retrieval)
4. [Stage Data Retrieval](#4-stage-data-retrieval)
5. [Question Retrieval](#5-question-retrieval)
6. [Relationship Retrieval](#6-relationship-retrieval)
7. [Research Cache Retrieval](#7-research-cache-retrieval)
8. [Complete Concept Page](#8-complete-concept-page)
9. [Learning Session Workflows](#9-learning-session-workflows)
10. [Data Export for Migration](#10-data-export-for-migration)
11. [Monitoring and Metrics](#11-monitoring-and-metrics)
12. [Complete Data Extraction Example](#12-complete-data-extraction-example)

---

## 1. Retrieval Overview

### Available Retrieval Tools

| Tool                        | Purpose                      | Use Case                 |
| --------------------------- | ---------------------------- | ------------------------ |
| `get_active_session`        | Get session with statistics  | Session overview         |
| `get_concepts_by_session`   | List all concepts in session | Bulk retrieval           |
| `get_concepts_by_status`    | Filter by pipeline status    | Status-specific queries  |
| `get_stage_data`            | Get stage-specific data      | Detailed stage info      |
| `get_concept_page`          | Complete concept view        | Single concept deep-dive |
| `get_related_concepts`      | Get concept relationships    | Knowledge graph          |
| `get_todays_concepts`       | Today's concepts (cached)    | Quick access             |
| `get_todays_learning_goals` | Today's goals (cached)       | Goal review              |
| `search_todays_concepts`    | Search by term               | Discovery                |
| `check_research_cache`      | Check cached research        | Research lookup          |
| `list_whitelisted_domains`  | List trusted sources         | Source quality           |
| `get_unstored_concepts`     | List pending transfers       | Migration status         |

### Data Hierarchy

```
Session
├── session_id (YYYY-MM-DD)
├── learning_goal
├── building_goal
├── status (in_progress | completed)
└── Concepts[]
    ├── concept_id
    ├── concept_name
    ├── current_status
    ├── current_data (JSON)
    ├── user_questions[]
    ├── knowledge_mcp_id (if transferred)
    ├── Stage Data
    │   ├── research: {...}
    │   ├── aim: {...}
    │   ├── shoot: {...}
    │   └── skin: {...}
    └── Relationships[]
        ├── prerequisite
        ├── related
        ├── similar
        └── builds_on
```

---

## 2. Session Discovery

### Get Active Session

**Tool**: `get_active_session`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | No | Session date (YYYY-MM-DD), defaults to today |

**Example Call**:

```json
{
  "date": "2025-01-25"
}
```

**Response Structure**:

```json
{
  "status": "success",
  "session_id": "2025-01-25",
  "date": "2025-01-25",
  "learning_goal": "Master React Server Components architecture",
  "building_goal": "Build a Next.js 14 dashboard with streaming",
  "session_status": "in_progress",
  "concept_count": 5,
  "concepts_by_status": {
    "identified": 0,
    "chunked": 0,
    "encoded": 1,
    "evaluated": 3,
    "stored": 1
  }
}
```

**Use Cases**:

- Start of learning session: Get overview of what was learned
- Progress check: See concept status distribution
- Goal reminder: Review learning and building objectives

### Get Today's Learning Goals (Cached)

**Tool**: `get_todays_learning_goals`

**No Parameters** - Always uses current date

**Response Structure**:

```json
{
  "status": "success",
  "date": "2025-01-25",
  "session_id": "2025-01-25",
  "learning_goal": "Master React Server Components architecture",
  "building_goal": "Build a Next.js 14 dashboard with streaming",
  "session_status": "in_progress",
  "concept_count": 5,
  "concepts_by_status": {
    "identified": 0,
    "chunked": 0,
    "encoded": 1,
    "evaluated": 3,
    "stored": 1
  },
  "cache_hit": true
}
```

**Note**: Cached for 5 minutes - ideal for frequent access without database load.

---

## 3. Concept Retrieval

### Get All Concepts in Session

**Tool**: `get_concepts_by_session`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session ID (YYYY-MM-DD) |
| `status_filter` | string | No | Filter by status |
| `include_stage_data` | boolean | No | Include all stage data (default: false) |

**Basic Call** (concept list only):

```json
{
  "session_id": "2025-01-25"
}
```

**Full Call** (with stage data):

```json
{
  "session_id": "2025-01-25",
  "status_filter": "evaluated",
  "include_stage_data": true
}
```

**Response Structure**:

```json
{
  "status": "success",
  "session_id": "2025-01-25",
  "count": 5,
  "concepts": [
    {
      "concept_id": "c-react-server-components-abc123",
      "session_id": "2025-01-25",
      "concept_name": "React Server Components",
      "current_status": "evaluated",
      "identified_at": "2025-01-25T10:00:00.000Z",
      "chunked_at": "2025-01-25T11:00:00.000Z",
      "encoded_at": "2025-01-25T12:00:00.000Z",
      "evaluated_at": "2025-01-25T13:00:00.000Z",
      "stored_at": null,
      "knowledge_mcp_id": null,
      "current_data": {
        "description": "Components that render on the server",
        "category": "React/Next.js",
        "difficulty": "intermediate"
      },
      "user_questions": [
        {
          "question": "Can Server Components use React Context?",
          "asked_at": "2025-01-25T12:30:00.000Z",
          "session_stage": "shoot",
          "answered": false
        }
      ],
      "created_at": "2025-01-25T10:00:00.000Z",
      "updated_at": "2025-01-25T13:00:00.000Z",
      "stage_data": {
        "research": { "explanation": "...", "key_points": [...] },
        "aim": { "learning_objectives": [...] },
        "shoot": { "detailed_explanation": "...", "source_urls": [...] },
        "skin": { "understanding_level": "intermediate", "confidence_score": 0.75 }
      }
    }
  ]
}
```

### Get Concepts by Status

**Tool**: `get_concepts_by_status`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session ID |
| `status` | string | Yes | Status to filter |

**Example - Get Evaluated Concepts**:

```json
{
  "session_id": "2025-01-25",
  "status": "evaluated"
}
```

**Use Cases**:

- Find concepts ready for transfer: `status: "evaluated"`
- Find concepts needing research: `status: "identified"`
- Find transferred concepts: `status: "stored"`

### Get Today's Concepts (Cached)

**Tool**: `get_todays_concepts`

**No Parameters** - Always uses current date

**Response** includes full concept list with 5-minute cache.

### Search Concepts

**Tool**: `search_todays_concepts`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search_term` | string | Yes | Text to search (case-insensitive) |

**Example**:

```json
{
  "search_term": "server"
}
```

**Response**:

```json
{
  "status": "success",
  "date": "2025-01-25",
  "session_id": "2025-01-25",
  "search_term": "server",
  "match_count": 2,
  "matches": [
    {
      "concept_id": "c-react-server-components-abc123",
      "concept_name": "React Server Components",
      "current_status": "evaluated"
    },
    {
      "concept_id": "c-server-actions-def456",
      "concept_name": "Server Actions",
      "current_status": "chunked"
    }
  ],
  "cache_hit": false
}
```

**Search Scope**: Searches concept names and `current_data` fields.

---

## 4. Stage Data Retrieval

### Get Single Stage Data

**Tool**: `get_stage_data`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_id` | string | Yes | Concept ID |
| `stage` | string | Yes | Stage name (research\|aim\|shoot\|skin) |

**Example - Get Research Stage**:

```json
{
  "concept_id": "c-react-server-components-abc123",
  "stage": "research"
}
```

**Response**:

```json
{
  "status": "success",
  "concept_id": "c-react-server-components-abc123",
  "stage": "research",
  "data": {
    "explanation": "React Server Components (RSC) are a new paradigm...",
    "key_points": [
      "Zero bundle size for server components",
      "Direct database/filesystem access",
      "Automatic code splitting"
    ],
    "sources": ["https://react.dev/blog/2023/03/22/react-labs"],
    "related_concepts": ["Suspense", "Streaming", "Client Components"]
  },
  "created_at": "2025-01-25T10:30:00.000Z"
}
```

### Stage Data Contents by Stage

#### Research Stage (`stage: "research"`)

```json
{
  "explanation": "Overview explanation of the concept",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "sources": ["URL1", "URL2"],
  "related_concepts": ["Related1", "Related2"]
}
```

#### Aim Stage (`stage: "aim"`)

```json
{
  "learning_objectives": ["Objective 1", "Objective 2"],
  "questions_to_answer": ["Question 1", "Question 2"],
  "focus_areas": ["Area 1", "Area 2"],
  "estimated_complexity": "beginner|intermediate|advanced"
}
```

#### Shoot Stage (`stage: "shoot"`)

```json
{
  "detailed_explanation": "In-depth explanation with examples",
  "code_examples": [
    {
      "title": "Example Title",
      "code": "code here",
      "explanation": "What this demonstrates"
    }
  ],
  "source_urls": [
    {
      "url": "https://...",
      "title": "Page Title",
      "quality_score": 1.0,
      "domain_category": "official"
    }
  ],
  "common_mistakes": ["Mistake 1", "Mistake 2"]
}
```

#### Skin Stage (`stage: "skin"`)

```json
{
  "understanding_level": "beginner|intermediate|advanced",
  "confidence_score": 0.75,
  "knowledge_gaps": ["Gap 1", "Gap 2"],
  "practical_applications": ["Application 1", "Application 2"],
  "ready_for_transfer": true,
  "review_notes": "Notes about understanding"
}
```

---

## 5. Question Retrieval

Questions are embedded in concept data. Retrieve via `get_concepts_by_session` or `get_concept_page`.

### Question Structure

```json
{
  "question": "Can Server Components use React Context?",
  "asked_at": "2025-01-25T12:30:00.000Z",
  "session_stage": "shoot",
  "answered": false,
  "answer": null
}
```

### Extracting All Questions from Session

```python
# Pseudocode for extracting all questions
session_concepts = get_concepts_by_session(session_id)
all_questions = []
for concept in session_concepts["concepts"]:
    for question in concept.get("user_questions", []):
        all_questions.append({
            "concept_id": concept["concept_id"],
            "concept_name": concept["concept_name"],
            **question
        })
```

---

## 6. Relationship Retrieval

### Get Related Concepts

**Tool**: `get_related_concepts`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_id` | string | Yes | Concept ID |
| `relationship_type` | string | No | Filter by type |

**Example - All Relationships**:

```json
{
  "concept_id": "c-react-server-components-abc123"
}
```

**Example - Specific Type**:

```json
{
  "concept_id": "c-react-server-components-abc123",
  "relationship_type": "prerequisite"
}
```

**Response**:

```json
{
  "status": "success",
  "concept_id": "c-react-server-components-abc123",
  "concept_name": "React Server Components",
  "relationship_filter": null,
  "related_count": 3,
  "related_concepts": [
    {
      "concept_id": "c-streaming-ssr-def456",
      "concept_name": "Streaming SSR",
      "relationship_type": "builds_on",
      "current_status": "evaluated",
      "session_id": "2025-01-25",
      "created_at": "2025-01-25T11:00:00.000Z"
    },
    {
      "concept_id": "c-server-actions-ghi789",
      "concept_name": "Server Actions",
      "relationship_type": "related",
      "current_status": "chunked",
      "session_id": "2025-01-25",
      "created_at": "2025-01-25T11:30:00.000Z"
    }
  ]
}
```

### Relationship Types for Learning

| Type           | Learning Implication                     |
| -------------- | ---------------------------------------- |
| `prerequisite` | Learn target concept BEFORE this one     |
| `builds_on`    | This concept EXTENDS the target          |
| `related`      | Study together for broader understanding |
| `similar`      | Compare and contrast approaches          |

---

## 7. Research Cache Retrieval

### Check Research Cache

**Tool**: `check_research_cache`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_name` | string | Yes | Concept name to lookup |

**Example**:

```json
{
  "concept_name": "React Server Components"
}
```

**Response (if cached)**:

```json
{
  "cached": true,
  "entry": {
    "concept_name": "React Server Components",
    "explanation": "React Server Components (RSC) are a new paradigm in React that allows components to render exclusively on the server. Unlike traditional SSR, RSC never hydrate on the client, resulting in zero JavaScript bundle impact.",
    "source_urls": [
      {
        "url": "https://react.dev/reference/react/use-server",
        "title": "React Server Components Documentation",
        "quality_score": 1.0,
        "domain_category": "official"
      },
      {
        "url": "https://nextjs.org/docs/app/building-your-application/rendering/server-components",
        "title": "Next.js Server Components Guide",
        "quality_score": 1.0,
        "domain_category": "official"
      }
    ],
    "last_researched_at": "2025-01-25T10:00:00.000Z",
    "created_at": "2025-01-25T10:00:00.000Z",
    "updated_at": "2025-01-25T10:00:00.000Z"
  },
  "cache_age_seconds": 14400
}
```

**Response (if not cached)**:

```json
{
  "cached": false,
  "entry": null,
  "cache_age_seconds": null
}
```

### List Whitelisted Domains

**Tool**: `list_whitelisted_domains`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by category |

**Example - All Domains**:

```json
{}
```

**Example - Official Only**:

```json
{
  "category": "official"
}
```

**Response**:

```json
{
  "domains": [
    {
      "domain": "docs.python.org",
      "category": "official",
      "quality_score": 1.0,
      "added_at": "2025-01-01T00:00:00.000Z",
      "added_by": "system"
    },
    {
      "domain": "reactjs.org",
      "category": "official",
      "quality_score": 1.0,
      "added_at": "2025-01-01T00:00:00.000Z",
      "added_by": "system"
    }
  ],
  "count": 10,
  "filter": "all"
}
```

---

## 8. Complete Concept Page

### Get Full Concept Details

**Tool**: `get_concept_page`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_id` | string | Yes | Concept ID |

**Example**:

```json
{
  "concept_id": "c-react-server-components-abc123"
}
```

**Response** (comprehensive single-page view):

```json
{
  "status": "success",
  "concept_id": "c-react-server-components-abc123",
  "concept_name": "React Server Components",
  "session_id": "2025-01-25",
  "current_status": "evaluated",
  "knowledge_mcp_id": null,

  "timeline": [
    {"status": "identified", "timestamp": "2025-01-25T10:00:00.000Z"},
    {"status": "chunked", "timestamp": "2025-01-25T11:00:00.000Z"},
    {"status": "encoded", "timestamp": "2025-01-25T12:00:00.000Z"},
    {"status": "evaluated", "timestamp": "2025-01-25T13:00:00.000Z"}
  ],

  "stage_data": {
    "research": {
      "explanation": "RSC overview...",
      "key_points": ["Point 1", "Point 2"]
    },
    "aim": {
      "learning_objectives": ["Objective 1", "Objective 2"]
    },
    "shoot": {
      "detailed_explanation": "In-depth explanation...",
      "code_examples": [...],
      "source_urls": [...]
    },
    "skin": {
      "understanding_level": "intermediate",
      "confidence_score": 0.75
    }
  },

  "user_questions": [
    {
      "question": "Can Server Components use React Context?",
      "asked_at": "2025-01-25T12:30:00.000Z",
      "session_stage": "shoot",
      "answered": false
    }
  ],
  "question_count": 1,

  "relationships": [
    {
      "concept_id": "c-streaming-ssr-def456",
      "concept_name": "Streaming SSR",
      "relationship_type": "builds_on"
    }
  ],
  "related_concept_count": 1,

  "current_data": {
    "description": "Components that render on the server",
    "category": "React/Next.js",
    "difficulty": "intermediate"
  },

  "created_at": "2025-01-25T10:00:00.000Z",
  "updated_at": "2025-01-25T13:00:00.000Z"
}
```

**Use Case**: Single API call for all concept information - ideal for:

- Learning session review
- Data migration export
- Comprehensive concept analysis

---

## 9. Learning Session Workflows

### Workflow 1: Daily Review Session

```
STEP 1: Get Session Overview
────────────────────────────
Tool: get_todays_learning_goals
→ Review: learning_goal, building_goal, concepts_by_status

STEP 2: Get All Concepts with Stage Data
────────────────────────────────────────
Tool: get_concepts_by_session
{
  "session_id": "2025-01-25",
  "include_stage_data": true
}
→ Full list with all stage data

STEP 3: Review Each Concept
───────────────────────────
For each concept:
  - Read research.explanation
  - Check aim.learning_objectives
  - Study shoot.code_examples
  - Note skin.knowledge_gaps

STEP 4: Review Unanswered Questions
───────────────────────────────────
Extract from concepts where answered = false
→ Address during learning session

STEP 5: Follow Relationships
────────────────────────────
Tool: get_related_concepts
→ Study prerequisite concepts first
→ Compare similar concepts
```

### Workflow 2: Knowledge Gap Analysis

```
STEP 1: Get Evaluated Concepts
──────────────────────────────
Tool: get_concepts_by_status
{
  "session_id": "2025-01-25",
  "status": "evaluated"
}

STEP 2: Extract Knowledge Gaps
──────────────────────────────
For each concept:
  Tool: get_stage_data
  {
    "concept_id": "...",
    "stage": "skin"
  }
  → Collect: knowledge_gaps, confidence_score < 0.8

STEP 3: Prioritize by Confidence
────────────────────────────────
Sort concepts by confidence_score ascending
→ Focus on lowest confidence first

STEP 4: Check Prerequisites
───────────────────────────
For low-confidence concepts:
  Tool: get_related_concepts
  {
    "concept_id": "...",
    "relationship_type": "prerequisite"
  }
  → Ensure prerequisites are mastered
```

### Workflow 3: Spaced Repetition Review

```
STEP 1: Get Historical Sessions
───────────────────────────────
For each day in review period:
  Tool: get_active_session
  {
    "date": "YYYY-MM-DD"
  }

STEP 2: Collect Concepts for Review
───────────────────────────────────
Gather concepts from multiple sessions
Filter by: current_status = "stored" OR "evaluated"

STEP 3: Review with Increasing Intervals
────────────────────────────────────────
Day 1: Review all new concepts
Day 3: Review Day 1 concepts
Day 7: Review Day 1-3 concepts
Day 14: Review Day 1-7 concepts
Day 30: Review Day 1-14 concepts
```

---

## 10. Data Export for Migration

### Complete Session Export

Extract all data from a session for migration to another database:

```
STEP 1: Get Session Metadata
────────────────────────────
Tool: get_active_session
{
  "date": "2025-01-25"
}
→ Store: session_id, learning_goal, building_goal, status

STEP 2: Get All Concepts with Full Data
───────────────────────────────────────
Tool: get_concepts_by_session
{
  "session_id": "2025-01-25",
  "include_stage_data": true
}
→ Store: Complete concept array with stage_data

STEP 3: Get All Relationships
─────────────────────────────
For each concept:
  Tool: get_related_concepts
  {
    "concept_id": "..."
  }
→ Store: relationship graph

STEP 4: Get Research Cache
──────────────────────────
For each unique concept_name:
  Tool: check_research_cache
  {
    "concept_name": "..."
  }
→ Store: cached explanations and source_urls

STEP 5: Get Domain Whitelist
────────────────────────────
Tool: list_whitelisted_domains
{}
→ Store: domain quality scoring configuration
```

### Export Data Schema

```json
{
  "export_metadata": {
    "exported_at": "2025-01-25T16:00:00.000Z",
    "source_system": "short-term-memory-mcp",
    "version": "0.5.0"
  },

  "session": {
    "session_id": "2025-01-25",
    "date": "2025-01-25",
    "learning_goal": "...",
    "building_goal": "...",
    "status": "completed"
  },

  "concepts": [
    {
      "concept_id": "...",
      "concept_name": "...",
      "current_status": "...",
      "current_data": {...},
      "user_questions": [...],
      "knowledge_mcp_id": "...",
      "timestamps": {
        "identified_at": "...",
        "chunked_at": "...",
        "encoded_at": "...",
        "evaluated_at": "...",
        "stored_at": "..."
      },
      "stage_data": {
        "research": {...},
        "aim": {...},
        "shoot": {...},
        "skin": {...}
      }
    }
  ],

  "relationships": [
    {
      "source_concept_id": "...",
      "target_concept_id": "...",
      "relationship_type": "..."
    }
  ],

  "research_cache": [
    {
      "concept_name": "...",
      "explanation": "...",
      "source_urls": [...],
      "last_researched_at": "..."
    }
  ],

  "domain_whitelist": [
    {
      "domain": "...",
      "category": "...",
      "quality_score": 0.0
    }
  ]
}
```

### Migration Target Mapping

| Short-Term Memory Field                 | Typical Target Field     | Notes              |
| --------------------------------------- | ------------------------ | ------------------ |
| `concept_name`                          | `title`, `name`          | Primary identifier |
| `current_data.description`              | `description`, `summary` | Brief description  |
| `stage_data.shoot.detailed_explanation` | `content`, `body`        | Main content       |
| `stage_data.shoot.source_urls`          | `sources`, `references`  | External links     |
| `stage_data.shoot.code_examples`        | `examples`, `snippets`   | Code samples       |
| `user_questions`                        | `faqs`, `questions`      | Q&A pairs          |
| `relationships`                         | `related_to`, `links`    | Graph edges        |
| `stage_data.skin.confidence_score`      | `mastery_level`          | Learning metric    |

---

## 11. Monitoring and Metrics

### System Health Check

**Tool**: `health_check`

**No Parameters**

**Response**:

```json
{
  "status": "success",
  "overall_status": "healthy",
  "timestamp": "2025-01-25T16:00:00.000Z",
  "response_time_ms": 15,
  "components": {
    "database": {
      "status": "healthy",
      "connection": "active",
      "integrity": "ok",
      "size_bytes": 1048576
    },
    "cache": {
      "status": "operational",
      "size": 25,
      "ttl_seconds": 300
    }
  }
}
```

### System Metrics

**Tool**: `get_system_metrics`

**No Parameters**

**Response**:

```json
{
  "status": "success",
  "timestamp": "2025-01-25T16:00:00.000Z",
  "database": {
    "size_bytes": 1048576,
    "size_mb": 1.0,
    "sessions": 7,
    "concepts": 35,
    "stage_data_entries": 140
  },
  "operations": {
    "reads": 1250,
    "writes": 340,
    "queries": 890,
    "errors": 2
  },
  "performance": {
    "read_times": { "avg_ms": 5.2, "min_ms": 1.0, "max_ms": 45.0 },
    "write_times": { "avg_ms": 12.3, "min_ms": 3.0, "max_ms": 89.0 },
    "query_times": { "avg_ms": 8.7, "min_ms": 2.0, "max_ms": 67.0 }
  },
  "cache": {
    "entries": 25,
    "ttl_seconds": 300
  }
}
```

### Error Log

**Tool**: `get_error_log`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | No | Max errors (default: 10, max: 100) |
| `error_type` | string | No | Filter by type |

**Example**:

```json
{
  "limit": 5,
  "error_type": "DatabaseError"
}
```

---

## 12. Complete Data Extraction Example

Here's a complete script for extracting all data from a session:

```
═══════════════════════════════════════════════════════════════
COMPLETE DATA EXTRACTION WORKFLOW
═══════════════════════════════════════════════════════════════

SESSION: 2025-01-25

STEP 1: Initialize Export
─────────────────────────
export_data = {
  "export_metadata": {
    "exported_at": current_timestamp(),
    "source_system": "short-term-memory-mcp",
    "version": "0.5.0"
  }
}

STEP 2: Get Session
───────────────────
Tool: get_active_session
{"date": "2025-01-25"}

export_data["session"] = {
  "session_id": response.session_id,
  "date": response.date,
  "learning_goal": response.learning_goal,
  "building_goal": response.building_goal,
  "status": response.session_status
}

STEP 3: Get All Concepts
────────────────────────
Tool: get_concepts_by_session
{
  "session_id": "2025-01-25",
  "include_stage_data": true
}

export_data["concepts"] = []
for concept in response.concepts:
  export_data["concepts"].append({
    "concept_id": concept.concept_id,
    "concept_name": concept.concept_name,
    "current_status": concept.current_status,
    "current_data": concept.current_data,
    "user_questions": concept.user_questions,
    "knowledge_mcp_id": concept.knowledge_mcp_id,
    "timestamps": {
      "identified_at": concept.identified_at,
      "chunked_at": concept.chunked_at,
      "encoded_at": concept.encoded_at,
      "evaluated_at": concept.evaluated_at,
      "stored_at": concept.stored_at
    },
    "stage_data": concept.stage_data
  })

STEP 4: Get All Relationships
─────────────────────────────
export_data["relationships"] = []
for concept in export_data["concepts"]:
  Tool: get_related_concepts
  {"concept_id": concept.concept_id}

  for related in response.related_concepts:
    export_data["relationships"].append({
      "source_concept_id": concept.concept_id,
      "target_concept_id": related.concept_id,
      "relationship_type": related.relationship_type
    })

STEP 5: Get Research Cache
──────────────────────────
export_data["research_cache"] = []
concept_names = set(c.concept_name for c in export_data["concepts"])

for name in concept_names:
  Tool: check_research_cache
  {"concept_name": name}

  if response.cached:
    export_data["research_cache"].append({
      "concept_name": response.entry.concept_name,
      "explanation": response.entry.explanation,
      "source_urls": response.entry.source_urls,
      "last_researched_at": response.entry.last_researched_at
    })

STEP 6: Get Domain Whitelist
────────────────────────────
Tool: list_whitelisted_domains
{}

export_data["domain_whitelist"] = []
for domain in response.domains:
  export_data["domain_whitelist"].append({
    "domain": domain.domain,
    "category": domain.category,
    "quality_score": domain.quality_score
  })

STEP 7: Validate Export
───────────────────────
Verify:
- All concepts have stage_data
- All relationships reference existing concepts
- Research cache covers all concept names
- No null required fields

STEP 8: Output Export
─────────────────────
Save export_data as JSON to:
- export_2025-01-25.json (complete export)
- export_2025-01-25_concepts.json (concepts only)
- export_2025-01-25_relationships.json (graph only)

═══════════════════════════════════════════════════════════════
EXPORT COMPLETE
═══════════════════════════════════════════════════════════════
```

---

## Quick Reference: Tool Summary

### Session & Overview

| Tool                        | Purpose                | Key Params |
| --------------------------- | ---------------------- | ---------- |
| `get_active_session`        | Session overview       | `date`     |
| `get_todays_learning_goals` | Today's goals (cached) | -          |

### Concept Retrieval

| Tool                      | Purpose                   | Key Params                         |
| ------------------------- | ------------------------- | ---------------------------------- |
| `get_concepts_by_session` | All concepts              | `session_id`, `include_stage_data` |
| `get_concepts_by_status`  | Filter by status          | `session_id`, `status`             |
| `get_todays_concepts`     | Today's concepts (cached) | -                                  |
| `search_todays_concepts`  | Search concepts           | `search_term`                      |
| `get_concept_page`        | Complete concept view     | `concept_id`                       |

### Stage & Relationships

| Tool                   | Purpose             | Key Params                        |
| ---------------------- | ------------------- | --------------------------------- |
| `get_stage_data`       | Stage-specific data | `concept_id`, `stage`             |
| `get_related_concepts` | Relationships       | `concept_id`, `relationship_type` |

### Research & Sources

| Tool                       | Purpose         | Key Params     |
| -------------------------- | --------------- | -------------- |
| `check_research_cache`     | Cached research | `concept_name` |
| `list_whitelisted_domains` | Domain quality  | `category`     |

### Monitoring

| Tool                 | Purpose           | Key Params            |
| -------------------- | ----------------- | --------------------- |
| `health_check`       | System status     | -                     |
| `get_system_metrics` | Performance stats | -                     |
| `get_error_log`      | Recent errors     | `limit`, `error_type` |

### Transfer Status

| Tool                    | Purpose           | Key Params   |
| ----------------------- | ----------------- | ------------ |
| `get_unstored_concepts` | Pending transfers | `session_id` |

---

_Document Version: 1.0_
_Last Updated: 2025-01-25_
_Compatible with: Short-Term Memory MCP v0.5.0+_
