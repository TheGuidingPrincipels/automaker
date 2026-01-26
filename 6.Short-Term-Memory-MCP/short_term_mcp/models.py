"""Pydantic data models for Short-Term Memory MCP Server"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ConceptStatus(str, Enum):
    """Valid concept statuses"""

    IDENTIFIED = "identified"
    CHUNKED = "chunked"
    ENCODED = "encoded"
    EVALUATED = "evaluated"
    STORED = "stored"


class SessionStatus(str, Enum):
    """Valid session statuses"""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Stage(str, Enum):
    """Valid pipeline stages"""

    RESEARCH = "research"
    AIM = "aim"
    SHOOT = "shoot"
    SKIN = "skin"


class UserQuestion(BaseModel):
    """User's question about a concept"""

    question: str
    asked_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    session_stage: str
    answered: bool = False
    answer: Optional[str] = None


class Session(BaseModel):
    """Daily learning session"""

    session_id: str
    date: str
    learning_goal: Optional[str] = None
    building_goal: Optional[str] = None
    status: SessionStatus = SessionStatus.IN_PROGRESS
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Concept(BaseModel):
    """Individual concept being tracked"""

    concept_id: str
    session_id: str
    concept_name: str
    current_status: ConceptStatus = ConceptStatus.IDENTIFIED

    # Timestamps
    identified_at: Optional[str] = None
    chunked_at: Optional[str] = None
    encoded_at: Optional[str] = None
    evaluated_at: Optional[str] = None
    stored_at: Optional[str] = None

    # Links
    knowledge_mcp_id: Optional[str] = None

    # Data
    current_data: Optional[Dict[str, Any]] = None
    user_questions: Optional[List[UserQuestion]] = None

    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConceptStageData(BaseModel):
    """Stage-specific data for a concept"""

    id: Optional[int] = None
    concept_id: str
    stage: Stage
    data: Dict[str, Any]
    created_at: Optional[str] = None


class SourceURL(BaseModel):
    """Metadata about a source URL used during research."""

    url: HttpUrl
    title: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    domain_category: Optional[str] = Field(None, pattern=r"^(official|in_depth|authoritative)$")


class ResearchCacheEntry(BaseModel):
    """Temporary research cache entry persisted in SQLite."""

    id: Optional[int] = None
    concept_name: str = Field(..., min_length=1, max_length=500)
    explanation: str = Field(..., min_length=1)
    source_urls: Optional[List[SourceURL]] = None
    last_researched_at: datetime
    created_at: datetime
    updated_at: datetime


class DomainWhitelist(BaseModel):
    """Trusted domain metadata powering source quality scoring."""

    id: Optional[int] = None
    domain: str = Field(..., pattern=r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    category: str = Field(..., pattern=r"^(official|in_depth|authoritative|community)$")
    quality_score: float = Field(..., ge=0.0, le=1.0)
    added_at: datetime
    added_by: str = Field(default="system")
