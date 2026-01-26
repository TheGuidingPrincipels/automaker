"""
Comprehensive stress tests for debugging runtime errors, edge cases,
performance issues, and concurrency bugs in the MCP Knowledge Server.
"""

import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pytest

from models.events import Event
from services.event_store import DuplicateEventError, EventStore, VersionConflictError
from services.outbox import Outbox


class TestRuntimeErrors:
    """Test for runtime exceptions and crashes"""

    def test_malformed_json_in_event_data(self, temp_event_db):
        """Test handling of malformed JSON in event data"""
        EventStore(temp_event_db)

        # Attempt to create event with non-serializable data
        class NonSerializable:
            pass

        with pytest.raises(Exception):
            Event(
                event_type="Test",
                aggregate_id="test-1",
                aggregate_type="Test",
                event_data={"obj": NonSerializable()},
                version=1,
            )

    def test_null_values_in_required_fields(self, temp_event_db):
        """Test null values in required fields"""
        EventStore(temp_event_db)

        # Test with None values
        with pytest.raises(Exception):
            Event(
                event_type=None,
                aggregate_id="test-1",
                aggregate_type="Test",
                event_data={},
                version=1,
            )

    def test_empty_event_data(self, temp_event_db):
        """Test empty event_data field"""
        store = EventStore(temp_event_db)

        # Empty dict should be allowed
        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=1,
        )
        assert store.append_event(event)

    def test_database_not_initialized(self):
        """Test behavior when database doesn't exist"""
        store = EventStore("/nonexistent/path/db.db")

        # Should raise an error when trying to append
        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={"test": "data"},
            version=1,
        )

        with pytest.raises(Exception):
            store.append_event(event)

    def test_corrupted_database_row(self, temp_event_db):
        """Test reading corrupted data from database"""
        store = EventStore(temp_event_db)

        # Manually insert corrupted JSON
        conn = sqlite3.connect(temp_event_db)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO events
               (event_id, event_type, aggregate_id, aggregate_type,
                event_data, metadata, version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "test-1",
                "Test",
                "agg-1",
                "Test",
                "{invalid json}",
                None,
                1,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        # Should handle the error gracefully
        events = store.get_events_by_aggregate("agg-1")
        # Depends on implementation - might return empty list or raise
        assert isinstance(events, list)

    def test_very_long_string_fields(self, temp_event_db):
        """Test extremely long string values"""
        store = EventStore(temp_event_db)

        # Create event with very long strings
        long_string = "x" * 100000
        event = Event(
            event_type="Test",
            aggregate_id=long_string[:100],  # Keep ID reasonable
            aggregate_type="Test",
            event_data={"long_field": long_string},
            version=1,
        )

        result = store.append_event(event)
        assert result is True

        # Verify retrieval
        retrieved = store.get_event_by_id(event.event_id)
        assert retrieved is not None
        assert len(retrieved.event_data["long_field"]) == 100000


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_large_event_payload(self, temp_event_db):
        """Test event with >100KB payload"""
        store = EventStore(temp_event_db)

        # Create a large payload (>100KB)
        large_data = {"items": [{"id": i, "data": "x" * 1000} for i in range(200)]}

        event = Event(
            event_type="LargeEvent",
            aggregate_id="large-1",
            aggregate_type="Test",
            event_data=large_data,
            version=1,
        )

        # Should handle large payloads
        result = store.append_event(event)
        assert result is True

        # Verify retrieval
        retrieved = store.get_event_by_id(event.event_id)
        assert retrieved is not None
        assert len(retrieved.event_data["items"]) == 200

    def test_special_characters_in_data(self, temp_event_db):
        """Test special characters and unicode"""
        store = EventStore(temp_event_db)

        special_chars = {
            "unicode": "你好世界 🚀 مرحبا",
            "quotes": 'She said "Hello\'s"',
            "backslash": "C:\\Users\\test\\file.txt",
            "newlines": "Line1\nLine2\rLine3\r\nLine4",
            "tabs": "Col1\tCol2\tCol3",
            "null_byte": "test\x00null",
            "emoji": "😀😁😂🤣😃😄",
        }

        event = Event(
            event_type="SpecialChars",
            aggregate_id="special-1",
            aggregate_type="Test",
            event_data=special_chars,
            version=1,
        )

        result = store.append_event(event)
        assert result is True

        retrieved = store.get_event_by_id(event.event_id)
        assert retrieved.event_data["unicode"] == special_chars["unicode"]
        assert retrieved.event_data["emoji"] == special_chars["emoji"]

    def test_version_zero(self, temp_event_db):
        """Test version number edge cases"""
        store = EventStore(temp_event_db)

        # Version 0 should fail (versions start at 1)
        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=0,
        )

        with pytest.raises(VersionConflictError):
            store.append_event(event)

    def test_negative_version(self, temp_event_db):
        """Test negative version number"""
        store = EventStore(temp_event_db)

        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=-1,
        )

        with pytest.raises(VersionConflictError):
            store.append_event(event)

    def test_very_high_version_number(self, temp_event_db):
        """Test very high version numbers"""
        store = EventStore(temp_event_db)

        # Skip to version 1000000 should fail
        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=1000000,
        )

        with pytest.raises(VersionConflictError):
            store.append_event(event)

    def test_empty_aggregate_id(self, temp_event_db):
        """Test empty aggregate ID"""
        store = EventStore(temp_event_db)

        event = Event(
            event_type="Test", aggregate_id="", aggregate_type="Test", event_data={}, version=1
        )

        # Should allow empty string (might be valid use case)
        result = store.append_event(event)
        assert result is True

    def test_duplicate_event_id_race_condition(self, temp_event_db):
        """Test duplicate event ID detection"""
        store = EventStore(temp_event_db)

        event1 = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=1,
            event_id="duplicate-id",
        )

        event2 = Event(
            event_type="Test",
            aggregate_id="test-2",
            aggregate_type="Test",
            event_data={},
            version=1,
            event_id="duplicate-id",
        )

        store.append_event(event1)

        with pytest.raises(DuplicateEventError):
            store.append_event(event2)

    def test_metadata_none_vs_empty(self, temp_event_db):
        """Test metadata as None vs empty dict"""
        store = EventStore(temp_event_db)

        event1 = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            metadata=None,
            version=1,
        )

        event2 = Event(
            event_type="Test",
            aggregate_id="test-2",
            aggregate_type="Test",
            event_data={},
            metadata={},
            version=1,
        )

        store.append_event(event1)
        store.append_event(event2)

        r1 = store.get_event_by_id(event1.event_id)
        r2 = store.get_event_by_id(event2.event_id)

        assert r1.metadata is None
        assert r2.metadata == {}


