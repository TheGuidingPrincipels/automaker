"""Tool implementations (without MCP decorators) for testing and reuse"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .config import DB_RETENTION_DAYS
from .database import get_db
from .models import (
    Concept,
    ConceptStatus,
    DomainWhitelist,
    ResearchCacheEntry,
    Session,
    SessionStatus,
    SourceURL,
    Stage,
)
from .utils import score_sources

logger = logging.getLogger(__name__)

# Default timeout for tool operations (20 seconds - well under Claude's 30s limit)
DEFAULT_TIMEOUT = 20.0


def normalize_optional_param(value: Any) -> Any:
    """
    Normalize optional parameters that may be passed as 'null' string or empty string.

    Converts:
    - String "null" -> None
    - Empty string "" -> None
    - None -> None
    - All other values -> unchanged

    This handles JSON deserialization where null becomes "null" string.

    Args:
        value: The parameter value to normalize

    Returns:
        None if value is None, "null", or "", otherwise the original value
    """
    if value is None or value == "null" or value == "":
        return None
    return value


async def with_timeout(coro, timeout: float = DEFAULT_TIMEOUT):
    """Wrapper to add timeout to async operations with graceful error handling"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Operation timed out after {timeout}s")
        return {
            "status": "error",
            "error_code": "TIMEOUT",
            "message": f"Operation timed out after {timeout} seconds. Please try again.",
        }
    except Exception as e:
        logger.error(f"Operation failed: {type(e).__name__}: {e}")
        return {"status": "error", "error_code": type(e).__name__, "message": str(e)}


async def invalidate_concept_cache(session_id: str) -> None:
    """
    Invalidate all cache entries related to a session when concepts are modified.

    This ensures search results and concept listings reflect real-time updates
    rather than stale cached data.

    Args:
        session_id: The session ID (typically YYYY-MM-DD format)
    """
    from .utils import cache, get_cache

    # Get the date from session_id (assuming YYYY-MM-DD format)
    date = session_id

    # Get both cache instances
    code_teacher_cache = get_cache()
    general_cache = cache

    # Cache keys that need invalidation
    keys_to_invalidate = [
        f"todays_concepts:{date}",
        f"todays_goals:{date}",
    ]

    # Invalidate in both caches (search queries use code_teacher_cache, others use general cache)
    for cache_instance in [code_teacher_cache, general_cache]:
        for key in keys_to_invalidate:
            try:
                # Delete by setting to None (cache.get will clean up expired entries)
                with cache_instance.lock:
                    if key in cache_instance.cache:
                        del cache_instance.cache[key]
            except Exception as e:
                logger.warning(f"Failed to invalidate cache key {key}: {e}")

    # Also invalidate all search queries for this date
    # Search keys are in format: "search:{date}:{term}"
    with code_teacher_cache.lock:
        search_prefix = f"search:{date}:"
        keys_to_remove = [k for k in code_teacher_cache.cache.keys() if k.startswith(search_prefix)]
        for key in keys_to_remove:
            del code_teacher_cache.cache[key]

    logger.debug(f"Invalidated cache for session {session_id}")


async def initialize_daily_session_impl(
    learning_goal: str, building_goal: str, date: str | None = None
) -> dict:
    """Initialize a new daily learning session."""

    async def _impl():
        db = get_db()

        # Use today if date not provided
        if not date:
            session_date = datetime.now().strftime("%Y-%m-%d")
        else:
            session_date = date

        session_id = session_date  # Use date as session_id for easy lookup

        # Check if session already exists
        existing = await db.async_get_session(session_id)
        if existing:
            return {
                "status": "warning",
                "message": f"Session {session_id} already exists",
                "session_id": session_id,
                "session": existing,
            }

        # Auto-cleanup old sessions BEFORE creating new one
        # This prevents backdated sessions (e.g., in tests) from being immediately deleted
        cutoff_date = (datetime.now() - timedelta(days=DB_RETENTION_DAYS)).strftime("%Y-%m-%d")
        result = await db.async_clear_old_sessions(cutoff_date)
        deleted = result["sessions_deleted"]

        # Create new session
        session = Session(
            session_id=session_id,
            date=session_date,
            learning_goal=learning_goal,
            building_goal=building_goal,
            status=SessionStatus.IN_PROGRESS,
        )

        await db.async_create_session(session)

        return {
            "status": "success",
            "message": f"Session {session_id} created successfully",
            "session_id": session_id,
            "cleaned_old_sessions": deleted,
        }

    return await with_timeout(_impl())


