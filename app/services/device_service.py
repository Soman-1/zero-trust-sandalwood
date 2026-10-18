"""Device management and Zero Trust hardware authentication service."""

import os
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.logging import logger
from app.core.security import generate_device_api_key, hash_device_api_key, verify_device_api_key
from app.core.errors import AppException, UnauthorizedError, ForbiddenError, NotFoundError
from app.database.models.device import Device, DeviceStatus
from app.database.models.region import Region
from app.schemas.device import DeviceRegisterRequest


class DeviceService:
    """Zero Trust field device management and authentication service."""

    @staticmethod
    def register_device(db: Session, request: DeviceRegisterRequest) -> Tuple[Device, str]:
        """Register a new field device and generate a secure one-time API key."""
        # 1. Check for duplicate device_id
        stmt = select(Device).where(Device.device_id == request.device_id)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            raise AppException(
                message=f"Device with ID '{request.device_id}' is already registered",
                status_code=400,
                error_code="DEVICE_ALREADY_EXISTS",
            )

        # 2. Check region existence if assigned
        if request.assigned_region_id is not None:
            region = db.get(Region, request.assigned_region_id)
            if not region:
                raise NotFoundError(
                    message=f"Assigned region with ID {request.assigned_region_id} does not exist"
                )

        # 3. Generate cryptographic API key and store its hash
        raw_api_key = generate_device_api_key()
        api_key_salt = os.urandom(16).hex()
        api_key_hash = hash_device_api_key(raw_api_key, salt=api_key_salt)

        device = Device(
            device_id=request.device_id,
            name=request.name,
            device_type=request.device_type,
            api_key_hash=api_key_hash,
            api_key_salt=api_key_salt,
            status=DeviceStatus.ACTIVE,
            assigned_region_id=request.assigned_region_id,
        )
        db.add(device)
        db.commit()
        db.refresh(device)

        logger.info(f"Registered IoT field device '{device.device_id}' (Type: {device.device_type})")
        return device, raw_api_key

    @staticmethod
    def authenticate_device(db: Session, device_id: str, raw_api_key: str) -> Device:
        """
        Zero Trust Device Gatekeeper:
        Verifies device identity, validates cryptographic credentials, and checks lifecycle status.
        """
        stmt = select(Device).where(Device.device_id == device_id)
        device = db.execute(stmt).scalar_one_or_none()

        if not device or not verify_device_api_key(
            raw_api_key,
            device.api_key_hash,
            salt=getattr(device, "api_key_salt", None),
        ):
            logger.warning(f"Failed device authentication attempt for device_id: '{device_id}'")
            raise UnauthorizedError(
                message="Invalid device credentials",
                details={"reason": "device_authentication_failed", "device_id": device_id},
            )

        # Zero Trust Status Validation
        if device.status == DeviceStatus.REVOKED:
            logger.error(f"REVOKED device '{device.device_id}' attempted data transmission!")
            raise ForbiddenError(
                message="Device has been permanently revoked due to security policy",
                details={"reason": "device_revoked", "device_id": device_id},
            )

        if device.status == DeviceStatus.INACTIVE:
            logger.warning(f"Inactive device '{device.device_id}' attempted access")
            raise ForbiddenError(
                message="Device is currently inactive",
                details={"reason": "device_inactive", "device_id": device_id},
            )

        # Update last seen
        device.last_seen_at = datetime.now(timezone.utc)
        db.commit()
        return device

    @staticmethod
    def get_device_by_id(db: Session, device_id: str) -> Device:
        """Retrieve device by hardware device_id string or raise 404."""
        stmt = select(Device).where(Device.device_id == device_id)
        device = db.execute(stmt).scalar_one_or_none()
        if not device:
            raise NotFoundError(message=f"Device '{device_id}' not found")
        return device

    @staticmethod
    def list_devices(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[DeviceStatus] = None,
        region_id_filter: Optional[int] = None,
    ) -> List[Device]:
        """List registered field devices with optional filtering."""
        stmt = select(Device)
        if status_filter:
            stmt = stmt.where(Device.status == status_filter)
        if region_id_filter:
            stmt = stmt.where(Device.assigned_region_id == region_id_filter)
        stmt = stmt.offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_device_status(db: Session, device_id: str, new_status: DeviceStatus) -> Device:
        """Change device operational status (e.g. revoke compromised device)."""
        device = DeviceService.get_device_by_id(db, device_id)
        old_status = device.status
        device.status = new_status
        db.commit()
        db.refresh(device)
        logger.warning(f"Device '{device.device_id}' status changed from '{old_status}' to '{new_status}'")
        return device

    @staticmethod
    def record_device_heartbeat(
        db: Session,
        device_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Device:
        """Update last seen telemetry and GPS location for a device."""
        device = DeviceService.get_device_by_id(db, device_id)
        device.last_seen_at = datetime.now(timezone.utc)
        if latitude is not None:
            device.last_latitude = latitude
        if longitude is not None:
            device.last_longitude = longitude
        db.commit()
        db.refresh(device)
        return device
