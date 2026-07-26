import os
import json
from typing import Optional, Dict, Any, Union
import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from Crypto.Cipher import AES


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
