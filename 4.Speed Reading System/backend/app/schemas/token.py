"""Pydantic schemas for token-related API endpoints."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import BreakType


class SchemaBase(BaseModel):
    """Base schema with ORM attribute support."""

    model_config = ConfigDict(from_attributes=True)


class TokenDTO(SchemaBase):
    word_index: int
    display_text: str
    orp_index_display: int
    delay_multiplier_after: float
    break_before: BreakType | None
    is_sentence_start: bool
    is_paragraph_start: bool


class TokenChunkResponse(BaseModel):
    document_id: UUID
    total_words: int
    range_start: int
    range_end: int
    tokens: list[TokenDTO]
