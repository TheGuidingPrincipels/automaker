"""Graph traversal utilities for relationship exploration."""

from __future__ import annotations

__all__ = ["RelationshipTraversal"]

import logging
from typing import TYPE_CHECKING

from src.relationships.types import Relationship, RelationshipType

if TYPE_CHECKING:
    from src.relationships.manager import RelationshipManager

logger = logging.getLogger(__name__)


class RelationshipTraversal:
    """Utilities for traversing the pseudo-graph of content relationships."""

    def __init__(self, manager: RelationshipManager):
        """Initialize traversal utilities.

        Args:
            manager: Relationship manager to query.
        """
        self.manager = manager

    def find_dependency_chain(
        self,
        content_id: str,
        max_depth: int = 10,
    ) -> list[list[str]]:
        """Find all dependency chains starting from a content item.

        Follows DEPENDS_ON relationships to find what this content depends on,
        and what those depend on, recursively.

        Args:
            content_id: Starting content ID.
            max_depth: Maximum chain depth to prevent infinite loops.

        Returns:
            List of dependency chains, where each chain is a list of content IDs.
        """
        chains = []
        visited = set()

        def traverse(current_id: str, current_chain: list[str], depth: int) -> None:
            if depth >= max_depth:
                return
            if current_id in visited:
                return

            visited.add(current_id)
            current_chain.append(current_id)

            # Get outgoing DEPENDS_ON relationships
            deps = self.manager.get_outgoing_relationships(
                current_id, RelationshipType.DEPENDS_ON
            )

            if not deps:
                # End of chain
                if len(current_chain) > 1:
                    chains.append(current_chain.copy())
            else:
                for rel in deps:
                    traverse(rel.target_id, current_chain.copy(), depth + 1)

            visited.discard(current_id)

        traverse(content_id, [], 0)
        return chains

    def find_implementation_chain(
        self,
        content_id: str,
        max_depth: int = 10,
    ) -> list[list[str]]:
        """Find implementation chains - what implements what.

        Args:
            content_id: Starting content ID.
            max_depth: Maximum chain depth.

        Returns:
            List of implementation chains.
        """
        chains = []
        visited = set()

        def traverse(current_id: str, current_chain: list[str], depth: int) -> None:
            if depth >= max_depth or current_id in visited:
                return

            visited.add(current_id)
            current_chain.append(current_id)

            # Get IMPLEMENTS relationships
            impls = self.manager.get_outgoing_relationships(
                current_id, RelationshipType.IMPLEMENTS
            )

            if not impls:
                if len(current_chain) > 1:
                    chains.append(current_chain.copy())
            else:
                for rel in impls:
                    traverse(rel.target_id, current_chain.copy(), depth + 1)

            visited.discard(current_id)

        traverse(content_id, [], 0)
        return chains

    def get_related_content(
        self,
        content_id: str,
        depth: int = 1,
        relationship_types: list[RelationshipType] | None = None,
    ) -> dict[str, list[Relationship]]:
        """Get all content related to a given content item.

        Args:
            content_id: Starting content ID.
            depth: How many hops to traverse (1 = direct relationships only).
            relationship_types: Optional filter for relationship types.

        Returns:
            Dict mapping content IDs to the relationships that connect them.
        """
        result: dict[str, list[Relationship]] = {}
        visited = {content_id}
        to_visit = [(content_id, 0)]

        while to_visit:
            current_id, current_depth = to_visit.pop(0)

            if current_depth >= depth:
                continue

            relationships = self.manager.get_relationships_for_content(current_id)

            for rel in relationships:
                # Skip if filtering by type and doesn't match
                if relationship_types and rel.relationship_type not in relationship_types:
                    continue

                # Get the other content ID
                other_id = rel.target_id if rel.source_id == current_id else rel.source_id

                if other_id not in result:
                    result[other_id] = []
                result[other_id].append(rel)

                if other_id not in visited:
                    visited.add(other_id)
                    to_visit.append((other_id, current_depth + 1))

        return result

    def find_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 5,
        relationship_types: list[RelationshipType] | None = None,
    ) -> list[Relationship] | None:
        """Find a path of relationships between two content items.

        Args:
            from_id: Starting content ID.
            to_id: Target content ID.
            max_depth: Maximum path length.
            relationship_types: Optional filter for relationship types.

        Returns:
            List of relationships forming the path, or None if no path found.
        """
        if from_id == to_id:
            return []

        # BFS for shortest path
        visited = {from_id}
        queue = [(from_id, [])]

        while queue:
            current_id, path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            relationships = self.manager.get_relationships_for_content(current_id)

            for rel in relationships:
                if relationship_types and rel.relationship_type not in relationship_types:
                    continue

                other_id = rel.target_id if rel.source_id == current_id else rel.source_id

                if other_id == to_id:
                    return path + [rel]

                if other_id not in visited:
                    visited.add(other_id)
                    queue.append((other_id, path + [rel]))

        return None

    def find_common_dependencies(
        self,
        content_ids: list[str],
    ) -> list[str]:
        """Find content that multiple items all depend on.

        Args:
            content_ids: List of content IDs to check.

        Returns:
            List of content IDs that all provided content depends on.
        """
        if not content_ids:
            return []

        # Get dependencies for each content
        dependency_sets = []
        for content_id in content_ids:
            deps = self.manager.get_outgoing_relationships(
                content_id, RelationshipType.DEPENDS_ON
            )
            dep_ids = {rel.target_id for rel in deps}
            dependency_sets.append(dep_ids)

        # Find intersection
        if not dependency_sets:
            return []

        common = dependency_sets[0]
        for dep_set in dependency_sets[1:]:
            common = common.intersection(dep_set)

        return list(common)

    def get_dependency_tree(
        self,
        content_id: str,
        max_depth: int = 5,
    ) -> dict:
        """Build a dependency tree starting from content.

        Args:
            content_id: Root content ID.
            max_depth: Maximum tree depth.

        Returns:
            Nested dict representing dependency tree.
        """

        def build_tree(current_id: str, depth: int, visited: set) -> dict:
            if depth >= max_depth or current_id in visited:
                return {"id": current_id, "children": [], "truncated": True}

            visited.add(current_id)

            deps = self.manager.get_outgoing_relationships(
                current_id, RelationshipType.DEPENDS_ON
            )

            children = []
            for rel in deps:
                child_tree = build_tree(rel.target_id, depth + 1, visited.copy())
                child_tree["relationship"] = rel.model_dump()
                children.append(child_tree)

            return {
                "id": current_id,
                "children": children,
                "truncated": False,
            }

        return build_tree(content_id, 0, set())

    def find_orphans(self, all_content_ids: set[str]) -> set[str]:
        """Find content with no relationships.

        Args:
            all_content_ids: Set of all known content IDs.

        Returns:
            Set of content IDs that have no relationships.
        """
        content_with_relationships = self.manager.get_content_ids_with_relationships()
        return all_content_ids - content_with_relationships

    def get_relationship_stats_for_content(self, content_id: str) -> dict:
        """Get relationship statistics for a content item.

        Args:
            content_id: Content ID to analyze.

        Returns:
            Dict with relationship stats.
        """
        all_rels = self.manager.get_relationships_for_content(content_id)
        outgoing = self.manager.get_outgoing_relationships(content_id)
        incoming = self.manager.get_incoming_relationships(content_id)

        # Count by type
        type_counts = {}
        for rel in all_rels:
            rel_type = rel.relationship_type.value
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

        return {
            "total_relationships": len(all_rels),
            "outgoing": len(outgoing),
            "incoming": len(incoming),
            "by_type": type_counts,
        }