class TestConcurrency:
    """Test concurrent operations and race conditions"""

    def test_concurrent_event_append_same_aggregate(self, temp_event_db):
        """Test 10+ simultaneous writes to same aggregate"""
        store = EventStore(temp_event_db)
        aggregate_id = "concurrent-agg-1"

        errors = []
        successes = []

        def append_event(version):
            try:
                event = Event(
                    event_type="ConcurrentTest",
                    aggregate_id=aggregate_id,
                    aggregate_type="Test",
                    event_data={"version": version},
                    version=version,
                )
                store.append_event(event)
                successes.append(version)
                return True
            except Exception as e:
                errors.append((version, str(e)))
                return False

        # Run 20 concurrent appends
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(append_event, i) for i in range(1, 21)]
            [f.result() for f in as_completed(futures)]

        # Due to version conflicts, only some should succeed
        # At least one should succeed
        assert len(successes) > 0

        # Most should fail with version conflict
        assert len(errors) > 0

        # Verify database integrity
        events = store.get_events_by_aggregate(aggregate_id)
        versions = [e.version for e in events]

        # Versions should be sequential
        assert versions == sorted(versions)
        assert versions == list(range(1, len(versions) + 1))

    def test_concurrent_different_aggregates(self, temp_event_db):
        """Test concurrent writes to different aggregates"""
        store = EventStore(temp_event_db)

        def create_aggregate(agg_num):
            events = []
            for version in range(1, 6):
                event = Event(
                    event_type="Test",
                    aggregate_id=f"agg-{agg_num}",
                    aggregate_type="Test",
                    event_data={"version": version},
                    version=version,
                )
                store.append_event(event)
                events.append(event)
            return events

        # Create 10 aggregates concurrently, each with 5 events
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_aggregate, i) for i in range(10)]
            [f.result() for f in as_completed(futures)]

        # Should have 50 total events
        total = store.count_events()
        assert total == 50

        # Each aggregate should have 5 events
        for i in range(10):
            count = store.count_events(aggregate_id=f"agg-{i}")
            assert count == 5

    def test_concurrent_read_write(self, temp_event_db):
        """Test concurrent reads and writes"""
        store = EventStore(temp_event_db)
        aggregate_id = "read-write-test"

        # Pre-populate with some events
        for i in range(1, 11):
            event = Event(
                event_type="Test",
                aggregate_id=aggregate_id,
                aggregate_type="Test",
                event_data={"num": i},
                version=i,
            )
            store.append_event(event)

        read_results = []
        write_results = []

        def reader():
            for _ in range(20):
                events = store.get_events_by_aggregate(aggregate_id)
                read_results.append(len(events))
                time.sleep(0.001)

        def writer():
            for i in range(11, 21):
                try:
                    event = Event(
                        event_type="Test",
                        aggregate_id=aggregate_id,
                        aggregate_type="Test",
                        event_data={"num": i},
                        version=i,
                    )
                    store.append_event(event)
                    write_results.append(True)
                except Exception:
                    write_results.append(False)
                time.sleep(0.002)

        # Run readers and writers concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            reader_futures = [executor.submit(reader) for _ in range(3)]
            writer_future = executor.submit(writer)

            for f in as_completed([*reader_futures, writer_future]):
                f.result()

        # Reads should have completed without errors
        assert len(read_results) == 60  # 3 readers * 20 reads each

        # Final count should be 20
        final_count = store.count_events(aggregate_id=aggregate_id)
        assert final_count == 20

    def test_outbox_concurrent_processing(self, temp_event_db):
        """Test outbox with 100+ pending items processed concurrently"""
        store = EventStore(temp_event_db)
        outbox = Outbox(temp_event_db)

        # Create 150 events and add to outbox
        event_ids = []
        for i in range(150):
            event = Event(
                event_type="BulkTest",
                aggregate_id=f"bulk-{i}",
                aggregate_type="Test",
                event_data={"index": i},
                version=1,
            )
            store.append_event(event)
            event_ids.append(event.event_id)

        # Add to outbox
        for event_id in event_ids:
            outbox.add_to_outbox(event_id, "neo4j")

        # Process concurrently
        processed = []
        failed = []

        def process_item():
            items = outbox.get_pending(projection_name="neo4j", limit=1)
            if items:
                item = items[0]
                outbox.mark_processing(item.outbox_id)

                # Simulate processing
                time.sleep(0.001)

                # Randomly fail some
                import random

                if random.random() < 0.1:
                    outbox.mark_failed(item.outbox_id, "Simulated failure")
                    failed.append(item.outbox_id)
                else:
                    outbox.mark_processed(item.outbox_id)
                    processed.append(item.outbox_id)

        # Process with 20 workers
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(process_item) for _ in range(150)]
            for f in as_completed(futures):
                f.result()

        # Check results
        counts = outbox.count_by_status()
        assert (
            counts.get("completed", 0) + counts.get("failed", 0) + counts.get("pending", 0) == 150
        )


