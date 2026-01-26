# Certainty Score System Analysis & Improvement Specification

**Document Type:** Technical Analysis & Feature Specification  
**Target Audience:** Development Team (Claude Code)  
**Priority:** MEDIUM  
**Estimated Implementation:** 2-3 sprints  
**Date:** 2025-11-01

---

## 📋 Executive Summary

**Current State:** The certainty score is a manually assigned 0-100 value with no automated calculation or guidance.

**Problem:** Manual scoring is subjective, inconsistent, and burdensome for users.

**Proposed Solution:** Implement automated certainty score calculation using multi-factor heuristics, with optional LLM-enhanced analysis.

**Expected Impact:**

- Reduce user cognitive load
- Increase scoring consistency across users
- Enable automated quality monitoring
- Support intelligent knowledge base curation

---

## 🔍 Current Implementation Analysis

### How Certainty Score Works Today

#### Data Flow

```
User → Manual Input (0-100) → MCP Server → Neo4j + ChromaDB
```

#### Current Functionality

✅ **Input Validation:**

- Enforces 0-100 numeric range
- Boundary tests passed (0, 100, -1, 150)
- Rejects invalid values

✅ **Storage:**

- Persisted in Neo4j (Concept node property)
- Indexed in ChromaDB metadata
- Maintained across updates

✅ **Retrieval & Filtering:**

- `get_concepts_by_certainty(min, max)` - Works perfectly
- Supports exact value queries (certainty=85)
- Handles inverted ranges (auto-corrects)
- Sorting by certainty works correctly

✅ **Update Capability:**

- Users can modify certainty via `update_concept`
- Updates propagate to both databases
- No history tracking of certainty changes

### Current Limitations

#### 1. Subjectivity Problem

**Scenario:** Three users creating the same concept

```python
User A: "Python For Loops" → certainty: 95 (very confident)
User B: "Python For Loops" → certainty: 70 (moderate confidence)
User C: "Python For Loops" → certainty: 85 (high confidence)
```

**Result:** Inconsistent scoring with no objective standard.

#### 2. No Guidance

**Issue:** Users must decide certainty without:

- Clear definitions of score ranges
- Examples of appropriate scores
- Feedback on whether their score is reasonable
- Comparison to similar concepts

#### 3. Manual Burden

**Problems:**

- Every concept requires conscious certainty decision
- Users must track their own certainty levels
- No automated recalculation as concepts evolve
- Forgotten updates lead to stale scores

#### 4. Lack of Standardization

**Inconsistencies:**

- What does 70 vs 75 mean?
- How does explanation quality affect certainty?
- Should well-connected concepts score higher?
- No documented scoring rubric

### What Works Well

✅ **Technical Infrastructure:** The storage, filtering, and retrieval mechanisms are solid.

✅ **Range Design:** 0-100 provides good granularity without overwhelming precision.

✅ **Update Flexibility:** Users can adjust scores as understanding improves.

---

## 🎯 Proposed Solution: Automated Certainty Calculation

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                 Concept Creation                     │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│          Certainty Calculation Engine                │
│  ┌───────────────────────────────────────────────┐  │
│  │  Factor 1: Explanation Quality (40%)          │  │
│  │  - Length & detail score                      │  │
│  │  - Structure & clarity score                  │  │
│  │  - Keyword richness score                     │  │
│  └───────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │  Factor 2: Relationship Density (30%)         │  │
│  │  - Number of relationships                    │  │
│  │  - Relationship type diversity                │  │
│  │  - Connection strength                        │  │
│  └───────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │  Factor 3: Metadata Completeness (20%)        │  │
│  │  - Area, topic, subtopic filled               │  │
│  │  - Consistent categorization                  │  │
│  └───────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │  Factor 4: Concept Maturity (10%)             │  │
│  │  - Update frequency (stabilization)           │  │
│  │  - Time since last modification               │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  Weighted Score: (F1×0.4 + F2×0.3 + F3×0.2 + F4×0.1)│
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│         Optional: LLM Enhancement Layer              │
│  - Semantic coherence check                          │
│  - Factual accuracy estimation                       │
│  - Explanation quality assessment                    │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│    Final Certainty Score (0-100) → Database          │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Factor 1: Explanation Quality (40% weight)

