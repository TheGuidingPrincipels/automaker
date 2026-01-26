# short_term_mcp/tests/test_research_cache_crud.py

from datetime import datetime

import pytest

from short_term_mcp.database import Database
from short_term_mcp.models import DomainWhitelist, ResearchCacheEntry, SourceURL


@pytest.fixture
def db():
    """Create test database"""
    test_db = Database(":memory:")
    test_db.initialize()
    yield test_db
    test_db.close()


# get_research_cache_entry Tests


@pytest.mark.asyncio
async def test_get_cache_entry_exists(db):
    """Test retrieve existing cache entry"""
    entry = ResearchCacheEntry(
        concept_name="python asyncio",
        explanation="Async I/O library",
        source_urls=[SourceURL(url="https://docs.python.org/asyncio", title="Docs")],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    await db.async_upsert_research_cache(entry)

    retrieved = await db.async_get_research_cache_entry("python asyncio")
    assert retrieved is not None
    assert retrieved.concept_name == "python asyncio"
    assert len(retrieved.source_urls) == 1


@pytest.mark.asyncio
async def test_get_cache_entry_not_found(db):
    """Test retrieve non-existent entry returns None"""
    retrieved = await db.async_get_research_cache_entry("nonexistent concept")
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_cache_entry_normalized(db):
    """Test case-insensitive lookup"""
    entry = ResearchCacheEntry(
        concept_name="python asyncio",
        explanation="Test",
        source_urls=[],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    await db.async_upsert_research_cache(entry)

    # Lookup with different case/whitespace
    retrieved = await db.async_get_research_cache_entry("Python  Asyncio")
    assert retrieved is not None
    assert retrieved.concept_name == "python asyncio"


# upsert_research_cache Tests


@pytest.mark.asyncio
async def test_upsert_insert(db):
    """Test insert new cache entry"""
    entry = ResearchCacheEntry(
        concept_name="react hooks",
        explanation="React state management",
        source_urls=[],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    result = await db.async_upsert_research_cache(entry)
    assert result.id is not None

    # Verify in database
    retrieved = await db.async_get_research_cache_entry("react hooks")
    assert retrieved is not None


@pytest.mark.asyncio
async def test_upsert_update(db):
    """Test update existing entry (UPSERT behavior)"""
    # Insert initial
    entry1 = ResearchCacheEntry(
        concept_name="kubernetes pods",
        explanation="Initial explanation",
        source_urls=[],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    result1 = await db.async_upsert_research_cache(entry1)
    original_id = result1.id

    # Update with new explanation
    entry2 = ResearchCacheEntry(
        concept_name="kubernetes pods",
        explanation="Updated explanation",
        source_urls=[SourceURL(url="https://kubernetes.io/pods", title="K8s")],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    result2 = await db.async_upsert_research_cache(entry2)

    # Verify same ID (update, not insert)
    assert result2.id == original_id

    # Verify updated content
    retrieved = await db.async_get_research_cache_entry("kubernetes pods")
    assert retrieved.explanation == "Updated explanation"
    assert len(retrieved.source_urls) == 1


# delete_research_cache Tests


@pytest.mark.asyncio
async def test_delete_cache_exists(db):
    """Test delete existing entry"""
    entry = ResearchCacheEntry(
        concept_name="docker containers",
        explanation="Test",
        source_urls=[],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    await db.async_upsert_research_cache(entry)

    success = await db.async_delete_research_cache("docker containers")
    assert success is True

    # Verify deleted
    retrieved = await db.async_get_research_cache_entry("docker containers")
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_cache_not_found(db):
    """Test delete non-existent entry returns False"""
    success = await db.async_delete_research_cache("nonexistent")
    assert success is False


# search_research_cache Tests


@pytest.mark.asyncio
async def test_search_exact_match(db):
    """Test search with exact match"""
    entry = ResearchCacheEntry(
        concept_name="python list comprehension",
        explanation="Test",
        source_urls=[],
        last_researched_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    await db.async_upsert_research_cache(entry)

    results = await db.async_search_research_cache("python list comprehension")
    assert len(results) == 1
    assert results[0].concept_name == "python list comprehension"


@pytest.mark.asyncio
async def test_search_partial_match(db):
    """Test search with partial match"""
    # Insert multiple entries
    for concept in ["python list comprehension", "python dict comprehension", "javascript arrays"]:
        entry = ResearchCacheEntry(
            concept_name=concept,
            explanation="Test",
            source_urls=[],
            last_researched_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await db.async_upsert_research_cache(entry)

    results = await db.async_search_research_cache("comprehension")
    assert len(results) == 2
    assert all("comprehension" in r.concept_name for r in results)


@pytest.mark.asyncio
async def test_search_no_matches(db):
    """Test search with no matches returns empty list"""
    results = await db.async_search_research_cache("nonexistent")
    assert results == []


# Domain Whitelist Tests


@pytest.mark.asyncio
async def test_add_domain_to_whitelist(db):
    """Test add new domain to whitelist"""
    domain = await db.async_add_domain_to_whitelist(
        domain="fastapi.tiangolo.com", category="official", quality_score=1.0, added_by="ai"
    )
    assert domain.id is not None
    assert domain.domain == "fastapi.tiangolo.com"


@pytest.mark.asyncio
async def test_add_domain_duplicate_error(db):
    """Test adding duplicate domain returns None"""
    await db.async_add_domain_to_whitelist(
        domain="example.com", category="official", quality_score=1.0
    )

    # Attempting to add duplicate should return None
    result = await db.async_add_domain_to_whitelist(
        domain="example.com", category="in_depth", quality_score=0.8
    )
    assert result is None


@pytest.mark.asyncio
async def test_remove_domain_exists(db):
    """Test remove existing domain"""
    await db.async_add_domain_to_whitelist(
        domain="example.com", category="official", quality_score=1.0
    )

    success = await db.async_remove_domain_from_whitelist("example.com")
    assert success is True


@pytest.mark.asyncio
async def test_remove_domain_not_found(db):
    """Test remove non-existent domain returns False"""
    success = await db.async_remove_domain_from_whitelist("nonexistent.com")
    assert success is False


@pytest.mark.asyncio
async def test_list_domains_all(db):
    """Test list all whitelisted domains"""
    domains = await db.async_list_whitelisted_domains()
    assert len(domains) == 10  # Initial seed domains


@pytest.mark.asyncio
async def test_list_domains_by_category(db):
    """Test list domains filtered by category"""
    domains = await db.async_list_whitelisted_domains(category="official")
    assert len(domains) == 4  # 4 official domains in seed data
    assert all(d.category == "official" for d in domains)
