# Short-Term Memory MCP - Master Test Execution Guide

## 📋 Overview

This guide provides comprehensive end-to-end testing instructions for the Short-Term Memory MCP server. The test suite is divided into **6 phases**, testing all **28 MCP tools** systematically.

**Total Estimated Time**: 4-6 hours (can be spread across multiple sessions)

---

## 🎯 Testing Objectives

1. **Functional Verification**: Ensure all 28 MCP tools work correctly
2. **End-to-End Workflows**: Test realistic user workflows
3. **Performance Validation**: Verify response times meet targets
4. **Error Handling**: Confirm graceful error handling
5. **Data Integrity**: Ensure data persistence and consistency
6. **Cache Behavior**: Validate 5-minute cache TTL and invalidation
7. **Production Readiness**: Assess monitoring and health capabilities

---

## 📦 Test Phases

| Phase                                       | Focus                      | Tools   | Time      | Dependencies       |
| ------------------------------------------- | -------------------------- | ------- | --------- | ------------------ |
| [Phase 1](PHASE-1-Foundation.md)            | Session & Concept Basics   | 6 tools | 45-60 min | None               |
| [Phase 2](PHASE-2-Pipeline-Data-Storage.md) | Pipeline Data & Storage    | 6 tools | 45-60 min | Phase 1            |
| [Phase 3](PHASE-3-Research-Cache.md)        | Research Cache System      | 6 tools | 45-60 min | None (independent) |
| [Phase 4](PHASE-4-Code-Teacher.md)          | Code Teacher Integration   | 3 tools | 30-45 min | Phase 1            |
| [Phase 5](PHASE-5-Knowledge-Graph.md)       | Knowledge Graph            | 4 tools | 45-60 min | Phase 1            |
| [Phase 6](PHASE-6-Monitoring.md)            | Monitoring & System Health | 3 tools | 30-45 min | None (independent) |

### Phase Dependencies

```
Phase 1 (Foundation)
  ├─> Phase 2 (builds on Phase 1 data)
  ├─> Phase 4 (needs today's session)
  └─> Phase 5 (needs concepts)

Phase 3 (Research Cache) - Independent

Phase 6 (Monitoring) - Independent
```

---

## 🛠️ Prerequisites

### System Requirements

- [ ] Short-Term Memory MCP server installed and running
- [ ] Claude Desktop configured with Short-Term Memory MCP
- [ ] Database initialized (SQLite)
- [ ] Python 3.11+ environment
- [ ] All dependencies installed (`uv sync`)

### Testing Environment

- [ ] Fresh database OR willing to work with existing data
- [ ] Multiple Claude Desktop sessions available (recommended)
- [ ] Timer or clock for cache TTL testing
- [ ] Note-taking tool for recording results
- [ ] Access to create GitHub issues (if bugs found)

### Knowledge Requirements

- [ ] Familiarity with MCP (Model Context Protocol)
- [ ] Understanding of Claude Desktop tool usage
- [ ] Basic understanding of the SHOOT pipeline (Research → AIM → SHOOT → SKIN)

---

## 🚀 Quick Start

### Option A: Complete Test Run (4-6 hours)

Execute all phases sequentially in a single session:

1. Start with Phase 1 (Foundation)
2. Continue through Phase 2 (using Phase 1 data)
3. Run Phase 3 (Research Cache) - independent
4. Run Phase 4 (Code Teacher) - needs today's session
5. Run Phase 5 (Knowledge Graph) - builds on existing concepts
6. Finish with Phase 6 (Monitoring)

### Option B: Incremental Testing (Multiple Sessions)

Spread testing across multiple days:

**Day 1**: Phases 1-2 (Core functionality)
**Day 2**: Phases 3-4 (Cache and Code Teacher)
**Day 3**: Phases 5-6 (Knowledge Graph and Monitoring)

### Option C: Independent Phase Testing

Test individual phases as needed:

- **Phase 3** (Research Cache) - Can run independently
- **Phase 6** (Monitoring) - Can run independently
- **Other phases** - Require setup from Phase 1

