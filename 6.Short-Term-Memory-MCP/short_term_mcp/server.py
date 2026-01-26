"""FastMCP server entry point for Short-Term Memory MCP Server"""

import asyncio
import logging
from typing import List, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from . import tools_impl
from .config import CACHE_TTL, DB_PATH
from .database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Background task handle
_cleanup_task = None

# Initialize MCP server
mcp = FastMCP("Short-term Memory MCP")


@mcp.tool()
async def initialize_daily_session(
    learning_goal: str, building_goal: str, date: str | None = None
) -> dict:
    """
    Initialize a new daily learning session.

    Args:
        learning_goal: What you want to learn today
        building_goal: What you want to build today
        date: Session date (YYYY-MM-DD), defaults to today

    Returns:
        Session information including session_id
    """
    return await tools_impl.initialize_daily_session_impl(learning_goal, building_goal, date)


@mcp.tool()
async def get_active_session(date: str | None = None) -> dict:
    """
    Get today's active session with concept statistics.

    Args:
        date: Session date (YYYY-MM-DD), defaults to today

    Returns:
        Session info with concept counts by status
    """
    return await tools_impl.get_active_session_impl(date)


@mcp.tool()
async def store_concepts_from_research(session_id: str, concepts: list[dict]) -> dict:
    """
    Store all concepts identified in Research session (bulk operation).

    Args:
        session_id: Session ID (YYYY-MM-DD)
        concepts: List of concept dictionaries with concept_name and data

    Returns:
        Summary of concepts created
    """
    return await tools_impl.store_concepts_from_research_impl(session_id, concepts)


@mcp.tool()
async def get_concepts_by_session(
    session_id: str, status_filter: str | None = None, include_stage_data: bool = False
) -> dict:
    """
    Get all concepts for a session, optionally filtered by status.

    Args:
        session_id: Session ID
        status_filter: Filter by status (identified/chunked/encoded/evaluated/stored)
        include_stage_data: Include stage-by-stage data for each concept

    Returns:
        List of concepts with their data
    """
    return await tools_impl.get_concepts_by_session_impl(
        session_id, status_filter, include_stage_data
    )


@mcp.tool()
async def update_concept_status(
    concept_id: str, new_status: str, timestamp: str | None = None
) -> dict:
    """
    Update a concept's status and timestamp.

    Args:
        concept_id: Concept ID
        new_status: New status (chunked/encoded/evaluated/stored)
        timestamp: Optional timestamp (ISO format), defaults to now

    Returns:
        Status update confirmation
    """
    return await tools_impl.update_concept_status_impl(concept_id, new_status, timestamp)


@mcp.tool()
async def store_stage_data(concept_id: str, stage: str, data: dict) -> dict:
    """
    Store stage-specific data for a concept.

    Args:
        concept_id: Concept ID
        stage: Stage name (research/aim/shoot/skin)
        data: Stage-specific data dictionary

    Returns:
        Confirmation of data storage
    """
    return await tools_impl.store_stage_data_impl(concept_id, stage, data)


@mcp.tool()
async def get_stage_data(concept_id: str, stage: str) -> dict:
    """
    Retrieve stage-specific data for a concept.

    Args:
        concept_id: Concept ID
        stage: Stage name (research/aim/shoot/skin)

    Returns:
        Stage data or not_found status
    """
    return await tools_impl.get_stage_data_impl(concept_id, stage)


@mcp.tool()
async def mark_concept_stored(concept_id: str, knowledge_mcp_id: str) -> dict:
    """
    Mark a concept as stored in Knowledge MCP with its permanent ID.

    Args:
        concept_id: Short-term concept ID
        knowledge_mcp_id: Permanent Knowledge MCP ID

    Returns:
        Confirmation of storage link
    """
    return await tools_impl.mark_concept_stored_impl(concept_id, knowledge_mcp_id)


@mcp.tool()
async def get_unstored_concepts(session_id: str) -> dict:
    """
    Get all concepts that haven't been stored to Knowledge MCP yet.

    Args:
        session_id: Session ID

    Returns:
        List of concepts missing Knowledge MCP IDs
    """
    return await tools_impl.get_unstored_concepts_impl(session_id)


# ============================================================================
# PHASE 4: RELIABILITY TOOLS (TIER 2)
# ============================================================================


