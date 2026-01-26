"""
MCP Tools for Relationship Operations

Provides relationship creation and management capabilities through the Model Context Protocol.
"""

import logging
import uuid
from enum import Enum
from typing import Any, Optional

from services.container import get_container, ServiceContainer
from .responses import (
    ErrorType,
    success_response,
    validation_error,
    not_found_error,
    database_error,
    internal_error,
)
from .service_utils import requires_services


logger = logging.getLogger(__name__)


def _get_neo4j_service(container: Optional[ServiceContainer] = None):
    """Get Neo4j service from container."""
    if container is not None and container.neo4j_service is not None:
        return container.neo4j_service
    return get_container().neo4j_service


def _get_event_store(container: Optional[ServiceContainer] = None):
    """Get event store from container."""
    if container is not None and container.event_store is not None:
        return container.event_store
    return get_container().event_store


def _get_outbox(container: Optional[ServiceContainer] = None):
    """Get outbox from container."""
    if container is not None and container.outbox is not None:
        return container.outbox
    return get_container().outbox


class RelationshipType(str, Enum):
    """Enum for valid relationship types with type safety."""

    PREREQUISITE = "PREREQUISITE"
    RELATES_TO = "RELATES_TO"
    INCLUDES = "INCLUDES"
    CONTAINS = "CONTAINS"


# Valid relationship types (lowercase tool input format)
VALID_RELATIONSHIP_TYPES = {"prerequisite", "relates_to", "includes", "contains"}


def _normalize_relationship_type(rel_type: str) -> str:
    """
    Normalize relationship type to match Neo4j storage format with runtime validation.

    Ensures consistency between create/delete/query operations.
    Maps lowercase tool types to uppercase Neo4j types.
    Validates against RelationshipType enum for type safety.

    Args:
        rel_type: Relationship type from tool call (e.g., "prerequisite", "includes")

    Returns:
        Normalized uppercase type (e.g., "PREREQUISITE", "INCLUDES")

    Raises:
        ValueError: If relationship type is not valid
    """
    if not rel_type or not isinstance(rel_type, str):
        raise ValueError(f"Invalid relationship type: {rel_type}. Must be a non-empty string.")

    # Mapping from lowercase tool input to enum values
    mapping = {
        "prerequisite": RelationshipType.PREREQUISITE.value,
        "relates_to": RelationshipType.RELATES_TO.value,
        "includes": RelationshipType.INCLUDES.value,
        "contains": RelationshipType.CONTAINS.value,
    }

    normalized = mapping.get(rel_type.lower())

    # Validate that the normalized type is in the enum
    if normalized is None:
        # Try direct uppercase match as fallback
        normalized = rel_type.upper()
        try:
            RelationshipType(normalized)
        except ValueError:
            valid_types = ", ".join(mapping.keys())
            raise ValueError(
                f"Invalid relationship type: '{rel_type}'. " f"Must be one of: {valid_types}"
            )

    logger.debug(f"Normalized relationship type '{rel_type}' -> '{normalized}'")
    return normalized


