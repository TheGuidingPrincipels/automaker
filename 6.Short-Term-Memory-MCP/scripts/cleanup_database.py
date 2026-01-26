#!/usr/bin/env python3
"""
Short-Term Memory MCP - Database Cleanup Script

Completely resets the database by deleting all sessions, concepts, stage data,
and research cache while preserving the domain whitelist configuration.

Usage:
    python scripts/cleanup_database.py [--backup] [--yes]

    Or create an alias:
    alias clean-short-term="python /path/to/scripts/cleanup_database.py"

Options:
    --backup    Create a backup of the database before cleaning
    --yes       Skip confirmation prompt (use with caution!)
"""

import asyncio
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from short_term_mcp.config import DB_PATH
from short_term_mcp.database import Database, get_db


def create_backup(db_path: Path) -> Path:
    """Create a timestamped backup of the database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    backup_path = backup_dir / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)

    return backup_path


def get_database_stats(db: Database) -> dict:
    """Get current database statistics."""
    stats = {}

    # Count sessions
    cursor = db.connection.execute("SELECT COUNT(*) FROM sessions")
    stats["sessions"] = cursor.fetchone()[0]

    # Count concepts
    cursor = db.connection.execute("SELECT COUNT(*) FROM concepts")
    stats["concepts"] = cursor.fetchone()[0]

    # Count stage data
    cursor = db.connection.execute("SELECT COUNT(*) FROM concept_stage_data")
    stats["stage_data"] = cursor.fetchone()[0]

    # Count research cache
    cursor = db.connection.execute("SELECT COUNT(*) FROM research_cache")
    stats["research_cache"] = cursor.fetchone()[0]

    # Count domain whitelist
    cursor = db.connection.execute("SELECT COUNT(*) FROM domain_whitelist")
    stats["domain_whitelist"] = cursor.fetchone()[0]

    # Database size
    stats["size_kb"] = db.get_database_size() / 1024

    return stats


def clean_database(db: Database) -> dict:
    """
    Clean all data from database while preserving domain whitelist.

    Returns:
        dict: Statistics about deleted records
    """
    stats_before = get_database_stats(db)

    with db.transaction():
        # Delete all sessions (CASCADE will handle concepts and stage_data)
        db.connection.execute("DELETE FROM sessions")

        # Delete all research cache
        db.connection.execute("DELETE FROM research_cache")

        # Keep domain_whitelist intact

    # Vacuum to reclaim space
    db.connection.execute("VACUUM")

    stats_after = get_database_stats(db)

    return {
        "deleted": {
            "sessions": stats_before["sessions"],
            "concepts": stats_before["concepts"],
            "stage_data": stats_before["stage_data"],
            "research_cache": stats_before["research_cache"],
        },
        "preserved": {
            "domain_whitelist": stats_after["domain_whitelist"],
        },
        "size_before_kb": stats_before["size_kb"],
        "size_after_kb": stats_after["size_kb"],
        "size_reclaimed_kb": stats_before["size_kb"] - stats_after["size_kb"],
    }


def print_stats(stats: dict, label: str = "Database Statistics"):
    """Print formatted database statistics."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print('=' * 60)

    if "deleted" in stats:
        print("\n🗑️  Deleted:")
        print(f"   Sessions:        {stats['deleted']['sessions']:>6}")
        print(f"   Concepts:        {stats['deleted']['concepts']:>6}")
        print(f"   Stage Data:      {stats['deleted']['stage_data']:>6}")
        print(f"   Research Cache:  {stats['deleted']['research_cache']:>6}")

        print("\n✅ Preserved:")
        print(f"   Domain Whitelist: {stats['preserved']['domain_whitelist']:>6}")

        print("\n💾 Storage:")
        print(f"   Before:   {stats['size_before_kb']:>8.2f} KB")
        print(f"   After:    {stats['size_after_kb']:>8.2f} KB")
        print(f"   Reclaimed: {stats['size_reclaimed_kb']:>8.2f} KB")
    else:
        print(f"\n📊 Current Data:")
        print(f"   Sessions:        {stats.get('sessions', 0):>6}")
        print(f"   Concepts:        {stats.get('concepts', 0):>6}")
        print(f"   Stage Data:      {stats.get('stage_data', 0):>6}")
        print(f"   Research Cache:  {stats.get('research_cache', 0):>6}")
        print(f"   Domain Whitelist: {stats.get('domain_whitelist', 0):>6}")
        print(f"\n💾 Size: {stats.get('size_kb', 0):.2f} KB")

    print('=' * 60 + '\n')


async def main():
    """Main cleanup routine."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean Short-Term Memory MCP database (complete reset)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a backup before cleaning",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  🧹 Short-Term Memory MCP - Database Cleanup")
    print("=" * 60)

    # Check if database exists
    if not DB_PATH.exists():
        print(f"\n❌ Database not found at: {DB_PATH}")
        print("   Nothing to clean!")
        sys.exit(0)

    # Get current stats
    db = get_db()
    current_stats = get_database_stats(db)
    print_stats(current_stats, "Current Database State")

    # Check if database is already empty
    total_records = (
        current_stats["sessions"]
        + current_stats["concepts"]
        + current_stats["stage_data"]
        + current_stats["research_cache"]
    )

    if total_records == 0:
        print("✨ Database is already clean! Nothing to delete.\n")
        sys.exit(0)

    # Confirmation
    if not args.yes:
        print("⚠️  WARNING: This will DELETE ALL DATA except domain whitelist!")
        print(f"   - {current_stats['sessions']} sessions")
        print(f"   - {current_stats['concepts']} concepts")
        print(f"   - {current_stats['stage_data']} stage data entries")
        print(f"   - {current_stats['research_cache']} research cache entries")
        print(f"\n   Domain whitelist ({current_stats['domain_whitelist']} domains) will be PRESERVED.")

        confirm = input("\n   Type 'RESET' to confirm deletion: ")

        if confirm != "RESET":
            print("\n❌ Cancelled - No changes made\n")
            sys.exit(1)

    # Create backup if requested
    if args.backup:
        print("\n📦 Creating backup...")
        backup_path = create_backup(DB_PATH)
        print(f"   ✓ Backup saved to: {backup_path}")

    # Perform cleanup
    print("\n🧹 Cleaning database...")
    cleanup_stats = clean_database(db)

    # Verify health
    print("\n🔍 Verifying database health...")
    health = db.get_health_status()

    if health["status"] != "healthy":
        print(f"   ⚠️  Warning: Database health check returned: {health['status']}")
        for issue in health.get("issues", []):
            print(f"      - {issue}")
    else:
        print("   ✓ Database is healthy")

    # Print results
    print_stats(cleanup_stats, "Cleanup Results")

    print("✅ Database cleanup complete!\n")
    print("💡 Tip: Create an alias for easy future use:")
    print(f"   alias clean-short-term='python {Path(__file__).resolve()}'")
    print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
