# Session 1: Foundation & Schema

## Overview

**Duration**: ~3-4 hours
**Goal**: Establish project foundation with monorepo structure, FastAPI backend skeleton, database schema, and local development environment.

**Deliverable**: A running FastAPI server with health endpoint, database migrations, and a SQLite-backed local dev setup (Postgres is optional later).

---

## Prerequisites

- Python 3.11+ installed
- Node.js 22+ installed (for Automaker integration)
- Docker & Docker Compose installed
- Git initialized

---

## Objectives & Acceptance Criteria

| #   | Objective         | Acceptance Criteria                                                                                                                            |
| --- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Backend structure | `backend/` directory with FastAPI app + migrations + tests                                                                                     |
| 2   | FastAPI skeleton  | Server starts; `GET /api/health` returns `200` with `{status, database, version}` (status is `"ok"` when DB reachable, otherwise `"degraded"`) |
| 3   | Database schema   | All tables created via Alembic migration                                                                                                       |
| 4   | Pydantic models   | DTOs defined for all API contracts                                                                                                             |
| 5   | Docker Compose    | `docker-compose up` starts backend (SQLite)                                                                                                    |
| 6   | Multi-user ready  | `user_id` columns present (nullable for v1)                                                                                                    |

---

## Project Structure

```
Speed Reading/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Settings via pydantic-settings
│   │   ├── database.py             # SQLAlchemy engine & session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── document.py         # Document model
│   │   │   ├── token.py            # Token model
│   │   │   └── session.py          # ReadingSession model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── document.py         # Document DTOs
│   │   │   ├── token.py            # Token DTOs
│   │   │   └── session.py          # Session DTOs
│   │   └── api/
│   │       ├── __init__.py
│   │       └── health.py           # Health endpoint
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── requirements.txt            # Optional (avoid drift; prefer pyproject as source-of-truth)
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml          # Placeholder
├── .env.example
├── .gitignore
└── README.md
```

---

## Implementation Details

### 0. Initial Setup (Execution Start)

> **Context**: The `4.Speed Reading System/backend/` directory does not exist yet. You must create it.

```bash
# Create correct folder structure
mkdir -p "4.Speed Reading System/backend/app/models"
mkdir -p "4.Speed Reading System/backend/app/schemas"
mkdir -p "4.Speed Reading System/backend/app/services"
mkdir -p "4.Speed Reading System/backend/app/api"
mkdir -p "4.Speed Reading System/backend/tests"
mkdir -p "4.Speed Reading System/backend/data"

cd "4.Speed Reading System/backend"
```

### 1. Backend Package Setup (`pyproject.toml`)

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "deepread-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.0",
]
```

### 2. Configuration (`app/config.py`)

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./data/deepread.db"

    # App
    app_name: str = "DeepRead"
    debug: bool = False

    # Limits
    max_document_words: int = 20_000
    chunk_size: int = 500  # tokens per chunk
    session_expiry_days: int = 7

    # Future auth hook
    auth_enabled: bool = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 3. Database Models

#### `models/document.py`

```python
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import uuid
import enum

from app.database import Base

class SourceType(str, enum.Enum):
    PASTE = "paste"
    MARKDOWN = "md"
    PDF = "pdf"

class Language(str, enum.Enum):
    ENGLISH = "en"
    GERMAN = "de"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True, index=True)  # Multi-user ready

    title = Column(String(500), nullable=False)
    source_type = Column(SAEnum(SourceType), nullable=False)
    language = Column(SAEnum(Language), nullable=False)
    original_filename = Column(String(255), nullable=True)

    normalized_text = Column(Text, nullable=False)
    total_words = Column(Integer, nullable=False)
    tokenizer_version = Column(String(50), nullable=False, default="1.0.0")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    tokens = relationship("Token", back_populates="document", cascade="all, delete-orphan")
    sessions = relationship("ReadingSession", back_populates="document", cascade="all, delete-orphan")
```

#### `models/token.py`

```python
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base

class BreakType(str, enum.Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"

class Token(Base):
    __tablename__ = "tokens"

    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    word_index = Column(Integer, primary_key=True)

    display_text = Column(String(500), nullable=False)  # With punctuation
    clean_text = Column(String(500), nullable=False)    # For ORP calc
    orp_index_display = Column(Integer, nullable=False) # ORP position in display_text

    delay_multiplier_after = Column(Float, nullable=False, default=1.0)
    break_before = Column(SAEnum(BreakType), nullable=True)

    is_sentence_start = Column(Boolean, nullable=False, default=False)
    is_paragraph_start = Column(Boolean, nullable=False, default=False)

    char_offset_start = Column(Integer, nullable=True)
    char_offset_end = Column(Integer, nullable=True)

    # Relationship
    document = relationship("Document", back_populates="tokens")
```

#### `models/session.py`

```python
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, UTC
import uuid

from app.database import Base
from app.config import get_settings

class ReadingSession(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)  # Multi-user ready

    # WPM settings
    target_wpm = Column(Integer, nullable=False, default=300)
    ramp_enabled = Column(Boolean, nullable=False, default=True)
    ramp_seconds = Column(Integer, nullable=False, default=30)
    ramp_start_wpm = Column(Integer, nullable=True)  # Calculated if null

    # Progress
    current_word_index = Column(Integer, nullable=False, default=0)
    last_known_percent = Column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC) + timedelta(days=get_settings().session_expiry_days))

    # Relationship
    document = relationship("Document", back_populates="sessions")
