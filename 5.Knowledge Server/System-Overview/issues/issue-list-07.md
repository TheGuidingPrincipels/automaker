#### Issue #7: Documentation Mismatch - sort_order Parameter Not Implemented

**Severity**: Medium
**Priority**: Medium
**Component**: get_concepts_by_certainty tool - Parameter validation

**Symptom**: Test documentation for get_concepts_by_certainty specifies a sort_order parameter ("asc" or "desc") that does not exist in the actual tool implementation.

**Expected**: Tool should accept sort_order parameter as documented in Phase 4 test specification, allowing users to control whether results are sorted ascending (lowest certainty first) or descending (highest certainty first).

**Actual**:

- Tool rejects sort_order parameter with validation error
- Tool always returns results in ascending order (lowest certainty first)
- No way to request descending sort order

**Trigger**:

1. Call get_concepts_by_certainty with sort_order="asc" or sort_order="desc"
2. Validation error occurs immediately

**Location**:

- Tool: get_concepts_by_certainty
- File: `tools/analytics_tools.py`
- Pydantic validation schema missing sort_order field

**Error**:

```
1 validation error for call[get_concepts_by_certainty]
sort_order
  Unexpected keyword argument [type=unexpected_keyword_argument, input_value='asc', input_type=str]
```

**Severity Impact**: Users following test documentation will encounter errors when attempting to use sort_order parameter. Limits flexibility for "discovery mode" workflows where users want highest-certainty concepts first. Creates inconsistency between documentation and implementation. Blocks test execution for TC-CERT-2.6.

**Constraints**:

- If parameter is intended: Must update tool implementation to accept sort_order
- If parameter is not intended: Must update all test documentation to remove references
- Default ascending sort behavior is functional and appropriate for "learning mode"

**Context**:

- Test Cases: TC-CERT-2.2 (initial discovery), TC-CERT-2.6 (explicit test)
- Frequency: Every attempt to use sort_order parameter
- Environment: Knowledge Server MCP, all services operational
- Documentation: PHASE-4-Analytics-and-System-Management.md lines 285-304 specify sort_order parameter
