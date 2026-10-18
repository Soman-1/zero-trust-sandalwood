"""Helpers to compile SandalwoodAuditRegistry and drive a local Hardhat node."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from solcx import compile_source, install_solc, set_solc_version

BLOCKCHAIN_DIR = Path(__file__).resolve().parents[1] / "blockchain"
CONTRACT_PATH = BLOCKCHAIN_DIR / "contracts" / "SandalwoodAuditRegistry.sol"

# Hardhat default account #0 (local-only; never use on a public network)
HARDHAT_ACCOUNT0_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
HARDHAT_ACCOUNT0_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
HARDHAT_ACCOUNT1_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
HARDHAT_CHAIN_ID = 31337
# Dedicated test port so we do not collide with a developer-owned node on 8545.
HARDHAT_PORT = 8549
HARDHAT_RPC = f"http://127.0.0.1:{HARDHAT_PORT}"


def compile_registry() -> Dict[str, Any]:
    """Compile Solidity source with solc 0.8.20; return abi + bytecode."""
    install_solc("0.8.20")
    set_solc_version("0.8.20")
    source = CONTRACT_PATH.read_text(encoding="utf-8")
    compiled = compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version="0.8.20",
    )
    # solcx keys look like "<stdin>:SandalwoodAuditRegistry"
    _, contract_interface = next(iter(compiled.items()))
    return {
        "abi": contract_interface["abi"],
        "bytecode": contract_interface["bin"],
    }


def deploy_registry(w3, private_key: str = HARDHAT_ACCOUNT0_KEY) -> Tuple[str, Any]:
    """Deploy SandalwoodAuditRegistry via web3.py; return (address, contract)."""
    artifact = compile_registry()
    account = w3.eth.account.from_key(private_key)
    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    # Hardhat auto-mines; use a generous HTTP timeout for compile+deploy.
    tx = contract.constructor().build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "chainId": int(w3.eth.chain_id),
            "gas": 3_000_000,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = account.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1 or not receipt.contractAddress:
        raise RuntimeError("Contract deployment failed")
    address = receipt.contractAddress
    return address, w3.eth.contract(address=address, abi=artifact["abi"])


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def wait_for_rpc(url: str = HARDHAT_RPC, timeout: float = 45.0) -> bool:
    from web3 import Web3, HTTPProvider

    host = "127.0.0.1"
    port = HARDHAT_PORT
    if "://" in url:
        try:
            port = int(url.rsplit(":", 1)[-1].rstrip("/"))
        except ValueError:
            port = HARDHAT_PORT

    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open(host, port):
            try:
                w3 = Web3(HTTPProvider(url, request_kwargs={"timeout": 2}))
                if w3.is_connected():
                    return True
            except Exception:
                pass
        time.sleep(0.4)
    return False


def _npx_command() -> list[str]:
    """Resolve npx in a Windows-friendly way (npx.cmd / shell)."""
    args = [
        "hardhat",
        "node",
        "--hostname",
        "127.0.0.1",
        "--port",
        str(HARDHAT_PORT),
    ]
    if os.name == "nt":
        return ["cmd.exe", "/c", "npx", *args]
    return ["npx", *args]

def start_hardhat_node() -> Optional[subprocess.Popen]:
    """Start `npx hardhat node` if RPC is not already up. Returns process or None if reused."""
    if wait_for_rpc(timeout=2.0):
        return None

    if not (BLOCKCHAIN_DIR / "node_modules" / "hardhat").exists():
        raise RuntimeError(
            "Hardhat is not installed under blockchain/. Run: npm install --prefix blockchain"
        )

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    log_path = BLOCKCHAIN_DIR / "hardhat-node.log"
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        _npx_command(),
        cwd=str(BLOCKCHAIN_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creationflags,
    )
    # Keep handle on the process so teardown can close the log file.
    proc._hardhat_log_file = log_file  # type: ignore[attr-defined]
    if not wait_for_rpc(timeout=60.0):
        stop_hardhat_node(proc)
        out = ""
        try:
            out = log_path.read_text(encoding="utf-8")
        except Exception:
            pass
        raise RuntimeError(f"Hardhat node failed to start.\n{out}")
    return proc


def stop_hardhat_node(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return
    log_file = getattr(proc, "_hardhat_log_file", None)
    if proc.poll() is not None:
        if log_file:
            try:
                log_file.close()
            except Exception:
                pass
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                check=False,
            )
        else:
            proc.terminate()
            proc.wait(timeout=10)
    except Exception:
        proc.kill()
    if log_file:
        try:
            log_file.close()
        except Exception:
            pass
