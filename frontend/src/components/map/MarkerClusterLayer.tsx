import { useEffect, useMemo, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.markercluster';

export type ClusterPoint = {
  id: string;
  lat: number;
  lon: number;
  color: string;
  radius?: number;
  fillColor?: string;
  weight?: number;
  dashArray?: string;
  tooltipHtml?: string;
  onClick?: () => void;
};

type MarkerClusterLayerProps = {
  points: ClusterPoint[];
  /** Stop clustering past this zoom so individual pins stay precise */
  disableClusteringAtZoom?: number;
  /** Fixed radius, or omit to use zoom-adaptive clustering (best for zoom-out speed) */
  maxClusterRadius?: number | ((zoom: number) => number);
  /** Numbered cluster badges — default Leaflet green/yellow/red, or solid blue */
  clusterStyle?: 'default' | 'blue';
  /**
   * Drop markers outside the viewport (much faster zoom with thousands of pins).
   * Safe with the SVG renderer; leave off for canvas maps, where re-adding a
   * culled vector leaves stale hit-testing.
   */
  removeOutsideVisibleBounds?: boolean;
};

type MarkerWithPointId = L.CircleMarker & { __pointId?: string };

function createBlueClusterIcon(cluster: L.MarkerCluster): L.DivIcon {
  const count = cluster.getChildCount();
  const size = count < 10 ? 34 : count < 40 ? 42 : 50;
  return L.divIcon({
    html: `<div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:rgba(14,165,233,0.9);border:2px solid #7dd3fc;
      display:flex;align-items:center;justify-content:center;
      color:#f0f9ff;font:700 12px/1 ui-monospace,monospace;
      box-shadow:0 2px 6px rgba(0,0,0,0.4);
    "><span>${count}</span></div>`,
    className: 'marker-cluster-blue',
    iconSize: L.point(size, size),
    iconAnchor: L.point(size / 2, size / 2),
  });
}

/** Bigger clusters when zoomed out = far fewer DOM draw calls */
function adaptiveClusterRadius(zoom: number): number {
  if (zoom <= 5) return 140;
  if (zoom <= 7) return 110;
  if (zoom <= 9) return 85;
  if (zoom <= 11) return 64;
  if (zoom <= 13) return 48;
  return 36;
}

/**
 * MarkerClusterGroup for specimen / detection dots.
 * SVG CircleMarkers for reliable clicks; optional viewport culling via props.
 */
export function MarkerClusterLayer({
  points,
  disableClusteringAtZoom = 15,
  maxClusterRadius,
  clusterStyle = 'default',
  removeOutsideVisibleBounds = false,
}: MarkerClusterLayerProps) {
  const map = useMap();
  const pointsRef = useRef(points);
  pointsRef.current = points;

  // Geometry/color identity only — ignore unstable onClick closures
  const signature = useMemo(
    () =>
      points
        .map((p) => `${p.id}:${p.lat.toFixed(4)},${p.lon.toFixed(4)},${p.color}`)
        .join('|'),
    [points]
  );

  useEffect(() => {
    const radiusOption = maxClusterRadius ?? adaptiveClusterRadius;
    const current = pointsRef.current;
    const many = current.length > 800;

    const cluster = L.markerClusterGroup({
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      spiderfyOnMaxZoom: true,
      spiderfyDistanceMultiplier: 1.6,
      disableClusteringAtZoom,
      maxClusterRadius: radiusOption,
      chunkedLoading: many,
      chunkInterval: many ? 40 : 200,
      chunkDelay: many ? 8 : 0,
      removeOutsideVisibleBounds,
      animate: false,
      animateAddingMarkers: false,
      ...(clusterStyle === 'blue' ? { iconCreateFunction: createBlueClusterIcon } : {}),
    });

    const markers: MarkerWithPointId[] = [];

    for (const p of current) {
      const marker = L.circleMarker([p.lat, p.lon], {
        radius: p.radius ?? 5,
        color: p.color,
        fillColor: p.fillColor ?? p.color,
        fillOpacity: 0.88,
        weight: p.weight ?? 1.2,
        dashArray: p.dashArray,
        interactive: true,
        bubblingMouseEvents: true,
      }) as MarkerWithPointId;

      marker.__pointId = p.id;

      if (p.tooltipHtml) {
        const html = p.tooltipHtml;
        marker.on('mouseover', function (this: L.CircleMarker) {
          if (!this.getTooltip()) {
            this.bindTooltip(html, {
              direction: 'top',
              offset: L.point(0, -6),
              opacity: 0.95,
              sticky: false,
            }).openTooltip();
          }
        });
      }

      markers.push(marker);
    }

    const firePointClick = (pointId: string | undefined, e?: L.LeafletMouseEvent) => {
      if (!pointId) return;
      if (e?.originalEvent) {
        L.DomEvent.stopPropagation(e.originalEvent);
        L.DomEvent.preventDefault(e.originalEvent);
      }
      const latest = pointsRef.current.find((x) => x.id === pointId);
      latest?.onClick?.();
    };

    cluster.on('click', (e: L.LeafletMouseEvent) => {
      const layer = e.layer as MarkerWithPointId | undefined;
      if (!layer || typeof layer.getLatLng !== 'function') return;
      // Cluster icons carry getChildCount and are handled by the plugin (zoom/spiderfy)
      if (typeof (layer as unknown as L.MarkerCluster).getChildCount === 'function') return;
      firePointClick(layer.__pointId, e);
    });

    cluster.addLayers(markers);
    map.addLayer(cluster);

    return () => {
      cluster.off('click');
      map.removeLayer(cluster);
      cluster.clearLayers();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    map,
    signature,
    disableClusteringAtZoom,
    maxClusterRadius,
    clusterStyle,
    removeOutsideVisibleBounds,
  ]);

  return null;
}
