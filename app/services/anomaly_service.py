"""AI Anomaly Detection service."""

from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.logging import logger
from app.core.errors import AppException
from app.ai.model import detector
from app.ai.preprocessing import extract_feature_matrix
from app.database.models.environmental_measurement import EnvironmentalMeasurement


class AnomalyService:
    """Coordinates AI Anomaly Detection inference and model lifecycle."""

    @staticmethod
    def evaluate(
        temperature: float,
        humidity: float,
        soil_moisture: float,
        additional_metrics: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """Evaluate an environmental reading using the Isolation Forest model."""
        return detector.predict_anomaly(
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            additional_metrics=additional_metrics,
        )

    @staticmethod
    def train_on_historical_telemetry(db: Session, min_samples: int = 10) -> int:
        """Retrain the AI model on real historical database measurements."""
        stmt = select(
            EnvironmentalMeasurement.temperature,
            EnvironmentalMeasurement.humidity,
            EnvironmentalMeasurement.soil_moisture,
            EnvironmentalMeasurement.additional_metrics,
        )
        records = db.execute(stmt).all()

        if len(records) < min_samples:
            raise AppException(
                message=f"Insufficient historical data for retraining. Found {len(records)} records, minimum required is {min_samples}.",
                status_code=400,
                error_code="INSUFFICIENT_TRAINING_DATA",
            )

        samples = [
            {
                "temperature": r.temperature,
                "humidity": r.humidity,
                "soil_moisture": r.soil_moisture,
                "additional_metrics": r.additional_metrics,
            }
            for r in records
        ]

        X = extract_feature_matrix(samples)
        detector.fit(X)
        logger.info(f"Successfully retrained AI Anomaly Detector on {len(records)} real field records.")
        return len(records)

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Return model metadata and operational metrics."""
        return {
            "model_type": "IsolationForest",
            "is_fitted": detector.is_fitted,
            "trained_samples": detector.trained_sample_count,
            "contamination_rate": detector.contamination,
            "feature_names": [
                "temperature",
                "humidity",
                "soil_moisture",
                "vpd_kpa",
                "heat_index",
                "temp_soil_gradient",
            ],
        }
