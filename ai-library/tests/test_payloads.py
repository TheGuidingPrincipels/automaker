# tests/test_payloads.py
"""Tests for payload schema."""

import pytest
from datetime import datetime

from src.payloads.schema import (
    ContentType,
    ClassificationTier,
    RelationshipType,
    TaxonomyPath,
    Relationship,
    ClassificationResult,
    Provenance,
    AuditEntry,
    ContentPayload,
)


class TestTaxonomyPath:
    """Tests for TaxonomyPath model."""

    def test_create_empty_taxonomy(self):
        """Create empty taxonomy path."""
        taxonomy = TaxonomyPath()

        assert taxonomy.level1 == ""
        assert taxonomy.level2 == ""
        assert taxonomy.level3 is None
        assert taxonomy.level4 is None
        assert taxonomy.full_path == ""

    def test_from_path_string_two_levels(self):
        """Parse path string with two levels."""
        taxonomy = TaxonomyPath.from_path_string("Agent-Systems/Research")

        assert taxonomy.level1 == "Agent-Systems"
        assert taxonomy.level2 == "Research"
        assert taxonomy.level3 is None
        assert taxonomy.full_path == "Agent-Systems/Research"

    def test_from_path_string_four_levels(self):
        """Parse path string with four levels."""
        taxonomy = TaxonomyPath.from_path_string("Blueprints/Dev/Tools/CLI")

        assert taxonomy.level1 == "Blueprints"
        assert taxonomy.level2 == "Dev"
        assert taxonomy.level3 == "Tools"
        assert taxonomy.level4 == "CLI"
        assert taxonomy.full_path == "Blueprints/Dev/Tools/CLI"

    def test_from_file_path_strips_library(self):
        """From file path strips library prefix and .md extension."""
        taxonomy = TaxonomyPath.from_file_path("library/tech/authentication.md")

        assert taxonomy.level1 == "tech"
        assert taxonomy.level2 == "authentication"
        assert taxonomy.full_path == "tech/authentication"


class TestRelationship:
    """Tests for Relationship model."""

    def test_create_relationship(self):
        """Create a relationship."""
        rel = Relationship(
            target_id="uuid-123",
            relationship_type=RelationshipType.RELATES_TO,
        )

        assert rel.target_id == "uuid-123"
        assert rel.relationship_type == RelationshipType.RELATES_TO
        assert rel.metadata == {}
        assert rel.created_by == "system"

    def test_relationship_with_metadata(self):
        """Create relationship with metadata."""
        rel = Relationship(
            target_id="uuid-456",
            relationship_type=RelationshipType.IMPLEMENTS,
            metadata={"version": "1.0", "complete": True},
        )

        assert rel.metadata["version"] == "1.0"
        assert rel.metadata["complete"] is True


class TestClassificationResult:
    """Tests for ClassificationResult model."""

    def test_default_classification_is_none(self):
        """Default classification has NONE tier."""
        result = ClassificationResult()

        assert result.confidence == 0.0
        assert result.tier_used == ClassificationTier.NONE
        assert result.reasoning is None
        assert result.alternatives == []

    def test_classification_with_llm_tier(self):
        """Classification with LLM tier."""
        result = ClassificationResult(
            taxonomy_path=TaxonomyPath.from_path_string("Tech/Auth"),
            confidence=0.85,
            tier_used=ClassificationTier.LLM,
            reasoning="Content discusses authentication patterns",
        )

        assert result.confidence == 0.85
        assert result.tier_used == ClassificationTier.LLM
        assert result.reasoning is not None


class TestProvenance:
    """Tests for Provenance model."""

    def test_create_basic_provenance(self):
        """Create basic provenance."""
        prov = Provenance(source_file="input/notes.md")

        assert prov.source_file == "input/notes.md"
        assert prov.source_url is None
        assert prov.extraction_method == "manual"
        assert prov.version == 1

    def test_provenance_with_session(self):
        """Provenance with session info."""
        prov = Provenance(
            source_file="input/docs.md",
            source_session_id="session-123",
            extraction_method="automated",
            original_heading_path=["Introduction", "Overview"],
        )

        assert prov.source_session_id == "session-123"
        assert prov.extraction_method == "automated"
        assert len(prov.original_heading_path) == 2


