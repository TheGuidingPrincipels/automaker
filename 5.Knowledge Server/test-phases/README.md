# MCP Knowledge Server Test Suite

This directory contains a comprehensive, end-to-end test suite for the MCP Knowledge Server. The test suite is designed to be executed by Claude Desktop sessions in a phased approach.

## 📋 Quick Start

1. **Read the Overview**: Start with `TEST-SUITE-OVERVIEW.md` to understand the test architecture
2. **Verify Prerequisites**: Ensure Neo4j, ChromaDB, and MCP server are running
3. **Execute Phase 1**: Open `PHASE-1-Foundation-and-Basic-Concepts.md` and begin testing
4. **Continue Sequentially**: Complete phases 2, 3, and 4 in order
5. **Generate Report**: Use `TEST-REPORT-TEMPLATE.md` to document your results

## 📁 Files in This Directory

### Core Documents

- **`TEST-SUITE-OVERVIEW.md`** - Start here! Complete overview of the test suite architecture, execution model, and guidelines
- **`TEST-REPORT-TEMPLATE.md`** - Template for final test report after completing all phases

### Test Phase Documents

- **`PHASE-1-Foundation-and-Basic-Concepts.md`** - 6 tools, 30 tests (45-60 minutes)
  - Basic connectivity, CRUD operations for concepts

- **`PHASE-2-Search-and-Discovery.md`** - 3 tools, 30 tests (30-45 minutes)
  - Semantic search, exact search, recent concepts

- **`PHASE-3-Relationship-Management.md`** - 5 tools, 46 tests (60-75 minutes)
  - Creating relationships, graph traversal, learning paths

- **`PHASE-4-Analytics-and-System-Management.md`** - 3 tools, 32 tests (30-40 minutes)
  - Hierarchy visualization, quality filtering, server statistics

## 🎯 Test Suite Statistics

- **Total Tools**: 17
- **Total Test Cases**: 138
- **Total Phases**: 4
- **Estimated Duration**: 3-4 hours
- **Test Coverage**: All MCP server tools and features

## 🚀 Execution Model

### Key Principles

1. **Sequential Execution**: Complete phases in order (1 → 2 → 3 → 4)
2. **One Tool at a Time**: Test each tool completely before moving to the next
3. **Mandatory Breaks**: Take breaks between tools for review and coordination
4. **Document Everything**: Record all results, issues, and observations
5. **Save Test Data**: Preserve concept IDs and relationship IDs for cross-phase validation

### Testing Flow

```
Phase 1 (Foundation)
    ↓
Phase 2 (Search & Discovery)
    ↓
Phase 3 (Relationship Management)
    ↓
Phase 4 (Analytics & Management)
    ↓
Final Report
```

## 📊 Test Categories

### By Tool Category

| Category      | Tools | Tests | File    |
| ------------- | ----- | ----- | ------- |
| System        | 2     | 4     | Phase 1 |
| Concept CRUD  | 4     | 30    | Phase 1 |
| Search        | 3     | 30    | Phase 2 |
| Relationships | 5     | 46    | Phase 3 |
| Analytics     | 3     | 32    | Phase 4 |

### By Test Type

- **Happy Path** (~45 tests): Normal, expected usage
- **Edge Cases** (~38 tests): Boundary conditions and special cases
- **Error Handling** (~35 tests): Invalid inputs and error scenarios
- **Validation** (~20 tests): Input validation and sanitization

## ✅ Prerequisites

Before starting the test suite, ensure:

### System Requirements

- [x] Neo4j 5.x running on `bolt://localhost:7687`
- [x] Python 3.11+
- [x] MCP Knowledge Server running
- [x] Claude Desktop connected to MCP server
- [x] ChromaDB persistent storage: `./data/chroma`
- [x] Event Store database: `./data/events.db`
- [x] Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

### Environment Variables

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
CHROMA_PERSIST_DIRECTORY=./data/chroma
EVENT_STORE_PATH=./data/events.db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## 🎓 For Testers

### Before You Start

1. Read `TEST-SUITE-OVERVIEW.md` completely
2. Verify all prerequisites are met
3. Ensure you have 3-4 hours available
4. Prepare note-taking system
5. Coordinate with test lead

### During Testing

1. Follow test cases exactly as written
2. Test ONE tool at a time
3. Document results immediately
4. Take breaks between tools
5. Report issues as you find them
6. Save important IDs (concept_id, relationship_id)

### After Each Phase

1. Complete phase summary section
2. Calculate success rate
3. List all issues found
4. Take a longer break
5. Get approval to continue

### After All Phases

1. Use `TEST-REPORT-TEMPLATE.md`
2. Compile all results
3. Calculate overall statistics
4. Make production readiness decision

## 🎯 For Coordinators

### Your Responsibilities

1. **Pre-Test**: Ensure environment is ready, assign testers
2. **During Test**: Monitor progress, review at break points, approve continuation
3. **Post-Test**: Collect reports, calculate metrics, make final decision

