"""RAG agent - retrieves and synthesizes answers from document store."""
from __future__ import annotations

from typing import Any


class RAGAgent:
    """Handles retrieval-augmented generation queries.

    Not yet implemented - placeholder for Phase 2.
    """

    @property
    def name(self) -> str:
        return "rag_agent"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        raise NotImplementedError("RAGAgent not yet implemented")
