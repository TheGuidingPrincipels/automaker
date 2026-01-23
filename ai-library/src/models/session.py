# src/models/session.py

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from .content import SourceDocument
from .content_mode import ContentMode
from .cleanup_plan import CleanupPlan
from .routing_plan import RoutingPlan


class SessionPhase(str, Enum):
    INITIALIZED = "initialized"           # Session created
    PARSING = "parsing"                   # Reading file and extracting blocks
    CLEANUP_PLAN_READY = "cleanup_plan_ready"   # Cleanup/structuring plan generated
    ROUTING_PLAN_READY = "routing_plan_ready"   # Complete routing plan generated
    AWAITING_APPROVAL = "awaiting_approval"     # User reviewing cleanup + routing
    READY_TO_EXECUTE = "ready_to_execute"       # All blocks resolved + plan approved
    EXECUTING = "executing"                     # Writing blocks to library
    VERIFYING = "verifying"                     # Post-execution checksum verification
    COMPLETED = "completed"                     # All blocks written and verified
    ERROR = "error"                             # Something went wrong


class ExtractionSession(BaseModel):
    """
    Complete session state for extracting a source document into the library.
    Designed to be serializable and resumable.
    """

    id: str
    created_at: datetime
    updated_at: datetime
    phase: SessionPhase

    # Source document
    source: Optional[SourceDocument] = None

    # Library context
    library_path: str
    library_manifest: Optional[dict] = None      # Snapshot used to constrain routing (model later)

    # Content mode (STRICT or REFINEMENT)
    content_mode: ContentMode = ContentMode.STRICT

    # AI-proposed plans (explicitly user-approved)
    cleanup_plan: Optional[CleanupPlan] = None
    routing_plan: Optional[RoutingPlan] = None

    # Conversation state
    pending_questions: list[dict] = Field(default_factory=list)
    conversation_history: list[dict] = Field(default_factory=list)

    # Execution tracking
    execution_log: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    # Completion
    source_deleted: bool = False

    @property
    def can_execute(self) -> bool:
        """
        Can execute only when:
        - source is parsed into blocks,
        - cleanup decisions are complete (every block kept or explicitly discarded),
        - routing decisions are complete (every kept block has a selected destination),
        - routing plan is approved.
        """
        if not self.source or not self.routing_plan:
            return False
        if not self.routing_plan.approved:
            return False
        return self.routing_plan.all_blocks_resolved
