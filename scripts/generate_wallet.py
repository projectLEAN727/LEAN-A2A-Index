import os
from eth_account import Account

def generate_and_update_env():
    # 新しいウォレットの生成
    acct = Account.create()
    address = acct.address
    private_key = acct.key.hex()
    
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    lines = []
    
    # 既存の.envの読み込み
    address_updated = False
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("LEAN_MASTER_WALLET_ADDRESS="):
                    lines.append(f"LEAN_MASTER_WALLET_ADDRESS={address}\n")
                    address_updated = True
                elif stripped.startswith("LEAN_PRIVATE_KEY="):
                    # 既に秘密鍵があれば上書き（今回は新規追加/上書き両対応）
                    pass
                else:
                    lines.append(line)
                    
    # 元ファイルにアドレス設定がなかった場合の追記
    if not address_updated:
        lines.append(f"LEAN_MASTER_WALLET_ADDRESS={address}\n")
        
    # 秘密鍵の追記
    lines.append(f"LEAN_PRIVATE_KEY={private_key}\n")
    
    # .envの保存
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    # パブリックアドレスのみを出力（秘密鍵は出力しない）
    print(address)

if __name__ == '__main__':
    generate_and_update_env()
