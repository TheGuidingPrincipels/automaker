# Code Teacher API Documentation

## Phase 5: Code Teacher Support Tools

**Status:** ✅ Complete
**Date:** 2025-10-10
**Version:** 1.0

---

## 📋 Overview

The Code Teacher Support tools provide optimized, cached access to today's learning session for Code Teacher's context awareness. These tools enable Code Teacher to understand what you're learning today and provide relevant, contextual assistance.

### Key Features

- **5-Minute Caching**: All queries cached for optimal performance
- **Thread-Safe**: Concurrent Code Teacher queries handled safely
- **Automatic Expiration**: Cache entries expire after TTL
- **Lightweight Queries**: Options for minimal data retrieval
- **Search Capability**: Find specific concepts quickly

---

## 🛠️ Tools

### 1. get_todays_concepts()

**Purpose:** Retrieve all concepts from today's session with full details.

**Parameters:** None

**Returns:**

```json
{
  "status": "success",
  "date": "2025-10-10",
  "session_id": "2025-10-10",
  "learning_goal": "Learn React Hooks",
  "building_goal": "Build todo app",
  "concept_count": 25,
  "concepts_by_status": {
    "identified": 10,
    "chunked": 8,
    "encoded": 5,
    "evaluated": 2,
    "stored": 0
  },
  "concepts": [
    {
      "concept_id": "uuid-001",
      "concept_name": "useState Hook",
      "current_status": "chunked",
      "current_data": {
        "area": "Frontend",
        "topic": "React",
        "subtopic": "Hooks"
      },
      "identified_at": "2025-10-10T10:30:00",
      "chunked_at": "2025-10-10T11:15:00",
      ...
    },
    ...
  ],
  "cache_hit": false
}
```

**Use Cases:**

- Code Teacher needs full context of today's learning
- Providing comprehensive assistance based on all concepts
- Reviewing progress through pipeline stages

**Performance:**

- Cache hit: <1ms
- Cache miss: <50ms
- Cached for: 5 minutes

---

### 2. get_todays_learning_goals()

**Purpose:** Get today's learning goals without full concept list (lightweight).

**Parameters:** None

**Returns:**

```json
{
  "status": "success",
  "date": "2025-10-10",
  "session_id": "2025-10-10",
  "learning_goal": "Learn React Hooks",
  "building_goal": "Build todo app",
  "session_status": "in_progress",
  "concept_count": 25,
  "concepts_by_status": {
    "identified": 10,
    "chunked": 8,
    "encoded": 5,
    "evaluated": 2,
    "stored": 0
  },
  "cache_hit": false
}
```

**Use Cases:**

- Quick context check without loading all concepts
- Code Teacher startup context awareness
- Status bar or summary displays

**Performance:**

- Cache hit: <1ms
- Cache miss: <20ms
- Cached for: 5 minutes

---

### 3. search_todays_concepts(search_term)

**Purpose:** Search today's concepts by name or content.

**Parameters:**

- `search_term` (string, required): Search text (case-insensitive)

**Returns:**

```json
{
  "status": "success",
  "date": "2025-10-10",
  "session_id": "2025-10-10",
  "search_term": "useState",
  "match_count": 1,
  "matches": [
    {
      "concept_id": "uuid-001",
      "concept_name": "useState Hook",
      "current_status": "chunked",
      "current_data": {
        "area": "Frontend",
        "topic": "React"
      },
      ...
    }
  ],
  "cache_hit": false
}
```

**Use Cases:**

- Finding specific concepts discussed today
- Quick lookup for user questions
- Contextual code assistance

**Performance:**

- Cache hit: <1ms
- Cache miss: <100ms (with 25 concepts)
- Cached per query for: 5 minutes

**Search Behavior:**

- Case-insensitive
- Searches in `concept_name` field
- Searches in `current_data` JSON content
- Returns all matches

---

## 📊 Caching System

### How Caching Works

1. **Cache Keys:**
   - `todays_concepts:{date}` - Full concept list
   - `todays_goals:{date}` - Learning goals only
   - `search:{date}:{search_term}` - Search results

2. **Cache Lifecycle:**
   - TTL: 5 minutes (300 seconds)
   - Thread-safe with locking
   - Automatic expiration on access
   - Independent caches per query type

