"""Satellite AI multi-spectral canopy identification and GBIF data ingestion API endpoints."""

import time
import base64
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.ai.satellite_classifier import (
    satellite_classifier,
    BASE_SPECTRAL_SIGNATURES,
    SPECIES_CLASSES,
)
from app.ai.aerial_detector import aerial_detector
from app.services.gbif_service import GBIFService
from app.services.weather_service import RealWorldWeatherService, WeatherFetchError
from app.schemas.satellite import (
    SatelliteIdentifyRequest,
    SatelliteIdentifyResponse,
    SatelliteScanRequest,
    SatelliteScanResponse,
    GBIFSyncRequest,
    GBIFSyncResponse,
    RealWorldTreeItem,
    AerialDetectRequest,
    AerialDetectResponse,
    AerialPresetsResponse,
    LiveClimateResponse,
    LandmarkPreset,
    DronePatrolMissionResponse,
)
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/satellite", tags=["Satellite AI & Real-World Trees"])


@router.post(
    "/identify",
    response_model=SatelliteIdentifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Identify Sandalwood Tree from Satellite GPS & Multi-Spectral Data",
    description=(
        "Applies AI multi-spectral canopy classification on Sentinel-2 reflectance bands at any GPS coordinate "
        "to distinguish Santalum album (Sandalwood) from Teak, Rosewood, Eucalyptus, Neem, and other species."
    ),
)
def identify_tree_from_satellite(
    payload: SatelliteIdentifyRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> SatelliteIdentifyResponse:
    bands_dict = payload.bands.model_dump() if payload.bands else None

    result = satellite_classifier.identify(
        latitude=payload.latitude,
        longitude=payload.longitude,
        bands=bands_dict,
        height_m=payload.elevation_m,
    )

    return SatelliteIdentifyResponse(
        latitude=result["latitude"],
        longitude=result["longitude"],
        is_sandalwood=result["is_sandalwood"],
        predicted_species=result["predicted_species"],
        predicted_common_name=result["predicted_common_name"],
        confidence_score=result["confidence_score"],
        all_probabilities=result["all_probabilities"],
        spectral_indices=result["spectral_indices"],
        sentinel_bands=result["sentinel_bands"],
        satellite_source=result["satellite_source"],
        evidence_origin=result.get("evidence_origin", "SIMULATED"),
        identification_timestamp=datetime.now(timezone.utc),
    )


@router.post(
    "/scan-area",
    response_model=SatelliteScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan Satellite Canopy Grid to Isolate Sandalwood Trees",
    description="Simulates satellite AI scanning across a geographic bounding box of thousands of trees, isolating Sandalwood specimens.",
)
def scan_satellite_bounding_box(
    payload: SatelliteScanRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> SatelliteScanResponse:
    start_time = time.time()

    scan_result = satellite_classifier.scan_grid(
        min_lat=payload.bbox.min_lat,
        min_lon=payload.bbox.min_lon,
        max_lat=payload.bbox.max_lat,
        max_lon=payload.bbox.max_lon,
        sample_count=payload.sample_tree_count,
        confidence_threshold=payload.confidence_threshold,
    )

    duration_ms = round((time.time() - start_time) * 1000, 2)

    return SatelliteScanResponse(
        total_trees_scanned=scan_result["total_trees_scanned"],
        sandalwood_detected_count=scan_result["sandalwood_detected_count"],
        other_species_count=scan_result["other_species_count"],
        scan_duration_ms=duration_ms,
        detected_sandalwood_trees=scan_result["detected_sandalwood_trees"],
        dominant_non_sandalwood_species=scan_result["dominant_non_sandalwood_species"],
        evidence_origin=scan_result.get("evidence_origin", "SIMULATED"),
        satellite_source=scan_result.get(
            "satellite_source",
            "SIMULATED — random points and synthetic reflectance, not a Sentinel-2 scene",
        ),
    )


@router.post(
    "/sync-gbif",
    response_model=GBIFSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync Real-World Occurrences from GBIF Public API",
    description="Queries the public Global Biodiversity Information Facility (GBIF) API for real-world Santalum album occurrences in India/Karnataka and persists them in the database.",
)
def sync_gbif_occurrences(
    payload: GBIFSyncRequest = GBIFSyncRequest(),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> GBIFSyncResponse:
    return GBIFService.sync_and_persist_gbif_records(
        db=db,
        limit=payload.limit,
        country=payload.country,
        state=payload.state,
    )


@router.get(
    "/spectral-profiles",
    status_code=status.HTTP_200_OK,
    summary="Get Multi-Spectral Canopy Profiles",
    description="Returns benchmark Sentinel-2 reflectance profiles for Sandalwood and co-occurring forest species.",
)
def get_spectral_profiles(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    formatted = {}
    for species, bands in BASE_SPECTRAL_SIGNATURES.items():
        formatted[species] = {
            k: {"mean": round(v[0], 3), "std": round(v[1], 3)} for k, v in bands.items()
        }
    return {
        "bands_info": {
            "blue": "Band 2 (490nm)",
            "green": "Band 3 (560nm)",
            "red": "Band 4 (665nm)",
            "red_edge": "Band 5 (705nm)",
            "nir": "Band 8 (842nm)",
            "swir1": "Band 11 (1610nm)",
            "swir2": "Band 12 (2190nm)",
        },
        "profiles": formatted,
    }


@router.get(
    "/real-world-trees",
    response_model=List[RealWorldTreeItem],
    status_code=status.HTTP_200_OK,
    summary="List Synced Real-World Biodiversity Trees",
    description="Retrieves registered real-world trees with research-grade GPS and observer metadata.",
)
def list_real_world_trees(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
) -> List[RealWorldTreeItem]:
    raw = GBIFService.fetch_real_sandalwood_occurrences(limit=limit)
    items: List[RealWorldTreeItem] = []
    for rec in raw:
        lat = rec.get("decimalLatitude")
        lon = rec.get("decimalLongitude")
        if lat is None or lon is None:
            continue
        key = str(rec.get("key") or rec.get("gbifID") or rec.get("identifier"))
        media = rec.get("media", [])
        img = media[0].get("identifier") if media and isinstance(media, list) else None
        items.append(
            RealWorldTreeItem(
                gbif_id=key,
                scientific_name=rec.get("scientificName", "Santalum album L."),
                vernacular_name="Indian Sandalwood (Shrigandha)",
                latitude=float(lat),
                longitude=float(lon),
                state_province=rec.get("stateProvince", "Karnataka"),
                locality=rec.get("locality") or rec.get("verbatimLocality") or "Agroforestry Reserve",
                recorded_by=rec.get("recordedBy", "Field Surveyor"),
                event_date=rec.get("eventDate"),
                image_url=img,
                inaturalist_url=rec.get("references"),
                dataset_name=rec.get("datasetName", "GBIF Dataset"),
                is_sandalwood=True,
            )
        )
    return items


# ==========================================
# DRONE & AERIAL COMPUTER VISION ENDPOINTS
# ==========================================

@router.get(
    "/aerial-presets",
    response_model=AerialPresetsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Benchmark Aerial Drone Flight Presets",
    description="Returns pre-calibrated UAV high-resolution flight presets over Karnataka forest reserves.",
)
def get_aerial_presets(
    current_user: User = Depends(get_current_user),
) -> AerialPresetsResponse:
    presets = aerial_detector.get_presets()
    return AerialPresetsResponse(presets=presets)


@router.post(
    "/detect-aerial",
    response_model=AerialDetectResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect and Classify Tree Crowns from Top-Down Drone/Aerial Imagery",
    description=(
        "Runs high-resolution computer vision AI model to localize individual tree crowns, "
        "differentiate Sandalwood from host trees (Neem, Casuarina), and compute canopy area and biomass."
    ),
)
def detect_aerial_canopies(
    payload: AerialDetectRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> AerialDetectResponse:
    if payload.image_base64:
        # Decode base64 if provided
        try:
            cleaned = payload.image_base64
            if "," in cleaned:
                cleaned = cleaned.split(",", 1)[1]
            raw_bytes = base64.b64decode(cleaned, validate=False)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 image payload",
            ) from exc
        if len(raw_bytes) > 1_500_000:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Decoded image exceeds 1.5MB limit",
            )

        result = aerial_detector.detect_from_image_bytes(
            image_data=raw_bytes,
            confidence_threshold=payload.confidence_threshold,
            center_lat=payload.center_lat,
            center_lon=payload.center_lon,
            gsd_cm=payload.ground_sampling_distance_cm,
        )
    else:
        # Default to preset
        preset_id = payload.preset_id or "shivamogga_plantation"
        result = aerial_detector.detect_from_preset(
            preset_id=preset_id,
            confidence_threshold=payload.confidence_threshold,
        )

    return AerialDetectResponse(
        preset_id=result["preset_id"],
        title=result["title"],
        location=result["location"],
        center_lat=result["center_lat"],
        center_lon=result["center_lon"],
        ground_sampling_distance_cm=result["ground_sampling_distance_cm"],
        flight_altitude_m=result["flight_altitude_m"],
        total_canopies_detected=result["total_canopies_detected"],
        sandalwood_count=result["sandalwood_count"],
        host_trees_count=result["host_trees_count"],
        other_trees_count=result["other_trees_count"],
        average_confidence=result["average_confidence"],
        estimated_sandalwood_biomass_kg=result["estimated_sandalwood_biomass_kg"],
        canopies=result["canopies"],
        pipeline_architecture=result["pipeline_architecture"],
        evidence_origin=result.get("evidence_origin", "SIMULATED"),
    )


@router.get(
    "/drone-patrol-mission",
    response_model=DronePatrolMissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Autonomous Drone Waypoint Mission & Canopy Target Schedule",
    description="Generates an automated serpentine survey flight grid with waypoints, distances, bearings, and scheduled sandalwood canopy target intercepts.",
)
def get_drone_patrol_mission(
    preset_id: str = Query("shivamogga_plantation", description="Flight preset identifier"),
    speed_mps: float = Query(8.0, ge=2.0, le=20.0, description="UAV flight speed in meters/second"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> DronePatrolMissionResponse:
    mission = aerial_detector.generate_patrol_mission(
        preset_id=preset_id,
        speed_mps=speed_mps,
    )
    return DronePatrolMissionResponse(**mission)


# ==========================================
# REAL-WORLD WEATHER & GLOBAL SATELLITE ROUTES
# ==========================================

@router.get(
    "/live-weather",
    response_model=LiveClimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Real-Time Weather & Soil Data for any GPS Coordinate",
    description="Queries Open-Meteo live API to fetch real-world temperature, humidity, multi-depth soil moisture, elevation, and compute VPD.",
)
def get_live_weather(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    current_user: User = Depends(get_current_user),
) -> LiveClimateResponse:
    try:
        data = RealWorldWeatherService.get_live_microclimate(latitude, longitude)
    except WeatherFetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Live weather unavailable: {exc}",
        ) from exc
    return LiveClimateResponse(**data)


@router.get(
    "/landmarks",
    response_model=List[LandmarkPreset],
    status_code=status.HTTP_200_OK,
    summary="Get Global Sandalwood & Agroforestry Landmarks",
    description="Returns curated global landmarks for Satellite Map fly-to navigation.",
)
def get_global_landmarks(
    current_user: User = Depends(get_current_user),
) -> List[LandmarkPreset]:
    return [
        LandmarkPreset(
            id="shivamogga_reserve",
            name="Shivamogga Agroforestry Reserve",
            category="Protected Forest",
            country="India",
            region_name="Karnataka",
            latitude=13.9355,
            longitude=75.5652,
            altitude_m=640.0,
            description="Core research zone with high-density Santalum album specimens and automated IoT microclimate monitoring nodes.",
            tree_species="Santalum album (Indian Sandalwood)",
            is_verified_reserve=True,
        ),
        LandmarkPreset(
            id="mysore_heritage",
            name="Mysore Sandalwood Heritage Belt",
            category="Heritage Reserve",
            country="India",
            region_name="Karnataka",
            latitude=12.3020,
            longitude=76.6420,
            altitude_m=763.0,
            description="Historic Royal Mysore Sandalwood cultivation center known for high concentration of alpha-santalol oil content.",
            tree_species="Santalum album",
            is_verified_reserve=True,
        ),
        LandmarkPreset(
            id="marayoor_kerala",
            name="Marayoor Natural Sandalwood Forest",
            category="Natural Reserve",
            country="India",
            region_name="Kerala",
            latitude=10.2798,
            longitude=77.1601,
            altitude_m=980.0,
            description="The only natural wild sandalwood forest in Kerala, nestled in the rain-shadow Western Ghats valley.",
            tree_species="Santalum album",
            is_verified_reserve=True,
        ),
        LandmarkPreset(
            id="sirsi_western_ghats",
            name="Sirsi High-Canopy Western Ghats",
            category="Canopy Sanctuary",
            country="India",
            region_name="Karnataka",
            latitude=14.6195,
            longitude=74.8354,
            altitude_m=590.0,
            description="Dense tropical evergreen bio-corridor providing optimal mixed shade and host tree pairings (Casuarina / Pongamia).",
            tree_species="Santalum album & Pterocarpus marsupium",
            is_verified_reserve=True,
        ),
        LandmarkPreset(
            id="br_hills_sanctuary",
            name="BR Hills Wildlife & Flora Sanctuary",
            category="Biosphere Reserve",
            country="India",
            region_name="Karnataka",
            latitude=11.9180,
            longitude=76.9450,
            altitude_m=1200.0,
            description="Highland ecological corridor linking the Eastern and Western Ghats with ancient sandalwood trees.",
            tree_species="Santalum album",
            is_verified_reserve=True,
        ),
        LandmarkPreset(
            id="perth_australia",
            name="Perth & Kalgoorlie Sandalwood Belt",
            category="Global Sister Reserve",
            country="Australia",
            region_name="Western Australia",
            latitude=-30.7489,
            longitude=121.4658,
            altitude_m=360.0,
            description="Major arid-zone Australian Sandalwood plantation belt adapted to low-precipitation landscapes.",
            tree_species="Santalum spicatum (Australian Sandalwood)",
            is_verified_reserve=False,
        ),
        LandmarkPreset(
            id="kona_hawaii",
            name="Kona Sandalwood Highlands",
            category="Pacific Island Reserve",
            country="United States",
            region_name="Hawaii",
            latitude=19.6400,
            longitude=-155.9969,
            altitude_m=1100.0,
            description="High-elevation volcanic slopes cultivating endemic Hawaiian 'Iliahi sandalwood varieties.",
            tree_species="Santalum paniculatum / freycinetianum",
            is_verified_reserve=False,
        ),
        LandmarkPreset(
            id="east_sumba",
            name="East Sumba Cendana Reserve",
            category="Indonesian Flora Reserve",
            country="Indonesia",
            region_name="East Nusa Tenggara",
            latitude=-9.6500,
            longitude=120.2600,
            altitude_m=420.0,
            description="Traditional Indonesian Cendana sandalwood groves with distinct multi-spectral canopy reflectance.",
            tree_species="Santalum album (Cendana)",
            is_verified_reserve=False,
        ),
    ]


@router.get(
    "/world-occurrences",
    response_model=List[RealWorldTreeItem],
    status_code=status.HTTP_200_OK,
    summary="Get Verified Global Sandalwood Occurrences with Real Photos",
    description="Returns global verified botanical occurrence records from GBIF and iNaturalist.",
)
def get_global_occurrences(
    limit: int = Query(60, ge=10, le=200),
    country: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
) -> List[RealWorldTreeItem]:
    raw = GBIFService.fetch_real_sandalwood_occurrences(limit=limit, country=country or "IN")
    items: List[RealWorldTreeItem] = []
    
    for rec in raw:
        lat = rec.get("decimalLatitude")
        lon = rec.get("decimalLongitude")
        if lat is None or lon is None:
            continue
        key = str(rec.get("key") or rec.get("gbifID") or rec.get("identifier") or "0")
        media = rec.get("media", [])
        img_url = media[0].get("identifier") if media and isinstance(media, list) else None
        
        items.append(
            RealWorldTreeItem(
                gbif_id=key,
                scientific_name=rec.get("scientificName", "Santalum album L."),
                vernacular_name="Indian Sandalwood (Shrigandha)",
                latitude=float(lat),
                longitude=float(lon),
                state_province=rec.get("stateProvince", "Karnataka"),
                locality=rec.get("locality") or rec.get("verbatimLocality") or "Agroforestry Reserve",
                recorded_by=rec.get("recordedBy", "Botanical Observer"),
                event_date=rec.get("eventDate"),
                image_url=img_url,
                inaturalist_url=rec.get("references"),
                dataset_name=rec.get("datasetName", "GBIF Public Ingestion"),
                is_sandalwood=True,
            )
        )
    return items

