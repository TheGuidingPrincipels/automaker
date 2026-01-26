# Test Phase 3: Relationship Management

## Overview

This phase tests the graph relationship capabilities of the MCP Knowledge Server, including creating connections between concepts, traversing the knowledge graph, and finding learning paths.

**Total Tools in Phase**: 5
**Estimated Time**: 60-75 minutes
**Dependencies**: Phase 1 and Phase 2 must be completed (multiple concepts must exist)

---

## Pre-Test Requirements

### System Checklist

- [ ] Phase 1 completed successfully
- [ ] Phase 2 completed successfully
- [ ] At least 5-6 concepts exist in knowledge base
- [ ] Neo4j is running and accessible
- [ ] Event Store is operational
- [ ] MCP server is running

### Required Data from Previous Phases

You'll need concept IDs from previous phases. If not available, create these test concepts:

**Setup Concept A**: Python Basics

```
name: "Python Basics"
explanation: "Fundamental concepts of Python programming including syntax, data types, and basic operations."
area: "Programming"
topic: "Python"
subtopic: "Fundamentals"
```

Save as: CONCEPT_A_ID

**Setup Concept B**: Python Functions

```
name: "Python Functions"
explanation: "Functions in Python allow code reuse and modular programming. Requires understanding of basic syntax."
area: "Programming"
topic: "Python"
subtopic: "Intermediate"
```

Save as: CONCEPT_B_ID

**Setup Concept C**: Python Classes

```
name: "Python Classes"
explanation: "Object-oriented programming in Python using classes and objects. Builds on functions and basic syntax."
area: "Programming"
topic: "Python"
subtopic: "Advanced"
```

Save as: CONCEPT_C_ID

**Setup Concept D**: Django Framework

```
name: "Django Web Framework"
explanation: "Django is a high-level Python web framework. Requires knowledge of Python classes and functions."
area: "Programming"
topic: "Web Development"
subtopic: "Frameworks"
```

Save as: CONCEPT_D_ID

**Setup Concept E**: REST APIs

```
name: "REST APIs"
explanation: "Representational State Transfer (REST) is an architectural style for web services. Related to web frameworks."
area: "Programming"
topic: "Web Development"
subtopic: "APIs"
```

Save as: CONCEPT_E_ID

---

## Test Execution Instructions

**IMPORTANT**: Test ONE tool at a time. After completing all tests for a tool:

1. Document results in the Test Results section
2. Take a break
3. Notify test coordinator
4. Wait for go-ahead before proceeding to next tool

---

## Tool 1: `create_relationship`

### Purpose

Create directed relationships between concepts to build the knowledge graph.

### Tool Specification

- **Input Parameters**:
  - `source_id` (required): string (UUID of source concept)
  - `target_id` (required): string (UUID of target concept)
  - `relationship_type` (required): string - "prerequisite", "relates_to", "includes", "contains"
  - `strength` (optional): float, 0.0-1.0, default=1.0
  - `notes` (optional): string (description)
- **Expected Output**:
  ```json
  {
    "success": true,
    "relationship_id": "<rel-id>",
    "message": "Relationship created successfully"
  }
  ```

### Test Cases

#### Test 1.1: Create PREREQUISITE Relationship

**Description**: Create prerequisite dependency (A is prerequisite of B)
**Action**: Link Python Basics → Python Functions
**Expected Result**: Relationship created successfully

**Test Data**:

```
source_id: CONCEPT_A_ID (Python Basics)
target_id: CONCEPT_B_ID (Python Functions)
relationship_type: "prerequisite"
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with above data
2. Verify success = true
3. Verify relationship_id is returned
4. Save relationship_id for later tests

**Pass/Fail Criteria**:

- ✅ PASS: Relationship created with valid ID
- ❌ FAIL: Error or missing relationship_id

**Save Data**: Record relationship_id as REL_1_ID

---

#### Test 1.2: Create PREREQUISITE Chain

**Description**: Create chain of prerequisites
**Action**: Create B→C and C→D relationships
**Expected Result**: Both relationships created

**Test Data**:

```
Relationship 1:
  source_id: CONCEPT_B_ID (Functions)
  target_id: CONCEPT_C_ID (Classes)
  relationship_type: "prerequisite"

Relationship 2:
  source_id: CONCEPT_C_ID (Classes)
  target_id: CONCEPT_D_ID (Django)
  relationship_type: "prerequisite"