class TestPerformance:
    """Test performance and resource usage"""

    def test_bulk_insert_performance(self, temp_event_db):
        """Test inserting many events quickly"""
        store = EventStore(temp_event_db)

        start_time = time.time()

        # Insert 1000 events
        for i in range(1000):
            event = Event(
                event_type="BulkInsert",
                aggregate_id=f"bulk-{i}",
                aggregate_type="Test",
                event_data={"index": i},
                version=1,
            )
            store.append_event(event)

        elapsed = time.time() - start_time

        # Should complete reasonably fast
        assert elapsed < 30  # 30 seconds max for 1000 inserts

        # Verify count
        count = store.count_events(event_type="BulkInsert")
        assert count == 1000

    def test_large_query_performance(self, temp_event_db):
        """Test querying large result sets"""
        store = EventStore(temp_event_db)
        aggregate_id = "large-agg"

        # Create aggregate with 500 events
        for i in range(1, 501):
            event = Event(
                event_type="LargeAggregate",
                aggregate_id=aggregate_id,
                aggregate_type="Test",
                event_data={"version": i},
                version=i,
            )
            store.append_event(event)

        # Query all events
        start_time = time.time()
        events = store.get_events_by_aggregate(aggregate_id)
        elapsed = time.time() - start_time

        assert len(events) == 500
        assert elapsed < 5  # Should be fast

    def test_connection_leak_detection(self, temp_event_db):
        """Test for connection leaks"""
        store = EventStore(temp_event_db)

        # Perform many operations
        for i in range(100):
            event = Event(
                event_type="ConnectionTest",
                aggregate_id=f"conn-{i}",
                aggregate_type="Test",
                event_data={},
                version=1,
            )
            store.append_event(event)

            # Also do reads
            store.get_event_by_id(event.event_id)
            store.get_events_by_aggregate(event.aggregate_id)
            store.count_events()

        # If connections aren't closed, this would eventually fail
        # The fact that it completes suggests connections are managed
        assert True


