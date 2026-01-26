"""Tests for research cache MCP tools"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from short_term_mcp.models import DomainWhitelist, ResearchCacheEntry, SourceURL
from short_term_mcp.tools_impl import (
    add_domain_to_whitelist_impl,
    check_research_cache_impl,
    list_whitelisted_domains_impl,
    remove_domain_from_whitelist_impl,
    trigger_research_impl,
    update_research_cache_impl,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock database for testing"""
    mock = Mock()
    mock.async_get_research_cache_entry = AsyncMock()
    mock.async_upsert_research_cache = AsyncMock()
    mock.async_add_domain_to_whitelist = AsyncMock()
    mock.async_remove_domain_from_whitelist = AsyncMock()
    mock.async_list_whitelisted_domains = AsyncMock()
    mock.connection = Mock()
    return mock


@pytest.fixture
def sample_cache_entry():
    """Sample research cache entry"""
    return ResearchCacheEntry(
        id=1,
        concept_name="python asyncio",
        explanation="Python's asynchronous I/O library",
        source_urls=[
            SourceURL(
                url="https://docs.python.org/3/library/asyncio.html",
                title="asyncio Documentation",
                quality_score=1.0,
                domain_category="official",
            )
        ],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_domain():
    """Sample domain whitelist entry"""
    return DomainWhitelist(
        id=1,
        domain="docs.python.org",
        category="official",
        quality_score=1.0,
        added_at=datetime.now(),
        added_by="ai",
    )


# ============================================================================
# TEST: check_research_cache_impl
# ============================================================================


@pytest.mark.asyncio
async def test_check_cache_hit(mock_db, sample_cache_entry):
    """Test cache hit returns entry with age"""
    mock_db.async_get_research_cache_entry.return_value = sample_cache_entry

    result = await check_research_cache_impl("Python Asyncio", mock_db)

    assert result["cached"] is True
    assert result["entry"] is not None
    assert result["cache_age_seconds"] >= 0
    assert isinstance(result["cache_age_seconds"], int)
    mock_db.async_get_research_cache_entry.assert_called_once_with("Python Asyncio")


@pytest.mark.asyncio
async def test_check_cache_miss(mock_db):
    """Test cache miss returns null entry"""
    mock_db.async_get_research_cache_entry.return_value = None

    result = await check_research_cache_impl("Unknown Concept", mock_db)

    assert result["cached"] is False
    assert result["entry"] is None
    assert result["cache_age_seconds"] is None
    mock_db.async_get_research_cache_entry.assert_called_once_with("Unknown Concept")


# ============================================================================
# TEST: trigger_research_impl
# ============================================================================


@pytest.mark.asyncio
async def test_trigger_research_returns_mock_data(mock_db):
    """Test trigger_research returns mock research data"""
    # Mock score_sources function behavior
    mock_db.connection.cursor.return_value.execute.return_value.fetchone.return_value = None

    result = await trigger_research_impl("Python Asyncio", "Explain async", mock_db)

    assert result["concept_name"] == "Python Asyncio"
    assert "explanation" in result
    assert len(result["explanation"]) > 0
    assert "source_urls" in result
    assert isinstance(result["source_urls"], list)
    assert len(result["source_urls"]) > 0


@pytest.mark.asyncio
async def test_trigger_research_with_empty_prompt(mock_db):
    """Test trigger_research works with empty prompt"""
    mock_db.connection.cursor.return_value.execute.return_value.fetchone.return_value = None

    result = await trigger_research_impl("FastAPI", "", mock_db)

    assert result["concept_name"] == "FastAPI"
    assert "source_urls" in result


# ============================================================================
# TEST: update_research_cache_impl
# ============================================================================


@pytest.mark.asyncio
async def test_update_cache_inserts_new_entry(mock_db, sample_cache_entry):
    """Test update_research_cache inserts new entry"""
    mock_db.async_get_research_cache_entry.return_value = None  # No existing entry
    mock_db.async_upsert_research_cache.return_value = sample_cache_entry
    mock_db.connection.cursor.return_value.execute.return_value.fetchone.return_value = None

    result = await update_research_cache_impl(
        "python asyncio",
        "Python's async library",
        [{"url": "https://docs.python.org/asyncio", "title": "Asyncio Docs"}],
        mock_db,
    )

    assert result["success"] is True
    assert result["action"] == "inserted"
    assert result["entry"] is not None
    mock_db.async_upsert_research_cache.assert_called_once()


@pytest.mark.asyncio
async def test_update_cache_updates_existing_entry(mock_db, sample_cache_entry):
    """Test update_research_cache updates existing entry"""
    mock_db.async_get_research_cache_entry.return_value = sample_cache_entry  # Existing entry
    mock_db.async_upsert_research_cache.return_value = sample_cache_entry
    mock_db.connection.cursor.return_value.execute.return_value.fetchone.return_value = None

    result = await update_research_cache_impl(
        "python asyncio",
        "Updated explanation",
        [{"url": "https://docs.python.org/asyncio", "title": "Asyncio Docs"}],
        mock_db,
    )

    assert result["success"] is True
    assert result["action"] == "updated"
    assert result["entry"] is not None


@pytest.mark.asyncio
async def test_update_cache_scores_sources(mock_db, sample_cache_entry):
    """Test update_research_cache scores source URLs"""
    mock_db.async_get_research_cache_entry.return_value = None
    mock_db.async_upsert_research_cache.return_value = sample_cache_entry
    mock_db.connection.cursor.return_value.execute.return_value.fetchone.return_value = None

    urls = [
        {"url": "https://docs.python.org/asyncio", "title": "Official Docs"},
        {"url": "https://example.com/tutorial", "title": "Tutorial"},
    ]

    result = await update_research_cache_impl("python asyncio", "Async programming", urls, mock_db)

    assert result["success"] is True
    # Verify that upsert was called (sources were scored and passed)
    mock_db.async_upsert_research_cache.assert_called_once()


# ============================================================================
# TEST: add_domain_to_whitelist_impl
# ============================================================================


@pytest.mark.asyncio
async def test_add_domain_succeeds(mock_db, sample_domain):
    """Test add_domain_to_whitelist succeeds"""
    mock_db.async_add_domain_to_whitelist.return_value = sample_domain

    result = await add_domain_to_whitelist_impl("docs.python.org", "official", 1.0, mock_db)

    assert result["success"] is True
    assert result["domain"]["domain"] == "docs.python.org"
    assert result["domain"]["category"] == "official"
    assert result["domain"]["quality_score"] == 1.0
    mock_db.async_add_domain_to_whitelist.assert_called_once_with(
        domain="docs.python.org", category="official", quality_score=1.0, added_by="ai"
    )


@pytest.mark.asyncio
async def test_add_domain_duplicate_error(mock_db):
    """Test add_domain_to_whitelist returns success: false on duplicate"""
    # Mock database returning None (duplicate domain)
    mock_db.async_add_domain_to_whitelist.return_value = None

    result = await add_domain_to_whitelist_impl("docs.python.org", "official", 1.0, mock_db)

    assert result["success"] is False
    assert "already exists" in result["message"].lower()


# ============================================================================
# TEST: remove_domain_from_whitelist_impl
# ============================================================================


@pytest.mark.asyncio
async def test_remove_domain_succeeds(mock_db):
    """Test remove_domain_from_whitelist succeeds"""
    mock_db.async_remove_domain_from_whitelist.return_value = True

    result = await remove_domain_from_whitelist_impl("docs.python.org", mock_db)

    assert result["success"] is True
    assert "removed" in result["message"]
    mock_db.async_remove_domain_from_whitelist.assert_called_once_with("docs.python.org")


@pytest.mark.asyncio
async def test_remove_domain_not_found(mock_db):
    """Test remove_domain_from_whitelist handles not found"""
    mock_db.async_remove_domain_from_whitelist.return_value = False

    result = await remove_domain_from_whitelist_impl("unknown.com", mock_db)

    assert result["success"] is False
    assert "not found" in result["message"]


# ============================================================================
# TEST: list_whitelisted_domains_impl
# ============================================================================


@pytest.mark.asyncio
async def test_list_domains_all(mock_db, sample_domain):
    """Test list_whitelisted_domains returns all domains"""
    domains = [sample_domain]
    mock_db.async_list_whitelisted_domains.return_value = domains

    result = await list_whitelisted_domains_impl(None, mock_db)

    assert result["count"] == 1
    assert result["filter"] == "all"
    assert len(result["domains"]) == 1
    assert result["domains"][0]["domain"] == "docs.python.org"
    mock_db.async_list_whitelisted_domains.assert_called_once_with(category=None)


@pytest.mark.asyncio
async def test_list_domains_filtered_by_category(mock_db, sample_domain):
    """Test list_whitelisted_domains filters by category"""
    domains = [sample_domain]
    mock_db.async_list_whitelisted_domains.return_value = domains

    result = await list_whitelisted_domains_impl("official", mock_db)

    assert result["count"] == 1
    assert result["filter"] == "official"
    assert len(result["domains"]) == 1
    mock_db.async_list_whitelisted_domains.assert_called_once_with(category="official")


@pytest.mark.asyncio
async def test_list_domains_empty_result(mock_db):
    """Test list_whitelisted_domains handles empty result"""
    mock_db.async_list_whitelisted_domains.return_value = []

    result = await list_whitelisted_domains_impl("in_depth", mock_db)

    assert result["count"] == 0
    assert result["filter"] == "in_depth"
    assert result["domains"] == []


@pytest.mark.asyncio
async def test_list_domains_normalizes_null_string(mock_db, sample_domain):
    """Test list_whitelisted_domains normalizes 'null' string to None"""
    domains = [sample_domain]
    mock_db.async_list_whitelisted_domains.return_value = domains

    # Pass "null" string - should be normalized to None before db call
    result = await list_whitelisted_domains_impl("null", mock_db)

    assert result["count"] == 1
    assert result["filter"] == "all"  # "null" normalized to None, so filter is "all"
    # Verify db was called with None, not "null"
    mock_db.async_list_whitelisted_domains.assert_called_once_with(category=None)


@pytest.mark.asyncio
async def test_list_domains_normalizes_empty_string(mock_db, sample_domain):
    """Test list_whitelisted_domains normalizes empty string to None"""
    domains = [sample_domain]
    mock_db.async_list_whitelisted_domains.return_value = domains

    # Pass empty string - should be normalized to None before db call
    result = await list_whitelisted_domains_impl("", mock_db)

    assert result["count"] == 1
    assert result["filter"] == "all"  # "" normalized to None, so filter is "all"
    # Verify db was called with None, not ""
    mock_db.async_list_whitelisted_domains.assert_called_once_with(category=None)


@pytest.mark.asyncio
async def test_list_domains_preserves_valid_category(mock_db, sample_domain):
    """Test list_whitelisted_domains preserves valid category strings"""
    domains = [sample_domain]
    mock_db.async_list_whitelisted_domains.return_value = domains

    # Pass valid category - should NOT be normalized
    result = await list_whitelisted_domains_impl("official", mock_db)

    assert result["filter"] == "official"
    # Verify db was called with "official", not None
    mock_db.async_list_whitelisted_domains.assert_called_once_with(category="official")


@pytest.mark.asyncio
async def test_add_domain_with_community_category(mock_db):
    """Test add_domain_to_whitelist accepts 'community' as valid category"""
    community_domain = DomainWhitelist(
        id=2,
        domain="stackoverflow.com",
        category="community",
        quality_score=0.6,
        added_at=datetime.now(),
        added_by="ai",
    )
    mock_db.async_add_domain_to_whitelist.return_value = community_domain

    result = await add_domain_to_whitelist_impl("stackoverflow.com", "community", 0.6, mock_db)

    assert result["success"] is True
    assert result["domain"]["domain"] == "stackoverflow.com"
    assert result["domain"]["category"] == "community"
    assert result["domain"]["quality_score"] == 0.6
    mock_db.async_add_domain_to_whitelist.assert_called_once_with(
        domain="stackoverflow.com", category="community", quality_score=0.6, added_by="ai"
    )
