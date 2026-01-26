# Short-Term Memory MCP - Product Requirements Document

**Version:** 1.0.0
**Status:** Production Ready
**Last Updated:** 2025-10-11

---

## Executive Summary

The Short-Term Memory MCP is a **daily concept lifecycle management system** that tracks 20-25 learning concepts through a structured 5-stage pipeline. It serves as a **7-day temporary staging area** between Research sessions and permanent Knowledge MCP storage, coordinating 6 different Claude Project sessions working together through file handoffs and status tracking.

**Key Capabilities:**

- 22 MCP tools across 5 tiers
- 5-stage pipeline (Research → AIM → SHOOT → SKIN → Storage)
- Hybrid storage (cumulative + incremental stage data)
- Multi-session coordination (6 Claude projects)
- Auto-cleanup (7-day retention)
- Production monitoring (health, metrics, errors)

---

## System Architecture

### Design Philosophy

**Purpose:** Temporary staging system for active learning concepts

**Core Principles:**

- Fresh context per session (no chat history)
- File handoffs between sessions (JSON files + MCP status)
- User does thinking, AI handles logistics (80/20 cognitive load)
- Pipeline orchestration (track status, not content)
- Auto-cleanup (concepts stored or deleted after 7 days)

**What This Is NOT:**

- Not a conversational assistant
- Not permanent storage (use Knowledge MCP)
- Not a learning assistant (use session-specific Claude projects)

---

## Database Schema

### Tables

**sessions** (Daily learning sessions)

```sql
session_id TEXT PRIMARY KEY        -- YYYY-MM-DD format
date TEXT NOT NULL
learning_goal TEXT                 -- What to learn today
building_goal TEXT                 -- What to build today
status TEXT                        -- 'in_progress' | 'completed'
created_at, updated_at TEXT
```

**concepts** (Individual concepts, 20-25 per session)

```sql
concept_id TEXT PRIMARY KEY        -- UUID
session_id TEXT                    -- FK → sessions
concept_name TEXT                  -- "useState Hook"
current_status TEXT                -- 'identified'|'chunked'|'encoded'|'evaluated'|'stored'

-- Timeline timestamps
identified_at, chunked_at, encoded_at, evaluated_at, stored_at TEXT

-- Links
knowledge_mcp_id TEXT              -- Permanent storage ID

-- Hybrid storage
current_data TEXT                  -- JSON: cumulative merged data
user_questions TEXT                -- JSON: questions during learning

created_at, updated_at TEXT
```

**concept_stage_data** (Incremental stage-specific data)

```sql
concept_id TEXT                    -- FK → concepts
stage TEXT                         -- 'research'|'aim'|'shoot'|'skin'
data TEXT                          -- JSON: stage-specific data
created_at TEXT

UNIQUE(concept_id, stage)          -- One entry per stage per concept
```

**research_cache** (Temporary cache for research outputs)

```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
concept_name TEXT UNIQUE NOT NULL
explanation TEXT NOT NULL
source_urls TEXT                   -- JSON array of SourceURL models
last_researched_at TEXT NOT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
```

**domain_whitelist** (Trusted domains for quality scoring)

```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
domain TEXT UNIQUE NOT NULL
category TEXT NOT NULL CHECK(category IN ('official','in_depth','authoritative'))
quality_score REAL NOT NULL CHECK(quality_score BETWEEN 0.0 AND 1.0)
added_at TEXT NOT NULL
added_by TEXT DEFAULT 'system'
```

> Seeded with 10 trusted domains (docs.python.org, reactjs.org, mdn, kubernetes.io, realpython.com, freecodecamp.org, css-tricks.com, github.com, stackoverflow.com, medium.com) on initialization.

### Indexes (11 total)

- `idx_sessions_date`, `idx_sessions_status`
- `idx_concepts_session`, `idx_concepts_status`, `idx_concepts_session_status` (composite)
- `idx_concepts_name`, `idx_stage_data_concept_stage` (composite)
- `idx_research_cache_name`, `idx_research_cache_created`
- `idx_domain_whitelist_domain`, `idx_domain_whitelist_category`

### Storage Strategy: Hybrid

**Cumulative:** `concepts.current_data` (merged data from all stages, fast access)
**Incremental:** `concept_stage_data` (stage-by-stage snapshots, audit trail)

