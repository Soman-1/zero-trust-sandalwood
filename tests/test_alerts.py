"""Comprehensive tests for Alert Generation, Operational Lifecycle, and Summary Metrics."""

import pytest
from datetime import datetime, timezone
from fastapi import status


def setup_alert_infrastructure(client):
    """Helper to setup admin, operator, viewer, region, device, and tree."""
    # 1. Admin
    client.post("/api/v1/auth/register", json={
        "email": "admin_alt@agroforestry.gov.in",
        "username": "admin_alt",
        "full_name": "Alert Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    admin_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_alt",
        "password": "Password12345!",
    }).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Operator
    client.post("/api/v1/auth/register", json={
        "email": "operator_alt@agroforestry.gov.in",
        "username": "operator_alt",
        "full_name": "Alert Operator",
        "password": "Password12345!",
        "role": "OPERATOR",
    })
    op_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "operator_alt",
        "password": "Password12345!",
    }).json()["access_token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # 3. Viewer
    client.post("/api/v1/auth/register", json={
        "email": "viewer_alt@agroforestry.gov.in",
        "username": "viewer_alt",
        "full_name": "Alert Viewer",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    view_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "viewer_alt",
        "password": "Password12345!",
    }).json()["access_token"]
    view_headers = {"Authorization": f"Bearer {view_token}"}

    # 4. Region
    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-ALERT",
            "name": "Alert Test Reserve",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [75.50, 13.90],
                        [75.60, 13.90],
                        [75.60, 14.00],
                        [75.50, 14.00],
                        [75.50, 13.90],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )

    # 5. Field Device
    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-ALT-01", "name": "Alert Sensor Node", "assigned_region_id": region_resp.json().get("id")},
        headers=admin_headers,
    )
    api_key = dev_reg.json()["api_key"]
    dev_headers = {"X-Device-ID": "DEV-ALT-01", "X-Device-Key": api_key}

    # 6. Sandalwood Tree
    tree_reg = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": "REG-KA-ALERT",
            "species": "Santalum album",
            "latitude": 13.9500,
            "longitude": 75.5500,
        },
        headers=admin_headers,
    )
    tree_uid = tree_reg.json()["tree_uid"]

    return admin_headers, op_headers, view_headers, dev_headers, "REG-KA-ALERT", tree_uid


def test_automatic_alert_generation_on_critical_telemetry(client):
    """Test that anomalous or threshold-breaching field telemetry triggers an Alert automatically."""
    admin_headers, _, _, dev_headers, region_id, tree_uid = setup_alert_infrastructure(client)

    # Ingest critical reading: 49.0°C and 6% soil moisture around sandalwood tree
    ingest_resp = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": region_id,
            "tree_id": tree_uid,
            "latitude": 13.9500,
            "longitude": 75.5500,
            "temperature": 49.0,
            "humidity": 12.0,
            "soil_moisture": 6.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=dev_headers,
    )
    assert ingest_resp.status_code == status.HTTP_201_CREATED

    # Query alerts for this region
    alerts_resp = client.get(f"/api/v1/alerts?region_id={region_id}", headers=admin_headers)
    assert alerts_resp.status_code == status.HTTP_200_OK
    data = alerts_resp.json()
    assert data["total"] >= 1
    latest_alert = data["alerts"][0]
    assert latest_alert["severity"] == "CRITICAL"
    assert latest_alert["status"] == "ACTIVE"
    assert latest_alert["tree_id"] is not None


