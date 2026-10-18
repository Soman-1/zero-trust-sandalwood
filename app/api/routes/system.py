"""System info, health diagnostics, and operational metrics API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.config import settings
from app.database.database import get_db
from app.database.models.region import Region, RegionStatus
from app.database.models.tree import Tree, TreeStatus
from app.database.models.device import Device, DeviceStatus
from app.database.models.environmental_measurement import EnvironmentalMeasurement
from app.database.models.alert import Alert, AlertStatus
from app.database.models.audit_log import AuditLog
from app.schemas.system import SystemInfoResponse
from app.ai.model import detector
from app.api.deps import get_current_user
from app.database.models.user import User

router = APIRouter(prefix="/system", tags=["System Diagnostics"])


@router.get(
    "/info",
    response_model=SystemInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get System Information & Health",
    description="Returns backend version, database connectivity, and aggregate counts of regions, trees, devices, alerts, and AI health.",
)
def get_system_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SystemInfoResponse:
    # 1. Regions
    total_regions = db.execute(select(func.count(Region.id))).scalar() or 0
    active_regions = db.execute(
        select(func.count(Region.id)).where(Region.status == RegionStatus.ACTIVE)
    ).scalar() or 0

    # 2. Sandalwood Trees
    total_trees = db.execute(select(func.count(Tree.id))).scalar() or 0
    active_trees = db.execute(
        select(func.count(Tree.id)).where(Tree.status.in_([TreeStatus.HEALTHY, TreeStatus.AT_RISK, TreeStatus.DISEASED]))
    ).scalar() or 0

    # 3. IoT Devices
    total_devices = db.execute(select(func.count(Device.id))).scalar() or 0
    active_devices = db.execute(
        select(func.count(Device.id)).where(Device.status == DeviceStatus.ACTIVE)
    ).scalar() or 0

    # 4. Telemetry & Alerts
    total_measurements = db.execute(select(func.count(EnvironmentalMeasurement.id))).scalar() or 0
    active_alerts = db.execute(
        select(func.count(Alert.id)).where(Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]))
    ).scalar() or 0

    # 5. Audit logs
    total_audit_logs = db.execute(select(func.count(AuditLog.id))).scalar() or 0

    return SystemInfoResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        database_status="CONNECTED",
        ai_model_type="IsolationForest",
        ai_model_fitted=detector.is_fitted,
        ai_trained_samples=detector.trained_sample_count,
        total_regions=total_regions,
        active_regions=active_regions,
        total_trees=total_trees,
        active_trees=active_trees,
        total_devices=total_devices,
        active_devices=active_devices,
        total_measurements=total_measurements,
        active_alerts=active_alerts,
        total_audit_logs=total_audit_logs,
    )
