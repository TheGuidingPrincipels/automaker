"""
Integration tests for understanding score with real Neo4j database.

These tests verify the understanding calculator works correctly with actual
database queries and data.
"""

from datetime import datetime

import pytest

from services.confidence.cache_manager import CacheManager
from services.confidence.config import CacheConfig
from services.confidence.data_access import DataAccessLayer
from services.confidence.models import Success
from services.confidence.understanding_calculator import UnderstandingCalculator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_understanding_score_with_real_concept_data(neo4j_session, redis_client):
    """Calculate understanding score using real database"""
    # Create test concept with relationships
    await create_test_concept_with_relationships(neo4j_session, "test-c1", relationship_count=7)

    dal = DataAccessLayer(neo4j_session)
    cache = CacheManager(redis_client, CacheConfig())
    calculator = UnderstandingCalculator(dal, cache, max_relationships=10)

    result = await calculator.calculate_understanding_score("test-c1")

    assert isinstance(result, Success)
    assert 0.0 <= result.value <= 1.0
    assert result.value > 0.5  # Should have decent score with 7 relationships

    # Cleanup
    await cleanup_test_concept(neo4j_session, "test-c1")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_understanding_score_uses_cache_on_second_call(neo4j_session, redis_client):
    """Second call should use cached data"""
    await create_test_concept_with_relationships(neo4j_session, "test-c2", relationship_count=5)

    dal = DataAccessLayer(neo4j_session)
    cache = CacheManager(redis_client, CacheConfig())
    calculator = UnderstandingCalculator(dal, cache, max_relationships=10)

    # First call - populates cache
    result1 = await calculator.calculate_understanding_score("test-c2")
    assert isinstance(result1, Success)

    # Second call - should use cache
    result2 = await calculator.calculate_understanding_score("test-c2")
    assert isinstance(result2, Success)
    assert result1.value == result2.value

    # Cleanup
    await cleanup_test_concept(neo4j_session, "test-c2")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_relationship_density_with_no_relationships(neo4j_session, redis_client):
    """Concept with no relationships should have 0.0 density"""
    await create_test_concept_isolated(neo4j_session, "test-c3")

    dal = DataAccessLayer(neo4j_session)
    cache = CacheManager(redis_client, CacheConfig())
    calculator = UnderstandingCalculator(dal, cache, max_relationships=10)

    result = await calculator.calculate_relationship_density("test-c3")

    assert isinstance(result, Success)
    assert result.value == 0.0

    # Cleanup
    await cleanup_test_concept(neo4j_session, "test-c3")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_understanding_score_with_rich_metadata(neo4j_session, redis_client):
    """Concept with tags and examples should score higher"""
    await create_test_concept_with_rich_metadata(neo4j_session, "test-c4", relationship_count=5)

    dal = DataAccessLayer(neo4j_session)
    cache = CacheManager(redis_client, CacheConfig())
    calculator = UnderstandingCalculator(dal, cache, max_relationships=10)

    result = await calculator.calculate_understanding_score("test-c4")

    assert isinstance(result, Success)
    assert result.value > 0.6  # Rich metadata + relationships should score high

    # Cleanup
    await cleanup_test_concept(neo4j_session, "test-c4")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_understanding_score_with_minimal_data(neo4j_session, redis_client):
    """Concept with minimal data should have lower score"""
    await create_test_concept_minimal(neo4j_session, "test-c5")

    dal = DataAccessLayer(neo4j_session)
    cache = CacheManager(redis_client, CacheConfig())
    calculator = UnderstandingCalculator(dal, cache, max_relationships=10)

    result = await calculator.calculate_understanding_score("test-c5")

    assert isinstance(result, Success)
    assert result.value < 0.5  # Minimal data should score low

    # Cleanup
    await cleanup_test_concept(neo4j_session, "test-c5")


