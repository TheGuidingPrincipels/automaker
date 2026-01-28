

## Your Mission

You are tasked with investigating and fixing pre-existing test failures in the Knowledge Server. Your goal is **NOT to simply make tests pass** - it is to **identify the TRUE root cause** of why tests are failing and fix the underlying issues properly.

> **CRITICAL**: A test that passes but masks an underlying bug is worse than a failing test. We need to understand the real problem before fixing anything.

---

## Phase 1: Read the Failure Catalog

**First, read the pre-existing test failures document:**

```
/5.Knowledge Server/docs/pre-existing-test-failures.md
```

This document contains:
- All 136 pre-existing test failures organized by category
- Initial hypotheses about root causes
- Priority recommendations
- Commands to run each test group

**Review the document to understand:**
1. Which categories have been marked as FIXED (if any)
2. Which category you should focus on next
3. The initial hypothesis for the failure cause

---

## Phase 2: Select ONE Category to Investigate

Work on **one category at a time**. Do not attempt to fix multiple categories in a single session.

**Selection criteria:**
1. Choose the highest priority unfixed category
2. Or ask the user which category they want to focus on
3. Categories marked `[FIXED]` in the document should be skipped

**Confirm with the user before proceeding:**
> "I've reviewed the test failures document. I'll focus on **[Category Name]** which has **[X] failing tests**. The initial hypothesis is [brief description]. Should I proceed with the deep investigation?"

---

## Phase 3: Deep Investigation with 5 Sub-Agents

Launch **5 parallel Opus 4.5 deepdive agents** to investigate the failing tests from multiple angles. Each agent has a specific focus area.

### Agent 1: Code Path Analysis
```
Investigate the actual code paths being tested:
- Read the failing test files
- Trace the code from test → tool → service → repository
- Identify what the tests EXPECT vs what the code ACTUALLY does
- Document the complete call chain for each failing test
- Look for recent changes that might have broken the contract
```

### Agent 2: Dependency & Import Analysis
```
Investigate dependency and import issues:
- Check if required modules are installed (requirements.txt, pyproject.toml)
- Trace import statements to find missing or circular dependencies
- Check if there are version mismatches between expected and installed packages
- Identify optional vs required dependencies
- Look for conditional imports that might be failing silently
```

### Agent 3: Mock & Fixture Analysis
```
Investigate test infrastructure issues:
- Analyze the test fixtures being used (conftest.py)
- Check if mocks are correctly targeting the right objects
- Verify mock paths match actual import paths
- Compare working tests vs failing tests for pattern differences
- Identify if service container patterns changed but tests weren't updated
```

### Agent 4: API Contract Analysis
```
Investigate API contract mismatches:
- Compare function signatures in tests vs actual implementation
- Check for required parameters that tests don't provide
- Look for return type changes that tests don't expect
- Identify breaking changes in function signatures
- Check docstrings vs actual behavior
```

### Agent 5: Historical Context Analysis
```
Investigate the history and context:
- Use git log to find when tests started failing (if possible)
- Look for related commits that might have introduced the issue
- Check if there are TODO comments or known issues documented
- Search for related issues or discussions in the codebase
- Identify if this is a regression or tests that never worked
```

### Launch Command Pattern

```python
# Launch all 5 agents in parallel
Task(subagent_type="deepdive", prompt="Agent 1 prompt...", description="Code Path Analysis")
Task(subagent_type="deepdive", prompt="Agent 2 prompt...", description="Dependency Analysis")
Task(subagent_type="deepdive", prompt="Agent 3 prompt...", description="Mock/Fixture Analysis")
Task(subagent_type="deepdive", prompt="Agent 4 prompt...", description="API Contract Analysis")
Task(subagent_type="deepdive", prompt="Agent 5 prompt...", description="Historical Context")
```

---

## Phase 4: Synthesize Findings & Identify TRUE Root Cause

After all 5 agents complete, synthesize their findings:

### Root Cause Classification

Classify the root cause into one of these categories:

| Type | Description | Example |
|------|-------------|---------|
| **Missing Dependency** | A required package is not installed | `mistralai` module not in pyproject.toml |
| **API Contract Break** | Function signature changed but tests weren't updated | `area` parameter became required |
| **Mock Path Mismatch** | Tests mock the wrong path due to refactoring | Mocking `module.service` but service moved to container |
| **Test Infrastructure** | Fixtures or setup don't initialize required services | Missing `configured_container` fixture |
| **Actual Bug** | The code has a bug that the test correctly catches | Off-by-one error, null handling issue |
| **Test Bug** | The test itself is incorrect | Wrong assertion, testing impossible state |
| **Environment Issue** | Tests require external services not available | Needs running Neo4j/Redis |

### Present Findings to User

