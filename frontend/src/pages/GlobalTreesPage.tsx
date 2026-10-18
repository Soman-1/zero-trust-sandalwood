import React, { useState, useEffect, useMemo, useDeferredValue, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Circle,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { globalTreesApi } from '../api/globalTrees';
import { GlobalTreeEnvironmentSnapshot, GlobalTreeItem, GlobalTreeStatsResponse } from '../types';
import { RegisterInternetTreeModal } from '../components/trees/RegisterInternetTreeModal';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import {
  Globe,
  Database,
  RefreshCw,
  Search,
  Camera,
  ExternalLink,
  ShieldCheck,
  TreePine,
  Compass,
  Thermometer,
  Droplets,
} from 'lucide-react';
import { MapAutoResizer } from '../components/map/SharpEsriImageryLayer';
import { EsriClarityBasemap } from '../components/map/EsriClarityBasemap';
import { MarkerClusterLayer, ClusterPoint } from '../components/map/MarkerClusterLayer';
import { ageLabel, gpsLabel, heartwoodEstimateLabel, survivalLabel } from '../utils/treeAssessment';
import {
  googleHybridUrl,
  googleSatelliteUrl,
  GOOGLE_HYBRID_ATTRIBUTION,
  GOOGLE_SAT_ATTRIBUTION,
  GOOGLE_TILE_SUBDOMAINS,
  ESRI_LABELS_URL,
  ESRI_IMAGERY_SAFE_MAX_NATIVE_ZOOM,
  TRANSPARENT_TILE_URL,
  MAP_CONSTRAINTS,
  TILE_PERF,
} from '../utils/basemapTiles';

const MAP_MAX_ZOOM = 20;
const SPECIMEN_FOCUS_ZOOM = ESRI_IMAGERY_SAFE_MAX_NATIVE_ZOOM;
const CLUSTER_DISABLE_ZOOM = 16;
const SIDEBAR_PAGE_SIZE = 60;
/** ~220 m at equator — match registry tree to nearest internet occurrence */
const REGISTRY_FOCUS_MAX_DEG = 0.002;
/** Survive route unmount when leaving Internet Sandalwood for Dashboard / Registry / etc. */
const MAP_VIEW_STORAGE_KEY = 'internet-sandalwood-map-view';
const DEFAULT_MAP_CENTER: [number, number] = [13.2, 76.8];
const DEFAULT_MAP_ZOOM = 7;

type FocusTarget = { id: string; lat: number; lon: number; nonce: number };

type SavedMapView = {
  lat: number;
  lon: number;
  zoom: number;
  selectedTreeId?: string | null;
  mapType?: 'esri' | 'hybrid' | 'satellite';
  activeTab?: 'split' | 'map' | 'gallery';
};

function loadSavedMapView(): SavedMapView | null {
  try {
    const raw = sessionStorage.getItem(MAP_VIEW_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as SavedMapView;
    if (
      !Number.isFinite(parsed.lat) ||
      !Number.isFinite(parsed.lon) ||
      !Number.isFinite(parsed.zoom)
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function saveMapView(patch: Partial<SavedMapView>): void {
  try {
    const prev = loadSavedMapView();
    const next: SavedMapView = {
      lat: patch.lat ?? prev?.lat ?? DEFAULT_MAP_CENTER[0],
      lon: patch.lon ?? prev?.lon ?? DEFAULT_MAP_CENTER[1],
      zoom: patch.zoom ?? prev?.zoom ?? DEFAULT_MAP_ZOOM,
      selectedTreeId:
        patch.selectedTreeId !== undefined
          ? patch.selectedTreeId
          : prev?.selectedTreeId ?? null,
      mapType: patch.mapType ?? prev?.mapType ?? 'esri',
      activeTab: patch.activeTab ?? prev?.activeTab ?? 'split',
    };
    sessionStorage.setItem(MAP_VIEW_STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* private mode / quota — ignore */
  }
}

/** Persist camera after pan/zoom so leaving the route does not reset the view. */
const MapViewPersistence: React.FC = () => {
  const map = useMap();

  useMapEvents({
    moveend() {
      const c = map.getCenter();
      saveMapView({ lat: c.lat, lon: c.lng, zoom: map.getZoom() });
    },
    zoomend() {
      const c = map.getCenter();
      saveMapView({ lat: c.lat, lon: c.lng, zoom: map.getZoom() });
    },
  });

  return null;
};

function findRegistryFocusMatch(
  trees: GlobalTreeItem[],
  treeUid: string | null,
  lat: number | null,
  lon: number | null,
): GlobalTreeItem | null {
  if (treeUid) {
    const byUid = trees.find(
      (t) => t.registered_tree_uid?.toUpperCase() === treeUid.toUpperCase()
    );
    if (byUid) return byUid;
  }
  if (lat == null || lon == null || !Number.isFinite(lat) || !Number.isFinite(lon)) {
    return null;
  }
  let best: GlobalTreeItem | null = null;
  let bestDist = Number.POSITIVE_INFINITY;
  for (const tree of trees) {
    const dLat = tree.latitude - lat;
    const dLon = tree.longitude - lon;
    const dist = dLat * dLat + dLon * dLon;
    if (dist < bestDist) {
      bestDist = dist;
      best = tree;
    }
  }
  if (best && bestDist <= REGISTRY_FOCUS_MAX_DEG * REGISTRY_FOCUS_MAX_DEG) {
    return best;
  }
  return null;
}

const MapController: React.FC<{ target: FocusTarget | null }> = ({ target }) => {
  const map = useMap();

  useEffect(() => {
    if (!target) return;
    map.stop();
    map.flyTo([target.lat, target.lon], SPECIMEN_FOCUS_ZOOM, {
      animate: true,
      duration: 0.85,
      easeLinearity: 0.25,
    });
  }, [target, map]);

  return null;
};

export const GlobalTreesPage: React.FC = () => {
  const { success, error: toastError, info } = useToast();
  const { canManage } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const appliedFocusKeyRef = useRef<string | null>(null);
  const restoredSelectionRef = useRef(false);
  const selectedTreeIdRef = useRef<string | null>(null);
  const initialViewRef = useRef<SavedMapView | null>(loadSavedMapView());
  const initialView = initialViewRef.current;

  const [trees, setTrees] = useState<GlobalTreeItem[]>([]);
  const [stats, setStats] = useState<GlobalTreeStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const deferredSearch = useDeferredValue(searchQuery);
  const [sourceFilter, setSourceFilter] = useState<'ALL' | 'GBIF' | 'INAT'>('ALL');
  const [stateFilter, setStateFilter] = useState<string>('ALL');
  const [hasPhotoOnly, setHasPhotoOnly] = useState(false);
  const [listVisibleCount, setListVisibleCount] = useState(SIDEBAR_PAGE_SIZE);

  // Selected item
  const [selectedTree, setSelectedTree] = useState<GlobalTreeItem | null>(null);
  const [focusTarget, setFocusTarget] = useState<FocusTarget | null>(null);
  const [environment, setEnvironment] = useState<GlobalTreeEnvironmentSnapshot | null>(null);
  const [envLoading, setEnvLoading] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);

  useEffect(() => {
    selectedTreeIdRef.current = selectedTree?.id ?? null;
  }, [selectedTree?.id]);
  const [activeTab, setActiveTab] = useState<'split' | 'map' | 'gallery'>(
    initialView?.activeTab ?? 'split'
  );
  // World Imagery (Esri.com satellite pyramid). Google only if the user picks it.
  const [mapType, setMapType] = useState<'esri' | 'hybrid' | 'satellite'>(
    initialView?.mapType ?? 'esri'
  );

  const tileLayers = {
    hybrid: {
      url: googleHybridUrl(),
      attribution: GOOGLE_HYBRID_ATTRIBUTION,
      maxZoom: MAP_MAX_ZOOM,
      maxNativeZoom: MAP_MAX_ZOOM,
      labels: false,
    },
    satellite: {
      url: googleSatelliteUrl(),
      attribution: GOOGLE_SAT_ATTRIBUTION,
      maxZoom: MAP_MAX_ZOOM,
      maxNativeZoom: MAP_MAX_ZOOM,
      labels: true,
    },
  } as const;

  // Load Data
  const loadData = async () => {
    try {
      setLoading(true);
      const treesRes = await globalTreesApi.listTrees({ limit: 2000 });
      setTrees(treesRes);
      // Prefer restored selection; do not jump to first tree when returning to this page
      setSelectedTree((curr) => {
        if (curr) return curr;
        const savedId = initialViewRef.current?.selectedTreeId;
        if (savedId) {
          const match = treesRes.find((t) => t.id === savedId);
          if (match) return match;
        }
        return treesRes[0] || null;
      });

      // Derive stats
      const gbif_count = treesRes.filter((t) => t.source.toLowerCase().includes('gbif')).length;
      const inaturalist_count = treesRes.filter((t) =>
        t.source.toLowerCase().includes('inaturalist')
      ).length;
      setStats({
        total_trees: treesRes.length,
        gbif_count,
        inaturalist_count,
        with_photos_count: treesRes.filter((t) => t.image_url).length,
        states_distribution: {},
        registered_assets_count: treesRes.filter((t) => t.is_platform_asset).length,
      });

      // Try fetching server-computed stats if available
      globalTreesApi
        .getStats()
        .then(setStats)
        .catch(() => {
          /* keep derived stats */
        });
    } catch (e: any) {
      console.error('Failed to load global trees:', e);
      toastError(e?.message || 'Failed to load internet sandalwood data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    setListVisibleCount(SIDEBAR_PAGE_SIZE);
  }, [sourceFilter, stateFilter, hasPhotoOnly, deferredSearch, activeTab]);

  // Handle Bulk Import
  const handleImportAll = async () => {
    try {
      setImporting(true);
      info('Synchronizing internet sandalwood occurrences into platform asset registry...');
      const res = await globalTreesApi.importAll();
      if (res.success) {
        success(res.message);
        await loadData();
      }
    } catch (e: any) {
      console.error('Import failed:', e);
      toastError(e?.message || 'Failed to import internet records');
    } finally {
      setImporting(false);
    }
  };

  // Filtered Trees
  const filteredTrees = useMemo(() => {
    return trees.filter((tree) => {
      // Source filter
      if (sourceFilter === 'GBIF' && !tree.source.toLowerCase().includes('gbif')) return false;
      if (sourceFilter === 'INAT' && !tree.source.toLowerCase().includes('inaturalist')) return false;

      // State filter
      if (stateFilter !== 'ALL') {
        const treeState = (tree.state_province || '').toLowerCase();
        if (!treeState.includes(stateFilter.toLowerCase())) return false;
      }

      // Photo filter
      if (hasPhotoOnly && !tree.image_url) return false;

      // Search query (deferred so typing stays responsive)
      if (deferredSearch.trim()) {
        const q = deferredSearch.toLowerCase();
        const matchLoc = (tree.locality || '').toLowerCase().includes(q);
        const matchState = (tree.state_province || '').toLowerCase().includes(q);
        const matchObserver = (tree.recorded_by || '').toLowerCase().includes(q);
        const matchSci = (tree.scientific_name || '').toLowerCase().includes(q);
        const matchSourceId = (tree.source_id || '').toLowerCase().includes(q);
        if (!matchLoc && !matchState && !matchObserver && !matchSci && !matchSourceId) {
          return false;
        }
      }

      return true;
    });
  }, [trees, sourceFilter, stateFilter, hasPhotoOnly, deferredSearch]);

  // Unique states for filter dropdown
  const availableStates = useMemo(() => {
    const states = new Set<string>();
    trees.forEach((t) => {
      if (t.state_province) {
        let clean = t.state_province.split(',')[0].trim();
        if (clean.length > 2 && !clean.includes('Plot')) {
          states.add(clean);
        }
      }
    });
    return Array.from(states).sort();
  }, [trees]);

  const handleSelectTree = useCallback((tree: GlobalTreeItem) => {
    const sameSpecimen = selectedTree?.id === tree.id;
    setSelectedTree(tree);
    saveMapView({
      selectedTreeId: tree.id,
      lat: tree.latitude,
      lon: tree.longitude,
      zoom: SPECIMEN_FOCUS_ZOOM,
    });
    // New nonce every click so re-selecting the same tree still re-focuses after zoom-out
    setFocusTarget({
      id: tree.id,
      lat: tree.latitude,
      lon: tree.longitude,
      nonce: Date.now(),
    });
    // Skip weather refetch when re-clicking the same pin (keeps zoom snappy)
    if (sameSpecimen && environment) return;

    const requestId = tree.id;
    setEnvironment(null);
    setEnvLoading(true);
    globalTreesApi
      .getEnvironment(tree.id)
      .then((env) => {
        if (selectedTreeIdRef.current === requestId) setEnvironment(env);
      })
      .catch(() => {
        if (selectedTreeIdRef.current === requestId) setEnvironment(null);
      })
      .finally(() => {
        if (selectedTreeIdRef.current === requestId) setEnvLoading(false);
      });
  }, [selectedTree?.id, environment]);

  // After data load: restore specimen panel without re-flying (camera already from session)
  useEffect(() => {
    if (loading || trees.length === 0 || restoredSelectionRef.current) return;
    const treeUid = (searchParams.get('tree_uid') || '').trim();
    const hasDeepLink =
      !!treeUid ||
      (searchParams.get('lat') != null && searchParams.get('lon') != null);
    if (hasDeepLink) {
      restoredSelectionRef.current = true;
      return;
    }

    restoredSelectionRef.current = true;
    const savedId = initialViewRef.current?.selectedTreeId;
    if (!savedId) return;
    const match = trees.find((t) => t.id === savedId);
    if (!match) return;

    setSelectedTree(match);
    setEnvLoading(true);
    globalTreesApi
      .getEnvironment(match.id)
      .then(setEnvironment)
      .catch(() => setEnvironment(null))
      .finally(() => setEnvLoading(false));
  }, [loading, trees, searchParams]);

  useEffect(() => {
    saveMapView({ mapType, activeTab });
  }, [mapType, activeTab]);

  // Deep-link from Tree Registry map-pin → focus that specimen here
  useEffect(() => {
    if (loading || trees.length === 0) return;

    const treeUid = (searchParams.get('tree_uid') || '').trim() || null;
    const latRaw = searchParams.get('lat');
    const lonRaw = searchParams.get('lon');
    const lat = latRaw != null && latRaw !== '' ? Number(latRaw) : null;
    const lon = lonRaw != null && lonRaw !== '' ? Number(lonRaw) : null;
    const hasLatLon = lat != null && lon != null && Number.isFinite(lat) && Number.isFinite(lon);

    if (!treeUid && !hasLatLon) {
      appliedFocusKeyRef.current = null;
      return;
    }

    const focusKey = `${treeUid || ''}|${hasLatLon ? lat : ''}|${hasLatLon ? lon : ''}`;
    if (appliedFocusKeyRef.current === focusKey) return;
    appliedFocusKeyRef.current = focusKey;

    // Clear query first so re-renders don't re-apply while selecting
    setSearchParams({}, { replace: true });

    const match = findRegistryFocusMatch(
      trees,
      treeUid,
      hasLatLon ? lat : null,
      hasLatLon ? lon : null,
    );

    setActiveTab('map');
    setSourceFilter('ALL');
    setStateFilter('ALL');
    setHasPhotoOnly(false);
    setSearchQuery('');

    if (match) {
      handleSelectTree(match);
    } else if (hasLatLon) {
      setSelectedTree(null);
      setEnvironment(null);
      setFocusTarget({
        id: treeUid || `registry-${lat},${lon}`,
        lat: lat as number,
        lon: lon as number,
        nonce: Date.now(),
      });
      info(
        treeUid
          ? `Showing registered location for ${treeUid} (no matching internet occurrence nearby).`
          : 'Showing registered tree coordinates on Internet Sandalwood map.'
      );
    }
  }, [loading, trees, searchParams, handleSelectTree, setSearchParams, info]);

  const handleRegistered = useCallback(
    (treeUid: string, storedEnv: GlobalTreeEnvironmentSnapshot | null) => {
      setTrees((prev) =>
        prev.map((t) =>
          t.id === selectedTree?.id
            ? { ...t, is_registered: true, is_platform_asset: true, registered_tree_uid: treeUid }
            : t
        )
      );
      setSelectedTree((prev) =>
        prev
          ? { ...prev, is_registered: true, is_platform_asset: true, registered_tree_uid: treeUid }
          : prev
      );
      if (storedEnv) setEnvironment({ ...storedEnv, stored: true });
      if (!selectedTree?.is_platform_asset) {
        setStats((prev) =>
          prev
            ? { ...prev, registered_assets_count: prev.registered_assets_count + 1 }
            : prev
        );
      }
    },
    [selectedTree?.id]
  );

  // Green ONLY when annotated as a Tree Registry asset (is_platform_asset from DB Tree match).
  // Detections (DET-*) and pure GBIF/iNat occurrences stay non-green (sky blue).
  const globalClusterPoints: ClusterPoint[] = useMemo(() => {
    return filteredTrees.map((tree) => {
      const registeredInDb = tree.is_platform_asset === true;
      return {
        id: `gt-${tree.id}`,
        lat: tree.latitude,
        lon: tree.longitude,
        color: registeredInDb ? '#34d399' : '#38bdf8',
        fillColor: registeredInDb ? '#059669' : '#0ea5e9',
        radius: tree.image_url ? 6 : 5,
        weight: 1.4,
        tooltipHtml: `<div style="font-size:11px"><strong><em>${tree.scientific_name}</em></strong><br/>${tree.source} · ${tree.locality || tree.state_province || 'India'}${tree.gps_accuracy != null ? `<br/>±${Math.round(tree.gps_accuracy)} m` : ''}${registeredInDb ? `<br/>Registered Tree ID: ${tree.registered_tree_uid}` : '<br/>Not in Tree Registry'}</div>`,
        onClick: () => handleSelectTree(tree),
      };
    });
  }, [filteredTrees, handleSelectTree]);

  const visibleListTrees = useMemo(
    () =>
      activeTab === 'gallery'
        ? filteredTrees.filter((t) => t.image_url).slice(0, listVisibleCount)
        : filteredTrees.slice(0, listVisibleCount),
    [filteredTrees, listVisibleCount, activeTab]
  );

  // Mount the map immediately so Esri tiles start fetching in parallel with the
  // occurrence API. Blocking on list data was the slow first paint.

  return (
    <div className="space-y-6 font-sans">
      {/* Top Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-slate-800/80 bg-slate-900/60 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="p-3.5 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 border border-emerald-500/30 text-emerald-400 shadow-glow-emerald">
            <Globe className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl font-bold text-slate-100 tracking-tight">
                Internet Sandalwood Locations
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                {trees.length} Verified Coordinates
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Verified <em>Santalum album</em> (Indian Sandalwood) occurrences harvested from the Global Biodiversity Information Facility (GBIF) and iNaturalist research-grade network.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={loadData}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700/60"
            title="Refresh Internet Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {canManage && (
            <button
              type="button"
              onClick={handleImportAll}
              disabled={importing}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 transition-all shadow-glow-emerald flex items-center gap-2 font-mono font-bold disabled:opacity-50"
            >
              <Database className={`w-4 h-4 ${importing ? 'animate-spin' : ''}`} />
              <span>{importing ? 'Importing...' : 'Sync & Re-Import to Registry'}</span>
            </button>
          )}
        </div>
      </div>

      {/* KPI Stats Grid */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
          <div className="glass-card p-4 rounded-2xl border border-slate-800/80 bg-slate-900/40">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Total Locations</span>
              <Globe className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{stats.total_trees}</p>
            <span className="text-[10px] text-emerald-400 font-mono">Deduplicated Points</span>
          </div>

          <div className="glass-card p-4 rounded-2xl border border-slate-800/80 bg-slate-900/40">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>GBIF Herbaria</span>
              <Database className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{stats.gbif_count}</p>
            <span className="text-[10px] text-slate-400 font-mono">Museum &amp; Research Sets</span>
          </div>

          <div className="glass-card p-4 rounded-2xl border border-slate-800/80 bg-slate-900/40">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>iNaturalist</span>
              <Compass className="w-4 h-4 text-cyan-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{stats.inaturalist_count}</p>
            <span className="text-[10px] text-cyan-400 font-mono">Field Observations</span>
          </div>

          <div className="glass-card p-4 rounded-2xl border border-slate-800/80 bg-slate-900/40">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Ground Photos</span>
              <Camera className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{stats.with_photos_count}</p>
            <span className="text-[10px] text-amber-400 font-mono">Specimens with Imagery</span>
          </div>

          <div className="glass-card p-4 rounded-2xl border border-slate-800/80 bg-slate-900/40 col-span-2 sm:col-span-1">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Platform Assets</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-emerald-400">{stats.registered_assets_count}</p>
            <span className="text-[10px] text-emerald-400/80 font-mono">Tracked in Zero Trust DB</span>
          </div>
        </div>
      )}

      {/* Filter & View Switcher Bar */}
      <div className="glass-panel p-4 rounded-2xl border border-slate-800/80 bg-slate-900/50 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5 flex-1">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search locality, observer, or state..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
            />
          </div>

          {/* Source Filter */}
          <div className="flex items-center rounded-xl bg-slate-950/60 border border-slate-800 p-1 text-xs">
            <button
              type="button"
              onClick={() => setSourceFilter('ALL')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                sourceFilter === 'ALL'
                  ? 'bg-slate-800 text-slate-100'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Sources
            </button>
            <button
              type="button"
              onClick={() => setSourceFilter('GBIF')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                sourceFilter === 'GBIF'
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              GBIF
            </button>
            <button
              type="button"
              onClick={() => setSourceFilter('INAT')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                sourceFilter === 'INAT'
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              iNaturalist
            </button>
          </div>

          {/* State Filter */}
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-emerald-500/50"
          >
            <option value="ALL">All States / Regions</option>
            {availableStates.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>

          {/* Photos Only Toggle */}
          <button
            type="button"
            onClick={() => setHasPhotoOnly(!hasPhotoOnly)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs border transition-all ${
              hasPhotoOnly
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-300 font-semibold'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Photos Only</span>
          </button>
        </div>

        {/* View Switcher */}
        <div className="flex items-center rounded-xl bg-slate-950/60 border border-slate-800 p-1 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('split')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'split' ? 'bg-slate-800 text-slate-100 font-bold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Split View
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('map')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'map' ? 'bg-slate-800 text-slate-100 font-bold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Full Map
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('gallery')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'gallery' ? 'bg-slate-800 text-slate-100 font-bold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Photo Gallery
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Map Container */}
        <div
          className={`${
            activeTab === 'map'
              ? 'lg:col-span-12 h-[750px]'
              : activeTab === 'gallery'
              ? 'hidden'
              : 'lg:col-span-7 xl:col-span-8 h-[650px]'
          } rounded-3xl overflow-hidden border border-slate-800/80 relative shadow-2xl transition-all`}
        >
          {/* Basemap switcher — Esri World Imagery / Google */}
          <div className="absolute top-3 right-3 z-[1000] flex gap-1 p-1 rounded-xl bg-slate-950/85 border border-slate-700/80 backdrop-blur-md shadow-lg">
            {([
              { id: 'esri' as const, label: 'Esri Imagery' },
              { id: 'hybrid' as const, label: 'Hybrid' },
              { id: 'satellite' as const, label: 'Satellite' },
            ]).map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setMapType(opt.id)}
                className={`px-2.5 py-1.5 rounded-lg text-[10px] font-mono font-bold uppercase tracking-wide transition-colors ${
                  mapType === opt.id
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <MapContainer
            center={
              initialView
                ? [initialView.lat, initialView.lon]
                : DEFAULT_MAP_CENTER
            }
            zoom={initialView?.zoom ?? DEFAULT_MAP_ZOOM}
            minZoom={MAP_CONSTRAINTS.minZoom}
            maxZoom={MAP_MAX_ZOOM}
            zoomSnap={MAP_CONSTRAINTS.zoomSnap}
            zoomDelta={MAP_CONSTRAINTS.zoomDelta}
            wheelPxPerZoomLevel={MAP_CONSTRAINTS.wheelPxPerZoomLevel}
            scrollWheelZoom={true}
            preferCanvas={false}
            zoomAnimation={true}
            fadeAnimation={false}
            markerZoomAnimation={false}
            style={{ height: '100%', width: '100%', background: '#0a1210' }}
          >
            {mapType === 'esri' ? (
              <EsriClarityBasemap showLabels maxZoom={MAP_MAX_ZOOM} />
            ) : (
              <>
                <TileLayer
                  key={mapType}
                  attribution={tileLayers[mapType].attribution}
                  url={tileLayers[mapType].url}
                  maxZoom={tileLayers[mapType].maxZoom}
                  maxNativeZoom={tileLayers[mapType].maxNativeZoom}
                  subdomains={[...GOOGLE_TILE_SUBDOMAINS]}
                  detectRetina={false}
                  errorTileUrl={TRANSPARENT_TILE_URL}
                  updateWhenZooming={TILE_PERF.updateWhenZooming}
                  updateWhenIdle={TILE_PERF.updateWhenIdle}
                  keepBuffer={TILE_PERF.keepBuffer}
                  updateInterval={TILE_PERF.updateInterval}
                />
                {tileLayers[mapType].labels && (
                  <TileLayer
                    key={`${mapType}-labels`}
                    url={ESRI_LABELS_URL}
                    detectRetina={false}
                    maxZoom={MAP_MAX_ZOOM}
                    maxNativeZoom={ESRI_IMAGERY_SAFE_MAX_NATIVE_ZOOM}
                    errorTileUrl={TRANSPARENT_TILE_URL}
                    opacity={1}
                    attribution=""
                    updateWhenZooming={TILE_PERF.updateWhenZooming}
                    updateWhenIdle={TILE_PERF.updateWhenIdle}
                    keepBuffer={TILE_PERF.keepBuffer}
                    updateInterval={TILE_PERF.updateInterval}
                  />
                )}
              </>
            )}
            <MapAutoResizer deps={[activeTab, mapType]} />
            <MapViewPersistence />
            <MapController target={focusTarget} />
            <MarkerClusterLayer
              points={globalClusterPoints}
              disableClusteringAtZoom={CLUSTER_DISABLE_ZOOM}
              clusterStyle="blue"
              removeOutsideVisibleBounds
            />
            {selectedTree && (
              <>
                {selectedTree.gps_accuracy != null && selectedTree.gps_accuracy > 0 && selectedTree.gps_accuracy <= 2000 && (
                  <Circle
                    center={[selectedTree.latitude, selectedTree.longitude]}
                    radius={selectedTree.gps_accuracy}
                    interactive={false}
                    pathOptions={{
                      color: '#fbbf24',
                      weight: 1,
                      dashArray: '4 4',
                      fill: false,
                      interactive: false,
                    }}
                  />
                )}
                {/* Same footprint as the specimen dot — thin white outline only, no size bump */}
                <CircleMarker
                  center={[selectedTree.latitude, selectedTree.longitude]}
                  radius={selectedTree.image_url ? 6 : 5}
                  interactive={false}
                  pathOptions={{
                    color: '#f8fafc',
                    weight: 2,
                    fill: false,
                    fillOpacity: 0,
                    opacity: 1,
                    interactive: false,
                  }}
                >
                  <Tooltip direction="top" offset={[0, -8]} permanent={false}>
                    <span className="text-[11px] font-semibold">
                      Selected · {selectedTree.latitude.toFixed(6)}, {selectedTree.longitude.toFixed(6)}
                    </span>
                  </Tooltip>
                </CircleMarker>
              </>
            )}
          </MapContainer>

          {selectedTree && activeTab === 'map' && (
            <div className="absolute bottom-4 left-4 z-[1000] w-[min(100%-2rem,360px)] p-3.5 rounded-2xl bg-slate-950/90 border border-emerald-500/40 backdrop-blur-md space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] font-mono uppercase text-emerald-400 font-bold">Selected tree</span>
                {selectedTree.is_platform_asset && (
                  <span className="text-[10px] font-mono text-emerald-300">{selectedTree.registered_tree_uid}</span>
                )}
                {selectedTree.is_registered && !selectedTree.is_platform_asset && (
                  <span className="text-[10px] font-mono text-amber-300">{selectedTree.registered_tree_uid}</span>
                )}
              </div>
              <p className="text-xs text-slate-200 truncate">
                {selectedTree.latitude.toFixed(6)}, {selectedTree.longitude.toFixed(6)}
              </p>
              {environment && (
                <p className="text-[11px] font-mono text-slate-400">
                  {environment.temperature_celsius.toFixed(1)}°C · {environment.relative_humidity_percent.toFixed(0)}% RH · soil {environment.soil_moisture_root_percent.toFixed(0)}%
                </p>
              )}
              <p className="text-[11px] font-mono text-slate-300">
                {survivalLabel(selectedTree.event_date)}
              </p>
              <p className="text-[11px] font-mono text-slate-400">
                {gpsLabel(selectedTree.gps_accuracy)} · Hosts unknown
              </p>
              {environment?.heartwood && (
                <p className="text-[11px] font-mono text-amber-300/90">
                  Heartwood {heartwoodEstimateLabel(environment.heartwood.estimated_heartwood_kg)} · age {ageLabel(null, environment.heartwood.estimated_age_years)}
                </p>
              )}
              {canManage && !selectedTree.is_platform_asset && (
                <button
                  type="button"
                  onClick={() => setRegisterOpen(true)}
                  className="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-semibold"
                >
                  Register with coordinates &amp; environment
                </button>
              )}
            </div>
          )}

          {/* Map Overlay Badge */}
          <div className="absolute top-4 left-4 z-[1000] px-3.5 py-2 rounded-2xl bg-slate-950/80 border border-slate-800/90 backdrop-blur-md text-xs font-mono flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-slate-300">Displaying {filteredTrees.length} GPS Coordinates</span>
            </div>
            <div className="flex items-center gap-3 text-[10px] text-slate-400">
              <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Tree Registry
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-sky-400"></span> Internet only
              </span>
            </div>
          </div>
        </div>

        {/* Specimen List / Detail Sidebar */}
        <div
          className={`${
            activeTab === 'map'
              ? 'hidden'
              : activeTab === 'gallery'
              ? 'lg:col-span-12'
              : 'lg:col-span-5 xl:col-span-4'
          } space-y-4`}
        >
          {/* Selected Tree Highlight Card */}
          {selectedTree && activeTab !== 'map' && (
            <div className="glass-panel p-4 rounded-2xl border border-emerald-500/40 bg-emerald-950/20 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold">
                  Selected Specimen
                </span>
                {selectedTree.is_platform_asset && (
                  <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Tree {selectedTree.registered_tree_uid}</span>
                  </span>
                )}
                {selectedTree.is_registered && !selectedTree.is_platform_asset && (
                  <span className="text-[10px] font-mono text-amber-400 flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>{selectedTree.registered_tree_uid}</span>
                  </span>
                )}
              </div>

              {selectedTree.image_url && (
                <div className="relative h-44 rounded-xl overflow-hidden border border-emerald-500/30">
                  <img
                    src={selectedTree.image_url}
                    alt={selectedTree.scientific_name}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}

              <div>
                <h3 className="font-bold text-sm text-slate-100">
                  <em>{selectedTree.scientific_name}</em>
                </h3>
                <p className="text-xs text-slate-400">{selectedTree.locality || selectedTree.state_province}</p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                  <span className="text-slate-500 block text-[9px]">LATITUDE</span>
                  <span className="text-slate-200 font-bold">{selectedTree.latitude.toFixed(7)}°N</span>
                </div>
                <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                  <span className="text-slate-500 block text-[9px]">LONGITUDE</span>
                  <span className="text-slate-200 font-bold">{selectedTree.longitude.toFixed(7)}°E</span>
                </div>
                <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800 col-span-2">
                  <span className="text-slate-500 block text-[9px]">GPS UNCERTAINTY</span>
                  <span className="text-amber-300 font-bold">{gpsLabel(selectedTree.gps_accuracy)}</span>
                </div>
                <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800 col-span-2">
                  <span className="text-slate-500 block text-[9px]">SURVIVAL</span>
                  <span className="text-slate-200 font-bold">{survivalLabel(selectedTree.event_date)}</span>
                </div>
                <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800 col-span-2">
                  <span className="text-slate-500 block text-[9px]">HOST TREES</span>
                  <span className="text-slate-200 font-bold">Hosts unknown</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-emerald-400 font-mono font-bold">ENVIRONMENT</span>
                  {envLoading && (
                    <span className="text-[10px] font-mono text-slate-500">Loading live data…</span>
                  )}
                </div>
                {environment ? (
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-500 block text-[9px] flex items-center gap-1">
                        <Thermometer className="w-3 h-3" /> TEMP
                      </span>
                      <span className="text-slate-200 font-bold">
                        {environment.temperature_celsius.toFixed(1)}°C
                      </span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-500 block text-[9px] flex items-center gap-1">
                        <Droplets className="w-3 h-3" /> HUMIDITY
                      </span>
                      <span className="text-slate-200 font-bold">
                        {environment.relative_humidity_percent.toFixed(1)}%
                      </span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-500 block text-[9px]">SOIL MOISTURE</span>
                      <span className="text-slate-200 font-bold">
                        {environment.soil_moisture_root_percent.toFixed(1)}%
                      </span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-500 block text-[9px]">SUITABILITY</span>
                      <span className="text-emerald-300 font-bold">
                        {environment.sandalwood_suitability_score ?? '—'}%
                      </span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800 col-span-2">
                      <span className="text-slate-500 block text-[9px]">ZONE / SOURCE</span>
                      <span className="text-slate-300">
                        {environment.growth_zone_classification || '—'}
                        {environment.canopy_stress_status
                          ? ` · ${environment.canopy_stress_status}`
                          : ''}
                      </span>
                      {environment.data_source && (
                        <span className="text-slate-500 block truncate">{environment.data_source}</span>
                      )}
                    </div>
                  </div>
                ) : (
                  !envLoading && (
                    <p className="text-[11px] text-slate-500">
                      Environmental data unavailable for this coordinate.
                    </p>
                  )
                )}
              </div>

              {environment?.heartwood && (
                <div className="space-y-2">
                  <span className="text-[10px] text-amber-400 font-mono font-bold">HEARTWOOD (ESTIMATE)</span>
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-amber-500/20">
                      <span className="text-slate-500 block text-[9px]">HEARTWOOD MASS</span>
                      <span className="text-amber-300 font-bold">
                        {heartwoodEstimateLabel(environment.heartwood.estimated_heartwood_kg)}
                      </span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-amber-500/20">
                      <span className="text-slate-500 block text-[9px]">AGE</span>
                      <span className="text-slate-200 font-bold">
                        {ageLabel(null, environment.heartwood.estimated_age_years)}
                      </span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-amber-500/20">
                      <span className="text-slate-500 block text-[9px]">ASSUMED GIRTH</span>
                      <span className="text-slate-200 font-bold">
                        {environment.heartwood.assumed_girth_cm.toFixed(1)} cm
                      </span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-amber-500/20">
                      <span className="text-slate-500 block text-[9px]">CORE RATIO</span>
                      <span className="text-slate-200 font-bold">
                        {(environment.heartwood.heartwood_ratio * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-900/80 border border-amber-500/20 col-span-2">
                      <span className="text-slate-500 block text-[9px]">GRADE</span>
                      <span className="text-amber-200/90">{environment.heartwood.sandalwood_grade}</span>
                      <span className="text-slate-500 block text-[9px] mt-1 leading-relaxed">
                        {environment.heartwood.assumption_note}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {canManage && !selectedTree.is_platform_asset && (
                <button
                  type="button"
                  onClick={() => setRegisterOpen(true)}
                  className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-semibold transition-colors"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Register this tree with coordinates &amp; environment
                </button>
              )}

              {selectedTree.bark_characteristics && (
                <div className="text-[11px] text-slate-300 p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-emerald-400 font-mono block mb-0.5 font-bold">
                    BARK PROFILE:
                  </span>
                  <p>{selectedTree.bark_characteristics}</p>
                </div>
              )}

              {selectedTree.external_url && (
                <a
                  href={selectedTree.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-emerald-400 font-semibold transition-colors"
                >
                  <span>Open Primary Source Record</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          )}

          {/* List of Specimens / Photo Gallery Grid */}
          <div
            className={
              activeTab === 'gallery'
                ? 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4'
                : 'space-y-2.5 max-h-[600px] overflow-y-auto pr-1 scrollbar-thin'
            }
          >
            {visibleListTrees.map((tree) => {
              const isSelected = selectedTree?.id === tree.id;

              if (activeTab === 'gallery') {
                return (
                  <div
                    key={tree.id}
                    onClick={() => handleSelectTree(tree)}
                    className={`glass-card rounded-2xl overflow-hidden border transition-all cursor-pointer group ${
                      isSelected
                        ? 'border-emerald-500 shadow-glow-emerald bg-slate-900'
                        : 'border-slate-800 hover:border-slate-700 bg-slate-900/60'
                    }`}
                  >
                    <div className="relative h-48 bg-slate-950 overflow-hidden">
                      {tree.image_url ? (
                        <img
                          src={tree.image_url}
                          alt={tree.scientific_name}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          loading="lazy"
                          decoding="async"
                        />
                      ) : (
                        <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 gap-2">
                          <TreePine className="w-8 h-8" />
                          <span className="text-[10px] font-mono">Herbarium Record</span>
                        </div>
                      )}
                      <span className="absolute top-2 left-2 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-slate-950/80 text-emerald-400 border border-emerald-500/20">
                        {tree.source.includes('GBIF') ? 'GBIF' : 'iNaturalist'}
                      </span>
                    </div>

                    <div className="p-3.5 space-y-1.5">
                      <h4 className="font-bold text-xs text-slate-200 truncate">
                        <em>{tree.scientific_name}</em>
                      </h4>
                      <p className="text-[11px] text-slate-400 truncate">
                        {tree.locality || tree.state_province}
                      </p>
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-800/80">
                        <span>
                          {tree.latitude.toFixed(5)}°N, {tree.longitude.toFixed(5)}°E
                        </span>
                        {tree.is_platform_asset && (
                          <span className="text-emerald-400 flex items-center gap-1 font-bold">
                            <ShieldCheck className="w-3 h-3" />
                            <span>Tree ID</span>
                          </span>
                        )}
                        {tree.is_registered && !tree.is_platform_asset && (
                          <span className="text-amber-400 flex items-center gap-1 font-bold">
                            <ShieldCheck className="w-3 h-3" />
                            <span>Detection</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              }

              // Split view compact card
              return (
                <div
                  key={tree.id}
                  onClick={() => handleSelectTree(tree)}
                  className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-center gap-3 ${
                    isSelected
                      ? 'bg-emerald-500/10 border-emerald-500/50 shadow-glow-emerald'
                      : 'bg-slate-900/40 border-slate-800/80 hover:bg-slate-850 hover:border-slate-700'
                  }`}
                >
                  {tree.image_url ? (
                    <img
                      src={tree.image_url}
                      alt={tree.scientific_name}
                      className="w-14 h-14 rounded-xl object-cover border border-slate-800 flex-shrink-0"
                      loading="lazy"
                      decoding="async"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 flex-shrink-0">
                      <TreePine className="w-6 h-6" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                          tree.source.includes('GBIF')
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : 'bg-cyan-500/15 text-cyan-400'
                        }`}
                      >
                        {tree.source.includes('GBIF') ? 'GBIF' : 'iNat'}
                      </span>
                      <span className="text-xs font-semibold text-slate-200 truncate">
                        <em>{tree.scientific_name}</em>
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 truncate mt-0.5">
                      {tree.locality || tree.state_province}
                    </p>
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 mt-1">
                      <span>
                        {tree.latitude.toFixed(5)}°N, {tree.longitude.toFixed(5)}°E
                        {tree.gps_accuracy != null ? ` · ±${Math.round(tree.gps_accuracy)}m` : ''}
                      </span>
                      {tree.is_platform_asset && (
                        <span className="text-emerald-400 font-bold">Tree ID</span>
                      )}
                      {tree.is_registered && !tree.is_platform_asset && (
                        <span className="text-amber-400 font-bold">Detection</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          {listVisibleCount <
            (activeTab === 'gallery'
              ? filteredTrees.filter((t) => t.image_url).length
              : filteredTrees.length) && (
            <button
              type="button"
              onClick={() => setListVisibleCount((n) => n + SIDEBAR_PAGE_SIZE)}
              className="w-full py-2.5 rounded-xl text-xs font-semibold bg-slate-900/80 border border-slate-800 text-slate-300 hover:text-emerald-300 hover:border-emerald-500/40 transition-colors"
            >
              Show more ({Math.min(
                SIDEBAR_PAGE_SIZE,
                (activeTab === 'gallery'
                  ? filteredTrees.filter((t) => t.image_url).length
                  : filteredTrees.length) - listVisibleCount
              )} more)
            </button>
          )}
        </div>
      </div>

      <RegisterInternetTreeModal
        isOpen={registerOpen}
        onClose={() => setRegisterOpen(false)}
        tree={selectedTree}
        environment={environment}
        onRegistered={handleRegistered}
      />
    </div>
  );
};