```

**Test Steps**:

1. Create first relationship (B→C)
2. Verify success
3. Create second relationship (C→D)
4. Verify success
5. Save both relationship IDs

**Pass/Fail Criteria**:

- ✅ PASS: Both relationships created
- ❌ FAIL: Either relationship fails

**Save Data**: REL_2_ID, REL_3_ID

---

#### Test 1.3: Create RELATES_TO Relationship

**Description**: Create associative relationship
**Action**: Link Django ↔ REST APIs
**Expected Result**: Relationship created

**Test Data**:

```
source_id: CONCEPT_D_ID (Django)
target_id: CONCEPT_E_ID (REST APIs)
relationship_type: "relates_to"
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with relates_to type
2. Verify success
3. Save relationship_id

**Pass/Fail Criteria**:

- ✅ PASS: Relationship created
- ❌ FAIL: Error

**Save Data**: REL_4_ID

---

#### Test 1.4: Create Relationship with Strength

**Description**: Create relationship with custom strength value
**Action**: Create relationship with strength=0.7
**Expected Result**: Relationship created with specified strength

**Test Data**:

```
source_id: CONCEPT_E_ID (REST APIs)
target_id: CONCEPT_D_ID (Django)
relationship_type: "relates_to"
strength: 0.7
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with strength parameter
2. Verify success
3. Later verify strength is stored (in get_related_concepts)

**Pass/Fail Criteria**:

- ✅ PASS: Relationship created with strength
- ❌ FAIL: Error or strength not accepted

**Save Data**: REL_5_ID

---

#### Test 1.5: Create Relationship with Notes

**Description**: Create relationship with descriptive notes
**Action**: Create relationship with notes field
**Expected Result**: Relationship created with notes

**Test Data**:

```
source_id: CONCEPT_A_ID (Python Basics)
target_id: CONCEPT_C_ID (Classes)
relationship_type: "prerequisite"
notes: "Understanding basics is essential before learning OOP concepts"
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with notes
2. Verify success

**Pass/Fail Criteria**:

- ✅ PASS: Relationship created
- ❌ FAIL: Error

---

#### Test 1.6: Invalid Relationship - Wrong Type

**Description**: Verify type validation
**Action**: Use invalid relationship type
**Expected Result**: Validation error

**Test Data**:

```
source_id: CONCEPT_A_ID
target_id: CONCEPT_B_ID
relationship_type: "INVALID_TYPE"
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with invalid type
2. Expect validation error
3. Verify error mentions valid types

**Pass/Fail Criteria**:

- ✅ PASS: Returns validation error listing valid types
- ❌ FAIL: Creates relationship or different error

---

#### Test 1.7: Invalid Relationship - Non-Existent Source

**Description**: Verify source concept must exist
**Action**: Use fake source_id
**Expected Result**: Not found error

**Test Data**:

```
source_id: "00000000-0000-0000-0000-000000000000"
target_id: CONCEPT_B_ID
relationship_type: "prerequisite"
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with fake source
2. Expect error about source not found

**Pass/Fail Criteria**:

- ✅ PASS: Returns source not found error
- ❌ FAIL: Creates relationship or different error

---

#### Test 1.8: Invalid Relationship - Non-Existent Target

**Description**: Verify target concept must exist
**Action**: Use fake target_id
**Expected Result**: Not found error

**Test Data**:

```
source_id: CONCEPT_A_ID
target_id: "00000000-0000-0000-0000-000000000000"
relationship_type: "prerequisite"
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with fake target
2. Expect error about target not found

**Pass/Fail Criteria**:

- ✅ PASS: Returns target not found error
- ❌ FAIL: Creates relationship or different error

---

#### Test 1.9: Invalid Strength Value

**Description**: Verify strength validation (0.0-1.0)
**Action**: Use strength > 1.0
**Expected Result**: Validation error or auto-adjustment

**Test Data**:

```
source_id: CONCEPT_A_ID
target_id: CONCEPT_B_ID
relationship_type: "relates_to"
strength: 1.5
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with invalid strength
2. Check response (error or auto-adjustment)

**Pass/Fail Criteria**:

- ✅ PASS: Handles gracefully (error or adjustment)
- ❌ FAIL: Creates with invalid strength

---

#### Test 1.10: Duplicate Relationship Detection

**Description**: Test creating duplicate relationship
**Action**: Create same relationship twice
**Expected Result**: Either prevented or allowed (both valid)

**Test Data**: Use same source, target, type as Test 1.1

**Test Steps**:

1. Create relationship (already exists from Test 1.1)
2. Try to create same relationship again
3. Check response

**Pass/Fail Criteria**:

- ✅ PASS: Either rejects duplicate or creates new instance
- ❌ FAIL: Crashes or corrupt state

---

#### Test 1.11: Bidirectional Relationships

**Description**: Create relationships in both directions
**Action**: Create A→B and B→A
**Expected Result**: Both allowed (different directions)

**Test Data**:

