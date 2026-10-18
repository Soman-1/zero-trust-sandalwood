"""Schemas for map detections (no Tree ID until operator assigns one)."""

from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.database.models.tree_detection import DetectionStatus
from app.schemas.tree import TREE_UID_PATTERN


class DetectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    detection_uid: str
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    species: str
    source: str
    confidence: Optional[float] = None
    region_id: Optional[int] = None
    status: DetectionStatus
    assigned_tree_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DetectionAssignRequest(BaseModel):
    """Operator assigns a Tree ID to an unassigned map detection."""

    tree_uid: str = Field(
        ...,
        min_length=4,
        max_length=20,
        description="Operator-chosen Tree ID, e.g. KA-01",
        json_schema_extra={"example": "KA-01"},
    )
    region_id: Optional[Union[str, int]] = Field(
        default=None,
        description="Optional. Not required to register a tree from GPS.",
    )
    species: Optional[str] = Field(default=None, max_length=100)
    estimated_age_years: Optional[float] = Field(None, ge=0.0)
    girth_cm: Optional[float] = Field(None, ge=0.0)
    height_m: Optional[float] = Field(None, ge=0.0)
    notes: Optional[str] = None

    @field_validator("tree_uid")
    @classmethod
    def normalize_tree_uid(cls, value: str) -> str:
        uid = value.strip().upper().replace(" ", "")
        if not TREE_UID_PATTERN.match(uid):
            raise ValueError("tree_uid must be STATE-NUMBER (e.g. KA-01)")
        return uid
