"""Tests for the Interactive Real-World GIS Map and Sandalwood Tree Finder UI."""

import pytest
from fastapi import status
from app.database.seed import seed_initial_data
from app.database.models.region import Region, RegionStatus
from app.database.models.tree import Tree
from app.database.models.user import User
from app.database.models.device import Device
from sqlalchemy import select
from tests.conftest import auth_headers
def test_get_gis_map_view_html(client):
    """The legacy map page is session-protected and returns the Leaflet shell."""
    anonymous = client.get("/map")
    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED

    headers = auth_headers(client, "map_html_user")
    resp = client.get("/map", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    assert "text/html" in resp.headers["content-type"]
    html_content = resp.text
    assert "Agroforestry GIS & Sandalwood Radar" in html_content
    assert "leaflet" in html_content.lower()
    assert "Sandalwood Trees" in html_content
    assert "Spatial Radar" in html_content


def test_seed_initial_data_creates_users_and_devices_without_reserves(db_session):
    """Seed creates users/devices only — no forest reserves or pre-registered trees."""
    seed_initial_data(db_session)

    regions = list(db_session.execute(select(Region)).scalars().all())
    assert len(regions) == 0

    users = list(db_session.execute(select(User)).scalars().all())
    assert len(users) >= 2

    devices = list(db_session.execute(select(Device)).scalars().all())
    assert len(devices) == 0

    trees = list(db_session.execute(select(Tree)).scalars().all())
    assert len(trees) == 0


def test_nearby_trees_spatial_search_on_operator_registered_data(client, db_session):
    """Spatial radar finds trees only after an operator assigns IDs and registers them."""
    seed_initial_data(db_session)

    from app.database.models.user import UserRole, UserStatus
    from app.core.security import hash_password
    from app.schemas.tree import TreeRegisterRequest
    from app.services.tree_service import TreeService

    db_session.add(
        Region(
            region_id="REG-KA-SHIVAMOGGA",
            name="Shivamogga Reserve",
            center_latitude=13.9350,
            center_longitude=75.5650,
            status=RegionStatus.ACTIVE,
        )
    )
    db_session.commit()

    admin = User(
        email="map_admin@agroforestry.gov.in",
        username="map_admin",
        full_name="Map Admin",
        hashed_password=hash_password("Password12345!"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin)
    db_session.commit()

    TreeService.register_tree(
        db_session,
        TreeRegisterRequest(
            tree_uid="KA-01",
            region_id="REG-KA-SHIVAMOGGA",
            latitude=13.9355,
            longitude=75.5652,
        ),
    )

    # Search within 2km of Shivamogga center (13.9350, 75.5650)
    headers = auth_headers(client, "map_nearby_admin")
    resp = client.post(
        "/api/v1/trees/nearby",
        json={
            "latitude": 13.9350,
            "longitude": 75.5650,
            "radius_meters": 2000.0,
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total_found"] >= 1
    first_tree = data["trees"][0]
    assert first_tree["distance_meters"] < 200.0
    assert first_tree["tree"]["tree_uid"] == "KA-01"
