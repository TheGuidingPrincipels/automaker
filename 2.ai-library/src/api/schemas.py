# src/api/schemas.py
"""API request and response schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from ..models.session import ExtractionSession, SessionPhase
from ..models.content import ContentBlock, BlockType
from ..models.content_mode import ContentMode
from ..models.cleanup_plan import CleanupPlan, CleanupItem, CleanupDisposition
from ..models.routing_plan import (
    RoutingPlan,
    BlockRoutingItem,
    BlockDestination,
    MergePreview,
    PlanSummary,
    validate_overview_text,
)
from ..models.library import LibraryFile, LibraryCategory


# =============================================================================
# Generic Responses
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: Optional[str] = None


# =============================================================================
# Session Schemas
# =============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    source_path: Optional[str] = None
    library_path: Optional[str] = None
    content_mode: str = "strict"  # "strict" or "refinement"


class SessionResponse(BaseModel):
    """Response with session details."""
    id: str
    phase: str
    created_at: datetime
    updated_at: datetime
    content_mode: str
    library_path: str
    source_file: Optional[str] = None
    total_blocks: int = 0
    kept_blocks: int = 0
    discarded_blocks: int = 0
    has_cleanup_plan: bool = False
    has_routing_plan: bool = False
    cleanup_approved: bool = False
    routing_approved: bool = False
    can_execute: bool = False
    errors: List[str] = Field(default_factory=list)

    @classmethod
    def from_session(cls, session: ExtractionSession) -> "SessionResponse":
        """Create response from session model."""
        total_blocks = 0
        discarded_blocks = 0

        if session.source:
            total_blocks = len(session.source.blocks)

        if session.cleanup_plan:
            discarded_blocks = sum(
                1 for item in session.cleanup_plan.items
                if item.final_disposition == CleanupDisposition.DISCARD
            )

        return cls(
            id=session.id,
            phase=session.phase.value,
            created_at=session.created_at,
            updated_at=session.updated_at,
            content_mode=session.content_mode.value,
            library_path=session.library_path,
            source_file=session.source.file_path if session.source else None,
            total_blocks=total_blocks,
            kept_blocks=total_blocks - discarded_blocks,
            discarded_blocks=discarded_blocks,
            has_cleanup_plan=session.cleanup_plan is not None,
            has_routing_plan=session.routing_plan is not None,
            cleanup_approved=session.cleanup_plan.approved if session.cleanup_plan else False,
            routing_approved=session.routing_plan.approved if session.routing_plan else False,
            can_execute=session.can_execute,
            errors=session.errors,
        )


class SessionListResponse(BaseModel):
    """Response with list of sessions."""
    sessions: List[SessionResponse]
    total: int


# =============================================================================
# Block Schemas
# =============================================================================


class BlockResponse(BaseModel):
    """Response with block details."""
    id: str
    block_type: str
    content: str
    content_preview: str
    heading_path: List[str]
    source_file: str
    source_line_start: int
    source_line_end: int
    checksum_exact: str
    checksum_canonical: str
    is_executed: bool
    integrity_verified: bool

    @classmethod
    def from_block(cls, block: ContentBlock) -> "BlockResponse":
        """Create response from block model."""
        return cls(
            id=block.id,
            block_type=block.block_type.value,
            content=block.content,
            content_preview=block.content[:200] if len(block.content) > 200 else block.content,
            heading_path=block.heading_path,
            source_file=block.source_file,
            source_line_start=block.source_line_start,
            source_line_end=block.source_line_end,
            checksum_exact=block.checksum_exact,
            checksum_canonical=block.checksum_canonical,
            is_executed=block.is_executed,
            integrity_verified=block.integrity_verified,
        )


class BlockListResponse(BaseModel):
    """Response with list of blocks."""
    blocks: List[BlockResponse]
    total: int


# =============================================================================
# Cleanup Schemas
# =============================================================================


class CleanupItemResponse(BaseModel):
    """Response for a cleanup item."""
    block_id: str
    heading_path: List[str]
    content_preview: str
    suggested_disposition: str
    suggestion_reason: str
    final_disposition: Optional[str] = None

    @classmethod
    def from_item(cls, item: CleanupItem) -> "CleanupItemResponse":
        """Create response from cleanup item."""
        return cls(
            block_id=item.block_id,
            heading_path=item.heading_path,
            content_preview=item.content_preview,
            suggested_disposition=item.suggested_disposition,
            suggestion_reason=item.suggestion_reason,
            final_disposition=item.final_disposition,
        )


class CleanupPlanResponse(BaseModel):
    """Response with cleanup plan."""
    session_id: str
    source_file: str
    created_at: datetime
    items: List[CleanupItemResponse]
    all_decided: bool
    approved: bool
    approved_at: Optional[datetime] = None
    pending_count: int
    total_count: int

    @classmethod
    def from_plan(cls, plan: CleanupPlan) -> "CleanupPlanResponse":
        """Create response from cleanup plan."""
        pending_count = sum(
            1 for item in plan.items
            if item.final_disposition is None
        )
        return cls(
            session_id=plan.session_id,
            source_file=plan.source_file,
            created_at=plan.created_at,
            items=[CleanupItemResponse.from_item(item) for item in plan.items],
            all_decided=plan.all_decided,
            approved=plan.approved,
            approved_at=plan.approved_at,
            pending_count=pending_count,
            total_count=len(plan.items),
        )


class CleanupDecisionRequest(BaseModel):
    """Request to set cleanup decision."""
    disposition: str  # "keep" or "discard"


# =============================================================================
# Routing Schemas
# =============================================================================


class DestinationOptionResponse(BaseModel):
    """Response for a destination option."""
    destination_file: str
    destination_section: Optional[str] = None
    action: str
    confidence: float
    reasoning: str
    proposed_file_title: Optional[str] = None
    proposed_file_overview: Optional[str] = None
    proposed_section_title: Optional[str] = None

    @classmethod
    def from_destination(cls, dest: BlockDestination) -> "DestinationOptionResponse":
        """Create response from destination."""
        return cls(
            destination_file=dest.destination_file,
            destination_section=dest.destination_section,
            action=dest.action,
            confidence=dest.confidence,
            reasoning=dest.reasoning,
            proposed_file_title=dest.proposed_file_title,
            proposed_file_overview=dest.proposed_file_overview,
            proposed_section_title=dest.proposed_section_title,
        )


class BlockRoutingItemResponse(BaseModel):
    """Response for a routing item."""
    block_id: str
    heading_path: List[str]
    content_preview: str
    options: List[DestinationOptionResponse]
    selected_option_index: Optional[int] = None
    custom_destination_file: Optional[str] = None
    custom_destination_section: Optional[str] = None
    custom_action: Optional[str] = None
    custom_proposed_file_title: Optional[str] = None
    custom_proposed_file_overview: Optional[str] = None
    status: str

    @classmethod
    def from_item(cls, item: BlockRoutingItem) -> "BlockRoutingItemResponse":
        """Create response from routing item."""
        return cls(
            block_id=item.block_id,
            heading_path=item.heading_path,
            content_preview=item.content_preview,
            options=[DestinationOptionResponse.from_destination(opt) for opt in item.options],
            selected_option_index=item.selected_option_index,
            custom_destination_file=item.custom_destination_file,
            custom_destination_section=item.custom_destination_section,
            custom_action=item.custom_action,
            custom_proposed_file_title=item.custom_proposed_file_title,
            custom_proposed_file_overview=item.custom_proposed_file_overview,
            status=item.status,
        )


class MergePreviewResponse(BaseModel):
    """Response for merge preview."""
    merge_id: str
    block_id: str
    existing_content: str
    existing_location: str
    new_content: str
    proposed_merge: str
    merge_reasoning: str

    @classmethod
    def from_preview(cls, preview: MergePreview) -> "MergePreviewResponse":
        """Create response from merge preview."""
        return cls(
            merge_id=preview.merge_id,
            block_id=preview.block_id,
            existing_content=preview.existing_content,
            existing_location=preview.existing_location,
            new_content=preview.new_content,
            proposed_merge=preview.proposed_merge,
            merge_reasoning=preview.merge_reasoning,
        )


class PlanSummaryResponse(BaseModel):
    """Response for plan summary."""
    total_blocks: int
    blocks_to_new_files: int
    blocks_to_existing_files: int
    blocks_requiring_merge: int
    estimated_actions: int

    @classmethod
    def from_summary(cls, summary: Optional[PlanSummary]) -> Optional["PlanSummaryResponse"]:
        """Create response from summary."""
        if not summary:
            return None
        return cls(
            total_blocks=summary.total_blocks,
            blocks_to_new_files=summary.blocks_to_new_files,
            blocks_to_existing_files=summary.blocks_to_existing_files,
            blocks_requiring_merge=summary.blocks_requiring_merge,
            estimated_actions=summary.estimated_actions,
        )


class RoutingPlanResponse(BaseModel):
    """Response with routing plan."""
    session_id: str
    source_file: str
    content_mode: str
    created_at: datetime
    blocks: List[BlockRoutingItemResponse]
    merge_previews: List[MergePreviewResponse]
    summary: Optional[PlanSummaryResponse] = None
    all_blocks_resolved: bool
    approved: bool
    approved_at: Optional[datetime] = None
    pending_count: int
    accepted_count: int

    @classmethod
    def from_plan(cls, plan: RoutingPlan) -> "RoutingPlanResponse":
        """Create response from routing plan."""
        return cls(
            session_id=plan.session_id,
            source_file=plan.source_file,
            content_mode=plan.content_mode,
            created_at=plan.created_at,
            blocks=[BlockRoutingItemResponse.from_item(b) for b in plan.blocks],
            merge_previews=[MergePreviewResponse.from_preview(m) for m in plan.merge_previews],
            summary=PlanSummaryResponse.from_summary(plan.summary),
            all_blocks_resolved=plan.all_blocks_resolved,
            approved=plan.approved,
            approved_at=plan.approved_at,
            pending_count=plan.pending_count,
            accepted_count=plan.accepted_count,
        )


class SelectDestinationRequest(BaseModel):
    """Request to select destination."""
    option_index: Optional[int] = None  # 0, 1, or 2
    custom_file: Optional[str] = None
    custom_section: Optional[str] = None
    custom_action: Optional[str] = None
    proposed_file_title: Optional[str] = None
    proposed_file_overview: Optional[str] = None

    @field_validator("proposed_file_overview")
    @classmethod
    def validate_proposed_file_overview(cls, v: Optional[str]) -> Optional[str]:
        return validate_overview_text(v)


class MergeDecisionRequest(BaseModel):
    """Request to decide on merge."""
    accept: bool
    edited_content: Optional[str] = None  # If user edits the merge


class SetContentModeRequest(BaseModel):
    """Request to set content mode."""
    mode: str  # "strict" or "refinement"


# =============================================================================
# Execution Schemas
# =============================================================================


class WriteResultResponse(BaseModel):
    """Response for a single write result."""
    block_id: str
    destination_file: str
    success: bool
    checksum_verified: bool
    error: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Response for execution."""
    session_id: str
    success: bool
    total_blocks: int
    blocks_written: int
    blocks_failed: int
    all_verified: bool
    results: List[WriteResultResponse]
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# Library Schemas
# =============================================================================