---

## 📋 Execution Instructions

### Before Starting

1. **Review the test phase file** you're about to execute
2. **Prepare your environment**:
   - Open Claude Desktop
   - Ensure MCP server is running
   - Have the test phase markdown file open
3. **Create a results document** to record findings
4. **Note the start time**

### During Testing

1. **Follow the test steps exactly** as written in each phase
2. **Test one tool at a time** - wait for results before proceeding
3. **Record results** at each checkpoint
4. **Stop at checkpoints** - this is important for reviewing results
5. **Document any issues** immediately
6. **Take breaks** between phases

### After Each Test

1. **Complete the phase test report** (at end of each phase file)
2. **Review findings** before moving to next phase
3. **Create GitHub issues** for any bugs found
4. **Update test status** (Pass/Fail)

### After Each Phase

1. **Assess phase outcome**: Pass / Pass with Issues / Fail
2. **If PASS**: Proceed to next phase
3. **If FAIL**: Document issues and fix before continuing
4. **Save your test report** for final summary

---

## 🔍 What to Test

### Phase 1: Foundation - Session & Concept Basics

**Tools**: 6 core session management tools

**Key Workflows**:

- Create daily session with goals
- Store multiple concepts from research
- Query and filter concepts
- Update concept status through pipeline
- Verify data persistence

**Success Criteria**:

- Session creation works
- Bulk concept storage succeeds
- Status transitions (identified → stored) work
- Filtering by status works

### Phase 2: Pipeline Data & Storage

**Tools**: 6 pipeline and storage tools

**Key Workflows**:

- Store stage-specific data (research, aim, shoot, skin)
- Retrieve stage data
- Mark concepts as stored in Knowledge MCP
- Complete session workflow
- Manual cleanup operations

**Success Criteria**:

- All 4 stages store data correctly
- UPSERT behavior works
- Knowledge MCP integration works
- Session completion validates unstored concepts
- Cascade deletion works

### Phase 3: Research Cache System

**Tools**: 6 research cache tools

**Key Workflows**:

- Cache miss/hit behavior
- Research triggering (mock)
- Cache UPSERT operations
- Domain whitelist CRUD
- Quality scoring

**Success Criteria**:

- Cache hit/miss detection works
- UPSERT inserts new, updates existing
- Domain whitelist management works
- Category filtering works
- Case-insensitive concept matching

### Phase 4: Code Teacher Integration

**Tools**: 3 cached query tools

**Key Workflows**:

- Get today's concepts (full data)
- Get today's learning goals (lightweight)
- Search today's concepts
- Cache hit/miss performance
- 5-minute TTL expiration

**Success Criteria**:

- Cache provides 5x+ speedup
- Cache hit < 100ms
- Cache invalidation on concept changes
- 5-minute TTL respected
- Per-query caching for searches

### Phase 5: Knowledge Graph

**Tools**: 4 relationship and question tools

**Key Workflows**:

- Add user questions to concepts
- Create relationships (4 types)
- Get comprehensive concept page
- Query and traverse relationships
- Build knowledge graph

**Success Criteria**:

- Questions tracked by stage
- All 4 relationship types work
- Comprehensive concept page shows everything
- Relationship traversal works
- Graph connectivity established

### Phase 6: Monitoring & System Health

**Tools**: 3 monitoring tools

**Key Workflows**:

- Health check (database, cache status)
- System metrics (performance, operations)
- Error log retrieval
- Production readiness assessment

**Success Criteria**:

- Health check < 100ms
- Metrics accurately reflect system state
- Error log tracks system errors
- All monitoring data accessible
- Production recommendations documented

---

## ✅ Success Criteria by Phase

### Phase 1: Foundation ✓

- [ ] 6/6 tools pass
- [ ] Session created with 5+ concepts
- [ ] All status transitions work
- [ ] Response times < 1 second

### Phase 2: Pipeline Data & Storage ✓

