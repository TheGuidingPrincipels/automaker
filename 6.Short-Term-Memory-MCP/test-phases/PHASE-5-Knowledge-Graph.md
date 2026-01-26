# Test Phase 5: Knowledge Graph (Questions & Relationships)

## 📋 Phase Overview

**Goal**: Test the knowledge graph features that allow tracking user questions and building relationships between concepts. These tools enable rich interconnected knowledge representation and comprehensive concept views.

**Tools Tested** (4):

1. `add_concept_question` - Add user questions to concepts
2. `get_concept_page` - Comprehensive single-page view of a concept
3. `add_concept_relationship` - Create relationships between concepts
4. `get_related_concepts` - Query concept relationships

**Estimated Time**: 45-60 minutes

---

## ✅ Prerequisites

- [ ] Phase 1 completed (or have an active session with at least 5 concepts)
- [ ] Short-Term Memory MCP server is running
- [ ] Session with multiple concepts available
- [ ] Concept IDs saved from previous phases

---

## 🧪 Test Execution

### Setup: Verify Your Concepts

List your concepts to get their IDs:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: [leave empty]
  include_stage_data: false
```

Save at least 5 concept IDs for testing.

---

### Test 1: Add Concept Questions

**Objective**: Track user questions asked during different pipeline stages.

#### Steps:

1. **Add a RESEARCH stage question**:

```
Tool: add_concept_question
Parameters:
  concept_id: [UUID of first concept]
  question: "What are the performance characteristics of B-tree indexes compared to hash indexes?"
  session_stage: "research"
```

2. **Verify the response** contains:
   - `status: "success"`
   - `concept_id` matching your input
   - `concept_name` (concept's name)
   - `question_added` (the question you just added)
   - `total_questions: 1`
   - `all_questions` array with your question object

3. **Verify question object** includes:
   - `question` (the text)
   - `session_stage: "research"`
   - `asked_at` (timestamp)

4. **Add multiple questions at different stages**:

AIM stage question:

```
Tool: add_concept_question
Parameters:
  concept_id: [same UUID]
  question: "How do I decide between B-tree and GiST indexes for my use case?"
  session_stage: "aim"
```

SHOOT stage question:

```
Tool: add_concept_question
Parameters:
  concept_id: [same UUID]
  question: "Why did my query not use the index I created?"
  session_stage: "shoot"
```

SKIN stage question:

```
Tool: add_concept_question
Parameters:
  concept_id: [same UUID]
  question: "What are the best practices for index maintenance?"
  session_stage: "skin"
```

5. **Verify total_questions increments**:
   - After 4 questions, `total_questions: 4`
   - `all_questions` array should have all 4 questions

6. **Add questions to other concepts** (for relationship testing later):

Concept 2:

```
Tool: add_concept_question
Parameters:
  concept_id: [UUID of second concept]
  question: "How does the query planner decide between index scan and sequential scan?"
  session_stage: "research"
```

Concept 3:

```
Tool: add_concept_question
Parameters:
  concept_id: [UUID of third concept]
  question: "What does EXPLAIN ANALYZE tell me about query performance?"
  session_stage: "aim"
```

7. **Test invalid stage**:

```
Tool: add_concept_question
Parameters:
  concept_id: [UUID]
  question: "Test question"
  session_stage: "invalid_stage"
```

Expected: Error with "INVALID_STAGE" (valid: research, aim, shoot, skin)

8. **Test non-existent concept**:

```
Tool: add_concept_question
Parameters:
  concept_id: "00000000-0000-0000-0000-000000000000"
  question: "Test question"
  session_stage: "research"
```

Expected: Error with "CONCEPT_NOT_FOUND"

9. **Test empty question**:

```
Tool: add_concept_question
Parameters:
  concept_id: [UUID]
  question: ""
  session_stage: "research"
