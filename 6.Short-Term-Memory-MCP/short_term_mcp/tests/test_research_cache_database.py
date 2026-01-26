"""Schema and model tests for the research cache feature (Session 1)."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from short_term_mcp.database import Database
from short_term_mcp.models import (
    DomainWhitelist,
    ResearchCacheEntry,
    SourceURL,
)


@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary database initialized with all tables."""
    db_path = tmp_path / "research_cache.db"
    db = Database(Path(db_path))
    db.initialize()
    yield db
    db.close()


def test_research_cache_table_exists(temp_db):
    cursor = temp_db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='research_cache'"
    )
    assert cursor.fetchone() is not None


def test_research_cache_schema(temp_db):
    cursor = temp_db.connection.execute("PRAGMA table_info(research_cache)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    expected_columns = {
        "concept_name": "TEXT",
        "explanation": "TEXT",
        "source_urls": "TEXT",
        "last_researched_at": "TEXT",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }
    for name, column_type in expected_columns.items():
        assert columns.get(name) == column_type


def test_research_cache_indexes(temp_db):
    cursor = temp_db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='research_cache'"
    )
    indexes = {row[0] for row in cursor.fetchall()}
    assert "idx_research_cache_name" in indexes
    assert "idx_research_cache_created" in indexes


def test_domain_whitelist_table_exists(temp_db):
    cursor = temp_db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='domain_whitelist'"
    )
    assert cursor.fetchone() is not None


def test_domain_whitelist_schema(temp_db):
    cursor = temp_db.connection.execute("PRAGMA table_info(domain_whitelist)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    expected_columns = {
        "domain": "TEXT",
        "category": "TEXT",
        "quality_score": "REAL",
        "added_at": "TEXT",
        "added_by": "TEXT",
    }
    for name, column_type in expected_columns.items():
        assert columns.get(name) == column_type


def test_domain_whitelist_initial_population(temp_db):
    cursor = temp_db.connection.execute("SELECT COUNT(*) FROM domain_whitelist")
    count = cursor.fetchone()[0]
    assert count == 10


def test_domain_whitelist_categories(temp_db):
    cursor = temp_db.connection.execute(
        "SELECT DISTINCT category FROM domain_whitelist ORDER BY category"
    )
    categories = [row[0] for row in cursor.fetchall()]
    assert categories == ["authoritative", "in_depth", "official"]


def test_research_cache_entry_model_valid():
    entry = ResearchCacheEntry(
        concept_name="python asyncio",
        explanation="Async IO primitives in Python",
        source_urls=[
            SourceURL(
                url="https://docs.python.org/3/library/asyncio.html",
                title="asyncio docs",
                quality_score=1.0,
                domain_category="official",
            )
        ],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert entry.concept_name == "python asyncio"
    assert entry.source_urls and len(entry.source_urls) == 1


def test_research_cache_entry_invalid_name():
    with pytest.raises(ValidationError):
        ResearchCacheEntry(
            concept_name="",
            explanation="missing name",
            last_researched_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


def test_domain_whitelist_model_invalid_category():
    with pytest.raises(ValidationError):
        DomainWhitelist(
            domain="example.com",
            category="blog",
            quality_score=0.5,
            added_at=datetime.now(),
        )


def test_source_url_requires_valid_url():
    with pytest.raises(ValidationError):
        SourceURL(url="notaurl", title="Invalid URL")
