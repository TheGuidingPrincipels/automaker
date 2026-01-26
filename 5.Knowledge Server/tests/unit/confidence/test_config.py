"""
Unit tests for cache configuration.

Tests environment variable loading, defaults, and security validation.
"""

import os

import pytest

from services.confidence.config import CacheConfig
from config import reset_settings


def test_cache_config_uses_environment_variables():
    """Config should read from environment variables"""
    os.environ["REDIS_HOST"] = "redis.example.com"
    os.environ["REDIS_PORT"] = "6380"
    os.environ["REDIS_DB"] = "5"

    config = CacheConfig()

    assert config.REDIS_HOST == "redis.example.com"
    assert config.REDIS_PORT == 6380
    assert config.REDIS_DB == 5

    # Cleanup
    del os.environ["REDIS_HOST"]
    del os.environ["REDIS_PORT"]
    del os.environ["REDIS_DB"]


def test_cache_config_uses_defaults_when_env_not_set():
    """Config should use defaults if environment not set"""
    # Ensure env vars are not set
    for key in ["REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD"]:
        os.environ.pop(key, None)

    config = CacheConfig()

    assert config.REDIS_HOST == "localhost"
    assert config.REDIS_PORT == 6379
    assert config.REDIS_DB == 0
    assert config.REDIS_PASSWORD == ""
    assert config.SCORE_CACHE_TTL == 3600
    assert config.CALC_CACHE_TTL == 86400


def test_cache_config_has_correct_key_prefixes():
    """Config should define correct cache key prefixes"""
    config = CacheConfig()

    assert config.SCORE_KEY_PREFIX == "confidence:score:"
    assert config.CALC_RELATIONSHIP_PREFIX == "confidence:calc:relationships:"
    assert config.CALC_REVIEW_PREFIX == "confidence:calc:review:"


def test_cache_config_has_performance_settings():
    """Config should have performance-related settings"""
    config = CacheConfig()

    assert config.MAX_CACHE_KEYS == 10000
    assert config.CONNECTION_POOL_SIZE == 10
    assert config.SOCKET_TIMEOUT == 5


def test_cache_config_validates_security_in_production():
    """Production environment should require Redis password"""
    # Reset settings singleton to pick up new env vars
    reset_settings()
    os.environ["ENV"] = "production"  # Use ENV (not ENVIRONMENT) per config/settings.py
    os.environ["REDIS_PASSWORD"] = ""

    try:
        reset_settings()  # Reset again after setting env vars
        config = CacheConfig()

        with pytest.raises(ValueError, match="Redis authentication required"):
            config.validate_security()
    finally:
        # Cleanup
        os.environ.pop("ENV", None)
        os.environ.pop("REDIS_PASSWORD", None)
        reset_settings()  # Reset to clean state


def test_cache_config_allows_empty_password_in_development():
    """Development environment should allow empty Redis password"""
    reset_settings()
    os.environ["ENV"] = "development"  # Use ENV per config/settings.py
    os.environ.pop("REDIS_PASSWORD", None)

    try:
        reset_settings()  # Reset again after setting env vars
        config = CacheConfig()

        # Should not raise exception
        config.validate_security()
    finally:
        # Cleanup
        os.environ.pop("ENV", None)
        reset_settings()


def test_cache_config_ssl_settings():
    """Config should support SSL/TLS settings"""
    os.environ["REDIS_SSL"] = "true"
    os.environ["REDIS_SSL_CERT_REQS"] = "required"

    config = CacheConfig()

    assert config.REDIS_SSL is True
    assert config.REDIS_SSL_CERT_REQS == "required"

    # Cleanup
    del os.environ["REDIS_SSL"]
    del os.environ["REDIS_SSL_CERT_REQS"]


def test_cache_config_ssl_defaults_to_false():
    """SSL should default to false in development"""
    os.environ.pop("REDIS_SSL", None)

    config = CacheConfig()

    assert config.REDIS_SSL is False
