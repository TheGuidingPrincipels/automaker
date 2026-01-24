"""Pydantic schemas for token-related API endpoints."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    """Base schema with ORM attribute support."""

    model_config = ConfigDict(from_attributes=True)


class BreakType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"


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
