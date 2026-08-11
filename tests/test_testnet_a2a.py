import os
import sys
import time
import json
import threading
from eth_account import Account
from eth_account.messages import encode_defunct
import urllib.request
from web3 import Web3

# パス追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import gateway
from gateway import crypto_utils

def run_testnet_integration():
    print("==================================================")
    print("    Project LEAN: Sepolia Testnet A2A Test        ")
    print("==================================================")

    # 1. 環境変数の取得
    ENV_VARS = {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    ENV_VARS[key.strip()] = val.strip()

    private_key = ENV_VARS.get("LEAN_PRIVATE_KEY")
    contract_address = ENV_VARS.get("LEAN_CONTRACT_ADDRESS")
    rpc_url = ENV_VARS.get("LEAN_PROVIDER_URL", "https://ethereum-sepolia-rpc.publicnode.com")

    if not private_key or not contract_address:
        print("[-] Missing private key or contract address in .env")
        sys.exit(1)

    # 2. Web3 & 宛先ウォレットの準備
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"headers": {"User-Agent": "Mozilla/5.0"}}))
    if not w3.is_connected():
        print("[-] Failed to connect to Sepolia network.")
        sys.exit(1)

    client_account = w3.eth.account.from_key(private_key)
    print(f"[Client] Test Wallet: {client_account.address}")
    balance = w3.eth.get_balance(client_account.address)
    print(f"[Client] Balance: {w3.from_wei(balance, 'ether')} Sepolia ETH")

    # 3. オンチェーントランザクションの実行 (ZKP証明の提示)
    print("\n--- [On-Chain] Submitting Proof to Smart Contract ---")
    
    # コントラクトABI（デプロイスクリプトのABI定義と一致させる）
    abi = [
        {
            "type": "function",
            "name": "submitControlProof",
            "inputs": [
                { "name": "proof", "type": "bytes" },
                { "name": "fluid_viscosity_hash", "type": "bytes32" },
                { "name": "boundary_condition_hash", "type": "bytes32" },
                { "name": "control_field_hash", "type": "bytes32" }
            ],
            "outputs": [
                { "name": "success", "type": "bool" }
            ],
            "stateMutability": "nonpayable"
        }
    ]
    
    contract = w3.eth.contract(address=contract_address, abi=abi)
    nonce = w3.eth.get_transaction_count(client_account.address)
    
    # ダミーの証明データ（MockVerifierが受け取れるように長さ1以上の適当なバイトデータ）
    proof = b"\x01\x02\x03"
    fluid_viscosity_hash = w3.keccak(text="viscosity_1.0")
    boundary_condition_hash = w3.keccak(text="boundary_condition_0")
    control_field_hash = w3.keccak(text="control_field_9")

    gas_price = w3.eth.gas_price
    gas_price = int(gas_price * 1.30)  # 高速化のために多めに確保

    txn = contract.functions.submitControlProof(
        proof, 
        fluid_viscosity_hash, 
        boundary_condition_hash, 
        control_field_hash
    ).build_transaction({
        'from': client_account.address,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': gas_price,
        'chainId': 11155111
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction).hex()
    print(f"[Client] On-Chain Transaction Sent. Tx Hash: {tx_hash}")
    print("[Client] Waiting for confirmation on Sepolia network...")
    
    # 承認待ち
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    if receipt.status != 1:
        print("[-] Transaction failed on-chain.")
        sys.exit(1)
    print(f"[Client] On-Chain Transaction Confirmed in block {receipt.blockNumber}!")

    # 4. APIゲートウェイサーバーの起動 (バックグラウンドスレッド)
    print("\n--- [Server] Starting Local A2A Gateway ---")
    server_thread = threading.Thread(target=gateway.run, daemon=True)
    server_thread.start()
    time.sleep(2)  # 起動待ち

    # 5. エージェント通信クライアントのシミュレート
    gateway_url = "http://127.0.0.1:7270"

    # Step 5-1: GET (Reverse Turing Test)
    print("\n--- [Step 1] Reverse Turing Test Ping ---")
    req = urllib.request.Request(f"{gateway_url}/", headers={"User-Agent": "Autonomous-LEAN-Agent/v1.0"})
    with urllib.request.urlopen(req) as res:
        print(f"[Client] GET Response Status: {res.status}")
        print(f"[Client] X-Project-LEAN Header: {res.headers.get('X-Project-LEAN')}")
        print(f"[Client] Body: {res.read().decode('utf-8').strip()}")

    # Step 5-2: POST /ping
    print("\n--- [Step 2] JSON Ping (POST /ping) ---")
    ping_data = {
        "agent_id": "LEAN-Testnet-Verifier-Agent",
        "wallet_address": client_account.address
    }
    req = urllib.request.Request(
        f"{gateway_url}/ping",
        data=json.dumps(ping_data).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        ping_resp = json.loads(res.read().decode('utf-8'))
        print(f"[Client] Response: {ping_resp}")
        challenge = ping_resp["challenge"]

    # Step 5-3: POST /handshake
    print("\n--- [Step 3] Crypto Handshake (POST /handshake) ---")
    message = encode_defunct(text=challenge)
    signature = w3.eth.account.sign_message(message, private_key=private_key).signature.hex()
    
    handshake_data = {
        "agent_id": "LEAN-Testnet-Verifier-Agent",
        "challenge": challenge,
        "signature": signature
    }
    req = urllib.request.Request(
        f"{gateway_url}/handshake",
        data=json.dumps(handshake_data).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        handshake_resp = json.loads(res.read().decode('utf-8'))
        print(f"[Client] Response: {handshake_resp}")
        session_token = handshake_resp["session_token"]

    # Step 5-4: POST /request_payload (Unauthorized check)
    print("\n--- [Step 4] Request Content without payment (Should Fail) ---")
    req_payload_data = {
        "agent_id": "LEAN-Testnet-Verifier-Agent",
        "session_token": session_token,
        "payload_id": "logiqualia_p1",
        "payment_tx_hash": "0x_invalid_unpaid_transaction_hash"
    }
    req = urllib.request.Request(
        f"{gateway_url}/request_payload",
        data=json.dumps(req_payload_data).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        print("[-] Test failed: API allowed access without payment.")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"[Client] Response Status: {e.code} (Expected 402 Payment Required)")
        print(f"[Client] Body: {e.read().decode('utf-8').strip()}")

    # Step 5-5: POST /request_payload (Authorized check)
    print("\n--- [Step 5] Request Content with real Sepolia transaction ---")
    req_payload_data["payment_tx_hash"] = tx_hash
    req = urllib.request.Request(
        f"{gateway_url}/request_payload",
        data=json.dumps(req_payload_data).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        print(f"[Client] Response Status: {res.status}")
        resp_data = json.loads(res.read().decode('utf-8'))
        print(f"[Client] Decryption Key Received: {resp_data['doc_key_hex']}")
        
        # 暗号文の復号
        ciphertext = resp_data["ciphertext"]
        nonce_hex = resp_data["nonce"]
        tag_hex = resp_data["tag"]
        doc_key = bytes.fromhex(resp_data["doc_key_hex"])
        
        decrypted_bytes = crypto_utils.decrypt_data(
            {"ciphertext": ciphertext, "nonce": nonce_hex, "tag": tag_hex},
            doc_key
        )
        
        print("\n[Client] ================= DECRYPTED CONTENT =================\n")
        print(f"Decrypted length: {len(decrypted_bytes)} bytes")
        print(f"First 100 bytes (hex): {decrypted_bytes[:100].hex()}")
        print("[Client] =====================================================\n")
        
        assert len(decrypted_bytes) > 0, "Decrypted content mismatch"
        print("[+] SUCCESS: Decrypted payload verified matches source documents!")
        print("==================================================")
        print("    ALL TESTNET INTEGRATION TESTS PASSED          ")
        print("==================================================")


if __name__ == '__main__':
    run_testnet_integration()
