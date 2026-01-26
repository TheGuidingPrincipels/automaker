# Product Requirements Document: Short-Term Memory MCP

## Overview

Short-Term Memory MCP is a Model Context Protocol (MCP) server that provides temporary storage and pipeline management for daily learning concepts. It serves as the "working memory" layer between research/learning activities and permanent knowledge storage (Knowledge MCP).

## System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Short-Term Memory MCP                     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Sessions   │  │   Concepts   │  │ Research Cache  │  │
│  │              │  │              │  │                 │  │
│  │ Daily goals  │  │ SHOOT stages │  │ • Explanations  │  │
│  │ Status       │  │ Status track │  │ • Source URLs   │  │
│  │ Retention    │  │ Stage data   │  │ • Quality score │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Domain Whitelist                        │  │
│  │  • Official docs (1.0)                               │  │
│  │  │  • In-depth tutorials (0.8)                       │  │
│  │  • Authoritative sources (0.6)                       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
           │                                      │
           ↓ (Transfer)                           ↓ (Research)
┌─────────────────────┐              ┌─────────────────────┐
│   Knowledge MCP     │              │    Context7 MCP     │
│                     │              │                     │
│ • Permanent storage │              │ • Research concepts │
│ • Neo4j graph       │              │ • Source URLs       │
│ • ChromaDB vectors  │              │ • Explanations      │
└─────────────────────┘              └─────────────────────┘
```

## Database Schema

### sessions Table

| Column        | Type             | Description                  |
| ------------- | ---------------- | ---------------------------- |
| session_id    | TEXT PRIMARY KEY | Date in YYYY-MM-DD format    |
| date          | TEXT NOT NULL    | Session date                 |
| learning_goal | TEXT             | What to learn today          |
| building_goal | TEXT             | What to build today          |
| status        | TEXT             | 'in_progress' or 'completed' |
| created_at    | TEXT             | ISO timestamp                |
| updated_at    | TEXT             | ISO timestamp                |

**Indexes**:

- `idx_sessions_date` on `date`
- `idx_sessions_status` on `status`

### concepts Table

| Column           | Type             | Description                     |
| ---------------- | ---------------- | ------------------------------- |
| concept_id       | TEXT PRIMARY KEY | UUID                            |
| session_id       | TEXT NOT NULL    | FK to sessions                  |
| concept_name     | TEXT NOT NULL    | Concept name                    |
| current_status   | TEXT             | Status (see ConceptStatus enum) |
| identified_at    | TEXT             | When identified                 |
| chunked_at       | TEXT             | When chunked                    |
| encoded_at       | TEXT             | When encoded                    |
| evaluated_at     | TEXT             | When evaluated                  |
| stored_at        | TEXT             | When stored to Knowledge MCP    |
| knowledge_mcp_id | TEXT             | ID in Knowledge MCP             |
| current_data     | TEXT             | JSON of cumulative data         |
| user_questions   | TEXT             | JSON array of questions         |
| created_at       | TEXT             | ISO timestamp                   |
| updated_at       | TEXT             | ISO timestamp                   |

**Indexes**:

- `idx_concepts_session` on `session_id`
- `idx_concepts_status` on `current_status`
- `idx_concepts_session_status` on `(session_id, current_status)`
- `idx_concepts_name` on `concept_name`

**ConceptStatus Enum**:

- `identified` - Found in research
- `chunked` - Chunked for processing
- `encoded` - Encoded as vectors
- `evaluated` - Evaluated for understanding
- `stored` - Stored to Knowledge MCP

### concept_stage_data Table

| Column     | Type                | Description               |
| ---------- | ------------------- | ------------------------- |
| id         | INTEGER PRIMARY KEY | Auto-increment            |
| concept_id | TEXT NOT NULL       | FK to concepts            |
| stage      | TEXT NOT NULL       | Stage name (SHOOT stages) |
| data       | TEXT NOT NULL       | JSON data                 |
| created_at | TEXT                | ISO timestamp             |

**Unique Constraint**: `(concept_id, stage)`

**Indexes**:

- `idx_stage_data_concept_stage` on `(concept_id, stage)`

### research_cache Table (Session 001-004)

| Column             | Type                 | Description                     |
| ------------------ | -------------------- | ------------------------------- |
| id                 | INTEGER PRIMARY KEY  | Auto-increment                  |
| concept_name       | TEXT NOT NULL UNIQUE | Normalized concept name         |
| explanation        | TEXT NOT NULL        | Research explanation            |
| source_urls        | TEXT                 | JSON array of SourceURL objects |
| last_researched_at | TEXT NOT NULL        | Last research timestamp         |
| created_at         | TEXT NOT NULL        | First cached timestamp          |
| updated_at         | TEXT NOT NULL        | Last updated timestamp          |

**Indexes**:

- `idx_research_cache_name` on `concept_name`
- `idx_research_cache_created` on `created_at`

**SourceURL Format**:

```json
{
  "url": "https://docs.python.org/3/library/asyncio.html",
  "title": "asyncio — Asynchronous I/O",
  "quality_score": 1.0,
  "domain_category": "official"
}
```

### domain_whitelist Table (Session 001-004)

| Column        | Type                 | Description                             |
| ------------- | -------------------- | --------------------------------------- |
| id            | INTEGER PRIMARY KEY  | Auto-increment                          |
| domain        | TEXT NOT NULL UNIQUE | Domain name (e.g., "docs.python.org")   |
| category      | TEXT NOT NULL        | 'official', 'in_depth', 'authoritative' |
| quality_score | REAL NOT NULL        | 0.0-1.0 quality score                   |
| added_at      | TEXT NOT NULL        | When added                              |
| added_by      | TEXT                 | 'system' or 'ai'                        |

**Check Constraints**:

- `category IN ('official', 'in_depth', 'authoritative')`
- `quality_score >= 0.0 AND quality_score <= 1.0`

**Indexes**:

- `idx_domain_whitelist_domain` on `domain`
- `idx_domain_whitelist_category` on `category`

**Initial Whitelist**:
| Domain | Category | Score |
|--------|----------|-------|
| docs.python.org | official | 1.0 |
| reactjs.org | official | 1.0 |
| developer.mozilla.org | official | 1.0 |
| kubernetes.io | official | 1.0 |
| realpython.com | in_depth | 0.8 |
| freecodecamp.org | in_depth | 0.8 |
| css-tricks.com | in_depth | 0.8 |
| github.com | authoritative | 0.6 |
| stackoverflow.com | authoritative | 0.6 |
| medium.com | authoritative | 0.6 |

## MCP Tools

### Tier 1: Core Session Tools (6 tools)

#### initialize_daily_session

- **Purpose**: Create new daily learning session
- **Parameters**: `learning_goal`, `building_goal`, `date` (optional)
- **Returns**: Session ID, cleanup statistics
- **Auto-cleanup**: Deletes sessions older than retention period (7 days default)

#### get_active_session

- **Purpose**: Get current session with statistics
- **Parameters**: `date` (optional)
- **Returns**: Session details, concept counts by status

#### store_concepts_from_research

- **Purpose**: Bulk store identified concepts
- **Parameters**: `session_id`, `concepts` (array)
- **Returns**: Created concept IDs

#### get_concepts_by_session

- **Purpose**: List concepts for session
- **Parameters**: `session_id`, `status_filter` (optional), `include_stage_data` (bool)
- **Returns**: Concept list with optional stage data

#### update_concept_status

- **Purpose**: Update concept status
- **Parameters**: `concept_id`, `new_status`, `timestamp` (optional)
- **Returns**: Previous and new status

#### store_stage_data

- **Purpose**: Store stage-specific data
- **Parameters**: `concept_id`, `stage`, `data` (dict)
- **Returns**: Data ID

### Tier 2: Reliability Tools (4 tools)

#### mark_session_complete

- **Purpose**: Mark session as complete
- **Parameters**: `session_id`
- **Returns**: Success or warning (if concepts unstored)

#### clear_old_sessions

- **Purpose**: Manual cleanup of old sessions
- **Parameters**: `days_to_keep` (default: 7)
- **Returns**: Deletion statistics

#### get_concepts_by_status

- **Purpose**: Filter concepts by single status
- **Parameters**: `session_id`, `status`
- **Returns**: Filtered concepts

#### get_stage_data

- **Purpose**: Retrieve stage-specific data
- **Parameters**: `concept_id`, `stage`
- **Returns**: Stage data with timestamp

### Tier 3: Knowledge MCP Integration (2 tools)

#### mark_concept_stored

- **Purpose**: Mark concept as transferred to Knowledge MCP
- **Parameters**: `concept_id`, `knowledge_mcp_id`
- **Returns**: Success status, stored timestamp

#### get_unstored_concepts

- **Purpose**: List concepts not yet transferred
- **Parameters**: `session_id`
- **Returns**: Unstored concepts list

### Tier 4: Code Teacher Support (3 tools)

#### get_todays_concepts

- **Purpose**: Get all concepts from today (cached 5 minutes)
- **Parameters**: None (uses current date)
- **Returns**: Concepts with statistics, `cache_hit` flag

#### get_todays_learning_goals

- **Purpose**: Get today's goals (cached 5 minutes)
- **Parameters**: None
- **Returns**: Learning/building goals, concept statistics

#### search_todays_concepts

- **Purpose**: Search today's concepts by name/content
- **Parameters**: `search_term`
- **Returns**: Matching concepts (cached per query)

### Tier 5: Monitoring & Production (3 tools)

#### health_check

- **Purpose**: Check system health
- **Parameters**: None
- **Returns**: Database status, cache status, response time

#### get_system_metrics

- **Purpose**: Get performance metrics
- **Parameters**: None
- **Returns**: Operation counts, timing statistics, database size

#### get_error_log

- **Purpose**: Retrieve recent errors
- **Parameters**: `limit` (default: 10, max: 100), `error_type` (optional)
- **Returns**: Error entries with timestamps

### Tier 6: User Questions & Relationships (4 tools)

#### add_concept_question

- **Purpose**: Add user question to concept
- **Parameters**: `concept_id`, `question`, `session_stage`
- **Returns**: Updated questions list

#### get_concept_page

- **Purpose**: Get comprehensive concept view
- **Parameters**: `concept_id`
- **Returns**: All data, stage data, questions, relationships, timeline

#### add_concept_relationship

- **Purpose**: Link two concepts
- **Parameters**: `concept_id`, `related_concept_id`, `relationship_type`
- **Returns**: Relationship details

#### get_related_concepts

- **Purpose**: Get concept relationships
- **Parameters**: `concept_id`, `relationship_type` (optional)
- **Returns**: Related concepts with enriched data

### Tier 9: Research Cache Tools (6 tools) - Session 004

#### check_research_cache

- **Purpose**: Check if concept is cached
- **Parameters**: `concept_name`
- **Returns**: `cached` (bool), `entry` (if cached), `cache_age_seconds`

#### trigger_research

- **Purpose**: Trigger research for concept (Context7 placeholder)
- **Parameters**: `concept_name`, `research_prompt`
- **Returns**: `explanation`, `source_urls` (scored)

#### update_research_cache

- **Purpose**: UPSERT cache entry
- **Parameters**: `concept_name`, `explanation`, `source_urls`
- **Returns**: `success`, `entry`, `action` (inserted/updated)

#### add_domain_to_whitelist

- **Purpose**: Add trusted domain
- **Parameters**: `domain`, `category`, `quality_score`
- **Returns**: Domain entry

#### remove_domain_from_whitelist

- **Purpose**: Remove domain from whitelist
- **Parameters**: `domain`
- **Returns**: Success status

#### list_whitelisted_domains

- **Purpose**: List whitelisted domains
- **Parameters**: `category` (optional filter)
- **Returns**: Domain list, count

## SHOOT Stage Workflow (Session 005)

### Without Cache (Legacy)

```python
async def shoot_stage_handler(concepts: List[str]) -> List[dict]:
    results = []
    for concept in concepts:
        # Always research (no cache check)
        research = await context7_research(concept)
        results.append({
            "concept": concept,
            "explanation": research.explanation,
            "status": "researched"
        })
    return results
