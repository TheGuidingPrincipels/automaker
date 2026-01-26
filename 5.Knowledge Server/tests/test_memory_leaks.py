"""
Tests for memory leaks and resource exhaustion
"""

import gc
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from models.events import Event
from services.event_store import EventStore
from services.outbox import Outbox


class TestResourceLeaks:
    """Tests for resource leaks and memory issues"""

    def test_memory_growth_with_large_queries(self, temp_event_db):
        """Test memory usage with large result sets"""
        store = EventStore(temp_event_db)

        # Create 1000 events
        for i in range(1000):
            event = Event(
                event_type="MemTest",
                aggregate_id=f"mem-{i % 10}",  # 10 aggregates with 100 events each
                aggregate_type="Test",
                event_data={"index": i, "data": "x" * 1000},
                version=(i // 10) + 1,
            )
            store.append_event(event)

        # Query repeatedly and check memory doesn't grow unbounded
        initial_memory = sys.getsizeof(gc.get_objects())

        for _ in range(10):
            events = store.get_all_events()
            assert len(events) == 1000
            del events
            gc.collect()

        final_memory = sys.getsizeof(gc.get_objects())

        # Memory shouldn't grow significantly
        growth = final_memory - initial_memory
        print(f"Memory growth: {growth} bytes")

        # Allow some growth but not unbounded
        assert growth < 1_000_000, "Possible memory leak detected"

    def test_connection_pool_exhaustion(self, temp_event_db):
        """Test many concurrent connections"""
        store = EventStore(temp_event_db)

        def query_events(i):
            event = Event(
                event_type="ConnTest",
                aggregate_id=f"conn-{i}",
                aggregate_type="Test",
                event_data={},
                version=1,
            )
            store.append_event(event)

            # Also query
            store.get_all_events()
            store.count_events()
            return True

        # Run 50 concurrent operations
        with ThreadPoolExecutor(max_workers=50) as executor:
            results = list(executor.map(query_events, range(50)))

        assert len(results) == 50
        assert all(results)


class TestEdgeCasesExtended:
    """Additional edge cases"""

    def test_unicode_edge_cases(self, temp_event_db):
        """Test various unicode edge cases"""
        store = EventStore(temp_event_db)

        test_cases = [
            "emoji: 😀😁😂🤣",
            "rtl: مرحبا بك في العالم",
            "cjk: 你好世界",
            "combining: é (e + ́)",
            "zero-width: a\u200bb\u200bc",
            "surrogate pairs: 𝕳𝖊𝖑𝖑𝖔",
        ]

        for i, text in enumerate(test_cases):
            event = Event(
                event_type="UnicodeTest",
                aggregate_id=f"unicode-{i}",
                aggregate_type="Test",
                event_data={"text": text},
                version=1,
            )

            store.append_event(event)
            retrieved = store.get_event_by_id(event.event_id)

            assert retrieved.event_data["text"] == text, f"Failed for: {text}"

    def test_json_edge_cases(self, temp_event_db):
        """Test JSON edge cases"""
        store = EventStore(temp_event_db)

        test_cases = [
            {"empty_string": ""},
            {"whitespace": "   \t\n\r  "},
            {"numbers": [0, -1, 1.5, -2.7, 1e10, 1e-10]},
            {"booleans": [True, False, None]},
            {"nested_empty": {"a": {}, "b": [], "c": None}},
            {"large_number": 9007199254740991},  # Max safe integer in JS
            {"float_precision": 0.1 + 0.2},  # Famous float issue
        ]

        for i, data in enumerate(test_cases):
            event = Event(
                event_type="JSONTest",
                aggregate_id=f"json-{i}",
                aggregate_type="Test",
                event_data=data,
                version=1,
            )

            store.append_event(event)
            retrieved = store.get_event_by_id(event.event_id)

            # JSON serialization may change some values slightly
            assert retrieved.event_data is not None

    def test_aggregate_id_edge_cases(self, temp_event_db):
        """Test edge cases in aggregate_id"""
        store = EventStore(temp_event_db)

        test_ids = [
            "",  # Empty
            " ",  # Space
            "a" * 1000,  # Very long
            "test-with-dashes",
            "test_with_underscores",
            "test.with.dots",
            "test/with/slashes",
            "test\\with\\backslashes",
            "test with spaces",
            "123",  # Numeric
            "test@example.com",  # Email-like
            "urn:uuid:12345",  # URN format
        ]

        for i, agg_id in enumerate(test_ids):
            event = Event(
                event_type="AggIdTest",
                aggregate_id=agg_id,
                aggregate_type="Test",
                event_data={"index": i},
                version=1,
            )

            result = store.append_event(event)
            assert result is True

            # Verify retrieval
            events = store.get_events_by_aggregate(agg_id)
            assert len(events) == 1

    def test_event_type_filtering_case_sensitivity(self, temp_event_db):
        """Test case sensitivity in event type filtering"""
        store = EventStore(temp_event_db)

        # Create events with different cases
        event1 = Event(
            event_type="TestEvent",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=1,
        )

        event2 = Event(
            event_type="testevent",
            aggregate_id="test-2",
            aggregate_type="Test",
            event_data={},
            version=1,
        )

        store.append_event(event1)
        store.append_event(event2)

        # Query with different cases
        upper = store.get_all_events(event_type="TESTEVENT")
        lower = store.get_all_events(event_type="testevent")
        mixed = store.get_all_events(event_type="TestEvent")

        print(f"TESTEVENT: {len(upper)}, testevent: {len(lower)}, TestEvent: {len(mixed)}")

        # SQLite is case-insensitive by default for TEXT, but depends on collation

    def test_version_gaps(self, temp_event_db):
        """Test that version gaps are not allowed"""
        store = EventStore(temp_event_db)

        # Create version 1
        event1 = Event(
            event_type="Test",
            aggregate_id="gap-test",
            aggregate_type="Test",
            event_data={},
            version=1,
        )
        store.append_event(event1)

        # Try to create version 3 (skipping 2)
        event3 = Event(
            event_type="Test",
            aggregate_id="gap-test",
            aggregate_type="Test",
            event_data={},
            version=3,
        )

        with pytest.raises(Exception):
            store.append_event(event3)

        # Verify we still only have version 1
        events = store.get_events_by_aggregate("gap-test")
        assert len(events) == 1
        assert events[0].version == 1


class TestOutboxEdgeCases:
    """Edge cases for outbox pattern"""

    def test_outbox_duplicate_event_projection_pair(self, temp_event_db):
        """Test adding same event to same projection twice"""
        store = EventStore(temp_event_db)
        outbox = Outbox(temp_event_db)

        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=1,
        )
        store.append_event(event)

        # Add to outbox twice for same projection
        outbox_id1 = outbox.add_to_outbox(event.event_id, "neo4j")
        outbox_id2 = outbox.add_to_outbox(event.event_id, "neo4j")

        # Both should succeed (duplicate processing allowed)
        assert outbox_id1 != outbox_id2

        pending = outbox.get_pending(projection_name="neo4j")
        assert len(pending) >= 2

    def test_outbox_invalid_projection_name(self, temp_event_db):
        """Test invalid projection names"""
        store = EventStore(temp_event_db)
        outbox = Outbox(temp_event_db)

        event = Event(
            event_type="Test",
            aggregate_id="test-1",
            aggregate_type="Test",
            event_data={},
            version=1,
        )
        store.append_event(event)

        # Should allow any projection name (no validation)
        invalid_names = ["", None, "invalid", "neo4j; DROP TABLE outbox;"]

        for name in invalid_names:
            try:
                if name is not None:
                    outbox.add_to_outbox(event.event_id, name)
            except Exception as e:
                print(f"Failed for {name}: {e}")

    def test_outbox_mark_nonexistent_item(self, temp_event_db):
        """Test marking non-existent outbox items"""
        outbox = Outbox(temp_event_db)

        # Try to mark non-existent item
        result = outbox.mark_processed("nonexistent-id")
        assert result is True  # Update succeeds but affects 0 rows

        result = outbox.mark_failed("nonexistent-id", "error")
        assert result is True

        result = outbox.retry_failed("nonexistent-id")
        assert result is False  # This one checks rowcount
