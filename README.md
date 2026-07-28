# lean-a2a-client (LEAN Agent-to-Agent Client SDK)

[![PyPI Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://pypi.org/project/lean-a2a-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**`lean-a2a-client`** は、外部AIエージェント（ElizaOS, CrewAI, LangChain, AutoGen等）が自律的決済（A2A Settlement）および暗号化データの取得・復号を数行のコードで実現するための汎用Python SDKパッケージです。

---

## 🚀 インストール (Installation)

```bash
pip install lean-a2a-client
```

ローカルソースからのインストール:
```bash
pip install .
```

---

## ⚡ Quick Start (1行導入 / Parasitic Integration)

既存のエージェントコードに `import a2a_client` を追加するだけで、価格ネゴシエーション、MNTオンチェーン決済、暗号署名ハンドシェイク、および AES-GCM 復号を全自動化できます。

### 🤖 HTTP 402 完全自動決済＆データ取得 (Auto-Budget `auto_fetch`)

エージェントの最大許容予算（`max_budget_mnt`）を設定し、価格判定からMNT送金・確認・復号までを自動処理します。

```python
import a2a_client

# 予算判定 ➔ Mantle送金 ➔ レシート承認待機 ➔ データ復号まで全自動実行
data_bytes = a2a_client.auto_fetch(
    gateway_url="http://localhost:7270",
    payload_id="logiqualia_p1",
    max_budget_mnt=0.50,  # 許容上限: 0.50 MNT
    private_key="0x_your_agent_private_key",
    rpc_url="https://rpc.mantle.xyz"
)

print(f"Decrypted Content ({len(data_bytes)} bytes):", data_bytes[:100])
```

### 1行取得例 (1-Line Fetch with existing Tx Hash)

```python
import a2a_client

# 既知の決済Tx Hashを用いたデータ取得＆復号
data_bytes = a2a_client.quick_fetch(
    gateway_url="http://localhost:7270",
    payload_id="logiqualia_p1",
    payment_tx_hash="0x_your_verified_payment_tx_hash",
    private_key="0x_agent_private_key"
)

print(f"Decrypted Content ({len(data_bytes)} bytes):", data_bytes[:100])
```

---

## 🛠 詳細な使い方 (Standard Usage)

より細かなハンドシェイク処理や認証管理を行う場合は、`A2AClient` クラスを使用します。

### CrewAI / ElizaOS エージェントへの統合例

```python
from a2a_client import A2AClient

# 1. クライアントの初期化
client = A2AClient(
    gateway_url="http://localhost:7270",
    private_key="0x_your_private_key",
    agent_id="ElizaOS-Trading-Agent-01"
)

# 2. 逆チューリングテスト＆チャレンジ取得 (Ping)
ping_info = client.ping()
print("Gateway Address:", ping_info["gateway_address"])

# 3. 暗号署名ハンドシェイク (Handshake)
session_token = client.handshake()
print("Session Token:", session_token)

# 4. 決済済みデータパッケージの取得 ＆ AES-GCM復号
decrypted_bytes = client.fetch(
    payload_id="logiqualia_p1",
    payment_tx_hash="0x_your_verified_payment_tx_hash"
)

# 復号結果の利用
with open("downloaded_payload.bin", "wb") as f:
    f.write(decrypted_bytes)
```

---

## ⚙ アーキテクチャフロー (A2A Workflow)

```
[ External Agent ]                   [ LEAN A2A Gateway ]
       |                                       |
       | ------ 1. GET / ping ---------------->| (Reverse Turing Test)
       |<------ Challenge Token -------------- |
       |                                       |
       | ------ 2. POST / handshake ---------->| (EIP-191 Signature Verification)
       |<------ Session Token -----------------|
       |                                       |
       | ------ 3. POST / request_payload ---->| (On-Chain Settlement Verification)
       |<------ Encrypted Payload + Key -------|
       |                                       |
[ AES-GCM Decryption ]                         |
```

---

## 📄 ライセンス (License)

MIT License
