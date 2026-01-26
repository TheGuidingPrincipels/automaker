"""Integration tests for confidence score DataAccessLayer property name fix.

Tests verify that DataAccessLayer correctly queries concept_id property (not id property)
in Neo4j, resolving the bug where all confidence calculations returned NOT_FOUND errors.
"""

import pytest

from services.confidence.data_access import DataAccessLayer
from services.confidence.models import ErrorCode, Success


@pytest.mark.asyncio
async def test_get_concept_for_confidence_returns_concept_data(
    neo4j_session_adapter, concept_with_metadata
):
    """Test that get_concept_for_confidence successfully retrieves existing concepts.

    BEFORE FIX: Returns Error(NOT_FOUND) because query uses {id: $concept_id}
    AFTER FIX: Returns Success(ConceptData) because query uses {concept_id: $concept_id}
    """
    dal = DataAccessLayer(neo4j_session_adapter)
    concept_id = concept_with_metadata["concept_id"]

    # This should succeed after fix
    result = await dal.get_concept_for_confidence(concept_id)

    # Assertions
    assert isinstance(result, Success), f"Expected Success, got: {result}"

    concept_data = result.value
    assert concept_data.id == concept_id
    assert concept_data.name == concept_with_metadata["name"]
    assert concept_data.explanation is not None


@pytest.mark.asyncio
async def test_get_concept_relationships_returns_relationships(
    neo4j_session_adapter, concept_with_relationships
):
    """Test that get_concept_relationships successfully retrieves concept relationships.

    BEFORE FIX: Returns empty relationships because queries use {id: $concept_id}
    AFTER FIX: Returns actual relationships because queries use {concept_id: $concept_id}
    """
    dal = DataAccessLayer(neo4j_session_adapter)
    concept_id = concept_with_relationships["concept_id"]

    # This should return relationships after fix
    result = await dal.get_concept_relationships(concept_id)

    # Assertions
    assert isinstance(result, Success), f"Expected Success, got: {result}"

    relationship_data = result.value
    # RelationshipData has total_relationships and connected_concept_ids
    assert relationship_data.total_relationships > 0, "Should have at least one relationship"
    assert len(relationship_data.connected_concept_ids) > 0, "Should have connected concepts"


@pytest.mark.asyncio
async def test_get_review_history_returns_reviews(
    neo4j_session_adapter, concept_with_review_history
):
    """Test that get_review_history successfully retrieves concept review history.

    BEFORE FIX: Returns Error(NOT_FOUND) because query uses {id: $concept_id}
    AFTER FIX: Returns Success(reviews) because query uses {concept_id: $concept_id}
    """
    dal = DataAccessLayer(neo4j_session_adapter)
    concept_id = concept_with_review_history["concept_id"]

    # This should return review history after fix
    result = await dal.get_review_history(concept_id)

    # Assertions
    assert isinstance(result, Success), f"Expected Success, got: {result}"

    review_data = result.value
    # ReviewData has last_reviewed_at and review_count
    assert review_data.last_reviewed_at is not None, "Should have last_reviewed_at"
    assert review_data.review_count >= 0, "Should have valid review_count"


# Fixtures would be defined in conftest.py
