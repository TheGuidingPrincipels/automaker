"""
Pytest fixtures for end-to-end integration tests.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from projections.chromadb_projection import ChromaDBProjection
from projections.neo4j_projection import Neo4jProjection
from services.chromadb_service import ChromaDbService
from services.compensation import CompensationManager
from services.embedding_cache import EmbeddingCache
from services.embedding_service import EmbeddingService
from services.event_store import EventStore
from services.neo4j_service import Neo4jService
from services.outbox import Outbox
from services.repository import DualStorageRepository


@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for test databases."""
    temp_path = tempfile.mkdtemp(prefix="e2e_test_")
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def mock_neo4j():
    """Create a mock Neo4j service for E2E tests."""
    mock = Mock(spec=Neo4jService)

    # Mock common responses
    mock.execute_read.return_value = []
    mock.execute_write.return_value = {"nodes_created": 1}
    mock.is_connected.return_value = True

    return mock


@pytest.fixture(scope="function")
def mock_chromadb():
    """Create a mock ChromaDB service for E2E tests."""
    mock = Mock(spec=ChromaDbService)

    # Mock collection with all required methods
    mock_collection = Mock()
    mock_collection.count.return_value = 0
    mock_collection.add.return_value = None
    mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
    mock_collection.update.return_value = None
    mock_collection.delete.return_value = None
    # Default empty query result
    mock_collection.query = Mock(
        return_value={"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
    )

    mock.collection = mock_collection
    mock.get_collection.return_value = mock_collection
    mock.health_check.return_value = True

    return mock


@pytest.fixture(scope="function")
def mock_embedding_service():
    """Create a mock embedding service for E2E tests."""
    mock = Mock(spec=EmbeddingService)

    # Mock config
    mock_config = Mock()
    mock_config.model_name = "all-MiniLM-L6-v2"
    mock.config = mock_config

    # Mock embedding generation (384-dimensional zero vector)
    mock.generate_embedding.return_value = [0.0] * 384
    mock.generate_batch.return_value = [[0.0] * 384]
    mock.is_ready = lambda: True
    mock.health_check.return_value = True

    return mock


@pytest.fixture(scope="function")
def e2e_event_store(temp_dir):
    """Create a real EventStore for E2E tests."""
    import sqlite3

    db_path = Path(temp_dir) / "events.db"

    # Initialize database tables with correct schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create events table (matching EventStore expected schema)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
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

    # Create outbox table (matching Outbox expected schema)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox (
            outbox_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            projection_name TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_attempt DATETIME,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id)
        )
    """
    )

    conn.commit()
    conn.close()

    return EventStore(str(db_path))


@pytest.fixture(scope="function")
def e2e_outbox(temp_dir):
    """Create a real Outbox for E2E tests."""
    db_path = Path(temp_dir) / "events.db"
    return Outbox(str(db_path))


@pytest.fixture(scope="function")
def e2e_embedding_cache(temp_dir):
    """Create a real EmbeddingCache for E2E tests."""
    import sqlite3

    cache_path = Path(temp_dir) / "embeddings.db"

    # Initialize embeddings cache table
    conn = sqlite3.connect(str(cache_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            text_hash TEXT NOT NULL,
            model_name TEXT NOT NULL,
            embedding TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (text_hash, model_name)
        )
    """
    )

    conn.commit()
    conn.close()

    return EmbeddingCache(str(cache_path))


@pytest.fixture(scope="function")
def e2e_repository(
    mock_neo4j,
    mock_chromadb,
    mock_embedding_service,
    e2e_event_store,
    e2e_outbox,
    e2e_embedding_cache,
):
    """Create a DualStorageRepository for E2E tests with mock databases."""
    # Create projections with mock services
    neo4j_projection = Neo4jProjection(neo4j_service=mock_neo4j)
    chromadb_projection = ChromaDBProjection(chromadb_service=mock_chromadb)

    return DualStorageRepository(
        event_store=e2e_event_store,
        outbox=e2e_outbox,
        neo4j_projection=neo4j_projection,
        chromadb_projection=chromadb_projection,
        embedding_service=mock_embedding_service,
        embedding_cache=e2e_embedding_cache,
    )


@pytest.fixture(scope="function")
def e2e_compensation(mock_neo4j, mock_chromadb, temp_dir):
    """Create a CompensationManager for E2E tests."""
    db_path = Path(temp_dir) / "events.db"
    return CompensationManager(
        neo4j_service=mock_neo4j, chromadb_service=mock_chromadb, db_path=str(db_path)
    )


@pytest.fixture(scope="function")
def e2e_configured_container(
    mock_neo4j,
    mock_chromadb,
    mock_embedding_service,
    e2e_event_store,
    e2e_outbox,
    e2e_repository
):
    """Set up a container with real E2E services as the global container.

    This fixture combines real event sourcing services (event_store, outbox,
    repository) with mock database services (neo4j, chromadb, embedding) to
    provide a functional E2E testing environment.

    The container is registered globally via set_container() so that code
    using get_container() will receive these services.
    """
    from services.container import ServiceContainer, set_container

    container = ServiceContainer()
    container.event_store = e2e_event_store
    container.outbox = e2e_outbox
    container.neo4j_service = mock_neo4j
    container.chromadb_service = mock_chromadb
    container.embedding_service = mock_embedding_service
    container.repository = e2e_repository
    container.confidence_runtime = None  # E2E tests don't need confidence scoring

    set_container(container)
    return container


@pytest.fixture(scope="function")
def sample_concepts():
    """Sample concept data for E2E workflows."""
    return [
        {
            "name": "Python Basics",
            "explanation": "Fundamental Python syntax and concepts",
            "area": "Programming",
            "topic": "Python",
            "subtopic": "Fundamentals",
        },
        {
            "name": "Functions",
            "explanation": "Reusable code blocks in Python",
            "area": "Programming",
            "topic": "Python",
            "subtopic": "Functions",
        },
        {
            "name": "Classes",
            "explanation": "Object-oriented programming in Python",
            "area": "Programming",
            "topic": "Python",
            "subtopic": "OOP",
        },
        {
            "name": "Decorators",
            "explanation": "Function wrappers in Python",
            "area": "Programming",
            "topic": "Python",
            "subtopic": "Advanced",
        },
        {
            "name": "Generators",
            "explanation": "Lazy iterators in Python",
            "area": "Programming",
            "topic": "Python",
            "subtopic": "Advanced",
        },
    ]
