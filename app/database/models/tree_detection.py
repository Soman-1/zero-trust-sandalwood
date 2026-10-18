"""Unassigned sandalwood detections shown on the map before an operator assigns a Tree ID."""

import enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Enum, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.region import Region
    from app.database.models.tree import Tree


class DetectionStatus(str, enum.Enum):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"


class TreeDetection(Base, TimestampMixin):
    """
    A located sandalwood candidate on the map.
    Has GPS but NO operator Tree ID until assigned (e.g. KA-01).
    """

    __tablename__ = "tree_detections"
    __table_args__ = (
        Index("ix_tree_detections_lat_lon", "latitude", "longitude"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    detection_uid: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    species: Mapped[str] = mapped_column(String(100), default="Santalum album", nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="UNKNOWN")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    region_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[DetectionStatus] = mapped_column(
        Enum(DetectionStatus, name="detection_status"),
        default=DetectionStatus.UNASSIGNED,
        nullable=False,
        index=True,
    )

    assigned_tree_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    region: Mapped[Optional["Region"]] = relationship("Region")
    assigned_tree: Mapped[Optional["Tree"]] = relationship("Tree")

    def __repr__(self) -> str:
        return (
            f"<TreeDetection(uid='{self.detection_uid}', status='{self.status}', "
            f"lat={self.latitude}, lon={self.longitude})>"
        )
