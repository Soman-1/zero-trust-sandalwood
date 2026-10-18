"""Unit + Hardhat/web3.py integration tests for the blockchain audit layer.

Coverage goals:
- Solidity constraints mirror backend call shaping (batch size, description length)
- Live record + on-chain verify through AuditContract / Web3Client
- onlyOwner rejection when signer is not the deployer
- AuditService marks rows ANCHORED only after CONFIRMED receipts
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
web3 = pytest.importorskip("web3")
from web3 import Web3, HTTPProvider

from app.blockchain.contract import AuditContract, REGISTRY_ABI
from app.blockchain.web3_client import Web3Client
from app.core.merkle import MerkleTree
from app.services.audit_service import AuditService
from tests.blockchain_harness import (
    HARDHAT_ACCOUNT0_KEY,
    HARDHAT_ACCOUNT1_KEY,
    HARDHAT_CHAIN_ID,
    HARDHAT_RPC,
    compile_registry,
    deploy_registry,
    start_hardhat_node,
    stop_hardhat_node,
)

CONTRACT_SOL = (
    Path(__file__).resolve().parents[1] / "blockchain" / "contracts" / "SandalwoodAuditRegistry.sol"
)


# ---------------------------------------------------------------------------
# Unit / static alignment (no chain required)
# ---------------------------------------------------------------------------


def test_registry_abi_includes_record_and_verify():
    names = {item.get("name") for item in REGISTRY_ABI if item.get("type") == "function"}
    assert "recordAuditBatch" in names
    assert "verifyAuditBatch" in names
    assert "getTotalBatches" in names
    assert "transferOwnership" in names
    assert "owner" in names


def test_compiled_abi_matches_backend_function_selectors():
    artifact = compile_registry()
    compiled_fns = {
        item["name"]
        for item in artifact["abi"]
        if item.get("type") == "function"
    }
    backend_fns = {
        item["name"]
        for item in REGISTRY_ABI
        if item.get("type") == "function"
    }
    # Backend ABI must be a subset of the compiled contract surface.
    assert backend_fns.issubset(compiled_fns)


def test_solidity_batch_limits_align_with_api_schema():
    source = CONTRACT_SOL.read_text(encoding="utf-8")
    assert "_batchSize > 0 && _batchSize <= 500" in source
    assert 'bytes(_description).length <= 128' in source
    assert "onlyOwner" in source

    from app.schemas.audit import BlockchainAnchorRequest

    field = BlockchainAnchorRequest.model_fields["batch_size"]
    assert field.metadata  # Field constraints present via Annotated/Field
    # Reconstruct via a valid / invalid payload
    BlockchainAnchorRequest(batch_size=500)
    with pytest.raises(Exception):
        BlockchainAnchorRequest(batch_size=501)
    with pytest.raises(Exception):
        BlockchainAnchorRequest(batch_size=0)


def test_frontend_backend_anchor_response_field_alignment():
    """Verifies that all frontend required fields are supported by backend schema."""
    from app.schemas.audit import BlockchainAnchorResponse

    backend_fields = set(BlockchainAnchorResponse.model_fields.keys())
    frontend_fields = {
        "success",
        "records_anchored",
        "merkle_root",
        "contract_address",
        "transaction_hash",
        "chain_id",
        "anchored_at",
    }
    assert frontend_fields.issubset(backend_fields)


def test_default_chain_id_matches_hardhat_chain_id():
    """Config and Hardhat both align on chain ID 31337."""
    from app.core.config import settings

    assert settings.BLOCKCHAIN_CHAIN_ID == 31337
    assert HARDHAT_CHAIN_ID == 31337
    assert settings.BLOCKCHAIN_PRIVATE_KEY is None


def test_empty_anchor_batch_is_honest_noop(db_session):
    """Empty pending set must not fake zero merkle/tx proofs."""
    result = AuditService.anchor_to_blockchain(db=db_session, batch_size=10)
    assert result.success is False
    assert result.anchored_records == 0
    assert result.merkle_root == ""
    assert result.tx_hash == ""
    assert "No pending" in result.message


def test_utf8_description_truncates_by_bytes():
    from app.blockchain.contract import _truncate_utf8_bytes

    # 100 multibyte chars → >128 bytes; must not exceed Solidity byte limit.
    text = "你" * 100
    truncated = _truncate_utf8_bytes(text, 128)
    assert len(truncated.encode("utf-8")) <= 128


def test_deploy_py_supports_live_deploy():
    """blockchain/scripts/deploy.py contains live deployment capability."""
    deploy_src = (
        Path(__file__).resolve().parents[1] / "blockchain" / "scripts" / "deploy.py"
    ).read_text(encoding="utf-8")
    assert "send_raw_transaction" in deploy_src
    assert "wait_for_transaction_receipt" in deploy_src
    assert "BLOCKCHAIN_CONTRACT_ADDRESS" in deploy_src


# ---------------------------------------------------------------------------
# Live Hardhat + web3.py integration
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def hardhat_node():
    try:
        proc = start_hardhat_node()
    except Exception as exc:
        pytest.skip(f"Hardhat node unavailable: {exc}")
    yield proc
    stop_hardhat_node(proc)


@pytest.fixture
def live_registry(hardhat_node):
    w3 = Web3(HTTPProvider(HARDHAT_RPC, request_kwargs={"timeout": 60}))
    if not w3.is_connected():
        pytest.skip("Hardhat RPC not connected")
    try:
        address, _ = deploy_registry(w3, HARDHAT_ACCOUNT0_KEY)
    except Exception as exc:
        pytest.skip(f"Contract deploy via web3.py failed: {exc}")
    client = Web3Client(
        rpc_url=HARDHAT_RPC,
        chain_id=HARDHAT_CHAIN_ID,
        private_key=HARDHAT_ACCOUNT0_KEY,
    )
    if not client.is_connected:
        pytest.skip("Web3Client failed to connect to Hardhat")
    contract = AuditContract(contract_address=address, client=client)
    return {"w3": w3, "address": address, "client": client, "contract": contract}


def test_web3_record_and_onchain_verify(live_registry):
    contract: AuditContract = live_registry["contract"]
    merkle_root = MerkleTree(["evt-a", "evt-b", "evt-c"]).root

    receipt = contract.record_audit_batch(
        merkle_root=merkle_root,
        batch_size=3,
        description="web3-integration-batch",
    )
    assert receipt["status"] == "CONFIRMED"
    assert receipt["tx_hash"].startswith("0x")
    assert receipt["block_number"] is not None

    # Fresh contract instance with empty local cache — must hit eth_call
    fresh = AuditContract(
        contract_address=live_registry["address"],
        client=live_registry["client"],
    )
    verification = fresh.verify_audit_batch(merkle_root)
    assert verification["is_anchored"] is True
    assert verification["source"] == "onchain"
    assert verification["batch_size"] == 3
    assert verification["recorder"].lower() == Web3.to_checksum_address(
        "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    ).lower()


def test_web3_rejects_non_owner_signer(live_registry):
    stranger_client = Web3Client(
        rpc_url=HARDHAT_RPC,
        chain_id=HARDHAT_CHAIN_ID,
        private_key=HARDHAT_ACCOUNT1_KEY,
    )
    stranger = AuditContract(
        contract_address=live_registry["address"],
        client=stranger_client,
    )
    merkle_root = "0xabcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    receipt = stranger.record_audit_batch(merkle_root=merkle_root, batch_size=1, description="intruder")
    assert receipt["status"] == "UNAVAILABLE"
    assert "failed" in receipt["message"].lower() or "owner" in receipt["message"].lower()

    verification = live_registry["contract"].verify_audit_batch(merkle_root)
    assert verification["is_anchored"] is False


def test_web3_rejects_duplicate_root(live_registry):
    contract: AuditContract = live_registry["contract"]
    root = "0x3333333333333333333333333333333333333333333333333333333333333333"
    first = contract.record_audit_batch(root, 2, "once")
    assert first["status"] == "CONFIRMED"
    second = contract.record_audit_batch(root, 2, "twice")
    assert second["status"] == "UNAVAILABLE"


def test_web3_rejects_zero_and_oversize_batch(live_registry):
    contract: AuditContract = live_registry["contract"]
    root = "0x4444444444444444444444444444444444444444444444444444444444444444"
    zero_batch = contract.record_audit_batch(root, 0, "empty")
    assert zero_batch["status"] == "UNAVAILABLE"
    oversize = contract.record_audit_batch(
        "0x5555555555555555555555555555555555555555555555555555555555555555",
        501,
        "too-big",
    )
    assert oversize["status"] == "UNAVAILABLE"


def test_audit_service_anchors_db_rows_after_confirmed_tx(live_registry, db_session, monkeypatch):
    from app.blockchain import contract as contract_module

    monkeypatch.setattr(contract_module, "audit_contract", live_registry["contract"])

    log1 = AuditService.record_event(
        db=db_session,
        event_type="BC_LIVE_1",
        action="TEST",
        description="live anchor 1",
    )
    log2 = AuditService.record_event(
        db=db_session,
        event_type="BC_LIVE_2",
        action="TEST",
        description="live anchor 2",
    )
    assert log1.blockchain_status == "LOCAL_ONLY"
    assert log2.blockchain_status == "LOCAL_ONLY"

    result = AuditService.anchor_to_blockchain(db=db_session, batch_size=10)
    assert result.success is True
    assert result.anchored_records == 2
    assert result.tx_hash.startswith("0x")

    db_session.refresh(log1)
    db_session.refresh(log2)
    assert log1.blockchain_status == "ANCHORED"
    assert log2.blockchain_status == "ANCHORED"
    assert log1.blockchain_tx == result.tx_hash

    # On-chain evidence must match the Merkle root computed from event hashes
    verification = live_registry["contract"].verify_audit_batch(result.merkle_root)
    assert verification["is_anchored"] is True
    assert verification["source"] == "onchain"


def test_hardhat_artifact_roundtrip_if_compiled():
    """If `npm run compile` has been run, artifact ABI must include verifyAuditBatch."""
    artifact_path = (
        Path(__file__).resolve().parents[1]
        / "blockchain"
        / "artifacts"
        / "contracts"
        / "SandalwoodAuditRegistry.sol"
        / "SandalwoodAuditRegistry.json"
    )
    if not artifact_path.exists():
        pytest.skip("Hardhat artifacts not compiled yet")
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    names = {item.get("name") for item in artifact["abi"] if item.get("type") == "function"}
    assert "recordAuditBatch" in names
    assert "verifyAuditBatch" in names
