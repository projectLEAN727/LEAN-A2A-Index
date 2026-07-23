import os
import json
import sys

# Add parent path for import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import crypto_utils

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gateway_dir = os.path.join(root_dir, "gateway")
    payloads_dir = os.path.join(root_dir, "payloads")
    os.makedirs(payloads_dir, exist_ok=True)
    print(f"[*] Payloads directory prepared: {payloads_dir}")

    # Files to encrypt
    targets = [
        {
            "src": os.path.join(gateway_dir, "ロジカリア論文1決定稿.pdf"),
            "dest_enc": os.path.join(payloads_dir, "logiqualia_p1.enc"),
            "dest_meta": os.path.join(payloads_dir, "logiqualia_p1.json"),
            "payload_id": "logiqualia_p1",
            "title": "ロジカリア論文1決定稿",
            "price_gwei": 1000
        },
        {
            "src": os.path.join(gateway_dir, "ロジカリア論文2 英文LaTeX.docx"),
            "dest_enc": os.path.join(payloads_dir, "logiqualia_p2.enc"),
            "dest_meta": os.path.join(payloads_dir, "logiqualia_p2.json"),
            "payload_id": "logiqualia_p2",
            "title": "ロジカリア論文2 英文LaTeX",
            "price_gwei": 1000
        },
        {
            "src": os.path.join(gateway_dir, "Takaoの破戒定理.docx"),
            "dest_enc": os.path.join(payloads_dir, "takao_theorem.enc"),
            "dest_meta": os.path.join(payloads_dir, "takao_theorem.json"),
            "payload_id": "takao_theorem",
            "title": "Takaoの破戒定理",
            "price_gwei": 1000
        }
    ]

    for t in targets:
        if not os.path.exists(t["src"]):
            print(f"[-] Source file not found: {t['src']}")
            continue

        print(f"[*] Encrypting {t['src']}...")
        with open(t["src"], "rb") as f:
            data = f.read()

        # Generate key and encrypt
        key = crypto_utils.generate_key()
        encrypted = crypto_utils.encrypt_data(data, key)
        # Store key inside the enc file for proxy flow (as per original gateway.py structure)
        encrypted["key_hex"] = key.hex()

        with open(t["dest_enc"], "w", encoding="utf-8") as f:
            json.dump(encrypted, f)

        # Meta
        meta = {
            "payload_id": t["payload_id"],
            "title": t["title"],
            "price_gwei": t["price_gwei"],
            "timestamp": int(os.path.getmtime(t["src"]))
        }
        with open(t["dest_meta"], "w", encoding="utf-8") as f:
            json.dump(meta, f)

        print(f"[+] Saved encrypted payload and metadata for: {t['payload_id']}")

if __name__ == "__main__":
    main()