**Rationale:** Quick access to latest state + historical progression

---

## 5-Stage Pipeline

### Status Progression

```
IDENTIFIED → CHUNKED → ENCODED → EVALUATED → STORED
(Research)   (AIM)     (SHOOT)   (SKIN)      (Storage)
```

### Stage Details

**Research (IDENTIFIED):**

- Bulk insert 20-25 concepts from resource analysis
- Initial metadata: definition, resources, category
- **Tools:** `initialize_daily_session`, `store_concepts_from_research`

**AIM (CHUNKED):**

- Create 3-5 preliminary groups
- Generate 2-3 guiding questions per concept
- User does chunking, AI organizes
- **Tools:** `get_concepts_by_session`, `store_stage_data`, `update_concept_status`

**SHOOT (ENCODED):**

- Two-pass encoding (quick: all 25, deep: 8-10 hardest)
- Self-explanation, relationships, difficulty rating
- Socratic questioning by AI, user struggles productively
- **Tools:** `get_stage_data`, `store_stage_data`, `add_concept_relationship`, `add_concept_question`, `update_concept_status`

**SKIN (EVALUATED):**

- Explain from memory (no notes)
- AI verifies accuracy vs SHOOT data
- Semantic batching (3-5 batches, 5-7 concepts each)
- **Tools:** `get_concepts_by_session`, `get_stage_data`, `store_stage_data`, `update_concept_status`

**Storage (STORED):**

- Transfer to Knowledge MCP (batch-by-batch)
- Link concepts via `knowledge_mcp_id`
- Verify completion before marking session complete
- **Tools:** `get_concepts_by_session`, `get_related_concepts`, `mark_concept_stored`, `get_unstored_concepts`, `mark_session_complete`

---

## Tool Catalog (22 Tools)

### Tier 1: Session Management (2 tools)

- `initialize_daily_session` - Start new session, auto-cleanup old sessions (7-day retention)
- `get_active_session` - Query session with concept statistics

### Tier 2: Data Staging (3 tools)

- `store_concepts_from_research` - Bulk insert 20-25 concepts (30s timeout)
- `store_stage_data` - Save stage-specific data (UPSERT pattern)
- `get_stage_data` - Retrieve stage-specific data

### Tier 3: Concept Management (4 tools)

- `get_concepts_by_session` - Query with status filter, optional stage data
- `update_concept_status` - Transition to next stage, update timestamp
- `get_concepts_by_status` - Convenience wrapper for single status
- `get_unstored_concepts` - Find concepts missing `knowledge_mcp_id`

### Tier 4: Knowledge MCP Integration (1 tool)

- `mark_concept_stored` - Link to Knowledge MCP, set status=stored

### Tier 5: Reliability (2 tools)

- `mark_session_complete` - Validate all concepts stored, finalize session
- `clear_old_sessions` - Manual cleanup (auto-cleanup runs on session creation)

### Tier 6: Code Teacher Support (3 tools - Cached 5min)

- `get_todays_concepts` - Full concept list + statistics (cache_hit flag)
- `get_todays_learning_goals` - Lightweight, goals + counts only
- `search_todays_concepts` - Case-insensitive search, cached per query

### Tier 7: Knowledge Graph (4 tools)

- `add_concept_question` - Track user questions during learning
- `get_concept_page` - Comprehensive single-page view (timeline, stage data, questions, relationships)
- `add_concept_relationship` - Link concepts (prerequisite, related, similar, builds_on)
- `get_related_concepts` - Query relationships with optional type filter

### Tier 8: Monitoring (3 tools)

- `health_check` - System health (database, cache, response time <50ms)
- `get_system_metrics` - Database size, operation counts, performance timing
- `get_error_log` - Recent errors with filtering (limit, error_type)

---

## Multi-Session Architecture

### 6 Claude Project Sessions

**1. Research Session** (Automated Script)

- Tools: `initialize_daily_session`, `store_concepts_from_research`
- Pattern: Automated, no user interaction
- Output: 20-25 concepts with status=identified

**2. AIM Session** (Claude Project 1 - Chunking)

- Tools: `get_active_session`, `get_concepts_by_session`, `store_stage_data`, `update_concept_status`
- Pattern: User chunks, AI organizes
- Output: 3-5 preliminary groups, concepts with status=chunked

**3. SHOOT Session** (Claude Project 2 - Encoding)

