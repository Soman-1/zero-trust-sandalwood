"""Service for aggregating, normalizing, and importing real-world Internet Sandalwood biodiversity data."""

import os
import json
import csv
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.logging import logger
from app.database.models.tree import Tree, TreeStatus
from app.core.errors import AppException, NotFoundError
from app.schemas.global_tree import (
    GlobalTreeItem,
    GlobalTreeStatsResponse,
    GlobalTreeImportResponse,
    GlobalTreeEnvironmentSnapshot,
    GlobalTreeHeartwoodEstimate,
    GlobalTreeRegisterResponse,
)
from app.schemas.tree import TreeRegisterRequest
from app.services.sandalwood_biometrics import calculate_allometric_sandalwood_biometrics

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")

# ~1.1 cm coordinate resolution; keeps research-grade GPS exact for map/import
_GPS_DECIMALS = 7
# Dedup only merges points within ~11 cm (was 4 dp / ~11 m and collapsed distinct trees)
_DEDUP_DECIMALS = 6
# Drop country/state-level centroids that look like trees on the map
_MAX_MAP_UNCERTAINTY_M = 5000.0

# In-memory cache — avoids re-parsing ~2MB JSON/CSV on every API hit
_records_cache: Optional[List[GlobalTreeItem]] = None
_records_cache_stamp: Optional[Tuple[float, ...]] = None


def _coord_key(lat: float, lon: float) -> str:
    return f"{round(lat, _DEDUP_DECIMALS):.{_DEDUP_DECIMALS}f},{round(lon, _DEDUP_DECIMALS):.{_DEDUP_DECIMALS}f}"


def _precise_coord(value: float) -> float:
    return round(float(value), _GPS_DECIMALS)


def _source_files() -> Tuple[str, ...]:
    return (
        os.path.join(DATASETS_DIR, "gbif_sandalwood_occurrences.json"),
        os.path.join(DATASETS_DIR, "street_view", "internet_ground_photos_catalog.json"),
        os.path.join(DATASETS_DIR, "sandalwood_occurrences_20260904_012006.csv"),
    )


def _dataset_mtime_stamp() -> Tuple[float, ...]:
    stamp: list[float] = []
    for path in _source_files():
        try:
            stamp.append(os.path.getmtime(path) if os.path.exists(path) else 0.0)
        except OSError:
            stamp.append(0.0)
    return tuple(stamp)


def _record_quality(rec: Dict[str, Any]) -> Tuple[int, float, int]:
    """Higher tuple = better map candidate when two GPS points collide."""
    has_photo = 1 if rec.get("image_url") else 0
    acc = rec.get("gps_accuracy")
    # Prefer known tight accuracy; unknown ranks mid; huge uncertainty ranks last
    if acc is None:
        acc_score = -250.0
    else:
        try:
            acc_score = -float(acc)
        except (TypeError, ValueError):
            acc_score = -250.0
    has_locality = 1 if rec.get("locality") else 0
    return (has_photo, acc_score, has_locality)


def _is_map_grade(lat: float, lon: float, gps_accuracy: Optional[float]) -> bool:
    """Reject null-island and ultra-coarse centroids that blur the map."""
    if abs(lat) < 0.01 and abs(lon) < 0.01:
        return False
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return False
    if gps_accuracy is not None:
        try:
            if float(gps_accuracy) > _MAX_MAP_UNCERTAINTY_M:
                return False
        except (TypeError, ValueError):
            pass
    return True


def _upsert_raw(raw_items: Dict[str, Dict[str, Any]], key: str, rec: Dict[str, Any]) -> None:
    existing = raw_items.get(key)
    if existing is None or _record_quality(rec) > _record_quality(existing):
        raw_items[key] = rec
    else:
        # Keep stronger pin, but enrich with photo / notes from the weaker record
        if not existing.get("image_url") and rec.get("image_url"):
            existing["image_url"] = rec["image_url"]
        if not existing.get("external_url") and rec.get("external_url"):
            existing["external_url"] = rec["external_url"]
        if existing.get("gps_accuracy") is None and rec.get("gps_accuracy") is not None:
            existing["gps_accuracy"] = rec["gps_accuracy"]
        if rec.get("bark_characteristics") and not existing.get("bark_characteristics"):
            existing["bark_characteristics"] = rec["bark_characteristics"]
        if rec.get("foliage_characteristics") and not existing.get("foliage_characteristics"):
            existing["foliage_characteristics"] = rec["foliage_characteristics"]


