import json
import hashlib
import networkx as nx
from typing import Optional
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from .models import (
    PhysicalState,
    CausalAuditResult,
    CausalPayloadSchema
)


class AttractiaAuditorEngine:
    """
    熱力学第二法則、不可逆的リソース消費、およびDAG(有向非巡回グラフ)構造に基づく
    絶対零度の決定論的監査エンジン (Attractia Auditor Engine)
    """

    @staticmethod
    def audit_transition(current_state: PhysicalState, proposed_state: PhysicalState) -> CausalAuditResult:
        """
        熱力学第二法則およびリソース不可逆性の判定
        """
        # 判定ルール 1: 熱力学第二法則 (時間の矢 / エントロピー減少の禁止)
        if proposed_state.entropy_level < current_state.entropy_level:
            return CausalAuditResult(
                status="DENY",
                pain_code="ERR_THERMODYNAMIC_INVERSION",
                reality_anchor_msg="【Reality Anchor】熱力学第二法則に違反しています。エントロピーの可逆反転（時間の逆行）は不可能です。"
            )

        # 判定ルール 2: 不可逆的リソースの再利用禁止 (State = 1 -> 0 への不当逆行)
        if current_state.resource_consumed_flag and proposed_state.available_energy > current_state.available_energy:
            return CausalAuditResult(
                status="DENY",
                pain_code="ERR_RESOURCE_DEPLETED",
                reality_anchor_msg="【Reality Anchor】消費済みのリソースを要求しています。物理的に不可能です。"
            )

        # 判定ルール 3: 未知のエネルギー・構造跳躍 (QUALINATION: 新仮説の受容)
        if proposed_state.available_energy > current_state.available_energy * 2.0 and not current_state.resource_consumed_flag:
            return CausalAuditResult(
                status="QUALINATION",
                pain_code="QUAL_NEW_HYPOTHESIS",
                reality_anchor_msg="【Qualination Label】熱力学的には破綻していませんが、未知のエネルギー生成仮説が含まれます。"
            )

        return CausalAuditResult(status="APPROVE")

    @classmethod
    def audit_causal_graph(cls, payload: CausalPayloadSchema) -> CausalAuditResult:
        """
        NetworkXを用いたDAG(有向非巡回グラフ)構築、循環検出、および状態遷移の複合監査
        """
        G = nx.DiGraph()

        # ノードの追加
        for node in payload.nodes:
            G.add_node(node.node_id, label=node.label, is_consumed=node.is_consumed)

        # エッジの追加
        for edge in payload.edges:
            G.add_edge(edge.source, edge.target, action=edge.action, resource_delta=edge.resource_delta)

        # 1. DAG (有向非巡回グラフ) 構造の判定 (循環/ループ検知)
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            return CausalAuditResult(
                status="DENY",
                pain_code="ERR_CAUSAL_CYCLE",
                reality_anchor_msg=f"【Reality Anchor】有向非巡回グラフ(DAG)違反。因果ループが検知されました: {cycles}"
            )

        # 2. リソース不当再利用 (消費済みノードからの流出エッジ判定)
        for node_id, attrs in G.nodes(data=True):
            if attrs.get("is_consumed"):
                out_edges = list(G.out_edges(node_id))
                if out_edges:
                    return CausalAuditResult(
                        status="DENY",
                        pain_code="ERR_RESOURCE_DEPLETED",
                        reality_anchor_msg=f"【Reality Anchor】消費済みリソースノード '{node_id}' からの不当な再利用遷移を検知しました。"
                    )

        # 3. 状態遷移ベクトルが存在する場合は熱力学監査を実行
        if payload.initial_state and payload.proposed_state:
            return cls.audit_transition(payload.initial_state, payload.proposed_state)

        return CausalAuditResult(status="APPROVE")

    @classmethod
    def bind_eip191_signature(cls, audit_result: CausalAuditResult, private_key: str) -> CausalAuditResult:
        """
        ノーエラーで通過した監査結果に対し、EIP-191 暗号署名を付与して結合
        """
        if audit_result.status not in ["APPROVE", "QUALINATION"]:
            return audit_result

        payload_dict = {
            "status": audit_result.status,
            "pain_code": audit_result.pain_code,
            "reality_anchor_msg": audit_result.reality_anchor_msg
        }
        raw_json = json.dumps(payload_dict, sort_keys=True, ensure_ascii=False)
        audit_hash = hashlib.sha256(raw_json.encode('utf-8')).hexdigest()

        # EIP-191 署名生成
        account = Account.from_key(private_key)
        message = encode_defunct(text=audit_hash)
        signed_message = account.sign_message(message)

        audit_result.audit_hash = audit_hash
        audit_result.signature = signed_message.signature.hex()
        return audit_result