class TestAuditEntry:
    """Tests for AuditEntry model."""

    def test_create_audit_entry(self):
        """Create basic audit entry."""
        entry = AuditEntry(action="created")

        assert entry.action == "created"
        assert entry.user == "system"
        assert entry.details == {}
        assert entry.previous_state is None

    def test_audit_entry_with_details(self):
        """Audit entry with details."""
        entry = AuditEntry(
            action="updated",
            user="ai-classifier",
            details={"field": "taxonomy", "old_value": "General"},
        )

        assert entry.details["field"] == "taxonomy"


class TestContentPayload:
    """Tests for ContentPayload model."""

    def test_create_basic_payload(self):
        """Create basic content payload using factory method."""
        payload = ContentPayload.create_basic(
            content_id="uuid-123",
            file_path="tech/auth.md",
            section="JWT Tokens",
            chunk_index=0,
            chunk_total=3,
            content_hash="abc123",
        )

        assert payload.content_id == "uuid-123"
        assert payload.file_path == "tech/auth.md"
        assert payload.section == "JWT Tokens"
        assert payload.chunk_index == 0
        assert payload.chunk_total == 3
        assert payload.content_type == ContentType.GENERAL
        # Should have created audit entry
        assert len(payload.audit_trail) == 1
        assert payload.audit_trail[0].action == "created"

    def test_payload_taxonomy_from_file_path(self):
        """Payload derives taxonomy from file path."""
        payload = ContentPayload.create_basic(
            content_id="uuid-456",
            file_path="agent-systems/research/market.md",
        )

        assert payload.taxonomy.level1 == "agent-systems"
        assert payload.taxonomy.level2 == "research"

    def test_add_relationship(self):
        """Add relationship to payload."""
        payload = ContentPayload.create_basic(
            content_id="uuid-789",
            file_path="tech/db.md",
        )

        payload.add_relationship(
            target_id="uuid-abc",
            rel_type=RelationshipType.DEPENDS_ON,
            metadata={"reason": "Required for auth"},
        )

        assert len(payload.relationships) == 1
        assert payload.relationships[0].target_id == "uuid-abc"
        assert payload.relationships[0].relationship_type == RelationshipType.DEPENDS_ON
        # Should have audit entry for relationship
        assert any(e.action == "relationship_added" for e in payload.audit_trail)

    def test_get_relationships_by_type(self):
        """Get relationships filtered by type."""
        payload = ContentPayload.create_basic(
            content_id="uuid-test",
            file_path="test.md",
        )

        payload.add_relationship("id1", RelationshipType.DEPENDS_ON)
        payload.add_relationship("id2", RelationshipType.RELATES_TO)
        payload.add_relationship("id3", RelationshipType.DEPENDS_ON)

        deps = payload.get_relationships_by_type(RelationshipType.DEPENDS_ON)

        assert len(deps) == 2
        assert all(r.relationship_type == RelationshipType.DEPENDS_ON for r in deps)

    def test_to_qdrant_payload(self):
        """Convert payload to Qdrant dict."""
        payload = ContentPayload.create_basic(
            content_id="uuid-qdrant",
            file_path="test/file.md",
            section="Test Section",
        )

        qdrant_dict = payload.to_qdrant_payload()

        assert isinstance(qdrant_dict, dict)
        assert qdrant_dict["content_id"] == "uuid-qdrant"
        assert qdrant_dict["file_path"] == "test/file.md"
        assert qdrant_dict["section"] == "Test Section"
        assert "taxonomy" in qdrant_dict
        assert "audit_trail" in qdrant_dict

    def test_from_qdrant_payload(self):
        """Reconstruct payload from Qdrant dict."""
        original = ContentPayload.create_basic(
            content_id="uuid-round-trip",
            file_path="round/trip.md",
            chunk_index=2,
            chunk_total=5,
        )

        qdrant_dict = original.to_qdrant_payload()
        reconstructed = ContentPayload.from_qdrant_payload(qdrant_dict)

        assert reconstructed.content_id == original.content_id
        assert reconstructed.file_path == original.file_path
        assert reconstructed.chunk_index == original.chunk_index
        assert reconstructed.chunk_total == original.chunk_total

    def test_phase_3b_fields_default_empty(self):
        """Phase 3B fields have sensible defaults."""
        payload = ContentPayload.create_basic(
            content_id="uuid-defaults",
            file_path="default.md",
        )

        # Classification should be at defaults
        assert payload.classification.confidence == 0.0
        assert payload.classification.tier_used == ClassificationTier.NONE

        # Relationships should be empty
        assert payload.relationships == []