### Rationale

The explanation is the primary indicator of understanding depth. Better explanations = higher certainty.

### Calculation Method

#### 1.1 Length & Detail Score (max: 40 points)

```python
def calculate_length_score(explanation: str) -> float:
    """
    Score based on explanation length.

    Scoring brackets:
    - 0-50 chars: 0-10 points (too brief)
    - 51-150 chars: 10-20 points (minimal)
    - 151-300 chars: 20-30 points (good)
    - 301-500 chars: 30-35 points (detailed)
    - 500+ chars: 35-40 points (comprehensive)
    """
    char_count = len(explanation)

    if char_count < 50:
        return (char_count / 50) * 10
    elif char_count < 150:
        return 10 + ((char_count - 50) / 100) * 10
    elif char_count < 300:
        return 20 + ((char_count - 150) / 150) * 10
    elif char_count < 500:
        return 30 + ((char_count - 300) / 200) * 5
    else:
        return min(40, 35 + ((char_count - 500) / 500) * 5)
```

#### 1.2 Structure & Clarity Score (max: 30 points)

```python
def calculate_structure_score(explanation: str) -> float:
    """
    Score based on explanation structure.

    Factors:
    - Sentence count (multiple sentences = better)
    - Punctuation usage (proper grammar)
    - Paragraph structure
    - Use of examples
    """
    score = 0

    # Sentence diversity (max 10 points)
    sentences = explanation.split('.')
    sentence_count = len([s for s in sentences if s.strip()])
    score += min(10, sentence_count * 2)

    # Punctuation indicators (max 10 points)
    has_comma = ',' in explanation
    has_colon = ':' in explanation
    has_semicolon = ';' in explanation
    has_parentheses = '(' in explanation and ')' in explanation

    score += (has_comma * 3) + (has_colon * 3) + (has_semicolon * 2) + (has_parentheses * 2)

    # Multiple paragraphs (max 5 points)
    paragraphs = [p for p in explanation.split('\n\n') if p.strip()]
    if len(paragraphs) > 1:
        score += min(5, len(paragraphs) * 2)

    # Example keywords (max 5 points)
    example_keywords = ['example', 'for instance', 'such as', 'like', 'e.g.', 'i.e.']
    has_examples = any(keyword in explanation.lower() for keyword in example_keywords)
    if has_examples:
        score += 5

    return min(30, score)
```

#### 1.3 Keyword Richness Score (max: 30 points)

```python
def calculate_keyword_richness(explanation: str, concept_name: str,
                                area: str, topic: str) -> float:
    """
    Score based on domain-relevant keyword usage.

    Factors:
    - Technical terms present
    - Concept name mentioned/explained
    - Domain vocabulary depth
    - Specificity of language
    """
    score = 0
    explanation_lower = explanation.lower()

    # Concept name referenced (max 5 points)
    concept_words = concept_name.lower().split()
    references = sum(1 for word in concept_words if word in explanation_lower)
    score += min(5, references * 2)

    # Domain-specific vocabulary (max 15 points)
    domain_terms = get_domain_terms(area, topic)  # Function to get relevant terms
    term_matches = sum(1 for term in domain_terms if term in explanation_lower)
    score += min(15, term_matches * 1.5)

    # Unique word count (vocabulary diversity, max 10 points)
    words = explanation_lower.split()
    unique_words = set(words)
    unique_ratio = len(unique_words) / max(1, len(words))
    score += unique_ratio * 10

    return min(30, score)
```

### Total Explanation Quality Score

