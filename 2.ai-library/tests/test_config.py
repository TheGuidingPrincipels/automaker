# tests/test_config.py
"""Tests for config env overrides."""

import pytest

from src.config import load_config


@pytest.mark.asyncio
async def test_env_overrides_apply(monkeypatch, tmp_path):
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("LIBRARY_PATH", str(tmp_path / "library"))
    monkeypatch.setenv("SESSIONS_PATH", str(tmp_path / "sessions"))

    config = await load_config(config_path=str(tmp_path / "missing.yaml"))

    assert config.api.host == "0.0.0.0"
    assert config.api.port == 9000
    assert config.library.path == str(tmp_path / "library")
    assert config.sessions.path == str(tmp_path / "sessions")


@pytest.mark.asyncio
async def test_env_overrides_invalid_port(monkeypatch, tmp_path):
    monkeypatch.setenv("API_PORT", "not-an-int")

    with pytest.raises(ValueError):
        await load_config(config_path=str(tmp_path / "missing.yaml"))
