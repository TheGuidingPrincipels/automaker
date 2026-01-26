# User Acceptance Testing (UAT) Plan

# MCP Knowledge Server

**Version**: 1.0
**Date**: 2025-10-07
**Test Environment**: Production Configuration
**Tester**: Automated + Manual Validation

---

## Executive Summary

This UAT plan validates the MCP Knowledge Server's readiness for production deployment through real-world scenarios that simulate actual user workflows. The testing covers all 16 MCP tools, performance characteristics, error handling, and integration with Claude Desktop.

### Objectives

1. Validate all MCP tools work correctly in production environment
2. Test real-world knowledge management workflows
3. Verify performance meets token efficiency targets
4. Confirm error handling and recovery mechanisms
5. Validate backup/restore and monitoring infrastructure
6. Ensure seamless Claude Desktop integration

### Success Criteria

- ✅ 100% test scenario pass rate
- ✅ Zero critical bugs
- ✅ Performance within token efficiency targets
- ✅ All 16 MCP tools functional
- ✅ Backup/restore successfully tested
- ✅ Monitoring and health checks operational

---

## Test Environment Setup

### Prerequisites

1. Production environment configured (`.env.production`)
2. Neo4j database running and accessible
3. ChromaDB initialized with embeddings
4. SQLite event store created
5. All dependencies installed
6. Monitoring scripts operational

### Verification Steps

```bash
# 1. Check production environment
cd /Users/ruben/Documents/GitHub/automaker/5.Knowledge Server
source .venv/bin/activate

# 2. Run readiness check
python tests/uat/uat_readiness_check.py

# 3. Verify databases
python -c "from services.neo4j_service import Neo4jService; Neo4jService().test_connection()"
python -c "from services.chromadb_service import ChromaDBService; ChromaDBService().test_connection()"

# 4. Check monitoring
python monitoring/health_check.py
```

---

## Test Scenarios

### Scenario 1: Knowledge Base Creation (Foundation)

**Objective**: Build a complete knowledge graph from scratch
**Duration**: 15 minutes
**Priority**: Critical

#### Test Steps

1. **Create foundational concepts**
   - Create "Python Programming" concept
   - Create "Object-Oriented Programming" concept
   - Create "Functions" concept
   - Create "Variables" concept
   - Create "Data Structures" concept

2. **Build relationships**
   - Link "Functions" as prerequisite for "Object-Oriented Programming"
   - Link "Variables" as prerequisite for "Functions"
   - Create hierarchy: Python → OOP → Functions → Variables

3. **Validate structure**
   - Query hierarchy with `list_hierarchy`
   - Verify prerequisite chains with `get_prerequisites`
   - Check concept chains with `get_concept_chain`

#### Expected Results

- All concepts created successfully
- Relationships correctly established
- Hierarchy navigation works correctly
- No orphaned concepts

#### Tools Tested

- `create_concept` (5 uses)
- `create_relationship` (4 uses)
- `list_hierarchy` (1 use)
- `get_prerequisites` (2 uses)
- `get_concept_chain` (1 use)

---

### Scenario 2: Concept Management (CRUD Operations)

**Objective**: Validate all CRUD operations work correctly
**Duration**: 10 minutes
**Priority**: Critical

#### Test Steps

1. **Create** - Add new concept "Machine Learning"
2. **Read** - Retrieve concept with `get_concept`
3. **Update** - Modify description and add examples
4. **Delete** - Remove concept and verify deletion

#### Expected Results

- Create returns success with concept_id
- Read returns full concept details
- Update modifies only specified fields
- Delete removes concept from both databases
- Token counts within targets (create<50, get<300, update<50, delete<30)

#### Tools Tested

- `create_concept`
- `get_concept`
- `update_concept`
- `delete_concept`

---

### Scenario 3: Search Operations (Discovery)

**Objective**: Validate search functionality finds relevant concepts
**Duration**: 15 minutes
**Priority**: Critical

#### Test Steps

1. **Semantic Search**
   - Search for "programming concepts" (should find Python, OOP, Functions)
   - Search for "learning algorithms" (should find ML concepts)
   - Search for "code organization" (should find OOP, Functions)

2. **Exact Search**
   - Search by name "Python"
   - Search by description keyword "object"
   - Search by subtopic "programming"

3. **Recent Concepts**
   - Get last 10 created concepts
   - Verify order is chronological

#### Expected Results

- Semantic search returns relevant concepts ranked by similarity
- Exact search finds precise matches
- Recent concepts ordered correctly
- Results include all necessary fields
- Token counts within targets (searches<200, but may exceed with 10 results)

#### Tools Tested

- `search_concepts_semantic` (3 uses)
- `search_concepts_exact` (3 uses)
- `get_recent_concepts` (1 use)

---

