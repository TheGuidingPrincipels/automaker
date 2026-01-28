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

    @property
    def all_decided(self) -> bool:
        return all(i.final_disposition in (CleanupDisposition.KEEP, CleanupDisposition.DISCARD) for i in self.items)
