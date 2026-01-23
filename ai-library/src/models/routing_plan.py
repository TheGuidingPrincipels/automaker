# src/models/routing_plan.py

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class BlockDestination(BaseModel):
    """One destination option for a single block (top-3 UI choices)."""
    destination_file: str                  # e.g., "library/tech/auth.md"
    destination_section: Optional[str] = None
    action: str                            # "create_file" | "create_section" | "append" | "insert_before" | "insert_after" | ("merge" in refinement)
    confidence: float                      # 0.0 to 1.0
    reasoning: str

    # For creation actions
    proposed_file_title: Optional[str] = None
    proposed_section_title: Optional[str] = None


class BlockRoutingItem(BaseModel):
    """Routing options + user selection for one kept block."""
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str                   # First 200 chars

    # Model output (always 3 options unless library empty)
    options: List[BlockDestination] = Field(default_factory=list)  # length 3

    # User decision (click selection; no typing required)
    selected_option_index: Optional[int] = None  # 0..2
    custom_destination_file: Optional[str] = None
    custom_destination_section: Optional[str] = None
    custom_action: Optional[str] = None

    status: str = "pending"                # "pending" | "selected" | "rejected"


class MergePreview(BaseModel):
    """Preview of a merge operation."""
    merge_id: str
    block_id: str
    existing_content: str
    existing_location: str
    new_content: str
    proposed_merge: str
    merge_reasoning: str


class PlanSummary(BaseModel):
    """Quick summary of the routing plan."""
    total_blocks: int
    blocks_to_new_files: int
    blocks_to_existing_files: int
    blocks_requiring_merge: int
    estimated_actions: int


class RoutingPlan(BaseModel):
    """Complete routing plan for user approval."""
    session_id: str
    source_file: str
    content_mode: str = "strict"      # "strict" or "refinement"
    created_at: datetime = Field(default_factory=datetime.now)

    # The complete plan
    blocks: List[BlockRoutingItem] = Field(default_factory=list)
    merge_previews: List[MergePreview] = Field(default_factory=list)  # refinement-only

    # Summary for quick review
    summary: Optional[PlanSummary] = None

    # Approval
    approved: bool = False
    approved_at: Optional[datetime] = None

    @property
    def all_blocks_resolved(self) -> bool:
        """All kept blocks must have a selected (or custom) destination."""
        return all(
            (b.status == "selected")
            and (b.selected_option_index is not None or b.custom_destination_file is not None)
            for b in self.blocks
        )

    @property
    def pending_count(self) -> int:
        return sum(1 for b in self.blocks if b.status == "pending")

    @property
    def accepted_count(self) -> int:
        return sum(1 for b in self.blocks if b.status == "selected")
