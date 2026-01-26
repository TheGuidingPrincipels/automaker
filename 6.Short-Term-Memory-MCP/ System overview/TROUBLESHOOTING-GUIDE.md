# Troubleshooting Guide

**Short-Term Memory MCP Server**

**Purpose:** Quick diagnostic and recovery procedures for common issues.

**Last Updated:** 2025-10-11

---

## Quick Diagnostics

### System Health Check

```python
# Run first when debugging
result = await health_check()

if result["overall_status"] != "healthy":
    print(f"⚠️ System degraded!")
    print(f"Database: {result['components']['database']['status']}")
    print(f"Response time: {result['response_time_ms']}ms")
```

**What to Check:**

- Database connection: Should be "active"
- Response time: Should be <50ms
- Integrity: Should be "ok"

---

## Common Issues & Solutions

### Issue 1: "Session won't complete"

**Symptom:** `mark_session_complete` returns warning

**Diagnosis:**

```python
# Check for unstored concepts
unstored = await get_unstored_concepts(session_id)
print(f"Unstored: {unstored['unstored_count']}")
for concept in unstored["concepts"]:
    print(f"  - {concept['concept_name']} (status: {concept['current_status']})")
```

**Cause:** Concepts missing `knowledge_mcp_id`

**Solution:**

```python
# Option 1: Complete Storing Session for remaining concepts
for concept in unstored["concepts"]:
    # Transfer to Knowledge MCP
    kmcp_id = await knowledge_mcp.create_concept(concept)
    await mark_concept_stored(concept["concept_id"], kmcp_id)

# Option 2: Check which concepts failed storage
# Look for concepts with status=evaluated but no knowledge_mcp_id
```

---

### Issue 2: "Concepts disappeared"

**Symptom:** Concepts from previous day are gone

**Diagnosis:**

```python
# Check retention period
metrics = await get_system_metrics()
print(f"Database has {metrics['database']['concepts']} concepts")

# Try querying old session
old_session = await get_active_session(date="2025-10-04")
# Returns: "not_found" if older than 7 days
```

**Cause:** Auto-cleanup after 7 days

**Solution:**

- **Expected behavior:** Concepts deleted after 7 days if not stored
- **Prevention:** Ensure Storing Session completes within 7 days
- **Recovery:** No recovery (intended deletion)
- **Check config:** `DB_RETENTION_DAYS = 7` in `config.py`

---

### Issue 3: "Cache showing stale data"

**Symptom:** Code Teacher shows old concept data

**Diagnosis:**

```python
# Check cache hit
result = await get_todays_concepts()
print(f"Cache hit: {result['cache_hit']}")  # True = cached

# Check concept count vs expected
print(f"Concept count: {result['concept_count']}")
```

**Cause:** 5-minute cache TTL hasn't expired

**Solution:**

```python
# Option 1: Wait for cache expiration (max 5 minutes)
# Cache automatically expires and refreshes

# Option 2: Use direct query (no cache)
# Learning sessions use get_concepts_by_session (no cache)
concepts = await get_concepts_by_session(session_id)

# Option 3: Restart Claude Desktop to clear cache
# Not recommended - cache cleanup runs automatically
```

**Cache Behavior:**

- TTL: 5 minutes (300 seconds)
- Background cleanup: Every 2.5 minutes
- Affects only Code Teacher tools (get*todays*_, search*todays*_)

---

### Issue 4: "Database locked"

**Symptom:** Timeout errors or "database is locked"

**Diagnosis:**

```python
# Check system metrics
metrics = await get_system_metrics()
print(f"Active operations: {metrics['operations']}")
print(f"Errors: {metrics['operations']['errors']}")

# Check error log
errors = await get_error_log(limit=10)
for e in errors["errors"]:
    print(f"{e['error_type']}: {e['message']}")
```

**Cause:** Too many concurrent operations (>5 semaphore limit)

**Solution:**

```python
# System automatically handles concurrency
# Semaphore limits to 5 concurrent DB operations

# If persistent:
# 1. Check for long-running operations (shouldn't happen)
# 2. Restart MCP server
# 3. Check database file permissions
```

