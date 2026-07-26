import os
import sys
import json
import time
from web3 import Web3
import solcx

def run_deployment():
    # 1. solc 0.8.20のセットアップ
    print("[*] Setting up Solidity compiler (solc 0.8.20)...")
    try:
        solcx.install_solc("0.8.20")
        solcx.set_solc_version("0.8.20")
        print("[+] solc 0.8.20 ready.")
    except Exception as e:
        print(f"[-] Error installing solc: {e}")
        sys.exit(1)

    # 2. .envファイルのロード
    ENV_VARS = {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    ENV_VARS[key.strip()] = val.strip()

    private_key = ENV_VARS.get("LEAN_PRIVATE_KEY")
    if not private_key:
        print("[-] LEAN_PRIVATE_KEY not found in .env!")
        sys.exit(1)

    # 3. RPCへの接続
    rpc_url = ENV_VARS.get("LEAN_PROVIDER_URL", "https://rpc.mantle.xyz")
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"headers": {"User-Agent": "Mozilla/5.0"}}))

    if not w3.is_connected():
        print(f"[-] Failed to connect to RPC: {rpc_url}")
        sys.exit(1)

    # ネットワーク設定に mantle を新規追加し、Chain ID 5000 を指定するコードを実装
    SUPPORTED_NETWORKS = {
        11155111: {
            "name": "Sepolia Testnet",
            "symbol": "Sepolia ETH"
        },
        5000: {
            "name": "Mantle Mainnet",
            "symbol": "MNT"
        }
    }

    try:
        chain_id = w3.eth.chain_id
        print(f"[*] Connected Chain ID: {chain_id}")
    except Exception as e:
        print(f"[-] Failed to fetch Chain ID: {e}")
        sys.exit(1)

    network_info = SUPPORTED_NETWORKS.get(chain_id, {"name": f"Unknown Network (Chain ID: {chain_id})", "symbol": "ETH"})
    print(f"[+] Active Network: {network_info['name']}")

    account = w3.eth.account.from_key(private_key)
    print(f"[+] Wallet Address: {account.address}")
    balance = w3.eth.get_balance(account.address)
    print(f"[+] Balance: {w3.from_wei(balance, 'ether')} {network_info['symbol']}")

    # デプロイに必要な最小残高のチェック (Mantleはガス代が非常に安いため、最小必要額を低く設定)
    min_balance = w3.to_wei(0.001, 'ether')
    if balance < min_balance:
        print(f"[-] Insufficient balance for deployment on {network_info['name']}.")
        print("[*] Note: Connection to Mantle verified successfully, but contract deployment requires MNT.")
        sys.exit(0)


    # 4. コントラクトのコンパイル
    contract_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        "contracts", "FluidControlOracle.sol"
    )

    print(f"[*] Compiling contract: {contract_path}")
    try:
        compiled_sol = solcx.compile_files([contract_path], output_values=["abi", "bin"])
    except Exception as e:
        print(f"[-] Compilation error: {e}")
        sys.exit(1)

    # コントラクト名の末尾一致でコンパイルデータを動的に特定
    oracle_key = next((k for k in compiled_sol.keys() if k.endswith(":FluidControlOracle")), None)

    if not oracle_key:
        print(f"[-] Failed to find compiled contracts. Available keys: {list(compiled_sol.keys())}")
        sys.exit(1)

    oracle_abi = compiled_sol[oracle_key]["abi"]
    oracle_bin = compiled_sol[oracle_key]["bin"]

    print("[+] Compilation successful.")

    # 5. コントラクトのデプロイ関数
    def deploy_contract(abi, bytecode, args=()):
        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        nonce = w3.eth.get_transaction_count(account.address)
        
        gas_price = w3.eth.gas_price
        gas_price = int(gas_price * 1.25)  # トランザクション承認を速めるためのガスプライス調整

        construct_txn = contract.constructor(*args).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 1500000,
            'gasPrice': gas_price,
            'chainId': chain_id
        })

        signed_txn = w3.eth.account.sign_transaction(construct_txn, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"[*] Sent transaction. Hash: {tx_hash.hex()}")
        
        print("[*] Waiting for transaction confirmation...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
        contract_address = tx_receipt.contractAddress
        print(f"[+] Contract deployed at address: {contract_address}")
        return contract_address, tx_hash.hex()

    # 6. Verifierアドレスの確認
    verifier_address = ENV_VARS.get("LEAN_VERIFIER_ADDRESS")
    if not verifier_address:
        print("[-] LEAN_VERIFIER_ADDRESS not found in .env!")
        sys.exit(1)
    print(f"[+] Using verifier address: {verifier_address}")

    # 7. FluidControlOracleのデプロイ
    print("\n=== Deploying FluidControlOracle ===")
    oracle_address, oracle_tx = deploy_contract(oracle_abi, oracle_bin, args=(verifier_address,))

    # 8. 環境変数の更新
    print("\n[*] Updating .env file...")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("LEAN_CONTRACT_ADDRESS="):
                    pass
                else:
                    lines.append(line)
                    
    lines.append(f"LEAN_CONTRACT_ADDRESS={oracle_address}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print("[+] .env file updated successfully.")
    print("\n--- Summary ---")
    print(f"Oracle Tx Hash: {oracle_tx}")
    print(f"Oracle Address: {oracle_address}")

if __name__ == '__main__':
    run_deployment()
