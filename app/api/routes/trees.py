"""Sandalwood tree registration, tracking, and spatial query API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.database.models.tree import Tree, TreeStatus
from app.schemas.tree import (
    TreeRegisterRequest,
    TreeUpdateRequest,
    TreeResponse,
    NearbyTreesRequest,
    NearbyTreeItem,
    NearbyTreesResponse,
    TreeDeletedResponse,
)
from app.schemas.tree_fetch import TreeFetchResponse
from app.schemas.tree_status import TreeStatusUpdateRequest
from app.services.tree_service import TreeService
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/trees", tags=["Sandalwood Trees"])


@router.post(
    "/fetch",
    response_model=TreeFetchResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch and Register External Sandalwood Trees",
    description="Calls external biodiversity APIs (GBIF, iNaturalist) to fetch occurrence records, deduplicate, and register new trees in the database.",
)
def fetch_external_trees(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
):
    result = TreeService.fetch_and_register_external(db=db, requested_by=current_user.id)
    return result


@router.post(
    "",
    response_model=TreeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Sandalwood Tree",
    description="Registers a sandalwood tree using an operator-assigned Tree ID (e.g. KA-01), validates GPS against the region boundary, and stores live area weather with that Tree ID.",
)
def register_tree(
    payload: TreeRegisterRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> TreeResponse:
    tree = TreeService.register_tree(
        db=db,
        request=payload,
        registered_by_user_id=current_user.id,
    )
    return TreeResponse.model_validate(tree)


@router.get(
    "",
    response_model=List[TreeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Sandalwood Trees",
    description="Retrieves a list of registered sandalwood trees with optional region and health status filters.",
)
def list_trees(
    region_id: Optional[str] = Query(None, description="Filter by region code or integer ID"),
    tree_status: Optional[TreeStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TreeResponse]:
    trees = TreeService.list_trees(
        db=db,
        region_identifier=region_id,
        status_filter=tree_status,
        skip=skip,
        limit=limit,
    )
    return [TreeResponse.model_validate(t) for t in trees]


@router.get(
    "/{tree_uid}",
    response_model=TreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Sandalwood Tree Details",
    description="Retrieves full registration information, GPS coordinates, and health status for a specific tree by Tree ID.",
)
def get_tree(
    tree_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TreeResponse:
    tree = TreeService.get_tree_by_uid(db=db, identifier=tree_uid)
    return TreeResponse.model_validate(tree)


@router.put(
    "/{tree_uid}",
    response_model=TreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Tree Measurements & Health",
    description="Updates physical attributes (girth, height, age) or operational status of a registered sandalwood tree.",
)
def update_tree(
    tree_uid: str,
    payload: TreeUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> TreeResponse:
    tree = TreeService.update_tree(
        db=db,
        identifier=tree_uid,
        request=payload,
    )
    return TreeResponse.model_validate(tree)


@router.post(
    "/{tree_uid}/environment/refresh",
    status_code=status.HTTP_201_CREATED,
    summary="Refresh Live Area Weather for Tree",
    description="Fetches current Open-Meteo weather for the tree GPS and stores a new environmental_measurements row linked to this Tree ID.",
)
def refresh_tree_environment(
    tree_uid: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
):
    from app.services.tree_environment_service import TreeEnvironmentService
    from app.schemas.measurement import MeasurementResponse
    from app.core.errors import AppException

    tree = TreeService.get_tree_by_uid(db=db, identifier=tree_uid)
    measurement = TreeEnvironmentService.capture_live_environment_for_tree(
        db=db,
        tree=tree,
        run_anomaly_check=True,
    )
    if measurement is None:
        raise AppException(
            message=f"Could not fetch live weather for tree '{tree_uid}'",
            status_code=502,
            error_code="WEATHER_FETCH_FAILED",
        )
    return MeasurementResponse.model_validate(measurement)


@router.post(
    "/nearby",
    response_model=NearbyTreesResponse,
    status_code=status.HTTP_200_OK,
    summary="Find Nearby Sandalwood Trees",
    description="Spatial distance query: finds all sandalwood trees within a radius (in meters) of a given GPS coordinate point.",
)
def find_nearby_trees(
    payload: NearbyTreesRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> NearbyTreesResponse:
    nearby_results = TreeService.find_nearby_trees(
        db=db,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_meters=payload.radius_meters,
        region_identifier=payload.region_id,
    )

    items = [
        NearbyTreeItem(
            tree=TreeResponse.model_validate(t),
            distance_meters=dist,
        )
        for t, dist in nearby_results
    ]

    return NearbyTreesResponse(
        center_latitude=payload.latitude,
        center_longitude=payload.longitude,
        radius_meters=payload.radius_meters,
        total_found=len(items),
        trees=items,
    )


@router.delete(
    "/{tree_uid}",
    response_model=TreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Decommission Sandalwood Tree",
    description="Marks a sandalwood tree as HARVESTED or REMOVED (Admin or Operator only).",
)
def decommission_tree(
    tree_uid: str,
    status_update: TreeStatus = Query(TreeStatus.HARVESTED, description="Decommissioning status"),
    reason: Optional[str] = Query(None, description="Reason for status change"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> TreeResponse:
    tree = TreeService.decommission_tree(
        db=db,
        identifier=tree_uid,
        status_update=status_update,
        reason=reason,
    )
    return TreeResponse.model_validate(tree)


@router.delete(
    "/{tree_uid}/record",
    response_model=TreeDeletedResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently Delete Sandalwood Tree",
    description="Removes a registered sandalwood tree from the registry (Admin or Operator only). Related history is retained with the tree link cleared.",
)
def delete_tree_record(
    tree_uid: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> TreeDeletedResponse:
    deleted_uid = TreeService.delete_tree(db=db, identifier=tree_uid)
    return TreeDeletedResponse(tree_uid=deleted_uid, deleted=True)


@router.patch(
    "/{tree_uid}/status",
    response_model=TreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Tree Status",
    description="Updates the protected status of a registered sandalwood tree, optionally recording a reason for the change. Only admin or operator roles may perform this operation.",
)
def update_tree_status(
    tree_uid: str,
    payload: TreeStatusUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> TreeResponse:
    tree = TreeService.update_status(db=db, tree_uid=tree_uid, status=payload.status, reason=payload.reason)
    return TreeResponse.model_validate(tree)


