"""Zero Trust Anti-Replay Protection and Nonce Validation Engine."""

import time
import threading
from typing import Dict, Set, Tuple, Optional
from app.core.config import settings
from app.core.logging import logger


class AntiReplayValidator:
    """
    Thread-safe Anti-Replay Validator:
    1. Enforces timestamp tolerance window (rejects stale or future requests beyond clock skew).
    2. Validates unique nonces to prevent payload replay attacks.
    3. Periodically evicts expired nonces to maintain bounded memory footprint.
    """

    def __init__(
        self,
        max_clock_skew_seconds: Optional[int] = None,
        max_entries: int = 10000,
        max_requests_per_second: int = 60,
    ):
        self.max_clock_skew = max_clock_skew_seconds or settings.ZERO_TRUST_MAX_CLOCK_SKEW_SECONDS
        self.max_entries = max_entries
        self.max_requests_per_second = max_requests_per_second
        self._seen_nonces: Dict[str, float] = {}  # nonce -> expiry_time
        self._caller_history: Dict[str, list] = {}  # caller_id -> list of timestamps
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
        self._redis_client = None

        env = (getattr(settings, "APP_ENV", "") or "").lower()
        redis_url = getattr(settings, "REDIS_URL", None)
        if redis_url:
            try:
                import redis
                client = redis.from_url(redis_url, socket_timeout=1)
                client.ping()
                self._redis_client = client
                logger.info("AntiReplayValidator connected to Redis for distributed nonce deduplication.")
            except Exception as e:
                self._redis_client = None
                if env in {"production", "staging"}:
                    raise RuntimeError(
                        f"REDIS_URL is configured but unreachable in {env}: {e}"
                    ) from e
                logger.warning(f"Redis not available ({e}), using in-memory anti-replay ledger.")
        elif env in {"production", "staging"}:
            raise RuntimeError("REDIS_URL is required for anti-replay when APP_ENV is production/staging.")

    @staticmethod
    def _rate_limit_exempt(rate_key: str) -> bool:
        """Only the in-process test client is exemptible, and never via env vars."""
        from app.core import runtime

        return rate_key == "testclient" and runtime.exempt_testclient_rate_limit

    def validate_request(
        self,
        request_timestamp: float,
        nonce: Optional[str] = None,
        caller_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate request freshness, nonce uniqueness, and caller request frequency.
        Returns: (is_valid: bool, error_message: Optional[str])
        """
        current_time = time.time()
        skew = abs(current_time - request_timestamp)

        # 1. Clock skew check
        if skew > self.max_clock_skew:
            logger.warning(
                f"Anti-Replay Rejection: Caller {caller_id or 'UNKNOWN'} clock skew {round(skew, 2)}s "
                f"exceeds tolerance ({self.max_clock_skew}s)"
            )
            return False, f"Clock skew {round(skew, 1)}s exceeds allowed tolerance window ({self.max_clock_skew}s)"

        # 2. Nonce check if supplied
        if nonce:
            nonce_checked_redis = False
            if self._redis_client:
                try:
                    was_set = self._redis_client.set(f"nonce:{nonce}", "1", ex=int(self.max_clock_skew), nx=True)
                    nonce_checked_redis = True
                    if not was_set:
                        logger.warning(f"Anti-Replay Rejection: Replayed nonce detected via Redis: '{nonce}' from {caller_id}")
                        return False, f"Replay attack detected: Nonce '{nonce}' has already been processed"
                except Exception as e:
                    logger.debug(f"Redis nonce check fallback: {e}")

            if not nonce_checked_redis:
                with self._lock:
                    self._cleanup_expired(current_time)

                    if nonce in self._seen_nonces:
                        logger.warning(f"Anti-Replay Rejection: Replayed nonce detected: '{nonce}' from {caller_id}")
                        return False, f"Replay attack detected: Nonce '{nonce}' has already been processed"

                    # Store nonce with expiry at timestamp + max_clock_skew
                    self._seen_nonces[nonce] = current_time + self.max_clock_skew

        # 3. Behavioral Rate Anomaly / DoS Flood Detection
        # Always rate-limit; map missing identity to a shared anonymous bucket.
        rate_key = caller_id if caller_id else "anonymous"
        if self._rate_limit_exempt(rate_key):
            return True, None
        with self._lock:
            history = self._caller_history.setdefault(rate_key, [])
            window_start = current_time - 1.0
            history = [t for t in history if t >= window_start]
            history.append(current_time)
            self._caller_history[rate_key] = history

            if len(history) > self.max_requests_per_second:
                logger.warning(
                    f"Zero Trust Behavioral Alert: Possible Denial-of-Service (DoS) attack from caller '{rate_key}' "
                    f"({len(history)} req/s exceeds limit {self.max_requests_per_second})"
                )
                return False, (
                    f"Possible Denial-of-Service (DoS) attack detected: request rate "
                    f"({len(history)} req/s) exceeds threshold ({self.max_requests_per_second})"
                )

        return True, None

    def check_rate(self, caller_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Apply the per-caller rate limit even when no timestamp header is present."""
        rate_key = caller_id if caller_id else "anonymous"
        if self._rate_limit_exempt(rate_key):
            return True, None
        current_time = time.time()
        with self._lock:
            history = self._caller_history.setdefault(rate_key, [])
            window_start = current_time - 1.0
            history = [t for t in history if t >= window_start]
            history.append(current_time)
            self._caller_history[rate_key] = history
            if len(history) > self.max_requests_per_second:
                return False, (
                    f"Possible Denial-of-Service (DoS) attack detected: request rate "
                    f"({len(history)} req/s) exceeds threshold ({self.max_requests_per_second})"
                )
        return True, None

    def _cleanup_expired(self, current_time: float) -> None:
        """Evict nonces older than their expiry threshold."""
        if current_time - self._last_cleanup < 60 and len(self._seen_nonces) < self.max_entries:
            return

        expired_keys = [k for k, exp in self._seen_nonces.items() if exp < current_time]
        for k in expired_keys:
            del self._seen_nonces[k]

        expired_callers = [
            cid for cid, times in self._caller_history.items()
            if not times or times[-1] < current_time - 10.0
        ]
        for cid in expired_callers:
            del self._caller_history[cid]

        self._last_cleanup = current_time


# Singleton instance
anti_replay_validator = AntiReplayValidator()
