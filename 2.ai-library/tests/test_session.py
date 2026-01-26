# tests/test_session.py
"""Tests for session management."""

import pytest
from datetime import datetime
from pathlib import Path

from src.session.storage import SessionStorage
from src.session.manager import SessionManager
from src.models.session import ExtractionSession, SessionPhase
from src.models.content_mode import ContentMode
from src.models.content import SourceDocument
from src.models.cleanup_plan import CleanupDisposition
from src.models.routing_plan import RoutingPlan, BlockRoutingItem, BlockDestination
import anyio


@pytest.fixture
def temp_sessions_dir(tmp_path):
    """Create a temporary sessions directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    return str(sessions_dir)


@pytest.fixture
def temp_library_dir(tmp_path):
    """Create a temporary library directory."""
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    return str(library_dir)


@pytest.fixture
def sample_source_file(tmp_path):
    """Create a sample source markdown file."""
    source_file = tmp_path / "source.md"
    source_file.write_text(
        """# Project Notes

## Authentication Ideas

JWT tokens should be validated on every request.

## Database Schema

The users table needs these fields:
- id (UUID)
- email (unique)
"""
    )
    return str(source_file)


class TestSessionStorage:
    """Tests for SessionStorage."""

    @pytest.mark.asyncio
    async def test_save_and_load_session(self, temp_sessions_dir):
        """Save and load a session."""
        storage = SessionStorage(temp_sessions_dir)

        session = ExtractionSession(
            id="test_session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            phase=SessionPhase.INITIALIZED,
            library_path="./library",
        )

        await storage.save(session)
        loaded = await storage.load("test_session")

        assert loaded is not None
        assert loaded.id == "test_session"
        assert loaded.phase == SessionPhase.INITIALIZED

    @pytest.mark.asyncio
    async def test_list_sessions(self, temp_sessions_dir):
        """List all sessions."""
        storage = SessionStorage(temp_sessions_dir)

        # Create multiple sessions
        for i in range(3):
            session = ExtractionSession(
                id=f"session_{i}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                phase=SessionPhase.INITIALIZED,
                library_path="./library",
            )
            await storage.save(session)

        sessions = await storage.list_sessions()
        assert len(sessions) == 3
        assert "session_0" in sessions

    @pytest.mark.asyncio
    async def test_delete_session(self, temp_sessions_dir):
        """Delete a session."""
        storage = SessionStorage(temp_sessions_dir)

        session = ExtractionSession(
            id="to_delete",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            phase=SessionPhase.INITIALIZED,
            library_path="./library",
        )
        await storage.save(session)

        assert await storage.exists("to_delete")
        result = await storage.delete("to_delete")
        assert result is True
        assert not await storage.exists("to_delete")

    @pytest.mark.asyncio
    async def test_delete_uploads_missing_file_is_noop(self, temp_sessions_dir):
        """Missing upload files should not block cleanup."""
        storage = SessionStorage(temp_sessions_dir)

        session_id = "missing_upload"
        upload_dir = anyio.Path(temp_sessions_dir) / "uploads" / session_id
        await upload_dir.mkdir(parents=True, exist_ok=True)

        missing_path = Path(temp_sessions_dir) / "uploads" / session_id / "source.md"
        source = SourceDocument(
            file_path=str(missing_path),
            checksum_exact="abcdef0123456789",
            total_blocks=0,
            blocks=[],
        )

        session = ExtractionSession(
            id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            phase=SessionPhase.INITIALIZED,
            source=source,
            library_path="./library",
        )

        await storage.delete_uploads(session)

        assert not await upload_dir.exists()

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, temp_sessions_dir):
        """Loading nonexistent session returns None."""
        storage = SessionStorage(temp_sessions_dir)
        loaded = await storage.load("nonexistent")
        assert loaded is None


class TestSessionManager:
    """Tests for SessionManager."""

    @pytest.mark.asyncio
    async def test_create_session(
        self, temp_sessions_dir, temp_library_dir, sample_source_file
    ):
        """Create a new extraction session."""
        storage = SessionStorage(temp_sessions_dir)
        manager = SessionManager(storage, temp_library_dir)

        session = await manager.create_session(sample_source_file)

        assert session.id is not None
        assert session.source is not None
        assert session.source.total_blocks > 0
        assert session.phase == SessionPhase.PARSING

    @pytest.mark.asyncio
    async def test_generate_cleanup_plan(
        self, temp_sessions_dir, temp_library_dir, sample_source_file
    ):
        """Generate cleanup plan for a session."""
        storage = SessionStorage(temp_sessions_dir)
        manager = SessionManager(storage, temp_library_dir)

        session = await manager.create_session(sample_source_file)
        cleanup_plan = await manager.generate_cleanup_plan(session.id)

        assert cleanup_plan.session_id == session.id
        assert len(cleanup_plan.items) > 0

        # Reload session to verify persistence
        loaded = await storage.load(session.id)
        assert loaded.cleanup_plan is not None
        assert loaded.phase == SessionPhase.CLEANUP_PLAN_READY

    @pytest.mark.asyncio
    async def test_set_cleanup_decisions(
        self, temp_sessions_dir, temp_library_dir, sample_source_file
    ):
        """Set cleanup decisions for blocks."""
        storage = SessionStorage(temp_sessions_dir)
        manager = SessionManager(storage, temp_library_dir)

        session = await manager.create_session(sample_source_file)
        cleanup_plan = await manager.generate_cleanup_plan(session.id)

        # Set decisions for all blocks
        for item in cleanup_plan.items:
            await manager.set_cleanup_decision(
                session.id, item.block_id, CleanupDisposition.KEEP
            )

        # Verify decisions are saved
        loaded = await storage.load(session.id)
        assert all(
            item.final_disposition == CleanupDisposition.KEEP
            for item in loaded.cleanup_plan.items
        )

    @pytest.mark.asyncio
    async def test_approve_cleanup_plan(
        self, temp_sessions_dir, temp_library_dir, sample_source_file
    ):
        """Approve cleanup plan after all decisions made."""
        storage = SessionStorage(temp_sessions_dir)
        manager = SessionManager(storage, temp_library_dir)

        session = await manager.create_session(sample_source_file)
        cleanup_plan = await manager.generate_cleanup_plan(session.id)

        # Set decisions
        for item in cleanup_plan.items:
            await manager.set_cleanup_decision(
                session.id, item.block_id, CleanupDisposition.KEEP
            )

        # Approve
        result = await manager.approve_cleanup_plan(session.id)
        assert result is True

        # Verify approval
        loaded = await storage.load(session.id)
        assert loaded.cleanup_plan.approved is True

    @pytest.mark.asyncio
    async def test_generate_routing_plan(
        self, temp_sessions_dir, temp_library_dir, sample_source_file
    ):
        """Generate routing plan after cleanup approval."""
        storage = SessionStorage(temp_sessions_dir)
        manager = SessionManager(storage, temp_library_dir)

        session = await manager.create_session(sample_source_file)
        cleanup_plan = await manager.generate_cleanup_plan(session.id)

        # Approve cleanup
        for item in cleanup_plan.items:
            await manager.set_cleanup_decision(
                session.id, item.block_id, CleanupDisposition.KEEP
            )
        await manager.approve_cleanup_plan(session.id)

        # Generate routing plan
        routing_plan = await manager.generate_routing_plan(session.id)

        assert routing_plan.session_id == session.id
        assert len(routing_plan.blocks) > 0

        # Reload to verify persistence
        loaded = await storage.load(session.id)
        assert loaded.routing_plan is not None
        assert loaded.phase == SessionPhase.ROUTING_PLAN_READY

    @pytest.mark.asyncio
    async def test_select_destination_rejects_invalid_option_index(
        self,
        temp_sessions_dir,
        temp_library_dir,
    ):
        """Invalid option_index should raise a clear error."""
        storage = SessionStorage(temp_sessions_dir)
        manager = SessionManager(storage, temp_library_dir)

        destination = BlockDestination(
            destination_file="tech/example.md",
            destination_section=None,
            action="append",
            confidence=0.9,
            reasoning="test",
        )
        item = BlockRoutingItem(
            block_id="block_001",
            heading_path=["Heading"],
            content_preview="Preview content",
            options=[destination],
            status="pending",
        )
        routing_plan = RoutingPlan(
            session_id="sess_invalid_option",
            source_file="source.md",
            content_mode="strict",
            blocks=[item],
        )

        session = ExtractionSession(
            id="sess_invalid_option",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            phase=SessionPhase.ROUTING_PLAN_READY,
            source=None,
            library_path=temp_library_dir,
            content_mode=ContentMode.STRICT,
            routing_plan=routing_plan,
        )
        await storage.save(session)

        with pytest.raises(ValueError, match="option_index"):
            await manager.select_destination(
                session_id=session.id,
                block_id="block_001",
                option_index=5,
            )

    @pytest.mark.asyncio
    async def test_cannot_execute_without_approval(
        self, temp_sessions_dir, temp_library_dir, sample_source_file
    ):
        """Cannot execute session without plan approval."""
        storage = SessionStorage(temp_sessions_dir)
        manager = SessionManager(storage, temp_library_dir)

        session = await manager.create_session(sample_source_file)

        # Without any plans, can_execute should be False
        assert not session.can_execute


class TestSessionPhases:
    """Tests for session phase transitions."""

    def test_session_phases_defined(self):
        """All session phases are defined."""
        phases = [
            SessionPhase.INITIALIZED,
            SessionPhase.PARSING,
            SessionPhase.CLEANUP_PLAN_READY,
            SessionPhase.ROUTING_PLAN_READY,
            SessionPhase.AWAITING_APPROVAL,
            SessionPhase.READY_TO_EXECUTE,
            SessionPhase.EXECUTING,
            SessionPhase.VERIFYING,
            SessionPhase.COMPLETED,
            SessionPhase.ERROR,
        ]
        assert len(phases) == 10

    def test_content_mode_strict(self):
        """STRICT mode doesn't allow modifications."""
        assert not ContentMode.STRICT.allows_modifications

    def test_content_mode_refinement(self):
        """REFINEMENT mode allows modifications."""
        assert ContentMode.REFINEMENT.allows_modifications
