# Sub-Plan D: REST API (Phase 4)

> **Master Plan Reference**: `knowledge-library-master-plan.md`
> **Execution Location**: This repository (`knowledge-library`)
> **Dependencies**: Sub-Plan A (Core Engine), Sub-Plan B (Smart Routing), Sub-Plan C (Vector/RAG)
> **Next Phase**: Sub-Plan E (Query Mode)

---

## Goal

Build HTTP endpoints for web UI integration with WebSocket streaming. This phase exposes all backend functionality through a REST API that the frontend can consume.

---

## Prerequisites from Previous Phases

Before starting this phase, ensure:

**From Sub-Plan A:**

- All data models implemented
- Session management working
- CleanupPlan + RoutingPlan models stable
- Execution + verification engine working (write + read-back + checksums)

**From Sub-Plan B:**

- Planning flow working (CleanupPlan then RoutingPlan)
- Top-3 routing options per block working (manifest-constrained)
- All-blocks-resolved gate working (including explicit discard)

**From Sub-Plan C:**

- Vector store functional
- Semantic search working
- Library indexer operational

---

## New Components

### Project Structure Additions

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry
│   ├── dependencies.py           # Dependency injection
│   ├── schemas.py                # Request/response schemas
│   └── routes/
│       ├── __init__.py
│       ├── sessions.py           # Session CRUD + decisions
│       ├── library.py            # Library browsing
│       └── query.py              # Search endpoints (prep for Phase 6)
```

---

## Implementation Details

### 1. FastAPI Application (`src/api/main.py`)

```python
# src/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import anyio