async def get_active_session_impl(date: str | None = None) -> dict:
    """Get today's active session with concept statistics."""

    async def _impl():
        db = get_db()

        if not date:
            session_date = datetime.now().strftime("%Y-%m-%d")
        else:
            session_date = date

        session_id = session_date
        session = await db.async_get_session(session_id)

        if not session:
            return {
                "status": "error",
                "error_code": "SESSION_NOT_FOUND",
                "message": f"Session {session_date} not found",
            }

        # Get concept statistics
        concepts = await db.async_get_concepts_by_session(session_id)
        stats = {}
        for status in ConceptStatus:
            stats[status.value] = sum(1 for c in concepts if c["current_status"] == status.value)

        return {
            "status": "success",
            "session_id": session_id,
            "date": session["date"],
            "learning_goal": session["learning_goal"],
            "building_goal": session["building_goal"],
            "session_status": session["status"],
            "concept_count": len(concepts),
            "concepts_by_status": stats,
        }

    return await with_timeout(_impl())


async def store_concepts_from_research_impl(session_id: str, concepts: list[dict]) -> dict:
    """Store all concepts identified in Research session (bulk operation)."""

    async def _impl():
        db = get_db()

        # Verify session exists
        session = await db.async_get_session(session_id)
        if not session:
            return {
                "status": "error",
                "error_code": "SESSION_NOT_FOUND",
                "message": f"Session {session_id} not found",
            }

        created_ids = []

        # Create concepts one by one with async operations
        for concept_data in concepts:
            concept_id = concept_data.get("concept_id", str(uuid.uuid4()))
            # Accept both 'concept_name' and 'name' fields for backward compatibility
            concept_name = concept_data.get("concept_name") or concept_data.get("name")
            if not concept_name:
                return {
                    "status": "error",
                    "error_code": "MISSING_CONCEPT_NAME",
                    "message": "Each concept must have either 'concept_name' or 'name' field",
                }
            data = concept_data.get("data", {})

            concept = Concept(
                concept_id=concept_id,
                session_id=session_id,
                concept_name=concept_name,
                current_status=ConceptStatus.IDENTIFIED,
                identified_at=datetime.now().isoformat(),
                current_data=data,
            )

            await db.async_create_concept(concept)
            created_ids.append(concept_id)

        return {
            "status": "success",
            "session_id": session_id,
            "concepts_created": len(created_ids),
            "concept_ids": created_ids,
        }

    return await with_timeout(_impl(), timeout=30.0)  # Longer timeout for bulk operation


async def get_concepts_by_session_impl(
    session_id: str, status_filter: str | None = None, include_stage_data: bool = False
) -> dict:
    """Get all concepts for a session, optionally filtered by status."""
    db = get_db()

    # Parse status filter
    status_enum = None
    if status_filter:
        try:
            status_enum = ConceptStatus(status_filter)
        except ValueError:
            return {
                "status": "error",
                "error_code": "INVALID_STATUS",
                "message": f"Invalid status: {status_filter}",
            }

    # Get concepts
    concepts = await db.async_get_concepts_by_session(session_id, status_enum)

    # Optionally include stage data
    if include_stage_data:
        for concept in concepts:
            concept["stage_data"] = {}
            for stage in Stage:
                stage_data = await db.async_get_stage_data(concept["concept_id"], stage)
                if stage_data:
                    concept["stage_data"][stage.value] = stage_data["data"]

    return {
        "status": "success",
        "session_id": session_id,
        "count": len(concepts),
        "concepts": concepts,
    }


async def update_concept_status_impl(
    concept_id: str, new_status: str, timestamp: str | None = None
) -> dict:
    """Update a concept's status and timestamp."""
    db = get_db()

    # Get current concept
    concept = await db.async_get_concept(concept_id)
    if not concept:
        return {
            "status": "error",
            "error_code": "CONCEPT_NOT_FOUND",
            "message": f"Concept {concept_id} not found",
        }

    # Parse status
    try:
        status_enum = ConceptStatus(new_status)
    except ValueError:
        return {
            "status": "error",
            "error_code": "INVALID_STATUS",
            "message": f"Invalid status: {new_status}",
        }

    # Update status
    success = await db.async_update_concept_status(concept_id, status_enum, timestamp)

    if success:
        # Invalidate cache for this session
        await invalidate_concept_cache(concept["session_id"])

        return {
            "status": "success",
            "concept_id": concept_id,
            "previous_status": concept["current_status"],
            "new_status": new_status,
            "timestamp": timestamp or datetime.now().isoformat(),
        }
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Status update failed"}


