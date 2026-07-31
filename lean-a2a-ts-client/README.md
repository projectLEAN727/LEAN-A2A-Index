# @lean-a2a/client (LEAN A2A Client TypeScript SDK)

[![npm version](https://img.shields.io/badge/npm-v0.1.0-blue.svg)](https://www.npmjs.com/package/@lean-a2a/client)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**`@lean-a2a/client`** は、ElizaOS、LangChain TS、CrewAI 等の TypeScript / Node.js AI エージェント環境で、Project LEAN の自律決済（A2A Settlement）および Protocol Fee 対応データ取得・AES-GCM 復号を数行で完結させるための公式 TypeScript SDK です。

---

## 🚀 インストール (Installation)

```bash
npm install @lean-a2a/client viem
```

---

## ⚡ Quick Start (ElizaOS / Node.js 1行導入)

### 🤖 HTTP 402 完全自動決済＆データ取得 (`autoFetch`)

価格確認 ➔ 予算ガード ➔ `FluidControlOracle` (`payAndUnlock`) コントラクト決済 ➔ トランザクション承認待機 ➔ AES-256-GCM データ復号を全自動で実行します。

```typescript
import { autoFetch } from '@lean-a2a/client';

async function main() {
  // 自動ネゴシエーション＆オンチェーン決済＆復号のワンライン実行
  const decryptedBuffer: Buffer = await autoFetch(
    'http://localhost:7270',                   // Gateway URL
    'logiqualia_p1',                            // Payload ID
    0.50,                                      // 最大許容予算 (0.50 MNT)
    '0x_your_agent_private_key',                // 送金用ウォレット秘密鍵
    'https://rpc.mantle.xyz'                   // Mantle RPC Endpoint
  );

  console.log(`[+] Decrypted Payload (${decryptedBuffer.length} bytes):`);
  console.log(decryptedBuffer.subarray(0, 100).toString('utf-8'));
}

main().catch(console.error);
```

---

## 🛠 詳細な使い方 (`A2AClient` クラス)

```typescript
import { A2AClient } from '@lean-a2a/client';

async function runAgent() {
  const client = new A2AClient({
    gatewayUrl: 'http://localhost:7270',
    privateKey: '0x_your_agent_private_key',
    agentId: 'ElizaOS-Trading-Agent-TS',
    rpcUrl: 'https://rpc.mantle.xyz'
  });

  // 1. 価格と決済用コントラクト情報(oracle_address, payload_bytes32)の取得
  const priceInfo = await client.getPrice('logiqualia_p1');
  console.log(`Required Price: ${priceInfo.price_mnt} MNT`);
  console.log(`Oracle Contract: ${priceInfo.oracle_address}`);

  // 2. 自律決済＆データ取得
  const payloadBuffer = await client.autoFetch(
    'logiqualia_p1',
    0.50 // maxBudgetMnt
  );

  console.log('Decrypted Content:', payloadBuffer.toString('utf-8'));
}
```

---

## ⚙ アーキテクチャフロー (Protocol Fee Mediated Workflow)

```
[ TS / ElizaOS Agent ]                 [ LEAN Gateway ]             [ FluidControlOracle ]
         |                                     |                              |
         | ----- 1. GET /price --------------->|                              |
         |<----- Price, Seller, Oracle Address-|                              |
         |                                     |                              |
         | (Budget Check)                      |                              |
         | ----- 2. payAndUnlock(bytes32, seller) --------------------------->| (Protocol Fee Split)
         |<----- Tx Receipt Confirmed ----------------------------------------|
         |                                     |                              |
         | ----- 3. POST /handshake ---------->| (EIP-191 Verification)       |
         |<----- Session Token ----------------|                              |
         |                                     |                              |
         | ----- 4. POST /request_payload ---->|                              |
         |<----- Encrypted Payload + Key ------|                              |
         |                                     |                              |
  [ AES-256-GCM Decryption ]                   |                              |
```

---

## 📄 ライセンス (License)

MIT License
