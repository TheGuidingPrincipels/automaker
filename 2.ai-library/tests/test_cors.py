# tests/test_cors.py
"""Tests for CORS configuration - simulating frontend requests."""

import pytest
from httpx import AsyncClient, ASGITransport

from src.api.main import create_app
from src.config import Config


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create a fresh app instance for CORS testing."""
    return create_app()


@pytest.fixture
async def cors_client(app):
    """Create test client for CORS testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# CORS Preflight (OPTIONS) Tests
# =============================================================================


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin(cors_client):
    """Test CORS preflight request from an allowed origin."""
    response = await cors_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3007"
    assert "GET" in response.headers.get("access-control-allow-methods", "")
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_origin(cors_client):
    """Test CORS preflight request from a disallowed origin."""
    response = await cors_client.options(
        "/health",
        headers={
            "Origin": "http://evil-site.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    # FastAPI CORS middleware returns 400 for disallowed origins
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_preflight_all_allowed_origins(cors_client):
    """Test CORS preflight request works for all configured origins."""
    allowed_origins = [
        "http://localhost:3007",
        "http://localhost:3008",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3007",
        "http://127.0.0.1:3008",
    ]

    for origin in allowed_origins:
        response = await cors_client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200, f"Preflight failed for origin: {origin}"
        assert response.headers.get("access-control-allow-origin") == origin


@pytest.mark.asyncio
async def test_cors_preflight_post_method(cors_client):
    """Test CORS preflight for POST requests (typical for API calls)."""
    response = await cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
    )

    assert response.status_code == 200
    assert "POST" in response.headers.get("access-control-allow-methods", "")


@pytest.mark.asyncio
async def test_cors_preflight_delete_method(cors_client):
    """Test CORS preflight for DELETE requests."""
    response = await cors_client.options(
        "/api/sessions/test123",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "DELETE",
        },
    )

    assert response.status_code == 200
    assert "DELETE" in response.headers.get("access-control-allow-methods", "")


@pytest.mark.asyncio
async def test_cors_preflight_custom_header(cors_client):
    """Test CORS preflight for X-Request-ID custom header."""
    response = await cors_client.options(
        "/api/query/ask",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Request-ID, Content-Type",
        },
    )

    assert response.status_code == 200
    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-request-id" in allowed_headers
    assert "content-type" in allowed_headers


@pytest.mark.asyncio
async def test_cors_preflight_authorization_header(cors_client):
    """Test CORS preflight for Authorization header (for authenticated requests)."""
    response = await cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allowed_headers


# =============================================================================
# CORS Simple Request Tests (Actual requests with Origin header)
# =============================================================================