**Prevention:**

- Don't call tools in tight loops
- Use batch operations (get_concepts_by_session once, process in memory)
- Let semaphore handle concurrency

---

### Issue 5: "Concept stuck in intermediate status"

**Symptom:** Concept has status=chunked but should be encoded

**Diagnosis:**

```python
# Get concept details
concepts = await get_concepts_by_session(session_id)
for c in concepts:
    if c["current_status"] != expected_status:
        print(f"⚠️ {c['concept_name']}: {c['current_status']}")
        print(f"   Timeline: {c['chunked_at']} → {c['encoded_at']}")
```

**Cause:** Session crashed or interrupted before updating status

**Solution:**

```python
# Manual status update
await update_concept_status(
    concept_id=stuck_concept_id,
    new_status="encoded"  # Or correct status
)

# If stage data exists but status not updated:
# 1. Check which stage data exists
stage_data = await get_stage_data(concept_id, "shoot")
if stage_data["status"] == "success":
    # Data exists, update status
    await update_concept_status(concept_id, "encoded")
```

---

### Issue 6: "Integration failure with Knowledge MCP"

**Symptom:** `mark_concept_stored` fails or Knowledge MCP unreachable

**Diagnosis:**

```python
# Check if Knowledge MCP is running
# (External to this system)

# Check for partially stored concepts
unstored = await get_unstored_concepts(session_id)
print(f"Unstored: {unstored['unstored_count']}")

# Check error log
errors = await get_error_log(error_type="UPDATE_FAILED")
```

**Cause:** Knowledge MCP server offline or network issue

**Solution:**

```python
# Option 1: Retry storage after Knowledge MCP is online
for concept in unstored["concepts"]:
    try:
        kmcp_id = await knowledge_mcp.create_concept(concept)
        await mark_concept_stored(concept["concept_id"], kmcp_id)
    except Exception as e:
        print(f"Failed: {concept['concept_name']}: {e}")

# Option 2: Export concepts to JSON for manual import
import json
with open("unstored_concepts.json", "w") as f:
    json.dump(unstored["concepts"], f, indent=2)
```

---

### Issue 7: "Session already exists"

**Symptom:** `initialize_daily_session` returns warning

**Diagnosis:**

```python
session = await initialize_daily_session(
    learning_goal="...",
    building_goal="..."
)

if session["status"] == "warning":
    print(f"Session exists: {session['session']['session_id']}")
    print(f"Status: {session['session']['status']}")
```

**Cause:** Session for today already created

**Solution:**

```python
# Option 1: Use existing session (most common)
# Continue with AIM/SHOOT/SKIN for existing session

# Option 2: Clear and restart (destructive)
await clear_old_sessions(days_to_keep=0)  # Delete all
await initialize_daily_session(...)  # Create new

# Option 3: Use different date (testing)
await initialize_daily_session(
    learning_goal="...",
    building_goal="...",
    date="2025-10-12"  # Tomorrow
)
```

---

### Issue 8: "Tools timing out"

**Symptom:** `error_code: "TIMEOUT"` in responses

**Diagnosis:**

```python
# Check operation timing
metrics = await get_system_metrics()
print(f"Avg query time: {metrics['performance']['query_times']['avg_ms']}ms")
print(f"Max query time: {metrics['performance']['query_times']['max_ms']}ms")

# Check database size
print(f"Database size: {metrics['database']['size_mb']} MB")
```

**Cause:** Database too large or slow disk I/O

**Solution:**

```python
# 1. Run cleanup
await clear_old_sessions(days_to_keep=7)

# 2. Check database integrity
result = await health_check()
print(f"Integrity: {result['components']['database']['integrity']}")

# 3. Vacuum database (if needed)
# Run from command line:
# sqlite3 data/short_term_memory.db "VACUUM;"

# 4. Reduce batch size
# Instead of include_stage_data=True for all concepts:
concepts = await get_concepts_by_session(session_id)  # No stage data
for concept in concepts[:5]:  # Process in smaller batches
    stage_data = await get_stage_data(concept["concept_id"], "shoot")
```