```

Expected: May accept or reject (document behavior)

#### Success Criteria:

- [ ] Questions added successfully to concepts
- [ ] All 4 stages (research, aim, shoot, skin) work
- [ ] total_questions increments correctly
- [ ] all_questions array contains all added questions
- [ ] Timestamps recorded for each question
- [ ] Invalid stage returns error
- [ ] Non-existent concept returns error
- [ ] Response time < 500ms

#### Record Results:

```
Questions added: [6+]
Stages tested: [research, aim, shoot, skin]
Total questions on concept 1: [4]
Invalid stage handling: [correct/incorrect]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 2: Get Concept Page (Comprehensive View)

**Objective**: Retrieve a complete single-page view of a concept with all data.

#### Steps:

1. **Get comprehensive view** of concept with questions:

```
Tool: get_concept_page
Parameters:
  concept_id: [UUID of first concept with 4 questions]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `concept_id` and `concept_name`
   - `session_id`
   - `current_status` (e.g., "identified", "chunked", etc.)
   - `knowledge_mcp_id` (may be null if not stored yet)
   - `timeline` array (all status transitions with timestamps)
   - `stage_data` object (data from research/aim/shoot/skin stages, if exists)
   - `user_questions` array (should have 4 questions)
   - `relationships` array (empty for now)
   - `current_data` (concept's data)
   - `created_at` and `updated_at` timestamps

3. **Verify timeline** includes:
   - Each status transition as a separate entry
   - Status name (identified, chunked, etc.)
   - Timestamp for each transition
   - Chronological order

4. **Verify stage_data** (if you added stage data in Phase 2):
   - `research`, `aim`, `shoot`, `skin` keys (if data exists)
   - Each contains the data stored for that stage

5. **Verify user_questions** includes:
   - All 4 questions added in Test 1
   - Each question has `question`, `session_stage`, `asked_at`

6. **Test with concept that has stage data** (from Phase 2):
   - Get concept page for concept with all 4 stages populated
   - Verify stage_data includes all stages

7. **Test with concept that has no questions**:

```
Tool: get_concept_page
Parameters:
  concept_id: [UUID of concept without questions]
```

Expected: `user_questions: []` (empty array)

8. **Test with concept that has Knowledge MCP ID** (if you completed Phase 2):
   - Should show `knowledge_mcp_id` populated
   - Should show `current_status: "stored"`

9. **Test non-existent concept**:

```
Tool: get_concept_page
Parameters:
  concept_id: "00000000-0000-0000-0000-000000000000"
```

Expected: Error with "CONCEPT_NOT_FOUND"

#### Success Criteria:

- [ ] Complete concept view returned
- [ ] Timeline shows all status transitions
- [ ] Stage data included (if exists)
- [ ] All user questions included
- [ ] Relationships included (empty for now)
- [ ] Knowledge MCP ID shown (if exists)
- [ ] Empty arrays handled gracefully (no questions, no relationships)
- [ ] Non-existent concept returns error
- [ ] Response time < 1 second

#### Record Results:

```
Complete view retrieved: [yes/no]
Timeline entries: [N]
Stage data keys: [research, aim, shoot, skin or subset]
User questions: [4 for concept 1]
Relationships: [0 - empty for now]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 3: Add Concept Relationships

**Objective**: Create relationships between concepts to build a knowledge graph.

#### Steps:

1. **Add a PREREQUISITE relationship**:

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID of "B-tree Index Structure"]
  related_concept_id: [UUID of "EXPLAIN ANALYZE Command"]
  relationship_type: "prerequisite"
```

2. **Verify the response** contains:
   - `status: "success"`
   - `concept_id` and `concept_name` (source concept)
   - `related_to` object with:
     - `concept_id` (target)
     - `concept_name` (target)
     - `relationship_type: "prerequisite"`
   - `total_relationships: 1`

3. **Add RELATED relationship**:

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID of "B-tree Index Structure"]
  related_concept_id: [UUID of "Index Scan vs Sequential Scan"]
  relationship_type: "related"
```

Expected: `total_relationships: 2`

4. **Add SIMILAR relationship**:

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID of "B-tree Index Structure"]
  related_concept_id: [UUID of "Covering Indexes"]
  relationship_type: "similar"