```python
def calculate_explanation_quality(explanation: str, concept_name: str,
                                  area: str, topic: str) -> float:
    """
    Weighted combination of explanation quality factors.

    Returns: 0-40 (40% of total certainty score)
    """
    length_score = calculate_length_score(explanation)  # 0-40
    structure_score = calculate_structure_score(explanation)  # 0-30
    keyword_score = calculate_keyword_richness(explanation, concept_name,
                                                area, topic)  # 0-30

    # Normalize to 0-40 range
    total = (length_score * 0.4) + (structure_score * 0.3) + (keyword_score * 0.3)

    return min(40, total)
```

---

## 🔗 Factor 2: Relationship Density (30% weight)

### Rationale

Well-connected concepts are better understood. More relationships = higher confidence in concept placement.

### Calculation Method

#### 2.1 Relationship Count Score (max: 15 points)

```python
def calculate_relationship_count_score(concept_id: str,
                                        neo4j_session) -> float:
    """
    Score based on number of relationships.

    Scoring:
    - 0 relationships: 0 points
    - 1-2 relationships: 5 points
    - 3-5 relationships: 10 points
    - 6-10 relationships: 13 points
    - 11+ relationships: 15 points
    """
    query = """
    MATCH (c:Concept {concept_id: $concept_id})-[r]-()
    WHERE r.deleted IS NULL OR r.deleted = false
    RETURN count(DISTINCT r) as rel_count
    """
    result = neo4j_session.run(query, concept_id=concept_id)
    rel_count = result.single()['rel_count']

    if rel_count == 0:
        return 0
    elif rel_count <= 2:
        return 5
    elif rel_count <= 5:
        return 10
    elif rel_count <= 10:
        return 13
    else:
        return 15
```

#### 2.2 Relationship Type Diversity Score (max: 10 points)

```python
def calculate_relationship_diversity_score(concept_id: str,
                                           neo4j_session) -> float:
    """
    Score based on variety of relationship types.

    Scoring:
    - 1 type: 3 points
    - 2 types: 7 points
    - 3+ types: 10 points
    """
    query = """
    MATCH (c:Concept {concept_id: $concept_id})-[r]-()
    WHERE r.deleted IS NULL OR r.deleted = false
    RETURN DISTINCT type(r) as rel_type
    """
    result = neo4j_session.run(query, concept_id=concept_id)
    rel_types = [record['rel_type'] for record in result]
    type_count = len(rel_types)

    if type_count == 0:
        return 0
    elif type_count == 1:
        return 3
    elif type_count == 2:
        return 7
    else:
        return 10
```

#### 2.3 Connection Strength Score (max: 5 points)

```python
def calculate_connection_strength_score(concept_id: str,
                                        neo4j_session) -> float:
    """
    Score based on average relationship strength.

    Higher average strength = better integrated concept
    """
    query = """
    MATCH (c:Concept {concept_id: $concept_id})-[r]-()
    WHERE r.deleted IS NULL OR r.deleted = false
    RETURN avg(r.strength) as avg_strength, count(r) as count
    """
    result = neo4j_session.run(query, concept_id=concept_id)
    record = result.single()

    if record['count'] == 0:
        return 0

    avg_strength = record['avg_strength']
    return avg_strength * 5  # 0-1 range → 0-5 points
```

### Total Relationship Density Score

```python
def calculate_relationship_density(concept_id: str, neo4j_session) -> float:
    """
    Weighted combination of relationship factors.

    Returns: 0-30 (30% of total certainty score)
    """
    count_score = calculate_relationship_count_score(concept_id, neo4j_session)
    diversity_score = calculate_relationship_diversity_score(concept_id, neo4j_session)
    strength_score = calculate_connection_strength_score(concept_id, neo4j_session)

    total = count_score + diversity_score + strength_score

    return min(30, total)
```

---

## 📝 Factor 3: Metadata Completeness (20% weight)

### Rationale

Complete metadata indicates thorough concept organization and understanding.

### Calculation Method

