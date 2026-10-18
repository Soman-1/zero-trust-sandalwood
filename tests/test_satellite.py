"""Test suite for Satellite AI Classifier and GBIF Biodiversity Ingestion."""

import pytest
from app.ai.satellite_classifier import satellite_classifier
from tests.conftest import auth_headers


def test_satellite_classifier_identify_sandalwood():
    """Verify satellite multi-spectral identification returns valid species classification."""
    res = satellite_classifier.identify(latitude=13.9355, longitude=75.5652)
    assert "predicted_species" in res
    assert "confidence_score" in res
    assert 0.0 <= res["confidence_score"] <= 1.0
    assert "spectral_indices" in res
    assert "ndvi" in res["spectral_indices"]
    assert "sentinel_bands" in res
    assert len(res["all_probabilities"]) == 7
    assert res["evidence_origin"] == "SIMULATED"
    assert res["satellite_source"].startswith("SIMULATED")


def test_satellite_classifier_scan_grid():
    """Verify satellite bounding box scanning classifies hundreds of trees."""
    grid = satellite_classifier.scan_grid(
        min_lat=13.90,
        min_lon=75.50,
        max_lat=13.95,
        max_lon=75.60,
        sample_count=100,
        confidence_threshold=0.6,
    )
    assert grid["total_trees_scanned"] == 100
    assert grid["sandalwood_detected_count"] >= 0
    assert len(grid["detected_sandalwood_trees"]) == grid["sandalwood_detected_count"]
    assert grid["evidence_origin"] == "SIMULATED"


def test_satellite_api_identify_endpoint(client):
    """Test POST /api/v1/satellite/identify endpoint."""
    # 1. Login to get token
    headers = auth_headers(client, "sat_admin_1")

    resp = client.post(
        "/api/v1/satellite/identify",
        json={
            "latitude": 13.9355,
            "longitude": 75.5652,
            "bands": {
                "blue": 0.045,
                "green": 0.082,
                "red": 0.058,
                "red_edge": 0.195,
                "nir": 0.485,
                "swir1": 0.210,
                "swir2": 0.115,
            },
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["predicted_species"] == "Santalum album"
    assert data["is_sandalwood"] is True
    assert data["confidence_score"] > 0.60


def test_satellite_api_scan_endpoint(client):
    """Test POST /api/v1/satellite/scan-area endpoint."""
    headers = auth_headers(client, "sat_admin_2")

    resp = client.post(
        "/api/v1/satellite/scan-area",
        json={
            "bbox": {
                "min_lat": 13.90,
                "min_lon": 75.50,
                "max_lat": 13.95,
                "max_lon": 75.60,
            },
            "sample_tree_count": 80,
            "confidence_threshold": 0.50,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trees_scanned"] == 80
    assert "scan_duration_ms" in data


def test_satellite_api_spectral_profiles(client):
    """Test GET /api/v1/satellite/spectral-profiles."""
    headers = auth_headers(client, "sat_admin_3")

    resp = client.get("/api/v1/satellite/spectral-profiles", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "Santalum album" in data["profiles"]
    assert "Tectona grandis" in data["profiles"]


def test_aerial_detector_presets():
    """Verify AerialDroneTreeDetector returns calibrated presets."""
    from app.ai.aerial_detector import aerial_detector
    presets = aerial_detector.get_presets()
    assert len(presets) >= 3
    assert any(p["id"] == "shivamogga_plantation" for p in presets)


def test_aerial_detector_detection_from_preset():
    """Verify aerial drone detection on preset flight data."""
    from app.ai.aerial_detector import aerial_detector
    res = aerial_detector.detect_from_preset("shivamogga_plantation", confidence_threshold=0.60)
    assert res["total_canopies_detected"] > 0
    assert res["sandalwood_count"] > 0
    assert res["average_confidence"] > 0.80
    assert len(res["canopies"]) == res["total_canopies_detected"]
    for c in res["canopies"]:
        assert 0.0 <= c["ymin"] <= c["ymax"] <= 1.0
        assert 0.0 <= c["xmin"] <= c["xmax"] <= 1.0


def test_aerial_detector_detection_from_image_bytes():
    """Verify aerial drone detection on custom image bytes."""
    from app.ai.aerial_detector import aerial_detector
    fake_img = b"PNG_HEADER_TEST_IMAGE_DATA_123456789"
    res = aerial_detector.detect_from_image_bytes(fake_img, confidence_threshold=0.50)
    assert res["total_canopies_detected"] >= 1
    assert "canopies" in res
    assert "pipeline_architecture" in res


def test_aerial_api_get_presets(client):
    """Test GET /api/v1/satellite/aerial-presets."""
    headers = auth_headers(client, "sat_admin_4")

    resp = client.get("/api/v1/satellite/aerial-presets", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "presets" in data
    assert len(data["presets"]) >= 3


def test_aerial_api_detect_endpoint_preset(client):
    """Test POST /api/v1/satellite/detect-aerial with preset."""
    headers = auth_headers(client, "sat_admin_5")

    resp = client.post(
        "/api/v1/satellite/detect-aerial",
        json={
            "preset_id": "shivamogga_plantation",
            "confidence_threshold": 0.70,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["preset_id"] == "shivamogga_plantation"
    assert data["sandalwood_count"] >= 1
    assert len(data["canopies"]) == data["total_canopies_detected"]


def test_satellite_live_weather_endpoint(client):
    """Test GET /api/v1/satellite/live-weather endpoint."""
    client.post("/api/v1/auth/register", json={
        "email": "sat_weather@agroforestry.gov.in",
        "username": "sat_weather",
        "full_name": "Satellite Weather",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "sat_weather",
        "password": "Password12345!",
    }).json()["access_token"]
    resp = client.get(
        "/api/v1/satellite/live-weather?latitude=13.9355&longitude=75.5652",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "temperature_celsius" in data
    assert "relative_humidity_percent" in data
    assert "soil_moisture_surface_percent" in data
    assert "elevation_meters" in data
    assert "sandalwood_suitability_score" in data
    assert "integrity_hash" in data
    assert len(data["integrity_hash"]) == 64


def test_satellite_landmarks_endpoint(client):
    """Test GET /api/v1/satellite/landmarks endpoint."""
    client.post("/api/v1/auth/register", json={
        "email": "sat_landmarks@agroforestry.gov.in",
        "username": "sat_landmarks",
        "full_name": "Satellite Landmarks",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "sat_landmarks",
        "password": "Password12345!",
    }).json()["access_token"]
    resp = client.get("/api/v1/satellite/landmarks", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 5
    assert any(lm["id"] == "shivamogga_reserve" for lm in data)
    assert any(lm["id"] == "mysore_heritage" for lm in data)


def test_satellite_world_occurrences_endpoint(client):
    """Test GET /api/v1/satellite/world-occurrences endpoint."""
    client.post("/api/v1/auth/register", json={
        "email": "sat_world@agroforestry.gov.in",
        "username": "sat_world",
        "full_name": "Satellite World",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "sat_world",
        "password": "Password12345!",
    }).json()["access_token"]
    resp = client.get("/api/v1/satellite/world-occurrences?limit=10", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["is_sandalwood"] is True
    assert "gbif_id" in data[0]

