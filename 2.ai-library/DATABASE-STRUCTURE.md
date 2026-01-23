# AI Library Database Structure Reference

> Token-efficient guide for Claude sessions working with the Knowledge Library System.

## Architecture Overview

**Storage Layers:**
| Layer | Technology | Location |
|-------|-----------|----------|
| Sessions | JSON files | `./sessions/` |
| Library | Markdown + YAML | `./library/` |
| Vectors | Qdrant DB | `localhost:6333` |
| Config | YAML | `./configs/` |

---

## 1. Session Storage

**Location:** `sessions/{session_id}.json`

**Model:** `src/models/session.py` → `ExtractionSession`

```
ExtractionSession:
├── id: str
├── phase: SessionPhase (10 states)
├── source: SourceDocument
├── cleanup_plan: CleanupPlan
├── routing_plan: RoutingPlan
├── conversation_history: list[dict]
├── execution_log: list[str]
└── errors: list[str]
```

**Phase Lifecycle:**
`INITIALIZED` → `PARSING` → `CLEANUP_PLAN_READY` → `ROUTING_PLAN_READY` → `AWAITING_APPROVAL` → `READY_TO_EXECUTE` → `EXECUTING` → `VERIFYING` → `COMPLETED`

**Access:** `src/session/storage.py` → `SessionStorage`

- `save(session)` - Atomic write (tmp → rename)
- `load(id)` - Direct JSON parse
- `list_sessions()` - Directory scan
- `delete(id)` - File unlink

---

## 2. Library Storage

**Location:** `library/` with `_index.yaml` metadata

**Structure:**

```
library/
├── _index.yaml          # Category tree
├── _backups/            # Pre-write backups
└── {category}/
    └── file.md          # Content with block markers
```

**Model:** `src/models/library.py` → `LibraryFile`, `LibraryCategory`

**Block Markers in Markdown:**

```html
<!-- BLOCK_START id=uuid source=file.md session=sid checksum=sha256 written=ts -->
...content...
<!-- BLOCK_END id=uuid -->
```

**Access:** `src/library/`

- `scanner.py` → `LibraryScanner.scan()` - File discovery
- `categories.py` → `CategoryManager` - Category CRUD
- `manifest.py` → `LibraryManifest` - Searchable snapshot

---

## 3. Vector Storage (Qdrant)

**Config:** `configs/settings.yaml`

```yaml
vector:
  url: localhost
  port: 6333
  collection_name: knowledge_library
embeddings:
  provider: mistral # or openai
  model: mistral-embed
```

**Collection:** `knowledge_library`

- **Distance:** Cosine similarity
- **Dimensions:** 1024 (Mistral) / 1536 (OpenAI)

**Payload Schema:** `src/payloads/schema.py` → `ContentPayload`

```
ContentPayload:
├── content_id: str (UUID)
├── content_type: enum (agent_system|blueprint|feature|research|note|general)
├── title: Optional[str]
├── file_path: str
├── section: Optional[str]
├── chunk_index: int
├── chunk_total: int
├── content_hash: str (MD5)
├── taxonomy: TaxonomyPath
│   └── level1, level2, level3, level4, full_path
├── classification: ClassificationResult
│   └── confidence, tier_used, reasoning
├── provenance: Provenance
│   └── source_file, extraction_method, ingested_at
└── relationships: list[Relationship]
```

**Payload Indexes:**

- `content_type` (KEYWORD)
- `taxonomy.full_path`, `taxonomy.level1`, `taxonomy.level2` (KEYWORD)
- `file_path` (KEYWORD)
- `content_hash` (KEYWORD)
- `classification.confidence` (FLOAT)
- `created_at`, `updated_at` (DATETIME)

**Index State:** `.vector_state.yaml` - Tracks per-file checksums for incremental indexing

**Access:** `src/vector/`

- `store.py` → `QdrantVectorStore` - CRUD operations
- `indexer.py` → `VectorIndexer` - Chunk & index library
- `search.py` → `SemanticSearch` - Query interface

---

## 4. Conversation Storage

**Location:** `sessions/conversations/`

```
conversations/
├── index.json           # Metadata index
└── {conv_id}.json       # Full conversation
```

**Access:** `src/query/conversation.py` → `ConversationManager`

- Atomic writes with per-conversation locks
- Paginated listing via index file

---

## 5. Configuration