```python
def calculate_metadata_completeness(area: str, topic: str, subtopic: str,
                                     all_concepts) -> float:
    """
    Score based on metadata fields and consistency.

    Factors:
    - Field completeness (area, topic, subtopic)
    - Categorization consistency
    - Appropriate hierarchy placement

    Returns: 0-20 (20% of total certainty score)
    """
    score = 0

    # Field completeness (max 12 points)
    if area:
        score += 4
    if topic:
        score += 4
    if subtopic:
        score += 4

    # Categorization consistency (max 8 points)
    # Check if this area/topic/subtopic combination is common
    if area and topic:
        # Query to see if this combination exists in other concepts
        similar_categorization_count = count_similar_categorization(
            area, topic, subtopic, all_concepts
        )

        if similar_categorization_count >= 3:
            # Well-established category
            score += 8
        elif similar_categorization_count >= 1:
            # Some precedent
            score += 4
        else:
            # New/unique categorization
            score += 2

    return min(20, score)

def count_similar_categorization(area: str, topic: str, subtopic: str,
                                  all_concepts) -> int:
    """
    Count concepts with same area/topic/subtopic combination.
    """
    count = 0
    for concept in all_concepts:
        if (concept.get('area') == area and
            concept.get('topic') == topic and
            concept.get('subtopic') == subtopic):
            count += 1
    return count
```

---

## ⏰ Factor 4: Concept Maturity (10% weight)

### Rationale

Concepts that have stabilized over time (fewer recent edits) are more certain.

### Calculation Method

```python
from datetime import datetime, timedelta

def calculate_concept_maturity(concept_id: str, neo4j_session) -> float:
    """
    Score based on concept stability over time.

    Factors:
    - Time since creation
    - Time since last modification
    - Update frequency (fewer recent updates = more mature)

    Returns: 0-10 (10% of total certainty score)
    """
    query = """
    MATCH (c:Concept {concept_id: $concept_id})
    RETURN c.created_at as created, c.last_modified as modified
    """
    result = neo4j_session.run(query, concept_id=concept_id)
    record = result.single()

    created = datetime.fromisoformat(record['created'])
    modified = datetime.fromisoformat(record['modified'])
    now = datetime.now()

    score = 0

    # Age score (max 5 points)
    age_days = (now - created).days
    if age_days >= 30:
        score += 5
    elif age_days >= 7:
        score += 3
    elif age_days >= 1:
        score += 1

    # Stability score (max 5 points)
    days_since_modification = (now - modified).days
    if days_since_modification >= 30:
        score += 5  # Very stable
    elif days_since_modification >= 7:
        score += 3  # Reasonably stable
    elif days_since_modification >= 1:
        score += 1  # Recently modified

    return min(10, score)
```

---

## 🧮 Complete Certainty Calculation Algorithm