def _safe_cypher_interpolation(
    template: str, value_to_inject: str, allowed_values: set, value_name: str = "value"
) -> str:
    """
    Safely interpolate a value into Cypher query with strict validation.

    **SECURITY NOTE:**
    This function exists because Neo4j does not support parameterization for:
    - Variable-length patterns: [:REL*1..{n}]
    - Type filters in WHERE clauses: type(rel) = {type}

    When parameterization is impossible, we use this function to provide
    defense-in-depth through:
    1. Whitelist validation (only enum values allowed)
    2. Character validation (no injection characters)
    3. Explicit security assertions

    **USE WITH CAUTION:** Only use when Neo4j parameterization is truly impossible.
    Always prefer parameterized queries when possible.

    Args:
        template: Query template with {value} placeholder
        value_to_inject: The value to interpolate (must be pre-validated)
        allowed_values: Set of permitted values (whitelist)
        value_name: Name for error messages (e.g., "relationship_type")

    Returns:
        Query string with safely interpolated value

    Raises:
        ValueError: If value not in whitelist or contains dangerous characters

    Example:
        >>> template = "WHERE type(rel) = '{value}'"
        >>> allowed = {"PREREQUISITE", "RELATES_TO"}
        >>> _safe_cypher_interpolation(template, "PREREQUISITE", allowed, "rel_type")
        "WHERE type(rel) = 'PREREQUISITE'"
    """
    # Validation 1: Whitelist check
    if value_to_inject not in allowed_values:
        raise ValueError(
            f"{value_name} '{value_to_inject}' not in whitelist: {sorted(allowed_values)}"
        )

    # Validation 2: Character safety check (defense-in-depth)
    # Even though whitelist should prevent these, we check explicitly
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "\\", "\n", "\r", "\x00"]
    for char in dangerous_chars:
        if char in value_to_inject:
            raise ValueError(
                f"{value_name} '{value_to_inject}' contains dangerous character: {char!r}"
            )

    # Validation 3: Length check (prevent potential buffer overflow or DoS)
    if len(value_to_inject) > 100:
        raise ValueError(f"{value_name} exceeds maximum length of 100 characters")

    # Safe to interpolate after all validations pass
    result = template.format(value=value_to_inject)

    logger.debug(
        f"Safe Cypher interpolation: {value_name}={value_to_inject} "
        f"(validated against {len(allowed_values)} allowed values)"
    )

    return result


# =============================================================================
# MCP Tool Functions
# =============================================================================


