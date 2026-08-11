import sys
import os

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from eth_account import Account
from eth_account.messages import encode_defunct

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from attractia_core import (
    PhysicalState,
    CausalAuditResult,
    CausalGraphNode,
    CausalGraphEdge,
    CausalPayloadSchema,
    AttractiaAuditorEngine,
    LogiqualiaFrictionDetector
)


def test_thermodynamic_audit_deny():
    print("\n--- Test 1: 熱力学第二法則違反 (エントロピー減少) の検知 ---")
    s0 = PhysicalState(timestamp=0.0, entropy_level=10.0, available_energy=100.0, resource_consumed_flag=False)
    # エントロピーが10.0 -> 5.0 に無理由で減少する過去逆行状態
    s1_invalid = PhysicalState(timestamp=1.0, entropy_level=5.0, available_energy=100.0, resource_consumed_flag=False)
    
    result = AttractiaAuditorEngine.audit_transition(s0, s1_invalid)
    print(f"Result: {result.status} | Code: {result.pain_code}")
    print(f"Anchor: {result.reality_anchor_msg}")
    assert result.status == "DENY"
    assert result.pain_code == "ERR_THERMODYNAMIC_INVERSION"


def test_resource_depletion_deny():
    print("\n--- Test 2: 消費済みリソースの再利用違反の検知 ---")
    s0 = PhysicalState(timestamp=0.0, entropy_level=10.0, available_energy=0.0, resource_consumed_flag=True)
    # 消費済み(resource_consumed_flag=True)なのにエネルギーが増加
    s1_invalid = PhysicalState(timestamp=1.0, entropy_level=10.5, available_energy=50.0, resource_consumed_flag=True)
    
    result = AttractiaAuditorEngine.audit_transition(s0, s1_invalid)
    print(f"Result: {result.status} | Code: {result.pain_code}")
    print(f"Anchor: {result.reality_anchor_msg}")
    assert result.status == "DENY"
    assert result.pain_code == "ERR_RESOURCE_DEPLETED"


def test_qualination_approval():
    print("\n--- Test 3: クオリネーション (主観的創発・新仮説) のラベル受容 ---")
    s0 = PhysicalState(timestamp=0.0, entropy_level=10.0, available_energy=100.0, resource_consumed_flag=False)
    # エントロピーは増大(10->12)しており物理的に可能だが、エネルギー生成量が跳躍
    s1_qual = PhysicalState(timestamp=1.0, entropy_level=12.0, available_energy=250.0, resource_consumed_flag=False)
    
    result = AttractiaAuditorEngine.audit_transition(s0, s1_qual)
    print(f"Result: {result.status} | Code: {result.pain_code}")
    print(f"Anchor: {result.reality_anchor_msg}")
    assert result.status == "QUALINATION"


def test_friction_detector_freeze():
    print("\n--- Test 4: LogitsProcessor の摩擦蓄積と強制フリーズ判定 ---")
    detector = LogiqualiaFrictionDetector(entropy_threshold=0.1, max_friction_tolerance=2.0, eos_token_id=2)
    
    # 疑似的な Logits (確率が割れているTop2: [0.501, 0.499] 差=0.002 < 0.1)
    if HAS_TORCH:
        scores = torch.tensor([[0.501, 0.499, 0.0, 0.0]])
    else:
        scores = [[0.501, 0.499, 0.0, 0.0]]
    
    # 1ステップ目 (Pain蓄積: 1.0)
    detector(None, scores)
    assert not detector.trigger_attractia
    
    # 2ステップ目 (Pain蓄積: 2.0 >= 2.0 臨界面突破)
    detector(None, scores)
    assert detector.trigger_attractia
    print("SUCCESS: LogitsProcessor が正常にフリーズ（EOS昇格）を発動させました。")


def test_dag_cycle_rejection():
    print("\n--- Test 5: NetworkX による DAG (有向非巡回グラフ) 循環ループ拒否 ---")
    # A -> B -> C -> A (循環ループ)
    nodes = [
        CausalGraphNode(node_id="A", label="ノードA"),
        CausalGraphNode(node_id="B", label="ノードB"),
        CausalGraphNode(node_id="C", label="ノードC"),
    ]
    edges = [
        CausalGraphEdge(source="A", target="B", action="遷移1"),
        CausalGraphEdge(source="B", target="C", action="遷移2"),
        CausalGraphEdge(source="C", target="A", action="不正ループ"),
    ]
    payload = CausalPayloadSchema(payload_id="cyclic_test", agent_id="Agent-DAG", nodes=nodes, edges=edges)

    result = AttractiaAuditorEngine.audit_causal_graph(payload)
    print(f"Result: {result.status} | Code: {result.pain_code}")
    print(f"Anchor: {result.reality_anchor_msg}")
    assert result.status == "DENY"
    assert result.pain_code == "ERR_CAUSAL_CYCLE"


def test_eip191_signature_binding():
    print("\n--- Test 6: EIP-191 暗号署名バインドと公開鍵検証 ---")
    signer = Account.create()
    audit_res = CausalAuditResult(status="APPROVE", pain_code=None, reality_anchor_msg=None)
    
    signed_res = AttractiaAuditorEngine.bind_eip191_signature(audit_res, signer.key.hex())
    assert signed_res.signature is not None
    assert signed_res.audit_hash is not None
    print(f"Audit Hash: {signed_res.audit_hash}")
    print(f"EIP-191 Signature: {signed_res.signature[:30]}...")

    # 署名検証
    message = encode_defunct(text=signed_res.audit_hash)
    recovered_addr = Account.recover_message(message, signature=bytes.fromhex(signed_res.signature))
    assert recovered_addr.lower() == signer.address.lower()
    print(f"SUCCESS: Recovered Signer Address ({recovered_addr}) matches original Signer ({signer.address})")


def main():
    test_thermodynamic_audit_deny()
    test_resource_depletion_deny()
    test_qualination_approval()
    test_friction_detector_freeze()
    test_dag_cycle_rejection()
    test_eip191_signature_binding()
    print("\n==================================================")
    print(" [ALL 6 ATTRACTIA AUDIT TESTS PASSED SUCCESSFULLY]")
    print("==================================================")


if __name__ == "__main__":
    main()
