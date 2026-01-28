# Session Cleanup Guide: Closing Sessions After Knowledge Transfer

## Document Purpose

This guide provides **exact instructions for downstream LLMs** to properly close, clean up, or delete Short-Term Memory MCP sessions after all concepts have been successfully transferred to the Knowledge MCP server.

---

## Table of Contents

1. [Available Cleanup Tools](#1-available-cleanup-tools)
2. [Recommended Cleanup Workflow](#2-recommended-cleanup-workflow)
3. [Tool Reference](#3-tool-reference)
4. [Cleanup Strategies](#4-cleanup-strategies)
5. [Current Limitations](#5-current-limitations)
6. [Decision Matrix](#6-decision-matrix)
7. [Complete Cleanup Examples](#7-complete-cleanup-examples)

---

## 1. Available Cleanup Tools

### MCP Tools (Available to LLMs)

| Tool                           | Purpose                           | Deletes Data? | Scope                 |
| ------------------------------ | --------------------------------- | ------------- | --------------------- |
| `mark_session_complete`        | Mark session as "completed"       | **No**        | Single session        |
| `clear_old_sessions`           | Delete sessions older than N days | **Yes**       | Multiple sessions     |
| `remove_domain_from_whitelist` | Remove trusted domain             | **Yes**       | Domain whitelist only |

### Non-MCP Tools (Manual/Script Only)

| Tool                    | Purpose                 | Access                                   |
| ----------------------- | ----------------------- | ---------------------------------------- |
| `cleanup_database.py`   | Complete database reset | Command-line script                      |
| `delete_research_cache` | Delete cache entry      | Database-level only (not exposed as MCP) |

---

## 2. Recommended Cleanup Workflow

### After Successful Knowledge Transfer

```
STEP 1: Verify All Concepts Transferred
────────────────────────────────────────
Tool: get_unstored_concepts
{
  "session_id": "YYYY-MM-DD"
}
→ Expected: "unstored_count": 0

STEP 2: Mark Session Complete
─────────────────────────────
Tool: mark_session_complete
{
  "session_id": "YYYY-MM-DD"
}
→ Expected: "status": "success"

STEP 3: Choose Cleanup Strategy (see Section 4)
───────────────────────────────────────────────
Option A: Wait for auto-cleanup (7 days)
Option B: Immediate cleanup with clear_old_sessions
Option C: Complete reset with cleanup script
```

---

## 3. Tool Reference

### `mark_session_complete`

**Purpose**: Mark a session as "completed" (status change only, NO deletion)

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session ID (YYYY-MM-DD format) |

**Example**:

```json
{
  "session_id": "2025-01-25"
}
```

**Response (Success)**:

```json
{
  "status": "success",
  "session_id": "2025-01-25",
  "total_concepts": 5,
  "completed_at": "2025-01-25T16:30:00.000Z",
  "message": "Session completed successfully"
}
```

**Response (Warning - unstored concepts)**:

```json
{
  "status": "warning",
  "session_id": "2025-01-25",
  "total_concepts": 5,
  "unstored_count": 2,
  "unstored_concepts": [
    { "concept_id": "c-abc123", "name": "Concept A", "status": "evaluated" },
    { "concept_id": "c-def456", "name": "Concept B", "status": "chunked" }
  ],
  "message": "Session has 2 concepts not yet transferred to Knowledge MCP"
}
```

**Important**: This tool does NOT delete any data. It only changes the session status from "in_progress" to "completed".

---

### `clear_old_sessions`

**Purpose**: Delete sessions (and all associated data) older than N days

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days_to_keep` | integer | No | 7 | Sessions older than this are deleted |

**Cascade Behavior**:

```
DELETE sessions WHERE date < cutoff_date
    ↓ (ON DELETE CASCADE)
Automatically deletes all concepts for those sessions
    ↓ (ON DELETE CASCADE)
Automatically deletes all concept_stage_data for those concepts
```

**Example 1: Keep only last 7 days** (default):

```json
{
  "days_to_keep": 7
}
```

**Example 2: Keep only today's session** (aggressive cleanup):

```json
{
  "days_to_keep": 1
}
```

**Example 3: Delete ALL sessions** (complete cleanup):

```json
{
  "days_to_keep": 0
}
```

**Response**:

```json
{
  "status": "success",
  "cutoff_date": "2025-01-18",
  "days_to_keep": 7,
  "sessions_deleted": 3,
  "concepts_deleted": 45,
  "message": "Cleaned 3 sessions and 45 concepts older than 2025-01-18",
  "deleted_sessions": ["2025-01-15", "2025-01-16", "2025-01-17"]
}
```

**Validation**: `days_to_keep` must be >= 0 (0 means delete everything)

---

### `remove_domain_from_whitelist`

**Purpose**: Remove a domain from the trusted research source whitelist

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domain` | string | Yes | Domain to remove (e.g., "example.com") |

**Example**:

```json
{
  "domain": "outdated-blog.com"
}
```

**Response**:

```json
{
  "success": true,
  "message": "Domain removed: outdated-blog.com"
}
```

**Note**: This only affects the domain whitelist, not sessions or concepts.

---

## 4. Cleanup Strategies

### Strategy A: Auto-Cleanup (Recommended for Normal Use)

**When to use**: Regular daily sessions where data retention for review is acceptable

**Workflow**:

1. Mark session complete
2. Let auto-cleanup handle deletion (runs when new session initializes)
3. Sessions automatically deleted after 7 days (configurable via `DB_RETENTION_DAYS`)

**Advantages**:

- Data available for review/recovery
- No explicit cleanup needed
- Safest approach

**Disadvantages**:

- Data persists for up to 7 days
- Disk space not immediately reclaimed

---

### Strategy B: Immediate Session Cleanup

**When to use**: When you need to free resources immediately after transfer

**Workflow**:

```json
// Step 1: Mark session complete
{
  "tool": "mark_session_complete",
  "params": {"session_id": "2025-01-25"}
}

// Step 2: Delete old sessions (keeps only today)
{
  "tool": "clear_old_sessions",
  "params": {"days_to_keep": 1}
}
```

**Advantages**:

- Immediate disk space recovery
- Clean state for next session

**Disadvantages**:

- Cannot recover deleted data
- Deletes ALL old sessions, not just the current one

---

### Strategy C: Complete Database Reset

**When to use**: Complete fresh start, testing, or troubleshooting

**Method**: Run cleanup script (not available as MCP tool)

```bash
# With backup (recommended)
python scripts/cleanup_database.py --backup --yes

# Without backup
python scripts/cleanup_database.py --yes
```

**What gets deleted**:

- All sessions
- All concepts
- All concept_stage_data
- All research_cache entries

**What is PRESERVED**:

- Domain whitelist (trusted sources)

**Advantages**:

- Complete fresh start
- Maximum disk space recovery (includes VACUUM)

**Disadvantages**:

- All data lost
- Must be run manually (not MCP tool)

---

## 5. Current Limitations

### No Direct Single-Session Deletion

**Problem**: There is no MCP tool to delete a SPECIFIC session immediately.

**Current behavior**: `clear_old_sessions` deletes ALL sessions older than a threshold, not a specific session.

**Workaround**: Use `clear_old_sessions(days_to_keep=1)` to keep only today's session.

---

### No Research Cache Cleanup via MCP

**Problem**: The `delete_research_cache` function exists in the database layer but is NOT exposed as an MCP tool.

**Impact**: Research cache entries persist until manually cleared via the cleanup script.

**Workaround**: Run `cleanup_database.py` script for complete reset, or accept that cache persists (beneficial for reuse across sessions).

---

### No Individual Concept Deletion

**Problem**: There is no MCP tool to delete a specific concept.

**Impact**: Concepts can only be deleted by deleting their parent session.

**Workaround**: Mark concept status as needed, then clean up sessions when ready.

---

## 6. Decision Matrix

| Scenario                    | Recommended Tool        | Parameters                |
| --------------------------- | ----------------------- | ------------------------- |
| Normal session end          | `mark_session_complete` | `session_id` only         |
| Want data deleted in 7 days | `mark_session_complete` | Auto-cleanup handles rest |
| Need immediate cleanup      | `clear_old_sessions`    | `days_to_keep: 1`         |
| Complete fresh start        | `cleanup_database.py`   | `--backup --yes`          |
| Delete all data now (MCP)   | `clear_old_sessions`    | `days_to_keep: 0`         |
| Keep last 3 days only       | `clear_old_sessions`    | `days_to_keep: 3`         |

---

## 7. Complete Cleanup Examples

### Example 1: Standard Transfer + Completion

```
# After all concepts transferred to Knowledge MCP:

1. VERIFY no unstored concepts
   Tool: get_unstored_concepts
   Input: {"session_id": "2025-01-25"}
   Expected: {"unstored_count": 0}

2. MARK session complete
   Tool: mark_session_complete
   Input: {"session_id": "2025-01-25"}
   Expected: {"status": "success"}

3. DONE - Auto-cleanup will handle deletion in 7 days
```

### Example 2: Transfer + Immediate Cleanup

```
# After all concepts transferred, clean up immediately:

1. VERIFY no unstored concepts
   Tool: get_unstored_concepts
   Input: {"session_id": "2025-01-25"}
   Expected: {"unstored_count": 0}

2. MARK session complete
   Tool: mark_session_complete
   Input: {"session_id": "2025-01-25"}
   Expected: {"status": "success"}

3. DELETE all but today's session
   Tool: clear_old_sessions
   Input: {"days_to_keep": 1}
   Expected: {"sessions_deleted": N, "concepts_deleted": M}

4. DONE - Only today's completed session remains
```

### Example 3: Complete Reset After Project Milestone

```
# End of project, want complete fresh start:

1. VERIFY all concepts transferred for all sessions
   Tool: get_unstored_concepts (for each session)

2. MARK all sessions complete
   Tool: mark_session_complete (for each session)

3. DELETE everything via MCP
   Tool: clear_old_sessions
   Input: {"days_to_keep": 0}
   Expected: {"sessions_deleted": ALL, "concepts_deleted": ALL}

# OR use cleanup script for full reset including cache:
# bash: python scripts/cleanup_database.py --backup --yes
```

### Example 4: Handling Partial Transfer Failure

```
# Some concepts failed to transfer:

1. CHECK unstored concepts
   Tool: get_unstored_concepts
   Input: {"session_id": "2025-01-25"}
   Response: {"unstored_count": 2, "concepts": [...]}

2. RETRY transfer for failed concepts
   (Use Knowledge MCP create_concept for each)
   (Then mark_concept_stored for each success)

3. VERIFY all transferred
   Tool: get_unstored_concepts
   Expected: {"unstored_count": 0}

4. MARK session complete
   Tool: mark_session_complete
   Input: {"session_id": "2025-01-25"}
   Expected: {"status": "success"}

5. CLEANUP as desired (Strategy A, B, or C)
```

---

## Summary: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│         SESSION CLEANUP QUICK REFERENCE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AFTER TRANSFER COMPLETE:                                   │
│  ─────────────────────────                                  │
│  1. get_unstored_concepts → verify count = 0                │
│  2. mark_session_complete → status = "success"              │
│                                                             │
│  CLEANUP OPTIONS:                                           │
│  ────────────────                                           │
│  • Auto (default): Wait 7 days, auto-deleted                │
│  • Keep today only: clear_old_sessions(days_to_keep=1)      │
│  • Delete ALL: clear_old_sessions(days_to_keep=0)           │
│  • Full reset: python scripts/cleanup_database.py --yes     │
│                                                             │
│  WHAT GETS DELETED (CASCADE):                               │
│  ────────────────────────────                               │
│  sessions → concepts → concept_stage_data                   │
│                                                             │
│  PRESERVED (NOT DELETED):                                   │
│  ─────────────────────────                                  │
│  • Domain whitelist (trusted research sources)              │
│  • Research cache (only deleted via script)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

_Document Version: 1.0_
_Last Updated: 2025-01-27_
_Compatible with: Short-Term Memory MCP v0.5.0+_
