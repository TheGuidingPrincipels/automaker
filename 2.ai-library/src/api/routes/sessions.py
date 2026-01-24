# src/api/routes/sessions.py
"""Session management routes."""

import logging
from datetime import datetime
from typing import Optional, List
from pathlib import PurePath, Path
import re

from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, File
import anyio

logger = logging.getLogger(__name__)

# Maximum file upload size (10 MB)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

from ..dependencies import (
    ConfigDep,
    SessionManagerDep,
    require_session,
)
from ..schemas import (
    CreateSessionRequest,
    SessionResponse,
    SessionListResponse,
    BlockResponse,
    BlockListResponse,
    CleanupPlanResponse,
    CleanupDecisionRequest,
    RoutingPlanResponse,
    SelectDestinationRequest,
    MergeDecisionRequest,
    SetContentModeRequest,
    ExecuteResponse,
    WriteResultResponse,
    SuccessResponse,
    ErrorResponse,
    StreamEvent,
)
from ...models.session import ExtractionSession, SessionPhase, ConversationTurn, PendingQuestion
from ...models.content_mode import ContentMode
from ...models.routing_plan import validate_overview_text
from ...models.cleanup_plan import CleanupDisposition
from ...execution.writer import ContentWriter


router = APIRouter()


# =============================================================================
# Session CRUD
# =============================================================================


@router.post("", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    manager: SessionManagerDep,
):
    """Create a new extraction session."""
    try:
        if request.content_mode not in ("strict", "refinement"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="content_mode must be 'strict' or 'refinement'",
            )

        mode = ContentMode.STRICT if request.content_mode == "strict" else ContentMode.REFINEMENT
        session = await manager.create_session(
            source_path=request.source_path,
            library_path=request.library_path,
            content_mode=mode,
        )
        return SessionResponse.from_session(session)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source file not found: {request.source_path}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("", response_model=SessionListResponse)
async def list_sessions(manager: SessionManagerDep):
    """List all sessions."""
    session_ids = await manager.list_sessions()
    sessions = []

    for sid in session_ids:
        session = await manager.get_session(sid)
        if session:
            sessions.append(SessionResponse.from_session(session))

    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    manager: SessionManagerDep,
):
    """Get session details."""
    session = await require_session(session_id, manager)
    return SessionResponse.from_session(session)


@router.delete("/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: str,
    manager: SessionManagerDep,
):
    """Delete a session."""
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    try:
        await manager.storage.delete_uploads(session)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload cleanup failed: {e}",
        ) from e

    # Delete from storage
    await manager.storage.delete(session_id)
    return SuccessResponse(message=f"Session {session_id} deleted")


# =============================================================================
# Source Upload
# =============================================================================


