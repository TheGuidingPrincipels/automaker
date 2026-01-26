#### Issue #4: Non-Existent Concept Returns Generic Error on Delete

**Severity**: Low
**Component**: delete_concept tool - Error handling
**Test Case**: TC-6.2 (Delete Non-Existent Concept)

**Symptom**: Attempting to delete non-existent concept returns generic "internal_error" instead of specific "concept_not_found" error

**Expected**: Error type "concept_not_found" with clear message

**Actual**: Error type "internal_error" with generic message "An unexpected error occurred. Please try again."

**Trigger**:

1. Call `delete_concept` with fake UUID: `00000000-0000-0000-0000-000000000000`
2. Observe error response

**Location**: To be determined (likely in `tools/concept_tools.py` - delete_concept error handling)

**Error**: `{"success":false,"error_type":"internal_error","error":"An unexpected error occurred. Please try again.","concept_id":"00000000-0000-0000-0000-000000000000"}`

**Severity Impact**: Low severity because idempotent delete (TC-6.3) works correctly - deleting already-deleted concepts succeeds gracefully. However, inconsistent error handling reduces code quality and user experience for edge case of attempting to delete truly non-existent concept.

**Constraints**: Error handling should be consistent with get_concept behavior

**Context**:

- Test case: TC-6.2
- Related: Same issue as #3 (update_concept)
- Pattern: Both update and delete return generic errors for non-existent resources
- Note: Idempotent delete (TC-6.3) works correctly, returning success
