# Session 3: Document Ingestion API

## Overview

**Duration**: ~3-4 hours
**Goal**: Implement document creation endpoints for **text input** (paste + Markdown `.md` contents), with **PDF upload deferred**.

**Deliverable**: Working API endpoints for creating documents from text (used for paste and Markdown file contents), with tokens stored in database.

> **v1 Scope Note (Web-only)**:
>
> - `.md` “upload” happens in the web UI by reading the file contents in the browser and sending them via `POST /documents/from-text`.
> - `POST /documents/from-file` and PDF extraction are deferred (see `../docs/FUTURE-PDF-UPLOAD.md`).

---

## Prerequisites

- Session 1 completed (database models, Docker Compose)
- Session 2 completed (tokenization engine)
- **Deferred (PDF future)**: Add PyMuPDF (`pymupdf`) + validate licensing
- **Deferred (file upload future)**: Add `python-multipart` for multipart uploads

---

## Key Decisions (Must Read)

1. **Use sync ingestion endpoints (`def`)**  
   We use sync SQLAlchemy. Implement the ingestion endpoints with `def` (not `async def`). FastAPI runs sync path operations in a threadpool, preventing event-loop blocking.
2. **Warnings are part of the API contract**  
   Ingestion warnings (e.g., normalization notices) must be returned to clients in the JSON response body (not silently dropped).
3. **No silent fallbacks**  
   Never return "0"/empty results on errors. Raise a typed exception and return a clear error response.
4. **Service layer is framework-agnostic**  
   `DocumentService` raises domain errors; the API layer maps them to HTTP responses.
5. **Atomic persistence**  
   A document is only considered created if the document row _and_ all token rows are persisted in the same transaction.

---

## Objectives & Acceptance Criteria

| #   | Objective                   | Acceptance Criteria                                                          |
| --- | --------------------------- | ---------------------------------------------------------------------------- |
| 1   | POST /documents/from-text   | Creates document from pasted text; returns `{document, warnings: []}`        |
| 2   | Token storage               | All tokens stored with correct indices; write is atomic (single transaction) |
| 3   | GET /documents/{id}         | Returns document metadata                                                    |
| 4   | GET /documents/{id}/preview | Returns full text for preview                                                |
| 5   | GET /documents/{id}/tokens  | Returns paginated token chunks (UUID `document_id`)                          |
| 6   | Word limit enforcement      | Rejects documents >20,000 words                                              |
| 7   | Error handling              | Domain errors map to clear 400/413/404 responses                             |

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── tokenizer/              # From Session 2
│   │   ├── document_service.py     # Document CRUD operations + domain errors
│   ├── api/
│   │   ├── health.py               # From Session 1
│   │   └── documents.py            # Document endpoints
│   └── schemas/
│       └── document.py             # Add DocumentCreateResponse (document + warnings)
└── tests/
    ├── conftest.py                 # DB + dependency overrides for API tests
    ├── api/
    │   └── test_documents.py
```

---

## Implementation Details

### 1. Document Service (`services/document_service.py`)

```python
"""
Document service for creating, storing, and retrieving documents.

Design notes:
- This layer is HTTP-framework agnostic: raise domain errors here, map to HTTP in the API layer.
- Writes are atomic: a document is never persisted without its full token set.
"""

from uuid import UUID, uuid4
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.models.document import Document, SourceType, Language
from app.models.token import Token, BreakType
from app.schemas.document import DocumentPreview
from app.schemas.token import TokenDTO, TokenChunkResponse
from app.services.tokenizer import tokenize_text, get_tokenizer_version
from app.config import get_settings

settings = get_settings()

class DocumentServiceError(Exception):
    """Base exception for document-service failures."""

class DocumentTooLargeError(DocumentServiceError):
    pass

class DocumentEmptyError(DocumentServiceError):
    pass

class DocumentNotFoundError(DocumentServiceError):
    pass

class InvalidLanguageError(DocumentServiceError):
    pass

class InvalidSourceTypeError(DocumentServiceError):
    pass

