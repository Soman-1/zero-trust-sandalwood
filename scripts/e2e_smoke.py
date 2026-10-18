"""End-to-end smoke checks against a running API (direct or Vite proxy)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASES = sys.argv[1:] or ["http://127.0.0.1:8000", "http://127.0.0.1:3000"]
PREFIX = "/api/v1"

results: list[tuple[str, str, str]] = []


def call(base: str, method: str, path: str, token: str | None = None, body: dict | None = None, timeout: float = 30):
    url = f"{base}{PREFIX}{path}"
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "X-Timestamp": str(time.time())}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            elapsed = (time.perf_counter() - started) * 1000
            payload = json.loads(raw) if raw else None
            return resp.status, payload, elapsed, None
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - started) * 1000
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload, elapsed, str(exc)
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return 0, None, elapsed, f"{type(exc).__name__}: {exc}"


def record(base: str, name: str, ok: bool, detail: str):
    status = "PASS" if ok else "FAIL"
    results.append((base, name, f"{status} {detail}"))
    print(f"[{status}] {base} {name}: {detail}")


def check(base: str):
    print(f"\n=== {base} ===")
    status, err = 0, ""
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{base}/health"), timeout=20) as resp:
            status = resp.status
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
    record(base, "health", status == 200, f"status={status} {err}")

    status, payload, ms, err = call(
        base, "POST", "/auth/login", body={"username_or_email": "admin", "password": "wrong-password"}
    )
    record(base, "login invalid", status in (400, 401, 403), f"status={status} {ms:.0f}ms")

    status, payload, ms, err = call(
        base, "POST", "/auth/login", body={"username_or_email": "admin", "password": "Admin12345!"}
    )
    token = None
    if status == 200 and isinstance(payload, dict):
        token = payload.get("access_token")
    record(base, "login admin", status == 200 and bool(token), f"status={status} {ms:.0f}ms {err or ''}")
    if not token:
        return

    checks = [
        ("GET", "/auth/me", None, 200),
        ("GET", "/dashboard/overview", None, 200),
        ("GET", "/dashboard/map-layer", None, 200),
        ("GET", "/trees?limit=50", None, 200),
        ("GET", "/regions", None, 200),
        ("GET", "/devices", None, 200),
        ("GET", "/alerts", None, 200),
        ("GET", "/audit/logs?limit=10", None, 200),
        ("GET", "/global-trees?limit=5", None, 200),
        ("GET", "/detections?limit=5", None, 200),
        ("GET", "/satellite/aerial-presets", None, 200),
        ("GET", "/alerts/summary/stats", None, 200),
        ("GET", "/audit/verify-chain", None, 200),
        ("GET", "/measurements?limit=5", None, 200),
        ("GET", "/anomaly/model-status", None, 200),
        ("GET", "/dashboard/timeseries?hours=24", None, 200),
        ("GET", "/street-view/presets", None, 200),
    ]
    for method, path, body, expect in checks:
        status, payload, ms, err = call(base, method, path, token=token, body=body, timeout=60)
        record(base, path, status == expect, f"status={status} expected={expect} {ms:.0f}ms {err or ''}")
        if status == 0:
            print("  error:", err)

    # tree create + invalid GPS + delete
    status, regions, _, _ = call(base, "GET", "/regions", token=token)
    region_id = None
    if status == 200 and isinstance(regions, list) and regions:
        region_id = regions[0].get("id") or regions[0].get("region_id")
    uid = f"KA-{int(time.time()) % 100000:05d}"
    record(
        base,
        "regions optional",
        status == 200 and isinstance(regions, list),
        f"count={len(regions) if isinstance(regions, list) else 'n/a'}",
    )
    body = {
        "tree_uid": uid,
        "species": "Santalum album",
        "latitude": 13.9355,
        "longitude": 75.5652,
    }
    if region_id is not None:
        body["region_id"] = region_id
    status, payload, ms, err = call(base, "POST", "/trees", token=token, body=body)
    record(base, "register tree", status in (200, 201), f"status={status} {ms:.0f}ms {payload if status >= 400 else ''}")
    status, payload, ms, err = call(
        base,
        "POST",
        "/trees",
        token=token,
        body={"tree_uid": "BAD", "latitude": 91, "longitude": 75.5652},
    )
    record(base, "reject invalid tree", status in (400, 422), f"status={status}")
    status, payload, ms, err = call(base, "DELETE", f"/trees/{uid}/record", token=token)
    record(base, "delete tree", status == 200, f"status={status} {payload}")
    status, _, _, _ = call(base, "GET", f"/trees/{uid}", token=token)
    record(base, "deleted tree gone", status == 404, f"status={status}")

    status, payload, ms, err = call(base, "GET", "/trees", token="not-a-token")
    record(base, "reject bad token", status in (401, 403), f"status={status}")


def main():
    for base in BASES:
        check(base)
    failed = [r for r in results if "FAIL" in r[2]]
    print(f"\n=== SUMMARY {len(results) - len(failed)} passed, {len(failed)} failed ===")
    for base, name, detail in failed:
        print(f"  FAIL {base} {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