@mcp.tool()
async def mark_session_complete(session_id: str) -> dict:
    """
    Mark a session as completed after all concepts are stored.

    Verifies all concepts have been stored to Knowledge MCP before marking complete.
    Returns a warning if any concepts are still unstored.

    Args:
        session_id: Session ID to mark as complete

    Returns:
        Success status with session statistics, or warning if concepts unstored
    """
    return await tools_impl.mark_session_complete_impl(session_id)


@mcp.tool()
async def clear_old_sessions(days_to_keep: int = 7) -> dict:
    """
    Manually clear sessions older than specified days.

    Sessions are automatically cleaned up when new sessions are created,
    but this tool allows manual cleanup on demand.
    Deletes sessions and all associated concepts and stage data.

    Args:
        days_to_keep: Keep sessions from last N days (default: 7)

    Returns:
        Deletion statistics including number of sessions and concepts deleted
    """
    return await tools_impl.clear_old_sessions_impl(days_to_keep)


@mcp.tool()
async def get_concepts_by_status(session_id: str, status: str) -> dict:
    """
    Get all concepts in a session filtered by specific status.

    Convenience wrapper for get_concepts_by_session with status filter.
    Provides a simpler interface when you only need one status.

    Args:
        session_id: Session ID
        status: Status to filter by (identified, chunked, encoded, evaluated, stored)

    Returns:
        List of concepts matching the specified status
    """
    return await tools_impl.get_concepts_by_status_impl(session_id, status)


# ============================================================================
# PHASE 5: CODE TEACHER SUPPORT
# ============================================================================


@mcp.tool()
async def get_todays_concepts() -> dict:
    """
    Get all concepts from today's session for Code Teacher queries.

    Optimized for Code Teacher with 5-minute caching. Returns all concepts
    from today's session with status statistics for context awareness.

    Returns:
        Today's concepts with statistics and metadata
        - status: "success" or "not_found"
        - date: Today's date (YYYY-MM-DD)
        - session_id: Today's session ID
        - learning_goal: What's being learned today
        - building_goal: What's being built today
        - concept_count: Total number of concepts
        - concepts_by_status: Count of concepts per status
        - concepts: Full list of concept objects
        - cache_hit: Whether this response came from cache
    """
    return await tools_impl.get_todays_concepts_impl()


@mcp.tool()
async def get_todays_learning_goals() -> dict:
    """
    Get today's learning and building goals without full concept list.

    Lightweight query optimized for Code Teacher context awareness.
    Returns session goals and statistics without loading all concepts.
    Cached for 5 minutes.

    Returns:
        Today's session goals and basic statistics
        - status: "success" or "not_found"
        - date: Today's date (YYYY-MM-DD)
        - session_id: Today's session ID
        - learning_goal: What's being learned today
        - building_goal: What's being built today
        - session_status: "in_progress" or "completed"
        - concept_count: Total number of concepts
        - concepts_by_status: Count of concepts per status
        - cache_hit: Whether this response came from cache
    """
    return await tools_impl.get_todays_learning_goals_impl()


@mcp.tool()
async def search_todays_concepts(search_term: str) -> dict:
    """
    Search today's concepts by name or content.

    Case-insensitive search through concept names and current_data fields.
    Useful for Code Teacher to find specific concepts discussed today.
    Results cached per query for 5 minutes.

    Args:
        search_term: Text to search for (case-insensitive)

    Returns:
        Matching concepts with search metadata
        - status: "success", "not_found", or "error"
        - date: Today's date (YYYY-MM-DD)
        - session_id: Today's session ID
        - search_term: The search term used
        - match_count: Number of matching concepts
        - matches: List of matching concept objects
        - cache_hit: Whether this response came from cache
    """
    return await tools_impl.search_todays_concepts_impl(search_term)


# =============================================================================
# PHASE 6: FUTURE FEATURES - User Questions & Relationships
# =============================================================================


