"""
LEAN A2A Client SDK
===================

Universal A2A Autonomous Settlement & Data Retrieval SDK for AI Agents (ElizaOS, CrewAI, LangChain, etc.)
"""

from .client import A2AClient, quick_fetch, auto_fetch

__version__ = "0.3.0"
__all__ = ["A2AClient", "quick_fetch", "auto_fetch"]