```

Expected: `total_relationships: 3`

5. **Add BUILDS_ON relationship**:

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID of "Covering Indexes"]
  related_concept_id: [UUID of "B-tree Index Structure"]
  relationship_type: "builds_on"
```

Expected: Success (note: reverse relationship from earlier)

6. **Create relationship web** (add more relationships):

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID of "Index Scan vs Sequential Scan"]
  related_concept_id: [UUID of "EXPLAIN ANALYZE Command"]
  relationship_type: "related"
```

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID of "Index Bloat and Maintenance"]
  related_concept_id: [UUID of "B-tree Index Structure"]
  relationship_type: "related"
```

7. **Test duplicate relationship**:

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID of "B-tree Index Structure"]
  related_concept_id: [UUID of "EXPLAIN ANALYZE Command"]
  relationship_type: "prerequisite"
```

Expected: `status: "warning"` with message about existing relationship

8. **Test self-referential relationship** (concept to itself):

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID of concept]
  related_concept_id: [same UUID]
  relationship_type: "related"
```

Expected: Error with "SELF_REFERENTIAL_RELATIONSHIP"

9. **Test invalid relationship type**:

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID]
  related_concept_id: [UUID]
  relationship_type: "invalid_type"
```

Expected: Error with "INVALID_RELATIONSHIP_TYPE" and list of valid types

10. **Test non-existent concept**:

```
Tool: add_concept_relationship
Parameters:
  concept_id: "00000000-0000-0000-0000-000000000000"
  related_concept_id: [valid UUID]
  relationship_type: "related"
```

Expected: Error with "CONCEPT_NOT_FOUND"

11. **Test non-existent related concept**:

```
Tool: add_concept_relationship
Parameters:
  concept_id: [valid UUID]
  related_concept_id: "00000000-0000-0000-0000-000000000000"
  relationship_type: "related"
```

Expected: Error with "RELATED_CONCEPT_NOT_FOUND"

#### Success Criteria:

- [ ] All 4 relationship types work (prerequisite, related, similar, builds_on)
- [ ] total_relationships increments correctly
- [ ] Duplicate relationship returns warning
- [ ] Self-referential relationship rejected
- [ ] Invalid relationship type rejected with helpful error
- [ ] Non-existent concepts rejected
- [ ] Response time < 500ms

#### Record Results:

```
Relationships created: [6+]
Types tested: [prerequisite, related, similar, builds_on]
Duplicate handling: [warning returned: yes/no]
Self-referential rejection: [yes/no]
Invalid type rejection: [yes/no]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 4: Get Related Concepts

**Objective**: Query and traverse concept relationships.

#### Steps:

1. **Get all relationships** for concept with multiple relationships:

```
Tool: get_related_concepts
Parameters:
  concept_id: [UUID of "B-tree Index Structure" - should have 3+ relationships]
  relationship_type: [leave empty]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `concept_id` and `concept_name` (source concept)
   - `relationship_filter: null` (no filter applied)
   - `related_count: 3` (or your count)
   - `related_concepts` array with relationship details

3. **Verify each related concept** includes:
   - `concept_id` (target concept)
   - `concept_name` (target concept)
   - `relationship_type`
   - `current_status` (enriched with target concept's status)
   - `current_data` (enriched with target concept's data)

4. **Filter by PREREQUISITE type**:

```
Tool: get_related_concepts
Parameters:
  concept_id: [UUID of "B-tree Index Structure"]
  relationship_type: "prerequisite"
```

Expected:

- `related_count: 1`
- `relationship_filter: "prerequisite"`
- Only "EXPLAIN ANALYZE Command" in results

5. **Filter by RELATED type**:

```
Tool: get_related_concepts
Parameters:
  concept_id: [UUID of "B-tree Index Structure"]
  relationship_type: "related"
```

Expected: Only "related" type relationships

6. **Filter by SIMILAR type**:

```
Tool: get_related_concepts
Parameters:
  concept_id: [UUID of "B-tree Index Structure"]
  relationship_type: "similar"
