"""Pydantic schemas for AI Anomaly Detection inference and model management."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AnomalyEvaluateRequest(BaseModel):
    """Payload to evaluate an environmental reading for anomalies."""
    temperature: float = Field(..., ge=-10.0, le=65.0, json_schema_extra={"example": 45.5})
    humidity: float = Field(..., ge=0.0, le=100.0, json_schema_extra={"example": 18.0})
    soil_moisture: float = Field(..., ge=0.0, le=100.0, json_schema_extra={"example": 12.0})
    additional_metrics: Optional[Dict[str, Any]] = Field(None, json_schema_extra={"example": {}})


class AnomalyEvaluateResponse(BaseModel):
    """Result of AI anomaly evaluation."""
    is_anomaly: bool
    anomaly_score: float
    details: Dict[str, Any]
    interpretation: str


class ModelRetrainResponse(BaseModel):
    """Confirmation response after retraining the AI model."""
    success: bool
    samples_trained: int
    message: str


class ModelStatusResponse(BaseModel):
    """Current AI model health and metadata."""
    model_type: str = "IsolationForest"
    is_fitted: bool
    trained_samples: int
    contamination_rate: float
    feature_names: list[str]