from .routes import sessions, library, query
from ..config import get_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    config = await get_config()
    app.state.config = config
    print(f"Starting Knowledge Library API...")
    print(f"Library path: {config.library.path}")

    yield

    # Shutdown
    print("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = anyio.run(get_config)

    app = FastAPI(
        title="Knowledge Library API",
        description="Personal Knowledge Library System - The Reliable Librarian",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(
        sessions.router,
        prefix="/api/sessions",
        tags=["sessions"]
    )
    app.include_router(
        library.router,
        prefix="/api/library",
        tags=["library"]
    )
    app.include_router(
        query.router,
        prefix="/api/query",
        tags=["query"]
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    @app.get("/api")
    async def api_info():
        """API information."""
        return {
            "name": "Knowledge Library API",
            "version": "0.1.0",
            "endpoints": {
                "sessions": "/api/sessions",
                "library": "/api/library",
                "query": "/api/query",
            }
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    config = anyio.run(get_config)
    uvicorn.run(
        "src.api.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=True,
    )
```

---

### 2. API Schemas (`src/api/schemas.py`)

```python
# src/api/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from ..models.session import SessionPhase
from ..models.content_mode import ContentMode


# ============== Session Schemas ==============

class CreateSessionRequest(BaseModel):
    """Request to create a new extraction session."""
    source_content: Optional[str] = None
    source_name: Optional[str] = None
    library_path: str = "./library"


class UploadSourceRequest(BaseModel):
    """Request to upload source content to session."""
    content: str
    filename: str


class SessionResponse(BaseModel):
    """Response with session state."""
    id: str
    phase: SessionPhase
    content_mode: ContentMode
    created_at: datetime
    updated_at: datetime

    source_file: Optional[str] = None
    total_blocks: int = 0
    kept_blocks: int = 0
    discarded_blocks: int = 0

    cleanup_pending: int = 0
    cleanup_approved: bool = False

    routing_pending: int = 0
    plan_approved: bool = False

    can_execute: bool = False
    source_deleted: bool = False

    @classmethod
    def from_session(cls, session) -> "SessionResponse":
        """Create response from session model."""
        total_blocks = len(session.source.blocks) if session.source else 0
        discarded_blocks = 0
        cleanup_pending = 0
        cleanup_approved = False

        if session.cleanup_plan:
            cleanup_approved = session.cleanup_plan.approved
            cleanup_pending = sum(1 for i in session.cleanup_plan.items if i.final_disposition is None)
            discarded_blocks = sum(1 for i in session.cleanup_plan.items if i.final_disposition == "discard")

        kept_blocks = total_blocks - discarded_blocks

        routing_pending = session.routing_plan.pending_count if session.routing_plan else 0
        plan_approved = session.routing_plan.approved if session.routing_plan else False

        return cls(
            id=session.id,
            phase=session.phase,
            content_mode=session.content_mode,
            created_at=session.created_at,
            updated_at=session.updated_at,
            source_file=session.source.file_path if session.source else None,
            total_blocks=total_blocks,
            kept_blocks=kept_blocks,
            discarded_blocks=discarded_blocks,
            cleanup_pending=cleanup_pending,
            cleanup_approved=cleanup_approved,
            routing_pending=routing_pending,
            plan_approved=plan_approved,
            can_execute=session.can_execute,
            source_deleted=session.source_deleted,
        )


class SessionListResponse(BaseModel):
    """Response with list of sessions."""
    sessions: List[SessionResponse]
    total: int


# ============== Block Schemas ==============

class ContentBlockResponse(BaseModel):
    """Response with content block details."""
    id: str
    content: str
    block_type: str
    heading_path: List[str] = Field(default_factory=list)
    checksum_exact: str
    checksum_canonical: str
    integrity_verified: bool
    is_executed: bool


# ============== Execution Schemas ==============

class ExecuteRequest(BaseModel):
    """Request to execute approved changes."""
    delete_source: bool = False


class ExecuteResponse(BaseModel):
    """Response from execution with verification status."""
    success: bool
    blocks_written: int = 0
    blocks_verified: int = 0
    checksums_matched: int = 0
    refinements_applied: int = 0  # If refinement mode
    log: List[str] = Field(default_factory=list)
    source_deleted: bool = False
    errors: List[str] = Field(default_factory=list)


# ============== Cleanup Schemas (NEW) ==============

class CleanupItemResponse(BaseModel):
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str
    suggested_disposition: str           # "keep" | "discard"
    suggestion_reason: str
    final_disposition: Optional[str] = None  # "keep" | "discard"


class CleanupPlanResponse(BaseModel):
    session_id: str
    source_file: str
    items: List[CleanupItemResponse]
    pending_count: int
    all_decided: bool
    approved: bool


class CleanupDecisionRequest(BaseModel):
    disposition: str  # "keep" | "discard"


# ============== Plan Schemas (NEW) ==============

class RoutingPlanResponse(BaseModel):
    """Complete routing plan for review."""
    session_id: str
    content_mode: str
    source_file: str

    blocks: List["BlockRoutingItemResponse"]
    merge_previews: List["MergePreviewResponse"]
    summary: "PlanSummaryResponse"

    pending_count: int
    accepted_count: int
    all_resolved: bool


class DestinationOptionResponse(BaseModel):
    """One of the top-3 destination options for a block."""
    destination_file: str
    destination_section: Optional[str] = None
    action: str
    confidence: float
    reasoning: str
    proposed_file_title: Optional[str] = None
    proposed_section_title: Optional[str] = None


class BlockRoutingItemResponse(BaseModel):
    """Single block in the routing plan (top-3 options + user selection)."""
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str
    options: List[DestinationOptionResponse] = Field(default_factory=list)  # length 3

    # User selection (click-based)
    selected_option_index: Optional[int] = None
    custom_destination_file: Optional[str] = None
    custom_destination_section: Optional[str] = None
    custom_action: Optional[str] = None

    status: str  # "pending" | "selected" | "rejected"


class SelectDestinationRequest(BaseModel):
    """Select one of the top-3 options (or a custom destination) for a block."""
    option_index: Optional[int] = None  # 0..2
    custom_destination_file: Optional[str] = None
    custom_destination_section: Optional[str] = None
    custom_action: Optional[str] = None


class MergePreviewResponse(BaseModel):
    """Preview of a merge operation."""
    merge_id: str
    block_id: str
    existing_content: str
    existing_location: str
    new_content: str
    proposed_merge: str
    merge_reasoning: str


class MergeDecisionRequest(BaseModel):
    """Decision on a merge preview (refinement mode only)."""
    decision: str  # "approve" | "edit" | "separate" | "reject"
    edited_content: Optional[str] = None


class PlanSummaryResponse(BaseModel):
    """Quick summary of the routing plan."""
    total_blocks: int
    blocks_to_new_files: int
    blocks_to_existing_files: int
    blocks_requiring_merge: int
    estimated_actions: int


class RerouteRequest(BaseModel):
    """Request to regenerate the top-3 options for a block (no typing required)."""
    reason_code: str  # e.g., "not_related" | "wrong_granularity" | "needs_new_page" | "other"
    prefer_file: Optional[str] = None
    prefer_section: Optional[str] = None


class RerouteResponse(BaseModel):
    """Response after re-routing."""
    success: bool
    block: BlockRoutingItemResponse
    message: str


# ============== Library Schemas ==============

class LibraryFileResponse(BaseModel):
    """Response with library file information."""
    path: str
    category: str
    title: str
    sections: List[str]
    last_modified: str
    block_count: int


class LibraryCategoryResponse(BaseModel):
    """Response with category information."""
    name: str
    path: str
    description: str
    files: List[LibraryFileResponse]
    subcategories: List["LibraryCategoryResponse"] = Field(default_factory=list)


class LibraryStructureResponse(BaseModel):
    """Response with full library structure."""
    root_path: str
    categories: List[LibraryCategoryResponse]
    total_files: int
    total_blocks: int


# ============== Search Schemas ==============

class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str
    limit: int = 10
    min_similarity: float = 0.5


class SearchResultResponse(BaseModel):
    """A single search result."""
    content: str
    file_path: str
    section: str
    similarity: float
    chunk_id: str


class SearchResponse(BaseModel):
    """Response with search results."""
    query: str
    results: List[SearchResultResponse]
    total: int


# ============== WebSocket Event Schemas ==============

class WSEvent(BaseModel):
    """WebSocket event structure."""
    type: str  # "phase_change" | "cleanup_ready" | "routing_ready" | "question" | "progress" | "error" | "verification"
    data: dict
```

---

### 3. Dependencies (`src/api/dependencies.py`)

```python
# src/api/dependencies.py

from typing import Annotated
from fastapi import Depends, HTTPException, status, Request

from ..config import Config
from ..session.manager import SessionManager
from ..library.scanner import LibraryScanner
from ..vector.search import SemanticSearch


def get_app_config(request: Request) -> Config:
    """Get application configuration loaded at startup."""
    config = getattr(request.app.state, "config", None)
    if not config:
        raise RuntimeError("Config not loaded")
    return config


def get_session_manager(
    config: Annotated[Config, Depends(get_app_config)]
) -> SessionManager:
    """Get session manager instance."""
    return SessionManager(config)


def get_library_scanner(
    config: Annotated[Config, Depends(get_app_config)]
) -> LibraryScanner:
    """Get library scanner instance."""
    return LibraryScanner(config.library.path)


def get_semantic_search(
    config: Annotated[Config, Depends(get_app_config)]
) -> SemanticSearch:
    """Get semantic search instance."""
    return SemanticSearch(config.library.path)


async def get_session_or_404(
    session_id: str,
    manager: Annotated[SessionManager, Depends(get_session_manager)]
):
    """Get session by ID or raise 404."""
    session = await manager.load_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return session
```

---

### 4. Session Routes (`src/api/routes/sessions.py`)

```python
# src/api/routes/sessions.py

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from typing import Annotated, List

from ..dependencies import (
    get_session_manager,
    get_session_or_404,
)
from ..schemas import (
    CreateSessionRequest,
    SessionResponse,
    SessionListResponse,
    ContentBlockResponse,
    MergeDecisionRequest,
    CleanupPlanResponse,
    CleanupDecisionRequest,
    RoutingPlanResponse,
    RerouteRequest,
    RerouteResponse,
    SelectDestinationRequest,
    ExecuteRequest,
    ExecuteResponse,
)
from ...session.manager import SessionManager
from ...models.session import ExtractionSession


router = APIRouter()


# ============== Session CRUD ==============

@router.post("/", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Create a new extraction session."""
    session = await manager.create_session(
        source_content=request.source_content,
        source_name=request.source_name,
        library_path=request.library_path,
    )
    return SessionResponse.from_session(session)


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    manager: Annotated[SessionManager, Depends(get_session_manager)],
    limit: int = 20,
    offset: int = 0,
):
    """List all sessions."""
    sessions = await manager.list_sessions(limit=limit, offset=offset)
    return SessionListResponse(
        sessions=[SessionResponse.from_session(s) for s in sessions],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session: Annotated[ExtractionSession, Depends(get_session_or_404)],
):
    """Get session state."""
    return SessionResponse.from_session(session)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Cancel and delete a session."""
    await manager.delete_session(session_id)
    return {"success": True, "message": f"Session {session_id} deleted"}


# ============== Source Upload ==============

@router.post("/{session_id}/upload", response_model=SessionResponse)
async def upload_source(
    session_id: str,
    file: UploadFile = File(...),
    manager: Annotated[SessionManager, Depends(get_session_manager)] = None,
):
    """Upload source document to session."""
    content = await file.read()

    try:
        decoded_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 encoded text"
        )

    session = await manager.add_source(
        session_id,
        decoded_content,
        file.filename,
    )
    return SessionResponse.from_session(session)


# ============== Blocks ==============

@router.get("/{session_id}/blocks", response_model=List[ContentBlockResponse])
async def get_blocks(
    session: Annotated[ExtractionSession, Depends(get_session_or_404)],
):
    """Get all content blocks from source."""
    if not session.source:
        return []

    return [
        ContentBlockResponse(
            id=block.id,
            content=block.content,
            block_type=block.block_type.value,
            heading_path=block.heading_path,
            checksum_exact=block.checksum_exact,
            checksum_canonical=block.checksum_canonical,
            integrity_verified=block.integrity_verified,
            is_executed=block.is_executed,
        )
        for block in session.source.blocks
    ]


# ============== LEGACY ENDPOINTS (REMOVED) ==============
# Legacy category/recommendation endpoints from the old incremental workflow are removed.
# The current workflow is CleanupPlan → RoutingPlan (top-3 options) → execute.


# ============== Plan Endpoints (NEW) ==============

@router.post("/{session_id}/cleanup/generate", response_model=CleanupPlanResponse)
async def generate_cleanup_plan(
    session_id: str,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Generate the cleanup plan (discard candidates + structuring suggestions)."""
    session = await manager.generate_cleanup_plan(session_id)
    if not session.cleanup_plan:
        raise HTTPException(500, "Cleanup plan generation failed")
    return CleanupPlanResponse.from_plan(session.cleanup_plan)


@router.get("/{session_id}/cleanup", response_model=CleanupPlanResponse)
async def get_cleanup_plan(
    session: Annotated[ExtractionSession, Depends(get_session_or_404)],
):
    """Get the cleanup plan for review (discard candidates + suggestions)."""
    if not session.cleanup_plan:
        raise HTTPException(400, "Cleanup plan not yet generated")
    return CleanupPlanResponse.from_plan(session.cleanup_plan)


@router.post("/{session_id}/cleanup/decide/{block_id}")
async def decide_cleanup_item(
    session_id: str,
    block_id: str,
    request: CleanupDecisionRequest,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Set keep/discard decision for a cleanup item (explicit user action)."""
    session = await manager.set_cleanup_decision(session_id, block_id, request.disposition)
    pending_count = sum(1 for i in session.cleanup_plan.items if i.final_disposition is None)
    return {"success": True, "pending_count": pending_count}


@router.post("/{session_id}/cleanup/approve")
async def approve_cleanup_plan(
    session_id: str,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Approve the cleanup plan. Requires all items decided."""
    session = await manager.approve_cleanup_plan(session_id)
    return {"success": True, "can_route": session.cleanup_plan.approved}


@router.post("/{session_id}/plan/generate", response_model=RoutingPlanResponse)
async def generate_routing_plan(
    session_id: str,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Generate the complete routing plan (top-3 options per kept block)."""
    session = await manager.generate_routing_plan(session_id)
    if not session.routing_plan:
        raise HTTPException(500, "Routing plan generation failed")
    return RoutingPlanResponse.from_plan(session.routing_plan)


@router.get("/{session_id}/plan", response_model=RoutingPlanResponse)
async def get_routing_plan(
    session: Annotated[ExtractionSession, Depends(get_session_or_404)],
):
    """
    Get the complete routing plan for review.

    Returns all blocks with their proposed destinations,
    merge previews, and summary statistics.
    """
    if not session.routing_plan:
        raise HTTPException(400, "Plan not yet generated")

    return RoutingPlanResponse.from_plan(session.routing_plan)


@router.post("/{session_id}/plan/select/{block_id}")
async def select_block_destination(
    session_id: str,
    block_id: str,
    request: SelectDestinationRequest,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Select one of the top-3 options (or a custom destination) for a block."""
    session = await manager.select_block_destination(session_id, block_id, request.model_dump())
    return {
        "success": True,
        "pending_count": session.routing_plan.pending_count,
        "can_execute": session.routing_plan.all_blocks_resolved,
    }


@router.post("/{session_id}/plan/reject-block/{block_id}")
async def reject_block(
    session_id: str,
    block_id: str,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Reject a block (without instruction - just marks as rejected)."""
    session = await manager.reject_block(session_id, block_id)
    return {"success": True}


@router.post("/{session_id}/plan/reroute-block/{block_id}", response_model=RerouteResponse)
async def reroute_block(
    session_id: str,
    block_id: str,
    request: RerouteRequest,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """
    Regenerate the top-3 options for a block using structured feedback.

    Normal flow stays click-based; this endpoint exists for “none of these fit” cases.
    """
    updated_item = await manager.reroute_block(session_id, block_id, request.model_dump())
    return {
        "success": True,
        "block": updated_item.model_dump(),
        "message": "Updated options generated - please choose one of the new top-3",
    }


@router.post("/{session_id}/merges/decide/{merge_id}")
async def decide_merge(
    session_id: str,
    merge_id: str,
    request: MergeDecisionRequest,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Decide on a merge preview (refinement mode only)."""
    await manager.decide_merge(session_id, merge_id, request.model_dump())
    return {"success": True}


@router.post("/{session_id}/plan/approve")
async def approve_plan(
    session_id: str,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """
    Approve the complete plan for execution.

    Only succeeds if all blocks are resolved (accepted).
    """
    session = await manager.load_session(session_id)

    if not session.routing_plan.all_blocks_resolved:
        raise HTTPException(
            400,
            {
                "message": "Cannot approve: not all blocks resolved",
                "pending": session.routing_plan.pending_count,
                "total": len(session.routing_plan.blocks),
            }
        )

    session.routing_plan.approved = True
    session.routing_plan.approved_at = datetime.now()
    session.phase = SessionPhase.READY_TO_EXECUTE

    await manager.save_session(session)

    return {"success": True, "can_execute": True}


@router.post("/{session_id}/mode")
async def set_content_mode(
    session_id: str,
    request: dict,  # {"mode": "strict" | "refinement"}
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Set the content mode for the session."""
    session = await manager.load_session(session_id)
    mode = request.get("mode", "strict")

    if mode not in ("strict", "refinement"):
        raise HTTPException(400, f"Invalid mode: {mode}")

    session.content_mode = ContentMode(mode)
    await manager.save_session(session)

    return {"success": True, "mode": mode}


# ============== Questions ==============

@router.get("/{session_id}/questions")
async def get_pending_questions(
    session: Annotated[ExtractionSession, Depends(get_session_or_404)],
):
    """Get pending questions from the model."""
    return {
        "questions": session.pending_questions,
        "count": len(session.pending_questions),
    }


@router.post("/{session_id}/questions/{question_id}")
async def answer_question(
    session_id: str,
    question_id: str,
    answer: str,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Answer a pending question."""
    session = await manager.answer_question(session_id, question_id, answer)
    return {
        "success": True,
        "remaining_questions": len(session.pending_questions),
    }


# ============== Execution ==============

@router.post("/{session_id}/execute", response_model=ExecuteResponse)
async def execute_session(
    session_id: str,
    request: ExecuteRequest,
    manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Execute all approved changes with verification."""
    session = await manager.load_session(session_id)

    if not session:
        raise HTTPException(404, "Session not found")

    # Check plan is approved (new workflow)
    if not session.routing_plan or not session.routing_plan.approved:
        raise HTTPException(400, "Plan not approved")

    # Execute and get verification results
    success, results = await manager.execute_session(session)

    source_deleted = False
    if success and request.delete_source:
        await manager.delete_source(session)
        source_deleted = True

    return ExecuteResponse(
        success=success,
        blocks_written=results.blocks_written,
        blocks_verified=results.blocks_verified,
        checksums_matched=results.checksums_matched,
        refinements_applied=results.refinements_applied,
        log=results.log,
        source_deleted=source_deleted,
        errors=results.errors,
    )


# ============== WebSocket Streaming ==============

@router.websocket("/{session_id}/stream")
async def session_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket for real-time session updates.

    Events:
    - phase_change: Session phase changed
    - cleanup_ready: Cleanup plan generated
    - routing_ready: Routing plan generated
    - question: Model asks a question
    - progress: Planning/execution progress
    - verification: Write verification results
    - error: Error occurred
    - complete: Session complete
    """
    await websocket.accept()

    app = websocket.scope["app"]
    manager = SessionManager(app.state.config)

    try:
        # Subscribe to session events
        async for event in manager.stream_session(session_id):
            await websocket.send_json({
                "type": event.type,
                "data": event.data,
                "timestamp": event.timestamp.isoformat() if hasattr(event, 'timestamp') else None,
            })

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "data": {"message": str(e)},
        })

    finally:
        await websocket.close()
```

---

### 5. Library Routes (`src/api/routes/library.py`)

```python
# src/api/routes/library.py

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from pathlib import Path

from ..dependencies import get_library_scanner, get_semantic_search
from ..schemas import (
    LibraryStructureResponse,
    LibraryCategoryResponse,
    LibraryFileResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
)
from ...library.scanner import LibraryScanner
from ...vector.search import SemanticSearch


router = APIRouter()


@router.get("/", response_model=LibraryStructureResponse)
async def get_library_structure(
    scanner: Annotated[LibraryScanner, Depends(get_library_scanner)],
):
    """Get the complete library structure."""
    structure = await scanner.get_structure()
    return LibraryStructureResponse(
        root_path=str(scanner.library_path),
        categories=[
            _convert_category(cat) for cat in structure.categories
        ],
        total_files=structure.total_files,
        total_blocks=structure.total_blocks,
    )


@router.get("/categories", response_model=list[LibraryCategoryResponse])
async def get_categories(
    scanner: Annotated[LibraryScanner, Depends(get_library_scanner)],
):
    """Get all categories."""
    categories = await scanner.get_categories()
    return [_convert_category(cat) for cat in categories]


@router.get("/files/{path:path}")
async def get_file(
    path: str,
    scanner: Annotated[LibraryScanner, Depends(get_library_scanner)],
):
    """Get a specific library file."""
    file_info = await scanner.get_file(path)

    if not file_info:
        raise HTTPException(404, f"File not found: {path}")

    return {
        "path": file_info.path,
        "category": file_info.category,
        "title": file_info.title,
        "sections": file_info.sections,
        "last_modified": file_info.last_modified,
        "content": await scanner.read_file_content(path),
    }


@router.get("/search")
async def search_library(
    q: str,
    limit: int = 10,
    min_similarity: float = 0.5,
    search: Annotated[SemanticSearch, Depends(get_semantic_search)] = None,
):
    """Search library content using semantic search."""
    # Ensure indexed
    await search.ensure_indexed()

    results = await search.search(
        query=q,
        n_results=limit,
        min_similarity=min_similarity,
    )

    return SearchResponse(
        query=q,
        results=[
            SearchResultResponse(
                content=r.content,
                file_path=r.file_path,
                section=r.section,
                similarity=r.similarity,
                chunk_id=r.chunk_id,
            )
            for r in results
        ],
        total=len(results),
    )


@router.post("/index")
async def index_library(
    force: bool = False,
    search: Annotated[SemanticSearch, Depends(get_semantic_search)] = None,
):
    """Trigger library indexing."""
    results = await search.ensure_indexed(force=force)
    stats = search.get_stats()

    return {
        "indexed_files": len(results),
        "files": results,
        "stats": stats,
    }


def _convert_category(cat) -> LibraryCategoryResponse:
    """Convert internal category to response model."""
    return LibraryCategoryResponse(
        name=cat.name,
        path=cat.path,
        description=cat.description,
        files=[
            LibraryFileResponse(
                path=f.path,
                category=f.category,
                title=f.title,
                sections=f.sections,
                last_modified=f.last_modified,
                block_count=f.block_count,
            )
            for f in cat.files
        ],
        subcategories=[_convert_category(sub) for sub in cat.subcategories],
    )
```

---

### 6. Query Routes (Prep for Phase 6) (`src/api/routes/query.py`)

```python
# src/api/routes/query.py

from fastapi import APIRouter, Depends
from typing import Annotated

from ..dependencies import get_semantic_search
from ..schemas import SearchRequest, SearchResponse, SearchResultResponse
from ...vector.search import SemanticSearch


router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    search: Annotated[SemanticSearch, Depends(get_semantic_search)],
):
    """
    Perform semantic search on the knowledge library.

    This endpoint is preparation for the full query mode in Phase 6.
    Currently returns raw search results without RAG generation.
    """
    await search.ensure_indexed()

    results = await search.search(
        query=request.query,
        n_results=request.limit,
        min_similarity=request.min_similarity,
    )

    return SearchResponse(
        query=request.query,
        results=[
            SearchResultResponse(
                content=r.content,
                file_path=r.file_path,
                section=r.section,
                similarity=r.similarity,
                chunk_id=r.chunk_id,
            )
            for r in results
        ],
        total=len(results),
    )


# Placeholder for Phase 6 query endpoint
@router.post("/ask")
async def query_library(
    question: str,
    conversation_id: str = None,
):
    """
    Query the knowledge library with natural language.

    NOTE: Full implementation in Phase 6 (Sub-Plan E).
    Currently returns a placeholder response.
    """
    return {
        "message": "Full query mode will be implemented in Phase 6",
        "question": question,
        "hint": "Use /search for semantic search in the meantime",
    }
```

---

### 7. Configuration Updates

Add to `src/config.py`:

```python
# Add to src/config.py

class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = Field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:5173",
    ])


class Config(BaseModel):
    # ... existing fields ...
    api: APIConfig = Field(default_factory=APIConfig)
```

Add to `configs/settings.yaml`:

```yaml
# API settings
api:
  host: ${API_HOST:0.0.0.0}
  port: ${API_PORT:8000}
  cors_origins:
    - http://localhost:3000
    - http://localhost:5173
```

---

### 8. Dependencies Update

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "python-multipart>=0.0.6",  # For file uploads
    "websockets>=12.0",         # For WebSocket support
]
```

---

### 9. Run Script

Create `run_api.py` in project root:

```python
#!/usr/bin/env python
"""Run the Knowledge Library API server."""

import uvicorn
from src.config import get_config
import anyio


def main():
    config = anyio.run(get_config)

    print(f"Starting Knowledge Library API...")
    print(f"  Host: {config.api.host}")
    print(f"  Port: {config.api.port}")
    print(f"  Library: {config.library.path}")

    uvicorn.run(
        "src.api.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
```

---

## API Endpoint Summary

### Sessions (`/api/sessions`)

| Method | Endpoint                              | Description                                 |
| ------ | ------------------------------------- | ------------------------------------------- |
| POST   | `/`                                   | Create new session (with content_mode)      |
| GET    | `/`                                   | List all sessions                           |
| GET    | `/{id}`                               | Get session state                           |
| DELETE | `/{id}`                               | Delete session                              |
| POST   | `/{id}/upload`                        | Upload source document                      |
| GET    | `/{id}/blocks`                        | Get content blocks                          |
| POST   | `/{id}/cleanup/generate`              | Generate cleanup plan                       |
| GET    | `/{id}/cleanup`                       | Get cleanup plan                            |
| POST   | `/{id}/cleanup/decide/{block_id}`     | Decide keep/discard (explicit)              |
| POST   | `/{id}/cleanup/approve`               | Approve cleanup plan                        |
| POST   | `/{id}/plan/generate`                 | Generate complete routing plan              |
| GET    | `/{id}/plan`                          | Get complete routing plan                   |
| POST   | `/{id}/plan/select/{block_id}`        | Select one of top-3 (or custom) destination |
| POST   | `/{id}/plan/reject-block/{block_id}`  | Reject block                                |
| POST   | `/{id}/plan/reroute-block/{block_id}` | Regenerate top-3 options (optional)         |
| POST   | `/{id}/merges/decide/{merge_id}`      | Decide merge preview (refinement mode only) |
| POST   | `/{id}/plan/approve`                  | Approve complete plan                       |
| POST   | `/{id}/mode`                          | Set content mode (strict/refinement)        |
| POST   | `/{id}/execute`                       | Execute approved plan                       |
| WS     | `/{id}/stream`                        | Real-time updates                           |

**REMOVED Endpoints** (replaced by plan-based workflow):

- ~~POST `/{id}/categories/{cat_id}`~~
- ~~POST `/{id}/categories/approve-all`~~
- ~~POST `/{id}/recommendations/{rec_id}`~~
- ~~POST `/{id}/recommendations/approve-all`~~
- ~~POST `/{id}/merges/{merge_id}`~~ (replaced by `/{id}/merges/decide/{merge_id}`)

### Library (`/api/library`)

| Method | Endpoint        | Description           |
| ------ | --------------- | --------------------- |
| GET    | `/`             | Get library structure |
| GET    | `/categories`   | Get all categories    |
| GET    | `/files/{path}` | Get specific file     |
| GET    | `/search?q=`    | Search library        |
| POST   | `/index`        | Trigger indexing      |

### Query (`/api/query`)

| Method | Endpoint  | Description             |
| ------ | --------- | ----------------------- |
| POST   | `/search` | Semantic search         |
| POST   | `/ask`    | Query library (Phase 6) |

---

## Acceptance Criteria

- [ ] FastAPI application structure complete
- [ ] Session CRUD endpoints working
- [ ] Source upload endpoint working
- [ ] Cleanup endpoints working (get, decide keep/discard, approve)
- [ ] Plan endpoints working (get, select top-3/custom, reject, reroute optional, approve)
- [ ] Content mode endpoint working (strict/refinement toggle)
- [ ] Re-routing (optional) returns refreshed options for user selection
- [ ] Execute endpoint checks plan approval
- [ ] ExecuteResponse includes verification fields (blocks_written, checksums_matched, etc.)
- [ ] WebSocket streaming working
- [ ] Library browsing endpoints working
- [ ] Search endpoint working
- [ ] CORS configured for frontend origins
- [ ] Health check endpoint
- [ ] Error handling with proper HTTP status codes

---

## Notes for Downstream Session

1. **CORS Origins**: Update `configs/settings.yaml` with your frontend URL before deployment
2. **WebSocket**: The `/stream` endpoint provides real-time updates during extraction flow
3. **Phase 6 Integration**: The `/api/query/ask` endpoint is a placeholder - full implementation comes in Sub-Plan E
4. **Authentication**: No auth in this phase - add in future if needed for multi-user
5. **Testing**: Use FastAPI's built-in Swagger UI at `/docs` for API testing

---

## Running the API

```bash
# Using the run script
python run_api.py

# Or directly with uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Access Swagger UI
open http://localhost:8000/docs
```

---

_End of Sub-Plan D_