```

### With Cache (Session 005)

```python
async def shoot_stage_handler(concepts: List[str], db: Database) -> List[dict]:
    results = []
    cache_hits = 0
    cache_misses = 0

    for concept in concepts:
        # Check cache first
        cache_result = await check_research_cache_impl(concept, db)

        if cache_result["cached"]:
            # Cache hit - use cached explanation
            logger.info(f"Cache HIT: {concept}")
            cache_hits += 1
            entry = cache_result["entry"]
            results.append({
                "concept": concept,
                "explanation": entry["explanation"],
                "source_urls": entry["source_urls"],
                "status": "cache_hit",
                "cache_age_seconds": cache_result["cache_age_seconds"]
            })
        else:
            # Cache miss - trigger research
            logger.info(f"Cache MISS: {concept}")
            cache_misses += 1
            research = await trigger_research_impl(concept, "", db)
            await update_research_cache_impl(
                concept_name=concept,
                explanation=research["explanation"],
                source_urls=research["source_urls"],
                db=db
            )
            results.append({
                "concept": concept,
                "explanation": research["explanation"],
                "source_urls": research["source_urls"],
                "status": "cache_miss"
            })

    # Log cache statistics
    hit_rate = (cache_hits / len(concepts) * 100) if concepts else 0
    logger.info(f"Cache statistics: {cache_hits} hits, {cache_misses} misses ({hit_rate:.1f}% hit rate)")

    return results
