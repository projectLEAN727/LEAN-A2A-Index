import json
import os
import sys
from eth_account.messages import encode_defunct
from eth_account import Account
from web3 import Web3
from web3.exceptions import TransactionNotFound, Web3ValueError

# Configuration loading
ENV_VARS = {}
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                ENV_VARS[key.strip()] = val.strip()

MASTER_WALLET = ENV_VARS.get("LEAN_MASTER_WALLET_ADDRESS", "0xEaE24D8b541BAcc5FeE47f66a7189FAA715e9AeC")
PROVIDER_URL = ENV_VARS.get("LEAN_PROVIDER_URL", "https://rpc.mantle.xyz")
CONTRACT_ADDRESS = ENV_VARS.get("LEAN_CONTRACT_ADDRESS", "0x3A7017743AA6094B627d50534A53585230597C9f")
MOCK_MODE = False

print(f"[!] [Settlement Proxy] Mode: PRODUCTION (Strict Verification Mode)")
print(f"[*] [Settlement Proxy] Master Wallet: {MASTER_WALLET}")
print(f"[*] [Settlement Proxy] Contract: {CONTRACT_ADDRESS}")

# Replay attack prevention tracking
USED_TX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "used_tx_hashes.json")

def load_used_transactions() -> set:
    if os.path.exists(USED_TX_FILE):
        try:
            with open(USED_TX_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_used_transaction(tx_hash: str):
    try:
        used = load_used_transactions()
        used.add(tx_hash.lower())
        with open(USED_TX_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(used), f)
    except Exception as e:
        print(f"[-] Failed to save used transaction hash: {e}")

# Web3 Initialization
w3 = Web3(Web3.HTTPProvider(PROVIDER_URL, request_kwargs={"headers": {"User-Agent": "Mozilla/5.0"}}))
if not w3.is_connected():
    raise ConnectionError(f"Critical Error: Failed to connect to Mantle RPC: {PROVIDER_URL}")

# Manifest & Keys Vault Loading
MANIFEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "price_manifest.json")
KEYS_VAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.keys")

def load_price_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def verify_signature(challenge: str, signature: str, expected_address: str) -> bool:
    try:
        message = encode_defunct(text=challenge)
        recovered_address = Account.recover_message(message, signature=signature)
        return recovered_address.lower() == expected_address.lower()
    except Exception as e:
        print(f"[-] Signature verification error: {e}")
        return False

def verify_payment_transaction(tx_hash: str, payload_id: str) -> bool:
    """
    Verifies on-chain Mantle payment transaction for the specific payload_id.
    Enforces exact price matching from price_manifest.json.
    """
    if not w3 or not w3.is_connected():
        raise ConnectionError("Critical Error: Web3 provider disconnected.")

    used_txs = load_used_transactions()
    if tx_hash.lower() in used_txs:
        print(f"[-] Replay Attack Blocked: Tx {tx_hash} already processed.")
        return False

    manifest = load_price_manifest()
    payloads_catalog = manifest.get("payloads", {})
    payload_info = payloads_catalog.get(payload_id)
    
    if not payload_info:
        print(f"[-] Payload ID '{payload_id}' not found in price manifest.")
        return False

    expected_gwei = payload_info.get("price_gwei", 50000000)
    
    print(f"[*] [On-Chain] Querying transaction receipt for Tx: {tx_hash} (Payload: {payload_id}, Expected: {payload_info.get('price_mnt')} MNT)")
    
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception as e:
        if isinstance(e, TransactionNotFound):
            print(f"[-] Tx receipt not found on-chain: {tx_hash}")
            return False
        if isinstance(e, (ValueError, Web3ValueError)):
            print(f"[-] Invalid tx hash format: {tx_hash}")
            return False
        raise ConnectionError(f"RPC communication failed: {e}")

    if not receipt or receipt.get("status") != 1:
        print(f"[-] Transaction execution failed on-chain for Tx: {tx_hash}")
        return False

    to_address = receipt.get("to")
    allowed_recipients = [MASTER_WALLET.lower(), CONTRACT_ADDRESS.lower()]
    if not to_address or to_address.lower() not in allowed_recipients:
        print(f"[-] Recipient mismatch: Got {to_address}, expected {allowed_recipients}")
        return False

    current_block = w3.eth.block_number
    tx_block = receipt.get("blockNumber")
    confirmations = current_block - tx_block + 1
    if confirmations < 1:
        print(f"[-] Insufficient block confirmations ({confirmations} < 1)")
        return False

    tx_details = w3.eth.get_transaction(tx_hash)
    actual_value_wei = tx_details.get("value", 0)
    expected_value_wei = w3.to_wei(expected_gwei, 'gwei')

    if actual_value_wei < expected_value_wei:
        print(f"[-] Insufficient payment value. Expected: {expected_value_wei} Wei, Got: {actual_value_wei} Wei")
        return False

    print(f"[+] [On-Chain] Payment Verified! Tx: {tx_hash}, Payload: {payload_id}, Value: {actual_value_wei} Wei")
    save_used_transaction(tx_hash)
    return True

def get_decryption_key_for_payload(payload_id: str) -> str:
    """
    Extracts decryption key from local vault without exposing key contents in logs.
    """
    if os.path.exists(KEYS_VAULT_PATH):
        with open(KEYS_VAULT_PATH, 'r', encoding='utf-8') as f:
            vault = json.load(f)
            key = vault.get(payload_id)
            if key:
                print(f"[+] Retrieved decryption key for payload '{payload_id}' from secure key vault.")
                return key
    print(f"[-] Key for payload '{payload_id}' not found in key vault.")
    return None
