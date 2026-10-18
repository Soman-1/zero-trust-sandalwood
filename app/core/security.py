"""Security utilities: password hashing and JWT token operations."""

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

import jwt

from app.core.config import settings
from app.core.errors import UnauthorizedError


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with a unique random salt.
    Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    salt = os.urandom(16)
    iterations = 100_000
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived_key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash using constant-time comparison.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False

        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])

        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(computed_hash, expected_hash)
    except Exception:
        return False


def create_access_token(
    subject: Any,
    role: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, datetime]:
    """
    Generate a signed JWT access token containing subject, role, and a unique jti identifier.
    Returns: (jwt_token_string, token_jti, expires_at_datetime)
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expires_at = now + expires_delta
    else:
        expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    token_jti = str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, token_jti, expires_at


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token signature and expiration.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(
            message="Token has expired",
            details={"reason": "token_expired"},
        )
    except jwt.InvalidTokenError:
        raise UnauthorizedError(
            message="Invalid authentication token",
            details={"reason": "invalid_token"},
        )


def generate_device_api_key() -> str:
    """Generate a secure cryptographic API key for IoT field devices."""
    random_bytes = os.urandom(24).hex()
    return f"sw_dev_{random_bytes}"


def hash_device_api_key(raw_api_key: str, salt: Optional[str] = None) -> str:
    """Hash a device API key. New keys use a per-device salt; legacy keys used JWT_SECRET."""
    if salt:
        material = bytes.fromhex(salt) + raw_api_key.encode("utf-8")
    else:
        material = settings.JWT_SECRET.encode("utf-8") + raw_api_key.encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def verify_device_api_key(raw_api_key: str, hashed_api_key: str, salt: Optional[str] = None) -> bool:
    """Verify a raw device API key against stored hash using constant-time comparison."""
    try:
        computed = hash_device_api_key(raw_api_key, salt=salt)
        return hmac.compare_digest(computed, hashed_api_key)
    except Exception:
        return False