```python
def calculate_certainty_score(concept_id: str, concept_data: dict,
                              neo4j_session, all_concepts: list) -> float:
    """
    Master function to calculate complete certainty score.

    Args:
        concept_id: UUID of the concept
        concept_data: Dictionary with name, explanation, area, topic, subtopic
        neo4j_session: Active Neo4j session
        all_concepts: List of all concepts (for consistency checking)

    Returns:
        Float between 0-100 representing certainty score
    """

    # Factor 1: Explanation Quality (40%)
    explanation_score = calculate_explanation_quality(
        explanation=concept_data['explanation'],
        concept_name=concept_data['name'],
        area=concept_data.get('area', ''),
        topic=concept_data.get('topic', '')
    )

    # Factor 2: Relationship Density (30%)
    relationship_score = calculate_relationship_density(
        concept_id=concept_id,
        neo4j_session=neo4j_session
    )

    # Factor 3: Metadata Completeness (20%)
    metadata_score = calculate_metadata_completeness(
        area=concept_data.get('area'),
        topic=concept_data.get('topic'),
        subtopic=concept_data.get('subtopic'),
        all_concepts=all_concepts
    )

    # Factor 4: Concept Maturity (10%)
    maturity_score = calculate_concept_maturity(
        concept_id=concept_id,
        neo4j_session=neo4j_session
    )

    # Calculate weighted total
    total_score = (
        explanation_score +      # Already weighted (0-40)
        relationship_score +     # Already weighted (0-30)
        metadata_score +         # Already weighted (0-20)
        maturity_score          # Already weighted (0-10)
    )

    # Round to whole number and ensure bounds
    final_score = max(0, min(100, round(total_score)))

    return final_score


# Example usage
def process_concept_creation(concept_data: dict, neo4j_session) -> dict:
    """
    Process concept creation with automatic certainty calculation.
    """
    # Create concept in database
    concept_id = create_concept_in_db(concept_data)

    # Wait briefly for graph to update
    time.sleep(0.1)

    # Calculate certainty score
    all_concepts = get_all_concepts(neo4j_session)
    certainty_score = calculate_certainty_score(
        concept_id=concept_id,
        concept_data=concept_data,
        neo4j_session=neo4j_session,
        all_concepts=all_concepts
    )

    # Update concept with calculated certainty
    update_concept_certainty(concept_id, certainty_score, neo4j_session)

    return {
        'concept_id': concept_id,
        'certainty_score': certainty_score,
        'message': f'Created with calculated certainty: {certainty_score}'
    }
```

---

## 🤖 Optional: LLM Enhancement Layer

### Purpose

Use LLM to enhance certainty calculation with semantic understanding.

### Implementation

```python
async def llm_enhanced_certainty(concept_data: dict,
                                 base_certainty: float,
                                 llm_client) -> float:
    """
    Use LLM to refine certainty score based on semantic analysis.

    This is OPTIONAL and can be disabled for performance.
    """

    prompt = f"""Analyze this concept and provide a certainty adjustment.

Concept Name: {concept_data['name']}
Explanation: {concept_data['explanation']}
Base Certainty Score: {base_certainty}/100

Evaluate:
1. Semantic coherence (does explanation match concept name?)
2. Factual accuracy (are there obvious errors?)
3. Explanation completeness (are key aspects covered?)
4. Clarity and precision of language

Respond with ONLY a number between -20 and +20 representing the adjustment.
- Positive adjustment: Explanation is better than metrics suggest
- Negative adjustment: Explanation has issues metrics missed
- Zero adjustment: Metrics accurately captured quality

Adjustment: """

    response = await llm_client.generate(prompt, max_tokens=10)

    try:
        adjustment = float(response.strip())
        adjustment = max(-20, min(20, adjustment))  # Clamp to range
    except ValueError:
        adjustment = 0  # Default to no adjustment if parse fails

    # Apply adjustment
    adjusted_score = base_certainty + adjustment
    final_score = max(0, min(100, adjusted_score))

    return final_score
```

### When to Use LLM Enhancement

**Use When:**

- User explicitly requests high-quality scoring
- Processing high-importance concepts
- Batch processing allows for async LLM calls
- Performance impact is acceptable

**Skip When:**

- Real-time creation needs to be fast (<200ms)
- Cost constraints (LLM API calls)
- Heuristic scores are sufficient

---

## 🔄 Automatic Recalculation Triggers

### When to Recalculate Certainty

