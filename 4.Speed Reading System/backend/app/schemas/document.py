"""Pydantic schemas for document-related API endpoints."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    """Base schema with ORM attribute support."""

    model_config = ConfigDict(from_attributes=True)


class SourceType(str, Enum):
    PASTE = "paste"
    MARKDOWN = "md"
    PDF = "pdf"


class Language(str, Enum):
    ENGLISH = "en"
    GERMAN = "de"


class DocumentFromTextRequest(BaseModel):
    title: str | None = Field(None, max_length=500)
    language: Language
    source_type: SourceType = SourceType.PASTE
    original_filename: str | None = Field(None, max_length=255)
    text: str = Field(..., min_length=1)


class DocumentFromFileRequest(BaseModel):
    language: Language


class DocumentMeta(SchemaBase):
    id: UUID
    title: str
    source_type: SourceType
    language: Language
    total_words: int
    tokenizer_version: str
    created_at: datetime
    updated_at: datetime


class DocumentPreviewAnchor(BaseModel):
    word_index: int
    type: str
    preview: str


class DocumentPreview(SchemaBase):
    id: UUID
    title: str
    preview_text: str
    total_words: int
    anchors: list[DocumentPreviewAnchor] = Field(default_factory=list)