- [ ] 6/6 tools pass
- [ ] All 4 stages store data
- [ ] Knowledge MCP IDs assigned
- [ ] Session marked complete
- [ ] Response times < 1 second

### Phase 3: Research Cache ✓

- [ ] 6/6 tools pass
- [ ] Cache hit/miss behavior correct
- [ ] UPSERT works
- [ ] Domain whitelist functional
- [ ] Response times < 500ms

### Phase 4: Code Teacher ✓

- [ ] 3/3 tools pass
- [ ] Cache provides 5x+ speedup
- [ ] Cache hit < 100ms
- [ ] TTL expiration works
- [ ] Cache invalidation works

### Phase 5: Knowledge Graph ✓

- [ ] 4/4 tools pass
- [ ] Questions added to concepts
- [ ] All relationship types work
- [ ] Knowledge graph built
- [ ] Response times < 500ms

### Phase 6: Monitoring ✓

- [ ] 3/3 tools pass
- [ ] System reports healthy
- [ ] Metrics tracked correctly
- [ ] Error log functional
- [ ] Production ready (or issues documented)

---

## 📊 Test Reporting

### Individual Phase Reports

Each phase has a test report template at the end of the phase file. Complete it after finishing the phase.

### Final Test Summary

After completing all phases, create a final summary report using the [Final Test Report Template](FINAL-TEST-REPORT.md).

### Issue Tracking

Create GitHub issues for:

- **Critical**: Crashes, data loss, broken core functionality
- **High**: Incorrect behavior, performance issues, data integrity problems
- **Medium**: Unexpected behavior, missing validations, poor error messages
- **Low**: Documentation issues, minor UX improvements

---

## 🐛 Troubleshooting

### MCP Server Not Responding

1. Check server is running: `ps aux | grep mcp`
2. Check logs: `tail -f ~/.mcp/logs/short-term-memory.log` (or server log location)
3. Restart server
4. Verify Claude Desktop configuration

### Database Issues

1. Check database file exists: `ls -lh ~/.mcp/short-term-memory.db` (or configured location)
2. Check file permissions
3. Try reading database: `sqlite3 ~/.mcp/short-term-memory.db ".tables"`
4. Check database integrity: `sqlite3 ~/.mcp/short-term-memory.db "PRAGMA integrity_check;"`

### Cache Issues

1. Cache TTL is 5 minutes - wait for expiration
2. Cache invalidates on concept modifications
3. Cache is in-memory - restart clears cache
4. Check cache size with `health_check`

### Performance Issues

1. Check database size with `get_system_metrics`
2. Review operation counts
3. Check for slow queries (avg_ms > 500ms)
4. Consider database cleanup if large

### Test Failures

1. **Document the failure** - exact steps, expected vs actual
2. **Check prerequisites** - did you complete dependent phases?
3. **Review error messages** - what is the tool returning?
4. **Verify data state** - is database in expected state?
5. **Create GitHub issue** if confirmed bug

---

## 🎯 Testing Best Practices

### Do's ✅

- ✅ Follow test steps exactly as written
- ✅ Stop at checkpoints to review results
- ✅ Record response times accurately
- ✅ Document all issues immediately
- ✅ Complete phase reports before moving on
- ✅ Take breaks between phases
- ✅ Test error cases (invalid inputs)
- ✅ Verify data persistence

### Don'ts ❌

- ❌ Skip steps or checkpoints
- ❌ Rush through tests
- ❌ Assume something works without testing
- ❌ Ignore error messages
- ❌ Modify test procedures without documentation
- ❌ Test multiple things simultaneously
- ❌ Continue after critical failures

---

## 📈 Performance Targets

| Operation                          | Target  | Critical |
| ---------------------------------- | ------- | -------- |
| Session creation                   | < 50ms  | < 200ms  |
| Bulk concept storage (10 concepts) | < 200ms | < 1s     |
| Concept query                      | < 50ms  | < 200ms  |
| Status update                      | < 100ms | < 500ms  |
| Stage data store                   | < 100ms | < 500ms  |
| Cache hit                          | < 100ms | < 200ms  |
| Cache miss                         | < 500ms | < 2s     |
| Health check                       | < 50ms  | < 100ms  |
| System metrics                     | < 200ms | < 500ms  |
| Search                             | < 300ms | < 1s     |

