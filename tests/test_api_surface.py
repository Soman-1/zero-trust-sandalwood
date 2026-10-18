"""Comprehensive tests for Full REST API Surface, User Administration, Decommissioning, and System Diagnostics."""

import pytest
from fastapi import status


def setup_admin_and_viewer(client):
    """Helper to setup admin and viewer."""
    client.post("/api/v1/auth/register", json={
        "email": "admin_surf@agroforestry.gov.in",
        "username": "admin_surf",
        "full_name": "Surface Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    admin_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_surf",
        "password": "Password12345!",
    }).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/api/v1/auth/register", json={
        "email": "viewer_surf@agroforestry.gov.in",
        "username": "viewer_surf",
        "full_name": "Surface Viewer",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    view_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "viewer_surf",
        "password": "Password12345!",
    }).json()["access_token"]
    view_headers = {"Authorization": f"Bearer {view_token}"}

    return admin_headers, view_headers


def test_user_administration_endpoints(client):
    """Test listing users, updating status, and updating role (Admin only)."""
    admin_headers, view_headers = setup_admin_and_viewer(client)

    # 1. Admin lists users
    resp = client.get("/api/v1/auth/users", headers=admin_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] >= 2

    # Find the viewer user id
    viewer_user = next(u for u in data["users"] if u["username"] == "viewer_surf")
    v_id = viewer_user["id"]

    # 2. Update role from VIEWER to OPERATOR
    role_resp = client.put(f"/api/v1/auth/users/{v_id}/role", json={"role": "OPERATOR"}, headers=admin_headers)
    assert role_resp.status_code == status.HTTP_200_OK
    assert role_resp.json()["role"] == "OPERATOR"

    # 3. Update status to SUSPENDED
    status_resp = client.put(f"/api/v1/auth/users/{v_id}/status", json={"status": "SUSPENDED"}, headers=admin_headers)
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.json()["status"] == "SUSPENDED"

    # 4. Non-admin / suspended user is blocked from user management
    blocked_resp = client.get("/api/v1/auth/users", headers=view_headers)
    assert blocked_resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)


def test_region_decommissioning(client):
    """Test decommissioning a region via DELETE endpoint."""
    admin_headers, _ = setup_admin_and_viewer(client)

    # Create region
    client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-DECOMM",
            "name": "Decommission Test Reserve",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [75.0, 13.0],
                        [75.1, 13.0],
                        [75.1, 13.1],
                        [75.0, 13.1],
                        [75.0, 13.0],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )

    # Decommission region
    del_resp = client.delete("/api/v1/regions/REG-KA-DECOMM", headers=admin_headers)
    assert del_resp.status_code == status.HTTP_200_OK
    assert del_resp.json()["status"] == "INACTIVE"


def test_tree_decommissioning(client):
    """Test decommissioning a sandalwood tree via DELETE endpoint."""
    admin_headers, _ = setup_admin_and_viewer(client)

    # Create region
    client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-TREE-DECOMM",
            "name": "Tree Decomm Reserve",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [75.0, 13.0],
                        [75.1, 13.0],
                        [75.1, 13.1],
                        [75.0, 13.1],
                        [75.0, 13.0],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )

    # Register tree
    tree_resp = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": "REG-KA-TREE-DECOMM",
            "species": "Santalum album",
            "latitude": 13.05,
            "longitude": 75.05,
        },
        headers=admin_headers,
    )
    tree_uid = tree_resp.json()["tree_uid"]

    # Decommission tree (e.g. mature harvested)
    del_resp = client.delete(
        f"/api/v1/trees/{tree_uid}?status_update=HARVESTED&reason=Mature+tree+lawfully+harvested",
        headers=admin_headers,
    )
    assert del_resp.status_code == status.HTTP_200_OK
    assert del_resp.json()["status"] == "HARVESTED"


def test_system_info_diagnostics(client):
    """Test system info endpoint returns healthy operational diagnostics."""
    admin_headers, _ = setup_admin_and_viewer(client)
    resp = client.get("/api/v1/system/info", headers=admin_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["database_status"] == "CONNECTED"
    assert data["ai_model_fitted"] is True
    assert "version" in data
    assert "environment" in data
