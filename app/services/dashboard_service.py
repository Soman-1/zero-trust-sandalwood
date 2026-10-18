"""Dashboard aggregation and GIS geospatial map layers service."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database.models.region import Region, RegionStatus
from app.database.models.tree import Tree, TreeStatus
from app.database.models.device import Device, DeviceStatus
from app.database.models.environmental_measurement import EnvironmentalMeasurement
from app.database.models.alert import Alert, AlertSeverity, AlertStatus
from app.database.models.audit_log import AuditLog
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    GISMapLayerResponse,
    GeoJSONFeature,
    TimeSeriesPoint,
    TimeSeriesResponse,
    RegionDashboardResponse,
    TreeHealthBreakdown,
    AlertSeverityBreakdown,
    Environmental24hSummary,
)
from app.services.region_service import RegionService
from app.services.tree_service import TreeService
from app.services.audit_service import AuditService


class DashboardService:
    """Consolidated business logic for operations dashboards and GIS mapping."""

    @staticmethod
    def get_overview_metrics(db: Session) -> DashboardOverviewResponse:
        """Compute executive overview KPIs across the two-layer agroforestry architecture."""
        now = datetime.now(timezone.utc)
        past_24h = now - timedelta(hours=24)

        # 1. Regions
        total_regions = db.execute(select(func.count(Region.id))).scalar() or 0
        active_regions = db.execute(
            select(func.count(Region.id)).where(Region.status == RegionStatus.ACTIVE)
        ).scalar() or 0

        # 2. Sandalwood Trees (SQL aggregation)
        tree_counts_stmt = select(Tree.status, func.count(Tree.id)).group_by(Tree.status)
        tree_status_counts = dict(db.execute(tree_counts_stmt).all())
        total_trees = sum(tree_status_counts.values())
        tree_breakdown = TreeHealthBreakdown(
            healthy=tree_status_counts.get(TreeStatus.HEALTHY, 0),
            at_risk=tree_status_counts.get(TreeStatus.AT_RISK, 0),
            diseased=tree_status_counts.get(TreeStatus.DISEASED, 0),
            harvested=tree_status_counts.get(TreeStatus.HARVESTED, 0),
            removed=tree_status_counts.get(TreeStatus.REMOVED, 0),
            total=total_trees,
        )

        # 3. IoT Devices (SQL aggregation)
        device_counts_stmt = select(Device.status, func.count(Device.id)).group_by(Device.status)
        device_status_counts = dict(db.execute(device_counts_stmt).all())
        total_devices = sum(device_status_counts.values())
        device_summary = {
            "total": total_devices,
            "active": device_status_counts.get(DeviceStatus.ACTIVE, 0),
            "revoked": device_status_counts.get(DeviceStatus.REVOKED, 0),
            "inactive": device_status_counts.get(DeviceStatus.INACTIVE, 0),
        }

        # 4. Environmental 24h Aggregates
        env_stmt = select(
            func.count(EnvironmentalMeasurement.id).label("count"),
            func.avg(EnvironmentalMeasurement.temperature).label("avg_temp"),
            func.avg(EnvironmentalMeasurement.humidity).label("avg_hum"),
            func.avg(EnvironmentalMeasurement.soil_moisture).label("avg_soil"),
        ).where(EnvironmentalMeasurement.recorded_at >= past_24h)
        env_row = db.execute(env_stmt).one()

        def round_or_none(val):
            return round(val, 2) if val is not None else None

        env_summary = Environmental24hSummary(
            avg_temperature=round_or_none(env_row.avg_temp),
            avg_humidity=round_or_none(env_row.avg_hum),
            avg_soil_moisture=round_or_none(env_row.avg_soil),
            total_readings_24h=env_row.count or 0,
        )

        # 5. Alerts (SQL aggregation)
        alert_counts_stmt = (
            select(Alert.severity, func.count(Alert.id))
            .where(Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]))
            .group_by(Alert.severity)
        )
        alert_severity_counts = dict(db.execute(alert_counts_stmt).all())
        total_active_alerts = sum(alert_severity_counts.values())
        alert_breakdown = AlertSeverityBreakdown(
            critical=alert_severity_counts.get(AlertSeverity.CRITICAL, 0),
            high=alert_severity_counts.get(AlertSeverity.HIGH, 0),
            medium=alert_severity_counts.get(AlertSeverity.MEDIUM, 0),
            low=alert_severity_counts.get(AlertSeverity.LOW, 0),
            total_active=total_active_alerts,
        )

        # 6. Security & Integrity Metrics
        tampered_count = db.execute(
            select(func.count(EnvironmentalMeasurement.id)).where(EnvironmentalMeasurement.is_tampered.is_(True))
        ).scalar() or 0
        anchored_logs = db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.blockchain_status == "ANCHORED")
        ).scalar() or 0

        # Fast chain verification for overview (deep verification is at /api/v1/audit/verify-chain)
        total_audit_events = db.execute(select(func.count(AuditLog.id))).scalar() or 0
        latest_audit = db.execute(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
        ).scalar_one_or_none()
        chain_valid = True
        if latest_audit and latest_audit.id > 1:
            prev_log = db.execute(
                select(AuditLog).where(AuditLog.id == latest_audit.id - 1)
            ).scalar_one_or_none()
            if prev_log and latest_audit.previous_hash != prev_log.event_hash:
                chain_valid = False

        security_metrics = {
            "tampered_records": tampered_count,
            "anchored_audit_logs": anchored_logs,
            "chain_valid": chain_valid,
            "total_audit_events": total_audit_events,
        }

        return DashboardOverviewResponse(
            total_regions=total_regions,
            active_regions=active_regions,
            tree_assets=tree_breakdown,
            devices=device_summary,
            environmental_24h=env_summary,
            alerts=alert_breakdown,
            security=security_metrics,
        )

    @staticmethod
    def get_gis_map_layers(
        db: Session,
        region_identifier: Optional[Union[str, int]] = None,
    ) -> GISMapLayerResponse:
        """
        Synthesize multi-layer GeoJSON FeatureCollection:
        1. Region boundary polygons.
        2. Registered Sandalwood Tree point markers with species & microclimate.
        3. Active IoT field nodes with GPS positions.

        Optimized for map boot: batched counts/climate, column-lean point queries.
        """
        features: List[GeoJSONFeature] = []

        # 1. Monitored Regions (Polygons)
        target_region = None
        reg_stmt = select(Region)
        if region_identifier is not None:
            target_region = RegionService.get_region_by_identifier(db, region_identifier)
            reg_stmt = reg_stmt.where(Region.id == target_region.id)

        regions = list(db.execute(reg_stmt).scalars().all())
        region_pks = [r.id for r in regions]
        region_code_by_pk = {r.id: r.region_id for r in regions}

        # Batch tree counts (avoid N+1)
        tree_counts: Dict[int, int] = {}
        if region_pks:
            for rid, cnt in db.execute(
                select(Tree.region_id, func.count(Tree.id))
                .where(Tree.region_id.in_(region_pks))
                .group_by(Tree.region_id)
            ).all():
                tree_counts[int(rid)] = int(cnt)

        # Batch latest regional measurement (one query, not per region)
        latest_meas_by_region: Dict[int, EnvironmentalMeasurement] = {}
        if region_pks:
            latest_ids = (
                select(
                    EnvironmentalMeasurement.region_id,
                    func.max(EnvironmentalMeasurement.id).label("max_id"),
                )
                .where(EnvironmentalMeasurement.region_id.in_(region_pks))
                .group_by(EnvironmentalMeasurement.region_id)
            ).subquery()
            for meas in db.execute(
                select(EnvironmentalMeasurement).join(
                    latest_ids,
                    EnvironmentalMeasurement.id == latest_ids.c.max_id,
                )
            ).scalars().all():
                if meas.region_id is not None:
                    latest_meas_by_region[int(meas.region_id)] = meas

        # 1. Monitored Regions (Polygons)
        for reg in regions:
            if reg.boundary_geojson:
                geom = reg.boundary_geojson
                if isinstance(geom, dict) and "type" in geom:
                    features.append(
                        GeoJSONFeature(
                            type="Feature",
                            geometry=geom,
                            properties={
                                "layer_type": "REGION_BOUNDARY",
                                "region_id": reg.region_id,
                                "name": reg.name,
                                "status": reg.status.value if hasattr(reg.status, "value") else str(reg.status),
                                "tree_count": tree_counts.get(reg.id, 0),
                                "area_hectares": reg.area_hectares,
                            },
                        )
                    )

        # 2. Registered Sandalwood Trees — lean columns only
        tree_stmt = select(
            Tree.tree_uid,
            Tree.latitude,
            Tree.longitude,
            Tree.species,
            Tree.status,
            Tree.girth_cm,
            Tree.height_m,
            Tree.estimated_age_years,
            Tree.region_id,
        )
        if region_identifier is not None and target_region is not None:
            tree_stmt = tree_stmt.where(Tree.region_id == target_region.id)

        for row in db.execute(tree_stmt).all():
            features.append(
                GeoJSONFeature(
                    type="Feature",
                    geometry={
                        "type": "Point",
                        "coordinates": [row.longitude, row.latitude],
                    },
                    properties={
                        "type": "tree",
                        "id": row.tree_uid,
                        "layer_type": "SANDALWOOD_TREE",
                        "tree_uid": row.tree_uid,
                        "species": row.species,
                        "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                        "girth": row.girth_cm,
                        "girth_cm": row.girth_cm,
                        "height": row.height_m,
                        "height_m": row.height_m,
                        "age": row.estimated_age_years,
                        "estimated_age_years": row.estimated_age_years,
                        "region_id": region_code_by_pk.get(row.region_id) if row.region_id else None,
                        "is_registered": True,
                    },
                )
            )

        # 2b. Unassigned map detections (NO Tree ID yet) — capped for radar boot speed
        from app.database.models.tree_detection import TreeDetection, DetectionStatus

        det_region_pk = target_region.id if target_region is not None else None
        det_stmt = (
            select(
                TreeDetection.detection_uid,
                TreeDetection.latitude,
                TreeDetection.longitude,
                TreeDetection.species,
                TreeDetection.source,
                TreeDetection.confidence,
                TreeDetection.region_id,
                TreeDetection.status,
            )
            .where(TreeDetection.status == DetectionStatus.UNASSIGNED)
            .order_by(TreeDetection.id.desc())
            .limit(1500)
        )
        if det_region_pk is not None:
            det_stmt = det_stmt.where(TreeDetection.region_id == det_region_pk)

        for det in db.execute(det_stmt).all():
            features.append(
                GeoJSONFeature(
                    type="Feature",
                    geometry={
                        "type": "Point",
                        "coordinates": [det.longitude, det.latitude],
                    },
                    properties={
                        "type": "detection",
                        "id": det.detection_uid,
                        "layer_type": "TREE_DETECTION",
                        "detection_uid": det.detection_uid,
                        "species": det.species,
                        "source": det.source,
                        "confidence": det.confidence,
                        "region_id": det.region_id,
                        "status": det.status.value if hasattr(det.status, "value") else str(det.status),
                        "is_registered": False,
                        "label": "Unassigned detection",
                    },
                )
            )

        # 3. Active IoT Devices (Points)
        dev_stmt = select(
            Device.device_id,
            Device.name,
            Device.device_type,
            Device.status,
            Device.last_latitude,
            Device.last_longitude,
            Device.last_seen_at,
        ).where(
            Device.status == DeviceStatus.ACTIVE,
            Device.last_latitude.isnot(None),
            Device.last_longitude.isnot(None),
        )
        if region_identifier is not None and target_region is not None:
            dev_stmt = dev_stmt.where(Device.assigned_region_id == target_region.id)

        for dev in db.execute(dev_stmt).all():
            features.append(
                GeoJSONFeature(
                    type="Feature",
                    geometry={
                        "type": "Point",
                        "coordinates": [dev.last_longitude, dev.last_latitude],
                    },
                    properties={
                        "type": "device",
                        "id": dev.device_id,
                        "layer_type": "IOT_DEVICE",
                        "device_id": dev.device_id,
                        "name": dev.name,
                        "device_type": dev.device_type.value if hasattr(dev.device_type, "value") else str(dev.device_type),
                        "status": dev.status.value if hasattr(dev.status, "value") else str(dev.status),
                        "last_seen_at": dev.last_seen_at.isoformat() if dev.last_seen_at else None,
                    },
                )
            )

        return GISMapLayerResponse(
            type="FeatureCollection",
            features=features,
        )

    @staticmethod
    def get_timeseries_chart_data(
        db: Session,
        region_identifier: Optional[Union[str, int]] = None,
        tree_identifier: Optional[Union[str, int]] = None,
        hours: int = 48,
    ) -> TimeSeriesResponse:
        """Fetch chronological time-series observations for frontend line/bar charts."""
        since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(EnvironmentalMeasurement).where(
            EnvironmentalMeasurement.recorded_at >= since_time
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

        stmt = stmt.order_by(EnvironmentalMeasurement.recorded_at.asc())
        records = list(db.execute(stmt).scalars().all())

        points = [
            TimeSeriesPoint(
                timestamp=r.recorded_at,
                temperature=r.temperature,
                humidity=r.humidity,
                soil_moisture=r.soil_moisture,
                is_anomaly=r.is_anomaly,
            )
            for r in records
        ]

        return TimeSeriesResponse(
            region_id=reg_code,
            tree_uid=tree_code,
            hours=hours,
            total_points=len(points),
            points=points,
        )

    @staticmethod
    def get_region_dashboard_detail(
        db: Session,
        region_identifier: Union[str, int],
    ) -> RegionDashboardResponse:
        """Deep-dive operational metrics for a specific monitored region."""
        region = RegionService.get_region_by_identifier(db, region_identifier)

        # Trees breakdown
        trees = list(db.execute(select(Tree).where(Tree.region_id == region.id)).scalars().all())
        tree_breakdown = TreeHealthBreakdown(
            healthy=sum(1 for t in trees if t.status == TreeStatus.HEALTHY),
            at_risk=sum(1 for t in trees if t.status == TreeStatus.AT_RISK),
            diseased=sum(1 for t in trees if t.status == TreeStatus.DISEASED),
            harvested=sum(1 for t in trees if t.status == TreeStatus.HARVESTED),
            removed=sum(1 for t in trees if t.status == TreeStatus.REMOVED),
            total=len(trees),
        )

        # Latest telemetry
        latest_meas = db.execute(
            select(EnvironmentalMeasurement)
            .where(EnvironmentalMeasurement.region_id == region.id)
            .order_by(EnvironmentalMeasurement.recorded_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        latest_env = None
        if latest_meas:
            latest_env = {
                "measurement_uid": latest_meas.measurement_uid,
                "temperature_c": latest_meas.temperature,
                "humidity_pct": latest_meas.humidity,
                "soil_moisture_pct": latest_meas.soil_moisture,
                "recorded_at": latest_meas.recorded_at.isoformat(),
                "is_anomaly": latest_meas.is_anomaly,
            }

        # Active alerts
        active_alerts = list(
            db.execute(
                select(Alert)
                .where(
                    Alert.region_id == region.id,
                    Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]),
                )
                .order_by(Alert.created_at.desc())
            ).scalars().all()
        )
        alerts_data = [
            {
                "alert_uid": a.alert_uid,
                "alert_type": a.alert_type,
                "severity": a.severity.value,
                "message": a.message,
                "created_at": a.created_at.isoformat(),
            }
            for a in active_alerts
        ]

        # Assigned devices
        devices = list(
            db.execute(
                select(Device).where(Device.assigned_region_id == region.id)
            ).scalars().all()
        )
        devices_data = [
            {
                "device_id": d.device_id,
                "name": d.name,
                "status": d.status.value,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            }
            for d in devices
        ]

        return RegionDashboardResponse(
            region_id=region.region_id,
            name=region.name,
            status=region.status.value,
            center_latitude=region.center_latitude,
            center_longitude=region.center_longitude,
            area_hectares=region.area_hectares,
            tree_assets=tree_breakdown,
            latest_environmental=latest_env,
            active_alerts=alerts_data,
            assigned_devices=devices_data,
        )