```
Relationship 1: A → B (prerequisite)
Relationship 2: B → A (relates_to)
```

**Test Steps**:

1. Create A→B relationship
2. Create B→A relationship (different type)
3. Verify both succeed

**Pass/Fail Criteria**:

- ✅ PASS: Both relationships created
- ❌ FAIL: Second relationship rejected

---

#### Test 1.12: Self-Referential Relationship

**Description**: Test relationship from concept to itself
**Action**: Create A→A relationship
**Expected Result**: Either allowed or rejected gracefully

**Test Data**:

```
source_id: CONCEPT_A_ID
target_id: CONCEPT_A_ID (same as source)
relationship_type: "relates_to"
```

**Test Steps**:

1. Use MCP tool: `create_relationship` with same source and target
2. Check response

**Pass/Fail Criteria**:

- ✅ PASS: Handles gracefully (allows or rejects clearly)
- ❌ FAIL: Crashes

---

#### Test 1.13: Verify Event Sourcing

**Description**: Verify relationship creation generates event
**Action**: Create relationship and check server stats
**Expected Result**: Event count increases

**Test Steps**:

1. Call `get_server_stats` and note total_events
2. Create a new relationship
3. Call `get_server_stats` again
4. Verify total_events increased

**Pass/Fail Criteria**:

- ✅ PASS: Event count increased
- ❌ FAIL: Event count unchanged

---

#### Test 1.14: Certainty Score Recalculation

**Description**: Verify creating relationship triggers certainty recalc
**Action**: Create relationship and check certainty scores
**Expected Result**: Certainty scores may update

**Test Steps**:

1. Get source concept and note certainty_score
2. Create relationship from that concept
3. Wait 5-10 seconds (async processing)
4. Get source concept again
5. Check if certainty_score changed

**Pass/Fail Criteria**:

- ✅ PASS: System processes without error (score may or may not change)
- ❌ FAIL: Error during recalculation

**Note**: Score may not change depending on algorithm, but should not error.

---

### Test Results for Tool 1

| Test Case              | Status | Notes | Rel ID | Timestamp |
| ---------------------- | ------ | ----- | ------ | --------- |
| 1.1 Basic Prerequisite |        |       |        |           |
| 1.2 Prerequisite Chain |        |       |        |           |
| 1.3 Relates To         |        |       |        |           |
| 1.4 With Strength      |        |       |        |           |
| 1.5 With Notes         |        |       |        |           |
| 1.6 Invalid Type       |        |       |        |           |
| 1.7 Invalid Source     |        |       |        |           |
| 1.8 Invalid Target     |        |       |        |           |
| 1.9 Invalid Strength   |        |       |        |           |
| 1.10 Duplicate         |        |       |        |           |
| 1.11 Bidirectional     |        |       |        |           |
| 1.12 Self-Reference    |        |       |        |           |
| 1.13 Event Sourcing    |        |       |        |           |
| 1.14 Certainty Recalc  |        |       |        |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

**Important IDs to Save**:

- CONCEPT_A_ID: ********\_\_\_********
- CONCEPT_B_ID: ********\_\_\_********
- CONCEPT_C_ID: ********\_\_\_********
- CONCEPT_D_ID: ********\_\_\_********
- CONCEPT_E_ID: ********\_\_\_********
- REL_1_ID through REL_5_ID: ********\_\_\_********

---

## Tool 2: `get_related_concepts`

### Purpose

Graph traversal to find concepts related to a given concept.

### Tool Specification

- **Input Parameters**:
  - `concept_id` (required): string (UUID)
  - `relationship_type` (optional): string (filter by type)
  - `direction` (optional): string - "outgoing", "incoming", "both", default="outgoing"
  - `max_depth` (optional): int, 1-5, default=1
- **Expected Output**:
  ```json
  {
    "success": true,
    "concept_id": "<UUID>",
    "related": [
      {
        "concept_id": "<UUID>",
        "name": "...",
        "relationship_type": "prerequisite",
        "strength": 1.0,
        "distance": 1
      }
    ],
    "total": 5
  }
  ```

### Test Cases

#### Test 2.1: Get Outgoing Relationships (Depth 1)

**Description**: Get concepts directly connected from source
**Action**: Get outgoing relationships from Python Basics
**Expected Result**: Returns Python Functions (and possibly Classes)

**Test Data**:

```
concept_id: CONCEPT_A_ID (Python Basics)
direction: "outgoing"
max_depth: 1
```

**Test Steps**:

1. Use MCP tool: `get_related_concepts` with above data
2. Verify success = true
3. Verify related array contains concepts linked from A
4. Verify distance = 1 for all results
5. Verify relationship_type is present

**Pass/Fail Criteria**:

