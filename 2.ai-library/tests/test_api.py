# tests/test_api.py
"""Tests for the REST API."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from httpx import AsyncClient, ASGITransport

from src.api.main import create_app
from src.api.dependencies import (
    get_session_manager,
    get_library_scanner,
    get_semantic_search,
    get_query_engine,
    get_config,
    get_vector_store,
)
from src.config import Config, APIConfig
from src.models.session import ExtractionSession, SessionPhase
from src.models.content import SourceDocument, ContentBlock, BlockType
from src.models.content_mode import ContentMode
from src.models.cleanup_plan import CleanupPlan, CleanupItem, CleanupDisposition
from src.models.library import LibraryFile, LibraryCategory
from src.models.routing_plan import RoutingPlan, BlockRoutingItem, BlockDestination
from src.query.engine import QueryResult
from src.query.retriever import RetrievedChunk
from src.extraction.checksums import generate_checksums
import anyio


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Create a mock config."""
    return Config()


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    block = ContentBlock(
        id="block_001",
        block_type=BlockType.PARAGRAPH,
        content="Test content for block",
        content_canonical="test content for block",
        canonicalization_version="v1",
        source_file="test.md",
        source_line_start=1,
        source_line_end=5,
        heading_path=["Test Section"],
        checksum_exact="a1b2c3d4e5f6g7h8",
        checksum_canonical="a1b2c3d4e5f6g7h8",
    )

    source = SourceDocument(
        file_path="test.md",
        checksum_exact="abcdef0123456789",
        total_blocks=1,
        blocks=[block],
    )

    cleanup_item = CleanupItem(
        block_id="block_001",
        heading_path=["Test Section"],
        content_preview="Test content...",
        suggested_disposition=CleanupDisposition.KEEP,
        suggestion_reason="Default keep",
        final_disposition=None,
    )

    cleanup_plan = CleanupPlan(
        session_id="test123",
        source_file="test.md",
        items=[cleanup_item],
        approved=False,
    )

    return ExtractionSession(
        id="test123",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.CLEANUP_PLAN_READY,
        source=source,
        library_path="./library",
        content_mode=ContentMode.STRICT,
        cleanup_plan=cleanup_plan,
    )


@pytest.fixture
def mock_session_manager(mock_session):
    """Create a mock session manager."""
    manager = AsyncMock()
    manager.get_session = AsyncMock(return_value=mock_session)
    manager.list_sessions = AsyncMock(return_value=["test123"])
    manager.create_session = AsyncMock(return_value=mock_session)
    manager.generate_cleanup_plan = AsyncMock(return_value=mock_session.cleanup_plan)
    manager.set_cleanup_decision = AsyncMock()
    manager.approve_cleanup_plan = AsyncMock(return_value=True)
    manager.approve_plan = AsyncMock(return_value=True)
    manager.select_destination = AsyncMock()
    manager.storage = AsyncMock()
    manager.storage.save = AsyncMock()
    manager.storage.delete = AsyncMock()
    return manager


@pytest.fixture
def mock_library_scanner():
    """Create a mock library scanner."""
    scanner = AsyncMock()
    scanner.scan = AsyncMock(return_value={
        "categories": [
            LibraryCategory(
                name="tech",
                path="tech",
                description="Technology",
                files=[
                    LibraryFile(
                        path="tech/auth.md",
                        category="tech",
                        title="Authentication",
                        sections=["OAuth", "JWT"],
                        last_modified="2024-01-01T00:00:00",
                        block_count=5,
                    )
                ],
                subcategories=[],
            )
        ],
        "total_files": 1,
        "total_sections": 2,
    })
    scanner.get_file = AsyncMock(return_value=LibraryFile(
        path="tech/auth.md",
        category="tech",
        title="Authentication",
        sections=["OAuth", "JWT"],
        last_modified="2024-01-01T00:00:00",
        block_count=5,
    ))
    scanner.search_sections = AsyncMock(return_value=[
        {
            "file_path": "tech/auth.md",
            "file_title": "Authentication",
            "section": "OAuth",
            "category": "tech",
        }
    ])
    return scanner


@pytest.fixture
def mock_semantic_search():
    """Create a mock semantic search."""
    search = AsyncMock()
    search.search = AsyncMock(return_value=[])
    search.ensure_indexed = AsyncMock(return_value={"status": "indexed", "files_indexed": 5})
    search.get_stats = AsyncMock(return_value={"total_chunks": 100})
    return search


