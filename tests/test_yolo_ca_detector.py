"""Unit tests for Coordinate Attention YOLOv5s Sandalwood Tree Detection."""

import io
import pytest
import numpy as np
from PIL import Image
from app.ai.yolo_ca_detector import (
    SandalwoodYOLOv5CADetector,
    letterbox_image,
    compute_iou,
    nms_boxes,
    yolo_ca_detector
)
from app.ai.aerial_detector import aerial_detector


def test_letterbox_image():
    """Test letterboxing image transformation maintains aspect ratio."""
    test_img = Image.new("RGB", (800, 600), color=(34, 139, 34))
    resized, scale, (pad_x, pad_y) = letterbox_image(test_img, target_size=(640, 640))

    assert resized.size == (640, 640)
    assert scale == 640 / 800
    assert pad_x == 0
    assert pad_y == (640 - int(600 * (640 / 800))) // 2


def test_iou_computation():
    """Test standard bounding box IoU computation."""
    b1 = np.array([10.0, 10.0, 50.0, 50.0])
    b2 = np.array([10.0, 10.0, 50.0, 50.0])
    assert pytest.approx(compute_iou(b1, b2), 0.001) == 1.0

    b3 = np.array([60.0, 60.0, 100.0, 100.0])
    assert compute_iou(b1, b3) == 0.0


def test_nms_boxes():
    """Test Non-Maximum Suppression suppresses overlapping boxes."""
    boxes = [
        {"box_id": "1", "xmin": 0.1, "ymin": 0.1, "xmax": 0.3, "ymax": 0.3, "confidence": 0.95},
        {"box_id": "2", "xmin": 0.11, "ymin": 0.11, "xmax": 0.31, "ymax": 0.31, "confidence": 0.85},
        {"box_id": "3", "xmin": 0.6, "ymin": 0.6, "xmax": 0.8, "ymax": 0.8, "confidence": 0.90},
    ]
    filtered = nms_boxes(boxes, iou_threshold=0.45)
    assert len(filtered) == 2
    assert filtered[0]["box_id"] == "1"
    assert filtered[1]["box_id"] == "3"


def test_yolo_ca_detector_detect_synthetic_image():
    """Test detection on a generated synthetic canopy image."""
    test_img = Image.new("RGB", (640, 640), color=(50, 120, 50))
    detections = yolo_ca_detector.detect(test_img, confidence_threshold=0.40)

    assert isinstance(detections, list)
    assert len(detections) > 0
    for det in detections:
        assert "ymin" in det and "xmin" in det and "ymax" in det and "xmax" in det
        assert "confidence" in det
        assert "crown_diameter_m" in det
        assert "canopy_area_sqm" in det
        assert det["is_sandalwood"] is True


def test_aerial_detector_integration():
    """Test that AerialDroneTreeDetector properly executes detection from raw bytes."""
    test_img = Image.new("RGB", (512, 512), color=(40, 140, 40))
    img_byte_arr = io.BytesIO()
    test_img.save(img_byte_arr, format='PNG')
    raw_bytes = img_byte_arr.getvalue()

    result = aerial_detector.detect_from_image_bytes(
        image_data=raw_bytes,
        confidence_threshold=0.40,
        center_lat=13.9355,
        center_lon=75.5652
    )

    assert result["total_canopies_detected"] > 0
    assert result["sandalwood_count"] > 0
    if yolo_ca_detector.is_loaded and result.get("evidence_origin") == "MODEL":
        assert "Improved-YOLOv5s" in result["pipeline_architecture"]
    else:
        assert result["evidence_origin"] == "SIMULATED"
        assert result["pipeline_architecture"].startswith("SIMULATED")
    assert "canopies" in result
    assert len(result["canopies"]) == result["total_canopies_detected"]