@mcp.tool()
async def add_concept_question(concept_id: str, question: str, session_stage: str) -> dict:
    """
    Add a user question to a concept.

    Use this tool when you have a question about a concept that you want to track.
    The question will be stored with the concept and can be answered later.

    Args:
        concept_id: The concept ID to add the question to
        question: The question text
        session_stage: Which stage the question was asked at (research/aim/shoot/skin)

    Returns:
        - status: "success" or "error"
        - concept_id: The concept ID
        - concept_name: The concept name
        - question_added: The question that was added
        - total_questions: Total number of questions for this concept
        - all_questions: List of all questions with metadata
    """
    return await tools_impl.add_concept_question_impl(concept_id, question, session_stage)


@mcp.tool()
async def get_concept_page(concept_id: str) -> dict:
    """
    Get comprehensive single-page view of a concept.

    This tool returns everything about a concept in one call:
    - All metadata (name, status, timestamps)
    - Complete timeline of status changes
    - All stage data from research, aim, shoot, and skin sessions
    - All user questions asked about this concept
    - All related concepts and their relationships
    - Link to Knowledge MCP if stored

    Args:
        concept_id: The concept ID to retrieve

    Returns:
        - status: "success" or "error"
        - concept_id, concept_name, session_id, current_status
        - knowledge_mcp_id: Link to permanent storage (if stored)
        - timeline: List of status changes with timestamps
        - stage_data: All data from each pipeline stage
        - user_questions: All questions with metadata
        - question_count: Number of questions
        - relationships: List of related concepts
        - related_concept_count: Number of related concepts
        - current_data: All additional concept data
        - created_at, updated_at: Metadata timestamps
    """
    return await tools_impl.get_concept_page_impl(concept_id)


@mcp.tool()
async def add_concept_relationship(
    concept_id: str, related_concept_id: str, relationship_type: str
) -> dict:
    """
    Add a relationship between two concepts.

    Use this to link concepts that are related to each other. This helps
    build a knowledge graph of how concepts connect.

    Relationship types:
    - prerequisite: related_concept must be learned before concept
    - related: concepts are related but not dependent
    - similar: concepts are similar/alternative approaches
    - builds_on: concept builds on/extends related_concept

    Args:
        concept_id: Source concept ID
        related_concept_id: Target concept ID to relate to
        relationship_type: Type of relationship (prerequisite/related/similar/builds_on)

    Returns:
        - status: "success", "warning", or "error"
        - concept_id, concept_name: Source concept
        - related_to: Target concept details with relationship type
        - total_relationships: Total number of relationships for source concept
    """
    return await tools_impl.add_concept_relationship_impl(
        concept_id, related_concept_id, relationship_type
    )


@mcp.tool()
async def get_related_concepts(concept_id: str, relationship_type: str | None = None) -> dict:
    """
    Get all concepts related to a given concept.

    Args:
        concept_id: Concept ID to get relationships for
        relationship_type: Optional filter by relationship type
                          (prerequisite/related/similar/builds_on)

    Returns:
        - status: "success" or "error"
        - concept_id, concept_name: Source concept
        - relationship_filter: Applied filter (or None)
        - related_count: Number of related concepts
        - related_concepts: List of related concepts with full details:
            - concept_id, concept_name
            - relationship_type
            - current_status, session_id
            - created_at: When relationship was created
    """
    return await tools_impl.get_related_concepts_impl(concept_id, relationship_type)


# ==============================================================================
# MONITORING & PRODUCTION TOOLS (Tier 5 - Phase 7)
# ==============================================================================


@mcp.tool()
async def health_check() -> dict:
    """
    Check system health and database status.

    Returns:
        - status: "success"
        - overall_status: "healthy" or "degraded"
        - timestamp: Check timestamp (ISO format)
        - response_time_ms: Time taken for health check
        - components: Health status of each component:
            - database: Connection status, integrity, size
            - cache: Operational status, size, TTL

    Use this tool to:
    - Verify system is operational
    - Check database connectivity
    - Monitor cache status
    - Measure system response time

    Example response:
    {
        "status": "success",
        "overall_status": "healthy",
        "response_time_ms": 12.34,
        "components": {
            "database": {
                "status": "healthy",
                "connection": "active",
                "integrity": "ok",
                "size_bytes": 12345
            },
            "cache": {
                "status": "operational",
                "size": 5,
                "ttl_seconds": 300
            }
        }
    }
    """
    return await tools_impl.health_check_impl()