@pytest.fixture
def mock_query_engine():
    """Create a mock query engine."""
    engine = AsyncMock()
    chunks = [
        RetrievedChunk(
            content=f"Chunk {i}",
            source_file=f"file{i}.md",
            section=f"Section {i}",
            similarity=0.9 - (i * 0.01),
            content_fingerprint=f"fp{i:02d}",
        )
        for i in range(8)
    ]
    engine.query = AsyncMock(
        return_value=QueryResult(
            answer="Test answer",
            sources=[c.source_file for c in chunks],
            confidence=0.9,
            conversation_id="conv-123",
            related_topics=[],
            raw_chunks=chunks,
        )
    )
    return engine


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = AsyncMock()
    store.initialize = AsyncMock()
    store.close = AsyncMock()
    return store


@pytest.fixture
async def client(
    mock_config,
    mock_session_manager,
    mock_library_scanner,
    mock_semantic_search,
    mock_vector_store,
):
    """Create test client with mocked dependencies."""
    app = create_app()

    # Create proper async override functions
    async def override_get_config():
        return mock_config

    async def override_get_session_manager(config: Config = None):
        return mock_session_manager

    async def override_get_library_scanner(config: Config = None):
        return mock_library_scanner

    async def override_get_vector_store(config: Config = None):
        return mock_vector_store

    async def override_get_semantic_search(config: Config = None, vector_store = None):
        return mock_semantic_search

    app.dependency_overrides[get_config] = override_get_config
    app.dependency_overrides[get_session_manager] = override_get_session_manager
    app.dependency_overrides[get_library_scanner] = override_get_library_scanner
    app.dependency_overrides[get_vector_store] = override_get_vector_store
    app.dependency_overrides[get_semantic_search] = override_get_semantic_search

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_query_engine(
    mock_config,
    mock_session_manager,
    mock_library_scanner,
    mock_semantic_search,
    mock_vector_store,
    mock_query_engine,
):
    """Create test client with mocked query engine."""
    app = create_app()

    async def override_get_config():
        return mock_config

    async def override_get_session_manager(config: Config = None):
        return mock_session_manager

    async def override_get_library_scanner(config: Config = None):
        return mock_library_scanner

    async def override_get_vector_store(config: Config = None):
        return mock_vector_store

    async def override_get_semantic_search(config: Config = None, vector_store=None):
        return mock_semantic_search

    async def override_get_query_engine(config: Config = None, search=None):
        return mock_query_engine

    app.dependency_overrides[get_config] = override_get_config
    app.dependency_overrides[get_session_manager] = override_get_session_manager
    app.dependency_overrides[get_library_scanner] = override_get_library_scanner
    app.dependency_overrides[get_vector_store] = override_get_vector_store
    app.dependency_overrides[get_semantic_search] = override_get_semantic_search
    app.dependency_overrides[get_query_engine] = override_get_query_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# =============================================================================
# Health & Root Tests
# =============================================================================


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_root(client):
    """Test API root endpoint."""
    response = await client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data


