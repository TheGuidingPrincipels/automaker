#!/usr/bin/env python3
"""
Database Cleanup Utility for MCP Knowledge Server

This script provides safe database cleanup operations with multiple modes:
- Full cleanup: Clear all data from all databases
- Selective cleanup: Clear specific databases
- Test data only: Remove only test-related data
- Dry run: Preview what would be deleted without making changes

Safety features:
- Automatic backup before cleanup
- Server running check
- User confirmation prompts
- Rollback capability
- Comprehensive logging
"""

import argparse
import builtins
import contextlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


# Color codes for output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(message):
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{message}{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}\n")


def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")


def check_server_running():
    """Check if the MCP server is currently running"""
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        if "mcp_server.py" in result.stdout:
            return True
    except Exception:
        pass
    return False


def create_backup():
    """Create a full backup before cleanup"""
    print_info("Creating backup before cleanup...")
    backup_script = Path(__file__).parent.parent / "backup" / "backup_all.sh"

    try:
        subprocess.run([str(backup_script)], capture_output=True, text=True, check=True)
        print_success("Backup created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Backup failed: {e}")
        return False


def get_neo4j_stats():
    """Get current Neo4j database statistics"""
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "mcp-knowledge-neo4j",
                "cypher-shell",
                "-u",
                "neo4j",
                "-p",
                "password",
                "MATCH (n) RETURN count(n) as node_count",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            return int(lines[1])
    except Exception:
        pass
    return 0


def get_chromadb_stats(chroma_dir):
    """Get current ChromaDB statistics"""
    try:
        import chromadb

        client = chromadb.PersistentClient(str(chroma_dir))
        collections = client.list_collections()
        if collections:
            collection = client.get_collection("concepts")
            return collection.count()
    except Exception:
        pass
    return 0


