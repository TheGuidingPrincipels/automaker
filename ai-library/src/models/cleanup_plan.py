# src/models/cleanup_plan.py

from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


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

    # User decision
    final_disposition: Optional[str] = None  # "keep" or "discard"


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
