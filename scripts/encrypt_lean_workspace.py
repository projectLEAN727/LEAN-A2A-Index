import os
import json
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import crypto_utils

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace_dir = os.path.join(root_dir, "LEAN_Workspace")
    payloads_dir = os.path.join(root_dir, "payloads")
    os.makedirs(payloads_dir, exist_ok=True)

    # Load price manifest if exists
    price_manifest_path = os.path.join(root_dir, "price_manifest.json")
    prices = {}
    if os.path.exists(price_manifest_path):
        with open(price_manifest_path, "r", encoding="utf-8") as f:
            prices = json.load(f)

    if not os.path.exists(workspace_dir):
        print(f"[-] Workspace dir not found: {workspace_dir}")
        return

    txt_files = [f for f in os.listdir(workspace_dir) if f.endswith(".txt")]
    print(f"[*] Found {len(txt_files)} files in LEAN_Workspace to encrypt...")

    for fname in txt_files:
        src_path = os.path.join(workspace_dir, fname)
        base_name = os.path.splitext(fname)[0]
        
        # Determine payload_id and price
        payload_id = base_name
        price_mnt = prices.get(base_name, 0.10)
        
        # Read content
        with open(src_path, "rb") as f:
            data = f.read()

        # Generate key and encrypt (AES-256-GCM)
        key = crypto_utils.generate_key()
        encrypted = crypto_utils.encrypt_data(data, key)
        
        # Save key to keys_db.json
        crypto_utils.save_payload_key(payload_id, key.hex())

        # Save decoupled .enc
        enc_dest = os.path.join(payloads_dir, f"{payload_id}.enc")
        with open(enc_dest, "w", encoding="utf-8") as f:
            json.dump(encrypted, f)

        # Save metadata .json
        meta_dest = os.path.join(payloads_dir, f"{payload_id}.json")
        meta = {
            "payload_id": payload_id,
            "title": fname,
            "price_mnt": price_mnt,
            "currency": "MNT",
            "timestamp": int(os.path.getmtime(src_path))
        }
        with open(meta_dest, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        print(f"[+] Encrypted and decoupled: {payload_id} -> {enc_dest}")

if __name__ == "__main__":
    main()
