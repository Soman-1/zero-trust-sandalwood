"""Sandalwood Tree management, identification, registration, and spatial lookup service."""

import math
from typing import List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, func, update

from app.core.logging import logger
from app.core.errors import AppException, NotFoundError
from app.core.geo import validate_coordinates, haversine_distance
from app.database.models.tree import Tree, TreeStatus
from app.services.tree_assessment import (
    BIOMETRICS_ALLOMETRIC_ESTIMATE,
    BIOMETRICS_FIELD_MEASURED,
    resolved_age_years,
)
from app.database.models.region import Region, RegionStatus
from app.schemas.tree import TreeRegisterRequest, TreeUpdateRequest
from app.services.region_service import RegionService


class TreeService:
    """Service for Sandalwood tree registration, ID generation, and spatial tracking."""

    @staticmethod
    def extract_state_code(region: Region) -> str:
        """Extract Indian state code from region_id (e.g. REG-KA-SHIVAMOGGA → KA)."""
        parts = region.region_id.split("-")
        if len(parts) >= 2 and len(parts[1]) == 2 and parts[1].isalpha():
            return parts[1].upper()
        return "KA"

    @staticmethod
    def generate_next_tree_uid(db: Session, region: Region) -> str:
        """
        Generate the next sequential human-readable Tree ID.
        Format: KA-00001, KA-00002 (state code + zero-padded sequence).
        Sequence is per-state so Karnataka and Tamil Nadu counters stay independent.
        """
        state = TreeService.extract_state_code(region)
        # Count both new-format (KA-00001) and legacy (SW-KA-00001) IDs for that state
        like_new = f"{state}-%"
        like_legacy = f"SW-{state}-%"
        total_for_state = db.execute(
            select(func.count(Tree.id)).where(
                (Tree.tree_uid.like(like_new)) | (Tree.tree_uid.like(like_legacy))
            )
        ).scalar() or 0
        next_number = total_for_state + 1

        tree_uid = f"{state}-{next_number:05d}"

        while db.execute(select(Tree).where(Tree.tree_uid == tree_uid)).scalar_one_or_none():
            next_number += 1
            tree_uid = f"{state}-{next_number:05d}"

        return tree_uid

    @staticmethod
    def register_tree(
        db: Session,
        request: TreeRegisterRequest,
        registered_by_user_id: Optional[int] = None,
        registered_by_device_id: Optional[int] = None,
    ) -> Tree:
        """
        Register a sandalwood tree from its GPS and store live environmental data.
        A region or reserve polygon is not required.
        """
        if (request.evidence_origin or "").upper() == "SIMULATED":
            from app.core.errors import ValidationError
            raise ValidationError(
                message="Simulated detections cannot be written to the tree registry.",
                details={"evidence_origin": "SIMULATED"},
            )

        validate_coordinates(request.latitude, request.longitude)

        region = None
        if request.region_id is not None:
            region = RegionService.get_region_by_identifier(db, request.region_id)
            if region.status != RegionStatus.ACTIVE:
                raise AppException(
                    message=f"Target region '{region.region_id}' is inactive. Trees cannot be registered in inactive zones.",
                    status_code=400,
                    error_code="REGION_INACTIVE",
                )
            is_inside = RegionService.is_point_in_region(
                region=region,
                latitude=request.latitude,
                longitude=request.longitude,
            )
            if not is_inside:
                logger.warning(
                    f"Tree registration rejected: Point ({request.latitude}, {request.longitude}) "
                    f"is outside boundary of region '{region.region_id}'"
                )
                raise AppException(
                    message=(
                        f"Tree GPS coordinates ({request.latitude}, {request.longitude}) "
                        f"fall outside the monitored boundary of region '{region.region_id}'"
                    ),
                    status_code=400,
                    error_code="COORDINATE_OUTSIDE_REGION",
                    details={
                        "region_id": region.region_id,
                        "latitude": request.latitude,
                        "longitude": request.longitude,
                    },
                )

        # Operator-assigned Tree ID (must be unique)
        tree_uid = request.tree_uid
        existing = db.execute(select(Tree).where(Tree.tree_uid == tree_uid)).scalar_one_or_none()
        if existing:
            raise AppException(
                message=f"Tree ID '{tree_uid}' is already registered. Choose a different ID.",
                status_code=409,
                error_code="TREE_UID_ALREADY_EXISTS",
                details={"tree_uid": tree_uid},
            )

        # 5. Persist Tree
        tree = Tree(
            tree_uid=tree_uid,
            species=request.species,
            region_id=region.id if region else None,
            latitude=request.latitude,
            longitude=request.longitude,
            altitude=request.altitude,
            gps_accuracy=request.gps_accuracy,
            estimated_age_years=resolved_age_years(
                request.planting_year,
                request.estimated_age_years,
            ),
            planting_year=request.planting_year,
            girth_cm=request.girth_cm,
            height_m=request.height_m,
            biometrics_source=request.biometrics_source,
            host_notes=request.host_notes,
            last_observed_on=request.last_observed_on,
            survival_confirmed=(
                True if request.survival_confirmed is None else request.survival_confirmed
            ),
            status=request.status,
            notes=request.notes,
        )
        db.add(tree)
        db.commit()
        db.refresh(tree)

        logger.info(
            f"Successfully registered Sandalwood Tree '{tree.tree_uid}' "
            f"at coordinates ({tree.latitude}, {tree.longitude})"
        )

        # 6. Live area weather → store with this Tree ID
        try:
            from app.services.tree_environment_service import TreeEnvironmentService
            TreeEnvironmentService.capture_live_environment_for_tree(db=db, tree=tree)
        except Exception as exc:
            logger.warning(
                f"Tree '{tree.tree_uid}' registered but initial environment capture failed: {exc}"
            )

        return tree

    @staticmethod
    def apply_allometric_estimate(
        db: Session,
        tree: Tree,
        estimated_age_years: Optional[float],
        girth_cm: Optional[float],
        height_m: Optional[float],
    ) -> Tree:
        """Store modelled stem biometrics on a tree that has no field measurements.

        Used for occurrence-sourced trees where no survey exists. A tree already
        carrying FIELD_MEASURED values is left untouched.
        """
        if tree.biometrics_source == BIOMETRICS_FIELD_MEASURED:
            return tree

        tree.estimated_age_years = estimated_age_years
        tree.girth_cm = girth_cm
        tree.height_m = height_m
        tree.biometrics_source = BIOMETRICS_ALLOMETRIC_ESTIMATE
        db.commit()
        db.refresh(tree)
        logger.info(
            f"Tree '{tree.tree_uid}' stored allometric estimate "
            f"(age ~{estimated_age_years} yrs, girth {girth_cm} cm, height {height_m} m)"
        )
        return tree

    @staticmethod
    def get_tree_by_uid(db: Session, identifier: Union[str, int]) -> Tree:
        """Retrieve tree by unique tree_uid (e.g. 'KA-00001') or database ID."""
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            tree = db.get(Tree, int(identifier))
            if tree:
                return tree

        stmt = select(Tree).where(Tree.tree_uid == str(identifier))
        tree = db.execute(stmt).scalar_one_or_none()
        if not tree:
            raise NotFoundError(message=f"Sandalwood tree '{identifier}' not found")
        return tree

    @staticmethod
    def list_trees(
        db: Session,
        region_identifier: Optional[Union[str, int]] = None,
        status_filter: Optional[TreeStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Tree]:
        """List registered sandalwood trees with optional region and status filters."""
        stmt = select(Tree)

        if region_identifier is not None:
            region = RegionService.get_region_by_identifier(db, region_identifier)
            stmt = stmt.where(Tree.region_id == region.id)

        if status_filter is not None:
            stmt = stmt.where(Tree.status == status_filter)

        stmt = stmt.offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_tree(
        db: Session,
        identifier: Union[str, int],
        request: TreeUpdateRequest,
    ) -> Tree:
        """Update sandalwood tree physical attributes or health status."""
        tree = TreeService.get_tree_by_uid(db, identifier)

        if request.species is not None:
            tree.species = request.species
        if request.planting_year is not None:
            tree.planting_year = request.planting_year
        if request.estimated_age_years is not None or request.planting_year is not None:
            tree.estimated_age_years = resolved_age_years(
                tree.planting_year,
                request.estimated_age_years
                if request.estimated_age_years is not None
                else tree.estimated_age_years,
            )
        if request.girth_cm is not None:
            tree.girth_cm = request.girth_cm
        if request.height_m is not None:
            tree.height_m = request.height_m
        if request.biometrics_source is not None:
            tree.biometrics_source = request.biometrics_source
        elif request.girth_cm is not None or request.height_m is not None:
            # A survey measurement supersedes any allometric estimate.
            tree.biometrics_source = BIOMETRICS_FIELD_MEASURED
        if request.host_notes is not None:
            tree.host_notes = request.host_notes
        if request.last_observed_on is not None:
            tree.last_observed_on = request.last_observed_on
        if request.survival_confirmed is not None:
            tree.survival_confirmed = request.survival_confirmed
        if request.status is not None:
            tree.status = request.status
            tree.survival_confirmed = True
        if request.notes is not None:
            tree.notes = request.notes

        db.commit()
        db.refresh(tree)
        logger.info(f"Updated tree '{tree.tree_uid}'")
        return tree

    @staticmethod
    def find_nearby_trees(
        db: Session,
        latitude: float,
        longitude: float,
        radius_meters: float = 500.0,
        region_identifier: Optional[Union[str, int]] = None,
    ) -> List[Tuple[Tree, float]]:
        """
        Query sandalwood trees located within radius_meters of a GPS coordinate.
        Returns a list of (Tree, distance_in_meters) sorted by distance ascending.
        """
        validate_coordinates(latitude, longitude)

        # High-performance spatial bounding box pre-filter
        delta_lat = (radius_meters + 50.0) / 111320.0
        delta_lon = (radius_meters + 50.0) / (111320.0 * max(0.01, math.cos(math.radians(latitude))))
        min_lat, max_lat = latitude - delta_lat, latitude + delta_lat
        min_lon, max_lon = longitude - delta_lon, longitude + delta_lon

        stmt = select(Tree).where(
            Tree.latitude >= min_lat,
            Tree.latitude <= max_lat,
            Tree.longitude >= min_lon,
            Tree.longitude <= max_lon,
        )

        if region_identifier is not None:
            region = RegionService.get_region_by_identifier(db, region_identifier)
            stmt = stmt.where(Tree.region_id == region.id)

        candidate_trees = db.execute(stmt).scalars().all()
        results: List[Tuple[Tree, float]] = []

        for tree in candidate_trees:
            dist = haversine_distance(latitude, longitude, tree.latitude, tree.longitude)
            if dist <= radius_meters:
                results.append((tree, dist))

        # Sort closest first
        results.sort(key=lambda x: x[1])
        return results

    @staticmethod
    def decommission_tree(
        db: Session,
        identifier: Union[str, int],
        status_update: TreeStatus = TreeStatus.HARVESTED,
        reason: Optional[str] = None,
    ) -> Tree:
        """Mark sandalwood tree as HARVESTED or REMOVED."""
        tree = TreeService.get_tree_by_uid(db, identifier)
        tree.status = status_update
        if reason:
            tree.notes = f"{tree.notes}\n[DECOMMISSION]: {reason}" if tree.notes else f"[DECOMMISSION]: {reason}"
        db.commit()
        db.refresh(tree)
        logger.info(f"Tree '{tree.tree_uid}' status updated to {status_update}")
        return tree

    @staticmethod
    def _detach_tree_references(db: Session, tree_pk: int) -> None:
        """Keep history rows, but drop the foreign key before the tree is removed."""
        from app.database.models.alert import Alert
        from app.database.models.audit_log import AuditLog
        from app.database.models.environmental_measurement import EnvironmentalMeasurement
        from app.database.models.tree_detection import DetectionStatus, TreeDetection

        db.execute(
            update(EnvironmentalMeasurement)
            .where(EnvironmentalMeasurement.tree_id == tree_pk)
            .values(tree_id=None)
        )
        db.execute(update(Alert).where(Alert.tree_id == tree_pk).values(tree_id=None))
        db.execute(update(AuditLog).where(AuditLog.tree_id == tree_pk).values(tree_id=None))
        db.execute(
            update(TreeDetection)
            .where(TreeDetection.assigned_tree_id == tree_pk)
            .values(assigned_tree_id=None, status=DetectionStatus.UNASSIGNED)
        )

    @staticmethod
    def delete_tree(db: Session, identifier: Union[str, int]) -> str:
        """Permanently remove a registered tree from the ledger."""
        tree = TreeService.get_tree_by_uid(db, identifier)
        tree_uid = tree.tree_uid
        TreeService._detach_tree_references(db, tree.id)
        db.delete(tree)
        db.commit()
        logger.info(f"Tree '{tree_uid}' permanently deleted from registry")
        return tree_uid

    @staticmethod
    def fetch_and_register_external(db: Session, requested_by: Optional[int] = None) -> dict:
        """Fetch occurrences and store as unassigned map detections (no Tree IDs)."""
        from app.services.gbif_service import (
            fetch_gbif,
            fetch_inaturalist,
            deduplicate,
            match_region,
        )
        from app.services.detection_service import DetectionService
        from app.database.models.tree_detection import TreeDetection

        gbif_records = fetch_gbif(limit=100)
        inat_records = fetch_inaturalist(limit=100)
        all_records = gbif_records + inat_records
        total_fetched = len(all_records)
        unique_records = deduplicate(all_records)
        duplicates = total_fetched - len(unique_records)

        regions = db.execute(select(Region)).scalars().all()
        if not regions:
            raise AppException(message="No regions found in DB", status_code=500, error_code="NO_REGIONS")
        fallback = regions[0]

        existing = {
            f"{round(d.latitude, 4):.4f},{round(d.longitude, 4):.4f}"
            for d in db.execute(select(TreeDetection)).scalars().all()
        }
        for t in db.execute(select(Tree)).scalars().all():
            existing.add(f"{round(t.latitude, 4):.4f},{round(t.longitude, 4):.4f}")

        inserted = 0
        for occ in unique_records:
            key = f"{round(occ.latitude, 4):.4f},{round(occ.longitude, 4):.4f}"
            if key in existing:
                continue
            region = match_region(occ.latitude, occ.longitude, regions, fallback)
            if not region:
                continue
            DetectionService.create_detection(
                db=db,
                latitude=occ.latitude,
                longitude=occ.longitude,
                source=str(occ.source),
                species=occ.species or "Santalum album",
                region_id=region.id,
                notes=f"Source: {occ.source} | ID: {occ.source_id}",
                commit=False,
            )
            existing.add(key)
            inserted += 1
        db.commit()
        return {"total_fetched": total_fetched, "registered": inserted, "duplicates": duplicates}

    @staticmethod
    def update_status(db: Session, tree_uid: str, status: TreeStatus, reason: Optional[str] = None) -> Tree:
        """Update the status of a tree with optional reason."""
        tree = TreeService.get_tree_by_uid(db, tree_uid)
        tree.status = status
        tree.survival_confirmed = True
        if reason:
            tree.notes = f"{tree.notes}\n[STATUS UPDATE]: {reason}" if tree.notes else f"[STATUS UPDATE]: {reason}"
        db.commit()
        db.refresh(tree)
        logger.info(f"Tree '{tree.tree_uid}' status updated to {status}")
        return tree
