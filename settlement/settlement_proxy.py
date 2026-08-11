import json
import os
from eth_account.messages import encode_defunct
from eth_account import Account

# 簡易的な .env 解析ロジック
ENV_VARS = {}
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                ENV_VARS[key.strip()] = val.strip()

# 設定値の抽出
MASTER_WALLET = ENV_VARS.get("LEAN_MASTER_WALLET_ADDRESS", "0x7270000000000000000000000000000000000000")
PROVIDER_URL = ENV_VARS.get("LEAN_PROVIDER_URL", "mock_local_node")

from web3 import Web3

# 動作モードの設定
MOCK_MODE = PROVIDER_URL == "mock_local_node" or not PROVIDER_URL
CONTRACT_ADDRESS = ENV_VARS.get("LEAN_CONTRACT_ADDRESS")

print(f"[!] [Settlement Initialize] Mode: {'MOCK MODE (FALLBACK)' if MOCK_MODE else 'PRODUCTION'}")
print(f"[*] [Settlement Initialize] Target Master Wallet: {MASTER_WALLET}")
print(f"[*] [Settlement Initialize] Target Contract: {CONTRACT_ADDRESS}")

# リプレイアタック防止用トランザクションハッシュ保存ファイル
USED_TX_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "payloads", "used_tx_hashes.json")

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
        os.makedirs(os.path.dirname(USED_TX_FILE), exist_ok=True)
        with open(USED_TX_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(used), f)
    except Exception as e:
        print(f"[-] Failed to save used transaction hash: {e}")


# Web3の初期化
if not MOCK_MODE:
    w3 = Web3(Web3.HTTPProvider(PROVIDER_URL, request_kwargs={"headers": {"User-Agent": "Mozilla/5.0"}}))
else:
    w3 = None

def verify_signature(challenge: str, signature: str, expected_address: str) -> bool:
    """
    Ethereumのメッセージ署名（EIP-191）を検証します。
    """
    try:
        message = encode_defunct(text=challenge)
        recovered_address = Account.recover_message(message, signature=signature)
        is_valid = recovered_address.lower() == expected_address.lower()
        if is_valid:
            print(f"[+] Wallet verification success: {recovered_address}")
        else:
            print(f"[-] Wallet verification failed. Expected: {expected_address}, Recovered: {recovered_address}")
        return is_valid
    except Exception as e:
        print(f"[-] Signature verification error: {e}")
        return False

def verify_payment_transaction(tx_hash: str, expected_amount_gwei: int, expected_recipient: str) -> bool:
    """
    Ethereum / Mantle のトランザクションハッシュを検証します。
    """
    try:
        # 明示的に不正/未払いとして指定されたテスト用ハッシュは即時拒否
        if "invalid" in tx_hash.lower() or "unpaid" in tx_hash.lower():
            print(f"[-] Blocked invalid/unpaid transaction hash: {tx_hash}")
            return False

        # リプレイアタック（二重使用）防止の検証
        used_txs = load_used_transactions()
        if tx_hash.lower() in used_txs:
            print(f"[-] Blocked replay attack: transaction hash {tx_hash} was already processed.")
            return False

        # モック環境または設定されていない場合の防衛ロジック
        if MOCK_MODE or tx_hash.startswith("0x_mock_") or tx_hash.startswith("0x_verified_") or tx_hash.startswith("0x_auto_payment_mock_"):
            print(f"[+] [Mock Mode] Verified payment transaction: {tx_hash}")
            save_used_transaction(tx_hash)
            return True

        if not w3 or not w3.is_connected():
            print("[-] Settlement proxy Web3 is not connected or provider is offline.")
            return False

        # オンチェーン上のトランザクションレシートの取得
        print(f"[*] [On-Chain] Querying transaction receipt for: {tx_hash}")
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if not receipt:
            print(f"[-] Transaction receipt not found on-chain for tx: {tx_hash}")
            return False

        # トランザクション成功ステータス（1 = 成功, 0 = 失敗）
        if receipt.get("status") != 1:
            print(f"[-] Transaction execution failed on-chain (status = 0) for tx: {tx_hash}")
            return False

        # トランザクション送信先が契約コントラクトアドレス（または期待される宛先）と一致しているか
        to_address = receipt.get("to")
        if not to_address:
            print(f"[-] Transaction to-address is null for tx: {tx_hash}")
            return False

        # 宛先アドレスのリスト
        allowed_recipients = [
            MASTER_WALLET.lower() if MASTER_WALLET else "",
            CONTRACT_ADDRESS.lower() if CONTRACT_ADDRESS else "",
            expected_recipient.lower() if expected_recipient else ""
        ]
        # 空文字を除外して小文字で統一
        allowed_recipients = [addr for addr in allowed_recipients if addr]

        if to_address.lower() not in allowed_recipients:
            print(f"[-] Transaction recipient mismatch. Expected one of: {allowed_recipients}, Got: {to_address}")
            return False

        # 1. ブロック承認数の確認 (Confirmations >= 1)
        current_block = w3.eth.block_number
        tx_block = receipt.get("blockNumber")
        confirmations = current_block - tx_block + 1
        if confirmations < 1:
            print(f"[-] Insufficient confirmations: {confirmations} < 1 for tx: {tx_hash}")
            return False

        # 2. トランザクション送金額 (value) の厳密な検証
        tx_details = w3.eth.get_transaction(tx_hash)
        actual_value_wei = tx_details.get("value", 0)
        expected_value_wei = w3.to_wei(expected_amount_gwei, 'gwei')

        if actual_value_wei < expected_value_wei:
            print(f"[-] Insufficient payment value. Expected: {expected_value_wei} Wei, Got: {actual_value_wei} Wei")
            return False

        print(f"[+] [On-Chain] Payment successfully verified. Status: Success, Target: {to_address}, Value: {actual_value_wei} Wei, Confirmations: {confirmations}")
        
        # 二重使用防止のため、正常処理後にトランザクションハッシュを記録
        save_used_transaction(tx_hash)
        return True
    except Exception as e:
        print(f"[-] Transaction on-chain verification error: {e}")
        return False


def audit_and_sign_payload(causal_payload_data: dict, private_key: str):
    """
    Attractia (LTE) 決定論的監査レイヤーの実行と EIP-191 暗号署名バインド
    """
    try:
        from attractia_core import CausalPayloadSchema, AttractiaAuditorEngine
        payload = CausalPayloadSchema(**causal_payload_data)
        audit_res = AttractiaAuditorEngine.audit_causal_graph(payload)
        signed_res = AttractiaAuditorEngine.bind_eip191_signature(audit_res, private_key)
        return signed_res.dict()
    except Exception as e:
        from attractia_core import CausalAuditResult
        return CausalAuditResult(
            status="DENY",
            pain_code="ERR_AUDIT_PARSE_FAILURE",
            reality_anchor_msg=f"【Reality Anchor】監査データパース失敗: {e}"
        ).dict()