# =============================================================================
# Session Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_sessions(client, mock_session_manager, mock_session):
    """Test listing sessions."""
    response = await client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_get_session(client, mock_session_manager, mock_session):
    """Test getting a session."""
    response = await client.get("/api/sessions/test123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test123"
    assert data["phase"] == "cleanup_plan_ready"


@pytest.mark.asyncio
async def test_get_session_not_found(client, mock_session_manager):
    """Test getting a non-existent session."""
    mock_session_manager.get_session = AsyncMock(return_value=None)
    response = await client.get("/api/sessions/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session(client, mock_session_manager, mock_session):
    """Test deleting a session."""
    response = await client.delete("/api/sessions/test123")
    assert response.status_code == 200
    mock_session_manager.storage.delete.assert_called_once_with("test123")


@pytest.mark.asyncio
async def test_create_session_invalid_content_mode(client, mock_session_manager):
    """Invalid content_mode should return 400 (not silently default)."""
    response = await client.post(
        "/api/sessions",
        json={"source_path": "test.md", "content_mode": "invalid"},
    )

    assert response.status_code == 400
    mock_session_manager.create_session.assert_not_called()


@pytest.mark.asyncio
async def test_upload_source_sanitizes_filename(client, mock_session_manager):
    """Uploaded filenames should be sanitized to prevent path traversal writes."""
    from datetime import datetime
    from unittest.mock import AsyncMock, patch
    from pathlib import Path

    # Session without a source so upload is allowed
    session = ExtractionSession(
        id="sess_upload",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.INITIALIZED,
        source=None,
        library_path="./library",
        content_mode=ContentMode.STRICT,
    )
    mock_session_manager.get_session = AsyncMock(return_value=session)

    # Patch parser to avoid real parsing and capture the temp path used
    source_doc = SourceDocument(
        file_path="upload.md",
        checksum_exact="abcdef0123456789",
        total_blocks=0,
        blocks=[],
    )

    with patch(
        "src.extraction.parser.parse_markdown_file",
        new=AsyncMock(return_value=source_doc),
    ) as mock_parse:
        response = await client.post(
            "/api/sessions/sess_upload/upload",
            files={"file": ("../../../evil.md", b"# hello", "text/markdown")},
        )

    assert response.status_code == 200
    called_path = mock_parse.call_args[0][0]
    resolved_parent = Path(called_path).resolve().parent
    assert resolved_parent == Path("./temp_uploads").resolve()


@pytest.mark.asyncio
async def test_execute_plan_supports_create_file_action(client, mock_session_manager, tmp_path):
    """execute_plan should handle routing action=create_file without failing."""
    from datetime import datetime
    from unittest.mock import AsyncMock

    library_path = str(tmp_path / "library")

    block_content = "Block content"
    exact, canonical = generate_checksums(block_content, is_code=False)
    block = ContentBlock(
        id="block_001",
        block_type=BlockType.PARAGRAPH,
        content=block_content,
        content_canonical=block_content,
        source_file="source.md",
        source_line_start=1,
        source_line_end=1,
        heading_path=["Heading"],
        checksum_exact=exact,
        checksum_canonical=canonical,
    )
    source = SourceDocument(
        file_path="source.md",
        checksum_exact="abcdef0123456789",
        total_blocks=1,
        blocks=[block],
    )

    dest = BlockDestination(
        destination_file="tech/new_file.md",
        destination_section=None,
        action="create_file",
        confidence=0.9,
        reasoning="test",
        proposed_file_title="New File",
    )
    item = BlockRoutingItem(
        block_id="block_001",
        heading_path=["Heading"],
        content_preview=block_content[:200],
        options=[dest],
        selected_option_index=0,
        status="selected",
    )
    routing_plan = RoutingPlan(
        session_id="sess_exec_create_file",
        source_file="source.md",
        content_mode="strict",
        blocks=[item],
        approved=True,
    )

    session = ExtractionSession(
        id="sess_exec_create_file",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.READY_TO_EXECUTE,
        source=source,
        library_path=library_path,
        content_mode=ContentMode.STRICT,
        routing_plan=routing_plan,
    )

    phases: list[SessionPhase] = []

    async def capture_save(sess):
        phases.append(sess.phase)

    mock_session_manager.get_session = AsyncMock(return_value=session)
    mock_session_manager.storage.save = AsyncMock(side_effect=capture_save)

    response = await client.post("/api/sessions/sess_exec_create_file/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    file_path = anyio.Path(library_path) / "tech" / "new_file.md"
    text = await file_path.read_text()
    assert "# New File" in text
    assert "BLOCK_START" in text
    assert SessionPhase.VERIFYING in phases


@pytest.mark.asyncio
async def test_execute_plan_supports_create_section_action(client, mock_session_manager, tmp_path):
    """execute_plan should handle routing action=create_section without failing."""
    from datetime import datetime
    from unittest.mock import AsyncMock

    library_path = anyio.Path(str(tmp_path / "library"))
    existing = library_path / "tech" / "existing.md"
    await existing.parent.mkdir(parents=True, exist_ok=True)
    await existing.write_text("# Existing\n\nIntro")

    block_content = "Block content"
    exact, canonical = generate_checksums(block_content, is_code=False)
    block = ContentBlock(
        id="block_001",
        block_type=BlockType.PARAGRAPH,
        content=block_content,
        content_canonical=block_content,
        source_file="source.md",
        source_line_start=1,
        source_line_end=1,
        heading_path=["Heading"],
        checksum_exact=exact,
        checksum_canonical=canonical,
    )
    source = SourceDocument(
        file_path="source.md",
        checksum_exact="abcdef0123456789",
        total_blocks=1,
        blocks=[block],
    )

    dest = BlockDestination(
        destination_file="tech/existing.md",
        destination_section=None,
        action="create_section",
        confidence=0.9,
        reasoning="test",
        proposed_section_title="New Section",
    )
    item = BlockRoutingItem(
        block_id="block_001",
        heading_path=["Heading"],
        content_preview=block_content[:200],
        options=[dest],
        selected_option_index=0,
        status="selected",
    )
    routing_plan = RoutingPlan(
        session_id="sess_exec_create_section",
        source_file="source.md",
        content_mode="strict",
        blocks=[item],
        approved=True,
    )

    session = ExtractionSession(
        id="sess_exec_create_section",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.READY_TO_EXECUTE,
        source=source,
        library_path=str(library_path),
        content_mode=ContentMode.STRICT,
        routing_plan=routing_plan,
    )

    mock_session_manager.get_session = AsyncMock(return_value=session)
    mock_session_manager.storage.save = AsyncMock()

    response = await client.post("/api/sessions/sess_exec_create_section/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    text = await existing.read_text()
    assert "## New Section" in text
    assert "BLOCK_START" in text

# =============================================================================
# Blocks Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_blocks(client, mock_session_manager, mock_session):
    """Test getting blocks from a session."""
    response = await client.get("/api/sessions/test123/blocks")
    assert response.status_code == 200
    data = response.json()
    assert "blocks" in data
    assert data["total"] == 1
    assert data["blocks"][0]["id"] == "block_001"


# =============================================================================
# Cleanup Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_cleanup_plan(client, mock_session_manager, mock_session):
    """Test getting cleanup plan."""
    response = await client.get("/api/sessions/test123/cleanup")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test123"
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_set_cleanup_decision(client, mock_session_manager, mock_session):
    """Test setting cleanup decision."""
    response = await client.post(
        "/api/sessions/test123/cleanup/decide/block_001",
        json={"disposition": "keep"}
    )
    assert response.status_code == 200
    mock_session_manager.set_cleanup_decision.assert_called_once()


@pytest.mark.asyncio
async def test_set_cleanup_decision_invalid(client, mock_session_manager, mock_session):
    """Test invalid cleanup decision."""
    response = await client.post(
        "/api/sessions/test123/cleanup/decide/block_001",
        json={"disposition": "invalid"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_approve_cleanup(client, mock_session_manager, mock_session):
    """Test approving cleanup plan."""
    response = await client.post("/api/sessions/test123/cleanup/approve")
    assert response.status_code == 200
    mock_session_manager.approve_cleanup_plan.assert_called_once_with("test123")


# =============================================================================
# Routing Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_routing_plan_not_found(client, mock_session_manager, mock_session):
    """Test getting routing plan when none exists."""
    mock_session.routing_plan = None
    response = await client.get("/api/sessions/test123/plan")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_select_destination(client, mock_session_manager, mock_session):
    """Test selecting a destination for a block."""
    response = await client.post(
        "/api/sessions/test123/plan/select/block_001",
        json={"option_index": 0}
    )
    assert response.status_code == 200
    mock_session_manager.select_destination.assert_called_once()


@pytest.mark.asyncio
async def test_approve_plan(client, mock_session_manager, mock_session):
    """Test approving routing plan."""
    response = await client.post("/api/sessions/test123/plan/approve")
    assert response.status_code == 200
    mock_session_manager.approve_plan.assert_called_once_with("test123")


# =============================================================================
# Content Mode Tests
# =============================================================================


@pytest.mark.asyncio
async def test_set_content_mode(client, mock_session_manager, mock_session):
    """Test setting content mode."""
    response = await client.post(
        "/api/sessions/test123/mode",
        json={"mode": "refinement"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_set_content_mode_invalid(client, mock_session_manager, mock_session):
    """Test invalid content mode."""
    response = await client.post(
        "/api/sessions/test123/mode",
        json={"mode": "invalid"}
    )
    assert response.status_code == 400


# =============================================================================
# Library Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_library_structure(client, mock_library_scanner):
    """Test getting library structure."""
    response = await client.get("/api/library")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert data["total_files"] == 1


@pytest.mark.asyncio
async def test_get_categories(client, mock_library_scanner):
    """Test getting categories."""
    response = await client.get("/api/library/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "tech"


@pytest.mark.asyncio
async def test_get_file(client, mock_library_scanner):
    """Test getting file metadata."""
    response = await client.get("/api/library/files/tech/auth.md")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Authentication"


@pytest.mark.asyncio
async def test_get_file_not_found(client, mock_library_scanner):
    """Test getting non-existent file."""
    mock_library_scanner.get_file = AsyncMock(return_value=None)
    response = await client.get("/api/library/files/nonexistent.md")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_library(client, mock_library_scanner):
    """Test library search."""
    response = await client.get("/api/library/search?query=oauth")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "oauth"
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_index_library(client, mock_semantic_search):
    """Test library indexing."""
    response = await client.post("/api/library/index")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "indexed"


# =============================================================================
# Query Tests
# =============================================================================


@pytest.mark.asyncio
async def test_semantic_search(client, mock_semantic_search):
    """Test semantic search."""
    response = await client.post(
        "/api/query/search",
        json={"query": "authentication", "n_results": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "authentication"


@pytest.mark.asyncio
async def test_ask_rag_query(client, mock_semantic_search):
    """Test ask endpoint with RAG query engine."""
    response = await client.post(
        "/api/query/ask",
        json={"question": "How does authentication work?"}
    )
    assert response.status_code == 200
    data = response.json()
    # With no search results, should get the "not found" message
    assert "couldn't find" in data["answer"].lower() or "answer" in data
    assert "confidence" in data
    assert "sources" in data


@pytest.mark.asyncio
async def test_ask_respects_max_sources(client_with_query_engine):
    """Ask endpoint respects max_sources."""
    response = await client_with_query_engine.post(
        "/api/query/ask",
        json={"question": "Explain tokens", "max_sources": 7},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["sources"]) == 7
