"""Pydantic schemas for session-related API endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    """Base schema with ORM attribute support."""

    model_config = ConfigDict(from_attributes=True)


class SessionCreateRequest(BaseModel):
    document_id: UUID
    start_word_index: int = 0
    target_wpm: int = Field(300, ge=100, le=1500)
    ramp_enabled: bool = True
    ramp_seconds: int = Field(30, ge=0, le=60)


class SessionProgressUpdate(BaseModel):
    current_word_index: int
    last_known_percent: float = Field(..., ge=0.0, le=100.0)
    target_wpm: int | None = None
    ramp_enabled: bool | None = None


class ResolveStartRequest(BaseModel):
    approx_word_index: int
    prefer: str = "sentence"
    direction: str = "backward"
    window: int = 50


class SessionResponse(SchemaBase):
    id: UUID
    document_id: UUID
    target_wpm: int
    ramp_enabled: bool
    ramp_seconds: int
    ramp_start_wpm: int | None
    current_word_index: int
    last_known_percent: float
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class SessionListItem(SchemaBase):
    id: UUID
    document_id: UUID
    document_title: str
    last_known_percent: float
    updated_at: datetime
    expires_at: datetime


class ResolveStartResponse(BaseModel):
    resolved_word_index: int
    reason: str
