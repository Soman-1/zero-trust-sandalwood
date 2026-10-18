"""Pydantic schemas for forest/agroforestry region management."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from app.database.models.region import RegionStatus


class RegionCreateRequest(BaseModel):
    """Payload to create a new monitoring region."""
    region_id: str = Field(
        ...,
        min_length=3,
        max_length=50,
        json_schema_extra={"example": "REG-KA-SHIVAMOGGA"},
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        json_schema_extra={"example": "Shivamogga Sandalwood Reserve"},
    )
    description: Optional[str] = Field(
        None,
        json_schema_extra={"example": "High density protected agroforestry belt in Western Ghats"},
    )
    boundary_geojson: Optional[Dict[str, Any]] = Field(
        None,
        description="GeoJSON Polygon defining the geographical boundary of the region",
        json_schema_extra={
            "example": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [75.56, 13.92],
                        [75.58, 13.92],
                        [75.58, 13.94],
                        [75.56, 13.94],
                        [75.56, 13.92],
                    ]
                ],
            }
        },
    )
    center_latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, json_schema_extra={"example": 13.9300})
    center_longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, json_schema_extra={"example": 75.5700})
    area_hectares: Optional[float] = Field(None, ge=0.0, json_schema_extra={"example": 140.5})
    status: RegionStatus = Field(default=RegionStatus.ACTIVE, json_schema_extra={"example": "ACTIVE"})


class RegionUpdateRequest(BaseModel):
    """Payload to update an existing region."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    center_latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    center_longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    area_hectares: Optional[float] = Field(None, ge=0.0)
    status: Optional[RegionStatus] = None


class RegionResponse(BaseModel):
    """Public representation of a forest/monitoring region."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    region_id: str
    name: str
    description: Optional[str]
    boundary_geojson: Optional[Dict[str, Any]]
    center_latitude: Optional[float]
    center_longitude: Optional[float]
    area_hectares: Optional[float]
    status: RegionStatus
    created_at: datetime
    updated_at: datetime
    tree_count: Optional[int] = 0
    device_count: Optional[int] = 0


class CoordinateCheckRequest(BaseModel):
    """Request payload to test GPS coordinate membership in a region."""
    latitude: float = Field(..., ge=-90.0, le=90.0, json_schema_extra={"example": 13.9310})
    longitude: float = Field(..., ge=-180.0, le=180.0, json_schema_extra={"example": 75.5720})


class CoordinateCheckResponse(BaseModel):
    """Result of coordinate region boundary test."""
    region_id: str
    region_name: str
    latitude: float
    longitude: float
    is_inside: bool
    message: str
