# Test Phase 6: Monitoring & System Health

## 📋 Phase Overview

**Goal**: Test the monitoring and production-readiness tools that provide system health checks, performance metrics, and error logging. These tools are essential for production deployments and debugging.

**Tools Tested** (3):

1. `health_check` - System health and connectivity verification
2. `get_system_metrics` - Performance metrics and statistics
3. `get_error_log` - Error tracking and debugging

**Estimated Time**: 30-45 minutes

---

## ✅ Prerequisites

- [ ] Any previous phases completed (or can work independently)
- [ ] Short-Term Memory MCP server is running
- [ ] Some data in database (sessions, concepts) preferred but not required
- [ ] Ability to trigger errors (optional for error log testing)

---

## 🧪 Test Execution

### Test 1: Health Check (System Operational Status)

**Objective**: Verify system health and database connectivity.

#### Steps:

1. **Perform health check** (baseline):

```
Tool: health_check
Parameters: [no parameters]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `overall_status: "healthy"` (or "degraded")
   - `timestamp` (ISO format)
   - `response_time_ms` (number)
   - `components` object with:
     - `database` subobject:
       - `status: "operational"` (or "down")
       - `details` (may include connection info)
     - `cache` subobject:
       - `status: "operational"`
       - `size` (number of cache entries)
       - `ttl_seconds: 300` (5-minute TTL)

3. **Verify response time**:
   - Target: < 100ms (ideally < 50ms)
   - Should be very fast (simple connectivity check)

4. **Record baseline health**:
   - overall_status
   - database status
   - cache status
   - cache size
   - response time

5. **Test multiple consecutive health checks** (should be consistently fast):

```
Tool: health_check
Parameters: [no parameters]
```

Repeat 3-5 times and verify:

- All return "healthy"
- Response times are consistent
- No performance degradation

6. **Test after database operations**:
   - Create a new session (if possible)
   - Run health check again
   - Verify still "healthy"

7. **Analyze cache status**:
   - Note cache size
   - Compare with previous calls (may vary based on TTL)
   - Verify cache TTL is 300 seconds

#### Success Criteria:

- [ ] Health check returns "healthy" status
- [ ] Database is "operational"
- [ ] Cache is "operational"
- [ ] Response time < 100ms (target: < 50ms)
- [ ] Consistent results across multiple calls
- [ ] All required fields present

#### Record Results:

```
Overall status: [healthy/degraded]
Database status: [operational/down]
Cache status: [operational]
Cache size: [N entries]
Response time: [X]ms
Multiple calls consistent: [yes/no]
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 2: Get System Metrics (Performance & Statistics)

**Objective**: Retrieve comprehensive system performance metrics and database statistics.

#### Steps:

1. **Get system metrics** (baseline):

