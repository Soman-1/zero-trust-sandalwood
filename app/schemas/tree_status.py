from enum import Enum
from pydantic import BaseModel, Field
from app.database.models.tree import TreeStatus

class TreeStatusUpdateRequest(BaseModel):
    """Schema for updating a tree's status.

    Attributes:
        status: New status for the tree (must be a valid TreeStatus enum value).
        reason: Optional free‑text justification for the status change.
    """
    status: TreeStatus = Field(..., description="New status for the tree")
    reason: str | None = Field(None, description="Optional reason for status change")
