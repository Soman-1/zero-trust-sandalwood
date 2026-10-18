"""Tests for the Blockchain evidence module and smart contract interface."""

import pytest
from app.blockchain.web3_client import Web3Client
from app.blockchain.contract import AuditContract
from app.blockchain.audit_logger import BlockchainAuditLogger
from app.database.seed import seed_initial_data


def test_web3_client_simulated_tx_generation():
    """Test deterministic transaction hash generation."""
    client = Web3Client()
    tx_hash = client.generate_simulated_tx_hash("sample-merkle-root")
    assert tx_hash.startswith("0x")
    assert len(tx_hash) == 66


def test_audit_contract_batch_recording_and_verification():
    """Test anchoring and verifying Merkle roots on the AuditContract wrapper."""
    contract = AuditContract()
    merkle_root = "0x8f3c7b2e1a4d9f6a5b8c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a"

    receipt = contract.record_audit_batch(
        merkle_root=merkle_root,
        batch_size=25,
        description="Daily Sandalwood Audit Batch #1",
    )

    assert receipt["status"] == "UNAVAILABLE"
    assert receipt["tx_hash"] is None
    assert receipt["batch_size"] == 25

    verification = contract.verify_audit_batch(merkle_root=merkle_root)
    assert verification["is_anchored"] is False


def test_blockchain_audit_logger_service(db_session):
    """Test full integration between audit records in DB and blockchain logger."""
    seed_initial_data(db_session)
    logger_service = BlockchainAuditLogger()

    result = logger_service.anchor_pending_logs(db=db_session, batch_size=50)
    assert result.anchored_records == 0
    assert result.success is False
    assert result.tx_hash == ""
    assert result.merkle_root == ""
    assert "No pending" in result.message


def test_empty_anchor_batch_is_honest_noop(db_session):
    from app.services.audit_service import AuditService

    result = AuditService.anchor_to_blockchain(db=db_session, batch_size=10)
    assert result.success is False
    assert result.anchored_records == 0
    assert result.merkle_root == ""
    assert result.tx_hash == ""
    assert "No pending" in result.message


def test_utf8_description_truncates_by_bytes():
    from app.blockchain.contract import _truncate_utf8_bytes

    text = "你" * 100
    truncated = _truncate_utf8_bytes(text, 128)
    assert len(truncated.encode("utf-8")) <= 128


def test_default_private_key_is_not_hardhat_account0():
    from app.core.config import settings

    assert settings.BLOCKCHAIN_PRIVATE_KEY is None
    assert settings.BLOCKCHAIN_CHAIN_ID == 31337
