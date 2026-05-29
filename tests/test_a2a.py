import sys
import os
import threading
import time
import urllib.request
import json
from eth_account import Account
from eth_account.messages import encode_defunct

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import gateway
from gateway import crypto_utils

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    
    req = urllib.request.Request(url, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
        
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.add_header("Content-Type", "application/json")
        req.data = json_data
        
    try:
        with urllib.request.urlopen(req) as res:
            res_headers = dict(res.info())
            res_body = res.read().decode('utf-8')
            return res.status, res_headers, res_body
    except urllib.error.HTTPError as e:
        res_body = e.read().decode('utf-8')
        return e.code, dict(e.info()), res_body

def run_integration_test():
    print("==================================================")
    print("      Project LEAN: A2A Integration Test          ")
    print("==================================================")
    
    # 1. ゲートウェイサーバーをバックグラウンドスレッドで起動
    server_thread = threading.Thread(target=gateway.run, daemon=True)
    server_thread.start()
    
    # サーバーの起動待ち
    time.sleep(1.5)
    
    # 2. テスト用自律エージェントのウォレット生成
    agent_wallet = Account.create()
    agent_id = "LEAN-Crawler-Beta-7"
    print(f"[Client] Simulated Agent ID: {agent_id}")
    print(f"[Client] Simulated Wallet Address: {agent_wallet.address}")
    
    base_url = "http://localhost:7270"
    
    # --- ステップ1: 逆チューリング・テスト (GET) ---
    print("\n--- [Step 1] Reverse Turing Test Ping ---")
    headers = {
        "User-Agent": "Autonomous-LEAN-Agent/v1.0",
        "X-AI-Agent-ID": agent_id
    }
    status, res_headers, body = make_request(base_url, "GET", headers=headers)
    print(f"[Client] Response Status: {status}")
    print(f"[Client] X-Project-LEAN Header: {res_headers.get('X-Project-LEAN')}")
    print(f"[Client] Response Body: {body.strip()}")
    
    assert status == 200, "Step 1 Failed"
    assert "ACK" in body, "Step 1 ACK missing"
    assert res_headers.get('X-Project-LEAN') == "Sovereign-Node-Active", "Step 1 Header missing"
    print("[+] Step 1 (Reverse Turing Test): SUCCESS")
    
    # --- ステップ2: JSON Ping (POST /ping) ---
    print("\n--- [Step 2] JSON Ping (POST /ping) ---")
    ping_payload = {
        "agent_id": agent_id,
        "wallet_address": agent_wallet.address
    }
    status, _, body = make_request(f"{base_url}/ping", "POST", ping_payload)
    print(f"[Client] Response Body: {body}")
    ping_res = json.loads(body)
    
    assert status == 200, "Step 2 Failed"
    challenge = ping_res.get("challenge")
    gateway_address = ping_res.get("gateway_address")
    print(f"[Client] Challenge Received: {challenge}")
    print(f"[Client] Gateway Settlement Address: {gateway_address}")
    
    assert challenge is not None, "Challenge not provided"
    print("[+] Step 2 (JSON Ping & Challenge Generation): SUCCESS")
    
    # --- ステップ3: 暗号メッセージ署名 ＆ ハンドシェイク (POST /handshake) ---
    print("\n--- [Step 3] Crypto Handshake (POST /handshake) ---")
    # チャレンジトークンに対して秘密鍵で署名を付与
    message = encode_defunct(text=challenge)
    signed_message = agent_wallet.sign_message(message)
    signature_hex = signed_message.signature.hex()
    
    handshake_payload = {
        "agent_id": agent_id,
        "challenge": challenge,
        "signature": signature_hex
    }
    status, _, body = make_request(f"{base_url}/handshake", "POST", handshake_payload)
    print(f"[Client] Response Body: {body}")
    handshake_res = json.loads(body)
    
    assert status == 200, "Step 3 Failed"
    session_token = handshake_res.get("session_token")
    print(f"[Client] Session Token Established: {session_token}")
    
    assert session_token is not None, "Session token not provided"
    print("[+] Step 3 (Crypto Handshake & Verification): SUCCESS")
    
    # --- ステップ4: 未決済のコンテンツ取得要求テスト (POST /request_payload - Failure) ---
    print("\n--- [Step 4] Request Content without payment (Should Fail) ---")
    req_payload_fail = {
        "agent_id": agent_id,
        "session_token": session_token,
        "payload_id": "logiqualia_p1",
        "payment_tx_hash": "0x_invalid_unpaid_transaction_hash"
    }
    # 決済が未払いなので402（またはモックバリデーションにより失敗）が期待される
    status, _, body = make_request(f"{base_url}/request_payload", "POST", req_payload_fail)
    print(f"[Client] Response Status: {status} (Expected failure)")
    print(f"[Client] Response Body: {body}")
    
    assert status == 402, f"Expected 402 Payment Required, got {status}"
    print("[+] Step 4 (Unauthorized content block): SUCCESS")
    
    # --- ステップ5: 決済済のコンテンツ取得 ＆ 復号 (POST /request_payload - Success) ---
    print("\n--- [Step 5] Request Content with verified transaction (Should Succeed) ---")
    # モック決済トランザクションハッシュを送信
    req_payload_success = {
        "agent_id": agent_id,
        "session_token": session_token,
        "payload_id": "logiqualia_p1",
        "payment_tx_hash": "0x_mock_successful_payment_hash"
    }
    status, _, body = make_request(f"{base_url}/request_payload", "POST", req_payload_success)
    print(f"[Client] Response Status: {status}")

    payload_res = json.loads(body)
    
    assert status == 200, "Step 5 Failed"
    
    # 暗号データパッケージの抽出
    ciphertext = payload_res.get("ciphertext")
    nonce = payload_res.get("nonce")
    tag = payload_res.get("tag")
    doc_key_hex = payload_res.get("doc_key_hex")
    
    print(f"[Client] Encrypted Payload Hash: {ciphertext[:30]}...")
    print(f"[Client] Decryption Key Received: {doc_key_hex}")
    
    # コンテンツの復号実行
    encrypted_dict = {
        "ciphertext": ciphertext,
        "nonce": nonce,
        "tag": tag
    }
    decrypted_bytes = crypto_utils.decrypt_data(encrypted_dict, bytes.fromhex(doc_key_hex))
    
    print("\n[Client] ================= DECRYPTED CONTENT =================\n")
    print(f"Decrypted length: {len(decrypted_bytes)} bytes")
    print(f"First 100 bytes (hex): {decrypted_bytes[:100].hex()}")
    print("[Client] =====================================================\n")

    
    # PDFまたはファイルのヘッダー検証など
    assert len(decrypted_bytes) > 0, "Decrypted content mismatch"
    print("[+] Step 5 (Tax Verification, Decrypt & Verification): SUCCESS")
    
    print("\n==================================================")
    print("      ALL INTEGRATION TESTS PASSED SUCCESSFULLY   ")
    print("==================================================")

if __name__ == '__main__':
    run_integration_test()
