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

    @property
    def all_decided(self) -> bool:
        return all(i.final_disposition in (CleanupDisposition.KEEP, CleanupDisposition.DISCARD) for i in self.items)
