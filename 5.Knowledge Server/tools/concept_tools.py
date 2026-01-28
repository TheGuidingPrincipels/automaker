"""
MCP Tools for Concept Management

Provides CRUD operations for concepts through the Model Context Protocol.
"""

import json
import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from services.container import get_container, ServiceContainer
from services.confidence.models import Success
from config.domains import is_predefined_area, AREA_SLUGS
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


def _get_repository(container: Optional[ServiceContainer] = None):
    """Get repository from container."""
    if container is not None and container.repository is not None:
        return container.repository
    return get_container().repository


def _get_confidence_service(container: Optional[ServiceContainer] = None):
    """Get confidence service from container."""
    if container is not None and container.confidence_service is not None:
        return container.confidence_service
    return get_container().confidence_service


# =============================================================================
# Pydantic Models for Request Validation
# =============================================================================


class ConceptCreate(BaseModel):
    """Model for creating a new concept"""

    name: str = Field(..., min_length=1, max_length=200, description="Concept name")
    explanation: str = Field(..., min_length=1, description="Detailed explanation of the concept")
    area: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Subject area (required, e.g., 'coding-development', 'ai-llms')"
    )
    topic: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Topic within area (required, e.g., 'Python', 'Memory Techniques')"
    )
    subtopic: Optional[str] = Field(None, max_length=100, description="Subtopic (e.g., 'For Loops')")
    source_urls: Optional[str] = Field(None, description="JSON string containing array of source URL objects")
    # confidence_score is calculated automatically by the confidence service

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @field_validator("explanation")
    @classmethod
    def explanation_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Explanation cannot be empty or whitespace")
        return v.strip()

    @field_validator("area", "topic")
    @classmethod
    def area_topic_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Value cannot be empty or whitespace")
        return v.strip()

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls_json(cls, v: str | None) -> str | None:
        """Validate JSON format and structure of source_urls"""
        if v is not None and v.strip():
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, list):
                    raise ValueError("source_urls must be a JSON array")
                for url_obj in parsed:
                    if not isinstance(url_obj, dict) or "url" not in url_obj:
                        raise ValueError('Each source URL must have "url" field')
            except json.JSONDecodeError as e:
                raise ValueError(f"source_urls must be valid JSON: {e}")
        return v


class ConceptUpdate(BaseModel):
    """Model for updating an existing concept"""
    explanation: Optional[str] = Field(None, min_length=1, description="Updated explanation")
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Updated name")
    area: Optional[str] = Field(None, max_length=100, description="Updated area")
    topic: Optional[str] = Field(None, max_length=100, description="Updated topic")
    subtopic: Optional[str] = Field(None, max_length=100, description="Updated subtopic")
    source_urls: Optional[str] = Field(None, description="JSON string containing array of source URL objects")
    # confidence_score is calculated automatically by the confidence service

    @field_validator("name", "explanation")
    @classmethod
    def string_must_not_be_empty(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Value cannot be empty or whitespace")
        return v.strip() if v else v

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls_json(cls, v: str | None) -> str | None:
        """Validate JSON format and structure of source_urls"""
        if v is not None and v.strip():
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, list):
                    raise ValueError("source_urls must be a JSON array")
                for url_obj in parsed:
                    if not isinstance(url_obj, dict) or "url" not in url_obj:
                        raise ValueError('Each source URL must have "url" field')
            except json.JSONDecodeError as e:
                raise ValueError(f"source_urls must be valid JSON: {e}")
        return v


# =============================================================================
# MCP Tool Functions
# =============================================================================