@pytest.mark.asyncio
async def test_cors_simple_get_allowed_origin(cors_client):
    """Test simple GET request with allowed origin header."""
    response = await cors_client.get(
        "/health",
        headers={"Origin": "http://localhost:3007"},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3007"
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_simple_get_disallowed_origin(cors_client):
    """Test simple GET request with disallowed origin - CORS headers not present."""
    response = await cors_client.get(
        "/health",
        headers={"Origin": "http://malicious-site.com"},
    )

    # The request still succeeds (server-side), but no CORS headers are returned
    # The browser would block the response client-side
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None


@pytest.mark.asyncio
async def test_cors_simple_get_no_origin(cors_client):
    """Test simple GET request without Origin header (same-origin or curl-like)."""
    response = await cors_client.get("/health")

    assert response.status_code == 200
    # No CORS headers should be present when no Origin is provided
    assert response.headers.get("access-control-allow-origin") is None


# =============================================================================
# Frontend Simulation Tests (Full request cycle)
# =============================================================================


@pytest.mark.asyncio
async def test_frontend_fetch_api_root(cors_client):
    """Simulate frontend fetch() call to API root."""
    # Simulate browser fetch() behavior
    response = await cors_client.get(
        "/api",
        headers={
            "Origin": "http://localhost:3007",
            "Accept": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3007"

    data = response.json()
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_frontend_fetch_with_credentials(cors_client):
    """Simulate frontend fetch() with credentials: 'include'."""
    # When credentials: 'include' is used in fetch(), the browser sends cookies
    # and the server must respond with access-control-allow-credentials: true
    response = await cors_client.get(
        "/health",
        headers={
            "Origin": "http://localhost:3007",
            "Cookie": "session_id=test123",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-credentials") == "true"
    # Origin must be explicitly set (not "*") when credentials are used
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3007"


@pytest.mark.asyncio
async def test_frontend_post_json_preflight(cors_client):
    """Simulate frontend POST request preflight (testing CORS not endpoint logic)."""
    # In browser fetch() with POST and JSON body, a preflight is always sent first
    # Testing that the preflight for a POST with Content-Type: application/json works
    preflight = await cors_client.options(
        "/api/query/search",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "POST" in preflight.headers.get("access-control-allow-methods", "")

    # Also test with different allowed origin
    preflight2 = await cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
    )

    assert preflight2.status_code == 200
    assert preflight2.headers.get("access-control-allow-origin") == "http://localhost:3007"


@pytest.mark.asyncio
async def test_frontend_request_with_custom_tracking_header(cors_client):
    """Simulate frontend request with X-Request-ID for tracing."""
    # Preflight for custom header
    preflight = await cors_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID",
        },
    )

    assert preflight.status_code == 200

    # Actual request with custom header
    response = await cors_client.get(
        "/health",
        headers={
            "Origin": "http://localhost:3007",
            "X-Request-ID": "trace-12345",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3007"


# =============================================================================
# CORS Method Validation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_cors_all_allowed_methods(cors_client):
    """Test that all configured HTTP methods are allowed in preflight."""
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

    for method in allowed_methods:
        response = await cors_client.options(
            "/api/sessions",
            headers={
                "Origin": "http://localhost:3007",
                "Access-Control-Request-Method": method,
            },
        )

        assert response.status_code == 200, f"Method {method} not allowed"
        allowed = response.headers.get("access-control-allow-methods", "")
        assert method in allowed, f"Method {method} not in allowed methods"


@pytest.mark.asyncio
async def test_cors_disallowed_method(cors_client):
    """Test that disallowed methods are rejected in preflight."""
    # TRACE method is typically not allowed
    response = await cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "TRACE",
        },
    )

    # FastAPI CORS middleware returns 400 for disallowed methods
    assert response.status_code == 400


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.asyncio
async def test_cors_localhost_vs_127(cors_client):
    """Test that both localhost and 127.0.0.1 variants work."""
    # Both should work independently
    localhost_response = await cors_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "GET",
        },
    )

    ip_response = await cors_client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:3007",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert localhost_response.status_code == 200
    assert ip_response.status_code == 200
    assert localhost_response.headers.get("access-control-allow-origin") == "http://localhost:3007"
    assert ip_response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3007"


@pytest.mark.asyncio
async def test_cors_wrong_port(cors_client):
    """Test that requests from wrong ports are rejected."""
    response = await cors_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:9999",  # Not in allowed list
            "Access-Control-Request-Method": "GET",
        },
    )

    # Should be rejected
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cors_https_not_allowed(cors_client):
    """Test that HTTPS origins are not in the allowed list (dev only has HTTP)."""
    response = await cors_client.options(
        "/health",
        headers={
            "Origin": "https://localhost:3007",  # HTTPS not in allowed list
            "Access-Control-Request-Method": "GET",
        },
    )

    # HTTPS variant is not configured, should be rejected
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cors_null_origin(cors_client):
    """Test that null origin (from file:// or data: URLs) is rejected."""
    response = await cors_client.options(
        "/health",
        headers={
            "Origin": "null",
            "Access-Control-Request-Method": "GET",
        },
    )

    # Null origin should be rejected
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cors_empty_origin(cors_client):
    """Test request with empty Origin header."""
    response = await cors_client.get(
        "/health",
        headers={"Origin": ""},
    )

    # Empty origin should be treated like no origin
    assert response.status_code == 200
    # Should not include CORS headers for empty origin
    assert response.headers.get("access-control-allow-origin") is None


# =============================================================================
# Multiple Headers Combination Tests
# =============================================================================


@pytest.mark.asyncio
async def test_cors_multiple_headers_request(cors_client):
    """Test preflight with multiple custom headers."""
    response = await cors_client.options(
        "/api/query/ask",
        headers={
            "Origin": "http://localhost:3007",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization, X-Request-ID",
        },
    )

    assert response.status_code == 200
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allowed
    assert "authorization" in allowed
    assert "x-request-id" in allowed