- ✅ PASS: Returns directly connected concepts
- ❌ FAIL: Missing expected concepts or wrong distance

---

#### Test 2.2: Get Incoming Relationships

**Description**: Get concepts that link TO this concept
**Action**: Get incoming relationships to Python Classes
**Expected Result**: Returns Python Functions (and possibly Basics)

**Test Data**:

```
concept_id: CONCEPT_C_ID (Python Classes)
direction: "incoming"
max_depth: 1
```

**Test Steps**:

1. Use MCP tool: `get_related_concepts` with incoming direction
2. Verify related array contains concepts linking to C
3. Verify these are the source concepts from prerequisite relationships

**Pass/Fail Criteria**:

- ✅ PASS: Returns incoming connections
- ❌ FAIL: Wrong concepts or direction ignored

---

#### Test 2.3: Get Bidirectional Relationships

**Description**: Get all relationships regardless of direction
**Action**: Get both incoming and outgoing
**Expected Result**: Returns all connected concepts

**Test Data**:

```
concept_id: CONCEPT_D_ID (Django)
direction: "both"
max_depth: 1
```

**Test Steps**:

1. Use MCP tool: `get_related_concepts` with direction="both"
2. Verify related array includes both incoming and outgoing
3. Should include Classes (incoming prerequisite) and REST APIs (outgoing relates_to)

**Pass/Fail Criteria**:

- ✅ PASS: Returns relationships in both directions
- ❌ FAIL: Only one direction or missing relationships

---

#### Test 2.4: Filter by Relationship Type

**Description**: Get only specific relationship type
**Action**: Get only prerequisite relationships
**Expected Result**: Only prerequisites returned

**Test Data**:

```
concept_id: CONCEPT_A_ID
relationship_type: "prerequisite"
direction: "outgoing"
```

**Test Steps**:

1. Use MCP tool: `get_related_concepts` with type filter
2. Verify all results have relationship_type = "prerequisite"
3. Verify no "relates_to" relationships included

**Pass/Fail Criteria**:

- ✅ PASS: Only prerequisite relationships returned
- ❌ FAIL: Other types included

---

#### Test 2.5: Multi-Hop Traversal (Depth 2)

**Description**: Traverse 2 levels deep
**Action**: Get relationships with max_depth=2
**Expected Result**: Returns concepts 1 and 2 hops away

**Test Data**:

```
concept_id: CONCEPT_A_ID (Python Basics)
direction: "outgoing"
max_depth: 2
```

**Test Steps**:

1. Use MCP tool: `get_related_concepts` with max_depth=2
2. Verify results include depth 1 and depth 2 concepts
3. Should include: B (depth 1), C (depth 2)
4. Verify distance field shows 1 or 2 appropriately

**Pass/Fail Criteria**:

- ✅ PASS: Returns multi-hop relationships with correct distances
- ❌ FAIL: Only depth 1 or wrong distances

---

#### Test 2.6: Multi-Hop Traversal (Depth 3)

**Description**: Traverse 3 levels deep
**Action**: Get relationships with max_depth=3
**Expected Result**: Returns concepts up to 3 hops away

**Test Data**:

```
concept_id: CONCEPT_A_ID
direction: "outgoing"
max_depth: 3
```

**Test Steps**:

1. Use MCP tool: `get_related_concepts` with max_depth=3
2. Verify results include concepts at distance 1, 2, and 3
3. Chain: A→B→C→D
4. Should find Django at distance 3

**Pass/Fail Criteria**:

- ✅ PASS: Finds concepts up to 3 hops with correct distances
- ❌ FAIL: Missing depth 3 concepts

---

#### Test 2.7: No Relationships Found

**Description**: Query concept with no relationships
**Action**: Get relationships for isolated concept
**Expected Result**: Empty results, graceful response

**Test Steps**:

1. Create a new isolated concept with no relationships
2. Use MCP tool: `get_related_concepts` on that concept
3. Verify success = true
4. Verify related array is empty
5. Verify total = 0

**Pass/Fail Criteria**:

- ✅ PASS: Graceful empty response
- ❌ FAIL: Error or crash

---

#### Test 2.8: Invalid Concept ID

**Description**: Query non-existent concept
**Action**: Use fake concept_id
**Expected Result**: Not found error

**Test Data**:

```
concept_id: "00000000-0000-0000-0000-000000000000"
```

**Test Steps**:

1. Use MCP tool: `get_related_concepts` with fake ID
2. Expect error response

**Pass/Fail Criteria**:

- ✅ PASS: Returns not found error
- ❌ FAIL: Different error or success

---

#### Test 2.9: Invalid Direction Parameter

**Description**: Test validation of direction parameter
**Action**: Use invalid direction value
**Expected Result**: Validation error

