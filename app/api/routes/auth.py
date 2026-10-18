"""Authentication API endpoints."""

from typing import Tuple, Optional
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    LogoutResponse,
)
from app.services.auth_service import AuthService
from app.api.deps import get_current_user, get_current_user_and_session, require_roles

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Registers a viewer account. Privileged roles are assigned only by an administrator.",
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    import app.core.runtime as runtime
    from app.core.errors import ForbiddenError

    if not settings.ALLOW_PUBLIC_REGISTRATION and not runtime.privileged_self_register:
        raise ForbiddenError(
            message="Public registration is disabled. Ask an administrator for an invite.",
            details={"allow_public_registration": False},
        )
    user = AuthService.register_user(db=db, request=payload)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates credentials and returns a Zero Trust JWT access token.",
)
def login(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    token, expires_in_seconds, user = AuthService.authenticate_user(
        db=db,
        request=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    response.set_cookie(
        key="agro_access_token",
        value=token,
        httponly=True,
        secure=settings.APP_ENV.lower() == "production",
        samesite="lax",
        max_age=expires_in_seconds,
        path="/",
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=expires_in_seconds,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Revokes current active session in the database to invalidate the token immediately.",
)
def logout(
    response: Response,
    auth_data: Tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    user, token_jti = auth_data
    AuthService.logout_user(db=db, user_id=user.id, token_jti=token_jti)
    response.delete_cookie(key="agro_access_token", path="/")
    return LogoutResponse(success=True, message="Logged out successfully and session revoked.")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Current User Profile",
    description="Returns the profile and role details of the currently authenticated user.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


# ==========================================
# USER ADMINISTRATION (ADMIN ONLY)
# ==========================================

from fastapi import Query
from app.database.models.user import UserRole, UserStatus
from app.schemas.auth import (
    UserStatusUpdateRequest,
    UserRoleUpdateRequest,
    PaginatedUsersResponse,
)
from app.api.deps import require_roles


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite User (Admin Only)",
    description="Creates an account with an explicit role. Public registration cannot do this.",
)
def invite_user(
    payload: UserRegisterRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = AuthService.register_user(db=db, request=payload, is_admin_invitation=True)
    return UserResponse.model_validate(user)


@router.get(
    "/users",
    response_model=PaginatedUsersResponse,
    status_code=status.HTTP_200_OK,
    summary="List Users (Admin Only)",
    description="Lists all system users with role and status filtering.",
)
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    status_filter: Optional[UserStatus] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PaginatedUsersResponse:
    users, total = AuthService.list_users(
        db=db,
        role=role,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return PaginatedUsersResponse(
        total=total,
        skip=skip,
        limit=limit,
        users=[UserResponse.model_validate(u) for u in users],
    )


@router.put(
    "/users/{user_id}/status",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Account Status (Admin Only)",
    description="Updates user account status (e.g. SUSPENDED, ACTIVE, INACTIVE).",
)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserResponse:
    updated = AuthService.update_user_status(db=db, user_id=user_id, new_status=payload.status)
    return UserResponse.model_validate(updated)


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Role (Admin Only)",
    description="Updates user permissions and RBAC role.",
)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserResponse:
    updated = AuthService.update_user_role(db=db, user_id=user_id, new_role=payload.role)
    return UserResponse.model_validate(updated)

