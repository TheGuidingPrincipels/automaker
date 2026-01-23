# Session 4: Sessions & Navigation API

## Overview

**Duration**: ~2-3 hours
**Goal**: Implement reading session management, the resolve-start endpoint for snapping to sentence/paragraph boundaries, and automatic session expiry.

**Deliverable**: Complete backend API with session CRUD, progress tracking, and navigation resolution.

---

## Prerequisites

- Session 1 completed (database models including ReadingSession)
- Session 3 completed (document and token endpoints)

---

## Objectives & Acceptance Criteria

| #   | Objective                          | Acceptance Criteria                                                                        |
| --- | ---------------------------------- | ------------------------------------------------------------------------------------------ |
| 1   | POST /sessions                     | Creates new reading session                                                                |
| 2   | GET /sessions/recent               | Lists sessions **created** in last N days (default: 7), newest-first (`created_at DESC`)   |
| 3   | PATCH /sessions/{id}/progress      | Updates reading progress (does **not** extend the 7-day retention window)                  |
| 4   | POST /documents/{id}/resolve-start | Returns nearest sentence/paragraph start                                                   |
| 5   | Session expiry                     | Sessions expire exactly 7 days after creation; background cleanup removes expired sessions |
| 6   | OpenAPI documentation              | All endpoints documented with examples                                                     |

### Definitions (Confirmed)

- **Recent sessions**: sessions created in the last N days (`created_at`), sorted newest-first.
- **Retention**: fixed window from `created_at` (progress updates do **not** extend `expires_at`).
- **Ramp start**: `ramp_start_wpm = 50% of target_wpm` (example: 600 → start 300).
- **Ramp duration**: user-selectable intro duration (v1 UX: 30s or 60s via `ramp_seconds`).

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── session_service.py      # Session CRUD and progress
│   │   └── navigation_service.py   # Resolve-start logic
│   ├── api/
│   │   ├── sessions.py             # Session endpoints
│   │   └── documents.py            # Add resolve-start endpoint
│   └── tasks/
│       ├── __init__.py
│       └── cleanup.py              # Session expiry cleanup
└── tests/
    ├── api/
    │   └── test_sessions.py
    └── services/
        └── test_navigation.py
```

---

## Implementation Details

### 1. Navigation Service (`services/navigation_service.py`)

```python
"""
Navigation service for resolving start positions.

When a user scrubs to a position or clicks a word, we often want to
snap to the nearest sentence or paragraph start for a clean reading
experience.
"""

from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.token import Token, BreakType
from app.schemas.session import ResolveStartResponse

