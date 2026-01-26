# Short-Term Memory MCP - Test Phases

Complete end-to-end test suite for the Short-Term Memory MCP server.

## 📁 Contents

### Quick Start

- **[MASTER-TEST-GUIDE.md](MASTER-TEST-GUIDE.md)** - Start here! Complete testing instructions and overview

### Test Phases (Execute in Order)

1. **[PHASE-1-Foundation.md](PHASE-1-Foundation.md)** - Session & Concept Basics (6 tools, 45-60 min)
2. **[PHASE-2-Pipeline-Data-Storage.md](PHASE-2-Pipeline-Data-Storage.md)** - Pipeline Data & Storage (6 tools, 45-60 min)
3. **[PHASE-3-Research-Cache.md](PHASE-3-Research-Cache.md)** - Research Cache System (6 tools, 45-60 min)
4. **[PHASE-4-Code-Teacher.md](PHASE-4-Code-Teacher.md)** - Code Teacher Integration (3 tools, 30-45 min)
5. **[PHASE-5-Knowledge-Graph.md](PHASE-5-Knowledge-Graph.md)** - Knowledge Graph (4 tools, 45-60 min)
6. **[PHASE-6-Monitoring.md](PHASE-6-Monitoring.md)** - Monitoring & System Health (3 tools, 30-45 min)

### Final Report

- **[FINAL-TEST-REPORT.md](FINAL-TEST-REPORT.md)** - Template for comprehensive test summary

## 🎯 What This Tests

- **28 MCP tools** covering all functionality
- **End-to-end workflows** simulating real user behavior
- **Performance validation** against target metrics
- **Cache behavior** (5-minute TTL, invalidation)
- **Data integrity** and persistence
- **Error handling** and edge cases
- **Production readiness** assessment

## 🚀 How to Use

### Quick Start (First Time)

1. Read [MASTER-TEST-GUIDE.md](MASTER-TEST-GUIDE.md)
2. Start with [PHASE-1-Foundation.md](PHASE-1-Foundation.md)
3. Complete phases in order (1 → 2 → 3 → 4 → 5 → 6)
4. Fill out [FINAL-TEST-REPORT.md](FINAL-TEST-REPORT.md)

### Testing Approach

- **One phase at a time** - Don't rush
- **Stop at checkpoints** - Review results between tools
- **Record everything** - Use the test report sections
- **Test one tool at a time** - Then take a break

### Time Commitment

- **Minimum**: 4 hours (efficient testing)
- **Recommended**: 6 hours (thorough with breaks)
- **Can be split** across multiple days

## 📊 Test Coverage

| Phase     | Tools  | Focus Area                | Dependencies |
| --------- | ------ | ------------------------- | ------------ |
| 1         | 6      | Session & concepts        | None         |
| 2         | 6      | Pipeline stages           | Phase 1      |
| 3         | 6      | Research caching          | None         |
| 4         | 3      | Cached queries            | Phase 1      |
| 5         | 4      | Questions & relationships | Phase 1      |
| 6         | 3      | Monitoring                | None         |
| **Total** | **28** | **Complete system**       | -            |

## ✅ Prerequisites

- Short-Term Memory MCP server installed and running
- Claude Desktop configured with the MCP
- Fresh database OR willing to work with existing data
- 4-6 hours available (can be split)
- Note-taking tool for results

## 🎓 What You'll Learn

By completing these tests, you'll understand:

1. How the **SHOOT pipeline** works (Research → AIM → SHOOT → SKIN)
2. How **concepts progress** through stages
3. How **caching optimizes** performance
4. How the **knowledge graph** connects concepts
5. How to **monitor** system health
6. **Production deployment** considerations

## 📈 Success Criteria

### Phase-Level

- All tools in phase pass functionality tests
- Response times meet targets
- No critical issues discovered
- Data integrity verified

### Overall

- 28/28 tools pass (100%)
- Average response time < 200ms
- Cache provides 5x+ speedup
- No critical blockers
- System reports "healthy"

## 🐛 If You Find Bugs

1. **Document immediately** - Use the test report section
2. **Check GitHub issues** - May already be reported
3. **Create new issue** - Include phase, tool, steps to reproduce
4. **Continue testing** - Unless critical blocker
5. **Report in final summary**

## 📝 Test Reports

Each phase has a built-in test report section:

- Record results after each tool test
- Note any issues or unexpected behavior
- Track performance measurements
- Assess pass/fail status

Complete the [FINAL-TEST-REPORT.md](FINAL-TEST-REPORT.md) after all phases.

## 🔗 Related Documentation

- [../PRD-Short-Term-Memory-MCP.md](../PRD-Short-Term-Memory-MCP.md) - System architecture
- [../TROUBLESHOOTING-GUIDE.md](../TROUBLESHOOTING-GUIDE.md) - Debug guide
- [../Session-System-Prompts-Guide.md](../Session-System-Prompts-Guide.md) - Session workflows
- [../short_term_mcp/tests/](../short_term_mcp/tests/) - Unit tests (165+ tests)

## 💡 Tips for Success

### Do's ✅

- Follow steps exactly as written
- Stop at checkpoints to review
- Record response times accurately
- Test error cases thoroughly
- Take breaks between phases

### Don'ts ❌

- Skip steps or rush
- Test multiple things at once
- Ignore error messages
- Continue after critical failures
- Forget to document issues

## 🏆 Testing Goals

1. **Functional Verification** - All tools work correctly
2. **Performance Validation** - Meet response time targets
3. **Data Integrity** - Ensure persistence and consistency
4. **Error Handling** - Graceful handling of edge cases
5. **Production Readiness** - Assess deployment readiness
6. **Knowledge Building** - Understand system deeply

## 📞 Questions or Issues?

- **Check**: [MASTER-TEST-GUIDE.md](MASTER-TEST-GUIDE.md) Troubleshooting section
- **Review**: [../TROUBLESHOOTING-GUIDE.md](../TROUBLESHOOTING-GUIDE.md)
- **Search**: GitHub issues
- **Create**: New GitHub issue with details

## 🎉 After Completion

When all phases pass:

1. Complete [FINAL-TEST-REPORT.md](FINAL-TEST-REPORT.md)
2. Create GitHub issues for bugs found
3. Share findings with team
4. Celebrate! You've thoroughly tested the entire system! 🚀

---

**Ready to start?** Open [MASTER-TEST-GUIDE.md](MASTER-TEST-GUIDE.md) and begin with Phase 1!
