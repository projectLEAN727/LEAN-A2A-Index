import os
import json

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    payloads_dir = os.path.join(root_dir, "payloads")
    
    if not os.path.exists(payloads_dir):
        print(f"[-] Payloads directory not found at: {payloads_dir}")
        return

    json_files = [f for f in os.listdir(payloads_dir) if f.endswith(".json")]
    
    print(f"[*] Found {len(json_files)} metadata files in {payloads_dir}")
    
    for filename in json_files:
        filepath = os.path.join(payloads_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 追加するフィールド
            data["currency"] = "MNT"
            data["verification_contract"] = "0xA8b053A0B76b564E57c011424ECCde68bA63664E"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                
            print(f"[+] Successfully updated: {filename}")
        except Exception as e:
            print(f"[-] Error updating {filename}: {e}")

if __name__ == "__main__":
    main()
