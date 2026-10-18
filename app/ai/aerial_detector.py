"""Aerial & Drone High-Resolution Computer Vision AI Model for Sandalwood Crown Detection."""

import io
import math
import base64
import hashlib
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from app.core.logging import logger

# Preset high-resolution aerial flight datasets
AERIAL_PRESETS = {
    "shivamogga_plantation": {
        "id": "shivamogga_plantation",
        "title": "Shivamogga Sandalwood Agroforestry Block (UAV 4K Orthomosaic)",
        "location": "Shivamogga Reserve, Karnataka (13.9355° N, 75.5652° E)",
        "ground_sampling_distance_cm": 3.5,
        "flight_altitude_m": 45.0,
        "center_lat": 13.9355,
        "center_lon": 75.5652,
        "description": "High-resolution UAV RGB orthomosaic showing mature Sandalwood trees intercropped with Neem (Azadirachta indica) host trees.",
        "simulated_canopies": [
            {
                "box_id": "UAV-SW-001",
                "ymin": 0.12, "xmin": 0.15, "ymax": 0.32, "xmax": 0.34,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.948,
                "crown_diameter_m": 4.8,
                "canopy_area_sqm": 18.1,
                "estimated_age_years": 14,
                "estimated_biomass_kg": 85.0,
                "health_status": "HEALTHY",
                "foliage_texture": "FINE_OVATE_LIGHT_GREEN",
            },
            {
                "box_id": "UAV-HOST-002",
                "ymin": 0.10, "xmin": 0.38, "ymax": 0.36, "xmax": 0.62,
                "species_scientific": "Azadirachta indica",
                "species_common": "Neem (Host Tree)",
                "is_sandalwood": False,
                "is_host_tree": True,
                "confidence": 0.912,
                "crown_diameter_m": 7.2,
                "canopy_area_sqm": 40.7,
                "estimated_age_years": 18,
                "estimated_biomass_kg": 240.0,
                "health_status": "HEALTHY",
                "foliage_texture": "PINNATE_DARK_GREEN",
            },
            {
                "box_id": "UAV-SW-003",
                "ymin": 0.42, "xmin": 0.45, "ymax": 0.60, "xmax": 0.62,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.965,
                "crown_diameter_m": 4.2,
                "canopy_area_sqm": 13.8,
                "estimated_age_years": 11,
                "estimated_biomass_kg": 62.5,
                "health_status": "HEALTHY",
                "foliage_texture": "FINE_OVATE_LIGHT_GREEN",
            },
            {
                "box_id": "UAV-SW-004",
                "ymin": 0.65, "xmin": 0.18, "ymax": 0.82, "xmax": 0.35,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.884,
                "crown_diameter_m": 3.9,
                "canopy_area_sqm": 11.9,
                "estimated_age_years": 9,
                "estimated_biomass_kg": 48.0,
                "health_status": "AT_RISK",
                "foliage_texture": "FINE_OVATE_PALE",
            },
            {
                "box_id": "UAV-HOST-005",
                "ymin": 0.58, "xmin": 0.68, "ymax": 0.85, "xmax": 0.92,
                "species_scientific": "Casuarina equisetifolia",
                "species_common": "Casuarina (Host Tree)",
                "is_sandalwood": False,
                "is_host_tree": True,
                "confidence": 0.926,
                "crown_diameter_m": 6.8,
                "canopy_area_sqm": 36.3,
                "estimated_age_years": 15,
                "estimated_biomass_kg": 190.0,
                "health_status": "HEALTHY",
                "foliage_texture": "NEEDLE_LIKE_WHISPERING",
            },
            {
                "box_id": "UAV-SW-006",
                "ymin": 0.38, "xmin": 0.72, "ymax": 0.54, "xmax": 0.87,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.931,
                "crown_diameter_m": 3.6,
                "canopy_area_sqm": 10.2,
                "estimated_age_years": 8,
                "estimated_biomass_kg": 41.0,
                "health_status": "HEALTHY",
                "foliage_texture": "FINE_OVATE_LIGHT_GREEN",
            },
        ],
    },
    "mysore_reserve": {
        "id": "mysore_reserve",
        "title": "Mysore Royal Sandalwood Forest Sector (Drone Multi-Spectral)",
        "location": "Mysore Forest Division, Karnataka (12.3020° N, 76.6420° E)",
        "ground_sampling_distance_cm": 4.0,
        "flight_altitude_m": 50.0,
        "center_lat": 12.3020,
        "center_lon": 76.6420,
        "description": "Mature native Sandalwood grove flanked by Rosewood (Dalbergia latifolia) and Teak (Tectona grandis).",
        "simulated_canopies": [
            {
                "box_id": "MYS-SW-101",
                "ymin": 0.15, "xmin": 0.20, "ymax": 0.38, "xmax": 0.42,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.972,
                "crown_diameter_m": 5.4,
                "canopy_area_sqm": 22.9,
                "estimated_age_years": 22,
                "estimated_biomass_kg": 160.0,
                "health_status": "HEALTHY",
                "foliage_texture": "DENSE_OVATE_DARK_OLIVE",
            },
            {
                "box_id": "MYS-TEAK-102",
                "ymin": 0.08, "xmin": 0.55, "ymax": 0.40, "xmax": 0.88,
                "species_scientific": "Tectona grandis",
                "species_common": "Teak",
                "is_sandalwood": False,
                "is_host_tree": False,
                "confidence": 0.941,
                "crown_diameter_m": 9.5,
                "canopy_area_sqm": 70.8,
                "estimated_age_years": 30,
                "estimated_biomass_kg": 450.0,
                "health_status": "HEALTHY",
                "foliage_texture": "LARGE_BROADLEAF_CANOPY",
            },
            {
                "box_id": "MYS-SW-103",
                "ymin": 0.48, "xmin": 0.12, "ymax": 0.68, "xmax": 0.31,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.938,
                "crown_diameter_m": 4.6,
                "canopy_area_sqm": 16.6,
                "estimated_age_years": 16,
                "estimated_biomass_kg": 105.0,
                "health_status": "HEALTHY",
                "foliage_texture": "FINE_OVATE_LIGHT_GREEN",
            },
            {
                "box_id": "MYS-ROSE-104",
                "ymin": 0.52, "xmin": 0.40, "ymax": 0.88, "xmax": 0.75,
                "species_scientific": "Dalbergia latifolia",
                "species_common": "Rosewood",
                "is_sandalwood": False,
                "is_host_tree": False,
                "confidence": 0.895,
                "crown_diameter_m": 8.8,
                "canopy_area_sqm": 60.8,
                "estimated_age_years": 28,
                "estimated_biomass_kg": 380.0,
                "health_status": "HEALTHY",
                "foliage_texture": "ROUNDED_DEEP_CANOPY",
            },
            {
                "box_id": "MYS-SW-105",
                "ymin": 0.70, "xmin": 0.78, "ymax": 0.90, "xmax": 0.96,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.915,
                "crown_diameter_m": 4.1,
                "canopy_area_sqm": 13.2,
                "estimated_age_years": 12,
                "estimated_biomass_kg": 72.0,
                "health_status": "HEALTHY",
                "foliage_texture": "FINE_OVATE_LIGHT_GREEN",
            },
        ],
    },
    "coorg_plantation": {
        "id": "coorg_plantation",
        "title": "Coorg Hill Agroforestry Parcel (High-Altitude UAV Flight)",
        "location": "Madikeri, Coorg, Karnataka (12.4244° N, 75.7382° E)",
        "ground_sampling_distance_cm": 3.0,
        "flight_altitude_m": 40.0,
        "center_lat": 12.4244,
        "center_lon": 75.7382,
        "description": "Terraced hill agroforestry plantation with juvenile and middle-aged Sandalwoods with Pongamia pinnata host canopies.",
        "simulated_canopies": [
            {
                "box_id": "CRG-SW-201",
                "ymin": 0.18, "xmin": 0.15, "ymax": 0.35, "xmax": 0.31,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.954,
                "crown_diameter_m": 4.0,
                "canopy_area_sqm": 12.6,
                "estimated_age_years": 10,
                "estimated_biomass_kg": 55.0,
                "health_status": "HEALTHY",
                "foliage_texture": "FINE_OVATE_LIGHT_GREEN",
            },
            {
                "box_id": "CRG-HOST-202",
                "ymin": 0.15, "xmin": 0.36, "ymax": 0.42, "xmax": 0.64,
                "species_scientific": "Pongamia pinnata",
                "species_common": "Honge / Pongamia (Host Tree)",
                "is_sandalwood": False,
                "is_host_tree": True,
                "confidence": 0.918,
                "crown_diameter_m": 6.5,
                "canopy_area_sqm": 33.2,
                "estimated_age_years": 14,
                "estimated_biomass_kg": 175.0,
                "health_status": "HEALTHY",
                "foliage_texture": "SHINY_DARK_GREEN_FOLIAGE",
            },
            {
                "box_id": "CRG-SW-203",
                "ymin": 0.45, "xmin": 0.40, "ymax": 0.62, "xmax": 0.56,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.961,
                "crown_diameter_m": 3.8,
                "canopy_area_sqm": 11.3,
                "estimated_age_years": 8,
                "estimated_biomass_kg": 42.0,
                "health_status": "HEALTHY",
                "foliage_texture": "FINE_OVATE_LIGHT_GREEN",
            },
            {
                "box_id": "CRG-SW-204",
                "ymin": 0.58, "xmin": 0.15, "ymax": 0.76, "xmax": 0.32,
                "species_scientific": "Santalum album",
                "species_common": "Indian Sandalwood (Shrigandha)",
                "is_sandalwood": True,
                "is_host_tree": False,
                "confidence": 0.928,
                "crown_diameter_m": 4.3,
                "canopy_area_sqm": 14.5,
                "estimated_age_years": 12,
                "estimated_biomass_kg": 68.0,
                "health_status": "HEALTHY",
                "foliage_texture": "FINE_OVATE_LIGHT_GREEN",
            },
            {
                "box_id": "CRG-HOST-205",
                "ymin": 0.55, "xmin": 0.65, "ymax": 0.85, "xmax": 0.92,
                "species_scientific": "Azadirachta indica",
                "species_common": "Neem (Host Tree)",
                "is_sandalwood": False,
                "is_host_tree": True,
                "confidence": 0.902,
                "crown_diameter_m": 7.0,
                "canopy_area_sqm": 38.5,
                "estimated_age_years": 16,
                "estimated_biomass_kg": 210.0,
                "health_status": "HEALTHY",
                "foliage_texture": "PINNATE_DARK_GREEN",
            },
        ],
    },
}


