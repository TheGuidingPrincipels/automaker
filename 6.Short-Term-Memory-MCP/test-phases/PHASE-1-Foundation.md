# Test Phase 1: Foundation - Session & Concept Basics

## 📋 Phase Overview

**Goal**: Test the foundational tools that manage daily learning sessions and basic concept operations. These tools form the entry point and core workflow of the Short-Term Memory MCP.

**Tools Tested** (6):

1. `initialize_daily_session` - Create daily learning sessions
2. `get_active_session` - Retrieve session information
3. `store_concepts_from_research` - Bulk store concepts
4. `get_concepts_by_session` - Query concepts with filters
5. `update_concept_status` - Progress concepts through pipeline
6. `get_concepts_by_status` - Filter concepts by status

**Estimated Time**: 45-60 minutes

---

## ✅ Prerequisites

- [ ] Short-Term Memory MCP server is running and connected to Claude Desktop
- [ ] Knowledge MCP server is available (for reference, not required for Phase 1)
- [ ] Fresh database (or willing to work with existing data)
- [ ] Test report template ready
- [ ] This is a new day OR you're willing to test with existing session

---

## 🧪 Test Execution

### Test 1: Initialize Daily Session

**Objective**: Create a new daily learning session with learning and building goals.

#### Steps:

1. **Call the tool** with today's goals:

```
Tool: initialize_daily_session
Parameters:
  learning_goal: "Understanding PostgreSQL indexing strategies and B-tree internals"
  building_goal: "Build a database query performance analyzer CLI tool"
  date: [leave empty or use today's date in YYYY-MM-DD format]
```

2. **Verify the response** contains:
   - `status: "success"` (or "warning" if session exists)
   - `session_id` matching today's date (YYYY-MM-DD)
   - `message` confirming creation
   - `cleaned_old_sessions` count (should be 0 if recent, >0 if old data exists)

3. **Expected behavior**:
   - ✅ New session created with provided goals
   - ✅ Auto-cleanup runs (deletes sessions older than 7 days)
   - ✅ If session already exists for today, returns warning with existing session details

#### Success Criteria:

- [ ] Session created successfully OR warning returned for existing session
- [ ] Session ID matches today's date
- [ ] Cleanup count is reasonable (0-N old sessions)
- [ ] Response time < 2 seconds

#### Record Results:

```
Status: [success/warning/error]
Session ID: [YYYY-MM-DD]
Cleaned sessions: [N]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 2: Get Active Session

**Objective**: Retrieve today's session information with concept statistics.

#### Steps:

1. **Call the tool** without parameters (defaults to today):

```
Tool: get_active_session
Parameters:
  date: [leave empty]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `session_id` matching today's date
   - `date` in YYYY-MM-DD format
   - `learning_goal` and `building_goal` matching what you set in Test 1
   - `session_status: "in_progress"`
   - `concept_count: 0` (no concepts added yet)
   - `concepts_by_status: {}` (empty object)

3. **Test with non-existent date**:

```
Tool: get_active_session
Parameters:
  date: "2020-01-01"
```

Expected: `status: "not_found"`

#### Success Criteria:

- [ ] Today's session retrieved successfully
- [ ] All fields present and correct
- [ ] Goals match what was set in Test 1
- [ ] Non-existent date returns "not_found"
- [ ] Response time < 500ms

#### Record Results:

