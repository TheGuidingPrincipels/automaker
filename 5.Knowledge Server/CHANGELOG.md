# Changelog

All notable changes to the MCP Knowledge Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-11-12

### Added

- **`get_tool_availability` MCP tool** - New diagnostic tool (tool #3) for checking service initialization status
  - Reports which tools are available/unavailable
  - Shows detailed service status for all backend services
  - Always available (no dependencies)
  - Location: `mcp_server.py:378-438`

- **`@requires_services` decorator** - Service dependency validation for all tools
  - Validates service availability before tool execution
  - Prevents `AttributeError` crashes when services are uninitialized
  - Returns clear `service_unavailable` error messages
  - Location: `tools/service_utils.py:16-92`

- **Service status utilities** - Helper functions for service monitoring
  - `get_service_status()`: Report initialization status of all services
  - `get_available_tools()`: List available and unavailable tools
  - Location: `tools/service_utils.py:95-218`

- **Comprehensive test suite** for service validation
  - 25 tests covering decorator behavior
  - 100% passing (25/25)
  - Tests decorator validation, real tool integration, and status utilities
  - Location: `tests/test_service_decorator.py`

### Changed

- **Tool count increased** from 16 to 17 tools
- **All 16 existing tools** now protected with `@requires_services` decorator
  - Concept tools: `@requires_services('repository')`
  - Search tools: `@requires_services('neo4j_service', 'chromadb_service', 'embedding_service')`
  - Relationship tools: `@requires_services('neo4j_service', 'event_store', 'outbox')`
  - Analytics tools: `@requires_services('neo4j_service')`

- **Error response format** - Added new error type
  - `service_unavailable` (503): Required backend service not initialized

### Fixed

- **Missing source_urls parameter exposure** in MCP tool wrappers (Issue #1)
  - Added `source_urls` parameter to `create_concept` and `update_concept` MCP tools
  - Backend already supported source_urls, but MCP interface layer didn't expose it
  - Users can now pass source URLs when creating/updating concepts
  - Maintains backward compatibility via optional parameter (defaults to None)
  - Follows existing pattern of optional parameters (aliases, area, topic, subtopic)
  - Location: `mcp_server.py` (create_concept and update_concept functions)
  - Test coverage: 8 new tests, all passing

- **24 critical null pointer vulnerabilities** across all tool modules
  - `concept_tools.py`: 5 null pointer issues (lines 133, 152, 233, 345, 417)
  - `search_tools.py`: 4 null pointer issues (lines 80, 100, 282, 401)
  - `relationship_tools.py`: 12 null pointer issues (multiple locations)
  - `analytics_tools.py`: 3 null pointer issues (lines 78, 109, 283)
  - Tools now return clear errors instead of crashing with `AttributeError`

### Documentation

- Updated `System-Overview/01-MCP-TOOLS.md` to v1.1
  - Added `get_tool_availability` tool documentation
  - Added "Service Availability & Troubleshooting" section
  - Updated tool count from 16 to 17
  - Updated error type table with `service_unavailable`

- Updated `docs/ERROR_HANDLING_GUIDE.md` to v1.1
  - Added "Service Availability Protection" section
  - Documented `@requires_services` decorator usage
  - Added troubleshooting guide for service unavailable errors
  - Updated error type list to 17 types

- Updated `System-Overview/Known-Issues.md` to v1.1
  - Added resolution entry for 24 null pointer vulnerabilities
  - Documented fix implementation and impact

- Updated `README.md`
  - Added troubleshooting section
  - Updated feature list with service protection
  - Updated tool count from 16 to 17
  - Added quick diagnostic steps

### Migration Notes

- **Backward Compatible**: No breaking changes
- **New Error Type**: Clients should handle `service_unavailable` (503) error type
- **New Tool**: `get_tool_availability` available for diagnostic purposes
- **Deployment**: No special migration steps required

---

## [Unreleased]

### Added - 2025-11-06

#### Confidence Scoring System - Session 8 (NFR Validation) ✅

**Services**:

- `services/confidence/nfr_validation.py` – async helpers to capture latency, cache, scalability, and accuracy metrics plus a consolidated validation report builder.

**Tests**:

- `tests/performance/test_confidence_nfr.py` – synthetic-yet-deterministic workload verifying p95 latency under 50ms, cache hit rate ≥85%, throughput above 1k calculations/sec, and accuracy thresholds (R² ≥0.75, MAE ≤0.15).

**Operational Notes**:

- Metrics surfaced to plan progress for auditability and provide clear go/no-go signalling for the certainty automation rollout.

### Added - 2025-11-05

#### Confidence Scoring System - Session 7 (Schema Update & Initial Scores) ✅

**Scripts**:

- `scripts/update_confidence_schema.py` – idempotent schema updater that seeds certainty properties and respects configurable retention tau defaults.
- `scripts/generate_initial_scores.py` – batch processor that reuses the composite runtime to populate scores, components, and cache entries for existing concepts.
- `scripts/validate_confidence_scores.py` – reporting utility that checks nulls, range compliance, and aggregates score statistics.

**Tests**:

- `tests/unit/confidence/test_confidence_scripts.py` – exercises schema updates, score generation success/failure handling, and validation metrics via async-friendly fakes.

**Operational Notes**:

- Scripts load `.env` configuration, support dependency injection for testing, and emit structured logging for plan auditability.

#### Confidence Scoring System - Session 6 (Integration Layer) ✅

**Runtime & Services**:

- `services/confidence/event_listener.py` – polls the event store for concept lifecycle events, recalculates automated certainty scores, and updates Neo4j/Redis with checkpointed progress.
- `services/confidence/runtime.py` – wires cache manager, composite calculator, and an async Neo4j session adapter; returns a managed runtime bundle with graceful teardown.
- `mcp_server.py` – bootstraps the confidence runtime, injects calculators into MCP tools, and starts a background worker that processes events on a five-second interval with safe shutdown handling.

**Tooling**:

- `tools/concept_tools.get_concept` now prefers automated scores when available, triggers on-demand calculations, and normalizes responses to the existing 0–100 scale.

**Tests**:

- `tests/unit/confidence/test_event_listener.py` – covers success, deletion, skip, and failure paths with checkpoint/assertion validation.
- `tests/test_concept_tools.py` – expanded coverage for automated score precedence, on-demand calculation, and error fallback behaviour.

### Added - 2025-11-04

#### Confidence Scoring System - Session 1 (Foundation Layer) ✅

**New Modules**:

- `services/confidence/models.py` - Pydantic data models for type-safe confidence calculation
  - `ConceptData` - Complete concept representation with validation
  - `RelationshipData` - Relationship metrics with deduplication
  - `ReviewData` - Review history with age calculation
  - `CompletenessReport` - Metadata scoring (explanation 40%, tags 30%, examples 30%)
  - `Error/Success` types - Result<T, E> pattern for predictable error handling

- `services/confidence/validation.py` - Input validation services
  - `validate_concept_id()` - ID format validation (non-empty, max 255 chars)
  - `validate_score()` - Score range validation [0.0, 1.0]
  - `validate_timestamp()` - ISO 8601 timestamp parsing
  - `check_data_completeness()` - Weighted metadata analysis

- `services/confidence/data_access.py` - Async Neo4j queries for confidence inputs
  - `DataAccessLayer.get_concept_for_confidence()` - Fetch concept with all fields
  - `DataAccessLayer.get_concept_relationships()` - Bidirectional relationship query
  - `DataAccessLayer.get_review_history()` - Review age calculation with created_at fallback

**Test Suite**:

- 38 unit tests with 99% code coverage
- Mock-based testing (no database dependencies)
- Edge case coverage: empty inputs, boundary values, error handling

**Design Patterns**:

- Result<T, E> for explicit error handling (no exceptions thrown)
- Pydantic models for runtime validation and type safety
- Async/await throughout for non-blocking I/O

**Integration**:

- Reuses existing `neo4j_service.py` connection pool
- Compatible with repository pattern for future integration (Session 6)
- Designed for composition (cache layer in Session 2)

**Dependencies**:

- Provides foundation for Sessions 2-6 (cache, calculators, integration)
- No dependencies on other sessions

**Commits**:

- `61312fd` - feat(session-1): implement foundation layer for confidence scoring system
- `d30cbde` - chore(progress): update session-1 completion status

**Documentation**:

- Added `System-Overview/05-CONFIDENCE-SCORING.md`
- Updated `feat-20251103-certainty-automation/progress.json`

---

#### Confidence Scoring System - Session 4 (Retention Engine + Composite Calculator) ✅

**New Modules**:

- `services/confidence/retention_calculator.py` - FSRS-inspired exponential decay retention model with tau updates and cache integration
- `services/confidence/composite_calculator.py` - 60/40 weighted blend of understanding and retention scores
- `tests/unit/confidence/test_retention_calculator.py` - 10 unit tests covering decay curves, tau updates, caching, and error paths
- `tests/unit/confidence/test_composite_calculator.py` - 4 unit tests verifying weighted combination and error propagation
- `tests/integration/test_retention_composite_integration.py` - 6 integration scenarios across time-based retention and composite behavior

**Enhancements**:

- `services/confidence/data_access.py` now exposes `get_concept_tau` / `update_concept_tau` for persistence of retention parameters
- `services/confidence/config.py` introduces `ConfidenceConfig` centralizing retention and composite weights with env overrides
- `services/confidence/retention_calculator.py` reuses cache manager for review history and gracefully handles missing concepts
- `services/confidence/__init__.py` updated module index to include retention/composite calculators

**Test Suite**:

- `pytest -m "not integration"` → 765 passed (unit suite)
- `pytest tests/integration/test_retention_composite_integration.py` → 6 passed (integration scenarios)

**Design Notes**:

- Retention curve uses `e^(-(days / τ))` with configurable tau multipliers (default 1.5x, capped at 90 days)
- Composite score enforces bounds [0.0, 1.0] and reuses Result pattern for consistency

**Files Updated**:

- `services/confidence/config.py`, `services/confidence/data_access.py`, `services/confidence/__init__.py`
- Repository documentation (`System-Overview/Execution/feat-20251103-certainty-automation.md`)
- Plan progress tracking (`feat-20251103-certainty-automation/progress.json`)

---

#### Confidence Scoring System - Session 5 (Event System + Scheduler) ✅

**New Modules**:

- `services/confidence/event_processor.py` - Observer-pattern dispatcher with built-in handlers for concept, relationship, and review events
- `services/confidence/scheduler.py` - Redis-locked priority queue with per-concept deduplication and batching for recalculations

**Test Suite**:

- `tests/unit/confidence/test_event_processor.py` - Validates handler registration, validation, and side effects for each event type
- `tests/unit/confidence/test_scheduler.py` - Covers priority ordering, lock enforcement, and deduplication behaviour
- `tests/integration/test_event_workflows.py` - End-to-end event scenarios covering concept updates, relationship churn, and review completions

**Runtime Enhancements**:

- Distributed locking via Redis SETNX with Lua-backed safe release
- Priority-aware batching within five-second windows to reduce redundant recalculations
- Cache invalidation coordination across score and calculation tiers

**Verification**:

- `pytest tests/unit/confidence` → 105 passed
- `pytest tests/integration/test_event_workflows.py` → 4 passed

## [0.1.0] - 2025-10-31

### Initial Release

Core MCP knowledge management server with Neo4j and ChromaDB dual storage.

**Features**:

- Concept CRUD operations via MCP tools
- Semantic search with vector embeddings
- Graph-based relationship management
- ChromaDB integration for similarity search
- Neo4j schema for structured knowledge storage

**Documentation**:

- System-Overview/ with architecture, algorithms, schema
- MCP tools reference
- Known issues and limitations

---

[Unreleased]: https://github.com/yourusername/mcp-knowledge-server/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/mcp-knowledge-server/releases/tag/v0.1.0
