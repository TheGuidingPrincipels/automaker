"""
Unit tests for Neo4jProjection class.

Tests projection logic in isolation using mocked Neo4j service.
"""

from unittest.mock import Mock

import pytest
from neo4j.exceptions import DatabaseError, ServiceUnavailable

from models.events import (
    ConceptCreated,
    ConceptDeleted,
    ConceptUpdated,
    Event,
    RelationshipCreated,
    RelationshipDeleted,
)
from projections.neo4j_projection import Neo4jProjection
from services.neo4j_service import Neo4jService


@pytest.fixture
def mock_neo4j_service():
    """Create a mock Neo4j service for testing."""
    service = Mock(spec=Neo4jService)
    service.execute_write = Mock(
        return_value={
            "nodes_created": 1,
            "properties_set": 5,
            "relationships_created": 0,
            "relationships_deleted": 0,
        }
    )
    service.execute_read = Mock(return_value=[])
    return service


@pytest.fixture
def projection(mock_neo4j_service):
    """Create Neo4jProjection instance with mocked service."""
    return Neo4jProjection(mock_neo4j_service)


class TestNeo4jProjectionBasics:
    """Test basic projection functionality."""

    def test_projection_name(self, projection):
        """Test that projection returns correct name."""
        assert projection.get_projection_name() == "neo4j"

    def test_unknown_event_type(self, projection, mock_neo4j_service):
        """Test handling of unknown event types."""
        event = Event(
            event_type="UnknownEvent",
            aggregate_id="test_001",
            aggregate_type="Test",
            event_data={"data": "test"},
            version=1,
        )

        result = projection.project_event(event)

        # Should return False for unknown event types
        assert result is False
        # Should not call Neo4j
        mock_neo4j_service.execute_write.assert_not_called()


