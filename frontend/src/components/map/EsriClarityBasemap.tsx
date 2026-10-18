import React from 'react';
import { TileLayer } from 'react-leaflet';
import {
  ESRI_WORLD_IMAGERY_URL,
  ESRI_IMAGERY_ATTRIBUTION,
  ESRI_IMAGERY_SAFE_MAX_NATIVE_ZOOM,
  ESRI_LABELS_URL,
  TRANSPARENT_TILE_URL,
  TILE_PERF,
} from '../../utils/basemapTiles';

/**
 * Natural Esri World Imagery basemap for Internet Sandalwood.
 *
 * One satellite pyramid only — no Clarity overlay on top. Stacking Clarity
 * (z≤17) over World Imagery caused an artificial colour shift when zooming
 * past Clarity's India cache limit.
 *
 * detectRetina stays off so HiDPI does not request a missing z+1 LOD
 * ("Map data not yet available" placeholder). Past safe native zoom, Leaflet
 * upscales the last real tiles instead of fetching blank Esri cells.
 */
export const EsriClarityBasemap: React.FC<{
  showLabels?: boolean;
  /** Highest zoom the map allows; tiles above native cap are upscaled. */
  maxZoom: number;
}> = ({ showLabels = true, maxZoom }) => (
  <>
    <TileLayer
      url={ESRI_WORLD_IMAGERY_URL}
      attribution={ESRI_IMAGERY_ATTRIBUTION}
      detectRetina={false}
      maxZoom={maxZoom}
      maxNativeZoom={ESRI_IMAGERY_SAFE_MAX_NATIVE_ZOOM}
      errorTileUrl={TRANSPARENT_TILE_URL}
      zIndex={1}
      updateWhenZooming={TILE_PERF.updateWhenZooming}
      updateWhenIdle={TILE_PERF.updateWhenIdle}
      keepBuffer={TILE_PERF.keepBuffer}
      updateInterval={TILE_PERF.updateInterval}
    />

    {showLabels && (
      <TileLayer
        url={ESRI_LABELS_URL}
        attribution=""
        detectRetina={false}
        maxZoom={maxZoom}
        maxNativeZoom={ESRI_IMAGERY_SAFE_MAX_NATIVE_ZOOM}
        errorTileUrl={TRANSPARENT_TILE_URL}
        opacity={1}
        zIndex={2}
        updateWhenZooming={TILE_PERF.updateWhenZooming}
        updateWhenIdle={TILE_PERF.updateWhenIdle}
        keepBuffer={TILE_PERF.keepBuffer}
        updateInterval={TILE_PERF.updateInterval}
      />
    )}
  </>
);
