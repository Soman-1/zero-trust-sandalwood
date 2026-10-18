"""Tests for Zero Trust middlewares: authentication, authorization, anti-replay."""

import time
import pytest
from fastapi import status
from app.middleware.authorization import RoleChecker, require_admin
from app.database.models.user import User, UserRole, UserStatus
from app.core.errors import ForbiddenError, UnauthorizedError


def test_zero_trust_middleware_headers_attached(client):
    """Test that Zero Trust diagnostic and security headers are attached to responses."""
    resp = client.get("/health")
    assert resp.status_code == status.HTTP_200_OK
    assert "X-Process-Time" in resp.headers
    assert resp.headers.get("X-Zero-Trust-Framework") == "Enforced"


def test_zero_trust_clock_skew_replay_defense(client):
    """Test that requests with expired/skewed timestamps are rejected."""
    # Stale timestamp from 1 hour ago
    old_timestamp = time.time() - 3600

    resp = client.get(
        "/health",
        headers={"X-Timestamp": str(old_timestamp)},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    data = resp.json()
    assert data["error"]["code"] == "CLOCK_SKEW_EXCEEDED"


def test_zero_trust_valid_timestamp_accepted(client):
    """Test that requests with fresh timestamps are accepted."""
    current_timestamp = time.time()
    resp = client.get(
        "/health",
        headers={"X-Timestamp": str(current_timestamp)},
    )
    assert resp.status_code == status.HTTP_200_OK


def test_rate_identity_ignores_device_header():
    """A forged X-Device-ID must not create a separate rate-limit bucket."""
    class _Client:
        host = "198.51.100.10"

    class _Request:
        client = _Client()
        headers = {"X-Device-ID": "spoofed-device"}

    from app.middleware.request_verification import client_rate_identity
    from app.core.anti_replay import AntiReplayValidator

    identity = client_rate_identity(_Request())
    assert identity == "198.51.100.10"
    assert "spoofed-device" not in identity

    limiter = AntiReplayValidator(max_requests_per_second=2)
    now = time.time()
    assert limiter.validate_request(now, caller_id=identity)[0] is True
    assert limiter.validate_request(now, caller_id=identity)[0] is True
    blocked, _message = limiter.validate_request(now, caller_id=identity)
    assert blocked is False


def test_weight_checksum_mismatch_refuses_load(tmp_path):
    from app.ai.satellite_classifier import ModelIntegrityError, verify_weight_checksum

    weights = tmp_path / "model.joblib"
    checksum = tmp_path / "model.joblib.sha256"
    weights.write_bytes(b"tampered")
    checksum.write_text("0" * 64, encoding="utf-8")
    with pytest.raises(ModelIntegrityError):
        verify_weight_checksum(str(weights), str(checksum))


def test_role_checker_enforcement():
    """Test RBAC role checker utility."""
    admin_user = User(id=1, email="admin@test.com", username="admin", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    viewer_user = User(id=2, email="viewer@test.com", username="viewer", role=UserRole.VIEWER, status=UserStatus.ACTIVE)

    # Admin should succeed
    assert require_admin(admin_user) == admin_user

    # Viewer should be blocked
    with pytest.raises(ForbiddenError):
        require_admin(viewer_user)

    # None should raise UnauthorizedError
    with pytest.raises(UnauthorizedError):
        require_admin(None)