async def store_stage_data_impl(concept_id: str, stage: str, data: dict) -> dict:
    """Store stage-specific data for a concept."""
    db = get_db()

    # Verify concept exists
    concept = await db.async_get_concept(concept_id)
    if not concept:
        return {
            "status": "error",
            "error_code": "CONCEPT_NOT_FOUND",
            "message": f"Concept {concept_id} not found",
        }

    # Parse stage
    try:
        stage_enum = Stage(stage)
    except ValueError:
        return {
            "status": "error",
            "error_code": "INVALID_STAGE",
            "message": f"Invalid stage: {stage}",
        }

    # Store data
    result_id = await db.async_store_stage_data(concept_id, stage_enum, data)

    return {"status": "success", "concept_id": concept_id, "stage": stage, "data_id": result_id}


async def get_stage_data_impl(concept_id: str, stage: str) -> dict:
    """Retrieve stage-specific data for a concept."""
    db = get_db()

    # Parse stage
    try:
        stage_enum = Stage(stage)
    except ValueError:
        return {
            "status": "error",
            "error_code": "INVALID_STAGE",
            "message": f"Invalid stage: {stage}",
        }

    # Get data
    stage_data = await db.async_get_stage_data(concept_id, stage_enum)

    if not stage_data:
        return {
            "status": "not_found",
            "message": f"No data found for concept {concept_id} at stage {stage}",
        }

    return {
        "status": "success",
        "concept_id": concept_id,
        "stage": stage,
        "data": stage_data["data"],
        "created_at": stage_data["created_at"],
    }


async def mark_concept_stored_impl(concept_id: str, knowledge_mcp_id: str) -> dict:
    """Mark a concept as stored in Knowledge MCP with its permanent ID."""
    db = get_db()

    # Verify concept exists
    concept = await db.async_get_concept(concept_id)
    if not concept:
        return {
            "status": "error",
            "error_code": "CONCEPT_NOT_FOUND",
            "message": f"Concept {concept_id} not found",
        }

    # Update concept with Knowledge MCP ID and stored status atomically
    timestamp = datetime.now().isoformat()

    with db.transaction():
        # Single atomic UPDATE for both status and knowledge_mcp_id
        cursor = db.connection.execute(
            """
            UPDATE concepts
            SET current_status = ?,
                stored_at = ?,
                knowledge_mcp_id = ?,
                updated_at = ?
            WHERE concept_id = ?
        """,
            (ConceptStatus.STORED.value, timestamp, knowledge_mcp_id, timestamp, concept_id),
        )

        if cursor.rowcount == 0:
            return {
                "status": "error",
                "error_code": "UPDATE_FAILED",
                "message": "Failed to mark concept as stored",
            }

    return {
        "status": "success",
        "concept_id": concept_id,
        "knowledge_mcp_id": knowledge_mcp_id,
        "stored_at": timestamp,
    }


async def get_unstored_concepts_impl(session_id: str) -> dict:
    """Get all concepts that haven't been stored to Knowledge MCP yet."""
    import json

    db = get_db()

    # Query concepts without Knowledge MCP IDs
    cursor = db.connection.execute(
        """
        SELECT * FROM concepts
        WHERE session_id = ?
        AND (knowledge_mcp_id IS NULL OR knowledge_mcp_id = '')
        ORDER BY created_at
    """,
        (session_id,),
    )

    unstored = []
    for row in cursor.fetchall():
        concept = dict(row)
        concept["current_data"] = json.loads(concept["current_data"] or "{}")
        concept["user_questions"] = json.loads(concept["user_questions"] or "[]")
        unstored.append(concept)

    return {
        "status": "success",
        "session_id": session_id,
        "unstored_count": len(unstored),
        "concepts": unstored,
    }


# ============================================================================
# PHASE 4: RELIABILITY TOOLS (TIER 2)
# ============================================================================


