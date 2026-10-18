"""Pydantic schemas for Dashboard Integration, GIS Geospatial Map Layers, and Time-Series Feeds."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class TreeHealthBreakdown(BaseModel):
    """Sandalwood tree asset counts categorized by health status."""
    healthy: int
    at_risk: int
    diseased: int
    harvested: int
    removed: int
    total: int


class AlertSeverityBreakdown(BaseModel):
    """Active alert counts categorized by severity."""
    critical: int
    high: int
    medium: int
    low: int
    total_active: int


class Environmental24hSummary(BaseModel):
    """Average physical metrics across the last 24 hours."""
    avg_temperature: Optional[float] = None
    avg_humidity: Optional[float] = None
    avg_soil_moisture: Optional[float] = None
    total_readings_24h: int


class DashboardOverviewResponse(BaseModel):
    """Executive operational dashboard KPI payload."""
    total_regions: int
    active_regions: int
    tree_assets: TreeHealthBreakdown
    devices: Dict[str, int]
    environmental_24h: Environmental24hSummary
    alerts: AlertSeverityBreakdown
    security: Dict[str, Any]


class GeoJSONFeature(BaseModel):
    """Standard GeoJSON Feature representation."""
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class GISMapLayerResponse(BaseModel):
    """Standard GeoJSON FeatureCollection for GIS map rendering."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]


class TimeSeriesPoint(BaseModel):
    """Single time-series data point for frontend charting."""
    timestamp: datetime
    temperature: float
    humidity: float
    soil_moisture: float
    is_anomaly: bool


class TimeSeriesResponse(BaseModel):
    """Time-series telemetry response for charts."""
    region_id: Optional[str] = None
    tree_uid: Optional[str] = None
    hours: int
    total_points: int
    points: List[TimeSeriesPoint]


class RegionDashboardResponse(BaseModel):
    """Comprehensive single region operational deep-dive payload."""
    region_id: str
    name: str
    status: str
    center_latitude: Optional[float]
    center_longitude: Optional[float]
    area_hectares: Optional[float]
    tree_assets: TreeHealthBreakdown
    latest_environmental: Optional[Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]
    assigned_devices: List[Dict[str, Any]]