@router.post("/{session_id}/upload", response_model=SessionResponse)
async def upload_source(
    session_id: str,
    manager: SessionManagerDep,
    file: UploadFile = File(...),
):
    """Upload a source file for an existing session (alternative to path-based creation)."""
    # This endpoint allows uploading a file directly instead of providing a path
    # For now, we save the file temporarily and process it
    session = await require_session(session_id, manager)

    if session.source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already has a source document",
        )

    # Validate file size before reading
    if file.size and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )

    safe_name = _sanitize_upload_filename(file.filename)

    uploads_dir = Path(manager.storage.upload_dir(session_id)).resolve()
    uploads_dir_async = anyio.Path(uploads_dir)
    await uploads_dir_async.mkdir(parents=True, exist_ok=True)

    target_path = (uploads_dir / safe_name).resolve()
    if not target_path.is_relative_to(uploads_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    upload_path = anyio.Path(target_path)
    content = await file.read()

    # Double-check size after reading (in case file.size was not available)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )

    await upload_path.write_bytes(content)

    # Parse the file
    from ...extraction.parser import parse_markdown_file

    source_doc = await parse_markdown_file(str(target_path))
    session.source = source_doc
    session.execution_log.append(
        f"Uploaded and parsed {source_doc.total_blocks} blocks from {file.filename}"
    )
    await manager.storage.save(session)

    return SessionResponse.from_session(session)


def _sanitize_upload_filename(filename: Optional[str]) -> str:
    """Sanitize an uploaded filename to a safe basename for local temp storage."""
    if not filename:
        return "upload"

    name = PurePath(filename).name
    name = name.replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    name = name.lstrip(".")  # Prevent hidden files

    return name[:120] if name else "upload"


def _pop_pending_question(
    session: ExtractionSession,
    question_id: Optional[str],
) -> PendingQuestion:
    """Pop a pending question by id (or FIFO)."""
    if not session.pending_questions:
        raise ValueError("No pending questions")

    if question_id:
        for index, question in enumerate(session.pending_questions):
            if question.id == question_id:
                return session.pending_questions.pop(index)
        raise ValueError(f"Pending question not found: {question_id}")

    return session.pending_questions.pop(0)


async def _send_stream_event(
    websocket: WebSocket,
    event_type: str,
    session_id: str,
    data: dict,
    timestamp: Optional[datetime] = None,
) -> None:
    """Send a StreamEvent payload with timestamp."""
    event = StreamEvent(
        event_type=event_type,
        session_id=session_id,
        data=data,
        timestamp=timestamp or datetime.now(),
    )
    await websocket.send_json(event.model_dump(mode="json"))


# =============================================================================
# Blocks
# =============================================================================


@router.get("/{session_id}/blocks", response_model=BlockListResponse)
async def get_blocks(
    session_id: str,
    manager: SessionManagerDep,
):
    """Get all blocks from the source document."""
    session = await require_session(session_id, manager)

    if not session.source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no source document",
        )

    blocks = [BlockResponse.from_block(b) for b in session.source.blocks]
    return BlockListResponse(blocks=blocks, total=len(blocks))


# =============================================================================
# Cleanup Plan
# =============================================================================


@router.post("/{session_id}/cleanup/generate", response_model=CleanupPlanResponse)
async def generate_cleanup_plan(
    session_id: str,
    manager: SessionManagerDep,
    use_ai: bool = False,
):
    """Generate a cleanup plan for the session."""
    session = await require_session(session_id, manager)

    if not session.source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no source document",
        )

    try:
        if use_ai:
            # Use AI-powered generation (streams events)
            async for event in manager.generate_cleanup_plan_with_ai(session_id):
                # For non-streaming endpoint, just consume events
                pass
            # Reload session with updated plan
            session = await manager.get_session(session_id)
        else:
            plan = await manager.generate_cleanup_plan(session_id)
            session = await manager.get_session(session_id)

        if not session or not session.cleanup_plan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate cleanup plan",
            )

        return CleanupPlanResponse.from_plan(session.cleanup_plan)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{session_id}/cleanup", response_model=CleanupPlanResponse)
async def get_cleanup_plan(
    session_id: str,
    manager: SessionManagerDep,
):
    """Get the current cleanup plan."""
    session = await require_session(session_id, manager)

    if not session.cleanup_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cleanup plan generated yet",
        )

    return CleanupPlanResponse.from_plan(session.cleanup_plan)


@router.post("/{session_id}/cleanup/decide/{block_id}", response_model=SuccessResponse)
async def set_cleanup_decision(
    session_id: str,
    block_id: str,
    request: CleanupDecisionRequest,
    manager: SessionManagerDep,
):
    """Set keep/discard decision for a block."""
    await require_session(session_id, manager)

    if request.disposition not in ("keep", "discard"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disposition must be 'keep' or 'discard'",
        )

    disposition = (
        CleanupDisposition.KEEP
        if request.disposition == "keep"
        else CleanupDisposition.DISCARD
    )

    try:
        await manager.set_cleanup_decision(session_id, block_id, disposition)
        return SuccessResponse(message=f"Block {block_id} marked as {request.disposition}")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{session_id}/cleanup/approve", response_model=SuccessResponse)
async def approve_cleanup_plan(
    session_id: str,
    manager: SessionManagerDep,
):
    """Approve the cleanup plan."""
    await require_session(session_id, manager)

    try:
        await manager.approve_cleanup_plan(session_id)
        return SuccessResponse(message="Cleanup plan approved")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# =============================================================================
