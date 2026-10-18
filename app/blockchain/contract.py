"""Smart contract interface for SandalwoodAuditRegistry."""

import re
import time
import threading
from typing import Any, Callable, Dict, Optional
from app.core.config import settings
from app.core.logging import logger
try:
    from web3 import Web3 as _Web3Check
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False

from app.blockchain.web3_client import Web3Client, web3_client

REGISTRY_ABI = [
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getTotalBatches",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_merkleRoot", "type": "bytes32"},
            {"internalType": "uint256", "name": "_batchSize", "type": "uint256"},
            {"internalType": "string", "name": "_description", "type": "string"},
        ],
        "name": "recordAuditBatch",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_merkleRoot", "type": "bytes32"}],
        "name": "verifyAuditBatch",
        "outputs": [
            {"internalType": "bool", "name": "isAnchored", "type": "bool"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "batchSize", "type": "uint256"},
            {"internalType": "address", "name": "recorder", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}],
        "name": "transferOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


_NONCE_ERROR_MARKERS = (
    "nonce too low",
    "nonce too high",
    "replacement transaction underpriced",
    "already known",
)
_EXPECTED_NONCE_PATTERN = re.compile(r"expected nonce to be (\d+)", re.IGNORECASE)
_NONCE_SEND_ATTEMPTS = 4


def _is_nonce_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _NONCE_ERROR_MARKERS)


def _resolve_next_nonce(w3, address: str, attempted: int, exc: Exception) -> int:
    """Pick the nonce to retry with after the node rejected `attempted`."""
    match = _EXPECTED_NONCE_PATTERN.search(str(exc))
    if match:
        return int(match.group(1))
    pending = w3.eth.get_transaction_count(address, "pending")
    return pending if pending > attempted else attempted + 1


def _truncate_utf8_bytes(text: str, max_bytes: int = 128) -> str:
    """Match Solidity bytes(string).length by truncating UTF-8 bytes, not characters."""
    raw = (text or "").encode("utf-8")
    if len(raw) <= max_bytes:
        return text or ""
    truncated = raw[:max_bytes]
    while truncated:
        try:
            return truncated.decode("utf-8")
        except UnicodeDecodeError:
            truncated = truncated[:-1]
    return ""