**Main:** `configs/settings.yaml` (122 lines)

| Section          | Purpose                                            |
| ---------------- | -------------------------------------------------- |
| `library`        | Library path                                       |
| `sessions`       | Session storage path                               |
| `sdk`            | Claude model config                                |
| `embeddings`     | Provider, model, API key                           |
| `vector`         | Qdrant connection                                  |
| `chunking`       | 512-2048 tokens, 128 overlap                       |
| `classification` | Two-tier confidence thresholds                     |
| `ranking`        | Weights: similarity 60%, taxonomy 25%, recency 15% |

**Taxonomy:** `configs/taxonomy.yaml` - Hierarchical category schema

---

## 6. API Routes

**Sessions:**
| Method | Endpoint | Handler |
|--------|----------|---------|
| GET | `/api/sessions` | List all |
| POST | `/api/sessions` | Create |
| GET | `/api/sessions/{id}` | Get |
| PUT | `/api/sessions/{id}` | Update |
| DELETE | `/api/sessions/{id}` | Delete |

**Library:**
| Method | Endpoint | Handler |
|--------|----------|---------|
| GET | `/api/library` | Full structure |
| GET | `/api/library/categories` | Top-level |
| GET | `/api/library/files/{path}` | File metadata |
| GET | `/api/library/files/{path}/content` | File content |
| GET | `/api/library/search?query=` | Section search |
| POST | `/api/library/index` | Trigger indexing |
| GET | `/api/library/index/stats` | Index stats |

**Query:**
| Method | Endpoint | Handler |
|--------|----------|---------|
| POST | `/api/query/search` | Semantic search |
| POST | `/api/query/ask` | RAG Q&A |
| GET | `/api/query/conversations` | List conversations |
| GET | `/api/query/conversations/{id}` | Get conversation |
| DELETE | `/api/query/conversations/{id}` | Delete |
| POST | `/api/query/similar` | Merge candidates |

---

## 7. Key Source Files

**Models:**

- `src/models/session.py` - ExtractionSession, SessionPhase
- `src/models/content.py` - ContentBlock, SourceDocument
- `src/models/library.py` - LibraryFile, LibraryCategory
- `src/payloads/schema.py` - ContentPayload (vector metadata)

**Storage:**

- `src/session/storage.py` - SessionStorage (JSON persistence)
- `src/vector/store.py` - QdrantVectorStore
- `src/vector/indexer.py` - LibraryIndexer
- `src/query/conversation.py` - ConversationManager

**Access:**

- `src/library/scanner.py` - LibraryScanner
- `src/vector/search.py` - SemanticSearch
- `src/query/engine.py` - QueryEngine (RAG orchestration)
- `src/query/retriever.py` - Retriever (re-ranking)

**API:**

- `src/api/main.py` - FastAPI app
- `src/api/routes/sessions.py`
- `src/api/routes/library.py`
- `src/api/routes/query.py`
- `src/api/dependencies.py` - Singleton DI

---

## 8. Data Flow

```
Query → FastAPI Route
  ↓
Dependency Injection (singletons)
  ↓
QueryEngine.ask() or SemanticSearch.search()
  ↓
Embed query → Qdrant similarity search
  ↓
Hydrate content from library files
  ↓
Re-rank (similarity + taxonomy + recency)
  ↓
[RAG: Claude LLM augmentation]
  ↓
Persist conversation → Return JSON
```

---

## 9. Integrity & Checksums

**Content Modes:**

- `STRICT` - Byte-exact code blocks
- `REFINEMENT` - Allows formatting changes

**Checksum Verification:** `src/extraction/checksums.py`

- Code: SHA256 of raw bytes
- Prose: SHA256 of canonical form (normalized whitespace)

**Write Verification:** `src/execution/writer.py`

- Writes with markers → reads back → verifies checksum

---

## Quick Reference

| What              | Where                                 |
| ----------------- | ------------------------------------- |
| Session data      | `sessions/{id}.json`                  |
| Library content   | `library/{category}/file.md`          |
| Library index     | `library/_index.yaml`                 |
| Vector embeddings | Qdrant `knowledge_library` collection |
| Vector state      | `.vector_state.yaml`                  |
| Conversations     | `sessions/conversations/`             |
| Config            | `configs/settings.yaml`               |
| Taxonomy          | `configs/taxonomy.yaml`               |
