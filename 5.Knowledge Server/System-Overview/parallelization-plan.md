# Parallelization Plan

Generated from: Issue-List.md
Generated at: 2026-01-12T07:45:00Z
Total Issues: 9
Parallel Batches: 4

---

## Summary

| Batch | Issues     | Max Parallel | Priority Focus   |
| ----- | ---------- | ------------ | ---------------- |
| 1     | #1, #5, #7 | 3 sessions   | HIGH priority #5 |
| 2     | #2, #8     | 2 sessions   | Medium/Low       |
| 3     | #3, #6     | 2 sessions   | Medium           |
| 4     | #4, #9     | 2 sessions   | Low              |

---

## File Conflict Analysis

### Files Touched by Each Issue

| Issue | Severity | Primary Files              | Secondary Files                |
| ----- | -------- | -------------------------- | ------------------------------ |
| #1    | Medium   | `tools/concept_tools.py`   | validation layer               |
| #2    | Medium   | `tools/concept_tools.py`   | repository layer               |
| #3    | Medium   | `tools/concept_tools.py`   | repository layer               |
| #4    | Low      | `tools/concept_tools.py`   | -                              |
| #5    | **HIGH** | `tools/search_tools.py`    | `services/chromadb_service.py` |
| #6    | Medium   | `tools/search_tools.py`    | `tools/analytics_tools.py`     |
| #7    | Medium   | `tools/analytics_tools.py` | -                              |
| #8    | Low      | `mcp_server.py`            | `tools/analytics_tools.py`     |
| #9    | Low      | `tools/analytics_tools.py` | -                              |

### Conflict Groups

| Group | File                           | Conflicting Issues |
| ----- | ------------------------------ | ------------------ |
| A     | `tools/concept_tools.py`       | #1, #2, #3, #4     |
| B     | `tools/search_tools.py`        | #5, #6             |
| C     | `tools/analytics_tools.py`     | #6, #7, #8, #9     |
| D     | `services/chromadb_service.py` | #5                 |
| E     | `mcp_server.py`                | #8                 |

---

## Batch 1 (3 issues - can run simultaneously)

**Priority**: Contains HIGH priority issue #5

These issues touch completely different files and can be fixed in parallel.

| Issue | Title                                                 | Severity | Files                                                   |
| ----- | ----------------------------------------------------- | -------- | ------------------------------------------------------- |
| #1    | Name Length Validation Not Enforced                   | Medium   | `tools/concept_tools.py`                                |
| #5    | Semantic Search Cannot Combine Area and Topic Filters | **HIGH** | `tools/search_tools.py`, `services/chromadb_service.py` |
| #7    | Documentation Mismatch - sort_order Parameter         | Medium   | `tools/analytics_tools.py`                              |

### Start Commands

Open 3 terminal windows and run:

**Terminal 1: Issue #1 - Name Validation (Medium)**

```bash
mkdir -p /tmp/issue-fixer-locks
echo '{"issue_id": "01", "file": "issue-list-01.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-01.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-01.md
# After completion: rm /tmp/issue-fixer-locks/issue-01.lock
```

**Terminal 2: Issue #5 - Semantic Search Filters (HIGH PRIORITY)**

```bash
echo '{"issue_id": "05", "file": "issue-list-05.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-05.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-05.md
# After completion: rm /tmp/issue-fixer-locks/issue-05.lock
```

**Terminal 3: Issue #7 - sort_order Parameter (Medium)**

```bash
echo '{"issue_id": "07", "file": "issue-list-07.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-07.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-07.md
# After completion: rm /tmp/issue-fixer-locks/issue-07.lock
```

---

## Batch 2 (2 issues - run after Batch 1)

**Dependencies**: Issue #2 waits for #1, Issue #8 waits for #7

| Issue | Title                            | Severity | Files                                       | Waits For   |
| ----- | -------------------------------- | -------- | ------------------------------------------- | ----------- |
| #2    | Explanation History Not Returned | Medium   | `tools/concept_tools.py`                    | Batch 1: #1 |
| #8    | Limited Outbox Metrics           | Low      | `mcp_server.py`, `tools/analytics_tools.py` | Batch 1: #7 |

### Start Commands

After Batch 1 completes, open 2 terminals:

**Terminal 1: Issue #2 - Explanation History (Medium)**

```bash
echo '{"issue_id": "02", "file": "issue-list-02.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-02.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-02.md
# After completion: rm /tmp/issue-fixer-locks/issue-02.lock
```

**Terminal 2: Issue #8 - Outbox Metrics (Low)**

```bash
echo '{"issue_id": "08", "file": "issue-list-08.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-08.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-08.md
# After completion: rm /tmp/issue-fixer-locks/issue-08.lock
```

---

## Batch 3 (2 issues - run after Batch 2)

**Dependencies**: Issue #3 waits for #2, Issue #6 waits for #5 AND #7

| Issue | Title                                 | Severity | Files                                               | Waits For       |
| ----- | ------------------------------------- | -------- | --------------------------------------------------- | --------------- |
| #3    | Update Returns Generic Error          | Medium   | `tools/concept_tools.py`                            | Batch 2: #2     |
| #6    | Uncategorized Concepts Not Searchable | Medium   | `tools/search_tools.py`, `tools/analytics_tools.py` | Batch 1: #5, #7 |

### Start Commands

After Batch 2 completes, open 2 terminals:

**Terminal 1: Issue #3 - Update Error Handling (Medium)**

