"""Tests for Code Teacher support tools (Phase 5)"""

import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from short_term_mcp.database import Database
from short_term_mcp.models import Concept, ConceptStatus, Session, SessionStatus
from short_term_mcp.tools_impl import (
    get_todays_concepts_impl,
    get_todays_learning_goals_impl,
    search_todays_concepts_impl,
)
from short_term_mcp.utils import get_cache


@pytest.fixture
def test_db():
    """Create test data in production database for today's session"""
    from short_term_mcp.database import get_db

    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    # Clean up any existing test data for today
    existing = db.get_session(today)
    if existing:
        # Delete existing session (will cascade to concepts)
        with db.transaction():
            db.connection.execute("DELETE FROM sessions WHERE session_id = ?", (today,))

    # Create today's session
    session = Session(
        session_id=today,
        date=today,
        learning_goal="Learn React Hooks",
        building_goal="Build todo app",
        status=SessionStatus.IN_PROGRESS,
    )
    db.create_session(session)

    # Create test concepts
    concepts_data = [
        {"name": "useState Hook", "area": "Frontend", "topic": "React"},
        {"name": "useEffect Hook", "area": "Frontend", "topic": "React"},
        {"name": "useContext Hook", "area": "Frontend", "topic": "React"},
        {"name": "Custom Hooks", "area": "Frontend", "topic": "React"},
        {"name": "Redux Toolkit", "area": "Frontend", "topic": "State Management"},
    ]

    for i, data in enumerate(concepts_data):
        concept = Concept(
            concept_id=f"test-concept-{i}",
            session_id=today,
            concept_name=data["name"],
            current_status=ConceptStatus.IDENTIFIED if i < 3 else ConceptStatus.CHUNKED,
            identified_at=datetime.now().isoformat(),
            current_data={"area": data["area"], "topic": data["topic"]},
        )
        db.create_concept(concept)

    yield db

    # Cleanup - remove test data
    with db.transaction():
        db.connection.execute("DELETE FROM sessions WHERE session_id = ?", (today,))


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test"""
    cache = get_cache()
    cache.clear()
    yield
    cache.clear()


# ============================================================================
# TEST CLASS 1: BASIC FUNCTIONALITY
# ============================================================================


class TestCodeTeacherBasics:
    """Test basic Code Teacher functionality"""

    @pytest.mark.asyncio
    async def test_get_todays_concepts_success(self, test_db):
        """Test getting today's concepts"""
        result = await get_todays_concepts_impl()

        assert result["status"] == "success"
        assert "date" in result
        assert result["concept_count"] == 5
        assert result["learning_goal"] == "Learn React Hooks"
        assert result["building_goal"] == "Build todo app"
        assert len(result["concepts"]) == 5
        assert result["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_get_todays_concepts_no_session(self):
        """Test when no session exists for today"""
        # No test_db fixture = no session
        result = await get_todays_concepts_impl()

        assert result["status"] == "not_found"
        assert "No session found for today" in result["message"]
        assert result["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_get_todays_concepts_statistics(self, test_db):
        """Test concept statistics in response"""
        result = await get_todays_concepts_impl()

        stats = result["concepts_by_status"]
        assert stats["identified"] == 3
        assert stats["chunked"] == 2
        assert stats["encoded"] == 0
        assert stats["evaluated"] == 0
        assert stats["stored"] == 0

    @pytest.mark.asyncio
    async def test_get_todays_learning_goals_success(self, test_db):
        """Test getting today's learning goals"""
        result = await get_todays_learning_goals_impl()

        assert result["status"] == "success"
        assert result["learning_goal"] == "Learn React Hooks"
        assert result["building_goal"] == "Build todo app"
        assert result["concept_count"] == 5
        assert result["session_status"] == "in_progress"
        assert "concepts" not in result  # Should not include full concept list
        assert result["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_get_todays_learning_goals_no_session(self):
        """Test learning goals when no session exists"""
        result = await get_todays_learning_goals_impl()

        assert result["status"] == "not_found"
        assert "No session found for today" in result["message"]


# ============================================================================
# TEST CLASS 2: SEARCH FUNCTIONALITY
# ============================================================================


class TestCodeTeacherSearch:
    """Test search functionality"""

    @pytest.mark.asyncio
    async def test_search_by_concept_name(self, test_db):
        """Test searching by concept name"""
        result = await search_todays_concepts_impl("useState")

        assert result["status"] == "success"
        assert result["match_count"] == 1
        assert result["matches"][0]["concept_name"] == "useState Hook"
        assert result["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, test_db):
        """Test case-insensitive search"""
        result = await search_todays_concepts_impl("HOOK")

        assert result["status"] == "success"
        assert result["match_count"] == 4  # All hook concepts
        assert result["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_search_by_data_content(self, test_db):
        """Test searching in current_data JSON"""
        result = await search_todays_concepts_impl("State Management")

        assert result["status"] == "success"
        assert result["match_count"] == 1
        assert result["matches"][0]["concept_name"] == "Redux Toolkit"
        assert result["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_search_empty_term(self, test_db):
        """Test search with empty term"""
        result = await search_todays_concepts_impl("")

        assert result["status"] == "error"
        assert result["error_code"] == "EMPTY_SEARCH_TERM"

    @pytest.mark.asyncio
    async def test_search_no_matches(self, test_db):
        """Test search with no matches"""
        result = await search_todays_concepts_impl("Angular")

        assert result["status"] == "success"
        assert result["match_count"] == 0
        assert result["matches"] == []

    @pytest.mark.asyncio
    async def test_search_no_session(self):
        """Test search when no session exists"""
        result = await search_todays_concepts_impl("test")

        assert result["status"] == "not_found"
        assert "No session found for today" in result["message"]


# ============================================================================
# TEST CLASS 3: CACHING BEHAVIOR
# ============================================================================


class TestCodeTeacherCaching:
    """Test caching behavior"""

    @pytest.mark.asyncio
    async def test_get_todays_concepts_caching(self, test_db):
        """Test that todays concepts are cached"""
        # First call - cache miss
        result1 = await get_todays_concepts_impl()
        assert result1["cache_hit"] is False

        # Second call - cache hit
        result2 = await get_todays_concepts_impl()
        assert result2["cache_hit"] is True
        assert result2["concept_count"] == result1["concept_count"]

    @pytest.mark.asyncio
    async def test_get_todays_learning_goals_caching(self, test_db):
        """Test that learning goals are cached"""
        # First call - cache miss
        result1 = await get_todays_learning_goals_impl()
        assert result1["cache_hit"] is False

        # Second call - cache hit
        result2 = await get_todays_learning_goals_impl()
        assert result2["cache_hit"] is True
        assert result2["learning_goal"] == result1["learning_goal"]

    @pytest.mark.asyncio
    async def test_search_results_caching(self, test_db):
        """Test that search results are cached per query"""
        # First search - cache miss
        result1 = await search_todays_concepts_impl("Hook")
        assert result1["cache_hit"] is False

        # Same search - cache hit
        result2 = await search_todays_concepts_impl("Hook")
        assert result2["cache_hit"] is True
        assert result2["match_count"] == result1["match_count"]

        # Different search - cache miss
        result3 = await search_todays_concepts_impl("Redux")
        assert result3["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_cache_expiration(self, test_db):
        """Test that cache entries expire after TTL"""
        from short_term_mcp.utils import SimpleCache

        # Create cache with 1-second TTL for testing
        test_cache = SimpleCache(default_ttl=1)

        # Set a value
        test_cache.set("test_key", {"data": "test"})

        # Should be cached
        assert test_cache.get("test_key") is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert test_cache.get("test_key") is None


# ============================================================================
# TEST CLASS 4: PERFORMANCE
# ============================================================================


class TestCodeTeacherPerformance:
    """Test performance targets"""

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, test_db):
        """Test cache hit performance (<1ms target)"""
        # Prime the cache
        await get_todays_concepts_impl()

        # Measure cache hit
        start = time.perf_counter()
        await get_todays_concepts_impl()
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 1.0, f"Cache hit took {elapsed:.2f}ms (target: <1ms)"

    @pytest.mark.asyncio
    async def test_cache_miss_query_performance(self, test_db):
        """Test cache miss query performance (<50ms target)"""
        get_cache().clear()

        start = time.perf_counter()
        result = await get_todays_concepts_impl()
        elapsed = (time.perf_counter() - start) * 1000

        assert result["status"] == "success"
        assert elapsed < 50.0, f"Query took {elapsed:.2f}ms (target: <50ms)"

    @pytest.mark.asyncio
    async def test_search_performance(self, test_db):
        """Test search performance with 5 concepts (<100ms target)"""
        start = time.perf_counter()
        result = await search_todays_concepts_impl("Hook")
        elapsed = (time.perf_counter() - start) * 1000

        assert result["status"] == "success"
        assert elapsed < 100.0, f"Search took {elapsed:.2f}ms (target: <100ms)"


# ============================================================================
# TEST CLASS 5: INTEGRATION
# ============================================================================


class TestCodeTeacherIntegration:
    """Test integration scenarios"""

    @pytest.mark.asyncio
    async def test_code_teacher_query_pattern(self, test_db):
        """Test typical Code Teacher query pattern"""
        # 1. Get learning goals for context
        goals = await get_todays_learning_goals_impl()
        assert goals["status"] == "success"

        # 2. Search for specific concept
        search = await search_todays_concepts_impl("useState")
        assert search["status"] == "success"
        assert search["match_count"] > 0

        # 3. Get all concepts if needed
        concepts = await get_todays_concepts_impl()
        assert concepts["status"] == "success"
        assert concepts["concept_count"] > 0

    @pytest.mark.asyncio
    async def test_cache_independence(self, test_db):
        """Test that different queries maintain separate caches"""
        # Make different queries
        concepts = await get_todays_concepts_impl()
        goals = await get_todays_learning_goals_impl()
        search = await search_todays_concepts_impl("Hook")

        # All should be cache misses
        assert concepts["cache_hit"] is False
        assert goals["cache_hit"] is False
        assert search["cache_hit"] is False

        # Second calls should be cache hits
        concepts2 = await get_todays_concepts_impl()
        goals2 = await get_todays_learning_goals_impl()
        search2 = await search_todays_concepts_impl("Hook")

        assert concepts2["cache_hit"] is True
        assert goals2["cache_hit"] is True
        assert search2["cache_hit"] is True
