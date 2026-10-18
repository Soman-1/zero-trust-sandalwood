"""Tests for IoT field device registration, Zero Trust authentication, and lifecycle management."""

import pytest
from fastapi import status


def get_auth_token(client, username="admin_tester", role="ADMIN"):
    """Helper fixture to register and login a user, returning a bearer token."""
    client.post("/api/v1/auth/register", json={
        "email": f"{username}@agroforestry.gov.in",
        "username": username,
        "full_name": f"{username} FullName",
        "password": "Password12345!",
        "role": role,
    })
    resp = client.post("/api/v1/auth/login", json={
        "username_or_email": username,
        "password": "Password12345!",
    })
    return resp.json()["access_token"]


def test_device_registration_success(client):
    """Test successful device registration and raw key generation."""
    token = get_auth_token(client, "admin_dev_1", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "device_id": "DEV-KA-001",
        "name": "Shivamogga Field Handheld #1",
        "device_type": "FIELD_HANDHELD",
    }
    response = client.post("/api/v1/devices", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "api_key" in data
    assert data["api_key"].startswith("sw_dev_")
    assert data["device"]["device_id"] == "DEV-KA-001"
    assert data["device"]["status"] == "ACTIVE"


def test_duplicate_device_id_rejection(client):
    """Test that duplicate hardware IDs are rejected."""
    token = get_auth_token(client, "admin_dev_2", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "device_id": "DEV-KA-DUP",
        "name": "Duplicate Test Node",
        "device_type": "STATIONARY_NODE",
    }
    r1 = client.post("/api/v1/devices", json=payload, headers=headers)
    assert r1.status_code == status.HTTP_201_CREATED

    r2 = client.post("/api/v1/devices", json=payload, headers=headers)
    assert r2.status_code == status.HTTP_400_BAD_REQUEST
    assert r2.json()["error"]["code"] == "DEVICE_ALREADY_EXISTS"


def test_device_authentication_and_heartbeat(client):
    """Test device authentication and heartbeat telemetry check-in."""
    token = get_auth_token(client, "admin_dev_3", "ADMIN")
    reg_resp = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-KA-SENSOR-10", "name": "Sensor 10"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = reg_resp.json()["api_key"]

    # Heartbeat with valid credentials
    dev_headers = {
        "X-Device-ID": "DEV-KA-SENSOR-10",
        "X-Device-Key": api_key,
    }
    heartbeat_resp = client.post(
        "/api/v1/devices/heartbeat",
        json={"latitude": 13.9310, "longitude": 75.5720},
        headers=dev_headers,
    )
    assert heartbeat_resp.status_code == status.HTTP_200_OK
    hb_data = heartbeat_resp.json()
    assert hb_data["success"] is True
    assert hb_data["device_id"] == "DEV-KA-SENSOR-10"
    assert hb_data["last_seen_at"] is not None


def test_zero_trust_invalid_device_credentials(client):
    """Test rejection of unknown devices and invalid API keys."""
    # 1. Unknown device ID
    r1 = client.post(
        "/api/v1/devices/heartbeat",
        json={"latitude": 13.9, "longitude": 75.5},
        headers={"X-Device-ID": "DEV-UNKNOWN", "X-Device-Key": "sw_dev_fakekey123"},
    )
    assert r1.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Valid device ID with wrong key
    token = get_auth_token(client, "admin_dev_4", "ADMIN")
    client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-KA-SENSOR-11", "name": "Sensor 11"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r2 = client.post(
        "/api/v1/devices/heartbeat",
        json={"latitude": 13.9, "longitude": 75.5},
        headers={"X-Device-ID": "DEV-KA-SENSOR-11", "X-Device-Key": "sw_dev_wrong_key"},
    )
    assert r2.status_code == status.HTTP_401_UNAUTHORIZED


def test_zero_trust_device_revocation(client):
    """
    Zero Trust Test:
    When a field device is marked REVOKED, all further submissions from it
    must be blocked with 403 Forbidden.
    """
    admin_token = get_auth_token(client, "admin_dev_5", "ADMIN")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Register device
    reg_resp = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-COMPROMISED-01", "name": "Lost Handheld"},
        headers=admin_headers,
    )
    api_key = reg_resp.json()["api_key"]
    dev_headers = {
        "X-Device-ID": "DEV-COMPROMISED-01",
        "X-Device-Key": api_key,
    }

    # 2. Verify device works initially
    pre_revoke = client.post("/api/v1/devices/heartbeat", json={}, headers=dev_headers)
    assert pre_revoke.status_code == status.HTTP_200_OK

    # 3. Admin revokes the device
    revoke_resp = client.patch(
        "/api/v1/devices/DEV-COMPROMISED-01/status",
        json={"status": "REVOKED"},
        headers=admin_headers,
    )
    assert revoke_resp.status_code == status.HTTP_200_OK
    assert revoke_resp.json()["status"] == "REVOKED"

    # 4. Revoked device attempts heartbeat -> MUST be 403 Forbidden
    post_revoke = client.post("/api/v1/devices/heartbeat", json={}, headers=dev_headers)
    assert post_revoke.status_code == status.HTTP_403_FORBIDDEN
    assert post_revoke.json()["error"]["details"]["reason"] == "device_revoked"


def test_device_rbac_permissions(client):
    """Test that VIEWER users cannot register or modify devices."""
    viewer_token = get_auth_token(client, "viewer_dev_user", "VIEWER")
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Viewer attempts device registration -> 403 Forbidden
    r1 = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-UNAUTH", "name": "Unauthorized Device"},
        headers=viewer_headers,
    )
    assert r1.status_code == status.HTTP_403_FORBIDDEN
