"""Central API v1 router mounting all modular domain routes."""

from fastapi import APIRouter
from app.api.routes.auth import router as auth_router
from app.api.routes.devices import router as devices_router
from app.api.routes.regions import router as regions_router
from app.api.routes.trees import router as trees_router
from app.api.routes.trees_status import router as trees_status_router
from app.api.routes.trees_fetch import router as trees_fetch_router
from app.api.routes.measurements import router as measurements_router
from app.api.routes.anomaly import router as anomaly_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.audit import router as audit_router
from app.api.routes.system import router as system_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.satellite import router as satellite_router
from app.api.routes.street_view import router as street_view_router
from app.api.routes.global_trees import router as global_trees_router
from app.api.routes.detections import router as detections_router

api_router = APIRouter()

# Authentication & User Management Routes
api_router.include_router(auth_router)

# IoT Field Device Management Routes
api_router.include_router(devices_router)

# Monitoring Region Management Routes
api_router.include_router(regions_router)

# Sandalwood Tree Registration & Spatial Routes
api_router.include_router(trees_router)
api_router.include_router(trees_fetch_router)
api_router.include_router(trees_status_router)

# Environmental Telemetry & Ingestion Routes
api_router.include_router(measurements_router)

# AI Environmental Anomaly Detection Routes
api_router.include_router(anomaly_router)

# Alert & Notification Lifecycle Routes
api_router.include_router(alerts_router)

# Audit Trail & Blockchain Integration Routes
api_router.include_router(audit_router)

# System Diagnostics & Telemetry Info Routes
api_router.include_router(system_router)

# Dashboard & GIS Analytics Routes
api_router.include_router(dashboard_router)

# Satellite AI & Real-World Internet Biodiversity Routes
api_router.include_router(satellite_router)

# Street View 360° & Ground AI Detection Routes
api_router.include_router(street_view_router)

# Global Internet Sandalwood Biodiversity Routes
api_router.include_router(global_trees_router)

# Unassigned map detections → operator Tree ID assignment
api_router.include_router(detections_router)

