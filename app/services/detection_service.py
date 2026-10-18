"""Manage map detections: located sandalwood without operator Tree IDs."""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from app.core.logging import logger
from app.core.errors import AppException, NotFoundError
from app.database.models.tree import Tree
from app.database.models.tree_detection import TreeDetection, DetectionStatus
from app.database.models.environmental_measurement import EnvironmentalMeasurement
from app.database.models.alert import Alert
from app.schemas.detection import DetectionAssignRequest
from app.schemas.tree import TreeRegisterRequest
from app.services.tree_service import TreeService


class DetectionService:
    """Unassigned detections on the map until an operator assigns a Tree ID."""

    @staticmethod
    def _next_detection_uid(db: Session) -> str:
        total = db.execute(select(func.count(TreeDetection.id))).scalar() or 0
        n = total + 1
        uid = f"DET-{n:05d}"
        while db.execute(select(TreeDetection).where(TreeDetection.detection_uid == uid)).scalar_one_or_none():
            n += 1
            uid = f"DET-{n:05d}"
        return uid

    @staticmethod
    def list_unassigned(db: Session, region_id: Optional[int] = None, limit: int = 2000) -> List[TreeDetection]:
        stmt = (
            select(TreeDetection)
            .where(TreeDetection.status == DetectionStatus.UNASSIGNED)
            .order_by(TreeDetection.id.asc())
            .limit(limit)
        )
        if region_id is not None:
            stmt = stmt.where(TreeDetection.region_id == region_id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_by_uid(db: Session, detection_uid: str) -> TreeDetection:
        det = db.execute(
            select(TreeDetection).where(TreeDetection.detection_uid == detection_uid)
        ).scalar_one_or_none()
        if not det:
            raise NotFoundError(message=f"Detection '{detection_uid}' not found")
        return det

    @staticmethod
    def create_detection(
        db: Session,
        *,
        latitude: float,
        longitude: float,
        source: str,
        species: str = "Santalum album",
        region_id: Optional[int] = None,
        confidence: Optional[float] = None,
        altitude: Optional[float] = None,
        notes: Optional[str] = None,
        commit: bool = True,
    ) -> TreeDetection:
        det = TreeDetection(
            detection_uid=DetectionService._next_detection_uid(db),
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            species=species,
            source=source,
            confidence=confidence,
            region_id=region_id,
            status=DetectionStatus.UNASSIGNED,
            notes=notes,
        )
        db.add(det)
        if commit:
            db.commit()
            db.refresh(det)
        else:
            db.flush()
        return det

    @staticmethod
    def assign_tree_id(
        db: Session,
        detection_uid: str,
        request: DetectionAssignRequest,
        registered_by_user_id: Optional[int] = None,
    ) -> Tuple[TreeDetection, object]:
        """Assign operator Tree ID → register tree + weather, mark detection ASSIGNED."""
        det = DetectionService.get_by_uid(db, detection_uid)
        if det.status == DetectionStatus.ASSIGNED:
            raise AppException(
                message=f"Detection '{detection_uid}' already has an assigned Tree ID",
                status_code=409,
                error_code="DETECTION_ALREADY_ASSIGNED",
            )

        tree = TreeService.register_tree(
            db=db,
            request=TreeRegisterRequest(
                tree_uid=request.tree_uid,
                region_id=request.region_id,
                species=request.species or det.species,
                latitude=det.latitude,
                longitude=det.longitude,
                altitude=det.altitude,
                estimated_age_years=request.estimated_age_years,
                girth_cm=request.girth_cm,
                height_m=request.height_m,
                notes=request.notes or det.notes,
            ),
            registered_by_user_id=registered_by_user_id,
        )

        det.status = DetectionStatus.ASSIGNED
        det.assigned_tree_id = tree.id
        db.commit()
        db.refresh(det)
        logger.info(
            f"Detection '{det.detection_uid}' assigned Tree ID '{tree.tree_uid}'"
        )
        return det, tree

    @staticmethod
    def migrate_legacy_registered_trees_to_detections(db: Session) -> int:
        """
        Move auto/legacy trees (SW-KA-*, GBIF-*, TREE-STREET-*) into unassigned
        detections and remove them from the registered trees table.
        Operator-style IDs (KA-01) are kept as registered trees.
        """
        trees = list(db.execute(select(Tree)).scalars().all())
        moved = 0
        for tree in trees:
            uid = tree.tree_uid.upper()
            is_operator_style = (
                len(uid) >= 4
                and uid[2] == "-"
                and uid[:2].isalpha()
                and uid[3:].isdigit()
                and not uid.startswith("SW-")
            )
            if is_operator_style:
                continue

            db.execute(delete(Alert).where(Alert.tree_id == tree.id))
            db.execute(
                delete(EnvironmentalMeasurement).where(
                    EnvironmentalMeasurement.tree_id == tree.id
                )
            )

            DetectionService.create_detection(
                db=db,
                latitude=tree.latitude,
                longitude=tree.longitude,
                altitude=tree.altitude,
                source="LEGACY_IMPORT",
                species=tree.species,
                region_id=tree.region_id,
                notes=(
                    f"Migrated from legacy tree record {tree.tree_uid}. "
                    f"{tree.notes or ''}"
                ).strip(),
                commit=False,
            )
            db.delete(tree)
            moved += 1

        db.commit()
        logger.info(f"Migrated {moved} legacy trees into unassigned map detections")
        return moved