```bash
echo '{"issue_id": "03", "file": "issue-list-03.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-03.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-03.md
# After completion: rm /tmp/issue-fixer-locks/issue-03.lock
```

**Terminal 2: Issue #6 - Uncategorized Search (Medium)**

```bash
echo '{"issue_id": "06", "file": "issue-list-06.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-06.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-06.md
# After completion: rm /tmp/issue-fixer-locks/issue-06.lock
```

---

## Batch 4 (2 issues - run after Batch 3)

**Dependencies**: Issue #4 waits for #3, Issue #9 waits for #6, #7, #8

| Issue | Title                        | Severity | Files                      | Waits For   |
| ----- | ---------------------------- | -------- | -------------------------- | ----------- |
| #4    | Delete Returns Generic Error | Low      | `tools/concept_tools.py`   | Batch 3: #3 |
| #9    | Hierarchy Cache              | Low      | `tools/analytics_tools.py` | Batch 3: #6 |

### Start Commands

After Batch 3 completes, open 2 terminals:

**Terminal 1: Issue #4 - Delete Error Handling (Low)**

```bash
echo '{"issue_id": "04", "file": "issue-list-04.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-04.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-04.md
# After completion: rm /tmp/issue-fixer-locks/issue-04.lock
```

**Terminal 2: Issue #9 - Hierarchy Cache (Low)**

```bash
echo '{"issue_id": "09", "file": "issue-list-09.md", "started_at": "'$(date -Iseconds)'"}' > /tmp/issue-fixer-locks/issue-09.lock
claude --profile issue-fixer-lean
# Inside Claude: /fix-issue ./System-Overview/issues/issue-list-09.md
# After completion: rm /tmp/issue-fixer-locks/issue-09.lock
```

---

## Conflict Map

| Issue A | Issue B    | Shared Files               | Batch Separation             |
| ------- | ---------- | -------------------------- | ---------------------------- |
| #1      | #2, #3, #4 | `tools/concept_tools.py`   | Sequential in batches        |
| #2      | #3, #4     | `tools/concept_tools.py`   | Sequential in batches        |
| #3      | #4         | `tools/concept_tools.py`   | Sequential in batches        |
| #5      | #6         | `tools/search_tools.py`    | #5 in Batch 1, #6 in Batch 3 |
| #6      | #7, #8, #9 | `tools/analytics_tools.py` | #6 in Batch 3, after #7      |
| #7      | #8, #9     | `tools/analytics_tools.py` | #7 in Batch 1, #8/#9 later   |

---

## Issue Priority Order (Recommended Fix Sequence)

For single-session fixing, prioritize in this order:

1. **Issue #5** (HIGH) - Semantic Search Filters - Major functional gap
2. **Issue #1** (Medium) - Name Validation - Data integrity
3. **Issue #2** (Medium) - Explanation History - Feature completeness
4. **Issue #3** (Medium) - Update Error Handling - User experience
5. **Issue #6** (Medium) - Uncategorized Search - Data discoverability
6. **Issue #7** (Medium) - sort_order Parameter - API completeness
7. **Issue #4** (Low) - Delete Error Handling - Consistency
8. **Issue #8** (Low) - Outbox Metrics - Observability
9. **Issue #9** (Low) - Hierarchy Cache - Testing convenience

---

## Lock Commands Reference

```bash
# Check if an issue file is locked (use zero-padded file number: 01, 02, etc.)
[ -f /tmp/issue-fixer-locks/issue-NN.lock ] && echo "LOCKED" || echo "AVAILABLE"

# Example: Check if issue-list-05.md is locked
[ -f /tmp/issue-fixer-locks/issue-05.lock ] && echo "LOCKED" || echo "AVAILABLE"

# List all active locks
ls -la /tmp/issue-fixer-locks/

# View lock details
cat /tmp/issue-fixer-locks/issue-NN.lock | jq .

# Force unlock (use with caution)
rm /tmp/issue-fixer-locks/issue-NN.lock

# Clear all locks
rm -f /tmp/issue-fixer-locks/*.lock
```

---

## Quick Start: Maximum Parallelism

To fix all issues as fast as possible:

### Phase 1: Start Batch 1 (3 terminals)

```bash
# Terminal 1
cd /Users/ruben/Documents/GitHub/automaker/5.Knowledge Server
echo '{"issue_id": "01"}' > /tmp/issue-fixer-locks/issue-01.lock && claude --profile issue-fixer-lean

# Terminal 2
cd /Users/ruben/Documents/GitHub/automaker/5.Knowledge Server
echo '{"issue_id": "05"}' > /tmp/issue-fixer-locks/issue-05.lock && claude --profile issue-fixer-lean

# Terminal 3
cd /Users/ruben/Documents/GitHub/automaker/5.Knowledge Server
echo '{"issue_id": "07"}' > /tmp/issue-fixer-locks/issue-07.lock && claude --profile issue-fixer-lean
```

### Phase 2-4: Continue with subsequent batches after each completes

Monitor progress with:

```bash
ls /tmp/issue-fixer-locks/
```

---

## Notes

- Issues #3 and #4 are related (same error handling pattern) - fix approach can be similar
- Issue #6 spans two tools (search_tools + analytics_tools) - requires extra care
- Issue #9 is "working as designed" - fix is optional cache invalidation feature
- All concept_tools.py issues (#1-4) follow similar patterns - knowledge transfers
