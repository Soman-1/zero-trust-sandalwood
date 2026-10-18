"""Comprehensive tests for Dashboard Integration, GIS Map Layers, and Time-Series APIs."""

import pytest
from datetime import datetime, timezone
from fastapi import status


def setup_dashboard_environment(client):
    """Helper to seed complete dataset for dashboard queries."""
    # 1. Admin
    client.post("/api/v1/auth/register", json={
        "email": "admin_dash@agroforestry.gov.in",
        "username": "admin_dash",
        "full_name": "Dash Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_dash",
        "password": "Password12345!",
    }).json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 2. Region
    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-DASH",
            "name": "Dashboard Reserve",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [75.20, 13.50],
                        [75.40, 13.50],
                        [75.40, 13.70],
                        [75.20, 13.70],
                        [75.20, 13.50],
                    ]
                ],
            },
        },
        headers=user_headers,
    )

    # 3. Device
    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-DASH-01", "name": "Dashboard Node", "assigned_region_id": region_resp.json().get("id")},
        headers=user_headers,
    )
    api_key = dev_reg.json()["api_key"]
    dev_headers = {"X-Device-ID": "DEV-DASH-01", "X-Device-Key": api_key}

    # 4. Sandalwood Trees (1 Healthy, 1 At Risk)
    t1 = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": "REG-KA-DASH",
            "species": "Santalum album",
            "latitude": 13.55,
            "longitude": 75.25,
            "status": "HEALTHY",
        },
        headers=user_headers,
    ).json()["tree_uid"]

    t2 = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-02",
            "region_id": "REG-KA-DASH",
            "species": "Santalum album",
            "latitude": 13.58,
            "longitude": 75.28,
            "status": "AT_RISK",
        },
        headers=user_headers,
    ).json()["tree_uid"]

    # 5. Ingest Telemetry
    client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": "REG-KA-DASH",
            "tree_id": t1,
            "latitude": 13.55,
            "longitude": 75.25,
            "temperature": 27.5,
            "humidity": 68.0,
            "soil_moisture": 48.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=dev_headers,
    )

    return user_headers, "REG-KA-DASH", t1


def test_dashboard_overview_endpoint(client):
    """Test executive overview KPI calculations."""
    user_headers, _, _ = setup_dashboard_environment(client)

    resp = client.get("/api/v1/dashboard/overview", headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total_regions"] >= 1
    assert data["tree_assets"]["total"] >= 2
    assert data["tree_assets"]["healthy"] >= 1
    assert data["tree_assets"]["at_risk"] >= 1
    assert data["environmental_24h"]["total_readings_24h"] >= 1
    assert data["environmental_24h"]["avg_temperature"] is not None
    assert "devices" in data
    assert "alerts" in data
    assert "security" in data


def test_gis_map_layer_endpoint(client):
    """Test GeoJSON FeatureCollection generation for GIS map viewers."""
    user_headers, region_id, _ = setup_dashboard_environment(client)

    resp = client.get(f"/api/v1/dashboard/map-layer?region_id={region_id}", headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    features = data["features"]
    assert len(features) >= 2  # Region polygon + Sandalwood tree points

    # Verify region boundary feature
    reg_feature = next(f for f in features if f["properties"].get("layer_type") == "REGION_BOUNDARY")
    assert reg_feature["geometry"]["type"] == "Polygon"
    assert reg_feature["properties"]["region_id"] == region_id

    # Verify tree feature
    tree_feature = next(f for f in features if f["properties"].get("layer_type") == "SANDALWOOD_TREE")
    assert tree_feature["geometry"]["type"] == "Point"
    assert tree_feature["properties"]["species"] == "Santalum album"


def test_timeseries_chart_data(client):
    """Test time-series endpoint for frontend chart rendering."""
    user_headers, region_id, _ = setup_dashboard_environment(client)

    resp = client.get(f"/api/v1/dashboard/timeseries?region_id={region_id}&hours=24", headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["region_id"] == region_id
    assert data["total_points"] >= 1
    assert len(data["points"]) >= 1
    point = data["points"][0]
    assert point["temperature"] == 27.5
    assert point["humidity"] == 68.0


def test_single_region_dashboard(client):
    """Test single region deep-dive dashboard payload."""
    user_headers, region_id, _ = setup_dashboard_environment(client)

    resp = client.get(f"/api/v1/dashboard/region/{region_id}", headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["region_id"] == region_id
    assert data["tree_assets"]["total"] >= 2
    assert data["latest_environmental"] is not None
    assert data["latest_environmental"]["temperature_c"] == 27.5