- Tools: `get_concepts_by_session`, `get_stage_data`, `store_stage_data`, `add_concept_relationship`, `add_concept_question`, `update_concept_status`
- Pattern: User explains, AI asks Socratic questions
- Output: Self-explanations, relationships, concepts with status=encoded

**4. SKIN Session** (Claude Project 3 - Verification)

- Tools: `get_concepts_by_session`, `get_stage_data`, `store_stage_data`, `update_concept_status`
- Pattern: User explains from memory, AI verifies accuracy
- Output: Verification data, semantic batches, concepts with status=evaluated

**5. Storing Session** (Claude Project 4 - Knowledge MCP Transfer)

- Tools: `get_concepts_by_session`, `get_stage_data`, `get_related_concepts`, `mark_concept_stored`, `get_unstored_concepts`, `mark_session_complete`
- Pattern: Automated transfer to Knowledge MCP
- Output: Concepts with knowledge_mcp_id, session with status=completed

**6. Code Teacher** (Conversational Assistant)

- Tools: `get_todays_learning_goals`, `get_todays_concepts`, `search_todays_concepts`
- Pattern: Calibrated assistance during building
- Output: Help calibrated to what user learned today

### Communication Pattern

Sessions communicate via:

1. JSON files (handoffs between sessions)
2. Short-term MCP status (concept.current_status)
3. Stage data (concept_stage_data table)

No shared chat history - each session starts fresh.

---

## Performance & Monitoring

### Performance Targets (All Met)

- Health check: <50ms (actual: ~12ms)
- Batch insert (25): <100ms (actual: ~2.5ms)
- Query session: <50ms (actual: ~0.1ms with cache)
- Cache hit: <1ms (actual: <1ms)

### Caching Strategy

- **Code Teacher cache:** 5-minute TTL (get*todays*_, search*todays*_)
- **General cache:** Not used (learning sessions need real-time status)
- **Background cleanup:** Every 2.5 minutes (CACHE_TTL/2)

### Concurrency Control

- Semaphore: Max 5 concurrent database operations
- Async operations: All DB calls use `asyncio.to_thread()`
- Cache locking: Thread-safe with `asyncio.Lock`

### Monitoring

- **health_check:** Database connectivity, cache status, response time
- **get_system_metrics:** DB size, operation counts, timing statistics
- **get_error_log:** Recent errors with context (last 100)

### Data Retention

- **Auto-cleanup:** 7 days (runs on session creation)
- **Manual cleanup:** `clear_old_sessions(days_to_keep)`
- **Cascade deletion:** Foreign keys delete concepts + stage_data

---

## Integration Points

### Knowledge MCP

**Purpose:** Permanent storage for concepts after evaluation

**Integration Flow:**

1. Short-term MCP stores concept through pipeline
2. When status=evaluated, transfer to Knowledge MCP
3. Knowledge MCP returns permanent `concept_id`
4. Call `mark_concept_stored(concept_id, knowledge_mcp_id)`
5. Short-term MCP links concept, sets status=stored

**Data Transfer:**

- All stage data (research, aim, shoot, skin)
- User questions
- Relationships
- Timeline (identified_at → stored_at)

### Code Teacher

**Purpose:** Provide today's learning context to building assistant

**Integration Flow:**

