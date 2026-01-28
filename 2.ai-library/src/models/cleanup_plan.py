# src/models/cleanup_plan.py

from enum import Enum
from datetime import datetime
import logging
from typing import Any, Optional, List
from pydantic import BaseModel, Field, field_validator

from ..utils.validation import normalize_confidence


logger = logging.getLogger(__name__)


class CleanupDisposition(str, Enum):
    KEEP = "keep"
    DISCARD = "discard"   # Only allowed with explicit user approval


class DetectedSignal(BaseModel):
    """A signal detected in the content that influences the keep/discard decision.

    Signals are specific patterns that the AI identifies when analyzing content,
    such as time-sensitive markers, explicit deletion instructions, or indicators
    of permanent reference value.

    Examples:
        - type="date_reference", detail="Contains date '2023-01-15' suggesting time-bound context"
        - type="explicit_marker", detail="Found 'TODO: delete' indicating temporary content"
        - type="original_work", detail="Contains original analysis that appears valuable"
    """
    type: str
    detail: str


class CleanupItem(BaseModel):
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str

    # Model suggestion (never executed automatically)
    suggested_disposition: str = CleanupDisposition.KEEP
    suggestion_reason: str = ""
    confidence: float = Field(
        default=0.5, description="AI confidence in the suggestion (0.0 to 1.0)"
    )

    # User decision
    final_disposition: Optional[str] = None  # "keep" or "discard"

    # AI analysis tracking - helps diagnose AI omissions vs explicit analysis
    ai_analyzed: bool = Field(
        default=False,
        description="True if AI provided analysis for this block, False if using defaults",
    )
    content_truncated: bool = Field(
        default=False,
        description="True if content was truncated before sending to AI",
    )
    original_content_length: int = Field(
        default=0,
        description="Original content length in characters",
    )

    # Duplicate detection - helps identify similar content across blocks
    similar_block_ids: List[str] = Field(
        default_factory=list,
        description="Block IDs with similar content (similarity >= threshold)",
    )
    similarity_score: Optional[float] = Field(
        default=None,
        description="Highest similarity score with another block (0.0-1.0)",
    )

    # Signal detection - specific patterns detected that influence the recommendation
    signals_detected: List[DetectedSignal] = Field(
        default_factory=list,
        description="Signals detected in content (e.g., date_reference, explicit_marker, original_work)",
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence_validator(cls, v: Any) -> float:
        """Normalize and clamp confidence value to valid range [0.0, 1.0]."""
        return normalize_confidence(v, log=logger)


class CleanupPlan(BaseModel):
    session_id: str
    source_file: str
    created_at: datetime = Field(default_factory=datetime.now)

    items: List[CleanupItem] = Field(default_factory=list)

    approved: bool = False
    approved_at: Optional[datetime] = None

    # Generation status tracking - helps diagnose AI failures
    ai_generated: bool = Field(
        default=True,
        description="True if suggestions came from AI, False if using defaults due to error",
    )
    generation_error: Optional[str] = Field(
        default=None,
        description="Error message if AI generation failed (e.g., missing OAuth token)",
    )

    # Duplicate detection summary - groups of blocks with similar content
    duplicate_groups: List[List[str]] = Field(
        default_factory=list,
        description="Groups of block IDs that appear to be duplicates or near-duplicates",
    )

    # Cleanup mode used for generation
    cleanup_mode: str = Field(
        default="balanced",
        description="Cleanup aggressiveness mode: conservative, balanced, or aggressive",
    )

    # Overall notes from AI about the cleanup analysis
    overall_notes: str = Field(
        default="",
        description="Overall notes from AI about the cleanup analysis (e.g., summary of document content)",
    )

    @property
    def all_decided(self) -> bool:
        return all(i.final_disposition in (CleanupDisposition.KEEP, CleanupDisposition.DISCARD) for i in self.items)
