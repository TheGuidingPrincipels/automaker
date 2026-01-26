# Test Issue List - Research Cache Manual Test Plan

Execution Date: 2025-11-12
Test Environment: Short-Term Memory MCP Server, SQLite database, Claude Desktop interface
Overall Status: PASS (with minor issues)
Total Issues Found: 0 Critical, 0 High, 1 Medium, 1 Low

## Low Priority Issues

### 🟢 Issue #2: Test plan documentation mismatch - "community" category not implemented

**Symptom**: Test plan (PHASE-3-Research-Cache.md) specifies 4 domain categories including "community", but system only implements 3 categories (official, in_depth, authoritative).

**Expected**: Either system should support "community" category as documented in test plan, or test plan should reflect actual implementation with only 3 categories.

**Actual**:

- Attempting to add domain with category "community" returns: `"Failed to add domain: CHECK constraint failed: category IN ('official', 'in_depth', 'authoritative')"`
- Database constraint explicitly limits to 3 categories

**Trigger**:

1. Follow test plan Test 4, step 3: Add domain with category "community"
2. Observe CHECK constraint error
3. Note test plan expectation doesn't match implementation

**Location**:

- Test Plan: PHASE-3-Research-Cache.md, Test 4, step 3
- Database: domain_whitelist table CHECK constraint
- Documentation discrepancy

**Error**: `"Failed to add domain: CHECK constraint failed: category IN ('official', 'in_depth', 'authoritative')"`

**Severity Impact**: Low - Documentation inconsistency only. System works correctly per its implementation. No functional impact since system properly validates and rejects invalid categories. Test can be adjusted to work with 3 categories.

**Constraints**: Decision needed: Add "community" category to implementation OR update test plan documentation to reflect 3-category design.

**Context**:

- Test case affected: TC-RC-04.3 (Add community domain)
- Discovered during Test 4: Add Domain to Whitelist
- Test plan shows reddit.com as example "community" domain
- System successfully validates all 3 implemented categories (official, in_depth, authoritative)
- Invalid category handling works correctly with proper error message for non-standard categories

## Notes for Developers

- Issue #1 affects user experience but not functionality - duplicate prevention works correctly
- Issue #2 is documentation-only - no code changes needed if 3-category design is intentional
- All error messages are exact copies from test execution on 2025-11-14
- Test environment contained persistent data from 2025-11-12 manual testing session
- All 6 Research Cache tools passed functional testing despite these issues

---

📋 Issue #1: Empty string parameter rejected for optional relationship_type filter
Symptom: When calling get_related_concepts with relationship_type set to empty string (""), tool returns error instead of treating it as null filter
Expected: Empty string should be treated as null/no filter, returning all relationships (consistent with other optional parameters in system)
Actual: Returns error: "Invalid relationship type: . Must be one of: prerequisite, related, similar, builds_on"
Trigger:

Call get_related_concepts tool
Set concept_id to valid concept with relationships
Set relationship_type parameter to empty string ("")
Tool returns error instead of treating as null filter

Location: short-term-memory MCP server, get_related_concepts tool implementation
Error: "Invalid relationship type: . Must be one of: prerequisite, related, similar, builds_on"
Severity Impact: Minor usability issue. Workaround exists (omit parameter entirely). Does not block functionality. May cause confusion for users expecting empty string to behave like null.
Constraints: Parameter validation should handle empty strings consistently across all tools. If empty string is invalid, documentation should specify "omit parameter" rather than "pass empty string".
Context:

Test Case: TC-P5-04.1 (get_related_concepts without filter)
Frequency: Occurs every time empty string used
Workaround: Omit relationship_type parameter entirely
Related tools: Other MCP tools may have similar inconsistency

Notes for Developers

Only 1 medium-priority issue found in Phase 5 testing
All 4 tools (add_concept_question, get_concept_page, add_concept_relationship, get_related_concepts) passed functional tests
Knowledge graph functionality working correctly
Issue #1 is cosmetic validation inconsistency with clear workaround
No data integrity or performance issues discovered
All 4 relationship types work correctly (prerequisite, related, similar, builds_on)
All 4 pipeline stages work correctly for questions (research, aim, shoot, skin)
Graph traversal and enrichment working as expected
