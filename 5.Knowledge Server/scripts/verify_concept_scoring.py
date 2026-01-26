#!/usr/bin/env python3
"""
Verification script for automated confidence score calculation.
Tests that creating a concept results in proper score calculation and storage.
"""

import asyncio
import sys
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import mcp_server
from tools import concept_tools, search_tools


async def verify_concept_scoring():
    """Verify that concept creation triggers automated confidence score calculation."""

    print("AGENT 2: CREATE CONCEPT SCORE VERIFICATION")
    print("=" * 43)
    print()

    test_concept_id = None

    try:
        # Setup services
        print("Initializing services...")
        await mcp_server.initialize()
        print("✓ Services initialized")
        print()

        # Step 1: Create a test concept with rich explanation
        print("Step 1: Creating test concept with rich explanation...")

        test_explanation = """
        Machine learning is a subset of artificial intelligence that enables computer systems
        to learn and improve from experience without being explicitly programmed. It focuses on
        developing algorithms that can access data and use it to learn for themselves. The process
        of learning begins with observations or data, such as examples, direct experience, or
        instruction, in order to look for patterns in data and make better decisions in the future
        based on the examples that we provide.

        The primary aim is to allow computers to learn automatically without human intervention
        or assistance and adjust actions accordingly. Machine learning algorithms are categorized
        into three main types: supervised learning, where the algorithm learns from labeled training
        data; unsupervised learning, where the algorithm finds hidden patterns in unlabeled data;
        and reinforcement learning, where the algorithm learns through trial and error to achieve
        a goal in a dynamic environment.

        Modern applications of machine learning include image recognition, natural language processing,
        recommendation systems, autonomous vehicles, fraud detection, and medical diagnosis. The field
        has grown exponentially with the availability of big data and increased computational power,
        particularly through the use of GPUs and cloud computing infrastructure.
        """

        result = await concept_tools.create_concept(
            name="Machine Learning Verification Test",
            explanation=test_explanation.strip(),
            area="Computer Science",
            topic="Artificial Intelligence",
        )

        if not result["success"]:
            print(f"✗ ERROR: Failed to create concept: {result}")
            return False

        test_concept_id = result["concept_id"]
        print(f"✓ Concept created: {test_concept_id}")
        print()

        # Step 2: Wait for async score calculation
        print("Step 2: Waiting 6 seconds for async score calculation...")
        await asyncio.sleep(6)
        print("✓ Wait complete")
        print()

        # Step 3: Retrieve concept via API
        print("Step 3: Retrieving concept via get_concept()...")
        concept_result = await concept_tools.get_concept(test_concept_id)

        if not concept_result["success"]:
            print(f"✗ ERROR: Failed to retrieve concept: {concept_result}")
            return False

        concept_data = concept_result["concept"]
        print("✓ Concept retrieved")
        print()

        # Step 4: Validate API response
        print("Step 4: Validating API response...")
        validations = {
            "confidence_score field exists": "confidence_score" in concept_data,
            "score is numeric": isinstance(concept_data.get("confidence_score"), (int, float)),
            "score is between 0 and 100": False,
            "score is > 0 (not default)": False,
        }

        api_score = concept_data.get("confidence_score", 0)
        if isinstance(api_score, (int, float)):
            validations["score is between 0 and 100"] = 0 <= api_score <= 100
            validations["score is > 0 (not default)"] = api_score > 0

        print(f"  API Score (0-100 scale): {api_score}")
        for check, passed in validations.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}: {passed}")
        print()

        # Step 5: Query Neo4j directly
        print("Step 5: Querying Neo4j directly...")

        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        RETURN c.confidence_score as confidence_score,
               c.confidence_score_auto as confidence_score_auto,
               properties(c) as all_properties
        """

        # Use neo4j service from search_tools (already initialized)
        result_records = search_tools.neo4j_service.execute_read(
            query, {"concept_id": test_concept_id}
        )

        if result_records and len(result_records) > 0:
            record = result_records[0]
            neo4j_score = record["confidence_score"]
            neo4j_score_auto = record["confidence_score_auto"]
            all_props = record["all_properties"]

            print(f"  Neo4j confidence_score: {neo4j_score}")
            print(f"  Neo4j confidence_score_auto: {neo4j_score_auto}")
            print()

            # Additional validations for Neo4j
            neo4j_validations = {
                "Property name is 'confidence_score'": neo4j_score is not None,
                "No 'confidence_score_auto' property": neo4j_score_auto is None,
                "Neo4j value is 0-1 scale": False,
                "API/Neo4j scale conversion correct": False,
            }

            if neo4j_score is not None:
                neo4j_validations["Neo4j value is 0-1 scale"] = 0 <= neo4j_score <= 1

                # Check scale conversion (Neo4j 0-1 -> API 0-100)
                if isinstance(api_score, (int, float)) and isinstance(neo4j_score, (int, float)):
                    expected_api_score = neo4j_score * 100
                    neo4j_validations["API/Neo4j scale conversion correct"] = (
                        abs(api_score - expected_api_score) < 0.01
                    )

            for check, passed in neo4j_validations.items():
                status = "✓" if passed else "✗"
                print(f"  {status} {check}: {passed}")
            print()
        else:
            print("  ✗ ERROR: Concept not found in Neo4j")
            print()
            return False

        # Step 6: Determine overall status
        print("=" * 43)
        all_validations = {**validations, **neo4j_validations}
        all_passed = all(all_validations.values())

        if all_passed:
            print("Status: PASS ✓")
            print()
            print("Summary:")
            print(f"- Concept created: {test_concept_id}")
            print("- Wait time: 6 seconds")
            print(f"- Score retrieved: {api_score:.1f} (0-100 scale)")
            print(f"- Neo4j raw value: {neo4j_score:.3f} (0-1 scale)")
            print("- All validations: PASSED")
            print()
            print("Issues found: none")
        else:
            print("Status: FAIL ✗")
            print()
            print("Issues found:")
            for check, passed in all_validations.items():
                if not passed:
                    print(f"  - {check}: FAILED")

        print()
        return all_passed

    except Exception as e:
        print(f"✗ ERROR: {e!s}")
        print(f"Exception type: {type(e).__name__}")
        import traceback

        print("\nTraceback:")
        print(traceback.format_exc())
        return False

    finally:
        # Cleanup
        if test_concept_id:
            print("Cleaning up...")
            try:
                await concept_tools.delete_concept(test_concept_id)
                print(f"✓ Test concept deleted: {test_concept_id}")
            except Exception as e:
                print(f"✗ Error during cleanup: {e}")


if __name__ == "__main__":
    result = asyncio.run(verify_concept_scoring())
    sys.exit(0 if result else 1)
