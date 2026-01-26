# Test Phase 3: Research Cache System

## 📋 Phase Overview

**Goal**: Test the research caching system that stores and retrieves concept research results, manages domain whitelists, and optimizes research workflows to avoid duplicate work.

**Tools Tested** (6):

1. `check_research_cache` - Check if concept has cached research
2. `trigger_research` - Trigger research for a concept (Context7 placeholder)
3. `update_research_cache` - Store/update research results
4. `add_domain_to_whitelist` - Add trusted source domains
5. `remove_domain_from_whitelist` - Remove domains from whitelist
6. `list_whitelisted_domains` - List whitelisted domains with filters

**Estimated Time**: 45-60 minutes

---

## ✅ Prerequisites

- [ ] Phases 1 and 2 completed (or can work independently)
- [ ] Short-Term Memory MCP server is running
- [ ] Fresh session OR willing to work with existing data
- [ ] Understanding that `trigger_research` returns mock data (Context7 not yet integrated)

---

## 🧪 Test Execution

### Test 1: Check Research Cache (Cache Miss)

**Objective**: Check for cached research and verify cache miss behavior.

#### Steps:

1. **Check for concept that doesn't exist in cache**:

```
Tool: check_research_cache
Parameters:
  concept_name: "Rust Ownership System"
```

2. **Verify the response** contains:
   - `cached: false`
   - `entry: null`
   - `cache_age_seconds: null`

3. **Try several other concepts** to verify empty cache:

```
Tool: check_research_cache
Parameters:
  concept_name: "GraphQL Schema Stitching"
```

Expected: `cached: false`, `entry: null`

4. **Test case sensitivity** (should be case-insensitive):

```
Tool: check_research_cache
Parameters:
  concept_name: "rust ownership system"
```

Expected: `cached: false` (still not cached, but query should work)

#### Success Criteria:

- [ ] Cache miss returns `cached: false` with null entry
- [ ] No errors on cache miss
- [ ] Case-insensitive queries work
- [ ] Response time < 200ms

#### Record Results:

```
Cache miss behavior: [correct/incorrect]
Case sensitivity: [handled correctly: yes/no]
Response time: [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 2: Trigger Research (Mock)

**Objective**: Test research triggering (currently returns mock data, future Context7 integration).

#### Steps:

1. **Trigger research for a concept**:

```
Tool: trigger_research
Parameters:
  concept_name: "Rust Ownership System"
  research_prompt: "Focus on borrowing rules, move semantics, and lifetimes"
```

2. **Verify the response** contains:
   - `concept_name: "Rust Ownership System"`
   - `explanation` (string with concept explanation)
   - `source_urls` (array of objects with url, title, quality_score)

3. **Verify mock data characteristics**:
   - Explanation should be non-empty
   - At least 2-3 source URLs
   - Each source has `url`, `title`, `quality_score` (0.0-1.0)
   - Quality scores vary based on domain (official docs should have higher scores)

4. **Trigger research with empty prompt**:

```
Tool: trigger_research
Parameters:
  concept_name: "GraphQL Schema Stitching"
  research_prompt: ""
```

Expected: Success with mock data (empty prompt should work)

5. **Test different concepts**:
   - "PostgreSQL MVCC"
   - "Kubernetes Pods and Services"
   - "React Server Components"

Verify each returns relevant-looking mock data.

#### Success Criteria:

- [ ] Research triggered successfully
- [ ] Mock data includes explanation and sources
- [ ] Source URLs have quality scores
- [ ] Empty research_prompt handled gracefully
- [ ] Response time < 1 second

#### Record Results:

```
Research triggered: [yes/no]
Mock data structure: [correct/incorrect]
Quality scores present: [yes/no]
Response time: [X]ms
Notes: [Note that this is mock data, Context7 not yet integrated]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 3: Update Research Cache

**Objective**: Store research results in cache (INSERT and UPDATE operations - UPSERT).

#### Steps:

1. **Store research results** for "Rust Ownership System":

```
Tool: update_research_cache
Parameters:
  concept_name: "Rust Ownership System"
  explanation: "Rust's ownership system is a set of rules that the compiler checks at compile time. It consists of three main concepts: ownership (each value has a single owner), borrowing (references allow access without taking ownership), and lifetimes (ensure references are valid). This system eliminates memory safety bugs without garbage collection."
  source_urls: [
    {
      "url": "https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html",
      "title": "Understanding Ownership - The Rust Programming Language"
    },
    {
      "url": "https://doc.rust-lang.org/nomicon/ownership.html",
      "title": "Ownership - The Rustonomicon"
    },
    {
      "url": "https://stackoverflow.com/questions/tagged/rust+ownership",
      "title": "Rust Ownership Questions - Stack Overflow"
    }
  ]
```

