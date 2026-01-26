# Test Phase 4: Code Teacher Integration

## 📋 Phase Overview

**Goal**: Test the Code Teacher support tools that provide optimized, cached queries for today's learning context. These tools enable the Code Teacher session to quickly understand what you're learning and building without expensive database queries.

**Tools Tested** (3):

1. `get_todays_concepts` - Retrieve all concepts from today with statistics (cached 5 min)
2. `get_todays_learning_goals` - Lightweight query for goals and stats (cached 5 min)
3. `search_todays_concepts` - Search today's concepts by name/content (cached 5 min)

**Estimated Time**: 30-45 minutes

---

## ✅ Prerequisites

- [ ] Phase 1 completed (or have an active session with concepts)
- [ ] Short-Term Memory MCP server is running
- [ ] **IMPORTANT**: You have a session created for TODAY with at least 5 concepts
- [ ] If you completed Phase 1-2 yesterday, create a new session today with concepts
- [ ] Timer or clock to measure 5-minute cache intervals

---

## 🧪 Test Execution

### Setup: Create Today's Session (if needed)

If you don't have a session for today, create one now:

```
Tool: initialize_daily_session
Parameters:
  learning_goal: "Master async/await patterns in Rust and tokio runtime"
  building_goal: "Build a concurrent web scraper with rate limiting"
```

Then add concepts:

```
Tool: store_concepts_from_research
Parameters:
  session_id: [today's date]
  concepts: [
    {"concept_name": "Tokio Runtime", "data": {"complexity": "intermediate"}},
    {"concept_name": "Futures and Polling", "data": {"complexity": "advanced"}},
    {"concept_name": "async/await Syntax", "data": {"complexity": "beginner"}},
    {"concept_name": "Rate Limiting Algorithms", "data": {"complexity": "intermediate"}},
    {"concept_name": "Concurrent HTTP Requests", "data": {"complexity": "intermediate"}}
  ]
```

---

### Test 1: Get Today's Concepts (First Call - Cache Miss)

**Objective**: Retrieve all concepts from today's session and measure cache miss performance.

#### Steps:

1. **Make the first call** (cache miss):

```
Tool: get_todays_concepts
Parameters: [no parameters]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `date` matching today (YYYY-MM-DD)
   - `session_id` matching today
   - `learning_goal` and `building_goal` from session
   - `concept_count: 5` (or your count)
   - `concepts_by_status` object with counts (e.g., `{"identified": 5}`)
   - `concepts` array with full concept data
   - `cache_hit: false` ⚠️ **IMPORTANT**: First call should be cache miss

3. **Verify concept data** includes:
   - `concept_id` (UUID)
   - `concept_name`
   - `current_status`
   - `current_data`
   - Timestamps (identified_at, etc.)

4. **Record response time** for cache miss (baseline):
   - Expected: < 500ms
   - Note: This queries the database

#### Success Criteria:

- [ ] Status is "success"
- [ ] All concepts returned with full data
- [ ] `cache_hit: false` (first call)
- [ ] Statistics calculated correctly
- [ ] Response time < 500ms

#### Record Results:

```
Status: [success/error]
Concept count: [5]
Cache hit: [false]
Response time (cache miss): [X]ms ⬅️ BASELINE
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 2: Get Today's Concepts (Second Call - Cache Hit)

**Objective**: Verify caching works and measure cache hit performance (should be 5-10x faster).

#### Steps:

1. **Immediately call again** (within 5 minutes):

```
Tool: get_todays_concepts
Parameters: [no parameters]
```

2. **Verify the response** contains:
   - Same data as Test 1
   - `cache_hit: true` ⚠️ **IMPORTANT**: Should now be cache hit

3. **Record response time** for cache hit:
   - Expected: < 100ms (target: 5-10x faster than cache miss)
   - Compare with Test 1 baseline

4. **Calculate speedup**:
   - Speedup = (Test 1 time) / (Test 2 time)
   - Expected: 5x-10x speedup

5. **Test cache consistency** - modify a concept:

```
Tool: update_concept_status
Parameters:
  concept_id: [UUID of first concept]
  new_status: "chunked"
```