@requires_services("neo4j_service", "event_store", "outbox")
async def create_relationship(
    source_id: str,
    target_id: str,
    relationship_type: str,
    strength: float = 1.0,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Create a relationship between two concepts.

    This tool creates a directed relationship in the knowledge graph,
    with support for different relationship types and strength indicators.

    Args:
        source_id: ID of the source concept (required)
        target_id: ID of the target concept (required)
        relationship_type: Type of relationship (required, one of: "prerequisite", "relates_to", "includes")
        strength: Strength of the relationship (default: 1.0, range: 0.0-1.0)
        notes: Optional notes or description for the relationship

    Returns:
        {
            "success": bool,
            "relationship_id": str,
            "message": str
        }

    Examples:
        >>> create_relationship("concept-001", "concept-002", "prerequisite", strength=1.0)
        >>> create_relationship("concept-003", "concept-004", "relates_to", notes="Similar topics")
    """
    try:
        # Get services from container
        neo4j = _get_neo4j_service()
        evt_store = _get_event_store()
        ob = _get_outbox()

        # Validate required parameters
        if not source_id or not isinstance(source_id, str):
            return validation_error(
                "source_id is required and must be a string",
                field="source_id",
                invalid_value=source_id,
            )

        if not target_id or not isinstance(target_id, str):
            return validation_error(
                "target_id is required and must be a string",
                field="target_id",
                invalid_value=target_id,
            )

        # Validate relationship type
        if relationship_type not in VALID_RELATIONSHIP_TYPES:
            return validation_error(
                f"relationship_type must be one of {VALID_RELATIONSHIP_TYPES}",
                field="relationship_type",
                invalid_value=relationship_type,
            )

        # Validate strength
        if not isinstance(strength, (int, float)) or strength < 0.0 or strength > 1.0:
            return validation_error(
                "strength must be a number between 0.0 and 1.0",
                field="strength",
                invalid_value=strength,
            )

        # Check if both concepts exist
        logger.info(f"Verifying concepts exist: {source_id}, {target_id}")

        check_query = """
        MATCH (c:Concept)
        WHERE c.concept_id IN [$source_id, $target_id]
          AND (c.deleted IS NULL OR c.deleted = false)
        RETURN c.concept_id AS concept_id
        """

        existing_concepts = neo4j.execute_read(
            check_query,
            {"source_id": source_id, "target_id": target_id}
        )

        existing_ids = {record.get("concept_id") for record in existing_concepts}

        if source_id not in existing_ids:
            return not_found_error("Concept", source_id)

        if target_id not in existing_ids:
            return not_found_error("Concept", target_id)

        # Check for duplicate relationship
        duplicate_check_query = """
        MATCH (from:Concept {concept_id: $source_id})-[r]->(to:Concept {concept_id: $target_id})
        WHERE type(r) = $rel_type
        RETURN r.relationship_id AS relationship_id
        """

        duplicates = neo4j.execute_read(
            duplicate_check_query,
            {
                "source_id": source_id,
                "target_id": target_id,
                "rel_type": _normalize_relationship_type(relationship_type),
            },
        )

        if duplicates:
            existing_rel_id = duplicates[0].get("relationship_id")
            logger.warning(f"Duplicate relationship found: {existing_rel_id}")
            return validation_error(
                f"Relationship already exists between {source_id} and {target_id}",
                field="relationship",
                invalid_value={"source_id": source_id, "target_id": target_id, "type": relationship_type, "existing_id": existing_rel_id}
            )

        # Generate unique relationship ID
        relationship_id = f"rel-{uuid.uuid4().hex[:12]}"

        # Build relationship data
        relationship_data = {
            "relationship_type": relationship_type.upper(),
            "from_concept_id": source_id,
            "to_concept_id": target_id,
            "strength": strength,
        }

        if notes:
            relationship_data["description"] = notes

        logger.info(
            f"Creating relationship: {source_id} -{relationship_type}-> {target_id} "
            f"(strength={strength})"
        )

        # Import event class
        from models.events import RelationshipCreated

        # Create event
        event = RelationshipCreated(
            aggregate_id=relationship_id, relationship_data=relationship_data, version=1
        )

        # Store event in event store
        evt_store.append_event(event)
        logger.debug(f"RelationshipCreated event stored: {event.event_id}")

        # Add to outbox for Neo4j projection
        # Capture outbox_id to mark correct entry as processed (fixes race condition #H002)
        outbox_id = ob.add_to_outbox(
            event_id=event.event_id,
            projection_name="neo4j"
        )
        logger.debug(f"Added to outbox for Neo4j projection: {outbox_id}")

        # Import projection to process immediately
        from projections.neo4j_projection import Neo4jProjection

        # Create projection instance and process event immediately
        projection = Neo4jProjection(neo4j)
        success = projection.project_event(event)

        if success:
            # Mark outbox entry as processed
            # Use captured outbox_id to avoid race condition (fixes #H002)
            ob.mark_processed(outbox_id)

            logger.info(
                f"Relationship created successfully: {relationship_id} "
                f"({source_id} -> {target_id})"
            )

            return success_response("Relationship created", relationship_id=relationship_id)
        else:
            logger.error(f"Failed to project relationship: {relationship_id}")
            return database_error(service_name="neo4j", operation="create_relationship")

    except ValueError as e:
        logger.warning(f"Validation error in create_relationship: {e}", extra={
            "operation": "create_relationship",
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "error": str(e)
        })
        return validation_error(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_relationship: {e}", exc_info=True, extra={
            "operation": "create_relationship",
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type
        })
        return internal_error(str(e))


@requires_services("neo4j_service", "event_store", "outbox")
async def delete_relationship(
    source_id: str, target_id: str, relationship_type: str
) -> dict[str, Any]:
    """
    Delete a relationship between two concepts.

    This tool removes a relationship from the knowledge graph using soft delete.
    The relationship is marked as deleted in Neo4j, and the event is stored for audit trail.

    Args:
        source_id: ID of the source concept (required)
        target_id: ID of the target concept (required)
        relationship_type: Type of relationship to delete (one of: "prerequisite", "relates_to", "includes")

    Returns:
        {
            "success": bool,
            "message": str
        }

    Examples:
        >>> delete_relationship("concept-001", "concept-002", "prerequisite")
    """
    try:
        # Get services from container
        neo4j = _get_neo4j_service()
        evt_store = _get_event_store()
        ob = _get_outbox()

        # Validate required parameters
        if not source_id or not isinstance(source_id, str):
            return validation_error(
                "source_id is required and must be a string",
                field="source_id",
                invalid_value=source_id,
            )

        if not target_id or not isinstance(target_id, str):
            return validation_error(
                "target_id is required and must be a string",
                field="target_id",
                invalid_value=target_id,
            )

        # Validate relationship type
        if relationship_type not in VALID_RELATIONSHIP_TYPES:
            return validation_error(
                f"relationship_type must be one of {VALID_RELATIONSHIP_TYPES}",
                field="relationship_type",
                invalid_value=relationship_type,
            )

        logger.info(f"Deleting relationship: {source_id} -{relationship_type}-> {target_id}")

        # Check if relationship exists
        find_query = """
        MATCH (from:Concept {concept_id: $source_id})-[r]->(to:Concept {concept_id: $target_id})
        WHERE type(r) = $rel_type
          AND (r.deleted IS NULL OR r.deleted = false)
        RETURN r.relationship_id AS relationship_id
        """

        existing_rels = neo4j.execute_read(
            find_query,
            {
                "source_id": source_id,
                "target_id": target_id,
                "rel_type": _normalize_relationship_type(relationship_type),
            },
        )

        if not existing_rels:
            return not_found_error("Relationship", f"{source_id}-{relationship_type}->{target_id}")

        relationship_id = existing_rels[0].get("relationship_id")

        # Import event class
        from models.events import RelationshipDeleted

        # Get current version from event store
        current_version = evt_store.get_latest_version(relationship_id)
        next_version = current_version + 1

        # Create event for audit trail
        # Include concept IDs so confidence scoring can recalculate both concepts
        event = RelationshipDeleted(
            aggregate_id=relationship_id,
            version=next_version,
            event_data={"deleted": True, "from_concept_id": source_id, "to_concept_id": target_id},
        )

        # Store event in event store
        evt_store.append_event(event)
        logger.debug(f"RelationshipDeleted event stored: {event.event_id}")

        # Add to outbox for Neo4j projection
        # Capture outbox_id to mark correct entry as processed (fixes race condition #H002)
        outbox_id = ob.add_to_outbox(
            event_id=event.event_id,
            projection_name="neo4j"
        )
        logger.debug(f"Added to outbox for Neo4j projection: {outbox_id}")

        # Import projection to process immediately
        from projections.neo4j_projection import Neo4jProjection

        # Create projection instance and process event immediately
        projection = Neo4jProjection(neo4j)
        success = projection.project_event(event)

        if success:
            # Mark outbox entry as processed
            # Use captured outbox_id to avoid race condition (fixes #H002)
            ob.mark_processed(outbox_id)

            logger.info(f"Relationship deleted successfully: {relationship_id}")

            return success_response("Relationship deleted")
        else:
            logger.error(f"Failed to delete relationship: {relationship_id}")
            return database_error(service_name="neo4j", operation="delete_relationship")

    except ValueError as e:
        logger.warning(f"Validation error in delete_relationship: {e}", extra={
            "operation": "delete_relationship",
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "error": str(e)
        })
        return validation_error(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in delete_relationship: {e}", exc_info=True, extra={
            "operation": "delete_relationship",
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type
        })
        return internal_error(str(e))


@requires_services("neo4j_service")
async def get_related_concepts(
    concept_id: str,
    relationship_type: str | None = None,
    direction: str = "outgoing",
    max_depth: int = 1,
) -> dict[str, Any]:
    """
    Get concepts related to a given concept through graph traversal.

    This tool traverses the knowledge graph to find related concepts with flexible
    direction and depth control.

    Args:
        concept_id: Starting concept ID (required)
        relationship_type: Optional filter (one of: "prerequisite", "relates_to", "includes")
        direction: Traversal direction - "outgoing", "incoming", or "both" (default: "outgoing")
        max_depth: Maximum hops to traverse, 1-5 (default: 1)

    Returns:
        {
            "concept_id": str,
            "related": [{
                "concept_id": str,
                "name": str,
                "relationship_type": str,
                "strength": float,
                "distance": int
            }],
            "total": int
        }

    Examples:
        >>> get_related_concepts("concept-001", direction="outgoing", max_depth=2)
        >>> get_related_concepts("concept-001", relationship_type="prerequisite", direction="incoming")
    """
    try:
        # Get Neo4j service from container
        neo4j = _get_neo4j_service()

        # Validate concept_id
        if not concept_id or not isinstance(concept_id, str):
            return validation_error(
                "concept_id is required and must be a string",
                field="concept_id",
                invalid_value=concept_id,
            )

        # Validate direction
        valid_directions = {"outgoing", "incoming", "both"}
        if direction not in valid_directions:
            return validation_error(
                f"direction must be one of {valid_directions}",
                field="direction",
                invalid_value=direction,
            )

        # Validate max_depth
        if not isinstance(max_depth, int) or max_depth < 1 or max_depth > 5:
            max_depth = min(max(1, max_depth), 5)
            logger.warning(f"max_depth adjusted to valid range: {max_depth}")

        # Validate relationship_type if provided
        if relationship_type and relationship_type not in VALID_RELATIONSHIP_TYPES:
            return validation_error(
                f"relationship_type must be one of {VALID_RELATIONSHIP_TYPES}",
                field="relationship_type",
                invalid_value=relationship_type,
            )

        logger.info(
            f"Finding related concepts for {concept_id}: "
            f"direction={direction}, type={relationship_type}, depth={max_depth}"
        )

        # Build direction-specific pattern
        if direction == "outgoing":
            rel_pattern = f"-[r*1..{max_depth}]->"
        elif direction == "incoming":
            rel_pattern = f"<-[r*1..{max_depth}]-"
        else:  # both
            rel_pattern = f"-[r*1..{max_depth}]-"

        # Build relationship type filter
        # SECURITY: Using safe interpolation due to Neo4j limitation (can't parameterize type filters)
        if relationship_type:
            normalized_type = _normalize_relationship_type(relationship_type)
            allowed_types = {e.value for e in RelationshipType}
            type_filter = _safe_cypher_interpolation(
                template="AND all(rel in r WHERE type(rel) = '{value}')",
                value_to_inject=normalized_type,
                allowed_values=allowed_types,
                value_name="relationship_type",
            )
        else:
            type_filter = ""

        # Query for related concepts
        query = f"""
        MATCH path = (start:Concept {{concept_id: $concept_id}}){rel_pattern}(related:Concept)
        WHERE (start.deleted IS NULL OR start.deleted = false)
          AND (related.deleted IS NULL OR related.deleted = false)
          {type_filter}
        WITH DISTINCT related,
             relationships(path) as rels,
             length(path) as distance,
             [rel in relationships(path) | type(rel)][0] as rel_type,
             [rel in relationships(path) | coalesce(rel.strength, 1.0)][0] as strength
        RETURN related.concept_id as concept_id,
               related.name as name,
               rel_type as relationship_type,
               strength,
               distance
        ORDER BY distance, related.name
        LIMIT 50
        """

        results = neo4j.execute_read(query, {"concept_id": concept_id})

        # Format results
        related = []
        for record in results:
            related.append(
                {
                    "concept_id": record.get("concept_id"),
                    "name": record.get("name"),
                    "relationship_type": record.get("relationship_type", "").lower(),
                    "strength": float(record.get("strength", 1.0)),
                    "distance": record.get("distance"),
                }
            )

        logger.info(f"Found {len(related)} related concepts for {concept_id}")

        return success_response(
            "Found",
            concept_id=concept_id,
            related=related,
            total=len(related)
        )

    except ValueError as e:
        logger.warning(f"Validation error in get_related_concepts: {e}", extra={
            "operation": "get_related_concepts",
            "concept_id": concept_id,
            "relationship_type": relationship_type,
            "direction": direction,
            "max_depth": max_depth,
            "error": str(e)
        })
        return validation_error(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_related_concepts: {e}", exc_info=True, extra={
            "operation": "get_related_concepts",
            "concept_id": concept_id,
            "relationship_type": relationship_type,
            "direction": direction,
            "max_depth": max_depth
        })
        return internal_error(str(e))


@requires_services("neo4j_service")
async def get_prerequisites(concept_id: str, max_depth: int = 5) -> dict[str, Any]:
    """
    Get complete prerequisite chain for a concept.

    This tool traverses PREREQUISITE relationships to build a learning path,
    ordered from deepest prerequisites to the target concept.

    Args:
        concept_id: Target concept ID (required)
        max_depth: Maximum chain depth, 1-10 (default: 5)

    Returns:
        {
            "concept_id": str,
            "chain": [{
                "concept_id": str,
                "name": str,
                "depth": int
            }],
            "total": int
        }

    Examples:
        >>> get_prerequisites("concept-advanced-topic", max_depth=5)
    """
    try:
        # Get Neo4j service from container
        neo4j = _get_neo4j_service()

        # Validate concept_id
        if not concept_id or not isinstance(concept_id, str):
            return validation_error(
                "concept_id is required and must be a string",
                field="concept_id",
                invalid_value=concept_id,
            )

        # Validate max_depth
        if not isinstance(max_depth, int) or max_depth < 1 or max_depth > 10:
            max_depth = min(max(1, max_depth), 10)
            logger.warning(f"max_depth adjusted to valid range: {max_depth}")

        logger.info(f"Finding prerequisites for {concept_id} (max_depth={max_depth})")

        # Query for prerequisite chain
        # SECURITY NOTE: Neo4j doesn't allow parameters in variable-length patterns [:REL*1..{n}]
        # max_depth is validated above to be an integer in range [1,10], making injection impossible
        # The relationship type is hardcoded as PREREQUISITE (not user input), so no type injection risk
        query = f"""
        MATCH path = (target:Concept {{concept_id: $concept_id}})<-[:PREREQUISITE*1..{max_depth}]-(prereq:Concept)
        WHERE (prereq.deleted IS NULL OR prereq.deleted = false)
          AND (target.deleted IS NULL OR target.deleted = false)
        WITH DISTINCT prereq.concept_id as concept_id,
             prereq.name as name,
             length(path) as depth
        RETURN concept_id, name, depth
        ORDER BY depth DESC, name
        """

        results = neo4j.execute_read(
            query,
            {"concept_id": concept_id}
        )

        # Format results
        chain = []
        for record in results:
            chain.append(
                {
                    "concept_id": record.get("concept_id"),
                    "name": record.get("name"),
                    "depth": record.get("depth"),
                }
            )

        logger.info(f"Found {len(chain)} prerequisites for {concept_id}")

        return success_response(
            "Found",
            concept_id=concept_id,
            chain=chain,
            total=len(chain)
        )

    except ValueError as e:
        logger.warning(f"Validation error in get_prerequisites: {e}", extra={
            "operation": "get_prerequisites",
            "concept_id": concept_id,
            "max_depth": max_depth,
            "error": str(e)
        })
        return validation_error(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_prerequisites: {e}", exc_info=True, extra={
            "operation": "get_prerequisites",
            "concept_id": concept_id,
            "max_depth": max_depth
        })
        return internal_error(str(e))


@requires_services("neo4j_service")
async def get_concept_chain(
    start_id: str, end_id: str, relationship_type: str | None = None
) -> dict[str, Any]:
    """
    Find shortest path between two concepts.

    This tool uses Neo4j's shortestPath algorithm to find the most direct
    connection between concepts in the knowledge graph.

    Args:
        start_id: Starting concept ID (required)
        end_id: Target concept ID (required)
        relationship_type: Optional relationship filter (one of: "prerequisite", "relates_to", "includes")

    Returns:
        {
            "success": bool,
            "path": [{
                "concept_id": str,
                "name": str
            }],
            "length": int
        }

    Examples:
        >>> get_concept_chain("concept-001", "concept-010")
        >>> get_concept_chain("concept-001", "concept-010", relationship_type="prerequisite")
    """
    try:
        # Get Neo4j service from container
        neo4j = _get_neo4j_service()

        # Validate IDs
        if not start_id or not isinstance(start_id, str):
            return validation_error(
                "start_id is required and must be a string",
                field="start_id",
                invalid_value=start_id,
            )

        if not end_id or not isinstance(end_id, str):
            return validation_error(
                "end_id is required and must be a string",
                field="end_id",
                invalid_value=end_id,
            )

        # Validate relationship_type if provided
        if relationship_type and relationship_type not in VALID_RELATIONSHIP_TYPES:
            return validation_error(
                f"relationship_type must be one of {VALID_RELATIONSHIP_TYPES}",
                field="relationship_type",
                invalid_value=relationship_type,
            )

        # Handle same start and end concept (single-node path)
        if start_id == end_id:
            logger.info(f"Returning single-node path for same start/end concept: {start_id}")

            # Verify concept exists and is not deleted
            verify_query = """
            MATCH (c:Concept {concept_id: $concept_id})
            WHERE c.deleted IS NULL OR c.deleted = false
            RETURN c.concept_id as concept_id, c.name as name
            """

            verify_results = neo4j.execute_read(
                verify_query,
                {"concept_id": start_id}
            )

            if not verify_results:
                return not_found_error("Concept", start_id)

            # Return single-node path with length 0
            concept_data = verify_results[0]
            return success_response(
                "Found",
                path=[{
                    "concept_id": concept_data["concept_id"],
                    "name": concept_data["name"]
                }],
                length=0
            )

        logger.info(f"Finding shortest path from {start_id} to {end_id}")

        # Build WHERE clause with both relationship type and deletion filters
        # SECURITY: Using safe interpolation due to Neo4j limitation (can't parameterize type filters)
        where_conditions = []
        if relationship_type:
            normalized_type = _normalize_relationship_type(relationship_type)
            allowed_types = {e.value for e in RelationshipType}
            type_condition = _safe_cypher_interpolation(
                template="all(r in relationships(path) WHERE type(r) = '{value}')",
                value_to_inject=normalized_type,
                allowed_values=allowed_types,
                value_name="relationship_type",
            )
            where_conditions.append(type_condition)
        where_conditions.append(
            "all(n in nodes(path) WHERE n.deleted IS NULL OR n.deleted = false)"
        )

        where_clause = "WHERE " + " AND ".join(where_conditions)

        # Query for shortest path
        query = f"""
        MATCH path = shortestPath(
            (start:Concept {{concept_id: $start_id}})-[*]-(end:Concept {{concept_id: $end_id}})
        )
        {where_clause}
        RETURN [n in nodes(path) | {{concept_id: n.concept_id, name: n.name}}] as path,
               length(path) as length
        """

        results = neo4j.execute_read(
            query,
            {"start_id": start_id, "end_id": end_id}
        )

        if not results:
            logger.info(f"No path found from {start_id} to {end_id}")
            return success_response("No path found", path=[], length=0)

        # Extract path
        path_data = results[0].get("path", [])
        length = results[0].get("length", 0)

        logger.info(f"Found path of length {length} from {start_id} to {end_id}")

        return success_response("Found", path=path_data, length=length)

    except ValueError as e:
        logger.warning(f"Validation error in get_concept_chain: {e}", extra={
            "operation": "get_concept_chain",
            "start_id": start_id,
            "end_id": end_id,
            "relationship_type": relationship_type,
            "error": str(e)
        })
        return validation_error(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_concept_chain: {e}", exc_info=True, extra={
            "operation": "get_concept_chain",
            "start_id": start_id,
            "end_id": end_id,
            "relationship_type": relationship_type
        })
        return internal_error(str(e))
