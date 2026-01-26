#!/usr/bin/env python3
"""
Duplicate Concept Cleanup Script

This script identifies and consolidates duplicate concepts in the knowledge base.
Duplicates are identified by matching name + area + topic.

Process:
1. Finds all duplicate concept groups
2. For each group, keeps the oldest concept (earliest created_at)
3. Migrates all relationships from duplicates to the kept concept
4. Soft-deletes duplicate concepts (sets deleted=true)
5. Removes duplicates from ChromaDB for consistency

Safety features:
- Dry run mode to preview changes
- Backup prompts before execution
- Detailed logging of all operations
- Verification step after cleanup
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.chromadb_service import ChromaDbService
from services.neo4j_service import Neo4jService


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str) -> None:
    """Print formatted header"""
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{message}{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.END}\n")


def print_success(message: str) -> None:
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_warning(message: str) -> None:
    """Print warning message"""
    print(f"{Colors.YELLOW}! {message}{Colors.END}")


def print_error(message: str) -> None:
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str) -> None:
    """Print info message"""
    print(f"{Colors.BLUE}→ {message}{Colors.END}")


class DuplicateCleanup:
    """Handles duplicate concept detection and consolidation"""

    def __init__(self, neo4j_service: Neo4jService, chromadb_service: ChromaDbService):
        self.neo4j = neo4j_service
        self.chromadb = chromadb_service

    def find_duplicates(self) -> list[dict[str, Any]]:
        """
        Find all duplicate concept groups.

        Returns:
            List of duplicate groups, each containing:
            - uniqueness_key: (name, area, topic)
            - concepts: List of concept IDs and created_at timestamps
        """
        query = """
        MATCH (c:Concept)
        WHERE (c.deleted IS NULL OR c.deleted = false)
        WITH c.name AS name,
             c.area AS area,
             c.topic AS topic,
             collect({
                 concept_id: c.concept_id,
                 created_at: c.created_at,
                 explanation: c.explanation
             }) AS concepts
        WHERE size(concepts) > 1
        RETURN name, area, topic, concepts
        ORDER BY size(concepts) DESC
        """

        try:
            results = self.neo4j.execute_read(query, {})

            duplicate_groups = []
            for row in results:
                duplicate_groups.append(
                    {
                        "name": row["name"],
                        "area": row["area"],
                        "topic": row["topic"],
                        "concepts": row["concepts"],
                        "count": len(row["concepts"]),
                    }
                )

            return duplicate_groups

        except Exception as e:
            logger.error(f"Error finding duplicates: {e}", exc_info=True)
            return []

    def consolidate_duplicate(
        self, duplicate_group: dict[str, Any], dry_run: bool = False
    ) -> tuple[bool, str]:
        """
        Consolidate a duplicate group by keeping the oldest concept.

        Process:
        1. Sort concepts by created_at, keep oldest
        2. Migrate all relationships from duplicates to kept concept
        3. Soft-delete duplicate concepts
        4. Remove duplicates from ChromaDB

        Args:
            duplicate_group: Group information from find_duplicates()
            dry_run: If True, only log what would be done

        Returns:
            Tuple of (success, message)
        """
        try:
            concepts = duplicate_group["concepts"]

            # Sort by created_at to find oldest (keep this one)
            sorted_concepts = sorted(concepts, key=lambda c: c["created_at"])
            kept_concept = sorted_concepts[0]
            duplicates_to_remove = sorted_concepts[1:]

            kept_id = kept_concept["concept_id"]
            duplicate_ids = [c["concept_id"] for c in duplicates_to_remove]

            print_info(f"Keeping: {kept_id} (created: {kept_concept['created_at']})")
            for dup in duplicates_to_remove:
                print_info(f"Removing: {dup['concept_id']} (created: {dup['created_at']})")

            if dry_run:
                print_warning("DRY RUN - No changes made")
                return True, "Dry run completed"

            # Step 1: Migrate incoming relationships (X -> duplicate) to (X -> kept)
            migrate_incoming_query = """
            MATCH (source:Concept)-[r]->(duplicate:Concept)
            WHERE duplicate.concept_id IN $duplicate_ids
            AND NOT (source.concept_id = $kept_id)
            WITH source, duplicate, type(r) AS rel_type, properties(r) AS rel_props
            MATCH (kept:Concept {concept_id: $kept_id})
            MERGE (source)-[new_rel]->(kept)
            SET new_rel = rel_props
            RETURN count(*) AS migrated_incoming
            """

            # Step 2: Migrate outgoing relationships (duplicate -> X) to (kept -> X)
            migrate_outgoing_query = """
            MATCH (duplicate:Concept)-[r]->(target:Concept)
            WHERE duplicate.concept_id IN $duplicate_ids
            AND NOT (target.concept_id = $kept_id)
            WITH duplicate, target, type(r) AS rel_type, properties(r) AS rel_props
            MATCH (kept:Concept {concept_id: $kept_id})
            MERGE (kept)-[new_rel]->(target)
            SET new_rel = rel_props
            RETURN count(*) AS migrated_outgoing
            """

            # Step 3: Delete old relationships
            delete_old_rels_query = """
            MATCH (duplicate:Concept)-[r]-(other:Concept)
            WHERE duplicate.concept_id IN $duplicate_ids
            DELETE r
            RETURN count(*) AS deleted_rels
            """

            # Step 4: Soft-delete duplicate concepts
            soft_delete_query = """
            MATCH (c:Concept)
            WHERE c.concept_id IN $duplicate_ids
            SET c.deleted = true,
                c.deleted_at = datetime()
            RETURN count(*) AS deleted_count
            """

            params = {"kept_id": kept_id, "duplicate_ids": duplicate_ids}

            # Execute migration and deletion
            incoming_result = self.neo4j.execute_write(migrate_incoming_query, params)
            outgoing_result = self.neo4j.execute_write(migrate_outgoing_query, params)
            delete_rels_result = self.neo4j.execute_write(delete_old_rels_query, params)
            soft_delete_result = self.neo4j.execute_write(soft_delete_query, params)

            migrated_incoming = incoming_result[0]["migrated_incoming"] if incoming_result else 0
            migrated_outgoing = outgoing_result[0]["migrated_outgoing"] if outgoing_result else 0
            deleted_rels = delete_rels_result[0]["deleted_rels"] if delete_rels_result else 0
            deleted_count = soft_delete_result[0]["deleted_count"] if soft_delete_result else 0

            print_success(f"Migrated {migrated_incoming} incoming relationships")
            print_success(f"Migrated {migrated_outgoing} outgoing relationships")
            print_success(f"Deleted {deleted_rels} old relationships")
            print_success(f"Soft-deleted {deleted_count} duplicate concepts")

            # Step 5: Remove duplicates from ChromaDB
            try:
                collection = self.chromadb.get_collection()
                if collection:
                    collection.delete(ids=duplicate_ids)
                    print_success(f"Removed {len(duplicate_ids)} concepts from ChromaDB")
            except Exception as e:
                print_warning(f"ChromaDB cleanup failed (non-critical): {e}")

            return True, f"Consolidated {len(duplicate_ids)} duplicates into {kept_id}"

        except Exception as e:
            error_msg = f"Error consolidating duplicate: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def verify_no_duplicates(self) -> tuple[bool, int]:
        """
        Verify that no duplicates remain after cleanup.

        Returns:
            Tuple of (success, remaining_duplicate_count)
        """
        duplicates = self.find_duplicates()
        return len(duplicates) == 0, len(duplicates)


async def main():
    """Main entry point"""
    print_header("Duplicate Concept Cleanup Utility")

    # Parse command line arguments
    dry_run = "--dry-run" in sys.argv
    auto_confirm = "--yes" in sys.argv

    if dry_run:
        print_warning("DRY RUN MODE - No changes will be made")
        print()

    # Initialize services
    print_info("Initializing services...")

    try:
        # Initialize Neo4j
        neo4j_service = Neo4jService(
            uri=Config.NEO4J_URI, user=Config.NEO4J_USER, password=Config.NEO4J_PASSWORD
        )

        if not neo4j_service.connect():
            print_error("Failed to connect to Neo4j")
            print_info("Please ensure Neo4j is running: docker-compose up -d")
            return 1

        print_success("Connected to Neo4j")

        # Initialize ChromaDB
        chromadb_service = ChromaDbService(
            persist_directory=Config.CHROMA_PERSIST_DIRECTORY, collection_name="concepts"
        )

        if not chromadb_service.connect():
            print_error("Failed to connect to ChromaDB")
            return 1

        print_success("Connected to ChromaDB")

        # Create cleanup instance
        cleanup = DuplicateCleanup(neo4j_service, chromadb_service)

        # Find duplicates
        print_header("Scanning for Duplicate Concepts")
        duplicate_groups = cleanup.find_duplicates()

        if not duplicate_groups:
            print_success("No duplicate concepts found!")
            return 0

        # Display summary
        print_info(f"Found {len(duplicate_groups)} duplicate groups")
        print()

        total_duplicates = sum(g["count"] - 1 for g in duplicate_groups)
        print_info(f"Total concepts to be consolidated: {total_duplicates}")
        print()

        # Display details
        for i, group in enumerate(duplicate_groups, 1):
            print(f"{Colors.BOLD}Group {i}:{Colors.END}")
            print(f"  Name: {group['name']}")
            print(f"  Area: {group['area'] or '(none)'}")
            print(f"  Topic: {group['topic'] or '(none)'}")
            print(f"  Duplicates: {group['count']}")
            print()

        # Confirmation prompt
        if not dry_run and not auto_confirm:
            print_warning("This will consolidate duplicates and soft-delete older versions.")
            response = input(f"\n{Colors.BOLD}Proceed with cleanup? (yes/no): {Colors.END}")
            if response.lower() not in ["yes", "y"]:
                print_info("Cleanup cancelled")
                return 0
            print()

        # Process each duplicate group
        print_header("Processing Duplicate Groups")

        success_count = 0
        failure_count = 0

        for i, group in enumerate(duplicate_groups, 1):
            print(f"\n{Colors.BOLD}Processing group {i}/{len(duplicate_groups)}:{Colors.END}")
            print(f"  {group['name']} ({group['area']}/{group['topic']})")
            print()

            success, message = cleanup.consolidate_duplicate(group, dry_run=dry_run)

            if success:
                success_count += 1
            else:
                failure_count += 1
                print_error(f"Failed: {message}")

        # Verification
        if not dry_run:
            print_header("Verification")
            verified, remaining = cleanup.verify_no_duplicates()

            if verified:
                print_success("Verification passed - no duplicates remain")
            else:
                print_warning(f"Verification found {remaining} duplicate groups remaining")

        # Summary
        print_header("Summary")
        print_info(f"Groups processed: {len(duplicate_groups)}")
        print_success(f"Successful: {success_count}")
        if failure_count > 0:
            print_error(f"Failed: {failure_count}")

        # Cleanup connections
        neo4j_service.close()
        print()
        print_success("Cleanup complete!")

        return 0 if failure_count == 0 else 1

    except Exception as e:
        print_error(f"Fatal error: {e}")
        logger.error("Fatal error in cleanup script", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