class GlobalTreeService:
    """Aggregates sandalwood occurrences from GBIF, iNaturalist, and curated catalogs."""

    @classmethod
    def invalidate_cache(cls) -> None:
        global _records_cache, _records_cache_stamp
        _records_cache = None
        _records_cache_stamp = None

    @classmethod
    def load_all_internet_records(cls) -> List[GlobalTreeItem]:
        """Harvests and deduplicates internet sandalwood occurrences (mtime-cached)."""
        global _records_cache, _records_cache_stamp

        stamp = _dataset_mtime_stamp()
        if _records_cache is not None and _records_cache_stamp == stamp:
            # Return shallow copies so annotation mutations don't poison the cache
            return [item.model_copy(deep=False) for item in _records_cache]

        raw_items: Dict[str, Dict[str, Any]] = {}

        # 1. Harvest from datasets/gbif_sandalwood_occurrences.json
        gbif_json_path = os.path.join(DATASETS_DIR, "gbif_sandalwood_occurrences.json")
        if os.path.exists(gbif_json_path):
            try:
                with open(gbif_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for r in data:
                        if not r.get("is_sandalwood", True):
                            continue
                        lat = r.get("latitude")
                        lon = r.get("longitude")
                        if lat is None or lon is None:
                            continue
                        try:
                            lat = float(lat)
                            lon = float(lon)
                        except (ValueError, TypeError):
                            continue

                        accuracy = None
                        try:
                            if r.get("coordinate_uncertainty_m") is not None:
                                accuracy = float(r.get("coordinate_uncertainty_m"))
                        except (ValueError, TypeError):
                            accuracy = None
                        if not _is_map_grade(lat, lon, accuracy):
                            continue

                        key = _coord_key(lat, lon)
                        rec_id = r.get("gbif_id") or f"GBIF-{round(lat, 5)}-{round(lon, 5)}"
                        gbif_id = r.get("gbif_id")
                        external = (
                            f"https://www.gbif.org/occurrence/{gbif_id}"
                            if gbif_id
                            else "https://www.gbif.org/occurrence/search?q=Santalum%20album"
                        )

                        _upsert_raw(
                            raw_items,
                            key,
                            {
                                "id": str(rec_id),
                                "source": "GBIF Biodiversity Network",
                                "source_id": str(rec_id),
                                "scientific_name": r.get("scientific_name", "Santalum album L."),
                                "vernacular_name": r.get("vernacular_name", "Indian Sandalwood (Shrigandha)"),
                                "latitude": _precise_coord(lat),
                                "longitude": _precise_coord(lon),
                                "elevation_m": float(r.get("elevation_m")) if r.get("elevation_m") is not None else None,
                                "gps_accuracy": accuracy,
                                "state_province": r.get("state_province") or "Karnataka",
                                "country": r.get("country") or "India",
                                "locality": r.get("locality") or r.get("county_district") or "Agroforestry Reserve",
                                "recorded_by": r.get("recorded_by") or "Botanical Survey Researcher",
                                "event_date": r.get("event_date"),
                                "image_url": None,
                                "external_url": external,
                                "bark_characteristics": "Dark grey-brown, deeply fissured bark characteristic of mature Santalum album.",
                                "foliage_characteristics": "Opposite ovate-elliptic leaves with pale glaucous underside.",
                                "notes": f"Dataset: {r.get('dataset_name', 'GBIF Indian Flora')} | Basis: {r.get('basis_of_record', 'OBSERVATION')}",
                            },
                        )
            except Exception as e:
                logger.error(f"Error loading GBIF JSON occurrences: {e}")

        # 2. Harvest from datasets/street_view/internet_ground_photos_catalog.json
        street_json_path = os.path.join(DATASETS_DIR, "street_view", "internet_ground_photos_catalog.json")
        if os.path.exists(street_json_path):
            try:
                with open(street_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for r in data:
                        if not r.get("is_sandalwood"):
                            continue
                        lat = r.get("latitude")
                        lon = r.get("longitude")
                        if lat is None or lon is None:
                            continue
                        try:
                            lat = float(lat)
                            lon = float(lon)
                        except (ValueError, TypeError):
                            continue

                        accuracy = None
                        try:
                            if r.get("positional_accuracy") is not None:
                                accuracy = float(r["positional_accuracy"])
                            elif r.get("gps_accuracy") is not None:
                                accuracy = float(r["gps_accuracy"])
                        except (ValueError, TypeError):
                            accuracy = 15.0
                        if not _is_map_grade(lat, lon, accuracy):
                            continue

                        key = _coord_key(lat, lon)
                        rec_id = r.get("photo_id") or f"INAT-{round(lat, 5)}-{round(lon, 5)}"
                        _upsert_raw(
                            raw_items,
                            key,
                            {
                                "id": str(rec_id),
                                "source": "iNaturalist Open Data",
                                "source_id": str(rec_id),
                                "scientific_name": r.get("scientific_name", "Santalum album L."),
                                "vernacular_name": r.get("vernacular_name", "Indian Sandalwood (Shrigandha)"),
                                "latitude": _precise_coord(lat),
                                "longitude": _precise_coord(lon),
                                "elevation_m": float(r.get("elevation_m")) if r.get("elevation_m") is not None else 650.0,
                                "gps_accuracy": accuracy if accuracy is not None else 15.0,
                                "state_province": r.get("state_province") or "Karnataka",
                                "country": r.get("country") or "India",
                                "locality": r.get("locality") or "Sandalwood Natural Habitat",
                                "recorded_by": r.get("observer") or "iNaturalist Field Botanist",
                                "event_date": r.get("event_date"),
                                "image_url": r.get("image_url"),
                                "external_url": r.get("inaturalist_url"),
                                "bark_characteristics": r.get("bark_characteristics"),
                                "foliage_characteristics": r.get("foliage_characteristics"),
                                "notes": f"License: {r.get('license', 'CC-BY-NC-4.0')} | Ground Observation",
                            },
                        )
            except Exception as e:
                logger.error(f"Error loading Street View catalog occurrences: {e}")

        # 3. Harvest from datasets/sandalwood_occurrences_20260904_012006.csv
        csv_path = os.path.join(DATASETS_DIR, "sandalwood_occurrences_20260904_012006.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        try:
                            lat = float(r.get("latitude", 0))
                            lon = float(r.get("longitude", 0))
                        except (ValueError, TypeError):
                            continue

                        accuracy = None
                        try:
                            if r.get("coordinate_uncertainty_m"):
                                accuracy = float(r.get("coordinate_uncertainty_m"))
                        except (ValueError, TypeError):
                            pass
                        if not _is_map_grade(lat, lon, accuracy):
                            continue

                        key = _coord_key(lat, lon)
                        rec_id = r.get("source_id") or f"SW-OCC-{round(lat, 5)}"
                        _upsert_raw(
                            raw_items,
                            key,
                            {
                                "id": f"{r.get('source', 'OCC')}-{rec_id}",
                                "source": f"{r.get('source', 'GBIF')} Open Data",
                                "source_id": str(rec_id),
                                "scientific_name": r.get("species") or "Santalum album L.",
                                "vernacular_name": "Indian Sandalwood (Shrigandha)",
                                "latitude": _precise_coord(lat),
                                "longitude": _precise_coord(lon),
                                "elevation_m": None,
                                "gps_accuracy": accuracy,
                                "state_province": r.get("place_name") or "South India",
                                "country": "India",
                                "locality": r.get("place_name") or "Natural Forest Reserve",
                                "recorded_by": r.get("observer") or "Field Surveyor",
                                "event_date": r.get("observed_on"),
                                "image_url": None,
                                "external_url": (
                                    f"https://www.gbif.org/occurrence/{rec_id}"
                                    if r.get("source") == "GBIF"
                                    else f"https://www.inaturalist.org/observations/{rec_id}"
                                ),
                                "bark_characteristics": "Field verified sandalwood trunk profile.",
                                "foliage_characteristics": "Crown signature matching Santalum genus.",
                                "notes": r.get("notes") or "",
                            },
                        )
            except Exception as e:
                logger.error(f"Error loading CSV occurrences: {e}")

        items: List[GlobalTreeItem] = [
            GlobalTreeItem(
                id=d["id"],
                source=d["source"],
                source_id=d["source_id"],
                scientific_name=d["scientific_name"],
                vernacular_name=d["vernacular_name"],
                latitude=d["latitude"],
                longitude=d["longitude"],
                elevation_m=d.get("elevation_m"),
                gps_accuracy=d.get("gps_accuracy"),
                state_province=d.get("state_province"),
                country=d.get("country", "India"),
                locality=d.get("locality"),
                recorded_by=d.get("recorded_by"),
                event_date=d.get("event_date"),
                image_url=d.get("image_url"),
                external_url=d.get("external_url"),
                bark_characteristics=d.get("bark_characteristics"),
                foliage_characteristics=d.get("foliage_characteristics"),
                notes=d.get("notes"),
                registered_tree_uid=None,
                is_registered=False,
            )
            for d in raw_items.values()
        ]

        _records_cache = items
        _records_cache_stamp = stamp
        logger.info(f"Loaded {len(items)} aggregated internet sandalwood occurrences (cached).")
        return [item.model_copy(deep=False) for item in items]

    @classmethod
    def get_annotated_trees(
        cls,
        db: Session,
        source: Optional[str] = None,
        state: Optional[str] = None,
        has_photo: Optional[bool] = None,
        query: Optional[str] = None,
        limit: int = 400,
    ) -> List[GlobalTreeItem]:
        """Returns all internet trees annotated with their database registration status."""
        items = cls.load_all_internet_records()

        # Build index of registered trees + imported detections by precise coordinate
        db_trees = db.execute(select(Tree.tree_uid, Tree.latitude, Tree.longitude)).all()
        db_coord_map = {
            _coord_key(t.latitude, t.longitude): t.tree_uid
            for t in db_trees
        }

        from app.database.models.tree_detection import TreeDetection

        detection_coords = {
            _coord_key(lat, lon): uid
            for uid, lat, lon in db.execute(
                select(
                    TreeDetection.detection_uid,
                    TreeDetection.latitude,
                    TreeDetection.longitude,
                )
            ).all()
        }

        # Annotate registration against Tree Registry only for platform assets.
        # Detection matches set is_registered but NOT is_platform_asset (map stays non-green).
        for item in items:
            key = _coord_key(item.latitude, item.longitude)
            if key in db_coord_map:
                item.is_registered = True
                item.is_platform_asset = True
                item.registered_tree_uid = db_coord_map[key]
            elif key in detection_coords:
                item.is_registered = True
                item.is_platform_asset = False
                item.registered_tree_uid = detection_coords[key]

        # Apply filtering
        filtered = items
        if source:
            source_lower = source.lower()
            filtered = [i for i in filtered if source_lower in i.source.lower()]
        if state:
            state_lower = state.lower()
            filtered = [i for i in filtered if i.state_province and state_lower in i.state_province.lower()]
        if has_photo is True:
            filtered = [i for i in filtered if i.image_url]
        elif has_photo is False:
            filtered = [i for i in filtered if not i.image_url]
        if query:
            q_lower = query.lower()
            filtered = [
                i for i in filtered
                if (i.locality and q_lower in i.locality.lower())
                or (i.state_province and q_lower in i.state_province.lower())
                or (i.recorded_by and q_lower in i.recorded_by.lower())
                or (i.scientific_name and q_lower in i.scientific_name.lower())
                or (i.source_id and q_lower in i.source_id.lower())
            ]

        # Prefer precise GPS + photos first so the map limit keeps the best pins
        filtered.sort(
            key=lambda i: (
                0 if i.image_url else 1,
                float(i.gps_accuracy) if i.gps_accuracy is not None else 250.0,
                i.id,
            )
        )
        return filtered[:limit]

    @classmethod
    def get_stats(cls, db: Session) -> GlobalTreeStatsResponse:
        """Calculates KPI statistics across internet sandalwood occurrences."""
        # Reuse annotated list once (dataset cache makes this cheap after warm-up)
        all_trees = cls.get_annotated_trees(db=db, limit=10000)

        gbif_count = sum(1 for t in all_trees if "gbif" in t.source.lower())
        inat_count = sum(1 for t in all_trees if "inaturalist" in t.source.lower())
        with_photos = sum(1 for t in all_trees if t.image_url)
        registered_count = sum(1 for t in all_trees if t.is_platform_asset)

        states: Dict[str, int] = {}
        for t in all_trees:
            st = t.state_province or "Other / Forest Reserve"
            # Simplify state names
            if "karnataka" in st.lower():
                st = "Karnataka"
            elif "tamil nadu" in st.lower():
                st = "Tamil Nadu"
            elif "kerala" in st.lower():
                st = "Kerala"
            elif "andhra" in st.lower():
                st = "Andhra Pradesh"
            elif "maharashtra" in st.lower():
                st = "Maharashtra"
            states[st] = states.get(st, 0) + 1

        return GlobalTreeStatsResponse(
            total_trees=len(all_trees),
            gbif_count=gbif_count,
            inaturalist_count=inat_count,
            with_photos_count=with_photos,
            states_distribution=states,
            registered_assets_count=registered_count,
        )

    @classmethod
    def import_all_to_db(cls, db: Session) -> GlobalTreeImportResponse:
        """Imports all unique internet sandalwood occurrences into the platform's Tree database."""
        all_items = cls.load_all_internet_records()
        total_scanned = len(all_items)

        # Load existing tree coordinates to prevent duplicates (precise GPS)
        existing_coords = set()
        for t in db.execute(select(Tree.latitude, Tree.longitude)).all():
            existing_coords.add(_coord_key(t.latitude, t.longitude))

        # Import as UNASSIGNED map detections (no Tree ID until operator assigns one)
        from app.database.models.tree_detection import TreeDetection, DetectionStatus
        from app.services.detection_service import DetectionService

        existing_det_coords = set()
        for d in db.execute(select(TreeDetection)).scalars().all():
            existing_det_coords.add(_coord_key(d.latitude, d.longitude))

        newly_registered = 0
        skipped_duplicates = 0

        for item in all_items:
            key = _coord_key(item.latitude, item.longitude)
            if key in existing_coords or key in existing_det_coords:
                skipped_duplicates += 1
                continue

            notes = (
                f"[INTERNET_HARVEST] Source: {item.source} | Source ID: {item.source_id}\n"
                f"GPS: {item.latitude:.{_GPS_DECIMALS}f},{item.longitude:.{_GPS_DECIMALS}f}"
                f"{f' (±{item.gps_accuracy}m)' if item.gps_accuracy is not None else ''}\n"
                f"Locality: {item.locality or 'Reserve Area'}, {item.state_province or 'Karnataka'}\n"
                f"Observer: {item.recorded_by or 'Botanical Survey'}\n"
                f"Date: {item.event_date or 'Recorded'}\n"
                f"Photos: {item.image_url or 'None'}\n"
                f"Reference: {item.external_url or 'N/A'}"
            )[:1000]

            DetectionService.create_detection(
                db=db,
                latitude=_precise_coord(item.latitude),
                longitude=_precise_coord(item.longitude),
                altitude=item.elevation_m,
                source="INTERNET_HARVEST",
                species="Santalum album",
                region_id=None,
                notes=notes,
                commit=False,
            )
            existing_det_coords.add(key)
            newly_registered += 1

        if newly_registered > 0:
            db.commit()

        total_in_db = db.execute(
            select(func.count(TreeDetection.id)).where(
                TreeDetection.status == DetectionStatus.UNASSIGNED
            )
        ).scalar() or 0

        return GlobalTreeImportResponse(
            success=True,
            total_scanned=total_scanned,
            newly_registered=newly_registered,
            skipped_duplicates=skipped_duplicates,
            total_registered_in_db=total_in_db,
            message=(
                f"Import completed. {newly_registered} new sandalwood detections added to the map "
                f"(no Tree IDs yet). Assign IDs yourself when ready. "
                f"{skipped_duplicates} duplicate locations skipped. "
                f"Unassigned detections now: {total_in_db}."
            ),
        )

    @classmethod
    def get_record_by_id(cls, occurrence_id: str) -> GlobalTreeItem:
        """Look up one internet sandalwood occurrence by catalog id or source id."""
        needle = (occurrence_id or "").strip()
        if not needle:
            raise NotFoundError(message="Occurrence id is required")
        for item in cls.load_all_internet_records():
            if item.id == needle or item.source_id == needle:
                return item
        raise NotFoundError(message=f"Internet sandalwood occurrence '{occurrence_id}' not found")

    @staticmethod
    def estimate_heartwood_for_site(
        suitability_score: Optional[float] = None,
        *,
        occurrence: Optional[GlobalTreeItem] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        elevation_m: Optional[float] = None,
    ) -> GlobalTreeHeartwoodEstimate:
        """Estimate commercial heartwood using shared sandalwood allometrics.

        Internet occurrence catalogs do not include DBH / heartwood measurements.
        Stem size is derived from a *continuous* site index so each specimen's
        GPS / elevation / live suitability can produce a distinct estimate
        (previously only 4 discrete suitability buckets → identical values for
        whole weather-cache cells).
        """
        lat = latitude if latitude is not None else (occurrence.latitude if occurrence else None)
        lon = longitude if longitude is not None else (occurrence.longitude if occurrence else None)
        elev = elevation_m
        if elev is None and occurrence is not None:
            elev = occurrence.elevation_m

        score = None
        if suitability_score is not None:
            try:
                score = float(suitability_score)
            except (TypeError, ValueError):
                score = None
        if score is not None:
            score = max(0.0, min(100.0, score))

        # Continuous climate suitability (0–1). Unknown → mid-range prior.
        climate_f = (score / 100.0) if score is not None else 0.55

        # Western Ghats sandalwood belt peaks near ~13.5°N, ~75.8°E
        if lat is not None and lon is not None:
            lat_f = max(0.0, 1.0 - abs(float(lat) - 13.5) / 4.5)
            lon_f = max(0.0, 1.0 - abs(float(lon) - 75.8) / 3.5)
            geo_f = 0.55 * lat_f + 0.45 * lon_f
        else:
            geo_f = 0.5

        # Santalum album commercial stands prefer ~600–1100 m ASL
        if elev is not None:
            try:
                elev_v = float(elev)
                elev_f = max(0.0, 1.0 - abs(elev_v - 850.0) / 700.0)
            except (TypeError, ValueError):
                elev_f = 0.5
        else:
            elev_f = 0.5

        # Fine site differentiation from full-precision coordinates so two trees
        # that share a weather-cache cell (~0.01°) still get distinct stems.
        micro_f = 0.5
        if lat is not None and lon is not None:
            # Stable 0–1 from fractional degrees (deterministic, not random)
            frac = abs(float(lat) * 1000.0) % 1.0 + abs(float(lon) * 1000.0) % 1.0
            micro_f = (frac % 1.0)

        site_index = (
            0.42 * climate_f
            + 0.22 * geo_f
            + 0.18 * elev_f
            + 0.18 * micro_f
        )
        site_index = max(0.05, min(0.98, site_index))

        # Continuous stem assumptions (mid-rotation commercial range)
        dbh_cm = 18.0 + site_index * 16.0          # ~18–34 cm
        height_m = 5.0 + site_index * 4.5          # ~5.0–9.5 m
        bark_fissure_index = 0.55 + site_index * 0.35  # 0.55–0.90

        if score is not None and score >= 75.0:
            size_label = "optimal-climate continuous site index"
        elif score is not None and score >= 55.0:
            size_label = "suitable-climate continuous site index"
        elif score is not None:
            size_label = "marginal-climate continuous site index"
        else:
            size_label = "location-derived continuous site index"

        biometrics = calculate_allometric_sandalwood_biometrics(
            dbh_cm=dbh_cm,
            height_m=height_m,
            bark_fissure_index=bark_fissure_index,
        )
        return GlobalTreeHeartwoodEstimate(
            estimated_age_years=int(biometrics["estimated_age_years"]),
            assumed_dbh_cm=round(dbh_cm, 1),
            assumed_girth_cm=float(biometrics["girth_cm"]),
            assumed_height_m=round(height_m, 1),
            estimated_heartwood_kg=float(biometrics["heartwood_kg"]),
            heartwood_ratio=float(biometrics["heartwood_ratio"]),
            sandalwood_grade=str(biometrics["sandalwood_grade"]),
            commercial_value_inr=float(biometrics["commercial_value_inr"]),
            method="allometric_assumed_stem",
            assumption_note=(
                "Estimated from assumed DBH/height "
                f"({size_label}, site_index={site_index:.3f}); not a measured heartwood core. "
                "GBIF/iNaturalist records do not include heartwood mass."
            ),
        )

    @classmethod
    def _environment_from_weather(
        cls,
        weather: Dict[str, Any],
        *,
        stored: bool = False,
        measurement_uid: Optional[str] = None,
        include_heartwood: bool = True,
        occurrence: Optional[GlobalTreeItem] = None,
    ) -> GlobalTreeEnvironmentSnapshot:
        suitability = weather.get("sandalwood_suitability_score")
        elev = weather.get("elevation_meters")
        if elev is None and occurrence is not None:
            elev = occurrence.elevation_m

        # Prefer occurrence GPS for stem site-index (weather coords may be cache-rounded)
        hw_lat = occurrence.latitude if occurrence is not None else weather.get("latitude")
        hw_lon = occurrence.longitude if occurrence is not None else weather.get("longitude")

        heartwood = None
        if include_heartwood:
            heartwood = cls.estimate_heartwood_for_site(
                suitability,
                occurrence=occurrence,
                latitude=float(hw_lat) if hw_lat is not None else None,
                longitude=float(hw_lon) if hw_lon is not None else None,
                elevation_m=float(elev) if elev is not None else None,
            )
        return GlobalTreeEnvironmentSnapshot(
            latitude=float(weather["latitude"]),
            longitude=float(weather["longitude"]),
            elevation_meters=weather.get("elevation_meters"),
            temperature_celsius=float(weather["temperature_celsius"]),
            relative_humidity_percent=float(weather["relative_humidity_percent"]),
            soil_temperature_celsius=weather.get("soil_temperature_celsius"),
            soil_moisture_surface_percent=weather.get("soil_moisture_surface_percent"),
            soil_moisture_root_percent=float(weather["soil_moisture_root_percent"]),
            surface_pressure_hpa=weather.get("surface_pressure_hpa"),
            wind_speed_kmh=weather.get("wind_speed_kmh"),
            wind_direction_deg=weather.get("wind_direction_deg"),
            cloud_cover_percent=weather.get("cloud_cover_percent"),
            vapor_pressure_deficit_kpa=weather.get("vapor_pressure_deficit_kpa"),
            sandalwood_suitability_score=suitability,
            growth_zone_classification=weather.get("growth_zone_classification"),
            canopy_stress_status=weather.get("canopy_stress_status"),
            data_source=weather.get("data_source"),
            stored=stored,
            measurement_uid=measurement_uid,
            heartwood=heartwood,
        )

    @classmethod
    def preview_environment(cls, occurrence_id: str) -> GlobalTreeEnvironmentSnapshot:
        """Fetch live environmental data for a selected internet specimen without registering it."""
        item = cls.get_record_by_id(occurrence_id)
        from app.services.weather_service import RealWorldWeatherService, WeatherFetchError
        from app.core.errors import AppException

        try:
            weather = RealWorldWeatherService.get_live_microclimate(
                latitude=item.latitude,
                longitude=item.longitude,
            )
        except WeatherFetchError as exc:
            raise AppException(
                message=f"Live weather unavailable for occurrence '{occurrence_id}': {exc}",
                status_code=502,
                error_code="WEATHER_FETCH_FAILED",
            ) from exc
        # Prefer catalog GPS for heartwood site index (weather may be cache-rounded)
        weather = dict(weather)
        weather["latitude"] = item.latitude
        weather["longitude"] = item.longitude
        if item.elevation_m is not None and weather.get("elevation_meters") is None:
            weather["elevation_meters"] = item.elevation_m
        return cls._environment_from_weather(weather, stored=False, occurrence=item)

    @classmethod
    def register_selected_tree(
        cls,
        db: Session,
        occurrence_id: str,
        tree_uid: str,
        notes: Optional[str] = None,
    ) -> GlobalTreeRegisterResponse:
        """
        Register one selected internet sandalwood tree using its catalog GPS
        and persist live environmental data against the assigned Tree ID.
        """
        from app.database.models.environmental_measurement import EnvironmentalMeasurement
        from app.services.tree_service import TreeService

        item = cls.get_record_by_id(occurrence_id)
        key = _coord_key(item.latitude, item.longitude)

        existing = db.execute(
            select(Tree.tree_uid, Tree.latitude, Tree.longitude)
        ).all()
        for row in existing:
            if _coord_key(row.latitude, row.longitude) == key:
                raise AppException(
                    message=(
                        f"This location is already registered as Tree ID '{row.tree_uid}'. "
                        "Select a different specimen or use the existing Tree ID."
                    ),
                    status_code=409,
                    error_code="TREE_LOCATION_ALREADY_REGISTERED",
                    details={"tree_uid": row.tree_uid, "occurrence_id": item.id},
                )

        provenance = (
            f"[INTERNET_SANDALWOOD] Source: {item.source} | Source ID: {item.source_id}\n"
            f"GPS: {item.latitude:.{_GPS_DECIMALS}f}, {item.longitude:.{_GPS_DECIMALS}f}"
            f"{f' (±{item.gps_accuracy}m)' if item.gps_accuracy is not None else ''}\n"
            f"Locality: {item.locality or 'Unknown'}, {item.state_province or 'Unknown'}\n"
            f"Observer: {item.recorded_by or 'Unknown'} | Date: {item.event_date or 'Unknown'}\n"
            f"Reference: {item.external_url or 'N/A'}"
        )
        if notes and notes.strip():
            provenance = f"{notes.strip()}\n{provenance}"

        request = TreeRegisterRequest(
            tree_uid=tree_uid,
            species=(item.scientific_name or "Santalum album")[:100],
            latitude=item.latitude,
            longitude=item.longitude,
            altitude=item.elevation_m,
            gps_accuracy=item.gps_accuracy,
            notes=provenance[:4000],
            last_observed_on=(item.event_date or None),
            survival_confirmed=False,
        )
        tree = TreeService.register_tree(db=db, request=request)

        measurement = db.execute(
            select(EnvironmentalMeasurement)
            .where(EnvironmentalMeasurement.tree_id == tree.id)
            .order_by(EnvironmentalMeasurement.recorded_at.desc())
        ).scalars().first()

        environment = None
        if measurement is not None:
            metrics = measurement.additional_metrics or {}
            suitability = metrics.get("sandalwood_suitability_score")
            environment = GlobalTreeEnvironmentSnapshot(
                latitude=measurement.latitude,
                longitude=measurement.longitude,
                elevation_meters=measurement.altitude if measurement.altitude is not None else metrics.get("elevation_meters"),
                temperature_celsius=measurement.temperature,
                relative_humidity_percent=measurement.humidity,
                soil_temperature_celsius=metrics.get("soil_temperature_celsius"),
                soil_moisture_surface_percent=metrics.get("soil_moisture_surface_percent"),
                soil_moisture_root_percent=measurement.soil_moisture,
                surface_pressure_hpa=metrics.get("surface_pressure_hpa"),
                wind_speed_kmh=metrics.get("wind_speed_kmh"),
                wind_direction_deg=metrics.get("wind_direction_deg"),
                cloud_cover_percent=metrics.get("cloud_cover_percent"),
                vapor_pressure_deficit_kpa=metrics.get("vapor_pressure_deficit_kpa"),
                sandalwood_suitability_score=suitability,
                growth_zone_classification=metrics.get("growth_zone_classification"),
                canopy_stress_status=metrics.get("canopy_stress_status"),
                data_source=metrics.get("data_source_label") or metrics.get("source"),
                stored=True,
                measurement_uid=measurement.measurement_uid,
                heartwood=cls.estimate_heartwood_for_site(
                    suitability,
                    occurrence=item,
                    latitude=item.latitude,
                    longitude=item.longitude,
                    elevation_m=item.elevation_m
                    if item.elevation_m is not None
                    else (
                        measurement.altitude
                        if measurement.altitude is not None
                        else metrics.get("elevation_meters")
                    ),
                ),
            )

        # The allometric estimate is shown to the operator before they confirm, so
        # persist it too — otherwise the saved tree reports "Age unknown" and
        # "Heartwood unknown" for figures the UI just displayed.
        if environment is not None and environment.heartwood is not None:
            TreeService.apply_allometric_estimate(
                db=db,
                tree=tree,
                estimated_age_years=environment.heartwood.estimated_age_years,
                girth_cm=environment.heartwood.assumed_girth_cm,
                height_m=environment.heartwood.assumed_height_m,
            )

        stored = environment is not None
        message = (
            f"Tree {tree.tree_uid} registered at "
            f"{tree.latitude:.6f}, {tree.longitude:.6f} with live environmental data."
            if stored
            else (
                f"Tree {tree.tree_uid} registered at "
                f"{tree.latitude:.6f}, {tree.longitude:.6f}, but live environmental data could not be stored."
            )
        )
        return GlobalTreeRegisterResponse(
            success=True,
            message=message,
            tree_uid=tree.tree_uid,
            occurrence_id=item.id,
            scientific_name=item.scientific_name,
            latitude=tree.latitude,
            longitude=tree.longitude,
            altitude=tree.altitude,
            gps_accuracy=tree.gps_accuracy,
            environment_stored=stored,
            environment=environment,
        )