6. **Query again** - cache should be invalidated:

```
Tool: get_todays_concepts
Parameters: [no parameters]
```

Expected:

- `cache_hit: false` (cache invalidated)
- Updated concept shows `current_status: "chunked"`

7. **Call again immediately**:

```
Tool: get_todays_concepts
Parameters: [no parameters]
```

Expected: `cache_hit: true` (new cache created)

#### Success Criteria:

- [ ] Second call returns `cache_hit: true`
- [ ] Cache hit is 5x+ faster than cache miss
- [ ] Cache invalidates on concept modification
- [ ] New cache created after invalidation
- [ ] Cache hit response time < 100ms

#### Record Results:

```
Cache hit: [true]
Response time (cache hit): [X]ms
Speedup: [N]x faster
Cache invalidation: [works/doesn't work]
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 3: Get Today's Learning Goals (Lightweight Query)

**Objective**: Test the lightweight query that returns only goals and statistics (no full concept data).

#### Steps:

1. **Call the lightweight tool** (first call - cache miss):

```
Tool: get_todays_learning_goals
Parameters: [no parameters]
```

2. **Verify the response** contains:
   - `status: "success"`
   - `date` matching today
   - `session_id` matching today
   - `learning_goal` and `building_goal`
   - `concept_count`
   - `concepts_by_status` (statistics)
   - `cache_hit: false`
   - **NO** `concepts` array (this is the key difference!)

3. **Compare payload size** with `get_todays_concepts`:
   - `get_todays_learning_goals` should have smaller response (no concept array)
   - Note the difference in data returned

4. **Test cache hit**:

```
Tool: get_todays_learning_goals
Parameters: [no parameters]
```

Expected: `cache_hit: true`, same data

5. **Test that both tools have separate caches**:
   - Both should cache independently
   - Invalidating concept should invalidate both caches

6. **Modify a concept to test cache invalidation**:

```
Tool: update_concept_status
Parameters:
  concept_id: [UUID]
  new_status: "encoded"