async def mark_session_complete_impl(session_id: str) -> dict:
    """
    Mark a session as completed.
    Should be called when all concepts stored to Knowledge MCP.

    Args:
        session_id: Session ID to mark as complete

    Returns:
        Success status with session statistics or warning if concepts unstored
    """
    db = get_db()

    # Verify session exists
    session = await db.async_get_session(session_id)
    if not session:
        return {
            "status": "error",
            "error_code": "SESSION_NOT_FOUND",
            "message": f"Session {session_id} not found",
        }

    # Check if all concepts are stored
    concepts = await db.async_get_concepts_by_session(session_id)
    unstored = [c for c in concepts if c["knowledge_mcp_id"] is None]

    if unstored:
        return {
            "status": "warning",
            "message": f"{len(unstored)} concepts not yet stored to Knowledge MCP",
            "unstored_count": len(unstored),
            "total_concepts": len(concepts),
            "session_id": session_id,
            "unstored_concepts": [
                {
                    "concept_id": c["concept_id"],
                    "concept_name": c["concept_name"],
                    "current_status": c["current_status"],
                }
                for c in unstored
            ],
        }

    # Mark complete
    success = await db.async_mark_session_complete(session_id)

    if not success:
        return {
            "status": "error",
            "error_code": "UPDATE_FAILED",
            "message": f"Failed to update session {session_id}",
        }

    return {
        "status": "success",
        "session_id": session_id,
        "total_concepts": len(concepts),
        "message": f"Session {session_id} marked as complete with {len(concepts)} concepts",
        "completed_at": datetime.now().isoformat(),
    }


async def clear_old_sessions_impl(days_to_keep: int = 7) -> dict:
    """
    Manually clear sessions older than specified days.
    Auto-cleanup runs on session creation, this is for manual cleanup.

    Args:
        days_to_keep: Keep sessions from last N days (default: 7)

    Returns:
        Deletion statistics including sessions and concepts deleted
    """
    if days_to_keep < 1:
        return {
            "status": "error",
            "error_code": "INVALID_PARAMETER",
            "message": "days_to_keep must be at least 1",
        }

    db = get_db()
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")

    # Get sessions to be deleted (for reporting)
    cursor = db.connection.execute(
        "SELECT session_id, date FROM sessions WHERE date < ?", (cutoff_date,)
    )
    sessions_to_delete = [dict(row) for row in cursor.fetchall()]

    # Perform deletion
    result = await db.async_clear_old_sessions(cutoff_date)

    return {
        "status": "success",
        "cutoff_date": cutoff_date,
        "days_to_keep": days_to_keep,
        "sessions_deleted": result["sessions_deleted"],
        "concepts_deleted": result["concepts_deleted"],
        "message": f"Deleted {result['sessions_deleted']} sessions older than {cutoff_date}",
        "deleted_sessions": [s["session_id"] for s in sessions_to_delete],
    }


async def get_concepts_by_status_impl(session_id: str, status: str) -> dict:
    """
    Convenience wrapper for get_concepts_by_session with status filter.
    Provides a simpler interface for filtering by single status.

    Args:
        session_id: Session ID
        status: Status to filter by (identified, chunked, encoded, evaluated, stored)

    Returns:
        Filtered concepts matching the specified status
    """

    async def _impl():
        # Validate status
        try:
            status_enum = ConceptStatus(status)
        except ValueError:
            return {
                "status": "error",
                "error_code": "INVALID_STATUS",
                "message": f"Invalid status: {status}",
                "valid_statuses": [s.value for s in ConceptStatus],
            }

        # Reuse existing implementation
        result = await get_concepts_by_session_impl(
            session_id=session_id, status_filter=status, include_stage_data=False
        )

        # Explicit handling for empty results
        if result.get("status") == "success" and result.get("count") == 0:
            logger.info(f"No concepts found for status {status} in session {session_id}")

        return result

    return await with_timeout(_impl(), timeout=10.0)


# ============================================================================
# PHASE 5: CODE TEACHER SUPPORT
# ============================================================================


async def get_todays_concepts_impl() -> dict:
    """
    Get all concepts from today's session for Code Teacher.

    Optimized for Code Teacher queries with caching for 5 minutes.
    Returns concepts with status statistics.

    Returns:
        Today's concepts with statistics, or not_found if no session today
    """

    async def _impl():
        from .utils import get_cache

        cache = get_cache()
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"todays_concepts:{today}"

        # Check cache first (async)
        cached = cache.get(cache_key)
        if cached is not None:
            # Return a copy with cache_hit flag
            result = cached.copy()
            result["cache_hit"] = True
            return result

        # Cache miss - query database
        db = get_db()
        session = await db.async_get_todays_session(today)

        if not session:
            return {
                "status": "not_found",
                "message": f"No session found for today ({today})",
                "date": today,
                "cache_hit": False,
            }

        # Get all concepts
        concepts = await db.async_get_concepts_by_session(session["session_id"])

        # Calculate statistics
        stats = {}
        for status in ConceptStatus:
            stats[status.value] = sum(1 for c in concepts if c["current_status"] == status.value)

        result = {
            "status": "success",
            "date": today,
            "session_id": session["session_id"],
            "learning_goal": session["learning_goal"],
            "building_goal": session["building_goal"],
            "concept_count": len(concepts),
            "concepts_by_status": stats,
            "concepts": concepts,
            "cache_hit": False,
        }

        # Cache for 5 minutes (async)
        cache.set(cache_key, result)

        return result

    return await with_timeout(_impl())


