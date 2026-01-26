# Current Issues - Hardening Phase

**Last Updated**: 2026-01-12
**Investigation Source**: Comprehensive code analysis + repository cleanup session
**Total Issues**: 17 (14 still present, 3 partially resolved)
**BLOCKER**: C1-01 prevents all tests from running - fix first!

---

## Quick Reference

| ID        | Issue                                     | Status      | Est. Time | Priority     |
| --------- | ----------------------------------------- | ----------- | --------- | ------------ |
| **C1-01** | **conftest.py import ordering (BLOCKER)** | **Present** | **5min**  | **CRITICAL** |
| C1-02     | mcp_server.py duplicate imports           | Present     | 5min      | High         |
| C1-03     | models/events.py missing Optional         | Present     | 5min      | High         |
| T1-01     | test_search_scenarios.py ServiceContainer | Present     | 30min     | High         |
| P1-01     | Result<T,E> Pattern                       | Present     | 4-6h      | High         |
| P1-02     | Custom Exception Hierarchy                | Partial     | 2-3h      | High         |
| P1-03     | Context Managers                          | Present     | 2h        | High         |
| P2-01     | Async Neo4j Service                       | Present     | 4-6h      | Medium       |
| P2-02     | ChromaDB Retry Logic                      | Present     | 2-3h      | Medium       |
| P2-03     | Specific Exception Handling               | Present     | 3-4h      | Medium       |
| P3-01     | Pydantic Validation                       | Partial     | 2h        | Low          |
| P3-02     | Hardcoded Metadata Fields                 | Present     | 15min     | Low          |
| P3-03     | Rate Limiting                             | Present     | 1h        | Low          |
| P3-04     | Full Snapshot Storage                     | Present     | 20min     | Low          |
| P3-05     | Comprehensive Logging                     | Partial     | 2h        | Low          |
| P3-06     | Neo4j Mock Tests                          | Present     | 30min     | Low          |
| P3-07     | Neo4j Config Issues                       | Present     | 1h        | Low          |

**Total Estimated Time**: 24-33 hours (+ 15 min for critical fixes)

---

## Critical Issues - January 2026 (BLOCKER)

**Discovered**: Repository cleanup session (2026-01-12)
**Details**: See `System-Overview/Known-Issues.md` for full documentation

### C1-01: conftest.py Import Ordering (CRITICAL BLOCKER)

**Status**: PRESENT
**File**: `tests/conftest.py`
**Est. Time**: 5 minutes

**Problem**: `import pytest` is on line 86, but `@pytest.fixture` is used at line 20.

**Impact**: **ALL TESTS BLOCKED** - NameError prevents pytest from loading.

**Fix**: Move `import pytest` to line 1-2 (top of file).

---

### C1-02: mcp_server.py Duplicate Imports

**Status**: PRESENT
**File**: `mcp_server.py`
**Est. Time**: 5 minutes

**Problem**: Lines 26-27 duplicate lines 18-19 (ConfidenceEventListener, ConfidenceRuntime imports).

**Fix**: Remove lines 26-27.

---

### C1-03: models/events.py Missing Optional Import

**Status**: PRESENT
**File**: `models/events.py:225`
**Est. Time**: 5 minutes

**Problem**: `Optional` used in `ConceptTauUpdated` class but not imported.

**Fix**: Add `Optional` to typing imports.

---

## Test Infrastructure Issues

### T1-01: test_search_scenarios.py Not Using ServiceContainer

**Status**: PRESENT
**File**: `tests/e2e/test_search_scenarios.py`
**Discovered**: 2026-01-11
**Est. Time**: 30 minutes

**Problem**: The test file uses the old module-level variable assignment pattern instead of the `e2e_configured_container` fixture. All 5 tests fail with "service not initialized" errors.

**Failing Tests**:

1. `TestSearchScenarios::test_semantic_search_basic` - `embedding_service not initialized`
2. `TestSearchScenarios::test_exact_search_with_filters` - `neo4j_service not initialized`
3. `TestSearchScenarios::test_recent_concepts_retrieval` - `neo4j_service not initialized`
4. `TestSearchScenarios::test_hierarchy_listing` - `neo4j_service not initialized`
5. `TestSearchScenarios::test_confidence_range_search` - `neo4j_service not initialized`

