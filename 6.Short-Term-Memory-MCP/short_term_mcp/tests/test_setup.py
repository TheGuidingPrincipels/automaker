"""Setup and dependency tests for Phase 0"""

import pytest


def test_dependencies():
    """Test that all required dependencies can be imported"""
    try:
        import fastmcp
        import pydantic
        import pytest

        assert True, "All dependencies imported successfully"
    except ImportError as e:
        pytest.fail(f"Failed to import dependency: {e}")


def test_config():
    """Test that configuration loads correctly"""
    from short_term_mcp.config import DATA_DIR, DB_PATH, LOG_DIR

    assert DATA_DIR.exists(), "Data directory should exist"
    assert LOG_DIR.exists(), "Log directory should exist"
    assert DB_PATH.parent.exists(), "Database parent directory should exist"


def test_project_structure():
    """Test that all required files exist"""
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent

    # Check directories
    assert (project_root / "short_term_mcp").exists()
    assert (project_root / "short_term_mcp" / "tests").exists()
    assert (project_root / "data").exists()
    assert (project_root / "logs").exists()

    # Check files
    required_files = [
        "short_term_mcp/__init__.py",
        "short_term_mcp/config.py",
        "short_term_mcp/database.py",
        "short_term_mcp/models.py",
        "short_term_mcp/tools.py",
        "short_term_mcp/server.py",
        "short_term_mcp/utils.py",
        "short_term_mcp/tests/__init__.py",
    ]

    for file_path in required_files:
        assert (project_root / file_path).exists(), f"{file_path} should exist"