async def get_todays_learning_goals_impl() -> dict:
    """
    Get today's learning and building goals without full concept list.

    Lightweight query optimized for Code Teacher context awareness.
    Cached for 5 minutes.

    Returns:
        Session goals and basic statistics
    """
    from .utils import get_cache

    cache = get_cache()
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"todays_goals:{today}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached is not None:
        # Return a copy with cache_hit flag
        result = cached.copy()
        result["cache_hit"] = True
        return result

    # Cache miss - query database
    db = get_db()
    session = await db.async_get_todays_session(today)

    if not session:
        return {
            "status": "not_found",
            "message": f"No session found for today ({today})",
            "date": today,
            "cache_hit": False,
        }

    # Get concept count only (lightweight)
    concepts = await db.async_get_concepts_by_session(session["session_id"])

    # Calculate statistics
    stats = {}
    for status in ConceptStatus:
        stats[status.value] = sum(1 for c in concepts if c["current_status"] == status.value)

    result = {
        "status": "success",
        "date": today,
        "session_id": session["session_id"],
        "learning_goal": session["learning_goal"],
        "building_goal": session["building_goal"],
        "session_status": session["status"],
        "concept_count": len(concepts),
        "concepts_by_status": stats,
        "cache_hit": False,
    }

    # Cache for 5 minutes
    cache.set(cache_key, result)

    return result


async def search_todays_concepts_impl(search_term: str) -> dict:
    """
    Search today's concepts by name or content.

    Case-insensitive search in concept names and current_data.
    Results cached per query for 5 minutes.

    Args:
        search_term: Text to search for in concept names and data

    Returns:
        Matching concepts with search metadata
    """
    from .utils import get_cache

    if not search_term or not search_term.strip():
        return {
            "status": "error",
            "error_code": "EMPTY_SEARCH_TERM",
            "message": "Search term cannot be empty",
        }

    cache = get_cache()
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"search:{today}:{search_term.lower()}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached is not None:
        # Return a copy with cache_hit flag
        result = cached.copy()
        result["cache_hit"] = True
        return result

    # Cache miss - query database
    db = get_db()
    session = await db.async_get_todays_session(today)

    if not session:
        return {
            "status": "not_found",
            "message": f"No session found for today ({today})",
            "date": today,
            "search_term": search_term,
            "cache_hit": False,
        }

    # Perform search
    matches = await db.async_search_concepts(session["session_id"], search_term)

    result = {
        "status": "success",
        "date": today,
        "session_id": session["session_id"],
        "search_term": search_term,
        "match_count": len(matches),
        "matches": matches,
        "cache_hit": False,
    }

    # Cache for 5 minutes
    cache.set(cache_key, result)

    return result


# =============================================================================
# PHASE 6: FUTURE FEATURES - User Questions & Relationships
# =============================================================================


async def add_concept_question_impl(concept_id: str, question: str, session_stage: str) -> dict:
    """
    Add a user question to a concept.

    Args:
        concept_id: Concept ID
        question: The question text
        session_stage: Which stage the question was asked (research/aim/shoot/skin)

    Returns:
        Updated concept with question added
    """
    db = get_db()

    # Verify concept exists
    concept = await db.async_get_concept(concept_id)
    if not concept:
        return {
            "status": "error",
            "error_code": "CONCEPT_NOT_FOUND",
            "message": f"Concept {concept_id} not found",
        }

    # Validate stage
    valid_stages = ["research", "aim", "shoot", "skin"]
    if session_stage.lower() not in valid_stages:
        return {
            "status": "error",
            "error_code": "INVALID_STAGE",
            "message": f"Invalid stage: {session_stage}. Must be one of: {', '.join(valid_stages)}",
        }

    # Add question
    success = await db.async_add_question_to_concept(concept_id, question, session_stage.lower())

    if not success:
        return {
            "status": "error",
            "error_code": "UPDATE_FAILED",
            "message": "Failed to add question to concept",
        }

    # Invalidate cache for this session
    await invalidate_concept_cache(concept["session_id"])

    # Get updated concept
    updated_concept = await db.async_get_concept(concept_id)
    if not updated_concept:
        return {
            "status": "error",
            "error_code": "CONCEPT_NOT_FOUND",
            "message": f"Concept {concept_id} was deleted during operation",
        }
    questions = updated_concept.get("user_questions", [])

    return {
        "status": "success",
        "concept_id": concept_id,
        "concept_name": updated_concept["concept_name"],
        "question_added": question,
        "total_questions": len(questions),
        "all_questions": questions,
    }


