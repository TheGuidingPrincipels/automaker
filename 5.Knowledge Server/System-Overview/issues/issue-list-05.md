#### Issue #5: Semantic Search Cannot Combine Area and Topic Filters

**Severity**: HIGH
**Priority**: P1
**Component**: search_concepts_semantic tool - ChromaDB where clause generation

**Symptom**: When attempting to use both area and topic filter parameters simultaneously in search_concepts_semantic, the tool returns a validation error instead of applying both filters.

**Expected**: The tool should accept multiple metadata filters (area, topic) simultaneously and return only concepts matching all specified criteria, similar to how search_concepts_exact handles multiple filters.

**Actual**: The tool returns:

```json
{
  "success": false,
  "error_type": "validation_error",
  "error": "The provided input is invalid. Please check your data and try again. (Expected where to have exactly one operator, got {'area': 'Computer Science', 'topic': 'Artificial I)"
}
```

**Trigger**:

1. Call search_concepts_semantic with parameters:

```json
{
  "query": "neural",
  "area": "Computer Science",
  "topic": "Artificial Intelligence"
}
```

**Location**:

- `tools/search_tools.py` - ChromaDB where clause generation in semantic search
- OR `services/chromadb_service.py` - Query construction logic

**Error Message**: "The provided input is invalid. Please check your data and try again. (Expected where to have exactly one operator, got {'area': 'Computer Science', 'topic': 'Artificial I)"

**Severity Impact**: This significantly limits search refinement capabilities. Users cannot narrow semantic searches to specific combinations of area and topic, forcing them to either:

1. Use only one filter and manually review more results
2. Switch to exact search (losing semantic similarity benefits)
3. Post-filter results in application code

This creates a major functional gap compared to search_concepts_exact, which successfully handles multiple simultaneous filters.

**Constraints**:

- ChromaDB's where clause syntax may require specific operator structure
- Current implementation appears to support only single metadata filters
- The search_concepts_exact tool demonstrates that the backend data supports multiple filter combinations

**Context**:

- Test Case ID: TC-SEARCH-1.4
- Frequency: 100% reproducible
- Workaround: Use topic filter alone (works), or use search_concepts_exact instead
- Related Tests: Test 1.3 (area only) and Test 1.4 (topic only) both pass individually
- Comparison: search_concepts_exact successfully combines area+topic+subtopic in Test 2.4

**Recommendation**: Fix ChromaDB where clause generation to support multiple metadata filters. Investigate whether ChromaDB requires specific syntax for compound where clauses (e.g., `{"$and": [{"area": "X"}, {"topic": "Y"}]}` format).
