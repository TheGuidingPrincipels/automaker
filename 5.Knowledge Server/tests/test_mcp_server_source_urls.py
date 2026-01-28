"""
Tests for source_urls parameter in MCP server tool wrappers.

Tests that mcp_server.py tool functions correctly expose and pass through
the source_urls parameter to the underlying concept_tools functions.
"""

import inspect
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest


# Add parent directory to path to import mcp_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_create_concept_signature_includes_source_urls():
    """Test that create_concept function signature includes source_urls parameter"""
    # Import the module to get access to the functions
    import mcp_server

    # Get the actual function from the decorated tool
    # The @mcp.tool() decorator wraps the function, so we need to get the original
    create_concept_func = None

    # Search for the function in the module
    for name, obj in inspect.getmembers(mcp_server):
        if name == "create_concept":
            # If it's a FunctionTool, get the underlying function
            create_concept_func = obj.fn if hasattr(obj, "fn") else obj
            break

    assert create_concept_func is not None, "create_concept function not found"

    # Get the signature
    sig = inspect.signature(create_concept_func)
    params = list(sig.parameters.keys())

    # Assert that source_urls is in the parameters
    assert "source_urls" in params, f"source_urls not found in parameters: {params}"

    # Verify it has the correct default value (None)
    source_urls_param = sig.parameters["source_urls"]
    assert source_urls_param.default is None or source_urls_param.default == inspect.Parameter.empty


