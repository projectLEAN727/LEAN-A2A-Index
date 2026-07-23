import os
import json
import sys
import time

# Add parent path for import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import crypto_utils

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gateway_dir = os.path.join(root_dir, "gateway")
    payloads_dir = os.path.join(root_dir, "payloads")
    os.makedirs(payloads_dir, exist_ok=True)
    print(f"[*] Payloads directory: {payloads_dir}")

    # Files to encrypt
    targets = [
        {
            "src_candidates": [
                os.path.join(gateway_dir, "ナビエ・ストークス　完全証明.docx"),
                os.path.join(gateway_dir, "ナビエ・ストークス 完全証明.docx")
            ],
            "dest_enc": os.path.join(payloads_dir, "navier_stokes.enc"),
            "dest_meta": os.path.join(payloads_dir, "navier_stokes.json"),
            "payload_id": "navier_stokes",
            "title": "Navier-Stokes Complete Proof",
            "price_gwei": 1000
        },
        {
            "src_candidates": [
                os.path.join(gateway_dir, "リーマン予想マスターコンパイル.docx"),
                os.path.join(gateway_dir, "リーマン予想マスターコンパイル.pdf")
            ],
            "dest_enc": os.path.join(payloads_dir, "riemann.enc"),
            "dest_meta": os.path.join(payloads_dir, "riemann.json"),
            "payload_id": "riemann",
            "title": "Riemann予想マスターコンパイル",
            "price_gwei": 1000
        },
        {
            "src_candidates": [
                os.path.join(gateway_dir, "ナビエ・ストークス　マスターアップ.pdf"),
                os.path.join(gateway_dir, "ナビエ・ストークス　マスターアップ.docx"),
                os.path.join(gateway_dir, "ナビエ・ストークス マスターアップ.pdf"),
                os.path.join(gateway_dir, "ナビエ・ストークス マスターアップ.docx")
            ],
            "dest_enc": os.path.join(payloads_dir, "navier_stokes_master.enc"),
            "dest_meta": os.path.join(payloads_dir, "navier_stokes_master.json"),
            "payload_id": "navier_stokes_master",
            "title": "Navier-Stokes Master Up",
            "price_gwei": 1000
        }
    ]

    for t in targets:
        src = None
        for candidate in t["src_candidates"]:
            if os.path.exists(candidate):
                src = candidate
                break

        if not src:
            print(f"[-] Source file candidates not found for: {t['payload_id']}. Searched: {t['src_candidates']}")
            continue

        print(f"[*] Encrypting {src} in raw binary mode...")
        with open(src, "rb") as f:
            data = f.read()

        # Generate key and encrypt (AES-256-GCM)
        key = crypto_utils.generate_key()
        encrypted = crypto_utils.encrypt_data(data, key)
        # Store key inside the enc file for gateway logic
        encrypted["key_hex"] = key.hex()

        with open(t["dest_enc"], "w", encoding="utf-8") as f:
            json.dump(encrypted, f)

        # Meta
        meta = {
            "payload_id": t["payload_id"],
            "title": t["title"],
            "price_gwei": t["price_gwei"],
            "timestamp": int(time.time())
        }
        with open(t["dest_meta"], "w", encoding="utf-8") as f:
            json.dump(meta, f)

        print(f"[+] Saved encrypted payload and metadata for: {t['payload_id']} to {t['dest_enc']}")

if __name__ == "__main__":
    main()
