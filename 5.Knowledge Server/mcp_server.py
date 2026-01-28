"""
MCP Knowledge Management Server
Main entry point for the FastMCP server
"""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from config import Config
from projections.chromadb_projection import ChromaDBProjection
from projections.neo4j_projection import Neo4jProjection
from services.chromadb_service import ChromaDbService
from services.compensation import CompensationManager
from services.confidence.event_listener import ConfidenceEventListener
from services.confidence.runtime import ConfidenceRuntime, build_confidence_runtime
from services.embedding_cache import EmbeddingCache
from services.embedding_service import EmbeddingConfig, EmbeddingService
from services.event_store import EventStore
from services.neo4j_service import Neo4jService
from services.outbox import Outbox
from services.repository import DualStorageRepository
from services.confidence.event_listener import ConfidenceEventListener
from services.confidence.runtime import ConfidenceRuntime, build_confidence_runtime
from services.container import get_container, reset_container

# Import tools
from tools import analytics_tools, concept_tools, relationship_tools, search_tools
from tools.responses import ErrorType, internal_error, success_response
from tools.service_utils import requires_services, get_available_tools, get_service_status

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def _check_migration_status(neo4j_service: Neo4jService) -> None:
    """
    Check if database migration from certainty_score to confidence_score is complete.

    This guard prevents the server from starting with unmigrated data, which would
    cause scores to appear incorrect (0.5 showing as 0.5% instead of 50%).

    Raises:
        RuntimeError: If unmigrated data is detected
    """
    query = """
    MATCH (c:Concept)
    WHERE c.certainty_score IS NOT NULL
    RETURN count(c) AS unmigrated_count
    """
    result = neo4j_service.execute_read(query)

    if result and result[0]["unmigrated_count"] > 0:
        count = result[0]["unmigrated_count"]
        raise RuntimeError(
            f"Database migration required: Found {count} concept(s) with legacy "
            f"'certainty_score' property. The application now uses 'confidence_score' "
            f"with 0-100 scale.\n\n"
            f"To migrate:\n"
            f"  1. Back up your Neo4j database\n"
            f"  2. Run: python scripts/migrate_certainty_to_confidence.py\n"
            f"  3. Restart the server\n\n"
            f"See PRE_COMMIT_FINDINGS.md for details."
        )


async def _run_confidence_worker(
    listener: ConfidenceEventListener,
    *,
    event_signal: asyncio.Event | None = None,
    interval_seconds: float = 5.0,
) -> None:
    """
    Background task that continuously processes confidence events.

    Args:
        listener: ConfidenceEventListener to process events
        event_signal: Optional asyncio.Event to trigger immediate processing
        interval_seconds: Fallback polling interval if no signal provided
    """
    while True:
        try:
            stats = await listener.process_pending_events(limit=200)
            if stats["processed"] or stats["failed"]:
                logger.debug("Confidence worker stats: %s", stats)
        except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation
            raise
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Confidence worker error: %s", exc, exc_info=True)
            await asyncio.sleep(interval_seconds * 2)
        else:
            # Wait for either event signal or timeout
            if event_signal:
                try:
                    await asyncio.wait_for(event_signal.wait(), timeout=interval_seconds)
                except TimeoutError:
                    # Timeout is normal - just means no events in this interval
                    pass
                finally:
                    # Clear signal for next iteration
                    event_signal.clear()
            else:
                # Backwards compatibility: poll-based without signal
                await asyncio.sleep(interval_seconds)


