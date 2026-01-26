"""Test configuration utilities.

Provides fixtures and helpers for overriding configuration in tests
without modifying os.environ directly.
"""

import os
from contextlib import contextmanager
from typing import Any, Generator

from config.settings import AppSettings, reset_settings


@contextmanager
def override_settings(**kwargs: Any) -> Generator[None, None, None]:
    """Context manager to override settings for testing.

    Usage:
        with override_settings(NEO4J_PASSWORD="test"):
            settings = get_settings()
            assert settings.neo4j.password == "test"

    Automatically resets the settings singleton after the context exits.

    Args:
        **kwargs: Environment variable overrides. Keys should be the env var names
                  (e.g., NEO4J_PASSWORD, CHROMA_PERSIST_DIRECTORY).
    """
    # Store original env vars
    original_env: dict[str, str | None] = {}

    # Apply env overrides
    for key, value in kwargs.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = str(value)

    # Reset singleton to pick up new values
    reset_settings()

    try:
        yield
    finally:
        # Restore original env
        for key, original in original_env.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original

        # Reset singleton again
        reset_settings()


def create_test_settings(**overrides: Any) -> AppSettings:
    """Create an isolated AppSettings instance for testing.

    Does NOT affect the global singleton.

    Usage:
        settings = create_test_settings(environment="test")
        assert settings.environment == "test"

    Args:
        **overrides: Direct field overrides passed to AppSettings constructor.
    """
    return AppSettings(**overrides)
