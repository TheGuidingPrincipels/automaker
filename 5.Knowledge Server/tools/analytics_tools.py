"""
MCP Tools for Analytics and Hierarchy Operations

Provides analytics capabilities and knowledge hierarchy navigation through
the Model Context Protocol.

Data Access Pattern (Read-Only):
    - Hierarchy queries: Uses neo4j_service with in-memory caching (5-min TTL)
    - Confidence filtering: Uses neo4j_service for score-based queries

Caching Strategy:
    - list_hierarchy(): Cached for 5 minutes (expensive aggregation)
    - get_concepts_by_confidence(): Not cached (parameterized queries)

For write operations, use concept_tools which routes through
DualStorageRepository to maintain event sourcing integrity.

See docs/adr/001-data-access-patterns.md for architecture guidelines.
See docs/adr/003-caching-strategy.md for caching documentation.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from services.container import get_container, ServiceContainer
from .responses import (
    ErrorType,
    success_response,
    validation_error,
    internal_error,
)
from .service_utils import requires_services


logger = logging.getLogger(__name__)


def _get_neo4j_service(container: Optional[ServiceContainer] = None):
    """Get Neo4j service from container."""
    if container is not None and container.neo4j_service is not None:
        return container.neo4j_service
    return get_container().neo4j_service


# =============================================================================
# Thread-Safe Caching Infrastructure
# =============================================================================

@dataclass
class CacheEntry:
    """Represents a cached value with timestamp for TTL validation."""
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    service_id: Optional[int] = None

    def is_valid(self, ttl_seconds: int, current_service_id: Optional[int] = None) -> bool:
        """Check if cache entry is still valid."""
        # Invalidate if service instance changed (test isolation)
        if current_service_id is not None and self.service_id != current_service_id:
            return False
        # Check TTL
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed < ttl_seconds


class QueryCache:
    """
    Thread-safe in-memory cache for query results.

    Usage:
        cache = QueryCache(default_ttl=300)  # 5-minute default TTL
        cache.set('hierarchy', result, service_id=id(neo4j_service))
        result = cache.get('hierarchy', service_id=id(neo4j_service))
    """

    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str, service_id: Optional[int] = None) -> Optional[Any]:
        """Get cached value if valid, None otherwise."""
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.is_valid(self._default_ttl, service_id):
                return entry.data
            elif entry:
                del self._cache[key]  # Expired or service changed
            return None

    def set(self, key: str, data: Any, service_id: Optional[int] = None):
        """Store value in cache."""
        with self._lock:
            self._cache[key] = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                service_id=service_id
            )

    def invalidate(self, key: str):
        """Remove specific key from cache."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()


# Module-level cache instance (5-minute TTL)
_CACHE_TTL_SECONDS = 300
_query_cache = QueryCache(default_ttl=_CACHE_TTL_SECONDS)


# =============================================================================
# MCP Tool Functions
# =============================================================================


