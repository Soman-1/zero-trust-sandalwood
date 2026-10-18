"""Cryptographic data integrity, canonical serialization, and tamper detection module."""

import json
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple


def canonicalize_payload(data: Dict[str, Any]) -> str:
    """
    Deterministic canonical JSON serialization:
    - Sorts all keys alphabetically.
    - Eliminates non-essential whitespace.
    - Encodes strings consistently in UTF-8.
    """
    def default_serializer(obj):
        if isinstance(obj, datetime):
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=timezone.utc)
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} is not JSON serializable")

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        default=default_serializer,
        ensure_ascii=False,
    )


def compute_sha256(canonical_string: str) -> str:
    """Compute SHA-256 cryptographic hash of a canonical string."""
    return hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()


def seal_canonical(canonical_string: str) -> str:
    """Keyed seal for new rows. Falls back to plain SHA-256 when no encryption key is set."""
    from app.core.config import settings

    key = (settings.ENCRYPTION_KEY or "").strip().encode("utf-8")
    if not key:
        return compute_sha256(canonical_string)
    return hmac.new(key, canonical_string.encode("utf-8"), hashlib.sha256).hexdigest()


def canonical_matches_stored(stored: Optional[str], canonical_string: str) -> bool:
    """Accept the current keyed seal and older unkeyed SHA-256 rows."""
    if not stored:
        return False
    legacy = compute_sha256(canonical_string)
    if hmac.compare_digest(stored, legacy):
        return True
    return hmac.compare_digest(stored, seal_canonical(canonical_string))


def measurement_canonical(
    region_id: Optional[int],
    tree_id: Optional[int],
    device_id: Optional[int],
    latitude: float,
    longitude: float,
    temperature: float,
    humidity: float,
    soil_moisture: float,
    recorded_at: datetime,
    additional_metrics: Optional[Dict[str, Any]] = None,
    altitude: Optional[float] = None,
) -> str:
    """Canonical JSON for a measurement, shared by new seals and legacy checks."""
    if isinstance(recorded_at, datetime):
        if recorded_at.tzinfo is None:
            norm_time = recorded_at.replace(tzinfo=timezone.utc).isoformat()
        else:
            norm_time = recorded_at.astimezone(timezone.utc).isoformat()
    else:
        norm_time = str(recorded_at)

    payload: Dict[str, Any] = {
        "region_id": region_id,
        "tree_id": tree_id,
        "device_id": device_id,
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "altitude": None if altitude is None else round(float(altitude), 2),
        "temperature": round(float(temperature), 2),
        "humidity": round(float(humidity), 2),
        "soil_moisture": round(float(soil_moisture), 2),
        "recorded_at": norm_time,
        "additional_metrics": additional_metrics or {},
    }
    return canonicalize_payload(payload)


def compute_measurement_integrity_hash(
    region_id: Optional[int],
    tree_id: Optional[int],
    device_id: Optional[int],
    latitude: float,
    longitude: float,
    temperature: float,
    humidity: float,
    soil_moisture: float,
    recorded_at: datetime,
    additional_metrics: Optional[Dict[str, Any]] = None,
    altitude: Optional[float] = None,
) -> str:
    """Keyed integrity seal for a measurement. Older rows used plain SHA-256."""
    canonical_str = measurement_canonical(
        region_id=region_id,
        tree_id=tree_id,
        device_id=device_id,
        latitude=latitude,
        longitude=longitude,
        temperature=temperature,
        humidity=humidity,
        soil_moisture=soil_moisture,
        recorded_at=recorded_at,
        additional_metrics=additional_metrics,
        altitude=altitude,
    )
    return seal_canonical(canonical_str)


def verify_measurement_integrity(measurement: Any) -> Tuple[bool, Optional[str], str]:
    """
    Recalculates the seal from stored fields.
    Accepts the current keyed seal and older unkeyed SHA-256 rows.
    Returns: (is_valid, stored_hash, computed_hash)
    """
    stored_hash = measurement.integrity_hash
    canonical_str = measurement_canonical(
        region_id=measurement.region_id,
        tree_id=measurement.tree_id,
        device_id=measurement.device_id,
        latitude=measurement.latitude,
        longitude=measurement.longitude,
        temperature=measurement.temperature,
        humidity=measurement.humidity,
        soil_moisture=measurement.soil_moisture,
        recorded_at=measurement.recorded_at,
        additional_metrics=measurement.additional_metrics,
        altitude=getattr(measurement, "altitude", None),
    )
    computed_hash = seal_canonical(canonical_str)
    if not stored_hash:
        return False, None, computed_hash
    return canonical_matches_stored(stored_hash, canonical_str), stored_hash, computed_hash
