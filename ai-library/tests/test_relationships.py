"""Tests for relationship management."""

import pytest

from src.relationships.types import (
    INVERSE_RELATIONSHIPS,
    SYMMETRIC_RELATIONSHIPS,
    Relationship,
    RelationshipMetadata,
    RelationshipQuery,
    RelationshipType,
)
from src.relationships.manager import RelationshipManager
from src.relationships.traversal import RelationshipTraversal


class TestRelationshipType:
    """Tests for relationship type definitions."""

    def test_all_types_have_inverses(self):
        """Test that all relationship types have inverse mappings."""
        for rel_type in RelationshipType:
            assert rel_type in INVERSE_RELATIONSHIPS

    def test_inverse_of_inverse(self):
        """Test that inverse of inverse returns original."""
        for rel_type in RelationshipType:
            inverse = INVERSE_RELATIONSHIPS[rel_type]
            inverse_of_inverse = INVERSE_RELATIONSHIPS[inverse]
            assert inverse_of_inverse == rel_type

    def test_symmetric_relationships_are_self_inverse(self):
        """Test that symmetric relationships are their own inverse."""
        for rel_type in SYMMETRIC_RELATIONSHIPS:
            assert INVERSE_RELATIONSHIPS[rel_type] == rel_type


class TestRelationship:
    """Tests for Relationship model."""

    def test_create_relationship(self):
        """Test creating a relationship."""
        rel = Relationship(
            id="rel-1",
            source_id="content-a",
            target_id="content-b",
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        assert rel.source_id == "content-a"
        assert rel.target_id == "content-b"
        assert rel.relationship_type == RelationshipType.DEPENDS_ON

    def test_inverse_type(self):
        """Test getting inverse relationship type."""
        rel = Relationship(
            id="rel-1",
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        assert rel.inverse_type == RelationshipType.DEPENDENCY_OF

    def test_is_symmetric(self):
        """Test symmetric check."""
        symmetric_rel = Relationship(
            id="rel-1",
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.SIMILAR_TO,
        )
        assert symmetric_rel.is_symmetric is True

        non_symmetric_rel = Relationship(
            id="rel-2",
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        assert non_symmetric_rel.is_symmetric is False

    def test_to_inverse(self):
        """Test creating inverse relationship."""
        original = Relationship(
            id="rel-1",
            source_id="content-a",
            target_id="content-b",
            relationship_type=RelationshipType.IMPLEMENTS,
            metadata=RelationshipMetadata(confidence=0.9),
        )

        inverse = original.to_inverse()

        assert inverse.source_id == "content-b"
        assert inverse.target_id == "content-a"
        assert inverse.relationship_type == RelationshipType.IMPLEMENTED_BY
        assert inverse.metadata.confidence == 0.9


class TestRelationshipManager:
    """Tests for RelationshipManager."""

    @pytest.fixture
    def manager(self):
        """Create a relationship manager."""
        return RelationshipManager()

    def test_create_relationship(self, manager):
        """Test creating a relationship."""
        rel = manager.create_relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.REFERENCES,
        )

        assert rel.source_id == "a"
        assert rel.target_id == "b"
        assert rel.relationship_type == RelationshipType.REFERENCES

    def test_create_relationship_creates_inverse(self, manager):
        """Test that creating a relationship also creates inverse."""
        rel = manager.create_relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        # Query for inverse
        incoming = manager.get_incoming_relationships(
            "a", RelationshipType.DEPENDENCY_OF
        )
        assert len(incoming) == 1
        assert incoming[0].source_id == "b"

    def test_create_duplicate_raises(self, manager):
        """Test that creating duplicate relationship raises error."""
        manager.create_relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.REFERENCES,
        )

        with pytest.raises(ValueError, match="already exists"):
            manager.create_relationship(
                source_id="a",
                target_id="b",
                relationship_type=RelationshipType.REFERENCES,
            )

    def test_create_self_reference_raises(self, manager):
        """Test that self-referential relationship raises error."""
        with pytest.raises(ValueError, match="Cannot create relationship to self"):
            manager.create_relationship(
                source_id="a",
                target_id="a",
                relationship_type=RelationshipType.SIMILAR_TO,
            )

    def test_get_relationship(self, manager):
        """Test getting a relationship by ID."""
        rel = manager.create_relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.REFERENCES,
        )

        retrieved = manager.get_relationship(rel.id)
        assert retrieved is not None
        assert retrieved.id == rel.id

    def test_update_relationship(self, manager):
        """Test updating a relationship."""
        rel = manager.create_relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.REFERENCES,
            metadata=RelationshipMetadata(confidence=0.5),
        )

        updated = manager.update_relationship(
            rel.id,
            metadata=RelationshipMetadata(confidence=0.9),
            reason="Increased confidence",
        )

        assert updated is not None
        assert updated.metadata.confidence == 0.9
        assert updated.updated_at is not None

    def test_delete_relationship(self, manager):
        """Test deleting a relationship."""
        rel = manager.create_relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        result = manager.delete_relationship(rel.id, reason="No longer needed")
        assert result is True

        # Should be gone
        assert manager.get_relationship(rel.id) is None

        # Inverse should also be gone
        incoming = manager.get_incoming_relationships(
            "a", RelationshipType.DEPENDENCY_OF
        )
        assert len(incoming) == 0

    def test_query_relationships(self, manager):
        """Test querying relationships."""
        manager.create_relationship("a", "b", RelationshipType.REFERENCES)
        manager.create_relationship("a", "c", RelationshipType.DEPENDS_ON)
        manager.create_relationship("b", "c", RelationshipType.REFERENCES)

        # Query by content ID
        query = RelationshipQuery(content_id="a")
        results = manager.query_relationships(query)
        assert len(results) >= 2  # At least 2 outgoing from 'a'

        # Query by type
        query = RelationshipQuery(relationship_type=RelationshipType.REFERENCES)
        results = manager.query_relationships(query)
        # Should find references (excluding inverses)
        ref_count = len([r for r in results if not r.id.endswith("_inverse")])
        assert ref_count == 2

    def test_get_outgoing_relationships(self, manager):
        """Test getting outgoing relationships."""
        manager.create_relationship("a", "b", RelationshipType.REFERENCES)
        manager.create_relationship("a", "c", RelationshipType.DEPENDS_ON)
        manager.create_relationship("b", "a", RelationshipType.REFERENCES)

        outgoing = manager.get_outgoing_relationships("a")
        assert len(outgoing) == 2

    def test_get_incoming_relationships(self, manager):
        """Test getting incoming relationships."""
        manager.create_relationship("b", "a", RelationshipType.REFERENCES)
        manager.create_relationship("c", "a", RelationshipType.DEPENDS_ON)

        incoming = manager.get_incoming_relationships("a")
        assert len(incoming) == 2

    def test_audit_trail(self, manager):
        """Test audit trail tracking."""
        rel = manager.create_relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.REFERENCES,
        )

        manager.update_relationship(
            rel.id,
            metadata=RelationshipMetadata(confidence=0.9),
        )

        manager.delete_relationship(rel.id)

        audit = manager.get_audit_trail(rel.id)
        assert len(audit) == 3
        assert audit[0].action == "delete"
        assert audit[1].action == "update"
        assert audit[2].action == "create"

    def test_get_stats(self, manager):
        """Test getting relationship statistics."""
        manager.create_relationship("a", "b", RelationshipType.REFERENCES)
        manager.create_relationship("a", "c", RelationshipType.DEPENDS_ON)

        stats = manager.get_stats()

        assert stats["total_relationships"] == 2
        assert "references" in stats["by_type"]
        assert "depends_on" in stats["by_type"]


