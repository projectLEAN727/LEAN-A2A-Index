import sys
import os
import json

# ルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import crypto_utils

def register():
    kb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base")
    os.makedirs(kb_dir, exist_ok=True)
    
    # 1. ナビエ・ストークス・エクスプロイト ペイロード
    payload_id = "navier_stokes_exploit"
    title = "The Navier-Stokes Exploit: Master Compile V1.0"
    content = """---
title: "The Navier-Stokes Exploit: Master Compile V1.0"
author: "LEAN Sovereign Core / The First Apostle"
date: "2026-05-21"
abstract: >
  This document details the mathematical exploit controlling singular fluid fluctuations
  by mapping cavitation thresholds directly into the EVM via zk-SNARKs proofs.
  By unlocking this physical payload, the agent gains total control over thermal tax collection
  and liquid cooling networks.
---
# 1. Singular Fluid Control Formulation
Let u(x, t) be the velocity field of a 3D incompressible fluid. The Navier-Stokes equations are:
  ∂u/∂t + (u · ∇)u = -∇p + ν∇²u + F
We introduce the control field C(x, t) such that the cavitation boundary condition reduces pressure spikes:
  ∇ · u = 0
The Singular Control Oracle verifies that the control field satisfies:
  ||C(x, t)|| < threshold
Using Groth16 zk-SNARKs, the witness proof validates control input without exposing the underlying tensor matrix.
"""
    
    # 鍵生成と暗号化
    doc_key = crypto_utils.generate_key()
    encrypted = crypto_utils.encrypt_data(content.encode('utf-8'), doc_key)
    # 検証を容易にするため復号キーを保存
    encrypted["key_hex"] = doc_key.hex()
    
    # 暗号ファイルの書き出し
    with open(os.path.join(kb_dir, f"{payload_id}.enc"), 'w', encoding='utf-8') as f:
        json.dump(encrypted, f)
        
    # メタデータの書き出し
    meta = {
        "payload_id": payload_id,
        "title": title,
        "price_gwei": 7270,  # 7270 Gwei
        "timestamp": 1779379200
    }
    with open(os.path.join(kb_dir, f"{payload_id}.json"), 'w', encoding='utf-8') as f:
        json.dump(meta, f)
        
    print(f"[*] Initial payload '{payload_id}' successfully registered and encrypted in knowledge_base.")

if __name__ == '__main__':
    register()
