# Test Phase 2: Search & Discovery

## Overview

This phase tests the search and discovery capabilities of the MCP Knowledge Server, including semantic search (AI-powered vector similarity), exact/filtered search, and time-based retrieval.

**Total Tools in Phase**: 3
**Estimated Time**: 30-45 minutes
**Dependencies**: Phase 1 must be completed (concepts must exist for searching)

---

## Pre-Test Requirements

### System Checklist

- [ ] Phase 1 completed successfully
- [ ] At least 3-5 concepts exist in the knowledge base
- [ ] Neo4j is running
- [ ] ChromaDB is running
- [ ] Embedding service is operational
- [ ] MCP server is running

### Required Data from Phase 1

You'll need these concept IDs from Phase 1:

- BASIC_CONCEPT_ID: ********\_\_\_********
- CATEGORIZED_CONCEPT_ID: ********\_\_\_********
- SOURCED_CONCEPT_ID: ********\_\_\_********

### Pre-Test Setup

Create additional test concepts for search testing:

**Setup Concept 1**: Machine Learning

```
name: "Machine Learning"
explanation: "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed."
area: "Computer Science"
topic: "Artificial Intelligence"
subtopic: "Learning Algorithms"
```

**Setup Concept 2**: Neural Networks

```
name: "Neural Networks"
explanation: "Neural networks are computing systems inspired by biological neural networks that constitute animal brains, used for pattern recognition and machine learning tasks."
area: "Computer Science"
topic: "Artificial Intelligence"
subtopic: "Deep Learning"
```

**Setup Concept 3**: Data Structures

```
name: "Data Structures"
explanation: "Data structures are specialized formats for organizing, processing, retrieving and storing data in computer science."
area: "Computer Science"
topic: "Fundamentals"
subtopic: "Core Concepts"
```

---

## Test Execution Instructions

**IMPORTANT**: Test ONE tool at a time. After completing all tests for a tool:

1. Document results in the Test Results section
2. Take a break
3. Notify test coordinator
4. Wait for go-ahead before proceeding to next tool

---

## Tool 1: `search_concepts_semantic`

### Purpose

Semantic search using ChromaDB embeddings and cosine similarity for natural language queries.

### Tool Specification

- **Input Parameters**:
  - `query` (required): string (natural language search query)
  - `limit` (optional): int, 1-50, default=10
  - `min_certainty` (optional): float, 0-100
  - `area` (optional): string (filter by area)
  - `topic` (optional): string (filter by topic)
- **Expected Output**:
  ```json
  {
    "success": true,
    "results": [
      {
        "concept_id": "<UUID>",
        "name": "...",
        "similarity": 0.8745,
        "area": "...",
        "topic": "...",
        "certainty_score": 85.0
      }
    ],
    "total": 10,
    "message": "..."
  }
  ```

### Test Cases

#### Test 1.1: Basic Semantic Search

**Description**: Search with simple natural language query
**Action**: Search for AI-related concepts
**Expected Result**: Returns relevant concepts ranked by similarity

**Test Data**:

```
query: "artificial intelligence and machine learning"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic` with above query
2. Verify success = true
3. Verify results array is not empty
4. Check that results contain AI-related concepts
5. Verify similarity scores are between 0-1
6. Verify results sorted by similarity (highest first)

**Pass/Fail Criteria**:

- ✅ PASS: Returns relevant results with valid similarity scores
- ❌ FAIL: No results, wrong results, or invalid scores

---

#### Test 1.2: Semantic Search with Limit

**Description**: Test limit parameter
**Action**: Search with limit=3
**Expected Result**: Returns exactly 3 results

**Test Data**:

```
query: "programming languages"
limit: 3
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic` with limit=3
2. Verify results array length <= 3
3. Verify total reflects actual count

**Pass/Fail Criteria**:

- ✅ PASS: Returns at most 3 results
- ❌ FAIL: Returns more than 3 results

---

#### Test 1.3: Semantic Search with Area Filter

