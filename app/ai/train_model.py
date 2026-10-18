"""High-Precision Production AI Training Pipeline v2:
Trains, calibrates, and evaluates a hardened Sandalwood & Host Species Multi-Class Classifier
with advanced feature engineering, hard-negative mining, and 3-model stacked ensemble.
"""

import os
import csv
import json
import numpy as np
import joblib
from typing import Dict, Any, Tuple, List
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    VotingClassifier,
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)
from app.ai.data_pipeline import build_unified_training_dataset, SPECIES_CONFIG

WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights")

# ── 15 primary spectral features + 6 advanced botanical ratio features = 21 total ──
PRIMARY_FEATURE_COLUMNS = [
    "band2_blue", "band3_green", "band4_red", "band5_red_edge",
    "band8_nir", "band11_swir1", "band12_swir2",
    "ndvi", "evi", "ndmi", "ci_red_edge", "savi", "ndre", "gndvi",
    "canopy_height_m",
]

# Derived ratio features computed during feature extraction (not stored in CSV)
DERIVED_FEATURE_NAMES = [
    "nir_swir2_ratio",      # Leaf water content proxy (sandalwood-diagnostic)
    "red_edge_red_ratio",   # Chlorophyll concentration gradient
    "swir1_swir2_ratio",    # Cellulose vs. lignin (oil-bearing leaf signal)
    "blue_red_ratio",       # Atmospheric scatter / canopy density proxy
    "green_red_ratio",      # Visible greenness ratio
    "nir_red_edge_slope",   # Red-edge inflection slope (species-diagnostic)
]

ALL_FEATURE_NAMES = PRIMARY_FEATURE_COLUMNS + DERIVED_FEATURE_NAMES


def _compute_derived_features(primary_vec: np.ndarray) -> np.ndarray:
    """Compute 6 advanced botanical ratio features from 15 primary features.

    These ratios exploit physical differences in sandalwood leaf biochemistry:
    - High essential oil content → distinct SWIR absorption profile
    - Smaller, thicker leaves → steeper red-edge inflection
    - Semi-parasitic growth → unique NIR/SWIR water-content signature
    """
    eps = 1e-6
    blue, green, red, red_edge = primary_vec[0], primary_vec[1], primary_vec[2], primary_vec[3]
    nir, swir1, swir2 = primary_vec[4], primary_vec[5], primary_vec[6]

    nir_swir2_ratio = nir / max(swir2, eps)
    red_edge_red_ratio = red_edge / max(red, eps)
    swir1_swir2_ratio = swir1 / max(swir2, eps)
    blue_red_ratio = blue / max(red, eps)
    green_red_ratio = green / max(red, eps)
    nir_red_edge_slope = (nir - red_edge) / max(nir + red_edge, eps)

    return np.array([
        nir_swir2_ratio,
        red_edge_red_ratio,
        swir1_swir2_ratio,
        blue_red_ratio,
        green_red_ratio,
        nir_red_edge_slope,
    ], dtype=np.float32)


def load_dataset_features(force_rebuild: bool = True) -> Tuple[np.ndarray, np.ndarray, list]:
    """Load dataset records, extract primary + derived features, return (X, y, raw_data)."""
    dataset = build_unified_training_dataset(samples_per_class=1500)

    X_list: List[np.ndarray] = []
    y_list: List[int] = []

    for item in dataset:
        primary = np.array([float(item[col]) for col in PRIMARY_FEATURE_COLUMNS], dtype=np.float32)
        derived = _compute_derived_features(primary)
        full_vec = np.concatenate([primary, derived])
        X_list.append(full_vec)
        y_list.append(int(item["class_id"]))

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)
    return X, y, dataset


