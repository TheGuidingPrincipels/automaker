# Confidence Scoring System

## Overview

The confidence scoring system provides automated, data-driven confidence metrics for concepts in the knowledge base. It replaces manual certainty scoring with a hybrid model combining understanding and retention scores.

**Implementation Status**: Session 1 (Foundation Layer) - ✅ Complete

## Architecture

### Hybrid Confidence Model

```
Confidence Score = 0.6 × Understanding Score + 0.4 × Retention Score
```

#### Understanding Score Components (Sessions 3-4)

- **40%** - Relationship density (connections to other concepts)
- **30%** - Explanation quality (completeness and depth)
- **30%** - Metadata richness (tags, examples, context)

#### Retention Score Components (Session 4)

- FSRS-based exponential decay model
- Factors: days since last review, review count, concept stability

## Foundation Layer (Session 1) ✅

### Data Models (`services/confidence/models.py`)

All data models use Pydantic for runtime validation and type safety:

#### Core Models

**ConceptData**

```python
class ConceptData(BaseModel):
    id: str                           # Concept identifier (max 255 chars)
    name: str                         # Concept name
    explanation: str                  # Required, validated non-empty
    created_at: datetime              # Creation timestamp
    last_reviewed_at: Optional[datetime]  # Last review (None if never reviewed)
    tags: list[str]                   # Metadata tags
    examples: list[str]               # Usage examples
```

**RelationshipData**

```python
class RelationshipData(BaseModel):
    total_relationships: int          # Count of all relationships
    relationship_types: dict[str, int]  # Type → count mapping
    connected_concept_ids: list[str]  # All connected concept IDs

    @property
    def unique_connections(self) -> int:
        """Deduplicated count of connected concepts"""
```

**ReviewData**

```python
class ReviewData(BaseModel):
    last_reviewed_at: datetime        # Last review timestamp
    days_since_review: int           # Calculated age (≥0)
    review_count: int                # Total review count (≥0)
```

**CompletenessReport**

```python
class CompletenessReport(BaseModel):
    has_explanation: bool            # True if explanation exists
    has_tags: bool                   # True if tags present
    has_examples: bool               # True if examples present
    has_relationships: bool          # True if connected to concepts
    metadata_score: float            # Weighted score [0.0, 1.0]
```

#### Error Handling Pattern

The system uses `Result<T, E>` pattern for predictable error handling:

```python
@dataclass
class Error:
    message: str                     # Human-readable error message
    code: ErrorCode                  # Enum: VALIDATION_ERROR, NOT_FOUND, etc.
    details: Optional[dict]          # Additional context

@dataclass
class Success:
    value: Any                       # Wrapped successful result

Result = Union[Success, Error]
```

**Error Codes**:

- `VALIDATION_ERROR` - Input validation failed
- `NOT_FOUND` - Concept does not exist
- `DATABASE_ERROR` - Neo4j query failed
- `INVALID_FORMAT` - Data format incorrect (e.g., timestamps)

### Validation Services (`services/confidence/validation.py`)

Input validation functions with explicit error returns:

#### validate_concept_id

```python
def validate_concept_id(concept_id: str) -> Result[str, Error]
```

- Checks: Non-empty, max 255 characters
- Returns: `Success(concept_id)` or `Error(VALIDATION_ERROR)`

#### validate_score

```python
def validate_score(score: float, label: str = "Score") -> Result[float, Error]
```

- Checks: Range [0.0, 1.0], numeric type
- Returns: `Success(score)` or `Error(VALIDATION_ERROR)`
- Supports custom label for error messages

#### validate_timestamp

```python
def validate_timestamp(timestamp: str) -> Result[datetime, Error]
```

- Checks: ISO 8601 format (with Z or +00:00 timezone)
- Returns: `Success(datetime)` or `Error(INVALID_FORMAT)`

#### check_data_completeness

```python
def check_data_completeness(concept_data: ConceptData) -> CompletenessReport
```

- Analyzes: explanation (40%), tags (30%), examples (30%)
- Returns: CompletenessReport with weighted metadata_score

### Data Access Layer (`services/confidence/data_access.py`)

Async Neo4j queries for confidence calculation inputs:

#### DataAccessLayer.get_concept_for_confidence

```python
async def get_concept_for_confidence(concept_id: str) -> Result[ConceptData, Error]
```

- Fetches: All concept fields needed for confidence calculation
- Returns: `Success(ConceptData)` or `Error(NOT_FOUND | DATABASE_ERROR)`

**Cypher Query**:

```cypher
MATCH (c:Concept {id: $concept_id})
RETURN c.id, c.name, c.explanation, c.created_at,
       c.last_reviewed_at, c.tags, c.examples
```

#### DataAccessLayer.get_concept_relationships

```python
async def get_concept_relationships(concept_id: str) -> Result[RelationshipData, Error]
```

- Fetches: Bidirectional relationships (incoming + outgoing)
- Aggregates: Type counts, connected concept IDs
- Returns: `Success(RelationshipData)` or `Error(DATABASE_ERROR)`

