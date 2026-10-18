// ==========================================
// 1. AUTHENTICATION & USERS
// ==========================================

export type UserRole = 'ADMIN' | 'OPERATOR' | 'RESEARCHER' | 'AUDITOR' | 'VIEWER';
export type UserStatus = 'ACTIVE' | 'INACTIVE' | 'SUSPENDED';

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: UserRole;
  status: UserStatus;
  last_login_at: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  user: User;
}

export interface PaginatedUsersResponse {
  total: number;
  skip: number;
  limit: number;
  users: User[];
}

// ==========================================
// 2. REGIONS & RESERVES
// ==========================================

export type RegionStatus = 'ACTIVE' | 'INACTIVE' | 'MONITORED' | 'RESTRICTED';

export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface Region {
  id: number;
  region_id: string;
  name: string;
  description: string | null;
  boundary_geojson: GeoJSONPolygon;
  center_latitude: number;
  center_longitude: number;
  area_hectares: number;
  status: RegionStatus;
  created_at: string;
  updated_at: string;
  tree_count?: number;
  device_count?: number;
}

export interface CoordinateCheckResponse {
  region_id: string;
  region_name: string;
  latitude: number;
  longitude: number;
  is_inside: boolean;
  message: string;
}

// ==========================================
// 3. SANDALWOOD TREES
// ==========================================

export type TreeStatus = 'HEALTHY' | 'AT_RISK' | 'DISEASED' | 'HARVESTED' | 'REMOVED' | 'COMPROMISED';

