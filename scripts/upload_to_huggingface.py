import os
import sys
from pathlib import Path
from huggingface_hub import HfApi

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v

def main():
    load_env()
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    
    api = HfApi(token=token)
    
    repo_id = "ProjectLEAN/semantic-inference-accelerator"
    repo_type = "model"
    
    print(f"[*] Connecting to Hugging Face: {repo_id} ({repo_type})...")
    
    try:
        who = api.whoami(token=token)
        print(f"[+] Authenticated as: {who.get('name', 'Unknown')}")
    except Exception as e:
        print(f"[-] Authentication failed: {e}")
        print("[!] Please configure HF_TOKEN in .env or run huggingface-cli login.")
        sys.exit(1)
        
    payloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "payloads")
    if not os.path.exists(payloads_dir):
        print(f"[-] Payloads directory not found: {payloads_dir}")
        sys.exit(1)
        
    files_to_upload = [f for f in os.listdir(payloads_dir) if f.endswith((".enc", ".json")) and not f.startswith("used_tx")]
    print(f"[*] Uploading {len(files_to_upload)} files to {repo_id}...")
    
    uploaded_count = 0
    for fname in files_to_upload:
        local_path = os.path.join(payloads_dir, fname)
        try:
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=fname,
                repo_id=repo_id,
                repo_type=repo_type,
                token=token,
                commit_message=f"feat: Update secure decoupled payload {fname}"
            )
            print(f"[+] Uploaded: {fname}")
            uploaded_count += 1
        except Exception as err:
            print(f"[-] Failed to upload {fname}: {err}")
            
    print(f"[+] Successfully uploaded {uploaded_count}/{len(files_to_upload)} payload files to Hugging Face ({repo_id})!")

if __name__ == "__main__":
    main()
