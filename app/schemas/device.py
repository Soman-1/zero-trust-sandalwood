"""Pydantic schemas for IoT field device management and telemetry."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.database.models.device import DeviceStatus


class DeviceRegisterRequest(BaseModel):
    """Payload to register a new IoT field device."""
    device_id: str = Field(
        ...,
        min_length=3,
        max_length=50,
        json_schema_extra={"example": "DEV-KA-HANDHELD-001"},
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        json_schema_extra={"example": "Shivamogga Field Handheld #1"},
    )
    device_type: str = Field(
        default="FIELD_HANDHELD",
        max_length=50,
        json_schema_extra={"example": "FIELD_HANDHELD"},
    )
    assigned_region_id: Optional[int] = Field(
        default=None,
        json_schema_extra={"example": 1},
    )


class DeviceResponse(BaseModel):
    """Public device profile and operational state (excludes credentials)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    name: str
    device_type: str
    status: DeviceStatus
    assigned_region_id: Optional[int]
    last_seen_at: Optional[datetime]
    last_latitude: Optional[float]
    last_longitude: Optional[float]
    created_at: datetime


class DeviceRegisterResponse(BaseModel):
    """Response returned upon successful device registration containing the one-time API key."""
    device: DeviceResponse
    api_key: str = Field(
        ...,
        description="One-time raw API key for device authentication. Store securely on the hardware.",
    )
    message: str = "Device registered successfully. Save the api_key securely as it will not be displayed again."


class DeviceStatusUpdateRequest(BaseModel):
    """Payload to update device operational/security state (e.g. revoke compromised device)."""
    status: DeviceStatus = Field(..., json_schema_extra={"example": "REVOKED"})


class DeviceHeartbeatRequest(BaseModel):
    """Periodic heartbeat payload from field devices."""
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, json_schema_extra={"example": 13.9310})
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, json_schema_extra={"example": 75.5720})


class DeviceHeartbeatResponse(BaseModel):
    """Confirmation response for device heartbeat."""
    success: bool = True
    device_id: str
    status: DeviceStatus
    last_seen_at: datetime
