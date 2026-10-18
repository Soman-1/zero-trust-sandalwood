"""Tests for health check, root endpoint, and core error handling."""

from fastapi import status


def test_health_check_returns_minimal_status(client):
    """Public health stays minimal so it does not disclose service internals."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    assert set(data.keys()) == {"status"}


def test_root_endpoint_returns_metadata(client):
    """Test that the root / endpoint returns metadata."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/health"


def test_openapi_documentation_accessible(client):
    """Test that OpenAPI docs and JSON schema endpoints are reachable."""
    docs_response = client.get("/docs")
    assert docs_response.status_code == status.HTTP_200_OK

    schema_response = client.get("/openapi.json")
    assert schema_response.status_code == status.HTTP_200_OK
    schema = schema_response.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "/health" in schema["paths"]


def test_not_found_endpoint_returns_structured_error(client):
    """Test that non-existent routes return structured JSON error instead of default text."""
    from tests.conftest import auth_headers
    headers = auth_headers(client, "health_not_found")
    response = client.get("/api/v1/non-existent-endpoint", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"
    assert data["error"]["message"] == "Not Found"