@requires_services("repository")
async def create_concept(
    name: str,
    explanation: str,
    area: str,
    topic: str,
    subtopic: Optional[str] = None,
    source_urls: Optional[str] = None
    # NOTE: confidence_score is calculated automatically, not a parameter
) -> Dict[str, Any]:
    """
    Create a new concept in the knowledge base.

    This tool creates a concept in both Neo4j (graph structure) and ChromaDB (vector search).
    Confidence scores are calculated automatically based on concept quality.

    Args:
        name: Name of the concept (required, 1-200 chars)
        explanation: Detailed explanation of the concept (required)
        area: Subject area (required, e.g., "coding-development", "ai-llms")
        topic: Topic within area (required, e.g., "Python", "Memory Techniques")
        subtopic: More specific classification (optional, e.g., "For Loops")
        source_urls: Optional JSON string containing array of source URL objects.
            Format: '[{"url": "https://...", "title": "...", "quality_score": 0.8, "domain_category": "official"}]'
            Each object should have:
            - url (required): Source URL
            - title (optional): Page title
            - quality_score (optional): 0.0-1.0 quality rating
            - domain_category (optional): "official", "in_depth", or "authoritative"

    Returns:
        {
            "success": bool,
            "message": str,
            "data": {
                "concept_id": str,
                "warnings": [str]  # optional
            }
        }

    Examples:
        >>> create_concept(
        ...     name="Python For Loops",
        ...     explanation="For loops iterate over sequences...",
        ...     area="coding-development",
        ...     topic="Python"
        ... )
        {
            "success": true,
            "message": "Created",
            "data": {"concept_id": "uuid-...", "warnings": []}
        }
    """
    try:
        # Validate inputs using Pydantic model
        concept_data = ConceptCreate(
            name=name,
            explanation=explanation,
            area=area,
            topic=topic,
            subtopic=subtopic,
            source_urls=source_urls
            # confidence_score is calculated and set automatically
        )

        logger.info(
            f"Creating concept: {concept_data.name}",
            extra={"operation": "create_concept", "concept_name": concept_data.name},
        )

        # Get repository from container
        repo = _get_repository()

        # Check for duplicate concepts (name + area + topic uniqueness)
        duplicate_check = repo.find_duplicate_concept(
            name=concept_data.name,
            area=concept_data.area,
            topic=concept_data.topic
        )

        if duplicate_check:
            error_msg = f"Concept already exists with same name/area/topic. Existing concept_id: {duplicate_check['concept_id']}"
            logger.warning(f"Duplicate concept detected: {error_msg}", extra={
                "operation": "create_concept",
                "concept_name": concept_data.name,
                "existing_concept_id": duplicate_check["concept_id"]
            })
            return validation_error(
                error_msg,
                field="name",
                invalid_value={"existing_concept_id": duplicate_check["concept_id"]}
            )

        # Soft validation: warn if using a custom (non-predefined) area
        warnings: list[str] = []
        if not is_predefined_area(concept_data.area):
            warnings.append(
                f"Area '{concept_data.area}' is not a predefined area. "
                f"Recommended areas: {', '.join(sorted(AREA_SLUGS))}. "
                "Custom areas are allowed but may affect discoverability."
            )

        # Convert to dict and parse JSON to native list for internal storage
        concept_dict = concept_data.model_dump(exclude_none=True)
        if source_urls:
            concept_dict["source_urls"] = json.loads(source_urls)  # Store as list, not string

        # Call repository
        success, error, concept_id = repo.create_concept(concept_dict)

        if success:
            if warnings:
                return success_response("Created", concept_id=concept_id, warnings=warnings)
            return success_response("Created", concept_id=concept_id)
        else:
            # Database error from repository
            logger.error(f"Repository error creating concept: {error}", extra={
                "operation": "create_concept",
                "error": error
            })
            return database_error(operation="create")

    except ValidationError as e:
        logger.warning(f"Validation error creating concept: {e}", extra={
            "operation": "create_concept",
            "error": str(e)
        })
        return validation_error(str(e))

    except ValueError as e:
        # Validation error (from Pydantic or custom validators)
        logger.warning(f"Validation error creating concept: {e}", extra={
            "operation": "create_concept",
            "error": str(e)
        })
        return validation_error(str(e))

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error creating concept: {e}", exc_info=True, extra={
            "operation": "create_concept"
        })
        return internal_error(str(e))


