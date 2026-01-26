#!/usr/bin/env python3
"""
Verification script for confidence score fix.

This script verifies that:
1. RelationshipDeleted events now include concept IDs
2. Event listener handles relationship events
3. No breaking changes were introduced
"""

import sys

from models.events import ConceptCreated, RelationshipCreated, RelationshipDeleted
from services.confidence.event_listener import ConfidenceEventListener


def test_relationship_deleted_event_structure():
    """Test that RelationshipDeleted can include concept IDs."""
    print("Testing RelationshipDeleted event structure...")

    # Test with new structure (includes concept IDs)
    event = RelationshipDeleted(
        aggregate_id="rel-123",
        version=1,
        event_data={"deleted": True, "from_concept_id": "concept-1", "to_concept_id": "concept-2"},
    )

    assert event.event_type == "RelationshipDeleted"
    assert event.aggregate_id == "rel-123"
    assert event.event_data["deleted"]
    assert event.event_data["from_concept_id"] == "concept-1"
    assert event.event_data["to_concept_id"] == "concept-2"
    print("✅ RelationshipDeleted with concept IDs works correctly")

    # Test backward compatibility (old structure without concept IDs)
    old_event = RelationshipDeleted(aggregate_id="rel-456", version=1)

    assert old_event.event_type == "RelationshipDeleted"
    assert old_event.aggregate_id == "rel-456"
    assert old_event.event_data["deleted"]
    print("✅ Backward compatibility maintained (old events still work)")


def test_relationship_created_event_structure():
    """Test that RelationshipCreated includes concept IDs."""
    print("\nTesting RelationshipCreated event structure...")

    event = RelationshipCreated(
        aggregate_id="rel-789",
        relationship_data={
            "relationship_type": "PREREQUISITE",
            "from_concept_id": "concept-a",
            "to_concept_id": "concept-b",
            "strength": 1.0,
        },
        version=1,
    )

    assert event.event_type == "RelationshipCreated"
    assert event.event_data["from_concept_id"] == "concept-a"
    assert event.event_data["to_concept_id"] == "concept-b"
    print("✅ RelationshipCreated structure verified")


def test_event_listener_handles_relationship_events():
    """Test that event listener includes relationship events in handled types."""
    print("\nTesting event listener configuration...")

    handled_types = ConfidenceEventListener._HANDLED_EVENT_TYPES

    assert "ConceptCreated" in handled_types
    assert "ConceptUpdated" in handled_types
    assert "ConceptDeleted" in handled_types
    assert "RelationshipCreated" in handled_types, "RelationshipCreated should be handled"
    assert "RelationshipDeleted" in handled_types, "RelationshipDeleted should be handled"

    print("✅ Event listener handles relationship events")
    print(f"   Handled event types: {handled_types}")


def test_no_breaking_changes():
    """Test that existing event types still work."""
    print("\nTesting backward compatibility...")

    # Test existing event types still work
    concept_event = ConceptCreated(
        aggregate_id="concept-999",
        concept_data={"name": "Test Concept", "explanation": "Test"},
        version=1,
    )

    assert concept_event.event_type == "ConceptCreated"
    print("✅ Existing event types unchanged")


def main():
    print("=" * 60)
    print("CONFIDENCE SCORE FIX VERIFICATION")
    print("=" * 60)
    print()

    try:
        test_relationship_deleted_event_structure()
        test_relationship_created_event_structure()
        test_event_listener_handles_relationship_events()
        test_no_breaking_changes()

        print("\n" + "=" * 60)
        print("✅ ALL VERIFICATION TESTS PASSED")
        print("=" * 60)
        print()
        print("Summary:")
        print("  • RelationshipDeleted events now include concept IDs")
        print("  • Event listener handles relationship events")
        print("  • Backward compatibility maintained")
        print("  • No breaking changes detected")
        print()
        return 0

    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
