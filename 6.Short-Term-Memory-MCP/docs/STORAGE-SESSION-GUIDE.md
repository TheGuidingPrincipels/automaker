# Short-Term Memory MCP: Storage Session Guide

## Document Purpose

This guide provides **exact instructions** for a downstream Claude Code session to store concepts, learning data, and research information in the Short-Term Memory MCP system. Follow these procedures precisely to ensure all relevant information is captured correctly for later retrieval and learning sessions.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Session Initialization](#2-session-initialization)
3. [Storing Concepts](#3-storing-concepts)
4. [Managing Concept Status](#4-managing-concept-status)
5. [Storing Stage Data](#5-storing-stage-data)
6. [Adding User Questions](#6-adding-user-questions)
7. [Creating Concept Relationships](#7-creating-concept-relationships)
8. [Research Cache Management](#8-research-cache-management)
9. [Transferring to Knowledge MCP](#9-transferring-to-knowledge-mcp)
10. [Session Completion](#10-session-completion)
11. [Complete Storage Workflow Example](#11-complete-storage-workflow-example)
12. [Data Format Specifications](#12-data-format-specifications)
13. [Error Handling](#13-error-handling)

---

## 1. Prerequisites

### Required MCP Server

Ensure the Short-Term Memory MCP server is running and connected. The server provides these tool prefixes:

- Tools are accessed directly (e.g., `initialize_daily_session`, `store_concepts_from_research`)

### Environment Configuration

```bash
# Default configuration (can be overridden via .env)
DB_PATH=data/short_term_memory.db
DB_RETENTION_DAYS=7
CACHE_TTL=300  # 5 minutes
QUERY_TIMEOUT=5.0
ENABLE_WAL=true
AUTO_VACUUM=true
```

---

## 2. Session Initialization

### Tool: `initialize_daily_session`

**When to Use**: At the start of every learning/storage session. Must be called before storing any concepts.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `learning_goal` | string | Yes | What you want to learn today (e.g., "Master Python async/await patterns") |
| `building_goal` | string | Yes | What you want to build today (e.g., "Async web scraper with rate limiting") |
| `date` | string | No | Session date in YYYY-MM-DD format (defaults to today) |

**Example Call**:

```json
{
  "learning_goal": "Understand React Server Components and their benefits",
  "building_goal": "Build a Next.js 14 app with streaming SSR",
  "date": "2025-01-25"
}
```

**Expected Response**:

```json
{
  "status": "success",
  "session_id": "2025-01-25",
  "message": "Session initialized for 2025-01-25",
  "cleaned_old_sessions": 2
}
```

**Important Notes**:

- Session ID is the date in YYYY-MM-DD format
- If session already exists for that date, returns `status: "warning"` with existing session
- Auto-cleanup runs, deleting sessions older than `DB_RETENTION_DAYS` (default: 7)

---

## 3. Storing Concepts

### Tool: `store_concepts_from_research`

**When to Use**: After identifying concepts during research. Use for bulk storage of multiple concepts.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session ID (YYYY-MM-DD format) |
| `concepts` | array | Yes | Array of concept objects |

**Concept Object Structure**:

```json
{
  "concept_name": "string (required)",
  "concept_id": "string (optional, auto-generated if omitted)",
  "data": {
    "description": "Brief description of the concept",
    "source": "Where this concept was identified",
    "category": "Category/domain of the concept",
    "difficulty": "beginner|intermediate|advanced",
    "prerequisites": ["list", "of", "prerequisite", "concepts"],
    "tags": ["relevant", "tags"],
    "notes": "Any additional notes"
  }
}
```

**Example Call**:

```json
{
  "session_id": "2025-01-25",
  "concepts": [
    {
      "concept_name": "React Server Components",
      "data": {
        "description": "Components that render on the server and send HTML to client",
        "source": "React documentation",
        "category": "React/Next.js",
        "difficulty": "intermediate",
        "prerequisites": ["React basics", "Component lifecycle"],
        "tags": ["react", "server-rendering", "performance"]
      }
    },
    {
      "concept_name": "Streaming SSR",
      "data": {
        "description": "Progressive server-side rendering with streaming HTML",
        "source": "Next.js 14 documentation",
        "category": "React/Next.js",
        "difficulty": "advanced",
        "prerequisites": ["React Server Components", "Suspense"],
        "tags": ["ssr", "streaming", "performance"]
      }
    },
    {
      "concept_name": "use client directive",
      "data": {
        "description": "Directive marking component boundary for client-side rendering",
        "source": "React documentation",
        "category": "React/Next.js",
        "difficulty": "beginner",
        "tags": ["react", "client-components", "bundling"]
      }
    }
  ]
}
```

**Expected Response**:

```json
{
  "status": "success",
  "session_id": "2025-01-25",
  "concepts_created": 3,
  "concept_ids": [
    "c-react-server-components-abc123",
    "c-streaming-ssr-def456",
    "c-use-client-directive-ghi789"
  ]
}
```

**Best Practices**:

- Store concepts in batches (up to 25+ at once is tested and supported)
- Include rich `data` object for better retrieval later
- Use descriptive concept names (they're searchable)
- All concepts start with status `identified`

---

## 4. Managing Concept Status

### Tool: `update_concept_status`

**When to Use**: To progress a concept through the SHOOT pipeline stages.

**Valid Status Values**:
| Status | Description | When to Use |
|--------|-------------|-------------|
| `identified` | Initial state | Set automatically on creation |
| `chunked` | Concept broken into chunks | After AIM stage processing |
| `encoded` | Vector representations created | After SHOOT stage processing |
| `evaluated` | Quality evaluated | After SKIN stage processing |
| `stored` | Transferred to Knowledge MCP | After successful transfer |

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_id` | string | Yes | The concept ID to update |
| `new_status` | string | Yes | New status value |
| `timestamp` | string | No | ISO timestamp (defaults to now) |

**Example Call**:

```json
{
  "concept_id": "c-react-server-components-abc123",
  "new_status": "chunked"
}
```

**Expected Response**:

```json
{
  "status": "success",
  "concept_id": "c-react-server-components-abc123",
  "previous_status": "identified",
  "new_status": "chunked",
  "timestamp": "2025-01-25T14:30:00.000Z"
}
```

---

## 5. Storing Stage Data

### Tool: `store_stage_data`

**When to Use**: To store stage-specific processing results for a concept.

**Valid Stages**:
| Stage | Purpose | Typical Data |
|-------|---------|--------------|
| `research` | Research findings | explanation, sources, key_points |
| `aim` | Learning objectives | questions, relationships, focus_areas |
| `shoot` | Deep research results | detailed_explanation, code_examples, source_urls |
| `skin` | Evaluation results | understanding_level, confidence_score, gaps |

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_id` | string | Yes | The concept ID |
| `stage` | string | Yes | Stage name (research\|aim\|shoot\|skin) |
| `data` | object | Yes | Stage-specific data dictionary |

**Example Calls for Each Stage**:

#### Research Stage Data

```json
{
  "concept_id": "c-react-server-components-abc123",
  "stage": "research",
  "data": {
    "explanation": "React Server Components (RSC) are a new paradigm that allows components to render on the server...",
    "key_points": [
      "Zero bundle size for server components",
      "Direct database/filesystem access",
      "Automatic code splitting"
    ],
    "sources": [
      "https://react.dev/blog/2023/03/22/react-labs-what-we-have-been-working-on-march-2023"
    ],
    "related_concepts": ["Suspense", "Streaming", "Client Components"]
  }
}
```

#### Aim Stage Data

```json
{
  "concept_id": "c-react-server-components-abc123",
  "stage": "aim",
  "data": {
    "learning_objectives": [
      "Understand when to use Server vs Client components",
      "Learn data fetching patterns with RSC",
      "Master component composition strategies"
    ],
    "questions_to_answer": [
      "How do RSC affect bundle size?",
      "What are the limitations of RSC?",
      "How to share state between server and client?"
    ],
    "focus_areas": ["performance", "data-fetching", "architecture"],
    "estimated_complexity": "medium"
  }
}
```

#### Shoot Stage Data

```json
{
  "concept_id": "c-react-server-components-abc123",
  "stage": "shoot",
  "data": {
    "detailed_explanation": "React Server Components represent a fundamental shift in React architecture...",
    "code_examples": [
      {
        "title": "Basic Server Component",
        "code": "// app/page.tsx\nexport default async function Page() {\n  const data = await fetchData();\n  return <div>{data}</div>;\n}",
        "explanation": "Server components can be async and fetch data directly"
      }
    ],
    "source_urls": [
      {
        "url": "https://react.dev/reference/react/use-server",
        "title": "Server Components Reference",
        "quality_score": 1.0,
        "domain_category": "official"
      }
    ],
    "common_mistakes": [
      "Trying to use hooks in server components",
      "Not properly marking client boundaries"
    ]
  }
}
```

#### Skin Stage Data

```json
{
  "concept_id": "c-react-server-components-abc123",
  "stage": "skin",
  "data": {
    "understanding_level": "intermediate",
    "confidence_score": 0.75,
    "knowledge_gaps": ["Advanced streaming patterns", "Error boundary integration"],
    "practical_applications": ["E-commerce product pages", "Dashboard with real-time data"],
    "ready_for_transfer": true,
    "review_notes": "Good foundational understanding, needs more practice with streaming"
  }
}
```

**Expected Response**:

```json
{
  "status": "success",
  "concept_id": "c-react-server-components-abc123",
  "stage": "shoot",
  "data_id": "sd-abc123-shoot-xyz789"
}
```

---

## 6. Adding User Questions

### Tool: `add_concept_question`

**When to Use**: When the learner has questions about a concept during any stage.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_id` | string | Yes | The concept ID |
| `question` | string | Yes | The question text |
| `session_stage` | string | Yes | Stage when question was asked |

**Example Call**:

```json
{
  "concept_id": "c-react-server-components-abc123",
  "question": "Can Server Components use React Context?",
  "session_stage": "shoot"
}
```

**Expected Response**:

```json
{
  "status": "success",
  "concept_id": "c-react-server-components-abc123",
  "concept_name": "React Server Components",
  "question_added": "Can Server Components use React Context?",
  "total_questions": 1,
  "all_questions": [
    {
      "question": "Can Server Components use React Context?",
      "asked_at": "2025-01-25T14:35:00.000Z",
      "session_stage": "shoot",
      "answered": false,
      "answer": null
    }
  ]
}
```

**Best Practices**:

- Add questions as they arise during learning
- Include the correct stage for context
- Questions are stored with the concept for later review

---

## 7. Creating Concept Relationships

### Tool: `add_concept_relationship`

**When to Use**: To link related concepts together.

**Relationship Types**:
| Type | Description | Example |
|------|-------------|---------|
| `prerequisite` | Target must be learned before source | "Variables" prerequisite for "Functions" |
| `related` | Concepts are related but not dependent | "REST API" related to "GraphQL" |
| `similar` | Concepts are similar/alternative approaches | "Redux" similar to "Zustand" |
| `builds_on` | Source extends/builds on target | "Hooks" builds_on "Component State" |

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_id` | string | Yes | Source concept ID |
| `related_concept_id` | string | Yes | Target concept ID |
| `relationship_type` | string | Yes | Type of relationship |

**Example Call**:

```json
{
  "concept_id": "c-streaming-ssr-def456",
  "related_concept_id": "c-react-server-components-abc123",
  "relationship_type": "builds_on"
}
```

**Expected Response**:

```json
{
  "status": "success",
  "concept_id": "c-streaming-ssr-def456",
  "concept_name": "Streaming SSR",
  "related_to": {
    "concept_id": "c-react-server-components-abc123",
    "concept_name": "React Server Components",
    "relationship_type": "builds_on"
  },
  "total_relationships": 1
}
```

**Validation Rules**:

- Cannot create self-referential relationships
- Cannot create duplicate relationships
- Both concepts must exist

---

## 8. Research Cache Management

### Checking Cache: `check_research_cache`

**When to Use**: Before triggering research to avoid duplicates.

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
    "explanation": "React Server Components are...",
    "source_urls": [...],
    "last_researched_at": "2025-01-20T10:00:00Z"
  },
  "cache_age_seconds": 432000
}
```

### Updating Cache: `update_research_cache`

**When to Use**: After completing research on a concept.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `concept_name` | string | Yes | Concept name (normalized) |
| `explanation` | string | Yes | Research explanation |
| `source_urls` | array | Yes | Array of source URL objects |

**Source URL Object Structure**:

```json
{
  "url": "https://react.dev/reference/react/use-server",
  "title": "Server Components Reference",
  "quality_score": 1.0,
  "domain_category": "official"
}
```

**Domain Categories and Quality Scores**:
| Category | Typical Score | Examples |
|----------|---------------|----------|
| `official` | 1.0 | docs.python.org, reactjs.org, developer.mozilla.org |
| `in_depth` | 0.8 | realpython.com, freecodecamp.org, css-tricks.com |
| `authoritative` | 0.6 | github.com, stackoverflow.com, medium.com |
| `community` | 0.4 | Personal blogs, tutorials |

**Example Call**:

```json
{
  "concept_name": "React Server Components",
  "explanation": "React Server Components (RSC) are a new paradigm in React that allows components to render exclusively on the server. Unlike traditional SSR, RSC never hydrate on the client, resulting in zero JavaScript bundle impact. They can directly access server resources like databases and file systems, making data fetching more efficient.",
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
    },
    {
      "url": "https://www.freecodecamp.org/news/react-server-components-for-beginners/",
      "title": "React Server Components for Beginners",
      "quality_score": 0.8,
      "domain_category": "in_depth"
    }
  ]
}
```

### Managing Domain Whitelist: `add_domain_to_whitelist`

**When to Use**: When you discover a new trustworthy source.

```json
{
  "domain": "blog.vercel.com",
  "category": "authoritative",
  "quality_score": 0.7
}
```

---

## 9. Transferring to Knowledge MCP

### Step 1: Get Unstored Concepts

**Tool**: `get_unstored_concepts`

```json
{
  "session_id": "2025-01-25"
}
```

**Response**:

```json
{
  "status": "success",
  "session_id": "2025-01-25",
  "unstored_count": 3,
  "concepts": [
    {
      "concept_id": "c-react-server-components-abc123",
      "concept_name": "React Server Components",
      "current_status": "evaluated"
    }
  ]
}
```

### Step 2: Transfer to Knowledge MCP

For each concept:

1. Gather all stage data
2. Get source URLs from research cache
3. Create entry in Knowledge MCP (external system)
4. Get the Knowledge MCP ID

### Step 3: Mark as Stored

**Tool**: `mark_concept_stored`

```json
{
  "concept_id": "c-react-server-components-abc123",
  "knowledge_mcp_id": "kb-rsc-permanent-id-12345"
}
```

**Response**:

```json
{
  "status": "success",
  "concept_id": "c-react-server-components-abc123",
  "knowledge_mcp_id": "kb-rsc-permanent-id-12345",
  "stored_at": "2025-01-25T16:00:00.000Z"
}
```

---

## 10. Session Completion

### Tool: `mark_session_complete`

**When to Use**: After all concepts have been transferred to Knowledge MCP.

```json
{
  "session_id": "2025-01-25"
}
```

**Success Response** (all concepts stored):

```json
{
  "status": "success",
  "session_id": "2025-01-25",
  "total_concepts": 3,
  "completed_at": "2025-01-25T16:30:00.000Z",
  "message": "Session completed successfully"
}
```

**Warning Response** (concepts not stored):

```json
{
  "status": "warning",
  "session_id": "2025-01-25",
  "total_concepts": 3,
  "unstored_count": 1,
  "unstored_concepts": [
    {
      "concept_id": "c-use-client-directive-ghi789",
      "name": "use client directive",
      "status": "evaluated"
    }
  ],
  "message": "Session has 1 concepts not yet transferred to Knowledge MCP"
}
```

---

## 11. Complete Storage Workflow Example

Here's a complete example of storing a learning session:

```
STEP 1: Initialize Session
─────────────────────────
Tool: initialize_daily_session
{
  "learning_goal": "Master React Server Components architecture",
  "building_goal": "Build a Next.js 14 dashboard with streaming"
}
→ Returns: session_id = "2025-01-25"

STEP 2: Store Identified Concepts
─────────────────────────────────
Tool: store_concepts_from_research
{
  "session_id": "2025-01-25",
  "concepts": [
    {"concept_name": "React Server Components", "data": {...}},
    {"concept_name": "Streaming SSR", "data": {...}},
    {"concept_name": "use client directive", "data": {...}},
    {"concept_name": "Suspense boundaries", "data": {...}},
    {"concept_name": "Server Actions", "data": {...}}
  ]
}
→ Returns: 5 concept_ids

STEP 3: Add Relationships
─────────────────────────
Tool: add_concept_relationship (multiple calls)
- "Streaming SSR" builds_on "React Server Components"
- "use client directive" related "React Server Components"
- "Suspense boundaries" prerequisite "Streaming SSR"
- "Server Actions" builds_on "React Server Components"

STEP 4: Process Through Stages
──────────────────────────────
For each concept:
  a. Store research stage data (store_stage_data, stage="research")
  b. Update status to "chunked" (update_concept_status)
  c. Store aim stage data (store_stage_data, stage="aim")
  d. Store shoot stage data (store_stage_data, stage="shoot")
  e. Update status to "encoded" (update_concept_status)
  f. Store skin stage data (store_stage_data, stage="skin")
  g. Update status to "evaluated" (update_concept_status)

STEP 5: Add Questions (as they arise)
─────────────────────────────────────
Tool: add_concept_question
{
  "concept_id": "c-rsc-abc123",
  "question": "How do RSC handle state management?",
  "session_stage": "shoot"
}

STEP 6: Update Research Cache
─────────────────────────────
Tool: update_research_cache
{
  "concept_name": "React Server Components",
  "explanation": "...",
  "source_urls": [...]
}

STEP 7: Transfer to Knowledge MCP
─────────────────────────────────
a. get_unstored_concepts → list of concepts
b. For each: Create in Knowledge MCP (external)
c. mark_concept_stored with knowledge_mcp_id

STEP 8: Complete Session
────────────────────────
Tool: mark_session_complete
{
  "session_id": "2025-01-25"
}
```

---

## 12. Data Format Specifications

### Timestamps

- Format: ISO 8601 (`YYYY-MM-DDTHH:mm:ss.sssZ`)
- Timezone: UTC
- Example: `2025-01-25T14:30:00.000Z`

### Session IDs

- Format: `YYYY-MM-DD`
- Example: `2025-01-25`

### Concept IDs

- Format: Auto-generated UUID with prefix
- Example: `c-react-server-components-abc123`

### JSON Data Fields

- All `data` parameters accept nested JSON objects
- Arrays are supported
- Maximum recommended depth: 3 levels

### String Lengths

- `concept_name`: 1-500 characters
- `explanation`: 1-50000 characters
- `question`: 1-2000 characters

---

## 13. Error Handling

### Common Error Codes

| Code                            | Meaning                   | Resolution                                           |
| ------------------------------- | ------------------------- | ---------------------------------------------------- |
| `SESSION_NOT_FOUND`             | Session doesn't exist     | Initialize session first                             |
| `CONCEPT_NOT_FOUND`             | Concept doesn't exist     | Verify concept_id                                    |
| `INVALID_STATUS`                | Invalid status value      | Use: identified\|chunked\|encoded\|evaluated\|stored |
| `INVALID_STAGE`                 | Invalid stage name        | Use: research\|aim\|shoot\|skin                      |
| `SELF_REFERENTIAL_RELATIONSHIP` | Concept related to itself | Use different concept IDs                            |
| `TIMEOUT`                       | Operation exceeded 5s     | Retry or reduce batch size                           |

### Error Response Format

```json
{
  "status": "error",
  "error_code": "SESSION_NOT_FOUND",
  "message": "No session found for 2025-01-25",
  "details": {}
}
```

### Recovery Procedures

**Session Not Found**:

1. Call `initialize_daily_session` with the correct date
2. Retry the failed operation

**Concept Not Found**:

1. Call `get_concepts_by_session` to list all concepts
2. Verify the concept_id
3. If missing, re-store the concept

**Timeout**:

1. Check system health with `health_check`
2. Reduce batch size for bulk operations
3. Retry with smaller data payload

---

## Summary Checklist

Before ending a storage session, verify:

- [ ] Session initialized with clear learning and building goals
- [ ] All concepts stored with descriptive data
- [ ] Concept relationships established
- [ ] Stage data stored for each pipeline stage
- [ ] User questions captured
- [ ] Research cache updated with source URLs
- [ ] All concepts marked as stored with Knowledge MCP IDs
- [ ] Session marked as complete

---

_Document Version: 1.0_
_Last Updated: 2025-01-25_
_Compatible with: Short-Term Memory MCP v0.5.0+_
