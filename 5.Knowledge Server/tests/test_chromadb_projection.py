"""
Unit tests for ChromaDBProjection class.

Tests projection logic in isolation using mocked ChromaDB service.
"""

from unittest.mock import Mock

import pytest

from models.events import (
    ConceptCreated,
    ConceptDeleted,
    ConceptUpdated,
    Event,
)
from projections.chromadb_projection import ChromaDBProjection
from services.chromadb_service import ChromaDbService


@pytest.fixture
def mock_collection():
    """Create a mock ChromaDB collection."""
    collection = Mock()
    collection.add = Mock()
    collection.update = Mock()
    collection.delete = Mock()
    collection.get = Mock(return_value={"ids": [], "documents": [], "metadatas": []})
    collection.count = Mock(return_value=0)
    return collection


@pytest.fixture
def mock_chromadb_service(mock_collection):
    """Create a mock ChromaDB service for testing."""
    service = Mock(spec=ChromaDbService)
    service.is_connected = Mock(return_value=True)
    service.get_collection = Mock(return_value=mock_collection)
    return service


@pytest.fixture
def projection(mock_chromadb_service):
    """Create ChromaDBProjection instance with mocked service."""
    return ChromaDBProjection(mock_chromadb_service)


class TestChromaDBProjectionBasics:
    """Test basic projection functionality."""

    def test_projection_name(self, projection):
        """Test that projection returns correct name."""
        assert projection.get_projection_name() == "chromadb"

    def test_unknown_event_type(self, projection, mock_chromadb_service, mock_collection):
        """Test handling of unknown event types."""
        event = Event(
            event_type="UnknownEvent",
            aggregate_id="test_001",
            aggregate_type="Test",
            event_data={"data": "test"},
            version=1,
        )

        result = projection.project_event(event)

        # Should return False for unknown event types
        assert result is False
        # Should not call ChromaDB
        mock_collection.add.assert_not_called()
        mock_collection.update.assert_not_called()
        mock_collection.delete.assert_not_called()

    def test_service_not_connected(self, mock_chromadb_service, mock_collection):
        """Test that projection fails gracefully when service not connected."""
        mock_chromadb_service.is_connected = Mock(return_value=False)
        projection = ChromaDBProjection(mock_chromadb_service)

        event = ConceptCreated(
            aggregate_id="concept_001",
            concept_data={"name": "Test", "explanation": "Test explanation"},
            version=1,
        )

        result = projection.project_event(event)

        # Should return False when not connected
        assert result is False
        # Should not attempt any operations
        mock_collection.add.assert_not_called()