**Target**: Ideal performance
**Critical**: Maximum acceptable performance

---

## 🔐 Data Integrity Checks

Throughout testing, verify:

- [ ] Data persists after operations
- [ ] Updates don't corrupt existing data
- [ ] Cascade deletes work correctly
- [ ] Timestamps are recorded accurately
- [ ] Relationships are bidirectional (where applicable)
- [ ] Cache invalidation doesn't lose data
- [ ] Concurrent operations don't cause corruption

---

## 🎓 Learning Outcomes

After completing all tests, you should understand:

1. **How the SHOOT pipeline works** (Research → AIM → SHOOT → SKIN)
2. **How concepts progress** through statuses (identified → chunked → encoded → evaluated → stored)
3. **How caching optimizes** performance (5-minute TTL, invalidation)
4. **How the knowledge graph** connects concepts
5. **How to monitor** system health and performance
6. **How to troubleshoot** issues using monitoring tools
7. **Production deployment** considerations

---

## 📞 Support

If you encounter issues:

1. **Check documentation**: PRD-Short-Term-Memory-MCP.md
2. **Review troubleshooting guide**: TROUBLESHOOTING-GUIDE.md
3. **Search existing issues**: GitHub issues
4. **Create new issue**: Include test phase, steps, and error messages
5. **Ask questions**: Include context and what you've tried

---

## ✨ Success!

When all 6 phases pass:

🎉 **Congratulations!** You've completed comprehensive end-to-end testing of the Short-Term Memory MCP!

Next steps:

1. Complete the [Final Test Report](FINAL-TEST-REPORT.md)
2. Create GitHub issues for any bugs found
3. Share findings with the development team
4. Consider performance benchmarking under load
5. Deploy to production (if ready)

---

## 📝 Quick Reference

### Tool Count by Phase

- Phase 1: 6 tools (Core)
- Phase 2: 6 tools (Pipeline)
- Phase 3: 6 tools (Cache)
- Phase 4: 3 tools (Code Teacher)
- Phase 5: 4 tools (Knowledge Graph)
- Phase 6: 3 tools (Monitoring)
- **Total: 28 tools**

### Test Execution Order

```
Start
  ↓
Phase 1 (Foundation) [Required]
  ↓
Phase 2 (Pipeline) [Builds on Phase 1]
  ↓
Phase 3 (Research Cache) [Can run anytime]
  ↓
Phase 4 (Code Teacher) [Needs today's session]
  ↓
Phase 5 (Knowledge Graph) [Needs concepts]
  ↓
Phase 6 (Monitoring) [Can run anytime]
  ↓
Final Report
  ↓
Complete! 🎉
```

### Time Budget

- **Minimum**: 4 hours (efficient testing)
- **Recommended**: 6 hours (thorough testing with breaks)
- **Maximum**: 8 hours (very detailed testing with documentation)

---

## 🚦 Status Tracking

Use this to track your progress:

- [ ] **Phase 1**: Foundation _(Status: Not Started / In Progress / Complete)_
- [ ] **Phase 2**: Pipeline Data & Storage _(Status: Not Started / In Progress / Complete)_
- [ ] **Phase 3**: Research Cache System _(Status: Not Started / In Progress / Complete)_
- [ ] **Phase 4**: Code Teacher Integration _(Status: Not Started / In Progress / Complete)_
- [ ] **Phase 5**: Knowledge Graph _(Status: Not Started / In Progress / Complete)_
- [ ] **Phase 6**: Monitoring & System Health _(Status: Not Started / In Progress / Complete)_
- [ ] **Final Report**: Summary and recommendations _(Status: Not Started / In Progress / Complete)_

**Overall Progress**: 0/7 (0%)

Good luck with testing! 🚀