@requires_services("repository")
async def get_concept(concept_id: str, include_history: bool = False) -> dict[str, Any]:
    """
    Retrieve a concept by its ID.

    Fetches concept details from Neo4j, optionally including explanation history.

    Args:
        concept_id: UUID of the concept to retrieve
        include_history: Whether to include explanation_history field (default: False)

    Returns:
        {
            "success": bool,
            "concept": {
                "concept_id": str,
                "name": str,
                "explanation": str,
                "area": str,
                "topic": str,
                "subtopic": str,
                "confidence_score": float,
                "created_at": str,
                "last_modified": str,
                "explanation_history": [...] (if include_history=True)
            },
            "message": str
        }

    Examples:
        >>> get_concept("concept-uuid-123")
        {"success": true, "concept": {...}, "message": "Found"}
    """
    try:
        logger.info(
            f"Getting concept: {concept_id}",
            extra={"operation": "get_concept", "concept_id": concept_id},
        )

        # Get repository from container
        repo = _get_repository()

        # Get concept from repository
        concept = repo.get_concept(concept_id)

        if concept:
            # Remove history if not requested (token efficiency)
            if not include_history and "explanation_history" in concept:
                del concept["explanation_history"]

            await _enrich_confidence_score(concept_id, concept)

            return success_response("Found", concept=concept)
        else:
            # Not found error
            logger.info(f"Concept not found: {concept_id}", extra={
                "operation": "get_concept",
                "concept_id": concept_id
            })
            return not_found_error("Concept", concept_id)

    except Exception as e:
        logger.error(f"Error getting concept {concept_id}: {e}", exc_info=True, extra={
            "operation": "get_concept",
            "concept_id": concept_id
        })
        return internal_error(str(e))


@requires_services("repository")
async def update_concept(
    concept_id: str,
    explanation: Optional[str] = None,
    name: Optional[str] = None,
    area: Optional[str] = None,
    topic: Optional[str] = None,
    subtopic: Optional[str] = None,
    source_urls: Optional[str] = None
    # NOTE: confidence_score is calculated automatically, not a parameter
) -> Dict[str, Any]:
    """
    Update an existing concept.

    Supports partial updates - only provided fields will be updated.
    Explanation changes are tracked in history. Embeddings are regenerated if needed.
    Confidence scores are recalculated automatically when concept is updated.

    Args:
        concept_id: UUID of the concept to update
        explanation: Updated explanation (optional)
        name: Updated name (optional)
        area: Updated area (optional)
        topic: Updated topic (optional)
        subtopic: Updated subtopic (optional)
        source_urls: Optional JSON string containing array of source URL objects.
            Format: '[{"url": "https://...", "title": "..."}]'

    Returns:
        {
            "success": bool,
            "updated_fields": List[str],
            "message": str
        }

    Examples:
        >>> update_concept(
        ...     concept_id="uuid-123",
        ...     explanation="Updated explanation..."
        ... )
        {"success": true, "updated_fields": ["explanation"], "message": "Updated"}
    """
    try:
        # Build updates dict from provided parameters
        updates = {}
        if explanation is not None:
            updates["explanation"] = explanation
        if name is not None:
            updates["name"] = name
        if area is not None:
            updates["area"] = area
        if topic is not None:
            updates["topic"] = topic
        if subtopic is not None:
            updates["subtopic"] = subtopic
        if source_urls is not None:
            updates["source_urls"] = source_urls
        # confidence_score is handled automatically by the confidence service

        # Validate no updates provided
        if not updates:
            logger.warning("Update concept called with no fields", extra={
                "operation": "update_concept",
                "concept_id": concept_id
            })
            return validation_error("No fields provided for update")

        # Validate using Pydantic model
        update_data = ConceptUpdate(**updates)

        logger.info(
            f"Updating concept {concept_id}: {list(updates.keys())}",
            extra={
                "operation": "update_concept",
                "concept_id": concept_id,
                "fields": list(updates.keys()),
            },
        )

        # Convert to dict and parse JSON to native list for internal storage
        update_dict = update_data.model_dump(exclude_none=True)
        if source_urls:
            update_dict["source_urls"] = json.loads(source_urls)  # Store as list, not string

        # Get repository from container
        repo = _get_repository()

        # Call repository
        success, error = repo.update_concept(concept_id, update_dict)

        if success:
            return success_response("Updated", updated_fields=list(updates.keys()))
        else:
            # Database or not found error
            logger.error(f"Repository error updating concept {concept_id}: {error}", extra={
                "operation": "update_concept",
                "concept_id": concept_id,
                "error": error
            })
            return database_error(operation="update")

    except ValueError as e:
        # Validation error
        logger.warning(f"Validation error updating concept {concept_id}: {e}", extra={
            "operation": "update_concept",
            "concept_id": concept_id,
            "error": str(e)
        })
        return validation_error(str(e))

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error updating concept {concept_id}: {e}", exc_info=True, extra={
            "operation": "update_concept",
            "concept_id": concept_id
        })
        return internal_error(str(e))