class LibraryFileResponse(BaseModel):
    """Response for library file."""
    path: str
    category: str
    title: str
    overview: Optional[str] = None
    sections: List[str]
    last_modified: str
    block_count: int
    is_valid: bool
    validation_errors: List[str]

    @classmethod
    def from_file(cls, file: LibraryFile) -> "LibraryFileResponse":
        """Create response from library file."""
        return cls(
            path=file.path,
            category=file.category,
            title=file.title,
            overview=file.overview,
            sections=file.sections,
            last_modified=file.last_modified,
            block_count=file.block_count,
            is_valid=file.is_valid,
            validation_errors=file.validation_errors,
        )


class LibraryCategoryResponse(BaseModel):
    """Response for library category."""
    name: str
    path: str
    description: str
    files: List[LibraryFileResponse]
    subcategories: List["LibraryCategoryResponse"]

    @classmethod
    def from_category(cls, cat: LibraryCategory) -> "LibraryCategoryResponse":
        """Create response from category."""
        return cls(
            name=cat.name,
            path=cat.path,
            description=cat.description,
            files=[LibraryFileResponse.from_file(f) for f in cat.files],
            subcategories=[cls.from_category(sub) for sub in cat.subcategories],
        )


class LibraryStructureResponse(BaseModel):
    """Response for library structure."""
    categories: List[LibraryCategoryResponse]
    total_files: int
    total_sections: int


