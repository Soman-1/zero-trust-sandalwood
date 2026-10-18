"""Web3 Client for interacting with EVM-compatible blockchain networks."""

import hashlib
import time
from typing import Optional
from app.core.config import settings
from app.core.logging import logger

try:
    from web3 import Web3, HTTPProvider
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False

RPC_REQUEST_TIMEOUT_SECONDS = 30


class Web3Client:
    """Manages RPC connection, transaction signing, and queries to blockchain node."""

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        chain_id: Optional[int] = None,
        private_key: Optional[str] = None,
    ):
        self.rpc_url = rpc_url or settings.BLOCKCHAIN_RPC
        self.chain_id = chain_id or settings.BLOCKCHAIN_CHAIN_ID
        self.private_key = private_key if private_key is not None else settings.BLOCKCHAIN_PRIVATE_KEY
        self._w3 = None
        self._connected_checked_at = 0.0

        if HAS_WEB3 and self.rpc_url:
            try:
                self._w3 = Web3(
                    HTTPProvider(
                        self.rpc_url,
                        request_kwargs={"timeout": RPC_REQUEST_TIMEOUT_SECONDS},
                    )
                )
                if self._probe_connection():
                    logger.info(f"Connected to live blockchain RPC: {self.rpc_url}")
                else:
                    logger.info(
                        f"Blockchain RPC unreachable at {self.rpc_url}; "
                        "anchors will stay LOCAL_ONLY until RPC is available."
                    )
            except Exception as e:
                logger.warning(f"Web3 connection error: {e}")
                self._w3 = None
        else:
            logger.info("Web3.py running without a live RPC connection.")

    def _probe_connection(self) -> bool:
        if not (HAS_WEB3 and self._w3):
            return False
        try:
            ok = bool(self._w3.is_connected())
            self._connected_checked_at = time.time()
            return ok
        except Exception:
            return False

    @property
    def is_connected(self) -> bool:
        """Re-probe periodically so a late-started Hardhat node can be picked up."""
        if not (HAS_WEB3 and self._w3):
            return False
        # Refresh at most every 5s to avoid hammering RPC on every call.
        if time.time() - self._connected_checked_at > 5:
            return self._probe_connection()
        try:
            return bool(self._w3.is_connected())
        except Exception:
            return False

    @property
    def w3(self):
        return self._w3

    def assert_chain_id(self) -> None:
        """Refuse to sign if configured chain ID does not match the live node."""
        if not (HAS_WEB3 and self._w3 and self.is_connected):
            raise RuntimeError("Blockchain RPC is not connected")
        live = int(self._w3.eth.chain_id)
        if live != int(self.chain_id):
            raise RuntimeError(
                f"Chain ID mismatch: configured {self.chain_id}, RPC reports {live}"
            )

    def generate_simulated_tx_hash(self, data: str) -> str:
        """Generate a deterministic 66-character EVM transaction hash for offline/local runs."""
        digest = hashlib.sha256(f"TX:{data}".encode("utf-8")).hexdigest()
        return f"0x{digest}"

    def get_block_number(self) -> int:
        """Get latest block number from chain or a coarse offline estimate."""
        if HAS_WEB3 and self._w3 and self.is_connected:
            try:
                return self._w3.eth.block_number
            except Exception:
                pass
        return int(time.time()) // 12


# Default singleton
web3_client = Web3Client()
