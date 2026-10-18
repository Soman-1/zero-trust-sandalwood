"""Pydantic schemas for Satellite AI Tree Identification and GBIF Biodiversity Ingestion."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone


class SentinelBands(BaseModel):
    blue: float = Field(0.05, description="Band 2 (490nm) Blue Reflectance [0-1]")
    green: float = Field(0.08, description="Band 3 (560nm) Green Reflectance [0-1]")
    red: float = Field(0.06, description="Band 4 (665nm) Red Reflectance [0-1]")
    red_edge: float = Field(0.18, description="Band 5 (705nm) Red Edge 1 Reflectance [0-1]")
    nir: float = Field(0.48, description="Band 8 (842nm) Near-Infrared Reflectance [0-1]")
    swir1: float = Field(0.22, description="Band 11 (1610nm) Shortwave IR-1 Reflectance [0-1]")
    swir2: float = Field(0.12, description="Band 12 (2190nm) Shortwave IR-2 Reflectance [0-1]")


class SatelliteIdentifyRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Target canopy latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Target canopy longitude")
    bands: Optional[SentinelBands] = Field(None, description="Optional custom Sentinel-2 multi-spectral reflectance bands")
    elevation_m: Optional[float] = Field(None, description="Optional elevation in meters")


class SpectralIndices(BaseModel):
    ndvi: float = Field(..., description="Normalized Difference Vegetation Index [(NIR-Red)/(NIR+Red)]")
    evi: float = Field(..., description="Enhanced Vegetation Index")
    ndmi: float = Field(..., description="Normalized Difference Moisture Index [(NIR-SWIR)/(NIR+SWIR)]")
    ci_red_edge: float = Field(..., description="Chlorophyll Red Edge Index")
    canopy_height_m: float = Field(..., description="Estimated canopy height in meters")


class SpeciesProbability(BaseModel):
    species_scientific: str
    species_common: str
    probability: float
    is_sandalwood: bool


class SatelliteIdentifyResponse(BaseModel):
    latitude: float
    longitude: float
    is_sandalwood: bool
    predicted_species: str
    predicted_common_name: str
    confidence_score: float
    all_probabilities: List[SpeciesProbability]
    spectral_indices: SpectralIndices
    sentinel_bands: SentinelBands
    satellite_source: str
    evidence_origin: str = "SIMULATED"
    identification_timestamp: datetime


class BoundingBox(BaseModel):
    min_lat: float = Field(..., ge=-90.0, le=90.0)
    min_lon: float = Field(..., ge=-180.0, le=180.0)
    max_lat: float = Field(..., ge=-90.0, le=90.0)
    max_lon: float = Field(..., ge=-180.0, le=180.0)

    @model_validator(mode='after')
    def validate_order(self):
        if self.min_lat > self.max_lat or self.min_lon > self.max_lon:
            raise ValueError('BoundingBox min_* must be <= max_*')
        return self


class SatelliteScanRequest(BaseModel):
    bbox: BoundingBox
    sample_tree_count: int = Field(500, ge=50, le=5000, description="Number of canopy points to scan in bounding box")
    confidence_threshold: float = Field(0.65, ge=0.4, le=0.99, description="Minimum probability to flag as Sandalwood")


class DetectedSandalwoodPoint(BaseModel):
    point_id: str
    latitude: float
    longitude: float
    confidence_score: float
    estimated_age_years: int
    ndvi: float
    canopy_height_m: float


class SatelliteScanResponse(BaseModel):
    total_trees_scanned: int
    sandalwood_detected_count: int
    other_species_count: int
    scan_duration_ms: float
    detected_sandalwood_trees: List[DetectedSandalwoodPoint]
    dominant_non_sandalwood_species: List[str]
    evidence_origin: str = "SIMULATED"
    satellite_source: str = "SIMULATED — random points and synthetic reflectance, not a Sentinel-2 scene"


class GBIFSyncRequest(BaseModel):
    limit: int = Field(50, ge=5, le=300, description="Number of occurrences to fetch from GBIF")
    country: str = Field("IN", description="ISO Country Code")
    state: Optional[str] = Field("Karnataka", description="State filter (optional)")


class RealWorldTreeItem(BaseModel):
    gbif_id: str
    scientific_name: str
    vernacular_name: str
    latitude: float
    longitude: float
    state_province: Optional[str]
    locality: Optional[str]
    recorded_by: Optional[str]
    event_date: Optional[str]
    image_url: Optional[str]
    inaturalist_url: Optional[str]
    dataset_name: Optional[str]
    is_sandalwood: bool


class GBIFSyncResponse(BaseModel):
    success: bool
    total_fetched: int
    records_saved_to_db: int
    sample_records: List[RealWorldTreeItem]
    message: str


# ==========================================
# AERIAL & DRONE TREE CROWN VISION SCHEMAS
# ==========================================

class AerialCrownBox(BaseModel):
    box_id: str = Field(..., description="Unique bounding box identifier (e.g. UAV-SW-001)")
    ymin: float = Field(..., ge=0.0, le=1.0, description="Normalized top coordinate [0.0 - 1.0]")
    xmin: float = Field(..., ge=0.0, le=1.0, description="Normalized left coordinate [0.0 - 1.0]")
    ymax: float = Field(..., ge=0.0, le=1.0, description="Normalized bottom coordinate [0.0 - 1.0]")
    xmax: float = Field(..., ge=0.0, le=1.0, description="Normalized right coordinate [0.0 - 1.0]")
    species_scientific: str = Field(..., description="Scientific species name (e.g. Santalum album)")
    species_common: str = Field(..., description="Common vernacular name")
    is_sandalwood: bool = Field(..., description="True if verified as Sandalwood")
    is_host_tree: bool = Field(False, description="True if identified as a beneficial host tree (Neem, Casuarina, Pongamia)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    crown_diameter_m: float = Field(..., description="Estimated crown diameter in meters")
    canopy_area_sqm: float = Field(..., description="Estimated canopy footprint area in square meters")
    estimated_age_years: int = Field(..., description="Estimated tree age in years")
    estimated_biomass_kg: float = Field(..., description="Estimated wood biomass in kg")
    health_status: str = Field("HEALTHY", description="Canopy health status (HEALTHY, AT_RISK, DISEASED)")
    foliage_texture: Optional[str] = Field(None, description="Visual foliage texture classification")


class AerialDetectRequest(BaseModel):
    preset_id: Optional[str] = Field(None, description="Preset aerial flight ID (e.g. shivamogga_plantation, mysore_reserve)")
    image_base64: Optional[str] = Field(
        None,
        max_length=2_000_000,
        description="Base64-encoded drone aerial image (JPG/PNG), max ~1.5MB decoded",
    )
    confidence_threshold: float = Field(0.60, ge=0.30, le=0.99, description="Minimum confidence threshold")
    center_lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional center GPS latitude of aerial tile")
    center_lon: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional center GPS longitude of aerial tile")
    ground_sampling_distance_cm: float = Field(3.5, ge=0.5, le=30.0, description="GSD in centimeters per pixel")


class AerialDetectResponse(BaseModel):
    preset_id: str
    title: str
    location: str
    center_lat: float
    center_lon: float
    ground_sampling_distance_cm: float
    flight_altitude_m: float
    total_canopies_detected: int
    sandalwood_count: int
    host_trees_count: int
    other_trees_count: int
    average_confidence: float
    estimated_sandalwood_biomass_kg: float
    canopies: List[AerialCrownBox]
    pipeline_architecture: str
    evidence_origin: str = "SIMULATED"
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AerialPresetItem(BaseModel):
    id: str
    title: str
    location: str
    ground_sampling_distance_cm: float
    flight_altitude_m: float
    center_lat: float
    center_lon: float
    description: str
    canopy_count: int
    sandalwood_count: int


class AerialPresetsResponse(BaseModel):
    presets: List[AerialPresetItem]


# ==========================================
# REAL-WORLD WEATHER & SATELLITE SCHEMAS
# ==========================================

class LiveClimateRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class LiveClimateResponse(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    elevation_meters: float = Field(..., ge=-500.0, le=9000.0)
    temperature_celsius: float = Field(..., ge=-90.0, le=60.0)
    relative_humidity_percent: float = Field(..., ge=0.0, le=100.0)
    soil_temperature_celsius: float = Field(..., ge=-90.0, le=70.0)
    soil_moisture_surface_percent: float = Field(..., ge=0.0, le=100.0)
    soil_moisture_root_percent: float = Field(..., ge=0.0, le=100.0)
    surface_pressure_hpa: float = Field(..., ge=300.0, le=1100.0)
    wind_speed_kmh: float = Field(..., ge=0.0, le=400.0)
    wind_direction_deg: float = Field(..., ge=0.0, le=360.0)
    cloud_cover_percent: float = Field(..., ge=0.0, le=100.0)
    solar_irradiance_wm2: float = Field(..., ge=0.0, le=1500.0)
    is_day: bool
    vapor_pressure_deficit_kpa: float = Field(..., ge=0.0)
    sandalwood_suitability_score: float = Field(..., ge=0.0, le=100.0)
    growth_zone_classification: str
    canopy_stress_status: str
    data_source: str
    timestamp: str = Field(..., description="Open-Meteo observation time normalized to UTC ISO-8601")
    fetched_at: Optional[str] = Field(
        None, description="Wall-clock UTC time when this process contacted Open-Meteo"
    )
    observation_timezone: Optional[str] = Field(
        None, description="IANA timezone used by Open-Meteo for the observation clock"
    )
    integrity_hash: str


class LandmarkPreset(BaseModel):
    id: str
    name: str
    category: str
    country: str
    region_name: str
    latitude: float
    longitude: float
    altitude_m: float
    description: str
    tree_species: str
    is_verified_reserve: bool


# ==========================================
# DRONE AUTONOMOUS WAYPOINT PATROL SCHEMAS
# ==========================================

class DronePatrolWaypoint(BaseModel):
    waypoint_id: str = Field(..., description="Unique waypoint identifier (e.g. WP-01)")
    sequence: int = Field(..., description="Flight order sequence 1-indexed")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    altitude_m: float = Field(..., description="Target flight altitude AGL in meters")
    leg_distance_m: float = Field(..., description="Distance in meters from preceding waypoint")
    cumulative_distance_m: float = Field(..., description="Total cumulative distance up to this waypoint")
    leg_bearing_deg: float = Field(..., description="Compass heading towards this waypoint (0-360 deg)")
    eta_sec: float = Field(..., description="Estimated arrival time in seconds from takeoff")
    action: str = Field("TRANSIT_SCAN", description="Mission action (TAKEOFF, TRANSIT_SCAN, RTB_LAND)")


class DroneMissionCanopyTarget(BaseModel):
    box_id: str
    latitude: float
    longitude: float
    species_scientific: str
    species_common: str
    is_sandalwood: bool
    is_host_tree: bool
    confidence: float
    crown_diameter_m: float
    estimated_biomass_kg: float
    health_status: str
    interception_time_sec: float
    associated_waypoint_id: str


class DronePatrolMissionResponse(BaseModel):
    mission_id: str
    drone_hardware_id: str
    preset_id: str
    preset_title: str
    reserve_name: str
    flight_altitude_m: float
    survey_speed_mps: float
    total_waypoints: int
    total_distance_m: float
    total_duration_sec: float
    sandalwood_count: int
    host_trees_count: int
    waypoints: List[DronePatrolWaypoint]
    canopy_targets: List[DroneMissionCanopyTarget]
    mission_integrity_hash: str
    pipeline_architecture: str

