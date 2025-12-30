"""Test health check endpoint."""

import pytest


@pytest.mark.unit
def test_health_check(client):
    """Test health check endpoint returns success."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["version"] == "1.0.0"
    assert data["error"] is None
