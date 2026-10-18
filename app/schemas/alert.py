"""Pydantic schemas for Alert management and operational lifecycle."""

from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, Field
from app.database.models.alert import AlertSeverity, AlertStatus


class AlertCreateRequest(BaseModel):
    """Payload to dispatch an alert manually or programmatically."""
    region_id: Optional[Union[str, int]] = Field(None, description="Optional target region code or ID")
    tree_id: Optional[Union[str, int]] = Field(None, description="Optional associated sandalwood tree UID")
    device_id: Optional[Union[str, int]] = Field(None, description="Optional associated IoT device ID")
    alert_type: str = Field(..., json_schema_extra={"example": "CRITICAL_SOIL_DEHYDRATION"})
    severity: AlertSeverity = Field(default=AlertSeverity.MEDIUM)
    message: str = Field(..., json_schema_extra={"example": "Soil moisture dropped below 10% critical threshold"})
    anomaly_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class AlertAcknowledgeRequest(BaseModel):
    """Payload to acknowledge an active alert."""
    notes: Optional[str] = Field(None, description="Operator acknowledgment notes")


class AlertResolveRequest(BaseModel):
    """Payload to resolve an alert with resolution notes."""
    resolution_notes: str = Field(..., description="Corrective action and resolution notes")


class AlertDismissRequest(BaseModel):
    """Payload to dismiss an alert (e.g. false positive)."""
    reason: Optional[str] = Field(None, description="Reason for alert dismissal")


class AlertResponse(BaseModel):
    """Public representation of an alert."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_uid: str
    region_id: Optional[int] = None
    tree_id: Optional[int]
    device_id: Optional[int]
    measurement_id: Optional[int]
    alert_type: str
    severity: AlertSeverity
    message: str
    anomaly_score: Optional[float]
    status: AlertStatus
    resolved_by_user_id: Optional[int]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class AlertSummaryStatsResponse(BaseModel):
    """Aggregated alert statistics for operations dashboards."""
    total_alerts: int
    active_count: int
    acknowledged_count: int
    resolved_count: int
    dismissed_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class PaginatedAlertsResponse(BaseModel):
    """Paginated list of alerts."""
    total: int
    skip: int
    limit: int
    alerts: List[AlertResponse]
