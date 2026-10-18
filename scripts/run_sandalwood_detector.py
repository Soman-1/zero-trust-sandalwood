"""Standalone CLI runner for Sandalwood (Santalum album) Tree Crown Detection using Coordinate Attention YOLOv5s.

Usage:
    python scripts/run_sandalwood_detector.py --source datasets/images/aerial_tiles/tile_01.png --save
    python scripts/run_sandalwood_detector.py --source santlum-main/santlum-main/stylegan/reals.png --conf 0.45 --save
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure root directory is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.yolo_ca_detector import yolo_ca_detector


def parse_args():
    parser = argparse.ArgumentParser(description="Coordinate Attention YOLOv5s Sandalwood Tree Detector")
    parser.add_argument(
        "--source",
        type=str,
        default="santlum-main/santlum-main/stylegan/reals.png",
        help="Path to image file, folder, or glob pattern"
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="app/ai/weights/sandalwood_yolov5s_ca.pt",
        help="Path to trained weights"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.45,
        help="Confidence threshold (0.0 to 1.0)"
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.45,
        help="NMS IoU threshold (0.0 to 1.0)"
    )
    parser.add_argument(
        "--gsd",
        type=float,
        default=3.5,
        help="Ground sampling distance in cm/pixel"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save annotated detection images"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="runs/detect_sandalwood",
        help="Directory to save annotated detection images"
    )
    return parser.parse_args()


def process_image(img_path: Path, detector, conf: float, iou: float, gsd: float, save: bool, out_dir: Path):
    print(f"\n[INFO] Processing image: {img_path.name}")
    try:
        image = Image.open(img_path).convert("RGB")
    except Exception as e:
        print(f"[ERROR] Error opening image {img_path}: {e}")
        return

    import time
    t0 = time.time()
    detections = detector.detect(
        image_input=image,
        confidence_threshold=conf,
        iou_threshold=iou,
        gsd_cm=gsd
    )
    elapsed_ms = round((time.time() - t0) * 1000, 1)

    print(f"[RESULT] Found {len(detections)} Sandalwood tree canopies in {elapsed_ms} ms (conf >= {conf}):")
    print(f"{'ID':<15} {'Confidence':<12} {'Crown Diam (m)':<16} {'Area (m2)':<12} {'Est Biomass':<14} {'BBox [ymin,xmin,ymax,xmax]'}")
    print("-" * 90)

    total_biomass = 0.0
    for d in detections:
        bbox_str = f"[{d['ymin']:.2f}, {d['xmin']:.2f}, {d['ymax']:.2f}, {d['xmax']:.2f}]"
        print(f"{d['box_id']:<15} {d['confidence']*100:>8.1f}%   {d['crown_diameter_m']:>12.2f}m    {d['canopy_area_sqm']:>8.1f}m2   {d['estimated_biomass_kg']:>8.1f} kg     {bbox_str}")
        total_biomass += d.get("estimated_biomass_kg", 0.0)

    print("-" * 90)
    print(f"[SUMMARY] Total Sandalwood Trees: {len(detections)} | Total Estimated Biomass: {total_biomass:.1f} kg")

    if save:
        out_dir.mkdir(parents=True, exist_ok=True)
        annotated = detector.annotate_image(image, detections)
        out_file = out_dir / f"detected_{img_path.name}"
        annotated.save(out_file)
        print(f"[SAVED] Annotated image saved to: {out_file.resolve()}")


def main():
    args = parse_args()
    source_path = Path(args.source)
    out_dir = Path(args.output_dir)

    print("=" * 60)
    print("Coordinate Attention YOLOv5s Sandalwood Detection CLI")
    print("=" * 60)
    print(f"Model: Coordinate Attention YOLOv5s (CABlock)")
    print(f"Weights: {args.weights}")
    print(f"Confidence Threshold: {args.conf}")

    if source_path.is_file():
        process_image(source_path, yolo_ca_detector, args.conf, args.iou, args.gsd, args.save, out_dir)
    elif source_path.is_dir():
        image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
        images = [f for f in source_path.iterdir() if f.suffix.lower() in image_exts]
        if not images:
            print(f"[WARN] No image files found in directory: {source_path}")
            return
        print(f"Found {len(images)} images in {source_path}")
        for img in images:
            process_image(img, yolo_ca_detector, args.conf, args.iou, args.gsd, args.save, out_dir)
    else:
        print(f"[ERROR] Source path does not exist: {source_path}")


if __name__ == "__main__":
    main()