```python
class CertaintyRecalculationTriggers:
    """
    Define when certainty should be automatically recalculated.
    """

    @staticmethod
    def should_recalculate(event_type: str, changes: dict) -> bool:
        """
        Determine if certainty should be recalculated based on event.
        """

        # Always recalculate on explanation changes
        if event_type == "ConceptUpdated" and "explanation" in changes:
            return True

        # Recalculate when relationships change
        if event_type in ["RelationshipCreated", "RelationshipDeleted"]:
            return True

        # Recalculate when metadata changes
        if event_type == "ConceptUpdated" and any(
            field in changes for field in ["area", "topic", "subtopic"]
        ):
            return True

        # Recalculate periodically for maturity updates
        # (Check if 7+ days since last calculation)
        if event_type == "ScheduledRecalculation":
            return True

        return False


# Integration with event handler
async def handle_concept_event(event: dict, neo4j_session, all_concepts):
    """
    Event handler that triggers certainty recalculation when needed.
    """
    if CertaintyRecalculationTriggers.should_recalculate(
        event['event_type'],
        event.get('changes', {})
    ):
        concept_id = event['concept_id']
        concept_data = get_concept_data(concept_id, neo4j_session)

        # Recalculate certainty
        new_certainty = calculate_certainty_score(
            concept_id=concept_id,
            concept_data=concept_data,
            neo4j_session=neo4j_session,
            all_concepts=all_concepts
        )

        # Update if changed significantly (>5 points)
        old_certainty = concept_data.get('certainty_score', 0)
        if abs(new_certainty - old_certainty) >= 5:
            update_concept_certainty(concept_id, new_certainty, neo4j_session)

            # Log certainty change event
            log_certainty_change(concept_id, old_certainty, new_certainty)
```

---

## 📊 Implementation Phases

### Phase 1: Server-Side Calculation (Sprint 1)

**Goal:** Implement core heuristic-based calculation

**Tasks:**

1. Implement Factor 1: Explanation Quality
   - Length scoring
   - Structure analysis
   - Keyword richness
2. Implement Factor 2: Relationship Density
   - Count relationships in Neo4j
   - Calculate diversity
   - Average strength
3. Implement Factor 3: Metadata Completeness
   - Check field presence
   - Consistency scoring
4. Implement Factor 4: Concept Maturity
   - Time-based scoring
5. Integrate into `create_concept` tool
6. Add automatic recalculation on updates

**Deliverables:**

- `certainty_calculator.py` module
- Unit tests for each factor
- Integration tests with MCP server
- Documentation

### Phase 2: User Interface (Sprint 2)

**Goal:** Add transparency and user override

**Tasks:**

1. Return calculated certainty in API responses
2. Add certainty breakdown field (show factor scores)
3. Allow user override (optional manual certainty)
4. Add `recalculate_certainty` tool for manual triggering
5. Create certainty history tracking

**Example Response:**

```json
{
  "success": true,
  "concept_id": "uuid-here",
  "certainty_score": 82,
  "certainty_breakdown": {
    "explanation_quality": 35,
    "relationship_density": 24,
    "metadata_completeness": 16,
    "concept_maturity": 7
  },
  "user_override": null,
  "last_calculated": "2025-11-01T08:00:00Z"
}
```

### Phase 3: LLM Enhancement (Sprint 3 - Optional)

**Goal:** Add optional LLM-based refinement

**Tasks:**

1. Implement LLM enhancement layer
2. Add async processing for LLM calls
3. Create configuration for LLM vs heuristic-only mode
4. Performance optimization (batch processing)
5. Cost monitoring and throttling

**Configuration:**

```python
CERTAINTY_CONFIG = {
    "mode": "heuristic_only",  # or "llm_enhanced"
    "llm_enhancement": {
        "enabled": False,
        "model": "claude-sonnet-4.5",
        "max_adjustment": 20,
        "timeout": 5000,  # ms
        "fallback_to_heuristic": True
    },
    "recalculation": {
        "on_update": True,
        "on_relationship_change": True,
        "periodic_interval": "7d"
    }
}
```

---

## 🧪 Testing Strategy

### Unit Tests