2. **Verify the response** contains:
   - `success: true`
   - `entry` object with concept_name, explanation, source_urls
   - `action: "inserted"` (first time)
   - `entry.last_researched_at` timestamp
   - `entry.created_at` timestamp

3. **Verify cache hit** now works:

```
Tool: check_research_cache
Parameters:
  concept_name: "Rust Ownership System"
```

Expected: `cached: true`, `entry` with full data, `cache_age_seconds` (small number)

4. **Test UPDATE (UPSERT)** - update the same concept:

```
Tool: update_research_cache
Parameters:
  concept_name: "Rust Ownership System"
  explanation: "Rust's ownership system is a compile-time memory management system with three core principles: 1) Each value has exactly one owner, 2) Ownership can be transferred (moved) or temporarily borrowed, 3) Borrowing rules prevent data races. This eliminates entire classes of bugs like use-after-free, double-free, and data races, all without runtime overhead."
  source_urls: [
    {
      "url": "https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html",
      "title": "Understanding Ownership - The Rust Book"
    },
    {
      "url": "https://doc.rust-lang.org/nomicon/ownership.html",
      "title": "Ownership - The Rustonomicon"
    },
    {
      "url": "https://blog.rust-lang.org/2015/05/11/traits.html",
      "title": "Abstraction without overhead - Rust Blog"
    },
    {
      "url": "https://www.youtube.com/watch?v=VFIOSWy93H0",
      "title": "Rust Ownership Explained - YouTube"
    }
  ]
```

Expected: `action: "updated"`, `entry.updated_at` > `entry.created_at`

5. **Verify UPDATE persisted**:

```
Tool: check_research_cache
Parameters:
  concept_name: "Rust Ownership System"
```

Expected: Updated explanation and 4 source URLs (not 3)

6. **Store several more concepts** to build cache:
   - "PostgreSQL MVCC"
   - "GraphQL Schema Stitching"
   - "Kubernetes Pods"
   - "React Server Components"

7. **Test case-insensitive UPSERT**:

```
Tool: update_research_cache
Parameters:
  concept_name: "rust ownership system"
  explanation: "Testing case insensitivity"
  source_urls: [{"url": "https://test.com", "title": "Test"}]
```

Expected: Should UPDATE (not insert new), verify with check_research_cache

#### Success Criteria:

- [ ] First insert returns `action: "inserted"`
- [ ] Update returns `action: "updated"`
- [ ] Cache hit works after insert
- [ ] Updated data persists correctly
- [ ] Case-insensitive UPSERT works
- [ ] Response time < 500ms

#### Record Results:

```
INSERT worked: [yes/no]
UPDATE worked (UPSERT): [yes/no]
Cache hit after insert: [yes/no]
Case-insensitive UPSERT: [yes/no]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 4: Add Domain to Whitelist

**Objective**: Build a whitelist of trusted source domains with quality scores.

#### Steps:

1. **Add official documentation domains**:

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "doc.rust-lang.org"
  category: "official"
  quality_score: 1.0
```

2. **Verify the response** contains:
   - `success: true`
   - `domain` object with:
     - `domain: "doc.rust-lang.org"`
     - `category: "official"`
     - `quality_score: 1.0`
     - `added_at` timestamp
     - `added_by: "system"` (default)

3. **Add more domains** with different categories and scores:

Official docs (high quality):

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "docs.python.org"
  category: "official"
  quality_score: 1.0
```

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "developer.mozilla.org"
  category: "official"
  quality_score: 0.95
```

In-depth tutorials:

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "use-the-index-luke.com"
  category: "in_depth"
  quality_score: 0.9
```

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "blog.rust-lang.org"
  category: "in_depth"
  quality_score: 0.85
```

Authoritative sources:

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "stackoverflow.com"
  category: "authoritative"
  quality_score: 0.7
```

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "github.com"
  category: "authoritative"
  quality_score: 0.6
```

Community resources:

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "reddit.com"
  category: "community"
  quality_score: 0.5
