"""
Integration tests for MCP Knowledge Server

Tests end-to-end workflows and component interactions
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from config import Config
from models.events import ConceptCreated, ConceptDeleted, ConceptUpdated
from services.event_store import EventStore
from services.outbox import Outbox


@pytest.fixture
def integration_db():
    """Create a temporary database for integration testing"""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize the database schema
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


def test_end_to_end_concept_workflow(integration_db):
    """
    Test complete concept creation workflow:
    Create event → Store → Outbox → Verify DB state
    """
    # Initialize services
    event_store = EventStore(integration_db)
    outbox = Outbox(integration_db)

    # Step 1: Create concept event
    concept_data = {
        "name": "Test Concept",
        "explanation": "Integration test concept",
        "area": "Testing",
        "topic": "Integration Tests",
        "subtopic": "Workflows",
        "confidence_score": 95
    }
    event = ConceptCreated(
        aggregate_id="concept_integration_001", concept_data=concept_data, version=1
    )

    # Step 2: Append to event store
    result = event_store.append_event(event)
    assert result is True

    # Step 3: Add to outbox for both projections
    neo4j_outbox_id = outbox.add_to_outbox(event.event_id, "neo4j")
    chroma_outbox_id = outbox.add_to_outbox(event.event_id, "chromadb")

    assert neo4j_outbox_id is not None
    assert chroma_outbox_id is not None

    # Step 4: Verify event stored correctly
    stored_event = event_store.get_event_by_id(event.event_id)
    assert stored_event is not None
    assert stored_event.event_type == "ConceptCreated"
    assert stored_event.aggregate_id == "concept_integration_001"
    assert stored_event.version == 1

    # Step 5: Verify outbox entries
    pending = outbox.get_pending()
    assert len(pending) == 2
    assert all(item.status == "pending" for item in pending)

    # Step 6: Simulate processing
    outbox.mark_processing(neo4j_outbox_id)
    outbox.mark_processed(neo4j_outbox_id)
    outbox.mark_processing(chroma_outbox_id)
    outbox.mark_processed(chroma_outbox_id)

    # Step 7: Verify all processed
    pending_after = outbox.get_pending()
    assert len(pending_after) == 0

    counts = outbox.count_by_status()
    assert counts.get("completed", 0) == 2


def test_multi_event_versioning(integration_db):
    """
    Test event versioning across multiple events:
    Create → Update → Update → Delete
    """
    event_store = EventStore(integration_db)
    aggregate_id = "concept_versioning_001"

    # Event 1: Create
    create_event = ConceptCreated(
        aggregate_id=aggregate_id,
        concept_data={"name": "Original Name", "confidence_score": 80},
        version=1
    )
    event_store.append_event(create_event)

    # Event 2: First update
    update_event_1 = ConceptUpdated(
        aggregate_id=aggregate_id,
        updates={"name": "Updated Name", "confidence_score": 85},
        version=2
    )
    event_store.append_event(update_event_1)

    # Event 3: Second update
    update_event_2 = ConceptUpdated(
        aggregate_id=aggregate_id,
        updates={"confidence_score": 90},
        version=3
    )
    event_store.append_event(update_event_2)

    # Event 4: Delete
    delete_event = ConceptDeleted(aggregate_id=aggregate_id, version=4)
    event_store.append_event(delete_event)

    # Verify all events stored
    events = event_store.get_events_by_aggregate(aggregate_id)
    assert len(events) == 4
    assert [e.version for e in events] == [1, 2, 3, 4]
    assert [e.event_type for e in events] == [
        "ConceptCreated",
        "ConceptUpdated",
        "ConceptUpdated",
        "ConceptDeleted",
    ]

    # Verify latest version
    latest_version = event_store.get_latest_version(aggregate_id)
    assert latest_version == 4

    # Verify get events from version 2
    events_from_v2 = event_store.get_events_by_aggregate(aggregate_id, from_version=2)
    assert len(events_from_v2) == 3
    assert all(e.version >= 2 for e in events_from_v2)


def test_outbox_retry_workflow(integration_db):
    """
    Test outbox retry workflow:
    Create event → Fail → Retry → Fail → Retry → Fail → Mark as failed
    """
    event_store = EventStore(integration_db)
    outbox = Outbox(integration_db)

    # Create event
    event = ConceptCreated(
        aggregate_id="concept_retry_001", concept_data={"name": "Retry Test"}, version=1
    )
    event_store.append_event(event)

    # Add to outbox
    outbox_id = outbox.add_to_outbox(event.event_id, "neo4j")

    # Simulate 3 failures
    for i in range(Outbox.MAX_ATTEMPTS):
        # Get pending (should still be there)
        pending = outbox.get_pending()
        if i < Outbox.MAX_ATTEMPTS:
            assert len(pending) == 1

        # Mark as failed
        outbox.mark_failed(outbox_id, f"Test failure {i+1}")

    # After 3 failures, should be marked as failed and not pending
    pending_final = outbox.get_pending()
    assert len(pending_final) == 0

    failed_items = outbox.get_failed_items()
    assert len(failed_items) == 1
    assert failed_items[0].outbox_id == outbox_id
    assert failed_items[0].attempts == Outbox.MAX_ATTEMPTS
    assert failed_items[0].status == "failed"

    # Test retry functionality
    result = outbox.retry_failed(outbox_id)
    assert result is True

    # Should be back in pending
    pending_after_retry = outbox.get_pending()
    assert len(pending_after_retry) == 1
    assert pending_after_retry[0].attempts == 0


def test_server_lifecycle(integration_db):
    """
    Test server initialization and shutdown
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from mcp_server import initialize

    # Test initialization (skip if external dependencies unavailable)
    try:
        asyncio.run(initialize())
    except RuntimeError as exc:
        if "Neo4j" in str(exc):
            pytest.skip("Neo4j service unavailable; skipping server lifecycle test")
        raise

    # Verify services are initialized
    from mcp_server import event_store, outbox

    assert event_store is not None
    assert outbox is not None

    # Note: Actual MCP server lifecycle testing would require
    # running the server, which is beyond unit/integration tests


