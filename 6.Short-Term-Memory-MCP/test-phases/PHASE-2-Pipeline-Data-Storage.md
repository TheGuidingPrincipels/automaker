# Test Phase 2: Pipeline Data & Storage

## 📋 Phase Overview

**Goal**: Test the tools that manage pipeline stage data and concept storage/completion lifecycle. These tools handle the workflow from concept identification through to permanent storage and cleanup.

**Tools Tested** (6):

1. `store_stage_data` - Store stage-specific data (research, aim, shoot, skin)
2. `get_stage_data` - Retrieve stage-specific data
3. `mark_concept_stored` - Mark concept as stored in Knowledge MCP
4. `get_unstored_concepts` - Find concepts not yet stored
5. `mark_session_complete` - Mark session as completed
6. `clear_old_sessions` - Manual cleanup of old sessions

**Estimated Time**: 45-60 minutes

---

## ✅ Prerequisites

- [ ] **Phase 1 completed successfully** (you have an active session with 5 concepts)
- [ ] At least 1 concept in "stored" status (from Phase 1, Test 5)
- [ ] At least 4 concepts in "identified" status
- [ ] Session ID from Phase 1 (today's date)
- [ ] Concept IDs saved from Phase 1
- [ ] Short-Term Memory MCP server is running

---

## 🧪 Test Execution

### Test 1: Store Stage Data

**Objective**: Store stage-specific data for concepts as they progress through the pipeline.

#### Steps:

1. **Select a concept** that is still in "identified" status (one of the 4 from Phase 1).

2. **Store RESEARCH stage data**:

```
Tool: store_stage_data
Parameters:
  concept_id: [UUID of selected concept]
  stage: "research"
  data: {
    "sources": [
      "https://www.postgresql.org/docs/current/indexes-types.html",
      "https://use-the-index-luke.com/"
    ],
    "key_points": [
      "B-trees are the default index type in PostgreSQL",
      "B-trees maintain sorted data for efficient range queries",
      "Height is logarithmic relative to number of entries"
    ],
    "research_duration_minutes": 15,
    "confidence_level": "high"
  }
```

3. **Verify the response** contains:
   - `status: "success"`
   - `concept_id` matching your input
   - `stage: "research"`
   - `data_id` (internal ID for the stage data)

4. **Store AIM stage data** for the same concept:

```
Tool: store_stage_data
Parameters:
  concept_id: [same UUID]
  stage: "aim"
  data: {
    "learning_objectives": [
      "Understand B-tree structure and balancing",
      "Learn when to use B-tree indexes vs other types",
      "Master query plan analysis with EXPLAIN"
    ],
    "chunking_strategy": "top-down",
    "estimated_mastery_time": "30 minutes",
    "prerequisites": ["basic SQL knowledge", "understanding of tree data structures"]
  }
```

Expected: Success with `stage: "aim"`

5. **Store SHOOT stage data** for the same concept:

```
Tool: store_stage_data
Parameters:
  concept_id: [same UUID]
  stage: "shoot"
  data: {
    "practice_exercises": [
      "Create B-tree index on users table",
      "Compare query plans with and without index",
      "Analyze index usage with pg_stat_user_indexes"
    ],
    "encoding_method": "practical examples",
    "hands_on_completed": true,
    "notes": "Successfully created indexes and observed 10x performance improvement"
  }
```

Expected: Success with `stage: "shoot"`

6. **Store SKIN stage data** for the same concept:

```
Tool: store_stage_data
Parameters:
  concept_id: [same UUID]
  stage: "skin"
  data: {
    "key_takeaways": [
      "B-trees excel at equality and range queries",
      "Index maintenance has minimal overhead in PostgreSQL",
      "Use partial indexes for filtered queries"
    ],
    "evaluation_score": 8.5,
    "areas_for_review": ["index bloat mitigation"],
    "ready_for_storage": true
  }
```

Expected: Success with `stage: "skin"`

7. **Test invalid stage**:

```
Tool: store_stage_data
Parameters:
  concept_id: [UUID]
  stage: "invalid_stage"
  data: {"test": "data"}
```

Expected: Error with "INVALID_STAGE"

8. **Test non-existent concept**:

```
Tool: store_stage_data
Parameters:
  concept_id: "00000000-0000-0000-0000-000000000000"
  stage: "research"
  data: {"test": "data"}
```

Expected: Error with "CONCEPT_NOT_FOUND"

9. **Test updating existing stage data** (UPSERT behavior):

```
Tool: store_stage_data
Parameters:
  concept_id: [same UUID]
  stage: "research"
  data: {
    "sources": [
      "https://www.postgresql.org/docs/current/indexes-types.html",
      "https://use-the-index-luke.com/",
      "https://stackoverflow.com/questions/tagged/postgresql+indexing"
    ],
    "sources_updated": true,
    "update_reason": "Added community resource"
  }
```

Expected: Success (should update the existing research stage data)

#### Success Criteria:

- [ ] All 4 stages (research, aim, shoot, skin) stored successfully
- [ ] Each stage returns unique data_id
- [ ] Invalid stage returns error
- [ ] Non-existent concept returns error
- [ ] Updating existing stage data works (UPSERT)
- [ ] Each operation response time < 500ms

#### Record Results:

```
Research stage stored: [yes/no]
AIM stage stored: [yes/no]
SHOOT stage stored: [yes/no]
SKIN stage stored: [yes/no]
UPSERT worked: [yes/no]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 2: Get Stage Data

**Objective**: Retrieve stage-specific data for a concept.

#### Steps:

1. **Retrieve RESEARCH stage data** (from Test 1):

```
Tool: get_stage_data
Parameters:
  concept_id: [UUID from Test 1]
  stage: "research"
```

2. **Verify the response** contains:
   - `status: "success"`
   - `concept_id` matching your input
   - `stage: "research"`
   - `data` object with sources, key_points (including updated sources from Test 1 step 9)
   - `created_at` timestamp

3. **Retrieve all other stages**:
   - Get AIM data: `get_stage_data` with `stage: "aim"`
   - Get SHOOT data: `get_stage_data` with `stage: "shoot"`
   - Get SKIN data: `get_stage_data` with `stage: "skin"`

4. **Test non-existent stage data** (use concept that doesn't have stage data):

```
Tool: get_stage_data
Parameters:
  concept_id: [UUID of a different concept from Phase 1]
  stage: "research"
```

Expected: `status: "not_found"`

5. **Test invalid stage**:

```
Tool: get_stage_data
Parameters:
  concept_id: [UUID]
  stage: "invalid_stage"
```

Expected: Error with "INVALID_STAGE"

#### Success Criteria:

- [ ] All 4 stages retrieved successfully with correct data
- [ ] Updated research data reflects changes from Test 1 step 9
- [ ] Non-existent stage data returns "not_found"
- [ ] Invalid stage returns error
- [ ] Response time < 300ms per query

#### Record Results:

```
All stages retrieved: [yes/no]
Data matches stored values: [yes/no]
UPSERT verification: [updated research data present: yes/no]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 3: Mark Concept Stored

**Objective**: Mark concepts as permanently stored in Knowledge MCP.

#### Steps:

1. **Update concept from Test 1 to "evaluated" status** (if not already):

```
Tool: update_concept_status
Parameters:
  concept_id: [UUID from Test 1]
  new_status: "evaluated"
```

2. **Mark concept as stored** with Knowledge MCP ID:

```
Tool: mark_concept_stored
Parameters:
  concept_id: [UUID from Test 1]
  knowledge_mcp_id: "kmcp_btree_index_structure_20251112_001"
```

3. **Verify the response** contains:
   - `status: "success"`
   - `concept_id` matching your input
   - `knowledge_mcp_id: "kmcp_btree_index_structure_20251112_001"`
   - `stored_at` timestamp

4. **Verify status updated atomically**:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: "stored"
  include_stage_data: false
```

Expected: Now 2 concepts with status "stored" (one from Phase 1, one from this test)

5. **Test marking non-existent concept**:

```
Tool: mark_concept_stored
Parameters:
  concept_id: "00000000-0000-0000-0000-000000000000"
  knowledge_mcp_id: "test_id"
```

Expected: Error with "CONCEPT_NOT_FOUND"

6. **Mark another concept as stored** (to prepare for Test 4):
   - Select another concept from Phase 1
   - Update its status to "evaluated"
   - Mark it stored with: `knowledge_mcp_id: "kmcp_index_scan_comparison_20251112_002"`

7. **Verify Knowledge MCP ID is persisted**:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: "stored"
  include_stage_data: false
```

Check that concepts have `knowledge_mcp_id` field populated.

#### Success Criteria:

- [ ] Concept marked as stored successfully
- [ ] Status atomically updated to "stored"
- [ ] Knowledge MCP ID persisted correctly
- [ ] stored_at timestamp recorded
- [ ] Non-existent concept returns error
- [ ] Response time < 500ms

#### Record Results:

```
Concepts marked as stored: [2]
Knowledge MCP IDs assigned: [yes/no]
Atomic status update: [yes/no]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 4: Get Unstored Concepts

**Objective**: Find all concepts in a session that haven't been stored to Knowledge MCP yet.

#### Steps:

1. **Query unstored concepts**:

```
Tool: get_unstored_concepts
Parameters:
  session_id: [today's date]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `session_id` matching your input
   - `unstored_count: 3` (you have 5 concepts, 2 stored in Test 3)
   - `concepts` array with 3 concepts
   - Each concept should NOT have `knowledge_mcp_id` populated

3. **Verify the correct concepts are returned**:
   - Concepts with status "stored" but no Knowledge MCP ID should NOT appear
   - Only concepts truly missing Knowledge MCP integration should appear

4. **Mark all remaining concepts as stored** (to test empty result):
   - For each of the 3 unstored concepts:
     - Update status to "evaluated" (if needed)
     - Call `mark_concept_stored` with unique Knowledge MCP IDs

5. **Query again** (should now be empty):

```
Tool: get_unstored_concepts
Parameters:
  session_id: [today's date]
```

Expected: `unstored_count: 0`, empty concepts array

6. **Test with non-existent session**:

```
Tool: get_unstored_concepts
Parameters:
  session_id: "2020-01-01"
```

Expected: Still success, but `unstored_count: 0` (no concepts for that session)

#### Success Criteria:

- [ ] Initially 3 unstored concepts found
- [ ] After marking all as stored, 0 unstored concepts
- [ ] Only concepts missing Knowledge MCP ID are returned
- [ ] Non-existent session returns empty result gracefully
- [ ] Response time < 500ms

#### Record Results:

```
Initial unstored count: [3]
Final unstored count: [0]
Correct filtering: [yes/no]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 5: Mark Session Complete

**Objective**: Mark a session as completed after all concepts are stored.

#### Steps:

1. **Verify all concepts are stored**:

```
Tool: get_unstored_concepts
Parameters:
  session_id: [today's date]
```

Expected: `unstored_count: 0`

2. **Mark session complete**:

```
Tool: mark_session_complete
Parameters:
  session_id: [today's date]
```

3. **Verify the response** contains:
   - `status: "success"`
   - `session_id` matching your input
   - `total_concepts: 5`
   - `message` confirming completion

4. **Verify session status updated**:

```
Tool: get_active_session
Parameters:
  date: [today's date]
```

Expected: `session_status: "completed"`

5. **Test completing session with unstored concepts** (create new session):
   - Create a new session for tomorrow: `initialize_daily_session` with `date: "2025-11-13"`
   - Add 2 concepts: `store_concepts_from_research`
   - Try to mark complete WITHOUT storing:

```
Tool: mark_session_complete
Parameters:
  session_id: "2025-11-13"
```

Expected: `status: "warning"` with list of unstored concepts

6. **Test completing non-existent session**:

```
Tool: mark_session_complete
Parameters:
  session_id: "2020-01-01"
```

Expected: Error with "SESSION_NOT_FOUND"

#### Success Criteria:

- [ ] Session marked complete successfully when all concepts stored
- [ ] Session status updated to "completed"
- [ ] Warning returned when unstored concepts remain
- [ ] Non-existent session returns error
- [ ] Response time < 500ms

#### Record Results:

```
Session marked complete: [yes/no]
Status updated: [completed]
Warning for unstored concepts: [yes/no]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 6: Clear Old Sessions

**Objective**: Manually clean up sessions older than a specified number of days.

#### Steps:

1. **Check current session count** (before cleanup):

```
Tool: get_system_metrics
Parameters: [none]
```

Note the `database.sessions` count.

2. **Create old test sessions** (if you have permission to manipulate dates):
   - This step may be skipped if you cannot create backdated sessions
   - Ideally, create sessions with dates 8+ days ago for testing

3. **Run cleanup** (keep last 7 days):

```
Tool: clear_old_sessions
Parameters:
  days_to_keep: 7
```

4. **Verify the response** contains:
   - `status: "success"`
   - `cutoff_date` (7 days ago in YYYY-MM-DD format)
   - `days_to_keep: 7`
   - `sessions_deleted` (count of deleted sessions)
   - `concepts_deleted` (count of deleted concepts)
   - `deleted_sessions` (array of session IDs)

5. **Test with different retention period**:

```
Tool: clear_old_sessions
Parameters:
  days_to_keep: 1
```

Expected: Should delete yesterday's sessions if any exist (including the test session from Test 5 step 5)

6. **Verify cascade deletion** (concepts and stage data deleted):
   - Check that concepts from deleted sessions are gone
   - Check that stage_data entries are gone
   - Use `get_system_metrics` to verify database counts decreased

7. **Test with invalid parameter**:

```
Tool: clear_old_sessions
Parameters:
  days_to_keep: 0
```

Expected: Error with "INVALID_PARAMETER" (minimum is 1 day)

8. **Test when no sessions to delete**:

```
Tool: clear_old_sessions
Parameters:
  days_to_keep: 365
```

Expected: Success with `sessions_deleted: 0`

#### Success Criteria:

- [ ] Old sessions deleted successfully
- [ ] Cascade deletion removes concepts and stage data
- [ ] Cutoff date calculated correctly
- [ ] Invalid parameter returns error
- [ ] No sessions to delete handled gracefully
- [ ] Response time < 2 seconds

#### Record Results:

```
Sessions deleted: [N]
Concepts deleted: [N]
Cascade deletion verified: [yes/no]
Response time: [X]ms
Notes: [any observations]
```

---

## 📊 Phase 2 Test Report

**Completion Date**: [YYYY-MM-DD]
**Tester**: [Your Name]
**MCP Server Version**: [Check package.json or git commit]

### Summary

| Test | Tool                  | Status            | Response Time | Notes |
| ---- | --------------------- | ----------------- | ------------- | ----- |
| 1    | store_stage_data      | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 2    | get_stage_data        | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 3    | mark_concept_stored   | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 4    | get_unstored_concepts | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 5    | mark_session_complete | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 6    | clear_old_sessions    | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |

### Issues Found

1. **Issue**: [Description]
   - **Severity**: Critical / High / Medium / Low
   - **Tool**: [Tool name]
   - **Steps to Reproduce**: [Steps]
   - **Expected**: [Expected behavior]
   - **Actual**: [Actual behavior]

2. [Add more issues as needed]

### Performance Observations

- Average response time: \_\_\_ ms
- Slowest operation: [Tool name] at \_\_\_ ms
- Any performance concerns: [Notes]

### Database State After Phase 2

- Completed sessions: [N]
- Sessions deleted: [N]
- Concepts with full stage data (all 4 stages): [N]
- Concepts with Knowledge MCP IDs: [N]

### Data Integrity Checks

- [ ] Stage data persisted correctly for all stages
- [ ] UPSERT behavior works (can update existing stage data)
- [ ] Knowledge MCP IDs stored and retrieved correctly
- [ ] Cascade deletion works (sessions → concepts → stage data)
- [ ] Session completion prevents marking with unstored concepts

### Overall Assessment

⬜ **PASS** - All tests passed, ready for Phase 3
⬜ **PASS WITH ISSUES** - Tests passed but issues noted
⬜ **FAIL** - Critical issues prevent progression to Phase 3

### Recommendations

[Any recommendations for improvements, bug fixes, or documentation updates]

---

## 🎯 Next Steps

If Phase 2 **PASSED**:

- ✅ Proceed to **Phase 3: Research Cache System**
- ✅ You may create a fresh session for Phase 3 if desired

If Phase 2 **FAILED**:

- ⚠️ Document all failures in the test report
- ⚠️ Create GitHub issues for bugs found
- ⚠️ Fix critical issues before proceeding
- ⚠️ Re-run Phase 2 after fixes
