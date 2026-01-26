# ADR 003: Caching Strategy

## Status

Accepted

## Context

The MCP Knowledge Server has multiple caching mechanisms that evolved organically. We need to document and standardize these patterns for consistency and maintainability.

### Current Caching Layers

| Cache Type       | Storage   | TTL          | Purpose                                      |
| ---------------- | --------- | ------------ | -------------------------------------------- |
| Embedding Cache  | SQLite    | Permanent    | Avoid recomputing expensive embeddings       |
| Hierarchy Cache  | In-memory | 5 minutes    | Reduce graph traversal for hierarchy queries |
| Confidence Cache | Redis     | Configurable | Distributed caching for confidence scores    |

## Decision

### 1. Embedding Cache (Persistent)

**Location:** `services/embedding_cache.py`

**Strategy:** Permanent cache with content-addressable keys

```python
# Key format: hash(text + model_name)
# Value: embedding vector (384 dimensions)
```

**Rationale:**

- Embedding generation is expensive (model inference)
- Same text always produces same embedding (deterministic)
- Cache hits dramatically improve performance
- SQLite provides persistence across restarts

**When to use:**

- Always cache embeddings for text that may be queried multiple times
- Repository automatically uses embedding cache

### 2. Query Result Cache (In-Memory with TTL)

**Location:** `tools/analytics_tools.py`

**Strategy:** In-memory cache with time-based invalidation

```python
_CACHE_TTL_SECONDS = 300  # 5 minutes

# Cache structure
_cache = {
    'hierarchy': {
        'data': <cached_result>,
        'timestamp': <datetime>,
        'service_id': <id(service)>  # Invalidate on service change
    }
}
```

**Rationale:**

- Hierarchy queries involve expensive graph traversal
- Data changes infrequently relative to query frequency
- 5-minute TTL balances freshness vs performance
- Service ID tracking handles test isolation

**When to use:**

- Aggregation queries that scan large portions of the graph
- Results that don't need real-time accuracy
- Functions called frequently with same parameters

**When NOT to cache:**

- Single-concept lookups (fast enough, need freshness)
- Search results (personalized/parameterized)
- Functions with many parameter combinations

### 3. Confidence Score Cache (Redis)

**Location:** `services/confidence/` (when Redis configured)

**Strategy:** Distributed cache for multi-instance deployments

**Rationale:**

- Confidence calculations involve multiple queries
- Scores don't change frequently
- Redis enables sharing across instances

**When to use:**

- Distributed/multi-instance deployments
- When Redis is available

## Implementation Pattern

### Standard Cache Implementation

```python
from datetime import datetime
from typing import Any, Optional
import threading

class CacheEntry:
    """Thread-safe cache entry with TTL."""
    def __init__(self, data: Any, ttl_seconds: int):
        self.data = data
        self.timestamp = datetime.now()
        self.ttl_seconds = ttl_seconds

    def is_valid(self) -> bool:
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed < self.ttl_seconds

class QueryCache:
    """Thread-safe in-memory cache for query results."""

    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.is_valid():
                return entry.data
            elif entry:
                del self._cache[key]  # Expired
            return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        with self._lock:
            self._cache[key] = CacheEntry(data, ttl or self._default_ttl)

    def invalidate(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()
```

### Cache Key Guidelines

- Include all parameters that affect the result
- Use consistent ordering for dict keys
- Consider service instance ID for test isolation

```python
def _cache_key(self, *args, **kwargs) -> str:
    """Generate deterministic cache key."""
    parts = [str(a) for a in args]
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)
```

## Consequences

### Positive

- Consistent caching approach across codebase
- Clear guidelines for when to cache
- Thread-safe implementation pattern
- Test isolation handled

### Negative

- Memory usage for in-memory caches
- Stale data within TTL window
- Cache invalidation complexity

### Mitigations

- TTL limits staleness window
- Critical paths can bypass cache
- Service ID tracking handles tests

## References

- `services/embedding_cache.py` - Embedding cache implementation
- `tools/analytics_tools.py` - Hierarchy cache (reference implementation)
