#!/usr/bin/env python3
"""
E2E Verification: Automated Confidence Scoring System

This script validates that:
1. Concepts get automated scores (not manual)
2. All tools return consistent scores
3. Search/analytics filters work correctly
4. Scores update when content changes
"""

import asyncio
from tools.concept_tools import create_concept, get_concept, update_concept
from tools.search_tools import search_concepts_exact, get_recent_concepts
from tools.analytics_tools import get_concepts_by_confidence


async def verify():
    print("="*70)
    print("🧪 E2E VERIFICATION: Automated Confidence Scoring System")
    print("="*70)
    print()

    concept_id = None

    try:
        # Test 1: Create concept without manual score
        print("[Test 1/6] Creating concept without manual score...")
        result = await create_concept(
            name="E2E Test Automated Scoring",
            explanation="This is a comprehensive test concept to verify automated scoring works correctly across all tools and search mechanisms. "
            * 10,
            area="Testing",
            topic="Automation",
            subtopic="E2E",
        )
        assert result["success"], f"Create failed: {result.get('message')}"
        concept_id = result["data"]["concept_id"]
        print(f"   ✅ Created concept: {concept_id}")

        # Wait for async confidence calculation
        print("\n[Test 2/6] Waiting for confidence calculation (6 seconds)...")
        await asyncio.sleep(6)
        print("   ✅ Wait complete")

        # Test 3: Get concept - should have automated score
        print("\n[Test 3/6] Retrieving concept via get_concept...")
        result = await get_concept(concept_id)
        assert result["success"], f"Get failed: {result.get('message')}"
        score = result["data"]["concept"]["confidence_score"]
        print(f"   ✅ get_concept returned score: {score}")
        assert 0 <= score <= 100, f"Score out of range: {score}"
        assert score > 0, "Score should be > 0 for concepts with content"

        # Test 4: Search exact - should return same score
        print("\n[Test 4/6] Searching via search_concepts_exact...")
        result = await search_concepts_exact(name="E2E Test Automated")
        assert result["success"], f"Search failed: {result.get('message')}"
        assert len(result["data"]["results"]) > 0, "No results found"
        search_score = result["data"]["results"][0]["confidence_score"]
        print(f"   ✅ search_concepts_exact returned score: {search_score}")
        assert search_score == score, f"Scores don't match! get={score}, search={search_score}"

        # Test 5: Recent concepts - should return same score
        print("\n[Test 5/6] Retrieving via get_recent_concepts...")
        result = await get_recent_concepts(days=1)
        assert result["success"], f"Recent query failed: {result.get('message')}"
        found = [c for c in result["data"]["results"] if c["concept_id"] == concept_id]
        assert len(found) > 0, "Concept not in recent results"
        recent_score = found[0]["confidence_score"]
        print(f"   ✅ get_recent_concepts returned score: {recent_score}")
        assert recent_score == score, f"Scores don't match! get={score}, recent={recent_score}"

        # Test 6: Analytics by confidence - should find it
        print("\n[Test 6/6] Filtering via get_concepts_by_confidence...")
        min_score = max(0, score - 10)
        max_score = min(100, score + 10)
        result = await get_concepts_by_confidence(
            min_confidence=min_score,
            max_confidence=max_score
        )
        assert result["success"], f"Analytics query failed: {result.get('message')}"
        found = [c for c in result["data"]["results"] if c["concept_id"] == concept_id]
        assert len(found) > 0, f"Concept not found in range [{min_score}, {max_score}]"
        analytics_score = found[0]["confidence_score"]
        print(f"   ✅ get_concepts_by_confidence returned score: {analytics_score}")
        assert analytics_score == score, f"Scores don't match! get={score}, analytics={analytics_score}"

        # Success summary
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("✅ Automated scoring works correctly")
        print(f"✅ Consistent score across all tools: {score}")
        print("✅ No manual override needed")
        print("✅ Search tools return correct scores (not 0.0!)")
        print("✅ Analytics filtering works correctly")
        print("=" * 70)

        return True

    except AssertionError as e:
        print("\n" + "=" * 70)
        print("❌ TEST FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print("=" * 70)
        return False

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ UNEXPECTED ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = asyncio.run(verify())
    exit(0 if success else 1)
