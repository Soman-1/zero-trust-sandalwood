"""Unit tests for the high-level AnomalyDetector in app/ai/detector.py."""

import pytest
from app.ai.detector import AnomalyDetector, anomaly_detector_service


def test_anomaly_detector_normal_evaluation():
    """Test evaluating normal environmental parameters."""
    result = anomaly_detector_service.evaluate(
        temperature=27.0,
        humidity=65.0,
        soil_moisture=50.0,
    )
    assert isinstance(result, dict)
    assert "is_anomaly" in result
    assert "anomaly_score" in result
    assert "severity" in result
    assert "vpd_kpa" in result
    assert result["vpd_kpa"] > 0.0


def test_anomaly_detector_extreme_heat_and_drought():
    """Test that extreme drought and heat conditions trigger abnormal factors."""
    result = anomaly_detector_service.evaluate(
        temperature=48.5,
        humidity=15.0,
        soil_moisture=8.0,
    )
    assert result["is_anomaly"] is True
    assert result["severity"] in ["HIGH", "CRITICAL"]
    assert "EXTREME_HEAT_STRESS" in result["abnormal_factors"]
    assert "SEVERE_ROOT_ZONE_DROUGHT" in result["abnormal_factors"]


def test_anomaly_detector_batch_evaluation():
    """Test batch telemetry evaluation."""
    readings = [
        {"temperature": 25.0, "humidity": 70.0, "soil_moisture": 55.0},
        {"temperature": 49.0, "humidity": 12.0, "soil_moisture": 6.0},
    ]
    results = anomaly_detector_service.evaluate_batch(readings)
    assert len(results) == 2
    assert results[0]["severity"] in ["NORMAL", "LOW"]
    assert results[1]["severity"] in ["HIGH", "CRITICAL"]
