#!/usr/bin/env python3
"""
Comprehensive integration test for confidence score fix.

Tests the complete flow:
1. RelationshipCreated events are processed
2. RelationshipDeleted events are processed
3. Both source and target concepts get updated scores
4. Scores are persisted to Neo4j
5. Cache is invalidated correctly
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from models.events import RelationshipCreated, RelationshipDeleted
from services.confidence.event_listener import ConfidenceEventListener
from services.confidence.models import Error, ErrorCode, Success


def create_mock_concept_lock():
    """Create a mock concept_lock that always acquires the lock."""
    @asynccontextmanager
    async def mock_concept_lock(concept_id: str):
        # Always yield True (lock acquired) for testing
        yield True
    return mock_concept_lock


def create_mock_components(tmp_path):
    """Create mock components for testing."""

    # Mock event store
    event_store = Mock()

    # Mock calculator that returns different scores
    calculator = SimpleNamespace()
    calculator.calculate_composite_score = AsyncMock()

    # Mock cache manager
    cache_manager = SimpleNamespace()
    cache_manager.set_cached_score = AsyncMock()
    cache_manager.invalidate_concept_cache = AsyncMock()
    # Add concept_lock mock for distributed locking (race condition fix)
    cache_manager.concept_lock = create_mock_concept_lock()

    # Mock Neo4j service
    neo4j = Mock()
    neo4j.execute_write = Mock()

    # Create listener
    listener = ConfidenceEventListener(
        event_store=event_store,
        calculator=calculator,
        cache_manager=cache_manager,
        neo4j_service=neo4j,
        checkpoint_path=tmp_path / "checkpoint.json",
        recalc_db_path=tmp_path / "pending_recalc.db",
    )

    return listener, event_store, calculator, cache_manager, neo4j


async def test_relationship_created_updates_both_concepts():
    """Test that RelationshipCreated triggers updates for both concepts."""
    print("\n" + "=" * 60)
    print("TEST: RelationshipCreated updates both concepts")
    print("=" * 60)

    tmp_path = Path("/tmp/test_confidence")
    tmp_path.mkdir(exist_ok=True)

    listener, event_store, calculator, cache_manager, neo4j = create_mock_components(tmp_path)

    # Create a RelationshipCreated event
    event = RelationshipCreated(
        aggregate_id="rel-123",
        relationship_data={
            "relationship_type": "PREREQUISITE",
            "from_concept_id": "concept-a",
            "to_concept_id": "concept-b",
            "strength": 1.0,
        },
        version=1,
    )

    # Setup event store to return this event
    event_store.get_all_events.return_value = [event]

    # Setup calculator to return different scores for each concept
    calculator.calculate_composite_score.side_effect = [
        Success(0.75),  # Score for concept-a
        Success(0.82),  # Score for concept-b
    ]

    # Process events
    stats = await listener.process_pending_events()

    # Verify results
    print(f"\n📊 Stats: {stats}")
    assert stats["processed"] == 1, f"Expected 1 processed, got {stats['processed']}"
    assert stats["failed"] == 0, f"Expected 0 failed, got {stats['failed']}"
    assert stats["skipped"] == 0, f"Expected 0 skipped, got {stats['skipped']}"

    # Verify calculator was called for both concepts
    print(f"\n🧮 Calculator calls: {calculator.calculate_composite_score.call_count}")
    assert (
        calculator.calculate_composite_score.call_count == 2
    ), f"Expected 2 calculate calls, got {calculator.calculate_composite_score.call_count}"

    call_args = [call[0][0] for call in calculator.calculate_composite_score.call_args_list]
    print(f"   Called for concepts: {call_args}")
    assert "concept-a" in call_args, "Calculator should be called for concept-a"
    assert "concept-b" in call_args, "Calculator should be called for concept-b"

    # Verify cache invalidation for both concepts
    print(f"\n💾 Cache invalidation calls: {cache_manager.invalidate_concept_cache.call_count}")
    assert (
        cache_manager.invalidate_concept_cache.call_count == 2
    ), f"Expected 2 cache invalidations, got {cache_manager.invalidate_concept_cache.call_count}"

    cache_calls = [call[0][0] for call in cache_manager.invalidate_concept_cache.call_args_list]
    print(f"   Invalidated cache for: {cache_calls}")
    assert "concept-a" in cache_calls, "Cache should be invalidated for concept-a"
    assert "concept-b" in cache_calls, "Cache should be invalidated for concept-b"

    # Verify scores were cached for both concepts
    print(f"\n📦 Score caching calls: {cache_manager.set_cached_score.call_count}")
    assert (
        cache_manager.set_cached_score.call_count == 2
    ), f"Expected 2 cache set calls, got {cache_manager.set_cached_score.call_count}"

    # Verify Neo4j persistence for both concepts
    print(f"\n💿 Neo4j write calls: {neo4j.execute_write.call_count}")
    assert (
        neo4j.execute_write.call_count == 2
    ), f"Expected 2 Neo4j writes, got {neo4j.execute_write.call_count}"

    # Check that both concept IDs were persisted
    neo4j_calls = neo4j.execute_write.call_args_list
    persisted_concepts = [call[1]["parameters"]["concept_id"] for call in neo4j_calls]
    persisted_scores = [call[1]["parameters"]["score"] for call in neo4j_calls]

    print(f"   Persisted concepts: {persisted_concepts}")
    print(f"   Persisted scores: {persisted_scores}")

    assert 'concept-a' in persisted_concepts, "concept-a should be persisted"
    assert 'concept-b' in persisted_concepts, "concept-b should be persisted"
    # Scores are multiplied by 100 before persisting (0.0-1.0 -> 0-100 scale)
    assert 75.0 in persisted_scores, "Score 75.0 (0.75 * 100) should be persisted"
    assert 82.0 in persisted_scores, "Score 82.0 (0.82 * 100) should be persisted"

    # Verify the queries include confidence_score and timestamp
    for call in neo4j_calls:
        query = call[0][0]
        assert 'confidence_score' in query, "Query should update confidence_score"
        assert 'confidence_last_calculated' in query, "Query should update timestamp"

    print("\n✅ RelationshipCreated test PASSED")
    return True


async def test_relationship_deleted_updates_both_concepts():
    """Test that RelationshipDeleted triggers updates for both concepts."""
    print("\n" + "=" * 60)
    print("TEST: RelationshipDeleted updates both concepts")
    print("=" * 60)

    tmp_path = Path("/tmp/test_confidence2")
    tmp_path.mkdir(exist_ok=True)

    listener, event_store, calculator, _cache_manager, neo4j = create_mock_components(tmp_path)

    # Create a RelationshipDeleted event (with new structure including concept IDs)
    event = RelationshipDeleted(
        aggregate_id="rel-456",
        version=2,
        event_data={"deleted": True, "from_concept_id": "concept-x", "to_concept_id": "concept-y"},
    )

    # Setup event store
    event_store.get_all_events.return_value = [event]

    # Setup calculator
    calculator.calculate_composite_score.side_effect = [
        Success(0.60),  # Score for concept-x
        Success(0.55),  # Score for concept-y
    ]

    # Process events
    stats = await listener.process_pending_events()

    # Verify results
    print(f"\n📊 Stats: {stats}")
    assert stats["processed"] == 1, f"Expected 1 processed, got {stats['processed']}"
    assert stats["failed"] == 0, f"Expected 0 failed, got {stats['failed']}"

    # Verify both concepts were recalculated
    print(f"\n🧮 Calculator calls: {calculator.calculate_composite_score.call_count}")
    assert (
        calculator.calculate_composite_score.call_count == 2
    ), f"Expected 2 calculate calls, got {calculator.calculate_composite_score.call_count}"

    call_args = [call[0][0] for call in calculator.calculate_composite_score.call_args_list]
    print(f"   Called for concepts: {call_args}")
    assert "concept-x" in call_args, "Calculator should be called for concept-x"
    assert "concept-y" in call_args, "Calculator should be called for concept-y"

    # Verify Neo4j persistence
    print(f"\n💿 Neo4j write calls: {neo4j.execute_write.call_count}")
    assert (
        neo4j.execute_write.call_count == 2
    ), f"Expected 2 Neo4j writes, got {neo4j.execute_write.call_count}"

    persisted_concepts = [
        call[1]["parameters"]["concept_id"] for call in neo4j.execute_write.call_args_list
    ]
    print(f"   Persisted concepts: {persisted_concepts}")
    assert "concept-x" in persisted_concepts, "concept-x should be persisted"
    assert "concept-y" in persisted_concepts, "concept-y should be persisted"

    print("\n✅ RelationshipDeleted test PASSED")
    return True


async def test_missing_concept_ids_handled_gracefully():
    """Test that events missing concept IDs don't crash the system."""
    print("\n" + "=" * 60)
    print("TEST: Missing concept IDs handled gracefully")
    print("=" * 60)

    tmp_path = Path("/tmp/test_confidence3")
    tmp_path.mkdir(exist_ok=True)

    listener, event_store, calculator, _cache_manager, _neo4j = create_mock_components(tmp_path)

    # Create a malformed RelationshipCreated event (missing concept IDs)
    event = RelationshipCreated(
        aggregate_id="rel-broken",
        relationship_data={
            "relationship_type": "PREREQUISITE",
            # Missing from_concept_id and to_concept_id
        },
        version=1,
    )

    event_store.get_all_events.return_value = [event]

    # Process events
    stats = await listener.process_pending_events()

    # Should process without crashing, but not calculate anything
    print(f"\n📊 Stats: {stats}")
    assert stats["processed"] == 1, "Event should still be marked as processed"
    assert (
        calculator.calculate_composite_score.call_count == 0
    ), "Calculator should not be called for malformed event"

    print("\n✅ Graceful error handling test PASSED")
    return True


