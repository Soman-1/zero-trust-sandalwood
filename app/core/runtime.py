"""Process-local switches that must not be enabled by environment variables.

Tests flip `privileged_self_register` so existing fixtures can create admins.
Production never sets this; public registration stays viewer-only.
"""

privileged_self_register: bool = False
require_ingest_freshness: bool = True
# Fixtures issue bursts well above the 60 req/s limit. Tests flip this so the
# suite is not rate-limited; the DoS test flips it back to assert enforcement.
exempt_testclient_rate_limit: bool = False
