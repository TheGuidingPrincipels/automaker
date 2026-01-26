"""
Tests for the database cleanup script.

Verifies that the cleanup script properly resets the database while
preserving domain whitelist and maintaining database integrity.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from short_term_mcp.config import DB_PATH
from short_term_mcp.database import Database, get_db
from short_term_mcp.models import Session

# Path to cleanup script
SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "cleanup_database.py"


@pytest.fixture
def populated_db():
    """Create a database populated with test data."""
    from short_term_mcp.models import Concept, ConceptStatus, ResearchCacheEntry, Stage

    db = get_db()

    # Use unique session ID to avoid conflicts between tests
    session_id = f"test_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    session = Session(
        session_id=session_id,
        date="2025-01-01",
        learning_goal="Test goal",
        building_goal="Test building",
        status="in_progress",
    )
    db.create_session(session)

    # Create test concepts
    for i in range(3):
        concept_id = f"test_concept_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        concept = Concept(
            session_id=session_id,
            concept_id=concept_id,
            concept_name=f"Test Concept {i}",
            current_status=ConceptStatus.IDENTIFIED,
            current_data={"test": True},
        )
        db.create_concept(concept)

        # Add stage data
        db.store_stage_data(
            concept_id=concept_id,
            stage=Stage.RESEARCH,
            data={"test": True},
        )

    # Create research cache entry using direct SQL to avoid complex Pydantic validation
    cache_concept_name = f"Test Research {datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    normalized_name = cache_concept_name.lower().strip()
    db.connection.execute(
        """
        INSERT INTO research_cache (concept_name, explanation, source_urls, last_researched_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            normalized_name,
            "Test explanation",
            '["https://example.com"]',  # JSON string
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
    )
    db.connection.commit()

    # Get initial stats
    cursor = db.connection.execute("SELECT COUNT(*) FROM sessions")
    sessions_count = cursor.fetchone()[0]

    cursor = db.connection.execute("SELECT COUNT(*) FROM concepts")
    concepts_count = cursor.fetchone()[0]

    cursor = db.connection.execute("SELECT COUNT(*) FROM research_cache")
    cache_count = cursor.fetchone()[0]

    cursor = db.connection.execute("SELECT COUNT(*) FROM domain_whitelist")
    domains_count = cursor.fetchone()[0]

    yield db, {
        "sessions": sessions_count,
        "concepts": concepts_count,
        "cache": cache_count,
        "domains": domains_count,
    }

    # Cleanup after test - be safe even if test deleted data
    try:
        db.connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        db.connection.execute(
            "DELETE FROM research_cache WHERE concept_name LIKE ?", ("Test Research%",)
        )
        db.connection.commit()
    except:
        pass  # Data may already be deleted by cleanup script


