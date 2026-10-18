// Geographic and GPS navigation utility functions

/** Shivamogga sandalwood reserve — default GIS radar center. */
export const DEFAULT_MAP_CENTER = {
  latitude: 13.9355,
  longitude: 75.5652,
  zoom: 8,
} as const;

export interface GPSCoordinate {
  latitude: number;
  longitude: number;
  altitude?: number | null;
  accuracy?: number;
  heading?: number | null;
  speed?: number | null;
}

/** Ray-casting point-in-polygon. Ring is GeoJSON [lon, lat][]. */
export function pointInPolygonRing(
  latitude: number,
  longitude: number,
  ring: number[][]
): boolean {
  if (!ring || ring.length < 3) return false;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersects =
      yi > latitude !== yj > latitude &&
      longitude < ((xj - xi) * (latitude - yi)) / (yj - yi + Number.EPSILON) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

/** True if lat/lon falls inside a GeoJSON Polygon / MultiPolygon boundary. */
export function pointInGeoJSON(
  latitude: number,
  longitude: number,
  geojson?: { type?: string; coordinates?: number[][][] | number[][][][] } | null
): boolean {
  if (!geojson?.type || !geojson.coordinates) return true;
  if (geojson.type === 'Polygon') {
    const rings = geojson.coordinates as number[][][];
    if (!rings[0]?.length) return true;
    if (!pointInPolygonRing(latitude, longitude, rings[0])) return false;
    for (let h = 1; h < rings.length; h++) {
      if (pointInPolygonRing(latitude, longitude, rings[h])) return false;
    }
    return true;
  }
  if (geojson.type === 'MultiPolygon') {
    const polys = geojson.coordinates as number[][][][];
    return polys.some((polygon) => {
      if (!polygon[0]?.length) return false;
      if (!pointInPolygonRing(latitude, longitude, polygon[0])) return false;
      for (let h = 1; h < polygon.length; h++) {
        if (pointInPolygonRing(latitude, longitude, polygon[h])) return false;
      }
      return true;
    });
  }
  return true;
}

export interface RouteStep {
  instruction: string;
  distanceMeters: number;
  durationSeconds: number;
  name: string;
}

export interface DetailedRouteResponse {
  distanceMeters: number;
  durationMinutes: number;
  geometry: [number, number][]; // [lat, lon]
  steps: RouteStep[];
  isRealRoadNetwork: boolean;
}

export interface ReverseGeocodeResult {
  displayName: string;
  road?: string;
  village?: string;
  suburb?: string;
  county?: string; // Taluk
  stateDistrict?: string;
  state?: string;
  country?: string;
  postcode?: string;
}

// Calculate great-circle distance between two points using Haversine formula (in meters)
export function calculateHaversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000; // Earth radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Format distance nicely: "450 m" or "14.2 km"
export function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  return `${(meters / 1000).toFixed(2)} km`;
}

// Calculate initial bearing from point 1 to point 2 in degrees [0, 360)
export function calculateBearing(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

  const y = Math.sin(deltaLambda) * Math.cos(phi2);
  const x =
    Math.cos(phi1) * Math.sin(phi2) -
    Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);
  const theta = Math.atan2(y, x);
  return (theta * 180 / Math.PI + 360) % 360;
}

// Convert bearing degrees to cardinal direction (N, NE, E, SE, S, SW, W, NW)
export function bearingToCardinal(bearing: number): string {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const index = Math.round(bearing / 45) % 8;
  return directions[index];
}

// Format GPS coordinates with sub-meter 6-decimal precision
export function formatCoordinates(lat: number, lon: number): string {
  return `${lat.toFixed(6)}°N, ${lon.toFixed(6)}°E`;
}

