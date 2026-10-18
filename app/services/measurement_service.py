"""Environmental data ingestion and telemetry pipeline service."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.logging import logger
from app.core.errors import AppException, ForbiddenError
from app.core.geo import validate_coordinates
from app.core.sensors import validate_sensor_readings, validate_recorded_timestamp
from app.core.integrity import compute_measurement_integrity_hash, verify_measurement_integrity
from app.database.models.device import Device
from app.database.models.region import RegionStatus
from app.database.models.environmental_measurement import EnvironmentalMeasurement
from app.schemas.measurement import (
    MeasurementIngestRequest,
    MeasurementBatchIngestRequest,
    IntegrityCheckResponse,
    IntegrityScanResponse,
)
from app.services.region_service import RegionService
from app.services.tree_service import TreeService


class MeasurementService:
    """Zero Trust Environmental Telemetry Ingestion Pipeline."""

    @staticmethod
    def ingest_single_measurement(
        db: Session,
        request: MeasurementIngestRequest,
        device: Device,
    ) -> EnvironmentalMeasurement:
        """
        Processes a single incoming field telemetry observation through the Zero Trust verification pipeline:
        1. Validates physical sensor limits (temperature, humidity, soil moisture).
        2. Validates GPS coordinates range.
        3. Validates recording timestamp plausibility.
        4. Verifies region exists, is active, and the GPS point is inside the region boundary.
        5. Verifies tree association if specified (tree exists and belongs to the region).
        6. Computes deterministic SHA-256 canonical integrity hash.
        7. Persists the measurement record and updates device telemetry.
        """
        # 1. Sensor Physical Limits Check
        validate_sensor_readings(
            temperature=request.temperature,
            humidity=request.humidity,
            soil_moisture=request.soil_moisture,
        )

        # 2. GPS Range Check
        validate_coordinates(request.latitude, request.longitude)

        # 3. Timestamp Plausibility Check
        recorded_at = validate_recorded_timestamp(request.recorded_at)

        # Forest reserve polygons are not used. GPS is stored without a reserve check.
        region = None
        if request.region_id is not None:
            region = RegionService.get_region_by_identifier(db, request.region_id)

        # Optional Tree Association Check
        tree_db_id: Optional[int] = None
        if request.tree_id is not None:
            tree = TreeService.get_tree_by_uid(db, request.tree_id)
            tree_db_id = tree.id

        # 6. AI Anomaly Detection Evaluation
        from app.ai.model import detector
        is_anomaly, anomaly_score, anomaly_details = detector.predict_anomaly(
            temperature=request.temperature,
            humidity=request.humidity,
            soil_moisture=request.soil_moisture,
            additional_metrics=request.additional_metrics,
        )

        # 7. Compute Cryptographic SHA-256 Integrity Hash
        integrity_hash = compute_measurement_integrity_hash(
            region_id=region.id if region else None,
            tree_id=tree_db_id,
            device_id=device.id,
            latitude=request.latitude,
            longitude=request.longitude,
            temperature=request.temperature,
            humidity=request.humidity,
            soil_moisture=request.soil_moisture,
            recorded_at=recorded_at,
            additional_metrics=request.additional_metrics,
            altitude=request.altitude,
        )

        # 8. Persist Environmental Measurement with AI Scoring
        measurement = EnvironmentalMeasurement(
            region_id=region.id if region else None,
            tree_id=tree_db_id,
            device_id=device.id,
            latitude=request.latitude,
            longitude=request.longitude,
            altitude=request.altitude,
            temperature=request.temperature,
            humidity=request.humidity,
            soil_moisture=request.soil_moisture,
            additional_metrics=request.additional_metrics,
            integrity_hash=integrity_hash,
            is_tampered=False,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            anomaly_details=anomaly_details,
            recorded_at=recorded_at,
        )
        db.add(measurement)

        # 9. Update Device Telemetry
        device.last_seen_at = datetime.now(timezone.utc)
        device.last_latitude = request.latitude
        device.last_longitude = request.longitude

        db.commit()
        db.refresh(measurement)

        # 10. Automated Alert Triggering
        from app.services.alert_service import AlertService
        AlertService.evaluate_and_trigger_alerts_for_measurement(db=db, measurement=measurement)

        logger.info(
            f"Ingested telemetry {measurement.measurement_uid} from device '{device.device_id}' "
            f"[Tree: {request.tree_id or 'None'}] "
            f"Temp: {measurement.temperature}°C, Humidity: {measurement.humidity}%, Soil: {measurement.soil_moisture}% "
            f"[Hash: {integrity_hash[:12]}...]"
        )
        return measurement

    @staticmethod
    def ingest_batch_measurements(
        db: Session,
        request: MeasurementBatchIngestRequest,
        device: Device,
    ) -> List[EnvironmentalMeasurement]:
        """Process batch of field observations in a single coordinated pipeline with batch commit."""
        from app.ai.model import detector
        from app.services.alert_service import AlertService

        region_cache: dict = {}
        tree_cache: dict = {}
        ingested: List[EnvironmentalMeasurement] = []
        alerts_to_commit = False

        for item in request.measurements:
            # 1. Sensor Physical Limits Check
            validate_sensor_readings(
                temperature=item.temperature,
                humidity=item.humidity,
                soil_moisture=item.soil_moisture,
            )

            # 2. GPS Range Check
            validate_coordinates(item.latitude, item.longitude)

            # 3. Timestamp Plausibility Check
            recorded_at = validate_recorded_timestamp(item.recorded_at)

            # Region lookup with cache
            region_db_id = None
            if item.region_id is not None:
                if item.region_id not in region_cache:
                    region = RegionService.get_region_by_identifier(db, item.region_id)
                    region_cache[item.region_id] = region.id if region else None
                region_db_id = region_cache[item.region_id]

            # Tree lookup with cache
            tree_db_id = None
            if item.tree_id is not None:
                if item.tree_id not in tree_cache:
                    tree = TreeService.get_tree_by_uid(db, item.tree_id)
                    tree_cache[item.tree_id] = tree.id if tree else None
                tree_db_id = tree_cache[item.tree_id]

            # Anomaly detection evaluation
            is_anomaly, anomaly_score, anomaly_details = detector.predict_anomaly(
                temperature=item.temperature,
                humidity=item.humidity,
                soil_moisture=item.soil_moisture,
                additional_metrics=item.additional_metrics,
            )

            # Compute Cryptographic SHA-256 Integrity Hash
            integrity_hash = compute_measurement_integrity_hash(
                region_id=region_db_id,
                tree_id=tree_db_id,
                device_id=device.id,
                latitude=item.latitude,
                longitude=item.longitude,
                temperature=item.temperature,
                humidity=item.humidity,
                soil_moisture=item.soil_moisture,
                recorded_at=recorded_at,
                additional_metrics=item.additional_metrics,
                altitude=item.altitude,
            )

            measurement = EnvironmentalMeasurement(
                region_id=region_db_id,
                tree_id=tree_db_id,
                device_id=device.id,
                latitude=item.latitude,
                longitude=item.longitude,
                altitude=item.altitude,
                temperature=item.temperature,
                humidity=item.humidity,
                soil_moisture=item.soil_moisture,
                additional_metrics=item.additional_metrics,
                integrity_hash=integrity_hash,
                is_tampered=False,
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                anomaly_details=anomaly_details,
                recorded_at=recorded_at,
            )
            ingested.append(measurement)

        if not ingested:
            return []

        # Batch insert measurements
        db.add_all(ingested)

        # Update Device Telemetry with the last reading
        last_item = request.measurements[-1]
        device.last_seen_at = datetime.now(timezone.utc)
        device.last_latitude = last_item.latitude
        device.last_longitude = last_item.longitude

        # Flush to generate measurement primary keys for alert referencing
        db.flush()

        # Batch evaluate alerts without individual commits
        for measurement in ingested:
            AlertService.evaluate_and_trigger_alerts_for_measurement(
                db=db, measurement=measurement, commit=False
            )

        # Single transaction commit for the entire batch
        db.commit()

        for m in ingested:
            db.refresh(m)

        logger.info(
            f"Batch ingested {len(ingested)} telemetry observations from device '{device.device_id}' in single transaction."
        )
        return ingested

    @staticmethod
    def get_measurement_by_uid(db: Session, measurement_uid: str) -> EnvironmentalMeasurement:
        """Retrieve single measurement by its unique UID."""
        stmt = select(EnvironmentalMeasurement).where(
            EnvironmentalMeasurement.measurement_uid == measurement_uid
        )
        measurement = db.execute(stmt).scalar_one_or_none()
        if not measurement:
            from app.core.errors import NotFoundError
            raise NotFoundError(message=f"Environmental measurement '{measurement_uid}' not found")
        return measurement

    @staticmethod
    def list_measurements(
        db: Session,
        region_identifier: Optional[Union[str, int]] = None,
        tree_identifier: Optional[Union[str, int]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        is_anomaly: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[EnvironmentalMeasurement], int]:
        """List environmental measurements with optional region, tree, time window, and anomaly filters."""
        from sqlalchemy import func

        stmt = select(EnvironmentalMeasurement)

        if region_identifier is not None:
            region = RegionService.get_region_by_identifier(db, region_identifier)
            stmt = stmt.where(EnvironmentalMeasurement.region_id == region.id)

        if tree_identifier is not None:
            tree = TreeService.get_tree_by_uid(db, tree_identifier)
            stmt = stmt.where(EnvironmentalMeasurement.tree_id == tree.id)

        if start_time is not None:
            stmt = stmt.where(EnvironmentalMeasurement.recorded_at >= start_time)

        if end_time is not None:
            stmt = stmt.where(EnvironmentalMeasurement.recorded_at <= end_time)

        if is_anomaly is not None:
            stmt = stmt.where(EnvironmentalMeasurement.is_anomaly == is_anomaly)

        # Count total matching
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        # Order latest first
        stmt = stmt.order_by(EnvironmentalMeasurement.recorded_at.desc()).offset(skip).limit(limit)
        results = list(db.execute(stmt).scalars().all())

        return results, total

    @staticmethod
    def get_latest_region_measurement(
        db: Session,
        region_identifier: Union[str, int],
    ) -> EnvironmentalMeasurement:
        """Get the most recent environmental telemetry reading for a given region."""
        region = RegionService.get_region_by_identifier(db, region_identifier)
        stmt = (
            select(EnvironmentalMeasurement)
            .where(EnvironmentalMeasurement.region_id == region.id)
            .order_by(EnvironmentalMeasurement.recorded_at.desc())
            .limit(1)
        )
        measurement = db.execute(stmt).scalar_one_or_none()
        if not measurement:
            from app.core.errors import NotFoundError
            raise NotFoundError(message=f"No environmental readings recorded for region '{region.region_id}'")
        return measurement

    @staticmethod
    def get_latest_tree_measurement(
        db: Session,
        tree_identifier: Union[str, int],
    ) -> EnvironmentalMeasurement:
        """Get the most recent microclimate reading recorded for a specific sandalwood tree."""
        tree = TreeService.get_tree_by_uid(db, tree_identifier)
        stmt = (
            select(EnvironmentalMeasurement)
            .where(EnvironmentalMeasurement.tree_id == tree.id)
            .order_by(EnvironmentalMeasurement.recorded_at.desc())
            .limit(1)
        )
        measurement = db.execute(stmt).scalar_one_or_none()
        if not measurement:
            from app.core.errors import NotFoundError
            raise NotFoundError(message=f"No environmental observations recorded for tree '{tree.tree_uid}'")
        return measurement

    @staticmethod
    def get_measurement_statistics(
        db: Session,
        region_identifier: Optional[Union[str, int]] = None,
        tree_identifier: Optional[Union[str, int]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        """Compute statistical aggregations (min, max, mean) over a time window for a region or tree."""
        from sqlalchemy import func
        from app.schemas.measurement import MeasurementStatsResponse

        stmt = select(
            func.count(EnvironmentalMeasurement.id).label("reading_count"),
            func.avg(EnvironmentalMeasurement.temperature).label("avg_temp"),
            func.min(EnvironmentalMeasurement.temperature).label("min_temp"),
            func.max(EnvironmentalMeasurement.temperature).label("max_temp"),
            func.avg(EnvironmentalMeasurement.humidity).label("avg_hum"),
            func.min(EnvironmentalMeasurement.humidity).label("min_hum"),
            func.max(EnvironmentalMeasurement.humidity).label("max_hum"),
            func.avg(EnvironmentalMeasurement.soil_moisture).label("avg_soil"),
            func.min(EnvironmentalMeasurement.soil_moisture).label("min_soil"),
            func.max(EnvironmentalMeasurement.soil_moisture).label("max_soil"),
            func.min(EnvironmentalMeasurement.recorded_at).label("earliest"),
            func.max(EnvironmentalMeasurement.recorded_at).label("latest"),
        )

        reg_code = None
        if region_identifier is not None:
            region = RegionService.get_region_by_identifier(db, region_identifier)
            stmt = stmt.where(EnvironmentalMeasurement.region_id == region.id)
            reg_code = region.region_id

        tree_code = None
        if tree_identifier is not None:
            tree = TreeService.get_tree_by_uid(db, tree_identifier)
            stmt = stmt.where(EnvironmentalMeasurement.tree_id == tree.id)
            tree_code = tree.tree_uid

        if start_time is not None:
            stmt = stmt.where(EnvironmentalMeasurement.recorded_at >= start_time)

        if end_time is not None:
            stmt = stmt.where(EnvironmentalMeasurement.recorded_at <= end_time)

        row = db.execute(stmt).one()

        def round_or_none(val: Optional[float]) -> Optional[float]:
            return round(val, 2) if val is not None else None

        return MeasurementStatsResponse(
            region_id=reg_code,
            tree_uid=tree_code,
            reading_count=row.reading_count or 0,
            avg_temperature=round_or_none(row.avg_temp),
            min_temperature=round_or_none(row.min_temp),
            max_temperature=round_or_none(row.max_temp),
            avg_humidity=round_or_none(row.avg_hum),
            min_humidity=round_or_none(row.min_hum),
            max_humidity=round_or_none(row.max_hum),
            avg_soil_moisture=round_or_none(row.avg_soil),
            min_soil_moisture=round_or_none(row.min_soil),
            max_soil_moisture=round_or_none(row.max_soil),
            earliest_reading=row.earliest,
            latest_reading=row.latest,
        )

    @staticmethod
    def verify_measurement_integrity_by_uid(
        db: Session,
        measurement_uid: str,
    ) -> IntegrityCheckResponse:
        """
        Zero Trust Integrity Verification:
        Dynamically recalculates the canonical SHA-256 seal of the stored record and compares
        it against the original integrity_hash.
        Flags tampering in the database if a discrepancy is detected.
        """
        measurement = MeasurementService.get_measurement_by_uid(db, measurement_uid)
        is_valid, stored_hash, computed_hash = verify_measurement_integrity(measurement)

        if not is_valid:
            measurement.is_tampered = True
            db.commit()
            logger.error(
                f"DATA TAMPERING DETECTED on measurement {measurement.measurement_uid}! "
                f"Stored Hash: {stored_hash}, Recalculated Hash: {computed_hash}"
            )
            return IntegrityCheckResponse(
                measurement_uid=measurement.measurement_uid,
                is_valid=False,
                status="TAMPERED_DETECTED",
                stored_hash=stored_hash,
                computed_hash=computed_hash,
                message="Integrity check FAILED: Record fields have been modified or corrupted since ingestion.",
            )
        else:
            if measurement.is_tampered:
                measurement.is_tampered = False
                db.commit()

            return IntegrityCheckResponse(
                measurement_uid=measurement.measurement_uid,
                is_valid=True,
                status="VERIFIED_AUTHENTIC",
                stored_hash=stored_hash,
                computed_hash=computed_hash,
                message="Cryptographic integrity verified. Record is authentic and unmodified.",
            )

    @staticmethod
    def audit_scan_measurements_integrity(
        db: Session,
        region_identifier: Optional[Union[str, int]] = None,
        limit: int = 500,
    ) -> IntegrityScanResponse:
        """Scan stored measurements across a region to detect any data tampering."""
        stmt = select(EnvironmentalMeasurement)
        if region_identifier is not None:
            region = RegionService.get_region_by_identifier(db, region_identifier)
            stmt = stmt.where(EnvironmentalMeasurement.region_id == region.id)

        stmt = stmt.order_by(EnvironmentalMeasurement.recorded_at.desc()).limit(limit)
        measurements = list(db.execute(stmt).scalars().all())

        valid_count = 0
        tampered_count = 0
        tampered_uids: List[str] = []

        for m in measurements:
            is_valid, _, _ = verify_measurement_integrity(m)
            if not is_valid:
                m.is_tampered = True
                tampered_count += 1
                tampered_uids.append(m.measurement_uid)
            else:
                m.is_tampered = False
                valid_count += 1

        db.commit()

        return IntegrityScanResponse(
            total_scanned=len(measurements),
            valid_count=valid_count,
            tampered_count=tampered_count,
            tampered_uids=tampered_uids,
            message=(
                f"Audit scan completed: {valid_count} authentic records, {tampered_count} tampered records detected."
            ),
        )

    # Class method alias
    ingest_measurement = ingest_single_measurement



