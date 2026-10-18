import React, { useEffect, useRef, useState } from 'react';
import { TileLayer, useMap, useMapEvents } from 'react-leaflet';
import {
  ESRI_WORLD_IMAGERY_URL,
  ESRI_LABELS_URL,
  ESRI_IMAGERY_ATTRIBUTION,
  ESRI_IMAGERY_MAX_NATIVE_ZOOM,
  ESRI_LABELS_MAX_NATIVE_ZOOM,
  ESRI_HD_FALLBACK_ZOOM,
  GOOGLE_HYBRID_ATTRIBUTION,
  GOOGLE_TILE_SUBDOMAINS,
  googleHybridUrl,
  isHiDpiScreen,
  nativeZoomForRetina,
  esriTileLayerMaxZoom,
  TILE_PERF,
} from '../../utils/basemapTiles';

/**
 * Single Esri World Imagery pyramid (same raster esri.com satellite demos use)
 * plus a reference label overlay.
 *
 * There is no ArcGIS MapView here — Leaflet TileLayer defaults detectRetina
 * to false, so 256px tiles were stretched to device pixels. detectRetina is
 * the raster equivalent of MapView.devicePixelRatio.
 *
 * Past ESRI_HD_FALLBACK_ZOOM, World Imagery often has no LOD for a cell and
 * Esri returns a 200 tile reading "Map data not yet available". Switch to
 * Google once, and unmount Esri so the missing pyramid is not fetched.
 */
export const SharpEsriImageryLayer: React.FC<{
  showLabels?: boolean;
  hdFallbackZoom?: number;
  /** When false, never swap Esri→Google (avoids mid-zoom basemap thrash on Internet Sandalwood). */
  enableHdFallback?: boolean;
}> = ({ showLabels = true, hdFallbackZoom = ESRI_HD_FALLBACK_ZOOM, enableHdFallback = true }) => {
  const map = useMap();
  const hiDpi = isHiDpiScreen();
  const layerMaxZoom = esriTileLayerMaxZoom();
  // detectRetina requests z+1, which is exactly the LOD Esri leaves blank.
  // Switch one zoom earlier on HiDPI so that request never goes out.
  const googleAtZoom = hiDpi ? Math.max(1, hdFallbackZoom - 1) : hdFallbackZoom;
  const [useGoogle, setUseGoogle] = useState(
    () => enableHdFallback && map.getZoom() >= googleAtZoom
  );
  const useGoogleRef = useRef(useGoogle);
  useGoogleRef.current = useGoogle;

  useMapEvents({
    // One switch when the integer zoom crosses the gap — not every animation frame.
    zoom() {
      if (!enableHdFallback) return;
      const next = map.getZoom() >= googleAtZoom;
      if (next !== useGoogleRef.current) {
        useGoogleRef.current = next;
        setUseGoogle(next);
      }
    },
  });

  useEffect(() => {
    if (!enableHdFallback) {
      useGoogleRef.current = false;
      setUseGoogle(false);
      return;
    }
    const next = map.getZoom() >= googleAtZoom;
    useGoogleRef.current = next;
    setUseGoogle(next);
  }, [map, googleAtZoom, enableHdFallback]);

  if (enableHdFallback && useGoogle) {
    return (
      <TileLayer
        key="google-close"
        url={googleHybridUrl()}
        attribution={`${ESRI_IMAGERY_ATTRIBUTION} · ${GOOGLE_HYBRID_ATTRIBUTION}`}
        maxZoom={21}
        maxNativeZoom={21}
        subdomains={[...GOOGLE_TILE_SUBDOMAINS]}
        zIndex={1}
        updateWhenZooming={TILE_PERF.updateWhenZooming}
        updateWhenIdle={TILE_PERF.updateWhenIdle}
        keepBuffer={TILE_PERF.keepBuffer}
        updateInterval={TILE_PERF.updateInterval}
      />
    );
  }

  return (
    <>
      <TileLayer
        url={ESRI_WORLD_IMAGERY_URL}
        attribution={ESRI_IMAGERY_ATTRIBUTION}
        detectRetina={hiDpi}
        maxZoom={layerMaxZoom}
        maxNativeZoom={nativeZoomForRetina(ESRI_IMAGERY_MAX_NATIVE_ZOOM)}
        zIndex={1}
        updateWhenZooming={TILE_PERF.updateWhenZooming}
        updateWhenIdle={TILE_PERF.updateWhenIdle}
        keepBuffer={TILE_PERF.keepBuffer}
        updateInterval={TILE_PERF.updateInterval}
      />
      {showLabels && (
        <TileLayer
          url={ESRI_LABELS_URL}
          detectRetina={hiDpi}
          maxZoom={layerMaxZoom}
          maxNativeZoom={nativeZoomForRetina(ESRI_LABELS_MAX_NATIVE_ZOOM)}
          opacity={1}
          zIndex={2}
          attribution=""
          updateWhenZooming={TILE_PERF.updateWhenZooming}
          updateWhenIdle={TILE_PERF.updateWhenIdle}
          keepBuffer={TILE_PERF.keepBuffer}
          updateInterval={TILE_PERF.updateInterval}
        />
      )}
    </>
  );
};

/** Keep Leaflet tiles painted after flex layout, tab, and fullscreen changes. */
export const MapAutoResizer: React.FC<{ deps?: unknown[] }> = ({ deps = [] }) => {
  const map = useMap();
  useEffect(() => {
    // ResizeObserver can fire every frame during flex settle and invalidateSize
    // dumps the tile grid — debounce so a layout pass is one refetch, not a storm.
    let timer = 0;
    const redraw = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => map.invalidateSize({ animate: false }), 120);
    };
    redraw();

    const container = map.getContainer();
    const observer =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => redraw())
        : null;
    observer?.observe(container);
    window.addEventListener('resize', redraw);

    return () => {
      window.clearTimeout(timer);
      observer?.disconnect();
      window.removeEventListener('resize', redraw);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, ...deps]);
  return null;
};

/**
 * Writes cursor lat/lon into an external HUD node.
 * Must render inside MapContainer (useMap). The visible label stays outside
 * so it is not clipped by Leaflet's overflow.
 */
export const CursorCoordsBinder: React.FC<{
  labelRef: React.RefObject<HTMLSpanElement | null>;
}> = ({ labelRef }) => {
  const map = useMap();

  useMapEvents({
    mousemove(e) {
      const el = labelRef.current;
      if (!el) return;
      el.textContent = `${e.latlng.lat.toFixed(5)}°N, ${e.latlng.lng.toFixed(5)}°E · z${map.getZoom().toFixed(0)}`;
    },
  });

  return null;
};
