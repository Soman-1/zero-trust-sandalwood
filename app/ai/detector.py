"""High-Level AI Environmental Anomaly Detector for Sandalwood Microclimates."""

from typing import Dict, Any, Tuple, Optional, List
import numpy as np

from app.core.logging import logger
from app.ai.preprocessing import extract_features, compute_vapor_pressure_deficit, compute_heat_index
from app.ai.model import EnvironmentalAnomalyDetector, anomaly_detector as default_model


class AnomalyDetector:
    """
    High-level Anomaly Detection Engine combining machine learning (Isolation Forest)
    with biological and environmental domain thresholds for sandalwood trees.
    """

    def __init__(self, base_model: Optional[EnvironmentalAnomalyDetector] = None):
        self.model = base_model or default_model

    def evaluate(
        self,
        temperature: float,
        humidity: float,
        soil_moisture: float,
        additional_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate field telemetry and return a structured anomaly assessment.
        
        Returns:
            dict containing:
                - is_anomaly (bool)
                - anomaly_score (float, 0.0 to 1.0)
                - confidence (float, 0.0 to 1.0)
                - vpd_kpa (float)
                - heat_index (float)
                - abnormal_factors (list[str])
                - severity (str: NORMAL, LOW, MEDIUM, HIGH, CRITICAL)
        """
        is_anomaly, score, details = self.model.predict_anomaly(
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            additional_metrics=additional_metrics,
        )

        vpd = compute_vapor_pressure_deficit(temperature, humidity)
        hi = compute_heat_index(temperature, humidity)

        abnormal_factors: List[str] = []
        if temperature > 42.0:
            abnormal_factors.append("EXTREME_HEAT_STRESS")
        elif temperature < 10.0:
            abnormal_factors.append("CHILL_STRESS")

        if humidity < 25.0:
            abnormal_factors.append("CRITICAL_ATMOSPHERIC_ARIDITY")
        elif humidity > 95.0:
            abnormal_factors.append("SATURATED_FUNGAL_RISK_HUMIDITY")

        if soil_moisture < 15.0:
            abnormal_factors.append("SEVERE_ROOT_ZONE_DROUGHT")
        elif soil_moisture > 85.0:
            abnormal_factors.append("ROOT_ANOXIA_WATERLOGGING")

        if vpd > 2.5:
            abnormal_factors.append("HIGH_VAPOR_PRESSURE_DEFICIT")

        # Determine severity rating
        if score >= 0.85 or len(abnormal_factors) >= 2:
            severity = "CRITICAL"
        elif score >= 0.70 or len(abnormal_factors) == 1:
            severity = "HIGH"
        elif score >= 0.50:
            severity = "MEDIUM"
        elif is_anomaly:
            severity = "LOW"
        else:
            severity = "NORMAL"

        confidence = round(min(1.0, 0.5 + abs(score - 0.5)), 3)

        return {
            "is_anomaly": is_anomaly or len(abnormal_factors) > 0,
            "anomaly_score": score,
            "confidence": confidence,
            "vpd_kpa": vpd,
            "heat_index": hi,
            "abnormal_factors": abnormal_factors,
            "severity": severity,
            "raw_features": details.get("feature_values", details.get("raw_features", {})),
        }

    def evaluate_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate a batch of telemetry observations."""
        return [
            self.evaluate(
                temperature=r["temperature"],
                humidity=r["humidity"],
                soil_moisture=r["soil_moisture"],
                additional_metrics=r.get("additional_metrics"),
            )
            for r in readings
        ]


# Singleton instance
anomaly_detector_service = AnomalyDetector()
