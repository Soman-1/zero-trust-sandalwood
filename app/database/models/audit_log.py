"""Audit log database model with cryptographic hash-chaining and blockchain anchoring."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class AuditLog(Base):
    """Immutable, cryptographically hash-chained audit ledger for Zero Trust security events."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audit_uid: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Actor References
    actor_type: Mapped[str] = mapped_column(String(20), default="SYSTEM", nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_device_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Context References
    region_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tree_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(String(100), default="EXECUTE", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Cryptographic Hash Chaining & Blockchain Anchoring
    previous_hash: Mapped[str] = mapped_column(
        String(64),
        default="0" * 64,
        nullable=False,
        index=True,
    )
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    blockchain_tx: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    blockchain_status: Mapped[str] = mapped_column(String(20), default="LOCAL_ONLY", nullable=False)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, uid='{self.audit_uid}', event='{self.event_type}', "
            f"actor='{self.actor_type}:{self.actor_id}', hash='{self.event_hash[:8]}...')>"
        )