async def get_concept_page_impl(concept_id: str) -> dict:
    """
    Get comprehensive single-page view of a concept.

    Includes:
    - All concept metadata
    - All stage data (research, aim, shoot, skin)
    - All user questions
    - Related concepts (if any)
    - Timeline of status changes

    Args:
        concept_id: Concept ID

    Returns:
        Complete concept page data
    """
    db = get_db()

    # Get concept with all stage data
    concept = await db.async_get_concept_with_all_data(concept_id)

    if not concept:
        return {
            "status": "error",
            "error_code": "CONCEPT_NOT_FOUND",
            "message": f"Concept {concept_id} not found",
        }

    # Build timeline from timestamps
    timeline = []
    status_fields = [
        ("identified", concept.get("identified_at")),
        ("chunked", concept.get("chunked_at")),
        ("encoded", concept.get("encoded_at")),
        ("evaluated", concept.get("evaluated_at")),
        ("stored", concept.get("stored_at")),
    ]

    for status, timestamp in status_fields:
        if timestamp:
            timeline.append({"status": status, "timestamp": timestamp})

    # Extract relationships from current_data
    current_data = concept.get("current_data", {})
    relationships = current_data.get("relationships", [])

    return {
        "status": "success",
        "concept_id": concept_id,
        "concept_name": concept["concept_name"],
        "session_id": concept["session_id"],
        "current_status": concept["current_status"],
        "knowledge_mcp_id": concept.get("knowledge_mcp_id"),
        # Timeline
        "timeline": timeline,
        # Stage data
        "stage_data": concept.get("stage_data", {}),
        # Questions
        "user_questions": concept.get("user_questions", []),
        "question_count": len(concept.get("user_questions", [])),
        # Relationships
        "relationships": relationships,
        "related_concept_count": len(relationships),
        # Additional data
        "current_data": current_data,
        # Metadata
        "created_at": concept.get("created_at"),
        "updated_at": concept.get("updated_at"),
    }


async def add_concept_relationship_impl(
    concept_id: str, related_concept_id: str, relationship_type: str
) -> dict:
    """
    Add a relationship between two concepts.

    Relationship types:
    - prerequisite: related_concept is needed before concept
    - related: concepts are related but not dependent
    - similar: concepts are similar/alternative approaches
    - builds_on: concept builds on related_concept

    Args:
        concept_id: Source concept ID
        related_concept_id: Target concept ID
        relationship_type: Type of relationship

    Returns:
        Updated relationship information
    """
    db = get_db()

    # Validate not self-referential
    if concept_id == related_concept_id:
        return {
            "status": "error",
            "error_code": "SELF_REFERENTIAL_RELATIONSHIP",
            "message": "Cannot create relationship to self",
        }

    # Validate both concepts exist
    concept = await db.async_get_concept(concept_id)
    related_concept = await db.async_get_concept(related_concept_id)

    if not concept:
        return {
            "status": "error",
            "error_code": "CONCEPT_NOT_FOUND",
            "message": f"Concept {concept_id} not found",
        }

    if not related_concept:
        return {
            "status": "error",
            "error_code": "RELATED_CONCEPT_NOT_FOUND",
            "message": f"Related concept {related_concept_id} not found",
        }

    # Validate relationship type
    valid_types = ["prerequisite", "related", "similar", "builds_on"]
    if relationship_type not in valid_types:
        return {
            "status": "error",
            "error_code": "INVALID_RELATIONSHIP_TYPE",
            "message": f"Invalid relationship type: {relationship_type}. Must be one of: {', '.join(valid_types)}",
        }

    # Get existing relationships
    current_data = concept.get("current_data", {})
    relationships = current_data.get("relationships", [])

    # Check if relationship already exists
    existing = next((r for r in relationships if r["concept_id"] == related_concept_id), None)

    if existing:
        return {
            "status": "warning",
            "message": f"Relationship to {related_concept_id} already exists",
            "concept_id": concept_id,
            "existing_relationship": existing,
        }

    # Add new relationship
    new_relationship = {
        "concept_id": related_concept_id,
        "concept_name": related_concept["concept_name"],
        "relationship_type": relationship_type,
        "created_at": datetime.now().isoformat(),
    }
    relationships.append(new_relationship)

    # Update concept data
    success = await db.async_update_concept_data(concept_id, {"relationships": relationships})

    if not success:
        return {
            "status": "error",
            "error_code": "UPDATE_FAILED",
            "message": "Failed to add relationship",
        }

    # Invalidate cache for this session
    await invalidate_concept_cache(concept["session_id"])

    return {
        "status": "success",
        "concept_id": concept_id,
        "concept_name": concept["concept_name"],
        "related_to": {
            "concept_id": related_concept_id,
            "concept_name": related_concept["concept_name"],
            "relationship_type": relationship_type,
        },
        "total_relationships": len(relationships),
    }