```
Tool: get_system_metrics
Parameters: [no parameters]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `timestamp` (ISO format)
   - `database` object with:
     - `size_bytes` (integer)
     - `size_mb` (float)
     - `sessions` (count)
     - `concepts` (count)
     - `stage_data_entries` (count)
   - `operations` object with:
     - `reads` (count)
     - `writes` (count)
     - `queries` (count)
     - `errors` (count)
   - `performance` object with:
     - `min_ms` (float)
     - `max_ms` (float)
     - `avg_ms` (float)
   - `cache` object with:
     - `entries` (count)
     - `ttl_seconds: 300`

3. **Record baseline metrics**:
   - Database size (MB)
   - Total sessions
   - Total concepts
   - Total stage_data_entries
   - Operation counts (reads, writes, queries, errors)
   - Performance stats (min, max, avg)
   - Cache entries

4. **Perform operations and verify metrics update**:

Create a new session:

```
Tool: initialize_daily_session
Parameters:
  learning_goal: "Test metrics tracking"
  building_goal: "Verify metrics increment"
  date: [tomorrow's date if today exists, or today]
```

Add concepts:

```
Tool: store_concepts_from_research
Parameters:
  session_id: [session ID from above]
  concepts: [
    {"concept_name": "Metrics Test Concept 1"},
    {"concept_name": "Metrics Test Concept 2"},
    {"concept_name": "Metrics Test Concept 3"}
  ]
```

5. **Get metrics again** and verify changes:

```
Tool: get_system_metrics
Parameters: [no parameters]
```

Expected changes:

- `sessions` increased by 1
- `concepts` increased by 3
- `writes` increased
- `queries` increased
- Database `size_bytes` increased

6. **Perform multiple reads and verify operation counts**:

```
Tool: get_concepts_by_session
Parameters:
  session_id: [session ID]
  status_filter: [leave empty]
  include_stage_data: false
```

Get metrics again:

```
Tool: get_system_metrics
Parameters: [no parameters]
```

Expected:

- `reads` increased
- `queries` increased

7. **Analyze performance statistics**:
   - Check `avg_ms` is reasonable (< 200ms typical)
   - Check `max_ms` to identify slow operations
   - Check `min_ms` for fastest operations

8. **Calculate database growth rate**:
   - Size per session: size_mb / sessions
   - Size per concept: size_mb / concepts
   - Document for capacity planning

9. **Verify cache metrics**:
   - Compare cache entries with health_check
   - Should be consistent

#### Success Criteria:

- [ ] All metric fields present and non-null
- [ ] Database size > 0
- [ ] Operation counts increase with operations
- [ ] Performance stats are reasonable (avg < 200ms)
- [ ] Metrics accurately reflect system state
- [ ] Response time < 500ms

#### Record Results:

```
Database size: [X.XX MB]
Total sessions: [N]
Total concepts: [N]
Stage data entries: [N]
Operations (reads/writes/queries/errors): [R/W/Q/E]
Performance (min/avg/max): [X/Y/Z ms]
Cache entries: [N]
Metrics increment correctly: [yes/no]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 3: Get Error Log (Error Tracking)

**Objective**: Test error logging and retrieval system.

#### Steps:

1. **Get error log** (initial state):

```
Tool: get_error_log
Parameters:
  limit: 10
  error_type: [leave empty]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `timestamp` (ISO format)
   - `filter` object with:
     - `limit: 10`
     - `error_type: null`
   - `error_count` (integer, may be 0)
   - `errors` array (may be empty)

3. **If errors exist**, verify each error entry includes:
   - `timestamp` (when error occurred)
   - `error_type` (e.g., "DatabaseError", "TimeoutError")
   - `message` (error description)
   - `context` (optional, additional details)

4. **Trigger errors** (optional, if safe):

Attempt invalid session ID:

```
Tool: store_concepts_from_research
Parameters:
  session_id: "invalid-session-id"
  concepts: [{"concept_name": "Test"}]
```

Expected: Should return error (not crash server)

Get error log again:

```
Tool: get_error_log
Parameters:
  limit: 10
  error_type: [leave empty]
```

Check if error was logged (note: validation errors may not be logged per design)

5. **Test limit parameter**:

Request 5 errors:

```
Tool: get_error_log
Parameters:
  limit: 5
  error_type: [leave empty]
```

Verify: `errors` array has ≤ 5 entries

Request 100 errors (max):

```
Tool: get_error_log
Parameters:
  limit: 100
  error_type: [leave empty]
```

Verify: Doesn't exceed 100 entries

Request 500 errors (should clamp to 100):

```
Tool: get_error_log
Parameters:
  limit: 500
  error_type: [leave empty]
```

Verify: Clamped to 100 max

6. **Test error_type filter**:

If you have errors of different types:

```
Tool: get_error_log
Parameters:
  limit: 10
  error_type: "DatabaseError"
```

Expected: Only "DatabaseError" entries (or empty if none exist)

7. **Test with no errors** (initial state):
   - If no errors exist, verify:
   - `error_count: 0`
   - `errors: []` (empty array)
   - No crashes or issues

8. **Verify error log behavior**:
   - Errors are sorted by timestamp (most recent first)
   - Error log is persistent (survives server restart)
   - System-level errors are logged (DB failures, timeouts, crashes)
   - User errors are NOT logged (validation errors, not_found, etc.)

9. **Check error log cap** (1000 entries max per implementation):
   - Note: You likely won't hit this limit in testing
   - Document that error log has maximum size to prevent unbounded growth

#### Success Criteria:

- [ ] Error log retrieves successfully
- [ ] Limit parameter works (1-100 range)
- [ ] error_type filter works (if errors exist)
- [ ] Empty error log handled gracefully
- [ ] Error entries have required fields (timestamp, type, message)
- [ ] Errors sorted by timestamp (most recent first)
- [ ] Response time < 300ms

#### Record Results:

```
Initial error count: [N]
Errors after triggering: [N]
Limit parameter works: [yes/no]
Error type filter works: [yes/no or N/A]
Empty log handled: [yes/no]
Error log cap documented: [yes/no]
Response time: [X]ms
Notes: [any observations, error types seen]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 4: Production Readiness Assessment

**Objective**: Assess overall production readiness based on monitoring tools.

#### Steps:

1. **Run all three monitoring tools** in sequence:

```
Tool: health_check
Tool: get_system_metrics
Tool: get_error_log (limit: 20)
```

2. **Evaluate system health**:
   - ✅ **Healthy**: Database operational, no errors, good performance
   - ⚠️ **Degraded**: Slow performance, some errors, cache issues
   - ❌ **Unhealthy**: Database down, many errors, crashes

3. **Performance evaluation**:
   - Average response time < 200ms: ✅ Good
   - Average response time 200-500ms: ⚠️ Acceptable
   - Average response time > 500ms: ❌ Needs optimization

4. **Error rate evaluation**:
   - 0 errors: ✅ Excellent
   - 1-5 errors: ⚠️ Investigate
   - 5+ errors: ❌ Critical issues

5. **Database size evaluation**:
   - Calculate growth rate: MB per session
   - Estimate storage needs for production
   - Document recommendations

6. **Cache effectiveness**:
   - Cache hit rate (from Phase 4): should be > 50%
   - Cache size: should grow/shrink appropriately
   - Cache TTL: 5 minutes is appropriate

7. **Create production monitoring recommendations**:
   - How often to run health_check (e.g., every 5 minutes)
   - When to alert (e.g., "degraded" status)
   - What metrics to track over time
   - Error log review frequency

#### Success Criteria:

- [ ] All monitoring tools work correctly
- [ ] System health can be assessed objectively
- [ ] Performance metrics are within acceptable ranges
- [ ] Error logging is functional
- [ ] Production recommendations documented

#### Record Results:

```
Overall health: [healthy/degraded/unhealthy]
Performance rating: [good/acceptable/needs optimization]
Error rate: [excellent/investigate/critical]
Database growth: [X MB per session]
Cache effectiveness: [documented in Phase 4]
Production ready: [yes/no/with caveats]
Recommendations: [list key recommendations]
Notes: [any observations]
```

---

## 📊 Phase 6 Test Report

**Completion Date**: [YYYY-MM-DD]
**Tester**: [Your Name]
**MCP Server Version**: [Check package.json or git commit]

### Summary

| Test | Tool                 | Status            | Response Time | Notes |
| ---- | -------------------- | ----------------- | ------------- | ----- |
| 1    | health_check         | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 2    | get_system_metrics   | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 3    | get_error_log        | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |       |
| 4    | Production readiness | ⬜ Pass / ⬜ Fail | -             |       |

### Issues Found

1. **Issue**: [Description]
   - **Severity**: Critical / High / Medium / Low
   - **Tool**: [Tool name]
   - **Steps to Reproduce**: [Steps]
   - **Expected**: [Expected behavior]
   - **Actual**: [Actual behavior]

2. [Add more issues as needed]

### System Health Summary

**Health Status**: ⬜ Healthy / ⬜ Degraded / ⬜ Unhealthy

- Database: ⬜ Operational / ⬜ Down
- Cache: ⬜ Operational / ⬜ Down
- Overall response time: \_\_\_ ms
- Error count: [N]

### Performance Metrics

**Database**:

- Size: [X.XX MB]
- Sessions: [N]
- Concepts: [N]
- Stage data entries: [N]
- Growth rate: [X MB per session]

**Operations** (since server start):

- Reads: [N]
- Writes: [N]
- Queries: [N]
- Errors: [N]

**Performance Timing**:

- Min: [X ms]
- Avg: [Y ms]
- Max: [Z ms]

**Cache**:

- Entries: [N]
- TTL: 300 seconds
- Hit rate (from Phase 4): [%]

### Error Analysis

**Error Summary**:

- Total errors logged: [N]
- Error types seen: [list types]
- Most common error: [type]
- Error rate: [errors per operation]

**Critical Errors**: [yes/no]
If yes, list:

1. [Error description]
2. [Error description]

### Production Readiness Assessment

⬜ **PRODUCTION READY** - All systems operational, ready for deployment
⬜ **READY WITH MONITORING** - Ready, but requires active monitoring
⬜ **NOT READY** - Critical issues must be resolved

**Strengths**:

- [List what's working well]

**Weaknesses**:

- [List areas needing improvement]

**Blockers** (if not ready):

- [Critical issues preventing production deployment]

### Monitoring Recommendations

1. **Health Check Frequency**: [e.g., every 5 minutes]
2. **Alert Thresholds**:
   - Alert on "degraded" status: [yes/no]
   - Alert on error count > [N]: [yes/no]
   - Alert on avg response time > [X]ms: [yes/no]
3. **Metrics to Track Over Time**:
   - [e.g., database growth rate]
   - [e.g., error rate trends]
   - [e.g., performance degradation]
4. **Log Review Frequency**: [e.g., daily, weekly]
5. **Capacity Planning**:
   - Estimated storage per month: [calculation]
   - Database cleanup schedule: [recommendation]

### Overall Assessment

⬜ **PASS** - All monitoring tools working, system healthy
⬜ **PASS WITH ISSUES** - Tools working but health concerns noted
⬜ **FAIL** - Monitoring tools not working or critical health issues

### Recommendations

[Any recommendations for improvements, bug fixes, monitoring setup, or documentation updates]

---

## 🎯 Next Steps

If Phase 6 **PASSED**:

- ✅ **All 6 test phases completed!**
- ✅ Short-Term Memory MCP is fully tested
- ✅ Proceed to **Integration Testing** (end-to-end workflows)
- ✅ Consider performance benchmarking under load
- ✅ Document findings and create final test report

If Phase 6 **FAILED**:

- ⚠️ Document all failures in the test report
- ⚠️ Create GitHub issues for bugs found
- ⚠️ Fix critical monitoring issues
- ⚠️ Re-run Phase 6 after fixes

---

## 📊 Production Deployment Checklist

Before deploying to production, ensure:

### Monitoring Setup

- [ ] Health check endpoint monitored (every 5 minutes)
- [ ] Alerts configured for degraded status
- [ ] Metrics dashboard created
- [ ] Error log review process established
- [ ] Performance baseline documented

### System Configuration

- [ ] Database retention policy configured (7 days default)
- [ ] Cache TTL appropriate for use case (5 minutes default)
- [ ] WAL mode enabled for better concurrency
- [ ] Auto-vacuum enabled
- [ ] Database backup strategy in place

### Performance

- [ ] Average response time < 200ms
- [ ] Cache hit rate > 50%
- [ ] No memory leaks observed
- [ ] Database growth rate acceptable

### Error Handling

- [ ] Error log cap configured (1000 entries)
- [ ] Error types documented
- [ ] Recovery procedures documented
- [ ] Monitoring for critical errors

### Documentation

- [ ] Monitoring runbook created
- [ ] Alert response procedures documented
- [ ] Capacity planning calculations completed
- [ ] Maintenance schedule established

---

## 💡 Monitoring Best Practices

Based on these tests:

1. **Regular Health Checks**:
   - Run health_check every 5 minutes
   - Alert on "degraded" status
   - Investigate any database connectivity issues immediately

2. **Metrics Tracking**:
   - Track database growth weekly
   - Monitor error rates daily
   - Review performance trends monthly
   - Plan capacity based on growth rate

3. **Error Management**:
   - Review error log daily in production
   - Investigate any increase in error rate
   - System errors (DB, timeouts) are logged
   - User/validation errors are NOT logged (by design)

4. **Performance Optimization**:
   - Cache hit rate should be > 50%
   - Average response time should be < 200ms
   - Investigate operations > 1 second
   - Optimize slow database queries

5. **Capacity Planning**:
   - Calculate: [sessions per day] × [MB per session] × [days retention]
   - Monitor database growth trends
   - Plan for 20-30% growth buffer
   - Schedule regular cleanup (7-day retention default)