class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    def create_from_text(
        self,
        text: str,
        language: str,
        title: str | None = None,
        source_type: str = "paste",
        original_filename: str | None = None,
        user_id: UUID | None = None,
    ) -> Document:
        """
        Create a document from text input.

        v1 notes:
        - Used for both paste input and Markdown `.md` "upload" (file contents are read client-side).
        - PDF upload is deferred.
        """
        try:
            source_type_enum = SourceType(source_type)
        except ValueError as e:
            raise InvalidSourceTypeError(f"Unsupported source type: {source_type}") from e

        # Validate and tokenize
        normalized_text, tokens = tokenize_text(
            text,
            language=language,
            source_type=source_type_enum.value,
        )

        if len(tokens) == 0:
            raise DocumentEmptyError("Document contains no readable text.")

        # Check word limit
        if len(tokens) > settings.max_document_words:
            raise DocumentTooLargeError(
                f"Document exceeds maximum word limit of {settings.max_document_words:,}. "
                f"This document has {len(tokens):,} words."
            )

        # Generate title if not provided
        if not title:
            if source_type_enum == SourceType.MARKDOWN and original_filename:
                title = (
                    original_filename.rsplit('.', 1)[0]
                    if '.' in original_filename
                    else original_filename
                )
            else:
                title = self._generate_title(normalized_text)

        # Create document
        try:
            language_enum = Language(language)
        except ValueError as e:
            raise InvalidLanguageError(f"Unsupported language: {language}") from e

        document = Document(
            id=uuid4(),
            user_id=user_id,
            title=title,
            source_type=source_type_enum,
            language=language_enum,
            original_filename=original_filename,
            normalized_text=normalized_text,
            total_words=len(tokens),
            tokenizer_version=get_tokenizer_version(),
        )

        with self.db.begin():
            self.db.add(document)
            self._store_tokens(document.id, tokens)
        self.db.refresh(document)

        return document

    def get_document(self, document_id: UUID) -> Document:
        """
        Get a document by ID.
        """
        document = self.db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if not document:
            raise DocumentNotFoundError("Document not found")

        return document

    def get_preview(self, document_id: UUID) -> DocumentPreview:
        """
        Get document preview with navigation anchors.
        """
        document = self.get_document(document_id)

        # Get anchor points (paragraph and heading starts)
        anchors = self._get_anchors(document_id)

        return DocumentPreview(
            id=document.id,
            title=document.title,
            preview_text=document.normalized_text,
            total_words=document.total_words,
            anchors=anchors,
        )

    def get_tokens(
        self,
        document_id: UUID,
        start: int = 0,
        limit: int | None = None,
    ) -> TokenChunkResponse:
        """
        Get a chunk of tokens for a document.
        """
        document = self.get_document(document_id)

        if limit is None:
            limit = settings.chunk_size

        # Clamp values
        start = max(0, min(start, document.total_words))
        limit = min(limit, settings.chunk_size * 2)  # Max 2x chunk size

        # Query tokens
        stmt = (
            select(Token)
            .where(
                Token.document_id == document_id,
                Token.word_index >= start,
                Token.word_index < start + limit,
            )
            .order_by(Token.word_index)
        )
        tokens = self.db.execute(stmt).scalars().all()

        token_dtos = [
            TokenDTO(
                word_index=t.word_index,
                display_text=t.display_text,
                orp_index_display=t.orp_index_display,
                delay_multiplier_after=t.delay_multiplier_after,
                break_before=t.break_before,
                is_sentence_start=t.is_sentence_start,
                is_paragraph_start=t.is_paragraph_start,
            )
            for t in tokens
        ]

        return TokenChunkResponse(
            document_id=document_id,
            total_words=document.total_words,
            range_start=start,
            range_end=start + len(token_dtos),
            tokens=token_dtos,
        )

    def delete_document(self, document_id: UUID) -> None:
        """
        Delete a document and all associated data.
        """
        document = self.get_document(document_id)
        with self.db.begin():
            self.db.delete(document)  # Cascade deletes tokens and sessions

    def _store_tokens(self, document_id: UUID, tokens: list) -> None:
        """
        Bulk insert tokens into database.
        """
        rows = [
            {
                "document_id": document_id,
                "word_index": t.word_index,
                "display_text": t.display_text,
                "clean_text": t.clean_text,
                "orp_index_display": t.orp_index_display,
                "delay_multiplier_after": t.delay_multiplier_after,
                "break_before": BreakType(t.break_before) if t.break_before else None,
                "is_sentence_start": t.is_sentence_start,
                "is_paragraph_start": t.is_paragraph_start,
                "char_offset_start": t.char_offset_start,
                "char_offset_end": t.char_offset_end,
            }
            for t in tokens
        ]
        self.db.execute(insert(Token), rows)

    def _get_anchors(self, document_id: UUID, max_anchors: int = 100) -> list[dict]:
        """
        Get navigation anchors (paragraph/heading starts) for preview.
        """
        # Query paragraph and heading start tokens
        stmt = (
            select(Token)
            .where(Token.document_id == document_id)
            .where(
                Token.is_paragraph_start.is_(True) |
                Token.break_before.is_not(None)
            )
            .order_by(Token.word_index)
            .limit(max_anchors)
        )
        tokens = self.db.execute(stmt).scalars().all()

        anchors = []
        for t in tokens:
            anchor_type = "paragraph"
            if t.break_before == BreakType.HEADING:
                anchor_type = "heading"

            anchors.append({
                "word_index": t.word_index,
                "type": anchor_type,
                "preview": t.display_text[:50],
            })

        return anchors

    def _generate_title(self, text: str, max_words: int = 6) -> str:
        """
        Generate a title from the first few words of text.
        """
        words = text.split()[:max_words]
        title = " ".join(words)

        if len(text.split()) > max_words:
            title += "..."

        return title[:100]  # Max 100 chars
