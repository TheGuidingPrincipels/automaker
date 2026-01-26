# short_term_mcp/tests/test_research_cache_utils.py

import pytest

from short_term_mcp.database import Database
from short_term_mcp.utils import normalize_concept_name, score_sources

# =============================================================================
# NORMALIZATION TESTS (15 tests)
# =============================================================================


def test_normalize_lowercase():
    """Test lowercase conversion"""
    assert normalize_concept_name("Python Asyncio") == "python asyncio"
    assert normalize_concept_name("KUBERNETES") == "kubernetes"


def test_normalize_whitespace_collapse():
    """Test multiple spaces collapsed to single space"""
    assert normalize_concept_name("python  asyncio") == "python asyncio"
    assert normalize_concept_name("a    b    c") == "a b c"


def test_normalize_strip_whitespace():
    """Test leading/trailing whitespace removed"""
    assert normalize_concept_name("  python  ") == "python"
    assert normalize_concept_name("\tpython\n") == "python"


def test_normalize_unicode_nfc():
    """Test Unicode NFC normalization"""
    # Composed vs decomposed forms
    composed = "café"  # U+00E9
    decomposed = "cafe\u0301"  # e + combining acute
    assert normalize_concept_name(composed) == normalize_concept_name(decomposed)
    assert normalize_concept_name(composed) == "café"


def test_normalize_emoji():
    """Test emoji preservation"""
    assert normalize_concept_name("🚀 rocket") == "🚀 rocket"
    assert normalize_concept_name("  🔥  firebase  ") == "🔥 firebase"


def test_normalize_tabs_newlines():
    """Test tabs and newlines replaced with spaces"""
    assert normalize_concept_name("python\tasyncio") == "python asyncio"
    assert normalize_concept_name("python\nasyncio") == "python asyncio"
    assert normalize_concept_name("python\r\nasyncio") == "python asyncio"


def test_normalize_empty_string():
    """Test empty string raises ValueError"""
    with pytest.raises(ValueError, match="cannot be empty"):
        normalize_concept_name("")


def test_normalize_none():
    """Test None input raises ValueError"""
    with pytest.raises(ValueError, match="cannot be empty"):
        normalize_concept_name(None)


def test_normalize_long_string():
    """Test extremely long string (no crash)"""
    long_string = "a " * 5000  # 10,000 characters
    result = normalize_concept_name(long_string)
    assert len(result) < len(long_string)  # Whitespace collapsed


def test_normalize_mixed_scripts():
    """Test mixed scripts preserved"""
    assert normalize_concept_name("Python 中文") == "python 中文"
    assert normalize_concept_name("Привет World") == "привет world"


def test_normalize_special_characters():
    """Test special characters preserved"""
    assert normalize_concept_name("C++/C#") == "c++/c#"
    assert normalize_concept_name("@angular/core") == "@angular/core"


def test_normalize_combining_characters():
    """Test combining characters preserved"""
    assert normalize_concept_name("naïve") == "naïve"
    assert normalize_concept_name("résumé") == "résumé"


def test_normalize_zero_width_characters():
    """Test zero-width characters handled"""
    # Zero-width space should be collapsed with adjacent whitespace
    assert normalize_concept_name("python\u200basyncio") == "python asyncio"


def test_normalize_idempotency():
    """Test normalization is idempotent"""
    input_text = "  Mixed   CASE   Unicode café  "
    normalized_once = normalize_concept_name(input_text)
    normalized_twice = normalize_concept_name(normalized_once)
    assert normalized_once == normalized_twice


def test_normalize_performance():
    """Test normalization performance <1ms for typical inputs"""
    import time

    test_input = "Python Async Programming" * 10  # ~250 chars

    start = time.perf_counter()
    for _ in range(100):
        normalize_concept_name(test_input)
    end = time.perf_counter()

    avg_time_ms = ((end - start) / 100) * 1000
    assert avg_time_ms < 1.0, f"Performance target missed: {avg_time_ms:.3f}ms"


# =============================================================================
# SOURCE SCORING TESTS (10 tests)
# =============================================================================


@pytest.fixture
def db_with_whitelist():
    """Create test database with domain whitelist"""
    db = Database(":memory:")
    db.initialize()
    return db