**Description**: Combine semantic search with metadata filter
**Action**: Search within specific area
**Expected Result**: Only results from specified area

**Test Data**:

```
query: "learning algorithms"
area: "Computer Science"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic` with area filter
2. Verify all results have area = "Computer Science"
3. Verify results are still ranked by similarity

**Pass/Fail Criteria**:

- ✅ PASS: All results match area filter and ranked by similarity
- ❌ FAIL: Results from other areas or not ranked properly

---

#### Test 1.4: Semantic Search with Topic Filter

**Description**: Filter by topic
**Action**: Search within specific topic
**Expected Result**: Only results from specified topic

**Test Data**:

```
query: "neural"
area: "Computer Science"
topic: "Artificial Intelligence"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic` with area+topic filter
2. Verify all results match both filters
3. Verify "Neural Networks" concept appears (if created in setup)

**Pass/Fail Criteria**:

- ✅ PASS: All results match filters
- ❌ FAIL: Results violate filters

---

#### Test 1.5: Semantic Search with Certainty Filter

**Description**: Filter by minimum certainty score
**Action**: Search with min_certainty threshold
**Expected Result**: Only results above threshold

**Test Data**:

```
query: "computer science"
min_certainty: 50.0
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic` with min_certainty=50
2. Verify all results have certainty_score >= 50.0
3. Verify results still ranked by similarity (not certainty)

**Pass/Fail Criteria**:

- ✅ PASS: All results meet certainty threshold
- ❌ FAIL: Results below threshold included

---

#### Test 1.6: Semantic Search - No Results

**Description**: Search for non-existent topic
**Action**: Search with query unlikely to match
**Expected Result**: Empty results, graceful response

**Test Data**:

```
query: "quantum entanglement in underwater basket weaving"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic` with obscure query
2. Verify success = true (even if no results)
3. Verify results array is empty
4. Verify total = 0
5. Verify message is informative

**Pass/Fail Criteria**:

- ✅ PASS: Graceful response with empty results
- ❌ FAIL: Error or crash

---

#### Test 1.7: Semantic Search - Invalid Limit (Auto-Adjust)

**Description**: Test parameter validation with out-of-range limit
**Action**: Use limit > 50
**Expected Result**: Auto-adjusted to 50 with warning

**Test Data**:

```
query: "test"
limit: 100
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic` with limit=100
2. Verify results count <= 50
3. Check for warning in response about limit adjustment

**Pass/Fail Criteria**:

- ✅ PASS: Limit auto-adjusted, warning present
- ❌ FAIL: Error or returns >50 results

---

#### Test 1.8: Semantic Search - Similarity Score Verification

**Description**: Verify similarity scores are valid and ordered
**Action**: Search and check score validity
**Expected Result**: All scores 0-1, descending order

**Test Data**:

```
query: "machine learning concepts"
limit: 5
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic`
2. For each result, verify similarity is float
3. Verify all similarities between 0.0-1.0
4. Verify results ordered by similarity DESC
5. Verify similarity decreases or stays same down the list

**Pass/Fail Criteria**:

- ✅ PASS: Valid scores in descending order
- ❌ FAIL: Invalid scores or wrong order

---

#### Test 1.9: Semantic Search - Query Variations

**Description**: Test semantic understanding with paraphrased queries
**Action**: Search similar concepts with different wording
**Expected Result**: Similar results for semantically similar queries

**Test Queries** (run separately):

```
query1: "AI and deep learning"
query2: "artificial intelligence and neural networks"
query3: "machine learning algorithms"
```

**Test Steps**:

1. Run all three queries
2. Compare top results
3. Verify overlap in returned concepts
4. Verify semantic similarity works (not just keyword matching)

**Pass/Fail Criteria**:

- ✅ PASS: Semantically similar queries return overlapping results
- ❌ FAIL: Completely different results for similar queries

---

#### Test 1.10: Semantic Search - Empty Query

**Description**: Test validation with empty query
**Action**: Search with empty string
**Expected Result**: Error or all results

