"""Pydantic schemas for authentication and user management."""

import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.database.models.user import UserRole, UserStatus

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""
    email: str = Field(..., min_length=5, max_length=255, json_schema_extra={"example": "operator@agroforestry.gov.in"})
    username: str = Field(..., min_length=3, max_length=50, json_schema_extra={"example": "operator_ka"})
    full_name: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "Ravi Kumar"})
    password: str = Field(..., min_length=8, max_length=128, json_schema_extra={"example": "SecurePassword123!"})
    role: UserRole = Field(default=UserRole.VIEWER, json_schema_extra={"example": "OPERATOR"})

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format")
        return clean


class UserLoginRequest(BaseModel):
    """Payload for user login."""
    username_or_email: str = Field(..., json_schema_extra={"example": "operator_ka"})
    password: str = Field(..., min_length=1, json_schema_extra={"example": "SecurePassword123!"})


class UserResponse(BaseModel):
    """Serialized user representation."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT Token and session response payload."""
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse


class LogoutResponse(BaseModel):
    """Logout confirmation response."""
    success: bool = True
    message: str = "Logged out successfully and session revoked."


class UserStatusUpdateRequest(BaseModel):
    """Payload to update user account status (e.g. SUSPENDED, ACTIVE, INACTIVE)."""
    status: UserStatus = Field(..., json_schema_extra={"example": "ACTIVE"})


class UserRoleUpdateRequest(BaseModel):
    """Payload to update user role (ADMIN, OPERATOR, VIEWER)."""
    role: UserRole = Field(..., json_schema_extra={"example": "OPERATOR"})


class PaginatedUsersResponse(BaseModel):
    """Paginated list of system users."""
    total: int
    skip: int
    limit: int
    users: list[UserResponse]