```

Expected: Only "similar" type relationships

7. **Filter by BUILDS_ON type**:

```
Tool: get_related_concepts
Parameters:
  concept_id: [UUID of "Covering Indexes"]
  relationship_type: "builds_on"
```

Expected: "B-tree Index Structure" (from Test 3 step 5)

8. **Test concept with no relationships**:

```
Tool: get_related_concepts
Parameters:
  concept_id: [UUID of concept with no relationships]
  relationship_type: [leave empty]
```

Expected: `related_count: 0`, empty `related_concepts` array

9. **Test invalid relationship type filter**:

```
Tool: get_related_concepts
Parameters:
  concept_id: [UUID]
  relationship_type: "invalid_type"
```

Expected: Error with "INVALID_RELATIONSHIP_TYPE"

10. **Test non-existent concept**:

```
Tool: get_related_concepts
Parameters:
  concept_id: "00000000-0000-0000-0000-000000000000"
  relationship_type: [leave empty]
```

Expected: Error with "CONCEPT_NOT_FOUND"

11. **Verify relationships appear in concept page**:

```
Tool: get_concept_page
Parameters:
  concept_id: [UUID of "B-tree Index Structure"]
```

Expected: `relationships` array now populated with all relationships

#### Success Criteria:

- [ ] All relationships retrieved without filter
- [ ] Filtering by type works for all 4 types
- [ ] Related concepts enriched with current_status and current_data
- [ ] Empty relationships handled gracefully
- [ ] Invalid type filter rejected
- [ ] Non-existent concept rejected
- [ ] Relationships appear in get_concept_page
- [ ] Response time < 500ms

#### Record Results:

```
All relationships retrieved: [yes/no]
Filtering works: [yes/no - all 4 types]
Enrichment (status/data): [yes/no]
Empty relationships: [handled correctly: yes/no]
Relationships in concept page: [yes/no]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 5: Knowledge Graph Verification

**Objective**: Verify the complete knowledge graph is built correctly.

#### Steps:

1. **Visualize the graph** (mentally or on paper):
   - Draw your concepts as nodes
   - Draw relationships as directed edges
   - Label edges with relationship types

Example structure:

```
"B-tree Index Structure"
  --[prerequisite]--> "EXPLAIN ANALYZE Command"
  --[related]--> "Index Scan vs Sequential Scan"
  --[similar]--> "Covering Indexes"

"Covering Indexes"
  --[builds_on]--> "B-tree Index Structure"

"Index Bloat and Maintenance"
  --[related]--> "B-tree Index Structure"

"Index Scan vs Sequential Scan"
  --[related]--> "EXPLAIN ANALYZE Command"
```

2. **Test bidirectional traversal**:
   - Get relationships FROM "B-tree Index Structure" → should show outgoing edges
   - Get relationships FROM "Covering Indexes" → should show "builds_on" to B-tree

3. **Test multi-hop traversal** (manually for now):
   - Get related concepts of "Covering Indexes" → get "B-tree Index Structure"
   - Get related concepts of "B-tree Index Structure" → get "EXPLAIN ANALYZE Command"
   - This creates path: Covering Indexes → B-tree → EXPLAIN ANALYZE (2 hops)

