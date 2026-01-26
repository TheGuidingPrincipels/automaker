# Quick Fix Guide: Test & CI/CD Issues

## Overview

- **Unit Tests**: 127 passed, 2 FAILED
- **Integration Tests**: 46 passed, 3 FAILED + 3 ERRORS (missing fixture)
- **Code Quality**: 50+ files need formatting, 20+ have linting issues
- **Pipeline Status**: BLOCKED - cannot deploy

---

## Priority 1: Critical Test Fixes (BLOCKING)

### Fix 1: test_concept_deleted_event_clears_cache

**File**: `tests/unit/confidence/test_event_listener.py` (Line 94)

**Current Issue**:

```python
assert "REMOVE c.certainty_score_auto" in args[0]
# FAILS because the query is now:
# MATCH (c:Concept {concept_id: $concept_id})
# SET c.certainty_score = 0.0
# REMOVE c.confidence_last_calculated
```

**Options**:

1. **Option A**: Update the implementation to also remove `certainty_score_auto`
2. **Option B**: Update the test to match the new implementation
   ```python
   assert "REMOVE c.confidence_last_calculated" in args[0]
   # And remove the certainty_score_auto assertion
   ```

**Recommendation**: Check with the team which behavior is correct, then update either the code or test accordingly.

---

### Fix 2: test_non_confidence_event_is_skipped

**File**: `tests/unit/confidence/test_event_listener.py` (Line 114)

**Current Issue**:

```python
# Test expects:
assert stats == {"processed": 0, "failed": 0, "skipped": 1}

# But gets:
assert stats == {"processed": 1, "failed": 0, "skipped": 0}
```

**Root Cause**: The event handling logic now processes relationship events instead of skipping them.

**Action**: Check the event listener implementation and decide:

1. Should non-confidence events be skipped? (update implementation)
2. OR should they be processed? (update test)

---

### Fix 3: test_relationship_created_updates_both_concepts

**File**: `tests/integration/test_confidence_fix_integration.py` (Line 141)

**Current Issue**:

```python
assert 'certainty_score_auto' in query
# Query doesn't include this property update
```

**Action**: Similar to Fix 1 - align query implementation with test expectations.

---

### Fix 4: Repository Not Initialized in Integration Tests

**Files**:

- `tests/integration/test_worker_timing.py:57` (test_race_condition_handling)
- `tests/integration/test_worker_timing.py:145` (test_relationship_triggered_recalculation)

**Current Issue**:

```
KeyError: 'concept_id'
WARNING: Tool 'create_concept' called but repository not initialized
```

**Solution**: Add repository initialization to test setup

```python
# In conftest.py or test file:
@pytest.fixture
async def initialized_repository():
    """Create and initialize repository before test"""
    # Setup mock or real Neo4j service
    # Setup ChromaDB service
    # Create DualStorageRepository
    # Set it globally or pass to test
    yield repo
    # Cleanup
```

---

### Fix 5: Missing Test Fixture

**File**: `tests/integration/conftest.py`

**Current Issue**:

```
fixture 'neo4j_session_adapter' not found
```

**Files Affected**:

- `tests/integration/confidence/test_data_access_property_fix.py` (3 tests)

**Solution**: Add this fixture to `tests/integration/conftest.py`:

```python
@pytest.fixture
async def neo4j_session_adapter():
    """
    Provide a Neo4j session adapter for integration tests.
    This wraps the neo4j_session fixture with any needed adapter logic.
    """
    # Option 1: Simple wrapper around neo4j_session
    session = neo4j_session  # This needs to be injected

    # Option 2: Create a DataAccessLayer adapter
    from services.confidence.data_access import DataAccessLayer
    adapter = DataAccessLayer(session)

    yield adapter
```

Or look at where this fixture is used and implement accordingly.

---

## Priority 2: Code Quality Fixes (NON-BLOCKING but important)

### Auto-Format Code

```bash
# Install tools if not already
pip install black isort

# Fix formatting
black .
isort .

# Verify
black --check .
isort --check-only .
```

### Fix Specific Ruff Issues

**config.py** - Fix import sorting:

```python
# Before:
import os
from pathlib import Path

from dotenv import load_dotenv

# After (proper order):
import os
from pathlib import Path

from dotenv import load_dotenv
```

**mcp_server.py** - Remove unused imports:

```python
# Remove:
from pathlib import Path  # Unused

# Remove from imports:
get_service_status  # This import is unused
```

---

## Priority 3: CI/CD Pipeline Improvements (OPTIONAL)

### Option A: Make Linting Blocking

**File**: `.github/workflows/ci-cd.yml`

Change from:

```yaml
- name: Run Ruff (Fast Python linter)
  run: |
    ruff check . --output-format=github || true  # Silent fail
```

To:

```yaml
- name: Run Ruff (Fast Python linter)
  run: |
    ruff check . --output-format=github  # Fail on errors
```

### Option B: Keep Non-Blocking but Add Reporting

```yaml
- name: Run Ruff (Fast Python linter)
  id: ruff
  run: |
    ruff check . --output-format=github || echo "ruff_failed=true" >> $GITHUB_OUTPUT

- name: Report Linting Issues
  if: always()
  run: |
    if [ "${{ steps.ruff.outputs.ruff_failed }}" = "true" ]; then
      echo "⚠️ Linting issues found (non-blocking)"
    fi
```

---

## Testing & Verification

### Run Tests Locally

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires Neo4j/Redis)
pytest tests/integration/ -v

# Run specific failing test
pytest tests/unit/confidence/test_event_listener.py::test_concept_deleted_event_clears_cache -v
```

### Check Code Quality

```bash
# Linting
ruff check .

# Formatting
black --check .

# Import sorting
isort --check-only .
```

---

## Files Modified Checklist

After fixing issues, these files will be modified:

- [ ] `tests/unit/confidence/test_event_listener.py` (fix 2 tests)
- [ ] `tests/integration/test_worker_timing.py` (fix setup/repo init)
- [ ] `tests/integration/test_confidence_fix_integration.py` (fix expectations)
- [ ] `tests/integration/conftest.py` (add missing fixture)
- [ ] `services/confidence/event_listener.py` (if changing behavior)
- [ ] `config.py` (format)
- [ ] `mcp_server.py` (remove unused imports, format)
- [ ] Multiple service files (format)
- [ ] `.github/workflows/ci-cd.yml` (optional: make linting blocking)

---

## Expected Outcome

After fixes:

- [ ] All unit tests pass (129/129)
- [ ] All integration tests pass (52/52, excluding slow tests)
- [ ] All code passes linting
- [ ] All code passes formatting checks
- [ ] CI/CD pipeline shows green
- [ ] Deployment can proceed

---

## Questions?

1. **Should `certainty_score_auto` be removed or not?**
   - Check with the confidence scoring team
   - Look at the schema changes and migration notes

2. **Should relationship events be skipped or processed?**
   - Check the event listener design doc
   - Verify against the confidence calculation logic

3. **Is the `|| true` approach correct for linting?**
   - Non-blocking linting is good for iterative development
   - But should be part of merge requirements or pre-commit hooks

---
