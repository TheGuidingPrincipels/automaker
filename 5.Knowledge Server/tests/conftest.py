"""
Pytest configuration and fixtures for all tests
"""

import contextlib
import tempfile
from pathlib import Path
from unittest.mock import Mock

from config import reset_settings, get_settings
from config.testing import override_settings
from services.container import (
    ServiceContainer,
    get_container,
    set_container,
    reset_container,
)


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config singleton before each test to ensure clean state."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture(autouse=True)
def reset_service_container():
    """Reset service container before and after each test for isolation.

    This autouse fixture ensures that no service state leaks between tests,
    preventing cross-test pollution when using the ServiceContainer pattern.
    """
    reset_container()
    yield
    reset_container()


@pytest.fixture
def mock_container():
    """Provide a ServiceContainer with mocked services.

    All services are replaced with Mock objects for pure unit testing.
    Does not affect the global container - use configured_container for that.

    Example:
        def test_something(mock_container):
            mock_container.neo4j_service.execute_read.return_value = [...]
            result = some_function(container=mock_container)
    """
    container = ServiceContainer()
    container.event_store = Mock()
    container.outbox = Mock()
    container.neo4j_service = Mock()
    container.chromadb_service = Mock()
    container.embedding_service = Mock()
    container.repository = Mock()
    container.confidence_runtime = Mock()
    container.confidence_runtime.calculator = Mock()
    return container


@pytest.fixture
def configured_container(mock_container):
    """Set up a mock container as the global container.

    This fixture sets the mocked container as the global singleton,
    so code using get_container() will receive the mocked version.

    Example:
        def test_integration(configured_container):
            configured_container.neo4j_service.execute_read.return_value = [...]
            # Code using get_container() will get the mocked container
            result = await some_tool_function()
    """
    set_container(mock_container)
    return mock_container


@pytest.fixture
def test_settings():
    """Provide isolated test settings."""
    return get_settings()

import pytest
import redis.asyncio as redis


@pytest.fixture
def temp_event_db():
    """Create a temporary event store database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize the database schema
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create events table
    cursor.execute(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            aggregate_type TEXT NOT NULL,
            event_data TEXT NOT NULL,
            metadata TEXT,
            version INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create indexes
    cursor.execute("CREATE INDEX idx_aggregate ON events(aggregate_id, version)")
    cursor.execute("CREATE INDEX idx_created_at ON events(created_at)")
    cursor.execute("CREATE INDEX idx_event_type ON events(event_type)")

    # Create outbox table
    cursor.execute(
        """
        CREATE TABLE outbox (
            outbox_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            projection_name TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_attempt DATETIME,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create indexes for outbox
    cursor.execute("CREATE INDEX idx_status ON outbox(status, projection_name)")
    cursor.execute("CREATE INDEX idx_event ON outbox(event_id)")

    # Create consistency_snapshots table
    cursor.execute(
        """
        CREATE TABLE consistency_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            neo4j_count INTEGER,
            chromadb_count INTEGER,
            discrepancies TEXT,
            checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    """
    )

    cursor.execute("CREATE INDEX idx_checked_at ON consistency_snapshots(checked_at)")

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_concept_data():
    """Sample concept data for testing"""
    return {
        "name": "Test Concept",
        "explanation": "This is a test concept for unit testing",
        "area": "Testing",
        "topic": "Unit Tests",
        "subtopic": "Fixtures",
        "confidence_score": 95
    }


@pytest.fixture
def temp_chroma_dir():
    """Create a temporary ChromaDB directory for testing"""
    import shutil

    temp_dir = tempfile.mkdtemp(prefix="chroma_test_")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def chromadb_service(temp_chroma_dir):
    """Create a ChromaDB service instance for testing"""
    from services.chromadb_service import ChromaDbConfig, ChromaDbService

    config = ChromaDbConfig(
        persist_directory=temp_chroma_dir,
        collection_name="test_concepts",
    )

    service = ChromaDbService(config=config)
    service.connect()

    yield service

    # Cleanup
    service.close()


# Shared Redis fixture for integration tests
@pytest.fixture
async def redis_client():
    """Provide a real Redis client for integration tests, or skip if unavailable.

    Uses DB 15 to avoid collision with any developer/local data. Cleans up
    the database after each test.
    """
    try:
        client = redis.Redis(
            host="localhost",
            port=6379,
            db=15,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await client.ping()
        yield client
        # Cleanup and close
        with contextlib.suppress(Exception):
            await client.flushdb()
        await client.close()
    except (redis.ConnectionError, redis.TimeoutError) as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.fixture(autouse=True)
def reset_repository_cache():
    """Clear version cache between tests for isolation.

    This ensures no stale cache data leaks between tests when
    using shared repository instances.
    """
    yield
    # Clear cache if repository exists in concept_tools
    try:
        from tools import concept_tools
        if hasattr(concept_tools, 'repository') and concept_tools.repository:
            concept_tools.repository._version_cache.clear()
    except (ImportError, AttributeError):
        pass
