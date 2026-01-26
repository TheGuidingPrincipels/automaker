# Test Phase 1: Foundation & Basic Concept Operations

## Overview

This phase tests the foundational tools of the MCP Knowledge Server, focusing on basic CRUD (Create, Read, Update, Delete) operations for concepts and system diagnostics.

**Total Tools in Phase**: 6
**Estimated Time**: 45-60 minutes
**Dependencies**: Neo4j, ChromaDB, Event Store must be running

---

## Pre-Test Requirements

### System Checklist

- [ ] Neo4j is running (bolt://localhost:7687)
- [ ] ChromaDB directory exists (/data/chroma)
- [ ] Event Store database exists (/data/events.db)
- [ ] MCP server is running
- [ ] Claude Desktop is connected to MCP server

### Environment Variables

Verify these are set:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
CHROMA_PERSIST_DIRECTORY=./data/chroma
EVENT_STORE_PATH=./data/events.db
```

---

## Test Execution Instructions

**IMPORTANT**: Test ONE tool at a time. After completing all tests for a tool:

1. Document results in the Test Results section
2. Take a break
3. Notify test coordinator
4. Wait for go-ahead before proceeding to next tool

---

## Tool 1: `ping`

### Purpose

Test MCP server connectivity and basic health check.

### Tool Specification

- **Input Parameters**: None
- **Expected Output**:
  ```json
  {
    "status": "ok",
    "message": "MCP Knowledge Server is running",
    "server_name": "knowledge-server",
    "timestamp": "<ISO 8601 timestamp>"
  }
  ```
- **Dependencies**: None (always available)

### Test Cases

#### Test 1.1: Basic Ping

**Description**: Verify server responds to ping
**Action**: Call `ping` tool with no parameters
**Expected Result**:

- Returns status "ok"
- Message confirms server is running
- Timestamp is valid ISO 8601 format
- Response time < 100ms

**Test Steps**:

1. Use MCP tool: `ping`
2. Verify response structure matches expected output
3. Check timestamp is current (within last few seconds)
4. Note response time

**Pass/Fail Criteria**:

- ✅ PASS: All fields present, status="ok", valid timestamp
- ❌ FAIL: Missing fields, error response, or timeout

---

#### Test 1.2: Multiple Consecutive Pings

**Description**: Verify server handles multiple rapid pings
**Action**: Call `ping` 5 times in succession
**Expected Result**: All 5 pings return successful responses

**Test Steps**:

1. Call `ping` tool 5 times
2. Verify each response is successful
3. Compare timestamps (should increment)

**Pass/Fail Criteria**:

- ✅ PASS: All 5 pings successful with incrementing timestamps
- ❌ FAIL: Any ping fails or returns error

---

### Test Results for Tool 1

| Test Case          | Status | Notes | Timestamp |
| ------------------ | ------ | ----- | --------- |
| 1.1 Basic Ping     |        |       |           |
| 1.2 Multiple Pings |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 2: `get_tool_availability`

### Purpose

Diagnostic tool to check which tools are available and their service dependencies.

### Tool Specification

- **Input Parameters**: None
- **Expected Output**:
  ```json
  {
    "success": true,
    "available": ["ping", "create_concept", ...],
    "unavailable": [],
    "total_tools": 17,
    "service_status": {
      "concept_tools": {"repository": true, "confidence_service": true},
      "search_tools": {"neo4j_service": true, "chromadb_service": true, "embedding_service": true},
      "relationship_tools": {"neo4j_service": true, "event_store": true, "outbox": true},
      "analytics_tools": {"neo4j_service": true}
    }
  }
  ```

### Test Cases

#### Test 2.1: Check All Tools Available

**Description**: Verify all 17 tools are available when services are running
**Action**: Call `get_tool_availability`
**Expected Result**:

- total_tools = 17
- All tools in "available" list
- "unavailable" list is empty
- All service_status values are true

**Test Steps**:

1. Use MCP tool: `get_tool_availability`
2. Count tools in "available" array (should be 17)
3. Verify "unavailable" array is empty
4. Check all service_status booleans are true

**Pass/Fail Criteria**:

- ✅ PASS: 17 available tools, no unavailable tools, all services true
- ❌ FAIL: Missing tools or services showing false

---

#### Test 2.2: Verify Service Status Details

**Description**: Check service status structure is complete
**Action**: Examine service_status object
**Expected Result**: All four categories present with correct services

**Test Steps**:

1. Call `get_tool_availability`
2. Verify concept_tools has: repository, confidence_service
3. Verify search_tools has: neo4j_service, chromadb_service, embedding_service
4. Verify relationship_tools has: neo4j_service, event_store, outbox
5. Verify analytics_tools has: neo4j_service

**Pass/Fail Criteria**:

- ✅ PASS: All categories and services present
- ❌ FAIL: Missing categories or services

---

### Test Results for Tool 2

| Test Case                  | Status | Notes | Timestamp |
| -------------------------- | ------ | ----- | --------- |
| 2.1 All Tools Available    |        |       |           |
| 2.2 Service Status Details |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 3: `create_concept`

### Purpose

Create new concepts in the knowledge base with automatic certainty scoring.

### Tool Specification

- **Input Parameters**:
  - `name` (required): string, 1-200 chars
  - `explanation` (required): string
  - `area` (optional): string, max 100 chars
  - `topic` (optional): string, max 100 chars
  - `subtopic` (optional): string, max 100 chars
  - `source_urls` (optional): JSON string array of source objects
- **Expected Output**:
  ```json
  {
    "success": true,
    "concept_id": "<UUID>",
    "message": "Concept created successfully"
  }
  ```

### Test Cases

#### Test 3.1: Create Basic Concept (Required Fields Only)

**Description**: Create concept with only required fields
**Action**: Create concept with name and explanation
**Expected Result**: Success with generated concept_id

**Test Data**:

```
name: "Test Concept - Basic"
explanation: "This is a basic test concept with minimal required fields for Phase 1 testing."
```

**Test Steps**:

1. Use MCP tool: `create_concept` with above data
2. Verify success = true
3. Save concept_id for later tests
4. Verify message confirms creation

**Pass/Fail Criteria**:

- ✅ PASS: Success response with valid UUID concept_id
- ❌ FAIL: Error response or missing concept_id

**Save Data**: Record concept_id as `BASIC_CONCEPT_ID`

---

#### Test 3.2: Create Fully Categorized Concept

**Description**: Create concept with all optional fields
**Action**: Create concept with area, topic, subtopic
**Expected Result**: Success with full categorization

**Test Data**:

```
name: "MCP Protocol"
explanation: "The Model Context Protocol (MCP) is a protocol that enables communication between AI models and external tools or data sources."
area: "Technology"
topic: "AI Protocols"
subtopic: "Communication Standards"
```

**Test Steps**:

1. Use MCP tool: `create_concept` with above data
2. Verify success = true
3. Save concept_id for later tests

**Pass/Fail Criteria**:

- ✅ PASS: Success with valid concept_id
- ❌ FAIL: Error or categorization not saved

**Save Data**: Record concept_id as `CATEGORIZED_CONCEPT_ID`

---

#### Test 3.3: Create Concept with Source URLs

**Description**: Create concept with source URL metadata
**Action**: Create concept with source_urls parameter
**Expected Result**: Success with sources stored

**Test Data**:

```
name: "Python Programming"
explanation: "Python is a high-level, interpreted programming language known for its simplicity and readability."
area: "Programming"
topic: "Languages"
source_urls: '[{"url": "https://www.python.org", "title": "Official Python Website", "quality_score": 0.95, "domain_category": "official"}]'
```

**Test Steps**:

1. Use MCP tool: `create_concept` with above data
2. Verify success = true
3. Save concept_id

**Pass/Fail Criteria**:

- ✅ PASS: Success with valid concept_id
- ❌ FAIL: Error or source_urls rejected

**Save Data**: Record concept_id as `SOURCED_CONCEPT_ID`

---

#### Test 3.4: Duplicate Detection

**Description**: Verify duplicate concepts are detected
**Action**: Attempt to create concept with same name+area+topic
**Expected Result**: Should either succeed (duplicates allowed) or fail with duplicate error

**Test Data**: Use same data as Test 3.2 (MCP Protocol)

**Test Steps**:

1. Use MCP tool: `create_concept` with Test 3.2 data
2. Check response message
3. If success, verify different concept_id
4. If failure, verify error mentions duplicate

**Pass/Fail Criteria**:

- ✅ PASS: System handles duplicate (either creates new or rejects with clear error)
- ❌ FAIL: Crashes or unclear error

---

#### Test 3.5: Invalid Input - Empty Name

**Description**: Verify validation rejects empty name
**Action**: Create concept with empty or whitespace-only name
**Expected Result**: Validation error

**Test Data**:

```
name: "   "
explanation: "Test explanation"
```

**Test Steps**:

1. Use MCP tool: `create_concept` with above data
2. Expect error response
3. Verify error message mentions name validation

**Pass/Fail Criteria**:

- ✅ PASS: Returns validation error
- ❌ FAIL: Creates concept with invalid name

---

#### Test 3.6: Invalid Input - Empty Explanation

**Description**: Verify validation rejects empty explanation
**Action**: Create concept with empty explanation
**Expected Result**: Validation error

**Test Data**:

```
name: "Test Concept"
explanation: ""
```

**Test Steps**:

1. Use MCP tool: `create_concept` with above data
2. Expect error response

**Pass/Fail Criteria**:

- ✅ PASS: Returns validation error
- ❌ FAIL: Creates concept with invalid explanation

---

#### Test 3.7: Invalid Input - Name Too Long

**Description**: Verify name length limit (200 chars)
**Action**: Create concept with 201-character name
**Expected Result**: Validation error

**Test Data**:

```
name: "A" * 201  (201 'A' characters)
explanation: "Test explanation"
```

**Test Steps**:

1. Use MCP tool: `create_concept` with 201-char name
2. Expect validation error

**Pass/Fail Criteria**:

- ✅ PASS: Returns validation error about length
- ❌ FAIL: Creates concept or different error

---

#### Test 3.8: Invalid Input - Malformed source_urls JSON

**Description**: Verify source_urls must be valid JSON
**Action**: Create concept with invalid JSON string
**Expected Result**: Validation error

**Test Data**:

```
name: "Test Concept"
explanation: "Test explanation"
source_urls: "{not valid json}"
```

**Test Steps**:

1. Use MCP tool: `create_concept` with invalid JSON
2. Expect validation error

**Pass/Fail Criteria**:

- ✅ PASS: Returns JSON validation error
- ❌ FAIL: Creates concept or crashes

---

#### Test 3.9: Verify Event Sourcing

**Description**: Verify concept creation generates event in event store
**Action**: Create concept and check server stats
**Expected Result**: Event count increments

**Test Steps**:

1. Call `get_server_stats` and note event_store.concept_events count
2. Create a new concept
3. Call `get_server_stats` again
4. Verify concept_events increased by 1

**Pass/Fail Criteria**:

- ✅ PASS: Event count increased by exactly 1
- ❌ FAIL: Event count unchanged or unexpected change

---

#### Test 3.10: Verify Dual Storage (Neo4j + ChromaDB)

**Description**: Verify concept stored in both databases
**Action**: Create concept then retrieve it
**Expected Result**: Successfully retrieved from Neo4j

**Test Steps**:

1. Create concept (save concept_id)
2. Use `get_concept` to retrieve it
3. Verify all fields match what was created

**Pass/Fail Criteria**:

- ✅ PASS: Concept retrieved with all correct data
- ❌ FAIL: Cannot retrieve or data mismatch

---

### Test Results for Tool 3

| Test Case               | Status | Notes | Concept ID | Timestamp |
| ----------------------- | ------ | ----- | ---------- | --------- |
| 3.1 Basic Concept       |        |       |            |           |
| 3.2 Fully Categorized   |        |       |            |           |
| 3.3 With Source URLs    |        |       |            |           |
| 3.4 Duplicate Detection |        |       |            |           |
| 3.5 Empty Name          |        |       |            |           |
| 3.6 Empty Explanation   |        |       |            |           |
| 3.7 Name Too Long       |        |       |            |           |
| 3.8 Malformed JSON      |        |       |            |           |
| 3.9 Event Sourcing      |        |       |            |           |
| 3.10 Dual Storage       |        |       |            |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

**Important IDs to Save**:

- BASIC_CONCEPT_ID: ********\_\_\_********
- CATEGORIZED_CONCEPT_ID: ********\_\_\_********
- SOURCED_CONCEPT_ID: ********\_\_\_********

---

## Tool 4: `get_concept`

### Purpose

Retrieve a concept by its UUID, with optional history.

### Tool Specification

- **Input Parameters**:
  - `concept_id` (required): string (UUID)
  - `include_history` (optional): boolean, default=false
- **Expected Output**:
  ```json
  {
    "success": true,
    "concept": {
      "concept_id": "<UUID>",
      "name": "...",
      "explanation": "...",
      "area": "...",
      "topic": "...",
      "subtopic": "...",
      "certainty_score": 0-100,
      "created_at": "<ISO datetime>",
      "last_modified": "<ISO datetime>",
      "explanation_history": [...] (if include_history=true)
    },
    "message": "..."
  }
  ```

### Test Cases

#### Test 4.1: Get Basic Concept

**Description**: Retrieve concept created in Test 3.1
**Action**: Get concept without history
**Expected Result**: Returns concept with all fields

**Test Data**: Use BASIC_CONCEPT_ID from Test 3.1

**Test Steps**:

1. Use MCP tool: `get_concept` with concept_id=BASIC_CONCEPT_ID
2. Verify success = true
3. Verify name matches "Test Concept - Basic"
4. Verify explanation matches original
5. Verify certainty_score is present (0-100)
6. Verify created_at is valid ISO timestamp
7. Verify last_modified equals created_at (not updated yet)

**Pass/Fail Criteria**:

- ✅ PASS: All fields present and match expected values
- ❌ FAIL: Missing fields or data mismatch

---

#### Test 4.2: Get Categorized Concept

**Description**: Retrieve concept with full categorization
**Action**: Get concept with area/topic/subtopic
**Expected Result**: All categorization fields present

**Test Data**: Use CATEGORIZED_CONCEPT_ID from Test 3.2

**Test Steps**:

1. Use MCP tool: `get_concept` with concept_id=CATEGORIZED_CONCEPT_ID
2. Verify area = "Technology"
3. Verify topic = "AI Protocols"
4. Verify subtopic = "Communication Standards"

**Pass/Fail Criteria**:

- ✅ PASS: All categorization fields correct
- ❌ FAIL: Missing or incorrect categorization

---

#### Test 4.3: Get Concept with History (No Updates Yet)

**Description**: Retrieve with include_history=true before updates
**Action**: Get concept with history flag
**Expected Result**: History should be empty or have only creation

**Test Data**: Use BASIC_CONCEPT_ID

**Test Steps**:

1. Use MCP tool: `get_concept` with concept_id=BASIC_CONCEPT_ID, include_history=true
2. Check explanation_history field
3. Verify it's either empty or has single entry

**Pass/Fail Criteria**:

- ✅ PASS: History is empty or single creation entry
- ❌ FAIL: Unexpected history entries

---

#### Test 4.4: Non-Existent Concept

**Description**: Verify error handling for invalid concept_id
**Action**: Get concept with fake UUID
**Expected Result**: Error response

**Test Data**:

```
concept_id: "00000000-0000-0000-0000-000000000000"
```

**Test Steps**:

1. Use MCP tool: `get_concept` with fake concept_id
2. Expect success = false
3. Verify error message mentions "not found"

**Pass/Fail Criteria**:

- ✅ PASS: Returns "not found" error
- ❌ FAIL: Returns success or different error

---

#### Test 4.5: Invalid UUID Format

**Description**: Verify validation for malformed UUID
**Action**: Get concept with invalid UUID string
**Expected Result**: Validation error

**Test Data**:

```
concept_id: "not-a-uuid"
```

**Test Steps**:

1. Use MCP tool: `get_concept` with invalid UUID
2. Expect error response

**Pass/Fail Criteria**:

- ✅ PASS: Returns validation error
- ❌ FAIL: Crashes or accepts invalid UUID

---

#### Test 4.6: Certainty Score Verification

**Description**: Verify certainty_score is calculated
**Action**: Check certainty_score field
**Expected Result**: Score between 0-100

**Test Data**: Use any created concept

**Test Steps**:

1. Use MCP tool: `get_concept` with any valid concept_id
2. Verify certainty_score field exists
3. Verify value is numeric
4. Verify value is between 0-100

**Pass/Fail Criteria**:

- ✅ PASS: Valid certainty_score 0-100
- ❌ FAIL: Missing, null, or out of range

---

### Test Results for Tool 4

| Test Case             | Status | Notes | Timestamp |
| --------------------- | ------ | ----- | --------- |
| 4.1 Get Basic Concept |        |       |           |
| 4.2 Get Categorized   |        |       |           |
| 4.3 Get with History  |        |       |           |
| 4.4 Non-Existent      |        |       |           |
| 4.5 Invalid UUID      |        |       |           |
| 4.6 Certainty Score   |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 5: `update_concept`

### Purpose

Update existing concepts with partial updates support.

### Tool Specification

- **Input Parameters**:
  - `concept_id` (required): string (UUID)
  - `explanation` (optional): string
  - `name` (optional): string, 1-200 chars
  - `area` (optional): string, max 100 chars
  - `topic` (optional): string, max 100 chars
  - `subtopic` (optional): string, max 100 chars
  - `source_urls` (optional): JSON string
- **Expected Output**:
  ```json
  {
    "success": true,
    "updated_fields": ["explanation", "name"],
    "message": "Concept updated successfully"
  }
  ```

### Test Cases

#### Test 5.1: Update Explanation Only

**Description**: Partial update of explanation field
**Action**: Update only explanation
**Expected Result**: Only explanation changes

**Test Data**:

```
concept_id: BASIC_CONCEPT_ID (from Test 3.1)
explanation: "UPDATED: This explanation has been modified during Phase 1 testing to verify update functionality."
```

**Test Steps**:

1. Get original concept and note all fields
2. Use MCP tool: `update_concept` with above data
3. Verify updated_fields = ["explanation"]
4. Get concept again
5. Verify explanation changed
6. Verify name, area, topic unchanged
7. Verify last_modified > created_at

**Pass/Fail Criteria**:

- ✅ PASS: Only explanation updated, other fields unchanged
- ❌ FAIL: Other fields changed or explanation not updated

---

#### Test 5.2: Update Multiple Fields

**Description**: Update multiple fields in single call
**Action**: Update name, area, and topic together
**Expected Result**: All specified fields update

**Test Data**:

```
concept_id: CATEGORIZED_CONCEPT_ID (from Test 3.2)
name: "MCP Protocol - UPDATED"
area: "Computer Science"
topic: "Network Protocols"
```

**Test Steps**:

1. Use MCP tool: `update_concept` with above data
2. Verify updated_fields includes all three fields
3. Get concept and verify all changes applied
4. Verify subtopic and explanation unchanged

**Pass/Fail Criteria**:

- ✅ PASS: All three fields updated, others unchanged
- ❌ FAIL: Some fields not updated or unspecified fields changed

---

#### Test 5.3: Update Source URLs

**Description**: Update source_urls metadata
**Action**: Add/update source URLs
**Expected Result**: Source URLs updated

**Test Data**:

```
concept_id: SOURCED_CONCEPT_ID (from Test 3.3)
source_urls: '[{"url": "https://docs.python.org", "title": "Python Documentation", "quality_score": 0.9, "domain_category": "official"}]'
```

**Test Steps**:

1. Use MCP tool: `update_concept` with new source_urls
2. Verify success
3. Get concept and verify source URLs changed

**Pass/Fail Criteria**:

- ✅ PASS: Source URLs updated successfully
- ❌ FAIL: Source URLs not updated or error

---

#### Test 5.4: Update with History Tracking

**Description**: Verify explanation history is tracked
**Action**: Update explanation and check history
**Expected Result**: History contains both versions

**Test Data**:

```
concept_id: BASIC_CONCEPT_ID
explanation: "SECOND UPDATE: Another modification to test history tracking."
```

**Test Steps**:

1. Use MCP tool: `update_concept` with new explanation
2. Get concept with include_history=true
3. Verify explanation_history has multiple entries
4. Verify both original and updated text in history

**Pass/Fail Criteria**:

- ✅ PASS: History shows progression of changes
- ❌ FAIL: History missing or incomplete

---

#### Test 5.5: Invalid Update - No Fields Provided

**Description**: Verify error when no update fields provided
**Action**: Call update with only concept_id
**Expected Result**: Validation error

**Test Data**:

```
concept_id: BASIC_CONCEPT_ID
(no other fields)
```

**Test Steps**:

1. Use MCP tool: `update_concept` with only concept_id
2. Expect validation error

**Pass/Fail Criteria**:

- ✅ PASS: Returns error requiring at least one field
- ❌ FAIL: Accepts empty update or crashes

---

#### Test 5.6: Invalid Update - Empty Name

**Description**: Verify validation rejects empty name
**Action**: Update with whitespace-only name
**Expected Result**: Validation error

**Test Data**:

```
concept_id: BASIC_CONCEPT_ID
name: "   "
```

**Test Steps**:

1. Use MCP tool: `update_concept` with empty name
2. Expect validation error

**Pass/Fail Criteria**:

- ✅ PASS: Returns validation error
- ❌ FAIL: Updates with invalid name

---

#### Test 5.7: Invalid Update - Non-Existent Concept

**Description**: Verify error for updating non-existent concept
**Action**: Update with fake concept_id
**Expected Result**: Not found error

**Test Data**:

```
concept_id: "00000000-0000-0000-0000-000000000000"
explanation: "Test"
```

**Test Steps**:

1. Use MCP tool: `update_concept` with fake ID
2. Expect "not found" error

**Pass/Fail Criteria**:

- ✅ PASS: Returns not found error
- ❌ FAIL: Different error or success

---

#### Test 5.8: Embedding Regeneration

**Description**: Verify embeddings regenerate when explanation changes
**Action**: Update explanation and verify system processes it
**Expected Result**: No errors, update succeeds

**Test Data**:

```
concept_id: BASIC_CONCEPT_ID
explanation: "Testing embedding regeneration with completely new content about machine learning and artificial intelligence."
```

**Test Steps**:

1. Use MCP tool: `update_concept` with new explanation
2. Verify success
3. Wait 5-10 seconds (for async processing)
4. Use semantic search for keywords in new explanation
5. Verify updated concept appears in results

**Pass/Fail Criteria**:

- ✅ PASS: Update succeeds and semantic search finds updated content
- ❌ FAIL: Update fails or search doesn't find new content

---

#### Test 5.9: Certainty Score Recalculation

**Description**: Verify certainty score recalculates after update
**Action**: Update concept and check if score changes
**Expected Result**: Score may change based on content

**Test Steps**:

1. Get concept and note certainty_score
2. Update with richer explanation and categorization
3. Wait 5-10 seconds (async recalculation)
4. Get concept again
5. Note if certainty_score changed

**Pass/Fail Criteria**:

- ✅ PASS: Score recalculation occurs (may increase/decrease)
- ❌ FAIL: System error during recalculation

**Note**: Score may not always change depending on update content.

---

### Test Results for Tool 5

| Test Case              | Status | Notes | Timestamp |
| ---------------------- | ------ | ----- | --------- |
| 5.1 Update Explanation |        |       |           |
| 5.2 Multiple Fields    |        |       |           |
| 5.3 Source URLs        |        |       |           |
| 5.4 History Tracking   |        |       |           |
| 5.5 No Fields Error    |        |       |           |
| 5.6 Empty Name Error   |        |       |           |
| 5.7 Non-Existent       |        |       |           |
| 5.8 Embedding Regen    |        |       |           |
| 5.9 Certainty Recalc   |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 6: `delete_concept`

### Purpose

Soft delete concepts (preserves in event store, removes from ChromaDB).

### Tool Specification

- **Input Parameters**:
  - `concept_id` (required): string (UUID)
- **Expected Output**:
  ```json
  {
    "success": true,
    "concept_id": "<UUID>",
    "message": "Concept deleted successfully"
  }
  ```

### Test Cases

#### Test 6.1: Delete Existing Concept

**Description**: Soft delete a concept
**Action**: Delete BASIC_CONCEPT_ID
**Expected Result**: Concept marked as deleted

**Test Data**: BASIC_CONCEPT_ID

**Test Steps**:

1. Verify concept exists with `get_concept`
2. Use MCP tool: `delete_concept` with concept_id=BASIC_CONCEPT_ID
3. Verify success = true
4. Try to get concept again
5. Verify error or deleted flag set

**Pass/Fail Criteria**:

- ✅ PASS: Delete succeeds, concept no longer retrievable
- ❌ FAIL: Delete fails or concept still accessible

---

#### Test 6.2: Delete Non-Existent Concept

**Description**: Verify error for deleting non-existent concept
**Action**: Delete with fake UUID
**Expected Result**: Not found error

**Test Data**:

```
concept_id: "00000000-0000-0000-0000-000000000000"
```

**Test Steps**:

1. Use MCP tool: `delete_concept` with fake ID
2. Expect error response

**Pass/Fail Criteria**:

- ✅ PASS: Returns not found error
- ❌ FAIL: Returns success or different error

---

#### Test 6.3: Idempotent Delete

**Description**: Verify deleting already-deleted concept is safe
**Action**: Delete same concept twice
**Expected Result**: Either succeeds both times or second returns appropriate message

**Test Data**: Use a concept from Phase 1 tests

**Test Steps**:

1. Delete a concept (first time)
2. Verify success
3. Delete same concept again
4. Check response (should be graceful)

**Pass/Fail Criteria**:

- ✅ PASS: Second delete is safe (success or "already deleted")
- ❌ FAIL: Second delete crashes or errors unexpectedly

---

#### Test 6.4: Verify Event Sourcing

**Description**: Verify delete creates event in event store
**Action**: Delete concept and check stats
**Expected Result**: Event count increases

**Test Steps**:

1. Get server stats and note event count
2. Create a test concept
3. Delete the concept
4. Get server stats again
5. Verify total events increased

**Pass/Fail Criteria**:

- ✅ PASS: Event count increased (includes create + delete)
- ❌ FAIL: Event count unchanged

---

#### Test 6.5: Verify Removal from Search

**Description**: Verify deleted concept doesn't appear in searches
**Action**: Delete concept then search for it
**Expected Result**: Not found in search results

**Test Steps**:

1. Create concept with unique name "DELETE_TEST_UNIQUE_12345"
2. Verify it appears in exact search
3. Delete the concept
4. Search again with same name
5. Verify not in results

**Pass/Fail Criteria**:

- ✅ PASS: Deleted concept not in search results
- ❌ FAIL: Still appears in search

---

### Test Results for Tool 6

| Test Case               | Status | Notes | Timestamp |
| ----------------------- | ------ | ----- | --------- |
| 6.1 Delete Existing     |        |       |           |
| 6.2 Delete Non-Existent |        |       |           |
| 6.3 Idempotent Delete   |        |       |           |
| 6.4 Event Sourcing      |        |       |           |
| 6.5 Search Removal      |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Phase 1 Summary

### Overall Phase Results

**Tools Tested**: 6/6

- [ ] Tool 1: ping
- [ ] Tool 2: get_tool_availability
- [ ] Tool 3: create_concept
- [ ] Tool 4: get_concept
- [ ] Tool 5: update_concept
- [ ] Tool 6: delete_concept

**Total Test Cases**: 30

**Pass/Fail Summary**:

- Tests Passed: **\_** / 30
- Tests Failed: **\_** / 30
- Success Rate: **\_**%

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

(Suggestions for improvements or next steps)

1.
2.
3.

### Data Artifacts

**Concept IDs Created** (save for future phases):

- BASIC_CONCEPT_ID: ********\_\_\_********
- CATEGORIZED_CONCEPT_ID: ********\_\_\_********
- SOURCED_CONCEPT_ID: ********\_\_\_********

### Sign-Off

**Tester Name**: **********\_**********
**Test Date**: **********\_**********
**Test Duration**: **********\_**********
**Phase Status**: [ ] PASS [ ] FAIL

**Next Phase**: Phase 2 - Search & Discovery