Present a structured report:

```markdown
## Investigation Report: [Category Name]

### Summary
- **Tests Analyzed:** X
- **Root Cause Type:** [From classification above]
- **Confidence Level:** HIGH/MEDIUM/LOW

### TRUE Root Cause
[Detailed explanation of the actual underlying issue - not just symptoms]

### Evidence
1. [Specific code/test that proves this]
2. [Git history or documentation]
3. [Comparison with working code]

### Why Tests Are Failing (Mechanism)
[Step-by-step explanation of how the root cause leads to test failure]

### Recommended Fix Approach
- Option A: [Description, pros, cons]
- Option B: [Description, pros, cons]
- Recommended: [Which option and why]

### Risk Assessment
- Risk of fix introducing new bugs: LOW/MEDIUM/HIGH
- Files that will be modified: [list]
- Tests that should be re-run after fix: [list]

### Questions for User (if any)
1. [Any decisions that need user input]
```

---

## Phase 5: Get User Approval

**Wait for explicit user approval before proceeding to fix.**

Ask:
> "Based on the investigation, the TRUE root cause is [X]. I recommend [approach]. Should I proceed to create a detailed fix plan?"

---

## Phase 6: Create Fix Plan (Plan Mode)

After user approval, enter plan mode and create a detailed implementation plan.

**The plan should include:**

1. **Files to Modify** - Exact file paths
2. **Changes per File** - Specific code changes
3. **Order of Operations** - Which changes must happen first
4. **Verification Steps** - How to verify each change worked
5. **Rollback Strategy** - How to undo if something breaks

**Plan Template:**

```markdown
## Fix Plan: [Category Name]

### Root Cause (Confirmed)
[Brief statement of the root cause]

### Step 1: [Action]
**File:** `/path/to/file.py`
**Change:** [Description]
**Verification:** `pytest tests/specific_test.py -v`

### Step 2: [Action]
...

### Final Verification
```bash
# Run all tests in this category
uv run pytest tests/[category_tests].py -v
```

### Success Criteria
- [ ] All X tests in category pass
- [ ] No regressions in related tests
- [ ] Root cause is addressed (not just symptoms)
```

---

## Phase 7: Implement Fixes

After plan approval:

1. Implement changes in the order specified
2. Run verification after each step
3. If a step fails, stop and investigate before continuing

---

## Phase 8: Update the Failure Catalog

**After successfully fixing a category, update `pre-existing-test-failures.md`:**

1. Mark the category as `[FIXED]`
2. Add a summary of what was fixed
3. Add the date fixed
4. Note any learnings for similar issues

**Example update:**

```markdown
## Issue 3: Null Confidence Score Tests - Outdated Mock Paths [FIXED]

**Status:** FIXED (2026-01-28)
**Root Cause:** Tests were mocking `tools.analytics_tools.neo4j_service` but services
moved to container pattern. Mock paths needed to use `configured_container` fixture.
**Fix Applied:** Updated all 12 tests to use `configured_container` fixture.
**Verification:** All 12 tests now pass.
```

---

## Important Reminders

### DO NOT:
- Make tests pass by weakening assertions
- Skip tests instead of fixing them (unless truly environment-dependent)
- Fix symptoms without understanding root cause
- Assume the initial hypothesis is correct without verification
- Modify multiple categories in one session

### DO:
- Verify root cause with evidence before fixing
- Ask clarifying questions if something is unclear
- Document findings even if you can't fix them
- Update the failure catalog as you progress
- Run full test suite after fixes to check for regressions

---

## Quick Reference: Commands

```bash
# Navigate to Knowledge Server
cd "/Users/ruben/Documents/GitHub/automaker/.worktrees/feature-2/5.Knowledge Server"

# Run all tests (see overall status)
uv run pytest tests/ -v --tb=short

# Run specific category
uv run pytest tests/[specific_test_file].py -v

# Run with detailed output
uv run pytest tests/[file].py -v --tb=long

# Check a single test
uv run pytest tests/[file].py::[TestClass]::[test_method] -v

# Check for import issues
uv run python -c "from [module] import [thing]"
```

---

## Session Handoff

If you cannot complete a category in one session, document:

1. What was investigated
2. What was found
3. What remains to be done
4. Any blockers or questions

Add this to the `pre-existing-test-failures.md` under the relevant category as "Investigation Notes".

---

## Start Here

1. Read `/5.Knowledge Server/docs/pre-existing-test-failures.md`
2. Identify the next unfixed category
3. Confirm with user which category to focus on
4. Launch 5 deepdive agents
5. Present findings and get approval
6. Create plan and implement fixes
7. Update the failure catalog

**Good luck! Remember: Find the TRUE root cause, not just a way to make tests green.**