**Test Data**:

```
query: ""
```

**Test Steps**:

1. Use MCP tool: `search_concepts_semantic` with empty query
2. Check response (may be error or return all concepts)

**Pass/Fail Criteria**:

- ✅ PASS: Handles gracefully (error or returns results)
- ❌ FAIL: Crashes

---

### Test Results for Tool 1

| Test Case             | Status | Notes | Timestamp |
| --------------------- | ------ | ----- | --------- |
| 1.1 Basic Search      |        |       |           |
| 1.2 With Limit        |        |       |           |
| 1.3 Area Filter       |        |       |           |
| 1.4 Topic Filter      |        |       |           |
| 1.5 Certainty Filter  |        |       |           |
| 1.6 No Results        |        |       |           |
| 1.7 Invalid Limit     |        |       |           |
| 1.8 Similarity Scores |        |       |           |
| 1.9 Query Variations  |        |       |           |
| 1.10 Empty Query      |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 2: `search_concepts_exact`

### Purpose

Exact/filtered search using Neo4j Cypher queries with traditional database filtering.

### Tool Specification

- **Input Parameters**:
  - `name` (optional): string (case-insensitive partial match)
  - `area` (optional): string (exact match)
  - `topic` (optional): string (exact match)
  - `subtopic` (optional): string (exact match)
  - `min_certainty` (optional): float, 0-100
  - `limit` (optional): int, 1-100, default=20
- **Expected Output**:
  ```json
  {
    "success": true,
    "results": [
      {
        "concept_id": "<UUID>",
        "name": "...",
        "area": "...",
        "topic": "...",
        "subtopic": "...",
        "certainty_score": 85.0,
        "created_at": "<ISO datetime>"
      }
    ],
    "total": 5,
    "message": "..."
  }
  ```

### Test Cases

#### Test 2.1: Search by Name (Partial Match)

**Description**: Search by partial name match
**Action**: Search for concepts with "learning" in name
**Expected Result**: All concepts with "learning" in name

**Test Data**:

```
name: "learning"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with name="learning"
2. Verify success = true
3. Verify all results contain "learning" in name (case-insensitive)
4. Verify results sorted by certainty DESC, then created_at DESC

**Pass/Fail Criteria**:

- ✅ PASS: All results match name filter
- ❌ FAIL: Results missing "learning" or wrong sort order

---

#### Test 2.2: Search by Area (Exact Match)

**Description**: Filter by exact area
**Action**: Get all concepts in "Computer Science" area
**Expected Result**: Only Computer Science concepts

**Test Data**:

```
area: "Computer Science"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with area
2. Verify all results have area = "Computer Science" (exact)
3. Verify results sorted by certainty and date

**Pass/Fail Criteria**:

- ✅ PASS: All results match area exactly
- ❌ FAIL: Results from other areas

---

#### Test 2.3: Search by Topic (Exact Match)

**Description**: Filter by exact topic
**Action**: Get all "Artificial Intelligence" topic concepts
**Expected Result**: Only AI topic concepts

**Test Data**:

```
area: "Computer Science"
topic: "Artificial Intelligence"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with area+topic
2. Verify all results match both filters exactly
3. Should include "Machine Learning" and "Neural Networks" from setup

**Pass/Fail Criteria**:

- ✅ PASS: All results match both filters
- ❌ FAIL: Results violate filters

---

#### Test 2.4: Search by Subtopic

**Description**: Filter by subtopic
**Action**: Get concepts in specific subtopic
**Expected Result**: Only matching subtopic

**Test Data**:

```
area: "Computer Science"
topic: "Artificial Intelligence"
subtopic: "Deep Learning"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with all three hierarchy levels
2. Verify exact matches on all three fields
3. Should find "Neural Networks" concept from setup

**Pass/Fail Criteria**:

- ✅ PASS: Results match all three hierarchy levels
- ❌ FAIL: Wrong results or missing expected concept

---

