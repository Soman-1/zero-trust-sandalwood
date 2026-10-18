"""Cryptographic Merkle Tree implementation for audit ledger anchoring (RFC 6962 compliant)."""

import hashlib
from typing import List, Tuple, Dict, Any, Optional


class MerkleTree:
    """
    Cryptographic Binary Merkle Tree for batching audit events.
    Uses RFC 6962 domain separation (0x00 for leaves, 0x01 for internal nodes)
    to prevent second-preimage attacks.
    """

    LEAF_PREFIX = b"\x00"
    NODE_PREFIX = b"\x01"

    def __init__(self, leaves: Optional[List[str]] = None):
        self.raw_leaves: List[str] = leaves or []
        self.leaf_hashes: List[bytes] = []
        self.levels: List[List[bytes]] = []
        if self.raw_leaves:
            self._build_tree()

    @staticmethod
    def _hash_leaf(data: str) -> bytes:
        """Hash a leaf node with domain prefix 0x00."""
        hasher = hashlib.sha256()
        hasher.update(MerkleTree.LEAF_PREFIX)
        hasher.update(data.encode("utf-8"))
        return hasher.digest()

    @staticmethod
    def _hash_nodes(left: bytes, right: bytes) -> bytes:
        """Hash two child nodes with domain prefix 0x01."""
        hasher = hashlib.sha256()
        hasher.update(MerkleTree.NODE_PREFIX)
        hasher.update(left)
        hasher.update(right)
        return hasher.digest()

    def _build_tree(self) -> None:
        """Construct the complete binary Merkle tree from raw leaves."""
        self.leaf_hashes = [self._hash_leaf(leaf) for leaf in self.raw_leaves]
        self.levels = [self.leaf_hashes]

        if not self.leaf_hashes:
            return

        current_level = self.leaf_hashes
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If odd number of nodes, pair with itself (standard Merkle duplication)
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = self._hash_nodes(left, right)
                next_level.append(parent)
            self.levels.append(next_level)
            current_level = next_level

    @property
    def root(self) -> str:
        """Return the hex-encoded 32-byte Merkle root string."""
        if not self.levels or not self.levels[-1]:
            return "0" * 64
        return self.levels[-1][0].hex()

    def get_proof(self, index: int) -> List[Dict[str, str]]:
        """
        Generate cryptographic audit path (Merkle Proof) for the leaf at index.
        Returns a list of sibling nodes with direction: [{"position": "left"|"right", "hash": "hex"}].
        """
        if index < 0 or index >= len(self.raw_leaves):
            raise IndexError(f"Leaf index {index} out of bounds (total leaves: {len(self.raw_leaves)})")

        proof: List[Dict[str, str]] = []
        current_idx = index

        for level in self.levels[:-1]:
            is_right_child = current_idx % 2 == 1
            sibling_idx = current_idx - 1 if is_right_child else current_idx + 1

            if sibling_idx < len(level):
                sibling_hash = level[sibling_idx].hex()
                position = "left" if is_right_child else "right"
                proof.append({"position": position, "hash": sibling_hash})
            else:
                # Sibling was duplicated self
                self_hash = level[current_idx].hex()
                proof.append({"position": "right", "hash": self_hash})

            current_idx = current_idx // 2

        return proof

    @staticmethod
    def verify_proof(leaf_data: str, proof: List[Dict[str, str]], expected_root: str) -> bool:
        """
        Verify that a leaf belongs to a Merkle tree with the given root.
        """
        current_hash = MerkleTree._hash_leaf(leaf_data)

        for step in proof:
            position = step.get("position")
            if position not in ("left", "right"):
                return False
            sibling_bytes = bytes.fromhex(step["hash"])
            if position == "left":
                current_hash = MerkleTree._hash_nodes(sibling_bytes, current_hash)
            else:
                current_hash = MerkleTree._hash_nodes(current_hash, sibling_bytes)

        return current_hash.hex().lower() == expected_root.lower().replace("0x", "")