```

4. **Test duplicate domain** (should handle gracefully):

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "doc.rust-lang.org"
  category: "official"
  quality_score: 1.0
```

Expected: May return error or handle as update (document behavior)

5. **Test invalid quality score**:

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "test.com"
  category: "official"
  quality_score: 1.5
```

Expected: Error (quality_score must be 0.0-1.0) OR clamped to 1.0

6. **Test invalid category**:

```
Tool: add_domain_to_whitelist
Parameters:
  domain: "test.com"
  category: "invalid_category"
  quality_score: 0.8
```

Expected: Error with valid category list

#### Success Criteria:

- [ ] Domains added successfully with correct attributes
- [ ] All 4 categories work (official, in_depth, authoritative, community)
- [ ] Quality scores stored correctly
- [ ] Duplicate domain handled gracefully
- [ ] Invalid quality score rejected or clamped
- [ ] Invalid category rejected
- [ ] Response time < 300ms per domain

#### Record Results:

```
Domains added: [8+]
Categories tested: [official, in_depth, authoritative, community]
Duplicate handling: [document behavior]
Invalid input validation: [works/doesn't work]
Response time (average): [X]ms
Notes: [any observations]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 5: List Whitelisted Domains

**Objective**: Query whitelisted domains with optional category filtering.

#### Steps:

1. **List all domains** (no filter):

```
Tool: list_whitelisted_domains
Parameters:
  category: [leave empty]
```

2. **Verify the response** contains:
   - `domains` array with 8+ domains (from Test 4)
   - `count: 8` (or higher)
   - `filter: null` or similar

3. **Verify domain objects** have all fields:
   - `domain` (string)
   - `category` (string)
   - `quality_score` (float)
   - `added_at` (timestamp)
   - `added_by` (string)

4. **Filter by "official" category**:

```
Tool: list_whitelisted_domains
Parameters:
  category: "official"
```

Expected:

- 3 domains (doc.rust-lang.org, docs.python.org, developer.mozilla.org)
- `filter: "official"`

5. **Filter by "in_depth" category**:

```
Tool: list_whitelisted_domains
Parameters:
  category: "in_depth"
```

Expected: 2 domains (use-the-index-luke.com, blog.rust-lang.org)

6. **Filter by "authoritative" category**:

```
Tool: list_whitelisted_domains
Parameters:
  category: "authoritative"
```

Expected: 2 domains (stackoverflow.com, github.com)

7. **Filter by "community" category**:

```
Tool: list_whitelisted_domains
Parameters:
  category: "community"
```

Expected: 1 domain (reddit.com)

8. **Test invalid category filter**:

```
Tool: list_whitelisted_domains
Parameters:
  category: "invalid_category"
```

Expected: Error OR empty list (document behavior)

9. **Verify quality score ordering** (domains should be ordered by quality score DESC or insertion order):
   - Check if official docs (score 1.0) appear first
   - Check ordering logic

#### Success Criteria:

- [ ] All domains listed without filter
- [ ] Category filtering works for all 4 categories
- [ ] Correct counts for each category
- [ ] Invalid category handled gracefully
- [ ] Response time < 300ms

#### Record Results:

```
Total domains: [8+]
Official: [3]
In-depth: [2]
Authoritative: [2]
Community: [1]
Filtering works: [yes/no]
Response time: [X]ms
Notes: [any observations, ordering logic]
```

---

**🛑 CHECKPOINT: Stop here and report results before continuing**

---

### Test 6: Remove Domain from Whitelist

**Objective**: Remove domains from the whitelist.

#### Steps:

1. **Remove a test domain**:

```
Tool: remove_domain_from_whitelist
Parameters:
  domain: "reddit.com"
```

2. **Verify the response** contains:
   - `success: true`
   - `message` confirming removal

3. **Verify removal persisted**:

```
Tool: list_whitelisted_domains
Parameters:
  category: [leave empty]
```

Expected: `count` decreased by 1, reddit.com not in list

4. **Try to remove the same domain again** (should fail gracefully):

```
Tool: remove_domain_from_whitelist
Parameters:
  domain: "reddit.com"
```

Expected: `success: false` with message like "Domain not found"

5. **Remove several more domains**:

```
Tool: remove_domain_from_whitelist
Parameters:
  domain: "github.com"
```

```
Tool: remove_domain_from_whitelist
Parameters:
  domain: "stackoverflow.com"
```

6. **Verify category counts updated**:

```
Tool: list_whitelisted_domains
Parameters:
  category: "authoritative"
```

Expected: `count: 0` (both authoritative domains removed)

7. **Test case sensitivity in removal**:

```
Tool: remove_domain_from_whitelist
Parameters:
  domain: "DOC.RUST-LANG.ORG"
```

Expected: Should remove doc.rust-lang.org (case-insensitive) OR return error (document behavior)

8. **Remove non-existent domain**:

```
Tool: remove_domain_from_whitelist
Parameters:
  domain: "nonexistent.example.com"
```

Expected: `success: false` with appropriate message

#### Success Criteria:

- [ ] Domains removed successfully
- [ ] Removal persists (verified with list)
- [ ] Removing non-existent domain returns success: false
- [ ] Category counts update correctly
- [ ] Case sensitivity handled appropriately
- [ ] Response time < 300ms

#### Record Results:

```
Domains removed: [3]
Removal persisted: [yes/no]
Non-existent domain handling: [correct/incorrect]
Case sensitivity: [document behavior]
Response time: [X]ms
Notes: [any observations]
```

---

## 📊 Phase 3 Test Report

**Completion Date**: [YYYY-MM-DD]
**Tester**: [Your Name]
**MCP Server Version**: [Check package.json or git commit]

### Summary

| Test | Tool                         | Status            | Response Time | Notes          |
| ---- | ---------------------------- | ----------------- | ------------- | -------------- |
| 1    | check_research_cache         | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |                |
| 2    | trigger_research             | ⬜ Pass / ⬜ Fail | \_\_\_ ms     | Mock data only |
| 3    | update_research_cache        | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |                |
| 4    | add_domain_to_whitelist      | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |                |
| 5    | list_whitelisted_domains     | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |                |
| 6    | remove_domain_from_whitelist | ⬜ Pass / ⬜ Fail | \_\_\_ ms     |                |

### Issues Found

1. **Issue**: [Description]
   - **Severity**: Critical / High / Medium / Low
   - **Tool**: [Tool name]
   - **Steps to Reproduce**: [Steps]
   - **Expected**: [Expected behavior]
   - **Actual**: [Actual behavior]

2. [Add more issues as needed]

### Performance Observations

- Average response time: \_\_\_ ms
- Slowest operation: [Tool name] at \_\_\_ ms
- Cache lookup speed: \_\_\_ ms
- Any performance concerns: [Notes]

### Cache System State After Phase 3

- Cached concepts: [N]
- Whitelisted domains: [N]
- Domains by category:
  - official: [N]
  - in_depth: [N]
  - authoritative: [N]
  - community: [N]

### Functional Checks

- [ ] Cache miss returns false with null entry
- [ ] Cache hit returns true with full data
- [ ] UPSERT behavior works (insert then update)
- [ ] Case-insensitive concept name matching
- [ ] Domain whitelist CRUD operations work
- [ ] Category filtering works
- [ ] Quality scores stored and retrieved correctly

### Integration Notes

- **trigger_research**: Currently returns mock data (Context7 not integrated yet)
- **Quality scoring**: Test how source_urls are scored based on whitelisted domains
- **Cache TTL**: Note if cache has expiration (check cache_age_seconds over time)

### Overall Assessment

⬜ **PASS** - All tests passed, ready for Phase 4
⬜ **PASS WITH ISSUES** - Tests passed but issues noted
⬜ **FAIL** - Critical issues prevent progression to Phase 4

### Recommendations

[Any recommendations for improvements, bug fixes, or documentation updates]

---

## 🎯 Next Steps

If Phase 3 **PASSED**:

- ✅ Proceed to **Phase 4: Code Teacher Integration**
- ✅ Research cache can be used in future sessions

If Phase 3 **FAILED**:

- ⚠️ Document all failures in the test report
- ⚠️ Create GitHub issues for bugs found
- ⚠️ Fix critical issues before proceeding
- ⚠️ Re-run Phase 3 after fixes

---

## 📝 Notes for Future Context7 Integration

When Context7 is integrated with `trigger_research`:

- [ ] Update Test 2 to validate real research results
- [ ] Test research prompt customization
- [ ] Verify source URL extraction from real web pages
- [ ] Test error handling for network failures
- [ ] Validate quality scoring with real domains
- [ ] Test caching of Context7 results