async def test_calculation_errors_queue_for_retry():
    """Test that calculation errors queue failed concepts for retry.

    When one concept's calculation fails, it is queued for retry while
    other concepts are still processed. This ensures eventual consistency
    while maximizing the work that can be done.
    """
    print("\n" + "="*60)
    print("TEST: Calculation errors queue for retry")
    print("="*60)

    tmp_path = Path("/tmp/test_confidence4")
    # Clean up any leftover data from previous test runs
    import shutil
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(exist_ok=True)

    listener, event_store, calculator, _cache_manager, neo4j = create_mock_components(tmp_path)

    event = RelationshipCreated(
        aggregate_id="rel-789",
        relationship_data={
            "relationship_type": "PREREQUISITE",
            "from_concept_id": "concept-m",
            "to_concept_id": "concept-n",
        },
        version=1,
    )

    event_store.get_all_events.return_value = [event]

    # First concept fails - second should still be attempted (queue-and-continue behavior)
    calculator.calculate_composite_score.side_effect = [
        Error("Concept not found", ErrorCode.NOT_FOUND),  # concept-m fails
        Success(0.88),  # concept-n succeeds
    ]

    stats = await listener.process_pending_events()

    print(f"\n Stats: {stats}")
    # Event should be marked as FAILED because not all concepts succeeded
    # (checkpoint doesn't advance, will be retried)
    assert stats["failed"] == 1, "Event should be marked as failed for retry"
    assert stats["processed"] == 0, "Event should NOT be marked as processed"

    # NEW BEHAVIOR: Both concepts are attempted
    # Failed concepts are queued for retry instead of stopping processing
    print(f"\n Calculator calls: {calculator.calculate_composite_score.call_count}")
    assert calculator.calculate_composite_score.call_count == 2, \
        "Both concepts should be attempted (queue failures for retry)"

    # NEW BEHAVIOR: Second concept's score IS persisted
    # (we process what we can, queue failures for retry)
    print(f"\n Neo4j write calls: {neo4j.execute_write.call_count}")
    assert neo4j.execute_write.call_count == 1, \
        "Successful concept's score should be persisted"

    # Verify the failed concept was queued for retry
    recalc_stats = await listener.get_pending_recalc_stats()
    assert recalc_stats.get("pending", 0) == 1, \
        "Failed concept should be queued for retry"

    print("\n Queue-and-continue semantics test PASSED")
    return True


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("CONFIDENCE SCORE FIX - COMPREHENSIVE INTEGRATION TEST")
    print("=" * 60)

    try:
        await test_relationship_created_updates_both_concepts()
        await test_relationship_deleted_updates_both_concepts()
        await test_missing_concept_ids_handled_gracefully()
        await test_calculation_errors_queue_for_retry()

        print("\n" + "=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        print()
        print("Summary:")
        print("  ✓ RelationshipCreated events trigger updates for both concepts")
        print("  ✓ RelationshipDeleted events trigger updates for both concepts")
        print("  ✓ Scores are persisted to Neo4j confidence_score_auto property")
        print("  ✓ Cache is properly invalidated")
        print("  ✓ Missing concept IDs handled gracefully")
        print("  ✓ Calculation errors queue failed concepts for retry")
        print()
        print("🎉 Implementation is CORRECT and ROBUST!")
        print()
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