@mcp.tool()
async def get_system_metrics() -> dict:
    """
    Get system performance metrics and statistics.

    Returns comprehensive metrics including:
    - Database size and record counts
    - Operation counters (reads, writes, queries, errors)
    - Performance timing statistics (min, max, avg)
    - Cache statistics

    Use this tool to:
    - Monitor system performance
    - Track operation counts
    - Analyze query performance
    - Check database growth
    - Monitor cache utilization

    Example response:
    {
        "status": "success",
        "database": {
            "size_mb": 0.12,
            "sessions": 3,
            "concepts": 75,
            "stage_data_entries": 300
        },
        "operations": {
            "reads": 150,
            "writes": 75,
            "queries": 225,
            "errors": 0
        },
        "performance": {
            "read_times": {"avg_ms": 0.5, "min_ms": 0.1, "max_ms": 2.0},
            "write_times": {"avg_ms": 1.2, "min_ms": 0.5, "max_ms": 5.0},
            "query_times": {"avg_ms": 0.8, "min_ms": 0.2, "max_ms": 3.0}
        },
        "cache": {
            "entries": 5,
            "ttl_seconds": 300
        }
    }
    """
    return await tools_impl.get_system_metrics_impl()


@mcp.tool()
async def get_error_log(limit: int = 10, error_type: str | None = None) -> dict:
    """
    Get recent error log entries.

    **Error Logging Scope:**
    Only system-level errors are logged, including:
    - Database connection failures
    - Transaction rollback errors
    - Unexpected runtime exceptions
    - Async operation timeouts

    **NOT logged:**
    - Validation errors (returned as error responses)
    - "not_found" responses (expected behavior)
    - User input errors (e.g., invalid status, missing fields)
    - Duplicate entries or constraint violations

    These are handled gracefully and returned as error responses rather
    than logged as system errors.

    Args:
        limit: Maximum number of errors to return (default 10, max 100)
        error_type: Optional filter by error type (e.g., "DatabaseError", "ValueError")

    Returns:
        Recent error entries with timestamps, types, messages, and context

    Use this tool to:
    - Debug recent system failures
    - Monitor error patterns
    - Identify recurring issues
    - Get error context for troubleshooting

    Example response:
    {
        "status": "success",
        "filter": {"limit": 10, "error_type": null},
        "error_count": 2,
        "errors": [
            {
                "timestamp": "2025-10-10T12:34:56",
                "error_type": "DatabaseError",
                "message": "Connection timeout",
                "context": {"operation": "query", "duration_ms": 5001}
            }
        ]
    }
    """
    return await tools_impl.get_error_log_impl(limit, error_type)


# ==============================================================================
# TIER 9: RESEARCH CACHE TOOLS (Session 004)
# ==============================================================================


@mcp.tool()
async def check_research_cache(concept_name: str) -> dict:
    """
    Check if concept is cached.

    Returns cached research if available, null otherwise.

    Args:
        concept_name: Concept to lookup

    Returns:
        {
            "cached": true|false,
            "entry": ResearchCacheEntry | null,
            "cache_age_seconds": int | null
        }
    """
    try:
        from short_term_mcp.tools_impl import check_research_cache_impl

        return await check_research_cache_impl(concept_name, get_db())
    except Exception as e:
        raise ToolError(f"Failed to check cache: {str(e)}")


@mcp.tool()
async def trigger_research(concept_name: str, research_prompt: str = "") -> dict:
    """
    Trigger research for concept (Context7 placeholder).

    Currently returns mock data for testing.
    Future: Integration with Context7 for real research.

    Args:
        concept_name: Concept to research
        research_prompt: Optional research instructions

    Returns:
        {
            "concept_name": str,
            "explanation": str,
            "source_urls": List[dict]
        }
    """
    try:
        from short_term_mcp.tools_impl import trigger_research_impl

        return await trigger_research_impl(concept_name, research_prompt, get_db())
    except Exception as e:
        raise ToolError(f"Failed to trigger research: {str(e)}")


