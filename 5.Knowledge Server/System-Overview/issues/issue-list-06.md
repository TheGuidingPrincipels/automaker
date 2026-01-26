#### Issue #6: Uncategorized Concepts Not Searchable via Exact Search

**Severity**: Medium
**Priority**: Medium
**Component**: list_hierarchy and search_concepts_exact tools - Categorization handling

**Symptom**: Concepts without area/topic/subtopic categorization appear in hierarchy under "Uncategorized" area but cannot be retrieved using search_concepts_exact with area="Uncategorized".

**Expected**: Concepts displayed in hierarchy as belonging to "Uncategorized" area should be searchable using exact search with area="Uncategorized" parameter.

**Actual**:

- list_hierarchy returns: "Uncategorized" area with concept_count=5
- search_concepts_exact(area="Uncategorized") returns: 0 results
- Inconsistent behavior between hierarchy display and search functionality

**Trigger**:

1. Call list_hierarchy
2. Observe "Uncategorized" area with concept_count > 0
3. Call search_concepts_exact with area="Uncategorized"
4. Results array is empty despite hierarchy showing concepts exist

**Location**:

- Tool: list_hierarchy (hierarchy aggregation logic)
- Tool: search_concepts_exact (area filtering logic)
- Likely: Mismatched handling of NULL/empty area values
- Files: `tools/search_tools.py` or `tools/analytics_tools.py`

**Error**: No error message - silent inconsistency between tools. Hierarchy treats NULL area as "Uncategorized" while search does not recognize "Uncategorized" as a valid area value.

**Severity Impact**: Users cannot discover or retrieve concepts that appear in the hierarchy under "Uncategorized". This breaks the expected workflow of "see in hierarchy → search by area" and creates confusion about data accessibility. Affects data discoverability and user trust in search functionality.

**Constraints**:

- Must maintain consistent representation of uncategorized concepts across all tools
- Search and hierarchy must agree on how NULL/empty categorization is handled
- Backward compatibility with existing queries

**Context**:

- Test Case: TC-HIER-1.4 (Handle Uncategorized Concepts)
- Frequency: Consistent - occurs whenever uncategorized concepts exist
- Environment: Knowledge Server MCP, all databases operational
- Data state: 5 concepts with NULL/empty area values present in database
