# tests/test_planning_flow.py
"""Tests for planning flow orchestration."""

import pytest
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.conversation.flow import PlanningFlow, PlanEvent, PlanEventType
from src.models.session import ExtractionSession, SessionPhase
from src.models.content import SourceDocument, ContentBlock, BlockType
from src.models.content_mode import ContentMode
from src.models.cleanup_plan import CleanupPlan, CleanupItem, CleanupDisposition
from src.models.cleanup_mode_setting import CleanupModeSetting
from src.models.routing_plan import RoutingPlan, BlockRoutingItem


def make_checksum(text: str) -> str:
    """Helper to create 16-char SHA-256 checksum."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@pytest.fixture
def mock_session():
    """Create a mock extraction session."""
    content1 = "# Authentication\n\nJWT tokens should be validated."
    content2 = "# Database\n\nUse PostgreSQL for persistence."
    canonical1 = "authentication jwt tokens should be validated"
    canonical2 = "database use postgresql for persistence"

    blocks = [
        ContentBlock(
            id="block_1",
            content=content1,
            content_canonical=canonical1,
            block_type=BlockType.HEADER_SECTION,
            heading_path=["Authentication"],
            checksum_exact=make_checksum(content1),
            checksum_canonical=make_checksum(canonical1),
            source_file="/tmp/source.md",
            source_line_start=1,
            source_line_end=3,
        ),
        ContentBlock(
            id="block_2",
            content=content2,
            content_canonical=canonical2,
            block_type=BlockType.HEADER_SECTION,
            heading_path=["Database"],
            checksum_exact=make_checksum(content2),
            checksum_canonical=make_checksum(canonical2),
            source_file="/tmp/source.md",
            source_line_start=5,
            source_line_end=7,
        ),
    ]

    full_content = f"{content1}\n\n{content2}"
    source = SourceDocument(
        file_path="/tmp/source.md",
        checksum_exact=make_checksum(full_content),
        total_blocks=2,
        blocks=blocks,
    )

    session = ExtractionSession(
        id="test_session",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.PARSING,
        library_path="./library",
        content_mode=ContentMode.STRICT,
        source=source,
    )

    return session


@pytest.fixture
def mock_session_with_cleanup(mock_session):
    """Create a session with an approved cleanup plan."""
    items = [
        CleanupItem(
            block_id="block_1",
            heading_path=["Authentication"],
            content_preview="JWT tokens...",
            suggested_disposition=CleanupDisposition.KEEP,
            suggestion_reason="Relevant content",
            final_disposition=CleanupDisposition.KEEP,
        ),
        CleanupItem(
            block_id="block_2",
            heading_path=["Database"],
            content_preview="Use PostgreSQL...",
            suggested_disposition=CleanupDisposition.KEEP,
            suggestion_reason="Relevant content",
            final_disposition=CleanupDisposition.KEEP,
        ),
    ]

    cleanup_plan = CleanupPlan(
        session_id=mock_session.id,
        source_file=mock_session.source.file_path,
        items=items,
        approved=True,
        approved_at=datetime.now(),
    )

    mock_session.cleanup_plan = cleanup_plan
    mock_session.phase = SessionPhase.CLEANUP_PLAN_READY
    return mock_session


class TestPlanEvent:
    """Tests for PlanEvent dataclass."""

    def test_create_progress_event(self):
        """Create a progress event."""
        event = PlanEvent(
            type=PlanEventType.PROGRESS,
            message="Processing...",
        )

        assert event.type == PlanEventType.PROGRESS
        assert event.message == "Processing..."
        assert event.timestamp is not None
        assert event.data is None

    def test_create_event_with_data(self):
        """Create an event with data."""
        event = PlanEvent(
            type=PlanEventType.CLEANUP_READY,
            message="Cleanup complete",
            data={"item_count": 5},
        )

        assert event.data == {"item_count": 5}


class TestPlanningFlow:
    """Tests for PlanningFlow class."""

    @pytest.mark.asyncio
    async def test_cleanup_requires_source(self):
        """Cleanup generation requires a source document."""
        session = ExtractionSession(
            id="no_source",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            phase=SessionPhase.INITIALIZED,
            library_path="./library",
            source=None,
        )

        flow = PlanningFlow()
        events = []

        async for event in flow.generate_cleanup_plan(session):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == PlanEventType.ERROR
        assert "no parsed source" in events[0].message

    @pytest.mark.asyncio
    async def test_cleanup_generates_events(self, mock_session):
        """Cleanup generation produces progress events."""
        # Mock SDK client
        mock_cleanup_plan = CleanupPlan(
            session_id=mock_session.id,
            source_file=mock_session.source.file_path,
            items=[
                CleanupItem(
                    block_id="block_1",
                    heading_path=["Authentication"],
                    content_preview="JWT tokens...",
                    suggested_disposition=CleanupDisposition.KEEP,
                    suggestion_reason="Relevant content",
                )
            ],
        )

        with patch.object(
            PlanningFlow,
            "__init__",
            lambda self, **kwargs: None,
        ):
            flow = PlanningFlow()
            flow.sdk_client = AsyncMock()
            flow.sdk_client.generate_cleanup_plan = AsyncMock(return_value=mock_cleanup_plan)
            flow.library_path = "./library"
            flow.manifest = MagicMock()

            events = []
            async for event in flow.generate_cleanup_plan(mock_session):
                events.append(event)

        # Should have: started, progress, ready
        event_types = [e.type for e in events]
        assert PlanEventType.CLEANUP_STARTED in event_types
        assert PlanEventType.PROGRESS in event_types
        assert PlanEventType.CLEANUP_READY in event_types

    @pytest.mark.asyncio
    async def test_routing_requires_approved_cleanup(self, mock_session):
        """Routing generation requires approved cleanup plan."""
        flow = PlanningFlow()
        events = []

        async for event in flow.generate_routing_plan(mock_session):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == PlanEventType.ERROR
        assert "cleanup plan" in events[0].message.lower()

    @pytest.mark.asyncio
    async def test_routing_requires_cleanup_approved(self, mock_session):
        """Routing requires the cleanup plan to be approved."""
        # Add unapproved cleanup plan
        mock_session.cleanup_plan = CleanupPlan(
            session_id=mock_session.id,
            source_file=mock_session.source.file_path,
            items=[],
            approved=False,
        )

        flow = PlanningFlow()
        events = []

        async for event in flow.generate_routing_plan(mock_session):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == PlanEventType.ERROR
        assert "approved" in events[0].message.lower()

    @pytest.mark.asyncio
    async def test_cleanup_blocks_include_type_key(self, mock_session):
        """PlanningFlow must pass blocks with `type` for prompt builders."""
        mock_cleanup_plan = CleanupPlan(
            session_id=mock_session.id,
            source_file=mock_session.source.file_path,
            items=[
                CleanupItem(
                    block_id="block_1",
                    heading_path=["Authentication"],
                    content_preview="JWT tokens...",
                    suggested_disposition=CleanupDisposition.KEEP,
                    suggestion_reason="Relevant content",
                )
            ],
        )

        with patch.object(
            PlanningFlow,
            "__init__",
            lambda self, **kwargs: None,
        ):
            flow = PlanningFlow()
            flow.sdk_client = AsyncMock()
            flow.sdk_client.generate_cleanup_plan = AsyncMock(return_value=mock_cleanup_plan)
            flow.library_path = "./library"
            flow.manifest = MagicMock()

            async for _ in flow.generate_cleanup_plan(mock_session):
                pass

        called_blocks = flow.sdk_client.generate_cleanup_plan.call_args.kwargs["blocks"]
        assert called_blocks
        assert all("type" in b for b in called_blocks)

    @pytest.mark.asyncio
    async def test_cleanup_passes_cleanup_mode_to_sdk(self, mock_session):
        """PlanningFlow must pass cleanup_mode parameter to SDK client."""
        mock_cleanup_plan = CleanupPlan(
            session_id=mock_session.id,
            source_file=mock_session.source.file_path,
            items=[
                CleanupItem(
                    block_id="block_1",
                    heading_path=["Authentication"],
                    content_preview="JWT tokens...",
                    suggested_disposition=CleanupDisposition.KEEP,
                    suggestion_reason="Relevant content",
                )
            ],
        )

        with patch.object(
            PlanningFlow,
            "__init__",
            lambda self, **kwargs: None,
        ):
            flow = PlanningFlow()
            flow.sdk_client = AsyncMock()
            flow.sdk_client.generate_cleanup_plan = AsyncMock(return_value=mock_cleanup_plan)
            flow.library_path = "./library"
            flow.manifest = MagicMock()

            # Test with aggressive mode
            async for _ in flow.generate_cleanup_plan(mock_session, cleanup_mode=CleanupModeSetting.AGGRESSIVE):
                pass

        # Verify cleanup_mode was passed to SDK
        called_cleanup_mode = flow.sdk_client.generate_cleanup_plan.call_args.kwargs["cleanup_mode"]
        assert called_cleanup_mode == CleanupModeSetting.AGGRESSIVE

    @pytest.mark.asyncio
    async def test_cleanup_defaults_to_balanced_mode(self, mock_session):
        """PlanningFlow should default to balanced cleanup mode."""
        mock_cleanup_plan = CleanupPlan(
            session_id=mock_session.id,
            source_file=mock_session.source.file_path,
            items=[
                CleanupItem(
                    block_id="block_1",
                    heading_path=["Authentication"],
                    content_preview="JWT tokens...",
                    suggested_disposition=CleanupDisposition.KEEP,
                    suggestion_reason="Relevant content",
                )
            ],
        )

        with patch.object(
            PlanningFlow,
            "__init__",
            lambda self, **kwargs: None,
        ):
            flow = PlanningFlow()
            flow.sdk_client = AsyncMock()
            flow.sdk_client.generate_cleanup_plan = AsyncMock(return_value=mock_cleanup_plan)
            flow.library_path = "./library"
            flow.manifest = MagicMock()

            # Test without specifying cleanup_mode (should default to balanced)
            async for _ in flow.generate_cleanup_plan(mock_session):
                pass

        # Verify cleanup_mode defaulted to balanced
        called_cleanup_mode = flow.sdk_client.generate_cleanup_plan.call_args.kwargs["cleanup_mode"]
        assert called_cleanup_mode == CleanupModeSetting.BALANCED

    @pytest.mark.asyncio
    async def test_cleanup_events_include_cleanup_mode(self, mock_session):
        """PlanningFlow should include cleanup_mode in event data."""
        mock_cleanup_plan = CleanupPlan(
            session_id=mock_session.id,
            source_file=mock_session.source.file_path,
            items=[
                CleanupItem(
                    block_id="block_1",
                    heading_path=["Authentication"],
                    content_preview="JWT tokens...",
                    suggested_disposition=CleanupDisposition.KEEP,
                    suggestion_reason="Relevant content",
                )
            ],
        )

        with patch.object(
            PlanningFlow,
            "__init__",
            lambda self, **kwargs: None,
        ):
            flow = PlanningFlow()
            flow.sdk_client = AsyncMock()
            flow.sdk_client.generate_cleanup_plan = AsyncMock(return_value=mock_cleanup_plan)
            flow.library_path = "./library"
            flow.manifest = MagicMock()

            events = []
            async for event in flow.generate_cleanup_plan(mock_session, cleanup_mode=CleanupModeSetting.CONSERVATIVE):
                events.append(event)

        # Check that cleanup_started event includes cleanup_mode
        started_event = next(e for e in events if e.type == PlanEventType.CLEANUP_STARTED)
        assert started_event.data["cleanup_mode"] == "conservative"

        # Check that cleanup_ready event includes cleanup_mode
        ready_event = next(e for e in events if e.type == PlanEventType.CLEANUP_READY)
        assert ready_event.data["cleanup_mode"] == "conservative"

    @pytest.mark.asyncio
    async def test_routing_blocks_include_type_key(self, mock_session_with_cleanup):
        """PlanningFlow must pass kept blocks with `type` for prompt builders."""
        mock_routing_plan = RoutingPlan(
            session_id=mock_session_with_cleanup.id,
            source_file=mock_session_with_cleanup.source.file_path,
            content_mode="strict",
            blocks=[
                BlockRoutingItem(
                    block_id="block_1",
                    heading_path=["Authentication"],
                    content_preview="JWT tokens...",
                    options=[],
                )
            ],
        )

        with patch.object(
            PlanningFlow,
            "__init__",
            lambda self, **kwargs: None,
        ):
            flow = PlanningFlow()
            flow.sdk_client = AsyncMock()
            flow.sdk_client.generate_routing_plan = AsyncMock(return_value=mock_routing_plan)
            flow.library_path = "./library"
            flow.manifest = MagicMock()
            flow.manifest.get_routing_context = AsyncMock(return_value={"summary": {}, "categories": []})

            async for _ in flow.generate_routing_plan(mock_session_with_cleanup):
                pass

        called_blocks = flow.sdk_client.generate_routing_plan.call_args.kwargs["blocks"]
        assert called_blocks
        assert all("type" in b for b in called_blocks)

    @pytest.mark.asyncio
    async def test_routing_candidate_finder_serializes_candidate_matches(self, mock_session_with_cleanup):
        """Candidate finder results must be JSON-serializable in library_context."""
        from src.library.candidates import CandidateMatch

        mock_routing_plan = RoutingPlan(
            session_id=mock_session_with_cleanup.id,
            source_file=mock_session_with_cleanup.source.file_path,
            content_mode="strict",
            blocks=[
                BlockRoutingItem(
                    block_id="block_1",
                    heading_path=["Authentication"],
                    content_preview="JWT tokens...",
                    options=[],
                )
            ],
        )

        class DummyCandidateFinder:
            async def top_candidates(self, library_context, block):
                return [
                    CandidateMatch(
                        file_path="tech/authentication.md",
                        section="JWT Tokens",
                        score=0.9,
                        match_reasons=["TF-IDF: 0.42"],
                    )
                ]

        with patch.object(
            PlanningFlow,
            "__init__",
            lambda self, **kwargs: None,
        ):
            flow = PlanningFlow()
            flow.sdk_client = AsyncMock()
            flow.sdk_client.generate_routing_plan = AsyncMock(return_value=mock_routing_plan)
            flow.library_path = "./library"
            flow.manifest = MagicMock()
            flow.manifest.get_routing_context = AsyncMock(return_value={"summary": {}, "categories": []})

            async for _ in flow.generate_routing_plan(
                mock_session_with_cleanup, DummyCandidateFinder()
            ):
                pass

        called_context = flow.sdk_client.generate_routing_plan.call_args.kwargs["library_context"]
        assert "block_candidates" in called_context
        assert called_context["block_candidates"]["block_1"][0]["file_path"] == "tech/authentication.md"


class TestPlanEventTypes:
    """Tests for PlanEventType enum."""

    def test_all_event_types_defined(self):
        """All expected event types are defined."""
        expected_types = [
            "progress",
            "cleanup_started",
            "cleanup_ready",
            "routing_started",
            "routing_ready",
            "candidate_search",
            "error",
        ]

        for type_name in expected_types:
            assert hasattr(PlanEventType, type_name.upper())
