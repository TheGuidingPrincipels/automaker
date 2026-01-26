# Phase 5: Test Organization Cleanup

## Context

This is Phase 5 of a 6-phase refactoring effort for the MCP Knowledge Server codebase. This phase focuses on organizing tests consistently and centralizing shared fixtures.

**Prerequisites:** Phases 1-4 should be completed first

---

## Problem Statement

Test organization is inconsistent:

| Issue                       | Example                                                            |
| --------------------------- | ------------------------------------------------------------------ |
| Mixed locations             | Root-level `test_repository.py` + `unit/` + `integration/` subdirs |
| Duplicate fixtures          | `mock_understanding_calculator` defined in multiple files          |
| Multiple mocking approaches | Mock, AsyncMock, MagicMock, custom Fake*, Stub* classes            |
| Inconsistent async handling | `@pytest.mark.asyncio` vs `@pytest_asyncio.fixture`                |
| Mixed test styles           | Function-based and class-based tests in same directories           |

**Target:** Clear organization, centralized fixtures, consistent patterns

---

## Pre-Implementation: Investigation Phase

Before making changes, launch 3 Explore agents:

### Agent 1: Test File Location Investigation

```
Map all test files in the codebase:
- tests/ root level files
- tests/unit/ contents
- tests/integration/ contents
- tests/e2e/ contents
- tests/performance/ contents
- tests/security/ contents
- Any other test directories

Document: File count per directory, which files could be moved.
```

### Agent 2: Fixture Investigation

```
Find all pytest fixtures:
- tests/conftest.py fixtures
- Local fixtures in individual test files
- Which fixtures are duplicated across files
- Fixture dependencies

Document: All fixtures, their locations, and duplications.
```

### Agent 3: Mocking Pattern Investigation

```
Analyze mocking approaches:
- Usage of Mock, AsyncMock, MagicMock
- Custom Fake* classes (FakeSession, FakeDriver, etc.)
- Custom Stub* classes
- patch() usage patterns
- Which tests use which approach

Document: Frequency of each approach and recommendations.
```

---

## Implementation Steps

### Step 1: Define Target Structure

```
tests/
├── conftest.py                 # ALL shared fixtures
├── unit/
│   ├── conftest.py             # Unit test specific setup
│   ├── tools/
│   │   ├── test_concept_tools.py
│   │   ├── test_search_tools.py
│   │   ├── test_relationship_tools.py
│   │   └── test_analytics_tools.py
│   ├── services/
│   │   ├── test_repository.py
│   │   ├── test_neo4j_service.py
│   │   ├── test_chromadb_service.py
│   │   └── test_embedding_service.py
│   └── confidence/
│       ├── test_composite_calculator.py
│       ├── test_understanding_calculator.py
│       └── test_retention_calculator.py
├── integration/
│   ├── conftest.py             # Real database fixtures
│   ├── test_repository_integration.py
│   ├── test_dual_storage.py
│   └── confidence/
│       └── test_confidence_integration.py
├── e2e/
│   ├── conftest.py             # Full stack fixtures
│   ├── test_mcp_server.py
│   └── test_search_scenarios.py
├── performance/
│   ├── conftest.py             # Performance specific setup
│   └── test_confidence_nfr.py
└── fixtures/
    ├── __init__.py
    ├── mocks.py                # Standard mock factories
    └── fakes.py                # Complex fake implementations
```

### Step 2: Centralize Fixtures in conftest.py

**File: `tests/conftest.py`**

