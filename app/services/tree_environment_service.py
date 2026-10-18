"""Capture and store live area weather for registered sandalwood trees (Open-Meteo)."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.core.integrity import compute_measurement_integrity_hash
from app.database.models.tree import Tree, TreeStatus
from app.database.models.environmental_measurement import EnvironmentalMeasurement
from app.services.weather_service import RealWorldWeatherService, WeatherFetchError


class TreeEnvironmentService:
    """Links each Tree ID to real-time surrounding environmental observations."""

    @staticmethod
    def _parse_observation_time(weather: Dict[str, Any]) -> datetime:
        """Prefer Open-Meteo observation UTC; fall back to fetch wall-clock only if needed."""
        for key in ("timestamp", "fetched_at"):
            raw = weather.get(key)
            if not raw:
                continue
            try:
                parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                continue
        return datetime.now(timezone.utc)

    @staticmethod
    def capture_live_environment_for_tree(
        db: Session,
        tree: Tree,
        *,
        run_anomaly_check: bool = False,
        weather: Optional[Dict[str, Any]] = None,
    ) -> Optional[EnvironmentalMeasurement]:
        """
        Fetch live weather for the tree GPS and persist a measurement row
        linked to that tree_id (temperature, humidity, soil moisture, extras).

        Returns None if Open-Meteo is unreachable or returns invalid data
        (does not invent synthetic readings).
        """
        if not settings.ENV_REFRESH_ENABLED:
            return None

        if weather is None:
            try:
                weather = RealWorldWeatherService.get_live_microclimate(
                    latitude=tree.latitude,
                    longitude=tree.longitude,
                )
            except WeatherFetchError as exc:
                logger.warning(
                    f"Live weather fetch failed for tree '{tree.tree_uid}': {exc}"
                )
                return None

        recorded_at = TreeEnvironmentService._parse_observation_time(weather)
        temperature = float(weather["temperature_celsius"])
        humidity = float(weather["relative_humidity_percent"])
        soil_moisture = float(weather["soil_moisture_root_percent"])

        additional_metrics: Dict[str, Any] = {
            "source": "OPEN_METEO",
            "data_source_label": weather.get("data_source"),
            "elevation_meters": weather.get("elevation_meters"),
            "soil_temperature_celsius": weather.get("soil_temperature_celsius"),
            "soil_moisture_surface_percent": weather.get("soil_moisture_surface_percent"),
            "surface_pressure_hpa": weather.get("surface_pressure_hpa"),
            "wind_speed_kmh": weather.get("wind_speed_kmh"),
            "wind_direction_deg": weather.get("wind_direction_deg"),
            "cloud_cover_percent": weather.get("cloud_cover_percent"),
            "vapor_pressure_deficit_kpa": weather.get("vapor_pressure_deficit_kpa"),
            "sandalwood_suitability_score": weather.get("sandalwood_suitability_score"),
            "growth_zone_classification": weather.get("growth_zone_classification"),
            "canopy_stress_status": weather.get("canopy_stress_status"),
            "weather_integrity_hash": weather.get("integrity_hash"),
            "observation_timezone": weather.get("observation_timezone"),
            "fetched_at": weather.get("fetched_at"),
            "observation_time_utc": weather.get("timestamp"),
        }

        altitude = weather.get("elevation_meters")
        if altitude is None:
            altitude = tree.altitude

        is_anomaly = False
        anomaly_score = None
        anomaly_details = None
        if run_anomaly_check:
            try:
                from app.ai.model import detector
                is_anomaly, anomaly_score, anomaly_details = detector.predict_anomaly(
                    temperature=temperature,
                    humidity=humidity,
                    soil_moisture=soil_moisture,
                    additional_metrics=additional_metrics,
                )
            except Exception as exc:
                logger.debug(f"Anomaly check skipped for '{tree.tree_uid}': {exc}")

        integrity_hash = compute_measurement_integrity_hash(
            region_id=tree.region_id,
            tree_id=tree.id,
            device_id=None,
            latitude=tree.latitude,
            longitude=tree.longitude,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            recorded_at=recorded_at,
            additional_metrics=additional_metrics,
        )

        measurement = EnvironmentalMeasurement(
            region_id=tree.region_id,
            tree_id=tree.id,
            device_id=None,
            latitude=tree.latitude,
            longitude=tree.longitude,
            altitude=altitude,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            additional_metrics=additional_metrics,
            integrity_hash=integrity_hash,
            is_tampered=False,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            anomaly_details=anomaly_details,
            recorded_at=recorded_at,
        )
        db.add(measurement)
        db.commit()
        db.refresh(measurement)

        logger.info(
            f"Stored live environment for '{tree.tree_uid}': "
            f"T={temperature}°C RH={humidity}% Soil={soil_moisture}% "
            f"[source=OPEN_METEO obs={recorded_at.isoformat()}]"
        )
        return measurement

    @staticmethod
    def refresh_active_trees(db: Session, *, limit: int = 200) -> int:
        """Refresh live weather for active (non-removed) trees. Returns count stored."""
        stmt = (
            select(Tree)
            .where(Tree.status.notin_([TreeStatus.HARVESTED, TreeStatus.REMOVED]))
            .order_by(Tree.id.asc())
            .limit(limit)
        )
        trees = list(db.execute(stmt).scalars().all())
        stored = 0
        weather_by_cell: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for tree in trees:
            cell = (round(float(tree.latitude), 2), round(float(tree.longitude), 2))
            if cell not in weather_by_cell:
                try:
                    weather_by_cell[cell] = RealWorldWeatherService.get_live_microclimate(
                        latitude=cell[0],
                        longitude=cell[1],
                    )
                except WeatherFetchError as exc:
                    logger.warning(f"Live weather fetch failed near {cell}: {exc}")
                    weather_by_cell[cell] = None
            if weather_by_cell[cell] is None:
                continue
            measurement = TreeEnvironmentService.capture_live_environment_for_tree(
                db=db,
                tree=tree,
                run_anomaly_check=True,
                weather=weather_by_cell[cell],
            )
            if measurement is not None:
                stored += 1
        logger.info(f"Environment refresh complete: {stored}/{len(trees)} trees updated")
        return stored
