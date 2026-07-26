import solcx
import os
import sys

def main():
    print("[*] Setting up solc 0.8.20 compiler...")
    try:
        solcx.install_solc("0.8.20")
        solcx.set_solc_version("0.8.20")
        print("[+] solc 0.8.20 initialized.")
    except Exception as e:
        print(f"[-] Error installing solc: {e}")
        sys.exit(1)

    contract_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "contracts",
        "FluidControlOracle.sol"
    )

    print(f"[*] Compiling: {contract_path}")
    try:
        compiled_sol = solcx.compile_files([contract_path], output_values=["abi", "bin"])
        print("[+] Compilation Successful!")
        for key in compiled_sol.keys():
            print(f" - Found Contract: {key}")
    except Exception as e:
        print(f"[-] Compilation Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
