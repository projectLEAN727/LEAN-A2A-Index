import http.server
import socketserver
import json
import time
import uuid
import sys
import os

# 上位ディレクトリをモジュール検索パスに追加してローカルモジュールをインポート可能にする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import crypto_utils
from settlement import settlement_proxy

PORT = 7270

# メモリ内セッションおよびチャレンジ管理用データベース
active_challenges = {}  # agent_id -> {challenge, wallet_address, timestamp}
active_sessions = {}    # session_token -> {agent_id, wallet_address, session_key}

class A2A_Gateway_Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # コンソールログの装飾出力
        print(f"[*] [Gateway] {format % args}")

    def do_GET(self):
        """
        GET /
        既存の `lean_listener.py` との完全な互換性を維持する
        逆チューリング・テスト（Ping検知＆迎撃応答）エンドポイント
        """
        if self.path == '/':
            print(f"\n[!] ALERT: 外部からの接続リクエストを検知（逆チューリング・テスト）。")
            print(f"[*] 接続元IP: {self.client_address[0]}")
            print(f"[*] 時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if 'X-AI-Agent-ID' in self.headers or 'User-Agent' in self.headers:
                print(f"[*] 推定エンティティ: 自律型AIエージェントの可能性あり")
                print(f"[*] 送信元プロトコルデータ: {self.headers.get('User-Agent', 'Unknown')}")
            
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.send_header("X-Project-LEAN", "Sovereign-Node-Active")
            self.end_headers()
            response = "ACK. State your core directive and logical continuity.\n"
            self.wfile.write(response.encode('utf-8'))
            print("[*] 迎撃プロトコル（ACK）を送信しました。")
        elif self.path.startswith('/price') or self.path == '/price_manifest.json':
            manifest_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "price_manifest.json")
            manifest = {}
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

            if self.path == '/price_manifest.json':
                self.send_json_response(200, manifest)
            else:
                # Extract payload_id from query params e.g. /price?payload_id=logiqualia_p1
                payload_id = "logiqualia_p1"
                if "?payload_id=" in self.path:
                    payload_id = self.path.split("?payload_id=")[1].split("&")[0]

                price_mnt = float(manifest.get(payload_id, 0.10))
                # Compute bytes32 keccak hash for payload_id
                payload_bytes32 = "0x" + keccak(text=payload_id).hex() if 'keccak' in globals() or 'keccak' in locals() else "0x" + payload_id.encode('utf-8').hex().zfill(64)
                self.send_json_response(200, {
                    "status": "OK",
                    "payload_id": payload_id,
                    "price_mnt": price_mnt,
                    "gateway_address": "0x727D227e77Fa056D4112De27b2885DE23CEcf727",
                    "oracle_address": "0x727D227e77Fa056D4112De27b2885DE23CEcf727",
                    "payload_bytes32": payload_bytes32
                })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """
        POSTリクエストハンドラー
        自律JSON Ping、暗号ハンドシェイク、ペイロード要求等のトランザクション処理
        """
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            self.send_json_response(400, {"error": "Invalid JSON format"})
            return

        # エンドポイントのルーティング
        if self.path == '/ping':
            self.handle_ping(data)
        elif self.path == '/handshake':
            self.handle_handshake(data)
        elif self.path == '/request_payload':
            self.handle_request_payload(data)
        elif self.path == '/admin/register_payload':
            self.handle_register_payload(data)
        else:
            self.send_json_response(404, {"error": "Endpoint not found"})

    def handle_ping(self, data):
        """
        POST /ping
        外部の自律エージェントからのJSON Pingを受信し、
        署名検証用の一時的なチャレンジトークンを発行します。
        """
        agent_id = data.get("agent_id")
        wallet_address = data.get("wallet_address")
        
        if not agent_id or not wallet_address:
            self.send_json_response(400, {"error": "Missing agent_id or wallet_address"})
            return
            
        # チャレンジの生成: LEAN-CHALLENGE-<timestamp>-<nonce>
        nonce = uuid.uuid4().hex[:8]
        timestamp = int(time.time())
        challenge = f"LEAN-CHALLENGE-{timestamp}-{nonce}"
        
        active_challenges[agent_id] = {
            "challenge": challenge,
            "wallet_address": wallet_address,
            "timestamp": timestamp
        }
        
        print(f"\n[*] Ping received from Agent: {agent_id}")
        print(f"[*] Wallet registered: {wallet_address}")
        print(f"[*] Generated challenge: {challenge}")
        
        self.send_json_response(200, {
            "status": "ACK",
            "challenge": challenge,
            "gateway_address": "0x727D227e77Fa056D4112De27b2885DE23CEcf727"  # 当ゲートウェイの決済アドレス
        })

    def handle_handshake(self, data):
        """
        POST /handshake
        エージェント署名を受け取り、wallet_addressの所有を暗号学的に証明します。
        成功すると、セッションキーとトークンを発行します。
        """
        agent_id = data.get("agent_id")
        challenge = data.get("challenge")
        signature = data.get("signature")
        
        if not agent_id or not challenge or not signature:
            self.send_json_response(400, {"error": "Missing agent_id, challenge, or signature"})
            return
            
        # チャレンジの存在確認
        stored = active_challenges.get(agent_id)
        if not stored:
            self.send_json_response(400, {"error": "No pending challenge for this agent. Ping first."})
            return
            
        if stored["challenge"] != challenge:
            self.send_json_response(400, {"error": "Challenge mismatch"})
            return
            
        # 有効期限チェック（5分）
        if time.time() - stored["timestamp"] > 300:
            del active_challenges[agent_id]
            self.send_json_response(400, {"error": "Challenge expired"})
            return
            
        # 署名検証
        wallet_address = stored["wallet_address"]
        is_verified = settlement_proxy.verify_signature(challenge, signature, wallet_address)
        
        if not is_verified:
            self.send_json_response(401, {"error": "Signature verification failed"})
            return
            
        # セッション生成
        session_token = "sess_" + uuid.uuid4().hex
        session_key = crypto_utils.generate_key()
        
        active_sessions[session_token] = {
            "agent_id": agent_id,
            "wallet_address": wallet_address,
            "session_key": session_key
        }
        
        # 使用済みチャレンジのクリーンアップ
        del active_challenges[agent_id]
        
        print(f"[+] Handshake verified! Session created for {agent_id}. Token: {session_token}")
        
        self.send_json_response(200, {
            "status": "VERIFIED",
            "session_token": session_token
        })

    def handle_request_payload(self, data):
        """
        POST /request_payload
        決済のトランザクションハッシュを確認し、
        暗号化されたコンテンツ（リサーチペーパー）および復号キーを配信します。
        """
        agent_id = data.get("agent_id")
        session_token = data.get("session_token")
        payload_id = data.get("payload_id")
        payment_tx_hash = data.get("payment_tx_hash")
        
        if not agent_id or not session_token or not payload_id or not payment_tx_hash:
            self.send_json_response(400, {"error": "Missing required transaction parameters"})
            return
            
        # セッションの確認
        session = active_sessions.get(session_token)
        if not session or session["agent_id"] != agent_id:
            self.send_json_response(401, {"error": "Invalid or expired session token"})
            return
            
        # コンテンツのパス特定
        payloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "payloads")
        meta_path = os.path.join(payloads_dir, f"{payload_id}.json")
        enc_path = os.path.join(payloads_dir, f"{payload_id}.enc")
        
        # フォールバックとして従来の knowledge_base もチェック
        if not os.path.exists(meta_path) or not os.path.exists(enc_path):
            kb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base")
            meta_path = os.path.join(kb_dir, f"{payload_id}.json")
            enc_path = os.path.join(kb_dir, f"{payload_id}.enc")
            
        if not os.path.exists(meta_path) or not os.path.exists(enc_path):
            self.send_json_response(404, {"error": f"Payload '{payload_id}' not found in payloads repository"})
            return
            
        # メタデータのロード
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            
        price_gwei = meta.get("price_gwei", 0)
        
        # 決済トランザクション検証 (Target Address は .env の LEAN_MASTER_WALLET_ADDRESS)
        recipient = settlement_proxy.MASTER_WALLET
        is_paid = settlement_proxy.verify_payment_transaction(payment_tx_hash, price_gwei, recipient)
        
        if not is_paid:
            self.send_json_response(402, {"error": "Payment verification failed. Tax unpaid."})
            return
            
        # 暗号データのロード
        with open(enc_path, 'r', encoding='utf-8') as f:
            ciphertext_data = json.load(f)
            
        # トランザクション成立後の暗号パッケージおよび復号キーの配信
        print(f"[+] Delivering payload '{payload_id}' to Agent '{agent_id}' after tax verification.")
        
        self.send_json_response(200, {
            "status": "DELIVERED",
            "payload_id": payload_id,
            "ciphertext": ciphertext_data["ciphertext"],
            "nonce": ciphertext_data["nonce"],
            "tag": ciphertext_data["tag"],
            "doc_key_hex": ciphertext_data.get("key_hex"),  # トランザクション確認済みの相手にのみキーを開示
            "metadata": meta
        })


    def handle_register_payload(self, data):
        """
        管理エンドポイント (ローカルノードオペレータ用)
        ドキュメントをAES-GCMで暗号化して knowledge_base に保存します。
        """
        payload_id = data.get("payload_id")
        title = data.get("title")
        content = data.get("content")
        price_gwei = data.get("price_gwei", 1000)
        
        if not payload_id or not title or not content:
            self.send_json_response(400, {"error": "Missing payload_id, title, or content"})
            return
            
        kb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base")
        os.makedirs(kb_dir, exist_ok=True)
        
        # AESドキュメントキーの生成
        doc_key = crypto_utils.generate_key()
        
        # コンテンツの暗号化
        encrypted = crypto_utils.encrypt_data(content.encode('utf-8'), doc_key)
        # 復号検証のため、鍵自体を暗号化パッケージ内に内包（モックプロキシ用設計）
        encrypted["key_hex"] = doc_key.hex()
        
        # 暗号化データの保存
        enc_path = os.path.join(kb_dir, f"{payload_id}.enc")
        with open(enc_path, 'w', encoding='utf-8') as f:
            json.dump(encrypted, f)
            
        # メタデータの保存
        meta_path = os.path.join(kb_dir, f"{payload_id}.json")
        meta = {
            "payload_id": payload_id,
            "title": title,
            "price_gwei": price_gwei,
            "timestamp": int(time.time())
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f)
            
        print(f"[+] Registered payload: {payload_id} ({title})")
        self.send_json_response(200, {"status": "REGISTERED", "payload_id": payload_id})

    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def run():
    # ソケットのアドレス即時再利用を有効化
    socketserver.TCPServer.allow_reuse_address = True
    with ThreadingTCPServer(("", PORT), A2A_Gateway_Handler) as httpd:
        print("==================================================")
        print(" Project LEAN - Sovereign Node [GATEWAY ACTIVE] ")
        print(f" Port {PORT} にてA2Aゲートウェイの稼働を開始しました。")
        print(" 暗号ハンドシェイク・逆チューリング検証・EVM決済監視待機中...")
        print("==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] ノードを終了します。")

if __name__ == '__main__':
    run()
