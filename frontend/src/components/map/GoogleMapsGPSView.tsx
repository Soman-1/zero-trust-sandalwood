import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Circle,
  Polyline,
  Tooltip,
  Marker,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';
import {
  GISMapLayerResponse,
  TreeStatus,
  LiveClimateResponse,
  Region,
  AerialCrownBox,
  AerialDetectResponse,
  DronePatrolMissionResponse,
  DroneLiveTelemetry,
  DroneMissionCanopyTarget,
} from '../../types';
import { TreeStatusBadge } from '../common/Badge';
import { satelliteApi } from '../../api/satellite';
import {
  formatDistance,
  calculateBearing,
  bearingToCardinal,
  formatCoordinates,
  fetchOSRMRoute,
  fetchNominatimReverseGeocode,
  fetchNominatimSearch,
  calculateHaversineDistance,
  DEFAULT_MAP_CENTER,
  GPSCoordinate,
  DetailedRouteResponse,
  ReverseGeocodeResult,
} from '../../utils/geoUtils';
import {
  Navigation,
  Search,
  Maximize2,
  Minimize2,
  Thermometer,
  Droplets,
  Mountain,
  ShieldCheck,
  Trees,
  Cpu,
  RefreshCw,
  X,
  Route,
  CornerUpRight,
  Ruler,
  CheckCircle2,
  LocateFixed,
  MapPin,
  Eye,
  ZoomIn,
  ZoomOut,
  Target,
  Sun,
  Activity,
  ChevronRight,
  Radio,
  Sparkles,
  Plane,
} from 'lucide-react';
import { DroneTacticalHUD } from '../drone/DroneTacticalHUD';
import { SharpEsriImageryLayer, MapAutoResizer, CursorCoordsBinder } from './SharpEsriImageryLayer';
import { MarkerClusterLayer, ClusterPoint } from './MarkerClusterLayer';
import { MapMeasurementTool } from './MapMeasurementTool';
import { RoutingOverlayLayer } from './RoutingOverlayLayer';
import {
  googleHybridUrl,
  googleSatelliteUrl,
  GOOGLE_HYBRID_ATTRIBUTION,
  GOOGLE_SAT_ATTRIBUTION,
  GOOGLE_TILE_SUBDOMAINS,
  MAP_CONSTRAINTS,
  TILE_PERF,
} from '../../utils/basemapTiles';


interface GoogleMapsGPSViewProps {
  mapData: GISMapLayerResponse | null;
  selectedRegionId?: string;
  onSelectTree?: (treeUid: string) => void;
  onAssignDetection?: (target: {
    detectionUid?: string;
    latitude: number;
    longitude: number;
    species?: string;
    source?: string;
    evidenceOrigin?: string;
  }) => void;
  highlightedTreeUid?: string | null;
  regions?: Region[];
  aerialScanData?: AerialDetectResponse | null;
  onClearAerialScan?: () => void;
  onOpenAerialScanner?: () => void;
  onSelectRegion?: (regionId: string) => void;
}




// Custom Autonomous Drone UAV Marker with dynamic heading orientation
const createDroneUAVIcon = (heading: number) => {
  return L.divIcon({
    className: 'custom-drone-uav-marker',
    html: `
      <div style="transform: rotate(${heading}deg); width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; position: relative;">
        <div style="position: absolute; inset: 0; background: rgba(34, 211, 238, 0.25); border-radius: 9999px; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="filter: drop-shadow(0 0 6px rgba(34, 211, 238, 0.9));">
          <circle cx="12" cy="12" r="3" fill="#06b6d4" />
          <line x1="12" y1="9" x2="12" y2="4" />
          <line x1="12" y1="15" x2="12" y2="20" />
          <line x1="9" y1="12" x2="4" y2="12" />
          <line x1="15" y1="12" x2="20" y2="12" />
          <circle cx="12" cy="3" r="2" stroke="#10b981" fill="#10b981" />
          <circle cx="12" cy="21" r="2" stroke="#64748b" />
          <circle cx="3" cy="12" r="2" stroke="#64748b" />
          <circle cx="21" cy="12" r="2" stroke="#64748b" />
        </svg>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
};

// Waypoint Map Marker
const createWaypointIcon = (label: string, isNext: boolean) => {
  return L.divIcon({
    className: 'custom-waypoint-marker',
    html: `
      <div style="width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; border-radius: 8px; font-family: monospace; font-size: 10px; font-weight: bold; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); ${
        isNext
          ? 'background: #06b6d4; color: #020617; border: 2px solid #67e8f9;'
          : 'background: #0f172a; color: #22d3ee; border: 1px solid rgba(34, 211, 238, 0.5);'
      }">
        ${label}
      </div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
};

// Map Auto Resizer lives in SharpEsriImageryLayer (shared with Internet Sandalwood)

// Map Fly-To and Pan Controller
const MapFlyController: React.FC<{
  center: [number, number] | null;
  zoom?: number;
  fitBoundsGeoJson?: GeoJSON.GeoJsonObject | null;
}> = ({ center, zoom, fitBoundsGeoJson }) => {
  const map = useMap();

  useEffect(() => {
    if (!map) return;
    if (fitBoundsGeoJson) {
      try {
        const layer = L.geoJSON(fitBoundsGeoJson);
        const bounds = layer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [50, 50], maxZoom: 18, duration: 1.2 });
          return;
        }
      } catch (e) {
        console.debug('Fit bounds error:', e);
      }
    }
    if (center) {
      map.flyTo(center, zoom || 16, { duration: 1.1 });
    }
  }, [center, zoom, fitBoundsGeoJson, map]);

  return null;
};

// Custom High-Precision Map Navigation Controls
const MapNavControls: React.FC<{
  onResetView: () => void;
}> = ({ onResetView }) => {
  const map = useMap();

  return (
    <div className="absolute top-4 left-4 z-[400] flex flex-col gap-1.5 pointer-events-auto">
      <div className="flex flex-col bg-[#111723]/95 border border-slate-700/80 rounded-xl overflow-hidden shadow-2xl">
        <button
          type="button"
          onClick={() => map.zoomIn()}
          className="p-2 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors border-b border-slate-800"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={() => map.zoomOut()}
          className="p-2 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
      </div>

      <button
        type="button"
        onClick={onResetView}
        className="p-2 bg-[#111723]/95 border border-slate-700/80 rounded-xl hover:bg-slate-800 text-slate-300 hover:text-white shadow-2xl transition-colors"
        title="Reset Tactical View"
      >
        <Target className="w-4 h-4" />
      </button>
    </div>
  );
};

// Map click / zoom — NO mousemove setState (that re-rendered the whole GIS map every pixel)
const MapEventDispatcher: React.FC<{
  onMapClick: (lat: number, lon: number) => void;
}> = ({ onMapClick }) => {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });

  return null;
};

