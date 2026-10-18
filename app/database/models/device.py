"""Device database model representing IoT field sensors and gateways."""

import enum
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, Enum, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.region import Region
    from app.database.models.environmental_measurement import EnvironmentalMeasurement
    from app.database.models.alert import Alert


class DeviceStatus(str, enum.Enum):
    """Device lifecycle and Zero Trust status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    REVOKED = "REVOKED"


class Device(Base, TimestampMixin):
    """Field IoT device transmitting telemetry or used for tree registration."""
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), default="ENVIRONMENTAL_SENSOR", nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_salt: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, name="device_status"),
        default=DeviceStatus.ACTIVE,
        nullable=False,
    )

    assigned_region_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    region: Mapped[Optional["Region"]] = relationship("Region", back_populates="devices")
    measurements: Mapped[List["EnvironmentalMeasurement"]] = relationship(
        "EnvironmentalMeasurement",
        back_populates="device",
    )
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="device")

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, device_id='{self.device_id}', status='{self.status}')>"
