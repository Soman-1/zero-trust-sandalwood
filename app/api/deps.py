"""Zero Trust authorization and authentication FastAPI dependencies."""

from typing import List, Tuple, Callable, Optional
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.core.errors import UnauthorizedError, ForbiddenError
from app.database.database import get_db
from app.database.models.user import User, UserRole, UserStatus
from app.services.auth_service import AuthService

security_bearer = HTTPBearer(auto_error=False)


def get_current_user_and_session(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> Tuple[User, str]:
    """
    Zero Trust dependency: validates JWT token, verifies active session state
    against database revocation list, and fetches the authenticated user.
    Accepts Authorization: Bearer or the httpOnly agro_access_token cookie.
    Returns: (User, token_jti)
    """
    # Fast path: Reuse user context already validated and populated by AuthenticationMiddleware
    if getattr(request.state, "is_authenticated", False) and getattr(request.state, "user", None):
        user = db.merge(request.state.user, load=False)
        token_jti = getattr(request.state, "session_jti", "")
        return user, token_jti

    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("agro_access_token")
    if not token:
        raise UnauthorizedError(
            message="Authentication credentials were not provided",
            details={"scheme": "Bearer"},
        )
    payload = decode_access_token(token)

    sub = payload.get("sub")
    token_jti = payload.get("jti")

    if not sub or not token_jti:
        raise UnauthorizedError(
            message="Malformed authentication token claims",
            details={"claims": ["sub", "jti"]},
        )

    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise UnauthorizedError(message="Invalid token subject")

    # Zero Trust Session Verification (Check database revocation list)
    is_valid_session = AuthService.validate_session(db, user_id=user_id, token_jti=token_jti)
    if not is_valid_session:
        raise UnauthorizedError(
            message="Session is inactive or has been revoked",
            details={"reason": "session_revoked"},
        )

    user = db.get(User, user_id)
    if not user:
        raise UnauthorizedError(message="User associated with token no longer exists")

    if user.status != UserStatus.ACTIVE:
        raise ForbiddenError(
            message=f"User account is {user.status.value.lower()}",
            details={"status": user.status.value},
        )

    return user, token_jti


def get_current_user(
    auth_data: Tuple[User, str] = Depends(get_current_user_and_session),
) -> User:
    """Dependency that returns the authenticated User entity."""
    user, _ = auth_data
    return user


def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Optional authentication dependency for public/dashboard endpoints."""
    if getattr(request.state, "is_authenticated", False) and getattr(request.state, "user", None):
        return db.merge(request.state.user, load=False)

    if not credentials or not credentials.credentials:
        return None
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        sub = payload.get("sub")
        token_jti = payload.get("jti")
        if not sub or not token_jti:
            return None
        user_id = int(sub)
        if not AuthService.validate_session(db, user_id=user_id, token_jti=token_jti):
            return None
        user = db.get(User, user_id)
        if user and user.status == UserStatus.ACTIVE:
            return user
        return None
    except Exception:
        return None


def get_current_session_jti(
    auth_data: Tuple[User, str] = Depends(get_current_user_and_session),
) -> str:
    """Dependency that returns the active session JTI."""
    _, token_jti = auth_data
    return token_jti


def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory to enforce Role-Based Access Control (RBAC).
    Usage: Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR))
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(
                message="You do not have sufficient permissions to perform this action",
                details={
                    "required_roles": [r.value for r in allowed_roles],
                    "user_role": user.role.value,
                },
            )
        return user

    return role_checker


def get_current_device(
    request: Request,
    db: Session = Depends(get_db),
) -> "Device":
    """
    Zero Trust dependency for IoT Field Devices:
    Extracts device headers (X-Device-ID & X-Device-Key), validates device credentials
    and ensures the device is ACTIVE and non-revoked.
    """
    from app.database.models.device import Device
    from app.services.device_service import DeviceService

    device_id = request.headers.get("x-device-id") or request.headers.get("X-Device-ID")
    device_key = request.headers.get("x-device-key") or request.headers.get("X-Device-Key")

    # Support combined X-API-Key header format "DEVICE_ID:API_KEY" as fallback
    if not (device_id and device_key):
        combined_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
        if combined_key and ":" in combined_key:
            parts = combined_key.split(":", 1)
            device_id, device_key = parts[0], parts[1]

    if not device_id or not device_key:
        raise UnauthorizedError(
            message="Device authentication credentials missing. Please provide X-Device-ID and X-Device-Key headers.",
            details={"required_headers": ["X-Device-ID", "X-Device-Key"]},
        )

    return DeviceService.authenticate_device(db=db, device_id=device_id.strip(), raw_api_key=device_key.strip())

