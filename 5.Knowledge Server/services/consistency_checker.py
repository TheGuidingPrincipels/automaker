"""
Consistency checker for dual storage system.

Verifies synchronization between Neo4j and ChromaDB databases.
"""

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from neo4j.exceptions import DatabaseError as Neo4jDatabaseError
from neo4j.exceptions import ServiceUnavailable, TransientError

from services.chromadb_service import ChromaDbService
from services.neo4j_service import Neo4jService


logger = logging.getLogger(__name__)


@dataclass
class ConsistencyReport:
    """Report of consistency check results."""

    neo4j_count: int
    chromadb_count: int
    matching_count: int
    neo4j_only: list[str]
    chromadb_only: list[str]
    mismatched: list[dict[str, Any]]
    is_consistent: bool
    checked_at: datetime

    def __str__(self) -> str:
        """Human-readable report."""
        lines = [
            "=== Dual Storage Consistency Report ===",
            f"Checked at: {self.checked_at.isoformat()}",
            f"Neo4j concepts: {self.neo4j_count}",
            f"ChromaDB concepts: {self.chromadb_count}",
            f"Matching: {self.matching_count}",
            "",
            f"Status: {'✅ CONSISTENT' if self.is_consistent else '❌ INCONSISTENT'}",
        ]

        if self.neo4j_only:
            lines.append(f"\nNeo4j only ({len(self.neo4j_only)}): {self.neo4j_only[:5]}")

        if self.chromadb_only:
            lines.append(f"\nChromaDB only ({len(self.chromadb_only)}): {self.chromadb_only[:5]}")

        if self.mismatched:
            lines.append(
                f"\nMismatched ({len(self.mismatched)}): {[m['concept_id'] for m in self.mismatched[:5]]}"
            )

        return "\n".join(lines)


