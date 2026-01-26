# Algorithms & Processing Documentation

# Core Algorithms and Processing Logic

**Version:** 1.0
**Status:** Production Ready
**Last Updated:** 2025-10-27

---

## Table of Contents

1. [Overview](#overview)
2. [Embedding Generation](#embedding-generation)
3. [Semantic Search](#semantic-search)
4. [Graph Algorithms](#graph-algorithms)
5. [Caching Strategies](#caching-strategies)
6. [Consistency Checking](#consistency-checking)

---

## Overview

The MCP Knowledge Server employs several key algorithms for knowledge management:

| Algorithm                           | Purpose                           | Complexity | Implementation                  |
| ----------------------------------- | --------------------------------- | ---------- | ------------------------------- |
| **Sentence-Transformers Embedding** | Convert text to 384-dim vectors   | O(n)       | `services/embedding_service.py` |
| **HNSW Vector Search**              | Fast approximate nearest neighbor | O(log n)   | ChromaDB (built-in)             |
| **Graph Traversal (BFS/DFS)**       | Navigate concept relationships    | O(V + E)   | Neo4j Cypher queries            |
| **Shortest Path**                   | Find learning paths               | O(V + E)   | Neo4j shortestPath()            |
| **SHA-256 Hashing**                 | Embedding cache keys              | O(1)       | `services/embedding_cache.py`   |

---

## Embedding Generation

### Algorithm: Sentence-Transformers

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
**Architecture:** Transformer-based (BERT variant)
**Output:** 384-dimensional dense vector

#### Process Flow

```
Input Text
    ↓
Tokenization (WordPiece)
    ↓
BERT Encoding (6 layers, 384 hidden)
    ↓
Mean Pooling (average of token embeddings)
    ↓
L2 Normalization
    ↓
384-dim Vector
```

#### Implementation

```python
class EmbeddingService:
    def __init__(self, config: EmbeddingConfig):
        self.model = SentenceTransformer(config.model_name)
        self.dimensions = 384

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for single text input.

        Algorithm:
        1. Check cache (SHA-256 hash of text)
        2. If not cached:
           a. Tokenize text
           b. BERT forward pass
           c. Mean pooling
           d. L2 normalization
           e. Cache result
        3. Return 384-dim vector

        Complexity: O(n) where n = text length
        """
        # 1. Compute text hash for cache lookup
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

        # 2. Check cache
        if self.cache:
            cached = self.cache.get(text_hash, self.model_name)
            if cached is not None:
                return cached

        # 3. Generate embedding
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization
        ).tolist()

        # 4. Store in cache
        if self.cache:
            self.cache.set(text_hash, self.model_name, embedding)

        return embedding
```

**Source:** `services/embedding_service.py:145-195`

---

### Batch Processing

**Purpose:** Generate multiple embeddings efficiently

```python
def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
    """
    Batch embedding generation for efficiency.

    Algorithm:
    1. Split texts into cached vs uncached
    2. For uncached texts:
       a. Batch encode (GPU acceleration if available)
       b. Store each in cache
    3. Combine cached + newly generated embeddings

    Complexity: O(n × m) where n = number of texts, m = avg text length
    Optimization: GPU batching reduces wall-clock time significantly
    """
    uncached_texts = []
    uncached_indices = []

    # Identify uncached texts
    for i, text in enumerate(texts):
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cached = self.cache.get(text_hash, self.model_name) if self.cache else None
        if cached is None:
            uncached_texts.append(text)
            uncached_indices.append(i)

    # Batch generate uncached embeddings
    if uncached_texts:
        uncached_embeddings = self.model.encode(
            uncached_texts,
            batch_size=self.batch_size,  # Default: 32
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        # Cache results
        for text, embedding in zip(uncached_texts, uncached_embeddings):
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            self.cache.set(text_hash, self.model_name, embedding.tolist())

    # Return combined results
    ...
```

**Performance:**

- **Single:** ~50ms per embedding (CPU)
- **Batch (32):** ~30ms per embedding (CPU), ~5ms (GPU)

---

## Semantic Search

### Algorithm: HNSW (Hierarchical Navigable Small World)

**Purpose:** Fast approximate nearest neighbor search in high-dimensional space
**Implementation:** ChromaDB (built-in)
**Distance Metric:** Cosine similarity

#### HNSW Overview

```
Layer 2 (coarse):  o-------o-------o
                   |       |       |
Layer 1:           o---o---o---o---o
                   | | | | | | | | |
Layer 0 (fine):    o-o-o-o-o-o-o-o-o
                   ↑
                   Entry point
```

**Key Properties:**

- **Graph Structure:** Multi-layer proximity graph
- **Insertion:** O(log n) with high probability
- **Search:** O(log n) with high probability
- **Memory:** O(n × d) where d = 384

#### Search Process

```python
def search_concepts_semantic(
    query: str,
    limit: int = 10,
    min_certainty: Optional[float] = None,
    area: Optional[str] = None,
    topic: Optional[str] = None
) -> Dict[str, Any]:
    """
    Semantic similarity search using HNSW.

    Algorithm:
    1. Generate query embedding (384-dim)
    2. HNSW search in ChromaDB:
       a. Start at top layer entry point
       b. Greedily navigate to nearest neighbor
       c. Descend to lower layers
       d. Refine search at bottom layer
       e. Return top-k results
    3. Apply metadata filters (area, topic)
    4. Post-filter by min_certainty
    5. Sort by similarity descending

    Complexity: O(log n) average case
    Worst case: O(n) if graph degenerates
    """
    # 1. Generate query embedding
    query_embedding = embedding_service.generate_embedding(query)

    # 2. Build metadata filter
    where_filter = {}
    if area:
        where_filter["area"] = area
    if topic:
        where_filter["topic"] = topic

    # 3. HNSW search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        include=["metadatas", "distances"],
        where=where_filter  # Pre-filter by metadata
    )

    # 4. Process results
    concepts = []
    for i, concept_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        similarity = 1.0 - distance  # Cosine distance → similarity

        # Post-filter by certainty
        certainty = results["metadatas"][0][i].get("certainty_score", 0)
        if min_certainty and certainty < min_certainty:
            continue

        concepts.append({
            "concept_id": concept_id,
            "similarity": round(similarity, 4),
            ...
        })

    # 5. Sort by similarity
    concepts.sort(key=lambda x: x["similarity"], reverse=True)

    return {"success": True, "results": concepts, "total": len(concepts)}
```

**Source:** `tools/search_tools.py:30-177`

---

### Distance Metrics

**Cosine Similarity:**

```
similarity = (A · B) / (||A|| × ||B||)

Where:
  A = query embedding (384-dim)
  B = concept embedding (384-dim)
  · = dot product
  ||x|| = L2 norm

Range: [-1, 1] (normalized embeddings: [0, 1])
  1.0 = identical direction
  0.0 = orthogonal
```

**ChromaDB Distance:**

```
distance = 1 - similarity

Range: [0, 2]
  0.0 = identical
  1.0 = orthogonal
  2.0 = opposite direction
```

---

## Graph Algorithms

### 1. Shortest Path

**Purpose:** Find learning path between two concepts
**Algorithm:** Bidirectional BFS (Neo4j built-in)

```cypher
MATCH path = shortestPath(
  (start:Concept {concept_id: $start_id})-[*..5]-(end:Concept {concept_id: $end_id})
)
WHERE ALL(r IN relationships(path) WHERE r.deleted IS NULL OR r.deleted = false)
  AND ALL(n IN nodes(path) WHERE n.deleted IS NULL OR n.deleted = false)
RETURN nodes(path), relationships(path)
```

**Complexity:** O(b^(d/2)) where:

- `b` = branching factor (avg relationships per node)
- `d` = depth (max 5)

**Performance:**

- **Small graphs (<1000 nodes):** <50ms
- **Large graphs (>10K nodes):** <500ms

**Source:** `tools/relationship_tools.py:675-850`

---

### 2. Prerequisite Chain (DFS)

**Purpose:** Find all prerequisites for a concept (recursive traversal)

```cypher
MATCH path = (c:Concept {concept_id: $concept_id})<-[:PREREQUISITE*1..$depth]-(prereq:Concept)
WHERE (c.deleted IS NULL OR c.deleted = false)
  AND (prereq.deleted IS NULL OR prereq.deleted = false)
  AND ALL(r IN relationships(path) WHERE r.deleted IS NULL OR r.deleted = false)
RETURN prereq.concept_id, prereq.name, length(path) AS depth
ORDER BY depth
```

**Algorithm:**

1. Start at target concept
2. Follow PREREQUISITE relationships backward
3. Recursively traverse up to max depth (default 3)
4. Return all discovered prerequisites with depth

**Complexity:** O(b^d) where:

- `b` = avg prerequisites per concept
- `d` = max depth (1-5)

**Source:** `tools/relationship_tools.py:566-672`

---

### 3. Related Concepts (BFS)

**Purpose:** Find concepts related to a given concept

```cypher
-- Outgoing relationships
MATCH (c:Concept {concept_id: $concept_id})-[r]->(related:Concept)
WHERE (c.deleted IS NULL OR c.deleted = false)
  AND (related.deleted IS NULL OR related.deleted = false)
  AND ($relationship_type IS NULL OR type(r) = $relationship_type)
RETURN related.concept_id, related.name, type(r), r.strength
LIMIT $limit

-- Incoming relationships
MATCH (c:Concept {concept_id: $concept_id})<-[r]-(related:Concept)
...

-- Both directions (UNION)
...
```

**Complexity:** O(1) for single-hop
**Performance:** <30ms for 20 results

**Source:** `tools/relationship_tools.py:398-563`

---

## Caching Strategies

### 1. Embedding Cache

**Purpose:** Avoid re-computing embeddings for identical text
**Storage:** SQLite (`embedding_cache` table)
**Key:** SHA-256 hash of (text + model_name)

#### Algorithm

```python
def get(self, text_hash: str, model_name: str) -> Optional[List[float]]:
    """
    Retrieve cached embedding.

    Lookup:
    1. SELECT embedding FROM embedding_cache
       WHERE text_hash = ? AND model_name = ?
    2. If found: Deserialize JSON → List[float]
    3. If not found: Return None

    Complexity: O(1) with index on text_hash
    """
    cursor.execute(
        "SELECT embedding FROM embedding_cache WHERE text_hash = ? AND model_name = ?",
        (text_hash, model_name)
    )
    row = cursor.fetchone()
    if row:
        return json.loads(row[0])
    return None

def set(self, text_hash: str, model_name: str, embedding: List[float]):
    """
    Store embedding in cache.

    Storage:
    1. Serialize embedding → JSON
    2. INSERT OR REPLACE INTO embedding_cache (...)
    3. Commit transaction

    Complexity: O(1) with index
    """
    cursor.execute(
        """
        INSERT OR REPLACE INTO embedding_cache (text_hash, model_name, embedding, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (text_hash, model_name, json.dumps(embedding))
    )
    connection.commit()
```

**Hit Rate:** ~80% in typical usage (concepts queried multiple times)
**Performance Gain:** ~50ms saved per cache hit

**Source:** `services/embedding_cache.py`

---

### 2. Hierarchy Cache

**Purpose:** Cache expensive knowledge hierarchy queries
**Storage:** In-memory Python dict
**TTL:** 5 minutes

```python
_hierarchy_cache = None
_hierarchy_cache_time = None
_CACHE_TTL_SECONDS = 300

def list_hierarchy() -> Dict[str, Any]:
    """
    Get cached hierarchy or rebuild.

    Algorithm:
    1. Check cache validity:
       if (now - cache_time) < TTL:
           return cached_hierarchy
    2. If expired or not cached:
       a. Query Neo4j for all concepts grouped by area/topic/subtopic
       b. Build nested structure
       c. Store in cache with current timestamp
    3. Return hierarchy

    Cache Invalidation: Time-based (5 minutes)
    Alternative: Event-based (invalidate on ConceptCreated/Deleted)

    Complexity: O(1) cache hit, O(n) cache miss
    """
    now = datetime.now()
    if (_hierarchy_cache is not None and
        _hierarchy_cache_time is not None and
        (now - _hierarchy_cache_time).total_seconds() < _CACHE_TTL_SECONDS):
        return _hierarchy_cache

    # Rebuild hierarchy from Neo4j
    ...

    _hierarchy_cache = result
    _hierarchy_cache_time = now

    return result
```

**Performance:**

- **Cache Hit:** <1ms
- **Cache Miss:** ~100-500ms (depends on concept count)

**Source:** `tools/analytics_tools.py:35-197`

---

## Consistency Checking

### Algorithm: Dual Storage Validation

**Purpose:** Detect discrepancies between Neo4j and ChromaDB

```python
class ConsistencyChecker:
    def check_consistency(self) -> Dict[str, Any]:
        """
        Verify Neo4j and ChromaDB are synchronized.

        Algorithm:
        1. Get all concept IDs from Neo4j
        2. Get all concept IDs from ChromaDB
        3. Compute set differences:
           a. missing_in_chromadb = neo4j_ids - chromadb_ids
           b. missing_in_neo4j = chromadb_ids - neo4j_ids
        4. For common concepts, validate metadata:
           a. Compare name, area, topic, certainty_score
           b. Report mismatches
        5. Store snapshot in consistency_snapshots table
        6. Return report

        Complexity: O(n) where n = total concepts
        """
        # 1. Get Neo4j concepts
        neo4j_query = """
        MATCH (c:Concept)
        WHERE (c.deleted IS NULL OR c.deleted = false)
        RETURN c.concept_id, c.name, c.area, c.topic, c.certainty_score
        """
        neo4j_concepts = {
            record["concept_id"]: record
            for record in neo4j_service.execute_read(neo4j_query)
        }

        # 2. Get ChromaDB concepts
        chromadb_results = collection.get(include=["metadatas"])
        chromadb_concepts = {
            id: metadata
            for id, metadata in zip(chromadb_results["ids"], chromadb_results["metadatas"])
        }

        # 3. Set differences
        neo4j_ids = set(neo4j_concepts.keys())
        chromadb_ids = set(chromadb_concepts.keys())

        missing_in_chromadb = neo4j_ids - chromadb_ids
        missing_in_neo4j = chromadb_ids - neo4j_ids

        # 4. Metadata validation
        mismatches = []
        for concept_id in neo4j_ids & chromadb_ids:
            neo4j_data = neo4j_concepts[concept_id]
            chromadb_data = chromadb_concepts[concept_id]

            if neo4j_data["name"] != chromadb_data.get("name"):
                mismatches.append({
                    "concept_id": concept_id,
                    "field": "name",
                    "neo4j_value": neo4j_data["name"],
                    "chromadb_value": chromadb_data.get("name")
                })

            # ... check other fields ...

        # 5. Generate report
        report = {
            "status": "consistent" if not (missing_in_chromadb or missing_in_neo4j or mismatches) else "inconsistent",
            "neo4j_count": len(neo4j_ids),
            "chromadb_count": len(chromadb_ids),
            "discrepancies": {
                "missing_in_chromadb": list(missing_in_chromadb),
                "missing_in_neo4j": list(missing_in_neo4j),
                "metadata_mismatches": mismatches
            }
        }

        # 6. Store snapshot
        self._store_snapshot(report)

        return report
```

**Source:** `services/consistency_checker.py`

---

## Performance Optimization Techniques

### 1. Batch Processing

**Embedding Generation:**

```python
# Bad: O(n) individual calls
for text in texts:
    embedding = generate_embedding(text)

# Good: O(1) batch call with GPU acceleration
embeddings = batch_generate_embeddings(texts)
```

**Performance Gain:** 3-10x faster for batches >10

---

### 2. Index Optimization

**Neo4j:**

- Indexes on `concept_id`, `name`, `certainty_score`, `created_at`
- Composite index on `(area, topic)` for hierarchy queries

**SQLite:**

- Index on `(text_hash, model_name)` for embedding cache
- Index on `(aggregate_id, version)` for event lookups

---

### 3. Connection Pooling

**Neo4j:**

```python
driver = GraphDatabase.driver(
    uri,
    auth=(user, password),
    max_connection_pool_size=10,
    connection_timeout=30
)
```

**Benefit:** Reuse connections, reduce handshake overhead

---

**Document Version:** 1.0
**Generated:** 2025-10-27
**Evidence Base:** `services/`, `tools/`, algorithm implementations