```

### 4. Pydantic Schemas (DTOs)

#### `schemas/document.py`

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID
from enum import Enum

class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class SourceType(str, Enum):
    PASTE = "paste"
    MARKDOWN = "md"
    PDF = "pdf"

class Language(str, Enum):
    ENGLISH = "en"
    GERMAN = "de"

# Request schemas
class DocumentFromTextRequest(BaseModel):
    title: str | None = Field(None, max_length=500)
    language: Language
    source_type: SourceType = SourceType.PASTE
    original_filename: str | None = Field(None, max_length=255)
    text: str = Field(..., min_length=1)

class DocumentFromFileRequest(BaseModel):
    language: Language

# Response schemas
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
    # Anchors for navigation (paragraph starts, heading starts)
    anchors: list[DocumentPreviewAnchor] = Field(default_factory=list)
```

#### `schemas/token.py`

```python
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from enum import Enum

class SchemaBase(BaseModel):
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
```

#### `schemas/session.py`

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID

class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# Request schemas
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
    prefer: str = "sentence"  # sentence | paragraph | heading
    direction: str = "backward"  # backward | forward | nearest
    window: int = 50  # Search window size

# Response schemas
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
    reason: str  # "sentence_start" | "paragraph_start" | "heading_start" | "exact"
```

### 5. Database Setup (`app/database.py`)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 6. FastAPI Main App (`app/main.py`)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import health

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start background tasks, warm caches
    yield
    # Shutdown: cleanup
    pass

app = FastAPI(
    title=settings.app_name,
    description="RSVP Speed-Reading Application",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix="/api", tags=["health"])
```

### 7. Health Endpoint (`app/api/health.py`)

```python
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Verify database connection
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        logger.exception("Health check DB query failed")
        db_connected = False

    return {
        "status": "ok" if db_connected else "degraded",
        "database": "connected" if db_connected else "unavailable",
        "version": "0.1.0",
    }
```

### 8. Docker Compose (`docker-compose.yml`)

```yaml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: deepread-backend
    ports:
      - '8001:8001'
    environment:
      DATABASE_URL: sqlite:////app/data/deepread.db
      DEBUG: 'true'
    volumes:
      - ./backend:/app
      - ./backend/data:/app/data
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 9. Backend Dockerfile (`backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Install Python dependencies (from pyproject.toml)
RUN pip install --no-cache-dir .

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 10. Environment Example (`.env.example`)

```env
# Database
DATABASE_URL=sqlite:///./data/deepread.db

# App
DEBUG=true
APP_NAME=DeepRead

# Limits
MAX_DOCUMENT_WORDS=20000
CHUNK_SIZE=500
SESSION_EXPIRY_DAYS=7

# Future auth
AUTH_ENABLED=false
```

> Tip: for non-Docker local runs, copy `.env.example` to `backend/.env` (the settings loader reads `.env` relative to the backend working directory). When running via Docker Compose, the `environment:` values in `docker-compose.yml` take precedence.

---

## Alembic Setup Commands

```bash
cd backend

# Initialize Alembic
alembic init alembic

# Edit alembic/env.py to import models and use config
# Then create initial migration
alembic revision --autogenerate -m "initial_schema"

# Apply migration
alembic upgrade head
```

### Alembic `env.py` Modifications

```python
# Add to alembic/env.py
from app.config import get_settings
from app.database import Base
from app.models import document, token, session  # Import all models

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

---

## Testing Requirements

### Test: Health Endpoint

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "database" in data
    assert "version" in data
```

### Test: Models Import

```python
# backend/tests/test_models.py
def test_models_import():
    from app.models.document import Document, SourceType, Language
    from app.models.token import Token, BreakType
    from app.models.session import ReadingSession

    assert Document.__tablename__ == "documents"
    assert Token.__tablename__ == "tokens"
    assert ReadingSession.__tablename__ == "sessions"
```

---

## Verification Checklist

- [ ] `docker-compose up` starts backend (SQLite)
- [ ] `GET /api/health` returns `{"status": "ok", "database": "connected", ...}` (or `"degraded"`/`"unavailable"` if DB is down)
- [ ] Alembic migration creates all 3 tables
- [ ] Tables have correct columns including nullable `user_id`
- [ ] All Pydantic schemas validate correctly
- [ ] pytest passes for health and model tests

---

## Context for Next Session

**What exists after Session 1:**

- Running FastAPI server at `http://localhost:8001`
- SQLite database with `documents`, `tokens`, `sessions` tables
- All Pydantic DTOs defined for the full API contract
- Docker Compose for local development

**Session 2 will need:**

- The database models (for storing tokenized output)
- The Pydantic schemas (for defining tokenizer output format)
- The `Language` enum (for language-aware tokenization)
