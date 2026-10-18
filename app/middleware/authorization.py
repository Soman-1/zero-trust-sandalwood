"""Authorization and Role-Based Access Control (RBAC) helpers."""

from typing import List, Callable, Optional
from app.core.errors import ForbiddenError, UnauthorizedError
from app.database.models.user import User, UserRole


class RoleChecker:
    """Enforces required user roles for executing operations."""

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Optional[User]) -> User:
        if not user:
            raise UnauthorizedError("Authentication required for this resource")
        if user.role not in self.allowed_roles:
            raise ForbiddenError(
                message="You do not have sufficient permissions to perform this action",
                details={
                    "user_role": user.role.value if hasattr(user.role, "value") else str(user.role),
                    "allowed_roles": [r.value if hasattr(r, "value") else str(r) for r in self.allowed_roles],
                },
            )
        return user


def require_admin(user: Optional[User]) -> User:
    """Convenience helper for admin-only operations."""
    return RoleChecker([UserRole.ADMIN])(user)


def require_operator_or_admin(user: Optional[User]) -> User:
    """Convenience helper for operator and admin operations."""
    return RoleChecker([UserRole.ADMIN, UserRole.OPERATOR])(user)
