"""Cryptographic audit ledger and blockchain anchoring API endpoints."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models.user import User, UserRole
from app.schemas.audit import (
    AuditLogResponse,
    AuditChainVerifyResponse,
    BlockchainAnchorRequest,
    BlockchainAnchorResponse,
    PaginatedAuditLogsResponse,
)
from app.services.audit_service import AuditService
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/audit", tags=["Audit Trail & Blockchain"])


@router.get(
    "/logs",
    response_model=PaginatedAuditLogsResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Audit Ledger",
    description="Retrieves immutable hash-chained audit logs for Zero Trust compliance.",
)
def list_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> PaginatedAuditLogsResponse:
    logs, total = AuditService.list_logs(
        db=db,
        event_type=event_type,
        actor_id=actor_id,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit,
    )
    return PaginatedAuditLogsResponse(
        total=total,
        skip=skip,
        limit=limit,
        logs=[AuditLogResponse.model_validate(log) for log in logs],
    )


@router.get(
    "/verify-chain",
    response_model=AuditChainVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Audit Ledger Cryptographic Chain",
    description="Validates all SHA-256 links in the audit ledger backwards to genesis, detecting any unauthorized tampering.",
)
def verify_audit_chain(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> AuditChainVerifyResponse:
    return AuditService.verify_chain_integrity(db=db)


@router.post(
    "/blockchain-anchor",
    response_model=BlockchainAnchorResponse,
    status_code=status.HTTP_200_OK,
    summary="Anchor Audit Batch to Blockchain",
    description="Computes a Merkle root over pending audit records and anchors them to an immutable blockchain reference.",
)
def anchor_audit_batch(
    payload: BlockchainAnchorRequest = BlockchainAnchorRequest(),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> BlockchainAnchorResponse:
    return AuditService.anchor_to_blockchain(db=db, batch_size=payload.batch_size)


@router.get(
    "/blockchain-verify",
    status_code=status.HTTP_200_OK,
    summary="Verify Merkle Root On-Chain",
    description="Calls SandalwoodAuditRegistry.verifyAuditBatch for a Merkle root.",
)
def verify_blockchain_batch(
    merkle_root: str = Query(..., min_length=64, description="64-hex or 0x-prefixed Merkle root"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> dict:
    from app.blockchain.contract import audit_contract

    return audit_contract.verify_audit_batch(merkle_root=merkle_root)
