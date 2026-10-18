"""Pydantic schemas for Environmental telemetry ingestion and querying."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
import json
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MeasurementIngestRequest(BaseModel):
    """Payload sent by IoT field sensors or handheld devices to ingest environmental data."""
    # 1. Region-level target (Mandatory)
    region_id: Optional[Union[str, int]] = Field(
        None,
        description="Optional. A forest reserve is not required.",
    )

    # 2. Tree-level target (Optional)
    tree_id: Optional[Union[str, int]] = Field(
        None,
        description="Optional registered sandalwood Tree ID (e.g. 'SW-KA-00001') if taken directly at tree",
        json_schema_extra={"example": "SW-KA-00001"},
    )

    # GPS Coordinates
    latitude: float = Field(..., ge=-90.0, le=90.0, json_schema_extra={"example": 13.9310})
    longitude: float = Field(..., ge=-180.0, le=180.0, json_schema_extra={"example": 75.5720})
    altitude: Optional[float] = Field(None, json_schema_extra={"example": 640.0})

    # Physical Sensor Readings
    temperature: float = Field(
        ...,
        ge=-10.0,
        le=65.0,
        description="Ambient air temperature in Celsius",
        json_schema_extra={"example": 28.5},
    )
    humidity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Relative air humidity percentage",
        json_schema_extra={"example": 68.4},
    )
    soil_moisture: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Volumetric soil moisture percentage",
        json_schema_extra={"example": 46.2},
    )

    # Extensible metrics for future sensors (rainfall, smoke, air quality, light, soil pH)
    additional_metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional extra sensor metrics. At most 20 keys and 2 KB serialized.",
        json_schema_extra={"example": {"rainfall_mm": 0.0, "soil_ph": 6.8, "solar_lux": 75000}},
    )

    @field_validator("additional_metrics")
    @classmethod
    def limit_additional_metrics(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if value is None:
            return value
        if len(value) > 20:
            raise ValueError("additional_metrics accepts at most 20 keys")
        encoded = json.dumps(value, default=str)
        if len(encoded) > 2048:
            raise ValueError("additional_metrics exceeds 2 KB")
        return value

    recorded_at: Optional[datetime] = Field(
        None,
        description="UTC timestamp when measurement was recorded on device. Defaults to ingestion time if omitted.",
    )


class MeasurementBatchIngestRequest(BaseModel):
    """Payload for batch telemetry synchronization from field gateways or offline sync."""
    measurements: List[MeasurementIngestRequest] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Array of environmental measurement records",
    )


class MeasurementResponse(BaseModel):
    """Public representation of an environmental observation."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    measurement_uid: str
    region_id: Optional[int] = None
    tree_id: Optional[int]
    device_id: Optional[int]
    latitude: float
    longitude: float
    altitude: Optional[float]
    temperature: float
    humidity: float
    soil_moisture: float
    additional_metrics: Optional[Dict[str, Any]]
    integrity_hash: Optional[str]
    is_tampered: bool
    is_anomaly: bool
    anomaly_score: Optional[float]
    recorded_at: datetime
    created_at: datetime


class IngestResponse(BaseModel):
    """Confirmation response after successful telemetry ingestion."""
    success: bool = True
    measurement_uid: str
    region_id: Optional[int] = None
    tree_id: Optional[int]
    device_id: int
    recorded_at: datetime
    message: str = "Environmental measurement successfully validated and ingested."


class BatchIngestResponse(BaseModel):
    """Confirmation response after successful batch telemetry synchronization."""
    success: bool = True
    total_received: int
    total_ingested: int
    measurement_uids: List[str]
    message: str = "Batch telemetry successfully validated and ingested."


class MeasurementStatsResponse(BaseModel):
    """Statistical aggregations over a time window for a region or tree."""
    region_id: Optional[str] = None
    tree_uid: Optional[str] = None
    reading_count: int
    avg_temperature: Optional[float] = None
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    avg_humidity: Optional[float] = None
    min_humidity: Optional[float] = None
    max_humidity: Optional[float] = None
    avg_soil_moisture: Optional[float] = None
    min_soil_moisture: Optional[float] = None
    max_soil_moisture: Optional[float] = None
    earliest_reading: Optional[datetime] = None
    latest_reading: Optional[datetime] = None


class PaginatedMeasurementsResponse(BaseModel):
    """Paginated list of environmental observations."""
    total: int
    skip: int
    limit: int
    measurements: List[MeasurementResponse]


class IntegrityCheckResponse(BaseModel):
    """Result of single measurement cryptographic integrity verification."""
    measurement_uid: str
    is_valid: bool
    status: str
    stored_hash: Optional[str] = None
    computed_hash: str
    message: str


class IntegrityScanResponse(BaseModel):
    """Result of bulk database integrity audit scan."""
    total_scanned: int
    valid_count: int
    tampered_count: int
    tampered_uids: List[str]
    message: str


