#### Issue #1: Name Length Validation Not Enforced

**Severity**: Medium
**Component**: create_concept tool - Input validation
**Test Case**: TC-3.7 (Invalid Input - Name Too Long)

**Symptom**: Concept created successfully with 201-character name

**Expected**: Validation error rejecting name > 200 characters

**Actual**: Concept created with success=true and valid concept_id: `916de507-908a-4eb8-b3b6-93e1d8b38b03`

**Trigger**:

1. Call `create_concept` with name parameter containing 201 characters
2. Provide valid explanation
3. Execute tool call

**Location**: To be determined (likely in `tools/concept_tools.py` or validation layer)

**Error**: No error - operation succeeded when it should have failed

**Severity Impact**: Allows database pollution with excessively long names. Could cause UI truncation issues, display problems, or downstream query failures. Violates documented API constraints (max 200 chars per specification).

**Constraints**: API specification states name field max length = 200 characters

**Context**:

- Test case: TC-3.7
- Environment: MCP Knowledge Server Phase 1 testing
- Affected tool: `create_concept`
- Related tests: Name validation working correctly for empty/whitespace (TC-3.5)