### Scenario 4: Relationship Building (Graph Construction)

**Objective**: Create and manage complex relationship networks
**Duration**: 15 minutes
**Priority**: High

#### Test Steps

1. **Create prerequisite chain**
   - Variables → Functions → Classes → Inheritance → Polymorphism

2. **Create related concepts**
   - Link "Encapsulation" as related to "Classes"
   - Link "Abstraction" as related to "Classes"

3. **Query relationships**
   - Get all related concepts for "Classes"
   - Get prerequisite chain from "Polymorphism" to root

4. **Delete relationships**
   - Remove one relationship
   - Verify it's deleted but concepts remain

#### Expected Results

- Relationships created bidirectionally
- Prerequisite chains navigable
- Related concepts queryable
- Relationship deletion doesn't affect concepts

#### Tools Tested

- `create_relationship` (multiple uses)
- `get_related_concepts` (2 uses)
- `get_prerequisites` (2 uses)
- `delete_relationship` (1 use)

---

### Scenario 5: Hierarchy Navigation (Complex Queries)

**Objective**: Navigate complex concept hierarchies
**Duration**: 10 minutes
**Priority**: High

#### Test Steps

1. **Build deep hierarchy**
   - Create 5-level deep concept tree
   - Programming → Python → OOP → Classes → Inheritance → Polymorphism

2. **Query full hierarchy**
   - Use `list_hierarchy` to get complete tree
   - Verify all levels present

3. **Get concept chains**
   - Query chain from root to leaf
   - Query chain from leaf to root

4. **Test prerequisites**
   - Get all prerequisites for leaf concept
   - Verify transitive prerequisites included

#### Expected Results

- Hierarchy fully navigable
- All levels correctly represented
- Chains complete and ordered
- Prerequisites include transitive dependencies

#### Tools Tested

- `list_hierarchy`
- `get_concept_chain`
- `get_prerequisites`

---

### Scenario 6: Batch Operations (Concurrency)

**Objective**: Test system under concurrent load
**Duration**: 15 minutes
**Priority**: High

#### Test Steps

1. **Batch create** - Add 50 concepts in rapid succession
2. **Batch update** - Modify 20 concepts concurrently
3. **Batch search** - Perform 20 semantic searches
4. **Batch relationships** - Create 30 relationships

#### Expected Results

- All operations complete successfully
- No race conditions or conflicts
- Event store maintains consistency
- No duplicate concepts created
- Response times acceptable (<500ms per operation)

#### Tools Tested

- All CRUD and search tools under load

---

### Scenario 7: Error Recovery (Failure Handling)

**Objective**: Validate graceful error handling
**Duration**: 10 minutes
**Priority**: Critical

#### Test Steps

1. **Invalid inputs**
   - Create concept with missing required fields
   - Update non-existent concept
   - Delete already-deleted concept

2. **Database failures** (simulated)
   - Attempt operation with Neo4j unavailable
   - Verify EventStore preserves data
   - Verify Outbox queues for retry

3. **Validation errors**
   - Invalid certainty score (outside 0-1)
   - Invalid relationship type
   - Duplicate concept name

#### Expected Results

- All errors handled gracefully
- Descriptive error messages returned
- No system crashes
- EventStore maintains consistency
- Failed operations queued for retry

#### Tools Tested

- All tools with invalid inputs
- Error handling utilities

---

### Scenario 8: Performance Testing (Load)

**Objective**: Validate performance under realistic load
**Duration**: 20 minutes
**Priority**: High

#### Test Steps

1. **Create knowledge base** - Add 100 concepts with relationships
2. **Search performance** - 50 semantic searches
3. **Hierarchy queries** - Query 100-concept hierarchy
4. **Token efficiency** - Measure response sizes

#### Expected Results

- Database handles 100+ concepts
- Search remains responsive (<1s)
- Hierarchy queries complete (<2s)
- Token counts within targets for simple operations
- Memory usage acceptable (<500MB)

#### Metrics Collected

- Response times (p50, p95, p99)
- Token counts per operation
- Memory usage
- Database query times

---

### Scenario 9: Claude Desktop Integration (End-to-End)

**Objective**: Validate seamless Claude Desktop integration
**Duration**: 15 minutes
**Priority**: Critical

#### Test Steps

1. **Server startup** - Start MCP server via Claude Desktop config
2. **Tool availability** - Verify all 16 tools visible
3. **Real conversations** - Use tools through natural language
   - "Create a concept about Python"
   - "Search for programming concepts"
   - "Show me the hierarchy"

4. **Error handling** - Trigger errors and verify messages

#### Expected Results

- Server starts without errors
- All 16 tools available in Claude Desktop
- Natural language invocations work
- Responses formatted correctly
- Errors displayed clearly

#### Tools Tested

