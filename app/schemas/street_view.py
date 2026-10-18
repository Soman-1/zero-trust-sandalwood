"""Pydantic schemas for Street View 360° Panoramas, Ground-Level AI Detection, and Internet Botanical Data."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class StreetDetectionBox(BaseModel):
    box_id: str = Field(..., description="Unique bounding box identifier (e.g. STREET-SW-001)")
    yaw_deg: float = Field(0.0, ge=-180.0, le=180.0, description="Horizontal spherical yaw angle in degrees (-180 to 180)")
    pitch_deg: float = Field(0.0, ge=-90.0, le=90.0, description="Vertical spherical pitch angle in degrees (-90 to 90)")
    ymin: float = Field(..., ge=0.0, le=1.0, description="Normalized top coordinate [0.0 - 1.0]")
    xmin: float = Field(..., ge=0.0, le=1.0, description="Normalized left coordinate [0.0 - 1.0]")
    ymax: float = Field(..., ge=0.0, le=1.0, description="Normalized bottom coordinate [0.0 - 1.0]")
    xmax: float = Field(..., ge=0.0, le=1.0, description="Normalized right coordinate [0.0 - 1.0]")
    species_scientific: str = Field(..., description="Botanical scientific name (e.g. Santalum album)")
    species_common: str = Field(..., description="Common vernacular name (e.g. Indian Sandalwood / Shrigandha)")
    is_sandalwood: bool = Field(..., description="True if verified as Santalum album")
    is_host_tree: bool = Field(False, description="True if identified as a beneficial host tree (Neem, Casuarina, Pongamia)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score [0.0 - 1.0]")
    dbh_cm: float = Field(..., description="Estimated Diameter at Breast Height (DBH) in centimeters")
    height_m: float = Field(..., description="Estimated total tree height in meters")
    estimated_age_years: int = Field(..., description="Estimated tree age in years based on DBH and growth rate")
    estimated_heartwood_kg: float = Field(0.0, description="Estimated commercial heartwood biomass in kg")
    health_status: str = Field("HEALTHY", description="Health status (HEALTHY, AT_RISK, DISEASED, STRESSED)")
    bark_texture: Optional[str] = Field(None, description="Visual bark fissure & texture classification")
    foliage_glaucous_index: Optional[float] = Field(None, description="Optical index of glaucous leaf underside [0.0 - 1.0]")
    host_association: Optional[str] = Field(None, description="Nearby identified haustorial host tree details")
    distance_meters: Optional[float] = Field(None, description="Calculated optical range from surveyor camera to tree in meters")
    tree_latitude: Optional[float] = Field(None, description="Exact geodesic latitude of tree ground root base")
    tree_longitude: Optional[float] = Field(None, description="Exact geodesic longitude of tree ground root base")
    sandalwood_grade: Optional[str] = Field(None, description="Official Indian Forest Service commercial grade (Bilagalu/Ghotla/Panjam/Ailam)")
    canopy_spread_m: Optional[float] = Field(None, description="Estimated crown diameter spread in meters")
    spike_disease_risk: Optional[str] = Field("LOW", description="Phytoplasma Sandalwood Spike Disease risk level (LOW, MEDIUM, HIGH)")
    sapwood_heartwood_ratio: Optional[float] = Field(None, description="Volumetric ratio of heartwood to total stem wood")


class StreetPanoramaItem(BaseModel):
    id: str = Field(..., description="Unique panorama preset identifier")
    route_id: str = Field(..., description="Associated route identifier")
    title: str = Field(..., description="Human-readable title of street scene")
    location: str = Field(..., description="Geographic locality and reserve name")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    heading_deg: float = Field(0.0, ge=0.0, le=360.0, description="Camera viewing heading in degrees (0 = North, 90 = East)")
    altitude_m: float = Field(..., description="Terrain elevation above sea level in meters")
    step_index: int = Field(1, description="Current waypoint sequence number along route")
    total_steps_in_route: int = Field(1, description="Total number of waypoints on this roadway route")
    road_name: str = Field(..., description="Name of roadway or forest patrol trail")
    surface_type: str = Field("ASPHALT_ROAD_CORRIDOR", description="Road surface type")
    description: str = Field(..., description="Detailed description of forestry landscape")
    panorama_url: str = Field(..., description="High-resolution 360 equirectangular or street-view photograph URL")
    lighting: str = Field("SUNNY_CLEAR", description="Environmental lighting conditions")
    detections: List[StreetDetectionBox] = Field(default_factory=list, description="List of detected trees in panorama")


class StreetRouteWaypoint(BaseModel):
    step_index: int
    panorama_id: str
    title: str
    latitude: float
    longitude: float
    heading_deg: float
    altitude_m: float
    next_step_index: Optional[int]
    prev_step_index: Optional[int]
    sandalwood_count: int
    host_trees_count: int


class StreetRoute(BaseModel):
    route_id: str
    name: str
    region_name: str
    total_distance_km: float
    center_lat: float
    center_lon: float
    road_type: str
    waypoints: List[StreetRouteWaypoint]


class StreetDetectRequest(BaseModel):
    preset_id: Optional[str] = Field(None, description="Preset street panorama ID (e.g. mysore_sandalwood_highway)")
    image_base64: Optional[str] = Field(None, max_length=2_000_000, description="Base64-encoded custom street photograph or panoramic crop")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional GPS latitude of captured scene")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional GPS longitude of captured scene")
    confidence_threshold: float = Field(0.60, ge=0.30, le=0.99, description="Minimum confidence threshold for detection")
    camera_fov_deg: float = Field(75.0, ge=30.0, le=120.0, description="Camera Field of View in degrees")


class StreetDetectResponse(BaseModel):
    preset_id: Optional[str]
    title: str
    location: str
    latitude: float
    longitude: float
    heading_deg: float
    total_trees_detected: int
    sandalwood_count: int
    host_trees_count: int
    other_trees_count: int
    average_confidence: float
    total_estimated_heartwood_kg: float
    estimated_commercial_value_inr: float
    detections: List[StreetDetectionBox]
    model_architecture: str = "SIMULATED — not a vision model"
    evidence_origin: str = "SIMULATED"
    inference_duration_ms: float
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InternetPhotoItem(BaseModel):
    photo_id: str
    source: str
    scientific_name: str
    vernacular_name: str
    locality: str
    state_province: str
    latitude: float
    longitude: float
    elevation_m: Optional[int] = None
    observer: str
    event_date: str
    image_url: str
    inaturalist_url: Optional[str]
    is_sandalwood: bool
    bark_characteristics: Optional[str]
    foliage_characteristics: Optional[str]
    view_type: str
    license: str


class InternetStreetDataSyncRequest(BaseModel):
    country: Optional[str] = Field("IN", description="Target ISO country code (default 'IN' for India)")
    state_province: Optional[str] = Field("Karnataka", description="Target state/province filter")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional target center latitude for live online spatial harvest")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional target center longitude for live online spatial harvest")
    radius_km: Optional[float] = Field(25.0, ge=1.0, le=150.0, description="Search radius in kilometers")
    limit: int = Field(50, ge=5, le=200, description="Maximum number of observation records to harvest and cache")


class InternetStreetDataSyncResponse(BaseModel):
    success: bool
    total_harvested: int
    sandalwood_photos_count: int
    host_tree_photos_count: int
    sources_scraped: List[str]
    photos: List[InternetPhotoItem]
    message: str
    sync_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegisterStreetTreeRequest(BaseModel):
    tree_uid: str = Field(
        ...,
        min_length=4,
        max_length=20,
        description="Operator-assigned Tree ID (e.g. KA-01)",
        json_schema_extra={"example": "KA-01"},
    )
    detection_box_id: str = Field(..., description="ID of detection box in street view")
    species: str = Field("Santalum album", description="Scientific species name")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    estimated_age_years: int = Field(15, ge=1, le=100)
    girth_cm: float = Field(85.0, ge=10.0, le=300.0)
    height_m: float = Field(8.0, ge=1.0, le=40.0)
    region_id: Optional[int] = Field(None, description="Optional Region ID in database")
    notes: Optional[str] = Field(None, description="Surveyor notes from Street View discovery")


class RegisterStreetTreeResponse(BaseModel):
    success: bool
    tree_uid: str
    species: str
    latitude: float
    longitude: float
    estimated_age_years: int
    girth_cm: float
    height_m: float
    status: str
    integrity_hash: str
    message: str
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GlobalDestinationItem(BaseModel):
    id: str
    name: str
    region: str
    country: str
    continent: str
    latitude: float
    longitude: float
    heading_deg: float
    altitude_m: float
    dominant_species: str
    description: str
    panorama_url: str
    outdoor_verified: bool = True
    lighting: str = "SUNNY_CLEAR"


class GlobalTeleportRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    location_label: Optional[str] = Field(None, description="Optional name or address label")


class GlobalTeleportUrls(BaseModel):
    google_street_view_embed: str
    google_earth_3d: str
    satellite_canopy_03m: str
    equirectangular_4k_photosphere: Optional[str]


class GlobalTeleportResponse(BaseModel):
    query_latitude: float
    query_longitude: float
    location_name: str
    nearest_panorama: GlobalDestinationItem
    distance_to_nearest_km: float
    heading_deg: float
    altitude_m: float
    solar_elevation_deg: float
    outdoor_verified: bool
    no_indoor_commercial_guarantee: bool
    urls: GlobalTeleportUrls
    detections: List[StreetDetectionBox]
    sandalwood_count: int
    total_trees_count: int
    ai_confidence_score: float