```python
class TestCertaintyCalculation:
    """Unit tests for certainty calculation components."""

    def test_explanation_length_score(self):
        """Test length-based scoring."""
        short = "Brief."
        assert calculate_length_score(short) < 10

        medium = "A" * 200
        assert 20 <= calculate_length_score(medium) <= 30

        long = "A" * 600
        assert calculate_length_score(long) >= 35

    def test_relationship_density(self):
        """Test relationship-based scoring."""
        # Mock concept with no relationships
        assert calculate_relationship_count_score("id-0-rels") == 0

        # Mock concept with 3 relationships
        assert 8 <= calculate_relationship_count_score("id-3-rels") <= 12

    def test_full_calculation(self):
        """Test complete certainty calculation."""
        concept_data = {
            'name': 'Test Concept',
            'explanation': 'A' * 300,  # Good length
            'area': 'Testing',
            'topic': 'Unit Tests',
            'subtopic': 'Certainty'
        }

        score = calculate_certainty_score("test-id", concept_data,
                                          mock_neo4j, mock_concepts)

        assert 0 <= score <= 100
        assert isinstance(score, (int, float))
```

### Integration Tests

```python
def test_certainty_on_concept_creation():
    """Test certainty calculation during concept creation."""
    concept = create_concept(
        name="Integration Test",
        explanation="Detailed explanation with multiple sentences. " * 3,
        area="Testing",
        topic="Integration"
    )

    assert 'certainty_score' in concept
    assert 40 <= concept['certainty_score'] <= 70  # Reasonable range
```

### Regression Tests

```python
def test_certainty_consistency():
    """Test that same input produces same output."""
    concept_data = {...}  # Fixed test data

    score1 = calculate_certainty_score("test-id", concept_data, neo4j, concepts)
    score2 = calculate_certainty_score("test-id", concept_data, neo4j, concepts)

    assert score1 == score2  # Deterministic
```

---

## 📈 Success Metrics

### Quantitative Metrics

- **Calculation Speed:** <50ms for heuristic-only mode
- **LLM Mode Speed:** <2000ms for LLM-enhanced mode
- **Accuracy:** Within ±10 points of expert human assessment
- **Consistency:** Same concept → same score (99.9% of time)
- **Coverage:** 100% of concepts have calculated certainty

### Qualitative Metrics

- **User Satisfaction:** Survey showing 80%+ approval
- **Override Rate:** <10% of concepts need manual override
- **Trust:** Users rely on calculated scores for decision-making

---

## 🚨 Risks & Mitigations

### Risk 1: Calculation Too Slow

**Impact:** HIGH  
**Mitigation:**

- Pre-calculate on creation
- Cache scores until changes occur
- Async recalculation in background
- Optimize Neo4j queries

### Risk 2: Scores Don't Match User Intuition

**Impact:** MEDIUM  
**Mitigation:**

- Allow user override
- Show factor breakdown for transparency
- Collect feedback and tune weights
- Gradual rollout with A/B testing

### Risk 3: LLM Enhancement Too Expensive

**Impact:** LOW  
**Mitigation:**

- Make LLM enhancement optional
- Heuristic-only mode as default
- Batch LLM requests
- Cache LLM results

### Risk 4: Frequent Recalculation Causes Performance Issues

**Impact:** MEDIUM  
**Mitigation:**

- Only recalculate on significant changes
- Rate limit recalculations
- Queue-based async processing
- Minimum threshold for recalculation (>5 point change)

---

## 📚 Documentation Requirements

### User-Facing Documentation

**Certainty Score Guide:**

```markdown
# Understanding Certainty Scores

Certainty scores (0-100) indicate how confident the system is about a concept.

## Score Ranges

- **90-100:** Highly certain - Well-documented, thoroughly connected
- **70-89:** Confident - Good explanation and relationships
- **50-69:** Moderate - Basic explanation, some connections
- **30-49:** Low - Limited information or connections
- **0-29:** Very Low - Minimal information, needs development

## What Affects Certainty?

1. **Explanation Quality (40%)** - Detail, clarity, structure
2. **Relationships (30%)** - Number and diversity of connections
3. **Metadata (20%)** - Complete categorization (area/topic/subtopic)
4. **Maturity (10%)** - Stability over time

## Can I Override?

Yes! While the system calculates certainty automatically, you can:

- Provide manual certainty during creation
- Update certainty at any time
- Request recalculation after significant changes
```

### Developer Documentation

