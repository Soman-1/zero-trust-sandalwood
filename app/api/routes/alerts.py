"""Alert lifecycle management, operator actions, and summary statistics API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.database.models.alert import AlertSeverity, AlertStatus
from app.schemas.alert import (
    AlertCreateRequest,
    AlertResponse,
    AlertAcknowledgeRequest,
    AlertResolveRequest,
    AlertDismissRequest,
    AlertSummaryStatsResponse,
    PaginatedAlertsResponse,
)
from app.services.alert_service import AlertService
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])


@router.get(
    "",
    response_model=PaginatedAlertsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Alerts",
    description="Lists actionable environmental and security alerts with filters for status, severity, region, or tree.",
)
def list_alerts(
    status_filter: Optional[AlertStatus] = Query(None, alias="status", description="Filter by alert status"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity level"),
    region_id: Optional[str] = Query(None, description="Filter by region code or ID"),
    tree_id: Optional[str] = Query(None, description="Filter by sandalwood tree UID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedAlertsResponse:
    alerts, total = AlertService.list_alerts(
        db=db,
        status=status_filter,
        severity=severity,
        region_identifier=region_id,
        tree_identifier=tree_id,
        skip=skip,
        limit=limit,
    )
    return PaginatedAlertsResponse(
        total=total,
        skip=skip,
        limit=limit,
        alerts=[AlertResponse.model_validate(a) for a in alerts],
    )


@router.get(
    "/summary/stats",
    response_model=AlertSummaryStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Alert Operations Summary",
    description="Retrieves aggregate alert statistics (active, critical, acknowledged, resolved) across regions.",
)
def get_alert_summary(
    region_id: Optional[str] = Query(None, description="Optional region code to filter statistics"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertSummaryStatsResponse:
    return AlertService.get_alert_summary(db=db, region_identifier=region_id)


@router.get(
    "/{alert_uid}",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Alert Details",
    description="Retrieves detailed information for a specific alert by its UID.",
)
def get_alert(
    alert_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertResponse:
    alert = AlertService.get_alert_by_uid(db=db, alert_uid=alert_uid)
    return AlertResponse.model_validate(alert)


@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Manual Alert",
    description="Allows field officers or operators to create an alert manually.",
)
def create_manual_alert(
    payload: AlertCreateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> AlertResponse:
    alert = AlertService.create_alert(
        db=db,
        region_identifier=payload.region_id,
        tree_identifier=payload.tree_id,
        device_identifier=payload.device_id,
        alert_type=payload.alert_type,
        severity=payload.severity,
        message=payload.message,
        anomaly_score=payload.anomaly_score,
    )
    return AlertResponse.model_validate(alert)


@router.post(
    "/{alert_uid}/acknowledge",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge Alert",
    description="Operator acknowledges an active alert to indicate investigation is in progress.",
)
def acknowledge_alert(
    alert_uid: str,
    payload: AlertAcknowledgeRequest = AlertAcknowledgeRequest(),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> AlertResponse:
    alert = AlertService.acknowledge_alert(
        db=db,
        alert_uid=alert_uid,
        user=current_user,
        notes=payload.notes,
    )
    return AlertResponse.model_validate(alert)


@router.post(
    "/{alert_uid}/resolve",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve Alert",
    description="Operator or field officer resolves an alert with corrective action notes.",
)
def resolve_alert(
    alert_uid: str,
    payload: AlertResolveRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> AlertResponse:
    alert = AlertService.resolve_alert(
        db=db,
        alert_uid=alert_uid,
        user=current_user,
        resolution_notes=payload.resolution_notes,
    )
    return AlertResponse.model_validate(alert)


@router.post(
    "/{alert_uid}/dismiss",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Dismiss Alert",
    description="Dismisses an alert (e.g. verified false alarm).",
)
def dismiss_alert(
    alert_uid: str,
    payload: AlertDismissRequest = AlertDismissRequest(),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> AlertResponse:
    alert = AlertService.dismiss_alert(
        db=db,
        alert_uid=alert_uid,
        user=current_user,
        reason=payload.reason,
    )
    return AlertResponse.model_validate(alert)
