"""Authentication and User Session service."""

from datetime import datetime, timezone
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func

from app.core.config import settings
from app.core.logging import logger
from app.core.security import hash_password, verify_password, create_access_token
from app.core.errors import AppException, UnauthorizedError, ForbiddenError, NotFoundError
from app.database.models.user import User, UserRole, UserStatus
from app.database.models.session import UserSession
from app.schemas.auth import UserRegisterRequest, UserLoginRequest


class AuthService:
    """Zero Trust authentication and session management service."""

    @staticmethod
    def register_user(
        db: Session,
        request: UserRegisterRequest,
        is_admin_invitation: bool = False,
    ) -> User:
        """Register a new user in the platform."""
        # Enforce unique email and username
        existing = db.execute(
            select(User).where(
                (User.email == request.email) | (User.username == request.username)
            )
        ).scalar_one_or_none()
        if existing:
            if existing.email == request.email:
                raise AppException(
                    message="A user with this email already exists",
                    status_code=400,
                    error_code="EMAIL_ALREADY_EXISTS",
                )
            raise AppException(
                message="A user with this username already exists",
                status_code=400,
                error_code="USERNAME_ALREADY_EXISTS",
            )

        from app.core.runtime import privileged_self_register

        allow_privileged = is_admin_invitation or privileged_self_register
        if not allow_privileged and request.role != UserRole.VIEWER:
            raise ForbiddenError(
                message="Public registration cannot assign a privileged role",
                details={"requested_role": request.role.value, "assigned_role": UserRole.VIEWER.value},
            )

        assigned_role = request.role if allow_privileged else UserRole.VIEWER
        hashed = hash_password(request.password)
        user = User(
            email=request.email,
            username=request.username,
            full_name=request.full_name,
            hashed_password=hashed,
            role=assigned_role,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Registered user '{user.username}' with role '{user.role}'")
        return user

    @staticmethod
    def authenticate_user(
        db: Session,
        request: UserLoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, int, User]:
        """
        Authenticate user credentials, enforce active account status,
        generate JWT, and persist active session record.
        """
        stmt = select(User).where(
            or_(
                User.username == request.username_or_email,
                User.email == request.username_or_email,
            )
        )
        user = db.execute(stmt).scalar_one_or_none()

        # Constant-time password check (protect against user enumeration)
        if not user or not verify_password(request.password, user.hashed_password):
            logger.warning(f"Failed authentication attempt for identifier: '{request.username_or_email}'")
            raise UnauthorizedError(
                message="Invalid username or password",
                details={"reason": "invalid_credentials"},
            )

        if user.status != UserStatus.ACTIVE:
            logger.warning(f"Inactive user '{user.username}' attempted login with status '{user.status}'")
            raise UnauthorizedError(
                message="Invalid username or password",
                details={"reason": "invalid_credentials"},
            )

        # Generate JWT and record session
        token, token_jti, expires_at = create_access_token(
            subject=user.id,
            role=user.role.value,
        )

        session = UserSession(
            user_id=user.id,
            token_jti=token_jti,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        db.add(session)
        db.commit()

        expires_in_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        logger.info(f"User '{user.username}' authenticated successfully. Session JTI: {token_jti}")
        return token, expires_in_seconds, user

    @staticmethod
    def logout_user(db: Session, user_id: int, token_jti: str) -> None:
        """Revoke active user session in the database."""
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.token_jti == token_jti,
        )
        session = db.execute(stmt).scalar_one_or_none()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Revoked session {token_jti} for user_id {user_id}")

    @staticmethod
    def validate_session(db: Session, user_id: int, token_jti: str) -> bool:
        """Verify that the JWT session is registered and unrevoked."""
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.token_jti == token_jti,
        )
        session = db.execute(stmt).scalar_one_or_none()
        if not session or not session.is_active:
            return False
        return True

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """Fetch user by database integer ID."""
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError(message=f"User with ID {user_id} not found")
        return user

    @staticmethod
    def list_users(
        db: Session,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[User], int]:
        """List users with optional role and status filters."""
        stmt = select(User)
        if role is not None:
            stmt = stmt.where(User.role == role)
        if status is not None:
            stmt = stmt.where(User.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        stmt = stmt.order_by(User.id.asc()).offset(skip).limit(limit)
        users = list(db.execute(stmt).scalars().all())
        return users, total

    @staticmethod
    def update_user_status(db: Session, user_id: int, new_status: UserStatus) -> User:
        """Update user account status (e.g. SUSPENDED, ACTIVE)."""
        user = AuthService.get_user_by_id(db, user_id)
        user.status = new_status
        if new_status != UserStatus.ACTIVE:
            now = datetime.now(timezone.utc)
            for session in list(user.sessions or []):
                if session.revoked_at is None:
                    session.revoked_at = now
        db.commit()
        db.refresh(user)
        logger.info(f"User {user.username} status updated to {new_status}")
        return user

    @staticmethod
    def update_user_role(db: Session, user_id: int, new_role: UserRole) -> User:
        """Update user role (e.g. OPERATOR, ADMIN)."""
        user = AuthService.get_user_by_id(db, user_id)
        user.role = new_role
        # Force re-login so JWT role claim cannot linger.
        now = datetime.now(timezone.utc)
        for session in list(user.sessions or []):
            if session.revoked_at is None:
                session.revoked_at = now
        db.commit()
        db.refresh(user)
        logger.info(f"User {user.username} role updated to {new_role}")
        return user