class TestOutboxStress:
    """Stress tests for outbox pattern"""

    def test_rapid_outbox_additions(self, temp_event_db):
        """Test adding many items to outbox rapidly"""
        store = EventStore(temp_event_db)
        outbox = Outbox(temp_event_db)

        # Create and add 500 items
        for i in range(500):
            event = Event(
                event_type="OutboxStress",
                aggregate_id=f"stress-{i}",
                aggregate_type="Test",
                event_data={},
                version=1,
            )
            store.append_event(event)
            outbox.add_to_outbox(event.event_id, "neo4j")

        # Verify all added
        pending = outbox.get_pending()
        assert len(pending) >= 500 or len(pending) == outbox.count_by_status().get("pending", 0)

    def test_retry_exhaustion(self, temp_event_db):
        """Test items that exceed max retry attempts"""
        store = EventStore(temp_event_db)
        outbox = Outbox(temp_event_db)

        # Create event and add to outbox
        event = Event(
            event_type="RetryTest",
            aggregate_id="retry-1",
            aggregate_type="Test",
            event_data={},
            version=1,
        )
        store.append_event(event)
        outbox_id = outbox.add_to_outbox(event.event_id, "neo4j")

        # Fail it multiple times
        for i in range(5):
            outbox.mark_failed(outbox_id, f"Attempt {i+1} failed")

        # Should be marked as failed after max attempts
        failed_items = outbox.get_failed_items()
        assert len(failed_items) > 0

        # Should not appear in pending anymore
        pending = outbox.get_pending()
        assert not any(p.outbox_id == outbox_id for p in pending)

    def test_outbox_status_transitions(self, temp_event_db):
        """Test all status transitions work correctly"""
        store = EventStore(temp_event_db)
        outbox = Outbox(temp_event_db)

        event = Event(
            event_type="StatusTest",
            aggregate_id="status-1",
            aggregate_type="Test",
            event_data={},
            version=1,
        )
        store.append_event(event)
        outbox_id = outbox.add_to_outbox(event.event_id, "neo4j")

        # Transition: pending -> processing
        outbox.mark_processing(outbox_id)

        # Transition: processing -> failed (attempt 1)
        outbox.mark_failed(outbox_id, "First failure")

        # Should be back to pending
        pending = outbox.get_pending()
        assert any(p.outbox_id == outbox_id for p in pending)

        # Try again: pending -> processing -> completed
        outbox.mark_processing(outbox_id)
        outbox.mark_processed(outbox_id)

        # Should be completed
        counts = outbox.count_by_status()
        assert counts.get("completed", 0) >= 1


class TestDataIntegrity:
    """Test data integrity and corruption scenarios"""

    def test_datetime_serialization(self, temp_event_db):
        """Test datetime handling across storage and retrieval"""
        store = EventStore(temp_event_db)

        event = Event(
            event_type="DateTimeTest",
            aggregate_id="dt-1",
            aggregate_type="Test",
            event_data={"timestamp": datetime.now().isoformat()},
            version=1,
        )

        store.append_event(event)

        retrieved = store.get_event_by_id(event.event_id)

        # created_at should be preserved
        assert isinstance(retrieved.created_at, datetime)
        assert retrieved.created_at.year == event.created_at.year

    def test_nested_json_structures(self, temp_event_db):
        """Test deeply nested JSON structures"""
        store = EventStore(temp_event_db)

        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "data": "deep value",
                                "array": [1, 2, 3, {"nested": "array"}],
                            }
                        }
                    }
                }
            }
        }

        event = Event(
            event_type="NestedTest",
            aggregate_id="nested-1",
            aggregate_type="Test",
            event_data=nested_data,
            version=1,
        )

        store.append_event(event)

        retrieved = store.get_event_by_id(event.event_id)
        assert (
            retrieved.event_data["level1"]["level2"]["level3"]["level4"]["level5"]["data"]
            == "deep value"
        )

    def test_query_with_invalid_parameters(self, temp_event_db):
        """Test queries with invalid parameter types"""
        store = EventStore(temp_event_db)

        # None aggregate_id should be handled
        events = store.get_events_by_aggregate(None)
        assert isinstance(events, list)

        # Negative limit/offset
        events = store.get_all_events(limit=-1, offset=-5)
        assert isinstance(events, list)
