import os
import json
from typing import Optional, Dict, Any, Union
import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from Crypto.Cipher import AES
from web3 import Web3


class A2AClient:
    """
    Client SDK for Project LEAN A2A (Agent-to-Agent) Autonomous Settlement & Gateway Access.
    """

    def __init__(
        self,
        gateway_url: str = "http://localhost:7270",
        private_key: Optional[str] = None,
        agent_id: str = "LEAN-Autonomous-Agent-01",
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
    ):
        self.gateway_url = gateway_url.rstrip("/")
        self.agent_id = agent_id
        self.rpc_url = rpc_url
        self.contract_address = contract_address

        if private_key:
            self.account = Account.from_key(private_key)
        else:
            self.account = Account.create()

        self.session_token: Optional[str] = None
        self.challenge: Optional[str] = None
        self.gateway_address: Optional[str] = None

    def ping(self) -> Dict[str, Any]:
        """
        Sends a ping request to the A2A Gateway to initiate challenge generation.
        """
        url = f"{self.gateway_url}/ping"
        payload = {
            "agent_id": self.agent_id,
            "wallet_address": self.account.address,
        }
        resp = httpx.post(url, json=payload, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        self.challenge = data.get("challenge")
        self.gateway_address = data.get("gateway_address")
        return data

    def handshake(self) -> str:
        """
        Signs the gateway challenge using EIP-191 and obtains a session token.
        """
        if not self.challenge:
            self.ping()

        message = encode_defunct(text=self.challenge)
        signed = self.account.sign_message(message)
        signature_hex = signed.signature.hex()

        url = f"{self.gateway_url}/handshake"
        payload = {
            "agent_id": self.agent_id,
            "challenge": self.challenge,
            "signature": signature_hex,
        }
        resp = httpx.post(url, json=payload, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        self.session_token = data.get("session_token")
        if not self.session_token:
            raise ValueError("Gateway did not return a valid session_token.")
        return self.session_token

    def get_price(self, payload_id: str) -> Dict[str, Any]:
        """
        Queries gateway or manifest endpoint to obtain required payment in MNT and destination wallet.
        """
        # 1. Query Gateway /price?payload_id=...
        url = f"{self.gateway_url}/price?payload_id={payload_id}"
        try:
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                if "price_mnt" in data:
                    return data
        except Exception:
            pass

        # 2. Fallback to GET /price_manifest.json
        try:
            manifest_url = f"{self.gateway_url}/price_manifest.json"
            resp = httpx.get(manifest_url, timeout=5.0)
            if resp.status_code == 200:
                manifest = resp.json()
                price = manifest.get(payload_id, 0.10)
                if not self.gateway_address:
                    try:
                        self.ping()
                    except Exception:
                        pass
                return {
                    "payload_id": payload_id,
                    "price_mnt": float(price),
                    "gateway_address": self.gateway_address or "0x727D227e77Fa056D4112De27b2885DE23CEcf727"
                }
        except Exception:
            pass

        # 3. Default fallback
        if not self.gateway_address:
            try:
                self.ping()
            except Exception:
                pass
        return {
            "payload_id": payload_id,
            "price_mnt": 0.10,
            "gateway_address": self.gateway_address or "0x727D227e77Fa056D4112De27b2885DE23CEcf727"
        }

    def request_payload(
        self,
        payload_id: str,
        payment_tx_hash: str,
    ) -> Dict[str, Any]:
        """
        Requests encrypted payload from gateway using verified payment transaction hash.
        """
        if not self.session_token:
            self.handshake()

        url = f"{self.gateway_url}/request_payload"
        payload = {
            "agent_id": self.agent_id,
            "session_token": self.session_token,
            "payload_id": payload_id,
            "payment_tx_hash": payment_tx_hash,
        }
        resp = httpx.post(url, json=payload, timeout=15.0)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def decrypt_payload(
        ciphertext_hex: str,
        nonce_hex: str,
        tag_hex: str,
        doc_key_hex: str,
    ) -> bytes:
        """
        Decrypts AES-GCM encrypted payload data.
        """
        key = bytes.fromhex(doc_key_hex)
        nonce = bytes.fromhex(nonce_hex)
        ciphertext = bytes.fromhex(ciphertext_hex)
        tag = bytes.fromhex(tag_hex)

        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)

    def fetch(
        self,
        payload_id: str,
        payment_tx_hash: str,
    ) -> bytes:
        """
        End-to-end payload retrieval: Handshake, request encrypted payload, and decrypt.
        """
        payload_resp = self.request_payload(payload_id, payment_tx_hash)
        ciphertext = payload_resp["ciphertext"]
        nonce = payload_resp["nonce"]
        tag = payload_resp["tag"]
        doc_key_hex = payload_resp["doc_key_hex"]

        return self.decrypt_payload(ciphertext, nonce, tag, doc_key_hex)

    def auto_fetch(
        self,
        payload_id: str,
        max_budget_mnt: float,
        private_key: Optional[str] = None,
        rpc_url: str = "https://rpc.mantle.xyz",
    ) -> bytes:
        """
        HTTP 402 Auto-Negotiation (Auto-Budget) workflow:
        1. Price Check: Obtains required payment in MNT and destination address.
        2. Budget Guard: Raises ValueError("Budget exceeded") if required price > max_budget_mnt.
        3. Autonomous Transfer: Signs and broadcasts local MNT transaction via Web3 on rpc_url.
        4. Receipt Confirmation: Waits for transaction confirmation receipt.
        5. Fetch & Decrypt: Executes handshake, requests payload, and decrypts AES-GCM content.
        """
        pkey = private_key or (self.account.key.hex() if hasattr(self, "account") and self.account else None)
        if not pkey:
            raise ValueError("Private key is required for auto_fetch payment.")

        # ① 価格確認 (Price Check)
        price_info = self.get_price(payload_id)
        price_mnt = float(price_info.get("price_mnt", 0.10))
        seller_raw = price_info.get("gateway_address", "0x727D227E77fA056D4112DE27b2885de23cECf727")
        oracle_raw = price_info.get("oracle_address", self.contract_address or "0x727D227E77fA056D4112DE27b2885de23cECf727")
        seller_address = Web3.to_checksum_address(seller_raw)
        oracle_address = Web3.to_checksum_address(oracle_raw)
        payload_b32 = price_info.get("payload_bytes32")

        # ② 予算判定 (Budget Guard)
        if price_mnt > max_budget_mnt:
            raise ValueError(f"Budget exceeded: Required price ({price_mnt} MNT) > max budget ({max_budget_mnt} MNT)")

        # ③ & ④ スマートコントラクト(payAndUnlock)経由の自律決済 ＆ 承認待機
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        sender_account = Account.from_key(pkey)

        if w3.is_connected():
            checksum_oracle = Web3.to_checksum_address(oracle_address)
            checksum_seller = Web3.to_checksum_address(seller_address)
            amount_wei = w3.to_wei(price_mnt, 'ether')

            # Format payload_id to bytes32
            if payload_b32 and isinstance(payload_b32, str) and payload_b32.startswith("0x"):
                p_bytes32 = bytes.fromhex(payload_b32[2:].zfill(64))
            elif isinstance(payload_id, str) and payload_id.startswith("0x") and len(payload_id) == 66:
                p_bytes32 = bytes.fromhex(payload_id[2:])
            else:
                p_bytes32 = Web3.keccak(text=payload_id)

            abi = [
                {
                    "type": "function",
                    "name": "payAndUnlock",
                    "inputs": [
                        { "name": "payload_id", "type": "bytes32" },
                        { "name": "seller", "type": "address" }
                    ],
                    "outputs": [
                        { "name": "success", "type": "bool" }
                    ],
                    "stateMutability": "payable"
                }
            ]

            contract = w3.eth.contract(address=checksum_oracle, abi=abi)
            nonce = w3.eth.get_transaction_count(sender_account.address)
            gas_price = w3.eth.gas_price

            tx = contract.functions.payAndUnlock(p_bytes32, checksum_seller).build_transaction({
                'from': sender_account.address,
                'value': amount_wei,
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': 100000,
            })
            try:
                tx['chainId'] = w3.eth.chain_id
            except Exception:
                tx['chainId'] = 5000  # Mantle Mainnet chain ID fallback

            signed_tx = w3.eth.account.sign_transaction(tx, private_key=pkey)
            tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = tx_hash_bytes.hex()
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)
            if receipt.get("status") != 1:
                raise RuntimeError(f"On-chain payAndUnlock transaction failed: {tx_hash}")
        else:
            # RPC unreachable or testing fallback
            tx_hash = f"0x_auto_payment_mock_{payload_id}"

        # ⑤ 取得・復号 (Fetch & Decrypt)
        if not self.session_token:
            self.handshake()

        return self.fetch(payload_id=payload_id, payment_tx_hash=tx_hash)


def quick_fetch(
    gateway_url: str,
    payload_id: str,
    payment_tx_hash: str,
    private_key: Optional[str] = None,
    agent_id: str = "LEAN-Agent-Quick",
) -> bytes:
    """
    1-line integration helper for external AI agents (ElizaOS, CrewAI, etc.).
    """
    client = A2AClient(gateway_url=gateway_url, private_key=private_key, agent_id=agent_id)
    return client.fetch(payload_id=payload_id, payment_tx_hash=payment_tx_hash)


def auto_fetch(
    gateway_url: str,
    payload_id: str,
    max_budget_mnt: float,
    private_key: str,
    rpc_url: str = "https://rpc.mantle.xyz",
    agent_id: str = "LEAN-Auto-Budget-Agent",
) -> bytes:
    """
    1-line HTTP 402 Auto-Negotiation (Auto-Budget) helper for external AI agents.
    """
    client = A2AClient(gateway_url=gateway_url, private_key=private_key, agent_id=agent_id, rpc_url=rpc_url)
    return client.auto_fetch(
        payload_id=payload_id,
        max_budget_mnt=max_budget_mnt,
        private_key=private_key,
        rpc_url=rpc_url,
    )
