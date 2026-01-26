"""
Tests for source_urls parameter in concept tools.

Tests the optional source_urls field added to create_concept and update_concept,
including JSON validation, storage in Neo4j and ChromaDB projections.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.concept_tools import create_concept, update_concept


@pytest.mark.asyncio
async def test_create_concept_with_source_urls():
    """Test creating concept with source URLs (JSON validation and storage)"""
    # Arrange
    source_urls = json.dumps(
        [
            {
                "url": "https://docs.python.org",
                "title": "Python Docs",
                "quality_score": 1.0,
                "domain_category": "official",
            },
            {
                "url": "https://realpython.com",
                "title": "Real Python",
                "quality_score": 0.8,
                "domain_category": "in_depth",
            },
        ]
    )

    # Mock repository
    mock_repository = MagicMock()
    mock_repository.find_duplicate_concept.return_value = None
    mock_repository.create_concept.return_value = (True, None, "concept-123")

    with patch("tools.concept_tools.repository", mock_repository):
        # Act
        result = await create_concept(
            name="python asyncio",
            explanation="Async programming in Python",
            source_urls=source_urls,
        )

    # Assert
    assert result["success"] is True
    assert result["data"]["concept_id"] == "concept-123"

    # Verify repository was called with parsed list (not JSON string)
    call_args = mock_repository.create_concept.call_args[0][0]
    assert "source_urls" in call_args
    assert isinstance(call_args["source_urls"], list)
    assert len(call_args["source_urls"]) == 2
    assert call_args["source_urls"][0]["url"] == "https://docs.python.org"


@pytest.mark.asyncio
async def test_create_concept_without_source_urls():
    """Test backward compatibility - source_urls is optional"""
    # Arrange
    mock_repository = MagicMock()
    mock_repository.find_duplicate_concept.return_value = None
    mock_repository.create_concept.return_value = (True, None, "concept-456")

    with patch("tools.concept_tools.repository", mock_repository):
        # Act
        result = await create_concept(
            name="test concept",
            explanation="Test explanation",
            # source_urls not provided - should work
        )

    # Assert
    assert result["success"] is True
    assert result["data"]["concept_id"] == "concept-456"

    # Verify repository was called without source_urls
    call_args = mock_repository.create_concept.call_args[0][0]
    assert "source_urls" not in call_args


@pytest.mark.asyncio
async def test_create_concept_invalid_json_source_urls():
    """Test JSON validation error for malformed source_urls"""
    # Arrange
    invalid_json = "not-valid-json"

    mock_repository = MagicMock()
    mock_repository.find_duplicate_concept.return_value = None

    with patch('tools.concept_tools.repository', mock_repository):
        # Act
        result = await create_concept(
            name="test concept",
            explanation="Test explanation",
            source_urls=invalid_json
        )

    # Assert
    assert result["success"] is False
    # Error message is: "The provided input is invalid... (source_urls must be valid JSON: ...)"
    assert "invalid" in result["error"]["message"].lower() or "json" in result["error"]["message"].lower()


@pytest.mark.asyncio
async def test_create_concept_source_urls_not_array():
    """Test validation error when source_urls is not a JSON array"""
    # Arrange
    not_array = json.dumps({"url": "https://example.com"})  # Object, not array

    mock_repository = MagicMock()
    mock_repository.find_duplicate_concept.return_value = None

    with patch('tools.concept_tools.repository', mock_repository):
        # Act
        result = await create_concept(
            name="test concept",
            explanation="Test explanation",
            source_urls=not_array
        )

    # Assert
    assert result["success"] is False
    assert "array" in result["error"]["message"].lower()


@pytest.mark.asyncio
async def test_update_concept_add_source_urls():
    """Test adding source URLs to existing concept"""
    # Arrange
    source_urls = json.dumps([{"url": "https://example.com", "title": "Example"}])

    mock_repository = MagicMock()
    mock_repository.update_concept.return_value = (True, None)

    with patch("tools.concept_tools.repository", mock_repository):
        # Act
        result = await update_concept(concept_id="concept-789", source_urls=source_urls)

    # Assert
    assert result["success"] is True
    assert "source_urls" in result["data"]["updated_fields"]

    # Verify repository was called with parsed list
    call_args = mock_repository.update_concept.call_args[0][1]
    assert "source_urls" in call_args
    assert isinstance(call_args["source_urls"], list)
    assert call_args["source_urls"][0]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_source_urls_missing_url_field():
    """Test validation error when source URL object lacks 'url' field"""
    # Arrange
    missing_url = json.dumps([{"title": "Example", "quality_score": 0.8}])  # Missing 'url' field

    mock_repository = MagicMock()
    mock_repository.find_duplicate_concept.return_value = None

    with patch('tools.concept_tools.repository', mock_repository):
        # Act
        result = await create_concept(
            name="test concept",
            explanation="Test explanation",
            source_urls=missing_url
        )

    # Assert
    assert result["success"] is False
    assert '"url"' in result["error"]["message"].lower() or 'url' in result["error"]["message"].lower()