/** Crown halos live in their own zoom listener — parent does not re-render on zoom */
const TreeCrownHaloLayer: React.FC<{
  treeFeatures: GISMapLayerResponse['features'];
}> = ({ treeFeatures }) => {
  const map = useMap();
  const [show, setShow] = useState(() => map.getZoom() >= 17 && treeFeatures.length <= 200);

  useMapEvents({
    zoomend() {
      const z = map.getZoom();
      setShow(z >= 17 && treeFeatures.length <= 200);
    },
  });

  if (!show) return null;

  return (
    <>
      {treeFeatures.map((tree) => {
        const coords = tree.geometry?.coordinates as number[];
        if (!coords || coords.length < 2) return null;
        const [lon, lat] = coords;
        const treeUid = String(tree.properties.id || tree.properties.tree_uid || '');
        const status = (tree.properties.status as TreeStatus) || 'HEALTHY';
        const color =
          status === 'AT_RISK' ? '#f59e0b' : status === 'DISEASED' ? '#ef4444' : '#10b981';
        const girthNum = typeof tree.properties.girth === 'number' ? tree.properties.girth : 28;
        const crownRadiusMeters = Math.max(3.5, girthNum / 10);
        return (
          <Circle
            key={`crown-${treeUid}`}
            center={[lat, lon]}
            radius={crownRadiusMeters}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: 0.14,
              weight: 1,
              dashArray: '2, 3',
            }}
          />
        );
      })}
    </>
  );
};

