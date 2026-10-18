"""Comprehensive tests for Sandalwood tree registration, sequential ID generation, and spatial queries."""

import pytest
from fastapi import status


def get_auth_token(client, username="admin_tree_user", role="ADMIN"):
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


def create_test_region(client, headers, region_id="REG-KA-SHIVAMOGGA"):
    """Helper to create a region with polygon boundary."""
    client.post(
        "/api/v1/regions",
        json={
            "region_id": region_id,
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
        headers=headers,
    )


def test_operator_assigned_sandalwood_tree_registration(client):
    """
    Operator assigns Tree IDs manually:
    Tree 1 -> KA-01
    Tree 2 -> KA-02
    Tree 3 -> KA-03
    """
    token = get_auth_token(client, "admin_tree_1", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}
    create_test_region(client, headers, "REG-KA-SHIVAMOGGA")

    # Tree #1
    t1 = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": "REG-KA-SHIVAMOGGA",
            "species": "Santalum album",
            "latitude": 13.9310,
            "longitude": 75.5720,
            "altitude": 640.0,
            "gps_accuracy": 1.5,
            "estimated_age_years": 15.0,
            "girth_cm": 48.0,
            "height_m": 7.2,
        },
        headers=headers,
    )
    assert t1.status_code == status.HTTP_201_CREATED
    assert t1.json()["tree_uid"] == "KA-01"

    # Tree #2
    t2 = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-02",
            "region_id": "REG-KA-SHIVAMOGGA",
            "species": "Santalum album",
            "latitude": 13.9315,
            "longitude": 75.5725,
            "altitude": 641.0,
            "gps_accuracy": 2.0,
            "estimated_age_years": 10.0,
            "girth_cm": 35.0,
            "height_m": 5.5,
        },
        headers=headers,
    )
    assert t2.status_code == status.HTTP_201_CREATED
    assert t2.json()["tree_uid"] == "KA-02"

    # Tree #3
    t3 = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "ka-03",
            "region_id": "REG-KA-SHIVAMOGGA",
            "species": "Santalum album",
            "latitude": 13.9320,
            "longitude": 75.5730,
            "altitude": 642.0,
            "gps_accuracy": 1.8,
            "estimated_age_years": 8.0,
            "girth_cm": 28.0,
            "height_m": 4.5,
        },
        headers=headers,
    )
    assert t3.status_code == status.HTTP_201_CREATED
    assert t3.json()["tree_uid"] == "KA-03"

    # Duplicate ID rejected
    dup = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": "REG-KA-SHIVAMOGGA",
            "species": "Santalum album",
            "latitude": 13.9330,
            "longitude": 75.5740,
        },
        headers=headers,
    )
    assert dup.status_code == status.HTTP_409_CONFLICT


def test_zero_trust_tree_outside_region_rejection(client):
    """
    Zero Trust Boundary Enforcement:
    If a tree is claimed at coordinates outside the designated region boundary,
    the registration must be rejected with 400 Bad Request (COORDINATE_OUTSIDE_REGION).
    """
    token = get_auth_token(client, "admin_tree_2", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}
    create_test_region(client, headers, "REG-KA-BOUNDARY-TEST")

    # Outside point: (12.9716, 77.5946) (Bangalore) against Shivamogga region (13.92-13.94, 75.56-75.58)
    resp = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": "REG-KA-BOUNDARY-TEST",
            "species": "Santalum album",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["error"]["code"] == "COORDINATE_OUTSIDE_REGION"


def test_nearby_trees_spatial_query(client):
    """Test querying sandalwood trees within a radius (e.g. 500m) of a GPS location."""
    token = get_auth_token(client, "admin_tree_3", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}
    create_test_region(client, headers, "REG-KA-SPATIAL-TEST")

    # Tree near center: ~50 meters away
    client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-02",
            "region_id": "REG-KA-SPATIAL-TEST",
            "species": "Santalum album",
            "latitude": 13.9304,
            "longitude": 75.5704,
        },
        headers=headers,
    )

    # Tree far away: ~1,500 meters away (still inside polygon)
    client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-03",
            "region_id": "REG-KA-SPATIAL-TEST",
            "species": "Santalum album",
            "latitude": 13.9390,
            "longitude": 75.5780,
        },
        headers=headers,
    )

    # Query with 200m radius from (13.9300, 75.5700) -> should only find the close tree
    nearby_resp = client.post(
        "/api/v1/trees/nearby",
        json={
            "latitude": 13.9300,
            "longitude": 75.5700,
            "radius_meters": 200.0,
            "region_id": "REG-KA-SPATIAL-TEST",
        },
        headers=headers,
    )
    assert nearby_resp.status_code == status.HTTP_200_OK
    data = nearby_resp.json()
    assert data["total_found"] == 1
    assert data["trees"][0]["distance_meters"] < 200.0


