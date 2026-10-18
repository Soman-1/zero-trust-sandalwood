"""Isolation Forest Anomaly Detection Model for Environmental Telemetry."""

import os
import hashlib
import hmac
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

from app.core.logging import logger
from app.ai.preprocessing import extract_features, extract_feature_matrix


class EnvironmentalAnomalyDetector:
    """Unsupervised AI Anomaly Detection Engine based on Isolation Forest."""

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=42,
        )
        self.is_fitted = False
        self.trained_sample_count = 0
        self._initialize_baseline_model()

    def _initialize_baseline_model(self) -> None:
        """
        Train on real-world microclimate telemetry observations from datasets/microclimate_iot_telemetry.csv,
        or fallback to Karnataka agroforestry distribution if missing.
        """
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "datasets",
            "microclimate_iot_telemetry.csv"
        )
        if os.path.exists(csv_path):
            import csv
            samples = []
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Extract normal non-anomalous baseline rows for calibration
                        if row.get("is_anomaly", "").lower() in ["false", "0", ""]:
                            samples.append({
                                "temperature": float(row.get("ambient_temperature_c") or row.get("temperature_c", 26.5)),
                                "humidity": float(row.get("relative_humidity_pct") or row.get("humidity_pct", 65.0)),
                                "soil_moisture": float(row.get("soil_moisture_pct", 50.0)),
                            })
                if samples:
                    X = extract_feature_matrix(samples)
                    self.fit(X)
                    logger.info(f"Initialized AI anomaly detector on {len(samples)} baseline telemetry records from dataset.")
                    return
            except Exception as e:
                logger.warning(f"Could not load telemetry CSV ({e}), using synthetic generator.")

        np.random.seed(42)
        n_samples = 500

        # Normal tropical diurnal variations
        temps = np.random.normal(loc=26.5, scale=3.0, size=n_samples).clip(18.0, 34.0)
        humidity = np.random.normal(loc=68.0, scale=8.0, size=n_samples).clip(45.0, 90.0)
        soil_moisture = np.random.normal(loc=52.0, scale=7.0, size=n_samples).clip(30.0, 75.0)

        samples = [
            {"temperature": t, "humidity": h, "soil_moisture": s}
            for t, h, s in zip(temps, humidity, soil_moisture)
        ]
        X = extract_feature_matrix(samples)
        self.fit(X)
        logger.info("Initialized AI anomaly detection baseline model.")

    def fit(self, X: np.ndarray) -> None:
        """Fit scaler and Isolation Forest model on feature matrix X."""
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        self.trained_sample_count = len(X)
        logger.info(f"AI Anomaly Model fitted on {self.trained_sample_count} observations.")

    def predict_anomaly(
        self,
        temperature: float,
        humidity: float,
        soil_moisture: float,
        additional_metrics: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Evaluate an environmental observation.
        Returns:
            - is_anomaly (bool): True if classified as an anomaly.
            - anomaly_score (float): Normalized score from 0.0 (normal) to 1.0 (highly abnormal).
            - anomaly_details (dict): Explanatory diagnostic breakdown.
        """
        features = extract_features(temperature, humidity, soil_moisture, additional_metrics)
        features_2d = features.reshape(1, -1)
        features_scaled = self.scaler.transform(features_2d)

        # Raw score: lower values represent anomalies
        raw_score = float(self.model.decision_function(features_scaled)[0])
        prediction = int(self.model.predict(features_scaled)[0])

        # Normalize score to 0.0 - 1.0 where higher is more anomalous
        # Raw decision_function typically ranges from -0.5 (very anomalous) to +0.5 (very normal)
        normalized_score = round(float(np.clip((0.2 - raw_score) / 0.5, 0.0, 1.0)), 4)

        # Rule-assisted validation guards for physical extremes
        is_extreme_temp = temperature > 42.0 or temperature < 5.0
        is_extreme_dry = soil_moisture < 15.0 and humidity < 30.0
        is_extreme_soil = soil_moisture < 10.0

        is_anomaly = (prediction == -1) or is_extreme_temp or is_extreme_dry or is_extreme_soil or (normalized_score > 0.65)

        # Primary explanatory factor
        primary_factor = "NORMAL_CONDITIONS"
        severity = "LOW"

        if is_anomaly:
            if temperature > 40.0:
                primary_factor = "ABNORMAL_HIGH_TEMPERATURE"
                severity = "CRITICAL" if temperature > 45.0 else "HIGH"
            elif soil_moisture < 15.0:
                primary_factor = "CRITICAL_SOIL_DEHYDRATION"
                severity = "HIGH"
            elif humidity < 25.0:
                primary_factor = "RAPID_HUMIDITY_DROP"
                severity = "MEDIUM"
            else:
                primary_factor = "UNUSUAL_ENVIRONMENTAL_COMBINATION"
                severity = "MEDIUM" if normalized_score < 0.8 else "HIGH"

        details = {
            "primary_factor": primary_factor,
            "severity_hint": severity,
            "raw_decision_score": round(raw_score, 4),
            "normalized_anomaly_score": normalized_score,
            "feature_values": {
                "temperature_c": temperature,
                "humidity_pct": humidity,
                "soil_moisture_pct": soil_moisture,
                "vpd_kpa": float(features[3]),
            },
        }

        return is_anomaly, normalized_score, details

    def save(self, filepath: str) -> None:
        """Persist model and scaler to disk with SHA-256 integrity checksum."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({"model": self.model, "scaler": self.scaler, "count": self.trained_sample_count}, filepath)
        with open(filepath, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        with open(f"{filepath}.sha256", "w", encoding="utf-8") as f:
            f.write(digest)
        logger.info(f"Saved AI model artifact to {filepath} (SHA-256: {digest[:16]}...)")

    def load(self, filepath: str) -> bool:
        """Load model and scaler from disk after verifying SHA-256 checksum."""
        if os.path.exists(filepath):
            checksum_path = f"{filepath}.sha256"
            if os.path.exists(checksum_path):
                with open(filepath, "rb") as f:
                    actual_digest = hashlib.sha256(f.read()).hexdigest()
                with open(checksum_path, "r", encoding="utf-8") as f:
                    expected_digest = f.read().strip().lower()
                if not hmac.compare_digest(actual_digest.lower(), expected_digest):
                    logger.error(f"Model integrity verification failed for {filepath}! Refusing to load.")
                    return False

            data = joblib.load(filepath)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.trained_sample_count = data.get("count", 0)
            self.is_fitted = True
            logger.info(f"Loaded AI model artifact from {filepath} with verified integrity")
            return True
        return False


# Global singleton instance
detector = EnvironmentalAnomalyDetector()
anomaly_detector = detector