# Helper functions for test data creation
async def create_test_concept_with_relationships(session, concept_id: str, relationship_count: int):
    """Create test concept with specified number of relationships"""
    query = """
    CREATE (c:Concept {
        id: $concept_id,
        name: $name,
        explanation: $explanation,
        created_at: $created_at,
        tags: $tags,
        examples: $examples
    })
    """
    await session.run(
        query,
        concept_id=concept_id,
        name="Test Concept",
        explanation="This is a comprehensive explanation with domain-specific terminology",
        created_at=datetime.now().isoformat(),
        tags=["test", "integration"],
        examples=["example1"],
    )

    # Create related concepts
    for i in range(relationship_count):
        related_id = f"{concept_id}-related-{i}"
        await session.run(
            """
            CREATE (c:Concept {
                id: $id,
                name: $name,
                explanation: 'Related concept',
                created_at: $created_at
            })
            """,
            id=related_id,
            name=f"Related {i}",
            created_at=datetime.now().isoformat(),
        )

        # Create relationship
        await session.run(
            """
            MATCH (c1:Concept {id: $concept_id})
            MATCH (c2:Concept {id: $related_id})
            CREATE (c1)-[:RELATES_TO]->(c2)
            """,
            concept_id=concept_id,
            related_id=related_id,
        )


async def create_test_concept_isolated(session, concept_id: str):
    """Create test concept with no relationships"""
    query = """
    CREATE (c:Concept {
        id: $concept_id,
        name: $name,
        explanation: $explanation,
        created_at: $created_at,
        tags: [],
        examples: []
    })
    """
    await session.run(
        query,
        concept_id=concept_id,
        name="Isolated Concept",
        explanation="Basic explanation",
        created_at=datetime.now().isoformat(),
    )


async def create_test_concept_with_rich_metadata(session, concept_id: str, relationship_count: int):
    """Create test concept with rich metadata (tags, examples)"""
    query = """
    CREATE (c:Concept {
        id: $concept_id,
        name: $name,
        explanation: $explanation,
        created_at: $created_at,
        tags: $tags,
        examples: $examples
    })
    """
    await session.run(
        query,
        concept_id=concept_id,
        name="Rich Concept",
        explanation="This is a comprehensive explanation with domain-specific terminology including advanced vocabulary and technical concepts",
        created_at=datetime.now().isoformat(),
        tags=["tag1", "tag2", "tag3"],
        examples=["example1", "example2"],
    )

    # Create relationships
    for i in range(relationship_count):
        related_id = f"{concept_id}-related-{i}"
        await session.run(
            """
            CREATE (c:Concept {
                id: $id,
                name: $name,
                explanation: 'Related concept',
                created_at: $created_at
            })
            """,
            id=related_id,
            name=f"Related {i}",
            created_at=datetime.now().isoformat(),
        )

        await session.run(
            """
            MATCH (c1:Concept {id: $concept_id})
            MATCH (c2:Concept {id: $related_id})
            CREATE (c1)-[:RELATES_TO]->(c2)
            """,
            concept_id=concept_id,
            related_id=related_id,
        )


async def create_test_concept_minimal(session, concept_id: str):
    """Create test concept with minimal data"""
    query = """
    CREATE (c:Concept {
        id: $concept_id,
        name: $name,
        explanation: $explanation,
        created_at: $created_at,
        tags: [],
        examples: []
    })
    """
    await session.run(
        query,
        concept_id=concept_id,
        name="Minimal",
        explanation="Basic",
        created_at=datetime.now().isoformat(),
    )


async def cleanup_test_concept(session, concept_id: str):
    """Delete test concept and all related concepts"""
    # Delete relationships first
    await session.run(
        """
        MATCH (c:Concept {id: $concept_id})-[r]-()
        DELETE r
        """,
        concept_id=concept_id,
    )

    # Delete related concepts
    await session.run(
        """
        MATCH (c:Concept)
        WHERE c.id STARTS WITH $prefix
        DELETE c
        """,
        prefix=concept_id,
    )
