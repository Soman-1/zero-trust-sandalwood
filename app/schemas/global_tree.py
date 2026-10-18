"""Pydantic schemas for Global Internet Sandalwood biodiversity occurrences."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class GlobalTreeItem(BaseModel):
    """Represents an individual real-world sandalwood tree location from internet biodiversity databases."""
    id: str = Field(..., description="Unique record identifier")
    source: str = Field(..., description="Data source name (GBIF, iNaturalist Open Data, etc.)")
    source_id: str = Field(..., description="Original record ID from the source")
    scientific_name: str = Field(default="Santalum album L.", description="Scientific botanical taxon name")
    vernacular_name: str = Field(default="Indian Sandalwood (Shrigandha)", description="Common name")
    latitude: float = Field(..., description="Latitude coordinate (decimal degrees)")
    longitude: float = Field(..., description="Longitude coordinate (decimal degrees)")
    elevation_m: Optional[float] = Field(None, description="Elevation above sea level in meters")
    gps_accuracy: Optional[float] = Field(None, description="Coordinate uncertainty in meters")
    state_province: Optional[str] = Field(None, description="State or province name")
    country: Optional[str] = Field(default="India", description="Country name")
    locality: Optional[str] = Field(None, description="Specific location or reserve description")
    recorded_by: Optional[str] = Field(None, description="Collector, botanist, or observer name")
    event_date: Optional[str] = Field(None, description="Observation or collection date string")
    image_url: Optional[str] = Field(None, description="Direct URL to specimen / field photograph")
    external_url: Optional[str] = Field(None, description="Link to external observation / specimen webpage")
    bark_characteristics: Optional[str] = Field(None, description="Trunk and bark morphological notes")
    foliage_characteristics: Optional[str] = Field(None, description="Canopy and leaf morphological notes")
    notes: Optional[str] = Field(None, description="Additional context or basis of record")
    registered_tree_uid: Optional[str] = Field(None, description="Tree UID if registered in platform asset database")
    is_registered: bool = Field(default=False, description="Whether this location is already a platform tree or imported detection")
    is_platform_asset: bool = Field(
        default=False,
        description="True only when a Tree ID asset exists at these coordinates (not a map detection)",
    )


class GlobalTreeStatsResponse(BaseModel):
    """Aggregated statistics for internet sandalwood occurrences."""
    total_trees: int
    gbif_count: int
    inaturalist_count: int
    with_photos_count: int
    states_distribution: Dict[str, int]
    registered_assets_count: int


class GlobalTreeHeartwoodEstimate(BaseModel):
    """Allometric heartwood estimate for an internet sandalwood occurrence.

    GBIF / iNaturalist do not publish measured heartwood. Values are derived from
    assumed stem biometrics (optionally modulated by site suitability), using the
    same MAGI / sigmoidal heartwood model as street-view detection.
    """
    estimated_age_years: int
    assumed_dbh_cm: float
    assumed_girth_cm: float
    assumed_height_m: float
    estimated_heartwood_kg: float
    heartwood_ratio: float
    sandalwood_grade: str
    commercial_value_inr: float
    method: str = Field(
        default="allometric_assumed_stem",
        description="Estimation method identifier",
    )
    assumption_note: str = Field(
        ...,
        description="Human-readable note that this is an estimate, not a measured core",
    )


class GlobalTreeEnvironmentSnapshot(BaseModel):
    """Live microclimate captured at an internet sandalwood coordinate."""
    latitude: float
    longitude: float
    elevation_meters: Optional[float] = None
    temperature_celsius: float
    relative_humidity_percent: float
    soil_temperature_celsius: Optional[float] = None
    soil_moisture_surface_percent: Optional[float] = None
    soil_moisture_root_percent: float
    surface_pressure_hpa: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    cloud_cover_percent: Optional[float] = None
    vapor_pressure_deficit_kpa: Optional[float] = None
    sandalwood_suitability_score: Optional[float] = None
    growth_zone_classification: Optional[str] = None
    canopy_stress_status: Optional[str] = None
    data_source: Optional[str] = None
    stored: bool = False
    measurement_uid: Optional[str] = None
    heartwood: Optional[GlobalTreeHeartwoodEstimate] = Field(
        None,
        description="Allometric heartwood estimate for the selected specimen",
    )


class GlobalTreeRegisterRequest(BaseModel):
    """Register one selected internet sandalwood occurrence as a platform tree."""
    occurrence_id: str = Field(..., min_length=1, description="Internet specimen id from the catalog")
    tree_uid: str = Field(
        ...,
        min_length=4,
        max_length=20,
        description="Operator-assigned Tree ID, e.g. KA-01",
        json_schema_extra={"example": "KA-01"},
    )
    notes: Optional[str] = Field(None, description="Optional operator notes stored with the tree")


class GlobalTreeRegisterResponse(BaseModel):
    """Registered tree plus the environmental snapshot stored with that Tree ID."""
    success: bool
    message: str
    tree_uid: str
    occurrence_id: str
    scientific_name: str
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    environment_stored: bool
    environment: Optional[GlobalTreeEnvironmentSnapshot] = None


class GlobalTreeImportResponse(BaseModel):
    """Response returned after bulk-importing internet occurrences into platform assets."""
    success: bool
    total_scanned: int
    newly_registered: int
    skipped_duplicates: int
    total_registered_in_db: int
    message: str
