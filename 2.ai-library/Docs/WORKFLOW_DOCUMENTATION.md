# AI-Library: Complete End-to-End Workflow Documentation

> **Purpose**: This document provides a comprehensive explanation of how the AI-Library system works, from document ingestion to retrieval. It is designed to help developers understand the system for making improvements.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Document Ingestion Workflow](#2-document-ingestion-workflow)
3. [What the LLM Does](#3-what-the-llm-does)
4. [Python Validation & API Layer](#4-python-validation--api-layer)
5. [Vector Database & Storage](#5-vector-database--storage)
6. [Query & Retrieval Workflow](#6-query--retrieval-workflow)
7. [Conversation Management](#7-conversation-management)
8. [Configuration Reference](#8-configuration-reference)
9. [Improvement Opportunities](#9-improvement-opportunities)

---

## 1. System Overview

The AI-Library is a personal knowledge management system that:

- **Ingests** user documents (markdown files)
- **Processes** them with LLM assistance for cleanup and routing decisions
- **Stores** content as vector embeddings in Qdrant
- **Retrieves** relevant information using semantic search (RAG)

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                │
│                    (API Endpoints / CLI / SDK)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Sessions   │  │   Library   │  │    Query    │  │   Health    │    │
│  │  /sessions  │  │  /library   │  │   /query    │  │   /health   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING LAYER                                │
│  ┌─────────────────────┐    ┌─────────────────────────────────────┐    │
│  │   Session Manager   │    │            Query Engine             │    │
│  │   (Document Flow)   │    │  (Retrieval + LLM + Formatting)     │    │
│  └─────────────────────┘    └─────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           SDK LAYER                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ClaudeCodeClient                              │   │
│  │  • generate_cleanup_plan()  → LLM suggests keep/discard         │   │
│  │  • generate_routing_plan()  → LLM suggests destinations         │   │
│  │  • query_text()             → LLM answers questions (RAG)       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          STORAGE LAYER                                  │
│  ┌─────────────────────┐    ┌─────────────────────────────────────┐    │
│  │   Library Files     │    │        Qdrant Vector DB             │    │
│  │   (Markdown)        │◄───│  (Embeddings + Metadata Payloads)   │    │
│  └─────────────────────┘    └─────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Files Reference

| Component          | File Path                         | Purpose                          |
| ------------------ | --------------------------------- | -------------------------------- |
| SDK Client         | `src/sdk/client.py`               | LLM interaction wrapper          |
| Cleanup Prompts    | `src/sdk/prompts/cleanup_mode.py` | LLM prompts for cleanup          |
| Routing Prompts    | `src/sdk/prompts/routing_mode.py` | LLM prompts for routing          |
| Query Prompts      | `src/sdk/prompts/output_mode.py`  | LLM prompts for RAG              |
| API Main           | `src/api/main.py`                 | FastAPI application              |
| Session Routes     | `src/api/routes/sessions.py`      | Document ingestion endpoints     |
| Query Routes       | `src/api/routes/query.py`         | Search & RAG endpoints           |
| Validation Schemas | `src/api/schemas.py`              | Pydantic request/response models |
| Vector Store       | `src/vector/store.py`             | Qdrant operations                |
| Indexer            | `src/vector/indexer.py`           | Document chunking & indexing     |
| Semantic Search    | `src/vector/search.py`            | High-level search interface      |
| Query Engine       | `src/query/engine.py`             | RAG orchestration                |
| Retriever          | `src/query/retriever.py`          | Document retrieval & re-ranking  |

---

## 2. Document Ingestion Workflow

When a user wants to add a document to the library, this is the complete step-by-step process:

### Step 1: Create Session

**Endpoint**: `POST /api/sessions`

```
User provides: source_path (file to import) + content_mode ("strict" or "refinement")
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  Validate content_mode │
                        │  (must be strict or    │
                        │   refinement)          │
                        └───────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  Parse markdown file   │
                        │  into blocks           │
                        │  (headings, paragraphs,│
                        │   code, lists)         │
                        └───────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  Create session with   │
                        │  unique UUID           │
                        └───────────────────────┘
```

**Code Location**: `src/api/routes/sessions.py:55-86`

### Step 2: Generate Cleanup Plan (LLM Task #1)

**Endpoint**: `POST /api/sessions/{session_id}/cleanup-plan`

The LLM analyzes each document block and suggests whether to keep or discard it.

```
Session blocks loaded
        │
        ▼
┌───────────────────────────────────────────────────┐
│            SDK: generate_cleanup_plan()            │
│                                                    │
│  Input to LLM:                                     │
│  • System prompt (cleanup instructions)            │
│  • For each block:                                 │
│    - Block ID                                      │
│    - Block type (heading, paragraph, code, etc.)  │
│    - Heading path (section hierarchy)             │
│    - Content preview (first 300 chars)            │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│              LLM Response (JSON)                   │
│                                                    │
│  {                                                 │
│    "cleanup_items": [                              │
│      {                                             │
│        "block_id": "block_001",                    │
│        "suggested_disposition": "keep",            │
│        "suggestion_reason": "Contains valuable...",│
│        "confidence": 0.9                           │
│      }                                             │
│    ],                                              │
│    "overall_notes": "Document contains..."         │
│  }                                                 │
└───────────────────────────────────────────────────┘
        │
        ▼
User reviews and approves/modifies cleanup decisions
```

**Code Location**: `src/sdk/client.py:180-244`, `src/sdk/prompts/cleanup_mode.py`

### Step 3: Apply User Cleanup Decisions

**Endpoint**: `POST /api/sessions/{session_id}/blocks/{block_id}/cleanup`

```
For each block, user decides: "keep" or "discard"
        │
        ▼
┌───────────────────────────────────────────────────┐
│  Validation:                                       │
│  • Check session exists                            │
│  • Check block exists                              │
│  • Validate disposition is "keep" or "discard"    │
└───────────────────────────────────────────────────┘
        │
        ▼
Block status updated in session state
```

**Code Location**: `src/api/routes/sessions.py:302-337`

### Step 4: Generate Routing Plan (LLM Task #2)

**Endpoint**: `POST /api/sessions/{session_id}/routing-plan`

For blocks marked as "keep", the LLM suggests where they should be placed in the library.

```
Only "kept" blocks are processed
        │
        ▼
┌───────────────────────────────────────────────────┐
│            SDK: generate_routing_plan()            │
│                                                    │
│  Input to LLM:                                     │
│  • System prompt (routing instructions)            │
│  • Full library structure (categories, files)      │
│  • For each kept block:                            │
│    - Block ID, type, heading path                  │
│    - Content preview (first 500 chars)             │
│    - Pre-computed candidate destinations with      │
│      similarity scores (from vector search)        │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│              LLM Response (JSON)                   │
│                                                    │
│  {                                                 │
│    "routing_items": [                              │
│      {                                             │
│        "block_id": "block_001",                    │
│        "options": [                                │
│          {                                         │
│            "destination_file": "tech/auth.md",     │
│            "destination_section": "JWT Tokens",    │
│            "action": "append",                     │
│            "confidence": 0.9,                      │
│            "reasoning": "Block discusses JWT..."   │
│          },                                        │
│          { ... option 2 ... },                     │
│          { ... option 3 ... }                      │
│        ]                                           │
│      }                                             │
│    ]                                               │
│  }                                                 │
└───────────────────────────────────────────────────┘
        │
        ▼
User selects one of 3 destination options per block
```

**Supported Routing Actions**:

- `append` - Add to end of existing file/section
- `create_file` - Create new file in library
- `create_section` - Create new section in existing file
- `insert_before` / `insert_after` - Insert relative to section

**Code Location**: `src/sdk/client.py:246-346`, `src/sdk/prompts/routing_mode.py`

### Step 5: Apply User Routing Decisions

**Endpoint**: `POST /api/sessions/{session_id}/blocks/{block_id}/route`

```
User selects destination for each block
        │
        ▼
┌───────────────────────────────────────────────────┐
│  Content written to library file                   │
│  (VerifiedWriter handles actual file operations)   │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│  Trigger library re-indexing                       │
│  (New content added to vector database)            │
└───────────────────────────────────────────────────┘
```

### Step 6: Index Content in Vector Database

**Endpoint**: `POST /api/library/index` (or automatic)

```
Library files
        │
        ▼
┌───────────────────────────────────────────────────┐
│           LibraryIndexer.index_all()               │
│                                                    │
│  1. Scan library directory for .md files           │
│  2. Check file checksums against state file        │
│     (.vector_state.yaml) to detect changes         │
│  3. For changed files:                             │
│     a. Extract chunks (at headers & paragraphs)    │
│     b. Delete old chunks for this file             │
│     c. Generate embeddings for new chunks          │
│     d. Store in Qdrant with metadata               │
│  4. Update state file with new checksums           │
└───────────────────────────────────────────────────┘
```

**Code Location**: `src/vector/indexer.py:58-93`

---

## 3. What the LLM Does

The LLM (Claude) performs three distinct tasks in the system:

### Task 1: Cleanup Planning

**Purpose**: Analyze document blocks to identify content that may not belong in a permanent knowledge library.

**What the LLM looks for**:

- Temporary notes or scratchpad content
- Duplicate or redundant information
- Placeholder text
- Completed todos
- Content that doesn't fit a knowledge library

**Key Rules**:

- **Preserve by default** - When in doubt, suggest KEEP
- **No auto-discard** - All decisions require user approval
- Returns confidence scores (0.0 to 1.0) for each suggestion

**Prompt Location**: `src/sdk/prompts/cleanup_mode.py:14-61`

### Task 2: Routing Planning

**Purpose**: Determine where content blocks should be placed in the library.

**What the LLM does**:

- Analyzes content to understand topic/domain
- Reviews existing library structure (categories, files, sections)
- Considers pre-computed similarity scores to existing content
- Provides exactly 3 destination options per block, ranked by fit

**Key Rules**:

- Match to existing files/sections when possible
- Suggest new files/sections only when truly needed
- Provide clear reasoning for each suggestion

**Prompt Location**: `src/sdk/prompts/routing_mode.py:12-90`

### Task 3: Query Answering (RAG)

**Purpose**: Synthesize accurate answers to user questions based on retrieved library content.

**What the LLM does**:

- Receives user question + retrieved context chunks
- Generates answer using ONLY the provided context
- Includes source citations: `[source: path/to/file.md]`
- Acknowledges gaps when context is insufficient

**Key Rules**:

- Never fabricate information not in context
- Always cite sources
- Be honest about uncertainty

**Prompt Location**: `src/sdk/prompts/output_mode.py:8-45`

### LLM Configuration

```python
# Default model (from src/sdk/client.py:57-63)
model = os.getenv("CLAUDE_MODEL", "claude-opus-4-5-20251101")
max_turns = 6  # Maximum conversation turns
```

---

## 4. Python Validation & API Layer

### API Structure

The API is built with FastAPI and organized into route modules:

```
src/api/
├── main.py           # Application factory, global error handler
├── dependencies.py   # Dependency injection (singletons)
├── errors.py         # Standardized error helpers
├── schemas.py        # Pydantic validation models
└── routes/
    ├── sessions.py   # Document ingestion
    ├── library.py    # Library browsing & indexing
    └── query.py      # Search & RAG queries
```

### Validation Steps

#### 1. File Upload Validation

**Location**: `src/api/routes/sessions.py:136-203`

```
┌─────────────────────────────────────────────────────────────┐
│  Validation Chain:                                          │
│                                                             │
│  1. Session Existence Check                                 │
│     └─ Returns 404 if session not found                     │
│                                                             │
│  2. Duplicate Source Check                                  │
│     └─ Returns 400 if session already has a source          │
│                                                             │
│  3. File Size Validation (10 MB limit)                      │
│     └─ Checks file.size before reading                      │
│     └─ Double-checks after reading actual content           │
│     └─ Returns 413 if too large                             │
│                                                             │
│  4. Filename Sanitization                                   │
│     └─ Extracts base name (removes path components)         │
│     └─ Removes null bytes                                   │
│     └─ Replaces special characters with underscores         │
│     └─ Truncates to 120 characters                          │
│                                                             │
│  5. Path Traversal Prevention                               │
│     └─ Resolves absolute paths                              │
│     └─ Verifies target is within allowed directory          │
│     └─ Returns 400 if path escape attempted                 │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Content Mode Validation

**Location**: `src/api/routes/sessions.py:62-66`

```python
if request.content_mode not in ("strict", "refinement"):
    raise HTTPException(status_code=400,
                        detail="content_mode must be 'strict' or 'refinement'")
```

#### 3. Library File Access Validation

**Location**: `src/api/routes/library.py:79-98`

```python
# Prevent path traversal attacks
library_root = Path(config.library.path).resolve()
target_path = (library_root / file_path).resolve()
if not str(target_path).startswith(str(library_root)):
    raise HTTPException(status_code=403,
                        detail="Access denied: File outside library root")
```

#### 4. Conversation ID Validation

**Location**: `src/api/schemas.py:511-526`

```python
@field_validator("conversation_id")
@classmethod
def validate_conversation_id(cls, v: Optional[str]) -> Optional[str]:
    if v is not None:
        try:
            UUID(v)
        except ValueError:
            raise ValueError("conversation_id must be a valid UUID")
    return v
```

### Key Schema Definitions

| Schema                   | Purpose         | Key Fields                                   |
| ------------------------ | --------------- | -------------------------------------------- |
| `CreateSessionRequest`   | New session     | `source_path`, `content_mode`                |
| `SearchRequest`          | Semantic search | `query`, `n_results`, `min_similarity`       |
| `AskRequest`             | RAG query       | `question`, `max_sources`, `conversation_id` |
| `CleanupDecisionRequest` | Cleanup action  | `disposition` ("keep"/"discard")             |

### Error Handling

**Global Exception Handler** (`src/api/main.py:45-52`):

- Catches all unhandled exceptions
- Logs with unique error ID
- Returns sanitized error response

**Standardized Errors** (`src/api/errors.py`):

- `APIError.not_found()` → 404
- `APIError.bad_request()` → 400
- `APIError.service_unavailable()` → 503
- `APIError.payload_too_large()` → 413

---

## 5. Vector Database & Storage

### Database Technology

- **Vector Database**: Qdrant (async client)
- **Distance Metric**: Cosine similarity
- **Default Collection**: `knowledge_library`

### Embedding Models

| Provider              | Model                    | Dimensions | Notes          |
| --------------------- | ------------------------ | ---------- | -------------- |
| **Mistral** (default) | `mistral-embed`          | 1024       | Recommended    |
| OpenAI                | `text-embedding-3-small` | 1536       | Alternative    |
| OpenAI                | `text-embedding-3-large` | 3072       | High precision |

**Configuration** (`src/config.py:72-79`):

```python
class EmbeddingsConfig(BaseModel):
    provider: str = "mistral"
    model: str = "mistral-embed"
```

### Document Chunking Strategy

**Location**: `src/vector/indexer.py:141-242`

```
┌─────────────────────────────────────────────────────────────┐
│  Chunking Rules:                                            │
│                                                             │
│  1. Split at section headers (#, ##, ###, etc.)             │
│  2. Split at paragraph boundaries (double newlines)         │
│  3. Minimum chunk size: 50 characters                       │
│  4. Target chunk size: 512-2048 tokens                      │
│                                                             │
│  Each chunk gets:                                           │
│  • UUID identifier                                          │
│  • MD5 content hash (for deduplication)                     │
│  • Section context (heading hierarchy)                      │
│  • Chunk index within file                                  │
└─────────────────────────────────────────────────────────────┘
```

### Payload Schema

Each vector point stores rich metadata:

**Location**: `src/payloads/schema.py:138-253`

```python
ContentPayload:
  content_id: str          # UUID identifier
  content_type: ContentType  # AGENT_SYSTEM, BLUEPRINT, FEATURE, etc.
  file_path: str           # Library location
  section: str             # Section header
  chunk_index: int         # Position in file
  chunk_total: int         # Total chunks in file
  content_hash: str        # MD5 for deduplication
  taxonomy: TaxonomyPath   # 4-level hierarchical path
  provenance: Provenance   # Source tracking
  created_at: datetime     # Creation timestamp
  updated_at: datetime     # Last update timestamp
```

### Payload Indexes

**Location**: `src/vector/store.py:86-116`

```python
indexes = [
    ("content_type", KEYWORD),
    ("taxonomy.full_path", KEYWORD),
    ("taxonomy.level1", KEYWORD),
    ("taxonomy.level2", KEYWORD),
    ("file_path", KEYWORD),
    ("content_hash", KEYWORD),
    ("classification.confidence", FLOAT),
    ("created_at", DATETIME),
    ("updated_at", DATETIME),
]
```

### Incremental Indexing

The system tracks file changes to avoid unnecessary re-indexing:

**Location**: `src/vector/indexer.py:58-93`

```
┌─────────────────────────────────────────────────────────────┐
│  Incremental Indexing Flow:                                 │
│                                                             │
│  1. Load state file (.vector_state.yaml)                    │
│     Contains: {file_path: {checksum, indexed_at}}           │
│                                                             │
│  2. For each library file:                                  │
│     a. Calculate MD5 checksum                               │
│     b. Compare with stored checksum                         │
│     c. If unchanged: skip                                   │
│     d. If changed/new: re-index                             │
│                                                             │
│  3. Update state file with new checksums                    │
│                                                             │
│  force=True: Ignores checksums, reindexes everything        │
└─────────────────────────────────────────────────────────────┘
```

### Storage Operations

| Operation       | Method                 | Location           |
| --------------- | ---------------------- | ------------------ |
| Add single item | `add_content()`        | `store.py:118-138` |
| Batch add       | `add_contents_batch()` | `store.py:140-165` |
| Delete by ID    | `delete_content()`     | `store.py:413-418` |
| Delete by file  | `delete_by_file()`     | `store.py:420-434` |
| Update metadata | `update_payload()`     | `store.py:401-411` |

---

## 6. Query & Retrieval Workflow

When a user asks a question, this is the complete flow:

### Complete RAG Pipeline

**Location**: `src/query/engine.py:61-180`

```
┌─────────────────────────────────────────────────────────────┐
│                    User Question                            │
│               "How do I implement JWT auth?"                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Load Conversation Context (if continuing)          │
│                                                             │
│  • Check if conversation_id provided                        │
│  • Load previous turns from ConversationManager             │
│  • Format last 5 turns as context string                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Document Retrieval                                 │
│                                                             │
│  Retriever.retrieve():                                      │
│  1. Fetch 2x candidates from SemanticSearch                 │
│  2. Convert to RetrievedChunk objects                       │
│  3. Deduplicate by content fingerprint (MD5)                │
│  4. Re-rank based on:                                       │
│     • Base similarity score                                 │
│     • Content length bonus (up to +0.1)                     │
│     • Section heading bonus (+0.05)                         │
│     • Query term overlap (up to +0.1)                       │
│  5. Return top_k results                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Format Context for LLM                             │
│                                                             │
│  ResponseFormatter.format_context_for_llm():                │
│                                                             │
│  ## Library Context                                         │
│  [1] Source: tech/authentication.md (Section: JWT Tokens)   │
│  JWT tokens are signed using HMAC-SHA256...                 │
│                                                             │
│  ---                                                        │
│                                                             │
│  [2] Source: tech/security.md (Section: Best Practices)     │
│  Always validate token expiration...                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Build Complete Prompt                              │
│                                                             │
│  build_query_prompt() combines:                             │
│  • Conversation history (if any)                            │
│  • Library context chunks                                   │
│  • Current question                                         │
│  • Response instructions                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: LLM Generation                                     │
│                                                             │
│  ClaudeCodeClient.query_text():                             │
│  • System prompt: "You are a knowledge librarian..."        │
│  • User prompt: formatted context + question                │
│  • Returns: synthesized answer with citations               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Parse Response                                     │
│                                                             │
│  ResponseFormatter.parse_response():                        │
│  • Extract citations: [source: path/to/file.md]             │
│  • Pattern: \[\s*(?:source|file):\s*([^\]]+)\]              │
│  • Returns: answer text + list of source files              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 7: Calculate Confidence Score                         │
│                                                             │
│  _calculate_confidence():                                   │
│  • 70%: Average similarity of top 5 chunks                  │
│  • 20%: Source diversity (1-5 unique sources)               │
│  • 10%: Content coverage (total length up to 5000 chars)    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 8: Persist Conversation                               │
│                                                             │
│  ConversationManager.add_turn():                            │
│  • Save user question as turn                               │
│  • Save assistant answer as turn                            │
│  • Auto-generate title from first message                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    QueryResult                              │
│  {                                                          │
│    answer: "To implement JWT auth, you should...",          │
│    sources: ["tech/authentication.md", "tech/security.md"], │
│    confidence: 0.85,                                        │
│    conversation_id: "abc-123",                              │
│    related_topics: ["OAuth", "Token Refresh"]               │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

### Semantic Search Details

**Location**: `src/vector/search.py:50-107`

```python
async def search(query, n_results=5, min_similarity=0.5, ...):
    # 1. Convert query to embedding
    # 2. Search Qdrant with 2x results (for re-ranking buffer)
    # 3. Filter by minimum similarity threshold
    # 4. Hydrate content from source files
    # 5. Return SearchResult objects
```

### Content Hydration

The system stores embeddings and metadata in Qdrant, but actual content is read from files at query time:

**Location**: `src/vector/search.py:109-168`

```
Why hydration?
• Keeps vector DB lean (only payloads, not full content)
• Content always reflects latest file state
• Easier to update content without re-embedding

Process:
1. Read original markdown file
2. Re-extract chunks using same algorithm
3. Match by chunk_index and content_hash
4. Return actual content (or placeholder if changed)
```

---

## 7. Conversation Management

### Storage

- **Location**: `./sessions/conversations/` directory
- **Format**: JSON files per conversation
- **Index**: `index.json` for efficient listing

### Data Structures

**Location**: `src/query/conversation.py:15-62`

```python
@dataclass
class ConversationTurn:
    role: str          # "user" or "assistant"
    content: str       # Message content
    timestamp: str     # ISO format
    sources: List[str] # Referenced files (for assistant turns)

@dataclass
class Conversation:
    id: str            # UUID
    title: str         # Auto-generated from first message
    created_at: str
    updated_at: str
    turns: List[ConversationTurn]
```

### Context Window

**Location**: `src/query/conversation.py:68`

```python
MAX_CONTEXT_TURNS = 5  # Only last 5 turns included in LLM context
```

This limits token usage while maintaining conversation continuity.

---

## 8. Configuration Reference

### Main Config File

**Location**: `src/config.py`

```python
class AppConfig(BaseModel):
    library: LibraryConfig      # Library path, file types
    embeddings: EmbeddingsConfig  # Provider, model, API keys
    vector: VectorConfig        # Qdrant URL, port, collection
    logging: LoggingConfig      # Log level, format
```

### Key Environment Variables

| Variable          | Purpose                | Default                    |
| ----------------- | ---------------------- | -------------------------- |
| `CLAUDE_MODEL`    | LLM model for SDK      | `claude-opus-4-5-20251101` |
| `MISTRAL_API_KEY` | Embedding API key      | -                          |
| `OPENAI_API_KEY`  | Alternative embeddings | -                          |
| `QDRANT_URL`      | Vector DB host         | `localhost`                |
| `QDRANT_PORT`     | Vector DB port         | `6333`                     |
| `QDRANT_API_KEY`  | Vector DB auth         | -                          |

---

## 9. Improvement Opportunities

This section identifies areas where the system could be enhanced:

### Document Ingestion

1. **Chunk Size Optimization**
   - Current: Fixed minimum 50 chars, target 512-2048 tokens
   - Opportunity: Dynamic chunk sizing based on content type
   - Location: `src/vector/indexer.py:141-242`

2. **Multi-Format Support**
   - Current: Markdown only
   - Opportunity: PDF, DOCX, HTML parsing
   - Location: `src/api/routes/sessions.py:136-203`

3. **Batch Import**
   - Current: Single file per session
   - Opportunity: Folder/bulk import with progress tracking

### LLM Processing

4. **Cleanup Plan Caching**
   - Current: Full LLM call for each cleanup request
   - Opportunity: Cache similar content patterns
   - Location: `src/sdk/client.py:180-244`

5. **Routing Pre-filtering**
   - Current: LLM sees full library structure
   - Opportunity: Pre-filter destinations using vector similarity
   - Location: `src/sdk/prompts/routing_mode.py:93-186`

6. **Streaming Responses**
   - Current: Full response awaited
   - Opportunity: Stream RAG answers for better UX
   - Location: `src/sdk/client.py:127-147`

### Vector Database

7. **Embedding Model Selection**
   - Current: Single provider configured globally
   - Opportunity: Model selection per content type
   - Location: `src/vector/embeddings.py`

8. **Hybrid Search**
   - Current: Pure vector similarity
   - Opportunity: Combine with BM25 keyword search
   - Location: `src/vector/store.py:167-235`

9. **Chunk Overlap**
   - Current: No overlap between chunks
   - Opportunity: Overlapping windows for better context
   - Location: `src/vector/indexer.py:141-242`

### Query & Retrieval

10. **Re-ranking Model**
    - Current: Heuristic scoring (length, terms)
    - Opportunity: Cross-encoder re-ranking
    - Location: `src/query/retriever.py:140-168`

11. **Query Expansion**
    - Current: Direct query embedding
    - Opportunity: LLM-based query rewriting
    - Location: `src/query/retriever.py:67-104`

12. **Confidence Calibration**
    - Current: Weighted average formula
    - Opportunity: Learn calibration from user feedback
    - Location: `src/query/engine.py:204-237`

### API & Validation

13. **Request Rate Limiting**
    - Current: None
    - Opportunity: Per-endpoint rate limits
    - Location: `src/api/main.py`

14. **Input Sanitization**
    - Current: Basic Pydantic validation
    - Opportunity: Content scanning for injection
    - Location: `src/api/schemas.py`

15. **Async Processing**
    - Current: Synchronous request handling
    - Opportunity: Background job queue for indexing
    - Location: `src/api/routes/library.py:145-162`

### Observability

16. **Metrics Collection**
    - Current: Basic logging
    - Opportunity: Prometheus metrics
    - Location: `src/api/main.py`

17. **Tracing**
    - Current: Error IDs only
    - Opportunity: Distributed tracing (OpenTelemetry)

---

## Appendix: API Endpoint Reference

| Endpoint                                 | Method | Purpose                   |
| ---------------------------------------- | ------ | ------------------------- |
| `/api/sessions`                          | POST   | Create extraction session |
| `/api/sessions/{id}`                     | GET    | Get session details       |
| `/api/sessions/{id}/upload`              | POST   | Upload source file        |
| `/api/sessions/{id}/cleanup-plan`        | POST   | Generate cleanup plan     |
| `/api/sessions/{id}/blocks/{id}/cleanup` | POST   | Apply cleanup decision    |
| `/api/sessions/{id}/routing-plan`        | POST   | Generate routing plan     |
| `/api/sessions/{id}/blocks/{id}/route`   | POST   | Apply routing decision    |
| `/api/library`                           | GET    | List library structure    |
| `/api/library/files/{path}`              | GET    | Get file content          |
| `/api/library/index`                     | POST   | Trigger indexing          |
| `/api/query/search`                      | POST   | Semantic search           |
| `/api/query/ask`                         | POST   | RAG query                 |
| `/api/query/conversations`               | GET    | List conversations        |
| `/api/query/conversations/{id}`          | GET    | Get conversation          |
| `/api/query/conversations/{id}`          | DELETE | Delete conversation       |
| `/api/query/similar`                     | POST   | Find similar content      |
| `/health`                                | GET    | Health check              |

---

_Document generated: 2026-01-23_
_AI-Library Version: Based on current codebase analysis_
