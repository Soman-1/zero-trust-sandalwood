"""Core database models registry."""

from app.database.models.user import User, UserRole, UserStatus
from app.database.models.session import UserSession
from app.database.models.device import Device, DeviceStatus
from app.database.models.region import Region, RegionStatus
from app.database.models.tree import Tree, TreeStatus
from app.database.models.environmental_measurement import EnvironmentalMeasurement
from app.database.models.alert import Alert, AlertSeverity, AlertStatus
from app.database.models.audit_log import AuditLog
from app.database.models.tree_detection import TreeDetection, DetectionStatus

__all__ = [
    "User",
    "UserRole",
    "UserStatus",
    "UserSession",
    "Device",
    "DeviceStatus",
    "Region",
    "RegionStatus",
    "Tree",
    "TreeStatus",
    "TreeDetection",
    "DetectionStatus",
    "EnvironmentalMeasurement",
    "Alert",
    "AlertSeverity",
    "AlertStatus",
    "AuditLog",
]
