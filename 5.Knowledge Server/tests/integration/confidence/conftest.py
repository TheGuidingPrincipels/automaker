"""
Pytest fixtures for confidence integration tests.

These fixtures provide Neo4j session adapters and test data
for testing the DataAccessLayer and confidence calculation.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from typing import AsyncIterator
from unittest.mock import AsyncMock, Mock

from config import Config
from services.neo4j_service import Neo4jService


class MockAsyncResult:
    """Mock async result from Neo4j query."""

    def __init__(self, records):
        self._records = records
        self._index = 0

    def single(self):
        """Return single record or None."""
        if self._records:
            return self._records[0]
        return None

    async def data(self):
        """Return all records as a list of dicts."""
        return self._records if self._records else []

    async def __aiter__(self):
        for record in self._records:
            yield record


class Neo4jSessionAdapter:
    """Adapter that wraps Neo4j service to provide async session interface."""

    def __init__(self, neo4j_service: Neo4jService):
        self._service = neo4j_service

    async def run(self, query: str, **params):
        """Execute a query and return async-compatible result."""
        # Execute query synchronously and wrap result
        result = self._service.execute_read(query, params)
        return MockAsyncResult(result if result else [])


@pytest.fixture(scope="function")
def neo4j_session_adapter():
    """
    Provide a Neo4j session adapter for integration tests.

    Skips if Neo4j is not available.
    """
    try:
        config = Config()
        service = Neo4jService(
            uri=config.NEO4J_URI,
            user=config.NEO4J_USER,
            password=config.NEO4J_PASSWORD
        )
        service.connect()

        if not service.is_connected():
            pytest.skip("Neo4j not available for integration tests")

        yield Neo4jSessionAdapter(service)

        # Cleanup
        service.close()

    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


@pytest.fixture(scope="function")
def concept_with_metadata(neo4j_session_adapter):
    """
    Create a test concept with metadata in Neo4j.

    Returns the concept data dict with concept_id, name, etc.
    Cleans up after test.
    """
    concept_id = f"test-confidence-{uuid.uuid4().hex[:8]}"
    concept_data = {
        "concept_id": concept_id,
        "name": "Test Confidence Concept",
        "explanation": "A test concept for confidence calculation testing",
        "area": "Testing",
        "topic": "Integration",
        "subtopic": "Confidence",
        "created_at": datetime.now().isoformat(),
        "tags": ["test", "confidence"],
        "examples": ["example1", "example2"]
    }

    # Create concept in Neo4j
    create_query = """
    CREATE (c:Concept {
        concept_id: $concept_id,
        name: $name,
        explanation: $explanation,
        area: $area,
        topic: $topic,
        subtopic: $subtopic,
        created_at: $created_at,
        tags: $tags,
        examples: $examples
    })
    RETURN c.concept_id AS id
    """

    try:
        neo4j_session_adapter._service.execute_write(create_query, concept_data)
        yield concept_data
    finally:
        # Cleanup
        delete_query = "MATCH (c:Concept {concept_id: $concept_id}) DETACH DELETE c"
        try:
            neo4j_session_adapter._service.execute_write(delete_query, {"concept_id": concept_id})
        except Exception:
            pass


@pytest.fixture(scope="function")
def concept_with_relationships(neo4j_session_adapter):
    """
    Create a test concept with relationships to other concepts.

    Returns the concept data dict.
    Cleans up after test.
    """
    concept_id = f"test-rel-source-{uuid.uuid4().hex[:8]}"
    target_id = f"test-rel-target-{uuid.uuid4().hex[:8]}"

    concept_data = {
        "concept_id": concept_id,
        "name": "Source Concept",
        "explanation": "A source concept with relationships",
        "created_at": datetime.now().isoformat()
    }

    # Create source concept, target concept, and relationship
    setup_query = """
    CREATE (source:Concept {
        concept_id: $source_id,
        name: $name,
        explanation: $explanation,
        created_at: $created_at
    })
    CREATE (target:Concept {
        concept_id: $target_id,
        name: 'Target Concept',
        explanation: 'A target concept',
        created_at: $created_at
    })
    CREATE (source)-[:RELATES_TO {strength: 1.0, created_at: $created_at}]->(target)
    RETURN source.concept_id AS id
    """

    try:
        neo4j_session_adapter._service.execute_write(setup_query, {
            "source_id": concept_id,
            "target_id": target_id,
            "name": concept_data["name"],
            "explanation": concept_data["explanation"],
            "created_at": concept_data["created_at"]
        })
        yield concept_data
    finally:
        # Cleanup both concepts and relationship
        cleanup_query = """
        MATCH (c:Concept)
        WHERE c.concept_id IN [$source_id, $target_id]
        DETACH DELETE c
        """
        try:
            neo4j_session_adapter._service.execute_write(cleanup_query, {
                "source_id": concept_id,
                "target_id": target_id
            })
        except Exception:
            pass


@pytest.fixture(scope="function")
def concept_with_review_history(neo4j_session_adapter):
    """
    Create a test concept with review history.

    Returns the concept data dict.
    Cleans up after test.
    """
    concept_id = f"test-review-{uuid.uuid4().hex[:8]}"

    concept_data = {
        "concept_id": concept_id,
        "name": "Reviewed Concept",
        "explanation": "A concept with review history",
        "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
        "last_reviewed_at": datetime.now().isoformat()
    }

    # Create concept with review history
    # Note: The actual review history might be stored differently
    # This creates a concept with review-related properties
    setup_query = """
    CREATE (c:Concept {
        concept_id: $concept_id,
        name: $name,
        explanation: $explanation,
        created_at: $created_at,
        last_reviewed_at: $last_reviewed_at,
        review_count: 3,
        review_outcomes: ['pass', 'pass', 'fail']
    })
    RETURN c.concept_id AS id
    """

    try:
        neo4j_session_adapter._service.execute_write(setup_query, {
            "concept_id": concept_id,
            "name": concept_data["name"],
            "explanation": concept_data["explanation"],
            "created_at": concept_data["created_at"],
            "last_reviewed_at": concept_data["last_reviewed_at"]
        })
        yield concept_data
    finally:
        # Cleanup
        delete_query = "MATCH (c:Concept {concept_id: $concept_id}) DETACH DELETE c"
        try:
            neo4j_session_adapter._service.execute_write(delete_query, {"concept_id": concept_id})
        except Exception:
            pass
