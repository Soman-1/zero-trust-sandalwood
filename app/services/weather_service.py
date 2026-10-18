"""Live Real-World Meteorological and Soil Ingestion Service using Open-Meteo Public API."""

from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from app.core.logging import logger


class WeatherFetchError(RuntimeError):
    """Raised when live Open-Meteo data cannot be fetched or fails validation."""


class RealWorldWeatherService:
    """Fetches live microclimate telemetry from Open-Meteo. Failures raise — no synthetic fill-ins."""

    OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
    _cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    CACHE_TTL_SECONDS = 300.0
    MAX_CACHE_ENTRIES = 500
    REQUEST_TIMEOUT_SECONDS = 8.0

    # Variables requested from Open-Meteo `current`
    _CURRENT_VARS = (
        "temperature_2m",
        "relative_humidity_2m",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "cloud_cover",
        "soil_temperature_0cm",
        "soil_moisture_0_to_1cm",
        "soil_moisture_1_to_3cm",
        "soil_moisture_3_to_9cm",
        "soil_moisture_9_to_27cm",
        "direct_normal_irradiance",
        "is_day",
    )

    _REQUIRED_CURRENT = (
        "time",
        "temperature_2m",
        "relative_humidity_2m",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "cloud_cover",
        "soil_temperature_0cm",
        "soil_moisture_0_to_1cm",
        "soil_moisture_9_to_27cm",
        "direct_normal_irradiance",
        "is_day",
    )

    @classmethod
    def get_live_microclimate(cls, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch live temperature, humidity, soil moisture, wind, and elevation.

        Raises WeatherFetchError on network/HTTP/parse/validation failure.
        Successful responses are cached for CACHE_TTL_SECONDS.
        """
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise WeatherFetchError(
                f"Invalid coordinates: latitude={latitude}, longitude={longitude}"
            )

        cache_key = f"{round(latitude, 2)}:{round(longitude, 2)}"
        now_ts = time.time()

        if cache_key in cls._cache:
            cached_time, cached_result = cls._cache[cache_key]
            if now_ts - cached_time < cls.CACHE_TTL_SECONDS:
                return cached_result

        query = urllib.parse.urlencode(
            {
                "latitude": f"{round(latitude, 4)}",
                "longitude": f"{round(longitude, 4)}",
                "current": ",".join(cls._CURRENT_VARS),
                "timezone": "auto",
            }
        )
        # Elevation is returned by Open-Meteo on every forecast response; do NOT pass
        # elevation=true — that param is invalid for /v1/forecast and returns HTTP 400.
        full_url = f"{cls.OPEN_METEO_BASE_URL}?{query}"

        req = urllib.request.Request(
            full_url,
            headers={
                "User-Agent": "ZeroTrustAgroforestryResearch/1.0 (sandalwood-gis-radar)",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=cls.REQUEST_TIMEOUT_SECONDS) as response:
                status = getattr(response, "status", None) or response.getcode()
                body = response.read().decode("utf-8")
                if status != 200:
                    raise WeatherFetchError(
                        f"Open-Meteo HTTP {status} for ({latitude}, {longitude}): {body[:300]}"
                    )
                raw_data = json.loads(body)
        except WeatherFetchError:
            raise
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")[:300]
            logger.error(
                f"Open-Meteo HTTP {err.code} for ({latitude}, {longitude}): {detail}"
            )
            raise WeatherFetchError(
                f"Open-Meteo HTTP {err.code}: {detail}"
            ) from err
        except urllib.error.URLError as err:
            logger.error(f"Open-Meteo network error for ({latitude}, {longitude}): {err}")
            raise WeatherFetchError(f"Open-Meteo network error: {err}") from err
        except TimeoutError as err:
            logger.error(f"Open-Meteo timeout for ({latitude}, {longitude})")
            raise WeatherFetchError("Open-Meteo request timed out") from err
        except json.JSONDecodeError as err:
            logger.error(f"Open-Meteo returned invalid JSON for ({latitude}, {longitude})")
            raise WeatherFetchError("Open-Meteo returned invalid JSON") from err
        except Exception as err:
            logger.error(
                f"Open-Meteo unexpected failure for ({latitude}, {longitude}): {err}"
            )
            raise WeatherFetchError(f"Open-Meteo request failed: {err}") from err

        if isinstance(raw_data, dict) and raw_data.get("error"):
            raise WeatherFetchError(
                f"Open-Meteo error: {raw_data.get('reason', 'unknown')}"
            )

        result = cls._parse_live_weather(latitude, longitude, raw_data)
        cls._cache[cache_key] = (now_ts, result)
        if len(cls._cache) > cls.MAX_CACHE_ENTRIES:
            # Evict oldest entries
            oldest = sorted(cls._cache.items(), key=lambda kv: kv[1][0])
            for key, _ in oldest[: max(1, len(cls._cache) - cls.MAX_CACHE_ENTRIES)]:
                cls._cache.pop(key, None)
        return result

    @classmethod
    def _require_number(
        cls,
        current: Dict[str, Any],
        key: str,
        *,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
    ) -> float:
        if key not in current or current[key] is None:
            raise WeatherFetchError(f"Open-Meteo response missing required field: {key}")
        try:
            value = float(current[key])
        except (TypeError, ValueError) as err:
            raise WeatherFetchError(
                f"Open-Meteo field '{key}' is not numeric: {current[key]!r}"
            ) from err
        if minimum is not None and value < minimum:
            raise WeatherFetchError(
                f"Open-Meteo field '{key}'={value} below minimum {minimum}"
            )
        if maximum is not None and value > maximum:
            raise WeatherFetchError(
                f"Open-Meteo field '{key}'={value} above maximum {maximum}"
            )
        return value

    @classmethod
    def _observation_utc(cls, raw_data: Dict[str, Any], current: Dict[str, Any]) -> datetime:
        """Convert Open-Meteo local observation time + utc_offset to aware UTC."""
        time_raw = current.get("time")
        if not time_raw:
            raise WeatherFetchError("Open-Meteo response missing current.time")

        try:
            local_naive = datetime.fromisoformat(str(time_raw))
        except ValueError as err:
            raise WeatherFetchError(
                f"Open-Meteo current.time is not ISO-8601: {time_raw!r}"
            ) from err

        offset_seconds = raw_data.get("utc_offset_seconds")
        if offset_seconds is None:
            # timezone=auto should always provide this; refuse to invent UTC.
            raise WeatherFetchError(
                "Open-Meteo response missing utc_offset_seconds; cannot normalize timestamp"
            )
        try:
            offset = int(offset_seconds)
        except (TypeError, ValueError) as err:
            raise WeatherFetchError(
                f"Invalid utc_offset_seconds: {offset_seconds!r}"
            ) from err

        return (local_naive - timedelta(seconds=offset)).replace(tzinfo=timezone.utc)

    @classmethod
    def _parse_live_weather(
        cls, latitude: float, longitude: float, raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not isinstance(raw_data, dict) or "current" not in raw_data:
            raise WeatherFetchError("Open-Meteo response missing 'current' block")

        current = raw_data["current"]
        if not isinstance(current, dict):
            raise WeatherFetchError("Open-Meteo 'current' block is not an object")

        missing = [k for k in cls._REQUIRED_CURRENT if k not in current or current[k] is None]
        if missing:
            raise WeatherFetchError(
                f"Open-Meteo response missing required fields: {', '.join(missing)}"
            )

        elevation = raw_data.get("elevation")
        if elevation is None:
            raise WeatherFetchError("Open-Meteo response missing elevation")
        try:
            elevation = float(elevation)
        except (TypeError, ValueError) as err:
            raise WeatherFetchError(f"Invalid elevation: {elevation!r}") from err
        if not (-500.0 <= elevation <= 9000.0):
            raise WeatherFetchError(f"Elevation out of range: {elevation}")

        temp = cls._require_number(current, "temperature_2m", minimum=-90.0, maximum=60.0)
        humidity = cls._require_number(
            current, "relative_humidity_2m", minimum=0.0, maximum=100.0
        )
        pressure = cls._require_number(
            current, "surface_pressure", minimum=300.0, maximum=1100.0
        )
        # Open-Meteo default unit for wind_speed_10m is km/h
        wind_speed = cls._require_number(
            current, "wind_speed_10m", minimum=0.0, maximum=400.0
        )
        wind_dir = cls._require_number(
            current, "wind_direction_10m", minimum=0.0, maximum=360.0
        )
        cloud_cover = cls._require_number(current, "cloud_cover", minimum=0.0, maximum=100.0)
        soil_temp = cls._require_number(
            current, "soil_temperature_0cm", minimum=-90.0, maximum=70.0
        )
        # volumetric m³/m³ → percent
        sm_surf_raw = cls._require_number(
            current, "soil_moisture_0_to_1cm", minimum=0.0, maximum=1.0
        )
        sm_root_raw = cls._require_number(
            current, "soil_moisture_9_to_27cm", minimum=0.0, maximum=1.0
        )
        soil_moisture_surface = round(sm_surf_raw * 100, 1)
        soil_moisture_root = round(sm_root_raw * 100, 1)

        solar_rad = cls._require_number(
            current, "direct_normal_irradiance", minimum=0.0, maximum=1500.0
        )
        is_day = bool(int(current["is_day"]))

        observation_utc = cls._observation_utc(raw_data, current)
        fetched_at_utc = datetime.now(timezone.utc)

        # Vapor Pressure Deficit (VPD) in kPa — Magnus formula
        es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
        ea = es * (humidity / 100.0)
        vpd = round(es - ea, 2)

        temp_score = 100 - min(abs(temp - 28.0) * 5, 50)
        soil_score = 100 - min(abs(soil_moisture_root - 28.0) * 4, 50)
        rh_score = 100 - min(abs(humidity - 60.0) * 3, 50)
        vpd_score = 100 if 0.8 <= vpd <= 2.2 else max(0, 100 - abs(vpd - 1.5) * 40)
        suitability_score = round(
            (temp_score * 0.3 + soil_score * 0.3 + rh_score * 0.2 + vpd_score * 0.2), 1
        )

        if suitability_score >= 80:
            growth_zone = "OPTIMAL_GROWTH"
            canopy_stress = "NOMINAL"
        elif suitability_score >= 60:
            growth_zone = "FAVORABLE"
            canopy_stress = "MILD_WATER_STRESS" if soil_moisture_root < 18 else "MODERATE"
        else:
            growth_zone = "STRESSED_ZONE"
            canopy_stress = "SEVERE_CLIMATIC_STRESS"

        source = "Open-Meteo High-Resolution Real-Time Model"
        obs_iso = observation_utc.isoformat()
        canonical_str = (
            f"LAT={latitude:.4f}|LON={longitude:.4f}|TEMP={temp:.1f}|"
            f"RH={humidity:.1f}|SM={soil_moisture_surface:.1f}|ELEV={elevation:.1f}|TIME={obs_iso}"
        )
        integrity_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        return {
            "latitude": round(latitude, 5),
            "longitude": round(longitude, 5),
            "elevation_meters": elevation,
            "temperature_celsius": temp,
            "relative_humidity_percent": humidity,
            "soil_temperature_celsius": soil_temp,
            "soil_moisture_surface_percent": soil_moisture_surface,
            "soil_moisture_root_percent": soil_moisture_root,
            "surface_pressure_hpa": pressure,
            "wind_speed_kmh": wind_speed,
            "wind_direction_deg": wind_dir,
            "cloud_cover_percent": cloud_cover,
            "solar_irradiance_wm2": solar_rad,
            "is_day": is_day,
            "vapor_pressure_deficit_kpa": vpd,
            "sandalwood_suitability_score": suitability_score,
            "growth_zone_classification": growth_zone,
            "canopy_stress_status": canopy_stress,
            "data_source": source,
            # Observation time from Open-Meteo (UTC), not wall-clock fetch time
            "timestamp": obs_iso,
            "fetched_at": fetched_at_utc.isoformat(),
            "observation_timezone": raw_data.get("timezone"),
            "integrity_hash": integrity_hash,
        }
