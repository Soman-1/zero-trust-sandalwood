"""Tests for Global Internet Sandalwood biodiversity data ingestion and APIs."""

import pytest
from fastapi import status


def get_auth_token(client, username="admin_global_tree", role="ADMIN"):
    """Helper to get user token."""
    client.post("/api/v1/auth/register", json={
        "email": f"{username}@agroforestry.gov.in",
        "username": username,
        "full_name": f"{username} Admin",
        "password": "Password12345!",
        "role": role,
    })
    resp = client.post("/api/v1/auth/login", json={
        "username_or_email": username,
        "password": "Password12345!",
    })
    return resp.json()["access_token"]


def test_get_global_tree_stats(client):
    """Test retrieving KPI statistics for internet sandalwood occurrences."""
    headers = {"Authorization": f"Bearer {get_auth_token(client, 'stats_viewer', 'VIEWER')}"}
    resp = client.get("/api/v1/global-trees/stats", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "total_trees" in data
    assert data["total_trees"] >= 300
    assert "gbif_count" in data
    assert "inaturalist_count" in data
    assert "with_photos_count" in data
    assert "states_distribution" in data
    assert data["gbif_count"] > 0
    assert data["inaturalist_count"] > 0


def test_list_global_trees(client):
    """Test listing internet occurrences with pagination and filtering."""
    headers = {"Authorization": f"Bearer {get_auth_token(client, 'list_viewer', 'VIEWER')}"}
    resp = client.get("/api/v1/global-trees?limit=10", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()
    assert len(items) == 10

    first = items[0]
    assert "id" in first
    assert "source" in first
    assert "latitude" in first
    assert "longitude" in first
    assert "scientific_name" in first
    assert "vernacular_name" in first


def test_filter_global_trees_by_source(client):
    """Test filtering by GBIF vs iNaturalist source."""
    headers = {"Authorization": f"Bearer {get_auth_token(client, 'source_viewer', 'VIEWER')}"}
    resp_gbif = client.get("/api/v1/global-trees?source=GBIF&limit=20", headers=headers)
    assert resp_gbif.status_code == status.HTTP_200_OK
    for item in resp_gbif.json():
        assert "gbif" in item["source"].lower()

    resp_inat = client.get("/api/v1/global-trees?source=iNaturalist&limit=20", headers=headers)
    assert resp_inat.status_code == status.HTTP_200_OK
    for item in resp_inat.json():
        assert "inaturalist" in item["source"].lower()


def test_filter_global_trees_with_photos(client):
    """Test filtering by photo availability."""
    headers = {"Authorization": f"Bearer {get_auth_token(client, 'photo_viewer', 'VIEWER')}"}
    resp = client.get("/api/v1/global-trees?has_photo=true&limit=15", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()
    assert len(items) > 0
    for item in items:
        assert item["image_url"] is not None
        assert len(item["image_url"]) > 0


def test_search_global_trees(client):
    """Test text search on locality and observer."""
    headers = {"Authorization": f"Bearer {get_auth_token(client, 'search_viewer', 'VIEWER')}"}
    resp = client.get("/api/v1/global-trees?query=Mysore&limit=10", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()
    assert len(items) > 0
    for item in items:
        loc = (item.get("locality") or "").lower()
        state = (item.get("state_province") or "").lower()
        assert "mysor" in loc or "mysor" in state


def test_preview_and_register_selected_tree(client, monkeypatch):
    """Selecting an internet specimen registers its GPS and stores environmental data."""
    from app.services.weather_service import RealWorldWeatherService
    from app.core.config import settings

    # Registration persists live weather only when env refresh capture is enabled.
    monkeypatch.setattr(settings, "ENV_REFRESH_ENABLED", True)

    sample_weather = {
        "latitude": 13.9,
        "longitude": 75.5,
        "elevation_meters": 640.0,
        "temperature_celsius": 27.4,
        "relative_humidity_percent": 68.0,
        "soil_temperature_celsius": 25.1,
        "soil_moisture_surface_percent": 22.0,
        "soil_moisture_root_percent": 31.5,
        "surface_pressure_hpa": 948.0,
        "wind_speed_kmh": 6.2,
        "wind_direction_deg": 210,
        "cloud_cover_percent": 18,
        "vapor_pressure_deficit_kpa": 1.1,
        "sandalwood_suitability_score": 82.0,
        "growth_zone_classification": "OPTIMAL_GROWTH",
        "canopy_stress_status": "NOMINAL",
        "data_source": "TEST",
    }

    def fake_weather(latitude, longitude):
        payload = dict(sample_weather)
        payload["latitude"] = latitude
        payload["longitude"] = longitude
        return payload

    monkeypatch.setattr(RealWorldWeatherService, "get_live_microclimate", classmethod(lambda cls, latitude, longitude: fake_weather(latitude, longitude)))

    headers = {"Authorization": f"Bearer {get_auth_token(client, 'register_operator', 'OPERATOR')}"}
    listing = client.get("/api/v1/global-trees?limit=1", headers=headers)
    assert listing.status_code == status.HTTP_200_OK
    occurrence = listing.json()[0]

    env = client.get(
        "/api/v1/global-trees/environment",
        params={"occurrence_id": occurrence["id"]},
        headers=headers,
    )
    assert env.status_code == status.HTTP_200_OK
    env_body = env.json()
    assert env_body["temperature_celsius"] == 27.4
    assert env_body["soil_moisture_root_percent"] == 31.5
    assert env_body["stored"] is False
    assert env_body["heartwood"] is not None
    assert env_body["heartwood"]["estimated_heartwood_kg"] > 0
    # Continuous site-index: optimal climate + Karnataka belt coords → mid-upper stem
    assert 22.0 <= env_body["heartwood"]["assumed_dbh_cm"] <= 34.0
    assert env_body["heartwood"]["method"] == "allometric_assumed_stem"
    assert "not a measured heartwood core" in env_body["heartwood"]["assumption_note"].lower()

    registered = client.post(
        "/api/v1/global-trees/register",
        headers=headers,
        json={"occurrence_id": occurrence["id"], "tree_uid": "KA-91"},
    )
    assert registered.status_code == status.HTTP_201_CREATED
    body = registered.json()
    assert body["success"] is True
    assert body["tree_uid"] == "KA-91"
    assert body["latitude"] == occurrence["latitude"]
    assert body["longitude"] == occurrence["longitude"]
    assert body["environment_stored"] is True
    assert body["environment"]["temperature_celsius"] == 27.4
    assert body["environment"]["stored"] is True
    assert body["environment"]["heartwood"] is not None
    assert body["environment"]["heartwood"]["estimated_heartwood_kg"] > 0

    duplicate = client.post(
        "/api/v1/global-trees/register",
        headers=headers,
        json={"occurrence_id": occurrence["id"], "tree_uid": "KA-92"},
    )
    assert duplicate.status_code == status.HTTP_409_CONFLICT


def test_estimate_heartwood_for_site_suitability_tiers():
    """Heartwood stem assumptions scale continuously with climate + location."""
    from app.services.global_tree_service import GlobalTreeService

    # Same GPS — higher suitability must not shrink the stem
    optimal = GlobalTreeService.estimate_heartwood_for_site(
        82.0, latitude=13.50, longitude=75.80, elevation_m=850.0
    )
    suitable = GlobalTreeService.estimate_heartwood_for_site(
        60.0, latitude=13.50, longitude=75.80, elevation_m=850.0
    )
    marginal = GlobalTreeService.estimate_heartwood_for_site(
        40.0, latitude=13.50, longitude=75.80, elevation_m=850.0
    )
    unknown = GlobalTreeService.estimate_heartwood_for_site(
        None, latitude=13.50, longitude=75.80, elevation_m=850.0
    )

    assert optimal.assumed_dbh_cm > suitable.assumed_dbh_cm
    assert suitable.assumed_dbh_cm > marginal.assumed_dbh_cm
    assert unknown.assumed_dbh_cm > 0
    assert optimal.estimated_heartwood_kg >= suitable.estimated_heartwood_kg
    assert suitable.estimated_heartwood_kg >= marginal.estimated_heartwood_kg
    assert all(h.heartwood_ratio >= 0 for h in (optimal, suitable, marginal, unknown))


def test_estimate_heartwood_differs_across_occurrence_locations():
    """Distinct GPS/elevation must not collapse to one shared age/heartwood value."""
    from app.services.global_tree_service import GlobalTreeService

    # Identical climate score (as when weather cache is shared) but different sites
    a = GlobalTreeService.estimate_heartwood_for_site(
        64.7, latitude=13.17208, longitude=77.28180, elevation_m=900.0
    )
    b = GlobalTreeService.estimate_heartwood_for_site(
        64.7, latitude=15.23869, longitude=74.58571, elevation_m=600.0
    )
    c = GlobalTreeService.estimate_heartwood_for_site(
        64.7, latitude=12.30000, longitude=76.64000, elevation_m=750.0
    )

    triples = {
        (h.estimated_age_years, h.estimated_heartwood_kg, h.assumed_girth_cm)
        for h in (a, b, c)
    }
    assert len(triples) >= 2, (
        f"Expected location-specific estimates, got identical {triples}"
    )
    # Nearby points inside same ~0.01° weather cell must still diverge via micro site factor
    near_a = GlobalTreeService.estimate_heartwood_for_site(
        64.7, latitude=13.17208, longitude=77.28180, elevation_m=900.0
    )
    near_b = GlobalTreeService.estimate_heartwood_for_site(
        64.7, latitude=13.17550, longitude=77.28520, elevation_m=910.0
    )
    assert (
        near_a.estimated_age_years,
        near_a.estimated_heartwood_kg,
        near_a.assumed_dbh_cm,
    ) != (
        near_b.estimated_age_years,
        near_b.estimated_heartwood_kg,
        near_b.assumed_dbh_cm,
    )

def test_import_all_global_trees_authenticated(client):
    """Test bulk import endpoint requires appropriate role and succeeds."""
    # Unauthorized request without token
    unauth_resp = client.post("/api/v1/global-trees/import-all")
    assert unauth_resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Authorized admin request
    token = get_auth_token(client, "admin_importer", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}
    auth_resp = client.post("/api/v1/global-trees/import-all", headers=headers)
    assert auth_resp.status_code == status.HTTP_200_OK
    result = auth_resp.json()
    assert result["success"] is True
    assert "total_scanned" in result
    assert "total_registered_in_db" in result
