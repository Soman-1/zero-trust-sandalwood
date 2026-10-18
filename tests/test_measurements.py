"""Tests for Environmental Monitoring queries, history, and statistical aggregations."""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi import status


def setup_monitoring_data(client):
    """Helper to seed region, device, tree, and time-series measurements."""
    # 1. Admin
    client.post("/api/v1/auth/register", json={
        "email": "admin_query@agroforestry.gov.in",
        "username": "admin_query",
        "full_name": "Query Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_query",
        "password": "Password12345!",
    }).json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 2. Region
    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-COORG",
            "name": "Coorg Reserve",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [75.80, 12.33],
                        [75.82, 12.33],
                        [75.82, 12.35],
                        [75.80, 12.35],
                        [75.80, 12.33],
                    ]
                ],
            },
        },
        headers=user_headers,
    )

    # 3. Device
    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-COORG-01", "name": "Coorg Sensor Node 1", "assigned_region_id": region_resp.json().get("id")},
        headers=user_headers,
    )
    api_key = dev_reg.json()["api_key"]
    dev_headers = {"X-Device-ID": "DEV-COORG-01", "X-Device-Key": api_key}

    # 4. Tree
    tree_reg = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": "REG-KA-COORG",
            "species": "Santalum album",
            "latitude": 12.3375,
            "longitude": 75.8069,
        },
        headers=user_headers,
    )
    tree_uid = tree_reg.json()["tree_uid"]

    # 5. Ingest time-series data:
    base_time = datetime.now(timezone.utc) - timedelta(hours=6)

    # 08:00 - Regional observation
    client.post("/api/v1/measurements/ingest", json={
        "region_id": "REG-KA-COORG",
        "tree_id": None,
        "latitude": 12.3350,
        "longitude": 75.8050,
        "temperature": 24.0,
        "humidity": 80.0,
        "soil_moisture": 60.0,
        "recorded_at": (base_time).isoformat(),
    }, headers=dev_headers)

    # 10:00 - Tree observation
    client.post("/api/v1/measurements/ingest", json={
        "region_id": "REG-KA-COORG",
        "tree_id": tree_uid,
        "latitude": 12.3375,
        "longitude": 75.8069,
        "temperature": 26.0,
        "humidity": 75.0,
        "soil_moisture": 55.0,
        "recorded_at": (base_time + timedelta(hours=2)).isoformat(),
    }, headers=dev_headers)

    # 12:00 - Tree observation (latest for tree)
    t_latest = client.post("/api/v1/measurements/ingest", json={
        "region_id": "REG-KA-COORG",
        "tree_id": tree_uid,
        "latitude": 12.3375,
        "longitude": 75.8069,
        "temperature": 30.0,
        "humidity": 65.0,
        "soil_moisture": 50.0,
        "recorded_at": (base_time + timedelta(hours=4)).isoformat(),
    }, headers=dev_headers)

    # 14:00 - Regional observation (latest for region)
    r_latest = client.post("/api/v1/measurements/ingest", json={
        "region_id": "REG-KA-COORG",
        "tree_id": None,
        "latitude": 12.3360,
        "longitude": 75.8055,
        "temperature": 32.0,
        "humidity": 60.0,
        "soil_moisture": 45.0,
        "recorded_at": (base_time + timedelta(hours=6)).isoformat(),
    }, headers=dev_headers)

    return user_headers, "REG-KA-COORG", tree_uid, r_latest.json()["measurement_uid"]


def test_latest_and_history_region_measurements(client):
    """Test retrieving latest and historical observations across a whole region."""
    user_headers, region_id, _, _ = setup_monitoring_data(client)

    # Latest region reading
    latest_resp = client.get(f"/api/v1/measurements/region/{region_id}/latest", headers=user_headers)
    assert latest_resp.status_code == status.HTTP_200_OK
    assert latest_resp.json()["temperature"] == 32.0

    # Region history (all 4 readings belong to region)
    hist_resp = client.get(f"/api/v1/measurements/region/{region_id}/history", headers=user_headers)
    assert hist_resp.status_code == status.HTTP_200_OK
    assert len(hist_resp.json()) == 4


def test_latest_and_history_tree_measurements(client):
    """Test retrieving latest and historical microclimate observations for a specific sandalwood tree."""
    user_headers, _, tree_uid, _ = setup_monitoring_data(client)

    # Latest tree reading
    latest_resp = client.get(f"/api/v1/measurements/tree/{tree_uid}/latest", headers=user_headers)
    assert latest_resp.status_code == status.HTTP_200_OK
    assert latest_resp.json()["temperature"] == 30.0

    # Tree history (only 2 readings are tied to tree)
    hist_resp = client.get(f"/api/v1/measurements/tree/{tree_uid}/history", headers=user_headers)
    assert hist_resp.status_code == status.HTTP_200_OK
    assert len(hist_resp.json()) == 2


def test_environmental_analytics_statistics(client):
    """Test statistical aggregation (min, max, avg, count) calculation."""
    user_headers, region_id, tree_uid, _ = setup_monitoring_data(client)

    # Region-wide statistics (4 observations: temps 24, 26, 30, 32 -> avg = 28.0)
    reg_stats = client.get(
        f"/api/v1/measurements/analytics/stats?region_id={region_id}",
        headers=user_headers,
    )
    assert reg_stats.status_code == status.HTTP_200_OK
    data = reg_stats.json()
    assert data["reading_count"] == 4
    assert data["min_temperature"] == 24.0
    assert data["max_temperature"] == 32.0
    assert data["avg_temperature"] == 28.0

    # Tree-specific statistics (2 observations: temps 26, 30 -> avg = 28.0)
    tree_stats = client.get(
        f"/api/v1/measurements/analytics/stats?tree_id={tree_uid}",
        headers=user_headers,
    )
    assert tree_stats.status_code == status.HTTP_200_OK
    tdata = tree_stats.json()
    assert tdata["reading_count"] == 2
    assert tdata["min_temperature"] == 26.0
    assert tdata["max_temperature"] == 30.0


def test_get_measurement_by_uid(client):
    """Test fetching single observation by UID."""
    user_headers, _, _, measurement_uid = setup_monitoring_data(client)

    resp = client.get(f"/api/v1/measurements/{measurement_uid}", headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["measurement_uid"] == measurement_uid
