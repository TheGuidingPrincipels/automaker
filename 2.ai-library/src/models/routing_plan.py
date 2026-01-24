# src/models/routing_plan.py

from typing import Optional, List
from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator

# Overview length constraints (shared across routing_plan and scanner)
OVERVIEW_MIN_LENGTH = 50
OVERVIEW_MAX_LENGTH = 250


def normalize_overview_text(overview: str) -> str:
    """Normalize overview text for length validation."""
    return re.sub(r"\s+", " ", overview).strip()


def validate_overview_text(overview: Optional[str]) -> Optional[str]:
    """Validate overview length (50-250 chars, normalized)."""
    if overview is None:
        return None
    normalized = normalize_overview_text(overview)
    if len(normalized) < OVERVIEW_MIN_LENGTH or len(normalized) > OVERVIEW_MAX_LENGTH:
        raise ValueError(
            f"proposed_file_overview must be {OVERVIEW_MIN_LENGTH}-{OVERVIEW_MAX_LENGTH} characters (got {len(normalized)})"
        )
    return normalized


class BlockDestination(BaseModel):
    """One destination option for a single block (top-3 UI choices)."""
    destination_file: str                  # e.g., "library/tech/auth.md"
    destination_section: Optional[str] = None
    action: str                            # "create_file" | "create_section" | "append" | "insert_before" | "insert_after" | ("merge" in refinement)
    confidence: float                      # 0.0 to 1.0
    reasoning: str

    # For creation actions
    proposed_file_title: Optional[str] = None
    proposed_file_overview: Optional[str] = None
    proposed_section_title: Optional[str] = None

    @field_validator("proposed_file_overview")
    @classmethod
    def validate_proposed_file_overview(cls, value: Optional[str]) -> Optional[str]:
        return validate_overview_text(value)


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
    custom_proposed_file_title: Optional[str] = None
    custom_proposed_file_overview: Optional[str] = None

    status: str = "pending"                # "pending" | "selected" | "rejected"

    @field_validator("custom_proposed_file_overview")
    @classmethod
    def validate_custom_file_overview(cls, value: Optional[str]) -> Optional[str]:
        return validate_overview_text(value)


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
