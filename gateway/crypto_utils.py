import os
from Crypto.Cipher import AES

def generate_key() -> bytes:
    """256ビット（32バイト）のAES鍵を生成します。"""
    return os.urandom(32)

def encrypt_data(data: bytes, key: bytes) -> dict:
    """
    AES-GCMを用いてデータを暗号化します。
    戻り値: { 'ciphertext': hex, 'nonce': hex, 'tag': hex }
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
