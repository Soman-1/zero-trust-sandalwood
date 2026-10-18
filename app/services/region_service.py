"""Region management and geographical boundary verification service."""

from typing import List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.logging import logger
from app.core.errors import AppException, NotFoundError
from app.core.geo import validate_coordinates, point_in_geojson, calculate_centroid
from app.database.models.region import Region, RegionStatus
from app.database.models.tree import Tree
from app.database.models.device import Device
from app.schemas.region import RegionCreateRequest, RegionUpdateRequest


class RegionService:
    """Service handling forest/agroforestry region lifecycle and GPS validation."""

    @staticmethod
    def create_region(db: Session, request: RegionCreateRequest) -> Region:
        """Create a new monitoring region with validated GeoJSON boundaries."""
        # 1. Check for duplicate region_id
        stmt = select(Region).where(Region.region_id == request.region_id)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            raise AppException(
                message=f"Region with ID '{request.region_id}' already exists",
                status_code=400,
                error_code="REGION_ALREADY_EXISTS",
            )

        # 2. Compute centroids automatically if omitted
        center_lat = request.center_latitude
        center_lon = request.center_longitude
        if (center_lat is None or center_lon is None) and request.boundary_geojson:
            calc_lat, calc_lon = calculate_centroid(request.boundary_geojson)
            center_lat = center_lat if center_lat is not None else calc_lat
            center_lon = center_lon if center_lon is not None else calc_lon

        region = Region(
            region_id=request.region_id,
            name=request.name,
            description=request.description,
            boundary_geojson=request.boundary_geojson,
            center_latitude=center_lat,
            center_longitude=center_lon,
            area_hectares=request.area_hectares,
            status=request.status,
        )
        db.add(region)
        db.commit()
        db.refresh(region)

        logger.info(f"Created monitoring region '{region.region_id}' ({region.name})")
        return region

    @staticmethod
    def get_region_by_identifier(db: Session, identifier: Union[str, int]) -> Region:
        """Retrieve region by database integer id or unique string region_id."""
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            region = db.get(Region, int(identifier))
            if region:
                return region

        stmt = select(Region).where(Region.region_id == str(identifier))
        region = db.execute(stmt).scalar_one_or_none()
        if not region:
            raise NotFoundError(message=f"Region '{identifier}' not found")
        return region

    @staticmethod
    def list_regions(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[RegionStatus] = None,
    ) -> List[Region]:
        """List monitoring regions with optional status filtering."""
        stmt = select(Region)
        if status_filter:
            stmt = stmt.where(Region.status == status_filter)
        stmt = stmt.offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_region(
        db: Session,
        identifier: Union[str, int],
        request: RegionUpdateRequest,
    ) -> Region:
        """Update existing region boundaries and properties."""
        region = RegionService.get_region_by_identifier(db, identifier)

        if request.name is not None:
            region.name = request.name
        if request.description is not None:
            region.description = request.description
        if request.status is not None:
            region.status = request.status
        if request.area_hectares is not None:
            region.area_hectares = request.area_hectares

        if request.boundary_geojson is not None:
            region.boundary_geojson = request.boundary_geojson
            # Recalculate centroids if not provided
            if request.center_latitude is None and request.center_longitude is None:
                calc_lat, calc_lon = calculate_centroid(request.boundary_geojson)
                region.center_latitude = calc_lat
                region.center_longitude = calc_lon

        if request.center_latitude is not None:
            region.center_latitude = request.center_latitude
        if request.center_longitude is not None:
            region.center_longitude = request.center_longitude

        db.commit()
        db.refresh(region)
        logger.info(f"Updated region '{region.region_id}'")
        return region

    @staticmethod
    def is_point_in_region(region: Region, latitude: float, longitude: float) -> bool:
        """
        Zero Trust GPS Gatekeeper:
        Validates coordinate ranges and performs exact point-in-polygon checks against region boundary.
        """
        validate_coordinates(latitude, longitude)
        return point_in_geojson(latitude, longitude, region.boundary_geojson)

    @staticmethod
    def get_region_counts(db: Session, region_id: int) -> Tuple[int, int]:
        """Return (tree_count, device_count) for a given region."""
        tree_count = db.execute(
            select(func.count()).select_from(Tree).where(Tree.region_id == region_id)
        ).scalar() or 0
        device_count = db.execute(
            select(func.count()).select_from(Device).where(Device.assigned_region_id == region_id)
        ).scalar() or 0
        return tree_count, device_count

    @staticmethod
    def decommission_region(db: Session, identifier: Union[str, int]) -> Region:
        """Decommission / deactivate a monitored region."""
        region = RegionService.get_region_by_identifier(db, identifier)
        region.status = RegionStatus.INACTIVE
        db.commit()
        db.refresh(region)
        logger.info(f"Decommissioned region '{region.region_id}'")
        return region

