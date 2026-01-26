"""Tests for Phase 4 Reliability Tools"""

import asyncio

# Import tools
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from short_term_mcp.database import Database
from short_term_mcp.models import SessionStatus
from short_term_mcp.tools_impl import clear_old_sessions_impl as clear_old_sessions
from short_term_mcp.tools_impl import get_active_session_impl as get_active_session
from short_term_mcp.tools_impl import get_concepts_by_status_impl as get_concepts_by_status
from short_term_mcp.tools_impl import initialize_daily_session_impl as initialize_daily_session
from short_term_mcp.tools_impl import mark_concept_stored_impl as mark_concept_stored
from short_term_mcp.tools_impl import mark_session_complete_impl as mark_session_complete
from short_term_mcp.tools_impl import (
    store_concepts_from_research_impl as store_concepts_from_research,
)
from short_term_mcp.tools_impl import update_concept_status_impl as update_concept_status


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    test_db_path = Path("test_reliability.db")
    db = Database(test_db_path)
    db.initialize()

    # Replace global db with test db for tools
    from short_term_mcp import database

    original_db = database._db
    database._db = db

    yield db

    # Cleanup
    database._db = original_db
    db.close()
    if test_db_path.exists():
        test_db_path.unlink()


class TestMarkSessionComplete:
    """Test mark_session_complete tool"""

    @pytest.mark.asyncio
    async def test_mark_session_complete_success(self, test_db):
        """Test marking completed session when all concepts stored"""
        session_id = "2025-10-10"

        # Create session with concepts
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, [{"concept_name": f"Concept {i}", "data": {}} for i in range(5)]
        )

        # Mark all concepts as stored
        for concept_id in store_result["concept_ids"]:
            await mark_concept_stored(concept_id, f"perm-{concept_id}")

        # Mark session complete
        result = await mark_session_complete(session_id)

        assert result["status"] == "success"
        assert result["session_id"] == session_id
        assert result["total_concepts"] == 5
        assert "completed_at" in result

        # Verify session status updated in database
        session = test_db.get_session(session_id)
        assert session["status"] == SessionStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_mark_session_complete_with_unstored_concepts(self, test_db):
        """Test warning when concepts not stored"""
        session_id = "2025-10-10"

        # Create session with 10 concepts
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, [{"concept_name": f"Concept {i}", "data": {}} for i in range(10)]
        )

        # Only mark 6 as stored
        for concept_id in store_result["concept_ids"][:6]:
            await mark_concept_stored(concept_id, f"perm-{concept_id}")

        # Attempt to mark complete
        result = await mark_session_complete(session_id)

        assert result["status"] == "warning"
        assert result["unstored_count"] == 4
        assert result["total_concepts"] == 10
        assert len(result["unstored_concepts"]) == 4
        assert "not yet stored" in result["message"]

        # Verify session NOT marked complete
        session = test_db.get_session(session_id)
        assert session["status"] == SessionStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_mark_session_complete_not_found(self, test_db):
        """Test error for non-existent session"""
        result = await mark_session_complete("2025-99-99")

        assert result["status"] == "error"
        assert result["error_code"] == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_mark_session_complete_empty_session(self, test_db):
        """Test marking complete for session with no concepts"""
        session_id = "2025-10-10"

        # Create session with no concepts
        await initialize_daily_session("Learn", "Build", session_id)

        # Mark complete (no concepts = all stored)
        result = await mark_session_complete(session_id)

        assert result["status"] == "success"
        assert result["total_concepts"] == 0

    @pytest.mark.asyncio
    async def test_mark_session_complete_idempotent(self, test_db):
        """Test marking complete multiple times is safe"""
        session_id = "2025-10-10"

        # Create and complete session
        await initialize_daily_session("Learn", "Build", session_id)
        store_result = await store_concepts_from_research(
            session_id, [{"concept_name": "Test", "data": {}}]
        )
        await mark_concept_stored(store_result["concept_ids"][0], "perm-001")

        # Mark complete twice
        result1 = await mark_session_complete(session_id)
        result2 = await mark_session_complete(session_id)

        assert result1["status"] == "success"
        assert result2["status"] == "success"


