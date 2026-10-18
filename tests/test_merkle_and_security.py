"""Tests for RFC 6962 MerkleTree and AntiReplayValidator security engine."""

import time
import pytest
from app.core.merkle import MerkleTree
from app.core.anti_replay import AntiReplayValidator


def test_merkle_tree_empty():
    """Test MerkleTree behavior with zero leaves."""
    tree = MerkleTree([])
    assert tree.root == "0" * 64


def test_merkle_tree_single_leaf():
    """Test MerkleTree with single leaf."""
    leaf = "event_hash_1"
    tree = MerkleTree([leaf])
    assert tree.root != "0" * 64
    assert len(tree.root) == 64


def test_merkle_tree_proof_generation_and_verification():
    """Test generating and verifying Merkle audit proofs."""
    leaves = [f"audit_event_hash_{i}" for i in range(8)]
    tree = MerkleTree(leaves)
    root = tree.root

    for i, leaf in enumerate(leaves):
        proof = tree.get_proof(i)
        assert isinstance(proof, list)
        assert len(proof) == 3  # log2(8) = 3
        # Verify valid proof
        assert MerkleTree.verify_proof(leaf, proof, root) is True
        # Verify tampered leaf fails
        assert MerkleTree.verify_proof(leaf + "_tampered", proof, root) is False


def test_merkle_tree_odd_leaves():
    """Test MerkleTree with odd number of leaves."""
    leaves = ["leaf_1", "leaf_2", "leaf_3", "leaf_4", "leaf_5"]
    tree = MerkleTree(leaves)
    root = tree.root
    assert root != "0" * 64

    # Verify proof for last odd leaf
    proof = tree.get_proof(4)
    assert MerkleTree.verify_proof(leaves[4], proof, root) is True


def test_anti_replay_validator_fresh_request():
    """Test valid fresh timestamp and unique nonce."""
    validator = AntiReplayValidator(max_clock_skew_seconds=60)
    current_time = time.time()

    is_valid, err = validator.validate_request(
        request_timestamp=current_time,
        nonce="nonce_unique_1001",
        caller_id="DEV-NODE-01",
    )
    assert is_valid is True
    assert err is None


def test_anti_replay_validator_blocks_nonce_reuse():
    """Test that reusing the same nonce is rejected as a replay attack."""
    validator = AntiReplayValidator(max_clock_skew_seconds=60)
    current_time = time.time()

    # First use
    is_valid_1, _ = validator.validate_request(current_time, nonce="reused_nonce_2002")
    assert is_valid_1 is True

    # Second use (replay)
    is_valid_2, err_2 = validator.validate_request(current_time, nonce="reused_nonce_2002")
    assert is_valid_2 is False
    assert "Replay attack detected" in err_2


def test_anti_replay_validator_clock_skew():
    """Test rejecting timestamps outside tolerance window."""
    validator = AntiReplayValidator(max_clock_skew_seconds=30)
    old_time = time.time() - 300  # 5 minutes in the past

    is_valid, err = validator.validate_request(request_timestamp=old_time)
    assert is_valid is False
    assert "Clock skew" in err
