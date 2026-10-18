"""Environmental measurements, time-series history, analytics, and data ingestion API endpoints."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User
from app.database.models.device import Device
from app.schemas.measurement import (
    MeasurementIngestRequest,
    MeasurementBatchIngestRequest,
    MeasurementResponse,
    IngestResponse,
    BatchIngestResponse,
    MeasurementStatsResponse,
    PaginatedMeasurementsResponse,
    IntegrityCheckResponse,
    IntegrityScanResponse,
)
from app.services.measurement_service import MeasurementService
from app.api.deps import get_current_user, get_current_device

router = APIRouter(prefix="/measurements", tags=["Environmental Measurements"])


# ==========================================
# 1. FIELD DEVICE INGESTION ENDPOINTS
# ==========================================

@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Field Environmental Telemetry",
    description=(
        "Zero Trust field data ingestion endpoint. Authenticates IoT hardware (X-Device-ID / X-Device-Key), "
        "validates physical sensor ranges, enforces region boundary rules, and persists environmental readings."
    ),
)
def ingest_measurement(
    payload: MeasurementIngestRequest,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> IngestResponse:
    measurement = MeasurementService.ingest_single_measurement(
        db=db,
        request=payload,
        device=current_device,
    )
    return IngestResponse(
        success=True,
        measurement_uid=measurement.measurement_uid,
        region_id=measurement.region_id,
        tree_id=measurement.tree_id,
        device_id=current_device.id,
        recorded_at=measurement.recorded_at,
        message="Environmental measurement successfully validated and ingested.",
    )


@router.post(
    "/ingest/batch",
    response_model=BatchIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch Ingest Field Telemetry",
    description="Allows IoT gateways, drones, or offline field devices to synchronize a batch of environmental observations.",
)
def ingest_batch_measurements(
    payload: MeasurementBatchIngestRequest,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> BatchIngestResponse:
    ingested = MeasurementService.ingest_batch_measurements(
        db=db,
        request=payload,
        device=current_device,
    )
    return BatchIngestResponse(
        success=True,
        total_received=len(payload.measurements),
        total_ingested=len(ingested),
        measurement_uids=[m.measurement_uid for m in ingested],
        message="Batch telemetry successfully validated and ingested.",
    )


# ==========================================
# 2. TELEMETRY RETRIEVAL & HISTORY ENDPOINTS
# ==========================================

@router.get(
    "",
    response_model=PaginatedMeasurementsResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Environmental Measurements",
    description="Lists time-series measurements with filters for region, tree, time window, and anomaly status.",
)
def list_measurements(
    region_id: Optional[str] = Query(None, description="Filter by region identifier"),
    tree_id: Optional[str] = Query(None, description="Filter by sandalwood tree UID (e.g. SW-KA-00001)"),
    start_time: Optional[datetime] = Query(None, description="Earliest recorded timestamp"),
    end_time: Optional[datetime] = Query(None, description="Latest recorded timestamp"),
    is_anomaly: Optional[bool] = Query(None, description="Filter by anomaly status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedMeasurementsResponse:
    items, total = MeasurementService.list_measurements(
        db=db,
        region_identifier=region_id,
        tree_identifier=tree_id,
        start_time=start_time,
        end_time=end_time,
        is_anomaly=is_anomaly,
        skip=skip,
        limit=limit,
    )
    return PaginatedMeasurementsResponse(
        total=total,
        skip=skip,
        limit=limit,
        measurements=[MeasurementResponse.model_validate(m) for m in items],
    )


@router.get(
    "/analytics/stats",
    response_model=MeasurementStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Environmental Analytics & Statistics",
    description="Calculates min, max, average statistics for temperature, humidity, and soil moisture over a time range.",
)
def get_analytics_stats(
    region_id: Optional[str] = Query(None, description="Region identifier"),
    tree_id: Optional[str] = Query(None, description="Sandalwood tree UID"),
    start_time: Optional[datetime] = Query(None, description="Start of time window"),
    end_time: Optional[datetime] = Query(None, description="End of time window"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeasurementStatsResponse:
    return MeasurementService.get_measurement_statistics(
        db=db,
        region_identifier=region_id,
        tree_identifier=tree_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get(
    "/region/{region_id}/latest",
    response_model=MeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Latest Environmental Telemetry for Region",
    description="Retrieves the most recent environmental reading recorded anywhere in the designated region.",
)
def get_latest_region_reading(
    region_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeasurementResponse:
    measurement = MeasurementService.get_latest_region_measurement(db=db, region_identifier=region_id)
    return MeasurementResponse.model_validate(measurement)


@router.get(
    "/region/{region_id}/history",
    response_model=List[MeasurementResponse],
    status_code=status.HTTP_200_OK,
    summary="Region Environmental History",
    description="Retrieves chronological environmental observations across the specified region.",
)
def get_region_history(
    region_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MeasurementResponse]:
    items, _ = MeasurementService.list_measurements(
        db=db,
        region_identifier=region_id,
        skip=skip,
        limit=limit,
    )
    return [MeasurementResponse.model_validate(m) for m in items]


@router.get(
    "/tree/{tree_uid}/latest",
    response_model=MeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Latest Microclimate Telemetry for Tree",
    description="Retrieves the most recent microclimate reading recorded directly around a registered sandalwood tree.",
)
def get_latest_tree_reading(
    tree_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeasurementResponse:
    measurement = MeasurementService.get_latest_tree_measurement(db=db, tree_identifier=tree_uid)
    return MeasurementResponse.model_validate(measurement)


@router.get(
    "/tree/{tree_uid}/history",
    response_model=List[MeasurementResponse],
    status_code=status.HTTP_200_OK,
    summary="Tree Microclimate History",
    description="Retrieves chronological observation history for a specific registered sandalwood tree.",
)
def get_tree_history(
    tree_uid: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MeasurementResponse]:
    items, _ = MeasurementService.list_measurements(
        db=db,
        tree_identifier=tree_uid,
        skip=skip,
        limit=limit,
    )
    return [MeasurementResponse.model_validate(m) for m in items]


@router.get(
    "/{measurement_uid}",
    response_model=MeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Measurement Details",
    description="Retrieves a specific environmental observation by its UID.",
)
def get_measurement(
    measurement_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeasurementResponse:
    measurement = MeasurementService.get_measurement_by_uid(db=db, measurement_uid=measurement_uid)
    return MeasurementResponse.model_validate(measurement)


# ==========================================
# 3. CRYPTOGRAPHIC INTEGRITY VERIFICATION
# ==========================================

@router.post(
    "/{measurement_uid}/verify-integrity",
    response_model=IntegrityCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Measurement Cryptographic Integrity",
    description=(
        "Zero Trust integrity check: dynamically recalculates the SHA-256 seal from stored observation data "
        "and detects if any fields were modified or corrupted directly in the database."
    ),
)
def verify_measurement_integrity_endpoint(
    measurement_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrityCheckResponse:
    return MeasurementService.verify_measurement_integrity_by_uid(db=db, measurement_uid=measurement_uid)


@router.post(
    "/integrity/audit-scan",
    response_model=IntegrityScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk Integrity Audit Scan",
    description="Scans stored measurements across a region to detect any data tampering or database corruption.",
)
def audit_scan_integrity_endpoint(
    region_id: Optional[str] = Query(None, description="Optional region code to filter scan"),
    limit: int = Query(500, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrityScanResponse:
    return MeasurementService.audit_scan_measurements_integrity(
        db=db,
        region_identifier=region_id,
        limit=limit,
    )
