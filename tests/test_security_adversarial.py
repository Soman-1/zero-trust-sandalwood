"""Adversarial Penetration and Security Tests for Zero Trust Architecture."""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi import status
from sqlalchemy import select

from app.database.models.environmental_measurement import EnvironmentalMeasurement
from app.database.models.audit_log import AuditLog
from app.services.audit_service import AuditService


def register_and_login_admin(client, suffix=""):
    """Helper to create and login admin user."""
    client.post("/api/v1/auth/register", json={
        "email": f"sec_admin_{suffix}@agroforestry.gov.in",
        "username": f"sec_admin_{suffix}",
        "full_name": "Security Officer",
        "password": "SecPassword12345!",
        "role": "ADMIN",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": f"sec_admin_{suffix}",
        "password": "SecPassword12345!",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_attack_token_replay_after_logout(client):
    """Attack Scenario 1: Replay an access token after user has explicitly logged out."""
    client.post("/api/v1/auth/register", json={
        "email": "replay_user@agroforestry.gov.in",
        "username": "replay_user",
        "full_name": "Replay User",
        "password": "SecPassword12345!",
        "role": "ADMIN",
    })
    login_resp = client.post("/api/v1/auth/login", json={
        "username_or_email": "replay_user",
        "password": "SecPassword12345!",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works initially
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == status.HTTP_200_OK

    # Logout (revokes session in database)
    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == status.HTTP_200_OK

    # Attacker tries to replay the same token -> must be rejected
    replayed = client.get("/api/v1/auth/me", headers=headers)
    assert replayed.status_code == status.HTTP_401_UNAUTHORIZED
    data = replayed.json()
    err_msg = data.get("error", {}).get("message", "") or data.get("message", "")
    assert "revoked" in err_msg.lower() or "session" in err_msg.lower() or "invalid" in err_msg.lower()


def test_attack_forged_and_revoked_device_credentials(client):
    """Attack Scenario 2: Telemetry transmission with forged keys or revoked devices."""
    admin_headers = register_and_login_admin(client, suffix="dev")

    # Create Region
    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-SEC-DEV",
            "name": "Security Test Plot",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [76.00, 14.00],
                        [76.10, 14.00],
                        [76.10, 14.10],
                        [76.00, 14.10],
                        [76.00, 14.00],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )

    # Register Device
    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-SEC-NODE", "name": "Security Sensor Node", "assigned_region_id": region_resp.json().get("id")},
        headers=admin_headers,
    )
    api_key = dev_reg.json()["api_key"]
    dev_headers = {"X-Device-ID": "DEV-SEC-NODE", "X-Device-Key": api_key}

    # 1. Attacker sends with fake API key
    fake_headers = {"X-Device-ID": "DEV-SEC-NODE", "X-Device-Key": "sw_dev_fake_key_1234567890"}
    r1 = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": "REG-SEC-DEV",
            "latitude": 14.05,
            "longitude": 76.05,
            "temperature": 25.0,
            "humidity": 60.0,
            "soil_moisture": 50.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=fake_headers,
    )
    assert r1.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Admin revokes the real device
    client.patch("/api/v1/devices/DEV-SEC-NODE/status", json={"status": "REVOKED"}, headers=admin_headers)

    # 3. Revoked device tries to transmit telemetry -> 403 Forbidden
    r2 = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": "REG-SEC-DEV",
            "latitude": 14.05,
            "longitude": 76.05,
            "temperature": 25.0,
            "humidity": 60.0,
            "soil_moisture": 50.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=dev_headers,
    )
    assert r2.status_code == status.HTTP_403_FORBIDDEN


def test_attack_gps_coordinate_spoofing_outside_boundary(client):
    """Attack Scenario 3: Telemetry spoofed with coordinates outside the region boundary."""
    admin_headers = register_and_login_admin(client, suffix="gps")

    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-SEC-GPS",
            "name": "GPS Security Plot",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [76.00, 14.00],
                        [76.10, 14.00],
                        [76.10, 14.10],
                        [76.00, 14.10],
                        [76.00, 14.00],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )

    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-SEC-GPS", "name": "GPS Node", "assigned_region_id": region_resp.json().get("id")},
        headers=admin_headers,
    )
    api_key = dev_reg.json()["api_key"]
    valid_dev_headers = {"X-Device-ID": "DEV-SEC-GPS", "X-Device-Key": api_key}

    # Telemetry ingest no longer rejects GPS against forest-reserve polygons.
    # Tree registration still enforces region boundaries (checked separately).
    spoofed = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": "REG-SEC-GPS",
            "latitude": 18.5000,
            "longitude": 78.5000,
            "temperature": 26.0,
            "humidity": 55.0,
            "soil_moisture": 45.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=valid_dev_headers,
    )
    assert spoofed.status_code == status.HTTP_201_CREATED
    assert spoofed.json()["success"] is True
    assert "measurement_uid" in spoofed.json()


