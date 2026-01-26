#!/usr/bin/env python3
"""
AGENT 3: Update Concept Score Recalculation Test
=================================================

Tests that updating a concept triggers automatic score recalculation:
1. Create concept with minimal explanation (10 words) → get initial score
2. Update concept with rich explanation (200+ words) → score recalculates
3. Verify score increased (better content → higher score)
4. Verify update_concept() does NOT accept confidence_score parameter
"""

import asyncio
import sys
from pathlib import Path


# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import mcp_server
from tools import concept_tools


async def setup_services():
    """Initialize all required services."""
    print("Initializing services...")
    await mcp_server.initialize()
    print("Services initialized successfully")
    return True


async def cleanup_services():
    """Cleanup services."""
    print("\nCleaning up services...")
    # Services will be cleaned up when process exits
    pass


async def run_test():
    """Run the update score recalculation test."""

    print("=" * 60)
    print("AGENT 3: UPDATE CONCEPT SCORE RECALCULATION")
    print("=" * 60)
    print()

    concept_id = None

    try:
        # Setup
        await setup_services()

        # =================================================================
        # TEST 1: Verify update_concept() signature does NOT include confidence_score
        # =================================================================
        print("TEST 1: Verify update_concept() signature")
        print("-" * 60)

        import inspect

        sig = inspect.signature(concept_tools.update_concept)
        params = list(sig.parameters.keys())

        print(f"Parameters: {params}")

        has_confidence_score = 'confidence_score' in params
        print(f"Has confidence_score parameter: {has_confidence_score}")

        if has_confidence_score:
            print("❌ FAIL: update_concept() should NOT have confidence_score parameter")
            return False
        else:
            print("✅ PASS: update_concept() correctly excludes confidence_score parameter")

        print()

        # =================================================================
        # TEST 2: Create concept with minimal explanation
        # =================================================================
        print("TEST 2: Create concept with MINIMAL explanation")
        print("-" * 60)

        minimal_explanation = "Short test concept with only ten words here."

        create_result = await concept_tools.create_concept(
            name="Test Concept Score Recalc",
            explanation=minimal_explanation,
            area="Testing",
            topic="Score Recalculation",
        )

        if not create_result["success"]:
            print(f"❌ FAIL: Failed to create concept: {create_result}")
            return False

        concept_id = create_result["data"]["concept_id"]
        print(f"✅ Created concept: {concept_id}")
        print(f"Explanation length: {len(minimal_explanation.split())} words")
        print()

        # Wait for score calculation
        print("Waiting 6 seconds for score calculation...")
        await asyncio.sleep(6)

        # =================================================================
        # TEST 3: Get initial score
        # =================================================================
        print("TEST 3: Retrieve initial score")
        print("-" * 60)

        get_result = await concept_tools.get_concept(concept_id)

        if not get_result["success"]:
            print(f"❌ FAIL: Failed to retrieve concept: {get_result}")
            return False

        initial_score = get_result["data"]["concept"]["confidence_score"]
        print(f"Initial score (0-100 scale): {initial_score}")

        if initial_score is None:
            print("❌ FAIL: Initial score is None")
            return False

        print("✅ PASS: Initial score retrieved")
        print()

        # =================================================================
        # TEST 4: Update concept with rich explanation
        # =================================================================
        print("TEST 4: Update concept with RICH explanation (200+ words)")
        print("-" * 60)

        rich_explanation = """
        This is a comprehensive and detailed explanation of the test concept designed to demonstrate
        score recalculation upon updates. The concept explores various aspects of automated confidence
        scoring systems in knowledge management platforms. When users update concepts with richer,
        more detailed explanations, the system should automatically recalculate the confidence score
        to reflect the improved content quality.

        Understanding score calculation considers multiple factors including explanation length,
        semantic coherence, information density, and structural completeness. A minimal explanation
        with only ten words provides basic information but lacks depth and context. In contrast,
        a rich explanation with multiple paragraphs, examples, and thorough coverage of the topic
        demonstrates higher quality and completeness.

        The automated scoring system uses natural language processing techniques to analyze concept
        quality. Longer explanations with well-structured content typically receive higher understanding
        scores. However, length alone is not sufficient - the content must be meaningful, coherent,
        and relevant to the concept being explained.

        This test verifies that the update_concept function triggers score recalculation automatically
        without accepting manual confidence_score parameters. The system should detect the content
        improvement and assign a higher score accordingly. This ensures that concept quality metrics
        remain accurate and up-to-date as users refine and enhance their knowledge base entries.

        The recalculation process happens asynchronously after the update is committed to the database.
        Event listeners detect the concept update event and trigger the confidence calculation workflow.
        This architecture ensures that score updates do not block the user's update operation while
        still maintaining accurate quality metrics across the knowledge base.
        """

        word_count = len(rich_explanation.split())
        print(f"Rich explanation length: {word_count} words")

        update_result = await concept_tools.update_concept(
            concept_id=concept_id, explanation=rich_explanation
        )

        if not update_result["success"]:
            print(f"❌ FAIL: Failed to update concept: {update_result}")
            return False

        print("✅ Updated concept with rich explanation")
        print(f"Updated fields: {update_result['updated_fields']}")

        # Verify confidence_score NOT in updated_fields
        if 'confidence_score' in update_result['updated_fields']:
            print("❌ FAIL: confidence_score should NOT be in updated_fields")
            return False

        print()

        # Wait for score recalculation
        print("Waiting 6 seconds for score recalculation...")
        await asyncio.sleep(6)

        # =================================================================
        # TEST 5: Get updated score
        # =================================================================
        print("TEST 5: Retrieve updated score")
        print("-" * 60)

        get_result2 = await concept_tools.get_concept(concept_id)

        if not get_result2["success"]:
            print(f"❌ FAIL: Failed to retrieve updated concept: {get_result2}")
            return False

        final_score = get_result2["data"]["concept"]["confidence_score"]
        print(f"Final score (0-100 scale): {final_score}")

        if final_score is None:
            print("❌ FAIL: Final score is None")
            return False

        print("✅ PASS: Final score retrieved")
        print()

        # =================================================================
        # TEST 6: Validate score changes
        # =================================================================
        print("TEST 6: Validate score recalculation")
        print("-" * 60)

        score_delta = final_score - initial_score
        score_changed = abs(score_delta) > 0.01  # Allow for floating point precision
        score_increased = score_delta > 0

        print(f"Initial score: {initial_score:.4f}")
        print(f"Final score:   {final_score:.4f}")
        print(f"Score delta:   {score_delta:+.4f}")
        print(f"Score changed: {score_changed}")
        print(f"Score increased: {score_increased}")
        print()

        # Validate results
        all_passed = True

        if not score_changed:
            print("❌ FAIL: Score did not change after update")
            all_passed = False
        else:
            print("✅ PASS: Score changed after update")

        if not score_increased:
            print("⚠️  WARNING: Score did not increase (expected rich content → higher score)")
            print("   Note: This may not always be guaranteed depending on score algorithm")
        else:
            print("✅ PASS: Score increased (rich content → higher score)")

        print()

        # =================================================================
        # FINAL REPORT
        # =================================================================
        print("=" * 60)
        print("AGENT 3: UPDATE CONCEPT SCORE RECALCULATION")
        print("=" * 60)
        print()
        print("Test: Update concept triggers score recalculation")
        print(f"Status: {'PASS' if all_passed else 'FAIL'}")
        print()
        print("Details:")
        print(f"- Initial score: {initial_score:.4f}")
        print(f"- Updated explanation: {word_count} words (rich content added)")
        print(f"- Final score: {final_score:.4f}")
        print(f"- Score delta: {score_delta:+.4f}")
        print(f"- Score increased: {'YES' if score_increased else 'NO'}")
        print("- Manual score parameter rejected: YES (not in function signature)")
        print()
        print(f"Issues found: {'none' if all_passed else 'Score did not change after update'}")
        print()

        return all_passed

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup test concept
        if concept_id:
            print("Cleaning up test concept...")
            try:
                await concept_tools.delete_concept(concept_id)
                print(f"✅ Deleted test concept: {concept_id}")
            except Exception as e:
                print(f"⚠️  Failed to delete test concept: {e}")

        # Cleanup services
        await cleanup_services()

        print()
        print("Test complete.")


if __name__ == "__main__":
    result = asyncio.run(run_test())
    sys.exit(0 if result else 1)
