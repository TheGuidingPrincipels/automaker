# Phase 4: Error Handling Standardization

**STATUS: ✅ COMPLETED** - Migration from `error_utils.py` to `responses.py` is complete.

## Context

This is Phase 4 of a 6-phase refactoring effort for the MCP Knowledge Server codebase. This phase focuses on standardizing error handling and response patterns.

**Prerequisites:** Phases 1-3 should be completed first

---

## Problem Statement

Multiple error handling patterns exist:

| Pattern                     | Location           | Style                                                          |
| --------------------------- | ------------------ | -------------------------------------------------------------- |
| Dict with `success: bool`   | Tools              | `{"success": True, "concept_id": "..."}`                       |
| Result union type           | Confidence service | `Result = Union[Success, Error]`                               |
| 8 response builders         | responses.py       | `success_response`, `error_response`, `validation_error`, etc. |
| Post-construction injection | Various            | `error["concept_id"] = None` added after building              |

**Issues:**

- Inconsistent response keys (`concept_id` vs `concept` vs `results`)
- Different error builders used inconsistently
- Tools manually add fields after error construction
- Two error code enums (ErrorType and ErrorCode with different casing)

**Target:** Single response pattern with consistent structure

---

## Pre-Implementation: Investigation Phase

Before making changes, launch 3 Explore agents:

### Agent 1: Tool Response Investigation

```
Analyze all tool function return statements:
- What keys are returned on success?
- What keys are returned on error?
- Which error builder functions are used?
- What fields are added post-construction?

Files to check: tools/concept_tools.py, tools/search_tools.py,
tools/relationship_tools.py, tools/analytics_tools.py

Document: All unique response structures and their usage counts.
```

### Agent 2: Error Builder Investigation

```
Analyze error handling utilities:
- tools/responses.py - all functions and their signatures
- ErrorType enum values
- services/confidence/models.py - ErrorCode enum
- How errors are constructed and returned

Document: All error types, builders, and their differences.
```

### Agent 3: Result Pattern Investigation

```
Analyze the confidence service Result pattern:
- Success and Error dataclasses
- How they're used in confidence calculations
- Whether this pattern is used elsewhere
- Benefits/drawbacks vs Dict pattern

Document: Where Result pattern is used vs Dict pattern.
```

---

## Implementation Steps

### Step 1: Define Standard Response Models

**File: `tools/responses.py`**

```python
"""Standard response models for MCP tools.

All tool functions should return ToolResponse for consistency.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from enum import Enum

class ErrorType(str, Enum):
    """Error types for tool responses."""
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    DATABASE_ERROR = "database_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"
    PERMISSION_ERROR = "permission_error"

@dataclass
class ErrorDetail:
    """Structured error information."""
    type: ErrorType
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class ToolResponse:
    """Standard response for all tool functions.

    Success response:
        ToolResponse(success=True, message="Created", data={"concept_id": "abc"})

    Error response:
        ToolResponse(
            success=False,
            message="Validation failed",
            error=ErrorDetail(type=ErrorType.VALIDATION_ERROR, message="Name required")
        )
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorDetail] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for MCP response."""
        result = {
            "success": self.success,
            "message": self.message,
        }
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = {
                "type": self.error.type.value,
                "message": self.error.message,
            }
            if self.error.field:
                result["error"]["field"] = self.error.field
            if self.error.details:
                result["error"]["details"] = self.error.details
        return result

# Convenience constructors
def success_response(message: str, **data) -> Dict[str, Any]:
    """Create a success response dict."""
    return ToolResponse(success=True, message=message, data=data or None).to_dict()

def error_response(
    error_type: ErrorType,
    message: str,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an error response dict."""
    return ToolResponse(
        success=False,
        message=message,
        error=ErrorDetail(type=error_type, message=message, field=field, details=details)
    ).to_dict()

def validation_error(message: str, field: str, value: Any = None) -> Dict[str, Any]:
    """Create a validation error response."""
    return error_response(
        ErrorType.VALIDATION_ERROR,
        message,
        field=field,
        details={"invalid_value": value} if value is not None else None
    )

def not_found_error(resource_type: str, resource_id: str) -> Dict[str, Any]:
    """Create a not found error response."""
    return error_response(
        ErrorType.NOT_FOUND,
        f"{resource_type} not found: {resource_id}",
        details={"resource_type": resource_type, "resource_id": resource_id}
    )
```

### Step 2: Responses Module (Completed)