```

### 3. Documents API (`api/documents.py`)

#### 3.0 Add create-response schema (`schemas/document.py`)

Return warnings in the response body so the frontend can display them in the import/preview flow.

```python
# Add to app/schemas/document.py
from pydantic import BaseModel, Field

class DocumentCreateResponse(BaseModel):
    document: DocumentMeta
    warnings: list[str] = Field(default_factory=list)
```

```python
"""
Document API endpoints.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.document_service import (
    DocumentService,
    DocumentEmptyError,
    DocumentNotFoundError,
    DocumentTooLargeError,
    InvalidLanguageError,
    InvalidSourceTypeError,
)
from app.schemas.document import (
    DocumentFromTextRequest,
    DocumentCreateResponse,
    DocumentMeta,
    DocumentPreview,
)
from app.schemas.token import TokenChunkResponse

router = APIRouter(prefix="/documents", tags=["documents"])

def _raise_for_service_error(err: Exception) -> None:
    if isinstance(err, DocumentTooLargeError):
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(err))
    if isinstance(err, (DocumentEmptyError, InvalidLanguageError, InvalidSourceTypeError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    if isinstance(err, DocumentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
    )

@router.post("/from-text", response_model=DocumentCreateResponse, status_code=status.HTTP_201_CREATED)
def create_document_from_text(
    request: DocumentFromTextRequest,
    db: Session = Depends(get_db),
):
    """
    Create a document from text.

    - **title**: Optional document title (auto-generated if not provided)
    - **language**: Language code ("en" or "de")
    - **text**: The text content to process
    - **source_type**: Optional ("paste" or "md") — for Markdown `.md` contents sent as text
    - **original_filename**: Optional (e.g., `"notes.md"`)
    """
    service = DocumentService(db)
    try:
        document = service.create_from_text(
            text=request.text,
            language=request.language.value,
            title=request.title,
            source_type=request.source_type.value,
            original_filename=request.original_filename,
        )
    except Exception as e:
        _raise_for_service_error(e)

    return DocumentCreateResponse(
        document=DocumentMeta.model_validate(document),
        warnings=[],
    )

@router.get("/{document_id}", response_model=DocumentMeta)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get document metadata by ID.
    """
    service = DocumentService(db)
    try:
        document = service.get_document(document_id)
    except Exception as e:
        _raise_for_service_error(e)
    return DocumentMeta.model_validate(document)

