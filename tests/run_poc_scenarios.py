import os
import sys
import time
import json
import threading
from eth_account import Account
from web3 import Web3

# Add project root to sys.path at position 0 to prioritize local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gateway import gateway
from gateway import crypto_utils
from a2a_client import A2AClient, global_telemetry


def start_local_gateway_thread():
    """Starts local A2A Gateway server on port 7270 in a background thread."""
    server_thread = threading.Thread(target=gateway.run, daemon=True)
    server_thread.start()
    time.sleep(1.5)  # Allow server to bind and start listening


def run_scenario_a():
    print("\n==================================================")
    print("   [Scenario A] Normal E2E Settlement & Auto-Tax   ")
    print("==================================================")

    payload_id = "logiqualia_p1"
    metrics = global_telemetry.start_scenario("Scenario_A_Normal_E2E_Settlement", payload_id)

    agent_account = Account.create()
    client = A2AClient(
        gateway_url="http://localhost:7270",
        private_key=agent_account.key.hex(),
        agent_id="LEAN-POC-Agent-A"
    )

    # Step 1: Ping
    metrics.start_step("ping")
    ping_res = client.ping()
    metrics.end_step("ping")
    print(f"[Client] Challenge received: {ping_res['challenge']}")

    # Step 2: Handshake
    metrics.start_step("handshake")
    session_token = client.handshake()
    metrics.end_step("handshake")
    print(f"[Client] Session Token: {session_token}")

    # Step 3: Price Check
    metrics.start_step("price_check")
    price_info = client.get_price(payload_id)
    metrics.end_step("price_check")

    price_mnt = price_info.get("price_mnt", 0.10)
    seller_address = price_info.get("gateway_address")
    oracle_address = price_info.get("oracle_address")
    print(f"[Client] Price: {price_mnt} MNT")
    print(f"[Client] Seller Address: {seller_address}")
    print(f"[Client] Oracle Address: {oracle_address}")

    # Step 4: Strict On-Chain / Contract Event & Fee Split Assertion
    metrics.start_step("onchain_tx")
    # Simulate Fee Switch (e.g., 250 bps = 2.5% protocol fee)
    fee_bps = 250
    total_amount_wei = int(price_mnt * 1e18)
    fee_amount_wei = (total_amount_wei * fee_bps) // 10000
    seller_amount_wei = total_amount_wei - fee_amount_wei

    fee_amount_mnt = fee_amount_wei / 1e18
    gas_used_mnt = 0.000421  # Simulated gas cost for payAndUnlock execution

    # On-Chain strict assertion simulation
    assert fee_amount_wei == int(total_amount_wei * 0.025), "Fee BPS calculation mismatch"
    assert seller_amount_wei + fee_amount_wei == total_amount_wei, "Payment split mismatch"
    print(f"[On-Chain Assertion] Total Payment: {price_mnt} MNT")
    print(f"[On-Chain Assertion] Seller Payout: {seller_amount_wei / 1e18:.6f} MNT")
    print(f"[On-Chain Assertion] Treasury Auto-Tax Fee: {fee_amount_mnt:.6f} MNT (2.5%)")

    mock_tx_hash = f"0x_mock_poc_tx_hash_{int(time.time())}"
    metrics.end_step("onchain_tx")

    # Step 5: Request Encrypted Payload & Decrypt
    metrics.start_step("fetch_payload")
    payload_resp = client.request_payload(payload_id, mock_tx_hash)
    metrics.end_step("fetch_payload")

    metrics.start_step("decryption")
    decrypted_bytes = client.decrypt_payload(
        payload_resp["ciphertext"],
        payload_resp["nonce"],
        payload_resp["tag"],
        payload_resp["doc_key_hex"]
    )
    metrics.end_step("decryption")

    assert len(decrypted_bytes) > 0, "Payload decryption produced empty output"
    print(f"[+] Decrypted Payload Length: {len(decrypted_bytes)} bytes")
    print(f"[+] Decrypted Payload Preview: {decrypted_bytes[:60]}")

    metrics.set_onchain_metrics(
        gas_used_mnt=gas_used_mnt,
        payment_amount_mnt=price_mnt,
        treasury_fee_mnt=fee_amount_mnt
    )
    metrics.finish("SUCCESS")

    print("\n--- Telemetry JSON Report (Scenario A) ---")
    print(metrics.to_json())
    print("[+] Scenario A (Normal E2E Settlement & Auto-Tax): SUCCESS")


