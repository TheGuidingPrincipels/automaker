#!/usr/bin/env python3
"""
Backfill automated confidence scores for all existing concepts.

This script:
1. Finds all concepts without automated scores
2. Calculates confidence scores using the full scoring system
3. Persists scores to Neo4j as confidence_score_auto
4. Updates cache in Redis

Usage:
    python scripts/backfill_confidence_scores.py

Options:
    --all           Recalculate ALL concepts (even those with existing scores)
    --limit N       Process only N concepts (default: all)
    --dry-run       Calculate but don't persist scores
"""

import argparse
import asyncio
import sys
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.confidence.models import Error
from services.confidence.runtime import build_confidence_runtime
from services.neo4j_service import Neo4jService


async def backfill_scores(
    recalculate_all: bool = False, limit: int | None = None, dry_run: bool = False
):
    """Backfill confidence scores for existing concepts."""

    print("=" * 60)
    print("CONFIDENCE SCORE BACKFILL")
    print("=" * 60)
    print(f"Mode: {'Recalculate ALL' if recalculate_all else 'Only missing scores'}")
    print(f"Limit: {limit if limit else 'No limit'}")
    print(f"Dry run: {dry_run}")
    print()

    # Initialize Neo4j
    print("Connecting to Neo4j...")
    neo4j = Neo4jService(
        uri=Config.NEO4J_URI, user=Config.NEO4J_USER, password=Config.NEO4J_PASSWORD
    )

    if not neo4j.connect():
        print("❌ Failed to connect to Neo4j")
        return False
    print("✅ Neo4j connected\n")

    # Build confidence runtime
    print("Initializing confidence scoring runtime...")
    runtime = await build_confidence_runtime(neo4j)

    if not runtime:
        print("❌ Failed to initialize confidence runtime")
        print("   Make sure Redis is running on localhost:6379")
        return False
    print("✅ Confidence runtime initialized\n")

    # Query for concepts
    print("Querying concepts...")

    if recalculate_all:
        query = """
        MATCH (c:Concept)
        WHERE c.deleted IS NULL OR c.deleted = false
        RETURN c.concept_id AS id, c.name AS name
        ORDER BY c.created_at DESC
        """
    else:
        query = """
        MATCH (c:Concept)
        WHERE (c.deleted IS NULL OR c.deleted = false)
          AND (c.confidence_score_auto IS NULL)
        RETURN c.concept_id AS id, c.name AS name
        ORDER BY c.created_at DESC
        """

    if limit:
        query += f" LIMIT {limit}"

    try:
        with neo4j.session() as session:
            result = session.run(query)
            concepts = [{"id": record["id"], "name": record["name"]} for record in result]
    except Exception as e:
        print(f"❌ Query failed: {e}")
        await runtime.close()
        return False

    total = len(concepts)

    if total == 0:
        print("ℹ️  No concepts found to process")
        await runtime.close()
        return True

    print(f"Found {total} concept(s) to process\n")
    print("=" * 60)

    # Process each concept
    success_count = 0
    error_count = 0

    for i, concept in enumerate(concepts, 1):
        concept_id = concept["id"]
        concept_name = concept["name"]

        # Calculate score
        try:
            result = await runtime.calculator.calculate_composite_score(concept_id)

            if isinstance(result, Error):
                print(f"[{i}/{total}] ❌ {concept_name[:40]}")
                print(f"         Error: {result.message}")
                error_count += 1
                continue

            score = result.value
            score_percentage = score * 100

            print(f"[{i}/{total}] {concept_name[:40]}")
            print(f"         Score: {score_percentage:.2f}/100 (raw: {score:.4f})")

            if not dry_run:
                # Persist to Neo4j
                update_query = """
                MATCH (c:Concept {concept_id: $concept_id})
                SET c.confidence_score_auto = $score,
                    c.confidence_last_calculated = datetime()
                RETURN c.confidence_score_auto AS persisted_score
                """

                try:
                    with neo4j.session() as session:
                        update_result = session.run(
                            update_query, concept_id=concept_id, score=float(score)
                        )
                        persisted = update_result.single()

                        if persisted:
                            # Also cache in Redis
                            await runtime.cache_manager.set_cached_score(concept_id, score)
                            print("         ✅ Persisted to Neo4j and cached")
                            success_count += 1
                        else:
                            print("         ⚠️  Concept not found in Neo4j")
                            error_count += 1
                except Exception as e:
                    print(f"         ❌ Persistence failed: {e}")
                    error_count += 1
            else:
                success_count += 1
                print("         ℹ️  Would persist (dry-run mode)")

        except Exception as e:
            print(f"[{i}/{total}] ❌ {concept_name[:40]}")
            print(f"         Exception: {e}")
            error_count += 1

    # Cleanup
    await runtime.close()

    # Summary
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Total processed: {total}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Errors: {error_count}")

    if dry_run:
        print("\nℹ️  This was a dry-run. Run without --dry-run to persist scores.")
    else:
        print("\n✅ Scores have been persisted to Neo4j and cached in Redis")

    print()

    return error_count == 0


def main():
    parser = argparse.ArgumentParser(
        description="Backfill automated confidence scores for concepts"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Recalculate ALL concepts (even those with existing scores)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only N concepts")
    parser.add_argument("--dry-run", action="store_true", help="Calculate but don't persist scores")

    args = parser.parse_args()

    success = asyncio.run(
        backfill_scores(recalculate_all=args.all, limit=args.limit, dry_run=args.dry_run)
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
