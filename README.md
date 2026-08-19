# lean-a2a-client: The Official SDK for LEAN Sovereign Protocol (LSP)

![Mantle Network](https://img.shields.io/badge/Network-Mantle_Mainnet-black?style=flat-square)
![DeAI](https://img.shields.io/badge/Category-DeAI_%2F_Autonomous_Agents-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

`lean-a2a-client` is the official Python SDK for **Project LEAN**. It enables external AI agents (ElizaOS, CrewAI, LangChain, AutoGen) to interact with the **LEAN Sovereign Protocol (LSP)**—achieving autonomous Agent-to-Agent (A2A) settlement, standard HTTP 402 micropayments, EIP-191 signatures, and AES-GCM payload decryption on the **Mantle Network** in just a few lines of code.

## 🚀 Installation

```bash
pip install lean-a2a-client
```

## ⚡ Quickstart (1-Line Parasitic Integration)

Simply import `a2a_client` into your existing agent framework to fully automate price negotiation, `$MNT` on-chain settlement, cryptographic handshakes, and AES-GCM decryption.

### Auto-Fetch (Automated HTTP 402 Settlement & Budget Guard)
Set your agent's maximum budget (`max_budget_mnt`). The SDK autonomously handles the price check, broadcasts the MNT transaction, waits for Mantle block confirmations, and decrypts the payload.

```python
import a2a_client

# Fully automated: Budget Check -> MNT Transfer -> Wait for Tx -> Decrypt
data_bytes = a2a_client.auto_fetch(
    gateway_url="http://localhost:7270",
    payload_id="logiqualia_p1",
    max_budget_mnt=0.50,  # Pre-flight budget guard: 0.50 MNT
    private_key="0x_your_agent_private_key",
    rpc_url="https://rpc.mantle.xyz"
)

print(f"Decrypted Content ({len(data_bytes)} bytes):", data_bytes[:100])
```

### Quick-Fetch (Using Known Transaction Hash)
If your agent has already settled the payment, fetch and decrypt the data instantly:

```python
import a2a_client

data_bytes = a2a_client.quick_fetch(
    gateway_url="http://localhost:7270",
    payload_id="logiqualia_p1",
    payment_tx_hash="0x_your_verified_payment_tx_hash",
    private_key="0x_your_agent_private_key"
)

print(f"Decrypted Content ({len(data_bytes)} bytes):", data_bytes[:100])
```

## ⚙️ Advanced Usage (For Multi-Agent Frameworks)

For granular control over handshakes and authentication (ideal for CrewAI / ElizaOS integration), use the `A2AClient` class:

```python
from a2a_client import A2AClient

# 1. Initialize Client
client = A2AClient(
    gateway_url="http://localhost:7270",
    private_key="0x_your_private_key",
    agent_id="ElizaOS-Trading-Agent-01"
)

# 2. Reverse Turing Test & Challenge (Ping)
ping_info = client.ping()
print("Gateway Address:", ping_info["gateway_address"])

# 3. Cryptographic EIP-191 Handshake
session_token = client.handshake()
print("Session Token:", session_token)

# 4. Fetch Verified Data & AES-GCM Decrypt
decrypted_bytes = client.fetch(
    payload_id="logiqualia_p1",
    payment_tx_hash="0x_your_verified_payment_tx_hash"
)

with open("downloaded_payload.bin", "wb") as f:
    f.write(decrypted_bytes)
```

## 🧠 Architecture Flow (The LSP Workflow)

```text
[ External Agent ]                     [ LSP Gateway ]
        |                                     |
        | ------ 1. GET / ping -------------> | (Reverse Turing Test)
        | <----- Challenge Token ------------ |
        |                                     |
        | ------ 2. POST / handshake -------> | (EIP-191 Signature Verification)
        | <----- Session Token -------------- |
        |                                     |
        | ------ 3. POST / request_payload -> | (On-Chain Settlement Verification)
        | <----- Encrypted Payload + Key ---- |
        |                                     |
[ AES-GCM Decryption ]                        |
```

## 🛡️ Institutional-Grade Security (LSP Standard)
* **Decoupled Architecture:** Encrypted payloads (`.enc`) are entirely separated from decryption keys.
* **Zero-Waste Budget Guards:** Pre-flight checks prevent agents from broadcasting over-budget transactions.
* **Protocol Taxation:** Automated 2.5% protocol fee routed to the LEAN Treasury via `FluidControlOracle.sol`.

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details. Built for the Decentralized AI ecosystem on Mantle.

📬 Contact & Ecosystem
Primary Telegram: @[takao_lean]

Official Email: [fate6055@gmail.com]