@requires_services("neo4j_service")
async def list_hierarchy() -> dict[str, Any]:
    """
    Get complete knowledge hierarchy with concept counts.

    Builds a nested structure showing:
    - Areas (top level)
      - Topics (within each area)
        - Subtopics (within each topic)

    Each level includes the count of concepts it contains.

    Returns:
        {
            "success": bool,
            "areas": [
                {
                    "name": str,
                    "concept_count": int,
                    "topics": [
                        {
                            "name": str,
                            "concept_count": int,
                            "subtopics": [
                                {
                                    "name": str,
                                    "concept_count": int
                                }
                            ]
                        }
                    ]
                }
            ],
            "total_concepts": int,
            "message": str
        }

    Note:
        Results are cached for 5 minutes for performance optimization.
        Cache is thread-safe and automatically invalidates when service changes.
    """
    try:
        # Get Neo4j service from container
        neo4j = _get_neo4j_service()

        # Check cache (thread-safe, handles service_id for test isolation)
        current_service_id = id(neo4j)
        cached_result = _query_cache.get('hierarchy', service_id=current_service_id)
        if cached_result is not None:
            logger.info("Returning cached hierarchy")
            return cached_result

        logger.info("Building knowledge hierarchy from Neo4j")

        # Query to get all concepts grouped by area/topic/subtopic
        query = """
        MATCH (c:Concept)
        WHERE (c.deleted IS NULL OR c.deleted = false)
        WITH c.area as area,
             c.topic as topic,
             c.subtopic as subtopic,
             count(*) as count
        RETURN area, topic, subtopic, count
        ORDER BY area, topic, subtopic
        """

        results = neo4j.execute_read(query, {})

        # Build nested structure
        areas_dict = {}
        total_concepts = 0

        for record in results:
            area = record.get("area") or "Uncategorized"
            topic = record.get("topic") or "General"
            subtopic = record.get("subtopic") or "General"
            count = record.get("count", 0)

            total_concepts += count

            # Ensure area exists
            if area not in areas_dict:
                areas_dict[area] = {"name": area, "concept_count": 0, "topics": {}}

            # Ensure topic exists
            if topic not in areas_dict[area]["topics"]:
                areas_dict[area]["topics"][topic] = {
                    "name": topic,
                    "concept_count": 0,
                    "subtopics": {},
                }

            # Add subtopic
            if subtopic not in areas_dict[area]["topics"][topic]["subtopics"]:
                areas_dict[area]["topics"][topic]["subtopics"][subtopic] = {
                    "name": subtopic,
                    "concept_count": 0,
                }

            # Update counts
            areas_dict[area]["topics"][topic]["subtopics"][subtopic]["concept_count"] += count
            areas_dict[area]["topics"][topic]["concept_count"] += count
            areas_dict[area]["concept_count"] += count

        # Convert nested dicts to lists
        areas_list = []
        for _area_name, area_data in sorted(areas_dict.items()):
            topics_list = []
            for _topic_name, topic_data in sorted(area_data["topics"].items()):
                subtopics_list = [
                    {"name": subtopic_data["name"], "concept_count": subtopic_data["concept_count"]}
                    for subtopic_name, subtopic_data in sorted(topic_data["subtopics"].items())
                ]

                topics_list.append(
                    {
                        "name": topic_data["name"],
                        "concept_count": topic_data["concept_count"],
                        "subtopics": subtopics_list,
                    }
                )

            areas_list.append(
                {
                    "name": area_data["name"],
                    "concept_count": area_data["concept_count"],
                    "topics": topics_list,
                }
            )

        message = f"Hierarchy contains {len(areas_list)} areas with {total_concepts} concepts"
        result = success_response(message, areas=areas_list, total_concepts=total_concepts)

        # Update cache (thread-safe)
        _query_cache.set('hierarchy', result, service_id=current_service_id)

        logger.info(f"Hierarchy built: {len(areas_list)} areas, {total_concepts} concepts")

        return result

    except ValueError as e:
        logger.warning(f"Validation error in list_hierarchy: {e}", extra={
            "operation": "list_hierarchy",
            "error": str(e)
        })
        return validation_error(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in list_hierarchy: {e}", exc_info=True, extra={
            "operation": "list_hierarchy"
        })
        return internal_error(str(e))


