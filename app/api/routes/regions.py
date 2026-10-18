"""Forest and agroforestry monitoring region API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.database.models.region import Region, RegionStatus
from app.schemas.region import (
    RegionCreateRequest,
    RegionUpdateRequest,
    RegionResponse,
    CoordinateCheckRequest,
    CoordinateCheckResponse,
)
from app.services.region_service import RegionService
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/regions", tags=["Regions"])


def build_region_response(db: Session, region: Region) -> RegionResponse:
    """Helper to assemble RegionResponse with associated counts."""
    tree_count, device_count = RegionService.get_region_counts(db, region.id)
    resp = RegionResponse.model_validate(region)
    resp.tree_count = tree_count
    resp.device_count = device_count
    return resp


@router.post(
    "",
    response_model=RegionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Monitoring Region",
    description="Registers a new forest or agroforestry monitoring region with GeoJSON boundary polygons.",
)
def create_region(
    payload: RegionCreateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> RegionResponse:
    region = RegionService.create_region(db=db, request=payload)
    return build_region_response(db, region)


@router.get(
    "",
    response_model=List[RegionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Monitoring Regions",
    description="Retrieves a list of all agroforestry regions with counts of registered trees and devices.",
)
def list_regions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    region_status: Optional[RegionStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RegionResponse]:
    regions = RegionService.list_regions(
        db=db,
        skip=skip,
        limit=limit,
        status_filter=region_status,
    )
    return [build_region_response(db, r) for r in regions]


@router.get(
    "/{region_id}",
    response_model=RegionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Region Details",
    description="Retrieves full region information, boundaries, centroid, and registration counts.",
)
def get_region(
    region_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegionResponse:
    region = RegionService.get_region_by_identifier(db=db, identifier=region_id)
    return build_region_response(db, region)


@router.put(
    "/{region_id}",
    response_model=RegionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Region",
    description="Updates region boundary coordinates, description, or operational status.",
)
def update_region(
    region_id: str,
    payload: RegionUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> RegionResponse:
    region = RegionService.update_region(
        db=db,
        identifier=region_id,
        request=payload,
    )
    return build_region_response(db, region)


@router.post(
    "/{region_id}/check-coordinate",
    response_model=CoordinateCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Coordinate Inside Region",
    description="Tests whether a specific GPS coordinate falls inside the monitored region's polygon boundary.",
)
def check_coordinate(
    region_id: str,
    payload: CoordinateCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoordinateCheckResponse:
    region = RegionService.get_region_by_identifier(db=db, identifier=region_id)
    is_inside = RegionService.is_point_in_region(
        region=region,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    return CoordinateCheckResponse(
        region_id=region.region_id,
        region_name=region.name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_inside=is_inside,
        message=(
            f"Coordinate is inside boundary for {region.region_id}"
            if is_inside
            else f"Coordinate is outside boundary for {region.region_id}"
        ),
    )


@router.delete(
    "/{region_id}",
    response_model=RegionResponse,
    status_code=status.HTTP_200_OK,
    summary="Decommission Region",
    description="Decommissions a region by setting its status to INACTIVE (Admin only).",
)
def decommission_region(
    region_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionResponse:
    region = RegionService.decommission_region(db=db, identifier=region_id)
    return build_region_response(db, region)