```python
"""Shared pytest fixtures for all tests.

Import fixtures from here rather than defining locally.
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path
import tempfile

# ============================================================
# Database Fixtures
# ============================================================

@pytest.fixture
def temp_event_db():
    """Create a temporary SQLite database for event store."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name
    Path(f.name).unlink(missing_ok=True)

@pytest.fixture
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB."""
    with tempfile.TemporaryDirectory() as d:
        yield d

# ============================================================
# Service Mocks
# ============================================================

@pytest.fixture
def mock_neo4j_service():
    """Mock Neo4j service for unit tests."""
    service = Mock()
    service.run_query = AsyncMock()
    service.session = MagicMock()
    return service

@pytest.fixture
def mock_chromadb_service():
    """Mock ChromaDB service for unit tests."""
    service = Mock()
    service.collection = Mock()
    service.collection.query = Mock(return_value={
        "ids": [[]],
        "distances": [[]],
        "metadatas": [[]]
    })
    return service

@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for unit tests."""
    service = Mock()
    service.encode = Mock(return_value=[[0.1] * 384])
    return service

@pytest.fixture
def mock_repository():
    """Mock repository for unit tests."""
    repo = Mock()
    repo.create_concept = AsyncMock()
    repo.get_concept = AsyncMock()
    repo.update_concept = AsyncMock()
    repo.delete_concept = AsyncMock()
    return repo

# ============================================================
# Confidence Service Mocks
# ============================================================

@pytest.fixture
def mock_understanding_calculator():
    """Mock understanding calculator for confidence tests."""
    calc = Mock()
    calc.calculate_understanding_score = AsyncMock(return_value=Mock(value=0.75))
    return calc

@pytest.fixture
def mock_retention_calculator():
    """Mock retention calculator for confidence tests."""
    calc = Mock()
    calc.calculate_retention_score = AsyncMock(return_value=Mock(value=0.80))
    return calc

@pytest.fixture
def mock_data_access():
    """Mock data access layer for confidence tests."""
    dal = Mock()
    dal.get_concept_relationships = AsyncMock(return_value=[])
    dal.get_concept_for_confidence = AsyncMock(return_value={
        "concept_id": "test-concept",
        "explanation": "Test explanation",
        "created_at": "2024-01-01T00:00:00Z"
    })
    return dal

@pytest.fixture
def mock_cache():
    """Mock cache for confidence tests."""
    cache = Mock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache

# ============================================================
# Sample Data Fixtures
# ============================================================

@pytest.fixture
def sample_concept_data():
    """Sample concept data for tests."""
    return {
        "name": "Test Concept",
        "explanation": "This is a test explanation with sufficient detail.",
        "area": "Testing",
        "topic": "Unit Tests",
        "subtopic": "Fixtures"
    }

@pytest.fixture
def sample_concept_id():
    """Sample concept ID."""
    return "concept-test-12345"

# ============================================================
# Async Fixtures
# ============================================================

@pytest_asyncio.fixture
async def async_mock_service():
    """Async fixture example for services needing async setup."""
    service = Mock()
    service.initialize = AsyncMock()
    await service.initialize()
    yield service
    # Cleanup if needed
```

### Step 3: Move Root-Level Test Files

Move files based on their type:

| Current Location                       | New Location                                  |
| -------------------------------------- | --------------------------------------------- |
| `tests/test_repository.py`             | `tests/unit/services/test_repository.py`      |
| `tests/test_neo4j_service.py`          | `tests/unit/services/test_neo4j_service.py`   |
| `tests/test_analytics_tools.py`        | `tests/unit/tools/test_analytics_tools.py`    |
| `tests/test_relationship_tools.py`     | `tests/unit/tools/test_relationship_tools.py` |
| `tests/test_chromadb_integration.py`   | `tests/integration/test_chromadb.py`          |
| `tests/test_repository_integration.py` | `tests/integration/test_repository.py`        |

**Script to move files:**

```bash
# Create directories
mkdir -p tests/unit/tools tests/unit/services tests/unit/confidence

# Move unit tests
mv tests/test_repository.py tests/unit/services/
mv tests/test_neo4j_service.py tests/unit/services/
mv tests/test_analytics_tools.py tests/unit/tools/
mv tests/test_relationship_tools.py tests/unit/tools/

# Move integration tests
mv tests/test_chromadb_integration.py tests/integration/test_chromadb.py
mv tests/test_repository_integration.py tests/integration/test_repository.py
```

### Step 4: Create Standard Mock Factories

**File: `tests/fixtures/mocks.py`**

```python
"""Standard mock factories for tests.

Use these instead of defining mocks inline.
"""
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Any, Dict, List, Optional

def create_mock_neo4j_result(records: List[Dict[str, Any]]) -> Mock:
    """Create a mock Neo4j query result."""
    result = Mock()
    result.data = Mock(return_value=records)
    result.single = Mock(return_value=records[0] if records else None)
    return result

def create_mock_chromadb_query_result(
    ids: List[str],
    distances: List[float],
    metadatas: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create a mock ChromaDB query result."""
    return {
        "ids": [ids],
        "distances": [distances],
        "metadatas": [metadatas],
        "documents": [[""] * len(ids)]
    }

def create_mock_concept(
    concept_id: str = "test-concept",
    name: str = "Test Concept",
    explanation: str = "Test explanation"
) -> Dict[str, Any]:
    """Create a mock concept dict."""
    return {
        "concept_id": concept_id,
        "name": name,
        "explanation": explanation,
        "area": "Testing",
        "topic": "Unit Tests",
        "confidence_score": 75.0,
        "created_at": "2024-01-01T00:00:00Z",
        "last_modified": "2024-01-01T00:00:00Z"
    }
```

