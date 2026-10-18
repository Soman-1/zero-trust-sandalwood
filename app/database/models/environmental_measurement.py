"""Environmental measurement database model for region and tree observations."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.region import Region
    from app.database.models.tree import Tree
    from app.database.models.device import Device
    from app.database.models.alert import Alert


class EnvironmentalMeasurement(Base):
    """Time-series environmental readings across a region, optionally tied to a sandalwood tree."""
    __tablename__ = "environmental_measurements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    measurement_uid: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )

    # Optional. Tree registrations store weather against GPS, not a reserve polygon.
    region_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 2. Tree-level layer (Optional: only when reading is at an individual tree)
    tree_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Ingesting Device
    device_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # GPS Coordinates
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Core Sensor Readings
    temperature: Mapped[float] = mapped_column(Float, nullable=False)  # °C
    humidity: Mapped[float] = mapped_column(Float, nullable=False)     # %
    soil_moisture: Mapped[float] = mapped_column(Float, nullable=False) # %

    # Extensible environmental parameters (e.g., rainfall, air_quality, smoke, light)
    additional_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Zero Trust & Integrity
    integrity_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_tampered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # AI Anomaly Detection Outputs
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    anomaly_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    region: Mapped["Region"] = relationship("Region", back_populates="measurements")
    tree: Mapped[Optional["Tree"]] = relationship("Tree", back_populates="measurements")
    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="measurements")
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="measurement")

    def __repr__(self) -> str:
        return (
            f"<EnvironmentalMeasurement(id={self.id}, uid='{self.measurement_uid}', "
            f"region_id={self.region_id}, tree_id={self.tree_id}, temp={self.temperature}, "
            f"humidity={self.humidity}, soil={self.soil_moisture})>"
        )
