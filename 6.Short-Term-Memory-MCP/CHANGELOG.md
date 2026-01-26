# Changelog

## fix-mcp-critical-null-checks-011CUzEm9nkcwos7Udem9ZdK

### Session 001 – Null Pointer Dereference Fix (2025-11-10)

- **CRITICAL FIX**: Fixed null pointer dereference in `add_concept_question_impl`
- Added null check after `async_get_concept()` to prevent crash if concept deleted during operation
- Prevents `AttributeError: 'NoneType' object has no attribute 'get'` and `TypeError: 'NoneType' object is not subscriptable`
- Returns clear error message: "Concept was deleted during operation"
- All 170 tests still passing (100%)
- Files changed: `short_term_mcp/tools_impl.py:867-872`

### Session 002 – TOCTOU Race Condition Fix (2025-11-10)

- **CRITICAL FIX**: Fixed Time-of-Check-Time-of-Use (TOCTOU) race condition in `add_question_to_concept`
- Moved concept read inside transaction for atomic read-modify-write operation
- Prevents lost updates when multiple threads add questions simultaneously
- Prevents data corruption from concurrent modifications
- All 170 tests still passing (100%)
- Files changed: `short_term_mcp/database.py:516-551`

### Session 003 – TOCTOU Race Condition Fix in update_concept_data (2025-11-10)

- **CRITICAL FIX**: Fixed Time-of-Check-Time-of-Use (TOCTOU) race condition in `update_concept_data`
- Moved concept read inside transaction for atomic read-modify-write operation
- Prevents lost relationship updates when multiple users add relationships simultaneously
- Prevents data corruption from concurrent modifications to current_data
- Double-fetch anti-pattern eliminated (was fetching concept twice)
- All 170 tests still passing (100%)
- Files changed: `short_term_mcp/database.py:553-578`

### Session 004 – Nested Transaction Atomicity Fix (2025-11-10)

- **CRITICAL FIX**: Fixed non-atomic database updates in `mark_concept_stored_impl`
- Replaced nested transactions with single atomic UPDATE for both status and knowledge_mcp_id
- Prevents data inconsistency where concepts marked "STORED" without knowledge_mcp_id
- Transaction-inside-transaction anti-pattern eliminated
- All 170 tests still passing (100%)
- Files changed: `short_term_mcp/tools_impl.py:393-435`

## fix-failing-tests-rca-011CUz77HdenbxENKifw3EJd

### Session 001 – Session Retention Bug Fix (2025-11-10)

- **CRITICAL FIX**: Fixed session retention bug in `initialize_daily_session_impl`
- Moved cleanup logic to run BEFORE session creation instead of after
- Prevents backdated sessions (e.g., in tests) from being immediately deleted
- All 42 failing tests now pass (170/170 tests passing - 100%)
- Files changed: `short_term_mcp/tools_impl.py:110-125`

## feat-research-cache-20251107

### Session 001 – Database Schema & Models (2025-11-10)

- Added research cache + domain whitelist tables with indexes and seed domains.
- Introduced SourceURL, ResearchCacheEntry, and DomainWhitelist Pydantic models.
- Added dedicated schema/model tests for the research cache subsystem.
- Updated SimpleCache to support synchronous clearing for deterministic tests.