async def get_related_concepts_impl(concept_id: str, relationship_type: str | None = None) -> dict:
    """
    Get all concepts related to a given concept.

    Args:
        concept_id: Concept ID
        relationship_type: Optional filter by relationship type

    Returns:
        List of related concepts with relationship information
    """
    db = get_db()

    # Get concept
    concept = await db.async_get_concept(concept_id)
    if not concept:
        return {
            "status": "error",
            "error_code": "CONCEPT_NOT_FOUND",
            "message": f"Concept {concept_id} not found",
        }

    # Validate relationship_type if provided
    if relationship_type is not None:
        valid_types = ["prerequisite", "related", "similar", "builds_on"]
        if relationship_type not in valid_types:
            return {
                "status": "error",
                "error_code": "INVALID_RELATIONSHIP_TYPE",
                "message": f"Invalid relationship type: {relationship_type}. Must be one of: {', '.join(valid_types)}",
            }

    # Extract relationships
    current_data = concept.get("current_data", {})
    relationships = current_data.get("relationships", [])

    # Filter by type if specified
    if relationship_type:
        relationships = [r for r in relationships if r["relationship_type"] == relationship_type]

    # Enrich with full concept data
    enriched_relationships = []
    for rel in relationships:
        related = await db.async_get_concept(rel["concept_id"])
        if related:
            enriched_relationships.append(
                {
                    "concept_id": rel["concept_id"],
                    "concept_name": rel["concept_name"],
                    "relationship_type": rel["relationship_type"],
                    "created_at": rel.get("created_at"),
                    "current_status": related["current_status"],
                    "session_id": related["session_id"],
                }
            )

    return {
        "status": "success",
        "concept_id": concept_id,
        "concept_name": concept["concept_name"],
        "relationship_filter": relationship_type,
        "related_count": len(enriched_relationships),
        "related_concepts": enriched_relationships,
    }


# ==============================================================================
# MONITORING & PRODUCTION TOOLS (Tier 5 - Phase 7)
# ==============================================================================


async def health_check_impl() -> dict:
    """
    Check system health and database status.

    Returns:
        System health status including database connectivity and cache status
    """
    import time

    from .utils import cache

    start_time = time.time()
    db = get_db()

    # Check database health
    db_health = await db.async_get_health_status()

    # Check cache health
    cache_stats = {
        "status": "operational",
        "size": len(cache.cache),
        "ttl_seconds": cache.default_ttl,
    }

    # Overall status
    overall_status = "healthy" if db_health["status"] == "healthy" else "degraded"

    # Response time
    response_time_ms = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "overall_status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": round(response_time_ms, 2),
        "components": {"database": db_health, "cache": cache_stats},
    }