@mcp.tool()
async def update_research_cache(
    concept_name: str, explanation: str, source_urls: List[dict]
) -> dict:
    """
    Update research cache with new results.

    Args:
        concept_name: Concept name
        explanation: Research explanation
        source_urls: List of {url, title} dicts

    Returns:
        {
            "success": true,
            "entry": ResearchCacheEntry,
            "action": "inserted" | "updated"
        }
    """
    try:
        from short_term_mcp.tools_impl import update_research_cache_impl

        return await update_research_cache_impl(concept_name, explanation, source_urls, get_db())
    except Exception as e:
        raise ToolError(f"Failed to update cache: {str(e)}")


@mcp.tool()
async def add_domain_to_whitelist(domain: str, category: str, quality_score: float) -> dict:
    """
    Add domain to whitelist.

    Args:
        domain: Domain to whitelist (e.g., "docs.python.org")
        category: Category (official|in_depth|authoritative)
        quality_score: Quality score (0.0-1.0)

    Returns:
        {
            "success": true,
            "domain": DomainWhitelist
        }
    """
    try:
        from short_term_mcp.tools_impl import add_domain_to_whitelist_impl

        return await add_domain_to_whitelist_impl(domain, category, quality_score, get_db())
    except Exception as e:
        raise ToolError(f"Failed to add domain: {str(e)}")


@mcp.tool()
async def remove_domain_from_whitelist(domain: str) -> dict:
    """
    Remove domain from whitelist.

    Args:
        domain: Domain to remove

    Returns:
        {
            "success": true|false,
            "message": str
        }
    """
    try:
        from short_term_mcp.tools_impl import remove_domain_from_whitelist_impl

        return await remove_domain_from_whitelist_impl(domain, get_db())
    except Exception as e:
        raise ToolError(f"Failed to remove domain: {str(e)}")


@mcp.tool()
async def list_whitelisted_domains(category: Optional[str] = None) -> dict:
    """
    List whitelisted domains.

    Args:
        category: Optional filter by category (official|in_depth|authoritative)

    Returns:
        {
            "domains": List[DomainWhitelist],
            "count": int,
            "filter": str
        }
    """
    try:
        from short_term_mcp.tools_impl import list_whitelisted_domains_impl

        return await list_whitelisted_domains_impl(category, get_db())
    except Exception as e:
        raise ToolError(f"Failed to list domains: {str(e)}")


async def cache_cleanup_task():
    """Background task to periodically clean expired cache entries"""
    from .utils import cache, get_cache

    logger.info("🧹 Cache cleanup task started")

    while True:
        try:
            # Sleep for half the cache TTL before cleanup
            await asyncio.sleep(CACHE_TTL / 2)

            # Cleanup both caches
            code_teacher_cache = get_cache()
            removed_ct = code_teacher_cache.cleanup_expired()
            removed_general = cache.cleanup_expired()

            total_removed = removed_ct + removed_general
            if total_removed > 0:
                logger.debug(f"🧹 Removed {total_removed} expired cache entries")
        except asyncio.CancelledError:
            logger.info("🧹 Cache cleanup task stopped")
            break
        except Exception as e:
            logger.error(f"❌ Cache cleanup error: {e}")
            # Continue running even if cleanup fails
            await asyncio.sleep(60)  # Wait a minute before retrying


def start_background_tasks():
    """Start background maintenance tasks"""
    global _cleanup_task
    try:
        loop = asyncio.get_event_loop()
        _cleanup_task = loop.create_task(cache_cleanup_task())
        logger.info("✅ Background tasks started")
    except RuntimeError:
        # No event loop yet, will be started later
        logger.debug("Event loop not ready, background tasks will start with server")


# Initialize database on module import with proper error handling
try:
    db = get_db()
    # Test database connectivity
    try:
        test_session = db.get_session("test-health-check")
        logger.info(f"✅ Short-term Memory MCP initialized")
        logger.info(f"📁 Database: {DB_PATH}")

        # Try to start background tasks
        start_background_tasks()
    except Exception as db_error:
        logger.error(f"❌ Database connection test failed: {db_error}")
        raise RuntimeError(f"Database not accessible: {db_error}")
except Exception as e:
    logger.error(f"❌ CRITICAL: Failed to initialize database: {e}")
    logger.error(f"Server cannot start. Please check database configuration.")
    # Re-raise to prevent server from starting in broken state
    raise


def main():
    """Entry point for uv/pip installation"""
    try:
        logger.info("🚀 Starting Short-term Memory MCP Server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        raise


if __name__ == "__main__":
    main()