**Test Data**:

```
concept_id: CONCEPT_A_ID
direction: "invalid_direction"
```

**Test Steps**:

1. Use MCP tool: `get_related_concepts` with invalid direction
2. Expect validation error

**Pass/Fail Criteria**:

- ✅ PASS: Returns validation error
- ❌ FAIL: Accepts invalid value or different error

---

#### Test 2.10: Strength Values in Results

**Description**: Verify strength field is returned
**Action**: Check strength in results
**Expected Result**: Strength values present (0.0-1.0)

**Test Data**: Use any concept with relationships

**Test Steps**:

1. Use MCP tool: `get_related_concepts` on concept with relationships
2. Check each result for strength field
3. Verify strength values between 0.0-1.0
4. Verify relationship from Test 1.4 shows strength=0.7

**Pass/Fail Criteria**:

- ✅ PASS: Strength values present and valid
- ❌ FAIL: Missing strength or invalid values

---

### Test Results for Tool 2

| Test Case             | Status | Notes | Timestamp |
| --------------------- | ------ | ----- | --------- |
| 2.1 Outgoing Depth 1  |        |       |           |
| 2.2 Incoming          |        |       |           |
| 2.3 Bidirectional     |        |       |           |
| 2.4 Filter by Type    |        |       |           |
| 2.5 Depth 2           |        |       |           |
| 2.6 Depth 3           |        |       |           |
| 2.7 No Relationships  |        |       |           |
| 2.8 Invalid ID        |        |       |           |
| 2.9 Invalid Direction |        |       |           |
| 2.10 Strength Values  |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 3: `get_prerequisites`

### Purpose

Get complete prerequisite chain for learning path planning.

### Tool Specification

- **Input Parameters**:
  - `concept_id` (required): string (UUID)
  - `max_depth` (optional): int, 1-10, default=5
- **Expected Output**:
  ```json
  {
    "success": true,
    "concept_id": "<UUID>",
    "chain": [
      {
        "concept_id": "<UUID>",
        "name": "...",
        "depth": 1
      }
    ],
    "total": 3
  }
  ```

### Test Cases

#### Test 3.1: Get Prerequisites - Single Level

**Description**: Get immediate prerequisites
**Action**: Get prerequisites of Python Functions
**Expected Result**: Returns Python Basics

**Test Data**:

```
concept_id: CONCEPT_B_ID (Python Functions)
max_depth: 1
```

**Test Steps**:

1. Use MCP tool: `get_prerequisites` with max_depth=1
2. Verify success = true
3. Verify chain includes Python Basics
4. Verify depth = 1 for all results
5. Verify ordered from deepest to target

**Pass/Fail Criteria**:

- ✅ PASS: Returns immediate prerequisites
- ❌ FAIL: Missing prerequisites or wrong depth

---

#### Test 3.2: Get Prerequisites - Full Chain

**Description**: Get complete prerequisite chain
**Action**: Get all prerequisites of Django
**Expected Result**: Returns Classes, Functions, Basics in order

**Test Data**:

```
concept_id: CONCEPT_D_ID (Django)
max_depth: 5
```

**Test Steps**:

1. Use MCP tool: `get_prerequisites` with max_depth=5
2. Verify chain includes all prerequisites in chain
3. Expected order (deepest to target): Basics (depth 3), Functions (depth 2), Classes (depth 1)
4. Verify depth values correct
5. Verify ordered by depth (deepest first)

**Pass/Fail Criteria**:

- ✅ PASS: Complete chain with correct order and depths
- ❌ FAIL: Missing prerequisites or wrong order

---

#### Test 3.3: No Prerequisites

**Description**: Query concept with no prerequisites
**Action**: Get prerequisites of Python Basics (root concept)
**Expected Result**: Empty chain

**Test Data**:

```
concept_id: CONCEPT_A_ID (Python Basics - no prerequisites)
```

**Test Steps**:

1. Use MCP tool: `get_prerequisites` on root concept
2. Verify success = true
3. Verify chain array is empty
4. Verify total = 0

**Pass/Fail Criteria**:

- ✅ PASS: Graceful empty response
- ❌ FAIL: Error

---

#### Test 3.4: Limited Depth

**Description**: Test max_depth limiting
**Action**: Get prerequisites with depth limit
**Expected Result**: Only prerequisites up to max_depth

**Test Data**:

```
concept_id: CONCEPT_D_ID (Django)
max_depth: 2
```

**Test Steps**:

1. Use MCP tool: `get_prerequisites` with max_depth=2
2. Verify only depth 1 and 2 prerequisites returned
3. Should include Classes (1) and Functions (2)
4. Should NOT include Basics (depth 3)

