"""Pydantic schemas for Cryptographic Audit Ledger and Blockchain Anchoring."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, computed_field


class AuditLogResponse(BaseModel):
    """Public representation of an immutable audit record."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    audit_uid: str
    event_type: str
    actor_type: str
    actor_id: Optional[str]
    actor_user_id: Optional[int]
    actor_device_id: Optional[int]
    region_id: Optional[int]
    tree_id: Optional[int]
    action: str
    description: str
    event_payload: Optional[Dict[str, Any]]
    previous_hash: str
    event_hash: str
    blockchain_tx: Optional[str]
    blockchain_status: str
    recorded_at: datetime

    @computed_field
    def log_uid(self) -> str:
        return self.audit_uid

    @computed_field
    def record_hash(self) -> str:
        return self.event_hash

    @computed_field
    def blockchain_tx_hash(self) -> Optional[str]:
        return self.blockchain_tx

    @computed_field
    def action_detail(self) -> str:
        return self.description

    @computed_field
    def created_at(self) -> str:
        return self.recorded_at.isoformat()


class AuditChainVerifyResponse(BaseModel):
    """Cryptographic verification report for the audit ledger hash chain."""
    is_chain_valid: bool
    total_verified: int
    broken_link_index: Optional[int] = None
    broken_event_uid: Optional[str] = None
    message: str
    genesis_hash: Optional[str] = None
    latest_hash: Optional[str] = None

    @computed_field
    def total_records_checked(self) -> int:
        return self.total_verified


class BlockchainAnchorRequest(BaseModel):
    """Payload to trigger blockchain anchoring batch."""
    batch_size: int = Field(default=50, ge=1, le=500, description="Max audit logs to anchor in this batch")


class BlockchainAnchorResponse(BaseModel):
    """Cryptographic proof receipt of blockchain anchoring."""
    success: bool
    batch_size: int
    merkle_root: str
    tx_hash: str
    block_number: int
    anchored_records: int
    timestamp: datetime
    message: str
    contract_address: Optional[str] = None
    chain_id: Optional[int] = None
    records_anchored: Optional[int] = None
    transaction_hash: Optional[str] = None
    anchored_at: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.records_anchored is None:
            self.records_anchored = self.anchored_records
        if self.transaction_hash is None:
            self.transaction_hash = self.tx_hash
        if self.anchored_at is None:
            self.anchored_at = self.timestamp.isoformat()


class PaginatedAuditLogsResponse(BaseModel):
    """Paginated list of audit trail logs."""
    total: int
    skip: int
    limit: int
    logs: List[AuditLogResponse]
