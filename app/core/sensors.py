"""Sensor validation module: physical range limits and timestamp plausibility checks."""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from app.core.errors import AppException

# Plausible physical operating boundaries for agroforestry sensors
TEMP_MIN_CELSIUS = -10.0
TEMP_MAX_CELSIUS = 65.0

HUMIDITY_MIN_PCT = 0.0
HUMIDITY_MAX_PCT = 100.0

SOIL_MOISTURE_MIN_PCT = 0.0
SOIL_MOISTURE_MAX_PCT = 100.0

# Allow a maximum clock drift of 10 minutes for future timestamps
MAX_FUTURE_DRIFT_MINUTES = 10


def validate_sensor_readings(temperature: float, humidity: float, soil_moisture: float) -> None:
    """
    Validate that environmental measurements fall within physically plausible terrestrial limits.
    Rejects impossible or corrupted sensor hardware outputs.
    """
    errors: Dict[str, Any] = {}

    if temperature is None or not (TEMP_MIN_CELSIUS <= temperature <= TEMP_MAX_CELSIUS):
        errors["temperature"] = {
            "value": temperature,
            "allowed_range": [TEMP_MIN_CELSIUS, TEMP_MAX_CELSIUS],
            "unit": "°C",
        }

    if humidity is None or not (HUMIDITY_MIN_PCT <= humidity <= HUMIDITY_MAX_PCT):
        errors["humidity"] = {
            "value": humidity,
            "allowed_range": [HUMIDITY_MIN_PCT, HUMIDITY_MAX_PCT],
            "unit": "%",
        }

    if soil_moisture is None or not (SOIL_MOISTURE_MIN_PCT <= soil_moisture <= SOIL_MOISTURE_MAX_PCT):
        errors["soil_moisture"] = {
            "value": soil_moisture,
            "allowed_range": [SOIL_MOISTURE_MIN_PCT, SOIL_MOISTURE_MAX_PCT],
            "unit": "%",
        }

    if errors:
        raise AppException(
            message="Environmental readings outside plausible physical operational limits",
            status_code=400,
            error_code="SENSOR_OUT_OF_BOUNDS",
            details=errors,
        )


def validate_recorded_timestamp(recorded_at: datetime) -> datetime:
    """
    Validate that recorded_at is plausible: not too far in the future and not stale.
    Normalizes offset-naive datetimes to UTC.
    """
    from app.core.config import settings

    if recorded_at is None:
        return datetime.now(timezone.utc)

    # Normalize to UTC
    if recorded_at.tzinfo is None:
        normalized = recorded_at.replace(tzinfo=timezone.utc)
    else:
        normalized = recorded_at.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    max_allowed = now + timedelta(minutes=MAX_FUTURE_DRIFT_MINUTES)

    if normalized > max_allowed:
        raise AppException(
            message="Sensor recording timestamp cannot be in the future",
            status_code=400,
            error_code="FUTURE_TIMESTAMP_REJECTED",
            details={
                "recorded_at": normalized.isoformat(),
                "server_time": now.isoformat(),
            },
        )

    max_age_hours = int(getattr(settings, "MAX_MEASUREMENT_AGE_HOURS", 72) or 72)
    min_allowed = now - timedelta(hours=max_age_hours)
    if normalized < min_allowed:
        raise AppException(
            message="Sensor recording timestamp is too old",
            status_code=400,
            error_code="STALE_TIMESTAMP_REJECTED",
            details={
                "recorded_at": normalized.isoformat(),
                "server_time": now.isoformat(),
                "max_age_hours": max_age_hours,
            },
        )

    return normalized
