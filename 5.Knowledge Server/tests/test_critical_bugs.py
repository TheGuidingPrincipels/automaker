"""
Tests that expose critical bugs found during debugging
"""

import contextlib
import sqlite3
from datetime import UTC, datetime

import pytest

from models.events import Event
from services.event_store import EventStore
from services.outbox import Outbox


class TestCriticalBugs:
    """Critical bugs discovered during stress testing"""

    def test_bug_1_metadata_empty_dict_becomes_none(self, temp_event_db):
        """
        BUG: Empty metadata dict is stored as None instead of empty dict

        When metadata={} is passed, it gets serialized to None in the database,
        causing data loss and inconsistency.
        """
        store = EventStore(temp_event_db)

        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            metadata={},  # Empty dict
            version=1,
        )

        store.append_event(event)
        retrieved = store.get_event_by_id(event.event_id)

        # BUG: Expected {} but got None
        print(f"Original metadata: {event.metadata}")
        print(f"Retrieved metadata: {retrieved.metadata}")
        assert retrieved.metadata == {}, f"Expected {{}}, got {retrieved.metadata}"

    def test_bug_2_nonexistent_path_creates_readonly_dirs(self, temp_event_db):
        """
        BUG: EventStore tries to create directories in read-only locations

        When initialized with invalid path, it tries to create parent directories
        even in read-only locations like /nonexistent, causing OSError
        """
        # This should fail gracefully when operations are attempted, not crash during init
        store = EventStore("/nonexistent/path/db.db")

        event = Event(
            event_type="Test",
            aggregate_id="test-invalid-path",
            aggregate_type="Test",
            event_data={},
            version=1,
        )

        with pytest.raises(Exception):
            store.append_event(event)

    def test_bug_3_pydantic_allows_non_serializable_objects(self, temp_event_db):
        """
        BUG: Pydantic allows non-JSON-serializable objects in event_data

        Event model accepts objects that cannot be JSON serialized,
        which will cause failures later during to_db_dict() or to_json()
        """

        class NonSerializable:
            def __init__(self):
                self.value = "test"

        # Event creation should now reject non-serializable payloads outright
        with pytest.raises(ValueError):
            Event(
                event_type="Test",
                aggregate_id="test-1",
                aggregate_type="Test",
                event_data={"obj": NonSerializable()},
                version=1,
            )

    def test_bug_4_connection_not_closed_on_error(self, temp_event_db):
        """
        BUG: Database connections may leak on exceptions

        Test that connections are properly closed even when errors occur
        """
        store = EventStore(temp_event_db)

        # Cause an error during append
        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=1,
        )

        # First append should succeed
        store.append_event(event)

        # Second append with same ID should fail
        with contextlib.suppress(Exception):
            store.append_event(event)

        # But we should still be able to use the store
        event2 = Event(
            event_type="Test",
            aggregate_id="test-2",
            aggregate_type="Test",
            event_data={},
            version=1,
        )

        # This should work if connections are properly closed
        result = store.append_event(event2)
        assert result is True

    def test_bug_5_sql_injection_vulnerability(self, temp_event_db):
        """
        SECURITY: Test for SQL injection vulnerabilities

        Ensure that user input in queries is properly parameterized
        """
        store = EventStore(temp_event_db)

        # Try SQL injection in aggregate_id
        malicious_id = "'; DROP TABLE events; --"

        event = Event(
            event_type="Test",
            aggregate_id=malicious_id,
            aggregate_type="Test",
            event_data={},
            version=1,
        )

        store.append_event(event)

        # Try to retrieve with malicious input
        events = store.get_events_by_aggregate(malicious_id)

        # Should return the event, not execute SQL
        assert len(events) == 1

        # Verify table still exists
        conn = sqlite3.connect(temp_event_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        conn.close()

        assert count >= 1, "Table should still exist"

    def test_bug_6_null_byte_handling(self, temp_event_db):
        """
        BUG: Null bytes in strings may cause issues

        SQLite and Python handle null bytes differently
        """
        store = EventStore(temp_event_db)

        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={"data": "before\x00after"},
            version=1,
        )

        result = store.append_event(event)
        assert result is True

        retrieved = store.get_event_by_id(event.event_id)
        # Null bytes may be stripped or preserved
        print(f"Original: {event.event_data['data']!r}")
        print(f"Retrieved: {retrieved.event_data['data']!r}")

    def test_bug_7_invalid_limit_offset_values(self, temp_event_db):
        """
        BUG: Negative or invalid limit/offset values not handled

        get_all_events with negative values may cause unexpected behavior
        """
        store = EventStore(temp_event_db)

        # Add some events
        for i in range(5):
            event = Event(
                event_type="Test",
                aggregate_id=f"test-{i}",
                aggregate_type="Test",
                event_data={},
                version=1,
            )
            store.append_event(event)

        # Try with negative limit
        events = store.get_all_events(limit=-1)
        print(f"Events with limit=-1: {len(events)}")

        # Try with negative offset
        events = store.get_all_events(offset=-5)
        print(f"Events with offset=-5: {len(events)}")

        # Try with None values
        events = store.get_all_events(limit=None, offset=None)
        assert len(events) == 5

    def test_bug_8_corrupted_json_in_database(self, temp_event_db):
        """
        BUG: Corrupted JSON in database causes entire query to fail

        If one row has corrupted JSON, all events in the query fail
        """
        store = EventStore(temp_event_db)

        # Add a valid event
        event1 = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={"valid": "data"},
            version=1,
        )
        store.append_event(event1)

        # Manually corrupt the database
        conn = sqlite3.connect(temp_event_db)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO events
               (event_id, event_type, aggregate_id, aggregate_type,
                event_data, metadata, version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "corrupt-1",
                "Test",
                "test-2",
                "Test",
                "{invalid json}}",
                None,
                1,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        # Try to get all events - should handle corruption gracefully
        events = store.get_all_events()
        print(f"Retrieved {len(events)} events (1 valid, 1 corrupted)")

        # Should either skip corrupted or return error, but not crash
        assert isinstance(events, list)

    def test_bug_9_concurrent_version_check_race_condition(self, temp_event_db):
        """
        BUG: Race condition in version checking allows duplicate versions

        Two threads can both check version and append at the same time
        """
        import threading

        store = EventStore(temp_event_db)

        aggregate_id = "race-test"
        results = []

        def append_version_1():
            event = Event(
                event_type="Test",
                aggregate_id=aggregate_id,
                aggregate_type="Test",
                event_data={"thread": "A"},
                version=1,
            )
            try:
                store.append_event(event)
                results.append("A-success")
            except Exception as e:
                results.append(f"A-error: {type(e).__name__}")

        def append_version_1_concurrent():
            event = Event(
                event_type="Test",
                aggregate_id=aggregate_id,
                aggregate_type="Test",
                event_data={"thread": "B"},
                version=1,
            )
            try:
                store.append_event(event)
                results.append("B-success")
            except Exception as e:
                results.append(f"B-error: {type(e).__name__}")

        # Start both threads simultaneously
        t1 = threading.Thread(target=append_version_1)
        t2 = threading.Thread(target=append_version_1_concurrent)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        print(f"Results: {results}")

        # Only one should succeed
        sum(1 for r in results if "success" in r)

        # Verify database has only one event with version 1
        events = store.get_events_by_aggregate(aggregate_id)
        versions = [e.version for e in events]

        print(f"Events in DB: {len(events)}, versions: {versions}")

        # Should have exactly one version 1
        assert versions.count(1) == 1, f"Expected 1 version-1 event, got {versions.count(1)}"

    def test_bug_10_outbox_missing_foreign_key_validation(self, temp_event_db):
        """
        BUG: Outbox allows adding non-existent event_id

        Foreign key constraint in schema not enforced at application level
        """
        outbox = Outbox(temp_event_db)

        # Try to add non-existent event to outbox
        # This should fail or at least warn
        try:
            outbox_id = outbox.add_to_outbox("nonexistent-event-id", "neo4j")
            print(f"Added non-existent event to outbox: {outbox_id}")

            # If it succeeds, we have a bug - referential integrity not enforced
            # This is a MINOR bug if SQLite doesn't enforce FK by default
        except Exception as e:
            print(f"Correctly prevented invalid FK: {e}")

    def test_bug_11_datetime_timezone_handling(self, temp_event_db):
        """
        BUG: Timezone information lost in datetime handling

        created_at uses datetime.now() which is timezone-naive
        """

        store = EventStore(temp_event_db)

        # Create event with timezone-aware datetime
        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=1,
            created_at=datetime.now(UTC),
        )

        store.append_event(event)
        retrieved = store.get_event_by_id(event.event_id)

        print(f"Original: {event.created_at}, TZ: {event.created_at.tzinfo}")
        print(f"Retrieved: {retrieved.created_at}, TZ: {retrieved.created_at.tzinfo}")

        # Timezone info may be lost