class TestCleanupScript:
    """Test suite for database cleanup script."""

    def test_script_exists(self):
        """Verify cleanup script file exists and is executable."""
        assert SCRIPT_PATH.exists(), f"Script not found at {SCRIPT_PATH}"
        assert SCRIPT_PATH.stat().st_mode & 0o111, "Script is not executable"

    def test_cleanup_with_cancel(self, populated_db):
        """Test that cleanup is cancelled when user doesn't confirm."""
        db, initial_stats = populated_db

        # Run script with 'NO' as input (should cancel)
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            input="NO\n",
            capture_output=True,
            text=True,
        )

        # Should exit with code 1 (cancelled)
        assert result.returncode == 1
        assert "Cancelled" in result.stdout

        # Verify no data was deleted
        cursor = db.connection.execute("SELECT COUNT(*) FROM sessions")
        assert cursor.fetchone()[0] == initial_stats["sessions"]

        cursor = db.connection.execute("SELECT COUNT(*) FROM concepts")
        assert cursor.fetchone()[0] == initial_stats["concepts"]

    def test_cleanup_with_confirmation(self, populated_db):
        """Test successful cleanup with user confirmation."""
        db, initial_stats = populated_db

        # Verify we have data to clean
        assert initial_stats["sessions"] > 0
        assert initial_stats["concepts"] > 0
        assert initial_stats["cache"] > 0
        assert initial_stats["domains"] > 0

        # Run script with 'RESET' as input
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            input="RESET\n",
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert "cleanup complete" in result.stdout.lower()

        # Verify sessions deleted
        cursor = db.connection.execute("SELECT COUNT(*) FROM sessions")
        assert cursor.fetchone()[0] == 0, "Sessions should be deleted"

        # Verify concepts deleted (CASCADE)
        cursor = db.connection.execute("SELECT COUNT(*) FROM concepts")
        assert cursor.fetchone()[0] == 0, "Concepts should be deleted"

        # Verify stage data deleted (CASCADE)
        cursor = db.connection.execute("SELECT COUNT(*) FROM concept_stage_data")
        assert cursor.fetchone()[0] == 0, "Stage data should be deleted"

        # Verify research cache deleted
        cursor = db.connection.execute("SELECT COUNT(*) FROM research_cache")
        assert cursor.fetchone()[0] == 0, "Research cache should be deleted"

        # Verify domain whitelist preserved
        cursor = db.connection.execute("SELECT COUNT(*) FROM domain_whitelist")
        domains_after = cursor.fetchone()[0]
        assert domains_after == initial_stats["domains"], "Domain whitelist should be preserved"

    def test_cleanup_with_yes_flag(self, populated_db):
        """Test cleanup with --yes flag skips confirmation."""
        db, initial_stats = populated_db

        # Run script with --yes flag (no input needed)
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--yes"],
            capture_output=True,
            text=True,
        )

        # Should succeed without prompting
        assert result.returncode == 0
        assert "Type 'RESET'" not in result.stdout  # No confirmation prompt

        # Verify data deleted
        cursor = db.connection.execute("SELECT COUNT(*) FROM sessions")
        assert cursor.fetchone()[0] == 0

    def test_cleanup_with_backup(self, populated_db, tmp_path):
        """Test cleanup with --backup flag creates backup file."""
        db, initial_stats = populated_db

        # Run script with --backup and --yes flags
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--backup", "--yes"],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0
        assert "Backup saved" in result.stdout

        # Check backup directory exists
        backup_dir = DB_PATH.parent / "backups"
        assert backup_dir.exists(), "Backup directory should exist"

        # Check backup file was created
        backup_files = list(backup_dir.glob("short_term_memory_backup_*.db"))
        assert len(backup_files) > 0, "Backup file should exist"

        # Verify backup is not empty
        latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
        assert latest_backup.stat().st_size > 0, "Backup should not be empty"

        # Cleanup backup
        latest_backup.unlink()

    def test_database_health_after_cleanup(self, populated_db):
        """Verify database remains healthy after cleanup."""
        db, initial_stats = populated_db

        # Run cleanup
        subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--yes"],
            capture_output=True,
            text=True,
        )

        # Check database health
        health = db.get_health_status()
        assert health["status"] == "healthy", "Database should be healthy after cleanup"
        assert "integrity" in health
        assert health["integrity"] == "ok", "Database integrity should be ok"

        # Verify we can still insert new data
        session_id = f"test_after_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = Session(
            session_id=session_id,
            date="2025-01-02",
            learning_goal="Post-cleanup test",
            building_goal="Testing",
            status="in_progress",
        )
        db.create_session(session)

        cursor = db.connection.execute(
            "SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id,)
        )
        assert cursor.fetchone()[0] == 1, "Should be able to insert after cleanup"

        # Cleanup
        db.connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        db.connection.commit()

    def test_cleanup_shows_statistics(self, populated_db):
        """Test that cleanup script displays meaningful statistics."""
        db, initial_stats = populated_db

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--yes"],
            capture_output=True,
            text=True,
        )

        output = result.stdout

        # Should show deleted counts
        assert "Deleted:" in output
        assert "Sessions:" in output
        assert "Concepts:" in output
        assert "Research Cache:" in output

        # Should show preserved
        assert "Preserved:" in output
        assert "Domain Whitelist:" in output

        # Should show storage info
        assert "Storage:" in output or "Size:" in output

    def test_cleanup_empty_database(self):
        """Test cleanup on already empty database."""
        db = get_db()

        # Ensure database is empty
        db.connection.execute("DELETE FROM sessions")
        db.connection.execute("DELETE FROM research_cache")
        db.connection.commit()

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--yes"],
            capture_output=True,
            text=True,
        )

        # Should detect empty database
        assert result.returncode == 0
        assert "already clean" in result.stdout.lower() or "nothing to" in result.stdout.lower()

    def test_cascade_deletion(self, populated_db):
        """Test that CASCADE deletion works correctly."""
        db, initial_stats = populated_db

        # Get concept count before cleanup
        cursor = db.connection.execute("SELECT COUNT(*) FROM concepts")
        concepts_before = cursor.fetchone()[0]
        assert concepts_before > 0, "Should have concepts to test CASCADE"

        cursor = db.connection.execute("SELECT COUNT(*) FROM concept_stage_data")
        stage_data_before = cursor.fetchone()[0]
        assert stage_data_before > 0, "Should have stage data to test CASCADE"

        # Run cleanup
        subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--yes"],
            capture_output=True,
            text=True,
        )

        # Verify CASCADE deleted concepts
        cursor = db.connection.execute("SELECT COUNT(*) FROM concepts")
        assert cursor.fetchone()[0] == 0, "Concepts should be CASCADE deleted"

        # Verify CASCADE deleted stage data
        cursor = db.connection.execute("SELECT COUNT(*) FROM concept_stage_data")
        assert cursor.fetchone()[0] == 0, "Stage data should be CASCADE deleted"


class TestCleanupScriptIntegration:
    """Integration tests for cleanup script with real workflow."""

    def test_full_workflow_with_cleanup(self):
        """Test complete workflow: populate → cleanup → repopulate."""
        db = get_db()

        # Step 1: Create initial data
        session_id_1 = f"workflow_test_1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_1 = Session(
            session_id=session_id_1,
            date="2025-01-01",
            learning_goal="Workflow test 1",
            building_goal="Testing",
            status="in_progress",
        )
        db.create_session(session_1)

        cursor = db.connection.execute("SELECT COUNT(*) FROM sessions")
        assert cursor.fetchone()[0] >= 1

        # Step 2: Run cleanup
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--yes"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        cursor = db.connection.execute("SELECT COUNT(*) FROM sessions")
        assert cursor.fetchone()[0] == 0

        # Step 3: Create new data after cleanup
        session_id_2 = f"workflow_test_2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_2 = Session(
            session_id=session_id_2,
            date="2025-01-02",
            learning_goal="Workflow test 2",
            building_goal="Testing",
            status="in_progress",
        )
        db.create_session(session_2)

        cursor = db.connection.execute(
            "SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id_2,)
        )
        assert cursor.fetchone()[0] == 1, "Should work normally after cleanup"

        # Cleanup
        db.connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id_2,))
        db.connection.commit()
