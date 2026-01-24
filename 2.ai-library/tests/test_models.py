# tests/test_models.py
"""Tests for model imports and basic model functionality."""

import pytest
from pydantic import ValidationError
from datetime import datetime


class TestModelsImport:
    """Verify all models can be imported from src.models."""

    def test_import_content_mode(self):
        """Test ContentMode enum import."""
        from src.models import ContentMode

        assert hasattr(ContentMode, "STRICT")
        assert hasattr(ContentMode, "REFINEMENT")

    def test_import_block_type(self):
        """Test BlockType enum import."""
        from src.models import BlockType

        assert hasattr(BlockType, "HEADER_SECTION")
        assert hasattr(BlockType, "PARAGRAPH")
        assert hasattr(BlockType, "LIST")
        assert hasattr(BlockType, "CODE_BLOCK")
        assert hasattr(BlockType, "BLOCKQUOTE")
        assert hasattr(BlockType, "TABLE")

    def test_import_content_block(self):
        """Test ContentBlock model import."""
        from src.models import ContentBlock

        assert ContentBlock is not None

    def test_import_source_document(self):
        """Test SourceDocument model import."""
        from src.models import SourceDocument

        assert SourceDocument is not None

    def test_import_library_file(self):
        """Test LibraryFile model import."""
        from src.models import LibraryFile

        assert LibraryFile is not None

    def test_import_library_category(self):
        """Test LibraryCategory model import."""
        from src.models import LibraryCategory

        assert LibraryCategory is not None

    def test_import_cleanup_disposition(self):
        """Test CleanupDisposition enum import."""
        from src.models import CleanupDisposition

        assert hasattr(CleanupDisposition, "KEEP")
        assert hasattr(CleanupDisposition, "DISCARD")

    def test_import_cleanup_item(self):
        """Test CleanupItem model import."""
        from src.models import CleanupItem

        assert CleanupItem is not None

    def test_import_cleanup_plan(self):
        """Test CleanupPlan model import."""
        from src.models import CleanupPlan

        assert CleanupPlan is not None

    def test_import_block_destination(self):
        """Test BlockDestination model import."""
        from src.models import BlockDestination

        assert BlockDestination is not None

    def test_import_block_routing_item(self):
        """Test BlockRoutingItem model import."""
        from src.models import BlockRoutingItem

        assert BlockRoutingItem is not None

    def test_import_merge_preview(self):
        """Test MergePreview model import."""
        from src.models import MergePreview

        assert MergePreview is not None

    def test_import_plan_summary(self):
        """Test PlanSummary model import."""
        from src.models import PlanSummary

        assert PlanSummary is not None

    def test_import_routing_plan(self):
        """Test RoutingPlan model import."""
        from src.models import RoutingPlan

        assert RoutingPlan is not None

    def test_import_session_phase(self):
        """Test SessionPhase enum import."""
        from src.models import SessionPhase

        assert hasattr(SessionPhase, "INITIALIZED")
        assert hasattr(SessionPhase, "PARSING")
        assert hasattr(SessionPhase, "CLEANUP_PLAN_READY")
        assert hasattr(SessionPhase, "ROUTING_PLAN_READY")
        assert hasattr(SessionPhase, "AWAITING_APPROVAL")
        assert hasattr(SessionPhase, "READY_TO_EXECUTE")
        assert hasattr(SessionPhase, "EXECUTING")
        assert hasattr(SessionPhase, "VERIFYING")
        assert hasattr(SessionPhase, "COMPLETED")
        assert hasattr(SessionPhase, "ERROR")

    def test_import_extraction_session(self):
        """Test ExtractionSession model import."""
        from src.models import ExtractionSession

        assert ExtractionSession is not None

    def test_import_all_at_once(self):
        """Test importing all models from src.models at once."""
        from src.models import (
            ContentMode,
            BlockType,
            ContentBlock,
            SourceDocument,
            LibraryFile,
            LibraryCategory,
            CleanupDisposition,
            CleanupItem,
            CleanupPlan,
            BlockDestination,
            BlockRoutingItem,
            MergePreview,
            PlanSummary,
            RoutingPlan,
            SessionPhase,
            ExtractionSession,
        )

        # Verify all imports are available
        assert all([
            ContentMode,
            BlockType,
            ContentBlock,
            SourceDocument,
            LibraryFile,
            LibraryCategory,
            CleanupDisposition,
            CleanupItem,
            CleanupPlan,
            BlockDestination,
            BlockRoutingItem,
            MergePreview,
            PlanSummary,
            RoutingPlan,
            SessionPhase,
            ExtractionSession,
        ])