def test_alert_lifecycle_transitions(client):
    """Test full alert lifecycle: ACTIVE -> ACKNOWLEDGED -> RESOLVED."""
    _, op_headers, _, _, region_id, _ = setup_alert_infrastructure(client)

    # 1. Create manual alert
    create_resp = client.post(
        "/api/v1/alerts",
        json={
            "region_id": region_id,
            "alert_type": "SUSPECTED_UNAUTHORIZED_PROXIMITY",
            "severity": "HIGH",
            "message": "Unusual motion detected near perimeter fence",
        },
        headers=op_headers,
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    alert_uid = create_resp.json()["alert_uid"]

    # 2. Acknowledge alert
    ack_resp = client.post(
        f"/api/v1/alerts/{alert_uid}/acknowledge",
        json={"notes": "Field patrol dispatched to Sector 4"},
        headers=op_headers,
    )
    assert ack_resp.status_code == status.HTTP_200_OK
    ack_data = ack_resp.json()
    assert ack_data["status"] == "ACKNOWLEDGED"
    assert "Field patrol dispatched" in ack_data["resolution_notes"]

    # 3. Resolve alert
    resolve_resp = client.post(
        f"/api/v1/alerts/{alert_uid}/resolve",
        json={"resolution_notes": "Perimeter inspected. Wildlife disturbance cleared. Fence intact."},
        headers=op_headers,
    )
    assert resolve_resp.status_code == status.HTTP_200_OK
    res_data = resolve_resp.json()
    assert res_data["status"] == "RESOLVED"
    assert res_data["resolved_at"] is not None
    assert "Fence intact" in res_data["resolution_notes"]


def test_alert_dismissal_flow(client):
    """Test dismissing a false positive alert."""
    _, op_headers, _, _, region_id, _ = setup_alert_infrastructure(client)

    create_resp = client.post(
        "/api/v1/alerts",
        json={
            "region_id": region_id,
            "alert_type": "FALSE_ALARM_TEST",
            "severity": "LOW",
            "message": "Sensor calibration glitch test",
        },
        headers=op_headers,
    )
    alert_uid = create_resp.json()["alert_uid"]

    dismiss_resp = client.post(
        f"/api/v1/alerts/{alert_uid}/dismiss",
        json={"reason": "Routine sensor maintenance calibration"},
        headers=op_headers,
    )
    assert dismiss_resp.status_code == status.HTTP_200_OK
    assert dismiss_resp.json()["status"] == "DISMISSED"


def test_alert_summary_statistics(client):
    """Test aggregated dashboard summary statistics."""
    admin_headers, op_headers, _, _, region_id, _ = setup_alert_infrastructure(client)

    # Create alerts of varying severity
    client.post("/api/v1/alerts", json={
        "region_id": region_id,
        "alert_type": "CRITICAL_FIRE_RISK",
        "severity": "CRITICAL",
        "message": "High fire index",
    }, headers=op_headers)

    client.post("/api/v1/alerts", json={
        "region_id": region_id,
        "alert_type": "MEDIUM_STRESS",
        "severity": "MEDIUM",
        "message": "Moderate soil dryness",
    }, headers=op_headers)

    stats_resp = client.get(f"/api/v1/alerts/summary/stats?region_id={region_id}", headers=admin_headers)
    assert stats_resp.status_code == status.HTTP_200_OK
    stats = stats_resp.json()
    assert stats["total_alerts"] >= 2
    assert stats["critical_count"] >= 1
    assert stats["active_count"] >= 2


def test_alert_rbac_enforcement(client):
    """Test that VIEWER role cannot acknowledge or resolve alerts."""
    _, op_headers, view_headers, _, region_id, _ = setup_alert_infrastructure(client)

    # Create alert as operator
    create_resp = client.post(
        "/api/v1/alerts",
        json={
            "region_id": region_id,
            "alert_type": "RBAC_TEST",
            "severity": "LOW",
            "message": "Test alert for RBAC",
        },
        headers=op_headers,
    )
    alert_uid = create_resp.json()["alert_uid"]

    # Viewer tries to acknowledge -> 403 Forbidden
    ack_resp = client.post(
        f"/api/v1/alerts/{alert_uid}/acknowledge",
        json={"notes": "Viewer trying to ack"},
        headers=view_headers,
    )
    assert ack_resp.status_code == status.HTTP_403_FORBIDDEN