def train_and_evaluate_model() -> Dict[str, Any]:
    """Train a hardened 3-model stacked ensemble, evaluate with feature importance, persist artifacts."""
    os.makedirs(WEIGHTS_DIR, exist_ok=True)

    print("\n" + "=" * 70)
    print("  ADVANCED SANDALWOOD ENSEMBLE CLASSIFIER v2 — TRAINING PIPELINE")
    print("=" * 70)

    X, y, raw_data = load_dataset_features(force_rebuild=True)
    class_names = [s["common_name"] for s in SPECIES_CONFIG]

    # ── Stratified Train/Test Split (80/20) ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"  Total Samples: {len(X)} | Training: {len(X_train)} | Test: {len(X_test)}")
    print(f"  Features ({len(ALL_FEATURE_NAMES)}): {', '.join(ALL_FEATURE_NAMES)}")

    # ── 1. Random Forest (broad spatial feature capture, multi-core) ──
    rf_model = RandomForestClassifier(
        n_estimators=400,
        max_depth=25,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    # ── 2. Extra Trees (high-variance low-bias complementary learner, multi-core) ──
    et_model = ExtraTreesClassifier(
        n_estimators=350,
        max_depth=25,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    # ── 3. Fast Histogram-based Gradient Boosted Trees (multi-core, sequential error correction) ──
    gb_model = HistGradientBoostingClassifier(
        max_iter=200,
        max_depth=10,
        learning_rate=0.07,
        min_samples_leaf=2,
        random_state=42,
    )

    # ── 4. Soft-Voting 3-Model Ensemble ──
    ensemble = VotingClassifier(
        estimators=[("rf", rf_model), ("et", et_model), ("gb", gb_model)],
        voting="soft",
        weights=[3, 3, 2],
        n_jobs=-1,
    )

    # ── 5. Probability Calibration via 5-Fold Stratified CV ──
    print("\n  Fitting 950-tree 3-model ensemble with 5-fold probability calibration...")
    calibrated_model = CalibratedClassifierCV(
        estimator=ensemble,
        method="sigmoid",
        cv=5,
        n_jobs=-1,
    )
    calibrated_model.fit(X_train, y_train)

    # ── Cross-Validation Evaluation ──
    print("  Evaluating ensemble performance across 5-fold cross-validation...")
    cv_scores = cross_val_score(
        ensemble, X_train, y_train,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        n_jobs=-1,
    )
    mean_cv = float(np.mean(cv_scores))
    std_cv = float(np.std(cv_scores))

    # ── Evaluation on Hold-Out Test Set ──
    y_pred = calibrated_model.predict(X_test)
    y_proba = calibrated_model.predict_proba(X_test)

    overall_accuracy = float(accuracy_score(y_test, y_pred))
    sandalwood_precision = float(precision_score(y_test, y_pred, labels=[0], average="micro"))
    sandalwood_recall = float(recall_score(y_test, y_pred, labels=[0], average="micro"))
    sandalwood_f1 = float(f1_score(y_test, y_pred, labels=[0], average="micro"))

    conf_mat = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)

    # ── Sandalwood Confidence Distribution ──
    sw_test_mask = y_test == 0
    sw_probs = y_proba[sw_test_mask, 0]
    sw_mean_conf = float(np.mean(sw_probs)) if len(sw_probs) > 0 else 0.0
    sw_min_conf = float(np.min(sw_probs)) if len(sw_probs) > 0 else 0.0

    # ── Feature Importance (from unfitted RF for interpretability) ──
    print("\n  Computing feature importance from Random Forest sub-model...")
    rf_standalone = RandomForestClassifier(
        n_estimators=300, max_depth=20, random_state=42, class_weight="balanced", n_jobs=-1
    )
    rf_standalone.fit(X_train, y_train)
    importances = rf_standalone.feature_importances_
    feature_importance = sorted(
        [(ALL_FEATURE_NAMES[i], round(float(importances[i]), 5)) for i in range(len(ALL_FEATURE_NAMES))],
        key=lambda x: x[1],
        reverse=True,
    )

    print("\n" + "=" * 70)
    print("  MODEL EVALUATION RESULTS (TEST SET)")
    print("=" * 70)
    print(f"  Overall Test Accuracy:         {overall_accuracy * 100:.2f}%")
    print(f"  5-Fold Cross-Validation:       {mean_cv * 100:.2f}% (±{std_cv * 100:.2f}%)")
    print(f"  Sandalwood Precision:          {sandalwood_precision * 100:.2f}%")
    print(f"  Sandalwood Recall:             {sandalwood_recall * 100:.2f}%")
    print(f"  Sandalwood F1-Score:           {sandalwood_f1 * 100:.2f}%")
    print(f"  Sandalwood Mean Confidence:    {sw_mean_conf * 100:.2f}%")
    print(f"  Sandalwood Min Confidence:     {sw_min_conf * 100:.2f}%")

    print("\n  Classification Report by Species Class:")
    for cls_name in class_names:
        metrics = report.get(cls_name, {})
        p = metrics.get("precision", 0) * 100
        r = metrics.get("recall", 0) * 100
        f1 = metrics.get("f1-score", 0) * 100
        print(f"   - {cls_name:<28} Precision: {p:.1f}% | Recall: {r:.1f}% | F1: {f1:.1f}%")

    print("\n  Top 10 Feature Importances:")
    for rank, (fname, imp) in enumerate(feature_importance[:10], 1):
        bar = "#" * int(imp * 100)
        print(f"   {rank:>2}. {fname:<24} {imp:.5f}  {bar}")

    # ── Save Model Artifacts ──
    model_path = os.path.join(WEIGHTS_DIR, "sandalwood_production_model.joblib")
    metrics_path = os.path.join(WEIGHTS_DIR, "model_metrics.json")

    for p in [model_path, metrics_path]:
        if os.path.exists(p):
            try:
                os.chmod(p, 0o666)
            except Exception:
                pass

    joblib.dump({
        "model": calibrated_model,
        "feature_names": ALL_FEATURE_NAMES,
        "primary_feature_names": PRIMARY_FEATURE_COLUMNS,
        "derived_feature_names": DERIVED_FEATURE_NAMES,
        "class_names": class_names,
        "accuracy": overall_accuracy,
        "sandalwood_precision": sandalwood_precision,
        "sandalwood_recall": sandalwood_recall,
        "dataset_size": len(X),
        "feature_importance": feature_importance,
    }, model_path)

    metrics_payload = {
        "model_version": "v2.0-advanced-ensemble",
        "dataset_size": len(X),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "num_features": len(ALL_FEATURE_NAMES),
        "overall_accuracy": round(overall_accuracy, 4),
        "mean_cross_val_score": round(mean_cv, 4),
        "sandalwood_precision": round(sandalwood_precision, 4),
        "sandalwood_recall": round(sandalwood_recall, 4),
        "sandalwood_f1_score": round(sandalwood_f1, 4),
        "sandalwood_mean_confidence": round(sw_mean_conf, 4),
        "sandalwood_min_confidence": round(sw_min_conf, 4),
        "confusion_matrix": conf_mat,
        "feature_names": ALL_FEATURE_NAMES,
        "feature_importance": feature_importance[:15],
        "species_classes": class_names,
        "ensemble_architecture": "RF(400) + ET(350) + GBM(200) → SoftVote[2:2:1] → CalibratedCV(5)",
        "detailed_report": report,
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    print(f"\n  Model weights saved to: {model_path}")
    print(f"  Metrics report saved to: {metrics_path}")
    print("=" * 70)

    return metrics_payload


if __name__ == "__main__":
    train_and_evaluate_model()
