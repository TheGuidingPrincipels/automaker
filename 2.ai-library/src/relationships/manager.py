"""Relationship manager for CRUD operations and tracking."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.relationships.types import (
    SYMMETRIC_RELATIONSHIPS,
    Relationship,
    RelationshipAuditEntry,
    RelationshipMetadata,
    RelationshipQuery,
    RelationshipType,
)

if TYPE_CHECKING:
    from src.vector.store import QdrantVectorStore

logger = logging.getLogger(__name__)


class RelationshipManager:
    """Manages content relationships with bidirectional tracking and audit trail."""

    def __init__(self, vector_store: QdrantVectorStore | None = None):
        """Initialize relationship manager.

        Args:
            vector_store: Optional vector store for relationship storage.
        """
        self._vector_store = vector_store
        if vector_store is None:
            logger.warning(
                "RelationshipManager initialized without vector_store - "
                "relationships will not persist beyond this session"
            )

        # In-memory storage (for testing/development)
        # In production, these are stored in the vector store payload
        self._relationships: dict[str, Relationship] = {}
        self._audit_trail: list[RelationshipAuditEntry] = []

        # Index for fast lookups
        self._source_index: dict[str, set[str]] = {}  # source_id -> relationship_ids
        self._target_index: dict[str, set[str]] = {}  # target_id -> relationship_ids
        self._content_index: dict[str, set[str]] = {}  # content_id -> relationship_ids

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        metadata: RelationshipMetadata | None = None,
        created_by: str = "system",
    ) -> Relationship:
        """Create a new relationship between content items.

        Args:
            source_id: Source content ID.
            target_id: Target content ID.
            relationship_type: Type of relationship.
            metadata: Optional relationship metadata.
            created_by: Who is creating this relationship.

        Returns:
            Created Relationship.

        Raises:
            ValueError: If relationship already exists or IDs are invalid.
        """
        # Validate not self-referential
        if source_id == target_id:
            raise ValueError("Cannot create relationship to self")

        # Check for duplicate
        existing = self._find_existing(source_id, target_id, relationship_type)
        if existing:
            raise ValueError(
                f"Relationship already exists: {existing.id}"
            )

        # Create relationship
        relationship_id = str(uuid.uuid4())
        relationship = Relationship(
            id=relationship_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            metadata=metadata or RelationshipMetadata(),
            created_at=datetime.now(UTC),
            created_by=created_by,
        )

        # Store relationship
        self._store_relationship(relationship)

        # For non-symmetric relationships, create inverse automatically
        if relationship_type not in SYMMETRIC_RELATIONSHIPS:
            inverse = relationship.to_inverse()
            self._store_relationship(inverse)

        # Audit trail
        self._add_audit_entry(
            relationship_id=relationship_id,
            action="create",
            actor=created_by,
            new_value=relationship.model_dump(),
        )

        logger.info(
            "Created relationship %s: %s -[%s]-> %s",
            relationship_id,
            source_id,
            relationship_type.value,
            target_id,
        )

        return relationship

    def _store_relationship(self, relationship: Relationship) -> None:
        """Store relationship and update indexes."""
        self._relationships[relationship.id] = relationship

        # Update indexes
        if relationship.source_id not in self._source_index:
            self._source_index[relationship.source_id] = set()
        self._source_index[relationship.source_id].add(relationship.id)

        if relationship.target_id not in self._target_index:
            self._target_index[relationship.target_id] = set()
        self._target_index[relationship.target_id].add(relationship.id)

        # Content index (both source and target)
        for content_id in [relationship.source_id, relationship.target_id]:
            if content_id not in self._content_index:
                self._content_index[content_id] = set()
            self._content_index[content_id].add(relationship.id)

    def _find_existing(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
    ) -> Relationship | None:
        """Find an existing relationship matching the criteria."""
        source_rels = self._source_index.get(source_id, set())
        for rel_id in source_rels:
            rel = self._relationships.get(rel_id)
            if (
                rel
                and rel.target_id == target_id
                and rel.relationship_type == relationship_type
            ):
                return rel
        return None

    def get_relationship(self, relationship_id: str) -> Relationship | None:
        """Get a relationship by ID."""
        return self._relationships.get(relationship_id)

    def update_relationship(
        self,
        relationship_id: str,
        metadata: RelationshipMetadata | None = None,
        updated_by: str = "system",
        reason: str | None = None,
    ) -> Relationship | None:
        """Update a relationship's metadata.

        Args:
            relationship_id: ID of relationship to update.
            metadata: New metadata (optional, updates if provided).
            updated_by: Who is updating.
            reason: Reason for update.

        Returns:
            Updated Relationship or None if not found.
        """
        relationship = self._relationships.get(relationship_id)
        if relationship is None:
            return None

        old_value = relationship.model_dump()

        if metadata is not None:
            relationship.metadata = metadata
        relationship.updated_at = datetime.now(UTC)

        # Audit trail
        self._add_audit_entry(
            relationship_id=relationship_id,
            action="update",
            actor=updated_by,
            old_value=old_value,
            new_value=relationship.model_dump(),
            reason=reason,
        )

        logger.info("Updated relationship %s", relationship_id)
        return relationship

    def delete_relationship(
        self,
        relationship_id: str,
        deleted_by: str = "system",
        reason: str | None = None,
    ) -> bool:
        """Delete a relationship.

        Args:
            relationship_id: ID of relationship to delete.
            deleted_by: Who is deleting.
            reason: Reason for deletion.

        Returns:
            True if deleted, False if not found.
        """
        relationship = self._relationships.get(relationship_id)
        if relationship is None:
            return False

        # Audit trail
        self._add_audit_entry(
            relationship_id=relationship_id,
            action="delete",
            actor=deleted_by,
            old_value=relationship.model_dump(),
            reason=reason,
        )

        # Remove from indexes
        self._source_index.get(relationship.source_id, set()).discard(relationship_id)
        self._target_index.get(relationship.target_id, set()).discard(relationship_id)
        self._content_index.get(relationship.source_id, set()).discard(relationship_id)
        self._content_index.get(relationship.target_id, set()).discard(relationship_id)

        # Remove relationship
        del self._relationships[relationship_id]

        # Also remove inverse if exists
        inverse_id = f"{relationship_id}_inverse"
        if inverse_id in self._relationships:
            inverse = self._relationships[inverse_id]
            self._source_index.get(inverse.source_id, set()).discard(inverse_id)
            self._target_index.get(inverse.target_id, set()).discard(inverse_id)
            self._content_index.get(inverse.source_id, set()).discard(inverse_id)
            self._content_index.get(inverse.target_id, set()).discard(inverse_id)
            del self._relationships[inverse_id]

        logger.info("Deleted relationship %s", relationship_id)
        return True

    def query_relationships(self, query: RelationshipQuery) -> list[Relationship]:
        """Query relationships based on criteria.

        Args:
            query: Query parameters.

        Returns:
            List of matching relationships.
        """
        results = []

        # Determine which relationships to check
        if query.content_id:
            relationship_ids = self._content_index.get(query.content_id, set())
        elif query.source_id:
            relationship_ids = self._source_index.get(query.source_id, set())
        elif query.target_id:
            relationship_ids = self._target_index.get(query.target_id, set())
        else:
            relationship_ids = set(self._relationships.keys())

        for rel_id in relationship_ids:
            rel = self._relationships.get(rel_id)
            if rel is None:
                continue

            # Apply filters
            if query.relationship_type and rel.relationship_type != query.relationship_type:
                continue

            if query.source_id and rel.source_id != query.source_id:
                continue

            if query.target_id and rel.target_id != query.target_id:
                continue

            if rel.metadata.confidence < query.min_confidence:
                continue

            # Skip inverses if not requested
            if not query.include_inverses and rel.id.endswith("_inverse"):
                continue

            results.append(rel)

        return results

    def get_relationships_for_content(
        self,
        content_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[Relationship]:
        """Get all relationships involving a content item.

        Args:
            content_id: Content ID to find relationships for.
            relationship_type: Optional filter by type.

        Returns:
            List of relationships involving this content.
        """
        query = RelationshipQuery(
            content_id=content_id,
            relationship_type=relationship_type,
        )
        return self.query_relationships(query)

    def get_outgoing_relationships(
        self,
        source_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[Relationship]:
        """Get relationships where content is the source.

        Args:
            source_id: Source content ID.
            relationship_type: Optional filter by type.

        Returns:
            List of outgoing relationships.
        """
        query = RelationshipQuery(
            source_id=source_id,
            relationship_type=relationship_type,
            include_inverses=False,
        )
        return self.query_relationships(query)

    def get_incoming_relationships(
        self,
        target_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[Relationship]:
        """Get relationships where content is the target.

        Args:
            target_id: Target content ID.
            relationship_type: Optional filter by type.

        Returns:
            List of incoming relationships.
        """
        query = RelationshipQuery(
            target_id=target_id,
            relationship_type=relationship_type,
            include_inverses=True,  # Include auto-created inverses for incoming queries
        )
        return self.query_relationships(query)

    def _add_audit_entry(
        self,
        relationship_id: str,
        action: str,
        actor: str,
        old_value: dict | None = None,
        new_value: dict | None = None,
        reason: str | None = None,
    ) -> None:
        """Add an audit trail entry."""
        entry = RelationshipAuditEntry(
            relationship_id=relationship_id,
            action=action,
            actor=actor,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
        self._audit_trail.append(entry)

    def get_audit_trail(
        self,
        relationship_id: str | None = None,
        limit: int = 100,
    ) -> list[RelationshipAuditEntry]:
        """Get audit trail entries.

        Args:
            relationship_id: Optional filter by relationship ID.
            limit: Maximum entries to return.

        Returns:
            List of audit entries, most recent first.
        """
        entries = self._audit_trail
        if relationship_id:
            entries = [e for e in entries if e.relationship_id == relationship_id]

        # Sort by timestamp descending
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def get_content_ids_with_relationships(self) -> set[str]:
        """Get IDs of all content that has relationships.

        Returns:
            Set of content IDs that have at least one relationship.
        """
        return set(self._content_index.keys())

    @property
    def relationship_count(self) -> int:
        """Total number of relationships (excluding inverses)."""
        return sum(1 for r in self._relationships.values() if not r.id.endswith("_inverse"))

    def get_stats(self) -> dict:
        """Get relationship statistics.

        Returns:
            Dictionary with relationship stats.
        """
        type_counts = {}
        for rel in self._relationships.values():
            if rel.id.endswith("_inverse"):
                continue
            rel_type = rel.relationship_type.value
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

        return {
            "total_relationships": self.relationship_count,
            "by_type": type_counts,
            "content_with_relationships": len(self._content_index),
            "audit_entries": len(self._audit_trail),
        }