**Pass/Fail Criteria**:

- ✅ PASS: Respects depth limit
- ❌ FAIL: Returns deeper prerequisites

---

#### Test 3.5: Invalid Concept ID

**Description**: Query non-existent concept
**Action**: Use fake concept_id
**Expected Result**: Not found error

**Test Data**:

```
concept_id: "00000000-0000-0000-0000-000000000000"
```

**Test Steps**:

1. Use MCP tool: `get_prerequisites` with fake ID
2. Expect not found error

**Pass/Fail Criteria**:

- ✅ PASS: Returns not found error
- ❌ FAIL: Different error or success

---

#### Test 3.6: Learning Path Ordering

**Description**: Verify prerequisites are ordered for learning
**Action**: Check order is deepest to target
**Expected Result**: Correct learning sequence

**Test Data**: Use CONCEPT_D_ID (Django)

**Test Steps**:

1. Use MCP tool: `get_prerequisites` on Django
2. Verify first item is deepest prerequisite (Basics)
3. Verify last item is immediate prerequisite (Classes)
4. Verify proper learning order (Basics → Functions → Classes)

**Pass/Fail Criteria**:

- ✅ PASS: Ordered for optimal learning path
- ❌ FAIL: Wrong order

---

### Test Results for Tool 3

| Test Case            | Status | Notes | Timestamp |
| -------------------- | ------ | ----- | --------- |
| 3.1 Single Level     |        |       |           |
| 3.2 Full Chain       |        |       |           |
| 3.3 No Prerequisites |        |       |           |
| 3.4 Limited Depth    |        |       |           |
| 3.5 Invalid ID       |        |       |           |
| 3.6 Learning Order   |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 4: `get_concept_chain`

### Purpose

Find shortest path between two concepts (useful for discovering connections).

### Tool Specification

- **Input Parameters**:
  - `start_id` (required): string (UUID)
  - `end_id` (required): string (UUID)
  - `relationship_type` (optional): string (filter by type)
- **Expected Output**:
  ```json
  {
    "success": true,
    "path": [
      {
        "concept_id": "<UUID>",
        "name": "..."
      }
    ],
    "length": 3
  }
  ```

### Test Cases

#### Test 4.1: Direct Connection (Length 1)

**Description**: Find path between directly connected concepts
**Action**: Get path from Python Basics to Python Functions
**Expected Result**: Path of length 2 (start and end)

**Test Data**:

```
start_id: CONCEPT_A_ID (Python Basics)
end_id: CONCEPT_B_ID (Python Functions)
```

**Test Steps**:

1. Use MCP tool: `get_concept_chain` with directly connected concepts
2. Verify success = true
3. Verify path array has 2 items [A, B]
4. Verify length = 1 (one relationship)
5. Verify path shows: Basics → Functions

**Pass/Fail Criteria**:

- ✅ PASS: Path shows direct connection
- ❌ FAIL: Wrong path or length

---

#### Test 4.2: Multi-Hop Path

**Description**: Find path through multiple hops
**Action**: Get path from Python Basics to Django
**Expected Result**: Path through intermediate concepts

**Test Data**:

```
start_id: CONCEPT_A_ID (Python Basics)
end_id: CONCEPT_D_ID (Django)
```

**Test Steps**:

1. Use MCP tool: `get_concept_chain`
2. Verify path shows: Basics → Functions → Classes → Django
3. Verify length = 3 (three relationships)
4. Verify all intermediate concepts included

**Pass/Fail Criteria**:

- ✅ PASS: Shortest path found with correct length
- ❌ FAIL: Wrong path or missing intermediate concepts

---

#### Test 4.3: Same Start and End

**Description**: Query with same concept as start and end
**Action**: Get path from concept to itself
**Expected Result**: Single-node path with length 0

**Test Data**:

```
start_id: CONCEPT_A_ID
end_id: CONCEPT_A_ID (same)
```

**Test Steps**:

1. Use MCP tool: `get_concept_chain` with same ID
2. Verify success = true
3. Verify path has single item (the concept itself)
4. Verify length = 0

**Pass/Fail Criteria**:

- ✅ PASS: Single-node path, length 0
- ❌ FAIL: Error or wrong result

---

#### Test 4.4: No Path Exists

**Description**: Query concepts with no connection
**Action**: Find path between unconnected concepts
**Expected Result**: Empty path or clear message

**Test Steps**:

1. Create an isolated concept with no relationships
2. Use MCP tool: `get_concept_chain` from isolated to connected concept
3. Verify graceful response
4. Verify path is empty or message indicates no path

**Pass/Fail Criteria**:

- ✅ PASS: Graceful response indicating no path
- ❌ FAIL: Error or crash

---

