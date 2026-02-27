"""Unit tests for OrchestratorAgent.

All dependencies (LLM, SQLAgent, RAGAgent) are replaced with lightweight
mocks so no external services are required.
"""
from __future__ import annotations

from typing import Any

import pytest

from src.agents.orchestrator import OrchestratorAgent


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class MockLLM:
    """Returns a single fixed response for every generate() call."""

    def __init__(self, response: str) -> None:
        self._response = response

    async def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        return self._response


class MockSQLAgent:
    name = "sql_agent"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        return "SQL result: answered from database"


class MockRAGAgent:
    name = "rag_agent"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        return "RAG result: answered from documents"


# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------


def _make_orchestrator(llm_response: str) -> OrchestratorAgent:
    return OrchestratorAgent(
        llm_provider=MockLLM(llm_response),  # type: ignore[arg-type]
        sql_agent=MockSQLAgent(),  # type: ignore[arg-type]
        rag_agent=MockRAGAgent(),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Tests — routing logic
# ---------------------------------------------------------------------------


class TestOrchestratorRouting:
    async def test_routes_to_sql_agent(self) -> None:
        """LLM classification of 'sql' should delegate to the SQL agent."""
        orchestrator = _make_orchestrator("sql")

        result = await orchestrator.execute("What was Q4 2025 revenue?")

        assert result == "SQL result: answered from database"

    async def test_routes_to_rag_agent(self) -> None:
        """LLM classification of 'rag' should delegate to the RAG agent."""
        orchestrator = _make_orchestrator("rag")

        result = await orchestrator.execute("What is the company refund policy?")

        assert result == "RAG result: answered from documents"

    async def test_fallback_to_rag_on_unknown(self) -> None:
        """An unrecognised classification label should fall back to the RAG agent."""
        orchestrator = _make_orchestrator("I'm not sure")

        result = await orchestrator.execute("Tell me about the team culture")

        assert result == "RAG result: answered from documents"

    async def test_sql_classification_case_insensitive(self) -> None:
        """'SQL' (uppercase) should still route to the SQL agent."""
        orchestrator = _make_orchestrator("SQL")

        result = await orchestrator.execute("How many employees do we have?")

        assert result == "SQL result: answered from database"

    async def test_classify_with_extra_text(self) -> None:
        """A response containing 'sql' embedded in extra text routes to SQL agent."""
        orchestrator = _make_orchestrator("I think sql is correct")

        result = await orchestrator.execute("Show me revenue by segment")

        assert result == "SQL result: answered from database"