@requires_services('neo4j_service')
async def get_concepts_by_confidence(
    min_confidence: float = 0,
    max_confidence: float = 100,
    limit: int = 20,
    sort_order: str = "asc"
) -> Dict[str, Any]:
    """
    Get concepts filtered by confidence score range.

    Useful for identifying concepts that need review (low confidence) or
    finding well-established concepts (high confidence).

    Args:
        min_confidence: Minimum confidence score (0-100, default: 0)
        max_confidence: Maximum confidence score (0-100, default: 100)
        limit: Maximum number of results (1-50, default: 20)
        sort_order: Sort direction - 'asc' for learning mode (lowest confidence first),
                    'desc' for discovery mode (highest confidence first).
                    Default: 'asc' (learning-first approach)

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

    Note:
        Results are sorted by confidence_score in the specified order.
        - 'asc' (default): Learning mode - surfaces concepts needing work (lowest confidence first)
        - 'desc': Discovery mode - surfaces well-established concepts (highest confidence first)
        Invalid sort_order values default to 'asc' for learning-first approach.
    """
    try:
        # Validate and adjust parameters
        warnings = []
        original_min = min_confidence
        original_max = max_confidence
        original_limit = limit

        if min_confidence < 0:
            min_confidence = 0
            warnings.append(f"Min confidence adjusted from {original_min} to 0 (minimum value)")
        if max_confidence > 100:
            max_confidence = 100
            warnings.append(f"Max confidence adjusted from {original_max} to 100 (maximum value)")
        if min_confidence > max_confidence:
            min_confidence, max_confidence = max_confidence, min_confidence
            warnings.append(f"Min/max confidence swapped: min was {original_min}, max was {original_max} (min must be <= max)")

        if limit < 1:
            limit = 1
            warnings.append(f"Limit adjusted from {original_limit} to 1 (minimum value)")
        elif limit > 50:
            limit = 50
            warnings.append(f"Limit adjusted from {original_limit} to 50 (maximum value)")

        # Validate and normalize sort_order (case-insensitive, default to 'asc')
        sort_order = sort_order.lower() if sort_order else "asc"
        if sort_order not in ["asc", "desc"]:
            sort_order = "asc"  # Default to learning mode for invalid values

        # Map sort_order to SQL ORDER BY direction
        order_by_direction = "ASC" if sort_order == "asc" else "DESC"

        logger.info(
            f"Getting concepts by confidence: range [{min_confidence}, {max_confidence}], "
            f"limit={limit}, sort_order={sort_order}"
        )

        # Get Neo4j service from container
        neo4j = _get_neo4j_service()

        # Query concepts within confidence range
        # Scores are stored as 0-100 in Neo4j
        # COALESCE handles NULL confidence_score by treating it as 0 (fixes #H003)
        # sort_order: 'asc' = learning mode (lowest confidence first), 'desc' = discovery mode (highest first)
        query = f"""
        MATCH (c:Concept)
        WHERE COALESCE(c.confidence_score, 0.0) >= $min_confidence
          AND COALESCE(c.confidence_score, 0.0) <= $max_confidence
          AND (c.deleted IS NULL OR c.deleted = false)
        RETURN c.concept_id as concept_id,
               c.name as name,
               c.area as area,
               c.topic as topic,
               c.subtopic as subtopic,
               COALESCE(c.confidence_score, 0.0) as confidence_score,
               c.created_at as created_at
        ORDER BY c.confidence_score {order_by_direction}, c.name
        LIMIT $limit
        """

        results = neo4j.execute_read(query, {
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "limit": limit
        })

        # Format results
        formatted_results = []
        for record in results:
            formatted_results.append({
                "concept_id": record.get("concept_id"),
                "name": record.get("name"),
                "area": record.get("area"),
                "topic": record.get("topic"),
                "subtopic": record.get("subtopic"),
                "confidence_score": float(record.get("confidence_score", 0)),
                "created_at": record.get("created_at")
            })

        logger.info(f"Found {len(formatted_results)} concepts in confidence range")

        message = f"Found {len(formatted_results)} concepts with confidence between {min_confidence} and {max_confidence}"

        if warnings:
            return success_response(
                message,
                results=formatted_results,
                total=len(formatted_results),
                warnings=warnings
            )
        return success_response(message, results=formatted_results, total=len(formatted_results))

    except ValueError as e:
        logger.warning(f"Validation error in get_concepts_by_confidence: {e}", extra={
            "operation": "get_concepts_by_confidence",
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "limit": limit,
            "error": str(e)
        })
        return validation_error(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_concepts_by_confidence: {e}", exc_info=True, extra={
            "operation": "get_concepts_by_confidence",
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "limit": limit
        })
        return internal_error(str(e))