```

## Knowledge MCP Integration (Session 005)

### Extended Tools

Knowledge MCP's `create_concept` and `update_concept` tools have been extended with optional `source_urls` parameter:

```python
async def create_concept(
    name: str,
    explanation: str,
    area: Optional[str] = None,
    topic: Optional[str] = None,
    subtopic: Optional[str] = None,
    source_urls: Optional[str] = None  # NEW: JSON string
) -> Dict[str, Any]:
    """
    Create concept with optional source URLs.

    Args:
        source_urls: Optional JSON string containing array of:
            [
                {
                    "url": "https://...",
                    "title": "...",
                    "quality_score": 1.0,
                    "domain_category": "official"
                }
            ]
    """
```

### Storage Locations

- **Neo4j**: `source_urls` property on Concept node (JSON string)
- **ChromaDB**: `source_urls` in metadata (JSON string)
- **Event Store**: `source_urls` in `ConceptCreated` event

### Transfer Workflow

See [Concept-Transfer-Workflow.md](docs/Concept-Transfer-Workflow.md) for complete workflow documentation.

## Performance Targets

### Cache Performance

- **Cache hit latency**: <100ms (95th percentile)
- **Cache vs research speedup**: >5x (median)
- **Duplicate research reduction**: 40-60%

### Database Performance

- **Session creation**: <50ms
- **Concept storage (bulk)**: <200ms for 10 concepts
- **Concept search**: <30ms

### API Performance

- **Health check**: <100ms
- **Tool execution**: <1s (excluding research)

### Retention

- **Auto-cleanup**: Sessions older than 7 days (configurable via `DB_RETENTION_DAYS`)
- **Manual cleanup**: Available via `clear_old_sessions` tool

## Configuration

Environment variables (`.env`):

```bash
# Database
DB_PATH=short_term_mcp.db
DB_RETENTION_DAYS=7

