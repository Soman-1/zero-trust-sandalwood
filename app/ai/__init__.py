"""AI and machine learning module for environmental anomaly detection."""

from app.ai.preprocessing import (
    compute_vapor_pressure_deficit,
    compute_heat_index,
    extract_features,
    extract_feature_matrix,
)
from app.ai.model import EnvironmentalAnomalyDetector, anomaly_detector
from app.ai.detector import AnomalyDetector, anomaly_detector_service
from app.ai.satellite_classifier import SatelliteSandalwoodClassifier, satellite_classifier
from app.ai.aerial_detector import AerialDroneTreeDetector, aerial_detector

__all__ = [
    "compute_vapor_pressure_deficit",
    "compute_heat_index",
    "extract_features",
    "extract_feature_matrix",
    "EnvironmentalAnomalyDetector",
    "anomaly_detector",
    "AnomalyDetector",
    "anomaly_detector_service",
    "SatelliteSandalwoodClassifier",
    "satellite_classifier",
    "AerialDroneTreeDetector",
    "aerial_detector",
]