#### Test 4.5: Filter by Relationship Type

**Description**: Find path using only specific relationship type
**Action**: Get path using only prerequisite relationships
**Expected Result**: Path using only specified type

**Test Data**:

```
start_id: CONCEPT_A_ID
end_id: CONCEPT_D_ID
relationship_type: "prerequisite"
```

**Test Steps**:

1. Use MCP tool: `get_concept_chain` with type filter
2. Verify path found
3. Verify only prerequisite relationships used
4. Should find: Basics → Functions → Classes → Django

**Pass/Fail Criteria**:

- ✅ PASS: Path uses only specified relationship type
- ❌ FAIL: Uses other relationship types

---

#### Test 4.6: Reverse Path

**Description**: Find path in opposite direction
**Action**: Get path from Django to Python Basics
**Expected Result**: Path exists (relationships are directed)

**Test Data**:

```
start_id: CONCEPT_D_ID (Django)
end_id: CONCEPT_A_ID (Python Basics)
```

**Test Steps**:

1. Use MCP tool: `get_concept_chain` in reverse direction
2. Check if path exists (depends on implementation - may use undirected search)
3. If path found, verify it's valid

**Pass/Fail Criteria**:

- ✅ PASS: Handles reverse direction appropriately
- ❌ FAIL: Error or unexpected behavior

**Note**: This tests whether shortestPath is directed or undirected.

---

#### Test 4.7: Invalid Start ID

**Description**: Query with non-existent start concept
**Action**: Use fake start_id
**Expected Result**: Not found error

**Test Data**:

```
start_id: "00000000-0000-0000-0000-000000000000"
end_id: CONCEPT_B_ID
```

**Test Steps**:

1. Use MCP tool: `get_concept_chain` with fake start
2. Expect not found error

**Pass/Fail Criteria**:

- ✅ PASS: Returns not found error
- ❌ FAIL: Different error or success

---

#### Test 4.8: Invalid End ID

**Description**: Query with non-existent end concept
**Action**: Use fake end_id
**Expected Result**: Not found error

**Test Data**:

```
start_id: CONCEPT_A_ID
end_id: "00000000-0000-0000-0000-000000000000"
```

**Test Steps**:

1. Use MCP tool: `get_concept_chain` with fake end
2. Expect not found error

**Pass/Fail Criteria**:

- ✅ PASS: Returns not found error
- ❌ FAIL: Different error or success

---

### Test Results for Tool 4

| Test Case             | Status | Notes | Timestamp |
| --------------------- | ------ | ----- | --------- |
| 4.1 Direct Connection |        |       |           |
| 4.2 Multi-Hop Path    |        |       |           |
| 4.3 Same Start/End    |        |       |           |
| 4.4 No Path           |        |       |           |
| 4.5 Filter by Type    |        |       |           |
| 4.6 Reverse Path      |        |       |           |
| 4.7 Invalid Start     |        |       |           |
| 4.8 Invalid End       |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Tool 5: `delete_relationship`

### Purpose

Soft delete relationships between concepts.

### Tool Specification

- **Input Parameters**:
  - `source_id` (required): string (UUID)
  - `target_id` (required): string (UUID)
  - `relationship_type` (required): string
- **Expected Output**:
  ```json
  {
    "success": true,
    "message": "Relationship deleted successfully"
  }
  ```

### Test Cases

#### Test 5.1: Delete Existing Relationship

**Description**: Delete a relationship created in Tool 1
**Action**: Delete specific relationship
**Expected Result**: Relationship removed

**Test Data**: Use source, target, type from Test 1.3 (Django → REST APIs)

**Test Steps**:

1. Verify relationship exists with `get_related_concepts`
2. Use MCP tool: `delete_relationship`
3. Verify success = true
4. Use `get_related_concepts` again
5. Verify relationship no longer appears

**Pass/Fail Criteria**:

- ✅ PASS: Relationship deleted and no longer appears
- ❌ FAIL: Delete fails or relationship still exists

---

#### Test 5.2: Delete Non-Existent Relationship

**Description**: Attempt to delete non-existent relationship
**Action**: Delete relationship that doesn't exist
**Expected Result**: Not found error or graceful response

**Test Data**:

```
source_id: CONCEPT_A_ID
target_id: CONCEPT_E_ID
relationship_type: "prerequisite"
(this relationship doesn't exist)
```

**Test Steps**:

1. Use MCP tool: `delete_relationship` for non-existent relationship
2. Check response

**Pass/Fail Criteria**:

- ✅ PASS: Graceful error about relationship not found
- ❌ FAIL: Crashes or unclear error

---

#### Test 5.3: Invalid Source ID

**Description**: Delete with non-existent source
**Action**: Use fake source_id
**Expected Result**: Not found error

