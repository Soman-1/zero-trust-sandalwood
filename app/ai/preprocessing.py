"""Feature engineering and preprocessing pipeline for agroforestry environmental telemetry."""

import math
from typing import List, Dict, Any
import numpy as np


def compute_vapor_pressure_deficit(temperature: float, humidity: float) -> float:
    """
    Calculate atmospheric Vapor Pressure Deficit (VPD) in kilopascals (kPa).
    VPD indicates atmospheric drying demand on tree foliage and soil.
    """
    # Saturated vapor pressure (Tetens formula)
    es = 0.61078 * math.exp((17.27 * temperature) / (temperature + 237.3))
    # Actual vapor pressure
    ea = es * (max(0.0, min(100.0, humidity)) / 100.0)
    vpd = max(0.0, es - ea)
    return round(vpd, 4)


def compute_heat_index(temperature: float, humidity: float) -> float:
    """Approximate combined heat stress index."""
    # Simplified Steadman formula for agroforestry microclimates
    return round(0.5 * (temperature + 61.0 + ((temperature - 68.0) * 1.2) + (humidity * 0.094)), 2)


def extract_features(
    temperature: float,
    humidity: float,
    soil_moisture: float,
    additional_metrics: Dict[str, Any] = None,
) -> np.ndarray:
    """
    Transform raw environmental readings into a normalized feature vector:
    [temperature, humidity, soil_moisture, vpd_proxy, heat_index_proxy, temp_soil_gradient]
    """
    vpd = compute_vapor_pressure_deficit(temperature, humidity)
    hi = compute_heat_index(temperature, humidity)
    temp_soil_gradient = round(temperature - soil_moisture, 2)

    features = [
        float(temperature),
        float(humidity),
        float(soil_moisture),
        float(vpd),
        float(hi),
        float(temp_soil_gradient),
    ]
    return np.array(features, dtype=np.float64)


def extract_feature_matrix(samples: List[Dict[str, Any]]) -> np.ndarray:
    """Extract a 2D numpy feature matrix from a list of sample dictionaries."""
    matrix = [
        extract_features(
            sample["temperature"],
            sample["humidity"],
            sample["soil_moisture"],
            sample.get("additional_metrics"),
        )
        for sample in samples
    ]
    return np.array(matrix, dtype=np.float64)
