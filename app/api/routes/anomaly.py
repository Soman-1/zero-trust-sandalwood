"""AI Environmental Anomaly Detection API endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.schemas.anomaly import (
    AnomalyEvaluateRequest,
    AnomalyEvaluateResponse,
    ModelRetrainResponse,
    ModelStatusResponse,
)
from app.services.anomaly_service import AnomalyService
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/anomaly", tags=["AI Anomaly Detection"])


@router.post(
    "/evaluate",
    response_model=AnomalyEvaluateResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Environmental Reading for Anomaly",
    description="Runs the Isolation Forest AI model against given environmental parameters to determine anomaly classification and score.",
)
def evaluate_reading(
    payload: AnomalyEvaluateRequest,
    current_user: User = Depends(get_current_user),
) -> AnomalyEvaluateResponse:
    is_anomaly, score, details = AnomalyService.evaluate(
        temperature=payload.temperature,
        humidity=payload.humidity,
        soil_moisture=payload.soil_moisture,
        additional_metrics=payload.additional_metrics,
    )
    interpretation = (
        f"ANOMALY DETECTED: {details.get('primary_factor')} (Score: {score})"
        if is_anomaly
        else f"NORMAL CONDITIONS: Microclimate within expected baseline (Score: {score})"
    )
    return AnomalyEvaluateResponse(
        is_anomaly=is_anomaly,
        anomaly_score=score,
        details=details,
        interpretation=interpretation,
    )


@router.post(
    "/train",
    response_model=ModelRetrainResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrain AI Anomaly Detection Model",
    description="Retrains the Isolation Forest model on historical database observations across the agroforestry plot.",
)
def retrain_model(
    min_samples: int = Query(10, ge=5, le=10000),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ModelRetrainResponse:
    count = AnomalyService.train_on_historical_telemetry(db=db, min_samples=min_samples)
    return ModelRetrainResponse(
        success=True,
        samples_trained=count,
        message=f"Isolation Forest model successfully retrained on {count} real observations.",
    )


@router.get(
    "/model-status",
    response_model=ModelStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Model Status",
    description="Retrieves current AI anomaly detection engine metadata, sample count, and contamination rate.",
)
def get_model_status(
    current_user: User = Depends(get_current_user),
) -> ModelStatusResponse:
    status_data = AnomalyService.get_status()
    return ModelStatusResponse(
        model_type=status_data["model_type"],
        is_fitted=status_data["is_fitted"],
        trained_samples=status_data["trained_samples"],
        contamination_rate=status_data["contamination_rate"],
        feature_names=status_data["feature_names"],
    )
