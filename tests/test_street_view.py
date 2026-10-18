"""Comprehensive test suite for Street View 360° Panoramas, Ground AI Detection, and Internet Data Ingestion."""

import pytest
import base64
from app.ai.street_detector import street_detector
from app.services.street_view_service import StreetViewService
from tests.conftest import auth_headers


def test_street_detector_presets():
    """Verify StreetSandalwoodDetector returns valid 360° panoramas and routes."""
    presets = street_detector.get_all_panoramas()
    assert len(presets) >= 3
    assert any(p["id"] == "mysore_sandalwood_highway" for p in presets)
    assert any(p["id"] == "shivamogga_reserve_perimeter" for p in presets)

    routes = street_detector.get_all_routes()
    assert len(routes) >= 2
    assert any(r["route_id"] == "route_mysore_heritage" for r in routes)


def test_street_detector_detect_preset():
    """Verify ground-level AI detection on preset panorama returns botanical traits & bounding boxes."""
    res = street_detector.detect_from_preset("mysore_sandalwood_highway", confidence_threshold=0.60)
    assert res["preset_id"] == "mysore_sandalwood_highway"
    assert res["total_trees_detected"] >= 2
    assert res["sandalwood_count"] >= 1
    assert res["average_confidence"] > 0.80
    assert res["total_estimated_heartwood_kg"] > 0
    assert res["estimated_commercial_value_inr"] > 0
    assert len(res["detections"]) == res["total_trees_detected"]

    # Verify spherical & normalized coordinates
    for det in res["detections"]:
        assert -180.0 <= det["yaw_deg"] <= 180.0
        assert -90.0 <= det["pitch_deg"] <= 90.0
        assert 0.0 <= det["ymin"] <= det["ymax"] <= 1.0
        assert 0.0 <= det["xmin"] <= det["xmax"] <= 1.0
        assert det["dbh_cm"] > 0
        assert det["height_m"] > 0


def test_street_detector_detect_custom_image():
    """Verify AI inference on custom uploaded ground-level image bytes."""
    fake_img = b"RAW_GROUND_CAMERA_FRAME_DATA_987654321"
    res = street_detector.detect_from_image_bytes(
        image_bytes=fake_img,
        confidence_threshold=0.55,
        latitude=12.3020,
        longitude=76.6420,
    )
    assert res["total_trees_detected"] >= 1
    assert "detections" in res
    assert "model_architecture" in res
    assert res["inference_duration_ms"] > 0


def test_street_view_api_get_presets(client):
    """Test GET /api/v1/street-view/presets endpoint."""
    headers = auth_headers(client, "street_admin_1")

    resp = client.get("/api/v1/street-view/presets", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    assert data[0]["id"] == "mysore_sandalwood_highway"


def test_street_view_api_get_single_panorama(client):
    """Test GET /api/v1/street-view/panorama/{preset_id} endpoint."""
    headers = auth_headers(client, "street_admin_2")

    resp = client.get("/api/v1/street-view/panorama/mysore_sandalwood_highway", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "mysore_sandalwood_highway"
    assert data["road_name"] == "Mysore - Nanjangud Forestry Roadway"
    assert len(data["detections"]) >= 2


def test_street_view_api_get_routes(client):
    """Test GET /api/v1/street-view/routes endpoint."""
    headers = auth_headers(client, "street_admin_3")

    resp = client.get("/api/v1/street-view/routes", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert data[0]["route_id"] == "route_mysore_heritage"
    assert len(data[0]["waypoints"]) >= 2


def test_street_view_api_detect_endpoint(client):
    """Test POST /api/v1/street-view/detect with preset ID."""
    headers = auth_headers(client, "street_admin_4")

    resp = client.post(
        "/api/v1/street-view/detect",
        json={
            "preset_id": "mysore_sandalwood_highway",
            "confidence_threshold": 0.60,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sandalwood_count"] >= 1
    assert len(data["detections"]) >= 2


def test_street_view_api_detect_custom_image_endpoint(client):
    """Test POST /api/v1/street-view/detect with base64 image."""
    headers = auth_headers(client, "street_admin_5")

    sample_b64 = base64.b64encode(b"TEST_IMAGE_BYTES_123456").decode("utf-8")

    resp = client.post(
        "/api/v1/street-view/detect",
        json={
            "image_base64": f"data:image/jpeg;base64,{sample_b64}",
            "confidence_threshold": 0.50,
            "latitude": 13.9355,
            "longitude": 75.5652,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trees_detected"] >= 1


def test_street_view_api_catalog_endpoint(client):
    """Test GET /api/v1/street-view/catalog endpoint."""
    headers = auth_headers(client, "street_admin_6")

    resp = client.get("/api/v1/street-view/catalog", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 5
    assert any(p["is_sandalwood"] for p in data)


def test_street_view_api_sync_internet_endpoint(client):
    """Test POST /api/v1/street-view/sync-internet-data endpoint."""
    headers = auth_headers(client, "street_admin_7")

    resp = client.post(
        "/api/v1/street-view/sync-internet-data",
        json={"country": "IN", "state_province": "Karnataka", "limit": 20},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["total_harvested"] >= 5
    assert len(data["sources_scraped"]) >= 2


def test_street_view_api_register_detected_tree(client):
    """Simulated street-view detections must not become registry trees."""
    headers = auth_headers(client, "street_admin_8")

    resp = client.post(
        "/api/v1/street-view/register-detected-tree",
        json={
            "tree_uid": "KA-99",
            "detection_box_id": "STREET-SW-001",
            "species": "Santalum album",
            "latitude": 12.3020,
            "longitude": 76.6420,
            "estimated_age_years": 16,
            "girth_cm": 89.5,
            "height_m": 8.4,
            "notes": "Verified roadside discovery on Mysore Highway",
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert resp.json()["error"]["details"]["evidence_origin"] == "SIMULATED"

    listed = client.get("/api/v1/trees", headers=headers)
    assert listed.status_code == 200
    payloads = listed.json()
    rows = payloads.get("trees", payloads) if isinstance(payloads, dict) else payloads
    assert all(row.get("tree_uid") != "KA-99" for row in rows)


def test_street_view_api_global_destinations(client):
    """Test GET /api/v1/street-view/global-destinations."""
    client.post("/api/v1/auth/register", json={
        "email": "street_dest@agroforestry.gov.in",
        "username": "street_dest",
        "full_name": "Street Destinations",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "street_dest",
        "password": "Password12345!",
    }).json()["access_token"]
    resp = client.get("/api/v1/street-view/global-destinations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 8
    assert any(d["country"] == "India" for d in data)
    assert any(d["country"] == "Australia" for d in data)
    assert any(d["country"] == "Brazil" for d in data)


def test_street_view_api_teleport_global(client):
    """Test POST /api/v1/street-view/teleport-global with outdoor verification."""
    headers = auth_headers(client, "street_teleport")
    resp = client.post(
        "/api/v1/street-view/teleport-global",
        json={
            "latitude": 10.2825,
            "longitude": 77.1620,
            "location_label": "Marayoor Sandalwood Reserve",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["outdoor_verified"] is True
    assert data["no_indoor_commercial_guarantee"] is True
    assert "urls" in data
    assert "google_street_view_embed" in data["urls"]
    assert "equirectangular_4k_photosphere" in data["urls"]

