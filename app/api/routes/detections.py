"""API for unassigned map detections and operator Tree ID assignment."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.schemas.detection import DetectionResponse, DetectionAssignRequest
from app.schemas.tree import TreeResponse
from app.services.detection_service import DetectionService
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/detections", tags=["Map Detections"])


@router.get(
    "",
    response_model=List[DetectionResponse],
    summary="List Unassigned Map Detections",
    description="Returns sandalwood detections on the map that do not yet have an operator-assigned Tree ID.",
)
def list_detections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DetectionResponse]:
    items = DetectionService.list_unassigned(db=db)
    return [DetectionResponse.model_validate(d) for d in items]


@router.post(
    "/{detection_uid}/assign",
    response_model=TreeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign Tree ID to Detection",
    description="Operator chooses a Tree ID (e.g. KA-01). Registers the tree, stores live weather, and removes the unassigned detection marker.",
)
def assign_detection(
    detection_uid: str,
    payload: DetectionAssignRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> TreeResponse:
    _det, tree = DetectionService.assign_tree_id(
        db=db,
        detection_uid=detection_uid,
        request=payload,
        registered_by_user_id=current_user.id,
    )
    return TreeResponse.model_validate(tree)


@router.post(
    "/migrate-legacy",
    status_code=status.HTTP_200_OK,
    summary="Migrate Legacy Auto-ID Trees to Unassigned Detections",
    description="One-time helper: moves SW-KA/GBIF auto-imported trees into detections without Tree IDs.",
)
def migrate_legacy(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    moved = DetectionService.migrate_legacy_registered_trees_to_detections(db=db)
    return {"moved_to_detections": moved, "message": "Legacy auto-ID trees are now unassigned map detections"}
