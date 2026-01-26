# Codebase Standardization: Master Plan Index

## Overview

This is the master index for a 6-phase refactoring effort to eliminate confusing patterns in the MCP Knowledge Server codebase.

---

## How to Use These Plans

Each phase has a self-contained plan file that can be given to a fresh Claude context. The workflow for each phase:

1. **Give Claude the phase plan file**
2. **Claude investigates** using 3 Explore sub-agents (as specified in each plan)
3. **Claude creates detailed implementation plan** based on investigation
4. **Execute the implementation**
5. **Verify success criteria**
6. **Move to next phase**

---

## Phase Index

| Phase | Focus                       | Plan File                                                                          | Dependencies |
| ----- | --------------------------- | ---------------------------------------------------------------------------------- | ------------ |
| **1** | Terminology Standardization | [`phase-1-terminology-standardization.md`](phase-1-terminology-standardization.md) | None         |
| **2** | Configuration Consolidation | [`phase-2-configuration-consolidation.md`](phase-2-configuration-consolidation.md) | Phase 1      |
| **3** | Data Access Patterns        | [`phase-3-data-access-patterns.md`](phase-3-data-access-patterns.md)               | Phases 1-2   |
| **4** | Error Handling              | [`phase-4-error-handling.md`](phase-4-error-handling.md)                           | Phases 1-3   |
| **5** | Test Organization           | [`phase-5-test-organization.md`](phase-5-test-organization.md)                     | Phases 1-4   |
| **6** | Documentation               | [`phase-6-documentation.md`](phase-6-documentation.md)                             | Phases 1-5   |

---

## Phase Summaries

### Phase 1: Terminology Standardization

**Problem:** Confusing names for same concepts

- certainty vs confidence (+ 0-1 vs 0-100 scale)
- concept_id vs aggregate_id
- explanation vs document vs text

**Solution:** Standardize to `confidence_score` (0-100), `concept_id`, `explanation`

---

### Phase 2: Configuration Consolidation

**Problem:** 5 different configuration patterns, values hardcoded in multiple places

**Solution:** Single Pydantic BaseSettings in `config/settings.py`, dependency injection

---

### Phase 3: Data Access Patterns

**Problem:** Three overlapping data access patterns, unclear when to use which

**Solution:** Document patterns in ADRs, clarify Repository (writes) vs direct queries (reads)

---

### Phase 4: Error Handling

**Problem:** Multiple error patterns (Dict, Result union, 4 builders), inconsistent responses

**Solution:** Standardize on `ToolResponse` dataclass with `success_response()` / `error_response()`

---

### Phase 5: Test Organization

**Problem:** Mixed locations, duplicate fixtures, multiple mocking approaches

**Solution:** Clear directory structure, centralized fixtures in conftest.py, standard mocks

---

### Phase 6: Documentation

**Problem:** Decisions not documented, conventions not explicit

**Solution:** ADRs in `docs/adr/`, CLAUDE.md for AI assistants, test README

---

## Key Decisions Made

| Decision                | Choice                                  |
| ----------------------- | --------------------------------------- |
| Confidence score scale  | 0-100 (human-readable)                  |
| Configuration system    | Pydantic BaseSettings                   |
| Response pattern        | ToolResponse dataclass                  |
| Internal result pattern | Keep Result[Success, Error] in services |
| Test organization       | By type (unit/integration/e2e)          |

---

## Starting a Phase

To start any phase, tell Claude:

```
I want to work on Phase X of the codebase standardization.
Here is the plan: [paste contents of phase-X file OR reference plans/phase-X-....md]
Please begin with the investigation phase using 3 Explore agents.
```