**Error Pattern**:

```
WARNING  tools.service_utils:service_utils.py:80 Tool 'search_concepts_semantic' called but embedding_service not initialized
```

**Fix Required**: Update to use `e2e_configured_container` fixture pattern:

```python
class TestSearchScenarios:
    @pytest.fixture(autouse=True)
    def setup_container(self, e2e_configured_container, mock_neo4j, mock_chromadb, mock_embedding_service):
        self.container = e2e_configured_container
        self.mock_neo4j = mock_neo4j
        # ... etc
        yield
```

**Reference**: See Issue #15 in `PRE_COMMIT_FINDINGS.md` for the pattern used to fix similar files.

---

## Priority 1: High Impact

### P1-01: Implement Result<T,E> Pattern

**Status**: PRESENT
**Files**: `services/repository.py`, `scripts/cleanup_duplicates.py`

**Problem**: Methods return `Tuple[bool, Optional[str], ...]` instead of a proper Result type.

**Locations**:

- `services/repository.py:135` - `create_concept()`
- `services/repository.py:262` - `update_concept()`
- `services/repository.py:372` - `delete_concept()`
- `scripts/cleanup_duplicates.py:144` - `consolidate_duplicate()`
- `scripts/cleanup_duplicates.py:258` - `verify_no_duplicates()`

**Fix**: Implement `Result[T, E]` type and replace tuple returns.

---

### P1-02: Custom Exception Hierarchy

**Status**: PARTIALLY RESOLVED
**Files**: `services/neo4j_service.py`, `services/chromadb_service.py`

**What's Done**:

- `EventStoreError`, `RepositoryError`, `OutboxError`, `CompensationError`, `ProjectionError`

**Still Missing**:

- `services/neo4j_service.py` - No `Neo4jError` class
- `services/chromadb_service.py` - No `ChromaDBError` class

**Fix**: Add custom exception classes for Neo4j and ChromaDB services.

---

### P1-03: Context Managers for All Resources

**Status**: PRESENT
**Files**: `services/event_store.py`, `services/outbox.py`, `services/embedding_cache.py`

**Problem**: Manual `.close()` calls instead of `with` statements.

**Locations**:

- `services/event_store.py` - 6 methods
- `services/outbox.py` - 9 methods
- `services/embedding_cache.py` - 5 methods

**Fix**: Replace `conn = _get_connection()...finally: conn.close()` with `with self._get_connection() as conn:`

---

## Priority 2: Medium Impact

### P2-01: Async/Await Refactor for Neo4j Service

**Status**: PRESENT
**Files**: `services/neo4j_service.py`, all callers

**Problem**: Service uses synchronous `GraphDatabase.driver()`.

**Evidence**:

- Line 126: `GraphDatabase.driver()` (sync)
- All 11 methods use `def` not `async def`
- Blocking I/O at lines 136, 192-208, 361-362, 400-401

**Fix**: Convert to `AsyncGraphDatabase.driver()` and async methods. Consider deferring due to large scope.

---

### P2-02: ChromaDB Retry Logic

**Status**: PRESENT
**Files**: `services/chromadb_service.py`, `mcp_server.py`, `projections/chromadb_projection.py`

