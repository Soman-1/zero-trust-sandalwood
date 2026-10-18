"""Street View 360° Panoramic AI Detection & Internet Data REST API Endpoints."""

import time
import base64
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, AppException
from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.ai.street_detector import street_detector
from app.services.street_view_service import StreetViewService
from app.schemas.street_view import (
    StreetPanoramaItem,
    StreetRoute,
    StreetDetectRequest,
    StreetDetectResponse,
    InternetPhotoItem,
    InternetStreetDataSyncRequest,
    InternetStreetDataSyncResponse,
    RegisterStreetTreeRequest,
    RegisterStreetTreeResponse,
)
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/street-view", tags=["Street View 360° & Ground AI"])


@router.get(
    "/presets",
    response_model=List[StreetPanoramaItem],
    status_code=status.HTTP_200_OK,
    summary="List All Real-World 360° Street View Panoramas",
    description="Returns high-resolution 360° equirectangular panoramas across Sandalwood reserves in Karnataka and India.",
)
def get_street_view_presets(
    current_user: User = Depends(get_current_user),
) -> List[StreetPanoramaItem]:
    return StreetViewService.get_presets()


@router.get(
    "/panorama/{preset_id}",
    response_model=StreetPanoramaItem,
    status_code=status.HTTP_200_OK,
    summary="Get Specific 360° Street View Panorama Scene",
)
def get_single_panorama(
    preset_id: str,
    current_user: User = Depends(get_current_user),
) -> StreetPanoramaItem:
    pano = StreetViewService.get_panorama(preset_id)
    if not pano:
        raise NotFoundError(message=f"Street View panorama with ID '{preset_id}' not found.")
    return pano


@router.get(
    "/routes",
    response_model=List[StreetRoute],
    status_code=status.HTTP_200_OK,
    summary="List Roadway Routes with Step-by-Step Waypoints",
)
def get_street_routes(
    current_user: User = Depends(get_current_user),
) -> List[StreetRoute]:
    return StreetViewService.get_routes()


@router.post(
    "/detect",
    response_model=StreetDetectResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Ground-Level AI Model on Street View Image / Panorama",
    description="Identifies Santalum album trees, bark texture, DBH, host tree pairings, and estimated heartwood volume from street imagery.",
)
def detect_sandalwood_street_view(
    payload: StreetDetectRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> StreetDetectResponse:
    if payload.image_base64:
        try:
            # Handle data URL prefix if present
            raw_b64 = payload.image_base64
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            result = street_detector.detect_from_image_bytes(
                image_bytes=img_bytes,
                confidence_threshold=payload.confidence_threshold,
                latitude=payload.latitude,
                longitude=payload.longitude,
                camera_fov_deg=payload.camera_fov_deg,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process custom image: {str(e)}",
            )
    elif payload.preset_id:
        try:
            result = street_detector.detect_from_preset(
                preset_id=payload.preset_id,
                confidence_threshold=payload.confidence_threshold,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    else:
        # Fallback to default Mysore Highway preset
        result = street_detector.detect_from_preset(
            preset_id="mysore_sandalwood_highway",
            confidence_threshold=payload.confidence_threshold,
        )

    return StreetDetectResponse(**result)


@router.post(
    "/sync-internet-data",
    response_model=InternetStreetDataSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Import Available Street-Level Botanical Data from the Internet",
    description="Harvests ground-level Santalum album observation photos and metadata from GBIF and iNaturalist open repositories.",
)
def sync_internet_data(
    payload: InternetStreetDataSyncRequest = InternetStreetDataSyncRequest(),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> InternetStreetDataSyncResponse:
    result = StreetViewService.sync_internet_street_data(
        country=payload.country,
        state=payload.state_province,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_km=payload.radius_km or 25.0,
        limit=payload.limit,
    )
    return InternetStreetDataSyncResponse(**result)


@router.get(
    "/catalog",
    response_model=List[InternetPhotoItem],
    status_code=status.HTTP_200_OK,
    summary="List Imported Internet Ground-Level Photographs & Geotags",
)
def get_ground_photos_catalog(
    current_user: User = Depends(get_current_user),
) -> List[InternetPhotoItem]:
    return StreetViewService.get_ground_photos_catalog()


from app.services.global_street_service import global_street_service
from app.schemas.street_view import (
    StreetPanoramaItem,
    StreetRoute,
    StreetDetectRequest,
    StreetDetectResponse,
    InternetPhotoItem,
    InternetStreetDataSyncRequest,
    InternetStreetDataSyncResponse,
    RegisterStreetTreeRequest,
    RegisterStreetTreeResponse,
    GlobalDestinationItem,
    GlobalTeleportRequest,
    GlobalTeleportResponse,
)

@router.post(
    "/register-detected-tree",
    response_model=RegisterStreetTreeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Detected Tree from Street View into Zero Trust Ledger",
    description="Anchors the discovered tree to the Zero Trust registry with an immutable SHA-256 integrity hash.",
)
def register_detected_tree(
    payload: RegisterStreetTreeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> RegisterStreetTreeResponse:
    result = StreetViewService.register_tree_from_street_view(
        db=db,
        req=payload,
        current_user=current_user,
    )
    return RegisterStreetTreeResponse(**result)


@router.get(
    "/global-destinations",
    response_model=List[GlobalDestinationItem],
    status_code=status.HTTP_200_OK,
    summary="List Curated Global 360° Forest & Agroforestry Destinations",
    description="Returns verified outdoor 360° panoramas across all continents (India, Australia, Indonesia, Hawaii, Brazil, Europe).",
)
def list_global_destinations(
    continent: Optional[str] = Query(None, description="Optional continent filter"),
    current_user: User = Depends(get_current_user),
) -> List[GlobalDestinationItem]:
    destinations = global_street_service.list_destinations(continent=continent)
    return [GlobalDestinationItem(**d) for d in destinations]


@router.post(
    "/teleport-global",
    response_model=GlobalTeleportResponse,
    status_code=status.HTTP_200_OK,
    summary="Teleport to Any GPS Coordinate on Earth with Outdoor Street View",
    description="Finds the nearest verified outdoor road/forest panorama on Earth, eliminating indoor commercial stores.",
)
def teleport_global_coordinate(
    payload: GlobalTeleportRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> GlobalTeleportResponse:
    res = global_street_service.teleport(
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_label=payload.location_label,
    )
    return GlobalTeleportResponse(**res)