@pytest.mark.asyncio
async def test_create_concept_passes_source_urls_to_backend():
    """Test that create_concept passes source_urls parameter to concept_tools.create_concept"""
    import mcp_server

    # Get the underlying function
    create_concept_func = None
    for name, obj in inspect.getmembers(mcp_server):
        if name == "create_concept":
            create_concept_func = obj.fn if hasattr(obj, "fn") else obj
            break

    assert create_concept_func is not None

    # Arrange
    source_urls_json = json.dumps(
        [
            {
                "url": "https://docs.python.org",
                "title": "Python Docs",
                "quality_score": 1.0,
                "domain_category": "official",
            }
        ]
    )

    mock_result = {
        "success": True,
        "message": "Concept created successfully",
        "data": {
            "concept_id": "test-concept-123"
        }
    }

    # Mock concept_tools.create_concept to verify it receives source_urls
    with patch("mcp_server.concept_tools.create_concept", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_result

        # Act - call the underlying function with source_urls
        result = await create_concept_func(
            name="Test Concept",
            explanation="Test explanation",
            area="coding-development",
            topic="Python",
            source_urls=source_urls_json,
        )

        # Assert - verify result is correct
        assert result["success"] is True
        assert result["data"]["concept_id"] == "test-concept-123"

        # Assert - verify concept_tools.create_concept was called with source_urls
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert "source_urls" in call_kwargs
        assert call_kwargs["source_urls"] == source_urls_json


def test_update_concept_signature_includes_source_urls():
    """Test that update_concept function signature includes source_urls parameter"""
    import mcp_server

    # Get the actual function from the decorated tool
    update_concept_func = None

    # Search for the function in the module
    for name, obj in inspect.getmembers(mcp_server):
        if name == "update_concept":
            # If it's a FunctionTool, get the underlying function
            update_concept_func = obj.fn if hasattr(obj, "fn") else obj
            break

    assert update_concept_func is not None, "update_concept function not found"

    # Get the signature
    sig = inspect.signature(update_concept_func)
    params = list(sig.parameters.keys())

    # Assert that source_urls is in the parameters
    assert "source_urls" in params, f"source_urls not found in parameters: {params}"

    # Verify it has the correct default value (None)
    source_urls_param = sig.parameters["source_urls"]
    assert source_urls_param.default is None or source_urls_param.default == inspect.Parameter.empty


@pytest.mark.asyncio
async def test_update_concept_passes_source_urls_to_backend():
    """Test that update_concept passes source_urls parameter to concept_tools.update_concept"""
    import mcp_server

    # Get the underlying function
    update_concept_func = None
    for name, obj in inspect.getmembers(mcp_server):
        if name == "update_concept":
            update_concept_func = obj.fn if hasattr(obj, "fn") else obj
            break

    assert update_concept_func is not None

    # Arrange
    source_urls_json = json.dumps(
        [
            {
                "url": "https://realpython.com/tutorials",
                "title": "Real Python Tutorials",
                "quality_score": 0.9,
                "domain_category": "in_depth",
            }
        ]
    )

    mock_result = {
        "success": True,
        "updated_fields": ["source_urls"],
        "message": "Concept updated successfully",
    }

    # Mock concept_tools.update_concept to verify it receives source_urls
    with patch("mcp_server.concept_tools.update_concept", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_result

        # Act - call the underlying function with source_urls
        result = await update_concept_func(
            concept_id="test-concept-123",
            explanation="Updated explanation",
            source_urls=source_urls_json,
        )

        # Assert - verify result is correct
        assert result["success"] is True
        assert "source_urls" in result["updated_fields"]

        # Assert - verify concept_tools.update_concept was called with source_urls
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert "source_urls" in call_kwargs
        assert call_kwargs["source_urls"] == source_urls_json


@pytest.mark.asyncio
async def test_create_concept_backward_compatible_without_source_urls():
    """Test that create_concept works when source_urls is omitted (backward compatibility)"""
    import mcp_server

    # Get the underlying function
    create_concept_func = None
    for name, obj in inspect.getmembers(mcp_server):
        if name == "create_concept":
            create_concept_func = obj.fn if hasattr(obj, "fn") else obj
            break

    assert create_concept_func is not None

    mock_result = {
        "success": True,
        "message": "Concept created successfully",
        "data": {
            "concept_id": "test-concept-456"
        }
    }

    # Mock concept_tools.create_concept
    with patch("mcp_server.concept_tools.create_concept", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_result

        # Act - call WITHOUT source_urls parameter (backward compatibility)
        result = await create_concept_func(
            name="Test Concept",
            explanation="Test explanation",
            area="coding-development",
            topic="General",
        )

        # Assert - verify it works without errors
        assert result["success"] is True
        assert result["data"]["concept_id"] == "test-concept-456"

        # Assert - verify concept_tools.create_concept was called with source_urls=None
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert "source_urls" in call_kwargs
        assert call_kwargs["source_urls"] is None


@pytest.mark.asyncio
async def test_update_concept_backward_compatible_without_source_urls():
    """Test that update_concept works when source_urls is omitted (backward compatibility)"""
    import mcp_server

    # Get the underlying function
    update_concept_func = None
    for name, obj in inspect.getmembers(mcp_server):
        if name == "update_concept":
            update_concept_func = obj.fn if hasattr(obj, "fn") else obj
            break

    assert update_concept_func is not None

    mock_result = {
        "success": True,
        "updated_fields": ["explanation"],
        "message": "Concept updated successfully",
    }

    # Mock concept_tools.update_concept
    with patch("mcp_server.concept_tools.update_concept", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_result

        # Act - call WITHOUT source_urls parameter (backward compatibility)
        result = await update_concept_func(
            concept_id="test-concept-456", explanation="Updated explanation"
        )

        # Assert - verify it works without errors
        assert result["success"] is True
        assert "explanation" in result["updated_fields"]

        # Assert - verify concept_tools.update_concept was called with source_urls=None
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert "source_urls" in call_kwargs
        assert call_kwargs["source_urls"] is None


@pytest.mark.asyncio
async def test_root_cause_verification_create_concept_accepts_source_urls():
    """
    ROOT CAUSE VERIFICATION TEST

    Original issue: create_concept rejects source_urls parameter with
    'unexpected_keyword_argument' error.

    This test reproduces the exact scenario from the issue report and verifies
    that it no longer produces a TypeError.
    """
    import mcp_server

    # Get the underlying function
    create_concept_func = None
    for name, obj in inspect.getmembers(mcp_server):
        if name == "create_concept":
            create_concept_func = obj.fn if hasattr(obj, "fn") else obj
            break

    # Exact source_urls format from issue report
    source_urls_from_issue = json.dumps(
        [
            {
                "url": "https://docs.python.org/3/library/asyncio.html",
                "title": "asyncio - Python Docs",
                "quality_score": 0.8,
                "domain_category": "official",
            }
        ]
    )

    mock_result = {
        "success": True,
        "message": "Concept created",
        "data": {
            "concept_id": "concept-xyz"
        }
    }

    with patch("mcp_server.concept_tools.create_concept", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_result

        # This used to raise: TypeError: unexpected keyword argument 'source_urls'
        # Now it should work without error
        result = await create_concept_func(
            name="Python asyncio",
            explanation="Asynchronous I/O in Python",
            area="coding-development",
            topic="Python",
            source_urls=source_urls_from_issue,
        )

        # Verify no TypeError was raised and result is correct
        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-xyz"

        # Verify the parameter was successfully passed through
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["source_urls"] == source_urls_from_issue


@pytest.mark.asyncio
async def test_root_cause_verification_update_concept_accepts_source_urls():
    """
    ROOT CAUSE VERIFICATION TEST

    Original issue: update_concept rejects source_urls parameter with
    'unexpected_keyword_argument' error.

    This test reproduces the exact scenario from the issue report and verifies
    that it no longer produces a TypeError.
    """
    import mcp_server

    # Get the underlying function
    update_concept_func = None
    for name, obj in inspect.getmembers(mcp_server):
        if name == "update_concept":
            update_concept_func = obj.fn if hasattr(obj, "fn") else obj
            break

    # Exact source_urls format from issue report
    source_urls_from_issue = json.dumps(
        [
            {
                "url": "https://docs.python.org/3/library/asyncio.html",
                "title": "asyncio - Python Docs",
                "quality_score": 0.8,
                "domain_category": "official",
            }
        ]
    )

    mock_result = {"success": True, "updated_fields": ["source_urls"], "message": "Concept updated"}

    with patch("mcp_server.concept_tools.update_concept", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_result

        # This used to raise: TypeError: unexpected keyword argument 'source_urls'
        # Now it should work without error
        result = await update_concept_func(
            concept_id="concept-123",
            explanation="Updated explanation",
            source_urls=source_urls_from_issue,
        )

        # Verify no TypeError was raised and result is correct
        assert result["success"] is True
        assert "source_urls" in result["updated_fields"]

        # Verify the parameter was successfully passed through
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["source_urls"] == source_urls_from_issue
