"""Orchestrator agent - routes queries to specialized agents."""
from __future__ import annotations

from typing import Any


class OrchestratorAgent:
    """Routes natural language queries to the appropriate specialized agent.

    Not yet implemented - placeholder for Phase 2.
    """

    @property
    def name(self) -> str:
        return "orchestrator"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        raise NotImplementedError("OrchestratorAgent not yet implemented")