```markdown
# Certainty Calculation Developer Guide

## Architecture

[Diagram from earlier]

## API Reference

`calculate_certainty_score(concept_id, concept_data, neo4j_session, all_concepts)`

## Configuration

See `config/certainty.yaml`

## Extending

Add new factors by:

1. Creating factor calculation function
2. Adding to weighted total in `calculate_certainty_score()`
3. Adjusting weights (must sum to 100%)
4. Adding tests
```

---

## ✅ Acceptance Criteria

### Phase 1 (Heuristic Calculation)

- [ ] All four factors implemented and tested
- [ ] Certainty calculated on concept creation
- [ ] Automatic recalculation on relevant updates
- [ ] Unit test coverage >90%
- [ ] Integration tests passing
- [ ] Performance: <50ms calculation time
- [ ] Documentation complete

### Phase 2 (User Interface)

- [ ] Certainty breakdown visible in API responses
- [ ] User override functionality working
- [ ] Manual recalculation tool added
- [ ] Certainty history tracking implemented
- [ ] User documentation published

### Phase 3 (LLM Enhancement - Optional)

- [ ] LLM enhancement layer implemented
- [ ] Async processing working
- [ ] Configuration options available
- [ ] Cost monitoring in place
- [ ] Fallback to heuristic on LLM failure

---

## 🎯 Expected Outcomes

### Before Implementation

- Manual, subjective certainty scores
- Inconsistent across users
- No guidance or standards
- High cognitive load

### After Implementation

- Automatic, objective certainty calculation
- Consistent scoring methodology
- Transparent factor breakdown
- Low user burden (optional override only)
- Continuous improvement as concepts evolve

---

## 📞 Questions for Discussion

1. **Weight Distribution:** Are the factor weights (40/30/20/10) appropriate, or should they be adjusted?

2. **LLM Enhancement:** Should Phase 3 (LLM) be implemented immediately, or start with heuristics only?

3. **User Override:** Should manual override replace calculated score, or be stored separately?

4. **Recalculation Frequency:** How aggressive should automatic recalculation be?

5. **Historical Tracking:** Should we store certainty score history for analysis?

6. **Minimum Threshold:** Should concepts require minimum certainty (e.g., 50) before being "published"?

---

## 📋 Implementation Checklist

**Pre-Development:**

- [ ] Review and approve this specification
- [ ] Prioritize phases
- [ ] Allocate sprint capacity
- [ ] Set up feature branch

**Phase 1 Development:**

- [ ] Implement Factor 1: Explanation Quality
- [ ] Implement Factor 2: Relationship Density
- [ ] Implement Factor 3: Metadata Completeness
- [ ] Implement Factor 4: Concept Maturity
- [ ] Integrate into create_concept
- [ ] Add recalculation triggers
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Performance testing
- [ ] Code review
- [ ] Merge to main

**Phase 2 Development:**

- [ ] Add certainty breakdown to responses
- [ ] Implement user override
- [ ] Add recalculation tool
- [ ] Implement history tracking
- [ ] Update API documentation
- [ ] Write user guide
- [ ] User acceptance testing

**Phase 3 Development (Optional):**

- [ ] Design LLM prompt
- [ ] Implement LLM layer
- [ ] Add async processing
- [ ] Add configuration
- [ ] Cost monitoring
- [ ] Performance optimization
- [ ] A/B testing

---

## 🏁 Conclusion

This specification provides a complete roadmap for implementing automated certainty score calculation. The proposed solution:

✅ **Removes manual burden** from users  
✅ **Increases consistency** through objective metrics  
✅ **Provides transparency** via factor breakdown  
✅ **Allows flexibility** with user override  
✅ **Scales automatically** with concept evolution  
✅ **Optional LLM enhancement** for advanced use cases

**Recommendation:** Begin with Phase 1 (heuristic calculation) to deliver immediate value, then iterate based on user feedback.

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-01  
**Status:** Ready for Implementation Review