class TestClearOldSessions:
    """Test clear_old_sessions tool"""

    @pytest.mark.asyncio
    async def test_clear_old_sessions_default_7_days(self, test_db):
        """Test clearing sessions older than 7 days"""
        today = datetime.now()

        # Create sessions at different dates
        old_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
        recent_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")
        today_date = today.strftime("%Y-%m-%d")

        # Manually create sessions in database to avoid auto-cleanup
        from short_term_mcp.models import Session, SessionStatus

        test_db.create_session(
            Session(
                session_id=old_date,
                date=old_date,
                learning_goal="Old",
                building_goal="Old",
                status=SessionStatus.IN_PROGRESS,
            )
        )
        test_db.create_session(
            Session(
                session_id=recent_date,
                date=recent_date,
                learning_goal="Recent",
                building_goal="Recent",
                status=SessionStatus.IN_PROGRESS,
            )
        )
        test_db.create_session(
            Session(
                session_id=today_date,
                date=today_date,
                learning_goal="Today",
                building_goal="Today",
                status=SessionStatus.IN_PROGRESS,
            )
        )

        # Clear old sessions (default 7 days)
        result = await clear_old_sessions()

        assert result["status"] == "success"
        assert result["days_to_keep"] == 7
        assert result["sessions_deleted"] == 1
        assert old_date in result["deleted_sessions"]

        # Verify old session deleted, others remain
        assert test_db.get_session(old_date) is None
        assert test_db.get_session(recent_date) is not None
        assert test_db.get_session(today_date) is not None

    @pytest.mark.asyncio
    async def test_clear_old_sessions_custom_days(self, test_db):
        """Test custom retention period"""
        today = datetime.now()

        # Create sessions: 6 days ago, 4 days ago, today
        date_6 = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        date_4 = (today - timedelta(days=4)).strftime("%Y-%m-%d")
        date_0 = today.strftime("%Y-%m-%d")

        await initialize_daily_session("Test", "Test", date_6)
        await initialize_daily_session("Test", "Test", date_4)
        await initialize_daily_session("Test", "Test", date_0)

        # Clear with 5-day retention (should delete 6-day-old session)
        result = await clear_old_sessions(days_to_keep=5)

        assert result["status"] == "success"
        assert result["days_to_keep"] == 5
        assert result["sessions_deleted"] == 1
        assert date_6 in result["deleted_sessions"]

        # Verify
        assert test_db.get_session(date_6) is None
        assert test_db.get_session(date_4) is not None
        assert test_db.get_session(date_0) is not None

    @pytest.mark.asyncio
    async def test_clear_old_sessions_cascades_to_concepts(self, test_db):
        """Test deletion cascades to concepts and stage data"""
        today = datetime.now()
        old_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")

        # Manually create session to avoid auto-cleanup
        from short_term_mcp.models import Session, SessionStatus

        test_db.create_session(
            Session(
                session_id=old_date,
                date=old_date,
                learning_goal="Test",
                building_goal="Test",
                status=SessionStatus.IN_PROGRESS,
            )
        )
        store_result = await store_concepts_from_research(
            old_date, [{"concept_name": f"C{i}", "data": {}} for i in range(5)]
        )

        # Verify concepts exist
        concepts_before = test_db.get_concepts_by_session(old_date)
        assert len(concepts_before) == 5

        # Clear old sessions
        result = await clear_old_sessions(days_to_keep=7)

        assert result["sessions_deleted"] == 1
        assert result["concepts_deleted"] == 5

        # Verify concepts deleted (cascade)
        concepts_after = test_db.get_concepts_by_session(old_date)
        assert len(concepts_after) == 0

    @pytest.mark.asyncio
    async def test_clear_old_sessions_no_sessions_to_delete(self, test_db):
        """Test when no old sessions exist"""
        today = datetime.now().strftime("%Y-%m-%d")

        # Create only today's session
        await initialize_daily_session("Test", "Test", today)

        # Clear old sessions
        result = await clear_old_sessions(days_to_keep=7)

        assert result["status"] == "success"
        assert result["sessions_deleted"] == 0
        assert result["concepts_deleted"] == 0

    @pytest.mark.asyncio
    async def test_clear_old_sessions_invalid_days(self, test_db):
        """Test error for invalid days_to_keep"""
        result = await clear_old_sessions(days_to_keep=0)

        assert result["status"] == "error"
        assert result["error_code"] == "INVALID_PARAMETER"

    @pytest.mark.asyncio
    async def test_clear_old_sessions_reports_deleted_ids(self, test_db):
        """Test that deleted session IDs are reported"""
        today = datetime.now()
        old1 = (today - timedelta(days=10)).strftime("%Y-%m-%d")
        old2 = (today - timedelta(days=9)).strftime("%Y-%m-%d")

        # Manually create sessions to avoid auto-cleanup
        from short_term_mcp.models import Session, SessionStatus

        test_db.create_session(
            Session(
                session_id=old1,
                date=old1,
                learning_goal="Test",
                building_goal="Test",
                status=SessionStatus.IN_PROGRESS,
            )
        )
        test_db.create_session(
            Session(
                session_id=old2,
                date=old2,
                learning_goal="Test",
                building_goal="Test",
                status=SessionStatus.IN_PROGRESS,
            )
        )

        result = await clear_old_sessions(days_to_keep=7)

        assert result["sessions_deleted"] == 2
        assert old1 in result["deleted_sessions"]
        assert old2 in result["deleted_sessions"]