class ConsistencyChecker:
    """
    Verifies consistency between Neo4j and ChromaDB.

    Compares concept data across both databases and identifies:
    - Concepts present in one DB but not the other
    - Concepts with mismatched metadata
    - Overall consistency statistics

    Example:
        ```python
        checker = ConsistencyChecker(neo4j_service, chromadb_service, db_path)
        report = checker.check_consistency()

        if not report.is_consistent:
            print(f"Found {len(report.neo4j_only)} concepts only in Neo4j")
            print(f"Found {len(report.chromadb_only)} concepts only in ChromaDB")
        ```
    """

    def __init__(
        self, neo4j: Neo4jService, chromadb: ChromaDbService, db_path: str | None = None
    ) -> None:
        """
        Initialize ConsistencyChecker.

        Args:
            neo4j: Neo4j service instance
            chromadb: ChromaDB service instance
            db_path: Optional path to SQLite database for storing snapshots
        """
        self.neo4j = neo4j
        self.chromadb = chromadb
        self.db_path = db_path

        logger.info("ConsistencyChecker initialized")

    def get_neo4j_concepts(self, include_deleted: bool = False) -> dict[str, dict[str, Any]]:
        """
        Get all concepts from Neo4j.

        Args:
            include_deleted: Whether to include soft-deleted concepts

        Returns:
            Dictionary mapping concept_id to concept data
        """
        try:
            # Query to get all concepts
            if include_deleted:
                query = """
                MATCH (c:Concept)
                RETURN c.concept_id AS concept_id, c.name AS name,
                       c.area AS area, c.topic AS topic,
                       c.subtopic AS subtopic, c.confidence_score AS confidence_score,
                       c.deleted AS deleted
                """
            else:
                query = """
                MATCH (c:Concept)
                WHERE c.deleted IS NULL OR c.deleted = false
                RETURN c.concept_id AS concept_id, c.name AS name,
                       c.area AS area, c.topic AS topic,
                       c.subtopic AS subtopic, c.confidence_score AS confidence_score,
                       c.deleted AS deleted
                """

            results = self.neo4j.execute_read(query, {})

            concepts = {}
            for record in results:
                concept_id = record["concept_id"]
                concepts[concept_id] = {
                    "name": record.get("name"),
                    "area": record.get("area"),
                    "topic": record.get("topic"),
                    "subtopic": record.get("subtopic"),
                    "confidence_score": record.get("confidence_score"),
                    "deleted": record.get("deleted", False)
                }

            logger.info(f"Retrieved {len(concepts)} concepts from Neo4j")
            return concepts

        except (ServiceUnavailable, TransientError, Neo4jDatabaseError) as e:
            logger.error(f"Database error getting Neo4j concepts: {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.critical(f"Unexpected error getting Neo4j concepts: {e}", exc_info=True)
            raise

    def get_chromadb_concepts(self) -> dict[str, dict[str, Any]]:
        """
        Get all concepts from ChromaDB.

        Returns:
            Dictionary mapping concept_id to concept metadata
        """
        try:
            collection = self.chromadb.get_collection()

            # Get all documents with their metadata
            results = collection.get(include=["metadatas"])

            concepts = {}
            for i, concept_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i] if i < len(results["metadatas"]) else {}
                concepts[concept_id] = {
                    "name": metadata.get("name"),
                    "area": metadata.get("area"),
                    "topic": metadata.get("topic"),
                    "subtopic": metadata.get("subtopic"),
                    "confidence_score": metadata.get("confidence_score")
                }

            logger.info(f"Retrieved {len(concepts)} concepts from ChromaDB")
            return concepts

        except (ValueError, KeyError, ConnectionError) as e:
            logger.error(f"Error getting ChromaDB concepts: {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.critical(f"Unexpected error getting ChromaDB concepts: {e}", exc_info=True)
            raise

    def find_discrepancies(
        self,
        neo4j_concepts: dict[str, dict[str, Any]],
        chromadb_concepts: dict[str, dict[str, Any]],
    ) -> tuple[list[str], list[str], list[dict[str, Any]]]:
        """
        Find discrepancies between Neo4j and ChromaDB.

        Args:
            neo4j_concepts: Concepts from Neo4j
            chromadb_concepts: Concepts from ChromaDB

        Returns:
            Tuple of (neo4j_only, chromadb_only, mismatched)
        """
        neo4j_ids = set(neo4j_concepts.keys())
        chromadb_ids = set(chromadb_concepts.keys())

        # Find concepts only in one database
        neo4j_only = list(neo4j_ids - chromadb_ids)
        chromadb_only = list(chromadb_ids - neo4j_ids)

        # Find mismatched metadata in common concepts
        mismatched = []
        common_ids = neo4j_ids & chromadb_ids

        for concept_id in common_ids:
            neo4j_data = neo4j_concepts[concept_id]
            chromadb_data = chromadb_concepts[concept_id]

            # Compare metadata fields
            differences = []
            for field in ['name', 'area', 'topic', 'subtopic', 'confidence_score']:
                neo4j_val = neo4j_data.get(field)
                chromadb_val = chromadb_data.get(field)

                # Handle None and missing values
                if neo4j_val != chromadb_val:
                    # Allow for type differences (int vs float for confidence_score)
                    if field == 'confidence_score':
                        try:
                            if float(neo4j_val or 0) == float(chromadb_val or 0):
                                continue
                        except (ValueError, TypeError):
                            pass

                    differences.append(
                        {"field": field, "neo4j": neo4j_val, "chromadb": chromadb_val}
                    )

            if differences:
                mismatched.append({"concept_id": concept_id, "differences": differences})

        logger.info(
            f"Found discrepancies: {len(neo4j_only)} Neo4j-only, "
            f"{len(chromadb_only)} ChromaDB-only, {len(mismatched)} mismatched"
        )

        return neo4j_only, chromadb_only, mismatched

    def check_consistency(
        self, include_deleted: bool = False, save_snapshot: bool = True
    ) -> ConsistencyReport:
        """
        Check consistency between Neo4j and ChromaDB.

        Args:
            include_deleted: Whether to include soft-deleted concepts in Neo4j
            save_snapshot: Whether to save snapshot to database

        Returns:
            ConsistencyReport with detailed findings
        """
        logger.info("Starting consistency check...")

        # Get concepts from both databases
        neo4j_concepts = self.get_neo4j_concepts(include_deleted=include_deleted)
        chromadb_concepts = self.get_chromadb_concepts()

        # Find discrepancies
        neo4j_only, chromadb_only, mismatched = self.find_discrepancies(
            neo4j_concepts, chromadb_concepts
        )

        # Calculate statistics
        neo4j_count = len(neo4j_concepts)
        chromadb_count = len(chromadb_concepts)
        matching_count = len(set(neo4j_concepts.keys()) & set(chromadb_concepts.keys())) - len(
            mismatched
        )

        # Determine if consistent
        is_consistent = len(neo4j_only) == 0 and len(chromadb_only) == 0 and len(mismatched) == 0

        # Create report
        report = ConsistencyReport(
            neo4j_count=neo4j_count,
            chromadb_count=chromadb_count,
            matching_count=matching_count,
            neo4j_only=neo4j_only,
            chromadb_only=chromadb_only,
            mismatched=mismatched,
            is_consistent=is_consistent,
            checked_at=datetime.utcnow(),
        )

        logger.info(f"Consistency check complete: {report.is_consistent}")

        # Save snapshot if requested
        if save_snapshot and self.db_path:
            self.save_snapshot(report)

        return report

    def save_snapshot(self, report: ConsistencyReport) -> str:
        """
        Save consistency check snapshot to database.

        Args:
            report: Consistency report to save

        Returns:
            Snapshot ID
        """
        if not self.db_path:
            logger.warning("No database path configured, cannot save snapshot")
            return ""

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Generate snapshot ID
                snapshot_id = str(uuid.uuid4())

                # Prepare discrepancies as text
                discrepancies = []
                if report.neo4j_only:
                    discrepancies.append(f"Neo4j only: {report.neo4j_only[:10]}")
                if report.chromadb_only:
                    discrepancies.append(f"ChromaDB only: {report.chromadb_only[:10]}")
                if report.mismatched:
                    mismatched_ids = [m["concept_id"] for m in report.mismatched[:10]]
                    discrepancies.append(f"Mismatched: {mismatched_ids}")

                discrepancies_text = "; ".join(discrepancies) if discrepancies else "None"

                # Insert snapshot
                cursor.execute(
                    """
                    INSERT INTO consistency_snapshots
                    (snapshot_id, neo4j_count, chromadb_count, discrepancies, checked_at, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        snapshot_id,
                        report.neo4j_count,
                        report.chromadb_count,
                        discrepancies_text,
                        report.checked_at.isoformat(),
                        "consistent" if report.is_consistent else "inconsistent",
                    ),
                )

                # Commit is automatic on context manager exit (success)
                logger.info(f"Saved consistency snapshot: {snapshot_id}")
                return snapshot_id

        except sqlite3.Error as e:
            logger.error(f"Database error saving consistency snapshot: {e}", exc_info=True)
            return ""
        except Exception as e:
            logger.critical(f"Unexpected error saving consistency snapshot: {e}", exc_info=True)
            raise

    def get_latest_snapshot(self) -> dict[str, Any] | None:
        """
        Get the most recent consistency snapshot.

        Returns:
            Dictionary with snapshot data, or None if no snapshots exist
        """
        if not self.db_path:
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT snapshot_id, neo4j_count, chromadb_count,
                           discrepancies, checked_at, status
                    FROM consistency_snapshots
                    ORDER BY checked_at DESC
                    LIMIT 1
                """
                )

                row = cursor.fetchone()

                if not row:
                    return None

                return {
                    "snapshot_id": row[0],
                    "neo4j_count": row[1],
                    "chromadb_count": row[2],
                    "discrepancies": row[3],
                    "checked_at": row[4],
                    "status": row[5],
                }

        except sqlite3.Error as e:
            logger.error(f"Database error getting latest snapshot: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.critical(f"Unexpected error getting latest snapshot: {e}", exc_info=True)
            raise
