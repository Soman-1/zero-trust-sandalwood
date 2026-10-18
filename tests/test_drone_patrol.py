
"""Tests for Autonomous Drone Patrol Mission Generator and Tactical HUD Telemetry."""

import pytest
from app.ai.aerial_detector import aerial_detector
from tests.conftest import auth_headers


def test_drone_patrol_mission_generator_shivamogga():
    """Verify autonomous drone patrol mission generation for Shivamogga reserve."""
    mission = aerial_detector.generate_patrol_mission(preset_id="shivamogga_plantation", speed_mps=8.0)
    
    assert mission["preset_id"] == "shivamogga_plantation"
    assert mission["total_waypoints"] == 8
    assert mission["total_distance_m"] > 500.0
    assert mission["total_duration_sec"] > 50.0
    assert mission["sandalwood_count"] > 0
    assert mission["drone_hardware_id"].startswith("DEV-UAV-")
    assert len(mission["mission_integrity_hash"]) == 64
    
    # Check sequential waypoints
    waypoints = mission["waypoints"]
    assert len(waypoints) == 8
    assert waypoints[0]["waypoint_id"] == "WP-01"
    assert waypoints[0]["action"] == "TAKEOFF"
    assert waypoints[-1]["action"] == "RTB_LAND"
    
    # Check bearings and positive distances
    for wp in waypoints:
        assert 0.0 <= wp["leg_bearing_deg"] <= 360.0
        assert wp["altitude_m"] == 45.0
        assert wp["eta_sec"] >= 0.0
        
    # Check canopy target timeline scheduling
    targets = mission["canopy_targets"]
    assert len(targets) == mission["sandalwood_count"] + mission["host_trees_count"]
    for t in targets:
        assert "Santalum album" in t["species_scientific"] or t["is_host_tree"]
        assert 0.0 <= t["confidence"] <= 1.0
        assert t["crown_diameter_m"] > 0.0
        assert t["interception_time_sec"] > 0.0
        assert t["associated_waypoint_id"].startswith("WP-")


def test_drone_patrol_mission_generator_mysore():
    """Verify autonomous drone patrol mission for Mysore heritage belt."""
    mission = aerial_detector.generate_patrol_mission(preset_id="mysore_reserve", speed_mps=10.0)
    assert mission["preset_id"] == "mysore_reserve"
    assert mission["survey_speed_mps"] == 10.0
    assert len(mission["waypoints"]) == 8


def test_drone_patrol_api_endpoint(client):
    """Verify GET /api/v1/satellite/drone-patrol-mission returns valid 200 payload."""
    headers = auth_headers(client, "drone_patrol_admin")
    resp = client.get(
        "/api/v1/satellite/drone-patrol-mission?preset_id=shivamogga_plantation&speed_mps=8.5",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mission_id"].startswith("MSN-UAV-")
    assert data["survey_speed_mps"] == 8.5
    assert len(data["waypoints"]) == 8
    assert data["sandalwood_count"] > 0
    assert len(data["canopy_targets"]) > 0
    assert len(data["mission_integrity_hash"]) == 64
