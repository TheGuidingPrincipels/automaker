"""
Migration script to add UNIQUE constraint on (aggregate_id, version)

This migration adds a UNIQUE INDEX to prevent race conditions in concurrent
event appends to the same aggregate.

Run this on existing databases to upgrade the schema.
"""

import sqlite3
import sys
from pathlib import Path


def check_for_duplicate_versions(db_path: Path) -> bool:
    """
    Check if database has any duplicate (aggregate_id, version) pairs

    Returns:
        True if duplicates found, False otherwise
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT aggregate_id, version, COUNT(*) as count
            FROM events
            GROUP BY aggregate_id, version
            HAVING count > 1
        """
        )

        duplicates = cursor.fetchall()

        if duplicates:
            print("\n⚠️  WARNING: Found duplicate (aggregate_id, version) pairs:")
            for agg_id, version, count in duplicates:
                print(f"   - aggregate_id={agg_id}, version={version}: {count} occurrences")
            return True

        return False

    finally:
        conn.close()


def constraint_exists(db_path: Path) -> bool:
    """Check if UNIQUE constraint already exists"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_aggregate_version'
        """
        )

        result = cursor.fetchone()
        return result is not None

    finally:
        conn.close()


def add_unique_constraint(db_path: Path) -> bool:
    """
    Add UNIQUE INDEX on (aggregate_id, version)

    Returns:
        True if successful, False otherwise
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("\n📝 Adding UNIQUE constraint on (aggregate_id, version)...")

        cursor.execute(
            """
            CREATE UNIQUE INDEX idx_aggregate_version
            ON events(aggregate_id, version)
        """
        )

        conn.commit()
        print("✅ UNIQUE constraint added successfully!")
        return True

    except sqlite3.IntegrityError as e:
        print("\n❌ ERROR: Cannot add UNIQUE constraint - duplicate data exists")
        print(f"   Details: {e}")
        print("\n   You must resolve duplicate versions before running this migration.")
        print("   Run this script with --check flag to see duplicates.")
        conn.rollback()
        return False

    except Exception as e:
        print(f"\n❌ ERROR: Failed to add constraint: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def migrate(db_path: Path, check_only: bool = False) -> bool:
    """
    Run migration to add UNIQUE constraint

    Args:
        db_path: Path to database file
        check_only: If True, only check for duplicates, don't apply migration

    Returns:
        True if migration successful or not needed, False otherwise
    """
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False

    print(f"🔍 Checking database at: {db_path}")

    # Check if constraint already exists
    if constraint_exists(db_path):
        print("✅ UNIQUE constraint already exists - no migration needed")
        return True

    # Check for duplicate data
    has_duplicates = check_for_duplicate_versions(db_path)

    if check_only:
        if has_duplicates:
            print("\n❌ Database has duplicate versions - migration will fail")
            print("   Fix duplicates before running migration.")
            return False
        else:
            print("\n✅ No duplicate versions found - safe to migrate")
            return True

    if has_duplicates:
        print("\n❌ Cannot proceed with migration - duplicate data exists")
        print("   Please fix duplicates first or delete the database and reinitialize.")
        return False

    # Apply migration
    return add_unique_constraint(db_path)


def main():
    """Main migration entry point"""

    # Determine database path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "data" / "events.db"

    # Parse command line args
    check_only = "--check" in sys.argv

    print("=" * 60)
    print("Migration: Add UNIQUE Constraint on (aggregate_id, version)")
    print("=" * 60)

    if check_only:
        print("\n🔍 CHECK MODE - No changes will be made\n")

    success = migrate(db_path, check_only=check_only)

    print("\n" + "=" * 60)

    if success:
        if check_only:
            print("✅ Check complete - database is ready for migration")
        else:
            print("✅ Migration complete!")
        return 0
    else:
        print("❌ Migration failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