# Routing Plan
# =============================================================================


@router.post("/{session_id}/plan/generate", response_model=RoutingPlanResponse)
async def generate_routing_plan(
    session_id: str,
    manager: SessionManagerDep,
    use_ai: bool = False,
    use_candidate_finder: bool = True,
):
    """Generate a routing plan for kept blocks."""
    session = await require_session(session_id, manager)

    if not session.cleanup_plan or not session.cleanup_plan.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cleanup plan must be approved first",
        )

    try:
        if use_ai:
            async for event in manager.generate_routing_plan_with_ai(
                session_id, use_candidate_finder=use_candidate_finder
            ):
                pass
            session = await manager.get_session(session_id)
        else:
            plan = await manager.generate_routing_plan(session_id)
            session = await manager.get_session(session_id)

        if not session or not session.routing_plan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate routing plan",
            )

        return RoutingPlanResponse.from_plan(session.routing_plan)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{session_id}/plan", response_model=RoutingPlanResponse)
async def get_routing_plan(
    session_id: str,
    manager: SessionManagerDep,
):
    """Get the current routing plan."""
    session = await require_session(session_id, manager)

    if not session.routing_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No routing plan generated yet",
        )

    return RoutingPlanResponse.from_plan(session.routing_plan)


@router.post("/{session_id}/plan/select/{block_id}", response_model=SuccessResponse)
async def select_destination(
    session_id: str,
    block_id: str,
    request: SelectDestinationRequest,
    manager: SessionManagerDep,
):
    """Select destination for a block."""
    await require_session(session_id, manager)

    try:
        await manager.select_destination(
            session_id=session_id,
            block_id=block_id,
            option_index=request.option_index,
            custom_file=request.custom_file,
            custom_section=request.custom_section,
            custom_action=request.custom_action,
            proposed_file_title=request.proposed_file_title,
            proposed_file_overview=request.proposed_file_overview,
        )
        return SuccessResponse(message=f"Destination selected for block {block_id}")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{session_id}/plan/reject-block/{block_id}", response_model=SuccessResponse)
async def reject_block(
    session_id: str,
    block_id: str,
    manager: SessionManagerDep,
):
    """Reject a block from the routing plan."""
    session = await require_session(session_id, manager)

    if not session.routing_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No routing plan generated",
        )

    # Find and update block status
    for item in session.routing_plan.blocks:
        if item.block_id == block_id:
            item.status = "rejected"
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found in routing plan: {block_id}",
        )

    await manager.storage.save(session)
    return SuccessResponse(message=f"Block {block_id} rejected")


@router.post("/{session_id}/plan/reroute-block/{block_id}", response_model=RoutingPlanResponse)
async def reroute_block(
    session_id: str,
    block_id: str,
    manager: SessionManagerDep,
):
    """
    Request new destination options for a block.

    This refreshes the AI suggestions for a specific block.
    """
    session = await require_session(session_id, manager)

    if not session.routing_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No routing plan generated",
        )

    # For now, return the current plan
    # Full implementation would regenerate options for this specific block
    return RoutingPlanResponse.from_plan(session.routing_plan)


@router.post("/{session_id}/plan/approve", response_model=SuccessResponse)
async def approve_plan(
    session_id: str,
    manager: SessionManagerDep,
):
    """Final approval of the routing plan."""
    await require_session(session_id, manager)

    try:
        await manager.approve_plan(session_id)
        return SuccessResponse(message="Routing plan approved")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# =============================================================================
# Merge Decisions (Refinement Mode)
# =============================================================================


@router.post("/{session_id}/merges/decide/{merge_id}", response_model=SuccessResponse)
async def decide_merge(
    session_id: str,
    merge_id: str,
    request: MergeDecisionRequest,
    manager: SessionManagerDep,
):
    """Decide on a merge operation (refinement mode only)."""
    session = await require_session(session_id, manager)

    if session.content_mode != ContentMode.REFINEMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merges are only available in refinement mode",
        )

    if not session.routing_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No routing plan generated",
        )

    # Find the merge preview
    merge = None
    for m in session.routing_plan.merge_previews:
        if m.merge_id == merge_id:
            merge = m
            break

    if not merge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merge not found: {merge_id}",
        )

    # Record decision (implementation would store this)
    return SuccessResponse(
        message=f"Merge {merge_id} {'accepted' if request.accept else 'rejected'}"
    )