# Performance
ENABLE_WAL=true
AUTO_VACUUM=true

# Logging
LOG_LEVEL=INFO
```

## Testing

### Test Coverage

- **165 total tests** (as of Session 004)
- **10 integration tests** (Session 005)
- **5 performance benchmarks** (Session 005)

### Test Suites

- `test_tools.py` - Core tool functionality
- `test_database.py` - Database operations
- `test_cache.py` - Cache functionality
- `test_research_cache.py` - Research cache tools
- `test_research_cache_integration.py` - Integration tests (Session 005)
- `test_research_cache_performance.py` - Performance benchmarks (Session 005)

### Running Tests

```bash
# All tests
pytest short_term_mcp/tests/ -v

# Integration tests only
pytest short_term_mcp/tests/test_research_cache_integration.py -v

# Performance benchmarks
pytest short_term_mcp/tests/benchmarks/ -v -m benchmark
```

## Dependencies

### Core

- `mcp` - Model Context Protocol SDK
- `sqlite3` - Database (built-in)
- `pydantic` - Data validation

### Development

- `pytest` - Testing framework
- `pytest-asyncio` - Async test support

## Deployment

### MCP Server Configuration

```json
{
  "mcpServers": {
    "short-term-memory": {
      "command": "uv",
      "args": ["--directory", "/path/to/Short-Term-Memory-MCP", "run", "short-term-mcp"]
    }
  }
}
```

### Database Initialization

Database is auto-created on first run with:

- All tables
- Indexes
- Initial domain whitelist

## Security

### SQL Injection

- All queries use parameterized statements
- No string concatenation in SQL

### Data Validation

- Pydantic models validate all inputs
- Foreign key constraints enforced
- Check constraints on enum values

## Known Limitations

1. **Single-user**: No multi-user support or authentication
2. **Local storage only**: SQLite database on local filesystem
3. **No concurrent sessions**: One session per day (by design)
4. **Research placeholder**: Context7 integration is mocked (to be implemented)
5. **Cache cleanup**: Manual cleanup required (no auto-expiration)

## Future Enhancements

1. **Auto cache expiration**: TTL for cache entries (30 days)
2. **Batch transfer**: Parallel concept transfer to Knowledge MCP
3. **Real Context7 integration**: Replace mock research
4. **Cache versioning**: Track research freshness
5. **URL validation**: Verify URLs are still accessible
6. **Multi-session support**: Multiple concurrent sessions

## Version History

- **v0.1.0** - Initial release (Core tools, Sessions, Concepts)
- **v0.2.0** - Reliability tools, Code Teacher support
- **v0.3.0** - Monitoring, User questions, Relationships
- **v0.4.0** - Research cache, Domain whitelist (Session 001-004)
- **v0.5.0** - SHOOT stage integration, Knowledge MCP transfer (Session 005)

## Related Documentation

- [Concept-Transfer-Workflow.md](docs/Concept-Transfer-Workflow.md) - Transfer workflow
- [TROUBLESHOOTING-GUIDE.md](TROUBLESHOOTING-GUIDE.md) - Debugging guide
- [Session-System-Prompts-Guide.md](Session-System-Prompts-Guide.md) - Session instructions