### Step 5: Consolidate Fake Classes

**File: `tests/fixtures/fakes.py`**

```python
"""Fake implementations for complex test scenarios.

Use these when Mock/AsyncMock isn't sufficient for stateful behavior.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import asyncio

@dataclass
class FakeNeo4jSession:
    """Fake Neo4j session that records queries."""
    queries: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Any] = field(default_factory=list)

    def run(self, query: str, **params) -> "FakeNeo4jResult":
        self.queries.append({"query": query, "params": params})
        return FakeNeo4jResult(self.results.pop(0) if self.results else [])

@dataclass
class FakeNeo4jResult:
    """Fake Neo4j result."""
    records: List[Dict[str, Any]]

    def data(self) -> List[Dict[str, Any]]:
        return self.records

    def single(self) -> Optional[Dict[str, Any]]:
        return self.records[0] if self.records else None

@dataclass
class FakeCache:
    """Fake cache with controllable hit ratio."""
    store: Dict[str, Any] = field(default_factory=dict)
    hit_ratio: float = 0.9

    async def get(self, key: str) -> Optional[Any]:
        import random
        if random.random() < self.hit_ratio and key in self.store:
            return self.store[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        self.store[key] = value

    async def warm(self, keys: List[str], value: Any = 0.75) -> None:
        for key in keys:
            self.store[key] = value
```

### Step 6: Update Test Files to Use Centralized Fixtures

**Before (local fixture):**

```python
# tests/unit/confidence/test_composite_calculator.py

@pytest.fixture
def mock_understanding_calculator():  # DUPLICATE
    calc = Mock()
    calc.calculate_understanding_score = AsyncMock()
    return calc

async def test_composite_calculation(mock_understanding_calculator):
    ...
```

**After (use conftest fixture):**

```python
# tests/unit/confidence/test_composite_calculator.py

# No local fixture needed - use conftest.py

async def test_composite_calculation(mock_understanding_calculator):
    # Fixture comes from tests/conftest.py
    ...
```

### Step 7: Standardize Async Test Handling

Use `@pytest.mark.asyncio` consistently:

```python
import pytest

# For async test functions
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None

# For async fixtures, use pytest_asyncio
import pytest_asyncio

@pytest_asyncio.fixture
async def async_service():
    service = await create_service()
    yield service
    await service.cleanup()
```

### Step 8: Add Test Style Guide

**File: `tests/README.md`**

```markdown
# Test Guidelines

## Directory Structure

- `unit/` - Tests with mocked dependencies
- `integration/` - Tests with real databases
- `e2e/` - Full system tests
- `performance/` - NFR and benchmark tests

## Fixtures

- **Always** use fixtures from `conftest.py` when available
- Add new shared fixtures to `tests/conftest.py`
- Only create local fixtures for test-specific setup

## Mocking

- Use `Mock`/`AsyncMock` for simple cases
- Use factories from `tests/fixtures/mocks.py` for standard patterns
- Use `Fake*` classes from `tests/fixtures/fakes.py` for stateful behavior

## Async Tests

- Use `@pytest.mark.asyncio` for async test functions
- Use `@pytest_asyncio.fixture` for async fixtures

## Naming

- Files: `test_<module_name>.py`
- Functions: `test_<behavior>_<expected_result>`
- Example: `test_create_concept_returns_success_response`
```

---

## Verification

1. **Run all tests from new locations:**

   ```bash
   pytest tests/ -v
   ```

2. **Verify no duplicate fixtures:**

   ```bash
   grep -r "@pytest.fixture" tests/ | grep -v conftest.py | wc -l
   # Should be minimal (only test-specific fixtures)
   ```

3. **Check directory structure:**

   ```bash
   tree tests/ -d
   # Should match target structure
   ```

4. **Verify imports work:**
   ```python
   from tests.fixtures.mocks import create_mock_concept
   from tests.fixtures.fakes import FakeCache
   ```

---

## Success Criteria

- [ ] All test files in appropriate subdirectories
- [ ] No root-level test files (except conftest.py)
- [ ] Shared fixtures centralized in `tests/conftest.py`
- [ ] Mock factories in `tests/fixtures/mocks.py`
- [ ] Fake classes in `tests/fixtures/fakes.py`
- [ ] Consistent `@pytest.mark.asyncio` usage
- [ ] `tests/README.md` documents conventions
- [ ] All tests pass after reorganization