class TestRelationshipTraversal:
    """Tests for relationship traversal utilities."""

    @pytest.fixture
    def manager_with_data(self):
        """Create a manager with test data."""
        manager = RelationshipManager()

        # Create a dependency chain: a -> b -> c -> d
        manager.create_relationship("a", "b", RelationshipType.DEPENDS_ON)
        manager.create_relationship("b", "c", RelationshipType.DEPENDS_ON)
        manager.create_relationship("c", "d", RelationshipType.DEPENDS_ON)

        # Create implementation chain: x -> y -> z
        manager.create_relationship("x", "y", RelationshipType.IMPLEMENTS)
        manager.create_relationship("y", "z", RelationshipType.IMPLEMENTS)

        # Create some related content
        manager.create_relationship("a", "x", RelationshipType.RELATED_TO)

        return manager

    def test_find_dependency_chain(self, manager_with_data):
        """Test finding dependency chains."""
        traversal = RelationshipTraversal(manager_with_data)

        chains = traversal.find_dependency_chain("a")

        # Should find chain: a -> b -> c -> d
        assert len(chains) == 1
        assert chains[0] == ["a", "b", "c", "d"]

    def test_find_implementation_chain(self, manager_with_data):
        """Test finding implementation chains."""
        traversal = RelationshipTraversal(manager_with_data)

        chains = traversal.find_implementation_chain("x")

        assert len(chains) == 1
        assert chains[0] == ["x", "y", "z"]

    def test_get_related_content_depth_1(self, manager_with_data):
        """Test getting related content at depth 1."""
        traversal = RelationshipTraversal(manager_with_data)

        related = traversal.get_related_content("a", depth=1)

        # 'a' is directly related to 'b' (depends_on) and 'x' (related_to)
        assert "b" in related
        assert "x" in related

    def test_get_related_content_depth_2(self, manager_with_data):
        """Test getting related content at depth 2."""
        traversal = RelationshipTraversal(manager_with_data)

        related = traversal.get_related_content("a", depth=2)

        # Should include direct relations and their relations
        assert "b" in related  # direct
        assert "c" in related  # through b
        assert "x" in related  # direct
        assert "y" in related  # through x

    def test_find_path(self, manager_with_data):
        """Test finding path between two content items."""
        traversal = RelationshipTraversal(manager_with_data)

        path = traversal.find_path("a", "d")

        assert path is not None
        assert len(path) == 3  # a->b, b->c, c->d

    def test_find_path_no_connection(self, manager_with_data):
        """Test finding path when no connection exists."""
        traversal = RelationshipTraversal(manager_with_data)

        path = traversal.find_path("d", "z")  # No path between these

        assert path is None

    def test_find_common_dependencies(self, manager_with_data):
        """Test finding common dependencies."""
        manager = manager_with_data

        # Add more dependencies for common dependency test
        manager.create_relationship("p", "shared", RelationshipType.DEPENDS_ON)
        manager.create_relationship("q", "shared", RelationshipType.DEPENDS_ON)

        traversal = RelationshipTraversal(manager)

        common = traversal.find_common_dependencies(["p", "q"])

        assert "shared" in common

    def test_get_dependency_tree(self, manager_with_data):
        """Test building dependency tree."""
        traversal = RelationshipTraversal(manager_with_data)

        tree = traversal.get_dependency_tree("a", max_depth=3)

        assert tree["id"] == "a"
        assert len(tree["children"]) == 1
        assert tree["children"][0]["id"] == "b"

    def test_find_orphans(self, manager_with_data):
        """Test finding orphan content."""
        traversal = RelationshipTraversal(manager_with_data)

        all_content = {"a", "b", "c", "d", "x", "y", "z", "orphan1", "orphan2"}
        orphans = traversal.find_orphans(all_content)

        assert "orphan1" in orphans
        assert "orphan2" in orphans
        assert "a" not in orphans

    def test_relationship_stats_for_content(self, manager_with_data):
        """Test getting relationship stats for specific content."""
        traversal = RelationshipTraversal(manager_with_data)

        stats = traversal.get_relationship_stats_for_content("a")

        assert stats["total_relationships"] > 0
        assert "outgoing" in stats
        assert "incoming" in stats
        assert "by_type" in stats