**Problem**: No retry logic for transient failures (Neo4j has it, ChromaDB doesn't).

**Missing in**:

- Connection initialization in `mcp_server.py`
- All ChromaDB service methods
- Projection operations (add, update, delete)

**Fix**: Add exponential backoff retry similar to Neo4j's `TransientError` handling.

---

### P2-03: Specific Exception Handling

**Status**: PRESENT (51 instances)
**Files**: All service files

**Problem**: Generic `except Exception as e` masks errors.

**Count by file**:
| File | Count |
|------|-------|
| `services/repository.py` | 9 |
| `services/outbox.py` | 9 |
| `services/neo4j_service.py` | 8 |
| `services/event_store.py` | 6 |
| `services/embedding_cache.py` | 5 |
| `mcp_server.py` | 5 |
| `services/chromadb_service.py` | 4 |
| `services/consistency_checker.py` | 4 |
| `services/compensation.py` | 3 |
| `services/embedding_service.py` | 3 |

**Fix**: Replace with specific exception types, re-raise unexpected errors.

---

## Priority 3: Low Impact

### P3-02: Hardcoded Metadata Fields

**Status**: PRESENT
**File**: `services/consistency_checker.py:222`

```python
for field in ['name', 'area', 'topic', 'subtopic', 'confidence_score']:
```

**Fix**: Extract to `METADATA_FIELDS` constant or derive from schema.

---

### P3-03: Rate Limiting for Consistency Checks

**Status**: PRESENT
**File**: `services/consistency_checker.py`

**Problem**: No cooldown between consistency checks.

**Fix**: Add `_last_check_time`, `_min_check_interval`, and `RateLimitError`.

---

### P3-04: Full Snapshot Storage

**Status**: PRESENT
**File**: `services/consistency_checker.py:338-342`

**Problem**: Discrepancy lists truncated to 10 items.

```python
discrepancies.append(f"Neo4j only: {report.neo4j_only[:10]}")  # Data loss!
```

**Fix**: Store full JSON or create `snapshot_discrepancies` table.

---

### P3-01: Pydantic Validation

**Status**: PARTIALLY IMPLEMENTED
**Files**: `services/repository.py`, `services/consistency_checker.py`, `tools/search_tools.py`

**Problem**: Core services accept raw dicts without validation.

**What's Done**: Tools layer has Pydantic models
**Missing**: Repository, consistency checker, search tools validation

---

### P3-05: Comprehensive Logging

**Status**: PARTIALLY IMPLEMENTED (~25%)
**Files**: All service files

**Problem**: No structured metrics logging.

**Missing**:

- `duration_ms` tracking
- Connection pool stats
- Queue depth metrics
- Consistent `extra={}` usage

---

### P3-06: Neo4j Mock Test Fixes

**Status**: PRESENT
**File**: `tests/test_neo4j_service.py`

**Problem**: `test_execute_read_success` (lines 195-216) uses improper mock.

**Fix**: Mock should return Neo4j Result object, not plain list.

---

### P3-07: Neo4j Config Issues

**Status**: PRESENT (4 sub-issues)
**Files**: `services/neo4j_service.py`, `scripts/init_neo4j.py`

1. `min_pool_size` defined but unused
2. No database name validation
3. Misleading schema init output
4. Health check doesn't test writes

---

## Recommended Fix Order

### BLOCKERS (fix immediately)

1. **C1-01**: conftest.py import ordering (5 min) - **UNBLOCKS ALL TESTS**
2. **C1-02**: mcp_server.py duplicate imports (5 min)
3. **C1-03**: models/events.py missing Optional (5 min)

### Quick Wins (do next)

1. **P3-02**: Hardcoded fields (15 min)
2. **P3-04**: Snapshot storage (20 min)
3. **P3-06**: Mock test fix (30 min)
4. **P3-03**: Rate limiting (1 hour)

### Medium Effort

5. **P1-03**: Context managers (2 hours)
6. **P1-02**: Exception hierarchy (2-3 hours)
7. **P2-02**: ChromaDB retry (2-3 hours)
8. **P2-03**: Exception handling (3-4 hours)

### Consider Deferring

- **P2-01**: Async Neo4j (large refactor, affects many files)
- **P1-01**: Result pattern (significant API changes)

---

## Files by Change Frequency

When fixing, consider grouping by file:

| File                              | Issues                            |
| --------------------------------- | --------------------------------- |
| `tests/conftest.py`               | **C1-01 (BLOCKER)**               |
| `mcp_server.py`                   | C1-02, P2-03                      |
| `models/events.py`                | C1-03                             |
| `services/consistency_checker.py` | P2-03, P3-01, P3-02, P3-03, P3-04 |
| `services/neo4j_service.py`       | P1-02, P2-01, P2-03, P3-07        |
| `services/repository.py`          | P1-01, P2-03, P3-01               |
| `services/chromadb_service.py`    | P1-02, P2-02, P2-03               |
| `services/event_store.py`         | P1-03, P2-03                      |
| `services/outbox.py`              | P1-03, P2-03                      |