class NavigationService:
    def __init__(self, db: Session):
        self.db = db

    def resolve_start_position(
        self,
        document_id: UUID,
        approx_index: int,
        prefer: str = "sentence",
        direction: str = "backward",
        window: int = 50,
    ) -> ResolveStartResponse:
        """
        Find the best starting position near the given index.

        Args:
            document_id: Document to search in
            approx_index: Approximate word index to start from
            prefer: What boundary to prefer ("sentence", "paragraph", "heading")
            direction: Search direction ("backward", "forward", "nearest")
            window: How many words to search in each direction

        Returns:
            ResolveStartResponse with resolved index and reason
        """
        # Define search range based on direction
        if direction == "backward":
            range_start = max(0, approx_index - window)
            range_end = approx_index + 1
        elif direction == "forward":
            range_start = approx_index
            range_end = approx_index + window + 1
        else:  # nearest
            range_start = max(0, approx_index - window)
            range_end = approx_index + window + 1

        # Query tokens in range (SQLAlchemy 2.0 style)
        tokens = self.db.execute(
            select(Token)
            .where(
                Token.document_id == document_id,
                Token.word_index >= range_start,
                Token.word_index < range_end,
            )
            .order_by(Token.word_index)
        ).scalars().all()

        if not tokens:
            # No tokens found, return exact position
            return ResolveStartResponse(
                resolved_word_index=approx_index,
                reason="exact"
            )

        # Find candidates based on preference
        candidates = self._find_candidates(tokens, approx_index, prefer)

        if not candidates:
            # No suitable boundary found, return exact
            return ResolveStartResponse(
                resolved_word_index=approx_index,
                reason="exact"
            )

        # Select best candidate based on direction
        best = self._select_best_candidate(
            candidates, approx_index, direction
        )

        return ResolveStartResponse(
            resolved_word_index=best["index"],
            reason=best["reason"]
        )

    def _find_candidates(
        self,
        tokens: list[Token],
        approx_index: int,
        prefer: str,
    ) -> list[dict]:
        """
        Find all candidate start positions in the token list.
        """
        candidates = []

        for token in tokens:
            # Heading starts (highest priority)
            if token.break_before == BreakType.HEADING:
                candidates.append({
                    "index": token.word_index,
                    "reason": "heading_start",
                    "priority": 3,
                })

            # Paragraph starts
            if token.is_paragraph_start and token.break_before != BreakType.HEADING:
                candidates.append({
                    "index": token.word_index,
                    "reason": "paragraph_start",
                    "priority": 2,
                })

            # Sentence starts
            if token.is_sentence_start and not token.is_paragraph_start:
                candidates.append({
                    "index": token.word_index,
                    "reason": "sentence_start",
                    "priority": 1,
                })

        # Filter by preference if specified
        if prefer == "heading":
            heading_candidates = [c for c in candidates if c["priority"] == 3]
            if heading_candidates:
                return heading_candidates
        elif prefer == "paragraph":
            para_candidates = [c for c in candidates if c["priority"] >= 2]
            if para_candidates:
                return para_candidates
        # For "sentence" or fallback, return all candidates

        return candidates

    def _select_best_candidate(
        self,
        candidates: list[dict],
        approx_index: int,
        direction: str,
    ) -> dict:
        """
        Select the best candidate based on direction and proximity.
        """
        if direction == "backward":
            # Find closest candidate at or before approx_index
            valid = [c for c in candidates if c["index"] <= approx_index]
            if valid:
                # Return the one closest to approx_index (highest index)
                return max(valid, key=lambda c: c["index"])

        elif direction == "forward":
            # Find closest candidate at or after approx_index
            valid = [c for c in candidates if c["index"] >= approx_index]
            if valid:
                # Return the one closest to approx_index (lowest index)
                return min(valid, key=lambda c: c["index"])

        else:  # nearest
            # Find closest candidate in either direction
            return min(candidates, key=lambda c: abs(c["index"] - approx_index))

        # Fallback to any candidate
        return min(candidates, key=lambda c: abs(c["index"] - approx_index))
```

### 2. Session Service (`services/session_service.py`)

```python
"""
Session service for managing reading sessions and progress.
"""

from uuid import UUID, uuid4
from datetime import datetime, timedelta, UTC
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.session import ReadingSession
from app.models.document import Document
from app.schemas.session import (
    SessionCreateRequest,
    SessionListItem,
    SessionProgressUpdate,
)
from app.config import get_settings

settings = get_settings()

