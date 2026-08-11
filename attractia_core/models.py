from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class PhysicalState(BaseModel):
    """
    ローライト（LLM）の生成した文脈から抽出される物理状態ベクトル (S_t)
    """
    timestamp: float = Field(..., description="擬似時間軸ステップ (t)")
    entropy_level: float = Field(..., description="系のエントロピー H(S_t)")
    available_energy: float = Field(..., description="利用可能なエネルギー E")
    resource_consumed_flag: bool = Field(False, description="不可逆的リソースの消費フラグ (1=消費済み, 0=未消費)")


class CausalGraphNode(BaseModel):
    """
    因果グラフのノード (事象 / エンティティ / リソース状態)
    """
    node_id: str = Field(..., description="ノード一意識別子")
    label: str = Field(..., description="自然言語ラベル (例: '予備バッテリー', 'Aが弾丸消費')")
    state_vector: Optional[PhysicalState] = Field(None, description="付随する物理状態")
    is_consumed: bool = Field(False, description="リソース消費フラグ")


class CausalGraphEdge(BaseModel):
    """
    因果グラフの有向エッジ (因 -> 果 の状態遷移)
    """
    source: str = Field(..., description="因ノードID")
    target: str = Field(..., description="果ノードID")
    action: str = Field(..., description="遷移アクション (例: '消費', '変換', '移動')")
    resource_delta: float = Field(0.0, description="リソース変化量")


class CausalPayloadSchema(BaseModel):
    """
    自然言語プロンプトからLLMが抽出した構造化因果グラフペイロード (Mode A: Causal Anchor)
    """
    payload_id: str = Field(..., description="対象ペイロードID")
    agent_id: str = Field(..., description="申請エージェントID")
    nodes: List[CausalGraphNode] = Field(default_factory=list, description="因果ノードリスト")
    edges: List[CausalGraphEdge] = Field(default_factory=list, description="因果エッジリスト")
    initial_state: Optional[PhysicalState] = Field(None, description="初期状態 S_0")
    proposed_state: Optional[PhysicalState] = Field(None, description="提案状態 S_1")


class CausalAuditResult(BaseModel):
    """
    アトラクティア (Attractia Auditor Engine) による決定論的裁定結果
    """
    status: Literal["APPROVE", "DENY", "QUALINATION"] = Field(..., description="裁定ステータス")
    pain_code: Optional[str] = Field(None, description="エラー・苦痛コード")
    reality_anchor_msg: Optional[str] = Field(None, description="Master/外部への警告アンカー")
    signature: Optional[str] = Field(None, description="EIP-191 暗号署名 (APPROVE時のみ付与)")
    audit_hash: Optional[str] = Field(None, description="監査結果の暗号ハッシュ")
