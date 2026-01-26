# Ruff Linting Errors Explained with Examples

A visual guide to understanding each error type and why it matters (or doesn't).

---

## ERRORS THAT DON'T AFFECT FUNCTIONALITY (1,170 errors = 68%)

### W293: Blank Line Contains Whitespace (363 errors)

**Impact: NONE** - Visual only

```python
# ERROR: Blank line has spaces/tabs
def foo():
    x = 1

    return x
    ↑ This line has whitespace but appears blank


# CORRECT: Truly blank
def foo():
    x = 1

    return x
```

**Why it matters:** Code formatters expect truly empty lines. Not a bug, just cleanliness.

---

### I001: Imports Not Sorted (163 errors)

**Impact: NONE** - Organization only

```python
# ERROR: Unsorted
from pathlib import Path
import os
from typing import Dict

# CORRECT: Standard library first, then third-party, then local
import os
from pathlib import Path

from typing import Dict
```

**Why it matters:** PEP 8 standard, helps code reviewers find imports. Not a bug.

---

### UP006: Use `dict` Instead of `Dict` (203 errors)

**Impact: NONE** - Just older syntax

```python
# ERROR: Old Python 3.8-3.9 syntax
from typing import Dict

def process(data: Dict[str, int]) -> None:
    pass

# CORRECT: Python 3.10+ syntax
def process(data: dict[str, int]) -> None:
    pass
```

**Why it matters:** Modern Python uses lowercase `dict` for type hints. Both work, just style.

---

### UP045: Use `X | None` Instead of `Optional[X]` (123 errors)

**Impact: NONE** - Just older syntax

```python
# ERROR: Old style
from typing import Optional

def maybe_find(key: str) -> Optional[str]:
    return ...

# CORRECT: Modern style
def maybe_find(key: str) -> str | None:
    return ...
```

**Why it matters:** PEP 604 (Python 3.10+) introduces this syntax. Both work identically.

---

### F541: F-String Without Placeholders (84 errors)

**Impact: MINIMAL** - Just inefficiency

```python
# ERROR: f-string not needed
message = f"Processing started"  # Extra computation for no reason

# CORRECT: Regular string
message = "Processing started"

# This WOULD need f-string:
name = "Alice"
message = f"Hello {name}"  # OK because it has a placeholder
```

**Why it matters:** Unnecessary `f` prefix wastes CPU cycles, confuses readers.

---

### UP007: Use `X | Y` Instead of `Union[X, Y]` (18 errors)

**Impact: NONE** - Just older syntax

```python
# ERROR: Old style
from typing import Union

def process(value: Union[str, int]) -> None:
    pass

# CORRECT: Modern style
def process(value: str | int) -> None:
    pass
```

**Why it matters:** Cleaner syntax in Python 3.10+. Same behavior.

---

## ERRORS THAT ARE USUALLY FINE (200 errors = 12%)

### F401: Unused Import (200 errors)

**Impact: MINOR** - Dead code

```python
# ERROR: Import never used
import os  # Added but never used
from typing import Dict  # Added but never used
import numpy  # Dead import

def process(data: dict) -> None:
    return data.keys()

# CORRECT: Only import what you use
def process(data: dict) -> None:
    return data.keys()
```

**Why it matters:**

- Confuses readers (why is this imported?)
- Slows down module load time slightly
- Creates security risk if imports change unexpectedly

**But:**

- Code STILL WORKS fine with unused imports
- Some imports are intentionally left for external API access

---

### F841: Local Variable Assigned But Never Used (60 errors)

**Impact: LOW** - Usually incomplete code

```python
# ERROR: Variable assigned but never read
def analyze_data(records):
    total = sum(r.amount for r in records)  # Assigned
    count = len(records)                     # Assigned

    return count  # Only count returned, total never used
    # ^ What was total for?

# CORRECT: Either use it or don't calculate it
def analyze_data(records):
    count = len(records)
    return count
```

**Why it matters:**

- Indicates incomplete refactoring
- Dead code that might confuse maintainers
- In tests: Often OK (test fixtures assign but don't use)

**Safety:** Code works fine, just potentially confusing.

---

### RUF059: Unpacked Variable Never Used (48 errors)

**Impact: LOW** - Usually test placeholders

```python
# ERROR: Unpacking but not using everything
def process_tuple():
    success, error, data = get_result()  # Unpacked all three

    return success  # Only use success, ignore error and data
    # ^ Why unpack error and data?

# CORRECT: Only unpack what you need
def process_tuple():
    success, _, _ = get_result()  # Explicit about ignoring others
    # OR
    result = get_result()
    return result[0]
```

**Why it matters:**

- Makes intent unclear
- Maintenance confusion (why are these unpacked?)

**Safety:** Code works fine, just bad style.

---

## ERRORS THAT REQUIRE REVIEW (308 errors = 18%)

### DTZ005: `datetime.now()` Without Timezone (76 errors)

**Impact: MEDIUM** - Could cause timestamp bugs

```python
from datetime import datetime

# ERROR: Naive datetime (no timezone)
start_time = datetime.now()  # Local time, but which timezone?
# What if code runs in US, stores time, then runs in Europe?

# CORRECT: Explicit timezone
from datetime import datetime, UTC

start_time = datetime.now(UTC)  # Crystal clear: UTC

# OR if you need local time:
import pytz
local_tz = pytz.timezone('America/New_York')
start_time = datetime.now(local_tz)
```

**Why it matters:**

- Timezone-naive datetimes are ambiguous
- Comparisons across timezones fail
- Daylight saving time causes off-by-one errors
- Serialization/deserialization bugs

**Risk Level:**

- LOW if: All timestamps are local-only, never compared across zones
- MEDIUM if: Timestamps are stored/transmitted/compared
- HIGH if: Multi-zone operations

**For MCP Server:** Likely LOW since it's a single-system knowledge base.

---

### E402: Module Level Import Not at Top of File (37 errors)

**Impact: LOW** - Violates Python conventions

```python
# ERROR: Import after code
import sys
from services import database

print("Initializing...")  # Code runs first

from tools import concept_tools  # Import after code runs!
# ^ This violates module initialization order

# CORRECT: All imports at top
import sys

from services import database
from tools import concept_tools

print("Initializing...")  # Code after all imports
```

**Why it matters:**

- Python expects imports at top
- Side effects in imports might not execute at the right time
- Tools expect imports at top (including type checkers)

**Safety:** Usually code still works, but can cause weird initialization bugs.

---

### B904: Raise Exception Without Context (14 errors)

**Impact: MEDIUM** - Hides debugging info

```python
# ERROR: Re-raising without context
try:
    database.connect()
except DatabaseError as err:
    raise OperationError("Failed to connect")  # Lost original error!
    # ^ Stack trace doesn't show DatabaseError


# CORRECT: Chain the exception
try:
    database.connect()
except DatabaseError as err:
    raise OperationError("Failed to connect") from err  # Keep original
    # ^ Stack trace shows BOTH errors, helps debugging
```

**Why it matters:**

- Original error is hidden
- Debugging is harder (you can't see what caused the original failure)
- Best practice for exception handling

**Safety:** Code works, but makes debugging harder.

---

### B017: Bare `except Exception` (7 errors)

**Impact: MEDIUM** - Too broad error catching

```python
# ERROR: Catches too much
try:
    process_data()
except Exception:  # What kind of exception?
    pass  # Silently swallowed! Could hide real bugs


# CORRECT: Catch specific exceptions
try:
    process_data()
except (ValueError, KeyError) as e:
    logger.warning(f"Data format issue: {e}")
except DatabaseError as e:
    logger.error(f"Database issue: {e}")
    raise  # Re-raise if it's critical
```

**Why it matters:**

- Bare `except Exception` catches everything (even KeyboardInterrupt in Python 3)
- Hides actual bugs
- Makes debugging impossible (can't see what failed)

**Safety:** Code might work but could hide critical bugs.

---

### RUF001: Ambiguous Unicode Characters (14 errors)

**Impact: LOW** - Confusing characters

```python
# ERROR: Confusing unicode
# String contains:
message = "Help message: ℹ"  # ℹ looks like 'i' but it's not!
              # ^ Unicode INFORMATION SOURCE (U+2139)
              # vs ASCII 'i' (U+0069)

# Later code:
if text == "Help message: i":  # Comparison fails!
    send_help()

# CORRECT: Use ASCII
message = "Help message: i"  # Plain ASCII
```

**Why it matters:**

- Unicode lookalikes cause comparison bugs
- Hard to debug (they look the same)
- Accessibility issues

**Safety:** Code might fail mysteriously when comparing strings.

---

## ERRORS WITH MINOR IMPACT (123 errors = 7%)

### UP035: Deprecated Typing Imports (83 errors)

**Impact: MINOR** - Will break in Python 3.14

```python
# ERROR: Deprecated (will be removed in Python 3.14)
from typing import Callable, List, Dict

def process(items: List[str]) -> Dict[str, Callable]:
    ...

# CORRECT NOW: Use modern equivalents
from collections.abc import Callable
from typing import Dict  # Dict still OK for now, will change

def process(items: list[str]) -> dict[str, Callable]:
    ...
```

**Why it matters:**

- `typing.List` will be removed in Python 3.14
- Modern code uses `list` directly
- No current impact, but future compatibility issue

**Safety:** Works today, might break in Python 3.14.

---

### RUF013: Implicit Optional (25 errors)

**Impact: LOW** - Type checking issue

```python
# ERROR: Implicit Optional (violates PEP 484)
def get_user(user_id: int) -> str = None:
    # Says "returns str" but actually returns str OR None
    # Type checker gets confused
    ...

# CORRECT: Be explicit
def get_user(user_id: int) -> str | None:
    ...

# OR
from typing import Optional
def get_user(user_id: int) -> Optional[str]:
    ...
```

**Why it matters:**

- Type checkers (mypy, pyright) get confused
- PEP 484 prohibits this pattern
- IDE autocomplete might be wrong

**Safety:** Code works, but type checking fails.

---

### S\* Security Errors (25 errors)

**Impact: MEDIUM** - Potential security issues

#### S603: `subprocess` call without checking input

```python
# ERROR: Untrusted input to subprocess
user_command = input("Enter command: ")
subprocess.call(user_command, shell=True)  # !! INJECTION RISK !!
# User could enter: "; rm -rf /"

# CORRECT: Don't use shell=True with user input
user_command = input("Enter command: ")
subprocess.run(["echo", user_command])  # Safe: command is separate from input
```

#### S311: Weak random generation

```python
# ERROR: Not cryptographically secure
import random
token = ''.join(random.choices('abcdef0123456789', k=16))
# Predictable! Can be guessed.

# CORRECT: Use secrets module
import secrets
token = secrets.token_hex(8)  # Cryptographically secure
```

**Why it matters:**

- SQL injection, command injection, weak secrets
- Real security vulnerabilities
- Can be exploited by attackers

**Safety:** CODE WORKS but is VULNERABLE TO ATTACK.

---

## ERRORS THAT DON'T MATTER MUCH (140 errors = 8%)

### SIM105: Use `contextlib.suppress()` (14 errors)

**Impact: NONE** - Just style

```python
# ERROR: Manual suppress
try:
    database.disconnect()
except ConnectionError:
    pass  # Ignore if already disconnected


# CORRECT: Use contextlib.suppress
from contextlib import suppress

with suppress(ConnectionError):
    database.disconnect()
```

**Why it matters:** `suppress()` is more readable and explicit.

---

### SIM108: Use Ternary Operator (11 errors)

**Impact: NONE** - Just style

```python
# ERROR: Simple if-else
if value > 10:
    result = "high"
else:
    result = "low"

# BETTER: Ternary operator
result = "high" if value > 10 else "low"
```

**Why it matters:** Ternary is more concise (when condition isn't complex).

---

### E712: Use `not x` Instead of `x == False` (8 errors)

**Impact: NONE** - Just style

```python
# ERROR: Explicit comparison to False
if process_success == False:  # Awkward!
    retry()

# CORRECT: Use not operator
if not process_success:
    retry()
```

**Why it matters:** `not x` is more readable and handles None correctly.

---

## SUMMARY TABLE

| Category                | Errors | Impact     | Fix Now?    |
| ----------------------- | ------ | ---------- | ----------- |
| Whitespace & Formatting | 365    | NONE       | YES - Auto  |
| Type Annotation Syntax  | 524    | NONE       | YES - Auto  |
| Unused Code             | 287    | LOW        | YES - Auto  |
| Import Organization     | 163    | NONE       | YES - Auto  |
| **Timezone Handling**   | **76** | **MEDIUM** | **MANUAL**  |
| **Exception Handling**  | **21** | **MEDIUM** | **MANUAL**  |
| **Security Issues**     | **25** | **HIGH**   | **REVIEW**  |
| Import Placement        | 37     | LOW        | MANUAL      |
| Code Style (SIM, RUF)   | 140    | NONE       | OPTIONAL    |
| Other                   | 74     | LOW        | AUTO/MANUAL |

---

## The Bottom Line

```
Functionality Impact by Category:

NO IMPACT:          1,239 errors (72%)
  ↓ Auto-fix immediately

LOW IMPACT:         378 errors (22%)
  ↓ Fix or ignore, doesn't break code

MEDIUM/HIGH RISK:   95 errors (6%)
  ↓ Manual review needed, could cause bugs
    - Timezone (76 errors)
    - Exception handling (14 errors)
    - Security (25 errors)
```

**Will the MCP server run?**
**YES.** None of these errors prevent execution.

**Will it work correctly?**
**PROBABLY.** But 95 errors (especially timezone & security) could cause subtle bugs.

**What should you do?**

1. Auto-fix all (1,199 errors): 5 minutes
2. Manual review medium/high risk (95 errors): 1-2 hours
3. Decide on style improvements (378 errors): Optional
