"""
Integration tests for Neo4jProjection with real Neo4j database.

Tests full projection workflow using actual Neo4j instance.
"""

import pytest

from models.events import (
    ConceptCreated,
    ConceptDeleted,
    ConceptUpdated,
    RelationshipCreated,
    RelationshipDeleted,
)
from projections.neo4j_projection import Neo4jProjection
from services.neo4j_service import create_neo4j_service_from_env


@pytest.fixture(scope="module")
def neo4j_service():
    """Create real Neo4j service for integration testing."""
    service = create_neo4j_service_from_env()
    if not service.connect():
        pytest.skip("Neo4j service unavailable; skipping Neo4j integration tests")
    yield service
    service.close()


@pytest.fixture
def clean_neo4j(neo4j_service):
    """Clean Neo4j database before each test."""
    # Delete all test concepts and relationships
    neo4j_service.execute_write(
        "MATCH (c:Concept) WHERE c.concept_id STARTS WITH 'test_' DETACH DELETE c"
    )
    yield
    # Cleanup after test
    neo4j_service.execute_write(
        "MATCH (c:Concept) WHERE c.concept_id STARTS WITH 'test_' DETACH DELETE c"
    )


@pytest.fixture
def projection(neo4j_service):
    """Create Neo4jProjection with real Neo4j service."""
    return Neo4jProjection(neo4j_service)


class TestConceptCreatedIntegration:
    """Integration tests for ConceptCreated projection."""

    def test_create_concept_in_neo4j(self, projection, neo4j_service, clean_neo4j):
        """Test creating a concept node in real Neo4j database."""
        event = ConceptCreated(
            aggregate_id="test_concept_001",
            concept_data={
                "name": "Integration Test Concept",
                "explanation": "A concept for integration testing",
                "confidence_score": 0.95,
                "area": "Testing",
                "topic": "Integration",
            },
            version=1,
        )

        # Project event
        result = projection.project_event(event)
        assert result is True

        # Verify concept exists in Neo4j
        query = "MATCH (c:Concept {concept_id: $id}) RETURN c"
        results = neo4j_service.execute_read(query, {"id": "test_concept_001"})

        assert len(results) == 1
        concept = results[0]["c"]
        assert concept["name"] == "Integration Test Concept"
        assert concept["explanation"] == "A concept for integration testing"
        assert concept["confidence_score"] == 0.95
        assert concept["area"] == "Testing"
        assert concept["topic"] == "Integration"

    def test_create_concept_with_all_properties(self, projection, neo4j_service, clean_neo4j):
        """Test creating concept with all optional properties."""
        event = ConceptCreated(
            aggregate_id="test_concept_002",
            concept_data={
                "name": "Full Concept",
                "explanation": "Complete concept",
                "confidence_score": 0.99,
                "area": "Mathematics",
                "topic": "Algebra",
                "subtopic": "Linear Equations",
                "examples": ["2x + 3 = 7", "y = mx + b"],
                "prerequisites": ["arithmetic", "variables"],
            },
            version=1,
        )

        result = projection.project_event(event)
        assert result is True

        # Verify all properties
        query = "MATCH (c:Concept {concept_id: $id}) RETURN c"
        results = neo4j_service.execute_read(query, {"id": "test_concept_002"})

        concept = results[0]["c"]
        assert concept["subtopic"] == "Linear Equations"
        assert concept["examples"] == ["2x + 3 = 7", "y = mx + b"]
        assert concept["prerequisites"] == ["arithmetic", "variables"]

    def test_create_concept_idempotency(self, projection, neo4j_service, clean_neo4j):
        """Test that creating same concept twice is idempotent."""
        event = ConceptCreated(
            aggregate_id="test_concept_003",
            concept_data={"name": "Idempotent Concept", "explanation": "Testing idempotency"},
            version=1,
        )

        # Project twice
        result1 = projection.project_event(event)
        result2 = projection.project_event(event)

        assert result1 is True
        assert result2 is True

        # Verify only one node exists
        query = "MATCH (c:Concept {concept_id: $id}) RETURN count(c) as count"
        results = neo4j_service.execute_read(query, {"id": "test_concept_003"})
        assert results[0]["count"] == 1