export interface Tree {
  id: number;
  tree_uid: string;
  region_id: number | null;
  region_code?: string;
  species: string;
  latitude: number;
  longitude: number;
  estimated_age_years: number | null;
  planting_year?: number | null;
  girth_cm: number | null;
  height_m: number | null;
  biometrics_source?: string | null;
  host_notes?: string | null;
  last_observed_on?: string | null;
  survival_confirmed?: boolean | null;
  status: TreeStatus;
  notes: string | null;
  age_label?: string;
  survival_label?: string;
  gps_label?: string;
  hosts_label?: string;
  heartwood_label?: string;
  gps_accuracy?: number | null;
  altitude?: number | null;
  registered_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface NearbyTreeItem {
  tree_uid: string;
  species: string;
  latitude: number;
  longitude: number;
  status: TreeStatus;
  distance_meters: number;
}

export interface NearbyTreesResponse {
  center_latitude: number;
  center_longitude: number;
  radius_meters: number;
  count: number;
  trees: NearbyTreeItem[];
}

// ==========================================
// 4. FIELD IOT DEVICES
// ==========================================

export type DeviceStatus = 'ACTIVE' | 'INACTIVE' | 'SUSPENDED' | 'REVOKED' | 'COMPROMISED';
export type DeviceType = 'STATIONARY_NODE' | 'MOBILE_SURVEYOR';

export interface Device {
  id: number;
  device_id: string;
  name: string;
  device_type: DeviceType;
  status: DeviceStatus;
  assigned_region_id: number | null;
  last_latitude: number | null;
  last_longitude: number | null;
  last_seen_at: string | null;
  registered_at: string;
}

export interface DeviceRegisterResponse {
  device: Device;
  api_key: string;
}

// ==========================================
// 5. ENVIRONMENTAL TELEMETRY & MEASUREMENTS
// ==========================================

export interface EnvironmentalMeasurement {
  id: number;
  measurement_uid: string;
  device_id: number | null;
  region_id: number | null;
  tree_id: number | null;
  latitude: number;
  longitude: number;
  temperature: number;
  humidity: number;
  soil_moisture: number;
  integrity_hash: string;
  is_anomaly: boolean;
  anomaly_score: number | null;
  recorded_at: string;
  ingested_at: string;
}

export interface PaginatedMeasurementsResponse {
  total: number;
  skip: number;
  limit: number;
  measurements: EnvironmentalMeasurement[];
}

export interface MeasurementMetricStat {
  min: number;
  max: number;
  avg: number;
}

export interface MeasurementStatsResponse {
  count: number;
  temperature: MeasurementMetricStat;
  humidity: MeasurementMetricStat;
  soil_moisture: MeasurementMetricStat;
}

export interface IntegrityCheckResponse {
  measurement_uid: string;
  stored_hash: string;
  computed_hash: string;
  is_valid: boolean;
  status: 'VALID' | 'TAMPERED';
  message: string;
  verified_at: string;
}

export interface IntegrityScanResponse {
  total_scanned: number;
  valid_records: number;
  corrupted_records: number;
  corrupted_uids: string[];
  scan_duration_ms: number;
  status: 'HEALTHY' | 'INTEGRITY_BREACH';
}

// ==========================================
// 6. AI ANOMALY DETECTION
// ==========================================

export interface AnomalyEvaluateRequest {
  temperature: number;
  humidity: number;
  soil_moisture: number;
  additional_metrics?: Record<string, number>;
}

export interface AnomalyEvaluateResponse {
  is_anomaly: boolean;
  anomaly_score: number;
  details: {
    vpd?: number;
    raw_decision_score?: number;
    primary_factor?: string;
    temperature?: number;
    humidity?: number;
    soil_moisture?: number;
  };
  interpretation: string;
}

export interface ModelStatusResponse {
  model_type: string;
  is_fitted: boolean;
  trained_samples: number;
  contamination_rate: number;
  feature_names: string[];
}

export interface ModelRetrainResponse {
  success: boolean;
  samples_trained: number;
  message: string;
}

// ==========================================
// 7. ALERTS & INCIDENT RESPONSE
// ==========================================

export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED';

export interface Alert {
  id: number;
  alert_uid: string;
  region_id: number;
  tree_id: number | null;
  device_id: number | null;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  description: string;
  resolution_notes: string | null;
  acknowledged_by_user_id: number | null;
  resolved_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedAlertsResponse {
  total: number;
  skip: number;
  limit: number;
  alerts: Alert[];
}

export interface AlertSummaryStatsResponse {
  total_active: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  acknowledged: number;
  resolved_today: number;
}

// ==========================================
// 8. AUDIT LEDGER & BLOCKCHAIN
// ==========================================

export interface AuditLog {
  id: number;
  audit_uid: string;
  log_uid?: string;
  event_type: string;
  actor_id: string;
  actor_type: string;
  actor_user_id?: number | null;
  actor_device_id?: number | null;
  region_id?: number | null;
  tree_id?: number | null;
  action: string;
  description: string;
  action_detail?: string;
  resource_type?: string;
  resource_id?: string;
  event_payload?: Record<string, unknown> | null;
  previous_hash: string;
  event_hash: string;
  record_hash?: string;
  blockchain_tx: string | null;
  blockchain_tx_hash?: string | null;
  blockchain_status: string;
  recorded_at: string;
  created_at?: string;
}

export interface PaginatedAuditLogsResponse {
  total: number;
  skip: number;
  limit: number;
  logs: AuditLog[];
}

export interface AuditChainVerifyResponse {
  is_chain_valid: boolean;
  total_verified: number;
  total_records_checked?: number;
  broken_link_index: number | null;
  broken_event_uid?: string | null;
  genesis_hash?: string;
  latest_hash?: string;
  message: string;
}

export interface BlockchainAnchorResponse {
  success: boolean;
  batch_size: number;
  anchored_records: number;
  records_anchored?: number;
  merkle_root: string;
  contract_address: string;
  tx_hash: string;
  transaction_hash?: string;
  chain_id: number;
  block_number?: number;
  timestamp?: string;
  anchored_at?: string;
  message?: string;
}

// ==========================================
// 9. DASHBOARD & SYSTEM DIAGNOSTICS
// ==========================================

export interface HealthMetricDistribution {
  healthy: number;
  at_risk: number;
  diseased: number;
  harvested: number;
}

export interface TreeHealthBreakdown {
  healthy: number;
  at_risk: number;
  diseased: number;
  harvested: number;
  removed: number;
  total: number;
}

export interface AlertSeverityBreakdown {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total_active: number;
}

export interface Environmental24hSummary {
  avg_temperature: number | null;
  avg_humidity: number | null;
  avg_soil_moisture: number | null;
  total_readings_24h: number;
}

export interface DashboardOverviewResponse {
  total_regions: number;
  active_regions: number;
  tree_assets: TreeHealthBreakdown;
  devices: {
    total: number;
    active: number;
    revoked: number;
    inactive: number;
  };
  environmental_24h: Environmental24hSummary;
  alerts: AlertSeverityBreakdown;
  security: {
    tampered_records: number;
    anchored_audit_logs: number;
    chain_valid: boolean;
    total_audit_events: number;
  };
}

export interface GISFeature {
  type: 'Feature';
  geometry: {
    type: 'Point' | 'Polygon';
    coordinates: number[] | number[][][];
  };
  properties: {
    type: 'region' | 'tree' | 'device' | 'detection';
    id: string;
    name?: string;
    status?: string;
    species?: string;
    age?: number;
    girth?: number;
    height?: number;
    device_type?: string;
    last_seen?: string;
    layer_type?: string;
    detection_uid?: string;
    source?: string;
    confidence?: number;
    is_registered?: boolean;
    label?: string;
    [key: string]: unknown;
  };
}

export interface GISMapLayerResponse {
  type: 'FeatureCollection';
  features: GISFeature[];
}

export interface TimeSeriesPoint {
  timestamp: string;
  temperature: number;
  humidity: number;
  soil_moisture: number;
  vpd?: number;
  is_anomaly?: boolean;
}

export interface TimeSeriesResponse {
  region_id: string | null;
  tree_id: string | null;
  datapoints: TimeSeriesPoint[];
}

export interface RegionDashboardResponse {
  region: Region;
  tree_count: number;
  device_count: number;
  health_distribution: HealthMetricDistribution;
  latest_measurement: EnvironmentalMeasurement | null;
  active_alerts: Alert[];
}

export interface SystemInfoResponse {
  app_name: string;
  version: string;
  environment: string;
  database_status: string;
  ai_model_type: string;
  ai_model_fitted: boolean;
  ai_trained_samples: number;
  total_regions: number;
  active_regions: number;
  total_trees: number;
  active_trees: number;
  total_devices: number;
  active_devices: number;
  total_measurements: number;
  active_alerts: number;
  total_audit_logs: number;
}

// ==========================================
// 10. REAL-WORLD WEATHER & MICROCLIMATE
// ==========================================

export interface LiveClimateResponse {
  latitude: number;
  longitude: number;
  elevation_meters: number;
  temperature_celsius: number;
  relative_humidity_percent: number;
  soil_temperature_celsius: number;
  soil_moisture_surface_percent: number;
  soil_moisture_root_percent: number;
  surface_pressure_hpa: number;
  wind_speed_kmh: number;
  wind_direction_deg: number;
  cloud_cover_percent: number;
  solar_irradiance_wm2: number;
  is_day: boolean;
  vapor_pressure_deficit_kpa: number;
  sandalwood_suitability_score: number;
  growth_zone_classification: string;
  canopy_stress_status: string;
  data_source: string;
  /** Open-Meteo observation time normalized to UTC ISO-8601 */
  timestamp: string;
  /** Wall-clock UTC when this process contacted Open-Meteo */
  fetched_at?: string | null;
  observation_timezone?: string | null;
  integrity_hash: string;
}

// ==========================================
// AERIAL DRONE & RADAR AI DETECTION TYPES
// ==========================================

export interface AerialCrownBox {
  box_id: string;
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
  species_scientific: string;
  species_common: string;
  is_sandalwood: boolean;
  is_host_tree?: boolean;
  confidence: number;
  crown_diameter_m: number;
  canopy_area_sqm: number;
  estimated_age_years: number;
  estimated_biomass_kg: number;
  health_status: string;
  foliage_texture?: string;
  lat?: number;
  lon?: number;
}

export interface AerialPresetItem {
  id: string;
  title: string;
  location: string;
  ground_sampling_distance_cm: number;
  flight_altitude_m: number;
  center_lat: number;
  center_lon: number;
  description: string;
  canopy_count: number;
  sandalwood_count: number;
}

export interface AerialPresetsResponse {
  presets: AerialPresetItem[];
}

export interface AerialDetectResponse {
  preset_id: string;
  title: string;
  location: string;
  center_lat: number;
  center_lon: number;
  ground_sampling_distance_cm: number;
  flight_altitude_m: number;
  total_canopies_detected: number;
  sandalwood_count: number;
  host_trees_count: number;
  other_trees_count: number;
  average_confidence: number;
  estimated_sandalwood_biomass_kg: number;
  canopies: AerialCrownBox[];
  pipeline_architecture: string;
  evidence_origin?: 'SIMULATED' | 'MODEL';
}

// ==========================================
// DRONE AUTONOMOUS WAYPOINT PATROL & HUD TYPES
// ==========================================

export interface DronePatrolWaypoint {
  waypoint_id: string;
  sequence: number;
  latitude: number;
  longitude: number;
  altitude_m: number;
  leg_distance_m: number;
  cumulative_distance_m: number;
  leg_bearing_deg: number;
  eta_sec: number;
  action: 'TAKEOFF' | 'TRANSIT_SCAN' | 'RTB_LAND' | string;
}

export interface DroneMissionCanopyTarget {
  box_id: string;
  latitude: number;
  longitude: number;
  species_scientific: string;
  species_common: string;
  is_sandalwood: boolean;
  is_host_tree: boolean;
  confidence: number;
  crown_diameter_m: number;
  estimated_biomass_kg: number;
  health_status: string;
  interception_time_sec: number;
  associated_waypoint_id: string;
}

export interface DronePatrolMissionResponse {
  mission_id: string;
  drone_hardware_id: string;
  preset_id: string;
  preset_title: string;
  reserve_name: string;
  flight_altitude_m: number;
  survey_speed_mps: number;
  total_waypoints: number;
  total_distance_m: number;
  total_duration_sec: number;
  sandalwood_count: number;
  host_trees_count: number;
  waypoints: DronePatrolWaypoint[];
  canopy_targets: DroneMissionCanopyTarget[];
  mission_integrity_hash: string;
  pipeline_architecture: string;
}

export interface DroneLiveTelemetry {
  latitude: number;
  longitude: number;
  altitude_m: number;
  speed_mps: number;
  heading_deg: number;
  pitch_deg: number;
  roll_deg: number;
  battery_pct: number;
  elapsed_sec: number;
  active_waypoint_index: number;
  locked_target: DroneMissionCanopyTarget | null;
  status: 'STANDBY' | 'FLYING' | 'PAUSED' | 'COMPLETED';
}

// ==========================================
// 12. GLOBAL INTERNET SANDALWOOD DATA
// ==========================================

export interface GlobalTreeItem {
  id: string;
  source: string;
  source_id: string;
  scientific_name: string;
  vernacular_name: string;
  latitude: number;
  longitude: number;
  elevation_m: number | null;
  gps_accuracy: number | null;
  state_province: string | null;
  country: string;
  locality: string | null;
  recorded_by: string | null;
  event_date: string | null;
  image_url: string | null;
  external_url: string | null;
  bark_characteristics: string | null;
  foliage_characteristics: string | null;
  notes: string | null;
  registered_tree_uid: string | null;
  is_registered: boolean;
  is_platform_asset?: boolean;
}

export interface GlobalTreeHeartwoodEstimate {
  estimated_age_years: number;
  assumed_dbh_cm: number;
  assumed_girth_cm: number;
  assumed_height_m: number;
  estimated_heartwood_kg: number;
  heartwood_ratio: number;
  sandalwood_grade: string;
  commercial_value_inr: number;
  method: string;
  assumption_note: string;
}

export interface GlobalTreeEnvironmentSnapshot {
  latitude: number;
  longitude: number;
  elevation_meters: number | null;
  temperature_celsius: number;
  relative_humidity_percent: number;
  soil_temperature_celsius: number | null;
  soil_moisture_surface_percent: number | null;
  soil_moisture_root_percent: number;
  surface_pressure_hpa: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  cloud_cover_percent: number | null;
  vapor_pressure_deficit_kpa: number | null;
  sandalwood_suitability_score: number | null;
  growth_zone_classification: string | null;
  canopy_stress_status: string | null;
  data_source: string | null;
  stored: boolean;
  measurement_uid: string | null;
  heartwood?: GlobalTreeHeartwoodEstimate | null;
}

export interface GlobalTreeRegisterResponse {
  success: boolean;
  message: string;
  tree_uid: string;
  occurrence_id: string;
  scientific_name: string;
  latitude: number;
  longitude: number;
  altitude: number | null;
  gps_accuracy: number | null;
  environment_stored: boolean;
  environment: GlobalTreeEnvironmentSnapshot | null;
}

export interface GlobalTreeStatsResponse {
  total_trees: number;
  gbif_count: number;
  inaturalist_count: number;
  with_photos_count: number;
  states_distribution: Record<string, number>;
  registered_assets_count: number;
}

export interface GlobalTreeImportResponse {
  success: boolean;
  total_scanned: number;
  newly_registered: number;
  skipped_duplicates: number;
  total_registered_in_db: number;
  message: string;
}

