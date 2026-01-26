#### Issue #3: Non-Existent Concept Returns Generic Error on Update

**Severity**: Medium
**Component**: update_concept tool - Error handling
**Test Case**: TC-5.7 (Invalid Update - Non-Existent Concept)

**Symptom**: Attempting to update non-existent concept returns generic "internal_error" instead of specific "concept_not_found" error

**Expected**: Error type "concept_not_found" with clear message like "The concept you're looking for doesn't exist or has been deleted"

**Actual**: Error type "internal_error" with generic message "An unexpected error occurred. Please try again."

**Trigger**:

1. Call `update_concept` with fake UUID: `00000000-0000-0000-0000-000000000000`
2. Provide valid update parameters (e.g., explanation)
3. Observe error response

**Location**: To be determined (likely in `tools/concept_tools.py` - update_concept error handling or repository layer)

**Error**: `{"success":false,"error_type":"internal_error","error":"An unexpected error occurred. Please try again.","updated_fields":[]}`

**Severity Impact**: Poor user experience due to unclear error messages. Users cannot distinguish between system failures and resource-not-found conditions. Makes debugging difficult. Inconsistent with error handling in `get_concept` which correctly returns "concept_not_found".

**Constraints**: Error handling should be consistent across all concept operations

**Context**:

- Test case: TC-5.7
- Affected tool: `update_concept`
- Comparison: `get_concept` correctly returns "concept_not_found" for same scenario (TC-4.4)
- This suggests error handling inconsistency between tools
