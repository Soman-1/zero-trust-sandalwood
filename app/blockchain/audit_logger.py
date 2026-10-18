"""Blockchain audit logger service for anchoring security events."""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.logging import logger
from app.database.models.audit_log import AuditLog
from app.blockchain.contract import AuditContract, audit_contract


class BlockchainAuditLogger:
    """Coordinates batching and anchoring of audit log records to the blockchain."""

    def __init__(self, contract: Optional[AuditContract] = None):
        self.contract = contract or audit_contract

    def anchor_pending_logs(
        self,
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Scan database for unanchored audit log records, compute Merkle root,
        and submit transaction to the blockchain contract.
        """
        from app.services.audit_service import AuditService

        result = AuditService.anchor_to_blockchain(db=db, batch_size=batch_size)
        return result

    def verify_onchain_evidence(self, merkle_root: str) -> Dict[str, Any]:
        """Verify proof of existence on the blockchain for a given Merkle root."""
        return self.contract.verify_audit_batch(merkle_root=merkle_root)


# Default logger instance
blockchain_audit_logger = BlockchainAuditLogger()