1. Code Teacher starts conversation
2. Query `get_todays_learning_goals()` (cached)
3. If user asks about concept, `search_todays_concepts(term)` (cached per query)
4. Calibrate assistance based on concept status:
   - encoded/evaluated/stored → minimal help (user learned this)
   - identified/chunked → more help (user hasn't learned yet)

**Cache Performance:**

- 5-minute TTL prevents database thrashing
- cache_hit flag indicates cache status
- Background cleanup prevents stale data

---

## Configuration

### File Locations

- **Database:** `data/short_term_memory.db` (SQLite)
- **Logs:** `logs/short_term_mcp.log`, `logs/errors.log` (JSON structured)
- **Config:** `short_term_mcp/config.py`

### Configurable Parameters

- `DB_RETENTION_DAYS = 7` - Session retention
- `ENABLE_WAL = True` - SQLite WAL mode for concurrent access
- `AUTO_VACUUM = True` - Automatic space reclamation
- `QUERY_TIMEOUT = 5.0` - Query timeout in seconds
- `BATCH_SIZE = 25` - Max concepts per batch
- `CACHE_TTL = 300` - Cache TTL in seconds

### Dependencies

- **fastmcp >= 2.12.4** - MCP server framework
- **pydantic >= 2.0.0** - Data validation
- **Python >= 3.11** - Required version

---

## Error Handling

### Error Codes

- `TIMEOUT` - Operation exceeded timeout (20s default, 30s for bulk)
- `SESSION_NOT_FOUND` - Session doesn't exist
- `CONCEPT_NOT_FOUND` - Concept doesn't exist
- `INVALID_STATUS` - Invalid status enum value
- `INVALID_STAGE` - Invalid stage enum value
- `INVALID_RELATIONSHIP_TYPE` - Invalid relationship type
- `UPDATE_FAILED` - Database update failed
- `EMPTY_SEARCH_TERM` - Search term is empty

### Timeout Protection

All tools wrapped with `asyncio.wait_for(coro, timeout=20.0)`

```python
{
    "status": "error",
    "error_code": "TIMEOUT",
    "message": "Operation timed out after 20 seconds"
}
```

### Validation

- Enum validation for statuses and stages
- Session existence checks before concept operations
- Concept existence checks before updates
- Pydantic models validate all inputs

---

## Testing

### Test Coverage

- **159 tests total, 100% pass rate**
- Phase 0: Setup (3 tests)
- Phase 1: Database (24 tests)
- Phase 2: Core Tools (24 tests)
- Phase 3: Integration (19 tests)
- Phase 4: Reliability (17 tests)
- Phase 5: Code Teacher (20 tests)
- Phase 6: Knowledge Graph (25 tests)
- Phase 7: Production (27 tests)

### Running Tests

```bash
pytest short_term_mcp/tests/ -v
pytest short_term_mcp/tests/test_production.py -v
pytest --cov=short_term_mcp --cov-report=term-missing
```

---

## Key Constraints

### Design Constraints

1. **7-day retention:** Concepts deleted if not stored within 7 days
2. **Sequential progression:** Status only moves forward (can't go backwards)
3. **One session per day:** Session ID = date (YYYY-MM-DD)
4. **Batch size:** Recommended 20-25 concepts per session
5. **No skipping stages:** Must progress identified → chunked → encoded → evaluated → stored

### Operational Constraints

1. **Fresh context:** Each Claude session starts fresh (no chat history)
2. **User does thinking:** AI handles logistics only (80/20 split)
3. **File handoffs:** Sessions communicate via JSON + MCP status
4. **Real-time status:** Learning sessions query directly (no caching except Code Teacher)
5. **Storage required:** Sessions won't complete until all concepts stored

---

## Quick Reference

### Typical Daily Workflow

```
09:00 - Research Session: initialize_daily_session + store_concepts_from_research
11:00 - AIM Session: chunk concepts → status=chunked
14:00 - SHOOT Session: encode concepts → status=encoded
18:00 - SKIN Session: verify concepts → status=evaluated
20:00 - Storing Session: transfer to Knowledge MCP → status=stored
       - Continuous: Code Teacher queries learning context
```

### Status Transitions

```
Research  → IDENTIFIED (bulk insert 20-25)
AIM       → CHUNKED (chunking + questions)
SHOOT     → ENCODED (self-explanation + relationships)
SKIN      → EVALUATED (verification + semantic batching)
Storing   → STORED (Knowledge MCP transfer)
```

### Common Queries

```python
# Start day
await initialize_daily_session(learning_goal, building_goal)

# Get concepts to process
await get_concepts_by_session(session_id, status_filter="identified")

# Update status after processing
await update_concept_status(concept_id, "chunked")

# Store stage data
await store_stage_data(concept_id, "aim", {...})

# Check completion
unstored = await get_unstored_concepts(session_id)
if unstored["unstored_count"] == 0:
    await mark_session_complete(session_id)
```

---

## Version History

**1.0.0** (2025-10-11) - Production release

- 22 MCP tools across 8 tiers
- Hybrid storage architecture
- Multi-session coordination
- Production monitoring
- 159 tests, 100% pass rate

---

**Document Purpose:** Quick reference for understanding Short-Term Memory MCP system architecture, capabilities, and constraints. Use this document to get oriented in new sessions and understand how the system works at a high level.

**Token Count:** ~3,800 tokens