class AuditContract:
    """Provides high-level methods to interact with the SandalwoodAuditRegistry contract."""

    def __init__(
        self,
        contract_address: Optional[str] = None,
        client: Optional[Web3Client] = None,
    ):
        self.contract_address = contract_address or settings.BLOCKCHAIN_CONTRACT_ADDRESS
        self.client = client or web3_client
        self.abi = REGISTRY_ABI
        self._local_registry: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _unavailable(
        self,
        formatted_root: str,
        batch_size: int,
        message: str,
    ) -> Dict[str, Any]:
        return {
            "tx_hash": None,
            "block_number": None,
            "merkle_root": formatted_root,
            "batch_size": batch_size,
            "timestamp": int(time.time()),
            "contract_address": self.contract_address,
            "chain_id": self.client.chain_id,
            "status": "UNAVAILABLE",
            "message": message,
        }

    def _send_with_nonce_retry(
        self,
        w3,
        account,
        build_tx: Callable[[int], Dict[str, Any]],
    ):
        """Sign and send a transaction, re-reading the nonce if the node rejects it.

        A single get_transaction_count read races against transactions that have
        not settled yet, which downgraded a valid anchor to UNAVAILABLE.
        """
        nonce = w3.eth.get_transaction_count(account.address, "pending")
        for attempt in range(1, _NONCE_SEND_ATTEMPTS + 1):
            signed = account.sign_transaction(build_tx(nonce))
            raw_tx = (
                getattr(signed, "raw_transaction", None)
                or getattr(signed, "rawTransaction")
            )
            try:
                return w3.eth.send_raw_transaction(raw_tx)
            except Exception as exc:
                if not _is_nonce_error(exc) or attempt == _NONCE_SEND_ATTEMPTS:
                    raise
                retry_nonce = _resolve_next_nonce(w3, account.address, nonce, exc)
                logger.warning(
                    f"Nonce {nonce} rejected (attempt {attempt}/{_NONCE_SEND_ATTEMPTS}): "
                    f"{exc}. Retrying with nonce {retry_nonce}."
                )
                nonce = retry_nonce
                time.sleep(0.2 * attempt)

    def record_audit_batch(
        self,
        merkle_root: str,
        batch_size: int,
        description: str = "Automated Zero Trust Audit Batch",
    ) -> Dict[str, Any]:
        """Submit recordAuditBatch. Returns CONFIRMED only after a mined receipt."""
        formatted_root = merkle_root if merkle_root.startswith("0x") else f"0x{merkle_root}"
        unavailable = self._unavailable(
            formatted_root,
            batch_size,
            "Blockchain signer or RPC is not available. Records remain LOCAL_ONLY.",
        )

        w3 = self.client.w3
        private_key = self.client.private_key
        if not (HAS_WEB3 and w3 and self.client.is_connected and private_key and self.contract_address):
            logger.warning("Audit anchor skipped: no live RPC connection or BLOCKCHAIN_PRIVATE_KEY")
            return unavailable

        with self._lock:
            try:
                from web3 import Web3

                self.client.assert_chain_id()
                account = w3.eth.account.from_key(private_key)
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=self.abi,
                )

                owner = contract.functions.owner().call()
                if owner.lower() != account.address.lower():
                    raise RuntimeError(
                        f"Signer {account.address} is not registry owner {owner}"
                    )

                root_bytes = bytes.fromhex(formatted_root[2:])
                if len(root_bytes) != 32:
                    raise ValueError("Merkle root must be 32 bytes")
                description = _truncate_utf8_bytes(description or "", 128)
                try:
                    estimated_gas = contract.functions.recordAuditBatch(
                        root_bytes,
                        int(batch_size),
                        description,
                    ).estimate_gas({"from": account.address})
                    gas_limit = int(estimated_gas * 1.2)
                except Exception:
                    gas_limit = 300000

                tx_hash = self._send_with_nonce_retry(
                    w3,
                    account,
                    lambda nonce: contract.functions.recordAuditBatch(
                        root_bytes,
                        int(batch_size),
                        description,
                    ).build_transaction(
                        {
                            "from": account.address,
                            "nonce": nonce,
                            "chainId": self.client.chain_id,
                            "gas": gas_limit,
                            "gasPrice": w3.eth.gas_price,
                        }
                    ),
                )
                try:
                    mined = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                except Exception as wait_exc:
                    # Receipt wait timed out — tx may still have mined.
                    logger.warning(f"Receipt wait uncertain for {tx_hash.hex()}: {wait_exc}")
                    try:
                        mined = w3.eth.get_transaction_receipt(tx_hash)
                    except Exception:
                        unavailable["message"] = (
                            f"On-chain anchor uncertain (receipt wait): {wait_exc}"
                        )
                        unavailable["tx_hash"] = (
                            tx_hash.hex()
                            if str(tx_hash.hex()).startswith("0x")
                            else "0x" + tx_hash.hex()
                        )
                        return unavailable

                if mined is None or mined.status != 1:
                    raise RuntimeError("Transaction reverted or receipt missing")

                receipt = {
                    "tx_hash": tx_hash.hex() if not str(tx_hash.hex()).startswith("0x") else tx_hash.hex(),
                    "block_number": mined.blockNumber,
                    "merkle_root": formatted_root,
                    "batch_size": batch_size,
                    "timestamp": int(time.time()),
                    "contract_address": self.contract_address,
                    "chain_id": self.client.chain_id,
                    "status": "CONFIRMED",
                }
                if not receipt["tx_hash"].startswith("0x"):
                    receipt["tx_hash"] = "0x" + receipt["tx_hash"]
                self._local_registry[formatted_root.lower()] = receipt
                logger.info(
                    f"Anchored audit Merkle root on-chain: {formatted_root} (tx: {receipt['tx_hash']})"
                )
                return receipt
            except Exception as exc:
                logger.error(f"On-chain audit anchor failed: {exc}")
                if _is_nonce_error(exc):
                    unavailable["message"] = (
                        f"On-chain anchor failed after {_NONCE_SEND_ATTEMPTS} nonce "
                        f"retries — the signer account has contending transactions: {exc}"
                    )
                else:
                    unavailable["message"] = f"On-chain anchor failed: {exc}"
                return unavailable

    def verify_audit_batch(self, merkle_root: str) -> Dict[str, Any]:
        """Verify if a Merkle root exists in the on-chain registry.

        Prefers a live eth_call to verifyAuditBatch. Falls back to the
        in-process receipt cache only when RPC is unavailable.
        """
        formatted_root = merkle_root if merkle_root.startswith("0x") else f"0x{merkle_root}"
        key = formatted_root.lower()

        w3 = self.client.w3
        if HAS_WEB3 and w3 and self.client.is_connected and self.contract_address:
            try:
                from web3 import Web3

                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=self.abi,
                )
                root_bytes = bytes.fromhex(formatted_root[2:])
                if len(root_bytes) != 32:
                    raise ValueError("Merkle root must be 32 bytes")
                is_anchored, timestamp, batch_size, recorder = contract.functions.verifyAuditBatch(
                    root_bytes
                ).call()
                local = self._local_registry.get(key, {})
                return {
                    "is_anchored": bool(is_anchored),
                    "tx_hash": local.get("tx_hash"),
                    "block_number": local.get("block_number"),
                    "timestamp": int(timestamp) if is_anchored else None,
                    "batch_size": int(batch_size) if is_anchored else None,
                    "recorder": recorder if is_anchored else None,
                    "contract_address": self.contract_address,
                    "source": "onchain",
                }
            except Exception as exc:
                logger.warning(f"On-chain verifyAuditBatch failed: {exc}")

        if key in self._local_registry:
            record = self._local_registry[key]
            return {
                "is_anchored": False,
                "tx_hash": record.get("tx_hash"),
                "block_number": record.get("block_number"),
                "timestamp": record.get("timestamp"),
                "contract_address": self.contract_address,
                "source": "unconfirmed_local_cache",
                "message": (
                    "Merkle root present in local receipt cache but on-chain "
                    "anchoring cannot be verified (RPC unavailable)"
                ),
            }

        return {
            "is_anchored": False,
            "tx_hash": None,
            "block_number": None,
            "timestamp": None,
            "contract_address": self.contract_address,
            "source": "unavailable",
        }

    def transfer_ownership(self, new_owner: str) -> Dict[str, Any]:
        """Transfer ownership of SandalwoodAuditRegistry contract to a new address."""
        w3 = self.client.w3
        private_key = self.client.private_key
        if not (HAS_WEB3 and w3 and self.client.is_connected and private_key and self.contract_address):
            return {"success": False, "message": "Blockchain signer or RPC is not available."}

        with self._lock:
            try:
                from web3 import Web3

                self.client.assert_chain_id()
                account = w3.eth.account.from_key(private_key)
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=self.abi,
                )
                new_owner_checksum = Web3.to_checksum_address(new_owner)
                try:
                    estimated_gas = contract.functions.transferOwnership(
                        new_owner_checksum
                    ).estimate_gas({"from": account.address})
                    gas_limit = int(estimated_gas * 1.2)
                except Exception:
                    gas_limit = 100000

                tx_hash = self._send_with_nonce_retry(
                    w3,
                    account,
                    lambda nonce: contract.functions.transferOwnership(
                        new_owner_checksum
                    ).build_transaction(
                        {
                            "from": account.address,
                            "nonce": nonce,
                            "chainId": self.client.chain_id,
                            "gas": gas_limit,
                            "gasPrice": w3.eth.gas_price,
                        }
                    ),
                )
                mined = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if mined.status != 1:
                    raise RuntimeError("Transaction reverted")

                hex_hash = tx_hash.hex()
                if not hex_hash.startswith("0x"):
                    hex_hash = "0x" + hex_hash
                return {
                    "success": True,
                    "tx_hash": hex_hash,
                    "block_number": mined.blockNumber,
                    "new_owner": new_owner_checksum,
                }
            except Exception as exc:
                logger.error(f"Failed to transfer ownership: {exc}")
                return {"success": False, "message": str(exc)}


# Default contract instance
audit_contract = AuditContract()