def test_tree_retrieval_and_update(client):
    """Test fetching tree by Tree ID and updating its attributes."""
    token = get_auth_token(client, "admin_tree_4", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}
    create_test_region(client, headers, "REG-KA-TREE-UPDATE")

    reg = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-04",
            "region_id": "REG-KA-TREE-UPDATE",
            "species": "Santalum album",
            "latitude": 13.9310,
            "longitude": 75.5720,
            "girth_cm": 30.0,
            "status": "HEALTHY",
        },
        headers=headers,
    )
    tree_uid = reg.json()["tree_uid"]

    # Fetch by tree_uid
    get_resp = client.get(f"/api/v1/trees/{tree_uid}", headers=headers)
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["tree_uid"] == tree_uid

    # Update girth and status
    update_resp = client.put(
        f"/api/v1/trees/{tree_uid}",
        json={"girth_cm": 34.5, "status": "AT_RISK", "notes": "Signs of insect borers on outer bark."},
        headers=headers,
    )
    assert update_resp.status_code == status.HTTP_200_OK
    updated_data = update_resp.json()
    assert updated_data["girth_cm"] == 34.5
    assert updated_data["status"] == "AT_RISK"
    assert "insect borers" in updated_data["notes"]


def test_allometric_estimate_resolves_age_and_heartwood_labels(client, db_session):
    """An occurrence-sourced tree must report its estimate, not 'unknown'.

    Guards the regression where register_selected_tree computed a heartwood
    estimate, showed it to the operator, then dropped it before persisting.
    """
    from app.services.tree_service import TreeService

    token = get_auth_token(client, "admin_tree_allometric", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    reg = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-07",
            "species": "Santalum album",
            "latitude": 13.9311,
            "longitude": 75.5721,
            "survival_confirmed": False,
        },
        headers=headers,
    )
    assert reg.status_code == status.HTTP_201_CREATED
    body = reg.json()
    assert body["age_label"] == "Age unknown"
    assert body["heartwood_label"].startswith("Heartwood unknown")

    tree = TreeService.get_tree_by_uid(db_session, "KA-07")
    TreeService.apply_allometric_estimate(
        db=db_session,
        tree=tree,
        estimated_age_years=16,
        girth_cm=81.7,
        height_m=7.4,
    )

    estimated = client.get("/api/v1/trees/KA-07", headers=headers).json()
    assert estimated["biometrics_source"] == "ALLOMETRIC_ESTIMATE"
    assert "allometric estimate" in estimated["age_label"]
    assert "modelled from estimated stem" in estimated["heartwood_label"]
    assert "kg" in estimated["heartwood_label"]

    # A field survey supersedes the estimate and is relabelled as measured.
    surveyed = client.put(
        "/api/v1/trees/KA-07",
        json={"girth_cm": 64.0, "height_m": 6.1, "host_notes": "Neem 4 m; Pongamia 9 m"},
        headers=headers,
    ).json()
    assert surveyed["biometrics_source"] == "FIELD_MEASURED"
    assert "modelled" not in surveyed["heartwood_label"]
    assert surveyed["hosts_label"] == "Neem 4 m; Pongamia 9 m"


def test_unsurveyed_hosts_label_explains_itself(client):
    """Host species are never inferred, so the blank must say what is needed."""
    token = get_auth_token(client, "admin_tree_hosts", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    reg = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-08",
            "species": "Santalum album",
            "latitude": 13.9312,
            "longitude": 75.5722,
        },
        headers=headers,
    )
    assert reg.status_code == status.HTTP_201_CREATED
    assert "needs a field visit" in reg.json()["hosts_label"]


def test_tree_rbac_permissions(client):
    """Test that VIEWER users cannot register or modify sandalwood trees."""
    viewer_token = get_auth_token(client, "viewer_tree_user", "VIEWER")
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    r1 = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-05",
            "region_id": "REG-KA-SHIVAMOGGA",
            "species": "Santalum album",
            "latitude": 13.9310,
            "longitude": 75.5720,
        },
        headers=viewer_headers,
    )
    assert r1.status_code == status.HTTP_403_FORBIDDEN


def test_tree_permanent_delete_removes_from_registry(client):
    """Delete must remove the tree from the registry list, not only change status."""
    token = get_auth_token(client, "admin_tree_delete", "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}
    create_test_region(client, headers, "REG-KA-TREE-DELETE")

    reg = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-99001",
            "region_id": "REG-KA-TREE-DELETE",
            "species": "Santalum album",
            "latitude": 13.93,
            "longitude": 75.57,
        },
        headers=headers,
    )
    assert reg.status_code == status.HTTP_201_CREATED
    tree_uid = reg.json()["tree_uid"]

    delete_resp = client.delete(f"/api/v1/trees/{tree_uid}/record", headers=headers)
    assert delete_resp.status_code == status.HTTP_200_OK
    assert delete_resp.json()["deleted"] is True
    assert delete_resp.json()["tree_uid"] == tree_uid

    missing = client.get(f"/api/v1/trees/{tree_uid}", headers=headers)
    assert missing.status_code == status.HTTP_404_NOT_FOUND

    listed = client.get("/api/v1/trees", headers=headers)
    assert listed.status_code == status.HTTP_200_OK
    assert all(item["tree_uid"] != tree_uid for item in listed.json())

    viewer_token = get_auth_token(client, "viewer_tree_delete", "VIEWER")
    denied = client.delete(
        f"/api/v1/trees/{tree_uid}/record",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN
