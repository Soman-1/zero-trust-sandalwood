"""Comprehensive tests for Real Environmental Data Ingestion Pipeline."""

import pytest
from datetime import datetime, timezone
from fastapi import status


def setup_test_infrastructure(client):
    """Helper to setup admin, region, device, and tree for ingestion tests."""
    # 1. Admin
    client.post("/api/v1/auth/register", json={
        "email": "admin_ingest@agroforestry.gov.in",
        "username": "admin_ingest",
        "full_name": "Ingest Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_ingest",
        "password": "Password12345!",
    }).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}

    # 2. Region
    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-SHIVAMOGGA",
            "name": "Shivamogga Reserve",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [75.56, 13.92],
                        [75.58, 13.92],
                        [75.58, 13.94],
                        [75.56, 13.94],
                        [75.56, 13.92],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )

    # 3. Field Device
    dev_reg = client.post(
        "/api/v1/devices",
        json={
            "device_id": "DEV-KA-NODE-01",
            "name": "Shivamogga Telemetry Node 1",
            "device_type": "STATIONARY_NODE",
            "assigned_region_id": region_resp.json().get("id"),
        },
        headers=admin_headers,
    )
    api_key = dev_reg.json()["api_key"]

    # 4. Sandalwood Tree
    tree_reg = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": "REG-KA-SHIVAMOGGA",
            "species": "Santalum album",
            "latitude": 13.9310,
            "longitude": 75.5720,
        },
        headers=admin_headers,
    )
    tree_uid = tree_reg.json()["tree_uid"]

    dev_headers = {
        "X-Device-ID": "DEV-KA-NODE-01",
        "X-Device-Key": api_key,
    }

    return admin_headers, dev_headers, "REG-KA-SHIVAMOGGA", tree_uid


def test_ingest_region_wide_measurement(client):
    """Test successful ingestion of a region-wide environmental reading (tree_id is None)."""
    _, dev_headers, region_id, _ = setup_test_infrastructure(client)

    payload = {
        "region_id": region_id,
        "tree_id": None,  # Region-level observation
        "latitude": 13.9300,
        "longitude": 75.5700,
        "temperature": 27.8,
        "humidity": 65.2,
        "soil_moisture": 44.0,
        "additional_metrics": {"rainfall_mm": 5.2, "solar_lux": 82000},
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    response = client.post("/api/v1/measurements/ingest", json=payload, headers=dev_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["tree_id"] is None
    assert "measurement_uid" in data


def test_ingest_tree_specific_measurement(client):
    """Test successful ingestion of a tree-specific reading tied to a registered sandalwood tree."""
    _, dev_headers, region_id, tree_uid = setup_test_infrastructure(client)

    payload = {
        "region_id": region_id,
        "tree_id": tree_uid,  # Linked to specific sandalwood tree
        "latitude": 13.9310,
        "longitude": 75.5720,
        "temperature": 29.1,
        "humidity": 62.0,
        "soil_moisture": 41.5,
        "additional_metrics": {"soil_ph": 6.7},
    }

    response = client.post("/api/v1/measurements/ingest", json=payload, headers=dev_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["tree_id"] is not None


def test_zero_trust_device_rejection_on_ingestion(client):
    """Test that unknown or unauthorized devices cannot ingest data."""
    _, dev_headers, region_id, _ = setup_test_infrastructure(client)

    payload = {
        "region_id": region_id,
        "latitude": 13.9300,
        "longitude": 75.5700,
        "temperature": 25.0,
        "humidity": 60.0,
        "soil_moisture": 50.0,
    }

    # 1. Missing headers -> 401 Unauthorized
    r1 = client.post("/api/v1/measurements/ingest", json=payload)
    assert r1.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Invalid API key -> 401 Unauthorized
    r2 = client.post(
        "/api/v1/measurements/ingest",
        json=payload,
        headers={"X-Device-ID": "DEV-KA-NODE-01", "X-Device-Key": "sw_dev_bad_key"},
    )
    assert r2.status_code == status.HTTP_401_UNAUTHORIZED


def test_rejection_of_impossible_sensor_values(client):
    """Test physical range limits enforcement on telemetry."""
    _, dev_headers, region_id, _ = setup_test_infrastructure(client)

    # Impossible temperature = 120°C
    r1 = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": region_id,
            "latitude": 13.9300,
            "longitude": 75.5700,
            "temperature": 120.0,
            "humidity": 60.0,
            "soil_moisture": 50.0,
        },
        headers=dev_headers,
    )
    assert r1.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # Impossible humidity = -15%
    r2 = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": region_id,
            "latitude": 13.9300,
            "longitude": 75.5700,
            "temperature": 25.0,
            "humidity": -15.0,
            "soil_moisture": 50.0,
        },
        headers=dev_headers,
    )
    assert r2.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


def test_zero_trust_out_of_boundary_telemetry_rejection(client):
    """Telemetry ingest stores GPS without forest-reserve polygon checks."""
    _, dev_headers, region_id, _ = setup_test_infrastructure(client)

    # Point outside Shivamogga polygon: (12.9716, 77.5946) (Bangalore)
    response = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": region_id,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 26.0,
            "humidity": 70.0,
            "soil_moisture": 55.0,
        },
        headers=dev_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["success"] is True
    assert "measurement_uid" in response.json()


def test_batch_telemetry_ingestion(client):
    """Test batch telemetry synchronization from field devices."""
    _, dev_headers, region_id, tree_uid = setup_test_infrastructure(client)

    batch_payload = {
        "measurements": [
            {
                "region_id": region_id,
                "tree_id": None,
                "latitude": 13.9300,
                "longitude": 75.5700,
                "temperature": 24.5,
                "humidity": 78.0,
                "soil_moisture": 52.0,
            },
            {
                "region_id": region_id,
                "tree_id": tree_uid,
                "latitude": 13.9310,
                "longitude": 75.5720,
                "temperature": 26.0,
                "humidity": 72.0,
                "soil_moisture": 49.0,
            },
        ]
    }

    response = client.post("/api/v1/measurements/ingest/batch", json=batch_payload, headers=dev_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["total_ingested"] == 2
    assert len(data["measurement_uids"]) == 2
