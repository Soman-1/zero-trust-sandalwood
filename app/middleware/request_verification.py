"""Zero Trust request verification and anti-replay defense middleware."""

import time
import uuid
from datetime import datetime, timezone
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.anti_replay import anti_replay_validator


def client_rate_identity(request: Request) -> str:
    """Identity for rate limits. Ignores client-supplied device headers."""
    client = request.client
    return client.host if client else "UNKNOWN"


class ZeroTrustRequestVerificationMiddleware(BaseHTTPMiddleware):
    """
    Zero Trust Verification Middleware:
    1. Enforces anti-replay timestamp & nonce validation on signed payloads (X-Timestamp, X-Nonce).
    2. Attaches security and performance headers (X-Process-Time, X-Zero-Trust-Framework).
    3. Detects and logs anomalous request patterns.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 1. Anti-Replay Timestamp & Nonce Verification
        timestamp_header = request.headers.get("X-Timestamp")
        nonce_header = request.headers.get("X-Nonce")

        # Rate-limit and replay buckets use the connection address.
        # X-Device-ID is client-supplied and is not an identity until the device key is checked.
        caller_id = client_rate_identity(request)
        ingest_path = request.url.path.startswith("/api/v1/measurements/ingest")
        from app.core.runtime import require_ingest_freshness

        if ingest_path and require_ingest_freshness and request.method == "POST":
            if not timestamp_header or not nonce_header:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": {
                            "code": "REPLAY_HEADERS_REQUIRED",
                            "message": "Device ingest requires X-Timestamp and X-Nonce headers",
                            "details": {"required_headers": ["X-Timestamp", "X-Nonce"]},
                        },
                    },
                )

        if timestamp_header:
            try:
                try:
                    req_ts = float(timestamp_header)
                except ValueError:
                    dt = datetime.fromisoformat(timestamp_header.replace("Z", "+00:00"))
                    req_ts = dt.timestamp()
            except Exception as e:
                logger.debug(f"Invalid timestamp header format: {e}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": {
                            "code": "INVALID_TIMESTAMP",
                            "message": "X-Timestamp is not a valid epoch or ISO-8601 timestamp",
                            "details": {},
                        },
                    },
                )

            is_valid, err_msg = anti_replay_validator.validate_request(
                request_timestamp=req_ts,
                nonce=nonce_header,
                caller_id=caller_id,
            )
            if not is_valid:
                is_dos = "Denial-of-Service" in (err_msg or "")
                is_skew = "Clock skew" in (err_msg or "")
                error_code = "DOS_ATTACK_DETECTED" if is_dos else ("CLOCK_SKEW_EXCEEDED" if is_skew else "REPLAY_ATTACK_DETECTED")
                status_code = 429 if is_dos else 400
                return JSONResponse(
                    status_code=status_code,
                    content={
                        "success": False,
                        "error": {
                            "code": error_code,
                            "message": err_msg or "Anti-replay validation failed",
                            "details": {},
                        },
                    },
                )
        else:
            limited, err_msg = anti_replay_validator.check_rate(caller_id)
            if not limited:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "DOS_ATTACK_DETECTED",
                            "message": err_msg or "Request rate exceeded",
                            "details": {},
                        },
                    },
                )

        # 2. Process Request with Tracing ID
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        response = await call_next(request)

        # 3. Attach Security, Tracing, and Diagnostic Headers
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time_ms}ms"
        response.headers["X-Zero-Trust-Framework"] = "Enforced"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        return response