**Cypher Query** (UNION for bidirectional):

```cypher
MATCH (c:Concept {id: $concept_id})
OPTIONAL MATCH (c)-[r]->(target:Concept)
RETURN target.id, type(r)
UNION
MATCH (c:Concept {id: $concept_id})
OPTIONAL MATCH (source:Concept)-[r]->(c)
RETURN source.id, type(r)
```

#### DataAccessLayer.get_review_history

```python
async def get_review_history(concept_id: str) -> Result[ReviewData, Error]
```

- Fetches: last_reviewed_at or created_at (fallback)
- Calculates: days_since_review (always ≥0)
- Returns: `Success(ReviewData)` or `Error(NOT_FOUND | DATABASE_ERROR)`

**Fallback Logic**:

- If `last_reviewed_at` is null → use `created_at` as baseline
- Ensures never-reviewed concepts have valid age calculation

## Test Coverage

**Unit Tests**: 38 tests, 99% code coverage

### Test Files

- `tests/unit/confidence/test_models.py` (10 tests)
  - Pydantic validation (empty fields, type errors)
  - Boundary values (negative numbers, score ranges)
  - Computed properties (unique_connections deduplication)

- `tests/unit/confidence/test_validation.py` (17 tests)
  - Valid inputs (concept IDs, scores, timestamps)
  - Boundary conditions (0.0, 1.0, 255 chars)
  - Invalid formats (malformed timestamps, out-of-range scores)
  - Completeness scoring (all combinations of metadata presence)

- `tests/unit/confidence/test_data_access.py` (11 tests)
  - Successful queries (concept fetch, relationships, review history)
  - Error handling (NOT_FOUND, DATABASE_ERROR)
  - Edge cases (no relationships, never-reviewed concepts)
  - DateTime parsing (with/without last_reviewed_at)

### Test Strategy

- **Mocking**: All tests use `AsyncMock` for Neo4j sessions
- **No Database**: Tests do not require running Neo4j instance
- **Async Support**: Uses `pytest-asyncio` for async method testing

## Integration Points

### Neo4j Connection

- Reuses existing `neo4j_service.py` connection pool
- All queries are async (compatible with Neo4j async driver)
- Connection errors wrapped in Result pattern

### Repository Pattern

- `DataAccessLayer` is standalone (no dependency on `repository.py`)
- Future integration: Session 6 will connect to existing repository
- Designed for composition (can wrap with cache layer in Session 2)

## Design Decisions

### Why Result<T, E> Instead of Exceptions?

1. **Explicit error handling** - Caller must handle Success/Error cases
2. **Type safety** - Errors are data, not control flow
3. **Predictable** - No hidden exception paths
4. **Composable** - Easy to chain operations with error propagation

### Why Pydantic Models?

1. **Runtime validation** - Catches invalid data at boundaries
2. **Type hints** - IDE support and mypy checking
3. **Serialization** - JSON export for caching (Session 2)
4. **Documentation** - Self-documenting with Field descriptions

### Why Separate Validation Module?

1. **Reusability** - Used by multiple calculators (Sessions 3-4)
2. **Testing** - Isolated validation logic easier to test
3. **Single Responsibility** - Models define structure, validation enforces rules

## Dependencies for Next Sessions

### Session 2 (Cache Infrastructure)

**Uses from Session 1**:

- `ConceptData` model → Cache keys
- `DataAccessLayer` → Wrapped by CacheManager
- `validate_concept_id()` → Pre-cache validation

### Sessions 3-4 (Calculators)

**Uses from Session 1**:

- `RelationshipData` → Understanding score calculation
- `ReviewData` → Retention score calculation
- `CompletenessReport` → Metadata scoring

### Session 6 (Integration)

**Uses from Session 1**:

- All data access methods → Integrated into repository.py
- Result pattern → Standardized error handling

## Known Limitations

1. **No Caching** - Every query hits Neo4j (deferred to Session 2)
2. **No Calculation Logic** - Foundation only fetches data (Sessions 3-4)
3. **Single-Concept Queries** - No bulk operations yet
4. **Review Count Placeholder** - Full review history tracking deferred

## Performance Characteristics

- **Query Complexity**: O(1) for concept fetch, O(N) for relationships
- **Memory**: Minimal - returns data models, no caching
- **Latency**: Depends on Neo4j response time (no optimization yet)

**Performance Optimization**: Session 2 will add Redis caching (target <10ms warm cache latency)

## Future Enhancements

1. **Bulk Operations** - `get_concepts_for_confidence([id1, id2, ...])`
2. **Review History Tracking** - Store all review timestamps, not just last
3. **Query Metrics** - Log execution times for performance monitoring
4. **Connection Pooling Health Checks** - Proactive connection validation

---

**Status**: ✅ Foundation Layer Complete (Session 1)
**Next**: Session 2 - Cache Infrastructure (Redis integration)
**Tests**: 38 passing, 99% coverage
**Commits**:

- `61312fd` - feat(session-1): implement foundation layer
- `d30cbde` - chore(progress): update session-1 completion status
