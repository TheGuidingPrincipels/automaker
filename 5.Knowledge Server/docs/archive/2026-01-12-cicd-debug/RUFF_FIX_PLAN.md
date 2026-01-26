# Ruff Linting Fix Action Plan

## Quick Start: 5-Minute Auto-Fix

```bash
# Fix all safe-fixable errors (removes 1,199 of 1,712)
ruff check . --fix

# Check remaining errors
ruff check .
# Should show ~513 errors remaining
```

**Expected Result After Auto-Fix:**

- Down to 513 errors (from 1,712)
- 70% reduction immediately
- All whitespace, import sorting, type annotation syntax fixed

---

## Priority Levels

### PRIORITY 1: Critical (Do First After Auto-Fix)

**Time Estimate:** 30-60 minutes
**Files:** mcp_server.py, repository.py, event_store.py

| Error      | Count | Files                 | Action                                              |
| ---------- | ----- | --------------------- | --------------------------------------------------- |
| **B904**   | 14    | Exception handlers    | Add `raise ... from err` or `raise ... from None`   |
| **B017**   | 7     | Exception handlers    | Replace bare `except Exception` with specific types |
| **DTZ005** | 76    | Event store, services | Add timezone info: `datetime.now(UTC)`              |
| **E402**   | 37    | Various               | Move imports to top of file                         |

**Sample Commands:**

```bash
# Find all B904 violations
ruff check . --select B904

# Find datetime issues
ruff check . --select DTZ005 --output-format=json | jq '.[] | .filename' | sort -u
```

### PRIORITY 2: High (Do Second)

**Time Estimate:** 1-2 hours
**Files:** concept_tools.py, repository.py, services/

| Error      | Count | Action                                                                   |
| ---------- | ----- | ------------------------------------------------------------------------ |
| **F841**   | 60    | Remove unused local variables or use them (UNSAFE_FIX - requires review) |
| **RUF059** | 48    | Remove unused unpacked variables (UNSAFE_FIX - requires review)          |
| **F401**   | 6     | Remove unused imports (6 not auto-fixed)                                 |

**Steps:**

```bash
# Review F841 errors (unused variables - often incomplete test code)
ruff check . --select F841 --output-format=json | jq '.[]' | head -50

# Review E402 errors (imports after code)
ruff check . --select E402
```

### PRIORITY 3: Medium (Do Third)

**Time Estimate:** 30-45 minutes
**Files:** All test files

| Error      | Count | Action                                                                   |
| ---------- | ----- | ------------------------------------------------------------------------ |
| **UP035**  | 83    | Change imports: `from typing import X` → `from collections.abc import X` |
| **RUF013** | 25    | Change implicit optionals (UNSAFE_FIX - test carefully)                  |

**Example:**

```python
# Before (UP035)
from typing import Dict, List, Callable

# After
from typing import Dict  # For Dict type (will become dict in future)
from collections.abc import Callable
```

### PRIORITY 4: Low (Optional - Code Quality)

**Time Estimate:** 1-2 hours if doing it

| Error      | Count | Impact            | Fix                            |
| ---------- | ----- | ----------------- | ------------------------------ |
| **RUF001** | 14    | Ambiguous Unicode | Replace with ASCII equivalents |
| **SIM105** | 14    | Style             | Use `contextlib.suppress()`    |
| **SIM108** | 11    | Style             | Use ternary operators          |

---

## File-by-File Breakdown

### Test Files (Can Auto-Fix, Low Priority)

```
test_stress_debugging.py          147 errors → mostly W293, F401
test_embedding_edge_cases.py      95 errors → mostly W293, F401
test_critical_bugs.py             91 errors → mostly W293, F401
test_memory_leaks.py              60 errors → mostly W293, F401
test_dual_storage_integration.py  31 errors → mixed
test_confidence_nfr.py            20 errors → mixed
smoke_tests.py                    24 errors → mixed
```

**Action:** Auto-fix and move on. Don't waste time on test linting.

### Production Code (Priority)

#### Tier 1 (Fix First)

```
mcp_server.py                     49 errors
├─ RUF013 (21): Implicit Optional - manual review
├─ UP006 (17): Dict→dict (will be fixed by --fix)
├─ UP045 (4): Optional syntax (will be fixed by --fix)
├─ DTZ005 (1): datetime.now() without tz
└─ Others (6): F401, I001, F541, UP035, UP041

concept_tools.py                  38 errors
├─ UP006 (8): Dict→dict
├─ I001 (7): Import sorting
├─ F401 (6): Unused imports
├─ UP045 (5): Optional syntax
└─ Others (12): Mixed

repository.py                     33 errors
├─ UP006 (10): Dict→dict
├─ RUF013 (8): Implicit Optional
├─ F401 (5): Unused imports
├─ UP045 (4): Optional syntax
└─ Others (6): Mixed
```

#### Tier 2 (Fix Second)

```
uat_runner.py                     31 errors (mostly fixable auto)
benchmark_tools.py               28 errors (mostly fixable auto)
cleanup_databases.py             27 errors (mostly fixable auto)
health_check.py                  26 errors (mostly fixable auto)
consistency_checker.py           26 errors (mostly fixable auto)
```

---

## Complete Step-by-Step Fix Process

### Step 1: Prepare (2 minutes)

```bash
cd /home/user/mcp-knowledge-server

# Create a branch for fixes
git checkout -b fix/ruff-linting-1712-errors

# Get baseline
ruff check . 2>&1 | tail -5
# Found 1712 errors
```