### Break Point Reviews

Approve continuation at each break point by reviewing:

- Results documented completely
- Issues properly categorized
- No critical blockers
- Tester ready to continue

## 📈 Success Criteria

### Per Phase

- **Excellent**: ≥95% pass rate
- **Good**: 85-94% pass rate
- **Acceptable**: 75-84% pass rate
- **Needs Work**: <75% pass rate

### Overall

```
Overall Success = (Total Passed / 138) × 100%
```

### Production Readiness

- **Production Ready**: ≥95% overall, no critical issues
- **Needs Minor Fixes**: 85-94% overall, only minor issues
- **Needs Major Fixes**: 75-84% overall, some critical issues
- **Not Ready**: <75% overall or multiple critical issues

## 🐛 Issue Severity Levels

### Critical (Blocks Production)

- Server crashes or data corruption
- Complete tool failure
- Data loss or inconsistency
- Security vulnerabilities

### Major (Degrades Functionality)

- Partial tool failure
- Incorrect results
- Performance issues
- Missing features

### Minor (Cosmetic or Edge Case)

- Unclear error messages
- Missing validations
- Suboptimal UX
- Documentation issues

## 📝 Test Data Management

### Phase 1 Creates

- BASIC_CONCEPT_ID
- CATEGORIZED_CONCEPT_ID
- SOURCED_CONCEPT_ID

### Phase 2 Creates

- Machine Learning concept
- Neural Networks concept
- Data Structures concept

### Phase 3 Creates

- CONCEPT_A_ID through CONCEPT_E_ID (Python learning path)
- REL_1_ID through REL_5_ID (various relationships)

### Phase 4 Uses

- All data from previous phases
- Creates additional test concepts as needed

## 🔍 What Gets Tested

### Concept Operations

- Create, read, update, delete
- Input validation
- Field constraints
- Source URLs
- Certainty scoring

### Search Capabilities

- Semantic search (AI-powered)
- Exact/filtered search
- Time-based retrieval
- Combined filters
- Sort ordering

### Relationship Management

- Four relationship types
- Graph traversal
- Multi-hop queries
- Learning paths
- Shortest path finding

### Analytics

- Hierarchy visualization
- Quality-based filtering
- System statistics
- Event sourcing
- Outbox processing

### System Health

- Connectivity
- Service availability
- Performance
- Data integrity
- Error handling

## 📚 Additional Resources

### Codebase References

**Tool Implementations**:

- `tools/concept_tools.py` - Concept CRUD operations
- `tools/search_tools.py` - Search and discovery
- `tools/relationship_tools.py` - Graph relationships
- `tools/analytics_tools.py` - Hierarchy and statistics
- `mcp_server.py` - Server and system tools

**Services**:

- `services/repository.py` - Dual storage repository
- `services/neo4j_service.py` - Graph database
- `services/chromadb_service.py` - Vector database
- `services/embedding_service.py` - Semantic embeddings
- `services/event_store.py` - Event sourcing

### Documentation

- Main README: `../README.md`
- API Documentation: `../docs/API.md`
- Architecture: `../docs/ARCHITECTURE.md`
- Backup & Restore: `../docs/BACKUP_AND_RESTORE.md`

## 🎉 Tips for Success

1. **Don't Rush**: Take your time with each test
2. **Document Everything**: Write down observations immediately
3. **Ask Questions**: If something is unclear, ask the coordinator
4. **Take Breaks**: Breaks are mandatory, not optional
5. **Be Thorough**: Don't skip tests even if they seem redundant
6. **Stay Organized**: Keep track of IDs and test data
7. **Report Issues Immediately**: Don't wait until the end
8. **Celebrate Wins**: Acknowledge successful tests!

## 🆘 Troubleshooting

### Common Issues

**Issue**: Semantic search returns no results
**Solution**: Check embedding service is running, verify model is loaded

**Issue**: Tools showing as unavailable
**Solution**: Run `get_tool_availability` to check service status, verify Neo4j and ChromaDB are running

**Issue**: High outbox pending count
**Solution**: Check database connectivity, review server logs for errors

**Issue**: Certainty scores are all 0
**Solution**: Verify confidence service is running, check for async processing errors

### Getting Help

1. Check the tool specification in the phase document
2. Review error messages carefully
3. Consult the test coordinator
4. Check server logs for details
5. Verify environment prerequisites

## 📞 Support

For questions or issues with the test suite:

- Contact test coordinator
- Review `TEST-SUITE-OVERVIEW.md`
- Check tool specifications in phase documents
- Consult codebase documentation

## 📜 Version History

- **v1.0** (2025-11-13): Initial comprehensive test suite creation
  - 4 test phases covering all 17 tools
  - 138 total test cases
  - Complete documentation and templates

---

**Ready to start testing?** Begin with `TEST-SUITE-OVERVIEW.md` for the complete picture, then dive into `PHASE-1-Foundation-and-Basic-Concepts.md` to begin your testing journey!

Good luck! 🚀