def test_configuration_loading():
    """
    Test configuration loading and defaults
    """
    # Test default values
    assert Config.MCP_SERVER_NAME == "knowledge-server"
    assert Config.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]
    assert Config.NEO4J_URI.startswith("bolt://")
    assert Config.EVENT_STORE_PATH.endswith(".db")

    # Test paths are strings
    assert isinstance(Config.CHROMA_PERSIST_DIRECTORY, str)
    assert isinstance(Config.EMBEDDING_MODEL, str)


def test_event_serialization(integration_db):
    """
    Test event serialization and deserialization
    """
    event_store = EventStore(integration_db)

    # Create event with complex data
    concept_data = {
        "name": "Serialization Test",
        "explanation": "Testing JSON serialization",
        "area": "Testing",
        "topic": "Serialization",
        "subtopic": "JSON",
        "confidence_score": 95,
        "metadata": {
            "author": "Test Suite",
            "tags": ["test", "integration"]
        }
    }

    event = ConceptCreated(aggregate_id="concept_serial_001", concept_data=concept_data, version=1)

    # Store and retrieve
    event_store.append_event(event)
    retrieved = event_store.get_event_by_id(event.event_id)

    # Verify all data preserved
    assert retrieved.event_data == concept_data
    assert retrieved.event_data["metadata"]["tags"] == ["test", "integration"]
    assert retrieved.created_at.year == datetime.now().year


def test_concurrent_outbox_processing(integration_db):
    """
    Test multiple projections processing simultaneously
    """
    event_store = EventStore(integration_db)
    outbox = Outbox(integration_db)

    # Create 5 events
    for i in range(5):
        event = ConceptCreated(
            aggregate_id=f"concept_concurrent_{i}", concept_data={"name": f"Concept {i}"}, version=1
        )
        event_store.append_event(event)

        # Add to both projections
        outbox.add_to_outbox(event.event_id, "neo4j")
        outbox.add_to_outbox(event.event_id, "chromadb")

    # Verify 10 pending items (5 events x 2 projections)
    pending = outbox.get_pending()
    assert len(pending) == 10

    # Get pending for specific projection
    neo4j_pending = outbox.get_pending(projection_name="neo4j")
    chroma_pending = outbox.get_pending(projection_name="chromadb")

    assert len(neo4j_pending) == 5
    assert len(chroma_pending) == 5

    # Process neo4j items
    for item in neo4j_pending:
        outbox.mark_processing(item.outbox_id)
        outbox.mark_processed(item.outbox_id)

    # Verify only chromadb items remain
    remaining = outbox.get_pending()
    assert len(remaining) == 5
    assert all(item.projection_name == "chromadb" for item in remaining)


def test_event_query_filtering(integration_db):
    """
    Test event store filtering and pagination
    """
    event_store = EventStore(integration_db)

    # Create 10 concept events
    for i in range(10):
        event = ConceptCreated(
            aggregate_id=f"concept_filter_{i}", concept_data={"name": f"Concept {i}"}, version=1
        )
        event_store.append_event(event)

    # Create 5 relationship events
    from models.events import RelationshipCreated

    for i in range(5):
        event = RelationshipCreated(
            aggregate_id=f"rel_filter_{i}",
            relationship_data={"from": f"concept_{i}", "to": f"concept_{i+1}"},
            version=1,
        )
        event_store.append_event(event)

    # Test get all events
    all_events = event_store.get_all_events()
    assert len(all_events) == 15

    # Test filter by type
    concept_events = event_store.get_all_events(event_type="ConceptCreated")
    assert len(concept_events) == 10

    relationship_events = event_store.get_all_events(event_type="RelationshipCreated")
    assert len(relationship_events) == 5

    # Test pagination
    page_1 = event_store.get_all_events(limit=5)
    assert len(page_1) == 5

    page_2 = event_store.get_all_events(limit=5, offset=5)
    assert len(page_2) == 5

    # Verify no overlap
    page_1_ids = {e.event_id for e in page_1}
    page_2_ids = {e.event_id for e in page_2}
    assert len(page_1_ids & page_2_ids) == 0


def test_error_handling(integration_db):
    """
    Test error handling and edge cases
    """
    event_store = EventStore(integration_db)
    Outbox(integration_db)

    # Test duplicate event error
    event = ConceptCreated(
        aggregate_id="concept_error_001", concept_data={"name": "Error Test"}, version=1
    )
    event_store.append_event(event)

    from services.event_store import DuplicateEventError

    with pytest.raises(DuplicateEventError):
        event_store.append_event(event)

    # Test version conflict
    from services.event_store import VersionConflictError

    conflict_event = ConceptUpdated(
        aggregate_id="concept_error_001",
        updates={"name": "Updated"},
        version=5,  # Wrong version (should be 2)
    )
    with pytest.raises(VersionConflictError):
        event_store.append_event(conflict_event)

    # Test getting non-existent event
    result = event_store.get_event_by_id("non-existent-id")
    assert result is None

    # Test getting events for non-existent aggregate
    events = event_store.get_events_by_aggregate("non-existent-aggregate")
    assert len(events) == 0

    # Test count for non-existent type
    count = event_store.count_events(event_type="NonExistentType")
    assert count == 0