class TestContentModeEnum:
    """Test ContentMode enum functionality."""

    def test_strict_mode_disallows_modifications(self):
        """STRICT mode should not allow modifications."""
        from src.models import ContentMode

        assert ContentMode.STRICT.allows_modifications is False

    def test_refinement_mode_allows_modifications(self):
        """REFINEMENT mode should allow modifications."""
        from src.models import ContentMode

        assert ContentMode.REFINEMENT.allows_modifications is True

    def test_strict_mode_description(self):
        """STRICT mode should have appropriate description."""
        from src.models import ContentMode

        desc = ContentMode.STRICT.description
        assert "Strict" in desc
        assert "byte-strict" in desc or "no merges" in desc

    def test_refinement_mode_description(self):
        """REFINEMENT mode should have appropriate description."""
        from src.models import ContentMode

        desc = ContentMode.REFINEMENT.description
        assert "Refinement" in desc


class TestContentBlock:
    """Test ContentBlock model functionality."""

    def test_content_block_from_source(self):
        """Test creating ContentBlock using from_source class method."""
        from src.models import ContentBlock, BlockType

        block = ContentBlock.from_source(
            content="Test content",
            content_canonical="test content",
            id="block_001",
            block_type=BlockType.PARAGRAPH,
            source_file="test.md",
            source_line_start=1,
            source_line_end=5,
        )

        assert block.id == "block_001"
        assert block.block_type == BlockType.PARAGRAPH
        assert block.content == "Test content"
        assert block.content_canonical == "test content"
        assert len(block.checksum_exact) == 16
        assert len(block.checksum_canonical) == 16
        assert block.checksum_exact != block.checksum_canonical  # Different content

    def test_content_block_default_values(self):
        """Test ContentBlock default field values."""
        from src.models import ContentBlock, BlockType

        block = ContentBlock.from_source(
            content="Test content",
            content_canonical="test content",
            id="block_001",
            block_type=BlockType.PARAGRAPH,
            source_file="test.md",
            source_line_start=1,
            source_line_end=5,
        )

        assert block.integrity_verified is False
        assert block.is_executed is False
        assert block.heading_path == []
        assert block.canonicalization_version == "v1"


class TestLibraryModels:
    """Test Library-related models."""

    def test_library_file_creation(self):
        """Test creating LibraryFile instance."""
        from src.models import LibraryFile

        lib_file = LibraryFile(
            path="tech/auth.md",
            category="tech",
            title="Authentication",
            last_modified="2024-01-01T00:00:00",
        )

        assert lib_file.path == "tech/auth.md"
        assert lib_file.category == "tech"
        assert lib_file.title == "Authentication"
        assert lib_file.sections == []
        assert lib_file.block_count == 0

    def test_library_category_creation(self):
        """Test creating LibraryCategory instance."""
        from src.models import LibraryCategory

        category = LibraryCategory(
            name="Technology",
            path="tech",
            description="Technical documentation",
        )

        assert category.name == "Technology"
        assert category.path == "tech"
        assert category.description == "Technical documentation"
        assert category.files == []
        assert category.subcategories == []


class TestCleanupModels:
    """Test cleanup plan models."""

    def test_cleanup_item_creation(self):
        """Test creating CleanupItem instance."""
        from src.models import CleanupItem, CleanupDisposition

        item = CleanupItem(
            block_id="block_001",
            content_preview="This is a preview...",
        )

        assert item.block_id == "block_001"
        assert item.suggested_disposition == CleanupDisposition.KEEP
        assert item.final_disposition is None

    def test_cleanup_plan_all_decided(self):
        """Test CleanupPlan.all_decided property."""
        from src.models import CleanupPlan, CleanupItem, CleanupDisposition

        plan = CleanupPlan(
            session_id="session_001",
            source_file="test.md",
            items=[
                CleanupItem(
                    block_id="block_001",
                    content_preview="Preview 1",
                    final_disposition=CleanupDisposition.KEEP,
                ),
                CleanupItem(
                    block_id="block_002",
                    content_preview="Preview 2",
                    final_disposition=CleanupDisposition.DISCARD,
                ),
            ],
        )

        assert plan.all_decided is True

    def test_cleanup_plan_not_all_decided(self):
        """Test CleanupPlan.all_decided when not all items have decisions."""
        from src.models import CleanupPlan, CleanupItem, CleanupDisposition

        plan = CleanupPlan(
            session_id="session_001",
            source_file="test.md",
            items=[
                CleanupItem(
                    block_id="block_001",
                    content_preview="Preview 1",
                    final_disposition=CleanupDisposition.KEEP,
                ),
                CleanupItem(
                    block_id="block_002",
                    content_preview="Preview 2",
                    # No final_disposition set
                ),
            ],
        )

        assert plan.all_decided is False


