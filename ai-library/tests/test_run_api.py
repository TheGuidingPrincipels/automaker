# tests/test_run_api.py
"""Regression tests for run_api entrypoint."""

import importlib


def test_run_api_is_importable():
    """Importing run_api should not fail (e.g., missing symbols)."""
    importlib.import_module("run_api")

