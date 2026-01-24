"""Pydantic schemas for Speed Reading System API."""

from app.schemas.document import (
    DocumentFromFileRequest,
    DocumentFromTextRequest,
    DocumentMeta,
    DocumentPreview,
    DocumentPreviewAnchor,
    Language,
    SourceType,
)
from app.schemas.session import (
    ResolveStartRequest,
    ResolveStartResponse,
    SessionCreateRequest,
    SessionListItem,
    SessionProgressUpdate,
    SessionResponse,
)
from app.schemas.token import BreakType, TokenChunkResponse, TokenDTO

__all__ = [
    # Enums
    "SourceType",
    "Language",
    "BreakType",
    # Document schemas
    "DocumentFromTextRequest",
    "DocumentFromFileRequest",
    "DocumentMeta",
    "DocumentPreviewAnchor",
    "DocumentPreview",
    # Token schemas
    "TokenDTO",
    "TokenChunkResponse",
    # Session schemas
    "SessionCreateRequest",
    "SessionProgressUpdate",
    "ResolveStartRequest",
    "ResolveStartResponse",
    "SessionResponse",
    "SessionListItem",
]
