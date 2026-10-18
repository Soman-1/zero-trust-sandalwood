# AI Model Weights

Binary model weights are **not** committed to Git (they are large and regenerable).

| File | Purpose | Size (approx.) |
|------|---------|----------------|
| `sandalwood_production_model.joblib` | Production satellite/species ensemble | ~117 MB |
| `sandalwood_yolov5s_ca.pt` | YOLOv5s + Coordinate Attention drone detector | ~14 MB |
| `model_metrics.json` | Training metrics metadata (committed) | small |
| `sandalwood_production_model.joblib.sha256` | Integrity checksum (committed) | small |

## Runtime behavior without weights

- **Satellite classifier**: trains a synthetic baseline model if the `.joblib` file is missing.
- **YOLO CA detector**: uses a deterministic botanical segmentation fallback if the `.pt` file is missing or PyTorch is unavailable.

## Restoring production weights

Place the weight files in this directory (same names as above). Verify the production joblib with:

```powershell
# From project root (PowerShell)
Get-FileHash app\ai\weights\sandalwood_production_model.joblib -Algorithm SHA256
# Compare to contents of sandalwood_production_model.joblib.sha256
```

Or retrain via the project training entrypoint (`app/ai/train_model.py`) when appropriate.