class TestGetConceptsByStatus:
    """Test get_concepts_by_status convenience tool"""

    @pytest.mark.asyncio
    async def test_get_concepts_by_status_success(self, test_db):
        """Test filtering by status"""
        session_id = "2025-10-10"

        # Create session with concepts
        await initialize_daily_session("Test", "Test", session_id)
        store_result = await store_concepts_from_research(
            session_id, [{"concept_name": f"C{i}", "data": {}} for i in range(10)]
        )

        # Update some to chunked
        for concept_id in store_result["concept_ids"][:4]:
            await update_concept_status(concept_id, "chunked")

        # Get only identified
        result = await get_concepts_by_status(session_id, "identified")
        assert result["status"] == "success"
        assert result["count"] == 6

        # Get only chunked
        result = await get_concepts_by_status(session_id, "chunked")
        assert result["status"] == "success"
        assert result["count"] == 4

    @pytest.mark.asyncio
    async def test_get_concepts_by_status_invalid_status(self, test_db):
        """Test error for invalid status"""
        session_id = "2025-10-10"
        await initialize_daily_session("Test", "Test", session_id)

        result = await get_concepts_by_status(session_id, "invalid_status")

        assert result["status"] == "error"
        assert result["error_code"] == "INVALID_STATUS"
        assert "valid_statuses" in result

    @pytest.mark.asyncio
    async def test_get_concepts_by_status_empty_result(self, test_db):
        """Test when no concepts match status"""
        session_id = "2025-10-10"

        await initialize_daily_session("Test", "Test", session_id)
        await store_concepts_from_research(session_id, [{"concept_name": "Test", "data": {}}])

        # All concepts are 'identified', search for 'encoded'
        result = await get_concepts_by_status(session_id, "encoded")

        assert result["status"] == "success"
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_get_concepts_by_status_all_statuses(self, test_db):
        """Test filtering for each valid status"""
        session_id = "2025-10-10"

        await initialize_daily_session("Test", "Test", session_id)
        store_result = await store_concepts_from_research(
            session_id, [{"concept_name": f"C{i}", "data": {}} for i in range(5)]
        )
        concept_ids = store_result["concept_ids"]

        # Create one concept at each status
        await update_concept_status(concept_ids[1], "chunked")
        await update_concept_status(concept_ids[2], "encoded")
        await update_concept_status(concept_ids[3], "evaluated")
        await mark_concept_stored(concept_ids[4], "perm-004")

        # Test each status
        statuses = ["identified", "chunked", "encoded", "evaluated", "stored"]
        for status in statuses:
            result = await get_concepts_by_status(session_id, status)
            assert result["status"] == "success"
            assert result["count"] == 1, f"Expected 1 concept with status {status}"


class TestIntegrationReliability:
    """Integration tests for reliability workflows"""

    @pytest.mark.asyncio
    async def test_complete_session_lifecycle(self, test_db):
        """Test complete lifecycle: create → process → complete → cleanup"""
        today = datetime.now()
        old_session = (today - timedelta(days=10)).strftime("%Y-%m-%d")
        new_session = today.strftime("%Y-%m-%d")

        # 1. Create old session (to be cleaned up) - use direct DB to avoid auto-cleanup
        from short_term_mcp.models import Session, SessionStatus

        test_db.create_session(
            Session(
                session_id=old_session,
                date=old_session,
                learning_goal="Old",
                building_goal="Old",
                status=SessionStatus.IN_PROGRESS,
            )
        )
        await store_concepts_from_research(
            old_session, [{"concept_name": "OldConcept", "data": {}}]
        )

        # 2. Create new session (also manually to avoid auto-cleanup)
        test_db.create_session(
            Session(
                session_id=new_session,
                date=new_session,
                learning_goal="New",
                building_goal="New",
                status=SessionStatus.IN_PROGRESS,
            )
        )
        store_result = await store_concepts_from_research(
            new_session, [{"concept_name": f"C{i}", "data": {}} for i in range(3)]
        )

        # 3. Process and store all concepts
        for concept_id in store_result["concept_ids"]:
            await mark_concept_stored(concept_id, f"perm-{concept_id}")

        # 4. Mark session complete
        complete_result = await mark_session_complete(new_session)
        assert complete_result["status"] == "success"

        # 5. Clean up old sessions
        cleanup_result = await clear_old_sessions(days_to_keep=7)
        assert cleanup_result["sessions_deleted"] == 1
        assert old_session in cleanup_result["deleted_sessions"]

        # 6. Verify state
        assert test_db.get_session(old_session) is None
        assert test_db.get_session(new_session) is not None

    @pytest.mark.asyncio
    async def test_prevent_completion_with_partial_storage(self, test_db):
        """Test that incomplete sessions cannot be marked complete"""
        session_id = "2025-10-10"

        await initialize_daily_session("Test", "Test", session_id)
        store_result = await store_concepts_from_research(
            session_id, [{"concept_name": f"C{i}", "data": {}} for i in range(5)]
        )

        # Store only 3 of 5
        for concept_id in store_result["concept_ids"][:3]:
            await mark_concept_stored(concept_id, f"perm-{concept_id}")

        # Try to complete - should warn
        result = await mark_session_complete(session_id)
        assert result["status"] == "warning"
        assert result["unstored_count"] == 2

        # Session should still be in_progress
        session = await get_active_session(session_id)
        assert session["session_status"] == SessionStatus.IN_PROGRESS.value


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