def test_score_sources_official_domain(db_with_whitelist):
    """Test official domain scores 1.0"""
    urls = [{"url": "https://docs.python.org/tutorial", "title": "Python Tutorial"}]
    scored = score_sources(urls, db_with_whitelist)

    assert scored[0]["quality_score"] == 1.0
    assert scored[0]["domain_category"] == "official"


def test_score_sources_in_depth_domain(db_with_whitelist):
    """Test in-depth domain scores 0.8"""
    urls = [{"url": "https://realpython.com/advanced", "title": "Real Python"}]
    scored = score_sources(urls, db_with_whitelist)

    assert scored[0]["quality_score"] == 0.8
    assert scored[0]["domain_category"] == "in_depth"


def test_score_sources_authoritative_domain(db_with_whitelist):
    """Test authoritative domain scores 0.6"""
    urls = [{"url": "https://stackoverflow.com/questions/123", "title": "SO Post"}]
    scored = score_sources(urls, db_with_whitelist)

    assert scored[0]["quality_score"] == 0.6
    assert scored[0]["domain_category"] == "authoritative"


def test_score_sources_unknown_domain(db_with_whitelist):
    """Test unknown domain scores 0.0"""
    urls = [{"url": "https://random-blog.com/post", "title": "Random Post"}]
    scored = score_sources(urls, db_with_whitelist)

    assert scored[0]["quality_score"] == 0.0
    assert scored[0]["domain_category"] is None


def test_score_sources_subdomain_matching(db_with_whitelist):
    """Test subdomain matches parent domain"""
    urls = [{"url": "https://api.github.com/repos", "title": "GitHub API"}]
    scored = score_sources(urls, db_with_whitelist)

    # github.com is whitelisted as authoritative (0.6)
    assert scored[0]["quality_score"] == 0.6
    assert scored[0]["domain_category"] == "authoritative"


def test_score_sources_case_insensitive(db_with_whitelist):
    """Test case-insensitive domain lookup"""
    urls = [{"url": "https://DOCS.PYTHON.ORG/tutorial", "title": "Tutorial"}]
    scored = score_sources(urls, db_with_whitelist)

    assert scored[0]["quality_score"] == 1.0


def test_score_sources_empty_list():
    """Test empty URL list returns empty list"""
    scored = score_sources([], None)
    assert scored == []


def test_score_sources_malformed_url(db_with_whitelist):
    """Test malformed URL handled gracefully"""
    urls = [{"url": "not-a-url", "title": "Invalid"}]
    scored = score_sources(urls, db_with_whitelist)

    # Should not crash, assign score 0.0
    assert scored[0]["quality_score"] == 0.0


def test_score_sources_sorting(db_with_whitelist):
    """Test sources sorted by quality_score DESC"""
    urls = [
        {"url": "https://random-blog.com/post", "title": "Blog"},
        {"url": "https://docs.python.org/tutorial", "title": "Docs"},
        {"url": "https://stackoverflow.com/questions/123", "title": "SO"},
    ]
    scored = score_sources(urls, db_with_whitelist)

    # Should be sorted: official (1.0), authoritative (0.6), unknown (0.0)
    assert scored[0]["quality_score"] == 1.0
    assert scored[1]["quality_score"] == 0.6
    assert scored[2]["quality_score"] == 0.0


def test_score_sources_performance(db_with_whitelist):
    """Test scoring performance <50ms for 100 URLs"""
    import time

    # Create 100 test URLs (mix of known and unknown domains)
    urls = []
    for i in range(100):
        if i % 3 == 0:
            urls.append({"url": f"https://docs.python.org/page{i}", "title": f"Doc {i}"})
        elif i % 3 == 1:
            urls.append({"url": f"https://stackoverflow.com/q/{i}", "title": f"SO {i}"})
        else:
            urls.append({"url": f"https://random-blog-{i}.com/post", "title": f"Blog {i}"})

    start = time.perf_counter()
    scored = score_sources(urls, db_with_whitelist)
    end = time.perf_counter()

    duration_ms = (end - start) * 1000
    assert duration_ms < 50.0, f"Performance target missed: {duration_ms:.3f}ms"
    assert len(scored) == 100
