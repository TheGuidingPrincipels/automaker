"""Tests for health check endpoint."""


def test_health_check(client):
    """Test that health check returns status and database info."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert data["database"] in ["connected", "unavailable"]
    assert "version" in data


def test_root_endpoint(client):
    """Test that root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "DeepRead API"
    assert "version" in data
