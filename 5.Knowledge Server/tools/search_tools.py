"""
MCP Tools for Search Operations

Provides semantic and exact search capabilities through the Model Context Protocol.

Data Access Pattern (Read-Only):
    - Semantic search: Uses chromadb_service directly for embedding similarity
    - Exact search: Uses neo4j_service directly for filtered graph queries
    - Recent concepts: Uses neo4j_service for time-based queries

For write operations (create/update/delete), use concept_tools which routes
through DualStorageRepository to maintain event sourcing integrity.

See docs/adr/001-data-access-patterns.md for architecture guidelines.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from services.container import get_container, ServiceContainer
from .responses import (
    ErrorType,
    success_response,
    validation_error,
    database_error,
    internal_error,
)
from .service_utils import requires_services


logger = logging.getLogger(__name__)


def _get_chromadb_service(container: Optional[ServiceContainer] = None):
    """Get ChromaDB service from container."""
    if container is not None and container.chromadb_service is not None:
        return container.chromadb_service
    return get_container().chromadb_service


def _get_neo4j_service(container: Optional[ServiceContainer] = None):
    """Get Neo4j service from container."""
    if container is not None and container.neo4j_service is not None:
        return container.neo4j_service
    return get_container().neo4j_service


def _get_embedding_service(container: Optional[ServiceContainer] = None):
    """Get embedding service from container."""
    if container is not None and container.embedding_service is not None:
        return container.embedding_service
    return get_container().embedding_service


# =============================================================================
# MCP Tool Functions
# =============================================================================


@requires_services("embedding_service", "chromadb_service")
async def search_concepts_semantic(
    query: str,
    limit: int = 10,
    min_confidence: Optional[float] = None,
    area: Optional[str] = None,
    topic: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for concepts using semantic similarity (ChromaDB embeddings).

    This tool performs semantic search by:
    1. Generating an embedding for the query
    2. Finding similar concepts using cosine similarity
    3. Optionally filtering by metadata (area, topic, min_confidence)

    Args:
        query: Natural language search query (required)
        limit: Maximum number of results to return (default: 10, max: 50)
        min_confidence: Minimum confidence score filter (0-100, optional)
        area: Filter by subject area (optional, e.g., "Programming")
        topic: Filter by topic (optional, e.g., "Python")

    Returns:
        {
            "success": bool,
            "results": [
                {
                    "concept_id": str,
                    "name": str,
                    "similarity": float,
                    "area": str,
                    "topic": str,
                    "confidence_score": float
                }
            ],
            "total": int,
            "message": str
        }

    Examples:
        >>> search_concepts_semantic("How to loop through items in Python?", limit=5)
        >>> search_concepts_semantic("machine learning basics", area="AI", min_confidence=80)
    """
    try:
        # Validate limit
        warnings = []
        original_limit = limit
        if limit < 1 or limit > 50:
            limit = min(max(limit, 1), 50)
            warnings.append(f"Limit adjusted from {original_limit} to {limit} (valid range: 1-50)")

        # Get services from container
        emb_service = _get_embedding_service()
        chroma_service = _get_chromadb_service()

        # Generate embedding for query
        logger.info(f"Generating embedding for query: {query[:50]}...")
        query_embedding = emb_service.generate_embedding(query)

        if query_embedding is None or len(query_embedding) == 0:
            logger.warning("Embedding generation returned None or empty", extra={
                "operation": "search_concepts_semantic",
                "query": query[:50]
            })
            return database_error(service_name="embedding", operation="generate")

        # Build metadata filter
        where_filter = {}
        if area:
            where_filter["area"] = area
        if topic:
            where_filter["topic"] = topic

        # Perform semantic search in ChromaDB
        collection = chroma_service.get_collection()

        search_params = {
            "query_embeddings": [query_embedding],
            "n_results": limit,
            "include": ["metadatas", "distances"],
        }

        if where_filter:
            search_params["where"] = where_filter

        results_data = collection.query(**search_params)

        # Process results
        concepts = []
        if results_data and results_data.get("ids"):
            ids = results_data["ids"][0]
            metadatas = results_data.get("metadatas", [[]])[0]
            distances = results_data.get("distances", [[]])[0]

            for i, concept_id in enumerate(ids):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0

                # Convert distance to similarity (0-1, where 1 is most similar)
                # For cosine distance: similarity = 1 - distance
                similarity = 1.0 - distance

                # Apply min_confidence filter (post-query filtering)
                # Scores are stored in 0-100 scale
                confidence_score = metadata.get("confidence_score", 0)

                if min_confidence is not None and confidence_score < min_confidence:
                    continue

                concepts.append({
                    "concept_id": concept_id,
                    "name": metadata.get("name", ""),
                    "similarity": round(similarity, 4),
                    "area": metadata.get("area"),
                    "topic": metadata.get("topic"),
                    "confidence_score": confidence_score
                })

        # Sort by similarity (descending)
        concepts.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(f"Semantic search returned {len(concepts)} results")

        if warnings:
            return success_response("Found", results=concepts, total=len(concepts), warnings=warnings)
        return success_response("Found", results=concepts, total=len(concepts))

    except ValueError as e:
        logger.error(f"Validation error in semantic search: {e}", extra={
            "operation": "search_concepts_semantic",
            "query": query,
            "error": str(e)
        })
        return validation_error(str(e))

    except Exception as e:
        logger.error(
            f"Unexpected error in semantic search: {e}",
            exc_info=True,
            extra={"operation": "search_concepts_semantic", "query": query},
        )
        # If it's an embedding error, use specific error type
        if "embedding" in str(e).lower():
            return database_error(service_name="embedding", operation="generate")
        return internal_error(str(e))