async def initialize():
    """
    Initialize all server services and configure tools.
    This function can be called standalone (for testing) or via the lifespan handler.
    """
    # Get or create the service container
    container = get_container()

    logger.info(f"Initializing {Config.MCP_SERVER_NAME}...")

    try:
        # Initialize event store
        container.event_store = EventStore(db_path=Config.EVENT_STORE_PATH)
        logger.info("✅ Event store initialized")

        # Initialize outbox
        container.outbox = Outbox(db_path=Config.EVENT_STORE_PATH)
        logger.info("✅ Outbox initialized")

        # Initialize Neo4j service with retry logic
        container.neo4j_service = Neo4jService(
            uri=Config.NEO4J_URI,
            user=Config.NEO4J_USER,
            password=Config.NEO4J_PASSWORD
        )

        # Connect to Neo4j with exponential backoff retry
        max_retries = 3
        retry_delays = [2, 4, 8]  # seconds
        neo4j_connected = False

        for attempt in range(max_retries):
            logger.info(f"Connecting to Neo4j (attempt {attempt + 1}/{max_retries})...")
            if container.neo4j_service.connect():
                neo4j_connected = True
                logger.info("✅ Neo4j service connected")

                # Check for unmigrated data before proceeding
                logger.info("Checking database migration status...")
                _check_migration_status(container.neo4j_service)
                logger.info("✅ Database migration check passed")

                break
            else:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(f"⚠️  Neo4j connection failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("❌ Neo4j connection failed after all retries")

        if not neo4j_connected:
            raise RuntimeError(
                "Failed to connect to Neo4j after 3 attempts. "
                "Please ensure Neo4j is running and credentials are correct. "
                f"Connection URI: {Config.NEO4J_URI}"
            )

        # Initialize ChromaDB service
        container.chromadb_service = ChromaDbService(
            persist_directory=Config.CHROMA_PERSIST_DIRECTORY,
            collection_name="concepts"
        )

        # Connect to ChromaDB
        logger.info("Connecting to ChromaDB...")
        if not container.chromadb_service.connect():
            raise RuntimeError(
                "Failed to connect to ChromaDB. "
                f"Persist directory: {Config.CHROMA_PERSIST_DIRECTORY}"
            )
        logger.info("✅ ChromaDB service connected")

        # Initialize and load embedding service
        embedding_config = EmbeddingConfig(
            model_name=Config.EMBEDDING_MODEL,
            backend=Config.EMBEDDING_BACKEND
        )
        container.embedding_service = EmbeddingService(config=embedding_config)

        logger.info(f"Initializing embedding service: {Config.EMBEDDING_MODEL} (backend: {Config.EMBEDDING_BACKEND})...")
        model_loaded = await container.embedding_service.initialize()
        if not model_loaded:
            logger.warning(
                "⚠️  Embedding model failed to load - semantic search will be degraded. "
                f"Model: {Config.EMBEDDING_MODEL}"
            )
        else:
            logger.info("✅ Embedding service initialized and model loaded")

        # Initialize embedding cache
        embedding_cache = EmbeddingCache(db_path=Config.EVENT_STORE_PATH)
        logger.info("✅ Embedding cache initialized")

        # Initialize projections
        neo4j_projection = Neo4jProjection(container.neo4j_service)
        chromadb_projection = ChromaDBProjection(container.chromadb_service)
        logger.info("✅ Projections initialized")

        # Initialize compensation manager with SQLite connection
        import sqlite3

        compensation_connection = sqlite3.connect(Config.EVENT_STORE_PATH)
        compensation_manager = CompensationManager(
            neo4j_service=container.neo4j_service,
            chromadb_service=container.chromadb_service,
            connection=compensation_connection
        )
        logger.info("✅ Compensation manager initialized")

        # Initialize repository
        container.repository = DualStorageRepository(
            event_store=container.event_store,
            outbox=container.outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=container.embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )
        logger.info("✅ Repository initialized")

        # Initialize confidence scoring runtime (optional)
        if container.confidence_listener_task:
            container.confidence_listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await container.confidence_listener_task
            container.confidence_listener_task = None
        container.confidence_listener = None
        if container.confidence_runtime:
            await container.confidence_runtime.close()
            container.confidence_runtime = None
        container.confidence_runtime = await build_confidence_runtime(
            container.neo4j_service,
            event_store=container.event_store,
            outbox=container.outbox,
            neo4j_projection=neo4j_projection,
        )
        if container.confidence_runtime:
            container.confidence_listener = ConfidenceEventListener(
                event_store=container.event_store,
                calculator=container.confidence_runtime.calculator,
                cache_manager=container.confidence_runtime.cache_manager,
                neo4j_service=container.neo4j_service,
            )
            container.confidence_listener_task = asyncio.create_task(
                _run_confidence_worker(
                    container.confidence_listener,
                    event_signal=container.event_store.new_event_signal
                )
            )
            logger.info("✅ Confidence event listener started")
        else:
            container.confidence_listener = None
            container.confidence_listener_task = None
            logger.warning(
                "Confidence scoring runtime unavailable; automated confidence scores disabled."
            )

        logger.info("✅ Tools configured")

        # Validate service health before marking server as ready
        logger.info("Validating service health...")

        # Check Neo4j health
        neo4j_health = container.neo4j_service.health_check()
        if neo4j_health.get("status") != "healthy":
            logger.error(f"❌ Neo4j health check failed: {neo4j_health}")
            raise RuntimeError(
                f"Neo4j service is unhealthy: {neo4j_health.get('error', 'Unknown error')}"
            )
        logger.info(
            f"✅ Neo4j health check passed (latency: {neo4j_health.get('latency_ms', 'N/A')}ms)"
        )

        # Check ChromaDB health
        chromadb_health = container.chromadb_service.health_check()
        if chromadb_health.get("status") != "healthy":
            logger.error(f"❌ ChromaDB health check failed: {chromadb_health}")
            raise RuntimeError(
                f"ChromaDB service is unhealthy: {chromadb_health.get('error', 'Unknown error')}"
            )
        logger.info(
            f"✅ ChromaDB health check passed (collection: {chromadb_health.get('collection_name', 'N/A')})"
        )

        # Check Embedding service health (allow degraded mode)
        embedding_health = container.embedding_service.health_check()
        if embedding_health.get("status") == "healthy":
            logger.info(
                f"✅ Embedding service health check passed (model: {embedding_health.get('model', 'N/A')})"
            )
        else:
            logger.warning(
                f"⚠️  Embedding service is degraded: {embedding_health.get('error', 'Model not loaded')} "
                "- Semantic search will use fallback behavior"
            )

        logger.info(f"🚀 {Config.MCP_SERVER_NAME} ready!")
        logger.info(f"   • Neo4j: {Config.NEO4J_URI}")
        logger.info(f"   • ChromaDB: {Config.CHROMA_PERSIST_DIRECTORY}")
        logger.info(f"   • Embedding Model: {Config.EMBEDDING_MODEL}")
        logger.info("   • Tools: 17 concept management tools available")

    except Exception as e:
        logger.error(f"❌ Failed to initialize server: {e}", exc_info=True)
        raise


@asynccontextmanager
async def lifespan(server: FastMCP):
    """
    FastMCP lifespan handler - initializes services on startup and cleans up on shutdown.
    This context manager is called automatically by FastMCP when the server starts.
    """
    # Initialize all services
    await initialize()

    # Yield control to the FastMCP server - server runs while yielded
    yield

    # Cleanup on shutdown (after yield)
    logger.info(f"Shutting down {Config.MCP_SERVER_NAME}...")

    # Use container's shutdown method for graceful cleanup
    container = get_container()
    await container.shutdown()

    logger.info("✅ Server shutdown complete")


# Initialize FastMCP server with lifespan handler
mcp = FastMCP(Config.MCP_SERVER_NAME, lifespan=lifespan)


@mcp.tool()
async def ping() -> dict[str, Any]:
    """
    Simple ping tool to test MCP server connectivity

    Returns:
        Dictionary with server status and timestamp
    """
    from datetime import datetime

    return {
        "status": "ok",
        "message": "MCP Knowledge Server is running",
        "server_name": Config.MCP_SERVER_NAME,
        "timestamp": datetime.now().isoformat(),
    }


@mcp.tool()
@requires_services("event_store", "outbox")
async def get_server_stats() -> dict[str, Any]:
    """
    Get server statistics

    Returns:
        Dictionary with event store and outbox statistics
    """
    try:
        container = get_container()

        # Get event store stats
        total_events = container.event_store.count_events()
        concept_events = container.event_store.count_events(event_type="ConceptCreated")

        # Get outbox stats
        outbox_counts = container.outbox.count_by_status()

        return {
            "success": True,
            "event_store": {"total_events": total_events, "concept_events": concept_events},
            "outbox": outbox_counts,
            "status": "healthy",
        }
    except Exception as e:
        logger.error(f"Error getting server stats: {e}", exc_info=True, extra={
            "operation": "get_server_stats"
        })
        err_response = internal_error("Failed to get server stats")
        err_response["status"] = "error"
        return err_response


@mcp.tool()
async def get_tool_availability() -> dict[str, Any]:
    """
    Check which MCP tools are currently available based on service initialization status.

    This diagnostic tool helps troubleshoot MCP server issues by showing:
    - Which tools are available and can be used
    - Which tools are unavailable due to missing services
    - The initialization status of all backend services
    - Total tool count

    Use this tool when:
    - MCP tools are not responding or throwing errors
    - You want to verify server initialization completed successfully
    - Debugging service connectivity issues

    Returns:
        {
            "success": True,
            "available": [...],         # List of available tool names
            "unavailable": [...],       # List of unavailable tool names
            "total_tools": int,        # Total number of tools (16)
            "service_status": {        # Detailed service initialization status
                "concept_tools": {...},
                "search_tools": {...},
                "relationship_tools": {...},
                "analytics_tools": {...}
            }
        }

    Example Response:
        {
            "success": True,
            "available": ["ping", "create_concept", "get_concept", ...],
            "unavailable": [],
            "total_tools": 16,
            "service_status": {
                "concept_tools": {
                    "repository": True,
                    "confidence_service": True
                },
                "search_tools": {
                    "neo4j_service": True,
                    "chromadb_service": True,
                    "embedding_service": True
                },
                ...
            }
        }
    """
    try:
        tool_status = get_available_tools()
        return {"success": True, **tool_status}
    except Exception as e:
        logger.error(f"Error checking tool availability: {e}", exc_info=True, extra={
            "operation": "get_tool_availability"
        })
        return internal_error(str(e))


# =============================================================================
# Concept Management Tools
# =============================================================================


@mcp.tool()
async def create_concept(
    name: str,
    explanation: str,
    area: str,
    topic: str,
    subtopic: str | None = None,
    source_urls: str | None = None,
) -> dict[str, Any]:
    """
    Create a new concept in the knowledge base.

    This tool creates a concept in both Neo4j (graph structure) and ChromaDB (vector search).
    Confidence scores are calculated automatically based on concept quality.

    Args:
        name: Concept name (required)
        explanation: Detailed explanation (required)
        area: Subject area (required, e.g., "coding-development", "ai-llms")
        topic: Topic within area (required, e.g., "Python", "Memory Techniques")
        subtopic: More specific classification (optional)
        source_urls: Optional JSON string containing array of source URL objects (optional)
            Format: '[{"url": "https://...", "title": "...", "quality_score": 0.8, "domain_category": "official"}]'

    Returns:
        {
            "success": bool,
            "message": str,
            "data": {
                "concept_id": str,
                "warnings": [str]  # optional
            }
        }
    """
    return await concept_tools.create_concept(
        name=name,
        explanation=explanation,
        area=area,
        topic=topic,
        subtopic=subtopic,
        source_urls=source_urls,
    )


@mcp.tool()
async def get_concept(concept_id: str, include_history: bool = False) -> dict[str, Any]:
    """
    Retrieve a concept by ID.

    Args:
        concept_id: UUID of the concept
        include_history: Include explanation history (default: False)

    Returns:
        {"success": bool, "concept": {...}, "message": str}
    """
    return await concept_tools.get_concept(concept_id=concept_id, include_history=include_history)


@mcp.tool()
async def update_concept(
    concept_id: str,
    explanation: str | None = None,
    name: str | None = None,
    area: str | None = None,
    topic: str | None = None,
    subtopic: str | None = None,
    source_urls: str | None = None,
) -> dict[str, Any]:
    """
    Update an existing concept (partial updates supported).

    Explanation changes are tracked in history. Embeddings are regenerated if needed.
    Confidence scores are recalculated automatically when concept is updated.

    Args:
        concept_id: UUID of the concept
        explanation: Updated explanation (optional)
        name: Updated name (optional)
        area: Updated area (optional)
        topic: Updated topic (optional)
        subtopic: Updated subtopic (optional)
        source_urls: Optional JSON string containing array of source URL objects (optional)
            Format: '[{"url": "https://...", "title": "...", "quality_score": 0.8, "domain_category": "official"}]'

    Returns:
        {"success": bool, "updated_fields": [...], "message": str}
    """
    return await concept_tools.update_concept(
        concept_id=concept_id,
        explanation=explanation,
        name=name,
        area=area,
        topic=topic,
        subtopic=subtopic,
        source_urls=source_urls,
    )


@mcp.tool()
async def delete_concept(concept_id: str) -> dict[str, Any]:
    """
    Delete a concept (soft delete).

    Args:
        concept_id: UUID of the concept to delete

    Returns:
        {"success": bool, "concept_id": str, "message": str}
    """
    return await concept_tools.delete_concept(concept_id=concept_id)


@mcp.tool()
async def search_concepts_semantic(
    query: str,
    limit: int = 10,
    min_confidence: float = None,
    area: str = None,
    topic: str = None
) -> Dict[str, Any]:
    """
    Search for concepts using semantic similarity (ChromaDB embeddings).

    Performs semantic search by generating an embedding for the query and finding
    similar concepts using cosine similarity. Optionally filters by metadata.

    Args:
        query: Natural language search query (required)
        limit: Maximum number of results (default: 10, max: 50)
        min_confidence: Minimum confidence score filter (0-100, optional)
        area: Filter by subject area (optional)
        topic: Filter by topic (optional)

    Returns:
        {"success": bool, "results": [...], "total": int, "message": str}
    """
    return await search_tools.search_concepts_semantic(
        query=query,
        limit=limit,
        min_confidence=min_confidence,
        area=area,
        topic=topic
    )


@mcp.tool()
async def search_concepts_exact(
    name: str = None,
    area: str = None,
    topic: str = None,
    subtopic: str = None,
    min_confidence: float = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search for concepts using exact/filtered criteria (Neo4j).

    Performs exact search by building a Cypher query with WHERE clauses.
    Filters by name (case-insensitive partial match), area, topic, subtopic,
    and minimum confidence score.

    Args:
        name: Filter by concept name (case-insensitive partial match, optional)
        area: Filter by subject area (exact match, optional)
        topic: Filter by topic (exact match, optional)
        subtopic: Filter by subtopic (exact match, optional)
        min_confidence: Minimum confidence score (0-100, optional)
        limit: Maximum number of results (default: 20, max: 100)

    Returns:
        {"success": bool, "results": [...], "total": int, "message": str}
    """
    return await search_tools.search_concepts_exact(
        name=name,
        area=area,
        topic=topic,
        subtopic=subtopic,
        min_confidence=min_confidence,
        limit=limit
    )


@mcp.tool()
async def get_recent_concepts(days: int = 7, limit: int = 20) -> dict[str, Any]:
    """
    Get recently created or modified concepts.

    Retrieves concepts based on the last_modified timestamp, useful for
    quick access to recent work. Automatically filters out deleted concepts.

    Args:
        days: Number of days to look back (default: 7, min: 1, max: 365)
        limit: Maximum number of results (default: 20, max: 100)

    Returns:
        {"success": bool, "results": [...], "total": int, "message": str}
    """
    return await search_tools.get_recent_concepts(days=days, limit=limit)


@mcp.tool()
async def create_relationship(
    source_id: str,
    target_id: str,
    relationship_type: str,
    strength: float = 1.0,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Create a relationship between two concepts.

    Creates a directed relationship in the knowledge graph with support for
    different relationship types and strength indicators.

    Args:
        source_id: ID of the source concept (required)
        target_id: ID of the target concept (required)
        relationship_type: Type of relationship - "prerequisite", "relates_to", or "includes" (required)
        strength: Strength of the relationship, 0.0-1.0 (default: 1.0)
        notes: Optional notes or description for the relationship

    Returns:
        {"success": bool, "relationship_id": str, "message": str}
    """
    return await relationship_tools.create_relationship(
        source_id=source_id,
        target_id=target_id,
        relationship_type=relationship_type,
        strength=strength,
        notes=notes,
    )


@mcp.tool()
async def delete_relationship(
    source_id: str, target_id: str, relationship_type: str
) -> dict[str, Any]:
    """
    Delete a relationship between two concepts.

    Removes a relationship from the knowledge graph using soft delete.
    The relationship is marked as deleted in Neo4j, and the event is stored for audit trail.

    Args:
        source_id: ID of the source concept (required)
        target_id: ID of the target concept (required)
        relationship_type: Type of relationship to delete - "prerequisite", "relates_to", or "includes" (required)

    Returns:
        {"success": bool, "message": str}
    """
    return await relationship_tools.delete_relationship(
        source_id=source_id, target_id=target_id, relationship_type=relationship_type
    )


@mcp.tool()
async def get_related_concepts(
    concept_id: str,
    relationship_type: str | None = None,
    direction: str = "outgoing",
    max_depth: int = 1,
) -> dict[str, Any]:
    """
    Get concepts related to a given concept through graph traversal.

    Traverses the knowledge graph to find related concepts with flexible
    direction and depth control.

    Args:
        concept_id: Starting concept ID (required)
        relationship_type: Optional filter - "prerequisite", "relates_to", or "includes"
        direction: Traversal direction - "outgoing", "incoming", or "both" (default: "outgoing")
        max_depth: Maximum hops to traverse, 1-5 (default: 1)

    Returns:
        {
            "concept_id": str,
            "related": [{"concept_id": str, "name": str, "relationship_type": str, "strength": float, "distance": int}],
            "total": int
        }
    """
    return await relationship_tools.get_related_concepts(
        concept_id=concept_id,
        relationship_type=relationship_type,
        direction=direction,
        max_depth=max_depth,
    )


@mcp.tool()
async def get_prerequisites(concept_id: str, max_depth: int = 5) -> dict[str, Any]:
    """
    Get complete prerequisite chain for a concept.

    Traverses PREREQUISITE relationships to build a learning path,
    ordered from deepest prerequisites to the target concept.

    Args:
        concept_id: Target concept ID (required)
        max_depth: Maximum chain depth, 1-10 (default: 5)

    Returns:
        {
            "concept_id": str,
            "chain": [{"concept_id": str, "name": str, "depth": int}],
            "total": int
        }
    """
    return await relationship_tools.get_prerequisites(concept_id=concept_id, max_depth=max_depth)


@mcp.tool()
async def get_concept_chain(
    start_id: str, end_id: str, relationship_type: str | None = None
) -> dict[str, Any]:
    """
    Find shortest path between two concepts.

    Uses Neo4j's shortestPath algorithm to find the most direct
    connection between concepts in the knowledge graph.

    Args:
        start_id: Starting concept ID (required)
        end_id: Target concept ID (required)
        relationship_type: Optional relationship filter - "prerequisite", "relates_to", or "includes"

    Returns:
        {
            "success": bool,
            "path": [{"concept_id": str, "name": str}],
            "length": int
        }
    """
    return await relationship_tools.get_concept_chain(
        start_id=start_id, end_id=end_id, relationship_type=relationship_type
    )


# =============================================================================
# Analytics and Hierarchy Tools
# =============================================================================


@mcp.tool()
async def list_hierarchy() -> dict[str, Any]:
    """
    Get complete knowledge hierarchy with concept counts.

    Returns a nested structure showing areas, topics, and subtopics with
    concept counts at each level. Results are cached for 5 minutes.

    Returns:
        {
            "success": bool,
            "message": str
            "data": {
                "areas": [
                    {
                        "name": str,  # slug
                        "label": str,
                        "description": str,
                        "is_predefined": bool,
                        "concept_count": int,
                        "topics": [
                            {
                                "name": str,
                                "concept_count": int,
                                "subtopics": [{"name": str, "concept_count": int}]
                            }
                        ]
                    }
                ],
                "total_concepts": int
            }
        }
    """
    return await analytics_tools.list_hierarchy()


@mcp.tool()
async def list_areas() -> dict[str, Any]:
    """
    Get list of all knowledge areas with concept counts.

    Returns a flat list of top-level areas without nested topics/subtopics.
    More lightweight than list_hierarchy() when only area-level info is needed.

    Returns:
        {
            "success": bool,
            "message": str,
            "data": {
                "areas": [
                    {
                        "name": str,
                        "label": str,
                        "description": str,
                        "concept_count": int,
                        "is_predefined": bool
                    }
                ],
                "total_areas": int,
                "total_concepts": int
            }
        }
    """
    return await analytics_tools.list_areas()


@mcp.tool()
async def get_concepts_by_confidence(
    min_confidence: float = 0,
    max_confidence: float = 100,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get concepts filtered by confidence score range.

    Useful for finding concepts that need review (low confidence) or
    well-established concepts (high confidence).

    Args:
        min_confidence: Minimum confidence score, 0-100 (default: 0)
        max_confidence: Maximum confidence score, 0-100 (default: 100)
        limit: Maximum results, 1-50 (default: 20)

    Returns:
        {
            "success": bool,
            "results": [{"concept_id": str, "name": str, "confidence_score": float, ...}],
            "total": int,
            "message": str
        }
    """
    return await analytics_tools.get_concepts_by_confidence(
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        limit=limit
    )


# =============================================================================
# MCP Resources
# =============================================================================


@mcp.resource("concept://{concept_id}")
async def get_concept_resource(concept_id: str) -> str:
    """
    Retrieve a concept as an MCP resource.

    Provides complete concept details including all fields and explanation
    history as a JSON string for MCP client caching.

    Args:
        concept_id: UUID of the concept

    Returns:
        JSON string with complete concept data
    """
    import json

    # Get concept with history included
    result = await concept_tools.get_concept(concept_id=concept_id, include_history=True)

    return json.dumps(result, indent=2)


@mcp.resource("hierarchy://areas")
async def get_hierarchy_resource() -> str:
    """
    Get knowledge hierarchy as an MCP resource.

    Returns the complete hierarchy structure as a JSON string.
    Results are cached for 5 minutes for performance.

    Returns:
        JSON string with hierarchy data
    """
    import json

    result = await analytics_tools.list_hierarchy()

    return json.dumps(result, indent=2)


def main():
    """Main entry point"""
    logger.info(f"Starting {Config.MCP_SERVER_NAME}...")

    try:
        # Run the MCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