@router.get("/{document_id}/preview", response_model=DocumentPreview)
def get_document_preview(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get document preview with full text and navigation anchors.

    Use this for the preview mode UI where users can scroll
    and click words to set their starting position.
    """
    service = DocumentService(db)
    try:
        return service.get_preview(document_id)
    except Exception as e:
        _raise_for_service_error(e)

@router.get("/{document_id}/tokens", response_model=TokenChunkResponse)
def get_document_tokens(
    document_id: UUID,
    start: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """
    Get a chunk of tokens for playback.

    - **start**: Starting word index (0-based)
    - **limit**: Number of tokens to return (max 1000)

    Frontend should prefetch chunks around the current reading position
    for smooth playback.
    """
    service = DocumentService(db)
    try:
        return service.get_tokens(document_id, start=start, limit=limit)
    except Exception as e:
        _raise_for_service_error(e)

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a document and all associated data.

    This permanently removes:
    - The document
    - All tokens
    - All reading sessions
    """
    service = DocumentService(db)
    try:
        service.delete_document(document_id)
    except Exception as e:
        _raise_for_service_error(e)
```

### 4. Update Main App (`main.py`)

```python
# Add to app/main.py imports
from app.api import health, documents

# Add router
app.include_router(documents.router, prefix="/api", tags=["documents"])
```

### (Deferred) File/PDF Upload Dependencies

PDF upload and multipart uploads are deferred (see `../docs/FUTURE-PDF-UPLOAD.md`). v1 does not add `python-multipart` or PyMuPDF.

---

## Testing Requirements

### Test: Document Creation from Text

```python
# tests/api/test_documents.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestCreateFromText:
    def test_create_simple_document(self):
        response = client.post("/api/documents/from-text", json={
            "language": "en",
            "text": "Hello world. This is a test document.",
        })

        assert response.status_code == 201
        data = response.json()
        assert "document" in data
        assert data["warnings"] == []
        assert "id" in data["document"]
        assert data["document"]["total_words"] > 0
        assert data["document"]["language"] == "en"
        assert data["document"]["source_type"] == "paste"

    def test_create_with_title(self):
        response = client.post("/api/documents/from-text", json={
            "title": "My Custom Title",
            "language": "de",
            "text": "Hallo Welt. Das ist ein Test.",
        })

        assert response.status_code == 201
        assert response.json()["document"]["title"] == "My Custom Title"

    def test_empty_text_rejected(self):
        response = client.post("/api/documents/from-text", json={
            "language": "en",
            "text": "   ",  # Whitespace only
        })

        assert response.status_code == 400

    def test_word_limit_enforced(self):
        # Create text with >20k words
        long_text = "word " * 25000

        response = client.post("/api/documents/from-text", json={
            "language": "en",
            "text": long_text,
        })

        assert response.status_code == 413
        assert "20,000" in response.json()["detail"]

class TestCreateFromFile:
    def test_create_from_markdown(self):
        md_content = b"# Heading\n\nThis is **markdown** content."

        response = client.post(
            "/api/documents/from-file",
            data={"language": "en"},
            files={"file": ("test.md", md_content, "text/markdown")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["warnings"] == []
        assert data["document"]["source_type"] == "md"

    def test_invalid_file_type_rejected(self):
        response = client.post(
            "/api/documents/from-file",
            data={"language": "en"},
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )

        assert response.status_code == 400
        assert "only .md and .pdf" in response.json()["detail"].lower()

class TestGetDocument:
    def test_get_existing_document(self, created_document_id):
        response = client.get(f"/api/documents/{created_document_id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(created_document_id)

    def test_get_nonexistent_document(self):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/documents/{fake_id}")

        assert response.status_code == 404

class TestGetTokens:
    def test_get_token_chunk(self, created_document_id):
        response = client.get(
            f"/api/documents/{created_document_id}/tokens",
            params={"start": 0, "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert data["range_start"] == 0
        assert len(data["tokens"]) <= 10

    def test_tokens_have_required_fields(self, created_document_id):
        response = client.get(f"/api/documents/{created_document_id}/tokens")
        data = response.json()

        if data["tokens"]:
            token = data["tokens"][0]
            assert "word_index" in token
            assert "display_text" in token
            assert "orp_index_display" in token
            assert "delay_multiplier_after" in token

# Fixture for tests that need an existing document
@pytest.fixture
def created_document_id():
    response = client.post("/api/documents/from-text", json={
        "language": "en",
        "text": "This is a test document with several words for testing.",
    })
    return response.json()["document"]["id"]
```

### Test: PDF Extraction

```python
# tests/services/test_pdf_extractor.py
import pytest
from app.services.pdf_extractor import extract_text_from_pdf, PDFExtractionError

class TestPDFExtraction:
    def test_extract_simple_pdf(self, sample_pdf_bytes):
        """Test extraction from a valid PDF."""
        result = extract_text_from_pdf(sample_pdf_bytes)

        assert result.text
        assert result.page_count > 0
        assert isinstance(result.warnings, list)

    def test_invalid_pdf_raises_error(self):
        """Test that invalid data raises appropriate error."""
        with pytest.raises(PDFExtractionError):
            extract_text_from_pdf(b"not a pdf")

    def test_empty_pdf_raises_error(self, empty_pdf_bytes):
        """Test that PDF with no text raises error."""
        with pytest.raises(PDFExtractionError) as exc:
            extract_text_from_pdf(empty_pdf_bytes)

        assert "no text" in str(exc.value).lower()

# You'll need to create test PDF files or generate them programmatically
@pytest.fixture
def sample_pdf_bytes():
    """Generate a simple test PDF."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World. This is a test PDF.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

@pytest.fixture
def empty_pdf_bytes():
    """Generate a PDF with no text (image only would be similar)."""
    import fitz
    doc = fitz.open()
    doc.new_page()  # Empty page
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
```

---

## Integration Test Script

```bash
#!/bin/bash
# tests/integration/test_document_flow.sh

BASE_URL="http://localhost:8000/api"

echo "=== Testing Document API ==="

# Test 1: Create from text
echo -e "\n1. Creating document from text..."
DOC_RESPONSE=$(curl -s -X POST "$BASE_URL/documents/from-text" \
  -H "Content-Type: application/json" \
  -d '{"language": "en", "text": "Hello world. This is a test document with multiple sentences. It should work correctly."}')

DOC_ID=$(echo $DOC_RESPONSE | jq -r '.document.id')
echo "Created document: $DOC_ID"
echo "Total words: $(echo $DOC_RESPONSE | jq -r '.document.total_words')"
echo "Warnings: $(echo $DOC_RESPONSE | jq -r '.warnings | length')"

# Test 2: Get document
echo -e "\n2. Getting document metadata..."
curl -s "$BASE_URL/documents/$DOC_ID" | jq '.title, .total_words'

# Test 3: Get preview
echo -e "\n3. Getting preview..."
curl -s "$BASE_URL/documents/$DOC_ID/preview" | jq '.total_words, .anchors | length'

# Test 4: Get tokens
echo -e "\n4. Getting tokens (first 5)..."
curl -s "$BASE_URL/documents/$DOC_ID/tokens?limit=5" | jq '.tokens[] | {word_index, display_text, orp_index_display}'

# Test 5: Delete
echo -e "\n5. Deleting document..."
curl -s -X DELETE "$BASE_URL/documents/$DOC_ID" -w "Status: %{http_code}\n"

echo -e "\n=== All tests complete ==="
```

---

## Verification Checklist

- [ ] `POST /api/documents/from-text` creates document and returns metadata
- [ ] `POST /api/documents/from-text` returns `warnings: []`
- [ ] `POST /api/documents/from-file` accepts .md files
- [ ] `POST /api/documents/from-file` accepts .pdf files
- [ ] `POST /api/documents/from-file` returns PDF extraction warnings (if any)
- [ ] PDF extraction handles multi-page documents
- [ ] PDF extraction returns warnings for problematic pages
- [ ] Documents >20,000 words are rejected with 413
- [ ] Empty/whitespace-only content is rejected with 400
- [ ] `GET /api/documents/{id}` returns correct metadata
- [ ] `GET /api/documents/{id}/preview` returns full text + anchors
- [ ] `GET /api/documents/{id}/tokens` returns paginated chunks
- [ ] Token chunks have all required fields
- [ ] `DELETE /api/documents/{id}` removes document and all tokens
- [ ] All tests pass

---

## Context for Next Session

**What exists after Session 3:**

- Complete document ingestion pipeline
- PDF extraction with PyMuPDF
- Token storage in database
- API endpoints for documents and tokens

**Session 4 will need:**

- Document endpoints (for session association)
- Token endpoints (for resolve-start functionality)
- Database session model (already exists from Session 1)
