from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models.tree import TreeStatus
from app.schemas.tree_status import TreeStatusUpdateRequest
from app.services.tree_service import TreeService
from app.api.deps import get_current_user, require_roles
from app.database.models.user import User, UserRole
from app.schemas.tree import TreeResponse

router = APIRouter(
    prefix="/trees/{tree_uid}/status",
    tags=["Sandalwood Trees"]
)

@router.patch(
    path="",
    response_model=TreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Tree Status",
    description="Updates the protected status of a registered sandalwood tree, optionally recording a reason for the change. Only admin or operator roles may perform this operation."
)
def update_tree_status(
    tree_uid: str,
    payload: TreeStatusUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> TreeResponse:
    tree = TreeService.update_status(db=db, tree_uid=tree_uid, status=payload.status, reason=payload.reason)
    return TreeResponse.model_validate(tree)
