# Implementation Plan: 13 Core Domains for Knowledge Server

**Created:** 2026-01-27  
**Status:** Pending Review  
**Scope:** Add predefined domain areas with required `area`/`topic` fields, exposed via MCP tools

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Target State](#3-target-state)
4. [Domain Definitions](#4-domain-definitions)
5. [Implementation Steps](#5-implementation-steps)
6. [File Changes Detail](#6-file-changes-detail)
7. [Migration Strategy](#7-migration-strategy)
8. [Testing Requirements](#8-testing-requirements)
9. [Rollback Plan](#9-rollback-plan)
10. [Verification Checklist](#10-verification-checklist)
11. [Repo Alignment Addendum (Important)](#11-repo-alignment-addendum-important)
12. [Appendix A: Complete File Listing](#appendix-a-complete-file-listing)
13. [Appendix B: Frequently Asked Questions](#appendix-b-frequently-asked-questions)

---

## 1. Executive Summary

### Intent lock (must NOT change)

Implement 13 predefined knowledge areas and require `area` + `topic` for new concept creation while preserving flexibility via **soft validation** (custom areas allowed; warnings only).

### Goal

Implement 13 predefined domain areas in the Knowledge Server to provide a structured taxonomy for organizing knowledge concepts. Areas will be **required** when creating concepts, with **soft validation** that recommends predefined areas but allows custom values.

### Key Changes

- Add `config/domains.py` with 13 predefined areas (slug/label/description)
- Make `area` and `topic` **required** fields (previously optional)
- Add new MCP tool `list_areas()` to expose available domains
- Update `list_hierarchy()` to show all predefined areas (even empty ones)
- Update tool availability registry (`get_tool_availability`) to include the new tool and keep tool-count tests correct
- Maintain backward compatibility for existing data (existing concepts with NULL `area/topic` remain readable)

### Risk Level: MEDIUM

- **Breaking**: `create_concept` now requires `area` and `topic`
- Soft validation avoids rejecting custom areas
- No DB migrations required (schema unchanged)

---

## 2. Current State Analysis

### 2.1 Area Field Implementation

**Location:** `tools/concept_tools.py` (lines 47-55)

```python
# CURRENT: Area is optional
class ConceptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    explanation: str = Field(..., min_length=1)
    area: Optional[str] = Field(None, max_length=100)      # Optional
    topic: Optional[str] = Field(None, max_length=100)     # Optional
    subtopic: Optional[str] = Field(None, max_length=100)  # Optional
```

### 2.2 Area Storage

| Storage     | Location                | Format                                     |
| ----------- | ----------------------- | ------------------------------------------ |
| Event Store | SQLite `data/events.db` | JSON in `event_data` field                 |
| Neo4j       | Concept node property   | `c.area` string property (nullable today)  |
| ChromaDB    | Metadata                | `metadata["area"]` string (nullable today) |

### 2.3 Area Usage in MCP Tools

| Tool                       | Area Parameter  | Current Behavior                         |
| -------------------------- | --------------- | ---------------------------------------- |
| `create_concept`           | Optional input  | Accepts any string or NULL               |
| `update_concept`           | Optional input  | Accepts any string or NULL               |
| `search_concepts_semantic` | Optional filter | Exact match filter                       |
| `search_concepts_exact`    | Optional filter | Exact match filter                       |
| `list_hierarchy`           | Output          | Groups by area; NULL → `"Uncategorized"` |

### 2.4 Known Limitations

1. **No predefined areas** - Any string accepted
2. **No validation** - Typos create new areas
3. **Area discovery** - Only via `list_hierarchy()` after concepts exist
4. **"Uncategorized" discoverability gap** - Concepts with NULL area are grouped under `"Uncategorized"`, but there is no explicit “search for NULL area” filter in `search_concepts_exact` today

---

## 3. Target State

### 3.1 Area Field Requirements

```python
# TARGET: Area is required, topic is required
class ConceptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    explanation: str = Field(..., min_length=1)
    area: str = Field(..., max_length=100)                 # REQUIRED
    topic: str = Field(..., max_length=100)                # REQUIRED
    subtopic: Optional[str] = Field(None, max_length=100)  # Optional (unchanged)
```

### 3.2 Validation Strategy

**Soft Validation (Recommended Approach):**

- If area is in predefined list → Accept silently
- If area is NOT in predefined list → Accept with WARNING in response (`data.warnings: list[str]`)
- Never reject a valid area string (maintains flexibility)

### 3.3 New MCP Tool

```python
@mcp.tool()
async def list_areas() -> dict[str, Any]:
    """
    Get all predefined knowledge areas.

    Returns (repo standard):
        {
            "success": True,
            "message": "...",
            "data": {
                "areas": [
                    {"slug": "coding-development", "label": "Coding & Development", "description": "..."},
                    ...
                ],
                "total": 13
            }
        }
    """
```

### 3.4 Enhanced Hierarchy

`list_hierarchy()` will include all 13 predefined areas, even if they contain 0 concepts.

```json
{
  "success": true,
  "message": "...",
  "data": {
    "areas": [
      {
        "name": "coding-development",
        "label": "Coding & Development",
        "description": "Programming, APIs, frameworks, software engineering",
        "concept_count": 42,
        "topics": [...],
        "is_predefined": true
      },
      {
        "name": "philosophy",
        "label": "Philosophy",
        "description": "Ethics, logic, metaphysics, epistemology",
        "concept_count": 0,
        "topics": [],
        "is_predefined": true
      }
    ],
    "total_concepts": 42
  }
}
```

---

## 4. Domain Definitions

### 4.1 The 13 Predefined Areas

| #   | Slug                 | Label                | Description                                          |
| --- | -------------------- | -------------------- | ---------------------------------------------------- |
| 1   | `coding-development` | Coding & Development | Programming, APIs, frameworks, software engineering  |
| 2   | `ai-llms`            | AI & LLMs            | Machine learning, prompts, agents, neural networks   |
| 3   | `productivity`       | Productivity         | Time management, workflows, efficiency, tools        |
| 4   | `learning`           | Learning             | Memory, retention, mind maps, study techniques       |
| 5   | `business`           | Business             | Strategy, sales, entrepreneurship, management        |
| 6   | `health`             | Health               | Exercise, nutrition, sleep, wellness                 |
| 7   | `mindset`            | Mindset              | Psychology, personal growth, habits, motivation      |
| 8   | `marketing`          | Marketing            | Copywriting, funnels, content, branding              |
| 9   | `video-content`      | Video & Content      | Video production, editing, streaming, media          |
| 10  | `spirituality`       | Spirituality         | Spiritual practices, meditation, consciousness       |
| 11  | `philosophy`         | Philosophy           | Ethics, logic, metaphysics, epistemology             |
| 12  | `history`            | History              | Historical events, civilizations, biographies        |
| 13  | `physics`            | Physics              | Classical mechanics, quantum physics, thermodynamics |

### 4.2 Design Decisions

1. **Slugs use kebab-case** for URL/API compatibility
2. **Labels are human-readable** for UI display
3. **Descriptions are brief** for tooltip/help text
4. **Custom areas allowed** to maintain flexibility
5. **No new "Uncategorized" area** - all new concepts must specify an area (legacy NULLs remain readable)

---

## 5. Implementation Steps

> **Important prerequisite:** This repo’s pytest currently fails at import time because `tests/conftest.py` uses `pytest` before importing it. Fixing that is required to do TDD. See Step 0.

### Step 0: Preflight — Make pytest runnable (REQUIRED)

**File:** `tests/conftest.py`

**Problem:** `@pytest.fixture` is used before `import pytest`, causing `NameError`.  
**Fix:** Move `import pytest` to the top of the file before the first fixture decorator.

**Verify:**

```bash
cd "5.Knowledge Server"
./.venv/bin/python -m pytest -q tests/unit
```

**Done when:** pytest reaches test execution (no conftest import crash).

---

### Step 1: Create Domain Configuration (NEW FILE)

**File:** `config/domains.py`

```python
"""
Predefined knowledge domains for the Knowledge Server.

This module defines the 13 core areas that organize knowledge concepts.
Custom areas are allowed but these provide a recommended taxonomy.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Area:
    """Represents a knowledge area/domain."""

    slug: str           # Unique identifier (kebab-case)
    label: str          # Human-readable name
    description: str    # Brief description for UI tooltips

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "slug": self.slug,
            "label": self.label,
            "description": self.description
        }


# The 13 predefined areas
PREDEFINED_AREAS: List[Area] = [
    Area(
        slug="coding-development",
        label="Coding & Development",
        description="Programming, APIs, frameworks, software engineering"
    ),
    Area(
        slug="ai-llms",
        label="AI & LLMs",
        description="Machine learning, prompts, agents, neural networks"
    ),
    Area(
        slug="productivity",
        label="Productivity",
        description="Time management, workflows, efficiency, tools"
    ),
    Area(
        slug="learning",
        label="Learning",
        description="Memory, retention, mind maps, study techniques"
    ),
    Area(
        slug="business",
        label="Business",
        description="Strategy, sales, entrepreneurship, management"
    ),
    Area(
        slug="health",
        label="Health",
        description="Exercise, nutrition, sleep, wellness"
    ),
    Area(
        slug="mindset",
        label="Mindset",
        description="Psychology, personal growth, habits, motivation"
    ),
    Area(
        slug="marketing",
        label="Marketing",
        description="Copywriting, funnels, content, branding"
    ),
    Area(
        slug="video-content",
        label="Video & Content",
        description="Video production, editing, streaming, media"
    ),
    Area(
        slug="spirituality",
        label="Spirituality",
        description="Spiritual practices, meditation, consciousness"
    ),
    Area(
        slug="philosophy",
        label="Philosophy",
        description="Ethics, logic, metaphysics, epistemology"
    ),
    Area(
        slug="history",
        label="History",
        description="Historical events, civilizations, biographies"
    ),
    Area(
        slug="physics",
        label="Physics",
        description="Classical mechanics, quantum physics, thermodynamics"
    ),
]

# Quick lookup set for validation
AREA_SLUGS: set[str] = {area.slug for area in PREDEFINED_AREAS}

# Mapping from slug to Area object
AREAS_BY_SLUG: dict[str, Area] = {area.slug: area for area in PREDEFINED_AREAS}


def is_predefined_area(slug: str) -> bool:
    """Check if an area slug is in the predefined list."""
    return slug in AREA_SLUGS


def get_area(slug: str) -> Optional[Area]:
    """Get Area object by slug, or None if not found."""
    return AREAS_BY_SLUG.get(slug)


def get_all_areas() -> List[dict]:
    """Get all predefined areas as dictionaries."""
    return [area.to_dict() for area in PREDEFINED_AREAS]
```

---

### Step 2: Update Config Package Exports (OPTIONAL)

**File:** `config/__init__.py`

Add to imports and `__all__` (ensure no circular imports):

```python
from config.domains import (
    Area,
    PREDEFINED_AREAS,
    AREA_SLUGS,
    AREAS_BY_SLUG,
    is_predefined_area,
    get_area,
    get_all_areas,
)

__all__ = [
    # ... existing exports ...
    "Area",
    "PREDEFINED_AREAS",
    "AREA_SLUGS",
    "is_predefined_area",
    "get_area",
    "get_all_areas",
]
```

---

### Step 3: Update Pydantic Models + Soft Validation

**File:** `tools/concept_tools.py`

#### 3a. Add imports

```python
from config.domains import is_predefined_area, AREA_SLUGS
```

#### 3b. Update ConceptCreate model (area/topic required)

```python
class ConceptCreate(BaseModel):
    """Model for creating a new concept"""

    name: str = Field(..., min_length=1, max_length=200, description="Concept name")
    explanation: str = Field(..., min_length=1, description="Detailed explanation of the concept")

    area: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description=(
            "Subject area (required). Recommended predefined slugs: "
            "coding-development, ai-llms, productivity, learning, business, health, mindset, "
            "marketing, video-content, spirituality, philosophy, history, physics. "
            "Custom areas are allowed (warning only)."
        ),
    )
    topic: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Topic within area (required, e.g., 'Python', 'Memory Techniques')",
    )
    subtopic: Optional[str] = Field(None, max_length=100, description="Subtopic (optional)")

    @field_validator("area", "topic")
    @classmethod
    def string_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Value cannot be empty or whitespace")
        return v.strip()
```

#### 3c. ConceptUpdate remains optional (partial updates)

Keep `ConceptUpdate.area/topic` optional so partial updates still work.

#### 3d. Update create_concept to emit soft warnings (repo format)

**Important:** Warnings must be returned in `data.warnings` (list) via `success_response`, not as a top-level `warning`.

```python
async def create_concept(...) -> Dict[str, Any]:
    try:
        concept_data = ConceptCreate(...)

        warnings: list[str] = []
        if not is_predefined_area(concept_data.area):
            warnings.append(
                f"Area '{concept_data.area}' is not a predefined area. "
                f"Recommended areas: {', '.join(sorted(AREA_SLUGS))}. "
                "Custom areas are allowed but may affect discoverability."
            )

        success, error, concept_id = repo.create_concept(concept_dict)

        if success:
            if warnings:
                return success_response("Created", concept_id=concept_id, warnings=warnings)
            return success_response("Created", concept_id=concept_id)
```

---

### Step 4: Add `list_areas` MCP Tool

**File:** `mcp_server.py`

Add a new tool near other analytics/hierarchy tools:

```python
@mcp.tool()
async def list_areas() -> dict[str, Any]:
    """
    Get all predefined knowledge areas.

    Returns:
        {"success": True, "message": "...", "data": {"areas": [...], "total": 13}}
    """
    from config.domains import get_all_areas
    from tools.responses import success_response

    areas = get_all_areas()
    return success_response(
        f"{len(areas)} predefined areas available",
        areas=areas,
        total=len(areas),
    )
```

---

### Step 5: Update `list_hierarchy` to Include Predefined Areas

**File:** `tools/analytics_tools.py`

Add import at top:

```python
from config.domains import PREDEFINED_AREAS
```

Modify `list_hierarchy` to:

- Pre-seed `areas_dict` with all predefined areas with `concept_count = 0`
- Keep legacy mapping for NULL area → `"Uncategorized"` when present
- Keep response payload nested under `data` via `success_response(...)`

Implementation outline (must be adapted to existing function):

```python
# Initialize areas_dict with all predefined areas (ensures they appear even if empty)
areas_dict = {}
for predefined in PREDEFINED_AREAS:
    areas_dict[predefined.slug] = {
        "name": predefined.slug,
        "label": predefined.label,
        "description": predefined.description,
        "concept_count": 0,
        "topics": {},
        "is_predefined": True,
    }

# When processing DB records, create custom areas on demand
if area not in areas_dict:
    areas_dict[area] = {
        "name": area,
        "label": area,
        "description": "",
        "concept_count": 0,
        "topics": {},
        "is_predefined": False,
    }
```

Ordering recommendation:

- Predefined areas first (in the defined order)
- Custom areas alphabetically
- `"Uncategorized"` last

---

### Step 6: Update MCP Tool Signatures + Docstrings (Breaking Change)

**File:** `mcp_server.py`

Update wrapper signature for `create_concept` to require `area` and `topic`:

```python
@mcp.tool()
async def create_concept(
    name: str,
    explanation: str,
    area: str,           # CHANGED: required
    topic: str,          # CHANGED: required
    subtopic: str | None = None,
    source_urls: str | None = None,
) -> dict[str, Any]:
    """... update docstring to describe required area/topic and optional data.warnings ..."""
```

Also update docstrings that currently describe `area/topic` as optional to reflect the new contract.

---

### Step 7: Update Tool Availability Registry (REQUIRED when adding tool)

**File:** `tools/service_utils.py`

Add `list_areas` to `tool_dependencies` with no dependencies, and update tests that pin tool counts.

Evidence: tool availability registry and tests exist in:

- `tools/service_utils.py`
- `tests/test_service_decorator.py` (asserts `total_tools == 16` today)

---

### Step 8: Update Existing Test + Doc Call Sites (REQUIRED for breaking change)

Because `create_concept` now requires `area/topic`, update all call sites that omit them.

Suggested workflow:

```bash
cd "5.Knowledge Server"
rg -n "create_concept\\(" tests
rg -n "create_concept\\(" System-Overview docs README.md
```

Known examples that currently omit taxonomy fields:

- `tests/integration/test_concept_tools_integration.py` has calls like `create_concept(name="...", explanation="...")`
- `tests/test_mcp_integration.py` has calls like `create_concept(name="...", explanation="...", area="Programming")` (missing topic)

---

## 6. File Changes Detail

### Summary Table

| File                       | Change Type   | Risk                         |
| -------------------------- | ------------- | ---------------------------- |
| `config/domains.py`        | CREATE        | None (new file)              |
| `config/__init__.py`       | MODIFY        | Low                          |
| `tools/concept_tools.py`   | MODIFY        | Medium                       |
| `tools/analytics_tools.py` | MODIFY        | Low                          |
| `mcp_server.py`            | MODIFY        | Medium (breaking signature)  |
| `tools/service_utils.py`   | MODIFY        | Low                          |
| `tests/**`                 | MODIFY/CREATE | Medium (breaking call sites) |

---

## 7. Migration Strategy

### 7.1 Existing Data Compatibility

**No migration required.** Existing concepts with NULL `area/topic` remain readable:

- `get_concept()` returns stored values (NULL remains NULL)
- `list_hierarchy()` maps NULL area to `"Uncategorized"`
- Searches without an `area` filter can still return concepts regardless of area value

**Clarification:** `search_concepts_exact(area=...)` cannot be used to explicitly query `area IS NULL` in the current implementation; this plan does not add that feature.

### 7.2 Optional Migration Script (Out of Scope)

If you want to migrate existing concepts to predefined areas, create `scripts/migrate_areas.py` (optional):

```python
"""
Optional migration script to update existing concepts with predefined areas.

This script:
1. Lists all concepts with NULL or non-standard areas
2. Suggests predefined area mappings
3. Updates concepts (with user confirmation)
"""
```

### 7.3 Backward Compatibility Matrix

| Scenario                        | Before   | After                 | Compatible? |
| ------------------------------- | -------- | --------------------- | ----------- |
| Create without `area/topic`     | Accepted | Rejected (required)   | ⚠️ Breaking |
| Create with custom `area`       | Accepted | Accepted with warning | ✅ Yes      |
| Create with predefined `area`   | Accepted | Accepted (no warning) | ✅ Yes      |
| Read existing NULL `area/topic` | Works    | Works                 | ✅ Yes      |

**Breaking Changes:**

1. `create_concept` now requires `area` and `topic`
2. Clients must update all call sites and docs that omit these fields

---

## 8. Testing Requirements

> IMPORTANT: Tool functions return structured response dicts; tests must assert on those responses (no `pytest.raises(...)` for tool-level validation).

### 8.1 Unit Tests (Domains)

Create `tests/unit/test_domains.py`:

```python
"""Unit tests for domain configuration."""

import pytest
from config.domains import (
    PREDEFINED_AREAS,
    AREA_SLUGS,
    is_predefined_area,
    get_area,
    get_all_areas,
)


class TestDomainConfiguration:
    """Test domain configuration."""

    def test_predefined_areas_count(self):
        """Should have exactly 13 predefined areas."""
        assert len(PREDEFINED_AREAS) == 13

    def test_all_areas_have_required_fields(self):
        """All areas should have slug, label, and description."""
        for area in PREDEFINED_AREAS:
            assert area.slug, f"Area missing slug: {area}"
            assert area.label, f"Area missing label: {area}"
            assert area.description, f"Area missing description: {area}"

    def test_slugs_are_kebab_case(self):
        """All slugs should be kebab-case."""
        import re

        pattern = re.compile(r"^[a-z]+(-[a-z]+)*$")
        for area in PREDEFINED_AREAS:
            assert pattern.match(area.slug), f"Invalid slug format: {area.slug}"

    def test_is_predefined_area(self):
        """Should correctly identify predefined areas."""
        assert is_predefined_area("coding-development") is True
        assert is_predefined_area("ai-llms") is True
        assert is_predefined_area("custom-area") is False
        assert is_predefined_area("") is False

    def test_get_area(self):
        """Should return Area object for valid slugs."""
        area = get_area("philosophy")
        assert area is not None
        assert area.slug == "philosophy"
        assert area.label == "Philosophy"
        assert get_area("invalid") is None

    def test_get_all_areas(self):
        """Should return all areas as dictionaries."""
        areas = get_all_areas()
        assert len(areas) == 13
        assert all(isinstance(a, dict) for a in areas)
        assert all("slug" in a and "label" in a and "description" in a for a in areas)
```

### 8.2 Integration Tests (Concept creation contract)

Update/add tests in `tests/integration/test_concept_tools_integration.py`:

```python
import pytest
from tools import concept_tools
from tools.responses import ErrorType


class TestCreateConceptWithRequiredTaxonomy:
    """Test concept creation with required area/topic + soft warnings."""

    @pytest.mark.asyncio
    async def test_create_concept_requires_area(self, repository):
        result = await concept_tools.create_concept(
            name="Test Concept",
            explanation="Test explanation",
            # area missing
            topic="Test Topic",
        )
        assert result["success"] is False
        assert result["error"]["type"] == ErrorType.VALIDATION_ERROR.value

    @pytest.mark.asyncio
    async def test_create_concept_requires_topic(self, repository):
        result = await concept_tools.create_concept(
            name="Test Concept",
            explanation="Test explanation",
            area="coding-development",
            # topic missing
        )
        assert result["success"] is False
        assert result["error"]["type"] == ErrorType.VALIDATION_ERROR.value

    @pytest.mark.asyncio
    async def test_create_concept_with_predefined_area_has_no_warnings(self, repository):
        result = await concept_tools.create_concept(
            name="Test Concept",
            explanation="Test explanation",
            area="coding-development",
            topic="Python",
        )
        assert result["success"] is True
        assert "warnings" not in (result.get("data") or {})

    @pytest.mark.asyncio
    async def test_create_concept_with_custom_area_has_warning(self, repository):
        result = await concept_tools.create_concept(
            name="Test Concept",
            explanation="Test explanation",
            area="my-custom-area",
            topic="Custom Topic",
        )
        assert result["success"] is True
        assert "warnings" in result["data"]
        assert any("not a predefined area" in w for w in result["data"]["warnings"])
```

### 8.3 MCP Tool Tests (`list_areas`)

Create a new test file `tests/test_list_areas_tool.py`:

```python
import pytest


class TestListAreasTool:
    @pytest.mark.asyncio
    async def test_list_areas_returns_all_predefined(self):
        import mcp_server

        list_areas_fn = mcp_server.list_areas.fn if hasattr(mcp_server.list_areas, "fn") else mcp_server.list_areas
        result = await list_areas_fn()

        assert result["success"] is True
        assert result["data"]["total"] == 13
        assert len(result["data"]["areas"]) == 13

    @pytest.mark.asyncio
    async def test_list_areas_structure(self):
        import mcp_server

        list_areas_fn = mcp_server.list_areas.fn if hasattr(mcp_server.list_areas, "fn") else mcp_server.list_areas
        result = await list_areas_fn()
        for area in result["data"]["areas"]:
            assert "slug" in area
            assert "label" in area
            assert "description" in area
```

### 8.4 Tool availability tests (count + inclusion)

Update `tests/test_service_decorator.py`:

- Update `total_tools == 16` → `total_tools == 17`
- Ensure `list_areas` appears in available/unavailable lists and is counted in total.

---

## 9. Rollback Plan

### 9.1 If Issues Occur

1. **Revert code changes:**

   ```bash
   git revert HEAD  # If committed
   # Or restore from backup
   ```

2. **No database changes needed** - Schema unchanged

3. **Clear caches:**
   - Restart server to clear in-memory caches (hierarchy cache is in-process)

### 9.2 Gradual Rollout Option

If concerned about breaking changes, implement in phases:

**Phase 1:** Add `list_areas()` tool and domain config (non-breaking)  
**Phase 2:** Add soft validation warnings (non-breaking)  
**Phase 3:** Make area/topic required (breaking - communicate to users first)

---

## 10. Verification Checklist

### Pre-Implementation

- [ ] Review this plan with stakeholders
- [ ] Ensure test environment is ready
- [ ] Fix pytest preflight issue in `tests/conftest.py` (Step 0)

### Post-Implementation

- [ ] All unit tests pass
- [ ] `list_areas()` returns 13 areas (`result["data"]["total"] == 13`)
- [ ] `list_hierarchy()` shows all 13 predefined areas (even when empty)
- [ ] `create_concept` requires `area` and `topic`
- [ ] `create_concept` with predefined area shows no warnings
- [ ] `create_concept` with custom area returns `data.warnings`
- [ ] Existing concepts (with NULL area) still accessible via read operations and appear under `"Uncategorized"` in hierarchy
- [ ] Tool availability registry includes `list_areas` and tool count tests updated (16 → 17)

### Manual Testing (repo-verified)

Option A: MCP Inspector (interactive)

```bash
cd "5.Knowledge Server"
./.venv/bin/mcp dev mcp_server.py
```

Then call tools in the inspector UI:

- `list_areas`
- `create_concept` (predefined area, custom area)
- `list_hierarchy`

Option B: Test-driven verification (recommended)

```bash
cd "5.Knowledge Server"
./.venv/bin/python -m pytest -q tests/unit/test_domains.py
./.venv/bin/python -m pytest -q tests/test_list_areas_tool.py
./.venv/bin/python -m pytest -q tests/test_service_decorator.py
./.venv/bin/python -m pytest -q tests/test_analytics_tools.py
```

---

## 11. Repo Alignment Addendum (Important)

This section documents the improvements made to keep this plan executable **against the current repo** (not theoretical).

1. **Pytest preflight is mandatory**
   - `tests/conftest.py` currently fails due to `pytest` import ordering.
   - This must be fixed before any TDD steps.

2. **Response format is standardized**
   - Success responses must use `success_response(...)` → payload under `data`.
   - Warnings must be returned as `data.warnings` (list), not top-level keys.

3. **Manual CLI commands must be real**
   - The Python `mcp` CLI does not support `mcp call ...`; use `mcp dev` (Inspector) or tests.

4. **Tool availability must be updated**
   - `get_tool_availability` uses a static registry with pinned counts in tests.
   - Adding a new tool requires updating `tools/service_utils.py` and `tests/test_service_decorator.py`.

5. **Test file paths must match the repo**
   - Use `tests/integration/test_concept_tools_integration.py` (exists) rather than non-existent files.

---

## Appendix A: Complete File Listing

Files to create/modify:

```
5.Knowledge Server/
├── config/
│   ├── __init__.py                # MODIFY (optional): export domains
│   ├── domains.py                 # CREATE: domain definitions
│   └── settings.py                # NO CHANGE
├── tools/
│   ├── concept_tools.py           # MODIFY: required area/topic, soft warnings
│   ├── analytics_tools.py         # MODIFY: include predefined empty areas
│   ├── search_tools.py            # NO CHANGE
│   ├── responses.py               # NO CHANGE
│   └── service_utils.py           # MODIFY: include list_areas in tool registry
├── mcp_server.py                  # MODIFY: add list_areas tool, update create_concept signature/docs
└── tests/
    ├── conftest.py                # MODIFY: import order fix (pytest)
    ├── unit/
    │   └── test_domains.py        # CREATE: domains tests
    ├── integration/
    │   └── test_concept_tools_integration.py  # MODIFY: taxonomy requirements tests + call sites
    ├── test_list_areas_tool.py    # CREATE: list_areas tests
    └── test_service_decorator.py  # MODIFY: tool count + list_areas inclusion
```

---

## Appendix B: Frequently Asked Questions

**Q: Can users still create concepts with custom areas?**  
A: Yes. Custom areas are allowed but will add a warning in `data.warnings` recommending predefined areas.

**Q: What happens to existing concepts with NULL area?**  
A: They remain unchanged and readable. They appear under `"Uncategorized"` in the hierarchy.

**Q: Is this a breaking change?**  
A: Yes. The `create_concept` API now requires `area` and `topic` parameters.

**Q: How do I add more predefined areas in the future?**  
A: Edit `config/domains.py` and add a new `Area` object to `PREDEFINED_AREAS`.

**Q: Should topics also be predefined?**  
A: Not in this implementation. Topics remain free-form strings within each area. A future enhancement could add predefined topics per area.

---

_End of Implementation Plan_
