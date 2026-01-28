"""
Service Utilities for MCP Tools

Provides decorators and utilities for service availability checking and error handling.
"""

import functools
import logging
from typing import Any, Callable, Dict, Optional

from services.container import get_container, ServiceContainer
from .responses import ErrorType, error_response


logger = logging.getLogger(__name__)


def requires_services(*service_names: str) -> Callable:
    """
    Decorator to check service availability before executing a tool function.

    This decorator protects against null pointer dereferences by validating that
    required services are initialized before the tool logic executes.

    Service lookup order:
    1. 'container' kwarg if provided (for explicit dependency injection)
    2. Global container via get_container()

    Args:
        *service_names: Names of required service variables (as strings)
            Valid service names:
            - 'repository': Main data repository (Neo4j + ChromaDB)
            - 'neo4j_service': Neo4j graph database service
            - 'chromadb_service': ChromaDB vector database service
            - 'embedding_service': Embedding generation service
            - 'event_store': Event sourcing store
            - 'outbox': Outbox pattern for eventual consistency
            - 'confidence_service': Confidence scoring service

    Returns:
        Decorated function that validates service availability

    Raises:
        No exceptions raised - returns error response instead

    Usage:
        @requires_services('repository')
        async def create_concept(...):
            # repository is guaranteed to be non-None here
            return repository.create_concept(...)

        @requires_services('neo4j_service', 'event_store')
        async def create_relationship(...):
            # Both services guaranteed to be non-None
            return neo4j_service.execute_write(...)

    Error Response:
        If any service is None, returns:
        {
            "success": false,
            "error": "Service Unavailable",
            "message": "<service_name> not initialized",
            "error_code": "SERVICE_UNAVAILABLE"
        }

    Security Note:
        This decorator prevents AttributeError crashes when services are not
        initialized. Fixes issues #C001-#C031 (24 critical null pointer issues).
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            # Prefer container kwarg if provided, otherwise use global container
            container: Optional[ServiceContainer] = kwargs.get('container') or get_container()

            # Check each required service
            for service_name in service_names:
                service = getattr(container, service_name, None)

                if service is None:
                    logger.warning(
                        f"Tool '{func.__name__}' called but {service_name} not initialized",
                        extra={
                            "tool": func.__name__,
                            "missing_service": service_name,
                            "required_services": list(service_names),
                        },
                    )
                    return error_response(
                        ErrorType.SERVICE_UNAVAILABLE,
                        f"{service_name} not initialized"
                    )

            # All services available - execute the tool
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_service_status() -> dict[str, dict[str, bool]]:
    """
    Check the initialization status of all services.

    Returns:
        Dict mapping module names to service availability status

    Example:
        {
            "concept_tools": {"repository": True},
            "search_tools": {"neo4j_service": True, "chromadb_service": False},
            ...
        }
    """
    container = get_container()

    status = {
        "concept_tools": {
            "repository": container.repository is not None,
            "confidence_service": container.confidence_service is not None
        },
        "search_tools": {
            "neo4j_service": container.neo4j_service is not None,
            "chromadb_service": container.chromadb_service is not None,
            "embedding_service": container.embedding_service is not None
        },
        "relationship_tools": {
            "neo4j_service": container.neo4j_service is not None,
            "event_store": container.event_store is not None,
            "outbox": container.outbox is not None
        },
        "analytics_tools": {
            "neo4j_service": container.neo4j_service is not None
        }
    }

    return status


def get_available_tools() -> dict[str, Any]:
    """
    Determine which tools are currently available based on service status.

    Returns:
        Dict with 'available' and 'unavailable' lists of tool names

    Example:
        {
            "available": ["ping", "create_concept", ...],
            "unavailable": ["search_concepts_semantic"],
            "total_tools": 17,
            "service_status": {...}
        }
    """
    status = get_service_status()

    # Define tool-to-service dependencies
    tool_dependencies = {
        # Concept tools (4)
        "create_concept": ["concept_tools.repository"],
        "get_concept": ["concept_tools.repository"],
        "update_concept": ["concept_tools.repository"],
        "delete_concept": ["concept_tools.repository"],
        # Search tools (3)
        "search_concepts_semantic": [
            "search_tools.chromadb_service",
            "search_tools.embedding_service",
        ],
        "search_concepts_exact": ["search_tools.neo4j_service"],
        "get_recent_concepts": ["search_tools.neo4j_service"],
        # Relationship tools (5)
        "create_relationship": [
            "relationship_tools.neo4j_service",
            "relationship_tools.event_store",
            "relationship_tools.outbox",
        ],
        "delete_relationship": [
            "relationship_tools.neo4j_service",
            "relationship_tools.event_store",
            "relationship_tools.outbox",
        ],
        "get_related_concepts": ["relationship_tools.neo4j_service"],
        "get_prerequisites": ["relationship_tools.neo4j_service"],
        "get_concept_chain": ["relationship_tools.neo4j_service"],
        # Analytics tools (2)
        "list_hierarchy": ["analytics_tools.neo4j_service"],
        "get_concepts_by_confidence": ["analytics_tools.neo4j_service"],

        # Server tools (no dependencies)
        "ping": [],
        "get_server_stats": [],

        # Taxonomy tools
        "list_areas": ["analytics_tools.neo4j_service"],
    }

    available = []
    unavailable = []

    for tool_name, dependencies in tool_dependencies.items():
        if not dependencies:
            # No dependencies, always available
            available.append(tool_name)
            continue

        # Check if all dependencies are satisfied
        all_satisfied = True
        for dep in dependencies:
            module_name, service_name = dep.split(".")
            if not status.get(module_name, {}).get(service_name, False):
                all_satisfied = False
                break

        if all_satisfied:
            available.append(tool_name)
        else:
            unavailable.append(tool_name)

    return {
        "available": sorted(available),
        "unavailable": sorted(unavailable),
        "total_tools": len(tool_dependencies),
        "service_status": status,
    }