#### Test 2.5: Combined Name + Area Search

**Description**: Combine name partial match with area exact match
**Action**: Search name within specific area
**Expected Result**: Results match both filters

**Test Data**:

```
name: "data"
area: "Computer Science"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with name+area
2. Verify all results contain "data" in name
3. Verify all results have area = "Computer Science"

**Pass/Fail Criteria**:

- ✅ PASS: All results match both filters
- ❌ FAIL: Results violate either filter

---

#### Test 2.6: Search with min_certainty Filter

**Description**: Filter by minimum certainty score
**Action**: Get only high-certainty concepts
**Expected Result**: Only concepts above threshold

**Test Data**:

```
min_certainty: 70.0
limit: 10
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with min_certainty
2. Verify all results have certainty_score >= 70.0
3. Verify results sorted by certainty DESC

**Pass/Fail Criteria**:

- ✅ PASS: All results >= 70 certainty
- ❌ FAIL: Results below threshold

---

#### Test 2.7: Search with Limit

**Description**: Test result limiting
**Action**: Search with small limit
**Expected Result**: Respects limit

**Test Data**:

```
area: "Computer Science"
limit: 2
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with limit=2
2. Verify results array length <= 2
3. Verify highest certainty concepts returned first

**Pass/Fail Criteria**:

- ✅ PASS: At most 2 results, highest quality first
- ❌ FAIL: More than 2 results

---

#### Test 2.8: Search with All Filters Combined

**Description**: Test all filter parameters together
**Action**: Use name, area, topic, min_certainty, limit
**Expected Result**: All filters applied correctly

**Test Data**:

```
name: "neural"
area: "Computer Science"
topic: "Artificial Intelligence"
min_certainty: 0
limit: 5
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with all parameters
2. Verify all filters respected
3. Verify sort order correct

**Pass/Fail Criteria**:

- ✅ PASS: All filters work together
- ❌ FAIL: Any filter not applied

---

#### Test 2.9: Search - No Results

**Description**: Search with filters that match nothing
**Action**: Search for non-existent combination
**Expected Result**: Empty results, graceful response

**Test Data**:

```
name: "NONEXISTENT_CONCEPT_XYZ"
area: "Computer Science"
```

**Test Steps**:

1. Use MCP tool: `search_concepts_exact` with non-matching filters
2. Verify success = true
3. Verify results array is empty
4. Verify total = 0

**Pass/Fail Criteria**:

- ✅ PASS: Graceful empty response
- ❌ FAIL: Error or crash

---

#### Test 2.10: Case Insensitivity Verification

**Description**: Verify name search is case-insensitive
**Action**: Search with different case variations
**Expected Result**: Same results regardless of case

**Test Data** (run separately):

```
name: "MACHINE"
name: "machine"
name: "MaChInE"
```

**Test Steps**:

1. Run search with each case variation
2. Verify all return same results
3. Verify "Machine Learning" concept found in all

**Pass/Fail Criteria**:

- ✅ PASS: Case-insensitive matching works
- ❌ FAIL: Different results for different cases

---

### Test Results for Tool 2

| Test Case             | Status | Notes | Timestamp |
| --------------------- | ------ | ----- | --------- |
| 2.1 By Name           |        |       |           |
| 2.2 By Area           |        |       |           |
| 2.3 By Topic          |        |       |           |
| 2.4 By Subtopic       |        |       |           |
| 2.5 Name + Area       |        |       |           |
| 2.6 min_certainty     |        |       |           |
| 2.7 With Limit        |        |       |           |
| 2.8 All Filters       |        |       |           |
| 2.9 No Results        |        |       |           |
| 2.10 Case Insensitive |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 3: `get_recent_concepts`

### Purpose

Get recently created or modified concepts based on time window.

### Tool Specification

- **Input Parameters**:
  - `days` (optional): int, 1-365, default=7
  - `limit` (optional): int, 1-100, default=20
