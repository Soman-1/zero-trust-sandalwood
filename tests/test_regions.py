"""Tests for monitoring region creation, boundary validation, and point-in-polygon checks."""

import pytest
from fastapi import status


def get_auth_token(client, username="admin_reg_user", role="ADMIN"):
    """Helper to get user token."""
    client.post("/api/v1/auth/register", json={
        "email": f"{username}@agroforestry.gov.in",
        "username": username,
        "full_name": f"{username} FullName",
        "password": "Password12345!",
        "role": role,
    })
    resp = client.post("/api/v1/auth/login", json={
        "username_or_email": username,
        "password": "Password12345!",
    })
    return resp.json()["access_token"]


def test_create_region_with_geojson_boundary(client):
    """Test region creation with automatic centroid calculation."""
    token = get_auth_token(client, "admin_reg_1", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "region_id": "REG-KA-SHIVAMOGGA",
        "name": "Shivamogga Sandalwood Reserve",
        "description": "Western Ghats agroforestry sanctuary",
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
        "area_hectares": 150.0,
    }

    response = client.post("/api/v1/regions", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["region_id"] == "REG-KA-SHIVAMOGGA"
    assert data["center_latitude"] is not None
    assert data["center_longitude"] is not None
    assert data["status"] == "ACTIVE"


def test_point_in_polygon_coordinate_checking(client):
    """
    Test Ray-Casting Point-in-Polygon boundary checking:
    1. Point inside polygon boundary -> is_inside = True
    2. Point outside polygon boundary -> is_inside = False
    """
    token = get_auth_token(client, "admin_reg_2", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a region bounded by 13.92-13.94 Lat, 75.56-75.58 Lon
    client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-POLYGON-TEST",
            "name": "Polygon Test Zone",
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
        headers=headers,
    )

    # 2. Check point INSIDE: (13.9300, 75.5700)
    inside_resp = client.post(
        "/api/v1/regions/REG-KA-POLYGON-TEST/check-coordinate",
        json={"latitude": 13.9300, "longitude": 75.5700},
        headers=headers,
    )
    assert inside_resp.status_code == status.HTTP_200_OK
    assert inside_resp.json()["is_inside"] is True

    # 3. Check point OUTSIDE: (12.9716, 77.5946) (Bangalore)
    outside_resp = client.post(
        "/api/v1/regions/REG-KA-POLYGON-TEST/check-coordinate",
        json={"latitude": 12.9716, "longitude": 77.5946},
        headers=headers,
    )
    assert outside_resp.status_code == status.HTTP_200_OK
    assert outside_resp.json()["is_inside"] is False


def test_invalid_gps_coordinates_rejection(client):
    """Test that out-of-range latitude/longitude are rejected."""
    token = get_auth_token(client, "admin_reg_3", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    # Invalid latitude > 90
    r1 = client.post(
        "/api/v1/regions/REG-KA-POLYGON-TEST/check-coordinate",
        json={"latitude": 95.0, "longitude": 75.0},
        headers=headers,
    )
    assert r1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Invalid longitude > 180
    r2 = client.post(
        "/api/v1/regions/REG-KA-POLYGON-TEST/check-coordinate",
        json={"latitude": 13.0, "longitude": 185.0},
        headers=headers,
    )
    assert r2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_region_update_and_retrieval(client):
    """Test retrieving and updating region properties."""
    token = get_auth_token(client, "admin_reg_4", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/v1/regions",
        json={"region_id": "REG-KA-MYSORE", "name": "Mysore Reserve", "area_hectares": 80.0},
        headers=headers,
    )

    # Fetch by region_id
    get_resp = client.get("/api/v1/regions/REG-KA-MYSORE", headers=headers)
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["name"] == "Mysore Reserve"

    # Update region name and area
    update_resp = client.put(
        "/api/v1/regions/REG-KA-MYSORE",
        json={"name": "Mysore Sandalwood Sanctuary", "area_hectares": 95.0},
        headers=headers,
    )
    assert update_resp.status_code == status.HTTP_200_OK
    assert update_resp.json()["name"] == "Mysore Sandalwood Sanctuary"
    assert update_resp.json()["area_hectares"] == 95.0


def test_region_rbac_restrictions(client):
    """Test that VIEWER role cannot create or modify regions."""
    viewer_token = get_auth_token(client, "viewer_reg_user", "VIEWER")
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Attempt create -> 403 Forbidden
    r1 = client.post(
        "/api/v1/regions",
        json={"region_id": "REG-UNAUTH", "name": "Unauthorized Region"},
        headers=viewer_headers,
    )
    assert r1.status_code == status.HTTP_403_FORBIDDEN