def test_attack_impossible_physical_sensor_values(client):
    """Attack Scenario 4: Sensor spoofing with physically impossible values."""
    admin_headers = register_and_login_admin(client, suffix="spoof")

    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-SEC-SPOOF",
            "name": "Spoof Security Plot",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [76.00, 14.00],
                        [76.10, 14.00],
                        [76.10, 14.10],
                        [76.00, 14.10],
                        [76.00, 14.00],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )

    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-SEC-SPOOF", "name": "Spoofed Sensor", "assigned_region_id": region_resp.json().get("id")},
        headers=admin_headers,
    )
    api_key = dev_reg.json()["api_key"]
    valid_dev_headers = {"X-Device-ID": "DEV-SEC-SPOOF", "X-Device-Key": api_key}

    # Temperature 150°C (impossible on Earth agroforestry) -> rejected by schema validator
    r1 = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": "REG-SEC-SPOOF",
            "latitude": 14.05,
            "longitude": 76.05,
            "temperature": 150.0,
            "humidity": 50.0,
            "soil_moisture": 50.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=valid_dev_headers,
    )
    assert r1.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # Future timestamp in year 2099 -> rejected by domain validator
    future_time = (datetime.now(timezone.utc) + timedelta(days=3650)).isoformat()
    r2 = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": "REG-SEC-SPOOF",
            "latitude": 14.05,
            "longitude": 76.05,
            "temperature": 25.0,
            "humidity": 50.0,
            "soil_moisture": 50.0,
            "recorded_at": future_time,
        },
        headers=valid_dev_headers,
    )
    assert r2.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


def test_attack_direct_database_tampering_detection(client, db_session):
    """Attack Scenario 5: Unauthorized rogue script alters recorded telemetry in database."""
    admin_headers = register_and_login_admin(client, suffix="tamper")

    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-SEC-TAMPER",
            "name": "Tamper Security Plot",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [76.00, 14.00],
                        [76.10, 14.00],
                        [76.10, 14.10],
                        [76.00, 14.10],
                        [76.00, 14.00],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )

    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-SEC-TAMPER", "name": "Tamper Test Node", "assigned_region_id": region_resp.json().get("id")},
        headers=admin_headers,
    )
    api_key = dev_reg.json()["api_key"]
    dev_headers = {"X-Device-ID": "DEV-SEC-TAMPER", "X-Device-Key": api_key}

    # Ingest legitimate observation
    resp = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": "REG-SEC-TAMPER",
            "latitude": 14.05,
            "longitude": 76.05,
            "temperature": 28.0,
            "humidity": 65.0,
            "soil_moisture": 55.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=dev_headers,
    )
    meas_uid = resp.json()["measurement_uid"]

    # Attacker directly alters temperature to 42.0 in the database table
    stmt = select(EnvironmentalMeasurement).where(EnvironmentalMeasurement.measurement_uid == meas_uid)
    record = db_session.execute(stmt).scalar_one()
    record.temperature = 42.0
    db_session.commit()

    # Zero Trust verification must flag tampering
    verify_resp = client.post(f"/api/v1/measurements/{meas_uid}/verify-integrity", headers=admin_headers)
    assert verify_resp.status_code == status.HTTP_200_OK
    data = verify_resp.json()
    assert data["is_valid"] is False
    assert data["status"] == "TAMPERED_DETECTED"


def test_attack_privilege_escalation_block(client):
    """Attack Scenario 6: Low-privileged VIEWER attempts administrative actions."""
    # Register Viewer
    client.post("/api/v1/auth/register", json={
        "email": "sec_viewer_esc@agroforestry.gov.in",
        "username": "sec_viewer_esc",
        "full_name": "Read Only Viewer",
        "password": "SecPassword12345!",
        "role": "VIEWER",
    })
    view_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "sec_viewer_esc",
        "password": "SecPassword12345!",
    }).json()["access_token"]
    view_headers = {"Authorization": f"Bearer {view_token}"}

    # Viewer attempts to register device -> 403 Forbidden
    r1 = client.post("/api/v1/devices", json={"device_id": "DEV-ROGUE", "name": "Rogue Node"}, headers=view_headers)
    assert r1.status_code == status.HTTP_403_FORBIDDEN

    # Viewer attempts to decommission region -> 403 Forbidden
    r2 = client.delete("/api/v1/regions/REG-SEC-TEST", headers=view_headers)
    assert r2.status_code == status.HTTP_403_FORBIDDEN


def test_attack_denial_of_service_flood_detection(client):
    """Attack Scenario 7: Sudden flood of requests from a single caller (Page 11 DoS defense)."""
    import time
    from app.core import runtime
    attacker_id = "DEV-FLOOD-ATTACKER-99"
    current_time = time.time()

    # Simulate rapid burst exceeding the 60 req/s rate limit threshold
    previous_exempt = runtime.exempt_testclient_rate_limit
    runtime.exempt_testclient_rate_limit = False
    responses = []
    try:
        for i in range(75):
            resp = client.get(
                "/health",
                headers={
                    "X-Timestamp": str(current_time),
                    "X-Device-ID": attacker_id,
                },
            )
            responses.append(resp)
    finally:
        runtime.exempt_testclient_rate_limit = previous_exempt

    # Early requests should succeed
    assert responses[0].status_code == status.HTTP_200_OK

    # Subsequent flooded requests must be blocked with 429 Too Many Requests / DOS_ATTACK_DETECTED
    last_resp = responses[-1]
    assert last_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    data = last_resp.json()
    assert data["error"]["code"] == "DOS_ATTACK_DETECTED"
    assert "Denial-of-Service" in data["error"]["message"]