```

7. **Check both caches are invalidated**:
   - Call `get_todays_learning_goals` → `cache_hit: false`
   - Call `get_todays_concepts` → `cache_hit: false`

#### Success Criteria:

- [ ] Lightweight query returns goals without concept array
- [ ] Response is smaller than full concept query
- [ ] Caching works (5-minute TTL)
- [ ] Cache invalidates on concept changes
- [ ] Response time < 300ms (miss), < 50ms (hit)

#### Record Results:

```
Status: [success/error]
Concepts array included: [no - correct!]
Cache hit (second call): [true]
Response time (miss): [X]ms
Response time (hit): [X]ms
Speedup: [N]x
Cache invalidation: [works/doesn't work]
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 4: Search Today's Concepts

**Objective**: Search concepts by name or content with per-query caching.

#### Steps:

1. **Search for a concept by name** (first call - cache miss):

```
Tool: search_todays_concepts
Parameters:
  search_term: "tokio"
```

2. **Verify the response** contains:
   - `status: "success"`
   - `date` matching today
   - `session_id` matching today
   - `search_term: "tokio"`
   - `match_count: 1` (or number of matches)
   - `matches` array with matching concept(s)
   - `cache_hit: false`

3. **Verify search is case-insensitive**:

```
Tool: search_todays_concepts
Parameters:
  search_term: "TOKIO"
```

Expected: Same results as lowercase search

4. **Test partial matching**:

```
Tool: search_todays_concepts
Parameters:
  search_term: "async"
```

Expected: Should match "async/await Syntax" (and possibly other concepts with "async" in data)

5. **Test search in concept data** (not just name):

```
Tool: search_todays_concepts
Parameters:
  search_term: "intermediate"
```

Expected: Should match concepts with `"complexity": "intermediate"` in their data

6. **Test cache hit for same query**:

```
Tool: search_todays_concepts
Parameters:
  search_term: "tokio"
```

Expected: `cache_hit: true`, faster response

7. **Test different search queries have separate caches**:

```
Tool: search_todays_concepts
Parameters:
  search_term: "rust"
```

Expected: `cache_hit: false` (different query)

8. **Test empty search term**:

```
Tool: search_todays_concepts
Parameters:
  search_term: ""
```

Expected: Error with "EMPTY_SEARCH_TERM"

9. **Test no matches**:

```
Tool: search_todays_concepts
Parameters:
  search_term: "nonexistent_concept_xyz"
```

Expected: `status: "success"`, `match_count: 0`, empty `matches` array

10. **Test cache invalidation on concept modification**:

```
Tool: update_concept_status
Parameters:
  concept_id: [UUID of a concept]
  new_status: "evaluated"
```

Then search again:

```
Tool: search_todays_concepts
Parameters:
  search_term: "tokio"
```

Expected: `cache_hit: false` (cache invalidated)

#### Success Criteria:

- [ ] Search finds concepts by name
- [ ] Search finds concepts by content (in current_data)
- [ ] Case-insensitive search works
- [ ] Partial matching works
- [ ] Per-query caching works (different queries have different caches)
- [ ] Cache invalidation works on concept changes
- [ ] Empty search term returns error
- [ ] No matches handled gracefully
- [ ] Response time < 300ms (miss), < 100ms (hit)

#### Record Results:

```
Search by name: [works/doesn't work]
Search by content: [works/doesn't work]
Case-insensitive: [yes/no]
Partial matching: [yes/no]
Cache hit (repeated query): [true/false]
Per-query caching: [works/doesn't work]
Cache invalidation: [works/doesn't work]
Response time (miss): [X]ms
Response time (hit): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 5: Cache TTL (5-Minute Expiration)

**Objective**: Verify that caches expire after 5 minutes (300 seconds).

#### Steps:

1. **Make a cached call**:

```
Tool: get_todays_concepts
Parameters: [no parameters]
```

Expected: `cache_hit: true` (from earlier tests)

2. **Note the current time**: [HH:MM:SS]

3. **Wait 5+ minutes** ⏰
   - Take a break
   - Do other work
   - Ensure at least 5 minutes pass
   - DO NOT modify any concepts during this time

4. **After 5+ minutes, call again**:

```
Tool: get_todays_concepts
Parameters: [no parameters]
```

Expected: `cache_hit: false` (cache expired and rebuilt)

5. **Verify cache rebuilt**:

```
Tool: get_todays_concepts
Parameters: [no parameters]
```

Expected: `cache_hit: true` (new cache)

6. **Test TTL for all three tools**:
   - `get_todays_learning_goals` - should also have expired cache
   - `search_todays_concepts` - should also have expired cache

#### Success Criteria:

- [ ] Cache expires after 5 minutes
- [ ] Cache is automatically rebuilt on next query
- [ ] All three Code Teacher tools respect 5-minute TTL
- [ ] No errors during cache expiration/rebuild

#### Record Results:

```
Cache expired after 5 minutes: [yes/no]
Cache rebuilt successfully: [yes/no]
All tools respect TTL: [yes/no]
Notes: [any observations, exact timing]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 6: No Session Today (Edge Case)

**Objective**: Test behavior when no session exists for today.

#### Steps:

1. **Test on a date with no session** (if possible, test with tomorrow's date):
   - Option A: Wait until tomorrow (no session created yet)
   - Option B: If your MCP allows, query with a future date parameter (may not be supported)

2. **Call get_todays_concepts**:

```
Tool: get_todays_concepts
Parameters: [no parameters]
```

Expected: `status: "not_found"` or similar

3. **Call get_todays_learning_goals**:

```
Tool: get_todays_learning_goals
Parameters: [no parameters]
```

Expected: `status: "not_found"`

4. **Call search_todays_concepts**:

```
Tool: search_todays_concepts
Parameters:
  search_term: "test"
```

Expected: `status: "not_found"` or `match_count: 0`

5. **Verify no errors** (graceful handling of missing session)

#### Success Criteria:

- [ ] Missing session returns "not_found" status
- [ ] No crashes or errors
- [ ] Graceful error messages
- [ ] Tools don't attempt to cache non-existent data

#### Record Results:

```
Missing session handling: [correct/incorrect]
Error messages: [clear/unclear]
No crashes: [yes/no]
Notes: [any observations]
```

---

## 📊 Phase 4 Test Report

**Completion Date**: [YYYY-MM-DD]
**Tester**: [Your Name]
**MCP Server Version**: [Check package.json or git commit]

### Summary

| Test | Tool                      | Status            | Cache Miss | Cache Hit | Speedup | Notes |
| ---- | ------------------------- | ----------------- | ---------- | --------- | ------- | ----- |
| 1-2  | get_todays_concepts       | ⬜ Pass / ⬜ Fail | \_\_\_ ms  | \_\_\_ ms | \_\_\_x |       |
| 3    | get_todays_learning_goals | ⬜ Pass / ⬜ Fail | \_\_\_ ms  | \_\_\_ ms | \_\_\_x |       |
| 4    | search_todays_concepts    | ⬜ Pass / ⬜ Fail | \_\_\_ ms  | \_\_\_ ms | \_\_\_x |       |
| 5    | Cache TTL (all tools)     | ⬜ Pass / ⬜ Fail | -          | -         | -       |       |
| 6    | No session edge case      | ⬜ Pass / ⬜ Fail | -          | -         | -       |       |

### Performance Analysis

**Cache Performance Targets**:

- ✅ Cache hit < 100ms (target met: yes/no)
- ✅ 5x speedup vs cache miss (achieved: \_\_\_x)
- ✅ Cache invalidation < 500ms (verified: yes/no)

**Observations**:

- Average cache miss time: \_\_\_ ms
- Average cache hit time: \_\_\_ ms
- Overall speedup: \_\_\_x
- Cache hit rate during testing: \_\_\_%

### Issues Found

1. **Issue**: [Description]
   - **Severity**: Critical / High / Medium / Low
   - **Tool**: [Tool name]
   - **Steps to Reproduce**: [Steps]
   - **Expected**: [Expected behavior]
   - **Actual**: [Actual behavior]

2. [Add more issues as needed]

### Functional Checks

- [ ] Cache miss populates cache (cache_hit: false)
- [ ] Cache hit uses cache (cache_hit: true)
- [ ] Cache provides 5x+ speedup
- [ ] Cache invalidates on concept modifications
- [ ] Cache expires after 5 minutes (TTL)
- [ ] Lightweight query excludes concept array
- [ ] Search is case-insensitive
- [ ] Search matches both name and content
- [ ] Per-query caching for searches
- [ ] Missing session handled gracefully

### Cache System Verification

- [ ] `get_todays_concepts` caching works
- [ ] `get_todays_learning_goals` caching works
- [ ] `search_todays_concepts` per-query caching works
- [ ] Cache invalidation propagates to all tools
- [ ] 5-minute TTL respected by all tools

### Overall Assessment

⬜ **PASS** - All tests passed, ready for Phase 5
⬜ **PASS WITH ISSUES** - Tests passed but issues noted
⬜ **FAIL** - Critical issues prevent progression to Phase 5

### Recommendations

[Any recommendations for cache tuning, performance improvements, or documentation updates]

---

## 🎯 Next Steps

If Phase 4 **PASSED**:

- ✅ Proceed to **Phase 5: Knowledge Graph (Questions & Relationships)**
- ✅ Code Teacher integration is working correctly

If Phase 4 **FAILED**:

- ⚠️ Document all failures in the test report
- ⚠️ Create GitHub issues for bugs found
- ⚠️ Check for caching issues or race conditions
- ⚠️ Re-run Phase 4 after fixes

---

## 💡 Tips for Code Teacher Usage

Based on these tests, here's how Code Teacher should use these tools:

1. **On session start**: Call `get_todays_learning_goals` to understand context (lightweight)
2. **When detailed context needed**: Call `get_todays_concepts` for full concept list
3. **When user asks about specific topics**: Use `search_todays_concepts` to find relevant concepts
4. **Rely on caching**: These calls are cached for 5 minutes, so don't worry about performance
5. **Handle missing sessions gracefully**: Check for `status: "not_found"` and prompt user to create session
