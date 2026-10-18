"""Device management and field telemetry API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.database.models.device import Device, DeviceStatus
from app.schemas.device import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceResponse,
    DeviceStatusUpdateRequest,
    DeviceHeartbeatRequest,
    DeviceHeartbeatResponse,
)
from app.services.device_service import DeviceService
from app.api.deps import get_current_user, require_roles, get_current_device

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post(
    "",
    response_model=DeviceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Field Device",
    description="Registers a new IoT field device or handheld and generates a one-time cryptographic API key.",
)
def register_device(
    payload: DeviceRegisterRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> DeviceRegisterResponse:
    device, raw_api_key = DeviceService.register_device(db=db, request=payload)
    return DeviceRegisterResponse(
        device=DeviceResponse.model_validate(device),
        api_key=raw_api_key,
    )


@router.get(
    "",
    response_model=List[DeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="List Registered Devices",
    description="Lists all field devices with optional filtering by status and assigned region.",
)
def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    device_status: Optional[DeviceStatus] = Query(None, alias="status"),
    region_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DeviceResponse]:
    devices = DeviceService.list_devices(
        db=db,
        skip=skip,
        limit=limit,
        status_filter=device_status,
        region_id_filter=region_id,
    )
    return [DeviceResponse.model_validate(d) for d in devices]


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Device Details",
    description="Retrieves public details and operational telemetry of a registered device.",
)
def get_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceResponse:
    device = DeviceService.get_device_by_id(db=db, device_id=device_id)
    return DeviceResponse.model_validate(device)


@router.patch(
    "/{device_id}/status",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Device Status (Revoke/Activate)",
    description="Updates device security status. Admin can revoke compromised devices immediately.",
)
def update_device_status(
    device_id: str,
    payload: DeviceStatusUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> DeviceResponse:
    device = DeviceService.update_device_status(
        db=db,
        device_id=device_id,
        new_status=payload.status,
    )
    return DeviceResponse.model_validate(device)


@router.post(
    "/heartbeat",
    response_model=DeviceHeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Device Telemetry Heartbeat",
    description="IoT device check-in transmitting current GPS coordinates and updating last-seen timestamp.",
)
def device_heartbeat(
    payload: DeviceHeartbeatRequest,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> DeviceHeartbeatResponse:
    device = DeviceService.record_device_heartbeat(
        db=db,
        device_id=current_device.device_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    return DeviceHeartbeatResponse(
        success=True,
        device_id=device.device_id,
        status=device.status,
        last_seen_at=device.last_seen_at,
    )
