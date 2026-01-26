"""
Neo4j Projection for Event Sourcing.

Projects events from the event store to Neo4j graph database,
creating concept nodes and relationships.
"""

import json
import logging
from datetime import UTC, datetime

from neo4j.exceptions import DatabaseError, ServiceUnavailable

from models.events import Event
from projections.base_projection import BaseProjection
from services.neo4j_service import Neo4jService


logger = logging.getLogger(__name__)


class Neo4jProjection(BaseProjection):
    """
    Projects events to Neo4j graph database.

    Transforms event store events into graph nodes and relationships,
    maintaining concept hierarchy and connections.
    """

    def __init__(self, neo4j_service: Neo4jService) -> None:
        """
        Initialize Neo4j projection.

        Args:
            neo4j_service: Neo4j service instance for database operations
        """
        self.neo4j = neo4j_service
        self.projection_name = "neo4j"

    def get_projection_name(self) -> str:
        """Get the name of this projection."""
        return self.projection_name

    def project_event(self, event: Event) -> bool:
        """
        Project an event to Neo4j.

        Routes events to appropriate handlers based on event type.

        Args:
            event: The event to project

        Returns:
            True if projection successful, False otherwise
        """
        try:
            # Route to appropriate handler based on event type
            handler_map = {
                "ConceptCreated": self._handle_concept_created,
                "ConceptUpdated": self._handle_concept_updated,
                "ConceptDeleted": self._handle_concept_deleted,
                "ConceptTauUpdated": self._handle_concept_tau_updated,
                "RelationshipCreated": self._handle_relationship_created,
                "RelationshipDeleted": self._handle_relationship_deleted,
            }

            handler = handler_map.get(event.event_type)
            if not handler:
                logger.warning(
                    f"No handler found for event type: {event.event_type}. "
                    f"Event ID: {event.event_id}"
                )
                return False

            # Execute handler
            success = handler(event)

            if success:
                logger.info(
                    f"Successfully projected {event.event_type} event. "
                    f"Event ID: {event.event_id}, Aggregate: {event.aggregate_id}"
                )
            else:
                logger.warning(
                    f"Failed to project {event.event_type} event. "
                    f"Event ID: {event.event_id}, Aggregate: {event.aggregate_id}"
                )

            return success

        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable while projecting event {event.event_id}: {e}")
            return False

        except DatabaseError as e:
            logger.error(f"Database error while projecting event {event.event_id}: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error projecting event {event.event_id}: {e}", exc_info=True)
            return False

    def _handle_concept_created(self, event: Event) -> bool:
        """
        Handle ConceptCreated event.

        Creates a new Concept node in Neo4j with all properties from event_data.
        Uses MERGE for idempotency.

        Args:
            event: ConceptCreated event

        Returns:
            True if successful, False otherwise
        """
        try:
            concept_id = event.aggregate_id
            event_data = event.event_data

            # Extract properties from event_data
            properties = {
                "concept_id": concept_id,
                "name": event_data.get("name", ""),
                "explanation": event_data.get("explanation", ""),
                "confidence_score": event_data.get("confidence_score", 0.0),
                "created_at": event.created_at.isoformat(),
                "last_modified": event.created_at.isoformat(),
            }

            # Optional properties
            if "area" in event_data:
                properties["area"] = event_data["area"]
            if "topic" in event_data:
                properties["topic"] = event_data["topic"]
            if "subtopic" in event_data:
                properties["subtopic"] = event_data["subtopic"]
            if "examples" in event_data:
                properties["examples"] = event_data["examples"]
            if "prerequisites" in event_data:
                properties["prerequisites"] = event_data["prerequisites"]

            # NEW: Add source_urls (serialized to JSON string for Neo4j compatibility)
            # Neo4j cannot store lists of dictionaries as properties (only primitives or lists of primitives)
            # Issue #1 fix: Serialize source_urls list of dicts to JSON string
            if "source_urls" in event_data:
                properties["source_urls"] = json.dumps(event_data["source_urls"])

            # Use MERGE for idempotency - won't create duplicates
            query = """
            MERGE (c:Concept {concept_id: $concept_id})
            SET c += $properties
            """

            result = self.neo4j.execute_write(
                query, parameters={"concept_id": concept_id, "properties": properties}
            )

            # Check if node was created or updated
            nodes_created = result.get("nodes_created", 0)
            properties_set = result.get("properties_set", 0)

            logger.debug(
                f"ConceptCreated projection: {nodes_created} nodes created, "
                f"{properties_set} properties set for concept {concept_id}"
            )

            return True

        except Exception as e:
            logger.error(
                f"Error handling ConceptCreated event {event.event_id}: {e}", exc_info=True
            )
            return False

    def _handle_concept_updated(self, event: Event) -> bool:
        """
        Handle ConceptUpdated event.

        Updates properties of an existing Concept node.

        Args:
            event: ConceptUpdated event

        Returns:
            True if successful, False otherwise
        """
        try:
            concept_id = event.aggregate_id
            updates = event.event_data.copy()

            # Add updated timestamp (timezone-aware UTC)
            updates["last_modified"] = datetime.now(UTC).isoformat()

            # Serialize source_urls if present (same as in _handle_concept_created)
            # Neo4j cannot store lists of dictionaries as properties
            if "source_urls" in updates:
                updates["source_urls"] = json.dumps(updates["source_urls"])

            # Update existing concept node
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            SET c += $updates
            RETURN c.concept_id as id
            """

            result = self.neo4j.execute_write(
                query, parameters={"concept_id": concept_id, "updates": updates}
            )

            # Verify node was found and updated
            if result.get("properties_set", 0) > 0:
                logger.debug(
                    f"ConceptUpdated projection: Updated {result['properties_set']} "
                    f"properties for concept {concept_id}"
                )
                return True
            else:
                logger.warning(
                    f"ConceptUpdated: Concept {concept_id} not found in Neo4j. "
                    f"Event: {event.event_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error handling ConceptUpdated event {event.event_id}: {e}", exc_info=True
            )
            return False

    def _handle_concept_deleted(self, event: Event) -> bool:
        """
        Handle ConceptDeleted event.

        Soft deletes a Concept node by setting deleted flag.
        Preserves node for audit trail.

        Args:
            event: ConceptDeleted event

        Returns:
            True if successful, False otherwise
        """
        try:
            concept_id = event.aggregate_id

            # Soft delete: set deleted flag and timestamp
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            SET c.deleted = true,
                c.deleted_at = $deleted_at
            RETURN c.concept_id as id
            """

            result = self.neo4j.execute_write(
                query,
                parameters={"concept_id": concept_id, "deleted_at": datetime.now(UTC).isoformat()},
            )

            if result.get("properties_set", 0) > 0:
                logger.debug(f"ConceptDeleted projection: Soft deleted concept {concept_id}")
                return True
            else:
                logger.warning(
                    f"ConceptDeleted: Concept {concept_id} not found in Neo4j. "
                    f"Event: {event.event_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error handling ConceptDeleted event {event.event_id}: {e}", exc_info=True
            )
            return False

    def _handle_concept_tau_updated(self, event: Event) -> bool:
        """
        Handle ConceptTauUpdated event.

        Updates the retention_tau property of a Concept node. This value
        is used in the exponential decay model for retention score calculation.

        Args:
            event: ConceptTauUpdated event with tau value in event_data

        Returns:
            True if successful, False otherwise
        """
        try:
            concept_id = event.aggregate_id
            tau = event.event_data.get("tau")

            if tau is None:
                logger.error(
                    f"ConceptTauUpdated event {event.event_id} missing tau value"
                )
                return False

            # Ensure tau is valid
            tau = max(1, int(tau))

            # Update retention_tau and timestamp
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            SET c.retention_tau = $tau,
                c.retention_tau_updated_at = $updated_at
            RETURN c.concept_id as id
            """

            result = self.neo4j.execute_write(
                query,
                parameters={
                    "concept_id": concept_id,
                    "tau": tau,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            )

            if result.get("properties_set", 0) > 0:
                logger.debug(
                    f"ConceptTauUpdated projection: Updated retention_tau to {tau} "
                    f"for concept {concept_id}"
                )
                return True
            else:
                logger.warning(
                    f"ConceptTauUpdated: Concept {concept_id} not found in Neo4j. "
                    f"Event: {event.event_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error handling ConceptTauUpdated event {event.event_id}: {e}",
                exc_info=True
            )
            return False

    def _handle_relationship_created(self, event: Event) -> bool:
        """
        Handle RelationshipCreated event.

        Creates a relationship between two concept nodes.
        Supports CONTAINS, PREREQUISITE, RELATES_TO, and INCLUDES relationship types.

        Args:
            event: RelationshipCreated event

        Returns:
            True if successful, False otherwise
        """
        try:
            event_data = event.event_data

            # Extract relationship data
            relationship_type = event_data.get("relationship_type", "RELATES_TO")
            from_concept_id = event_data.get("from_concept_id")
            to_concept_id = event_data.get("to_concept_id")

            if not from_concept_id or not to_concept_id:
                logger.error(
                    f"RelationshipCreated event {event.event_id} missing from/to concept IDs"
                )
                return False

            # Validate relationship type (security: prevent Cypher injection)
            valid_types = ["CONTAINS", "PREREQUISITE", "RELATES_TO", "INCLUDES"]
            if relationship_type not in valid_types:
                logger.warning(
                    f"Invalid relationship type: {relationship_type}. Valid types: {valid_types}. Using RELATES_TO"
                )
                relationship_type = "RELATES_TO"

            # Defensive assertion to prevent Cypher injection
            assert (
                relationship_type in valid_types
            ), f"Relationship type must be one of {valid_types}"

            # Build relationship properties
            rel_properties = {
                "relationship_id": event.aggregate_id,
                "created_at": event.created_at.isoformat(),
            }

            # Add optional properties
            if "strength" in event_data:
                rel_properties["strength"] = event_data["strength"]
            if "description" in event_data:
                rel_properties["description"] = event_data["description"]

            # Create relationship using dynamic relationship type
            # Note: Neo4j doesn't support parameterized relationship types in Cypher,
            # so we need to build the query string dynamically
            query = f"""
            MATCH (from:Concept {{concept_id: $from_id}})
            MATCH (to:Concept {{concept_id: $to_id}})
            MERGE (from)-[r:{relationship_type}]->(to)
            SET r += $properties
            RETURN r
            """

            result = self.neo4j.execute_write(
                query,
                parameters={
                    "from_id": from_concept_id,
                    "to_id": to_concept_id,
                    "properties": rel_properties,
                },
            )

            if result.get("relationships_created", 0) > 0 or result.get("properties_set", 0) > 0:
                logger.debug(
                    f"RelationshipCreated projection: Created {relationship_type} "
                    f"from {from_concept_id} to {to_concept_id}"
                )
                return True
            else:
                logger.warning(
                    f"RelationshipCreated: Could not create relationship. "
                    f"One or both concepts may not exist. Event: {event.event_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error handling RelationshipCreated event {event.event_id}: {e}", exc_info=True
            )
            return False

    def _handle_relationship_deleted(self, event: Event) -> bool:
        """
        Handle RelationshipDeleted event.

        Deletes a relationship between concept nodes.

        Args:
            event: RelationshipDeleted event

        Returns:
            True if successful, False otherwise
        """
        try:
            relationship_id = event.aggregate_id

            # Delete relationship by ID
            query = """
            MATCH ()-[r {relationship_id: $relationship_id}]->()
            DELETE r
            RETURN count(r) as deleted_count
            """

            # Use execute_read to get the count, then execute_write to delete
            # Actually, we need to use execute_write for DELETE operations
            result = self.neo4j.execute_write(
                query, parameters={"relationship_id": relationship_id}
            )

            if result.get("relationships_deleted", 0) > 0:
                logger.debug(
                    f"RelationshipDeleted projection: Deleted relationship {relationship_id}"
                )
                return True
            else:
                logger.warning(
                    f"RelationshipDeleted: Relationship {relationship_id} not found. "
                    f"Event: {event.event_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error handling RelationshipDeleted event {event.event_id}: {e}", exc_info=True
            )
            return False
