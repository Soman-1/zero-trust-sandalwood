import React from 'react';
import { Polyline, CircleMarker } from 'react-leaflet';

interface MapMeasurementToolProps {
  points: [number, number][];
}

export const MapMeasurementTool: React.FC<MapMeasurementToolProps> = ({ points }) => {
  if (points.length === 0) return null;

  return (
    <>
      {points.length > 1 && (
        <Polyline
          positions={points}
          pathOptions={{ color: '#f59e0b', weight: 3, opacity: 0.9, dashArray: '4, 4' }}
        />
      )}
      {points.map((pt, idx) => (
        <CircleMarker
          key={`m-${idx}`}
          center={pt}
          radius={5}
          pathOptions={{ color: '#f59e0b', fillColor: '#fbbf24', fillOpacity: 1, weight: 2 }}
        />
      ))}
    </>
  );
};