4. **Count total relationships in session**:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [today's date]
  status_filter: [leave empty]
  include_stage_data: false
```

For each concept, check if it has relationships in current_data.

5. **Verify relationship data persistence**:
   - Relationships are stored in `current_data` field
   - Each concept stores its outgoing relationships
   - Retrieve with `get_concept_page` to verify

6. **Test cache invalidation** (if using Code Teacher tools):

```
Tool: add_concept_relationship
Parameters:
  concept_id: [UUID]
  related_concept_id: [UUID]
  relationship_type: "related"
```

Then:

```
Tool: get_todays_concepts
Parameters: [none]
```

Expected: Cache should be invalidated (cache_hit: false) and concept data updated

#### Success Criteria:

- [ ] Knowledge graph is connected (concepts have relationships)
- [ ] Bidirectional traversal works (can navigate in both directions)
- [ ] Relationships persisted in current_data
- [ ] get_concept_page shows complete graph view
- [ ] Cache invalidation works for relationship changes

#### Record Results:

```
Total concepts in graph: [N]
Total relationships: [N]
Graph connectivity: [connected/disconnected/multiple components]
Bidirectional traversal: [works/doesn't work]
Cache invalidation: [works/doesn't work]
Notes: [any observations about graph structure]
```

---

## 📊 Phase 5 Test Report

**Completion Date**: [YYYY-MM-DD]
**Tester**: [Your Name]
**MCP Server Version**: [Check package.json or git commit]

### Summary

| Test | Tool                         | Status            | Response Time | Notes |
| ---- | ---------------------------- | ----------------- | ------------- | ----- |
| 1    | add_concept_question         | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 2    | get_concept_page             | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 3    | add_concept_relationship     | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 4    | get_related_concepts         | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 5    | Knowledge graph verification | ⬜ Pass / ⬜ Fail | -             |       |

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
- get_concept_page with full data: \_\_\_ ms
- Any performance concerns: [Notes]

### Knowledge Graph State After Phase 5

**User Questions**:

- Total questions added: [N]
- Concepts with questions: [N]
- Questions by stage:
  - research: [N]
  - aim: [N]
  - shoot: [N]
  - skin: [N]

**Relationships**:

- Total relationships: [N]
- Relationship types used:
  - prerequisite: [N]
  - related: [N]
  - similar: [N]
  - builds_on: [N]
- Concepts with relationships: [N]
- Graph connectivity: [connected/disconnected]

### Functional Checks

- [ ] Questions added to concepts successfully
- [ ] Questions tracked by pipeline stage
- [ ] Complete concept page view includes all data
- [ ] Timeline shows status progression
- [ ] All 4 relationship types work
- [ ] Relationship enrichment (status/data) works
- [ ] Filtering by relationship type works
- [ ] Duplicate relationships prevented/warned
- [ ] Self-referential relationships rejected
- [ ] Relationships appear in concept page
- [ ] Cache invalidation on relationship changes

### Data Integrity Checks

- [ ] Questions persisted in user_questions array
- [ ] Relationships persisted in current_data
- [ ] No data loss on updates
- [ ] Timestamps recorded correctly
- [ ] Enriched data accurate (status/data from related concepts)

### Overall Assessment

⬜ **PASS** - All tests passed, ready for Phase 6
⬜ **PASS WITH ISSUES** - Tests passed but issues noted
⬜ **FAIL** - Critical issues prevent progression to Phase 6

### Recommendations

[Any recommendations for improvements, bug fixes, or documentation updates]

---

## 🎯 Next Steps

If Phase 5 **PASSED**:

- ✅ Proceed to **Phase 6: Monitoring & System Health**
- ✅ Knowledge graph features are working correctly

If Phase 5 **FAILED**:

- ⚠️ Document all failures in the test report
- ⚠️ Create GitHub issues for bugs found
- ⚠️ Fix critical issues before proceeding
- ⚠️ Re-run Phase 5 after fixes

---

## 💡 Knowledge Graph Best Practices

Based on these tests, here are best practices:

1. **Use relationship types appropriately**:
   - **prerequisite**: Concept A must be understood before B
   - **related**: Concepts are related but not dependent
   - **similar**: Concepts are similar or alternative approaches
   - **builds_on**: Concept B extends/builds upon concept A

2. **Track questions during learning**:
   - Add questions as they arise during each stage
   - Questions help identify knowledge gaps
   - Questions can guide future learning

3. **Build rich connections**:
   - Link related concepts to build knowledge graph
   - Use get_concept_page for comprehensive concept view
   - Traverse relationships to understand dependencies

4. **Leverage enriched data**:
   - get_related_concepts provides current status of related concepts
   - Use this to understand which related concepts are ready
   - Plan learning path based on relationship graph
