"""Global Internet Sandalwood Biodiversity API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.api.deps import get_current_user, require_roles
from app.services.global_tree_service import GlobalTreeService
from app.schemas.global_tree import (
    GlobalTreeItem,
    GlobalTreeStatsResponse,
    GlobalTreeImportResponse,
    GlobalTreeEnvironmentSnapshot,
    GlobalTreeRegisterRequest,
    GlobalTreeRegisterResponse,
)

router = APIRouter(prefix="/global-trees", tags=["Global Internet Sandalwood Data"])


@router.get(
    "",
    response_model=List[GlobalTreeItem],
    status_code=status.HTTP_200_OK,
    summary="List all Internet Sandalwood Tree Locations",
    description="Returns aggregated, research-grade sandalwood occurrences from GBIF and iNaturalist open data, annotated with local database asset registration status.",
)
def list_global_trees(
    source: Optional[str] = Query(None, description="Filter by data source (e.g. GBIF, iNaturalist)"),
    state: Optional[str] = Query(None, description="Filter by state or province (e.g. Karnataka, Tamil Nadu)"),
    has_photo: Optional[bool] = Query(None, description="Filter records that have ground / specimen photos"),
    query: Optional[str] = Query(None, description="Search term matching locality, observer, or taxon name"),
    limit: int = Query(800, ge=1, le=5000, description="Max records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[GlobalTreeItem]:
    return GlobalTreeService.get_annotated_trees(
        db=db,
        source=source,
        state=state,
        has_photo=has_photo,
        query=query,
        limit=limit,
    )


@router.get(
    "/stats",
    response_model=GlobalTreeStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Global Sandalwood Statistics",
    description="Returns breakdown of total internet occurrences, sources, photo availability, and platform asset enrollment.",
)
def get_global_tree_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GlobalTreeStatsResponse:
    return GlobalTreeService.get_stats(db=db)


@router.get(
    "/environment",
    response_model=GlobalTreeEnvironmentSnapshot,
    status_code=status.HTTP_200_OK,
    summary="Preview environmental data for a selected internet sandalwood tree",
    description=(
        "Fetches live microclimate (temperature, humidity, soil, wind, suitability) at the "
        "selected specimen GPS and attaches an allometric heartwood estimate without registering it."
    ),
)
def preview_selected_tree_environment(
    occurrence_id: str = Query(..., min_length=1, description="Internet specimen id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GlobalTreeEnvironmentSnapshot:
    return GlobalTreeService.preview_environment(occurrence_id=occurrence_id)


@router.post(
    "/register",
    response_model=GlobalTreeRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a selected internet sandalwood tree with coordinates and environment",
    description="Registers the selected GBIF/iNaturalist specimen using its catalog GPS and stores live environmental data with the assigned Tree ID.",
)
def register_selected_internet_tree(
    payload: GlobalTreeRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> GlobalTreeRegisterResponse:
    return GlobalTreeService.register_selected_tree(
        db=db,
        occurrence_id=payload.occurrence_id,
        tree_uid=payload.tree_uid,
        notes=payload.notes,
    )


@router.post(
    "/import-all",
    response_model=GlobalTreeImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import All Internet Sandalwood Locations into Platform Asset Registry",
    description="Harvests all verified internet sandalwood locations, matches spatial regions, assigns unique asset UIDs, and enrolls them into the database.",
)
def import_all_internet_trees(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> GlobalTreeImportResponse:
    return GlobalTreeService.import_all_to_db(db=db)
