# src/conversation/flow.py
"""
Planning flow orchestration with async event streaming.

Coordinates the generation of cleanup and routing plans using:
- ClaudeCodeClient for AI suggestions
- LibraryManifest for routing context
- CandidateFinder for pre-filtering destinations
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import AsyncIterator, Dict, Any, List, Optional
from datetime import datetime

from ..models.session import ExtractionSession, SessionPhase
from ..models.cleanup_plan import CleanupPlan, CleanupDisposition
from ..models.cleanup_mode_setting import CleanupModeSetting
from ..models.routing_plan import RoutingPlan, BlockRoutingItem, BlockDestination
from ..sdk.client import ClaudeCodeClient
from ..library.manifest import LibraryManifest


class PlanEventType(str, Enum):
    """Types of events emitted during plan generation."""
    PROGRESS = "progress"
    CLEANUP_STARTED = "cleanup_started"
    CLEANUP_READY = "cleanup_ready"
    ROUTING_STARTED = "routing_started"
    ROUTING_READY = "routing_ready"
    CANDIDATE_SEARCH = "candidate_search"
    ERROR = "error"


@dataclass
class PlanEvent:
    """Event emitted during planning flow."""
    type: PlanEventType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None


class PlanningFlow:
    """
    Orchestrates the generation of cleanup and routing plans.

    Uses async generators to stream progress events to the UI,
    allowing real-time feedback during AI generation.
    """

    def __init__(
        self,
        sdk_client: Optional[ClaudeCodeClient] = None,
        library_path: str = "./library",
    ):
        """
        Initialize the planning flow.

        Args:
            sdk_client: Claude Code SDK client (creates default if None)
            library_path: Path to the library for manifest generation
        """
        self.sdk_client = sdk_client or ClaudeCodeClient()
        self.library_path = library_path
        self.manifest = LibraryManifest(library_path)

    async def generate_cleanup_plan(
        self,
        session: ExtractionSession,
        cleanup_mode: CleanupModeSetting = CleanupModeSetting.BALANCED,
    ) -> AsyncIterator[PlanEvent]:
        """
        Generate a cleanup plan with AI suggestions.

        Yields PlanEvent objects for progress tracking.
        The final event contains the completed CleanupPlan.

        Args:
            session: The extraction session with parsed source
            cleanup_mode: Cleanup aggressiveness mode (conservative, balanced, aggressive)

        Yields:
            PlanEvent objects tracking progress
        """
        if not session.source:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message="Session has no parsed source document",
            )
            return

        yield PlanEvent(
            type=PlanEventType.CLEANUP_STARTED,
            message=f"Starting cleanup plan generation for {session.source.total_blocks} blocks (mode: {cleanup_mode.value})",
            data={"block_count": session.source.total_blocks, "cleanup_mode": cleanup_mode.value},
        )

        # Prepare blocks for SDK
        blocks = [
            {
                "id": block.id,
                "content": block.content,
                "heading_path": block.heading_path,
                "type": block.block_type.value,
                "checksum": block.checksum_exact,
            }
            for block in session.source.blocks
        ]

        yield PlanEvent(
            type=PlanEventType.PROGRESS,
            message="Analyzing content for discard candidates...",
            data={"step": "analysis", "cleanup_mode": cleanup_mode.value},
        )

        try:
            # Generate cleanup plan using SDK
            cleanup_plan = await self.sdk_client.generate_cleanup_plan(
                session_id=session.id,
                source_file=session.source.file_path,
                blocks=blocks,
                content_mode=session.content_mode.value,
                conversation_history=self._format_conversation_history(session),
                pending_questions=self._pending_question_texts(session),
                cleanup_mode=cleanup_mode,
            )

            # Count discard suggestions (for user info only - no auto-discard)
            discard_count = sum(
                1 for item in cleanup_plan.items
                if item.suggested_disposition == CleanupDisposition.DISCARD
            )

            yield PlanEvent(
                type=PlanEventType.CLEANUP_READY,
                message=f"Cleanup plan ready: {discard_count} discard suggestions for review",
                data={
                    "cleanup_plan": cleanup_plan.model_dump(),
                    "total_items": len(cleanup_plan.items),
                    "discard_suggestions": discard_count,
                    "cleanup_mode": cleanup_mode.value,
                },
            )

        except Exception as e:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message=f"Failed to generate cleanup plan: {str(e)}",
                data={"error": str(e)},
            )

    async def generate_routing_plan(
        self,
        session: ExtractionSession,
        candidate_finder: Optional[Any] = None,
    ) -> AsyncIterator[PlanEvent]:
        """
        Generate a routing plan with AI suggestions.

        Requires approved cleanup plan. Uses candidate finder
        (if provided) to pre-filter destinations before AI ranking.

        Args:
            session: The extraction session with approved cleanup plan
            candidate_finder: Optional CandidateFinder for pre-filtering

        Yields:
            PlanEvent objects tracking progress
        """
        # Validate prerequisites
        if not session.cleanup_plan:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message="No cleanup plan found",
            )
            return

        if not session.cleanup_plan.approved:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message="Cleanup plan must be approved before routing",
            )
            return

        if not session.source:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message="Session has no parsed source document",
            )
            return

        # Get kept block IDs
        kept_block_ids = {
            item.block_id
            for item in session.cleanup_plan.items
            if item.final_disposition == CleanupDisposition.KEEP
        }

        yield PlanEvent(
            type=PlanEventType.ROUTING_STARTED,
            message=f"Starting routing plan generation for {len(kept_block_ids)} kept blocks",
            data={"kept_block_count": len(kept_block_ids)},
        )

        # Prepare kept blocks for SDK
        kept_blocks = [
            {
                "id": block.id,
                "content": block.content,
                "heading_path": block.heading_path,
                "type": block.block_type.value,
                "checksum": block.checksum_exact,
            }
            for block in session.source.blocks
            if block.id in kept_block_ids
        ]

        # Get library context for routing
        yield PlanEvent(
            type=PlanEventType.PROGRESS,
            message="Loading library manifest...",
            data={"step": "manifest"},
        )

        try:
            library_context = await self.manifest.get_routing_context()
        except Exception as e:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message=f"Failed to load library manifest: {str(e)}",
                data={"error": str(e)},
            )
            return

        # Optional: Use candidate finder to pre-filter
        if candidate_finder:
            yield PlanEvent(
                type=PlanEventType.CANDIDATE_SEARCH,
                message="Pre-filtering destination candidates...",
                data={"step": "candidate_search"},
            )

            # Get candidates for each block
            block_candidates = {}
            for block in kept_blocks:
                candidates = await candidate_finder.top_candidates(
                    library_context, block
                )
                block_candidates[block["id"]] = candidates

            # Add candidate hints to library context
            library_context["block_candidates"] = {
                block_id: [asdict(c) for c in candidates]
                for block_id, candidates in block_candidates.items()
            }

        yield PlanEvent(
            type=PlanEventType.PROGRESS,
            message="Generating routing suggestions with AI...",
            data={"step": "ai_routing"},
        )

        try:
            # Generate routing plan using SDK
            routing_plan = await self.sdk_client.generate_routing_plan(
                session_id=session.id,
                source_file=session.source.file_path,
                blocks=kept_blocks,
                library_context=library_context,
                content_mode=session.content_mode.value,
                conversation_history=self._format_conversation_history(session),
                pending_questions=self._pending_question_texts(session),
            )

            # Count blocks with options
            blocks_with_options = sum(
                1 for block in routing_plan.blocks
                if len(block.options) > 0
            )

            yield PlanEvent(
                type=PlanEventType.ROUTING_READY,
                message=f"Routing plan ready: {blocks_with_options}/{len(routing_plan.blocks)} blocks have suggestions",
                data={
                    "routing_plan": routing_plan.model_dump(),
                    "total_blocks": len(routing_plan.blocks),
                    "blocks_with_options": blocks_with_options,
                },
            )

        except Exception as e:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message=f"Failed to generate routing plan: {str(e)}",
                data={"error": str(e)},
            )

    @staticmethod
    def _format_conversation_history(session: ExtractionSession) -> str:
        """Format conversation history for prompt context."""
        if not session.conversation_history:
            return ""

        lines = []
        for turn in session.conversation_history:
            timestamp = turn.timestamp.isoformat()
            lines.append(f"- [{timestamp}] {turn.role}: {turn.content}")
        return "\n".join(lines)

    @staticmethod
    def _pending_question_texts(session: ExtractionSession) -> List[str]:
        """Extract pending question text for prompt context."""
        return [q.question for q in session.pending_questions]

    async def validate_routing_options(
        self,
        routing_plan: RoutingPlan,
    ) -> List[str]:
        """
        Validate that all routing options point to valid destinations.

        Checks that:
        - Existing file destinations actually exist
        - Section references are valid
        - New file/section proposals follow naming conventions

        Args:
            routing_plan: The routing plan to validate

        Returns:
            List of validation warnings (empty if all valid)
        """
        warnings = []
        manifest = await self.manifest.generate()

        # Build set of valid file paths
        valid_files = {f["path"] for f in manifest.get("flat_file_list", [])}

        # Build section index
        section_index = manifest.get("section_index", {})

        for block in routing_plan.blocks:
            for i, option in enumerate(block.options):
                # Check existing file destinations
                if option.action in ("append", "insert_before", "insert_after", "merge"):
                    if option.destination_file not in valid_files:
                        warnings.append(
                            f"Block {block.block_id}, option {i+1}: "
                            f"File not found: {option.destination_file}"
                        )

                    # Check section exists if specified
                    if option.destination_section:
                        file_sections = section_index.get(option.destination_file, [])
                        section_titles = [s["title"] for s in file_sections]
                        if option.destination_section not in section_titles:
                            if option.action not in ("create_section", "create_file"):
                                warnings.append(
                                    f"Block {block.block_id}, option {i+1}: "
                                    f"Section not found: {option.destination_section}"
                                )

        return warnings
