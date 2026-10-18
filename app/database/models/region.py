"""Region database model representing agroforestry / forest monitoring zones."""

import enum
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Float, Enum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.device import Device
    from app.database.models.tree import Tree
    from app.database.models.environmental_measurement import EnvironmentalMeasurement
    from app.database.models.alert import Alert


class RegionStatus(str, enum.Enum):
    """Region operational status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MONITORED = "MONITORED"


class Region(Base, TimestampMixin):
    """Agroforestry monitoring region entity holding boundaries and aggregate data."""
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    region_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Geographic Boundary: GeoJSON polygon / coordinates array
    boundary_geojson: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    center_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    center_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    area_hectares: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[RegionStatus] = mapped_column(
        Enum(RegionStatus, name="region_status"),
        default=RegionStatus.ACTIVE,
        nullable=False,
    )

    # Relationships
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="region")
    trees: Mapped[List["Tree"]] = relationship("Tree", back_populates="region", cascade="all, delete-orphan")
    measurements: Mapped[List["EnvironmentalMeasurement"]] = relationship(
        "EnvironmentalMeasurement",
        back_populates="region",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="region", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Region(id={self.id}, region_id='{self.region_id}', name='{self.name}')>"
