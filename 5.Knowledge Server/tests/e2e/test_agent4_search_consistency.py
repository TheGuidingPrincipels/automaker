#!/usr/bin/env python3
"""
AGENT 4: Search Consistency Verification
==========================================

Verifies that all search tools return identical confidence scores.

Test Plan:
1. Create test concept with unique name
2. Wait 6 seconds for score calculation
3. Retrieve score via ALL tools:
   - get_concept(concept_id)
   - search_concepts_exact(name=...)
   - get_recent_concepts(days=1)
   - get_concepts_by_confidence(min_confidence=0, max_confidence=100)
4. Validate:
   - All 4 tools return EXACTLY the same score
   - Score is in 0-100 scale (not 0-1)
   - No discrepancies between tools
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path


# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import mcp_server
from tools import analytics_tools, concept_tools, search_tools


async def setup_services():
    """Initialize all required services."""
    print("Initializing services...")
    await mcp_server.initialize()
    print("Services initialized successfully")
    print()


async def cleanup_services():
    """Cleanup services."""
    print("\nCleaning up services...")
    # Services will be cleaned up when process exits


async def run_test():
    """Run the search consistency verification test."""

    print("=" * 60)
    print("AGENT 4: SEARCH CONSISTENCY VERIFICATION")
    print("=" * 60)
    print()

    concept_id = None

    try:
        # Setup
        await setup_services()

        # =================================================================
        # Step 1: Create test concept with unique name
        # =================================================================
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_name = f"test_search_consistency_{timestamp}"

        print(f"Step 1: Creating test concept: {test_name}")
        print("-" * 60)

        create_result = await concept_tools.create_concept(
            name=test_name,
            explanation="Test concept for search consistency verification",
            area="Testing",
            topic="Verification",
        )

        if not create_result or not create_result.get("success"):
            print(f"❌ FAIL: Could not create test concept: {create_result}")
            return False

        concept_id = create_result["data"]["concept_id"]
        print(f"✅ Created concept with ID: {concept_id}")
        print()

        # =================================================================
        # Step 2: Wait 6 seconds for score calculation
        # =================================================================
        print("Step 2: Waiting 6 seconds for confidence score calculation...")
        print("-" * 60)
        await asyncio.sleep(6)
        print("✅ Wait complete")
        print()

        # =================================================================
        # Step 3: Retrieve score via all tools
        # =================================================================
        print("Step 3: Retrieving scores from all tools")
        print("-" * 60)

        scores = {}

        # Tool 1: get_concept
        print("1. Testing get_concept()...")
        result = await concept_tools.get_concept(concept_id)
        if result and result.get("success") and result.get("data", {}).get("concept"):
            concept = result["data"]["concept"]
            scores["get_concept"] = concept.get("confidence_score")
            print(f"   Score: {scores['get_concept']}")
        else:
            print(f"   ❌ ERROR: Could not retrieve concept: {result}")
            scores["get_concept"] = None

        # Tool 2: search_concepts_exact
        print("2. Testing search_concepts_exact()...")
        exact_result = await search_tools.search_concepts_exact(name=test_name)
        if exact_result and exact_result.get("success") and len(exact_result.get("data", {}).get("results", [])) > 0:
            scores["search_concepts_exact"] = exact_result["data"]["results"][0].get("confidence_score")
            print(f"   Score: {scores['search_concepts_exact']}")
        else:
            print(f"   ❌ ERROR: Concept not found in exact search: {exact_result}")
            scores["search_concepts_exact"] = None

        # Tool 3: get_recent_concepts
        print("3. Testing get_recent_concepts()...")
        recent_result = await search_tools.get_recent_concepts(days=1)
        if recent_result and recent_result.get("success"):
            recent_concepts = recent_result.get("data", {}).get("results", [])
            recent_concept = next((c for c in recent_concepts if c.get("concept_id") == concept_id), None)
            if recent_concept:
                scores["get_recent_concepts"] = recent_concept.get("confidence_score")
                print(f"   Score: {scores['get_recent_concepts']}")
            else:
                print(
                    f"   ❌ ERROR: Concept not found in recent concepts (found {len(recent_concepts)} concepts)"
                )
                scores["get_recent_concepts"] = None
        else:
            print(f"   ❌ ERROR: Failed to get recent concepts: {recent_result}")
            scores["get_recent_concepts"] = None

        # Tool 4: get_concepts_by_confidence
        print("4. Testing get_concepts_by_confidence()...")
        confidence_result = await analytics_tools.get_concepts_by_confidence(min_confidence=0, max_confidence=100)
        if confidence_result and confidence_result.get("success"):
            confidence_concepts = confidence_result.get("data", {}).get("results", [])
            confidence_concept = next((c for c in confidence_concepts if c.get("concept_id") == concept_id), None)
            if confidence_concept:
                scores["get_concepts_by_confidence"] = confidence_concept.get("confidence_score")
                print(f"   Score: {scores['get_concepts_by_confidence']}")
            else:
                print(f"   ❌ ERROR: Concept not found in confidence search (found {len(confidence_concepts)} concepts)")
                scores["get_concepts_by_confidence"] = None
        else:
            print(f"   ❌ ERROR: Failed to get concepts by confidence: {confidence_result}")
            scores["get_concepts_by_confidence"] = None

        print()

        # =================================================================
        # Step 4: Validate results
        # =================================================================
        print("=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        print()

        print(f"Test concept: {concept_id}")
        print()

        # Check if all scores were retrieved
        all_retrieved = all(score is not None for score in scores.values())

        if not all_retrieved:
            print("❌ FAIL: Not all tools returned a score")
            for tool, score in scores.items():
                status = "✓" if score is not None else "✗"
                print(f"  {status} {tool}: {score}")
            print()
            return False

        # Print all scores
        print("Scores from each tool:")
        for tool, score in scores.items():
            print(f"  - {tool}: {score}")
        print()

        # Check if all scores are identical
        score_values = list(scores.values())
        all_identical = all(s == score_values[0] for s in score_values)

        # Check if all scores are in 0-100 scale
        all_in_range = all(0 <= s <= 100 for s in score_values if s is not None)

        # Determine overall status
        test_passed = all_identical and all_in_range

        print("Test: All search tools return identical scores")
        print(f"Status: {'PASS' if test_passed else 'FAIL'}")
        print()

        print("Details:")
        print(f"  - All scores identical: {'YES' if all_identical else 'NO'}")
        print(f"  - All scores in 0-100 scale: {'YES' if all_in_range else 'NO'}")
        print()

        if not all_identical:
            print("Issues found:")
            print("  Score discrepancies detected:")
            for tool, score in scores.items():
                print(f"    {tool}: {score}")
        else:
            print("Issues found: none")

        print()

        return test_passed

    finally:
        # =================================================================
        # Cleanup
        # =================================================================
        if concept_id:
            print("-" * 60)
            print(f"Cleaning up test concept: {concept_id}")
            await concept_tools.delete_concept(concept_id)
            print("✅ Test concept deleted")
            print()

        await cleanup_services()


if __name__ == "__main__":
    success = asyncio.run(run_test())
    sys.exit(0 if success else 1)