- **Expected Output**:
  ```json
  {
    "success": true,
    "results": [
      {
        "concept_id": "<UUID>",
        "name": "...",
        "area": "...",
        "topic": "...",
        "subtopic": "...",
        "certainty_score": 85.0,
        "created_at": "<ISO datetime>",
        "last_modified": "<ISO datetime>"
      }
    ],
    "total": 5,
    "message": "...",
    "warnings": []
  }
  ```

### Test Cases

#### Test 3.1: Recent Concepts - Default (7 Days)

**Description**: Get concepts from last week
**Action**: Call with no parameters
**Expected Result**: Concepts from last 7 days

**Test Data**: No parameters (use defaults)

**Test Steps**:

1. Use MCP tool: `get_recent_concepts` with no parameters
2. Verify success = true
3. Verify all results have last_modified within last 7 days
4. Verify sorted by last_modified DESC (newest first)
5. Verify limit = 20 (default)

**Pass/Fail Criteria**:

- ✅ PASS: Returns recent concepts, sorted correctly
- ❌ FAIL: Old concepts or wrong sort order

---

#### Test 3.2: Recent Concepts - Last 24 Hours

**Description**: Get very recent concepts
**Action**: Get concepts from last day
**Expected Result**: Only today's concepts

**Test Data**:

```
days: 1
```

**Test Steps**:

1. Use MCP tool: `get_recent_concepts` with days=1
2. Verify all results from last 24 hours
3. Should include concepts from Phase 1 and Phase 2 setup

**Pass/Fail Criteria**:

- ✅ PASS: Only concepts from last 24 hours
- ❌ FAIL: Older concepts included

---

#### Test 3.3: Recent Concepts - Large Time Window

**Description**: Get concepts from longer period
**Action**: Get concepts from last 30 days
**Expected Result**: All concepts from last month

**Test Data**:

```
days: 30
```

**Test Steps**:

1. Use MCP tool: `get_recent_concepts` with days=30
2. Verify results span up to 30 days
3. Verify sorted by last_modified DESC

**Pass/Fail Criteria**:

- ✅ PASS: Appropriate time window, correct sort
- ❌ FAIL: Wrong time window or sort

---

#### Test 3.4: Recent Concepts with Limit

**Description**: Test limit parameter
**Action**: Get recent concepts with small limit
**Expected Result**: Respects limit

**Test Data**:

```
days: 7
limit: 3
```

**Test Steps**:

1. Use MCP tool: `get_recent_concepts` with limit=3
2. Verify results array length <= 3
3. Verify most recently modified concepts returned

**Pass/Fail Criteria**:

- ✅ PASS: At most 3 results, newest first
- ❌ FAIL: More than 3 results

---

#### Test 3.5: Recently Modified vs Created

**Description**: Verify last_modified is used (not created_at)
**Action**: Update a concept then get recent
**Expected Result**: Updated concept appears

**Test Steps**:

1. Update one of the setup concepts with new explanation
2. Wait a moment
3. Use MCP tool: `get_recent_concepts` with days=1
4. Verify updated concept is in results
5. Verify last_modified > created_at for that concept

**Pass/Fail Criteria**:

- ✅ PASS: Updated concept appears based on last_modified
- ❌ FAIL: Updated concept missing or wrong timestamp used

---

#### Test 3.6: Invalid Days - Too Small

**Description**: Test parameter validation with days=0
**Action**: Use days below minimum
**Expected Result**: Auto-adjusted to 1 with warning

**Test Data**:

```
days: 0
```

**Test Steps**:

1. Use MCP tool: `get_recent_concepts` with days=0
2. Check for warning about adjustment
3. Verify results use days=1

**Pass/Fail Criteria**:

- ✅ PASS: Auto-adjusted with warning
- ❌ FAIL: Error or accepts invalid value

---

#### Test 3.7: Invalid Days - Too Large

**Description**: Test parameter validation with days>365
**Action**: Use days above maximum
**Expected Result**: Auto-adjusted to 365 with warning

**Test Data**:

```
days: 500
```

**Test Steps**:

