from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.tree_service import TreeService
from app.api.deps import require_roles
from app.database.models.user import User, UserRole
from app.schemas.tree_fetch import TreeFetchResponse

router = APIRouter(prefix="/trees/fetch", tags=["Sandalwood Trees"])

@router.post(
    "",
    response_model=TreeFetchResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch and Register External Sandalwood Trees",
    description="Calls external biodiversity APIs (GBIF, iNaturalist) to fetch occurrence records, deduplicate, and register new trees in the database."
)
def fetch_external_trees(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
):
    result = TreeService.fetch_and_register_external(db=db, requested_by=current_user.id)
    return result
