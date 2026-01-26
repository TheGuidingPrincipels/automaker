#### Issue #8: Limited Outbox Metrics - No Pending or Failed Counts

**Severity**: Low
**Priority**: Low
**Component**: get_server_stats tool - Outbox status reporting

**Symptom**: get_server_stats returns outbox status with only "completed" count. No "pending" or "failed" fields are present in the response, limiting visibility into outbox processing health.

**Expected**: Outbox status should include:

- pending: Number of items awaiting processing
- completed: Number of successfully processed items
- failed: Number of items that failed processing

This allows comprehensive monitoring of outbox health and identification of processing bottlenecks or failures.

**Actual**: Outbox response structure: `{"completed": 106}`
Only completed count is tracked and exposed. Cannot determine if items are stuck pending or have failed processing.

**Trigger**:

1. Call get_server_stats
2. Examine outbox field in response
3. Only "completed" field present

**Location**:

- Tool: get_server_stats
- File: `mcp_server.py` or `tools/analytics_tools.py`
- Outbox status aggregation logic

**Error**: No error - missing fields in response structure. This is a limitation rather than a failure.

**Severity Impact**: Limited observability into system health. Cannot proactively detect:

- Outbox processing delays (high pending count)
- Projection failures (high failed count)
- Processing bottlenecks

However, completed count is the most important metric and is functioning. System continues operating normally; this only affects monitoring capabilities.

**Constraints**:

- Must not impact performance of stats retrieval
- If pending/failed tracking added, must be efficient queries
- Consider whether pending/failed are actually tracked in outbox implementation

**Context**:

- Test Cases: TC-STATS-3.3 (Verify Outbox Status), TC-STATS-3.9 (Failed Detection)
- Frequency: Consistent - all get_server_stats calls show limited metrics
- Environment: Knowledge Server MCP, outbox processing functional
- Observation: System is healthy despite limited metrics (completed count growing appropriately)