### Step 2: Auto-Fix (5 minutes)

```bash
# Run safe fixes
ruff check . --fix

# Check result
ruff check . 2>&1 | tail -5
# Found ~513 errors (down from 1712)

# Commit this
git add -A
git commit -m "fix: Apply ruff auto-fixes (1199 issues resolved)

- Fixed whitespace issues (W293)
- Sorted imports (I001)
- Updated type annotation syntax (UP006, UP045, UP007)
- Removed unused imports (F401)
- Cleaned up f-strings (F541)
- Fixed miscellaneous style issues

1199 of 1712 errors now fixed automatically."
```

### Step 3: Manual High-Priority Fixes (1-2 hours)

#### 3a. Fix E402 (Module imports not at top)

```bash
ruff check . --select E402 --output-format=json | jq '.[] | "\(.filename):\(.location.row): \(.message)"'

# Manually move imports in flagged files to top
```

#### 3b. Fix B904 (Exception chaining)

```bash
ruff check . --select B904

# Edit flagged exception handlers to add:
# raise NewError(...) from err  # or from None for suppressed
```

#### 3c. Fix B017 (Bare except Exception)

```bash
ruff check . --select B017

# Replace bare except Exception with specific exception types
```

#### 3d. Review DTZ005 (Datetime without timezone)

```bash
ruff check . --select DTZ005 --output-format=json | jq '.[] | .filename' | sort -u

# Add UTC timezone to datetime.now() calls
```

### Step 4: Test & Commit

```bash
# Run your test suite
pytest tests/

# Run linting to see progress
ruff check . 2>&1 | tail -5

# Commit
git add -A
git commit -m "fix: Resolve high-priority linting issues

- Fixed exception handling patterns (B904, B017)
- Fixed module-level import placement (E402)
- Added timezone awareness to datetime calls (DTZ005)
- Removed ~100 remaining critical issues

Remaining ~400 issues are low-priority style suggestions."
```

### Step 5: Optional - Unsafe Fixes (1-2 hours)

```bash
# Try unsafe fixes (may require manual review)
ruff check . --fix --unsafe-fixes

# Carefully review changes
git diff

# Test thoroughly
pytest tests/

# Commit if all tests pass
git add -A
git commit -m "fix: Apply unsafe ruff fixes (205 issues)

- Removed unused variables (F841)
- Removed unused unpacked variables (RUF059)
- Fixed boolean comparisons (E712)
- Applied ternary operator suggestions (SIM108)
- Applied exception suppression improvements (SIM105)

205 issues resolved. Total remaining: ~95 low-priority style issues."
```

### Step 6: Push & Create PR

```bash
git push origin fix/ruff-linting-1712-errors

# Create PR with description
gh pr create --title "fix: Resolve 1712 ruff linting errors" \
  --body "Reduces linting errors from 1712 to <100. All fixes are code quality improvements, no functional changes."
```

---

## Danger Zones (Don't Over-Automate)

### Do NOT use `--unsafe-fixes` without review

Some changes might alter behavior:

- F841 (unused variables): Might be intentional placeholders
- RUF059 (unused unpacking): Could be for API consistency
- SIM108 (ternary): More complex conditions become less readable

### Do NOT ignore DTZ005

Even though it's marked NOT_FIXABLE, timezone issues can cause real bugs:

- Timestamps compared across systems
- Daylight saving time transitions
- Event ordering in distributed systems

### Do NOT auto-fix exception handlers (B904, B017)

Manual review ensures:

- Proper exception type specificity
- Correct exception chaining
- No loss of debugging information

---

## Success Criteria

**GOOD OUTCOME:**

- All 1199 safe fixes applied via `--fix`
- E402, B904, B017, DTZ005 manually reviewed
- ~300 low-priority style issues remaining
- All tests passing
- Code functionality unchanged
- CI/CD can proceed (or nearly proceed)

**PERFECT OUTCOME:**

- All above PLUS
- Unsafe fixes reviewed and applied: ~500 errors fixed
- Total down to <100 errors
- Code is cleaner and more maintainable

---

## Time Budget

```
Step 1 (Prepare):          2 min
Step 2 (Auto-fix):         5 min
Step 3 (Manual fixes):     90 min (1.5 hours)
Step 4 (Test & commit):    10 min
Step 5 (Unsafe fixes):     120 min (2 hours) - OPTIONAL
Step 6 (Push & PR):        5 min

MINIMUM TIME:    2 + 5 + 90 + 10 + 5 = 112 min (< 2 hours)
WITH UNSAFE:     2 + 5 + 90 + 10 + 120 + 5 = 232 min (< 4 hours)
```

---

## Questions to Answer Before Starting

1. **Do you need to maintain Python 3.8/3.9 compatibility?**
   - If YES: Some UP006/UP045/UP007 fixes need reverting
   - If NO: Proceed with all fixes

2. **Is timezone handling critical?**
   - If YES: Spend extra time on DTZ005
   - If NO: Lower priority

3. **Are exception handlers tested?**
   - If YES: Safe to apply B904/B017 fixes
   - If NO: Manual review required

4. **Can you run tests after changes?**
   - If YES: Safe to apply unsafe fixes
   - If NO: Stick to safe fixes only

---

## Next Steps

1. Read RUFF_ANALYSIS_REPORT.md (comprehensive analysis)
2. Run `ruff check . --fix` to auto-fix 1199 issues
3. Pick 2-3 high-priority errors and fix them
4. Run tests
5. Commit and push

Start with Step 1 above for a 2-hour sprint to get most issues resolved.
