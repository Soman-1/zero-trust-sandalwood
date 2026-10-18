"""Alert lifecycle and automated notification service."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.logging import logger
from app.core.errors import NotFoundError, AppException
from app.database.models.user import User
from app.database.models.alert import Alert, AlertSeverity, AlertStatus
from app.database.models.environmental_measurement import EnvironmentalMeasurement
from app.schemas.alert import AlertSummaryStatsResponse
from app.services.region_service import RegionService
from app.services.tree_service import TreeService
from app.services.device_service import DeviceService


class AlertService:
    """Alert creation, evaluation, and operational lifecycle service."""

    @staticmethod
    def create_alert(
        db: Session,
        region_identifier: Optional[Union[str, int]],
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        tree_identifier: Optional[Union[str, int]] = None,
        device_identifier: Optional[Union[str, int]] = None,
        measurement_id: Optional[int] = None,
        anomaly_score: Optional[float] = None,
    ) -> Alert:
        """Create and persist an actionable alert. A forest reserve is not required."""
        region = None
        if region_identifier is not None:
            region = RegionService.get_region_by_identifier(db, region_identifier)

        tree_db_id = None
        if tree_identifier is not None:
            tree = TreeService.get_tree_by_uid(db, tree_identifier)
            tree_db_id = tree.id

        device_db_id = None
        if device_identifier is not None:
            device = DeviceService.get_device_by_identifier(db, device_identifier)
            device_db_id = device.id

        alert = Alert(
            region_id=region.id if region else None,
            tree_id=tree_db_id,
            device_id=device_db_id,
            measurement_id=measurement_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            anomaly_score=anomaly_score,
            status=AlertStatus.ACTIVE,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        logger.warning(
            f"ALERT TRIGGERED [{alert.severity}]: {alert.alert_type} (UID: {alert.alert_uid}) "
            f"Region: {region.region_id if region else 'None'}, Tree: {tree_identifier or 'None'}. Message: {alert.message}"
        )
        return alert

    @staticmethod
    def get_alert_by_uid(db: Session, alert_uid: str) -> Alert:
        """Fetch alert by unique identifier."""
        stmt = select(Alert).where(Alert.alert_uid == alert_uid)
        alert = db.execute(stmt).scalar_one_or_none()
        if not alert:
            raise NotFoundError(message=f"Alert '{alert_uid}' not found")
        return alert

    @staticmethod
    def list_alerts(
        db: Session,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        region_identifier: Optional[Union[str, int]] = None,
        tree_identifier: Optional[Union[str, int]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Alert], int]:
        """List alerts with filtering by status, severity, region, or tree."""
        stmt = select(Alert)

        if status is not None:
            stmt = stmt.where(Alert.status == status)

        if severity is not None:
            stmt = stmt.where(Alert.severity == severity)

        if region_identifier is not None:
            region = RegionService.get_region_by_identifier(db, region_identifier)
            stmt = stmt.where(Alert.region_id == region.id)

        if tree_identifier is not None:
            tree = TreeService.get_tree_by_uid(db, tree_identifier)
            stmt = stmt.where(Alert.tree_id == tree.id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        stmt = stmt.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
        alerts = list(db.execute(stmt).scalars().all())

        return alerts, total

    @staticmethod
    def acknowledge_alert(
        db: Session,
        alert_uid: str,
        user: User,
        notes: Optional[str] = None,
    ) -> Alert:
        """Transition alert to ACKNOWLEDGED state."""
        alert = AlertService.get_alert_by_uid(db, alert_uid)
        if alert.status not in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
            raise AppException(
                message=f"Cannot acknowledge alert in '{alert.status}' status",
                status_code=400,
                error_code="INVALID_ALERT_STATE_TRANSITION",
            )

        alert.status = AlertStatus.ACKNOWLEDGED
        ack_note = f"[ACK by {user.username}]: {notes or 'Acknowledged'}"
        alert.resolution_notes = (
            f"{alert.resolution_notes}\n{ack_note}" if alert.resolution_notes else ack_note
        )
        db.commit()
        db.refresh(alert)
        logger.info(f"Alert {alert.alert_uid} acknowledged by user '{user.username}'")
        return alert

    @staticmethod
    def resolve_alert(
        db: Session,
        alert_uid: str,
        user: User,
        resolution_notes: str,
    ) -> Alert:
        """Transition alert to RESOLVED state."""
        alert = AlertService.get_alert_by_uid(db, alert_uid)
        if alert.status in [AlertStatus.RESOLVED, AlertStatus.DISMISSED]:
            raise AppException(
                message=f"Alert is already '{alert.status}'",
                status_code=400,
                error_code="ALERT_ALREADY_CLOSED",
            )

        alert.status = AlertStatus.RESOLVED
        alert.resolved_by_user_id = user.id
        alert.resolved_at = datetime.now(timezone.utc)
        res_entry = f"[RESOLVED by {user.username}]: {resolution_notes}"
        alert.resolution_notes = (
            f"{alert.resolution_notes}\n{res_entry}" if alert.resolution_notes else res_entry
        )
        db.commit()
        db.refresh(alert)
        logger.info(f"Alert {alert.alert_uid} resolved by user '{user.username}'")
        return alert

    @staticmethod
    def dismiss_alert(
        db: Session,
        alert_uid: str,
        user: User,
        reason: Optional[str] = None,
    ) -> Alert:
        """Transition alert to DISMISSED state."""
        alert = AlertService.get_alert_by_uid(db, alert_uid)
        alert.status = AlertStatus.DISMISSED
        alert.resolved_by_user_id = user.id
        alert.resolved_at = datetime.now(timezone.utc)
        dismiss_entry = f"[DISMISSED by {user.username}]: {reason or 'Dismissed as false positive'}"
        alert.resolution_notes = (
            f"{alert.resolution_notes}\n{dismiss_entry}" if alert.resolution_notes else dismiss_entry
        )
        db.commit()
        db.refresh(alert)
        logger.info(f"Alert {alert.alert_uid} dismissed by user '{user.username}'")
        return alert

    @staticmethod
    def get_alert_summary(
        db: Session,
        region_identifier: Optional[Union[str, int]] = None,
    ) -> AlertSummaryStatsResponse:
        """Compute aggregated alert metrics via database GROUP BY."""
        base_filter = []
        if region_identifier is not None:
            region = RegionService.get_region_by_identifier(db, region_identifier)
            base_filter.append(Alert.region_id == region.id)

        # Query counts grouped by status
        status_stmt = select(Alert.status, func.count(Alert.id)).group_by(Alert.status)
        if base_filter:
            status_stmt = status_stmt.where(*base_filter)
        status_counts = dict(db.execute(status_stmt).all())

        # Query counts grouped by severity
        severity_stmt = select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity)
        if base_filter:
            severity_stmt = severity_stmt.where(*base_filter)
        severity_counts = dict(db.execute(severity_stmt).all())

        total = sum(status_counts.values())

        return AlertSummaryStatsResponse(
            total_alerts=total,
            active_count=status_counts.get(AlertStatus.ACTIVE, 0),
            acknowledged_count=status_counts.get(AlertStatus.ACKNOWLEDGED, 0),
            resolved_count=status_counts.get(AlertStatus.RESOLVED, 0),
            dismissed_count=status_counts.get(AlertStatus.DISMISSED, 0),
            critical_count=severity_counts.get(AlertSeverity.CRITICAL, 0),
            high_count=severity_counts.get(AlertSeverity.HIGH, 0),
            medium_count=severity_counts.get(AlertSeverity.MEDIUM, 0),
            low_count=severity_counts.get(AlertSeverity.LOW, 0),
        )

    @staticmethod
    def evaluate_and_trigger_alerts_for_measurement(
        db: Session,
        measurement: EnvironmentalMeasurement,
        commit: bool = True,
    ) -> Optional[Alert]:
        """
        Evaluates an ingested environmental observation against AI anomaly results
        and critical physical boundaries, automatically creating an Alert if necessary.
        """
        if not measurement.is_anomaly and measurement.temperature <= 42.0 and measurement.soil_moisture >= 15.0:
            return None

        # Determine severity and alert type
        alert_type = "ENVIRONMENTAL_ANOMALY"
        severity = AlertSeverity.MEDIUM
        messages = []

        if measurement.temperature > 45.0:
            alert_type = "EXTREME_HEAT_CRITICAL"
            severity = AlertSeverity.CRITICAL
            messages.append(f"Dangerous high temperature recorded: {measurement.temperature}°C")
        elif measurement.temperature > 40.0:
            alert_type = "HIGH_TEMPERATURE_WARNING"
            severity = AlertSeverity.HIGH
            messages.append(f"Abnormally high temperature recorded: {measurement.temperature}°C")

        if measurement.soil_moisture < 10.0:
            alert_type = "CRITICAL_SOIL_DEHYDRATION"
            severity = AlertSeverity.CRITICAL
            messages.append(f"Severe soil drought: volumetric moisture at {measurement.soil_moisture}%")
        elif measurement.soil_moisture < 15.0:
            alert_type = "LOW_SOIL_MOISTURE"
            severity = AlertSeverity.HIGH if severity != AlertSeverity.CRITICAL else AlertSeverity.CRITICAL
            messages.append(f"Low soil moisture detected: {measurement.soil_moisture}%")

        if not messages and measurement.is_anomaly:
            alert_type = "AI_DETECTED_ANOMALY"
            severity = AlertSeverity.HIGH if (measurement.anomaly_score or 0) > 0.75 else AlertSeverity.MEDIUM
            diag = measurement.anomaly_details.get("primary_factor", "UNUSUAL_CONDITIONS") if measurement.anomaly_details else "UNUSUAL_CONDITIONS"
            messages.append(f"AI Anomaly Model detected abnormal environmental patterns: {diag}")

        alert_message = "; ".join(messages)

        alert = Alert(
            region_id=measurement.region_id,
            tree_id=measurement.tree_id,
            device_id=measurement.device_id,
            measurement_id=measurement.id,
            alert_type=alert_type,
            severity=severity,
            message=alert_message,
            anomaly_score=measurement.anomaly_score,
            status=AlertStatus.ACTIVE,
        )
        db.add(alert)
        if commit:
            db.commit()
            db.refresh(alert)

        logger.warning(
            f"Auto-triggered alert {alert.alert_uid} [{alert.severity}] from measurement {measurement.measurement_uid}"
        )
        return alert
