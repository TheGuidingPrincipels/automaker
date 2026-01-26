"""
Unit tests for ConsistencyChecker.

Tests the consistency verification utility for dual storage.
"""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from services.consistency_checker import ConsistencyChecker, ConsistencyReport


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create consistency_snapshots table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE consistency_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            neo4j_count INTEGER,
            chromadb_count INTEGER,
            discrepancies TEXT,
            checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    """
    )
    conn.commit()
    conn.close()

    yield db_path

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_neo4j_service():
    """Create mock Neo4j service."""
    service = Mock()
    service.execute_read = Mock(return_value=[])
    return service


@pytest.fixture
def mock_chromadb_service():
    """Create mock ChromaDB service."""
    service = Mock()
    mock_collection = Mock()
    mock_collection.get = Mock(return_value={"ids": [], "metadatas": []})
    service.get_collection = Mock(return_value=mock_collection)
    return service


class TestConsistencyChecker:
    """Test ConsistencyChecker initialization and basic operations."""

    def test_initialization(self, mock_neo4j_service, mock_chromadb_service, temp_db):
        """Test that ConsistencyChecker initializes correctly."""
        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)

        assert checker.neo4j == mock_neo4j_service
        assert checker.chromadb == mock_chromadb_service
        assert checker.db_path == temp_db

    def test_get_neo4j_concepts_empty(self, mock_neo4j_service, mock_chromadb_service, temp_db):
        """Test getting concepts from empty Neo4j."""
        mock_neo4j_service.execute_read = Mock(return_value=[])

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        concepts = checker.get_neo4j_concepts()

        assert concepts == {}
        mock_neo4j_service.execute_read.assert_called_once()

    def test_get_neo4j_concepts_with_data(self, mock_neo4j_service, mock_chromadb_service, temp_db):
        """Test getting concepts from Neo4j with data."""
        mock_neo4j_service.execute_read = Mock(return_value=[
            {
                "concept_id": "concept_001",
                "name": "Test Concept",
                "area": "Testing",
                "topic": "Unit Tests",
                "subtopic": None,
                "confidence_score": 90,
                "deleted": False
            }
        ])

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        concepts = checker.get_neo4j_concepts()

        assert len(concepts) == 1
        assert "concept_001" in concepts
        assert concepts["concept_001"]["name"] == "Test Concept"
        assert concepts["concept_001"]["confidence_score"] == 90

    def test_get_chromadb_concepts_empty(self, mock_neo4j_service, mock_chromadb_service, temp_db):
        """Test getting concepts from empty ChromaDB."""
        mock_collection = Mock()
        mock_collection.get = Mock(return_value={"ids": [], "metadatas": []})
        mock_chromadb_service.get_collection = Mock(return_value=mock_collection)

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        concepts = checker.get_chromadb_concepts()

        assert concepts == {}

    def test_get_chromadb_concepts_with_data(
        self, mock_neo4j_service, mock_chromadb_service, temp_db
    ):
        """Test getting concepts from ChromaDB with data."""
        mock_collection = Mock()
        mock_collection.get = Mock(return_value={
            'ids': ['concept_001'],
            'metadatas': [{
                'name': 'Test Concept',
                'area': 'Testing',
                'topic': 'Unit Tests',
                'subtopic': None,
                'confidence_score': 90
            }]
        })
        mock_chromadb_service.get_collection = Mock(return_value=mock_collection)

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        concepts = checker.get_chromadb_concepts()

        assert len(concepts) == 1
        assert "concept_001" in concepts
        assert concepts["concept_001"]["name"] == "Test Concept"


class TestDiscrepancyDetection:
    """Test discrepancy detection logic."""

    def test_find_discrepancies_no_concepts(
        self, mock_neo4j_service, mock_chromadb_service, temp_db
    ):
        """Test finding discrepancies with no concepts in either database."""
        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)

        neo4j_only, chromadb_only, mismatched = checker.find_discrepancies({}, {})

        assert neo4j_only == []
        assert chromadb_only == []
        assert mismatched == []

    def test_find_discrepancies_neo4j_only(
        self, mock_neo4j_service, mock_chromadb_service, temp_db
    ):
        """Test finding concepts only in Neo4j."""
        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)

        neo4j_concepts = {"concept_001": {"name": "Test"}}
        chromadb_concepts = {}

        neo4j_only, chromadb_only, mismatched = checker.find_discrepancies(
            neo4j_concepts, chromadb_concepts
        )

        assert neo4j_only == ["concept_001"]
        assert chromadb_only == []
        assert mismatched == []

    def test_find_discrepancies_chromadb_only(
        self, mock_neo4j_service, mock_chromadb_service, temp_db
    ):
        """Test finding concepts only in ChromaDB."""
        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)

        neo4j_concepts = {}
        chromadb_concepts = {"concept_002": {"name": "Test"}}

        neo4j_only, chromadb_only, mismatched = checker.find_discrepancies(
            neo4j_concepts, chromadb_concepts
        )

        assert neo4j_only == []
        assert chromadb_only == ["concept_002"]
        assert mismatched == []

    def test_find_discrepancies_matching_concepts(
        self, mock_neo4j_service, mock_chromadb_service, temp_db
    ):
        """Test finding no discrepancies when concepts match."""
        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)

        concept_data = {
            "name": "Test Concept",
            "area": "Testing",
            "topic": "Unit Tests",
            "subtopic": None,
            "confidence_score": 90
        }

        neo4j_concepts = {"concept_001": concept_data.copy()}
        chromadb_concepts = {"concept_001": concept_data.copy()}

        neo4j_only, chromadb_only, mismatched = checker.find_discrepancies(
            neo4j_concepts, chromadb_concepts
        )

        assert neo4j_only == []
        assert chromadb_only == []
        assert mismatched == []

    def test_find_discrepancies_mismatched_metadata(
        self, mock_neo4j_service, mock_chromadb_service, temp_db
    ):
        """Test finding mismatched metadata between databases."""
        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)

        neo4j_concepts = {
            "concept_001": {
                "name": "Test Concept",
                "area": "Testing",
                "confidence_score": 90
            }
        }

        chromadb_concepts = {
            "concept_001": {
                "name": "Different Name",  # Mismatch
                "area": "Testing",
                "confidence_score": 80  # Mismatch
            }
        }

        neo4j_only, chromadb_only, mismatched = checker.find_discrepancies(
            neo4j_concepts, chromadb_concepts
        )

        assert neo4j_only == []
        assert chromadb_only == []
        assert len(mismatched) == 1
        assert mismatched[0]["concept_id"] == "concept_001"
        assert len(mismatched[0]["differences"]) == 2  # name and confidence_score


class TestConsistencyCheck:
    """Test full consistency check workflow."""

    def test_check_consistency_empty_databases(
        self, mock_neo4j_service, mock_chromadb_service, temp_db
    ):
        """Test consistency check with empty databases."""
        mock_neo4j_service.execute_read = Mock(return_value=[])

        mock_collection = Mock()
        mock_collection.get = Mock(return_value={"ids": [], "metadatas": []})
        mock_chromadb_service.get_collection = Mock(return_value=mock_collection)

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        report = checker.check_consistency(save_snapshot=False)

        assert report.neo4j_count == 0
        assert report.chromadb_count == 0
        assert report.is_consistent is True

    def test_check_consistency_consistent_databases(
        self, mock_neo4j_service, mock_chromadb_service, temp_db
    ):
        """Test consistency check with matching databases."""
        mock_neo4j_service.execute_read = Mock(return_value=[
            {
                "concept_id": "concept_001",
                "name": "Test",
                "area": "Testing",
                "topic": None,
                "subtopic": None,
                "confidence_score": 90,
                "deleted": False
            }
        ])

        mock_collection = Mock()
        mock_collection.get = Mock(return_value={
            'ids': ['concept_001'],
            'metadatas': [{
                'name': 'Test',
                'area': 'Testing',
                'topic': None,
                'subtopic': None,
                'confidence_score': 90
            }]
        })
        mock_chromadb_service.get_collection = Mock(return_value=mock_collection)

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        report = checker.check_consistency(save_snapshot=False)

        assert report.neo4j_count == 1
        assert report.chromadb_count == 1
        assert report.is_consistent is True

    def test_save_snapshot(self, mock_neo4j_service, mock_chromadb_service, temp_db):
        """Test saving consistency snapshot to database."""
        mock_neo4j_service.execute_read = Mock(return_value=[])
        mock_collection = Mock()
        mock_collection.get = Mock(return_value={"ids": [], "metadatas": []})
        mock_chromadb_service.get_collection = Mock(return_value=mock_collection)

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)
        checker.check_consistency(save_snapshot=True)

        # Verify snapshot was saved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM consistency_snapshots")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_get_latest_snapshot(self, mock_neo4j_service, mock_chromadb_service, temp_db):
        """Test retrieving latest consistency snapshot."""
        mock_neo4j_service.execute_read = Mock(return_value=[])
        mock_collection = Mock()
        mock_collection.get = Mock(return_value={"ids": [], "metadatas": []})
        mock_chromadb_service.get_collection = Mock(return_value=mock_collection)

        checker = ConsistencyChecker(mock_neo4j_service, mock_chromadb_service, temp_db)

        # Create snapshot
        checker.check_consistency(save_snapshot=True)

        # Retrieve latest
        snapshot = checker.get_latest_snapshot()

        assert snapshot is not None
        assert snapshot["neo4j_count"] == 0
        assert snapshot["chromadb_count"] == 0
        assert snapshot["status"] == "consistent"


class TestConsistencyReport:
    """Test ConsistencyReport dataclass."""

    def test_consistency_report_str(self):
        """Test string representation of ConsistencyReport."""
        report = ConsistencyReport(
            neo4j_count=10,
            chromadb_count=10,
            matching_count=10,
            neo4j_only=[],
            chromadb_only=[],
            mismatched=[],
            is_consistent=True,
            checked_at=datetime.utcnow(),
        )

        report_str = str(report)

        assert "Neo4j concepts: 10" in report_str
        assert "ChromaDB concepts: 10" in report_str
        assert "✅ CONSISTENT" in report_str

    def test_consistency_report_with_discrepancies(self):
        """Test report with discrepancies."""
        report = ConsistencyReport(
            neo4j_count=11,
            chromadb_count=10,
            matching_count=9,
            neo4j_only=["concept_001"],
            chromadb_only=[],
            mismatched=[{"concept_id": "concept_002", "differences": []}],
            is_consistent=False,
            checked_at=datetime.utcnow(),
        )

        report_str = str(report)

        assert "❌ INCONSISTENT" in report_str
        assert "Neo4j only" in report_str
        assert "Mismatched" in report_str