# =============================================================================
# Content Mode
# =============================================================================


@router.post("/{session_id}/mode", response_model=SessionResponse)
async def set_content_mode(
    session_id: str,
    request: SetContentModeRequest,
    manager: SessionManagerDep,
):
    """Set the content mode for the session."""
    session = await require_session(session_id, manager)

    if request.mode not in ("strict", "refinement"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'strict' or 'refinement'",
        )

    session.content_mode = (
        ContentMode.STRICT if request.mode == "strict" else ContentMode.REFINEMENT
    )
    await manager.storage.save(session)

    return SessionResponse.from_session(session)


# =============================================================================
# Execution
# =============================================================================


@router.post("/{session_id}/execute", response_model=ExecuteResponse)
async def execute_plan(
    session_id: str,
    manager: SessionManagerDep,
    config: ConfigDep,
):
    """Execute the approved routing plan."""
    session = await require_session(session_id, manager)

    if not session.can_execute:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session cannot execute: routing plan not approved or blocks not resolved",
        )

    # Update phase
    session.phase = SessionPhase.EXECUTING
    await manager.storage.save(session)

    writer = ContentWriter(session.library_path)
    results: List[WriteResultResponse] = []
    errors: List[str] = []
    created_files: set[str] = set()
    ensured_sections: set[tuple[str, str]] = set()

    try:
        for item in session.routing_plan.blocks:
            if item.status != "selected":
                continue

            # Get destination from selected option or custom
            proposed_file_title = None
            proposed_file_overview = None
            proposed_section_title = None
            if item.selected_option_index is not None:
                dest = item.options[item.selected_option_index]
                dest_file = dest.destination_file
                dest_section = dest.destination_section
                action = dest.action
                proposed_file_title = dest.proposed_file_title
                proposed_file_overview = dest.proposed_file_overview
                proposed_section_title = dest.proposed_section_title
            else:
                dest_file = item.custom_destination_file
                dest_section = item.custom_destination_section
                action = item.custom_action or "append"
                proposed_file_title = item.custom_proposed_file_title
                proposed_file_overview = item.custom_proposed_file_overview

            if not dest_file:
                error = f"Block {item.block_id}: No destination specified"
                errors.append(error)
                results.append(WriteResultResponse(
                    block_id=item.block_id,
                    destination_file="",
                    success=False,
                    checksum_verified=False,
                    error=error,
                ))
                continue

            # Find the block in source
            block = None
            for b in session.source.blocks:
                if b.id == item.block_id:
                    block = b
                    break

            if not block:
                error = f"Block {item.block_id}: Not found in source"
                errors.append(error)
                results.append(WriteResultResponse(
                    block_id=item.block_id,
                    destination_file=dest_file,
                    success=False,
                    checksum_verified=False,
                    error=error,
                ))
                continue

            # Map routing actions to writer operations
            position = action
            section = dest_section

            if action == "create_file":
                if dest_file not in created_files:
                    if not proposed_file_title:
                        error = f"Block {block.id}: create_file requires proposed_file_title"
                        errors.append(error)
                        results.append(WriteResultResponse(
                            block_id=block.id,
                            destination_file=dest_file,
                            success=False,
                            checksum_verified=False,
                            error=error,
                        ))
                        continue
                    if not proposed_file_overview:
                        error = f"Block {block.id}: create_file requires proposed_file_overview"
                        errors.append(error)
                        results.append(WriteResultResponse(
                            block_id=block.id,
                            destination_file=dest_file,
                            success=False,
                            checksum_verified=False,
                            error=error,
                        ))
                        continue

                    try:
                        normalized_overview = validate_overview_text(proposed_file_overview)
                    except ValueError as e:
                        error = f"Block {block.id}: {str(e)}"
                        errors.append(error)
                        results.append(WriteResultResponse(
                            block_id=block.id,
                            destination_file=dest_file,
                            success=False,
                            checksum_verified=False,
                            error=error,
                        ))
                        continue

                    create_result = await writer.create_file(
                        destination=dest_file,
                        title=proposed_file_title,
                        overview=normalized_overview,
                    )

                    if not create_result.success:
                        error = f"Block {block.id}: {create_result.error}"
                        errors.append(error)
                        results.append(WriteResultResponse(
                            block_id=block.id,
                            destination_file=dest_file,
                            success=False,
                            checksum_verified=False,
                            error=error,
                        ))
                        continue
                    created_files.add(dest_file)

                # After creating the file, append the block content to it
                position = "append"
                section = None

            elif action == "create_section":
                section_title = proposed_section_title or dest_section
                if not section_title:
                    error = f"Block {block.id}: create_section requires proposed_section_title"
                    errors.append(error)
                    results.append(WriteResultResponse(
                        block_id=block.id,
                        destination_file=dest_file,
                        success=False,
                        checksum_verified=False,
                        error=error,
                    ))
                    continue

                key = (dest_file, section_title)
                if key not in ensured_sections:
                    create_section_result = await writer.create_section(
                        destination=dest_file,
                        section_title=section_title,
                    )

                    if not create_section_result.success:
                        error = f"Block {block.id}: {create_section_result.error}"
                        errors.append(error)
                        results.append(WriteResultResponse(
                            block_id=block.id,
                            destination_file=dest_file,
                            success=False,
                            checksum_verified=False,
                            error=error,
                        ))
                        continue
                    ensured_sections.add(key)

                position = "insert_after"
                section = section_title

            elif action in ("insert_before", "insert_after"):
                if not dest_section:
                    error = f"Block {block.id}: Section required for {action}"
                    errors.append(error)
                    results.append(WriteResultResponse(
                        block_id=block.id,
                        destination_file=dest_file,
                        success=False,
                        checksum_verified=False,
                        error=error,
                    ))
                    continue

            elif action == "merge":
                error = f"Block {block.id}: merge execution is not implemented"
                errors.append(error)
                results.append(WriteResultResponse(
                    block_id=block.id,
                    destination_file=dest_file,
                    success=False,
                    checksum_verified=False,
                    error=error,
                ))
                continue

            # Write with verification
            result = await writer.write_block(
                block=block,
                destination=dest_file,
                session_id=session.id,
                position=position,
                mode=session.content_mode,
                section=section,
            )

            results.append(WriteResultResponse(
                block_id=block.id,
                destination_file=dest_file,
                success=result.success,
                checksum_verified=result.verified,
                error=result.error,
            ))

            if not result.success:
                errors.append(f"Block {block.id}: {result.error}")

        # Update session phase
        blocks_written = sum(1 for r in results if r.success)
        blocks_failed = sum(1 for r in results if not r.success)
        all_verified = all(r.checksum_verified for r in results if r.success)

        if blocks_failed == 0:
            if config.safety.verify_after_execute:
                session.phase = SessionPhase.VERIFYING
                await manager.storage.save(session)

            if config.safety.verify_after_execute and not all_verified:
                session.phase = SessionPhase.ERROR
                session.errors.append("Post-execution verification failed")
            else:
                session.phase = SessionPhase.COMPLETED
        else:
            session.phase = SessionPhase.ERROR

        session.errors.extend(errors)
        await manager.storage.save(session)

        return ExecuteResponse(
            session_id=session_id,
            success=blocks_failed == 0,
            total_blocks=len(results),
            blocks_written=blocks_written,
            blocks_failed=blocks_failed,
            all_verified=all_verified,
            results=results,
            errors=errors,
        )

    except Exception as e:
        session.phase = SessionPhase.ERROR
        session.errors.append(str(e))
        await manager.storage.save(session)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# WebSocket Streaming