1. Use MCP tool: `get_recent_concepts` with days=500
2. Check for warning about adjustment
3. Verify results use days=365

**Pass/Fail Criteria**:

- ✅ PASS: Auto-adjusted to 365 with warning
- ❌ FAIL: Error or uses invalid value

---

#### Test 3.8: Invalid Limit - Out of Range

**Description**: Test limit validation
**Action**: Use limit > 100
**Expected Result**: Auto-adjusted to 100

**Test Data**:

```
days: 7
limit: 150
```

**Test Steps**:

1. Use MCP tool: `get_recent_concepts` with limit=150
2. Verify warning about limit adjustment
3. Verify results count <= 100

**Pass/Fail Criteria**:

- ✅ PASS: Auto-adjusted with warning
- ❌ FAIL: Returns >100 results

---

#### Test 3.9: No Recent Concepts

**Description**: Test when no concepts in time window
**Action**: Use very short time window with no recent activity
**Expected Result**: Empty results, graceful response

**Note**: This test may be hard to achieve if testing immediately after creation.
Skip if all test concepts are recent.

**Test Steps**:

1. If possible, use a time window with no concepts
2. Verify graceful empty response

**Pass/Fail Criteria**:

- ✅ PASS: Graceful empty response
- ❌ FAIL: Error

---

#### Test 3.10: Sort Order Verification

**Description**: Verify results are sorted by last_modified DESC
**Action**: Get recent concepts and verify sort
**Expected Result**: Descending order by last_modified

**Test Data**:

```
days: 7
limit: 10
```

**Test Steps**:

1. Use MCP tool: `get_recent_concepts`
2. Extract last_modified timestamps from all results
3. Verify each timestamp <= previous timestamp (descending)
4. Verify most recently modified is first

**Pass/Fail Criteria**:

- ✅ PASS: Perfect descending order
- ❌ FAIL: Out of order results

---

### Test Results for Tool 3

| Test Case               | Status | Notes | Timestamp |
| ----------------------- | ------ | ----- | --------- |
| 3.1 Default 7 Days      |        |       |           |
| 3.2 Last 24 Hours       |        |       |           |
| 3.3 Large Window        |        |       |           |
| 3.4 With Limit          |        |       |           |
| 3.5 Modified vs Created |        |       |           |
| 3.6 Invalid Days Min    |        |       |           |
| 3.7 Invalid Days Max    |        |       |           |
| 3.8 Invalid Limit       |        |       |           |
| 3.9 No Recent           |        |       |           |
| 3.10 Sort Order         |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Phase 2 Summary

### Overall Phase Results

**Tools Tested**: 3/3

- [ ] Tool 1: search_concepts_semantic
- [ ] Tool 2: search_concepts_exact
- [ ] Tool 3: get_recent_concepts

**Total Test Cases**: 30

**Pass/Fail Summary**:

- Tests Passed: **\_** / 30
- Tests Failed: **\_** / 30
- Success Rate: **\_**%

### Search Quality Assessment

#### Semantic Search Quality

- Relevance of results: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Similarity score accuracy: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Filter effectiveness: [ ] Excellent [ ] Good [ ] Fair [ ] Poor

#### Exact Search Quality

- Filter accuracy: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Sort order correctness: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Performance: [ ] Excellent [ ] Good [ ] Fair [ ] Poor

#### Recent Concepts Quality

- Time window accuracy: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Sort order correctness: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Parameter validation: [ ] Excellent [ ] Good [ ] Fair [ ] Poor

### Critical Issues Found

(Document any critical bugs or failures)

1.
2.
3.

### Minor Issues Found

(Document any minor issues or warnings)

1.
2.
3.

### Recommendations

(Suggestions for improvements)

1.
2.
3.

### Sign-Off

**Tester Name**: **********\_**********
**Test Date**: **********\_**********
**Test Duration**: **********\_**********
**Phase Status**: [ ] PASS [ ] FAIL

**Next Phase**: Phase 3 - Relationship Management
