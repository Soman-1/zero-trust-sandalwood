"""Comprehensive tests for Zero Trust authentication, RBAC, and session revocation."""

import pytest
from fastapi import status, Depends, APIRouter
from app.database.models.user import UserRole, UserStatus, User
from app.api.deps import require_roles, get_current_user


def test_user_registration_success(client):
    """Test successful user registration."""
    payload = {
        "email": "test_operator@agroforestry.gov.in",
        "username": "test_op1",
        "full_name": "Test Operator One",
        "password": "SecurePassword123!",
        "role": "OPERATOR",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["username"] == payload["username"]
    assert data["role"] == "OPERATOR"
    assert data["status"] == "ACTIVE"
    assert "hashed_password" not in data


def test_user_registration_duplicate_rejection(client):
    """Test rejection of duplicate registration attempts."""
    payload = {
        "email": "dup_user@agroforestry.gov.in",
        "username": "dup_user",
        "full_name": "Duplicate User",
        "password": "SecurePassword123!",
        "role": "VIEWER",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == status.HTTP_201_CREATED

    # Duplicate email
    r2 = client.post("/api/v1/auth/register", json={
        "email": "dup_user@agroforestry.gov.in",
        "username": "other_username",
        "full_name": "Other Name",
        "password": "SecurePassword123!",
        "role": "VIEWER",
    })
    assert r2.status_code == status.HTTP_400_BAD_REQUEST
    assert r2.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    # Duplicate username
    r3 = client.post("/api/v1/auth/register", json={
        "email": "other_email@agroforestry.gov.in",
        "username": "dup_user",
        "full_name": "Other Name",
        "password": "SecurePassword123!",
        "role": "VIEWER",
    })
    assert r3.status_code == status.HTTP_400_BAD_REQUEST
    assert r3.json()["error"]["code"] == "USERNAME_ALREADY_EXISTS"


def test_user_login_and_me_endpoint(client):
    """Test user login and fetching current authenticated profile."""
    # 1. Register user
    client.post("/api/v1/auth/register", json={
        "email": "login_user@agroforestry.gov.in",
        "username": "login_user",
        "full_name": "Login Tester",
        "password": "MySuperSecretPassword123",
        "role": "OPERATOR",
    })

    # 2. Login with username
    login_resp = client.post("/api/v1/auth/login", json={
        "username_or_email": "login_user",
        "password": "MySuperSecretPassword123",
    })
    assert login_resp.status_code == status.HTTP_200_OK
    token_data = login_resp.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Access /me endpoint with Bearer token
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == status.HTTP_200_OK
    me_data = me_resp.json()
    assert me_data["username"] == "login_user"
    assert me_data["role"] == "OPERATOR"


def test_login_failure_invalid_credentials(client):
    """Test that invalid passwords and non-existent users are rejected."""
    # Invalid password
    resp1 = client.post("/api/v1/auth/login", json={
        "username_or_email": "login_user",
        "password": "WrongPassword!",
    })
    assert resp1.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp1.json()["error"]["code"] == "UNAUTHORIZED"

    # Non-existent user
    resp2 = client.post("/api/v1/auth/login", json={
        "username_or_email": "non_existent_user_999",
        "password": "SomePassword123!",
    })
    assert resp2.status_code == status.HTTP_401_UNAUTHORIZED


def test_zero_trust_logout_and_session_revocation(client):
    """
    Zero Trust Verification:
    After logout, the token must be revoked immediately in the database
    and rejected on subsequent requests, even if the expiration is in the future.
    """
    # 1. Register & login
    client.post("/api/v1/auth/register", json={
        "email": "revocation_user@agroforestry.gov.in",
        "username": "revocation_user",
        "full_name": "Revoke Tester",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    login_resp = client.post("/api/v1/auth/login", json={
        "username_or_email": "revocation_user",
        "password": "Password12345!",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Confirm token works before logout
    pre_logout = client.get("/api/v1/auth/me", headers=headers)
    assert pre_logout.status_code == status.HTTP_200_OK

    # 3. Perform logout
    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == status.HTTP_200_OK
    assert logout_resp.json()["success"] is True

    # 4. Attempt to use revoked token - MUST be rejected with 401 Unauthorized
    post_logout = client.get("/api/v1/auth/me", headers=headers)
    assert post_logout.status_code == status.HTTP_401_UNAUTHORIZED
    assert post_logout.json()["error"]["details"]["reason"] == "session_revoked"


def test_rbac_role_enforcement(client, app):
    """Test Role-Based Access Control gatekeeper."""
    # Create test protected routes
    test_router = APIRouter(prefix="/api/v1/test-rbac")

    @test_router.get("/admin-only")
    def admin_endpoint(user: User = Depends(require_roles(UserRole.ADMIN))):
        return {"message": "Welcome Admin"}

    @test_router.get("/operator-or-admin")
    def operator_endpoint(user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR))):
        return {"message": "Welcome Operator/Admin"}

    app.include_router(test_router)

    # Register Viewer User
    client.post("/api/v1/auth/register", json={
        "email": "viewer_user@agroforestry.gov.in",
        "username": "viewer_user",
        "full_name": "Viewer Only",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    viewer_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "viewer_user",
        "password": "Password12345!",
    }).json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Register Admin User
    client.post("/api/v1/auth/register", json={
        "email": "super_admin@agroforestry.gov.in",
        "username": "super_admin",
        "full_name": "Super Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    admin_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "super_admin",
        "password": "Password12345!",
    }).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Viewer attempts admin route -> 403 Forbidden
    r1 = client.get("/api/v1/test-rbac/admin-only", headers=viewer_headers)
    assert r1.status_code == status.HTTP_403_FORBIDDEN

    # 2. Viewer attempts operator/admin route -> 403 Forbidden
    r2 = client.get("/api/v1/test-rbac/operator-or-admin", headers=viewer_headers)
    assert r2.status_code == status.HTTP_403_FORBIDDEN

    # 3. Admin attempts admin route -> 200 OK
    r3 = client.get("/api/v1/test-rbac/admin-only", headers=admin_headers)
    assert r3.status_code == status.HTTP_200_OK
    assert r3.json()["message"] == "Welcome Admin"


def test_logout_with_cookie_only_revokes_session(client):
    """A reload drops the in-memory bearer token. The cookie must still revoke the session."""
    client.post("/api/v1/auth/register", json={
        "email": "cookie_logout@agroforestry.gov.in",
        "username": "cookie_logout",
        "full_name": "Cookie Logout",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    login = client.post("/api/v1/auth/login", json={
        "username_or_email": "cookie_logout",
        "password": "Password12345!",
    })
    assert login.status_code == status.HTTP_200_OK
    token = login.json()["access_token"]
    assert "agro_access_token" in login.cookies or "agro_access_token" in client.cookies

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == status.HTTP_200_OK

    replay = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert replay.status_code == status.HTTP_401_UNAUTHORIZED