class TestConceptUpdatedIntegration:
    """Integration tests for ConceptUpdated projection."""

    def test_update_concept_properties(self, projection, neo4j_service, clean_neo4j):
        """Test updating concept properties."""
        # First create a concept
        create_event = ConceptCreated(
            aggregate_id="test_concept_004",
            concept_data={
                "name": "Original Name",
                "explanation": "Original explanation",
                "confidence_score": 0.5
            },
            version=1,
        )
        projection.project_event(create_event)

        # Now update it
        update_event = ConceptUpdated(
            aggregate_id="test_concept_004",
            updates={
                "explanation": "Updated explanation",
                "confidence_score": 0.95
            },
            version=2
        )

        result = projection.project_event(update_event)
        assert result is True

        # Verify updates
        query = "MATCH (c:Concept {concept_id: $id}) RETURN c"
        results = neo4j_service.execute_read(query, {"id": "test_concept_004"})

        concept = results[0]["c"]
        assert concept["name"] == "Original Name"  # Unchanged
        assert concept["explanation"] == "Updated explanation"  # Updated
        assert concept["confidence_score"] == 0.95  # Updated
        assert "last_modified" in concept  # Timestamp added

    def test_update_nonexistent_concept(self, projection, neo4j_service, clean_neo4j):
        """Test updating non-existent concept returns False."""
        update_event = ConceptUpdated(
            aggregate_id="test_nonexistent", updates={"explanation": "Updated"}, version=1
        )

        result = projection.project_event(update_event)
        assert result is False


class TestConceptDeletedIntegration:
    """Integration tests for ConceptDeleted projection."""

    def test_soft_delete_concept(self, projection, neo4j_service, clean_neo4j):
        """Test soft deleting a concept."""
        # Create concept
        create_event = ConceptCreated(
            aggregate_id="test_concept_005",
            concept_data={"name": "To Be Deleted", "explanation": "Will be deleted"},
            version=1,
        )
        projection.project_event(create_event)

        # Delete concept
        delete_event = ConceptDeleted(aggregate_id="test_concept_005", version=2)

        result = projection.project_event(delete_event)
        assert result is True

        # Verify concept still exists but marked as deleted
        query = "MATCH (c:Concept {concept_id: $id}) RETURN c"
        results = neo4j_service.execute_read(query, {"id": "test_concept_005"})

        assert len(results) == 1
        concept = results[0]["c"]
        assert concept["deleted"] is True
        assert "deleted_at" in concept
        assert concept["name"] == "To Be Deleted"  # Data preserved


class TestRelationshipCreatedIntegration:
    """Integration tests for RelationshipCreated projection."""

    def test_create_contains_relationship(self, projection, neo4j_service, clean_neo4j):
        """Test creating CONTAINS relationship between concepts."""
        # Create two concepts
        concept1 = ConceptCreated(
            aggregate_id="test_concept_006",
            concept_data={"name": "Parent Concept", "explanation": "Parent"},
            version=1,
        )
        concept2 = ConceptCreated(
            aggregate_id="test_concept_007",
            concept_data={"name": "Child Concept", "explanation": "Child"},
            version=1,
        )

        projection.project_event(concept1)
        projection.project_event(concept2)

        # Create relationship
        rel_event = RelationshipCreated(
            aggregate_id="test_rel_001",
            relationship_data={
                "relationship_type": "CONTAINS",
                "from_concept_id": "test_concept_006",
                "to_concept_id": "test_concept_007",
                "strength": 1.0,
                "description": "Parent contains child",
            },
            version=1,
        )

        result = projection.project_event(rel_event)
        assert result is True

        # Verify relationship exists
        query = """
        MATCH (from:Concept {concept_id: $from_id})-[r:CONTAINS]->(to:Concept {concept_id: $to_id})
        RETURN r
        """
        results = neo4j_service.execute_read(
            query, {"from_id": "test_concept_006", "to_id": "test_concept_007"}
        )

        assert len(results) == 1
        rel = results[0]["r"]
        assert rel["relationship_id"] == "test_rel_001"
        assert rel["strength"] == 1.0
        assert rel["description"] == "Parent contains child"

    def test_create_prerequisite_relationship(self, projection, neo4j_service, clean_neo4j):
        """Test creating PREREQUISITE relationship."""
        # Create concepts
        concept1 = ConceptCreated(
            aggregate_id="test_concept_008",
            concept_data={"name": "Basic Concept", "explanation": "Must learn first"},
            version=1,
        )
        concept2 = ConceptCreated(
            aggregate_id="test_concept_009",
            concept_data={"name": "Advanced Concept", "explanation": "Requires basic"},
            version=1,
        )

        projection.project_event(concept1)
        projection.project_event(concept2)

        # Create PREREQUISITE relationship
        rel_event = RelationshipCreated(
            aggregate_id="test_rel_002",
            relationship_data={
                "relationship_type": "PREREQUISITE",
                "from_concept_id": "test_concept_009",
                "to_concept_id": "test_concept_008",
                "description": "Advanced requires basic",
            },
            version=1,
        )

        result = projection.project_event(rel_event)
        assert result is True

        # Verify PREREQUISITE relationship
        query = """
        MATCH (from:Concept {concept_id: $from_id})-[r:PREREQUISITE]->(to:Concept {concept_id: $to_id})
        RETURN r
        """
        results = neo4j_service.execute_read(
            query, {"from_id": "test_concept_009", "to_id": "test_concept_008"}
        )

        assert len(results) == 1

    def test_create_relationship_missing_nodes(self, projection, neo4j_service, clean_neo4j):
        """Test creating relationship when nodes don't exist."""
        rel_event = RelationshipCreated(
            aggregate_id="test_rel_003",
            relationship_data={
                "relationship_type": "CONTAINS",
                "from_concept_id": "test_nonexistent_001",
                "to_concept_id": "test_nonexistent_002",
            },
            version=1,
        )

        result = projection.project_event(rel_event)
        # Should return False when nodes don't exist
        assert result is False