class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        request: SessionCreateRequest,
        user_id: UUID | None = None,
    ) -> ReadingSession:
        """
        Create a new reading session for a document.
        """
        now = datetime.now(UTC)

        # Verify document exists
        document = self.db.execute(
            select(Document).where(Document.id == request.document_id)
        ).scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Validate start index
        if request.start_word_index < 0 or request.start_word_index >= document.total_words:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start index. Must be between 0 and {document.total_words - 1}"
            )

        # Ramp start is exactly 50% of the target WPM (e.g., 600 -> 300).
        ramp_start = None
        if request.ramp_enabled:
            ramp_start = int(request.target_wpm * 0.5)

        # Calculate initial percentage
        initial_percent = (request.start_word_index / document.total_words) * 100

        session = ReadingSession(
            id=uuid4(),
            document_id=request.document_id,
            user_id=user_id,
            target_wpm=request.target_wpm,
            ramp_enabled=request.ramp_enabled,
            ramp_seconds=request.ramp_seconds,
            ramp_start_wpm=ramp_start,
            current_word_index=request.start_word_index,
            last_known_percent=initial_percent,
            created_at=now,
            # Fixed retention window from creation (do not extend on updates).
            expires_at=now + timedelta(days=settings.session_expiry_days),
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def get_session(self, session_id: UUID) -> ReadingSession:
        """
        Get a session by ID.
        """
        now = datetime.now(UTC)
        session = self.db.execute(
            select(ReadingSession).where(
                ReadingSession.id == session_id,
                ReadingSession.expires_at > now,
            )
        ).scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        return session

    def get_recent_sessions(
        self,
        user_id: UUID | None = None,
        days: int = 7,
    ) -> list[SessionListItem]:
        """
        Get recent sessions with document info.
        """
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=days)

        stmt = (
            select(ReadingSession)
            .options(joinedload(ReadingSession.document))
            .where(
                ReadingSession.created_at >= cutoff,
                ReadingSession.expires_at > now,
            )
            .order_by(ReadingSession.created_at.desc())
        )

        if user_id is not None:
            stmt = stmt.where(ReadingSession.user_id == user_id)

        sessions = self.db.execute(stmt).scalars().all()

        return [
            SessionListItem(
                id=s.id,
                document_id=s.document_id,
                document_title=s.document.title,
                last_known_percent=s.last_known_percent,
                updated_at=s.updated_at,
                expires_at=s.expires_at,
            )
            for s in sessions
        ]

    def get_latest_session_for_document(
        self,
        document_id: UUID,
        user_id: UUID | None = None,
    ) -> ReadingSession | None:
        """
        Get the most recent session for a document.
        Used for "Continue Reading" functionality.
        """
        now = datetime.now(UTC)
        stmt = (
            select(ReadingSession)
            .where(
                ReadingSession.document_id == document_id,
                ReadingSession.expires_at > now,
            )
            .order_by(ReadingSession.updated_at.desc())
        )

        if user_id is not None:
            stmt = stmt.where(ReadingSession.user_id == user_id)

        return self.db.execute(stmt).scalars().first()

    def update_progress(
        self,
        session_id: UUID,
        update: SessionProgressUpdate,
    ) -> ReadingSession:
        """
        Update session progress.
        Called periodically during playback and on pause.
        """
        now = datetime.now(UTC)
        session = self.db.execute(
            select(ReadingSession)
            .options(joinedload(ReadingSession.document))
            .where(
                ReadingSession.id == session_id,
                ReadingSession.expires_at > now,
            )
        ).scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # Validate current index against document bounds
        if update.current_word_index < 0 or update.current_word_index >= session.document.total_words:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid current_word_index. Must be between 0 and {session.document.total_words - 1}"
            )

        # Update progress
        session.current_word_index = update.current_word_index
        session.last_known_percent = update.last_known_percent

        # Optionally update settings if provided
        if update.target_wpm is not None:
            session.target_wpm = update.target_wpm
            # Recalculate ramp start if ramp is enabled
            if session.ramp_enabled:
                session.ramp_start_wpm = int(update.target_wpm * 0.5)

        if update.ramp_enabled is not None:
            session.ramp_enabled = update.ramp_enabled
            if session.ramp_enabled and session.ramp_start_wpm is None:
                session.ramp_start_wpm = int(session.target_wpm * 0.5)

        # NOTE: do NOT extend expires_at here (fixed 7-day retention window).

        self.db.commit()
        self.db.refresh(session)

        return session

    def delete_session(self, session_id: UUID) -> None:
        """
        Delete a session.
        """
        session = self.get_session(session_id)
        self.db.delete(session)
        self.db.commit()

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.
        Returns count of deleted sessions.
        """
        result = self.db.execute(
            delete(ReadingSession).where(ReadingSession.expires_at <= datetime.now(UTC))
        )
        self.db.commit()
        return result.rowcount or 0
```

### 3. Sessions API (`api/sessions.py`)

```python
"""
Session API endpoints.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.session_service import SessionService
from app.schemas.session import (
    SessionCreateRequest,
    SessionResponse,
    SessionListItem,
    SessionProgressUpdate,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionResponse, status_code=201)
