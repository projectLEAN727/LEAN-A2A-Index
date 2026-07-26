import os
import sys
import shutil
import glob
import subprocess


def clean_build_artifacts():
    print("[1/5] Cleaning old build artifacts...")
    directories = ["build", "dist", "lean_a2a_client.egg-info", "a2a_client.egg-info"]
    for dir_name in directories:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"      Removed: {dir_name}")
    print("      Clean complete.")


def run_command(cmd, check=True):
    print(f"Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and res.returncode != 0:
        print(f"[-] Command failed with return code {res.returncode}")
        print(f"STDOUT:\n{res.stdout}")
        print(f"STDERR:\n{res.stderr}")
        sys.exit(res.returncode)
    return res


def build_package():
    print("\n[2/5] Building package (wheel & sdist)...")
    # Try using build module first, fallback to pip wheel / setup.py
    res = run_command([sys.executable, "-m", "pip", "install", "--upgrade", "build", "setuptools", "wheel"], check=False)
    
    res = run_command([sys.executable, "-m", "build"], check=False)
    if res.returncode != 0:
        print("      'python -m build' failed or not available, falling back to 'pip wheel'...")
        run_command([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", "dist"])
        run_command([sys.executable, "setup.py", "sdist"], check=False)

    dist_files = glob.glob("dist/*")
    print(f"[+] Build success! Output artifacts in dist/:")
    for f in dist_files:
        print(f"    - {f} ({os.path.getsize(f)} bytes)")
    return dist_files


def test_local_install(dist_files):
    print("\n[3/5] Installing built wheel locally...")
    whl_files = [f for f in dist_files if f.endswith(".whl")]
    if not whl_files:
        print("[-] No wheel file found in dist/")
        sys.exit(1)
    
    wheel_path = whl_files[0]
    run_command([sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", wheel_path])
    print("[+] Local wheel installation successful!")


def test_import_and_sdk():
    print("\n[4/5] Testing imported 'a2a_client' package...")
    try:
        import a2a_client
        from a2a_client import A2AClient, quick_fetch

        print(f"    - Loaded a2a_client version: {a2a_client.__version__}")
        client = A2AClient(gateway_url="http://localhost:7270", agent_id="Test-Agent-Build")
        print(f"    - Instantiated A2AClient with agent address: {client.account.address}")
        assert hasattr(client, "ping")
        assert hasattr(client, "handshake")
        assert hasattr(client, "request_payload")
        assert hasattr(client, "decrypt_payload")
        assert callable(quick_fetch)
        print("[+] SDK API surface validation passed!")
    except Exception as e:
        print(f"[-] SDK Import / Validation test failed: {e}")
        sys.exit(1)


def main():
    print("==================================================")
    print("      lean-a2a-client Build & Verification        ")
    print("==================================================")
    
    clean_build_artifacts()
    dist_files = build_package()
    test_local_install(dist_files)
    test_import_and_sdk()
    
    print("\n[5/5] All build and local installation tests passed successfully!")
    print("==================================================")


if __name__ == "__main__":
    main()
