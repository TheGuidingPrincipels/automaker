"""
Data access layer for confidence scoring system.

Provides Neo4j queries for retrieving concept data, relationships, and review history
needed for confidence calculation.
"""

import asyncio
from collections import Counter
from datetime import datetime

from services.confidence.config import ConfidenceConfig
from services.confidence.models import (
    ConceptData,
    Error,
    ErrorCode,
    RelationshipData,
    ReviewData,
    Success,
)


class DataAccessLayer:
    """
    Data access layer for confidence score calculations.

    This class provides specialized Neo4j queries for retrieving data needed
    to calculate confidence scores. It is separate from the main repository
    because:

    1. **Specialized Queries**: Runs aggregate and graph traversal queries
       specific to confidence calculation (relationships, review history, tau)
    2. **Async Context**: Designed for async background workers
    3. **Shared Sessions**: Uses Neo4jService wrapped in AsyncNeo4jSessionAdapter,
       NOT creating its own database connections

    Note:
        This is a READ-ONLY data access layer. All writes must go through
        DualStorageRepository to maintain event sourcing integrity.

    See docs/adr/001-data-access-patterns.md for architecture guidelines.

    Queries provided:
        - get_concept_for_confidence(): Fetch concept data for scoring
        - get_concept_relationships(): Count and type relationships
        - get_review_history(): Fetch review data for retention calculation
        - get_concept_tau(): Get retention decay constant
    """

    def __init__(self, neo4j_session):
        """
        Initialize data access layer with Neo4j session.

        Args:
            neo4j_session: Neo4j session or driver instance
        """
        self.session = neo4j_session

    async def get_concept_for_confidence(self, concept_id: str) -> Success | Error:
        """
        Fetch concept with all fields needed for confidence calculation.

        Args:
            concept_id: Unique identifier for the concept

        Returns:
            Success(ConceptData) if concept found
            Error(NOT_FOUND) if concept doesn't exist
            Error(DATABASE_ERROR) if Neo4j query fails
        """
        try:
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            RETURN c.concept_id AS id,
                   c.name AS name,
                   c.explanation AS explanation,
                   c.created_at AS created_at,
                   c.last_reviewed_at AS last_reviewed_at,
                   c.tags AS tags,
                   c.examples AS examples,
                   c.area AS area,
                   c.topic AS topic,
                   c.subtopic AS subtopic
            """

            result = await self.session.run(query, concept_id=concept_id)
            record = result.single()
            if asyncio.iscoroutine(record):
                record = await record

            if not record:
                return Error(f"Concept not found: {concept_id}", ErrorCode.NOT_FOUND)

            concept_data = ConceptData(
                id=record["id"],
                name=record["name"],
                explanation=record["explanation"],
                created_at=datetime.fromisoformat(record["created_at"]),
                last_reviewed_at=(
                    datetime.fromisoformat(record["last_reviewed_at"])
                    if record["last_reviewed_at"]
                    else None
                ),
                tags=record["tags"] or [],
                examples=record["examples"] or [],
                area=record.get("area"),
                topic=record.get("topic"),
                subtopic=record.get("subtopic"),
            )

            return Success(concept_data)

        except Exception as e:
            return Error(
                f"Database error: {e!s}",
                ErrorCode.DATABASE_ERROR,
                details={"exception": type(e).__name__},
            )

    async def get_concept_relationships(self, concept_id: str) -> Success | Error:
        """
        Fetch relationship data for confidence calculation.

        Args:
            concept_id: Unique identifier for the concept

        Returns:
            Success(RelationshipData) with relationship counts and types
            Error(DATABASE_ERROR) if query fails
        """
        try:
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            OPTIONAL MATCH (c)-[r]->(target:Concept)
            RETURN target.concept_id AS target_id, type(r) AS type
            UNION
            MATCH (c:Concept {concept_id: $concept_id})
            OPTIONAL MATCH (source:Concept)-[r]->(c)
            RETURN source.concept_id AS target_id, type(r) AS type
            """

            result = await self.session.run(query, concept_id=concept_id)
            records = await result.data()

            # Filter out None values (from OPTIONAL MATCH with no relationships)
            relationships = [r for r in records if r["target_id"] is not None]

            # Count relationship types
            type_counts = Counter(r["type"] for r in relationships)

            # Extract unique connected concept IDs
            connected_ids = [r["target_id"] for r in relationships]

            relationship_data = RelationshipData(
                total_relationships=len(relationships),
                relationship_types=dict(type_counts),
                connected_concept_ids=connected_ids,
            )

            return Success(relationship_data)

        except Exception as e:
            return Error(
                f"Database error: {e!s}",
                ErrorCode.DATABASE_ERROR,
                details={"exception": type(e).__name__},
            )

    async def get_review_history(self, concept_id: str) -> Success | Error:
        """
        Fetch review history for retention calculation.

        Args:
            concept_id: Unique identifier for the concept

        Returns:
            Success(ReviewData) with review history
            Error(NOT_FOUND) if concept doesn't exist
            Error(DATABASE_ERROR) if query fails
        """
        try:
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            RETURN c.last_reviewed_at AS last_reviewed_at,
                   c.created_at AS created_at,
                   COALESCE(c.review_count, 0) AS review_count
            """

            result = await self.session.run(query, concept_id=concept_id)
            record = result.single()
            if asyncio.iscoroutine(record):
                record = await record

            if not record:
                return Error(f"Concept not found: {concept_id}", ErrorCode.NOT_FOUND)

            # Use last_reviewed_at if available, otherwise use created_at
            if record["last_reviewed_at"]:
                last_reviewed = datetime.fromisoformat(record["last_reviewed_at"])
            else:
                last_reviewed = datetime.fromisoformat(record["created_at"])

            days_since_review = (datetime.now() - last_reviewed).days

            review_data = ReviewData(
                last_reviewed_at=last_reviewed,
                days_since_review=max(0, days_since_review),  # Ensure non-negative
                review_count=record["review_count"],
            )

            return Success(review_data)

        except Exception as e:
            return Error(
                f"Database error: {e!s}",
                ErrorCode.DATABASE_ERROR,
                details={"exception": type(e).__name__},
            )

    async def get_concept_tau(self, concept_id: str) -> Success | Error:
        """Retrieve the current retention tau for a concept."""

        config = ConfidenceConfig()

        try:
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            RETURN COALESCE(c.retention_tau, $default_tau) AS tau
            """

            result = await self.session.run(
                query,
                concept_id=concept_id,
                default_tau=config.DEFAULT_TAU_DAYS,
            )
            record = result.single()
            if asyncio.iscoroutine(record):
                record = await record

            if not record:
                return Error(f"Concept not found: {concept_id}", ErrorCode.NOT_FOUND)

            tau_value = record["tau"] if record["tau"] is not None else config.DEFAULT_TAU_DAYS
            return Success(max(1, int(tau_value)))

        except Exception as e:
            return Error(
                f"Database error: {e!s}",
                ErrorCode.DATABASE_ERROR,
                details={"exception": type(e).__name__},
            )

