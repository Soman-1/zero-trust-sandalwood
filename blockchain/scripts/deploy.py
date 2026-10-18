"""Smart contract compilation and deployment script for SandalwoodAuditRegistry."""

import json
import os
import sys

from app.core.config import settings
from app.core.logging import logger

ABI = [
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "batchSize", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "recorder", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "description", "type": "string"},
        ],
        "name": "BatchAnchored",
        "type": "event",
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
    {
        "inputs": [],
        "name": "getTotalBatches",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def deploy_contract(rpc_url: str = None, private_key: str = None) -> str:
    """Deploy SandalwoodAuditRegistry contract to target EVM node."""
    rpc = rpc_url or settings.BLOCKCHAIN_RPC
    pk = private_key or settings.BLOCKCHAIN_PRIVATE_KEY
    logger.info(f"Connecting to blockchain RPC at: {rpc}")
    
    artifact_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "artifacts", "contracts", "SandalwoodAuditRegistry.sol", "SandalwoodAuditRegistry.json"
    )

    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc))
        if w3.is_connected() and pk and os.path.exists(artifact_path):
            with open(artifact_path, "r", encoding="utf-8") as f:
                artifact = json.load(f)
            abi = artifact.get("abi", ABI)
            bytecode = artifact.get("bytecode")
            if bytecode:
                account = w3.eth.account.from_key(pk)
                contract = w3.eth.contract(abi=abi, bytecode=bytecode)
                nonce = w3.eth.get_transaction_count(account.address)
                chain_id = int(w3.eth.chain_id)
                tx = contract.constructor().build_transaction({
                    "from": account.address,
                    "nonce": nonce,
                    "chainId": chain_id,
                    "gas": 3000000,
                    "gasPrice": w3.eth.gas_price,
                })
                signed = account.sign_transaction(tx)
                raw_tx = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
                tx_hash = w3.eth.send_raw_transaction(raw_tx)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                if receipt.contractAddress:
                    logger.info(f"SandalwoodAuditRegistry deployed live on-chain at: {receipt.contractAddress}")
                    return receipt.contractAddress
    except Exception as e:
        logger.warning(f"Live deployment skipped/fallback ({e}); using configured contract address.")

    contract_addr = settings.BLOCKCHAIN_CONTRACT_ADDRESS or ""
    if not contract_addr:
        raise RuntimeError(
            "Live deploy failed and BLOCKCHAIN_CONTRACT_ADDRESS is not set. "
            "Compile artifacts (npx hardhat compile) and ensure RPC + private key are available."
        )
    logger.warning(
        f"Live deploy did not produce a new address; using configured address: {contract_addr}"
    )
    return contract_addr


if __name__ == "__main__":
    deployed_address = deploy_contract()
    print(f"Contract address: {deployed_address}")
