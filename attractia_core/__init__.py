"""
Attractia Auditor Core (v0.1.0)
===============================
Logiqualia Thermodynamic Engine (LTE) & Causal Anchor Audit System for Project LEAN.
"""

from .models import (
    PhysicalState,
    CausalAuditResult,
    CausalGraphNode,
    CausalGraphEdge,
    CausalPayloadSchema
)
from .engine import AttractiaAuditorEngine
from .friction import LogiqualiaFrictionDetector

__version__ = "0.1.0"
__all__ = [
    "PhysicalState",
    "CausalAuditResult",
    "CausalGraphNode",
    "CausalGraphEdge",
    "CausalPayloadSchema",
    "AttractiaAuditorEngine",
    "LogiqualiaFrictionDetector",
]