# =============================================================================


@router.websocket("/{session_id}/stream")
async def session_stream(
    websocket: WebSocket,
    session_id: str,
    manager: SessionManagerDep,
):
    """
    WebSocket endpoint for real-time session updates.

    Streams events during:
    - Cleanup plan generation (with AI)
    - Routing plan generation (with AI)
    - Execution progress
    """
    await websocket.accept()

    try:
        session = await manager.get_session(session_id)
        if not session:
            await _send_stream_event(
                websocket,
                "error",
                session_id,
                {"message": f"Session not found: {session_id}"},
            )
            await websocket.close()
            return

        # Send initial status
        await _send_stream_event(
            websocket,
            "connected",
            session_id,
            {
                "phase": session.phase.value,
                "message": "Connected to session stream",
            },
        )

        # Listen for commands
        while True:
            try:
                message = await websocket.receive_json()
                command = message.get("command")
                session = await manager.get_session(session_id)
                if not session:
                    await _send_stream_event(
                        websocket,
                        "error",
                        session_id,
                        {"message": f"Session not found: {session_id}"},
                    )
                    break

                if command == "generate_cleanup":
                    if session.pending_questions:
                        question = session.pending_questions[0]
                        await _send_stream_event(
                            websocket,
                            "question",
                            session_id,
                            question.model_dump(mode="json"),
                            timestamp=question.created_at,
                        )
                        continue

                    # Stream cleanup plan generation
                    async for event in manager.generate_cleanup_plan_with_ai(session_id):
                        await _send_stream_event(
                            websocket,
                            event.type.value if hasattr(event.type, "value") else str(event.type),
                            session_id,
                            {
                                "message": event.message,
                                "progress": event.progress if hasattr(event, "progress") else None,
                                "data": event.data,
                            },
                            timestamp=getattr(event, "timestamp", None),
                        )

                elif command == "generate_routing":
                    if session.pending_questions:
                        question = session.pending_questions[0]
                        await _send_stream_event(
                            websocket,
                            "question",
                            session_id,
                            question.model_dump(mode="json"),
                            timestamp=question.created_at,
                        )
                        continue

                    # Stream routing plan generation
                    async for event in manager.generate_routing_plan_with_ai(session_id):
                        await _send_stream_event(
                            websocket,
                            event.type.value if hasattr(event.type, "value") else str(event.type),
                            session_id,
                            {
                                "message": event.message,
                                "progress": event.progress if hasattr(event, "progress") else None,
                                "data": event.data,
                            },
                            timestamp=getattr(event, "timestamp", None),
                        )

                elif command == "user_message":
                    text = message.get("message")
                    if not text:
                        await _send_stream_event(
                            websocket,
                            "error",
                            session_id,
                            {"message": "user_message requires message"},
                        )
                        continue

                    turn = ConversationTurn(role="user", content=text)
                    session.conversation_history.append(turn)
                    await manager.storage.save(session)
                    await _send_stream_event(
                        websocket,
                        "user_message",
                        session_id,
                        turn.model_dump(mode="json"),
                        timestamp=turn.timestamp,
                    )

                elif command == "answer":
                    answer_text = message.get("answer")
                    if not answer_text:
                        await _send_stream_event(
                            websocket,
                            "error",
                            session_id,
                            {"message": "answer requires answer"},
                        )
                        continue

                    try:
                        _pop_pending_question(session, message.get("question_id"))
                        await manager.storage.save(session)  # Save immediately after mutation
                    except ValueError as e:
                        await _send_stream_event(
                            websocket,
                            "error",
                            session_id,
                            {"message": str(e)},
                        )
                        continue

                    turn = ConversationTurn(role="user", content=answer_text)
                    session.conversation_history.append(turn)
                    await manager.storage.save(session)
                    await _send_stream_event(
                        websocket,
                        "user_message",
                        session_id,
                        turn.model_dump(mode="json"),
                        timestamp=turn.timestamp,
                    )

                elif command == "ping":
                    await _send_stream_event(websocket, "pong", session_id, {})

                else:
                    await _send_stream_event(
                        websocket,
                        "error",
                        session_id,
                        {"message": f"Unknown command: {command}"},
                    )

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.exception("WebSocket error for session %s", session_id)
        try:
            await _send_stream_event(
                websocket,
                "error",
                session_id,
                {"message": str(e)},
            )
        except Exception:
            logger.debug("Failed to send error message to WebSocket client")
        await websocket.close()