**Timeout Limits:**

- Default: 20 seconds
- Bulk insert: 30 seconds
- If hitting limits, process in smaller batches

---

## Recovery Procedures

### Resume Interrupted AIM Session

**Scenario:** AIM session crashed after processing 10/25 concepts

**Recovery:**

```python
# 1. Check which concepts are chunked
concepts = await get_concepts_by_session(session_id)
chunked = [c for c in concepts if c["current_status"] == "chunked"]
identified = [c for c in concepts if c["current_status"] == "identified"]

print(f"Completed: {len(chunked)}/25")
print(f"Remaining: {len(identified)}")

# 2. Resume processing remaining concepts
for concept in identified:
    # Continue chunking...
    await store_stage_data(concept["concept_id"], "aim", {...})
    await update_concept_status(concept["concept_id"], "chunked")
```

---

### Resume Interrupted SHOOT Session

**Scenario:** SHOOT session crashed during Pass 1

**Recovery:**

```python
# 1. Check which concepts are encoded
concepts = await get_concepts_by_session(session_id)
encoded = [c for c in concepts if c["current_status"] == "encoded"]
chunked = [c for c in concepts if c["current_status"] == "chunked"]

print(f"Encoded: {len(encoded)}/25")
print(f"Remaining: {len(chunked)}")

# 2. Resume encoding
for concept in chunked:
    # Continue encoding...
    await store_stage_data(concept["concept_id"], "shoot", {...})
    await update_concept_status(concept["concept_id"], "encoded")

# 3. If interrupted during Pass 2, check difficulty ratings
shoot_data = []
for concept in encoded:
    data = await get_stage_data(concept["concept_id"], "shoot")
    shoot_data.append({
        "concept_id": concept["concept_id"],
        "difficulty": data["data"]["difficulty_rating"]
    })

# Sort by difficulty, process top 8-10
shoot_data.sort(key=lambda x: x["difficulty"], reverse=True)
hardest = shoot_data[:10]
```

---

### Restore from Partial Storing Session

**Scenario:** Storing session completed 2/4 batches

**Recovery:**

```python
# 1. Check what's stored
unstored = await get_unstored_concepts(session_id)
print(f"Unstored: {unstored['unstored_count']}")

evaluated = await get_concepts_by_status(session_id, "evaluated")
stored = await get_concepts_by_status(session_id, "stored")

print(f"Progress: {len(stored['concepts'])}/{len(evaluated['concepts']) + len(stored['concepts'])}")

# 2. Process remaining concepts
for concept in unstored["concepts"]:
    # Get all data
    concept_data = await get_concepts_by_session(
        session_id,
        include_stage_data=True
    )

    # Find this concept in results
    full_concept = next(c for c in concept_data if c["concept_id"] == concept["concept_id"])

    # Transfer to Knowledge MCP
    kmcp_id = await knowledge_mcp.create_concept(full_concept)
    await mark_concept_stored(concept["concept_id"], kmcp_id)

# 3. Complete session
await mark_session_complete(session_id)
```

---

### Fix Concepts Stuck in Intermediate Status

**Scenario:** Multiple concepts have status=chunked but stage_data exists for "shoot"

**Recovery:**

```python
# 1. Identify mismatched concepts
concepts = await get_concepts_by_session(session_id)

for concept in concepts:
    # Check if stage data exists beyond current status
    if concept["current_status"] == "chunked":
        shoot_data = await get_stage_data(concept["concept_id"], "shoot")

        if shoot_data["status"] == "success":
            # Stage data exists but status not updated
            print(f"⚠️ Fixing {concept['concept_name']}")
            await update_concept_status(concept["concept_id"], "encoded")

    if concept["current_status"] == "encoded":
        skin_data = await get_stage_data(concept["concept_id"], "skin")

        if skin_data["status"] == "success":
            # Stage data exists but status not updated
            print(f"⚠️ Fixing {concept['concept_name']}")
            await update_concept_status(concept["concept_id"], "evaluated")
```

---

## Diagnostic Commands

### Check System Health