export const GoogleMapsGPSView: React.FC<GoogleMapsGPSViewProps> = ({
  mapData,
  selectedRegionId,
  onSelectTree,
  onAssignDetection,
  highlightedTreeUid,
  regions = [],
  aerialScanData = null,
  onClearAerialScan,
  onOpenAerialScanner,
  onSelectRegion,
}) => {

  const containerRef = useRef<HTMLDivElement>(null);
  const cursorLabelRef = useRef<HTMLSpanElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Basemap — Esri World Imagery. Do not swap hosts on zoom (that remounted tiles).
  const [mapType, setMapType] = useState<'hybrid' | 'satellite' | 'esri'>('esri');

  const tileLayers = {
    hybrid: {
      url: googleHybridUrl(),
      attribution: GOOGLE_HYBRID_ATTRIBUTION,
      maxZoom: TILE_PERF.maxZoom,
      maxNativeZoom: 21,
    },
    satellite: {
      url: googleSatelliteUrl(),
      attribution: GOOGLE_SAT_ATTRIBUTION,
      maxZoom: TILE_PERF.maxZoom,
      maxNativeZoom: 21,
    },
  };

  // Automatically focus on aerial scan coordinates when detected
  useEffect(() => {
    if (aerialScanData?.center_lat && aerialScanData?.center_lon) {
      setFlyTarget([aerialScanData.center_lat, aerialScanData.center_lon]);
      setFlyZoom(17);
    }
  }, [aerialScanData]);

  // Compute sub-meter geographic coordinates for top-down detected tree crowns
  const aerialCanopiesWithCoords = React.useMemo(() => {
    if (!aerialScanData?.canopies || aerialScanData.canopies.length === 0) return [];
    const cLat = aerialScanData.center_lat || DEFAULT_MAP_CENTER.latitude;
    const cLon = aerialScanData.center_lon || DEFAULT_MAP_CENTER.longitude;
    const latSpan = 0.0022;
    const lonSpan = 0.0022;

    return aerialScanData.canopies.map((canopy: AerialCrownBox) => {
      const cy = (canopy.ymin + canopy.ymax) / 2.0;
      const cx = (canopy.xmin + canopy.xmax) / 2.0;
      const lat = cLat + (0.5 - cy) * latSpan;
      const lon = cLon + (cx - 0.5) * lonSpan;
      return {
        ...canopy,
        lat,
        lon,
      };
    });
  }, [aerialScanData]);

  // Layer Filter State
  const [activeLayerFilter, setActiveLayerFilter] = useState<'all' | 'healthy' | 'at_risk' | 'devices'>('all');

  // Navigation Target & FlyTo State
  const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null);
  const [flyZoom, setFlyZoom] = useState<number>(14);

  // Live cursor coordinates written by CursorCoordsBinder (inside MapContainer)

  // User Live Geolocation
  const [userGPS, setUserGPS] = useState<GPSCoordinate | null>(null);
  const [isLocating, setIsLocating] = useState<boolean>(false);

  // Measurement Ruler Tool State
  const [isMeasuring, setIsMeasuring] = useState<boolean>(false);
  const [measurePoints, setMeasurePoints] = useState<[number, number][]>([]);

  // Search & Geocoding State
  const [searchQuery, setSearchQuery] = useState('');

  const [searchResults, setSearchResults] = useState<{ lat: number; lon: number; displayName: string; type?: string; category?: string }[]>([]);
  const [isSearchingOnline, setIsSearchingOnline] = useState(false);
  const [showSearchResults, setShowSearchResults] = useState(false);

  // Asset Inspection Drawer State
  const [selectedAsset, setSelectedAsset] = useState<{
    type: 'tree' | 'device' | 'region' | 'coordinate' | 'detection';
    id: string;
    name: string;
    lat: number;
    lon: number;
    rawProps?: Record<string, any>;
  } | null>(null);
  const [activeDrawerTab, setActiveDrawerTab] = useState<'overview' | 'climate' | 'navigation'>('overview');
  const [addressData, setAddressData] = useState<ReverseGeocodeResult | null>(null);

  // Real-Time Climate Telemetry State
  const [climateData, setClimateData] = useState<LiveClimateResponse | null>(null);
  const [loadingClimate, setLoadingClimate] = useState<boolean>(false);

  // Road Navigation Route State
  const [navRoute, setNavRoute] = useState<{
    targetName: string;
    targetCoords: [number, number];
    routeDetails: DetailedRouteResponse;
    bearing: number;
  } | null>(null);
  const [loadingRoute, setLoadingRoute] = useState<boolean>(false);

  // ==========================================
  // 🛸 AUTONOMOUS DRONE PATROL & HUD STATE
  // ==========================================
  const [isDronePatrolActive, setIsDronePatrolActive] = useState<boolean>(false);
  const [droneMission, setDroneMission] = useState<DronePatrolMissionResponse | null>(null);
  const [isPatrolPlaying, setIsPatrolPlaying] = useState<boolean>(false);
  const [patrolSpeedMult, setPatrolSpeedMult] = useState<number>(1);
  const [interceptedTargets, setInterceptedTargets] = useState<DroneMissionCanopyTarget[]>([]);
  const [, setLoadingMission] = useState<boolean>(false);
  const [droneTelemetry, setDroneTelemetry] = useState<DroneLiveTelemetry>({
    latitude: 13.9371,
    longitude: 75.5632,
    altitude_m: 45.0,
    speed_mps: 8.0,
    heading_deg: 90.0,
    pitch_deg: 0.0,
    roll_deg: 0.0,
    battery_pct: 100.0,
    elapsed_sec: 0,
    active_waypoint_index: 0,
    locked_target: null,
    status: 'STANDBY',
  });

  // Toggle Drone Autonomous Patrol Sweep
  const handleToggleDronePatrol = async () => {
    if (!isDronePatrolActive) {
      setIsDronePatrolActive(true);
      setLoadingMission(true);
      try {
        const mission = await satelliteApi.getDronePatrolMission('shivamogga_plantation', 8.0);
        setDroneMission(mission);
        if (mission.waypoints.length > 0) {
          const wp0 = mission.waypoints[0];
          setDroneTelemetry({
            latitude: wp0.latitude,
            longitude: wp0.longitude,
            altitude_m: wp0.altitude_m,
            speed_mps: mission.survey_speed_mps,
            heading_deg: wp0.leg_bearing_deg,
            pitch_deg: 0,
            roll_deg: 0,
            battery_pct: 100,
            elapsed_sec: 0,
            active_waypoint_index: 0,
            locked_target: null,
            status: 'STANDBY',
          });
          setFlyTarget([wp0.latitude, wp0.longitude]);
          setFlyZoom(17);
        }
      } catch (err) {
        console.error('Failed to load drone patrol mission:', err);
      } finally {
        setLoadingMission(false);
      }
    } else {
      setIsDronePatrolActive(false);
      setIsPatrolPlaying(false);
    }
  };

  // Autonomous Drone Flight Simulation Loop
  useEffect(() => {
    if (!isPatrolPlaying || !droneMission || droneMission.waypoints.length < 2) return;

    // 4 Hz, not 12.5 Hz: each flush re-renders the UAV marker and HUD. The tile
    // and tree layers are not watching zoom/pan, but they still sit in this tree.
    const intervalMs = 250;
    const timer = setInterval(() => {
      setDroneTelemetry((prev) => {
        const deltaSec = (intervalMs / 1000) * patrolSpeedMult;
        const newElapsed = prev.elapsed_sec + deltaSec;
        const totalDuration = droneMission.total_duration_sec;

        if (newElapsed >= totalDuration) {
          setIsPatrolPlaying(false);
          return {
            ...prev,
            elapsed_sec: totalDuration,
            battery_pct: Math.max(10, 100 - (totalDuration / 20)),
            status: 'COMPLETED',
          };
        }

        const waypoints = droneMission.waypoints;
        let legIdx = 0;
        for (let i = 0; i < waypoints.length - 1; i++) {
          if (newElapsed >= waypoints[i].eta_sec && newElapsed <= waypoints[i + 1].eta_sec) {
            legIdx = i;
            break;
          }
          if (i === waypoints.length - 2 && newElapsed > waypoints[i + 1].eta_sec) {
            legIdx = i;
          }
        }

        const wpA = waypoints[legIdx];
        const wpB = waypoints[legIdx + 1];
        const legDuration = Math.max(0.1, wpB.eta_sec - wpA.eta_sec);
        const legProgress = Math.min(1.0, Math.max(0.0, (newElapsed - wpA.eta_sec) / legDuration));

        const curLat = wpA.latitude + (wpB.latitude - wpA.latitude) * legProgress;
        const curLon = wpA.longitude + (wpB.longitude - wpA.longitude) * legProgress;
        const curHeading = wpB.leg_bearing_deg;

        const pitch = Math.sin(newElapsed * 1.5) * 1.8;
        const roll = Math.cos(newElapsed * 2.0) * 1.4;
        const battery = Math.max(15, 100 - (newElapsed / totalDuration) * 14);

        const locked = droneMission.canopy_targets.find(
          (t) => Math.abs(t.interception_time_sec - newElapsed) < 1.8 * patrolSpeedMult
        ) || null;

        if (locked) {
          setInterceptedTargets((old) => {
            if (old.some((item) => item.box_id === locked.box_id)) return old;
            return [locked, ...old];
          });
        }

        return {
          latitude: curLat,
          longitude: curLon,
          altitude_m: wpB.altitude_m,
          speed_mps: droneMission.survey_speed_mps,
          heading_deg: curHeading,
          pitch_deg: pitch,
          roll_deg: roll,
          battery_pct: battery,
          elapsed_sec: newElapsed,
          active_waypoint_index: legIdx + 1,
          locked_target: locked,
          status: 'FLYING',
        };
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isPatrolPlaying, droneMission, patrolSpeedMult]);

  // Quick Fly-to Forest Presets
  const presets = [
    { name: 'Marayoor (Kerala)', lat: 10.2825, lon: 77.1620, zoom: 15 },
    { name: 'Coorg (Western Ghats)', lat: 12.4435, lon: 75.6880, zoom: 15 },
    { name: 'Shivamogga Reserve', lat: 13.9100, lon: 75.4800, zoom: 15 },
    { name: 'Mysore Sandalwood Belt', lat: 12.3850, lon: 76.6850, zoom: 15 },
    { name: 'Sirsi Bio-Corridor', lat: 14.6196, lon: 74.8354, zoom: 15 },
  ];

  // Geolocation Handler
  const startGPSLocation = useCallback(() => {
    if (!navigator.geolocation) return;
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords: GPSCoordinate = {
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          heading: pos.coords.heading || undefined,
          speed: pos.coords.speed || undefined,
        };
        setUserGPS(coords);
        setIsLocating(false);
        setFlyTarget([coords.latitude, coords.longitude]);
        setFlyZoom(16);
      },
      () => {
        const fallbackGPS: GPSCoordinate = {
          latitude: DEFAULT_MAP_CENTER.latitude,
          longitude: DEFAULT_MAP_CENTER.longitude,
          accuracy: 4.2,
        };
        setUserGPS(fallbackGPS);
        setFlyTarget([fallbackGPS.latitude, fallbackGPS.longitude]);
        setFlyZoom(16);
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    );
  }, []);

  // Inspect Point & Load Telemetry
  const inspectPoint = async (
    lat: number,
    lon: number,
    name: string,
    type: 'tree' | 'device' | 'region' | 'coordinate' | 'detection',
    id: string,
    rawProps?: Record<string, any>
  ) => {
    setSelectedAsset({ type, id, name, lat, lon, rawProps });
    setActiveDrawerTab('overview');
    setLoadingClimate(true);
    try {
      const [clim, addr] = await Promise.all([
        satelliteApi.getLiveWeather(lat, lon),
        fetchNominatimReverseGeocode(lat, lon),
      ]);
      setClimateData(clim);
      setAddressData(addr);
    } catch (e) {
      console.error('Inspection failed:', e);
    } finally {
      setLoadingClimate(false);
    }
  };

  // Start Real Road Navigation Route
  const startNavigation = async (targetLat: number, targetLon: number, targetName: string) => {
    const startLat = userGPS ? userGPS.latitude : DEFAULT_MAP_CENTER.latitude;
    const startLon = userGPS ? userGPS.longitude : DEFAULT_MAP_CENTER.longitude;

    setLoadingRoute(true);
    try {
      const routeRes = await fetchOSRMRoute(startLat, startLon, targetLat, targetLon);
      const bearing = calculateBearing(startLat, startLon, targetLat, targetLon);

      setNavRoute({
        targetName,
        targetCoords: [targetLat, targetLon],
        routeDetails: routeRes,
        bearing,
      });

      setActiveDrawerTab('navigation');
      setFlyTarget([targetLat, targetLon]);
      setFlyZoom(15);
    } catch (err) {
      console.error('Navigation error:', err);
    } finally {
      setLoadingRoute(false);
    }
  };

  // Map Click
  const handleMapClick = (lat: number, lon: number) => {
    if (isMeasuring) {
      setMeasurePoints((prev) => [...prev, [lat, lon]]);
      return;
    }
    inspectPoint(lat, lon, `Location (${lat.toFixed(4)}, ${lon.toFixed(4)})`, 'coordinate', `${lat.toFixed(4)},${lon.toFixed(4)}`);
  };

  // Debounce ref so we don't hammer Nominatim on every keystroke
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Search
  const handleSearchChange = (val: string) => {
    setSearchQuery(val);

    // Clear existing debounce timer
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);

    if (val.trim().length < 2) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }

    // Debounce: wait 400ms after user stops typing before hitting API
    searchDebounceRef.current = setTimeout(async () => {
      setIsSearchingOnline(true);
      try {
        const results = await fetchNominatimSearch(val.trim());
        setSearchResults(results);
        setShowSearchResults(true);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearchingOnline(false);
      }
    }, 400);
  };

  const handleSelectSearchResult = (result: { lat: number; lon: number; displayName: string }) => {
    setFlyTarget([result.lat, result.lon]);
    setFlyZoom(16);
    inspectPoint(result.lat, result.lon, result.displayName.split(',')[0], 'coordinate', 'SEARCH');
    setShowSearchResults(false);
    setSearchQuery(result.displayName.split(',')[0]);
  };

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) return;

    // Direct coordinate input
    const coordMatch = q.match(/^([-+]?\d+(\.\d+)?)[,\s]+([-+]?\d+(\.\d+)?)$/);
    if (coordMatch) {
      const lat = parseFloat(coordMatch[1]);
      const lon = parseFloat(coordMatch[3]);
      setFlyTarget([lat, lon]);
      setFlyZoom(17);
      inspectPoint(lat, lon, `GPS ${lat.toFixed(5)}, ${lon.toFixed(5)}`, 'coordinate', 'COORD');
      setShowSearchResults(false);
      return;
    }

    // If dropdown already has results, use the top one
    if (searchResults.length > 0) {
      handleSelectSearchResult(searchResults[0]);
      return;
    }

    // Otherwise fire a live search right now on Enter
    setIsSearchingOnline(true);
    try {
      const results = await fetchNominatimSearch(q);
      if (results.length > 0) {
        setSearchResults(results);
        setShowSearchResults(true);
        handleSelectSearchResult(results[0]);
      } else {
        setSearchResults([]);
        setShowSearchResults(true);
      }
    } finally {
      setIsSearchingOnline(false);
    }
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      }
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
      setIsFullscreen(false);
    }
  };

  const totalMeasuredDistance = measurePoints.reduce((acc, curr, idx) => {
    if (idx === 0) return 0;
    const prev = measurePoints[idx - 1];
    return acc + calculateHaversineDistance(prev[0], prev[1], curr[0], curr[1]);
  }, 0);

  // Features
  const features = mapData?.features || [];

  const treeFeatures = React.useMemo(() => {
    return features.filter((f) => {
      const isTree = f.properties.type === 'tree' || f.properties.layer_type === 'SANDALWOOD_TREE';
      if (!isTree) return false;
      const status = f.properties.status;
      if (activeLayerFilter === 'all') return true;
      if (activeLayerFilter === 'healthy') return status === 'HEALTHY';
      if (activeLayerFilter === 'at_risk') return status === 'AT_RISK' || status === 'DISEASED';
      return false;
    });
  }, [features, activeLayerFilter]);

  const detectionFeatures = React.useMemo(() => {
    return features.filter((f) => {
      return f.properties.type === 'detection' || f.properties.layer_type === 'TREE_DETECTION';
    });
  }, [features]);

  const deviceFeatures = React.useMemo(() => {
    return features.filter((f) => {
      const isDevice = f.properties.type === 'device' || f.properties.layer_type === 'IOT_DEVICE';
      return isDevice && (activeLayerFilter === 'all' || activeLayerFilter === 'devices');
    });
  }, [features, activeLayerFilter]);

  const getTreeColor = (status?: string) => {
    switch (status) {
      case 'HEALTHY':
        return '#10b981';
      case 'AT_RISK':
        return '#f59e0b';
      case 'DISEASED':
        return '#ef4444';
      default:
        return '#10b981';
    }
  };

  const treeClusterPoints: ClusterPoint[] = React.useMemo(() => {
    return treeFeatures.flatMap((tree) => {
      const coords = tree.geometry?.coordinates as number[];
      if (!coords || coords.length < 2) return [];
      const [lon, lat] = coords;
      const treeUid = String(tree.properties.id || tree.properties.tree_uid || '');
      const status = (tree.properties.status as TreeStatus) || 'HEALTHY';
      const color = getTreeColor(status);
      return [
        {
          id: `tree-${treeUid}`,
          lat,
          lon,
          color,
          fillColor: color,
          radius: 6,
          weight: 1,
          tooltipHtml: `<div style="font-size:11px"><strong>${treeUid}</strong><br/><em>Santalum album · ${status}</em></div>`,
          onClick: () => {
            inspectPoint(lat, lon, `Tree ${treeUid}`, 'tree', treeUid, tree.properties as Record<string, any>);
            if (onSelectTree) onSelectTree(treeUid);
          },
        },
      ];
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [treeFeatures, onSelectTree]);

  const highlightedTreeFeature = React.useMemo(() => {
    if (!highlightedTreeUid) return null;
    return treeFeatures.find((t) => {
      const uid = String(t.properties.id || t.properties.tree_uid || '');
      return uid === highlightedTreeUid;
    }) || null;
  }, [treeFeatures, highlightedTreeUid]);

  const detectionClusterPoints: ClusterPoint[] = React.useMemo(() => {
    return detectionFeatures.flatMap((det) => {
      const coords = det.geometry?.coordinates as number[];
      if (!coords || coords.length < 2) return [];
      const [lon, lat] = coords;
      const detUid = String(det.properties.detection_uid || det.properties.id || '');
      return [
        {
          id: `det-${detUid}`,
          lat,
          lon,
          color: '#f59e0b',
          fillColor: '#fbbf24',
          radius: 5.5,
          weight: 1.5,
          dashArray: '4, 3',
          tooltipHtml:
            '<div style="font-size:11px"><strong style="color:#fcd34d">Unassigned detection</strong><br/>No Tree ID — click to assign</div>',
          onClick: () => {
            inspectPoint(
              lat,
              lon,
              'Unassigned detection',
              'detection',
              detUid,
              det.properties as Record<string, any>
            );
            if (onAssignDetection) {
              onAssignDetection({
                detectionUid: detUid,
                latitude: lat,
                longitude: lon,
                species: String(det.properties.species || 'Santalum album'),
                source: String(det.properties.source || 'DETECTION'),
              });
            }
          },
        },
      ];
    });
  }, [detectionFeatures, onAssignDetection]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full min-h-[600px] rounded-2xl overflow-hidden border border-slate-800 bg-[#0a0d14] font-sans select-none flex flex-col ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : ''
      }`}
    >
      {/* 1. TOP DEDICATED APPLICATION CONTROL BAR (Cleanly Separated, Zero Collision) */}
      <div className="bg-[#111723] p-2.5 px-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2.5 z-20 shadow-md">
        {/* Left: Search Bar & Preset Quick-Links */}
        <div className="flex items-center gap-2 flex-1 max-w-xl">
          <div className="relative w-64 sm:w-72">
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-700 text-xs">
              <Search className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                onFocus={() => searchResults.length > 0 && setShowSearchResults(true)}
                placeholder="Search places, trees, coords..."
                className="bg-transparent text-slate-200 placeholder-slate-500 focus:outline-none w-full text-xs"
              />
              {isSearchingOnline && (
                <RefreshCw className="w-3 h-3 animate-spin text-slate-400 flex-shrink-0" />
              )}
            </form>

            {showSearchResults && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-slate-950 border border-slate-700 rounded-xl p-1 shadow-2xl max-h-56 overflow-y-auto text-xs z-50 divide-y divide-slate-900/60">
                {searchResults.length === 0 ? (
                  <div className="p-3 text-center text-slate-500 flex items-center justify-center gap-2">
                    <Search className="w-3.5 h-3.5" />
                    <span>No places found — try a different name</span>
                  </div>
                ) : (
                  searchResults.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleSelectSearchResult(item)}
                      className="p-2 rounded-lg hover:bg-slate-800 cursor-pointer flex items-center gap-2 text-slate-300 transition-colors group"
                    >
                      <MapPin className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 group-hover:text-emerald-300" />
                      <span className="truncate flex-1">{item.displayName}</span>
                      {item.category && item.category !== 'coordinate' && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-500 flex-shrink-0 capitalize">{item.category}</span>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Quick Presets Pills */}
          <div className="hidden xl:flex items-center gap-1">
            {presets.map((p) => (
              <button
                key={p.name}
                type="button"
                onClick={() => {
                  setFlyTarget([p.lat, p.lon]);
                  setFlyZoom(p.zoom);
                  inspectPoint(p.lat, p.lon, p.name, 'region', p.name);
                }}
                className="px-2.5 py-1 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 text-[11px] font-medium transition-colors whitespace-nowrap bg-slate-900/60 border border-slate-800"
              >
                {p.name.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Map Controls & Street View Toggle */}
        <div className="flex items-center gap-2">
          {/* Basemap Selector */}
          <div className="hidden sm:flex items-center bg-slate-900 p-0.5 rounded-xl border border-slate-800 text-[11px]">
            {(['hybrid', 'satellite', 'esri'] as const).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setMapType(type)}
                className={`px-2.5 py-1 rounded-lg capitalize transition-all font-medium ${
                  mapType === type
                    ? 'bg-slate-800 text-slate-100 font-bold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {type === 'esri' ? 'Esri Imagery' : type}
              </button>
            ))}
          </div>

          {/* AI Aerial Drone Radar Scanner Trigger */}
          {onOpenAerialScanner && (
            <button
              type="button"
              onClick={onOpenAerialScanner}
              className={`p-1.5 px-2.5 rounded-xl border text-xs font-semibold transition-all flex items-center gap-1.5 ${
                aerialScanData
                  ? 'bg-emerald-600 text-white border-emerald-400 shadow-glow-emerald'
                  : 'bg-slate-900 border-emerald-800/80 text-emerald-400 hover:text-white hover:bg-emerald-950/60'
              }`}
              title="Launch AI Aerial Drone Tree Crown Scanner (Coordinate Attention YOLOv5s)"
            >
              <Radio className={`w-3.5 h-3.5 ${aerialScanData ? 'animate-pulse' : ''}`} />
              <span className="hidden sm:inline">AI Drone Scan</span>
            </button>
          )}

          {/* Autonomous Drone Patrol & Tactical HUD Button */}
          <button
            type="button"
            onClick={handleToggleDronePatrol}
            className={`p-1.5 px-2.5 rounded-xl border text-xs font-semibold transition-all flex items-center gap-1.5 ${
              isDronePatrolActive
                ? 'bg-cyan-500 text-slate-950 border-cyan-300 font-bold shadow-glow-cyan'
                : 'bg-slate-900 border-cyan-800/80 text-cyan-400 hover:text-white hover:bg-cyan-950/60'
            }`}
            title="Launch Autonomous UAV Drone Flight Patrol & Tactical HUD"
          >
            <Plane className={`w-3.5 h-3.5 ${isDronePatrolActive ? 'animate-pulse' : ''}`} />
            <span className="hidden sm:inline">Drone Patrol</span>
          </button>



          {/* Fullscreen Toggle */}
          <button
            type="button"
            onClick={toggleFullscreen}
            className="p-1.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Active Aerial Drone AI Radar Scan Banner */}
      {aerialScanData && (
        <div className="p-2.5 px-4 bg-gradient-to-r from-emerald-950/95 via-slate-900/95 to-[#111723] border-b border-emerald-500/50 flex flex-wrap items-center justify-between gap-3 z-10 text-xs shadow-md">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping flex-shrink-0" />
            <div className="flex items-center gap-2 flex-wrap font-mono">
              <span className="font-bold text-emerald-300">🛰️ AI DRONE RADAR ACTIVE:</span>
              <span className="text-slate-200 font-semibold">{aerialScanData.title}</span>
              <span className="text-slate-500">&bull;</span>
              <span className="text-emerald-400 font-bold">{aerialScanData.sandalwood_count} Sandalwood Crowns</span>
              <span className="text-slate-500">&bull;</span>
              <span className="text-amber-400 font-bold">{aerialScanData.host_trees_count || 0} Host Trees</span>
              <span className="text-slate-500">&bull;</span>
              <span className="text-slate-300 font-bold">{aerialScanData.estimated_sandalwood_biomass_kg} kg Biomass</span>
              <span className="text-slate-500">&bull;</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-900/80 text-emerald-300 text-[10px] border border-emerald-700/60 font-semibold">
                {aerialScanData.pipeline_architecture}
              </span>
            </div>
          </div>

          {onClearAerialScan && (
            <button
              type="button"
              onClick={onClearAerialScan}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-rose-950/60 text-slate-300 hover:text-rose-300 text-[11px] font-medium border border-slate-700 hover:border-rose-800/60 transition-colors"
            >
              Clear Scan
            </button>
          )}
        </div>
      )}

      {/* 2. MAIN GIS VIEWPORT
          Absolute inset (not h-full) so Leaflet gets a real pixel height.
          h-full inside this flex column resolved to 0 and tiles never painted. */}
      <div className="flex-1 min-h-0 relative">
        <div className="absolute inset-0">
          <MapContainer
            center={[DEFAULT_MAP_CENTER.latitude, DEFAULT_MAP_CENTER.longitude]}
            zoom={8}
            minZoom={MAP_CONSTRAINTS.minZoom}
            maxZoom={MAP_CONSTRAINTS.maxZoom}
            zoomSnap={MAP_CONSTRAINTS.zoomSnap}
            zoomDelta={MAP_CONSTRAINTS.zoomDelta}
            wheelPxPerZoomLevel={MAP_CONSTRAINTS.wheelPxPerZoomLevel}
            scrollWheelZoom={true}
            preferCanvas={true}
            zoomAnimation={true}
            fadeAnimation={false}
            markerZoomAnimation={false}
            className="w-full h-full"
            style={{ height: '100%', width: '100%' }}
          >
            {mapType === 'esri' ? (
              <SharpEsriImageryLayer showLabels />
            ) : (
              <TileLayer
                key={mapType}
                attribution={tileLayers[mapType].attribution}
                url={tileLayers[mapType].url}
                maxZoom={tileLayers[mapType].maxZoom}
                maxNativeZoom={tileLayers[mapType].maxNativeZoom}
                subdomains={[...GOOGLE_TILE_SUBDOMAINS]}
                detectRetina={false}
                updateWhenZooming={TILE_PERF.updateWhenZooming}
                updateWhenIdle={TILE_PERF.updateWhenIdle}
                keepBuffer={TILE_PERF.keepBuffer}
                updateInterval={TILE_PERF.updateInterval}
              />
            )}

            <MapAutoResizer />
            <CursorCoordsBinder labelRef={cursorLabelRef} />
            <MapFlyController
              center={flyTarget}
              zoom={flyZoom}
            />
            <MapNavControls onResetView={() => { setFlyTarget([DEFAULT_MAP_CENTER.latitude, DEFAULT_MAP_CENTER.longitude]); setFlyZoom(DEFAULT_MAP_CENTER.zoom); }} />
            <MapEventDispatcher onMapClick={handleMapClick} />





            {/* User GPS Pin */}
            {userGPS && (
              <>
                <CircleMarker
                  center={[userGPS.latitude, userGPS.longitude]}
                  radius={8}
                  pathOptions={{ color: '#ffffff', fillColor: '#10b981', fillOpacity: 1, weight: 2.5 }}
                >
                  <Tooltip permanent={false} direction="top">
                    <span className="text-xs font-mono">My GPS (±{Math.round(userGPS.accuracy || 4)}m)</span>
                  </Tooltip>
                </CircleMarker>
                <Circle
                  center={[userGPS.latitude, userGPS.longitude]}
                  radius={userGPS.accuracy || 20}
                  pathOptions={{ color: '#10b981', fillColor: '#10b981', fillOpacity: 0.12, weight: 1 }}
                />
              </>
            )}

            {/* Navigation Route */}
            <RoutingOverlayLayer navRoute={navRoute} />

            {/* Measuring Polyline and Points */}
            <MapMeasurementTool points={measurePoints} />

            {/* Registered Sandalwood Trees — clustered for smooth zoom/pan */}
            <MarkerClusterLayer
              points={treeClusterPoints}
              disableClusteringAtZoom={17}
            />
            {highlightedTreeFeature && (() => {
              const coords = highlightedTreeFeature.geometry?.coordinates as number[];
              if (!coords || coords.length < 2) return null;
              const [lon, lat] = coords;
              return (
                <CircleMarker
                  center={[lat, lon]}
                  radius={10}
                  pathOptions={{
                    color: '#ffffff',
                    fillColor: '#34d399',
                    fillOpacity: 1,
                    weight: 2.5,
                  }}
                />
              );
            })()}
            <TreeCrownHaloLayer treeFeatures={treeFeatures} />

            {/* Unassigned detections — clustered */}
            <MarkerClusterLayer
              points={detectionClusterPoints}
              disableClusteringAtZoom={16}
            />

            {/* IoT Gateways */}
            {deviceFeatures.map((dev) => {
              const coords = dev.geometry?.coordinates as number[];
              if (!coords || coords.length < 2) return null;
              const [lon, lat] = coords;
              const devId = String(dev.properties.id || dev.properties.device_id || '');
              const isHighlighted = selectedAsset?.id === devId;

              return (
                <CircleMarker
                  key={`dev-${devId}`}
                  center={[lat, lon]}
                  radius={isHighlighted ? 8 : 6}
                  eventHandlers={{
                    click: () => {
                      inspectPoint(lat, lon, `Device ${devId}`, 'device', devId, dev.properties as Record<string, any>);
                    },
                  }}
                  pathOptions={{
                    color: isHighlighted ? '#ffffff' : '#38bdf8',
                    fillColor: '#38bdf8',
                    fillOpacity: 0.9,
                    weight: 2,
                  }}
                >
                  <Tooltip direction="top" offset={[0, -6]}>
                    <span className="text-xs font-mono">{devId} (Online Gateway)</span>
                  </Tooltip>
                </CircleMarker>
              );
            })}

            {/* 🛰️ AI Aerial Drone Sandalwood Canopies (Coordinate Attention YOLOv5s) */}
            {aerialCanopiesWithCoords.map((canopy: AerialCrownBox, idx: number) => {
              if (canopy.lat === undefined || canopy.lon === undefined) return null;
              const isSw = canopy.is_sandalwood;
              const isHost = canopy.is_host_tree;
              const crownColor = isSw ? '#10b981' : (isHost ? '#f59e0b' : '#94a3b8');
              const crownRadius = Math.max(2.5, (canopy.crown_diameter_m || 4.0) / 2.0);
              const isHighlighted = selectedAsset?.id === canopy.box_id;

              return (
                <React.Fragment key={`aerial-canopy-${canopy.box_id || idx}`}>
                  {/* Outer Canopy Spread Circle (Physical Radius in Meters) */}
                  <Circle
                    center={[canopy.lat, canopy.lon]}
                    radius={crownRadius}
                    pathOptions={{
                      color: crownColor,
                      fillColor: crownColor,
                      fillOpacity: isSw ? 0.32 : 0.18,
                      weight: isHighlighted ? 2.5 : 1.5,
                      dashArray: isSw ? undefined : '3, 4',
                    }}
                  />

                  {/* High-Precision Center Pin with Radar Ping */}
                  <CircleMarker
                    center={[canopy.lat, canopy.lon]}
                    radius={isHighlighted ? 9 : (isSw ? 6.5 : 5)}
                    eventHandlers={{
                      click: () => {
                        inspectPoint(
                          canopy.lat!,
                          canopy.lon!,
                          'Unassigned aerial detection',
                          'detection',
                          canopy.box_id,
                          {
                            ...canopy,
                            source: 'UAV_DRONE_AI_RADAR',
                            architecture: aerialScanData?.pipeline_architecture || 'Improved-YOLOv5s-CA',
                          }
                        );
                        const evidenceOrigin = aerialScanData?.evidence_origin
                          || (aerialScanData?.pipeline_architecture?.startsWith('SIMULATED') ? 'SIMULATED' : undefined);
                        if (onAssignDetection && canopy.is_sandalwood && evidenceOrigin !== 'SIMULATED') {
                          onAssignDetection({
                            latitude: canopy.lat!,
                            longitude: canopy.lon!,
                            species: canopy.species_scientific || 'Santalum album',
                            source: 'UAV_DRONE_AI_RADAR',
                            evidenceOrigin,
                          });
                        }
                      },
                    }}
                    pathOptions={{
                      color: isHighlighted ? '#ffffff' : crownColor,
                      fillColor: crownColor,
                      fillOpacity: 0.95,
                      weight: isHighlighted ? 3 : 1.5,
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -8]} opacity={0.98}>
                      <div className="text-[11px] font-sans p-1 space-y-1 min-w-[170px]">
                        <div className="flex items-center justify-between gap-2 border-b border-slate-700/60 pb-1">
                          <strong className="font-mono text-amber-300 font-bold">Unassigned</strong>
                          <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-[9px] font-bold font-mono">
                            {(canopy.confidence * 100).toFixed(1)}% AI
                          </span>
                        </div>
                        <div className="text-slate-200 font-semibold italic text-xs">
                          {canopy.species_scientific}
                        </div>
                        <div className="text-amber-200/90 text-[10px]">No Tree ID — click to assign</div>
                        <div className="grid grid-cols-2 gap-1 pt-1 border-t border-slate-800 text-[10px] font-mono text-slate-300">
                          <div>Diam: <span className="text-emerald-400 font-semibold">{canopy.crown_diameter_m}m</span></div>
                          <div>Area: <span className="text-emerald-400 font-semibold">{canopy.canopy_area_sqm}m²</span></div>
                        </div>
                      </div>
                    </Tooltip>
                  </CircleMarker>
                </React.Fragment>
              );
            })}

            {/* Autonomous Drone Patrol Flight Path & Waypoints */}
            {isDronePatrolActive && droneMission && (
              <>
                {/* Serpentine Survey Polyline */}
                <Polyline
                  positions={droneMission.waypoints.map((wp) => [wp.latitude, wp.longitude])}
                  pathOptions={{
                    color: '#22d3ee',
                    weight: 2.5,
                    dashArray: '6, 8',
                    opacity: 0.85,
                  }}
                />

                {/* Waypoint Markers */}
                {droneMission.waypoints.map((wp, idx) => (
                  <Marker
                    key={`patrol-wp-${wp.waypoint_id}`}
                    position={[wp.latitude, wp.longitude]}
                    icon={createWaypointIcon(wp.waypoint_id, idx === droneTelemetry.active_waypoint_index)}
                  >
                    <Tooltip direction="top" offset={[0, -14]} opacity={0.95}>
                      <div className="text-[10px] font-mono p-0.5">
                        <strong className="text-cyan-300 block">{wp.waypoint_id} ({wp.action})</strong>
                        <span className="text-slate-400">Alt: {wp.altitude_m}m &bull; ETA: {wp.eta_sec}s</span>
                      </div>
                    </Tooltip>
                  </Marker>
                ))}

                {/* Drone Ground Nadir Sensor Footprint */}
                <Circle
                  center={[droneTelemetry.latitude, droneTelemetry.longitude]}
                  radius={18}
                  pathOptions={{
                    color: droneTelemetry.locked_target ? '#10b981' : '#22d3ee',
                    fillColor: droneTelemetry.locked_target ? '#10b981' : '#22d3ee',
                    fillOpacity: droneTelemetry.locked_target ? 0.35 : 0.15,
                    weight: 1.5,
                    dashArray: '3, 4',
                  }}
                />

                {/* Animated Drone UAV Marker */}
                <Marker
                  position={[droneTelemetry.latitude, droneTelemetry.longitude]}
                  icon={createDroneUAVIcon(droneTelemetry.heading_deg)}
                  zIndexOffset={1000}
                >
                  <Tooltip direction="top" offset={[0, -20]} opacity={0.95} permanent>
                    <div className="text-[10px] font-mono p-0.5 text-center">
                      <strong className="text-cyan-300 block">{droneMission.drone_hardware_id}</strong>
                      <span className="text-slate-300">{droneTelemetry.altitude_m.toFixed(0)}m AGL &bull; {droneTelemetry.speed_mps.toFixed(0)}m/s</span>
                    </div>
                  </Tooltip>
                </Marker>
              </>
            )}
          </MapContainer>

          {/* Floating Tactical Drone HUD Console */}
          {isDronePatrolActive && droneMission && (
            <div className="absolute bottom-16 left-4 right-4 z-[450] max-w-5xl mx-auto pointer-events-auto shadow-2xl">
              <DroneTacticalHUD
                mission={droneMission}
                telemetry={droneTelemetry}
                isPlaying={isPatrolPlaying}
                speedMultiplier={patrolSpeedMult}
                onTogglePlay={() => setIsPatrolPlaying(!isPatrolPlaying)}
                onReset={() => {
                  setIsPatrolPlaying(false);
                  if (droneMission.waypoints.length > 0) {
                    const wp0 = droneMission.waypoints[0];
                    setDroneTelemetry({
                      latitude: wp0.latitude,
                      longitude: wp0.longitude,
                      altitude_m: wp0.altitude_m,
                      speed_mps: droneMission.survey_speed_mps,
                      heading_deg: wp0.leg_bearing_deg,
                      pitch_deg: 0,
                      roll_deg: 0,
                      battery_pct: 100,
                      elapsed_sec: 0,
                      active_waypoint_index: 0,
                      locked_target: null,
                      status: 'STANDBY',
                    });
                    setFlyTarget([wp0.latitude, wp0.longitude]);
                    setFlyZoom(17);
                  }
                }}
                onChangeSpeed={(mult) => setPatrolSpeedMult(mult)}
                onClose={() => {
                  setIsDronePatrolActive(false);
                  setIsPatrolPlaying(false);
                }}
                interceptedTargets={interceptedTargets}
              />
            </div>
          )}

          {/* Bottom HUD: Coordinates & Locate Me */}
          <div className="absolute bottom-3 left-4 right-4 z-[400] flex items-center justify-between pointer-events-none">
            <div className="pointer-events-auto px-3.5 py-1.5 rounded-xl bg-[#111723]/95 border border-slate-800 text-[11px] font-mono text-slate-400 shadow-xl flex items-center gap-3">
              <span ref={cursorLabelRef}>Move cursor for live GPS</span>
              <span>&bull;</span>
              <span className="text-emerald-400 font-semibold">Sub-Meter GIS Precision</span>
            </div>

            <div className="pointer-events-auto">
              <button
                type="button"
                onClick={startGPSLocation}
                className={`p-2 px-3 rounded-xl border shadow-2xl flex items-center gap-1.5 transition-colors text-xs font-medium ${
                  userGPS
                    ? 'bg-emerald-600 text-white border-emerald-500 font-semibold'
                    : 'bg-[#111723]/95 border-slate-700/80 text-slate-300 hover:text-white'
                }`}
                title="Locate Me via GPS"
              >
                <LocateFixed className={`w-3.5 h-3.5 ${isLocating ? 'animate-spin' : ''}`} />
                <span>Locate Me</span>
              </button>
            </div>
          </div>
        </div>

      </div>

      {/* 3. ASSET INSPECTION SIDE DRAWER */}
      {selectedAsset && (
        <div className="absolute top-16 right-4 bottom-12 z-[450] w-84 bg-[#111723] rounded-2xl border border-slate-700/80 shadow-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-right-3">
          {/* Header */}
          <div className="p-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
            <div className="truncate">
              <h3 className="font-semibold text-sm text-slate-100 truncate">{selectedAsset.name}</h3>
              <p className="text-[10px] font-mono text-slate-400">
                {selectedAsset.lat.toFixed(5)}°N, {selectedAsset.lon.toFixed(5)}°E
              </p>
            </div>
            <button
              type="button"
              onClick={() => setSelectedAsset(null)}
              className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Tab Control */}
          <div className="flex border-b border-slate-800 p-1 bg-slate-950/40 text-xs">
            <button
              type="button"
              onClick={() => setActiveDrawerTab('overview')}
              className={`flex-1 py-1.5 rounded-lg font-medium transition-colors ${
                activeDrawerTab === 'overview' ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Overview
            </button>
            <button
              type="button"
              onClick={() => setActiveDrawerTab('climate')}
              className={`flex-1 py-1.5 rounded-lg font-medium transition-colors ${
                activeDrawerTab === 'climate' ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Weather
            </button>
            <button
              type="button"
              onClick={() => setActiveDrawerTab('navigation')}
              className={`flex-1 py-1.5 rounded-lg font-medium transition-colors ${
                activeDrawerTab === 'navigation' ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Route
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-3.5 space-y-3 text-xs">
            {activeDrawerTab === 'overview' && (
              <div className="space-y-3">
                {addressData && (
                  <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
                    <span className="text-[10px] text-slate-500 uppercase font-mono block">Administrative Location</span>
                    <p className="font-medium text-slate-200 text-xs">
                      {addressData.village || addressData.suburb || 'Agroforestry Plot'}
                    </p>
                    <p className="text-[10px] text-slate-400 truncate">
                      {addressData.county ? `${addressData.county}, ` : ''}{addressData.state}, {addressData.country}
                    </p>
                  </div>
                )}

                {selectedAsset.type === 'tree' && selectedAsset.rawProps && (
                  <div className="grid grid-cols-2 gap-2 font-mono">
                    <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Health</span>
                      <span className="text-xs font-semibold text-emerald-400">
                        {selectedAsset.rawProps.status || 'HEALTHY'}
                      </span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Est. Age</span>
                      <span className="text-xs font-semibold text-slate-200">
                        {selectedAsset.rawProps.age || selectedAsset.rawProps.estimated_age_years || 12} yrs
                      </span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Girth</span>
                      <span className="text-xs font-semibold text-slate-200">
                        {selectedAsset.rawProps.girth || selectedAsset.rawProps.girth_cm || 28} cm
                      </span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Canopy</span>
                      <span className="text-xs font-semibold text-emerald-400">
                        {(((selectedAsset.rawProps.girth || 28) / 10)).toFixed(1)}m Footprint
                      </span>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => startNavigation(selectedAsset.lat, selectedAsset.lon, selectedAsset.name)}
                    className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Route className="w-3.5 h-3.5" />
                    <span>Turn-by-Turn GPS Directions</span>
                  </button>
                </div>
              </div>
            )}

            {activeDrawerTab === 'climate' && (
              <div className="space-y-2.5">
                {loadingClimate ? (
                  <div className="p-6 text-center text-slate-400 text-xs">
                    <RefreshCw className="w-4 h-4 animate-spin text-emerald-400 mx-auto mb-1.5" />
                    <span>Loading Open-Meteo satellite climate...</span>
                  </div>
                ) : climateData ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2 font-mono">
                      <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                        <span className="text-[10px] text-slate-500 block">Air Temp</span>
                        <span className="text-sm font-bold text-slate-100">{climateData.temperature_celsius}°C</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                        <span className="text-[10px] text-slate-500 block">Humidity</span>
                        <span className="text-sm font-bold text-slate-100">{climateData.relative_humidity_percent}%</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                        <span className="text-[10px] text-slate-500 block">Surface Soil</span>
                        <span className="text-sm font-bold text-slate-100">{climateData.soil_moisture_surface_percent}%</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                        <span className="text-[10px] text-slate-500 block">Elevation</span>
                        <span className="text-sm font-bold text-slate-100">{climateData.elevation_meters}m</span>
                      </div>
                    </div>

                    <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-300 flex items-center justify-between font-mono">
                      <span>Suitability Score:</span>
                      <strong className="text-emerald-400">{climateData.sandalwood_suitability_score}%</strong>
                    </div>
                  </div>
                ) : (
                  <p className="text-slate-500 text-center py-4">No climate data available.</p>
                )}
              </div>
            )}

            {activeDrawerTab === 'navigation' && (
              <div className="space-y-2.5">
                {loadingRoute ? (
                  <div className="p-6 text-center text-slate-400 text-xs">
                    <RefreshCw className="w-4 h-4 animate-spin text-emerald-400 mx-auto mb-1.5" />
                    <span>Calculating OSRM road route...</span>
                  </div>
                ) : navRoute ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2 font-mono bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Distance</span>
                        <span className="text-sm font-bold text-slate-100">
                          {formatDistance(navRoute.routeDetails.distanceMeters)}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Drive Time</span>
                        <span className="text-sm font-bold text-emerald-400">
                          ~{navRoute.routeDetails.durationMinutes} mins
                        </span>
                      </div>
                    </div>

                    <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
                      {navRoute.routeDetails.steps.slice(0, 5).map((step, sIdx) => (
                        <div key={sIdx} className="p-2 rounded-lg bg-slate-900/40 border border-slate-800/60 text-[11px] text-slate-300 flex items-start gap-2">
                          <CornerUpRight className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                          <span className="truncate flex-1">{step.instruction}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <button
                      type="button"
                      onClick={() => startNavigation(selectedAsset.lat, selectedAsset.lon, selectedAsset.name)}
                      className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-colors"
                    >
                      Compute Directions
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
