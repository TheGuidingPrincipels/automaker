# src/session/manager.py
"""
Session lifecycle management.

Orchestrates the extraction workflow:
- Create sessions from source documents
- Generate cleanup and routing plans (with AI suggestions in Sub-Plan B)
- Record user decisions
- Execute approved plans
- Verify and delete source documents
"""

import uuid
from datetime import datetime
from typing import Optional, List, AsyncIterator

from ..models.session import ExtractionSession, SessionPhase
from ..models.content import SourceDocument
from ..models.content_mode import ContentMode
from ..models.cleanup_plan import CleanupPlan, CleanupItem, CleanupDisposition
from ..models.routing_plan import RoutingPlan, BlockRoutingItem, validate_overview_text
from ..extraction.parser import parse_markdown_file
from .storage import SessionStorage


class SessionManager:
    """Manage extraction session lifecycle."""

    def __init__(self, storage: SessionStorage, library_path: str = "./library"):
        self.storage = storage
        self.library_path = library_path

    async def create_session(
        self,
        source_path: Optional[str],
        library_path: Optional[str] = None,
        content_mode: ContentMode = ContentMode.STRICT,
    ) -> ExtractionSession:
        """
        Create a new extraction session and parse the source document.

        Args:
            source_path: Path to the source markdown file (optional)
            library_path: Path to the library (optional, uses default)
            content_mode: STRICT or REFINEMENT mode

        Returns:
            New ExtractionSession with parsed blocks
        """
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now()

        session = ExtractionSession(
            id=session_id,
            created_at=now,
            updated_at=now,
            phase=SessionPhase.INITIALIZED,
            library_path=library_path or self.library_path,
            content_mode=content_mode,
        )

        await self.storage.save(session)

        if source_path is None:
            return session

        # Parse the source document
        session.phase = SessionPhase.PARSING
        await self.storage.save(session)

        try:
            source_doc = await parse_markdown_file(source_path)
            session.source = source_doc
            session.execution_log.append(
                f"Parsed {source_doc.total_blocks} blocks from {source_path}"
            )
        except Exception as e:
            session.phase = SessionPhase.ERROR
            session.errors.append(f"Failed to parse source: {str(e)}")
            await self.storage.save(session)
            raise

        await self.storage.save(session)
        return session

    async def generate_cleanup_plan(self, session_id: str) -> CleanupPlan:
        """
        Generate a cleanup plan for a session.

        In Phase 1, this creates a simple plan with all blocks marked as KEEP.
        The SDK integration (Phase 1 completion) will add AI suggestions.

        Args:
            session_id: The session ID

        Returns:
            CleanupPlan with items for each block
        """
        session = await self.storage.load(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if not session.source:
            raise ValueError("Session has no parsed source document")

        # Create cleanup items for each block
        items = []
        for block in session.source.blocks:
            items.append(
                CleanupItem(
                    block_id=block.id,
                    heading_path=block.heading_path,
                    content_preview=block.content[:200],
                    suggested_disposition=CleanupDisposition.KEEP,
                    suggestion_reason="Default: keep all content",
                    final_disposition=None,  # User must decide
                )
            )

        cleanup_plan = CleanupPlan(
            session_id=session_id,
            source_file=session.source.file_path,
            items=items,
        )

        session.cleanup_plan = cleanup_plan
        session.phase = SessionPhase.CLEANUP_PLAN_READY
        await self.storage.save(session)

        return cleanup_plan

    async def set_cleanup_decision(
        self,
        session_id: str,
        block_id: str,
        disposition: CleanupDisposition,
    ) -> None:
        """
        Set the user's cleanup decision for a block.

        Args:
            session_id: The session ID
            block_id: The block ID
            disposition: KEEP or DISCARD
        """
        session = await self.storage.load(session_id)
        if not session or not session.cleanup_plan:
            raise ValueError("Session or cleanup plan not found")

        for item in session.cleanup_plan.items:
            if item.block_id == block_id:
                item.final_disposition = disposition
                break

        await self.storage.save(session)

    async def approve_cleanup_plan(self, session_id: str) -> bool:
        """
        Approve the cleanup plan after all decisions are made.

        Args:
            session_id: The session ID

        Returns:
            True if approved successfully
        """
        session = await self.storage.load(session_id)
        if not session or not session.cleanup_plan:
            raise ValueError("Session or cleanup plan not found")

        if not session.cleanup_plan.all_decided:
            raise ValueError("Not all blocks have cleanup decisions")

        session.cleanup_plan.approved = True
        session.cleanup_plan.approved_at = datetime.now()
        await self.storage.save(session)

        return True

    async def generate_routing_plan(self, session_id: str) -> RoutingPlan:
        """
        Generate a routing plan for kept blocks.

        In Phase 1, this creates a skeleton plan without AI suggestions.
        The SDK integration will add destination options.

        Args:
            session_id: The session ID

        Returns:
            RoutingPlan with items for each kept block
        """
        session = await self.storage.load(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if not session.cleanup_plan or not session.cleanup_plan.approved:
            raise ValueError("Cleanup plan must be approved first")

        if not session.source:
            raise ValueError("Session has no parsed source document")

        # Get list of kept block IDs
        kept_block_ids = {
            item.block_id
            for item in session.cleanup_plan.items
            if item.final_disposition == CleanupDisposition.KEEP
        }

        # Create routing items for kept blocks
        blocks = []
        for block in session.source.blocks:
            if block.id in kept_block_ids:
                blocks.append(
                    BlockRoutingItem(
                        block_id=block.id,
                        heading_path=block.heading_path,
                        content_preview=block.content[:200],
                        options=[],  # Will be populated by SDK
                        status="pending",
                    )
                )

        routing_plan = RoutingPlan(
            session_id=session_id,
            source_file=session.source.file_path,
            content_mode=session.content_mode.value,
            blocks=blocks,
        )

        session.routing_plan = routing_plan
        session.phase = SessionPhase.ROUTING_PLAN_READY
        await self.storage.save(session)

        return routing_plan

    async def select_destination(
        self,
        session_id: str,
        block_id: str,
        option_index: Optional[int] = None,
        custom_file: Optional[str] = None,
        custom_section: Optional[str] = None,
        custom_action: Optional[str] = None,
        proposed_file_title: Optional[str] = None,
        proposed_file_overview: Optional[str] = None,
    ) -> None:
        """
        Select destination for a block (user click selection).

        Args:
            session_id: The session ID
            block_id: The block ID
            option_index: Index of selected option (0-2)
            custom_file: Custom destination file (if not using options)
            custom_section: Custom destination section
            custom_action: Custom action
        """
        session = await self.storage.load(session_id)
        if not session or not session.routing_plan:
            raise ValueError("Session or routing plan not found")

        normalized_overview = (
            validate_overview_text(proposed_file_overview)
            if proposed_file_overview is not None
            else None
        )

        for item in session.routing_plan.blocks:
            if item.block_id == block_id:
                if option_index is not None:
                    options_count = len(item.options)
                    if options_count == 0:
                        raise ValueError(
                            f"Invalid option_index {option_index}: block {block_id} has no options"
                        )
                    if option_index < 0 or option_index >= options_count:
                        raise ValueError(
                            "Invalid option_index "
                            f"{option_index}: block {block_id} has {options_count} options "
                            f"(valid range 0-{options_count - 1})"
                        )
                    item.selected_option_index = option_index
                    if proposed_file_title is not None:
                        item.options[option_index].proposed_file_title = proposed_file_title
                    if normalized_overview is not None:
                        item.options[option_index].proposed_file_overview = normalized_overview
                else:
                    item.custom_destination_file = custom_file
                    item.custom_destination_section = custom_section
                    item.custom_action = custom_action
                    item.custom_proposed_file_title = proposed_file_title
                    item.custom_proposed_file_overview = normalized_overview
                item.status = "selected"
                break

        await self.storage.save(session)

    async def approve_plan(self, session_id: str) -> bool:
        """
        Final approval of the complete routing plan.

        Args:
            session_id: The session ID

        Returns:
            True if approved successfully

        Raises:
            ValueError: If not all blocks are resolved
        """
        session = await self.storage.load(session_id)
        if not session or not session.routing_plan:
            raise ValueError("Session or routing plan not found")

        if not session.routing_plan.all_blocks_resolved:
            raise ValueError(
                f"Not all blocks resolved. Pending: {session.routing_plan.pending_count}"
            )

        session.routing_plan.approved = True
        session.routing_plan.approved_at = datetime.now()
        session.phase = SessionPhase.READY_TO_EXECUTE
        await self.storage.save(session)

        return True

    async def get_session(self, session_id: str) -> Optional[ExtractionSession]:
        """Get a session by ID."""
        return await self.storage.load(session_id)

    async def list_sessions(self) -> List[str]:
        """List all session IDs."""
        return await self.storage.list_sessions()

    async def delete_source(self, session_id: str) -> bool:
        """
        Delete the source document after successful verification.

        Only allowed when all blocks are verified.

        Args:
            session_id: The session ID

        Returns:
            True if deleted successfully
        """
        import anyio

        session = await self.storage.load(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if session.phase != SessionPhase.COMPLETED:
            raise ValueError("Cannot delete source before session is completed")

        if not session.source:
            raise ValueError("No source document in session")

        # Verify all blocks are integrity-verified
        if not all(block.integrity_verified for block in session.source.blocks):
            raise ValueError("Not all blocks have been verified")

        # Delete the source file
        source_path = anyio.Path(session.source.file_path)
        if await source_path.exists():
            await source_path.unlink()
            session.source_deleted = True
            session.execution_log.append(f"Deleted source: {session.source.file_path}")
            await self.storage.save(session)
            return True

        return False

    # =========================================================================
    # AI-powered plan generation (Sub-Plan B)
    # =========================================================================

    async def generate_cleanup_plan_with_ai(
        self,
        session_id: str,
    ) -> AsyncIterator:
        """
        Generate a cleanup plan with AI suggestions using PlanningFlow.

        Streams progress events for real-time UI feedback.

        Args:
            session_id: The session ID

        Yields:
            PlanEvent objects tracking progress

        Returns:
            Final event contains the completed CleanupPlan
        """
        from ..conversation.flow import PlanningFlow, PlanEvent, PlanEventType

        session = await self.storage.load(session_id)
        if not session:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message=f"Session not found: {session_id}",
            )
            return

        # Create planning flow
        flow = PlanningFlow(library_path=session.library_path)

        # Stream cleanup plan generation
        async for event in flow.generate_cleanup_plan(session):
            yield event

            # If cleanup is ready, update session
            if event.type == PlanEventType.CLEANUP_READY and event.data:
                plan_data = event.data.get("cleanup_plan")
                if plan_data:
                    cleanup_plan = CleanupPlan.model_validate(plan_data)
                    session.cleanup_plan = cleanup_plan
                    session.phase = SessionPhase.CLEANUP_PLAN_READY
                    await self.storage.save(session)

    async def generate_routing_plan_with_ai(
        self,
        session_id: str,
        use_candidate_finder: bool = True,
    ) -> AsyncIterator:
        """
        Generate a routing plan with AI suggestions using PlanningFlow.

        Streams progress events for real-time UI feedback.
        Optionally uses CandidateFinder for pre-filtering.

        Args:
            session_id: The session ID
            use_candidate_finder: Whether to use lexical pre-filtering

        Yields:
            PlanEvent objects tracking progress

        Returns:
            Final event contains the completed RoutingPlan
        """
        from ..conversation.flow import PlanningFlow, PlanEvent, PlanEventType
        from ..library.candidates import CandidateFinder

        session = await self.storage.load(session_id)
        if not session:
            yield PlanEvent(
                type=PlanEventType.ERROR,
                message=f"Session not found: {session_id}",
            )
            return

        # Create planning flow
        flow = PlanningFlow(library_path=session.library_path)

        # Optional candidate finder
        candidate_finder = CandidateFinder() if use_candidate_finder else None

        # Stream routing plan generation
        async for event in flow.generate_routing_plan(session, candidate_finder):
            yield event

            # If routing is ready, update session
            if event.type == PlanEventType.ROUTING_READY and event.data:
                plan_data = event.data.get("routing_plan")
                if plan_data:
                    routing_plan = RoutingPlan.model_validate(plan_data)
                    session.routing_plan = routing_plan
                    session.phase = SessionPhase.ROUTING_PLAN_READY
                    await self.storage.save(session)

    async def find_merge_candidates(
        self,
        session_id: str,
        block_id: str,
    ) -> List:
        """
        Find merge candidates for a specific block (REFINEMENT mode only).

        Args:
            session_id: The session ID
            block_id: The block to find merge candidates for

        Returns:
            List of MergeCandidate objects
        """
        from ..merge.detector import MergeDetector
        from ..library.manifest import LibraryManifest

        session = await self.storage.load(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if session.content_mode != ContentMode.REFINEMENT:
            return []  # Merge only in refinement mode

        if not session.source:
            raise ValueError("Session has no parsed source document")

        # Find the block
        block = None
        for b in session.source.blocks:
            if b.id == block_id:
                block = {
                    "id": b.id,
                    "content": b.content,
                    "heading_path": b.heading_path,
                    "block_type": b.block_type,
                }
                break

        if not block:
            raise ValueError(f"Block not found: {block_id}")

        # Get library context
        manifest = LibraryManifest(session.library_path)
        library_context = await manifest.get_routing_context()

        # Find merge candidates
        detector = MergeDetector(library_path=session.library_path)
        candidates = await detector.find_merge_candidates(
            block=block,
            library_context=library_context,
            content_mode=session.content_mode.value,
        )

        return candidates
