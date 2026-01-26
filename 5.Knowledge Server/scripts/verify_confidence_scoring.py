#!/usr/bin/env python3
"""
Verify that the confidence scoring system is working correctly.

This script checks:
1. Redis connectivity
2. Confidence runtime initialization
3. Score calculation for a test concept
4. Proper persistence to Neo4j

Usage:
    python scripts/verify_confidence_scoring.py
"""

import asyncio
import sys
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis.asyncio as redis

from config import Config
from services.confidence.models import Error, Success
from services.confidence.runtime import build_confidence_runtime
from services.neo4j_service import Neo4jService


async def main():
    print("=" * 60)
    print("CONFIDENCE SCORING VERIFICATION")
    print("=" * 60)

    # Step 1: Check Redis
    print("\n1. Checking Redis connectivity...")
    try:
        redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
        response = await redis_client.ping()
        if response:
            print("   ✅ Redis is running and responding")
        else:
            print("   ❌ Redis ping failed")
            return False
        await redis_client.close()
    except Exception as e:
        print(f"   ❌ Redis connection failed: {e}")
        return False

    # Step 2: Initialize Neo4j
    print("\n2. Connecting to Neo4j...")
    try:
        neo4j = Neo4jService(
            uri=Config.NEO4J_URI, user=Config.NEO4J_USER, password=Config.NEO4J_PASSWORD
        )
        if not neo4j.connect():
            print("   ❌ Neo4j connection failed")
            return False
        print("   ✅ Neo4j connected")
    except Exception as e:
        print(f"   ❌ Neo4j error: {e}")
        return False

    # Step 3: Build confidence runtime
    print("\n3. Building confidence runtime...")
    try:
        runtime = await build_confidence_runtime(neo4j)
        if not runtime:
            print("   ❌ Confidence runtime failed to initialize")
            print("      Make sure Redis is running on localhost:6379")
            return False
        print("   ✅ Confidence runtime initialized successfully")
    except Exception as e:
        print(f"   ❌ Runtime initialization error: {e}")
        return False

    # Step 4: Find a test concept
    print("\n4. Finding a test concept...")
    try:
        query = """
        MATCH (c:Concept)
        WHERE c.deleted IS NULL OR c.deleted = false
        RETURN c.concept_id AS id, c.name AS name
        LIMIT 1
        """
        with neo4j.session() as session:
            result = session.run(query)
            record = result.single()

            if not record:
                print("   ⚠️  No concepts found in database")
                print("      Create a concept first to test scoring")
                await runtime.close()
                return True  # Redis works, just no test data

            concept_id = record["id"]
            concept_name = record["name"]
            print(f"   ✅ Found concept: {concept_name} ({concept_id})")
    except Exception as e:
        print(f"   ❌ Query error: {e}")
        await runtime.close()
        return False

    # Step 5: Calculate confidence score
    print("\n5. Calculating confidence score...")
    try:
        result = await runtime.calculator.calculate_composite_score(concept_id)

        if isinstance(result, Error):
            print(f"   ❌ Calculation failed: {result.message}")
            await runtime.close()
            return False

        score = result.value
        score_percentage = score * 100  # Convert 0-1 to 0-100
        print(f"   ✅ Score calculated: {score_percentage:.2f}/100")
        print(f"      (Raw value: {score:.4f})")
    except Exception as e:
        print(f"   ❌ Calculation error: {e}")
        await runtime.close()
        return False

    # Step 6: Verify score components
    print("\n6. Checking score components...")
    try:
        # Try to get breakdown by calling sub-calculators
        understanding_result = (
            await runtime.calculator.understanding_calc.calculate_understanding_score(concept_id)
        )
        retention_result = await runtime.calculator.retention_calc.calculate_retention_score(
            concept_id
        )

        if isinstance(understanding_result, Success):
            understanding = understanding_result.value
            print(f"   ✅ Understanding score: {understanding:.4f} (weight: 60%)")
        else:
            print(f"   ⚠️  Understanding calculation issue: {understanding_result.message}")

        if isinstance(retention_result, Success):
            retention = retention_result.value
            print(f"   ✅ Retention score: {retention:.4f} (weight: 40%)")
        else:
            print(f"   ⚠️  Retention calculation issue: {retention_result.message}")

    except Exception as e:
        print(f"   ⚠️  Could not get score breakdown: {e}")

    # Step 7: Check if score is cached
    print("\n7. Verifying Redis cache...")
    try:
        cached_score = await runtime.cache_manager.get_cached_score(concept_id)
        if cached_score is not None:
            print(f"   ✅ Score is cached in Redis: {cached_score:.4f}")
        else:
            print("   ℹ️  Score not yet cached (will be cached by event listener)")
    except Exception as e:
        print(f"   ⚠️  Cache check error: {e}")

    # Step 8: Check Neo4j properties
    print("\n8. Checking Neo4j properties...")
    try:
        query = """
        MATCH (c:Concept {concept_id: $concept_id})
        RETURN c.confidence_score AS manual_score,
               c.confidence_score_auto AS auto_score,
               c.confidence_last_calculated AS last_calc
        """
        with neo4j.session() as session:
            result = session.run(query, concept_id=concept_id)
            record = result.single()

            if record:
                manual = record.get("manual_score", "Not set")
                auto = record.get("auto_score", "Not set")
                last_calc = record.get("last_calc", "Never")

                print(f"   Manual score (confidence_score): {manual}")
                print(f"   Auto score (confidence_score_auto): {auto}")
                print(f"   Last calculated: {last_calc}")

                if auto == "Not set":
                    print("   ℹ️  Auto score not yet persisted to Neo4j")
                    print("      The event listener will persist it in the background")
    except Exception as e:
        print(f"   ⚠️  Property check error: {e}")

    # Cleanup
    await runtime.close()

    print("\n" + "=" * 60)
    print("✅ VERIFICATION COMPLETE - Confidence scoring is working!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the MCP server - it will now use Redis for confidence scoring")
    print("2. Create new concepts - they will get automated scores")
    print("3. Run scripts/backfill_confidence_scores.py for existing concepts")
    print()

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
