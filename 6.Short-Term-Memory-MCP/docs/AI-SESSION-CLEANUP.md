# AI Guide: Session Cleanup via MCP Tools

## Purpose

Close and delete Short-Term Memory sessions after transferring concepts to Knowledge MCP.

---

## Required Tools

| Tool                    | Action                                |
| ----------------------- | ------------------------------------- |
| `mark_session_complete` | Mark session finished (status change) |
| `clear_old_sessions`    | Delete session data (actual deletion) |

---

## Workflow

```
1. mark_session_complete(session_id)  → Status: "completed"
2. clear_old_sessions(days_to_keep=1) → Delete all except today
```

---

## Tool 1: `mark_session_complete`

**Purpose**: Mark session as finished. Does NOT delete data.

**Input**:

```json
{ "session_id": "2025-01-25" }
```

**Output (success)**:

```json
{
  "status": "success",
  "session_id": "2025-01-25",
  "completed_at": "2025-01-25T16:30:00Z"
}
```

**Output (warning - unstored concepts)**:

```json
{
  "status": "warning",
  "unstored_count": 2,
  "unstored_concepts": [{ "concept_id": "c-abc", "name": "Concept A" }]
}
```

**Rule**: Only mark complete when `get_unstored_concepts` returns `unstored_count: 0`.

---

## Tool 2: `clear_old_sessions`

**Purpose**: Delete sessions older than N days. Cascades to concepts and stage data.

**Input**:

```json
{ "days_to_keep": 1 }
```

**Output**:

```json
{
  "status": "success",
  "sessions_deleted": 3,
  "concepts_deleted": 45,
  "deleted_sessions": ["2025-01-22", "2025-01-23", "2025-01-24"]
}
```

**Parameter Values**:

| `days_to_keep` | Effect              |
| -------------- | ------------------- |
| `7` (default)  | Keep last 7 days    |
| `1`            | Keep only today     |
| `0`            | Delete ALL sessions |

**Cascade**: Deleting a session automatically deletes all its concepts and stage data.

---

## Complete Example

```
STEP 1: Verify transfer complete
────────────────────────────────
Tool: get_unstored_concepts
Input: {"session_id": "2025-01-25"}
Assert: unstored_count == 0

STEP 2: Mark session complete
─────────────────────────────
Tool: mark_session_complete
Input: {"session_id": "2025-01-25"}
Assert: status == "success"

STEP 3: Delete old sessions
───────────────────────────
Tool: clear_old_sessions
Input: {"days_to_keep": 1}
Result: All sessions except today deleted
```

---

## Quick Reference

```
┌────────────────────────────────────────────┐
│  CLOSE SESSION AFTER TRANSFER              │
├────────────────────────────────────────────┤
│  1. mark_session_complete(session_id)      │
│  2. clear_old_sessions(days_to_keep=1)     │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  DELETE ALL DATA                           │
├────────────────────────────────────────────┤
│  clear_old_sessions(days_to_keep=0)        │
└────────────────────────────────────────────┘
```

---

## Error Handling

| Error                                          | Cause                     | Action                                  |
| ---------------------------------------------- | ------------------------- | --------------------------------------- |
| `status: "warning"` from mark_session_complete | Unstored concepts exist   | Transfer remaining concepts first       |
| `sessions_deleted: 0`                          | No old sessions to delete | Expected if only today's session exists |

---

## Notes

- `mark_session_complete` = status change only (no deletion)
- `clear_old_sessions` = actual data deletion (cascades)
- Research cache is NOT deleted by these tools (persists for reuse)
- Domain whitelist is preserved
