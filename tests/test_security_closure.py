"""Locks the zero-trust gaps that used to be open by default."""

import app.core.runtime as runtime
from fastapi import status
from app.core.config import settings


def test_public_register_cannot_choose_admin(client):
    previous = runtime.privileged_self_register
    runtime.privileged_self_register = False
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "would_be_admin@agroforestry.gov.in",
                "username": "would_be_admin",
                "full_name": "Privilege Escalation",
                "password": "Password12345!",
                "role": "ADMIN",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        runtime.privileged_self_register = previous


def test_public_registration_is_closed_when_disabled(client):
    previous_flag = settings.ALLOW_PUBLIC_REGISTRATION
    previous_priv = runtime.privileged_self_register
    settings.ALLOW_PUBLIC_REGISTRATION = False
    runtime.privileged_self_register = False
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "closed_reg@agroforestry.gov.in",
                "username": "closed_reg",
                "full_name": "Closed Registration",
                "password": "Password12345!",
                "role": "VIEWER",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        settings.ALLOW_PUBLIC_REGISTRATION = previous_flag
        runtime.privileged_self_register = previous_priv


def test_debug_sink_is_gone(client):
    response = client.post("/api/v1/system/agent-debug-log", json={"msg": "nope"})
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND)


def test_system_info_requires_auth(client):
    response = client.get("/api/v1/system/info")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_suspended_login_matches_bad_password(client):
    from tests.conftest import auth_headers

    admin_headers = auth_headers(client, "phase1_admin")
    client.post("/api/v1/auth/register", json={
        "email": "suspended_login@agroforestry.gov.in",
        "username": "suspended_login",
        "full_name": "Suspended Login",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    users = client.get("/api/v1/auth/users", headers=admin_headers).json()["users"]
    user_id = next(user["id"] for user in users if user["username"] == "suspended_login")
    suspended = client.put(
        f"/api/v1/auth/users/{user_id}/status",
        json={"status": "SUSPENDED"},
        headers=admin_headers,
    )
    assert suspended.status_code == status.HTTP_200_OK

    bad = client.post("/api/v1/auth/login", json={
        "username_or_email": "nobody_phase1",
        "password": "not-the-password",
    })
    blocked = client.post("/api/v1/auth/login", json={
        "username_or_email": "suspended_login",
        "password": "Password12345!",
    })
    assert bad.status_code == status.HTTP_401_UNAUTHORIZED
    assert blocked.status_code == status.HTTP_401_UNAUTHORIZED
    assert blocked.json()["error"]["message"] == bad.json()["error"]["message"]
    assert "status" not in blocked.json()["error"]["details"]


def test_simulated_evidence_cannot_register_tree(client):
    from tests.conftest import auth_headers

    headers = auth_headers(client, "sim_tree_admin")
    response = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-77",
            "latitude": 13.9,
            "longitude": 75.5,
            "evidence_origin": "SIMULATED",
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["details"]["evidence_origin"] == "SIMULATED"
