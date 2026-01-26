"""
Unit tests for data access layer in confidence scoring system.

Tests Neo4j queries for concept retrieval, relationship data, and review history.
Uses mocked Neo4j session to avoid database dependencies.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from services.confidence.data_access import DataAccessLayer
from services.confidence.models import Error, ErrorCode, Success


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j session for testing"""
    session = Mock()
    session.run = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_get_concept_for_confidence_with_valid_id_returns_concept_data(
    mock_neo4j_session,
):
    """Valid concept ID should return ConceptData"""
    # Mock Neo4j response
    mock_result = Mock()
    mock_result.single = Mock(
        return_value={
            "id": "c1",
            "name": "Test Concept",
            "explanation": "Test explanation",
            "created_at": datetime.now().isoformat(),
            "last_reviewed_at": None,
            "tags": ["tag1"],
            "examples": ["example1"],
        }
    )
    mock_neo4j_session.run.return_value = mock_result

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_concept_for_confidence("c1")

    assert isinstance(result, Success)
    assert result.value.id == "c1"
    assert result.value.name == "Test Concept"
    assert result.value.explanation == "Test explanation"


@pytest.mark.asyncio
async def test_get_concept_for_confidence_with_last_reviewed_at_parses_datetime(
    mock_neo4j_session,
):
    """last_reviewed_at should be parsed correctly"""
    reviewed_date = datetime.now() - timedelta(days=7)
    mock_result = Mock()
    mock_result.single = Mock(
        return_value={
            "id": "c1",
            "name": "Test Concept",
            "explanation": "Test explanation",
            "created_at": datetime.now().isoformat(),
            "last_reviewed_at": reviewed_date.isoformat(),
            "tags": [],
            "examples": [],
        }
    )
    mock_neo4j_session.run.return_value = mock_result

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_concept_for_confidence("c1")

    assert isinstance(result, Success)
    assert result.value.last_reviewed_at is not None
    assert result.value.last_reviewed_at.date() == reviewed_date.date()


@pytest.mark.asyncio
async def test_get_concept_for_confidence_with_nonexistent_id_returns_not_found_error(
    mock_neo4j_session,
):
    """Non-existent concept ID should return NOT_FOUND error"""
    mock_result = Mock()
    mock_result.single = Mock(return_value=None)
    mock_neo4j_session.run.return_value = mock_result

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_concept_for_confidence("nonexistent")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.NOT_FOUND
    assert "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_get_concept_for_confidence_with_database_error_returns_database_error(
    mock_neo4j_session,
):
    """Database connection error should return DATABASE_ERROR"""
    mock_neo4j_session.run.side_effect = Exception("Connection failed")

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_concept_for_confidence("c1")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.DATABASE_ERROR
    assert "database error" in result.message.lower()


@pytest.mark.asyncio
async def test_get_concept_relationships_returns_relationship_data(mock_neo4j_session):
    """Should return RelationshipData with counts and types"""
    mock_result = Mock()
    mock_result.data = AsyncMock(
        return_value=[
            {"target_id": "c2", "type": "RELATES_TO"},
            {"target_id": "c3", "type": "DEPENDS_ON"},
            {"target_id": "c4", "type": "RELATES_TO"},
        ]
    )
    mock_neo4j_session.run.return_value = mock_result

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_concept_relationships("c1")

    assert isinstance(result, Success)
    assert result.value.total_relationships == 3
    assert result.value.relationship_types["RELATES_TO"] == 2
    assert result.value.relationship_types["DEPENDS_ON"] == 1
    assert len(result.value.connected_concept_ids) == 3


@pytest.mark.asyncio
async def test_get_concept_relationships_with_no_relationships_returns_empty_data(
    mock_neo4j_session,
):
    """Concept with no relationships should return empty RelationshipData"""
    mock_result = Mock()
    mock_result.data = AsyncMock(return_value=[{"target_id": None, "type": None}])
    mock_neo4j_session.run.return_value = mock_result

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_concept_relationships("c1")

    assert isinstance(result, Success)
    assert result.value.total_relationships == 0
    assert result.value.relationship_types == {}
    assert result.value.connected_concept_ids == []


@pytest.mark.asyncio
async def test_get_concept_relationships_with_database_error_returns_database_error(
    mock_neo4j_session,
):
    """Database error should return DATABASE_ERROR"""
    mock_neo4j_session.run.side_effect = Exception("Query timeout")

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_concept_relationships("c1")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.DATABASE_ERROR


@pytest.mark.asyncio
async def test_get_review_history_calculates_days_since_review(mock_neo4j_session):
    """Should calculate days_since_review correctly"""
    reviewed_date = datetime.now() - timedelta(days=14)
    mock_result = Mock()
    mock_result.single = Mock(
        return_value={
            "last_reviewed_at": reviewed_date.isoformat(),
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "review_count": 3,
        }
    )
    mock_neo4j_session.run.return_value = mock_result

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_review_history("c1")

    assert isinstance(result, Success)
    assert result.value.days_since_review == 14
    assert result.value.review_count == 3


@pytest.mark.asyncio
async def test_get_review_history_with_never_reviewed_uses_created_at(
    mock_neo4j_session,
):
    """Never-reviewed concept should use created_at as baseline"""
    created_date = datetime.now() - timedelta(days=30)
    mock_result = Mock()
    mock_result.single = Mock(
        return_value={
            "last_reviewed_at": None,
            "created_at": created_date.isoformat(),
            "review_count": 0,
        }
    )
    mock_neo4j_session.run.return_value = mock_result

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_review_history("c1")

    assert isinstance(result, Success)
    assert result.value.days_since_review == 30  # Based on created_at
    assert result.value.review_count == 0


@pytest.mark.asyncio
async def test_get_review_history_with_nonexistent_concept_returns_not_found(
    mock_neo4j_session,
):
    """Non-existent concept should return NOT_FOUND error"""
    mock_result = Mock()
    mock_result.single = Mock(return_value=None)
    mock_neo4j_session.run.return_value = mock_result

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_review_history("nonexistent")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_review_history_with_database_error_returns_database_error(
    mock_neo4j_session,
):
    """Database error should return DATABASE_ERROR"""
    mock_neo4j_session.run.side_effect = Exception("Connection lost")

    dal = DataAccessLayer(mock_neo4j_session)
    result = await dal.get_review_history("c1")

    assert isinstance(result, Error)
    assert result.code == ErrorCode.DATABASE_ERROR
