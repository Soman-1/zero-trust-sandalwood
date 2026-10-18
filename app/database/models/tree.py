"""Tree database model representing registered sandalwood trees."""

import enum
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, Boolean, Enum, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.region import Region
    from app.database.models.environmental_measurement import EnvironmentalMeasurement
    from app.database.models.alert import Alert


class TreeStatus(str, enum.Enum):
    """Tree health and registration status."""
    HEALTHY = "HEALTHY"
    AT_RISK = "AT_RISK"
    DISEASED = "DISEASED"
    HARVESTED = "HARVESTED"
    REMOVED = "REMOVED"


class Tree(Base, TimestampMixin):
    """Sandalwood tree entity uniquely registered within a forest/agroforestry region."""
    __tablename__ = "trees"
    __table_args__ = (
        Index("ix_trees_lat_lon", "latitude", "longitude"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tree_uid: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    species: Mapped[str] = mapped_column(String(100), default="Santalum album", nullable=False)

    region_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # GPS and Location
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gps_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Physical Attributes
    estimated_age_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    planting_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    girth_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # FIELD_MEASURED when girth/height came off a tape; ALLOMETRIC_ESTIMATE when
    # they were inferred from site index. Never present both as the same claim.
    biometrics_source: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    host_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_observed_on: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    survival_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    status: Mapped[TreeStatus] = mapped_column(
        Enum(TreeStatus, name="tree_status"),
        default=TreeStatus.HEALTHY,
        nullable=False,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    region: Mapped[Optional["Region"]] = relationship("Region", back_populates="trees")
    measurements: Mapped[List["EnvironmentalMeasurement"]] = relationship(
        "EnvironmentalMeasurement",
        back_populates="tree",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="tree", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tree(id={self.id}, tree_uid='{self.tree_uid}', region_id={self.region_id}, status='{self.status}')>"
