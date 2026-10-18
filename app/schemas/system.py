"""Pydantic schemas for unified System Information and Health Diagnostics."""

from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    """Aggregated system operational and database telemetry diagnostics."""
    app_name: str
    version: str
    environment: str
    database_status: str = "CONNECTED"
    ai_model_type: str = "IsolationForest"
    ai_model_fitted: bool
    ai_trained_samples: int
    total_regions: int
    active_regions: int
    total_trees: int
    active_trees: int
    total_devices: int
    active_devices: int
    total_measurements: int
    active_alerts: int
    total_audit_logs: int
