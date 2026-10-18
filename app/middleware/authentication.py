"""Authentication middleware for Bearer token inspection and session validation."""

from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.logging import logger
import app.database.database as db_module
from app.database.models.user import User, UserStatus
from app.services.auth_service import AuthService

# Paths that do not require a user session. Device ingest is authenticated
# by X-Device-ID / X-Device-Key on the route, not by a user JWT.
_PUBLIC_EXACT = {
    "/",
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
}
_DEVICE_PREFIXES = (
    "/api/v1/measurements/ingest",
    "/api/v1/devices/heartbeat",
)
_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


def _is_public(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    if path in _PUBLIC_EXACT:
        return True
    if path in _DOCS_PATHS or path.startswith("/docs"):
        return bool(settings.DEBUG)
    if method == "POST" and any(path == p or path.startswith(p + "/") for p in _DEVICE_PREFIXES):
        return True
    return False


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that inspects incoming Authorization headers,
    verifies session validity against the revocation ledger,
    and attaches authenticated user context to request.state.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request.state.user = None
        request.state.session_jti = None
        request.state.is_authenticated = False

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = request.cookies.get("agro_access_token")

        session_revoked = False
        if token:
            try:
                payload = decode_access_token(token)
                sub = payload.get("sub")
                token_jti = payload.get("jti")

                if sub and token_jti:
                    user_id = int(sub)
                    with db_module.SessionLocal() as db:
                        is_valid = AuthService.validate_session(db, user_id=user_id, token_jti=token_jti)
                        if not is_valid:
                            session_revoked = True
                        else:
                            user = db.get(User, user_id)
                            if user and user.status == UserStatus.ACTIVE:
                                request.state.user = user
                                request.state.session_jti = token_jti
                                request.state.is_authenticated = True
            except Exception as e:
                logger.debug(f"Auth middleware token parse note: {e}")

        if not _is_public(request.url.path, request.method):
            if not token:
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Authentication required for this resource",
                            "details": {"scheme": "Bearer"},
                        },
                    },
                )
            if not request.state.is_authenticated:
                details = {"scheme": "Bearer"}
                if session_revoked:
                    details["reason"] = "session_revoked"
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error": {
                            "code": "INVALID_CREDENTIALS",
                            "message": "Invalid, expired, or revoked authentication credentials",
                            "details": details,
                        },
                    },
                )

        response = await call_next(request)
        return response