async def get_system_metrics_impl() -> dict:
    """
    Get system performance metrics and statistics.

    Returns:
        Comprehensive metrics including operations, timing, and database stats
    """
    db = get_db()

    # Get database metrics
    db_metrics = await db.async_get_metrics()

    # Get database size
    db_size_bytes = await db.async_get_database_size()
    db_size_mb = db_size_bytes / (1024 * 1024)

    # Get session and concept counts
    try:
        cursor = db.connection.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]

        cursor = db.connection.execute("SELECT COUNT(*) FROM concepts")
        concept_count = cursor.fetchone()[0]

        cursor = db.connection.execute("SELECT COUNT(*) FROM concept_stage_data")
        stage_data_count = cursor.fetchone()[0]
    except Exception as e:
        session_count = 0
        concept_count = 0
        stage_data_count = 0

    # Cache metrics
    from .utils import cache

    cache_metrics = {"entries": len(cache.cache), "ttl_seconds": cache.default_ttl}

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "size_bytes": db_size_bytes,
            "size_mb": round(db_size_mb, 2),
            "sessions": session_count,
            "concepts": concept_count,
            "stage_data_entries": stage_data_count,
        },
        "operations": db_metrics["operations"],
        "performance": db_metrics["timing"],
        "cache": cache_metrics,
    }


async def get_error_log_impl(limit: int = 10, error_type: str | None = None) -> dict:
    """
    Get recent error log entries.

    Args:
        limit: Maximum number of errors to return (default 10, max 100)
        error_type: Optional filter by error type

    Returns:
        Recent error entries with timestamps and context
    """
    db = get_db()

    # Validate and cap limit
    if limit < 1:
        limit = 10
    elif limit > 100:
        limit = 100

    # Get errors
    errors = await db.async_get_errors(limit=limit, error_type=error_type)

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "filter": {"limit": limit, "error_type": error_type},
        "error_count": len(errors),
        "errors": errors,
    }


# ==============================================================================
# TIER 9: RESEARCH CACHE TOOLS (Session 004)
# ==============================================================================


async def check_research_cache_impl(concept_name: str, db) -> Dict:
    """Implementation for check_research_cache tool"""
    entry = await db.async_get_research_cache_entry(concept_name)

    if entry:
        cache_age = (datetime.now() - entry.last_researched_at).total_seconds()
        return {"cached": True, "entry": entry.model_dump(), "cache_age_seconds": int(cache_age)}
    else:
        return {"cached": False, "entry": None, "cache_age_seconds": None}


async def trigger_research_impl(concept_name: str, research_prompt: str, db) -> Dict:
    """Implementation for trigger_research tool (mock for now)"""
    # TODO: Replace with Context7 integration
    mock_explanation = f"Research result for {concept_name}"
    mock_urls = [{"url": "https://example.com/doc", "title": f"{concept_name} Documentation"}]

    # Score sources
    scored_urls = score_sources(mock_urls, db)

    return {
        "concept_name": concept_name,
        "explanation": mock_explanation,
        "source_urls": scored_urls,
    }


async def update_research_cache_impl(
    concept_name: str, explanation: str, source_urls: List[dict], db
) -> Dict:
    """Implementation for update_research_cache tool"""
    # Check if entry exists (for action reporting)
    existing = await db.async_get_research_cache_entry(concept_name)
    action = "updated" if existing else "inserted"

    # Score sources before storing
    scored_urls = score_sources(source_urls, db)

    # Create entry
    source_url_models = [SourceURL(**url) for url in scored_urls]
    entry = ResearchCacheEntry(
        concept_name=concept_name,
        explanation=explanation,
        source_urls=source_url_models,
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # UPSERT
    result = await db.async_upsert_research_cache(entry)

    return {"success": True, "entry": result.model_dump(), "action": action}


async def add_domain_to_whitelist_impl(
    domain: str, category: str, quality_score: float, db
) -> Dict:
    """Implementation for add_domain_to_whitelist tool"""
    domain_entry = await db.async_add_domain_to_whitelist(
        domain=domain, category=category, quality_score=quality_score, added_by="ai"
    )

    if domain_entry is None:
        return {
            "success": False,
            "message": f"Domain already exists in whitelist: {domain}",
        }

    return {"success": True, "domain": domain_entry.model_dump()}


async def remove_domain_from_whitelist_impl(domain: str, db) -> Dict:
    """Implementation for remove_domain_from_whitelist tool"""
    success = await db.async_remove_domain_from_whitelist(domain)

    return {
        "success": success,
        "message": f"Domain {'removed' if success else 'not found'}: {domain}",
    }


async def list_whitelisted_domains_impl(category: Optional[str], db) -> Dict:
    """Implementation for list_whitelisted_domains tool"""
    # Normalize "null" string and empty string to None
    category = normalize_optional_param(category)

    domains = await db.async_list_whitelisted_domains(category=category)

    return {
        "domains": [d.model_dump() for d in domains],
        "count": len(domains),
        "filter": category or "all",
    }
