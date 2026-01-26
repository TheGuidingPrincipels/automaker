#!/usr/bin/env python3
"""
Redis Cache Cleanup Script

Clears Redis caches used by the confidence scoring system.

Usage:
    python scripts/cleanup_redis.py              # Full cleanup with confirmation
    python scripts/cleanup_redis.py --dry-run    # Preview without deleting
    python scripts/cleanup_redis.py --yes        # Skip confirmation prompt
"""

import asyncio
import sys
from pathlib import Path


# Add parent directory to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis.asyncio as redis

from services.confidence.config import CacheConfig


async def cleanup_redis(dry_run=False, skip_confirm=False):
    """
    Clear all keys from Redis database.

    Args:
        dry_run: If True, show what would be deleted without deleting
        skip_confirm: If True, skip confirmation prompt
    """
    print("=" * 60)
    print("Redis Cache Cleanup Script")
    print("=" * 60)
    print()

    cache_config = CacheConfig()

    # Connect to Redis
    print(
        f"Connecting to Redis: {cache_config.REDIS_HOST}:{cache_config.REDIS_PORT} (DB {cache_config.REDIS_DB})"
    )
    redis_client = redis.Redis(
        host=cache_config.REDIS_HOST,
        port=cache_config.REDIS_PORT,
        db=cache_config.REDIS_DB,
        password=cache_config.REDIS_PASSWORD or None,
        decode_responses=True,
    )

    try:
        # Check connection
        await redis_client.ping()
        print("✅ Connected to Redis successfully")
        print()

        # Get current key count
        keys = await redis_client.keys("*")
        key_count = len(keys)

        print("📊 Current Redis Status:")
        print(f"   Total keys: {key_count}")

        if key_count == 0:
            print("\n✅ Redis is already empty - nothing to clean")
            return

        # Show sample keys
        if keys:
            print("\n📝 Sample keys (showing first 10):")
            for i, key in enumerate(keys[:10]):
                print(f"   {i+1}. {key}")
            if key_count > 10:
                print(f"   ... and {key_count - 10} more keys")

        print()

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print(f"   Would delete {key_count} keys from Redis")
            return

        # Confirm deletion
        if not skip_confirm:
            print("⚠️  WARNING: This will delete ALL keys from Redis!")
            print(f"   {key_count} keys will be permanently removed")
            print()
            confirm = input("   Type 'yes' to confirm deletion: ")
            if confirm.lower() != "yes":
                print("\n❌ Cleanup cancelled by user")
                return

        # Clear all keys
        print(f"\n🗑️  Deleting {key_count} keys from Redis...")
        await redis_client.flushdb()
        print(f"✅ Successfully deleted {key_count} keys from Redis")

        # Verify
        remaining = len(await redis_client.keys("*"))
        if remaining == 0:
            print("✅ Verification: Redis is now empty")
        else:
            print(f"⚠️  Warning: {remaining} keys still remain in Redis")

    except redis.ConnectionError as e:
        print("\n❌ ERROR: Could not connect to Redis")
        print(f"   {e!s}")
        print("\n   Make sure Redis is running:")
        print("   - Check if Redis is installed: redis-cli ping")
        print("   - Start Redis: redis-server (or via Docker/Homebrew)")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR during Redis cleanup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await redis_client.close()
        print("\n🔌 Disconnected from Redis")


def main():
    """Parse arguments and run cleanup"""
    dry_run = "--dry-run" in sys.argv
    skip_confirm = "--yes" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return

    asyncio.run(cleanup_redis(dry_run=dry_run, skip_confirm=skip_confirm))

    print("\n" + "=" * 60)
    print("Redis Cleanup Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