3. **Cache Hits:**
   - Response includes `cache_hit: true`
   - Sub-millisecond response time
   - No database query

4. **Cache Misses:**
   - Response includes `cache_hit: false`
   - Database query executed
   - Result cached for next request

### Cache Configuration

Located in [config.py](short_term_mcp/config.py#L18):

```python
CACHE_TTL = 300  # 5 minutes in seconds
```

---

## 💡 Usage Patterns

### Pattern 1: Initial Context Load

**Goal:** Get basic context when Code Teacher starts.

```python
# Quick context check
goals = await get_todays_learning_goals()

if goals['status'] == 'success':
    print(f"Today's focus: {goals['learning_goal']}")
    print(f"Building: {goals['building_goal']}")
    print(f"Concepts: {goals['concept_count']}")
```

### Pattern 2: Detailed Concept Review

**Goal:** Provide comprehensive assistance based on all concepts.

```python
# Get all concepts
concepts = await get_todays_concepts()

if concepts['status'] == 'success':
    for concept in concepts['concepts']:
        # Analyze each concept for assistance
        pass
```

### Pattern 3: Specific Concept Lookup

**Goal:** Find and reference specific concepts.

```python
# Search for specific concept
result = await search_todays_concepts("useState")

if result['status'] == 'success' and result['match_count'] > 0:
    concept = result['matches'][0]
    print(f"Found: {concept['concept_name']}")
    print(f"Status: {concept['current_status']}")
```

### Pattern 4: Progressive Context Building

**Goal:** Load context efficiently based on need.

```python
# 1. Start with goals (lightweight)
goals = await get_todays_learning_goals()

# 2. Search if user asks about specific concept
if user_mentions("useState"):
    result = await search_todays_concepts("useState")

# 3. Load full list only if needed
if need_comprehensive_view:
    all_concepts = await get_todays_concepts()
```

---

## 🔍 Error Handling

### No Session Found

**Response:**

```json
{
  "status": "not_found",
  "message": "No session found for today (2025-10-10)",
  "date": "2025-10-10",
  "cache_hit": false
}
```

**Handling:**

```python
result = await get_todays_concepts()
if result['status'] == 'not_found':
    print("No learning session today")
    # Suggest creating a session
```

### Empty Search Term

**Response:**

```json
{
  "status": "error",
  "error_code": "EMPTY_SEARCH_TERM",
  "message": "Search term cannot be empty"
}
```

**Handling:**

```python
if not search_term.strip():
    print("Please provide a search term")
else:
    result = await search_todays_concepts(search_term)
```

### No Search Matches

**Response:**

```json
{
  "status": "success",
  "match_count": 0,
  "matches": []
}
```

**Handling:**

```python
result = await search_todays_concepts("Angular")
if result['match_count'] == 0:
    print(f"No concepts found matching '{result['search_term']}'")
```

---

## ⚡ Performance Benchmarks

### Actual Performance (Phase 5 Tests)

All tests passed with the following performance:

| Operation                  | Target | Actual | Result |
| -------------------------- | ------ | ------ | ------ |
| Cache hit                  | <1ms   | <1ms   | ✅ Met |
| Cache miss (full concepts) | <50ms  | <50ms  | ✅ Met |
| Search with 25 concepts    | <100ms | <100ms | ✅ Met |
| Learning goals query       | <20ms  | <20ms  | ✅ Met |

### Performance Tips

1. **Use Learning Goals First:**
   - 2-3x faster than full concepts
   - Sufficient for basic context

2. **Leverage Caching:**
   - Repeated queries are <1ms
   - Cache lasts 5 minutes
   - Independent per query type

3. **Search vs Full Load:**
   - Search when you need specific concepts
   - Full load when you need everything
   - Both benefit from caching

---

## 🔧 Implementation Details

### File Locations

- **Tool Implementations:** [tools_impl.py#L508-697](short_term_mcp/tools_impl.py#L508)
- **MCP Server Registration:** [server.py#L234-307](short_term_mcp/server.py#L234)
- **Database Methods:** [database.py#L305-341](short_term_mcp/database.py#L305)
- **Caching System:** [utils.py](short_term_mcp/utils.py)
- **Tests:** [test_code_teacher.py](short_term_mcp/tests/test_code_teacher.py)

### Architecture

```
Code Teacher Query
    ↓
MCP Tool (server.py)
    ↓
Implementation (tools_impl.py)
    ↓
Cache Check (utils.py) ─→ Cache Hit → Return
    ↓ Cache Miss
Database Query (database.py)
    ↓
Cache Result
    ↓
Return
```

### Caching Strategy

- **Write-Through:** Results cached immediately after query
- **TTL-Based:** Entries expire after 5 minutes
- **Lazy Cleanup:** Expired entries removed on access
- **Thread-Safe:** Locking prevents race conditions

---

## 🧪 Testing

### Test Coverage

- **20 tests** in [test_code_teacher.py](short_term_mcp/tests/test_code_teacher.py)
- **5 test classes:**
  - TestCodeTeacherBasics (5 tests)
  - TestCodeTeacherSearch (6 tests)
  - TestCodeTeacherCaching (4 tests)
  - TestCodeTeacherPerformance (3 tests)
  - TestCodeTeacherIntegration (2 tests)

### Running Tests

```bash
# All Code Teacher tests
.venv/bin/pytest short_term_mcp/tests/test_code_teacher.py -v

# Specific test class
.venv/bin/pytest short_term_mcp/tests/test_code_teacher.py::TestCodeTeacherCaching -v

# Performance tests only
.venv/bin/pytest short_term_mcp/tests/test_code_teacher.py::TestCodeTeacherPerformance -v -s
```

### Test Results

```
20 passed in 1.20s
100% pass rate
All performance targets met
```

---

## 📝 Examples

### Example 1: Code Teacher Context Awareness

```python
# On Code Teacher startup
async def initialize_context():
    """Load today's learning context"""
    goals = await get_todays_learning_goals()

    if goals['status'] == 'success':
        context = {
            'learning': goals['learning_goal'],
            'building': goals['building_goal'],
            'concepts': goals['concept_count'],
            'in_progress': goals['concepts_by_status']['identified']
        }
        return context
    return None
```

### Example 2: Contextual Code Assistance

```python
async def provide_assistance(user_code: str):
    """Provide assistance based on today's concepts"""
    # Check if code relates to any concepts
    concepts = await get_todays_concepts()

    if concepts['status'] == 'success':
        for concept in concepts['concepts']:
            if concept['concept_name'].lower() in user_code.lower():
                # Provide targeted help for this concept
                return f"I see you're working with {concept['concept_name']}"

    return "How can I help?"
```

### Example 3: Smart Search

```python
async def answer_question(question: str):
    """Answer user question using today's concepts"""
    # Extract key terms from question
    key_terms = extract_keywords(question)

    # Search for relevant concepts
    for term in key_terms:
        result = await search_todays_concepts(term)
        if result['match_count'] > 0:
            return f"Based on today's learning about {term}..."

    return "I don't have information about that in today's session"
```

---

## 🎯 Integration with Code Teacher

### Recommended Workflow

1. **On Startup:**
   - Call `get_todays_learning_goals()`
   - Cache context for session

2. **During Interaction:**
   - Use cached context for general questions
   - Call `search_todays_concepts()` for specific topics
   - Call `get_todays_concepts()` for comprehensive review

3. **Performance Optimization:**
   - Let caching work automatically
   - Don't clear cache unnecessarily
   - Use learning goals for frequent context checks

### Best Practices

✅ **DO:**

- Use `get_todays_learning_goals()` for quick context
- Search before loading all concepts
- Trust the cache (it's thread-safe)
- Check `status` field in responses

❌ **DON'T:**

- Manually implement caching (it's built-in)
- Call `get_todays_concepts()` repeatedly (use cache)
- Ignore `status: "not_found"` responses
- Search with empty terms

---

## 📚 Related Documentation

- [API Documentation](API-Documentation.md) - All MCP tools (Phases 1-4)
- [Integration Testing](Integration-Testing.md) - Pipeline integration
- [System Plan](System-Plan.md) - Overall implementation plan

---

**Last Updated:** 2025-10-10
**Phase:** 5 of 7
**Status:** ✅ Complete
