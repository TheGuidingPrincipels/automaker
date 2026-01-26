#!/usr/bin/env python3
"""
Cleanup: Migrate confidence_score_auto → confidence_score in Neo4j

Run this AFTER deploying the code changes from Phase 1.

This script:
1. Copies confidence_score_auto → confidence_score
2. Removes old confidence_score_auto property
3. Sets default scores (0.0) for concepts without scores
"""

import asyncio

from config import get_settings
from services.neo4j_service import Neo4jService


async def cleanup():
    """Migrate old property names to new schema."""
    settings = get_settings()
    neo4j = Neo4jService(
        uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password
    )

    try:
        await neo4j.connect()
        print("🔗 Connected to Neo4j")

        # Step 1: Copy confidence_score_auto → confidence_score
        print("\n📋 Step 1/3: Migrating automated scores to main property...")
        query1 = """
        MATCH (c:Concept)
        WHERE c.confidence_score_auto IS NOT NULL
        SET c.confidence_score = c.confidence_score_auto
        RETURN count(c) as migrated
        """
        result = neo4j.execute_write(query1, {})
        migrated = result[0]["migrated"] if result else 0
        print(f"   ✅ Migrated {migrated} concepts")

        # Step 2: Remove old property
        print("\n🧹 Step 2/3: Removing old confidence_score_auto property...")
        query2 = """
        MATCH (c:Concept)
        WHERE c.confidence_score_auto IS NOT NULL
        REMOVE c.confidence_score_auto
        RETURN count(c) as cleaned
        """
        result = neo4j.execute_write(query2, {})
        cleaned = result[0]["cleaned"] if result else 0
        print(f"   ✅ Cleaned {cleaned} concepts")

        # Step 3: Set missing scores to 0.0
        print("\n🔧 Step 3/3: Setting default scores for concepts without scores...")
        query3 = """
        MATCH (c:Concept)
        WHERE c.confidence_score IS NULL
        SET c.confidence_score = 0.0
        RETURN count(c) as defaulted
        """
        result = neo4j.execute_write(query3, {})
        defaulted = result[0]["defaulted"] if result else 0
        print(f"   ✅ Set default scores for {defaulted} concepts")

        # Summary
        print("\n" + "=" * 60)
        print("🎉 CLEANUP COMPLETE!")
        print("=" * 60)
        print(f"   📊 Migrated:  {migrated} concepts")
        print(f"   🧹 Cleaned:   {cleaned} concepts")
        print(f"   🔧 Defaulted: {defaulted} concepts")
        print("\n✅ Database is ready for automated-only scoring system")

    except Exception as e:
        print(f"\n❌ ERROR during cleanup: {e}")
        raise
    finally:
        await neo4j.disconnect()
        print("\n🔌 Disconnected from Neo4j")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Neo4j Property Cleanup Script")
    print("="*60)
    print("\nThis script migrates confidence_score_auto → confidence_score")
    print("Run AFTER deploying Phase 1 code changes\n")

    asyncio.run(cleanup())