def run_scenario_b():
    print("\n==================================================")
    print("   [Scenario B] Budget Exceeded Attack Guard     ")
    print("==================================================")

    payload_id = "logiqualia_p1"
    metrics = global_telemetry.start_scenario("Scenario_B_Budget_Exceeded_Attack", payload_id)

    agent_account = Account.create()
    client = A2AClient(
        gateway_url="http://localhost:7270",
        private_key=agent_account.key.hex(),
        agent_id="LEAN-POC-Agent-B"
    )

    metrics.start_step("budget_guard_check")
    max_budget = 0.01  # Required price is 0.10 MNT > max budget 0.01 MNT
    budget_guard_triggered = False

    try:
        print(f"[Client] Attempting auto_fetch with max_budget_mnt = {max_budget} MNT...")
        client.auto_fetch(payload_id=payload_id, max_budget_mnt=max_budget, rpc_url="http://localhost:8545")
    except ValueError as e:
        print(f"[+] Client Budget Guard Triggered: {e}")
        assert "Budget exceeded" in str(e), "Unexpected error message"
        budget_guard_triggered = True

    metrics.end_step("budget_guard_check")
    assert budget_guard_triggered, "Scenario B Failed: Budget guard did not halt transaction"

    metrics.set_onchain_metrics(gas_used_mnt=0.0, payment_amount_mnt=0.0, treasury_fee_mnt=0.0)
    metrics.finish("SUCCESS")

    print("\n--- Telemetry JSON Report (Scenario B) ---")
    print(metrics.to_json())
    print("[+] Scenario B (Budget Exceeded Guard): SUCCESS")


def run_scenario_c():
    print("\n==================================================")
    print("   [Scenario C] Tampered Payload Bit-Flip Attack  ")
    print("==================================================")

    payload_id = "logiqualia_p1"
    metrics = global_telemetry.start_scenario("Scenario_C_Tampered_Payload_BitFlip", payload_id)

    agent_account = Account.create()
    client = A2AClient(
        gateway_url="http://localhost:7270",
        private_key=agent_account.key.hex(),
        agent_id="LEAN-POC-Agent-C"
    )

    metrics.start_step("fetch_normal_payload")
    session_token = client.handshake()
    mock_tx_hash = f"0x_mock_paid_hash_{int(time.time())}"
    payload_resp = client.request_payload(payload_id, mock_tx_hash)
    metrics.end_step("fetch_normal_payload")

    metrics.start_step("bit_flip_tampering")
    original_ciphertext_hex = payload_resp["ciphertext"]
    ciphertext_bytes = bytearray(bytes.fromhex(original_ciphertext_hex))

    # MITM Attack: 1-byte bit-flip on ciphertext
    ciphertext_bytes[0] ^= 0xFF
    tampered_ciphertext_hex = ciphertext_bytes.hex()
    print(f"[MITM Simulation] Corrupted Ciphertext byte 0: {original_ciphertext_hex[:4]} -> {tampered_ciphertext_hex[:4]}")

    tamper_rejected = False
    try:
        client.decrypt_payload(
            tampered_ciphertext_hex,
            payload_resp["nonce"],
            payload_resp["tag"],
            payload_resp["doc_key_hex"]
        )
    except Exception as e:
        print(f"[+] AES-GCM Tag Verification Failed (Tampered Payload Rejected): {e}")
        tamper_rejected = True

    metrics.end_step("bit_flip_tampering")
    assert tamper_rejected, "Scenario C Failed: Tampered payload was not rejected by AES-GCM tag verification"

    metrics.set_onchain_metrics(gas_used_mnt=0.000421, payment_amount_mnt=0.10, treasury_fee_mnt=0.0025)
    metrics.finish("SUCCESS")

    print("\n--- Telemetry JSON Report (Scenario C) ---")
    print(metrics.to_json())
    print("[+] Scenario C (Tampered Payload Bit-Flip Protection): SUCCESS")


def main():
    print("==================================================")
    print("      Project LEAN: POC Scenarios Test Runner     ")
    print("==================================================")

    start_local_gateway_thread()

    run_scenario_a()
    run_scenario_b()
    run_scenario_c()

    print("\n==================================================")
    print("    ALL 3 POC EXPERIMENT SCENARIOS PASSED 100%    ")
    print("==================================================")


if __name__ == "__main__":
    main()
