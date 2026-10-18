/**
 * Shared satellite basemap definitions.
 * Esri World Imagery is the same raster pyramid esri.com satellite demos use.
 * HiDPI sharpness comes from detectRetina / Google scale=2, not from swapping
 * tile hosts on zoomend.
 */

export const ESRI_CLARITY_URL =
  'https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

export const ESRI_WORLD_IMAGERY_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

export const ESRI_LABELS_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}';

/** Google satellite — standard tiles (fast zoom-out / pan) */
export const GOOGLE_SATELLITE_URL =
  'https://{s}.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}';

/** Google hybrid — standard tiles (fast). Prefer this for map interaction. */
export const GOOGLE_HYBRID_URL =
  'https://{s}.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}';

/** Retina HD — only for very close canopy inspection (4× heavier) */
export const GOOGLE_HYBRID_HD_URL =
  'https://{s}.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}&scale=2';

export const GOOGLE_SATELLITE_HD_URL =
  'https://{s}.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&scale=2';

/** OpenStreetMap streets overlay / fallback navigation basemap */
export const OSM_STREETS_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

export const GOOGLE_TILE_SUBDOMAINS = ['mt0', 'mt1', 'mt2', 'mt3'] as const;

/**
 * World Imagery is patchy past this zoom (rural India, Hawaii, etc.).
 * Esri answers missing LODs with a 200 PNG that says "Map data not yet available",
 * so Leaflet will paint that text unless we leave the pyramid before then.
 */
export const ESRI_HD_FALLBACK_ZOOM = 15;
export const OSM_TILE_SUBDOMAINS = ['a', 'b', 'c'] as const;

/**
 * World Imagery / Clarity cached pyramids stop at 19.
 * Zooming the map past this only CSS-scales the last tiles (soft imagery + labels).
 */
export const ESRI_IMAGERY_MAX_NATIVE_ZOOM = 19;

/** Reference/World_Boundaries_and_Places is cached through 19 — not 15. */
export const ESRI_LABELS_MAX_NATIVE_ZOOM = 19;

/**
 * Clarity is a separate, sharper pyramid but it is only cached to 17 over India
 * (z18+ answers 404). Keep it as the detail layer under that cap.
 */
export const ESRI_CLARITY_MAX_NATIVE_ZOOM = 17;

/**
 * World Imagery still has real tiles at 18, but 19+ frequently answers with a
 * 200 PNG reading "Map data not yet available" (a fixed 2,521-byte placeholder).
 * Stop fetching at 18 and let Leaflet upscale so close zoom degrades to soft
 * imagery instead of an error graphic.
 */
export const ESRI_IMAGERY_SAFE_MAX_NATIVE_ZOOM = 18;

/** Transparent 1×1 PNG — blank tile instead of a broken-image icon on 404. */
export const TRANSPARENT_TILE_URL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

/**
 * Leaflet Map constraints. zoomSnap/zoomDelta = 1 is the raster equivalent of
 * ArcGIS view.constraints.snapToZoom: one integer LOD per wheel notch, no
 * fractional zoom that fetches an extra tile level.
 */
export const MAP_CONSTRAINTS = {
  minZoom: 3,
  maxZoom: ESRI_IMAGERY_MAX_NATIVE_ZOOM,
  zoomSnap: 1,
  zoomDelta: 1,
  wheelPxPerZoomLevel: 80,
} as const;

/** True when the screen needs a higher tile LOD (MapView devicePixelRatio >= 1.5). */
export function isHiDpiScreen(): boolean {
  if (typeof window === 'undefined') return false;
  return (window.devicePixelRatio || 1) >= 1.5;
}

/**
 * detectRetina requests z+1 and draws it at half CSS size. Cap native zoom so
 * the URL zoom (mapZoom + 1) never walks past the cached Esri pyramid.
 */
export function nativeZoomForRetina(serviceMaxZoom: number): number {
  return isHiDpiScreen() ? Math.max(0, serviceMaxZoom - 1) : serviceMaxZoom;
}

/**
 * Leaflet's detectRetina path decrements layer maxZoom by 1. Pass one extra
 * so a HiDPI map can still reach the native imagery cap instead of going blank.
 */
export function esriTileLayerMaxZoom(): number {
  return isHiDpiScreen() ? ESRI_IMAGERY_MAX_NATIVE_ZOOM + 1 : ESRI_IMAGERY_MAX_NATIVE_ZOOM;
}

/** Google scale=2 is a 512px tile for the same x/y/z — sharp on HiDPI without a second zoom pyramid. */
export function googleHybridUrl(): string {
  return isHiDpiScreen() ? GOOGLE_HYBRID_HD_URL : GOOGLE_HYBRID_URL;
}

export function googleSatelliteUrl(): string {
  return isHiDpiScreen() ? GOOGLE_SATELLITE_HD_URL : GOOGLE_SATELLITE_URL;
}

/**
 * Shared Leaflet TileLayer props.
 * updateWhenZooming false + updateWhenIdle true was the zoom stutter: Leaflet
 * CSS-scaled the current 256px tiles for the whole gesture, then fired a burst
 * of fetches on zoomend. Load the next LOD during the gesture instead.
 */
export const TILE_PERF = {
  updateWhenZooming: true,
  updateWhenIdle: false,
  keepBuffer: 1,
  updateInterval: 150,
  maxZoom: ESRI_IMAGERY_MAX_NATIVE_ZOOM,
} as const;

export const ESRI_CLARITY_ATTRIBUTION =
  '&copy; Esri World Imagery (Clarity), Maxar, Earthstar Geographics';

export const ESRI_IMAGERY_ATTRIBUTION =
  '&copy; Esri, Maxar, Earthstar Geographics';

export const GOOGLE_SAT_ATTRIBUTION = '&copy; Google Satellite Imagery';
export const GOOGLE_HYBRID_ATTRIBUTION = '&copy; Google Hybrid Satellite';
export const OSM_ATTRIBUTION = '&copy; OpenStreetMap contributors';
