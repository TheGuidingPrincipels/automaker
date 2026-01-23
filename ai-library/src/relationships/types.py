"""Relationship type definitions for content connections."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    """10 types of relationships between content items."""

    # Dependency relationships
    DEPENDS_ON = "depends_on"  # A depends on B (B is prerequisite for A)
    DEPENDENCY_OF = "dependency_of"  # Inverse of depends_on

    # Implementation relationships
    IMPLEMENTS = "implements"  # A implements concepts from B
    IMPLEMENTED_BY = "implemented_by"  # Inverse of implements

    # Reference relationships
    REFERENCES = "references"  # A references or cites B
    REFERENCED_BY = "referenced_by"  # Inverse of references

    # Hierarchy relationships
    PARENT_OF = "parent_of"  # A is parent/broader concept of B
    CHILD_OF = "child_of"  # A is child/specific instance of B

    # Similarity relationships
    SIMILAR_TO = "similar_to"  # A and B cover similar topics (bidirectional)
    RELATED_TO = "related_to"  # A and B are related (bidirectional)


# Define inverse relationships
INVERSE_RELATIONSHIPS: dict[RelationshipType, RelationshipType] = {
    RelationshipType.DEPENDS_ON: RelationshipType.DEPENDENCY_OF,
    RelationshipType.DEPENDENCY_OF: RelationshipType.DEPENDS_ON,
    RelationshipType.IMPLEMENTS: RelationshipType.IMPLEMENTED_BY,
    RelationshipType.IMPLEMENTED_BY: RelationshipType.IMPLEMENTS,
    RelationshipType.REFERENCES: RelationshipType.REFERENCED_BY,
    RelationshipType.REFERENCED_BY: RelationshipType.REFERENCES,
    RelationshipType.PARENT_OF: RelationshipType.CHILD_OF,
    RelationshipType.CHILD_OF: RelationshipType.PARENT_OF,
    RelationshipType.SIMILAR_TO: RelationshipType.SIMILAR_TO,  # Self-inverse
    RelationshipType.RELATED_TO: RelationshipType.RELATED_TO,  # Self-inverse
}

# Relationships that are symmetric (bidirectional by nature)
SYMMETRIC_RELATIONSHIPS = {
    RelationshipType.SIMILAR_TO,
    RelationshipType.RELATED_TO,
}


class RelationshipMetadata(BaseModel):
    """Metadata associated with a relationship."""

    # Common metadata
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in this relationship"
    )
    source: str = Field(
        default="manual", description="How relationship was created (manual, ai, auto)"
    )
    notes: str | None = Field(default=None, description="Optional notes/context")

    # Specific metadata based on relationship type
    # For DEPENDS_ON: what aspect depends?
    dependency_aspect: str | None = Field(
        default=None, description="What aspect of A depends on B"
    )

    # For IMPLEMENTS: what is implemented?
    implementation_details: str | None = Field(
        default=None, description="How A implements concepts from B"
    )

    # For REFERENCES: context of reference
    reference_context: str | None = Field(
        default=None, description="Context where B is referenced in A"
    )

    # For SIMILAR_TO: similarity score from vector comparison
    similarity_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Computed similarity score"
    )


class Relationship(BaseModel):
    """A relationship between two content items."""

    id: str = Field(..., description="Unique relationship ID")
    source_id: str = Field(..., description="Source content ID")
    target_id: str = Field(..., description="Target content ID")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    metadata: RelationshipMetadata = Field(
        default_factory=RelationshipMetadata, description="Relationship metadata"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = Field(default="system", description="Who created this relationship")
    updated_at: datetime | None = Field(default=None)

    @property
    def inverse_type(self) -> RelationshipType:
        """Get the inverse relationship type."""
        return INVERSE_RELATIONSHIPS[self.relationship_type]

    @property
    def is_symmetric(self) -> bool:
        """Check if this is a symmetric relationship."""
        return self.relationship_type in SYMMETRIC_RELATIONSHIPS

    def to_inverse(self) -> Relationship:
        """Create the inverse relationship.

        Returns:
            New Relationship with source/target swapped and inverse type.
        """
        return Relationship(
            id=f"{self.id}_inverse",
            source_id=self.target_id,
            target_id=self.source_id,
            relationship_type=self.inverse_type,
            metadata=self.metadata.model_copy(),
            created_at=self.created_at,
            created_by=self.created_by,
            updated_at=self.updated_at,
        )


class RelationshipAuditEntry(BaseModel):
    """Audit trail entry for relationship changes."""

    relationship_id: str
    action: str = Field(..., description="create, update, delete")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str = Field(default="system", description="Who performed the action")
    old_value: dict | None = Field(default=None)
    new_value: dict | None = Field(default=None)
    reason: str | None = Field(default=None, description="Reason for change")


class RelationshipQuery(BaseModel):
    """Query parameters for finding relationships."""

    content_id: str | None = Field(
        default=None, description="Find relationships involving this content"
    )
    relationship_type: RelationshipType | None = Field(
        default=None, description="Filter by relationship type"
    )
    source_id: str | None = Field(
        default=None, description="Find relationships from this source"
    )
    target_id: str | None = Field(
        default=None, description="Find relationships to this target"
    )
    min_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )
    include_inverses: bool = Field(
        default=True, description="Include inverse relationships in results"
    )
