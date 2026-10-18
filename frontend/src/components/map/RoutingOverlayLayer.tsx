import React from 'react';
import { Polyline } from 'react-leaflet';
import { DetailedRouteResponse } from '../../utils/geoUtils';

interface RoutingOverlayLayerProps {
  navRoute: {
    targetName: string;
    targetCoords: [number, number];
    routeDetails: DetailedRouteResponse;
    bearing: number;
  } | null;
}

export const RoutingOverlayLayer: React.FC<RoutingOverlayLayerProps> = ({ navRoute }) => {
  if (!navRoute || !navRoute.routeDetails?.geometry?.length) return null;

  return (
    <Polyline
      positions={navRoute.routeDetails.geometry}
      pathOptions={{ color: '#10b981', weight: 4, opacity: 0.9 }}
    />
  );
};