// Fetch Real Road Network Navigation Route from Open Source Routing Machine (OSRM)
export async function fetchOSRMRoute(
  startLat: number,
  startLon: number,
  endLat: number,
  endLon: number
): Promise<DetailedRouteResponse> {
  const url = `https://router.project-osrm.org/route/v1/driving/${startLon},${startLat};${endLon},${endLat}?overview=full&geometries=geojson&steps=true`;

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(6000) });
    if (res.ok) {
      const data = await res.json();
      if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
        const route = data.routes[0];
        const rawCoords = route.geometry.coordinates; // [lon, lat]
        const latLngPoints: [number, number][] = rawCoords.map((c: [number, number]) => [c[1], c[0]]);

        const steps: RouteStep[] = [];
        if (route.legs && route.legs[0]?.steps) {
          route.legs[0].steps.forEach((s: {
            maneuver?: { modifier?: string; type?: string };
            name?: string;
            distance?: number;
            duration?: number;
          }) => {
            if (s.maneuver) {
              const modifier = s.maneuver.modifier ? ` ${s.maneuver.modifier}` : '';
              const instr = `${s.maneuver.type || 'Proceed'}${modifier} ${s.name ? 'onto ' + s.name : ''}`.trim();
              steps.push({
                instruction: instr || 'Proceed along route',
                distanceMeters: s.distance || 0,
                durationSeconds: s.duration || 0,
                name: s.name || 'Forest / Highway Track',
              });
            }
          });
        }

        return {
          distanceMeters: route.distance,
          durationMinutes: Math.max(1, Math.round(route.duration / 60)),
          geometry: latLngPoints,
          steps,
          isRealRoadNetwork: true,
        };
      }
    }
  } catch (err) {
    console.debug('OSRM routing fetch fallback to geodetic line:', err);
  }

  // Fallback to high-precision direct GPS line
  const directDist = calculateHaversineDistance(startLat, startLon, endLat, endLon);
  const stepsCount = 24;
  const dLat = (endLat - startLat) / stepsCount;
  const dLon = (endLon - startLon) / stepsCount;
  const points: [number, number][] = [];

  for (let i = 0; i <= stepsCount; i++) {
    points.push([startLat + dLat * i, startLon + dLon * i]);
  }

  return {
    distanceMeters: directDist,
    durationMinutes: Math.max(1, Math.round(directDist / 700)),
    geometry: points,
    steps: [
      {
        instruction: 'Direct GPS Geodetic Line Navigation to Target Asset',
        distanceMeters: directDist,
        durationSeconds: Math.round(directDist / 12),
        name: 'Target GPS Coordinates',
      },
    ],
    isRealRoadNetwork: false,
  };
}

// Fetch exact reverse geocoding address from OpenStreetMap Nominatim
export async function fetchNominatimReverseGeocode(
  lat: number,
  lon: number
): Promise<ReverseGeocodeResult | null> {
  const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`;

  try {
    const res = await fetch(url, {
      headers: {
        'User-Agent': 'ZeroTrustAgroforestry/1.0 (sandalwood-gps)',
        Accept: 'application/json',
      },
      signal: AbortSignal.timeout(5000),
    });

    if (res.ok) {
      const data = await res.json();
      const addr = data.address || {};
      return {
        displayName: data.display_name || `${lat.toFixed(5)}, ${lon.toFixed(5)}`,
        road: addr.road,
        village: addr.village || addr.hamlet || addr.suburb || addr.town,
        suburb: addr.suburb,
        county: addr.county || addr.taluk,
        stateDistrict: addr.state_district || addr.district,
        state: addr.state || 'Karnataka',
        country: addr.country || 'India',
        postcode: addr.postcode,
      };
    }
  } catch (e) {
    console.debug('Reverse geocode fallback:', e);
  }

  return null;
}

// Search real-world places using OpenStreetMap Nominatim Forward Geocoding
// Works globally like Google Maps — returns top results with type labels
export async function fetchNominatimSearch(
  query: string
): Promise<{ lat: number; lon: number; displayName: string; type?: string; category?: string }[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];

  // Support direct coordinate paste: "12.3456, 76.1234" or "12.3456 76.1234"
  const coordMatch = trimmed.match(/^([-+]?\d{1,3}(?:\.\d+)?)[,\s]+([-+]?\d{1,3}(?:\.\d+)?)$/);
  if (coordMatch) {
    const lat = parseFloat(coordMatch[1]);
    const lon = parseFloat(coordMatch[2]);
    if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
      return [{ lat, lon, displayName: `${lat.toFixed(6)}, ${lon.toFixed(6)}`, type: 'coordinate', category: 'coordinate' }];
    }
  }

  // Build Nominatim URL — global search, no country restriction, structured result
  const params = new URLSearchParams({
    format: 'json',
    q: trimmed,
    limit: '8',
    addressdetails: '1',
    namedetails: '1',
    'accept-language': 'en',
    dedupe: '1',
  });

  const url = `https://nominatim.openstreetmap.org/search?${params.toString()}`;

  try {
    const res = await fetch(url, {
      headers: {
        'User-Agent': 'ZeroTrustAgroforestry/1.0 (sandalwood-gps-monitoring)',
        'Accept': 'application/json',
        'Referer': 'https://localhost:3000',
      },
      signal: AbortSignal.timeout(8000),
    });

    if (!res.ok) {
      console.warn(`Nominatim returned HTTP ${res.status}`);
      return [];
    }

    const data: Array<{
      lat: string;
      lon: string;
      display_name: string;
      type?: string;
      category?: string;
      namedetails?: { name?: string };
      address?: { country?: string; state?: string; city?: string; town?: string; village?: string };
    }> = await res.json();

    return data.map((item) => {
      // Build a clean short label: "Name, City/State, Country"
      const addr = item.address || {};
      const placeName = item.namedetails?.name || item.display_name.split(',')[0];
      const locality = addr.city || addr.town || addr.village || addr.state || '';
      const country = addr.country || '';
      const shortLabel = [placeName, locality, country].filter(Boolean).join(', ');

      return {
        lat: parseFloat(item.lat),
        lon: parseFloat(item.lon),
        displayName: shortLabel || item.display_name,
        type: item.type,
        category: item.category,
      };
    });
  } catch (e) {
    console.debug('Nominatim search error:', e);
    return [];
  }
}