@requires_services("neo4j_service")
async def search_concepts_exact(
    name: Optional[str] = None,
    area: Optional[str] = None,
    topic: Optional[str] = None,
    subtopic: Optional[str] = None,
    min_confidence: Optional[float] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search for concepts using exact/filtered criteria (Neo4j).

    This tool performs exact search by:
    1. Building a Cypher query with WHERE clauses
    2. Filtering by name (case-insensitive CONTAINS), area, topic, subtopic, min_confidence
    3. Sorting by created_at DESC

    Args:
        name: Filter by concept name (case-insensitive partial match, optional)
        area: Filter by subject area (exact match, optional)
        topic: Filter by topic (exact match, optional)
        subtopic: Filter by subtopic (exact match, optional)
        min_confidence: Minimum confidence score (0-100, optional)
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        {
            "success": bool,
            "results": [
                {
                    "concept_id": str,
                    "name": str,
                    "area": str,
                    "topic": str,
                    "subtopic": str,
                    "confidence_score": float,
                    "created_at": str
                }
            ],
            "total": int,
            "message": str
        }

    Examples:
        >>> search_concepts_exact(area="Programming", topic="Python")
        >>> search_concepts_exact(name="loop", min_confidence=80)
    """
    try:
        # Validate limit
        if limit < 1 or limit > 100:
            limit = min(max(limit, 1), 100)

        # Build Cypher query dynamically
        where_clauses = []
        params = {}

        # Name filter (case-insensitive CONTAINS)
        if name:
            where_clauses.append("toLower(c.name) CONTAINS toLower($name)")
            params["name"] = name

        # Area filter (exact match)
        if area:
            where_clauses.append("c.area = $area")
            params["area"] = area

        # Topic filter (exact match)
        if topic:
            where_clauses.append("c.topic = $topic")
            params["topic"] = topic

        # Subtopic filter (exact match)
        if subtopic:
            where_clauses.append("c.subtopic = $subtopic")
            params["subtopic"] = subtopic

        # Min confidence filter (score stored as 0-100)
        if min_confidence is not None:
            where_clauses.append("COALESCE(c.confidence_score, 0.0) >= $min_confidence")
            params["min_confidence"] = min_confidence

        # Always filter out deleted concepts
        where_clauses.append("(c.deleted IS NULL OR c.deleted = false)")

        # Build WHERE clause
        where_clause = " AND ".join(where_clauses) if where_clauses else "true"

        # Build complete Cypher query
        query = f"""
        MATCH (c:Concept)
        WHERE {where_clause}
        RETURN c.concept_id AS concept_id, c.name AS name,
               c.area AS area, c.topic AS topic, c.subtopic AS subtopic,
               COALESCE(c.confidence_score, 0.0) AS confidence_score,
               c.created_at AS created_at
        ORDER BY c.confidence_score DESC, c.created_at DESC
        LIMIT $limit
        """

        params["limit"] = limit

        logger.info(f"Executing exact search with filters: {params}")

        # Get Neo4j service from container
        neo4j = _get_neo4j_service()

        # Execute query
        results = neo4j.execute_read(query, params)

        # Process results
        concepts = []
        for record in results:
            concepts.append({
                "concept_id": record.get("concept_id"),
                "name": record.get("name"),
                "area": record.get("area"),
                "topic": record.get("topic"),
                "subtopic": record.get("subtopic"),
                "confidence_score": record.get("confidence_score"),
                "created_at": record.get("created_at")
            })

        logger.info(f"Exact search returned {len(concepts)} results")

        return success_response("Found", results=concepts, total=len(concepts))

    except ValueError as e:
        logger.error(f"Validation error in exact search: {e}", extra={
            "operation": "search_concepts_exact",
            "filters": {"name": name, "area": area, "topic": topic},
            "error": str(e)
        })
        return validation_error(str(e))

    except Exception as e:
        logger.error(f"Unexpected error in exact search: {e}", exc_info=True, extra={
            "operation": "search_concepts_exact",
            "filters": {"name": name, "area": area, "topic": topic}
        })
        return database_error(service_name="neo4j", operation="query")


@requires_services("neo4j_service")
async def get_recent_concepts(days: int = 7, limit: int = 20) -> dict[str, Any]:
    """
    Get recently created or modified concepts.

    This tool retrieves concepts based on the last_modified timestamp,
    useful for quick access to recent work.

    Args:
        days: Number of days to look back (default: 7, min: 1, max: 365)
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        {
            "success": bool,
            "results": [
                {
                    "concept_id": str,
                    "name": str,
                    "area": str,
                    "topic": str,
                    "subtopic": str,
                    "confidence_score": float,
                    "created_at": str,
                    "last_modified": str
                }
            ],
            "total": int,
            "message": str
        }

    Examples:
        >>> get_recent_concepts(days=7, limit=20)
        >>> get_recent_concepts(days=30)  # Last month
    """
    try:
        # Validate days parameter
        warnings = []
        original_days = days
        if days < 1 or days > 365:
            days = min(max(days, 1), 365)
            logger.warning(f"Days parameter out of range, adjusted to {days}")
            warnings.append(f"Days adjusted from {original_days} to {days} (valid range: 1-365)")

        # Validate limit parameter
        original_limit = limit
        if limit < 1 or limit > 100:
            limit = min(max(limit, 1), 100)
            logger.warning(f"Limit parameter out of range, adjusted to {limit}")
            warnings.append(f"Limit adjusted from {original_limit} to {limit} (valid range: 1-100)")

        # Calculate cutoff timestamp
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        logger.info(f"Getting concepts modified since {cutoff_iso} (last {days} days)")

        # Build Cypher query
        query = """
        MATCH (c:Concept)
        WHERE (c.deleted IS NULL OR c.deleted = false)
          AND c.last_modified >= $cutoff
        RETURN c.concept_id AS concept_id, c.name AS name,
               c.area AS area, c.topic AS topic, c.subtopic AS subtopic,
               COALESCE(c.confidence_score, 0.0) AS confidence_score,
               c.created_at AS created_at, c.last_modified AS last_modified
        ORDER BY c.last_modified DESC
        LIMIT $limit
        """

        params = {"cutoff": cutoff_iso, "limit": limit}

        # Get Neo4j service from container
        neo4j = _get_neo4j_service()

        # Execute query
        results = neo4j.execute_read(query, params)

        # Process results
        concepts = []
        for record in results:
            concepts.append({
                "concept_id": record.get("concept_id"),
                "name": record.get("name"),
                "area": record.get("area"),
                "topic": record.get("topic"),
                "subtopic": record.get("subtopic"),
                "confidence_score": record.get("confidence_score"),
                "created_at": record.get("created_at"),
                "last_modified": record.get("last_modified")
            })

        logger.info(f"Recent concepts query returned {len(concepts)} results")

        message = f"Found {len(concepts)} concepts from last {days} days"
        if warnings:
            return success_response(message, results=concepts, total=len(concepts), warnings=warnings)
        return success_response(message, results=concepts, total=len(concepts))

    except ValueError as e:
        logger.error(f"Validation error in get_recent_concepts: {e}", extra={
            "operation": "get_recent_concepts",
            "days": days,
            "limit": limit,
            "error": str(e)
        })
        return validation_error(str(e))

    except Exception as e:
        logger.error(f"Unexpected error in get_recent_concepts: {e}", exc_info=True, extra={
            "operation": "get_recent_concepts",
            "days": days,
            "limit": limit
        })
        return database_error(service_name="neo4j", operation="query")
