"""Geospatial utilities: GPS coordinate validation, Ray-Casting point-in-polygon, and geometric calculations."""

from typing import List, Dict, Any, Tuple, Optional
from app.core.errors import AppException


def validate_coordinates(latitude: float, longitude: float) -> None:
    """Validate that GPS coordinates are within realistic global ranges."""
    if latitude is None or longitude is None:
        raise AppException(
            message="GPS coordinates cannot be null",
            status_code=400,
            error_code="INVALID_GPS_COORDINATES",
        )
    if not (-90.0 <= latitude <= 90.0):
        raise AppException(
            message=f"Invalid latitude '{latitude}'. Latitude must be between -90.0 and 90.0",
            status_code=400,
            error_code="INVALID_LATITUDE",
        )
    if not (-180.0 <= longitude <= 180.0):
        raise AppException(
            message=f"Invalid longitude '{longitude}'. Longitude must be between -180.0 and 180.0",
            status_code=400,
            error_code="INVALID_LONGITUDE",
        )


def point_in_linear_ring(lat: float, lon: float, ring: List[List[float]]) -> bool:
    """
    Ray-Casting Algorithm to test if a point (lat, lon) is inside a GeoJSON linear ring.
    GeoJSON linear ring format: [[lon1, lat1], [lon2, lat2], ..., [lon1, lat1]]
    """
    n = len(ring)
    if n < 3:
        return False

    inside = False
    # Standard GeoJSON coordinates are [longitude, latitude]
    p1_lon, p1_lat = ring[0][0], ring[0][1]

    for i in range(1, n + 1):
        p2_lon, p2_lat = ring[i % n][0], ring[i % n][1]

        # Check if ray crosses the line segment between (p1_lon, p1_lat) and (p2_lon, p2_lat)
        if min(p1_lat, p2_lat) < lat <= max(p1_lat, p2_lat):
            if lon <= max(p1_lon, p2_lon):
                if p1_lat != p2_lat:
                    x_inters = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                else:
                    x_inters = p1_lon

                if p1_lon == p2_lon or lon <= x_inters:
                    inside = not inside

        p1_lon, p1_lat = p2_lon, p2_lat

    return inside


def point_in_geojson(lat: float, lon: float, geojson: Optional[Dict[str, Any]]) -> bool:
    """
    Test if (latitude, longitude) is inside a GeoJSON Polygon or MultiPolygon.
    Returns True if no boundary is defined (unconstrained) or if the point is strictly inside.
    """
    if not geojson:
        return True

    geom_type = geojson.get("type")
    coordinates = geojson.get("coordinates")

    if not geom_type or not coordinates:
        return True

    if geom_type == "Polygon":
        # First ring is the exterior boundary
        if not coordinates or not coordinates[0]:
            return True
        exterior_ring = coordinates[0]
        is_inside_exterior = point_in_linear_ring(lat, lon, exterior_ring)
        if not is_inside_exterior:
            return False

        # Interior holes (if any)
        for hole in coordinates[1:]:
            if point_in_linear_ring(lat, lon, hole):
                return False  # Inside a hole means outside the polygon

        return True

    elif geom_type == "MultiPolygon":
        # Inside any sub-polygon
        for polygon in coordinates:
            exterior_ring = polygon[0]
            if point_in_linear_ring(lat, lon, exterior_ring):
                # Check if in holes of this polygon
                in_hole = any(point_in_linear_ring(lat, lon, hole) for hole in polygon[1:])
                if not in_hole:
                    return True
        return False

    return True


def calculate_centroid(geojson: Optional[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate the center (latitude, longitude) from GeoJSON coordinates.
    Returns: (center_latitude, center_longitude)
    """
    if not geojson or "coordinates" not in geojson:
        return None, None

    geom_type = geojson.get("type")
    coords = geojson.get("coordinates")

    all_lats: List[float] = []
    all_lons: List[float] = []

    if geom_type == "Polygon" and coords:
        for pt in coords[0]:
            all_lons.append(pt[0])
            all_lats.append(pt[1])
    elif geom_type == "MultiPolygon" and coords:
        for poly in coords:
            for pt in poly[0]:
                all_lons.append(pt[0])
                all_lats.append(pt[1])

    if not all_lats:
        return None, None

    avg_lat = sum(all_lats) / len(all_lats)
    avg_lon = sum(all_lons) / len(all_lons)
    return round(avg_lat, 6), round(avg_lon, 6)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two GPS coordinates in meters.
    Uses the Haversine formula.
    """
    import math

    # Earth radius in meters
    R = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return round(distance, 2)