class TestPerformanceIssues:
    """Performance bottlenecks and inefficiencies"""

    def test_perf_1_no_database_connection_pooling(self, temp_event_db):
        """
        PERFORMANCE: New connection created for every operation

        Each method call creates a new connection, no pooling
        """
        import time

        store = EventStore(temp_event_db)

        # Measure time for 100 operations
        start = time.time()
        for i in range(100):
            event = Event(
                event_type="PerfTest",
                aggregate_id=f"perf-{i}",
                aggregate_type="Test",
                event_data={},
                version=1,
            )
            store.append_event(event)
        elapsed = time.time() - start

        print(f"100 inserts took {elapsed:.2f}s ({elapsed/100*1000:.1f}ms per insert)")

        # Connection overhead is significant without pooling

    def test_perf_2_no_batch_insert_support(self, temp_event_db):
        """
        PERFORMANCE: No support for batch inserts

        Must insert events one at a time
        """
        store = EventStore(temp_event_db)

        # Would be much faster with batch insert
        events = [
            Event(
                event_type="BatchTest",
                aggregate_id=f"batch-{i}",
                aggregate_type="Test",
                event_data={},
                version=1,
            )
            for i in range(100)
        ]

        import time

        start = time.time()
        for event in events:
            store.append_event(event)
        elapsed = time.time() - start

        print(f"Sequential insert: {elapsed:.2f}s")
        print("No batch insert method available")

    def test_perf_3_inefficient_max_version_query(self, temp_event_db):
        """
        PERFORMANCE: Version check queries MAX version every time

        Could be optimized with caching or index
        """
        store = EventStore(temp_event_db)
        aggregate_id = "perf-agg"

        # Create 100 events for same aggregate
        import time

        start = time.time()
        for i in range(1, 101):
            event = Event(
                event_type="Test",
                aggregate_id=aggregate_id,
                aggregate_type="Test",
                event_data={},
                version=i,
            )
            store.append_event(event)
        elapsed = time.time() - start

        print(f"100 versioned inserts: {elapsed:.2f}s ({elapsed/100*1000:.1f}ms each)")
        print("Each insert queries MAX(version) - could be optimized")