def create_session(
    request: SessionCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Create a new reading session.

    - **document_id**: ID of the document to read
    - **start_word_index**: Starting word position (default: 0)
    - **target_wpm**: Target words per minute (100-1500)
    - **ramp_enabled**: Whether to use ramp/build-up mode
    - **ramp_seconds**: Intro duration (v1 UX: 30 or 60 seconds)
    - **ramp_start_wpm**: Derived on create when ramp is enabled (50% of target)
    """
    service = SessionService(db)
    session = service.create_session(request)
    return SessionResponse.model_validate(session)

@router.get("/recent", response_model=list[SessionListItem])
def get_recent_sessions(
    days: int = Query(7, ge=1, le=7, description="Number of days to look back (max: 7)"),
    db: Session = Depends(get_db),
):
    """
    Get recent reading sessions.

    Returns sessions from the last N days, sorted by most recently created.
    Each session includes document title and progress percentage.
    """
    service = SessionService(db)
    return service.get_recent_sessions(days=days)

@router.get("/document/{document_id}/latest", response_model=SessionResponse | None)
def get_latest_session_for_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get the most recent session for a document.

    Use this for "Continue Reading" functionality. Returns null if no
    active session exists for the document.
    """
    service = SessionService(db)
    session = service.get_latest_session_for_document(document_id)

    if session:
        return SessionResponse.model_validate(session)
    return None

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a session by ID.
    """
    service = SessionService(db)
    session = service.get_session(session_id)
    return SessionResponse.model_validate(session)

@router.patch("/{session_id}/progress", response_model=SessionResponse)
def update_session_progress(
    session_id: UUID,
    update: SessionProgressUpdate,
    db: Session = Depends(get_db),
):
    """
    Update session reading progress.

    Call this:
    - Every ~10 seconds during playback
    - When user pauses
    - On page unload (best effort)

    Progress updates do NOT extend session retention.
    """
    service = SessionService(db)
    session = service.update_progress(session_id, update)
    return SessionResponse.model_validate(session)

@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a reading session.
    """
    service = SessionService(db)
    service.delete_session(session_id)
```

### 4. Add resolve-start to Documents API

```python
# Add to api/documents.py

from app.services.navigation_service import NavigationService
from app.schemas.session import ResolveStartRequest, ResolveStartResponse

@router.post("/{document_id}/resolve-start", response_model=ResolveStartResponse)
def resolve_start_position(
    document_id: UUID,
    request: ResolveStartRequest,
    db: Session = Depends(get_db),
):
    """
    Resolve the best starting position near an approximate index.

    When a user scrubs to a position or clicks a word, use this to
    find the nearest sentence, paragraph, or heading start.

    - **approx_word_index**: The approximate position to start from
    - **prefer**: Preferred boundary type ("sentence", "paragraph", "heading")
    - **direction**: Search direction ("backward", "forward", "nearest")
    - **window**: How many words to search (default: 50)

    Returns the resolved index and the type of boundary found.
    """
    # First verify document exists
    from app.services.document_service import DocumentService
    doc_service = DocumentService(db)
    doc = doc_service.get_document(document_id)  # Raises 404 if not found

    # Validate approx_word_index is inside the document
    if request.approx_word_index < 0 or request.approx_word_index >= doc.total_words:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"approx_word_index must be between 0 and {doc.total_words - 1}",
        )

    nav_service = NavigationService(db)
    return nav_service.resolve_start_position(
        document_id=document_id,
        approx_index=request.approx_word_index,
        prefer=request.prefer,
        direction=request.direction,
        window=request.window,
    )
