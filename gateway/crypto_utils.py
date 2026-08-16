import os
import json
from typing import Optional
from Crypto.Cipher import AES

KEYS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys_db.json")


def generate_key() -> bytes:
    """256ビット（32バイト）のAES鍵を生成します。"""
    return os.urandom(32)


def encrypt_data(data: bytes, key: bytes) -> dict:
    """
    AES-GCMを用いてデータを暗号化します。
    戻り値: { 'ciphertext': hex, 'nonce': hex, 'tag': hex } (※復号キー key_hex は含めない)
    """
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return {
        "ciphertext": ciphertext.hex(),
        "nonce": cipher.nonce.hex(),
        "tag": tag.hex()
    }


def decrypt_data(encrypted_dict: dict, key: bytes) -> bytes:
    """
    AES-GCMを用いて暗号化データを復号します。
    """
    cipher = AES.new(
        key, 
        AES.MODE_GCM, 
        nonce=bytes.fromhex(encrypted_dict["nonce"])
    )
    decrypted = cipher.decrypt_and_verify(
        bytes.fromhex(encrypted_dict["ciphertext"]),
        bytes.fromhex(encrypted_dict["tag"])
    )
    return decrypted


def load_keys_db() -> dict:
    """ローカルのキーデータベース keys_db.json を読み込みます。"""
    if os.path.exists(KEYS_DB_PATH):
        try:
            with open(KEYS_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_payload_key(payload_id: str, key_hex: str):
    """キーデータベース (gateway/keys_db.json) に payload_id の復号キーを保存します。"""
    db = load_keys_db()
    db[payload_id] = key_hex
    os.makedirs(os.path.dirname(KEYS_DB_PATH), exist_ok=True)
    with open(KEYS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def get_payload_key(payload_id: str) -> Optional[str]:
    """キーデータベース (gateway/keys_db.json) から payload_id の復号キーを取得します。"""
    db = load_keys_db()
    return db.get(payload_id)