class TestRelationshipDeletedIntegration:
    """Integration tests for RelationshipDeleted projection."""

    def test_delete_relationship(self, projection, neo4j_service, clean_neo4j):
        """Test deleting a relationship."""
        # Create concepts and relationship
        concept1 = ConceptCreated(
            aggregate_id="test_concept_010",
            concept_data={"name": "Concept A", "explanation": "A"},
            version=1,
        )
        concept2 = ConceptCreated(
            aggregate_id="test_concept_011",
            concept_data={"name": "Concept B", "explanation": "B"},
            version=1,
        )

        projection.project_event(concept1)
        projection.project_event(concept2)

        rel_created = RelationshipCreated(
            aggregate_id="test_rel_004",
            relationship_data={
                "relationship_type": "RELATES_TO",
                "from_concept_id": "test_concept_010",
                "to_concept_id": "test_concept_011",
            },
            version=1,
        )
        projection.project_event(rel_created)

        # Verify relationship exists
        query = """
        MATCH ()-[r {relationship_id: $id}]->()
        RETURN count(r) as count
        """
        results = neo4j_service.execute_read(query, {"id": "test_rel_004"})
        assert results[0]["count"] == 1

        # Delete relationship
        rel_deleted = RelationshipDeleted(aggregate_id="test_rel_004", version=2)

        result = projection.project_event(rel_deleted)
        assert result is True

        # Verify relationship is gone
        results = neo4j_service.execute_read(query, {"id": "test_rel_004"})
        assert results[0]["count"] == 0


class TestFullProjectionWorkflow:
    """Test complete projection workflows."""

    def test_full_concept_lifecycle(self, projection, neo4j_service, clean_neo4j):
        """Test full concept lifecycle: create -> update -> delete."""
        # Create
        create_event = ConceptCreated(
            aggregate_id="test_concept_012",
            concept_data={
                "name": "Lifecycle Concept",
                "explanation": "Testing full lifecycle",
                "confidence_score": 0.5
            },
            version=1,
        )
        assert projection.project_event(create_event) is True

        # Update
        update_event = ConceptUpdated(
            aggregate_id="test_concept_012",
            updates={"confidence_score": 0.95, "explanation": "Updated"},
            version=2
        )
        assert projection.project_event(update_event) is True

        # Delete
        delete_event = ConceptDeleted(aggregate_id="test_concept_012", version=3)
        assert projection.project_event(delete_event) is True

        # Verify final state
        query = "MATCH (c:Concept {concept_id: $id}) RETURN c"
        results = neo4j_service.execute_read(query, {"id": "test_concept_012"})

        concept = results[0]["c"]
        assert concept["deleted"] is True
        assert concept["confidence_score"] == 0.95  # Updated value preserved
        assert concept["explanation"] == "Updated"

    def test_complex_graph_structure(self, projection, neo4j_service, clean_neo4j):
        """Test creating complex graph with multiple concepts and relationships."""
        # Create area concept
        area = ConceptCreated(
            aggregate_id="test_concept_013",
            concept_data={"name": "Area: Math", "explanation": "Mathematics area"},
            version=1,
        )

        # Create topic concepts
        topic1 = ConceptCreated(
            aggregate_id="test_concept_014",
            concept_data={"name": "Topic: Algebra", "explanation": "Algebra topic"},
            version=1,
        )

        topic2 = ConceptCreated(
            aggregate_id="test_concept_015",
            concept_data={"name": "Topic: Geometry", "explanation": "Geometry topic"},
            version=1,
        )

        # Project all concepts
        for event in [area, topic1, topic2]:
            assert projection.project_event(event) is True

        # Create containment relationships
        area_contains_topic1 = RelationshipCreated(
            aggregate_id="test_rel_005",
            relationship_data={
                "relationship_type": "CONTAINS",
                "from_concept_id": "test_concept_013",
                "to_concept_id": "test_concept_014",
            },
            version=1,
        )

        area_contains_topic2 = RelationshipCreated(
            aggregate_id="test_rel_006",
            relationship_data={
                "relationship_type": "CONTAINS",
                "from_concept_id": "test_concept_013",
                "to_concept_id": "test_concept_015",
            },
            version=1,
        )

        assert projection.project_event(area_contains_topic1) is True
        assert projection.project_event(area_contains_topic2) is True

        # Verify graph structure
        query = """
        MATCH (area:Concept {concept_id: $area_id})-[:CONTAINS]->(topic:Concept)
        RETURN count(topic) as topic_count
        """
        results = neo4j_service.execute_read(query, {"area_id": "test_concept_013"})
        assert results[0]["topic_count"] == 2