```python
# Overall health
health = await health_check()
print(f"Status: {health['overall_status']}")
print(f"Response time: {health['response_time_ms']}ms")
print(f"Database: {health['components']['database']['status']}")
print(f"Cache: {health['components']['cache']['status']}")
```

**Expected:**

- overall_status: "healthy"
- response_time_ms: <50ms
- database.status: "healthy"
- cache.status: "operational"

---

### Check Performance Metrics

```python
# Database and performance stats
metrics = await get_system_metrics()

print(f"Database size: {metrics['database']['size_mb']} MB")
print(f"Sessions: {metrics['database']['sessions']}")
print(f"Concepts: {metrics['database']['concepts']}")
print(f"Stage data entries: {metrics['database']['stage_data_entries']}")

print(f"\nOperations:")
print(f"  Reads: {metrics['operations']['reads']}")
print(f"  Writes: {metrics['operations']['writes']}")
print(f"  Errors: {metrics['operations']['errors']}")

print(f"\nAvg Performance:")
print(f"  Read: {metrics['performance']['read_times']['avg_ms']}ms")
print(f"  Write: {metrics['performance']['write_times']['avg_ms']}ms")
print(f"  Query: {metrics['performance']['query_times']['avg_ms']}ms")
```

**Watch For:**

- Database size >10 MB → Run cleanup
- Errors >10 → Check error log
- Avg query time >100ms → Performance issue

---

### Check Error Log

```python
# Recent errors
errors = await get_error_log(limit=10)

if errors["error_count"] > 0:
    print(f"Recent errors: {errors['error_count']}")
    for e in errors["errors"]:
        print(f"  [{e['timestamp']}] {e['error_type']}")
        print(f"    {e['message']}")
        if e.get("context"):
            print(f"    Context: {e['context']}")

# Filter by type
db_errors = await get_error_log(limit=20, error_type="DatabaseError")
timeout_errors = await get_error_log(limit=20, error_type="TIMEOUT")
```

---

### Check Pipeline Progress

```python
# Session overview
session = await get_active_session()

print(f"Session: {session['session_id']}")
print(f"Status: {session['session_status']}")
print(f"Total concepts: {session['concept_count']}")
print(f"\nPipeline Progress:")
print(f"  Identified: {session['concepts_by_status']['identified']}")
print(f"  Chunked: {session['concepts_by_status']['chunked']}")
print(f"  Encoded: {session['concepts_by_status']['encoded']}")
print(f"  Evaluated: {session['concepts_by_status']['evaluated']}")
print(f"  Stored: {session['concepts_by_status']['stored']}")

# Completion percentage
total = session["concept_count"]
stored = session["concepts_by_status"]["stored"]
print(f"\n{stored}/{total} stored ({stored/total*100:.1f}%)")
```

---

### Verify Completion

```python
# Before marking session complete
unstored = await get_unstored_concepts(session_id)

if unstored["unstored_count"] == 0:
    print("✅ All concepts stored, ready to complete")
    result = await mark_session_complete(session_id)
    print(f"Session complete: {result['total_concepts']} concepts")
else:
    print(f"⚠️ {unstored['unstored_count']} concepts not stored:")
    for c in unstored["concepts"]:
        print(f"  - {c['concept_name']} (status: {c['current_status']})")
    print("\nComplete Storing Session before marking complete")
```

---

## Manual Fixes

### Manual Status Update

```python
# Update concept status manually
concept_id = "uuid-123"
new_status = "encoded"  # chunked|encoded|evaluated|stored

result = await update_concept_status(concept_id, new_status)
print(f"Updated: {result['previous_status']} → {result['new_status']}")
```

**When to Use:**

- Session crashed before updating status
- Stage data exists but status not updated
- Manual recovery needed

---

### Force Cleanup

```python
# Delete all old sessions
result = await clear_old_sessions(days_to_keep=7)
print(f"Deleted {result['sessions_deleted']} sessions")
print(f"Deleted {result['concepts_deleted']} concepts")

# Emergency cleanup (keep only today)
result = await clear_old_sessions(days_to_keep=1)

# Delete everything (testing only)
result = await clear_old_sessions(days_to_keep=0)
```

