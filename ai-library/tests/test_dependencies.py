# tests/test_dependencies.py
"""Tests for FastAPI dependencies."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.api import dependencies
from src.config import Config


@pytest.mark.asyncio
async def test_get_config_does_not_call_sync_loader(monkeypatch):
    """Async get_config should not call the sync loader (blocks event loop)."""
    dependencies._config = None

    def boom():
        raise AssertionError("get_config_sync should not be called from async get_config")

    monkeypatch.setattr(dependencies, "get_config_sync", boom)
    monkeypatch.setattr(dependencies, "load_config", AsyncMock(return_value=Config()))

    config = await dependencies.get_config()
    assert isinstance(config, Config)


@pytest.mark.asyncio
async def test_get_vector_store_surfaces_init_failures():
    """Vector store init failures should raise instead of being silently ignored."""
    dependencies._vector_store = None
    dependencies._vector_store_init_error = None

    config = Config()
    mock_store = AsyncMock()
    mock_store.initialize = AsyncMock(side_effect=RuntimeError("qdrant down"))

    with patch("src.api.dependencies.QdrantVectorStore", return_value=mock_store):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_vector_store(config)

    assert exc.value.status_code == 503
    assert "qdrant down" in str(exc.value.detail)