```
Status: [success/not_found]
Concept count: [0]
Session status: [in_progress]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 3: Store Concepts from Research

**Objective**: Bulk store multiple concepts identified during research phase.

#### Steps:

1. **Call the tool** with realistic concepts:

```
Tool: store_concepts_from_research
Parameters:
  session_id: [today's date from Test 1, e.g., "2025-11-12"]
  concepts: [
    {
      "concept_name": "B-tree Index Structure",
      "data": {
        "description": "Balanced tree data structure used in PostgreSQL for indexing",
        "complexity": "intermediate",
        "estimated_time": "30 minutes"
      }
    },
    {
      "concept_name": "Index Scan vs Sequential Scan",
      "data": {
        "description": "Performance comparison between different query execution strategies",
        "complexity": "beginner",
        "estimated_time": "20 minutes"
      }
    },
    {
      "concept_name": "EXPLAIN ANALYZE Command",
      "data": {
        "description": "PostgreSQL command for analyzing query execution plans",
        "complexity": "beginner",
        "estimated_time": "15 minutes"
      }
    },
    {
      "concept_name": "Covering Indexes",
      "data": {
        "description": "Indexes that include all columns needed for a query",
        "complexity": "intermediate",
        "estimated_time": "25 minutes"
      }
    },
    {
      "concept_name": "Index Bloat and Maintenance",
      "data": {
        "description": "Understanding and preventing index fragmentation",
        "complexity": "advanced",
        "estimated_time": "40 minutes"
      }
    }
  ]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `session_id` matching your session
   - `concepts_created: 5`
   - `concept_ids` array with 5 UUIDs

3. **Test error case** - try with invalid session:

```
Tool: store_concepts_from_research
Parameters:
  session_id: "2020-01-01"
  concepts: [{"concept_name": "Test Concept"}]
```

Expected: Error with "SESSION_NOT_FOUND"

#### Success Criteria:

- [ ] 5 concepts created successfully
- [ ] All concept IDs returned
- [ ] Invalid session returns proper error
- [ ] Response time < 1 second for 5 concepts

#### Record Results:

```
Status: [success/error]
Concepts created: [5]
First concept ID: [UUID]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 4: Get Concepts by Session

**Objective**: Query all concepts for a session with optional filtering.

#### Steps:

1. **Retrieve all concepts** (no filter):

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: [leave empty]
  include_stage_data: false
```

2. **Verify the response** contains:
   - `status: "success"`
   - `session_id` matching your session
   - `count: 5`
   - `concepts` array with 5 items
   - Each concept has:
     - `concept_id` (UUID)
     - `concept_name` (matching what you entered)
     - `current_status: "identified"`
     - `identified_at` timestamp
     - `current_data` with your description/complexity/time

3. **Test with status filter**:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: "identified"
  include_stage_data: false
```

Expected: Same 5 concepts (all are status "identified")

4. **Test with invalid status**:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: "invalid_status"
  include_stage_data: false
```

Expected: Error with "INVALID_STATUS"

5. **Test include_stage_data**:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: [leave empty]
  include_stage_data: true
```

Expected: Same results but with `stage_data` object (empty for now)

#### Success Criteria:

- [ ] All 5 concepts retrieved
- [ ] Status filter works correctly
- [ ] Invalid status returns error
- [ ] include_stage_data flag works
- [ ] Response time < 500ms

#### Record Results:

```
Status: [success/error]
Concept count: [5]
All concepts have status "identified": [yes/no]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 5: Update Concept Status

**Objective**: Progress a concept through the pipeline by updating its status.

#### Steps:

1. **Select first concept** from Test 4 results and save its `concept_id`.

2. **Update status from "identified" to "chunked"**:

```
Tool: update_concept_status
Parameters:
  concept_id: [UUID from step 1]
  new_status: "chunked"
  timestamp: [leave empty to use current time]
```

3. **Verify the response** contains:
   - `status: "success"`
   - `concept_id` matching your input
   - `previous_status: "identified"`
   - `new_status: "chunked"`
   - `timestamp` (ISO format)

4. **Verify the update persisted**:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: "chunked"
  include_stage_data: false
```

Expected: 1 concept returned (the one you just updated)

5. **Test progression through all statuses** (use same concept):
   - Update to "encoded": `update_concept_status` with `new_status: "encoded"`
   - Update to "evaluated": `update_concept_status` with `new_status: "evaluated"`
   - Update to "stored": `update_concept_status` with `new_status: "stored"`

6. **Test invalid status**:

```
Tool: update_concept_status
Parameters:
  concept_id: [UUID]
  new_status: "invalid_status"
```

Expected: Error with "INVALID_STATUS"

7. **Test non-existent concept**:

```
Tool: update_concept_status
Parameters:
  concept_id: "00000000-0000-0000-0000-000000000000"
  new_status: "chunked"
```

Expected: Error with "CONCEPT_NOT_FOUND"

#### Success Criteria:

- [ ] Status updated from identified → chunked → encoded → evaluated → stored
- [ ] Each update returns correct previous_status and new_status
- [ ] Updates are persisted (verified with get_concepts_by_session)
- [ ] Invalid status returns error
- [ ] Non-existent concept returns error
- [ ] Each update response time < 500ms

#### Record Results:

```
Status: [success/error]
Status progression: identified → chunked → encoded → evaluated → stored
All transitions successful: [yes/no]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 6: Get Concepts by Status

**Objective**: Filter concepts by a specific status (convenience wrapper).

#### Steps:

1. **Query concepts with status "stored"** (should be 1 from Test 5):

```
Tool: get_concepts_by_status
Parameters:
  session_id: [today's date]
  status: "stored"
```

2. **Verify the response** contains:
   - `status: "success"`
   - `session_id` matching your session
   - `count: 1`
   - `concepts` array with 1 concept (the one you progressed to "stored")

3. **Query concepts with status "identified"** (should be 4 remaining):

```
Tool: get_concepts_by_status
Parameters:
  session_id: [today's date]
  status: "identified"
```

Expected: `count: 4` with 4 concepts

4. **Query concepts with status "chunked"** (should be 0):

```
Tool: get_concepts_by_status
Parameters:
  session_id: [today's date]
  status: "chunked"
```

Expected: `count: 0`, empty concepts array

5. **Test invalid status**:

```
Tool: get_concepts_by_status
Parameters:
  session_id: [today's date]
  status: "invalid_status"
```

Expected: Error with list of valid statuses

#### Success Criteria:

- [ ] Status filtering works correctly
- [ ] Counts match expected values (1 stored, 4 identified, 0 chunked)
- [ ] Empty results handled gracefully
- [ ] Invalid status returns helpful error with valid options
- [ ] Response time < 500ms

#### Record Results:

```
Status: [success/error]
Stored concepts: [1]
Identified concepts: [4]
Chunked concepts: [0]
Response time: [X]ms
Notes: [any observations]
```

---

## 📊 Phase 1 Test Report

**Completion Date**: [YYYY-MM-DD]
**Tester**: [Your Name]
**MCP Server Version**: [Check package.json or git commit]

### Summary

| Test | Tool                         | Status            | Response Time | Notes |
| ---- | ---------------------------- | ----------------- | ------------- | ----- |
| 1    | initialize_daily_session     | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 2    | get_active_session           | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 3    | store_concepts_from_research | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 4    | get_concepts_by_session      | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 5    | update_concept_status        | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 6    | get_concepts_by_status       | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |

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

### Database State After Phase 1

- Sessions in database: [N]
- Concepts in database: [N]
- Concepts by status:
  - identified: [N]
  - chunked: [N]
  - encoded: [N]
  - evaluated: [N]
  - stored: [N]

### Overall Assessment

⬜ **PASS** - All tests passed, ready for Phase 2
⬜ **PASS WITH ISSUES** - Tests passed but issues noted
⬜ **FAIL** - Critical issues prevent progression to Phase 2

### Recommendations

[Any recommendations for improvements, bug fixes, or documentation updates]

---

## 🎯 Next Steps

If Phase 1 **PASSED**:

- ✅ Proceed to **Phase 2: Pipeline Data & Storage**
- ✅ Keep this session data for continuity (Phase 2 builds on Phase 1 data)

If Phase 1 **FAILED**:

- ⚠️ Document all failures in the test report
- ⚠️ Create GitHub issues for bugs found
- ⚠️ Fix critical issues before proceeding
- ⚠️ Re-run Phase 1 after fixes