**Warning:** Permanent deletion, cannot undo

---

### Database Integrity Check

```bash
# Run from command line
sqlite3 data/short_term_memory.db "PRAGMA integrity_check;"
```

**Expected:** "ok"

**If Errors:**

1. Backup database: `cp data/short_term_memory.db data/short_term_memory_backup.db`
2. Try repair: `sqlite3 data/short_term_memory.db ".recover" | sqlite3 data/short_term_memory_new.db`
3. If fails, restore from backup

---

### Manual Database Vacuum

```bash
# Reclaim space after deletions
sqlite3 data/short_term_memory.db "VACUUM;"
```

**When to Run:**

- After large cleanup
- Database file size too large
- Slow query performance

---

## Prevention Best Practices

### Avoid Database Lock Issues

```python
# ❌ Don't do this
for i in range(100):
    await get_active_session()  # Unnecessary queries

# ✅ Do this
session = await get_active_session()  # Query once
for concept in session_concepts:
    process(concept)  # Use cached data
```

---

### Avoid Timeout Issues

```python
# ❌ Don't do this
concepts = await get_concepts_by_session(
    session_id,
    include_stage_data=True  # Heavy query
)
# Then loop through concepts making more queries

# ✅ Do this
concepts = await get_concepts_by_session(session_id)  # Lightweight
for concept in concepts[:5]:  # Process in batches
    stage_data = await get_stage_data(concept["concept_id"], "shoot")
    process(concept, stage_data)
```

---

### Ensure Session Completion

```python
# ✅ Always verify before completing
unstored = await get_unstored_concepts(session_id)
if unstored["unstored_count"] == 0:
    await mark_session_complete(session_id)
else:
    # Fix unstored concepts first
    print(f"⚠️ {unstored['unstored_count']} concepts unstored")
```

---

### Regular Maintenance

```bash
# Weekly: Check system health
pytest short_term_mcp/tests/test_production.py -v

# Monthly: Database cleanup
python -c "
from short_term_mcp.tools_impl import clear_old_sessions
import asyncio
result = asyncio.run(clear_old_sessions(days_to_keep=7))
print(f'Cleaned: {result[\"sessions_deleted\"]} sessions')
"

# As needed: Integrity check
sqlite3 data/short_term_memory.db "PRAGMA integrity_check;"
```

---

## Error Code Reference

| Error Code                  | Meaning                      | Solution                                                  |
| --------------------------- | ---------------------------- | --------------------------------------------------------- |
| `TIMEOUT`                   | Operation >20s (or 30s bulk) | Reduce batch size, check DB performance                   |
| `SESSION_NOT_FOUND`         | Session doesn't exist        | Create session with initialize_daily_session              |
| `CONCEPT_NOT_FOUND`         | Concept doesn't exist        | Check concept_id, verify session                          |
| `INVALID_STATUS`            | Invalid status value         | Use enum: identified, chunked, encoded, evaluated, stored |
| `INVALID_STAGE`             | Invalid stage value          | Use enum: research, aim, shoot, skin                      |
| `INVALID_RELATIONSHIP_TYPE` | Invalid relationship         | Use: prerequisite, related, similar, builds_on            |
| `UPDATE_FAILED`             | Database update failed       | Check error log, retry, check database integrity          |
| `EMPTY_SEARCH_TERM`         | Search term empty            | Provide non-empty search term                             |

---

## When to Escalate

### Contact System Administrator If:

1. Database corruption (integrity_check fails)
2. Persistent timeout errors (even with small batches)
3. Cache not expiring (stale data >5 minutes)
4. Health check fails repeatedly
5. Errors >100 in error log

### Safe to Handle Yourself:

1. Session completion warnings (unstored concepts)
2. Interrupted session recovery
3. Manual status updates
4. Old session cleanup
5. Cache behavior questions

---

**Document Purpose:** Quick reference for debugging and recovering from common issues. Start with health_check, use diagnostic commands, follow recovery procedures.

**Token Count:** ~2,400 tokens