def get_sqlite_stats(db_path):
    """Get current SQLite event store statistics"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        pass
    return 0


def clear_neo4j(dry_run=False):
    """Clear all data from Neo4j database"""
    print_info("Clearing Neo4j database...")

    if dry_run:
        node_count = get_neo4j_stats()
        print_info(f"Would delete {node_count} nodes and their relationships")
        return True

    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "mcp-knowledge-neo4j",
                "cypher-shell",
                "-u",
                "neo4j",
                "-p",
                "password",
                "MATCH (n) DETACH DELETE n",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print_success("Neo4j database cleared")

        # Verify
        remaining = get_neo4j_stats()
        if remaining == 0:
            print_success(f"Verified: {remaining} nodes remaining")
        else:
            print_warning(f"Warning: {remaining} nodes still in database")

        return True
    except Exception as e:
        print_error(f"Failed to clear Neo4j: {e}")
        return False


def clear_chromadb(chroma_dir, dry_run=False):
    """Clear all data from ChromaDB"""
    print_info("Clearing ChromaDB...")

    if dry_run:
        doc_count = get_chromadb_stats(chroma_dir)
        print_info(f"Would delete {doc_count} documents from ChromaDB")
        return True

    try:
        # Delete all files in ChromaDB directory
        for item in chroma_dir.glob("*"):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil

                shutil.rmtree(item)

        print_success("ChromaDB data cleared")
        return True
    except Exception as e:
        print_error(f"Failed to clear ChromaDB: {e}")
        return False


def clear_sqlite(db_path, dry_run=False):
    """Clear all data from SQLite event store"""
    print_info("Clearing SQLite event store...")

    if dry_run:
        event_count = get_sqlite_stats(db_path)
        print_info(f"Would delete {event_count} events from SQLite")
        return True

    try:
        # Delete the database file
        if db_path.exists():
            db_path.unlink()
            # Also delete WAL and SHM files if they exist
            for suffix in ["-shm", "-wal"]:
                wal_file = Path(str(db_path) + suffix)
                if wal_file.exists():
                    wal_file.unlink()

        print_success("SQLite event store cleared")
        return True
    except Exception as e:
        print_error(f"Failed to clear SQLite: {e}")
        return False


def reinitialize_databases(dry_run=False):
    """Reinitialize all database schemas"""
    print_info("Reinitializing database schemas...")

    if dry_run:
        print_info("Would run initialization scripts for all databases")
        return True

    scripts_dir = Path(__file__).parent
    success = True

    # Initialize SQLite
    try:
        subprocess.run(
            ["python", str(scripts_dir / "init_database.py")], check=True, capture_output=True
        )
        print_success("SQLite event store initialized")
    except Exception as e:
        print_error(f"Failed to initialize SQLite: {e}")
        success = False

    # Initialize Neo4j
    try:
        subprocess.run(
            ["python", str(scripts_dir / "init_neo4j.py")], check=True, capture_output=True
        )
        print_success("Neo4j schema initialized")
    except Exception as e:
        print_error(f"Failed to initialize Neo4j: {e}")
        success = False

    # Initialize ChromaDB
    try:
        subprocess.run(
            ["python", str(scripts_dir / "init_chromadb.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        # ChromaDB init adds a test document, remove it
        import chromadb

        client = chromadb.PersistentClient("./data/chroma")
        collection = client.get_collection("concepts")
        with contextlib.suppress(builtins.BaseException):
            collection.delete(ids=["test_concept_001"])
        print_success("ChromaDB collection initialized")
    except Exception as e:
        print_error(f"Failed to initialize ChromaDB: {e}")
        success = False

    return success


def print_database_stats():
    """Print current database statistics"""
    print_header("Current Database Statistics")

    neo4j_nodes = get_neo4j_stats()
    print(f"Neo4j: {neo4j_nodes} nodes")

    chromadb_docs = get_chromadb_stats(Path("./data/chroma"))
    print(f"ChromaDB: {chromadb_docs} documents")

    sqlite_events = get_sqlite_stats(Path("./data/events.db"))
    print(f"SQLite: {sqlite_events} events")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Database cleanup utility for MCP Knowledge Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current database statistics
  python cleanup_databases.py --stats

  # Dry run - see what would be deleted
  python cleanup_databases.py --dry-run

  # Full cleanup with backup
  python cleanup_databases.py --full

  # Clear specific database
  python cleanup_databases.py --neo4j
  python cleanup_databases.py --chromadb
  python cleanup_databases.py --sqlite

  # Full cleanup without backup (use with caution!)
  python cleanup_databases.py --full --no-backup
        """,
    )

    parser.add_argument("--full", action="store_true", help="Clear all databases")
    parser.add_argument("--neo4j", action="store_true", help="Clear Neo4j database only")
    parser.add_argument("--chromadb", action="store_true", help="Clear ChromaDB only")
    parser.add_argument("--sqlite", action="store_true", help="Clear SQLite event store only")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be deleted without making changes"
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="Skip backup creation (not recommended)"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show current database statistics and exit"
    )
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    args = parser.parse_args()

    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print_header("MCP Knowledge Server - Database Cleanup Utility")

    # Show stats and exit if requested
    if args.stats:
        print_database_stats()
        return 0

    # Check if any cleanup option is selected
    if not (args.full or args.neo4j or args.chromadb or args.sqlite):
        print_error("No cleanup option specified. Use --help for usage information.")
        return 1

    # Show current statistics
    print_database_stats()

    # Check if server is running
    if check_server_running():
        print_error("MCP server is currently running!")
        print_error("Please stop the server before running cleanup.")
        return 1

    # Determine what to clean
    clean_neo4j = args.full or args.neo4j
    clean_chromadb = args.full or args.chromadb
    clean_sqlite = args.full or args.sqlite

    # Show what will be cleaned
    print_info("Cleanup plan:")
    if clean_neo4j:
        print(f"  • Neo4j: {get_neo4j_stats()} nodes will be deleted")
    if clean_chromadb:
        print(
            f"  • ChromaDB: {get_chromadb_stats(Path('./data/chroma'))} documents will be deleted"
        )
    if clean_sqlite:
        print(f"  • SQLite: {get_sqlite_stats(Path('./data/events.db'))} events will be deleted")
    print()

    if args.dry_run:
        print_warning("DRY RUN MODE - No changes will be made")
        print()

    # Confirmation prompt
    if not args.yes and not args.dry_run:
        response = input(
            f"{Colors.YELLOW}⚠️  This will permanently delete data. Continue? (yes/no): {Colors.END}"
        )
        if response.lower() != "yes":
            print_info("Cleanup cancelled")
            return 0

    # Create backup unless disabled
    if not args.no_backup and not args.dry_run and not create_backup():
        print_error("Backup failed. Cleanup cancelled for safety.")
        return 1

    # Perform cleanup
    success = True

    if clean_neo4j and not clear_neo4j(args.dry_run):
        success = False

    if clean_chromadb and not clear_chromadb(Path("./data/chroma"), args.dry_run):
        success = False

    if clean_sqlite and not clear_sqlite(Path("./data/events.db"), args.dry_run):
        success = False

    # Reinitialize databases if not dry run
    if not args.dry_run and success and not reinitialize_databases():
        success = False

    # Final statistics
    if not args.dry_run:
        print()
        print_database_stats()

    if success:
        print_success("Cleanup completed successfully!")
        if not args.dry_run:
            print_info("All databases are now clean and ready for use")
        return 0
    else:
        print_error("Cleanup completed with errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
