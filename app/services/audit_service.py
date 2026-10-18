"""Audit trail ledger service with cryptographic hash chaining and blockchain anchoring."""

import hmac
import threading
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.config import settings
from app.core.logging import logger
from app.core.integrity import canonicalize_payload, canonical_matches_stored, seal_canonical
from app.core.merkle import MerkleTree
from app.database.models.audit_log import AuditLog
from app.schemas.audit import AuditChainVerifyResponse, BlockchainAnchorResponse

GENESIS_PREVIOUS_HASH = "0" * 64
_ledger_lock = threading.Lock()
_anchor_lock = threading.Lock()


class AuditService:
    """Zero Trust Cryptographic Audit Ledger & Blockchain Anchoring Service."""

    @staticmethod
    def compute_event_hash(
        event_type: str,
        actor_type: str,
        actor_id: Optional[str],
        action: str,
        description: str,
        event_payload: Optional[Dict[str, Any]],
        previous_hash: str,
        recorded_at: datetime,
        actor_user_id: Optional[int] = None,
        actor_device_id: Optional[int] = None,
        region_id: Optional[int] = None,
        tree_id: Optional[int] = None,
    ) -> str:
        """Calculate deterministic SHA-256 hash of the audit entry."""
        time_str = (
            recorded_at.astimezone(timezone.utc).isoformat()
            if recorded_at.tzinfo
            else recorded_at.replace(tzinfo=timezone.utc).isoformat()
        )
        payload_data = {
            "event_type": event_type,
            "actor_type": actor_type,
            "actor_id": str(actor_id) if actor_id is not None else "NONE",
            "actor_user_id": actor_user_id,
            "actor_device_id": actor_device_id,
            "region_id": region_id,
            "tree_id": tree_id,
            "action": action,
            "description": description,
            "payload": event_payload or {},
            "previous_hash": previous_hash,
            "recorded_at": time_str,
        }
        canonical_str = canonicalize_payload(payload_data)
        return seal_canonical(canonical_str)

    @staticmethod
    def record_event(
        db: Session,
        event_type: str,
        action: str,
        description: str,
        actor_type: str = "SYSTEM",
        actor_id: Optional[str] = None,
        actor_user_id: Optional[int] = None,
        actor_device_id: Optional[int] = None,
        region_id: Optional[int] = None,
        tree_id: Optional[int] = None,
        event_payload: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Appends an immutable, hash-chained record to the audit ledger.
        Fetches the previous event hash to construct an unbroken cryptographic chain.
        """
        with _ledger_lock:
            # Serialize appends so concurrent writers cannot fork previous_hash.
            stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
            try:
                stmt = stmt.with_for_update()
            except Exception:
                pass
            last_log = db.execute(stmt).scalar_one_or_none()
            previous_hash = last_log.event_hash if last_log else GENESIS_PREVIOUS_HASH

            now = datetime.now(timezone.utc)
            event_hash = AuditService.compute_event_hash(
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                action=action,
                description=description,
                event_payload=event_payload,
                previous_hash=previous_hash,
                recorded_at=now,
                actor_user_id=actor_user_id,
                actor_device_id=actor_device_id,
                region_id=region_id,
                tree_id=tree_id,
            )

            log_entry = AuditLog(
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                actor_user_id=actor_user_id,
                actor_device_id=actor_device_id,
                region_id=region_id,
                tree_id=tree_id,
                action=action,
                description=description,
                event_payload=event_payload,
                previous_hash=previous_hash,
                event_hash=event_hash,
                blockchain_status="LOCAL_ONLY",
                recorded_at=now,
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)

            logger.info(
                f"AUDIT LOG [{log_entry.event_type}]: {log_entry.action} by {log_entry.actor_type}:{log_entry.actor_id} "
                f"(Hash: {event_hash[:8]}... Prev: {previous_hash[:8]}...)"
            )
            return log_entry

    @staticmethod
    def verify_chain_integrity(db: Session) -> AuditChainVerifyResponse:
        """
        Iterates across the entire chronological audit trail, verifying:
        1. Correct previous_hash linking.
        2. Unbroken deterministic event_hash recalculation.
        Detects any unauthorized modification, deletion, or ledger tampering.
        """
        stmt = select(AuditLog).order_by(AuditLog.id.asc())
        logs = list(db.execute(stmt).scalars().all())

        if not logs:
            return AuditChainVerifyResponse(
                is_chain_valid=True,
                total_verified=0,
                genesis_hash=GENESIS_PREVIOUS_HASH,
                latest_hash=GENESIS_PREVIOUS_HASH,
                message="Audit ledger is empty. Chain is intact.",
            )

        expected_prev_hash = GENESIS_PREVIOUS_HASH

        for idx, entry in enumerate(logs):
            # 1. Check backward link
            if not hmac.compare_digest(entry.previous_hash, expected_prev_hash):
                logger.error(
                    f"LEDGER CHAIN BROKEN at index {idx} (UID: {entry.audit_uid})! "
                    f"Expected Prev: {expected_prev_hash}, Stored Prev: {entry.previous_hash}"
                )
                return AuditChainVerifyResponse(
                    is_chain_valid=False,
                    total_verified=idx,
                    broken_link_index=idx,
                    broken_event_uid=entry.audit_uid,
                    genesis_hash=logs[0].previous_hash,
                    latest_hash=entry.previous_hash,
                    message=f"Audit chain broken at record index {idx}: previous_hash mismatch.",
                )

            # 2. Recompute and verify event hash (keyed seal or older SHA-256)
            recomputed = AuditService.compute_event_hash(
                event_type=entry.event_type,
                actor_type=entry.actor_type,
                actor_id=entry.actor_id,
                action=entry.action,
                description=entry.description,
                event_payload=entry.event_payload,
                previous_hash=entry.previous_hash,
                recorded_at=entry.recorded_at,
                actor_user_id=entry.actor_user_id,
                actor_device_id=entry.actor_device_id,
                region_id=entry.region_id,
                tree_id=entry.tree_id,
            )
            time_str = (
                entry.recorded_at.astimezone(timezone.utc).isoformat()
                if entry.recorded_at.tzinfo
                else entry.recorded_at.replace(tzinfo=timezone.utc).isoformat()
            )
            legacy_canonical = canonicalize_payload({
                "event_type": entry.event_type,
                "actor_type": entry.actor_type,
                "actor_id": str(entry.actor_id) if entry.actor_id is not None else "NONE",
                "actor_user_id": entry.actor_user_id,
                "actor_device_id": entry.actor_device_id,
                "region_id": entry.region_id,
                "tree_id": entry.tree_id,
                "action": entry.action,
                "description": entry.description,
                "payload": entry.event_payload or {},
                "previous_hash": entry.previous_hash,
                "recorded_at": time_str,
            })
            if not canonical_matches_stored(entry.event_hash, legacy_canonical):
                logger.error(
                    f"AUDIT RECORD TAMPERED at index {idx} (UID: {entry.audit_uid})! "
                    f"Stored Hash: {entry.event_hash}, Recalculated: {recomputed}"
                )
                return AuditChainVerifyResponse(
                    is_chain_valid=False,
                    total_verified=idx,
                    broken_link_index=idx,
                    broken_event_uid=entry.audit_uid,
                    genesis_hash=logs[0].previous_hash,
                    latest_hash=entry.event_hash,
                    message=f"Audit record tampered at record index {idx}: event_hash mismatch.",
                )

            expected_prev_hash = entry.event_hash

        return AuditChainVerifyResponse(
            is_chain_valid=True,
            total_verified=len(logs),
            genesis_hash=logs[0].previous_hash,
            latest_hash=logs[-1].event_hash,
            message=f"Audit ledger integrity verified across {len(logs)} hash-chained records.",
        )

    @staticmethod
    def _mark_anchored(
        db: Session,
        logs: List[AuditLog],
        tx_hash: str,
    ) -> None:
        for log in logs:
            log.blockchain_tx = tx_hash or log.blockchain_tx
            log.blockchain_status = "ANCHORED"
        db.commit()

    @staticmethod
    def _reset_pending_to_local(db: Session, logs: List[AuditLog]) -> None:
        for log in logs:
            if log.blockchain_status == "PENDING":
                log.blockchain_status = "LOCAL_ONLY"
        db.commit()

    @staticmethod
    def anchor_to_blockchain(
        db: Session,
        batch_size: int = 50,
    ) -> BlockchainAnchorResponse:
        """
        Computes a cryptographic Merkle root over unanchored audit records
        and generates an immutable distributed ledger anchoring receipt.

        Uses PENDING + on-chain verify recovery so a mined tx that loses the
        DB commit (or times out waiting for a receipt) can still be finalized.
        """
        with _anchor_lock:
            return AuditService._anchor_to_blockchain_unlocked(db, batch_size)

    @staticmethod
    def _anchor_to_blockchain_unlocked(
        db: Session,
        batch_size: int,
    ) -> BlockchainAnchorResponse:
        from app.blockchain.contract import audit_contract

        now = datetime.now(timezone.utc)
        stmt = (
            select(AuditLog)
            .where(AuditLog.blockchain_status.in_(("LOCAL_ONLY", "PENDING")))
            .order_by(AuditLog.id.asc())
            .limit(batch_size)
        )
        try:
            stmt = stmt.with_for_update()
        except Exception:
            pass
        unanchored = list(db.execute(stmt).scalars().all())

        if not unanchored:
            return BlockchainAnchorResponse(
                success=False,
                batch_size=0,
                merkle_root="",
                tx_hash="",
                block_number=0,
                anchored_records=0,
                timestamp=now,
                message="No pending audit logs to anchor.",
                contract_address=settings.BLOCKCHAIN_CONTRACT_ADDRESS,
                chain_id=settings.BLOCKCHAIN_CHAIN_ID,
            )

        tree = MerkleTree([log.event_hash for log in unanchored])
        merkle_root = tree.root
        batch_len = len(unanchored)

        # Recovery: root may already be on-chain from a prior orphaned attempt.
        prior = audit_contract.verify_audit_batch(merkle_root)
        if prior.get("is_anchored"):
            tx_hash = prior.get("tx_hash") or ""
            AuditService._mark_anchored(db, unanchored, tx_hash)
            logger.info(
                f"Recovered {batch_len} audit records already on-chain. Merkle: {merkle_root[:10]}..."
            )
            return BlockchainAnchorResponse(
                success=True,
                batch_size=batch_len,
                merkle_root=merkle_root,
                tx_hash=tx_hash,
                block_number=int(prior.get("block_number") or 0),
                anchored_records=batch_len,
                timestamp=now,
                message=f"Recovered {batch_len} audit records already anchored on-chain.",
                contract_address=settings.BLOCKCHAIN_CONTRACT_ADDRESS,
                chain_id=settings.BLOCKCHAIN_CHAIN_ID,
            )

        for log in unanchored:
            log.blockchain_status = "PENDING"
        db.commit()

        receipt = audit_contract.record_audit_batch(
            merkle_root=merkle_root,
            batch_size=batch_len,
            description=f"Audit batch {batch_len} records",
        )

        if receipt.get("status") == "CONFIRMED" and receipt.get("tx_hash"):
            try:
                AuditService._mark_anchored(db, unanchored, receipt["tx_hash"])
            except Exception as exc:
                logger.error(f"DB commit after on-chain confirm failed: {exc}")
                # Leave PENDING; next call recovers via verify_audit_batch.
                return BlockchainAnchorResponse(
                    success=False,
                    batch_size=batch_len,
                    merkle_root=merkle_root,
                    tx_hash=receipt.get("tx_hash") or "",
                    block_number=int(receipt.get("block_number") or 0),
                    anchored_records=0,
                    timestamp=now,
                    message=(
                        "On-chain anchor confirmed but database update failed. "
                        "Retry to finalize ANCHORED status."
                    ),
                    contract_address=settings.BLOCKCHAIN_CONTRACT_ADDRESS,
                    chain_id=settings.BLOCKCHAIN_CHAIN_ID,
                )

            logger.info(
                f"Anchored {batch_len} audit records on-chain. "
                f"Merkle: {merkle_root[:10]}... Tx: {receipt['tx_hash'][:14]}..."
            )
            return BlockchainAnchorResponse(
                success=True,
                batch_size=batch_len,
                merkle_root=merkle_root,
                tx_hash=receipt["tx_hash"],
                block_number=int(receipt["block_number"]),
                anchored_records=batch_len,
                timestamp=now,
                message=(
                    f"Successfully anchored {batch_len} audit records "
                    f"to blockchain transaction {receipt['tx_hash']}."
                ),
                contract_address=settings.BLOCKCHAIN_CONTRACT_ADDRESS,
                chain_id=settings.BLOCKCHAIN_CHAIN_ID,
            )

        # Timed-out / failed send: check whether the root still landed on-chain.
        recovered = audit_contract.verify_audit_batch(merkle_root)
        if recovered.get("is_anchored"):
            tx_hash = recovered.get("tx_hash") or receipt.get("tx_hash") or ""
            AuditService._mark_anchored(db, unanchored, tx_hash)
            logger.info(f"Recovered on-chain anchor after uncertain receipt for {merkle_root[:10]}...")
            return BlockchainAnchorResponse(
                success=True,
                batch_size=batch_len,
                merkle_root=merkle_root,
                tx_hash=tx_hash,
                block_number=int(recovered.get("block_number") or receipt.get("block_number") or 0),
                anchored_records=batch_len,
                timestamp=now,
                message=f"Recovered {batch_len} audit records after uncertain receipt.",
                contract_address=settings.BLOCKCHAIN_CONTRACT_ADDRESS,
                chain_id=settings.BLOCKCHAIN_CHAIN_ID,
            )

        AuditService._reset_pending_to_local(db, unanchored)
        logger.warning("Audit batch not marked ANCHORED: chain receipt was not confirmed")
        return BlockchainAnchorResponse(
            success=False,
            batch_size=batch_len,
            merkle_root=merkle_root,
            tx_hash="",
            block_number=0,
            anchored_records=0,
            timestamp=now,
            message=receipt.get("message") or "Chain unavailable. Records remain LOCAL_ONLY.",
            contract_address=settings.BLOCKCHAIN_CONTRACT_ADDRESS,
            chain_id=settings.BLOCKCHAIN_CHAIN_ID,
        )

    @staticmethod
    def list_logs(
        db: Session,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[AuditLog], int]:
        """List audit records with filtering and pagination."""
        stmt = select(AuditLog)

        if event_type:
            stmt = stmt.where(AuditLog.event_type == event_type)

        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)

        if start_time:
            stmt = stmt.where(AuditLog.recorded_at >= start_time)

        if end_time:
            stmt = stmt.where(AuditLog.recorded_at <= end_time)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        stmt = stmt.order_by(AuditLog.recorded_at.desc()).offset(skip).limit(limit)
        logs = list(db.execute(stmt).scalars().all())

        return logs, total