```

### 5. Cleanup Task (`tasks/cleanup.py`)

**Config additions (`app/config.py`):**

- `enable_session_cleanup_task: bool = True` (env: `ENABLE_SESSION_CLEANUP_TASK`)
- `session_cleanup_interval_seconds: int = 3600` (env: `SESSION_CLEANUP_INTERVAL_SECONDS`)

```python
"""
Background tasks for session cleanup.

Note: SQLAlchemy ORM usage here is synchronous. To avoid blocking the event loop,
run cleanup work in a thread (asyncio.to_thread).
"""

import asyncio
import logging
from datetime import datetime, UTC

from app.config import get_settings
from app.database import SessionLocal
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)
settings = get_settings()

def cleanup_expired_sessions_once() -> int:
    db = SessionLocal()
    try:
        service = SessionService(db)
        return service.cleanup_expired_sessions()
    finally:
        db.close()

async def cleanup_expired_sessions_loop() -> None:
    while True:
        try:
            deleted_count = await asyncio.to_thread(cleanup_expired_sessions_once)
            if deleted_count:
                logger.info(
                    "[%s] Cleaned up %s expired sessions",
                    datetime.now(UTC),
                    deleted_count,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Session cleanup error")

        await asyncio.sleep(settings.session_cleanup_interval_seconds)
```

### 6. Update Main App for Cleanup Task

```python
# Update app/main.py

from contextlib import asynccontextmanager
import asyncio
from app.config import get_settings
from app.tasks.cleanup import cleanup_expired_sessions_loop

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background cleanup task (optional; disable via settings/env)
    cleanup_task = None
    if settings.enable_session_cleanup_task:
        cleanup_task = asyncio.create_task(cleanup_expired_sessions_loop())

    yield

    # Cancel cleanup task on shutdown
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

# Update FastAPI app initialization
app = FastAPI(
    title=settings.app_name,
    description="RSVP Speed-Reading Application",
    version="0.1.0",
    lifespan=lifespan,  # Add this
)

# Add sessions router
from app.api import health, documents, sessions

app.include_router(sessions.router, prefix="/api", tags=["sessions"])
```

---

## Testing Requirements

### Test: Session CRUD

```python
# backend/tests/api/test_sessions.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

class TestSessionCreate:
    def test_create_session(self, client, document_id):
        response = client.post("/api/sessions", json={
            "document_id": str(document_id),
            "start_word_index": 0,
            "target_wpm": 300,
            "ramp_enabled": True,
            "ramp_seconds": 30,
        })

        assert response.status_code == 201
        data = response.json()
        assert data["target_wpm"] == 300
        assert data["ramp_enabled"] == True
        assert data["ramp_start_wpm"] == 150  # 50% of 300
        assert data["current_word_index"] == 0

    def test_create_session_with_offset(self, client, document_id):
        response = client.post("/api/sessions", json={
            "document_id": str(document_id),
            "start_word_index": 50,
            "target_wpm": 400,
        })

        assert response.status_code == 201
        assert response.json()["current_word_index"] == 50

    def test_invalid_document_id(self, client):
        response = client.post("/api/sessions", json={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "target_wpm": 300,
        })

        assert response.status_code == 404

class TestSessionProgress:
    def test_update_progress(self, client, session_id):
        before = client.get(f"/api/sessions/{session_id}").json()

        response = client.patch(f"/api/sessions/{session_id}/progress", json={
            "current_word_index": 100,
            "last_known_percent": 25.5,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["current_word_index"] == 100
        assert data["last_known_percent"] == 25.5
        assert data["expires_at"] == before["expires_at"]  # fixed retention

    def test_update_with_wpm_change(self, client, session_id):
        response = client.patch(f"/api/sessions/{session_id}/progress", json={
            "current_word_index": 150,
            "last_known_percent": 37.5,
            "target_wpm": 500,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["target_wpm"] == 500
        assert data["ramp_start_wpm"] == 250  # 50% of 500

class TestRecentSessions:
    def test_get_recent_sessions(self, client, session_id):
        response = client.get("/api/sessions/recent")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check structure
        session = data[0]
        assert "document_title" in session
        assert "last_known_percent" in session

    def test_get_latest_for_document(self, client, document_id, session_id):
        response = client.get(f"/api/sessions/document/{document_id}/latest")

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(document_id)

# Fixtures
@pytest.fixture
def document_id(client):
    """Create a test document and return its ID."""
    response = client.post("/api/documents/from-text", json={
        "language": "en",
        "text": " ".join(["word"] * 500),  # 500 words
    })
    assert response.status_code == 201
    return response.json()["document"]["id"]

@pytest.fixture
def session_id(client, document_id):
    """Create a test session and return its ID."""
    response = client.post("/api/sessions", json={
        "document_id": document_id,
        "target_wpm": 300,
    })
    return response.json()["id"]
```

### Test: Navigation Service

```python
# backend/tests/services/test_navigation.py
import pytest
from uuid import uuid4
from app.services.navigation_service import NavigationService
from app.database import SessionLocal
from app.models.document import Document, SourceType, Language
from app.models.token import Token, BreakType

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def document_with_boundaries(db_session):
    """
    Seed a document + tokens with deterministic sentence/paragraph/heading boundaries.
    """
    document_id = uuid4()

    doc = Document(
        id=document_id,
        title="Navigation Test Doc",
        source_type=SourceType.PASTE,
        language=Language.ENGLISH,
        normalized_text=" ".join([f"w{i}" for i in range(60)]),
        total_words=60,
        tokenizer_version="test",
    )
    db_session.add(doc)

    tokens: list[Token] = []
    for i in range(60):
        tokens.append(Token(
            document_id=document_id,
            word_index=i,
            display_text=f"w{i}",
            clean_text=f"w{i}",
            orp_index_display=0,
            delay_multiplier_after=1.0,
            break_before=None,
            is_sentence_start=(i in (0, 10, 20, 30, 40, 50)),
            is_paragraph_start=(i in (0, 40)),
        ))

    # Mark a heading start at word 20
    tokens[20].break_before = BreakType.HEADING

    db_session.add_all(tokens)
    db_session.commit()

    yield document_id

    db_session.delete(doc)
    db_session.commit()

class TestResolveStart:
    def test_finds_sentence_start(self, db_session, document_with_boundaries):
        """Test that resolve-start finds sentence boundaries."""
        service = NavigationService(db_session)

        # Position in middle of sentence
        result = service.resolve_start_position(
            document_id=document_with_boundaries,
            approx_index=15,   # should snap to 10
            prefer="sentence",
            direction="backward",
        )

        assert result.reason == "sentence_start"
        assert result.resolved_word_index == 10

    def test_finds_paragraph_start(self, db_session, document_with_boundaries):
        """Test that resolve-start finds paragraph boundaries."""
        service = NavigationService(db_session)

        result = service.resolve_start_position(
            document_id=document_with_boundaries,
            approx_index=50,
            prefer="paragraph",
            direction="backward",
        )

        assert result.reason == "paragraph_start"
        assert result.resolved_word_index == 40

    def test_returns_exact_when_no_boundary(self, db_session, document_with_boundaries):
        """Test fallback to exact position."""
        service = NavigationService(db_session)

        # Very small window that won't find boundaries
        result = service.resolve_start_position(
            document_id=document_with_boundaries,
            approx_index=11,
            prefer="sentence",
            direction="backward",
            window=1,
        )

        assert result.reason == "exact"
        assert result.resolved_word_index == 11

    def test_forward_direction(self, db_session, document_with_boundaries):
        """Test forward search direction."""
        service = NavigationService(db_session)

        result = service.resolve_start_position(
            document_id=document_with_boundaries,
            approx_index=5,   # should snap forward to 10
            prefer="sentence",
            direction="forward",
        )

        assert result.reason == "sentence_start"
        assert result.resolved_word_index == 10
```

---

## API Documentation (OpenAPI)

After this session, the OpenAPI docs at `/docs` should show:

### Endpoints

| Method | Path                               | Description                     |
| ------ | ---------------------------------- | ------------------------------- |
| POST   | /api/sessions                      | Create reading session          |
| GET    | /api/sessions/recent               | List recent sessions            |
| GET    | /api/sessions/document/{id}/latest | Get latest session for document |
| GET    | /api/sessions/{id}                 | Get session by ID               |
| PATCH  | /api/sessions/{id}/progress        | Update progress                 |
| DELETE | /api/sessions/{id}                 | Delete session                  |
| POST   | /api/documents/{id}/resolve-start  | Resolve start position          |

### Example Requests

```bash
# Create session
curl -X POST "http://localhost:8000/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "uuid-here",
    "target_wpm": 400,
    "ramp_enabled": true,
    "ramp_seconds": 30
  }'

# Update progress
curl -X PATCH "http://localhost:8000/api/sessions/session-uuid/progress" \
  -H "Content-Type: application/json" \
  -d '{
    "current_word_index": 250,
    "last_known_percent": 50.0
  }'

# Resolve start position
curl -X POST "http://localhost:8000/api/documents/doc-uuid/resolve-start" \
  -H "Content-Type: application/json" \
  -d '{
    "approx_word_index": 100,
    "prefer": "sentence",
    "direction": "backward"
  }'
```

---

## Verification Checklist

- [ ] `POST /api/sessions` creates session with correct defaults
- [ ] `POST /api/sessions` calculates ramp_start_wpm correctly (50% of target)
- [ ] `GET /api/sessions/recent` returns sessions with document titles
- [ ] `GET /api/sessions/recent` is sorted newest-first by session creation
- [ ] `GET /api/sessions/document/{id}/latest` returns null for no sessions
- [ ] `PATCH /api/sessions/{id}/progress` updates all fields
- [ ] `PATCH /api/sessions/{id}/progress` does **not** extend `expires_at` (fixed retention)
- [ ] `POST /documents/{id}/resolve-start` finds sentence boundaries
- [ ] `POST /documents/{id}/resolve-start` respects direction parameter
- [ ] Background cleanup task starts with app
- [ ] OpenAPI docs show all endpoints with descriptions
- [ ] All tests pass

---

## Context for Next Session

**What exists after Session 4:**

- Complete backend API:
  - Document CRUD + preview + tokens
  - Session CRUD + progress tracking
  - resolve-start for navigation
  - Background cleanup
- OpenAPI documentation at `/docs`

**Session 5 will need:**

- All API endpoints documented above
- Understanding of chunk retrieval (`GET /documents/{id}/tokens`)
- Session progress update endpoint for auto-save
- resolve-start endpoint for scrubber jumps

---

## Backend Complete!

After Session 4, the backend is feature-complete for v1 (web-only). The remaining sessions focus on the React frontend.

> **v1 Scope Note**: `POST /api/documents/from-file` + PDF upload are deferred (see `../docs/FUTURE-PDF-UPLOAD.md`).

**Full API Summary:**

```
Health:
  GET  /api/health

Documents:
  POST /api/documents/from-text
  GET  /api/documents/{id}
  GET  /api/documents/{id}/preview
  GET  /api/documents/{id}/tokens
  POST /api/documents/{id}/resolve-start
  DELETE /api/documents/{id}

Sessions:
  POST   /api/sessions
  GET    /api/sessions/recent
  GET    /api/sessions/document/{id}/latest
  GET    /api/sessions/{id}
  PATCH  /api/sessions/{id}/progress
  DELETE /api/sessions/{id}
```