**File: `tools/responses.py`** (created, error_utils.py deleted)

```python
"""Response utilities for MCP tools.

Provides standardized success and error response builders.
"""
from tools.responses import (
    ErrorType,
    success_response,
    error_response,
    validation_error,
    not_found_error,
)

# Re-export for backwards compatibility
__all__ = ["ErrorType", "build_error_response", "build_validation_error", "build_not_found_error"]

def build_error_response(error_type: ErrorType, message: str = None, details: dict = None):
    """DEPRECATED: Use error_response() from tools/responses.py"""
    warnings.warn("build_error_response is deprecated, use error_response()", DeprecationWarning)
    return error_response(error_type, message or "An error occurred", details=details)

def build_validation_error(error_message: str, field: str = None, invalid_value: Any = None):
    """DEPRECATED: Use validation_error() from tools/responses.py"""
    warnings.warn("build_validation_error is deprecated, use validation_error()", DeprecationWarning)
    return validation_error(error_message, field or "unknown", invalid_value)

def build_not_found_error(resource_type: str, resource_id: str):
    """DEPRECATED: Use not_found_error() from tools/responses.py"""
    warnings.warn("build_not_found_error is deprecated, use not_found_error()", DeprecationWarning)
    return not_found_error(resource_type, resource_id)
```

### Step 3: Update concept_tools.py

**Before:**

```python
return {
    "success": True,
    "concept_id": concept_id,
    "message": "Concept created successfully"
}
```

**After:**

```python
from tools.responses import success_response, validation_error, not_found_error

# Success
return success_response("Concept created", concept_id=concept_id)

# Validation error
return validation_error("Name is required", field="name", value=name)

# Not found
return not_found_error("Concept", concept_id)
```

### Step 4: Update Other Tool Files

Apply same pattern to:

- `tools/search_tools.py`
- `tools/relationship_tools.py`
- `tools/analytics_tools.py`

**Example for search_tools.py:**

```python
# Before
return {
    "success": True,
    "results": results,
    "total": len(results),
    "message": "Search completed"
}

# After
return success_response(
    "Search completed",
    results=results,
    total=len(results)
)
```

### Step 5: Keep Result Pattern for Services

The confidence service's `Result = Union[Success, Error]` pattern is good for internal use. Keep it but convert at service boundary:

**File: `tools/concept_tools.py` (confidence integration)**

```python
from services.confidence.models import Success, Error

# When calling confidence service
result = await confidence_service.calculate(concept_id)

# Convert to tool response at boundary
if isinstance(result, Success):
    return success_response("Confidence calculated", score=result.value)
elif isinstance(result, Error):
    return error_response(
        ErrorType.INTERNAL_ERROR,
        result.message,
        details={"code": result.code.value}
    )
```

### Step 6: Unify Error Code Enums

Remove duplicate `ErrorCode` from confidence models, use shared `ErrorType`:

**File: `services/confidence/models.py`**

```python
# Remove this duplicate enum
# class ErrorCode(str, Enum):
#     VALIDATION_ERROR = "VALIDATION_ERROR"
#     ...

# Import from shared location
from tools.responses import ErrorType

@dataclass
class Error:
    message: str
    code: ErrorType  # Was ErrorCode
    details: Optional[dict] = None
```

---

## Verification

1. **Run tests:**

   ```bash
   pytest tests/ -v
   ```

2. **Check response consistency:**

   ```python
   # All tools should return similar structure
   from tools.concept_tools import create_concept
   result = await create_concept(name="Test", explanation="Test explanation")
   assert "success" in result
   assert "message" in result
   # On success: "data" contains resource-specific fields
   # On error: "error" contains type, message, optional field/details
   ```

3. **Verify responses module:**

   ```python
   from tools.responses import error_response
   # All imports from responses.py should work
   ```

4. **Test MCP server responses:**
   - Create concept → verify response structure
   - Get non-existent concept → verify error structure
   - Validation failure → verify error has field info

---

## Success Criteria

- [ ] `tools/responses.py` contains standard response models
- [ ] All tool functions use `success_response()` and `error_response()`
- [ ] No post-construction field injection (no `result["concept_id"] = None`)
- [ ] Old error builders marked deprecated
- [ ] Single `ErrorType` enum (no duplicate `ErrorCode`)
- [ ] Confidence service converts Result to ToolResponse at boundary
- [ ] All tests pass
- [ ] Response structure is consistent across all tools