@requires_services("repository")
async def delete_concept(concept_id: str) -> dict[str, Any]:
    """
    Delete a concept (soft delete).

    Marks the concept as deleted in Neo4j and removes it from ChromaDB.
    The event is preserved in the event store for audit trail.

    Args:
        concept_id: UUID of the concept to delete

    Returns:
        {
            "success": bool,
            "concept_id": str,
            "message": str
        }

    Examples:
        >>> delete_concept("concept-uuid-123")
        {"success": true, "concept_id": "concept-uuid-123", "message": "Deleted"}
    """
    try:
        logger.info(
            f"Deleting concept: {concept_id}",
            extra={"operation": "delete_concept", "concept_id": concept_id},
        )

        # Get repository from container
        repo = _get_repository()

        # Call repository
        success, error = repo.delete_concept(concept_id)

        if success:
            return success_response("Deleted", concept_id=concept_id)
        else:
            # Database or not found error
            logger.error(f"Repository error deleting concept {concept_id}: {error}", extra={
                "operation": "delete_concept",
                "concept_id": concept_id,
                "error": error
            })
            return database_error(operation="delete")

    except Exception as e:
        logger.error(f"Error deleting concept {concept_id}: {e}", exc_info=True, extra={
            "operation": "delete_concept",
            "concept_id": concept_id
        })
        return internal_error(str(e))


async def _enrich_confidence_score(concept_id: str, concept: dict[str, Any]) -> None:
    """
    Ensure the concept payload contains a confidence score in 0-100 scale.

    Process:
    1. Read persisted score from Neo4j (stored as 0-100 scale)
    2. If not present, calculate on-demand via confidence_service (returns 0-1, convert to 0-100)

    Raises:
        RuntimeError: If confidence calculation fails (no silent fallbacks)
    """
    # Get score from Neo4j (stored as 0-100 scale)
    score = concept.get("confidence_score")

    # Get confidence service from container
    conf_service = _get_confidence_service()

    if score is not None:
        # Score from Neo4j is already in 0-100 scale
        display_score = _clamp_confidence_score(score)
    elif conf_service is not None:
        # Calculate on-demand (returns 0-1 scale, convert to 0-100)
        result = await conf_service.calculate_composite_score(concept_id)  # type: ignore[attr-defined]
        if isinstance(result, Success):
            display_score = result.value * 100.0  # Convert 0-1 to 0-100
        else:
            # Confidence calculation must work 100% - propagate error
            error_msg = f"Confidence calculation failed for {concept_id}: {result.message}"
            logger.error(error_msg, extra={
                "concept_id": concept_id,
                "error_code": result.code.value if hasattr(result, 'code') else "unknown"
            })
            raise RuntimeError(error_msg)
    else:
        # No confidence service available - use default score for new concepts
        display_score = 0.0

    concept["confidence_score"] = display_score


def _clamp_confidence_score(value: Any) -> float:
    """
    Validate and clamp confidence score to 0-100 range.

    Scores are stored in 0-100 scale. This function validates the range
    and logs errors for out-of-range values (which indicate upstream bugs).
    """
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return 0.0

    # Valid range is 0-100
    if 0.0 <= raw <= 100.0:
        return raw

    # Out-of-range values indicate upstream bug - log and clamp
    if raw > 100.0:
        logger.error(
            "Confidence score out of range: %s (expected 0-100). "
            "This indicates a bug in score calculation. Capping to 100.0",
            raw,
        )
        return 100.0
    else:  # raw < 0.0
        logger.error(
            "Confidence score out of range: %s (expected 0-100). "
            "This indicates a bug in score calculation. Returning 0.0",
            raw,
        )
        return 0.0


# Tool registration will be done in mcp_server.py using @mcp.tool() decorator
