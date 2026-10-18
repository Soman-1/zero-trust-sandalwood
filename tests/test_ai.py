"""Comprehensive tests for AI Environmental Anomaly Detection and Isolation Forest Model."""

import pytest
from datetime import datetime, timezone
from fastapi import status

from app.ai.preprocessing import compute_vapor_pressure_deficit, extract_features
from app.ai.model import detector


def setup_user_and_infrastructure(client):
    """Helper to setup admin, region, and device."""
    # 1. Admin
    client.post("/api/v1/auth/register", json={
        "email": "admin_ai@agroforestry.gov.in",
        "username": "admin_ai",
        "full_name": "AI Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_ai",
        "password": "Password12345!",
    }).json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 2. Region
    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-AI",
            "name": "AI Test Reserve",
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
        headers=user_headers,
    )

    # 3. Device
    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-AI-01", "name": "AI Telemetry Node", "assigned_region_id": region_resp.json().get("id")},
        headers=user_headers,
    )
    api_key = dev_reg.json()["api_key"]
    dev_headers = {"X-Device-ID": "DEV-AI-01", "X-Device-Key": api_key}

    return user_headers, dev_headers, "REG-KA-AI"


def test_feature_engineering_vpd():
    """Test feature extraction and vapor pressure deficit calculation."""
    vpd = compute_vapor_pressure_deficit(temperature=30.0, humidity=60.0)
    assert vpd > 0.0
    assert isinstance(vpd, float)

    features = extract_features(temperature=28.0, humidity=70.0, soil_moisture=50.0)
    assert len(features) == 6
    assert features[0] == 28.0
    assert features[1] == 70.0
    assert features[2] == 50.0


def test_ai_normal_environmental_evaluation(client):
    """Test that normal tropical agroforestry readings are classified as non-anomalous."""
    user_headers, _, _ = setup_user_and_infrastructure(client)

    payload = {
        "temperature": 27.0,
        "humidity": 68.0,
        "soil_moisture": 52.0,
    }
    resp = client.post("/api/v1/anomaly/evaluate", json=payload, headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["is_anomaly"] is False
    assert data["anomaly_score"] < 0.65
    assert "NORMAL CONDITIONS" in data["interpretation"]


def test_ai_extreme_heat_and_drought_anomaly_detection(client):
    """Test that extreme high temperatures and severe drought trigger anomaly detection."""
    user_headers, _, _ = setup_user_and_infrastructure(client)

    # Extreme heat spike (47°C, 16% humidity, 8% soil moisture)
    payload = {
        "temperature": 47.0,
        "humidity": 16.0,
        "soil_moisture": 8.0,
    }
    resp = client.post("/api/v1/anomaly/evaluate", json=payload, headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["is_anomaly"] is True
    assert data["anomaly_score"] > 0.60
    assert "ANOMALY DETECTED" in data["interpretation"]
    assert data["details"]["primary_factor"] in [
        "ABNORMAL_HIGH_TEMPERATURE",
        "CRITICAL_SOIL_DEHYDRATION",
        "UNUSUAL_ENVIRONMENTAL_COMBINATION",
    ]


def test_ai_scoring_during_telemetry_ingestion(client):
    """
    Test that incoming field telemetry is automatically evaluated by AI upon ingestion
    and stored with is_anomaly, anomaly_score, and anomaly_details.
    """
    user_headers, dev_headers, region_id = setup_user_and_infrastructure(client)

    # Ingest anomalous reading directly through IoT pipeline
    ingest_resp = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": region_id,
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
    uid = ingest_resp.json()["measurement_uid"]

    # Query the stored observation
    fetch_resp = client.get(f"/api/v1/measurements/{uid}", headers=user_headers)
    assert fetch_resp.status_code == status.HTTP_200_OK
    meas_data = fetch_resp.json()
    assert meas_data["is_anomaly"] is True
    assert meas_data["anomaly_score"] is not None
    assert meas_data["anomaly_score"] > 0.5


def test_ai_model_status_endpoint(client):
    """Test checking model status and parameters."""
    user_headers, _, _ = setup_user_and_infrastructure(client)

    resp = client.get("/api/v1/anomaly/model-status", headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["model_type"] == "IsolationForest"
    assert data["is_fitted"] is True
    assert data["trained_samples"] > 0