class TestConceptCreatedProjection:
    """Test ConceptCreated event projection."""

    def test_project_concept_created_minimal(self, projection, mock_neo4j_service):
        """Test projecting ConceptCreated with minimal data."""
        event = ConceptCreated(
            aggregate_id="concept_001",
            concept_data={
                "name": "Test Concept",
                "explanation": "A test concept",
                "confidence_score": 0.95
            },
            version=1,
        )

        result = projection.project_event(event)

        assert result is True
        mock_neo4j_service.execute_write.assert_called_once()

        # Verify query structure
        call_args = mock_neo4j_service.execute_write.call_args
        query = call_args[0][0]
        params = call_args[1]["parameters"]

        assert "MERGE" in query
        assert "Concept" in query
        assert params["concept_id"] == "concept_001"
        assert params["properties"]["name"] == "Test Concept"
        assert params["properties"]["confidence_score"] == 0.95

    def test_project_concept_created_full(self, projection, mock_neo4j_service):
        """Test projecting ConceptCreated with all optional fields."""
        event = ConceptCreated(
            aggregate_id="concept_002",
            concept_data={
                "name": "Full Concept",
                "explanation": "Complete concept data",
                "confidence_score": 0.99,
                "area": "Mathematics",
                "topic": "Algebra",
                "subtopic": "Linear Equations",
                "examples": ["x + 2 = 5", "3y = 9"],
                "prerequisites": ["arithmetic", "variables"],
            },
            version=1,
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_neo4j_service.execute_write.call_args
        params = call_args[1]["parameters"]

        # Verify all properties are included
        props = params["properties"]
        assert props["area"] == "Mathematics"
        assert props["topic"] == "Algebra"
        assert props["subtopic"] == "Linear Equations"
        assert props["examples"] == ["x + 2 = 5", "3y = 9"]
        assert props["prerequisites"] == ["arithmetic", "variables"]

    def test_project_concept_created_with_source_urls(self, projection, mock_neo4j_service):
        """Test projecting ConceptCreated with source_urls as list of dictionaries.

        source_urls must be serialized to JSON string for Neo4j storage,
        as Neo4j properties cannot store lists of dictionaries (only primitives or lists of primitives).
        """
        import json

        source_urls_data = [
            {
                "url": "https://docs.python.org/3/library/asyncio.html",
                "title": "asyncio — Asynchronous I/O",
                "quality_score": 1.0,
                "domain_category": "official",
            },
            {
                "url": "https://realpython.com/async-io-python/",
                "title": "Async IO in Python",
                "quality_score": 0.8,
                "domain_category": "in_depth",
            },
        ]

        event = ConceptCreated(
            aggregate_id="concept_with_urls",
            concept_data={
                "name": "Python AsyncIO",
                "explanation": "Asynchronous I/O framework in Python",
                "area": "Programming",
                "topic": "Python",
                "source_urls": source_urls_data,  # List of dicts
            },
            version=1,
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_neo4j_service.execute_write.call_args
        params = call_args[1]["parameters"]
        props = params["properties"]

        # CRITICAL: source_urls must be JSON string, not list of dicts
        assert "source_urls" in props
        assert isinstance(
            props["source_urls"], str
        ), "source_urls must be serialized to JSON string for Neo4j storage"

        # Verify it's valid JSON and matches original data
        deserialized = json.loads(props["source_urls"])
        assert deserialized == source_urls_data
        assert len(deserialized) == 2
        assert deserialized[0]["url"] == "https://docs.python.org/3/library/asyncio.html"

    def test_concept_created_idempotency(self, projection, mock_neo4j_service):
        """Test that MERGE ensures idempotency."""
        event = ConceptCreated(
            aggregate_id="concept_003",
            concept_data={"name": "Idempotent Concept", "explanation": "Test"},
            version=1,
        )

        # Project same event twice
        result1 = projection.project_event(event)
        result2 = projection.project_event(event)

        assert result1 is True
        assert result2 is True

        # Both calls should succeed (MERGE handles duplicates)
        assert mock_neo4j_service.execute_write.call_count == 2


class TestConceptUpdatedProjection:
    """Test ConceptUpdated event projection."""

    def test_project_concept_updated(self, projection, mock_neo4j_service):
        """Test projecting ConceptUpdated event."""
        event = ConceptUpdated(
            aggregate_id="concept_001",
            updates={
                "explanation": "Updated explanation",
                "confidence_score": 0.98
            },
            version=2
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_neo4j_service.execute_write.call_args
        query = call_args[0][0]
        params = call_args[1]["parameters"]

        assert "MATCH" in query
        assert "Concept" in query
        assert params["concept_id"] == "concept_001"
        assert "explanation" in params["updates"]
        assert "confidence_score" in params["updates"]
        assert "last_modified" in params["updates"]

    def test_concept_updated_not_found(self, projection, mock_neo4j_service):
        """Test updating non-existent concept."""
        # Mock Neo4j returning no properties set (concept not found)
        mock_neo4j_service.execute_write.return_value = {"properties_set": 0}

        event = ConceptUpdated(
            aggregate_id="nonexistent_concept", updates={"explanation": "Updated"}, version=2
        )

        result = projection.project_event(event)

        # Should return False when concept not found
        assert result is False


class TestConceptDeletedProjection:
    """Test ConceptDeleted event projection."""

    def test_project_concept_deleted(self, projection, mock_neo4j_service):
        """Test projecting ConceptDeleted event (soft delete)."""
        event = ConceptDeleted(aggregate_id="concept_001", version=3)

        result = projection.project_event(event)

        assert result is True
        call_args = mock_neo4j_service.execute_write.call_args
        query = call_args[0][0]
        params = call_args[1]["parameters"]

        # Verify soft delete query
        assert "MATCH" in query
        assert "SET" in query
        assert "deleted = true" in query
        assert params["concept_id"] == "concept_001"
        assert "deleted_at" in params

    def test_concept_deleted_not_found(self, projection, mock_neo4j_service):
        """Test deleting non-existent concept."""
        mock_neo4j_service.execute_write.return_value = {"properties_set": 0}

        event = ConceptDeleted(aggregate_id="nonexistent_concept", version=1)

        result = projection.project_event(event)

        assert result is False


class TestRelationshipCreatedProjection:
    """Test RelationshipCreated event projection."""

    def test_project_relationship_created_contains(self, projection, mock_neo4j_service):
        """Test creating CONTAINS relationship."""
        mock_neo4j_service.execute_write.return_value = {
            "relationships_created": 1,
            "properties_set": 2,
        }

        event = RelationshipCreated(
            aggregate_id="rel_001",
            relationship_data={
                "relationship_type": "CONTAINS",
                "from_concept_id": "concept_001",
                "to_concept_id": "concept_002",
                "strength": 1.0,
            },
            version=1,
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_neo4j_service.execute_write.call_args
        query = call_args[0][0]
        params = call_args[1]["parameters"]

        assert "CONTAINS" in query
        assert "MERGE" in query
        assert params["from_id"] == "concept_001"
        assert params["to_id"] == "concept_002"
        assert params["properties"]["strength"] == 1.0

    def test_project_relationship_created_prerequisite(self, projection, mock_neo4j_service):
        """Test creating PREREQUISITE relationship."""
        mock_neo4j_service.execute_write.return_value = {"relationships_created": 1}

        event = RelationshipCreated(
            aggregate_id="rel_002",
            relationship_data={
                "relationship_type": "PREREQUISITE",
                "from_concept_id": "concept_001",
                "to_concept_id": "concept_003",
                "description": "Requires understanding of concept_001",
            },
            version=1,
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_neo4j_service.execute_write.call_args
        query = call_args[0][0]

        assert "PREREQUISITE" in query

    def test_project_relationship_invalid_type(self, projection, mock_neo4j_service):
        """Test relationship with invalid type defaults to RELATES_TO."""
        mock_neo4j_service.execute_write.return_value = {"relationships_created": 1}

        event = RelationshipCreated(
            aggregate_id="rel_003",
            relationship_data={
                "relationship_type": "INVALID_TYPE",
                "from_concept_id": "concept_001",
                "to_concept_id": "concept_002",
            },
            version=1,
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_neo4j_service.execute_write.call_args
        query = call_args[0][0]

        # Should default to RELATES_TO
        assert "RELATES_TO" in query

    def test_relationship_created_missing_nodes(self, projection, mock_neo4j_service):
        """Test creating relationship when nodes don't exist."""
        # Mock Neo4j returning no relationships created
        mock_neo4j_service.execute_write.return_value = {
            "relationships_created": 0,
            "properties_set": 0,
        }

        event = RelationshipCreated(
            aggregate_id="rel_004",
            relationship_data={
                "relationship_type": "CONTAINS",
                "from_concept_id": "nonexistent_001",
                "to_concept_id": "nonexistent_002",
            },
            version=1,
        )

        result = projection.project_event(event)

        # Should return False when nodes don't exist
        assert result is False

    def test_relationship_created_missing_ids(self, projection, mock_neo4j_service):
        """Test relationship creation with missing from/to IDs."""
        event = RelationshipCreated(
            aggregate_id="rel_005",
            relationship_data={
                "relationship_type": "CONTAINS"
                # Missing from_concept_id and to_concept_id
            },
            version=1,
        )

        result = projection.project_event(event)

        # Should return False for invalid data
        assert result is False
        mock_neo4j_service.execute_write.assert_not_called()


class TestRelationshipDeletedProjection:
    """Test RelationshipDeleted event projection."""

    def test_project_relationship_deleted(self, projection, mock_neo4j_service):
        """Test deleting a relationship."""
        mock_neo4j_service.execute_write.return_value = {"relationships_deleted": 1}

        event = RelationshipDeleted(aggregate_id="rel_001", version=2)

        result = projection.project_event(event)

        assert result is True
        call_args = mock_neo4j_service.execute_write.call_args
        query = call_args[0][0]
        params = call_args[1]["parameters"]

        assert "DELETE" in query
        assert params["relationship_id"] == "rel_001"

    def test_relationship_deleted_not_found(self, projection, mock_neo4j_service):
        """Test deleting non-existent relationship."""
        mock_neo4j_service.execute_write.return_value = {"relationships_deleted": 0}

        event = RelationshipDeleted(aggregate_id="nonexistent_rel", version=1)

        result = projection.project_event(event)

        # Should return False when relationship not found
        assert result is False


class TestErrorHandling:
    """Test error handling in projection."""

    def test_service_unavailable_error(self, projection, mock_neo4j_service):
        """Test handling of ServiceUnavailable exception."""
        mock_neo4j_service.execute_write.side_effect = ServiceUnavailable("Connection lost")

        event = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

        result = projection.project_event(event)

        # Should return False on service unavailable
        assert result is False

    def test_database_error(self, projection, mock_neo4j_service):
        """Test handling of DatabaseError exception."""
        mock_neo4j_service.execute_write.side_effect = DatabaseError("Query error")

        event = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

        result = projection.project_event(event)

        # Should return False on database error
        assert result is False

    def test_unexpected_exception(self, projection, mock_neo4j_service):
        """Test handling of unexpected exceptions."""
        mock_neo4j_service.execute_write.side_effect = Exception("Unexpected error")

        event = ConceptCreated(aggregate_id="concept_001", concept_data={"name": "Test"}, version=1)

        result = projection.project_event(event)

        # Should return False on unexpected errors
        assert result is False


class TestProjectionIntegration:
    """Test projection integration scenarios."""

    def test_projection_workflow_multiple_events(self, projection, mock_neo4j_service):
        """Test projecting multiple events in sequence."""
        # Create concept
        create_event = ConceptCreated(
            aggregate_id="concept_001",
            concept_data={"name": "Initial Concept", "explanation": "First version"},
            version=1,
        )

        # Update concept
        update_event = ConceptUpdated(
            aggregate_id="concept_001", updates={"explanation": "Updated version"}, version=2
        )

        # Delete concept
        delete_event = ConceptDeleted(aggregate_id="concept_001", version=3)

        # Project all events
        assert projection.project_event(create_event) is True
        assert projection.project_event(update_event) is True
        assert projection.project_event(delete_event) is True

        # Verify all events were projected
        assert mock_neo4j_service.execute_write.call_count == 3