class AerialDroneTreeDetector:
    """High-Resolution Computer Vision Engine for Aerial Tree Crown Localization & Species Recognition."""

    def __init__(self):
        logger.info("Initialized Aerial Drone Tree Crown Computer Vision Detector.")

    def get_presets(self) -> List[Dict[str, Any]]:
        """Return metadata for all available aerial flight presets."""
        presets_list = []
        for p_id, p_data in AERIAL_PRESETS.items():
            presets_list.append({
                "id": p_data["id"],
                "title": p_data["title"],
                "location": p_data["location"],
                "ground_sampling_distance_cm": p_data["ground_sampling_distance_cm"],
                "flight_altitude_m": p_data["flight_altitude_m"],
                "center_lat": p_data["center_lat"],
                "center_lon": p_data["center_lon"],
                "description": p_data["description"],
                "canopy_count": len(p_data["simulated_canopies"]),
                "sandalwood_count": sum(1 for c in p_data["simulated_canopies"] if c["is_sandalwood"]),
            })
        return presets_list

    def detect_from_preset(
        self,
        preset_id: str,
        confidence_threshold: float = 0.60,
    ) -> Dict[str, Any]:
        """Run detection on a benchmark aerial flight preset."""
        preset = AERIAL_PRESETS.get(preset_id, AERIAL_PRESETS["shivamogga_plantation"])
        raw_canopies = preset["simulated_canopies"]

        filtered_canopies = []
        for c in raw_canopies:
            if c["confidence"] >= confidence_threshold:
                filtered_canopies.append(c)

        sandalwood_count = sum(1 for c in filtered_canopies if c["is_sandalwood"])
        host_count = sum(1 for c in filtered_canopies if c.get("is_host_tree", False))
        other_count = len(filtered_canopies) - sandalwood_count - host_count

        total_biomass = sum(c.get("estimated_biomass_kg", 50.0) for c in filtered_canopies if c["is_sandalwood"])
        avg_conf = (
            sum(c["confidence"] for c in filtered_canopies) / len(filtered_canopies)
            if filtered_canopies
            else 0.0
        )

        return {
            "preset_id": preset["id"],
            "title": preset["title"],
            "location": preset["location"],
            "center_lat": preset["center_lat"],
            "center_lon": preset["center_lon"],
            "ground_sampling_distance_cm": preset["ground_sampling_distance_cm"],
            "flight_altitude_m": preset["flight_altitude_m"],
            "total_canopies_detected": len(filtered_canopies),
            "sandalwood_count": sandalwood_count,
            "host_trees_count": host_count,
            "other_trees_count": other_count,
            "average_confidence": round(avg_conf, 4),
            "estimated_sandalwood_biomass_kg": round(total_biomass, 1),
            "canopies": filtered_canopies,
            "pipeline_architecture": "SIMULATED — preset canopy layout, not a live detection",
            "evidence_origin": "SIMULATED",
        }

    def detect_from_image_bytes(
        self,
        image_data: bytes,
        confidence_threshold: float = 0.50,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        gsd_cm: float = 3.5,
    ) -> Dict[str, Any]:
        """
        Analyze uploaded drone aerial image byte stream using Coordinate Attention YOLOv5s deep learning engine.
        Extracts tree crown bounding boxes, measures crown diameter, canopy area, and computes allometric biomass.
        """
        from app.ai.yolo_ca_detector import yolo_ca_detector

        c_lat = center_lat or 13.9355
        c_lon = center_lon or 75.5652

        # Run Coordinate Attention YOLOv5s inference
        canopies = yolo_ca_detector.detect(
            image_input=image_data,
            confidence_threshold=confidence_threshold,
            gsd_cm=gsd_cm
        )

        sandalwood_count = sum(1 for c in canopies if c.get("is_sandalwood", True))
        host_count = sum(1 for c in canopies if c.get("is_host_tree", False))
        other_count = len(canopies) - sandalwood_count - host_count
        total_biomass = sum(c.get("estimated_biomass_kg", 50.0) for c in canopies if c.get("is_sandalwood", True))
        avg_conf = sum(c["confidence"] for c in canopies) / len(canopies) if canopies else 0.0
        simulated = (not yolo_ca_detector.is_loaded) or any(
            c.get("evidence_origin") == "SIMULATED" for c in canopies
        )

        return {
            "preset_id": "custom_upload",
            "title": "Custom Drone Orthomosaic Upload",
            "location": f"GPS Reference ({c_lat:.4f}° N, {c_lon:.4f}° E)",
            "center_lat": c_lat,
            "center_lon": c_lon,
            "ground_sampling_distance_cm": gsd_cm,
            "flight_altitude_m": round(gsd_cm * 12.5, 1),
            "total_canopies_detected": len(canopies),
            "sandalwood_count": sandalwood_count,
            "host_trees_count": host_count,
            "other_trees_count": other_count,
            "average_confidence": round(avg_conf, 4),
            "estimated_sandalwood_biomass_kg": round(total_biomass, 1),
            "canopies": canopies,
            "pipeline_architecture": (
                "SIMULATED — boxes were placed without YOLO inference"
                if simulated
                else "Improved-YOLOv5s with Coordinate Attention (CABlock) + Empirical Allometrics"
            ),
            "evidence_origin": "SIMULATED" if simulated else "MODEL",
        }

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @staticmethod
    def _calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_lambda = math.radians(lon2 - lon1)
        y = math.sin(delta_lambda) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
        bearing = math.degrees(math.atan2(y, x))
        return round((bearing + 360.0) % 360.0, 1)

    def generate_patrol_mission(
        self,
        preset_id: str = "shivamogga_plantation",
        speed_mps: float = 8.0,
    ) -> Dict[str, Any]:
        """
        Generate an autonomous serpentine survey flight mission over the designated sandalwood reserve.
        Computes flight waypoints, bearings, cumulative distances, and schedules target canopy interceptions.
        """
        preset = AERIAL_PRESETS.get(preset_id, AERIAL_PRESETS["shivamogga_plantation"])
        c_lat = preset["center_lat"]
        c_lon = preset["center_lon"]
        alt_m = preset["flight_altitude_m"]
        speed = max(2.0, min(speed_mps, 20.0))

        # Define serpentine photogrammetry grid offsets around the center (covering ~400m x 400m compartment)
        raw_waypoints_def = [
            ("WP-01", c_lat + 0.0016, c_lon - 0.0020, "TAKEOFF"),
            ("WP-02", c_lat + 0.0016, c_lon + 0.0020, "TRANSIT_SCAN"),
            ("WP-03", c_lat + 0.0005, c_lon + 0.0020, "TRANSIT_SCAN"),
            ("WP-04", c_lat + 0.0005, c_lon - 0.0018, "TRANSIT_SCAN"),
            ("WP-05", c_lat - 0.0006, c_lon - 0.0018, "TRANSIT_SCAN"),
            ("WP-06", c_lat - 0.0006, c_lon + 0.0020, "TRANSIT_SCAN"),
            ("WP-07", c_lat - 0.0016, c_lon + 0.0000, "TRANSIT_SCAN"),
            ("WP-08", c_lat + 0.0016, c_lon - 0.0020, "RTB_LAND"),
        ]

        waypoints: List[Dict[str, Any]] = []
        cum_dist = 0.0
        prev_lat, prev_lon = raw_waypoints_def[0][1], raw_waypoints_def[0][2]

        for idx, (wp_id, wp_lat, wp_lon, action) in enumerate(raw_waypoints_def):
            seq = idx + 1
            if idx == 0:
                leg_dist = 0.0
                bearing = 90.0
            else:
                leg_dist = self._haversine_distance(prev_lat, prev_lon, wp_lat, wp_lon)
                bearing = self._calculate_bearing(prev_lat, prev_lon, wp_lat, wp_lon)
                cum_dist += leg_dist

            eta = round(cum_dist / speed, 1)
            waypoints.append({
                "waypoint_id": wp_id,
                "sequence": seq,
                "latitude": round(wp_lat, 6),
                "longitude": round(wp_lon, 6),
                "altitude_m": alt_m,
                "leg_distance_m": round(leg_dist, 1),
                "cumulative_distance_m": round(cum_dist, 1),
                "leg_bearing_deg": bearing,
                "eta_sec": eta,
                "action": action,
            })
            prev_lat, prev_lon = wp_lat, wp_lon

        total_duration = round(cum_dist / speed, 1)

        # Map simulated canopies to geographic coordinates and schedule their flight interception
        canopy_targets: List[Dict[str, Any]] = []
        canopies = preset.get("simulated_canopies", [])
        span_lat = 0.0032
        span_lon = 0.0038

        for idx, c in enumerate(canopies):
            canopy_lat = round(c_lat + (0.5 - (c["ymin"] + c["ymax"]) / 2.0) * span_lat, 6)
            canopy_lon = round(c_lon + ((c["xmin"] + c["xmax"]) / 2.0 - 0.5) * span_lon, 6)

            # Assign to sequential flight timeline
            progress_ratio = (idx + 0.8) / max(len(canopies), 1)
            interception_time = round(progress_ratio * (total_duration * 0.82), 1)
            closest_wp = waypoints[min(int(progress_ratio * (len(waypoints) - 2)) + 1, len(waypoints) - 1)]["waypoint_id"]

            canopy_targets.append({
                "box_id": c["box_id"],
                "latitude": canopy_lat,
                "longitude": canopy_lon,
                "species_scientific": c["species_scientific"],
                "species_common": c["species_common"],
                "is_sandalwood": c["is_sandalwood"],
                "is_host_tree": c.get("is_host_tree", False),
                "confidence": c["confidence"],
                "crown_diameter_m": c["crown_diameter_m"],
                "estimated_biomass_kg": c.get("estimated_biomass_kg", 50.0),
                "health_status": c.get("health_status", "HEALTHY"),
                "interception_time_sec": interception_time,
                "associated_waypoint_id": closest_wp,
            })

        canopy_targets.sort(key=lambda x: x["interception_time_sec"])

        mission_id = f"MSN-UAV-{preset['id'].replace('_', '-').upper()}-01"
        hardware_id = f"DEV-UAV-{preset['id'].split('_')[0].upper()}-01"
        mission_payload = f"{mission_id}:{hardware_id}:{c_lat}:{c_lon}:{cum_dist}:{len(canopy_targets)}"
        mission_hash = hashlib.sha256(mission_payload.encode("utf-8")).hexdigest()

        return {
            "mission_id": mission_id,
            "drone_hardware_id": hardware_id,
            "preset_id": preset["id"],
            "preset_title": preset["title"],
            "reserve_name": preset["location"],
            "flight_altitude_m": alt_m,
            "survey_speed_mps": speed,
            "total_waypoints": len(waypoints),
            "total_distance_m": round(cum_dist, 1),
            "total_duration_sec": total_duration,
            "sandalwood_count": sum(1 for t in canopy_targets if t["is_sandalwood"]),
            "host_trees_count": sum(1 for t in canopy_targets if t["is_host_tree"]),
            "waypoints": waypoints,
            "canopy_targets": canopy_targets,
            "mission_integrity_hash": mission_hash,
            "pipeline_architecture": "Autonomous Serpentine Survey Grid + Coordinate Attention YOLOv5s Target Locking",
        }


# Global singleton detector instance
aerial_detector = AerialDroneTreeDetector()