class LibrarySearchResult(BaseModel):
    """Single search result."""
    file_path: str
    file_title: str
    section: str
    category: str


class LibrarySearchResponse(BaseModel):
    """Response for library search."""
    results: List[LibrarySearchResult]
    query: str
    total: int


class IndexResponse(BaseModel):
    """Response for indexing operation."""
    status: str
    files_indexed: int
    details: Optional[List[str]] = None


# =============================================================================
# Query/Search Schemas
# =============================================================================


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str
    n_results: int = 5
    min_similarity: float = 0.5
    filter_taxonomy: Optional[str] = None
    filter_content_type: Optional[str] = None


class SearchResultResponse(BaseModel):
    """Response for a single search result."""
    content: str
    file_path: str
    section: str
    similarity: float
    chunk_id: str
    taxonomy_path: Optional[str] = None
    content_type: Optional[str] = None


class SearchResponse(BaseModel):
    """Response for search."""
    results: List[SearchResultResponse]
    query: str
    total: int


class AskRequest(BaseModel):
    """Request to ask the library using RAG."""
    question: str
    max_sources: int = 10
    conversation_id: Optional[str] = None  # For multi-turn conversations

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate conversation_id is a valid UUID format if provided."""
        if v is not None:
            try:
                UUID(v)
            except ValueError:
                raise ValueError("conversation_id must be a valid UUID")
        return v


class SourceInfo(BaseModel):
    """Information about a source used in an answer."""
    file_path: str
    section: Optional[str] = None
    similarity: Optional[float] = None


class AskResponse(BaseModel):
    """Response for ask with RAG-generated answer."""
    answer: str
    sources: List[SourceInfo]
    confidence: float
    conversation_id: Optional[str] = None
    related_topics: List[str] = Field(default_factory=list)


# =============================================================================
# Conversation Schemas
# =============================================================================


class ConversationTurnResponse(BaseModel):
    """A single turn in a conversation."""
    role: str
    content: str
    timestamp: str
    sources: List[str] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    """Response with conversation details."""
    id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    turns: List[ConversationTurnResponse] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    """Response with list of conversations."""
    conversations: List[ConversationResponse]
    total: int


class FindSimilarResultResponse(BaseModel):
    """Response for a single similar content result."""
    content: str
    file_path: str
    section: str
    similarity: float
    chunk_id: str


class FindSimilarResponse(BaseModel):
    """Response for find similar endpoint."""
    results: List[FindSimilarResultResponse]
    total: int


# =============================================================================
# WebSocket Event Schemas
# =============================================================================


class StreamEvent(BaseModel):
    """WebSocket stream event."""
    event_type: str
    session_id: str
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