**Test Data**:

```
source_id: "00000000-0000-0000-0000-000000000000"
target_id: CONCEPT_B_ID
relationship_type: "prerequisite"
```

**Test Steps**:

1. Use MCP tool: `delete_relationship` with fake source
2. Expect error

**Pass/Fail Criteria**:

- ✅ PASS: Returns not found error
- ❌ FAIL: Different error or success

---

#### Test 5.4: Invalid Target ID

**Description**: Delete with non-existent target
**Action**: Use fake target_id
**Expected Result**: Not found error

**Test Data**:

```
source_id: CONCEPT_A_ID
target_id: "00000000-0000-0000-0000-000000000000"
relationship_type: "prerequisite"
```

**Test Steps**:

1. Use MCP tool: `delete_relationship` with fake target
2. Expect error

**Pass/Fail Criteria**:

- ✅ PASS: Returns not found error
- ❌ FAIL: Different error or success

---

#### Test 5.5: Delete and Verify Chain Updated

**Description**: Verify deleting relationship breaks chain
**Action**: Delete middle link in prerequisite chain
**Expected Result**: Chain becomes shorter

**Test Steps**:

1. Get prerequisites of Django (should show full chain)
2. Delete B→C relationship (Functions → Classes)
3. Get prerequisites of Django again
4. Verify chain is shorter (only shows Classes)

**Pass/Fail Criteria**:

- ✅ PASS: Chain updated after deletion
- ❌ FAIL: Chain unchanged

---

#### Test 5.6: Idempotent Delete

**Description**: Delete same relationship twice
**Action**: Delete already-deleted relationship
**Expected Result**: Graceful response

**Test Data**: Use relationship from Test 5.1 (already deleted)

**Test Steps**:

1. Delete relationship (already done in 5.1)
2. Try to delete same relationship again
3. Check response (should be graceful)

**Pass/Fail Criteria**:

- ✅ PASS: Graceful response (already deleted or not found)
- ❌ FAIL: Crashes

---

#### Test 5.7: Verify Event Sourcing

**Description**: Verify delete creates event
**Action**: Delete relationship and check stats
**Expected Result**: Event count increases

**Test Steps**:

1. Get server stats and note event count
2. Delete a relationship
3. Get server stats again
4. Verify event count increased

**Pass/Fail Criteria**:

- ✅ PASS: Event count increased
- ❌ FAIL: Event count unchanged

---

#### Test 5.8: Certainty Score Recalculation

**Description**: Verify delete triggers certainty recalc
**Action**: Delete relationship and check scores
**Expected Result**: Scores may update

**Test Steps**:

1. Get source and target concepts, note certainty scores
2. Delete relationship between them
3. Wait 5-10 seconds (async processing)
4. Get concepts again
5. Check if scores changed

**Pass/Fail Criteria**:

- ✅ PASS: System processes without error
- ❌ FAIL: Error during processing

**Note**: Scores may not change, but should not error.

---

### Test Results for Tool 5

| Test Case               | Status | Notes | Timestamp |
| ----------------------- | ------ | ----- | --------- |
| 5.1 Delete Existing     |        |       |           |
| 5.2 Delete Non-Existent |        |       |           |
| 5.3 Invalid Source      |        |       |           |
| 5.4 Invalid Target      |        |       |           |
| 5.5 Chain Updated       |        |       |           |
| 5.6 Idempotent Delete   |        |       |           |
| 5.7 Event Sourcing      |        |       |           |
| 5.8 Certainty Recalc    |        |       |           |

**Overall Tool Status**: [ ] PASS [ ] FAIL

---

## Phase 3 Summary

### Overall Phase Results

**Tools Tested**: 5/5

- [ ] Tool 1: create_relationship
- [ ] Tool 2: get_related_concepts
- [ ] Tool 3: get_prerequisites
- [ ] Tool 4: get_concept_chain
- [ ] Tool 5: delete_relationship

**Total Test Cases**: 46

**Pass/Fail Summary**:

- Tests Passed: **\_** / 46
- Tests Failed: **\_** / 46
- Success Rate: **\_**%

### Graph Quality Assessment

#### Relationship Creation

- Type validation: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Constraint enforcement: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Event sourcing: [ ] Excellent [ ] Good [ ] Fair [ ] Poor

#### Graph Traversal

- Accuracy: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Performance: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Depth handling: [ ] Excellent [ ] Good [ ] Fair [ ] Poor

#### Learning Paths

- Prerequisite chains: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Shortest path: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Relationship filtering: [ ] Excellent [ ] Good [ ] Fair [ ] Poor

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

**Next Phase**: Phase 4 - Analytics & System Management