- All 16 MCP tools through Claude Desktop UI

---

### Scenario 10: Backup & Restore Cycle (Disaster Recovery)

**Objective**: Validate complete backup and restore functionality
**Duration**: 20 minutes
**Priority**: Critical

#### Test Steps

1. **Create test data** - Build knowledge base with 20 concepts
2. **Run backup** - Execute `backup/backup_all.sh`
3. **Verify backup** - Check backup files created
4. **Simulate disaster** - Clear all databases
5. **Restore** - Execute `backup/restore_all.sh`
6. **Validate restoration** - Verify all data restored correctly

#### Expected Results

- Backup creates all database dumps
- Backup manifest JSON created
- Restore completes without errors
- All concepts restored correctly
- Relationships intact after restore
- Event store consistency maintained

#### Tools Tested

- Backup scripts
- Restore scripts
- Data consistency validation

---

## Integration Test

### Comprehensive System Validation

**Objective**: Validate entire system working together in production configuration

#### Test Flow

1. **Environment Setup**
   - Load production configuration
   - Start all services (Neo4j, ChromaDB)
   - Initialize monitoring

2. **Functional Testing**
   - Execute all 10 UAT scenarios sequentially
   - Log results for each scenario
   - Capture performance metrics

3. **Infrastructure Testing**
   - Health checks pass (all databases accessible)
   - Monitoring exports metrics correctly
   - Backup completes successfully
   - Restore works correctly

4. **Claude Desktop Testing**
   - Connect to MCP server
   - Execute real conversations
   - Verify all tools functional
   - Test error handling

5. **Results Collection**
   - Generate comprehensive test report
   - Document any failures or issues
   - Collect performance metrics
   - Create recommendations

#### Success Criteria

- ✅ All 10 scenarios pass
- ✅ Zero critical or major bugs
- ✅ Health checks pass
- ✅ Backup/restore successful
- ✅ Claude Desktop integration works
- ✅ Performance meets targets

---

## Test Data Requirements

### Concept Categories

1. **Programming** (15 concepts)
   - Python, JavaScript, Java
   - OOP, Functional Programming
   - Variables, Functions, Classes

2. **Data Science** (10 concepts)
   - Machine Learning, Deep Learning
   - Neural Networks, Regression
   - Data Cleaning, Feature Engineering

3. **Web Development** (10 concepts)
   - HTML, CSS, JavaScript
   - React, Vue, Angular
   - REST APIs, GraphQL

4. **DevOps** (10 concepts)
   - Docker, Kubernetes
   - CI/CD, Jenkins
   - Monitoring, Logging

### Relationship Types

- Prerequisites (30 relationships)
- Related concepts (20 relationships)
- Hierarchical (15 relationships)

---

## Test Execution Procedure

### Automated Testing

```bash
# Run automated UAT suite
cd /Users/ruben/Documents/GitHub/automaker/5.Knowledge Server
source .venv/bin/activate
python tests/uat/uat_runner.py --verbose --report

# View results
cat tests/uat/uat_results.json
```

### Manual Testing

1. Start Claude Desktop
2. Verify MCP server connection
3. Execute test scenarios through conversation
4. Document results manually

---

## Defect Management

### Severity Levels

- **Critical**: System crash, data loss, security issue
- **Major**: Feature not working, significant performance issue
- **Minor**: UI issue, minor bug, improvement opportunity
- **Trivial**: Documentation typo, cosmetic issue

### Reporting Template

```markdown
**ID**: UAT-XXX
**Severity**: Critical/Major/Minor/Trivial
**Scenario**: [Scenario name]
**Steps to Reproduce**: [List steps]
**Expected**: [Expected behavior]
**Actual**: [Actual behavior]
**Environment**: Production config
**Status**: Open/Fixed/Won't Fix
```

---

## Acceptance Criteria

### Must Have (All must pass)

- ✅ All 16 MCP tools functional
- ✅ No critical or major bugs
- ✅ Backup/restore works correctly
- ✅ Claude Desktop integration successful
- ✅ Performance within acceptable ranges
- ✅ Error handling graceful and informative
- ✅ Documentation complete and accurate

### Should Have (90% pass rate acceptable)

- Token efficiency targets met for simple operations
- Response times < 1 second for most operations
- Memory usage < 500MB under load
- All test scenarios pass without modification

---

## Sign-off

### Test Execution Sign-off

- [ ] All test scenarios executed
- [ ] Results documented
- [ ] Defects logged and triaged
- [ ] Performance metrics collected

### UAT Approval

- [ ] Product Owner approval
- [ ] Technical lead approval
- [ ] Documentation complete
- [ ] Ready for production deployment

**Tester**: ******\_\_\_\_******
**Date**: ******\_\_\_\_******
**Signature**: ******\_\_\_\_******