class TestConceptCreatedProjection:
    """Test ConceptCreated event projection."""

    def test_project_concept_created_minimal(
        self, projection, mock_chromadb_service, mock_collection
    ):
        """Test projecting ConceptCreated with minimal data."""
        event = ConceptCreated(
            aggregate_id="concept_001",
            concept_data={
                "name": "Test Concept",
                "explanation": "A test concept explanation",
                "confidence_score": 0.95
            },
            version=1,
        )

        result = projection.project_event(event)

        assert result is True
        mock_collection.add.assert_called_once()

        # Verify call structure
        call_args = mock_collection.add.call_args
        assert call_args[1]["ids"] == ["concept_001"]
        assert call_args[1]["documents"] == ["A test concept explanation"]

        # Verify metadata
        metadata = call_args[1]["metadatas"][0]
        assert metadata["name"] == "Test Concept"
        assert metadata["confidence_score"] == 0.95
        assert "created_at" in metadata
        assert "last_modified" in metadata

    def test_project_concept_created_full(self, projection, mock_chromadb_service, mock_collection):
        """Test projecting ConceptCreated with all optional fields."""
        event = ConceptCreated(
            aggregate_id="concept_002",
            concept_data={
                "name": "Full Concept",
                "explanation": "Complete concept explanation",
                "confidence_score": 0.99,
                "area": "Mathematics",
                "topic": "Algebra",
                "subtopic": "Linear Equations",
            },
            version=1,
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_collection.add.call_args
        metadata = call_args[1]["metadatas"][0]

        # Verify all hierarchical metadata included
        assert metadata["area"] == "Mathematics"
        assert metadata["topic"] == "Algebra"
        assert metadata["subtopic"] == "Linear Equations"
        assert metadata["name"] == "Full Concept"
        assert metadata["confidence_score"] == 0.99

    def test_concept_created_empty_explanation(
        self, projection, mock_chromadb_service, mock_collection
    ):
        """Test that empty explanation is handled gracefully."""
        event = ConceptCreated(
            aggregate_id="concept_003",
            concept_data={
                "name": "Empty Explanation",
                "explanation": "",
                "confidence_score": 0.5
            },
            version=1
        )

        result = projection.project_event(event)

        # Should still succeed with empty document
        assert result is True
        call_args = mock_collection.add.call_args
        assert call_args[1]["documents"] == [""]

    def test_concept_created_idempotency(self, projection, mock_chromadb_service, mock_collection):
        """Test that creating same concept twice calls add twice."""
        event = ConceptCreated(
            aggregate_id="concept_004",
            concept_data={"name": "Idempotent", "explanation": "Test"},
            version=1,
        )

        # Project same event twice
        result1 = projection.project_event(event)
        result2 = projection.project_event(event)

        assert result1 is True
        assert result2 is True

        # Both calls should succeed (ChromaDB handles duplicates)
        assert mock_collection.add.call_count == 2

    def test_concept_created_exception_handling(
        self, projection, mock_chromadb_service, mock_collection
    ):
        """Test error handling when ChromaDB add() fails."""
        mock_collection.add.side_effect = Exception("ChromaDB error")

        event = ConceptCreated(
            aggregate_id="concept_005",
            concept_data={"name": "Error Test", "explanation": "Test"},
            version=1,
        )

        result = projection.project_event(event)

        # Should return False on error
        assert result is False


class TestConceptUpdatedProjection:
    """Test ConceptUpdated event projection."""

    def test_project_concept_updated_explanation(
        self, projection, mock_chromadb_service, mock_collection
    ):
        """Test updating concept explanation."""
        # Mock existing concept
        mock_collection.get = Mock(return_value={
            'ids': ['concept_001'],
            'documents': ['Old explanation'],
            'metadatas': [{
                'name': 'Test Concept',
                'confidence_score': 0.8,
                'created_at': '2025-01-01T00:00:00',
                'last_modified': '2025-01-01T00:00:00'
            }]
        })

        event = ConceptUpdated(
            aggregate_id="concept_001",
            updates={"explanation": "New updated explanation"},
            version=2,
        )

        result = projection.project_event(event)

        assert result is True
        mock_collection.update.assert_called_once()

        call_args = mock_collection.update.call_args
        assert call_args[1]["ids"] == ["concept_001"]
        assert call_args[1]["documents"] == ["New updated explanation"]

        # Verify metadata updated with new timestamp
        metadata = call_args[1]["metadatas"][0]
        assert "last_modified" in metadata
        assert metadata["last_modified"] != "2025-01-01T00:00:00"

    def test_project_concept_updated_metadata_only(
        self, projection, mock_chromadb_service, mock_collection
    ):
        """Test updating only metadata (no explanation change)."""
        # Mock existing concept
        mock_collection.get = Mock(return_value={
            'ids': ['concept_002'],
            'documents': ['Existing explanation'],
            'metadatas': [{
                'name': 'Old Name',
                'confidence_score': 0.7,
                'area': 'Science'
            }]
        })

        event = ConceptUpdated(
            aggregate_id="concept_002",
            updates={
                "name": "Updated Name",
                "confidence_score": 0.95
            },
            version=2
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_collection.update.call_args

        # Should keep existing document
        assert call_args[1]["documents"] == ["Existing explanation"]

        # Should update metadata
        metadata = call_args[1]["metadatas"][0]
        assert metadata["name"] == "Updated Name"
        assert metadata["confidence_score"] == 0.95
        assert metadata["area"] == "Science"  # Preserved from existing

    def test_concept_updated_not_found(self, projection, mock_chromadb_service, mock_collection):
        """Test updating concept that doesn't exist."""
        # Mock concept not found
        mock_collection.get = Mock(return_value={"ids": [], "documents": [], "metadatas": []})

        event = ConceptUpdated(
            aggregate_id="concept_999", updates={"explanation": "New"}, version=2
        )

        result = projection.project_event(event)

        # Should return False when concept not found
        assert result is False
        mock_collection.update.assert_not_called()

    def test_concept_updated_all_fields(self, projection, mock_chromadb_service, mock_collection):
        """Test updating all possible fields."""
        mock_collection.get = Mock(
            return_value={"ids": ["concept_003"], "documents": ["Old"], "metadatas": [{}]}
        )

        event = ConceptUpdated(
            aggregate_id="concept_003",
            updates={
                "explanation": "New explanation",
                "name": "New Name",
                "confidence_score": 0.88,
                "area": "New Area",
                "topic": "New Topic",
                "subtopic": "New Subtopic",
            },
            version=2,
        )

        result = projection.project_event(event)

        assert result is True
        call_args = mock_collection.update.call_args
        metadata = call_args[1]["metadatas"][0]

        assert metadata["name"] == "New Name"
        assert metadata["confidence_score"] == 0.88
        assert metadata["area"] == "New Area"
        assert metadata["topic"] == "New Topic"
        assert metadata["subtopic"] == "New Subtopic"

    def test_concept_updated_exception_handling(
        self, projection, mock_chromadb_service, mock_collection
    ):
        """Test error handling when update() fails."""
        mock_collection.get = Mock(
            return_value={"ids": ["concept_004"], "documents": ["Test"], "metadatas": [{}]}
        )
        mock_collection.update.side_effect = Exception("Update error")

        event = ConceptUpdated(
            aggregate_id="concept_004", updates={"explanation": "New"}, version=2
        )

        result = projection.project_event(event)

        assert result is False


class TestConceptDeletedProjection:
    """Test ConceptDeleted event projection."""

    def test_project_concept_deleted(self, projection, mock_chromadb_service, mock_collection):
        """Test deleting concept from ChromaDB."""
        event = ConceptDeleted(aggregate_id="concept_001", version=2)

        result = projection.project_event(event)

        assert result is True
        mock_collection.delete.assert_called_once()

        call_args = mock_collection.delete.call_args
        assert call_args[1]["ids"] == ["concept_001"]

    def test_concept_deleted_idempotency(self, projection, mock_chromadb_service, mock_collection):
        """Test that deleting same concept twice succeeds (idempotent)."""
        event = ConceptDeleted(aggregate_id="concept_002", version=2)

        result1 = projection.project_event(event)
        result2 = projection.project_event(event)

        assert result1 is True
        assert result2 is True
        assert mock_collection.delete.call_count == 2

    def test_concept_deleted_exception_handling(
        self, projection, mock_chromadb_service, mock_collection
    ):
        """Test error handling when delete() fails."""
        mock_collection.delete.side_effect = Exception("Delete error")

        event = ConceptDeleted(aggregate_id="concept_003", version=2)

        result = projection.project_event(event)

        assert result is False


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_runtime_error_from_service(self, projection, mock_chromadb_service):
        """Test handling RuntimeError from service operations."""
        mock_chromadb_service.get_collection.side_effect = RuntimeError("Not connected")

        event = ConceptCreated(
            aggregate_id="concept_001",
            concept_data={"name": "Test", "explanation": "Test"},
            version=1,
        )

        result = projection.project_event(event)

        assert result is False

    def test_missing_required_fields(self, projection, mock_chromadb_service, mock_collection):
        """Test handling event with missing required fields."""
        event = Event(
            event_type="ConceptCreated",
            aggregate_id="concept_001",
            aggregate_type="Concept",
            event_data={},  # Missing name and explanation
            version=1,
        )

        result = projection.project_event(event)

        # Should still succeed, using defaults
        assert result is True
        call_args = mock_collection.add.call_args
        assert call_args[1]["metadatas"][0]["name"] == ""
