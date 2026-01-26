"""Helper functions for Short-Term Memory MCP Server"""

import re
import threading
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .config import CACHE_TTL


class CacheEntry:
    """Single cache entry with expiration"""

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        """Check if this cache entry has expired"""
        return datetime.now() > self.expires_at


class SimpleCache:
    """Thread-safe cache with TTL support (sync + async friendly)."""

    def __init__(self, default_ttl: int = CACHE_TTL):
        self.cache: dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self._lock = threading.RLock()

    @property
    def lock(self) -> threading.RLock:
        """Expose the underlying lock for rare manual coordination."""
        return self._lock

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        with self.lock:
            entry = self.cache.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self.cache[key]
                return None

            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set cache value with TTL."""
        with self.lock:
            ttl = ttl or self.default_ttl
            self.cache[key] = CacheEntry(value, ttl)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries, return count removed."""
        with self.lock:
            expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)


# Global cache instance for Code Teacher queries
_code_teacher_cache = SimpleCache()

# Global cache instance for general use
cache = SimpleCache()


def get_cache() -> SimpleCache:
    """Get the global Code Teacher cache instance"""
    return _code_teacher_cache


# =============================================================================
# RESEARCH CACHE UTILITIES (Session 002)
# =============================================================================


def normalize_concept_name(name: str) -> str:
    """
    Normalize concept name for cache lookup.

    Normalization steps:
    1. Unicode NFC normalization (composed form)
    2. Lowercase conversion
    3. Whitespace collapse (multiple spaces → single space)
    4. Strip leading/trailing whitespace

    Args:
        name: Raw concept name (user input)

    Returns:
        Normalized concept name (cache key)

    Raises:
        ValueError: If name is empty or None

    Examples:
        >>> normalize_concept_name("Python Asyncio")
        "python asyncio"

        >>> normalize_concept_name("  Multiple   Spaces  ")
        "multiple spaces"

        >>> normalize_concept_name("café")
        "café"
    """
    if not name:
        raise ValueError("Concept name cannot be empty or None")

    # Step 1: Unicode NFC normalization (composed form)
    # This ensures "café" (U+00E9) and "café" (U+0065 U+0301) are equivalent
    normalized = unicodedata.normalize("NFC", name)

    # Step 2: Lowercase conversion
    normalized = normalized.lower()

    # Step 3: Replace zero-width characters with spaces (they are word separators)
    # Zero-width space (U+200B), zero-width joiner (U+200D), zero-width non-joiner (U+200C)
    normalized = normalized.replace("\u200b", " ")  # Zero-width space
    normalized = normalized.replace("\u200c", " ")  # Zero-width non-joiner
    normalized = normalized.replace("\u200d", " ")  # Zero-width joiner
    normalized = normalized.replace("\ufeff", " ")  # Zero-width no-break space

    # Step 4: Whitespace collapse
    # Replace all whitespace sequences (spaces, tabs, newlines) with single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Step 5: Strip leading/trailing whitespace
    normalized = normalized.strip()

    return normalized


def score_sources(urls: List[Dict], db) -> List[Dict]:
    """
    Score source URLs using domain whitelist.

    Scoring algorithm:
    1. Extract domain from URL
    2. Lookup domain in whitelist (case-insensitive, subdomain matching)
    3. Assign quality_score and domain_category from whitelist
    4. Unknown domains get score 0.0 and null category
    5. Sort by quality_score DESC (highest first)

    Args:
        urls: List of source URL dicts with 'url' and optional 'title'
        db: Database instance for whitelist lookup

    Returns:
        List of source URL dicts with added quality_score and domain_category,
        sorted by quality_score descending

    Examples:
        >>> urls = [
        ...     {"url": "https://docs.python.org/tutorial", "title": "Tutorial"},
        ...     {"url": "https://stackoverflow.com/questions/123", "title": "SO Post"}
        ... ]
        >>> scored = score_sources(urls, db)
        >>> scored[0]["quality_score"]
        1.0
    """
    if not urls:
        return []

    scored_urls = []

    for url_dict in urls:
        url = url_dict.get("url", "")

        # Extract domain from URL
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if not domain:
                # Malformed URL or non-HTTP scheme
                scored_urls.append({**url_dict, "quality_score": 0.0, "domain_category": None})
                continue

            # Lookup domain in whitelist (with subdomain matching)
            quality_score, domain_category = _lookup_domain_quality(domain, db)

            scored_urls.append(
                {**url_dict, "quality_score": quality_score, "domain_category": domain_category}
            )

        except Exception:
            # Malformed URL - skip but don't crash
            scored_urls.append({**url_dict, "quality_score": 0.0, "domain_category": None})

    # Sort by quality_score DESC (highest first)
    scored_urls.sort(key=lambda x: x.get("quality_score", 0.0), reverse=True)

    return scored_urls


def _lookup_domain_quality(domain: str, db) -> tuple[float, Optional[str]]:
    """
    Lookup domain quality in whitelist.

    Supports subdomain matching:
    - api.github.com matches github.com
    - docs.python.org matches exactly

    Args:
        domain: Lowercased domain (e.g., "docs.python.org")
        db: Database instance

    Returns:
        Tuple of (quality_score, domain_category)
        Returns (0.0, None) if domain not whitelisted
    """
    cursor = db.connection.cursor()

    # Try exact match first
    cursor.execute(
        """
        SELECT quality_score, category
        FROM domain_whitelist
        WHERE LOWER(domain) = ?
    """,
        (domain,),
    )

    row = cursor.fetchone()
    if row:
        return (row[0], row[1])

    # Try parent domain match (for subdomains)
    # Extract parent domain: api.github.com → github.com
    parts = domain.split(".")
    if len(parts) > 2:
        parent_domain = ".".join(parts[-2:])  # Last two parts
        cursor.execute(
            """
            SELECT quality_score, category
            FROM domain_whitelist
            WHERE LOWER(domain) = ?
        """,
            (parent_domain,),
        )

        row = cursor.fetchone()
        if row:
            return (row[0], row[1])

    # Unknown domain
    return (0.0, None)