class TestRoutingModels:
    """Test routing plan models."""

    def test_block_destination_creation(self):
        """Test creating BlockDestination instance."""
        from src.models import BlockDestination

        dest = BlockDestination(
            destination_file="library/tech/auth.md",
            action="append",
            confidence=0.85,
            reasoning="Best match based on content similarity",
        )

        assert dest.destination_file == "library/tech/auth.md"
        assert dest.action == "append"
        assert dest.confidence == 0.85
        assert dest.destination_section is None

    def test_block_destination_rejects_short_overview(self):
        """BlockDestination enforces overview length."""
        from src.models import BlockDestination

        with pytest.raises(ValidationError):
            BlockDestination(
                destination_file="library/tech/auth.md",
                action="create_file",
                confidence=0.5,
                reasoning="Test",
                proposed_file_title="Auth File",
                proposed_file_overview="Too short.",
            )

    def test_routing_plan_pending_count(self):
        """Test RoutingPlan.pending_count property."""
        from src.models import RoutingPlan, BlockRoutingItem

        plan = RoutingPlan(
            session_id="session_001",
            source_file="test.md",
            blocks=[
                BlockRoutingItem(
                    block_id="block_001",
                    content_preview="Preview 1",
                    status="pending",
                ),
                BlockRoutingItem(
                    block_id="block_002",
                    content_preview="Preview 2",
                    status="selected",
                    selected_option_index=0,
                ),
                BlockRoutingItem(
                    block_id="block_003",
                    content_preview="Preview 3",
                    status="pending",
                ),
            ],
        )

        assert plan.pending_count == 2
        assert plan.accepted_count == 1

    def test_plan_summary_creation(self):
        """Test creating PlanSummary instance."""
        from src.models import PlanSummary

        summary = PlanSummary(
            total_blocks=10,
            blocks_to_new_files=3,
            blocks_to_existing_files=6,
            blocks_requiring_merge=1,
            estimated_actions=10,
        )

        assert summary.total_blocks == 10
        assert summary.blocks_to_new_files == 3


class TestSessionModels:
    """Test session models."""

    def test_session_phase_values(self):
        """Test all SessionPhase enum values exist."""
        from src.models import SessionPhase

        phases = [
            "INITIALIZED",
            "PARSING",
            "CLEANUP_PLAN_READY",
            "ROUTING_PLAN_READY",
            "AWAITING_APPROVAL",
            "READY_TO_EXECUTE",
            "EXECUTING",
            "VERIFYING",
            "COMPLETED",
            "ERROR",
        ]
        for phase in phases:
            assert hasattr(SessionPhase, phase)

    def test_extraction_session_creation(self):
        """Test creating ExtractionSession instance."""
        from src.models import ExtractionSession, SessionPhase, ContentMode

        now = datetime.now()
        session = ExtractionSession(
            id="session_001",
            created_at=now,
            updated_at=now,
            phase=SessionPhase.INITIALIZED,
            library_path="/path/to/library",
        )

        assert session.id == "session_001"
        assert session.phase == SessionPhase.INITIALIZED
        assert session.content_mode == ContentMode.STRICT
        assert session.can_execute is False

    def test_extraction_session_can_execute_false_without_routing(self):
        """Test ExtractionSession.can_execute is False without routing plan."""
        from src.models import ExtractionSession, SessionPhase

        now = datetime.now()
        session = ExtractionSession(
            id="session_001",
            created_at=now,
            updated_at=now,
            phase=SessionPhase.INITIALIZED,
            library_path="/path/to/library",
        )

        assert session.can_execute is False
