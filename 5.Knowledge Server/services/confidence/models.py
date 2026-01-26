"""
Pydantic data models for confidence scoring system.

Provides type-safe data structures with validation for concept data,
relationships, review history, and error handling.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator

from tools.responses import ErrorType


class ConceptData(BaseModel):
    """Complete concept data for confidence calculation"""

    id: str = Field(..., min_length=1, max_length=255)
    name: str
    explanation: str
    created_at: datetime
    last_reviewed_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    area: str | None = None
    topic: str | None = None
    subtopic: str | None = None

    @field_validator("explanation")
    @classmethod
    def explanation_not_empty(cls, value: str) -> str:
        if not value or value.strip() == "":
            raise ValueError("Explanation cannot be empty")
        return value


class RelationshipData(BaseModel):
    """Relationship metrics for understanding score"""

    total_relationships: int = Field(..., ge=0)
    relationship_types: dict[str, int]
    connected_concept_ids: list[str]

    @property
    def unique_connections(self) -> int:
        return len(set(self.connected_concept_ids))


class ReviewData(BaseModel):
    """Review history for retention score"""

    last_reviewed_at: datetime
    days_since_review: int = Field(..., ge=0)
    review_count: int = Field(default=0, ge=0)


class CompletenessReport(BaseModel):
    """Data completeness metrics"""

    has_explanation: bool
    has_tags: bool
    has_examples: bool
    has_relationships: bool
    metadata_score: float = Field(..., ge=0.0, le=1.0)


# Error handling types
# Note: ErrorCode has been replaced by ErrorType from tools/responses.py
# Kept for backwards compatibility during transition
ErrorCode = ErrorType  # Alias for backwards compatibility


@dataclass
class Error:
    """Error result containing error details"""

    message: str
    code: ErrorType  # Changed from ErrorCode to ErrorType
    details: Optional[dict] = None


@dataclass
class Success:
    """Success result containing value"""

    value: Any


# Type alias for Result pattern
Result = Union[Success, Error]
