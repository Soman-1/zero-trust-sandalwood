"""Dashboard Integration, GIS map layers, and time-series charting API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    GISMapLayerResponse,
    TimeSeriesResponse,
    RegionDashboardResponse,
)
from app.services.dashboard_service import DashboardService
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/dashboard", tags=["Dashboard & GIS Analytics"])


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Executive Dashboard Overview",
    description="Calculates executive KPIs across regions, sandalwood tree health assets, active IoT devices, 24h environmental trends, and active alerts.",
)
def get_overview_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardOverviewResponse:
    return DashboardService.get_overview_metrics(db=db)


@router.get(
    "/map-layer",
    response_model=GISMapLayerResponse,
    status_code=status.HTTP_200_OK,
    summary="GIS Geospatial Map Layer (GeoJSON)",
    description="Returns standard GeoJSON FeatureCollection containing region polygons, sandalwood tree coordinates, and active IoT nodes for Mapbox/Leaflet GIS rendering.",
)
def get_gis_map_layer(
    region_id: Optional[str] = Query(None, description="Optional region code to filter GIS features"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> GISMapLayerResponse:
    return DashboardService.get_gis_map_layers(db=db, region_identifier=region_id)


@router.get(
    "/timeseries",
    response_model=TimeSeriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Time-Series Charting Telemetry",
    description="Fetches chronological telemetry observations suitable for frontend line/bar charts.",
)
def get_timeseries_data(
    region_id: Optional[str] = Query(None, description="Filter by region code"),
    tree_id: Optional[str] = Query(None, description="Filter by sandalwood Tree UID"),
    hours: int = Query(48, ge=1, le=720, description="Hours of history to retrieve"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TimeSeriesResponse:
    return DashboardService.get_timeseries_chart_data(
        db=db,
        region_identifier=region_id,
        tree_identifier=tree_id,
        hours=hours,
    )


@router.get(
    "/region/{region_id}",
    response_model=RegionDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Single Region Operational Deep-Dive",
    description="Deep-dive operational dashboard for a specific agroforestry region.",
)
def get_region_dashboard(
    region_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegionDashboardResponse:
    return DashboardService.get_region_dashboard_detail(db=db, region_identifier=region_id)
