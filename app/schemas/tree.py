"""Pydantic schemas for Sandalwood tree registration, tracking, and spatial queries."""

import re
from datetime import date, datetime
from typing import Optional, List, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)
from app.database.models.tree import TreeStatus
# Provenance of girth_cm / height_m on a tree record.
BIOMETRICS_FIELD_MEASURED = "FIELD_MEASURED"
BIOMETRICS_ALLOMETRIC_ESTIMATE = "ALLOMETRIC_ESTIMATE"

# User-assigned IDs: KA-01, KA-00001, TN-12, etc.
TREE_UID_PATTERN = re.compile(r"^[A-Z]{2}-\d{1,5}$")

_BIOMETRICS_SOURCES = {BIOMETRICS_FIELD_MEASURED, BIOMETRICS_ALLOMETRIC_ESTIMATE}


def _normalize_biometrics_source(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    source = value.strip().upper()
    if source not in _BIOMETRICS_SOURCES:
        raise ValueError(
            f"biometrics_source must be one of {sorted(_BIOMETRICS_SOURCES)}"
        )
    return source


class TreeRegisterRequest(BaseModel):
    """Payload to register a newly identified sandalwood tree in the field."""
    tree_uid: str = Field(
        ...,
        min_length=4,
        max_length=20,
        description="Operator-assigned Tree ID (state code + number), e.g. KA-01 or KA-00001",
        json_schema_extra={"example": "KA-01"},
    )
    region_id: Optional[Union[str, int]] = Field(
        default=None,
        description="Optional. Trees are registered by GPS; a region is not required.",
    )
    species: str = Field(
        default="Santalum album",
        max_length=100,
        json_schema_extra={"example": "Santalum album (East Indian Sandalwood)"},
    )

    # GPS Location
    latitude: float = Field(..., ge=-90.0, le=90.0, json_schema_extra={"example": 13.9310})
    longitude: float = Field(..., ge=-180.0, le=180.0, json_schema_extra={"example": 75.5720})
    altitude: Optional[float] = Field(None, json_schema_extra={"example": 640.5})
    gps_accuracy: Optional[float] = Field(None, ge=0.0, json_schema_extra={"example": 2.1})

    # Physical Attributes
    estimated_age_years: Optional[float] = Field(None, ge=0.0, json_schema_extra={"example": 12.0})
    planting_year: Optional[int] = Field(
        None,
        description="Calendar year the tree was planted, when a plantation record exists",
        json_schema_extra={"example": 2008},
    )
    girth_cm: Optional[float] = Field(None, ge=0.0, json_schema_extra={"example": 45.5})
    height_m: Optional[float] = Field(None, ge=0.0, json_schema_extra={"example": 6.8})
    biometrics_source: Optional[str] = Field(
        None,
        description=(
            "FIELD_MEASURED when girth/height were measured on site, "
            "ALLOMETRIC_ESTIMATE when they were inferred from site index"
        ),
        json_schema_extra={"example": "FIELD_MEASURED"},
    )
    host_notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Nearby host trees with distance, e.g. Neem 4 m",
    )
    last_observed_on: Optional[str] = Field(
        None,
        max_length=40,
        description="Observation date when survival has not been field-confirmed",
    )
    survival_confirmed: Optional[bool] = Field(
        None,
        description="True after a field status check. False for internet occurrences.",
    )

    status: TreeStatus = Field(default=TreeStatus.HEALTHY, json_schema_extra={"example": "HEALTHY"})
    notes: Optional[str] = Field(None, json_schema_extra={"example": "High oil-content mature tree near ridge."})
    evidence_origin: Optional[str] = Field(
        default=None,
        description="SIMULATED blocks registration. Field surveys omit this field.",
    )

    @field_validator("tree_uid")
    @classmethod
    def normalize_and_validate_tree_uid(cls, value: str) -> str:
        uid = value.strip().upper().replace(" ", "")
        if not TREE_UID_PATTERN.match(uid):
            raise ValueError(
                "tree_uid must be STATE-NUMBER (e.g. KA-01, KA-00001, TN-12). "
                "You assign this ID; the server does not auto-generate it."
            )
        return uid

    @field_validator("planting_year")
    @classmethod
    def validate_planting_year(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        year = date.today().year
        if value < 1800 or value > year:
            raise ValueError(f"planting_year must be between 1800 and {year}")
        return value

    @field_validator("biometrics_source")
    @classmethod
    def validate_biometrics_source(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_biometrics_source(value)

    @model_validator(mode="after")
    def default_biometrics_source(self) -> "TreeRegisterRequest":
        if self.biometrics_source is None and (self.girth_cm or self.height_m):
            self.biometrics_source = BIOMETRICS_FIELD_MEASURED
        return self


class TreeUpdateRequest(BaseModel):
    """Payload to update physical measurements or health status of a registered sandalwood tree."""
    species: Optional[str] = None
    estimated_age_years: Optional[float] = Field(None, ge=0.0)
    planting_year: Optional[int] = None
    girth_cm: Optional[float] = Field(None, ge=0.0)
    height_m: Optional[float] = Field(None, ge=0.0)
    biometrics_source: Optional[str] = None
    host_notes: Optional[str] = Field(None, max_length=500)
    last_observed_on: Optional[str] = Field(None, max_length=40)
    survival_confirmed: Optional[bool] = None
    status: Optional[TreeStatus] = None
    notes: Optional[str] = None

    @field_validator("planting_year")
    @classmethod
    def validate_planting_year(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        year = date.today().year
        if value < 1800 or value > year:
            raise ValueError(f"planting_year must be between 1800 and {year}")
        return value

    @field_validator("biometrics_source")
    @classmethod
    def validate_biometrics_source(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_biometrics_source(value)


class TreeResponse(BaseModel):
    """Public representation of a registered Sandalwood Tree."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tree_uid: str
    species: str
    region_id: Optional[int] = None
    latitude: float
    longitude: float
    altitude: Optional[float]
    gps_accuracy: Optional[float]
    estimated_age_years: Optional[float]
    planting_year: Optional[int] = None
    girth_cm: Optional[float]
    height_m: Optional[float]
    biometrics_source: Optional[str] = None
    host_notes: Optional[str] = None
    last_observed_on: Optional[str] = None
    survival_confirmed: Optional[bool] = None
    status: TreeStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def age_label(self) -> str:
        from app.services.tree_assessment import age_label as _age_label
        return _age_label(
            self.planting_year,
            self.estimated_age_years,
            self.biometrics_source,
        )

    @computed_field
    @property
    def survival_label(self) -> str:
        from app.services.tree_assessment import survival_label as _survival_label
        return _survival_label(
            self.status,
            self.survival_confirmed,
            self.last_observed_on,
            self.notes,
        )

    @computed_field
    @property
    def gps_label(self) -> str:
        from app.services.tree_assessment import gps_label as _gps_label
        return _gps_label(self.gps_accuracy)

    @computed_field
    @property
    def hosts_label(self) -> str:
        from app.services.tree_assessment import hosts_label as _hosts_label
        return _hosts_label(self.host_notes)

    @computed_field
    @property
    def heartwood_label(self) -> str:
        from app.services.tree_assessment import heartwood_label as _heartwood_label
        return _heartwood_label(self.girth_cm, self.height_m, self.biometrics_source)


class TreeDeletedResponse(BaseModel):
    """Confirmation that a registered tree was permanently removed."""
    tree_uid: str
    deleted: bool = True


class NearbyTreesRequest(BaseModel):
    """Payload to query sandalwood trees within a radius of a GPS coordinate."""
    latitude: float = Field(..., ge=-90.0, le=90.0, json_schema_extra={"example": 13.9310})
    longitude: float = Field(..., ge=-180.0, le=180.0, json_schema_extra={"example": 75.5720})
    radius_meters: float = Field(default=500.0, ge=1.0, le=50000.0, json_schema_extra={"example": 500.0})
    region_id: Optional[Union[str, int]] = Field(None, json_schema_extra={"example": "REG-KA-SHIVAMOGGA"})


class NearbyTreeItem(BaseModel):
    """Sandalwood tree record with calculated distance from search center."""
    tree: TreeResponse
    distance_meters: float


class NearbyTreesResponse(BaseModel):
    """Spatial query results for nearby sandalwood trees."""
    center_latitude: float
    center_longitude: float
    radius_meters: float
    total_found: int
    trees: List[NearbyTreeItem]
