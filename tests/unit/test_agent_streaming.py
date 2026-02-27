"""Unit tests for agent execute_stream() methods.

All dependencies (LLM, retrievers, DuckDB) are replaced with lightweight
mocks so no external services are required.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest

from src.models import AgentStatusEvent, TokenEvent, SourcesEvent, RetrievalResult, Chunk
from src.agents.orchestrator import OrchestratorAgent
from src.agents.rag_agent import RAGAgent
from src.agents.sql_agent import SQLAgent


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class MockLLM:
    """Returns pre-recorded responses for generate() and streams tokens for stream()."""

    def __init__(self, generate_responses: list[str], stream_tokens: list[str] | None = None) -> None:
        self._generate_responses = list(generate_responses)
        self._generate_call_count = 0
        self._stream_tokens = stream_tokens or ["Hello", " world"]

    async def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        result = self._generate_responses[self._generate_call_count]
        self._generate_call_count += 1
        return result

    async def stream(self, prompt: str, *, max_tokens: int = 4096) -> AsyncIterator[str]:
        for token in self._stream_tokens:
            yield token


def _make_retrieval_result(content: str = "test chunk", score: float = 0.9) -> RetrievalResult:
    chunk = Chunk(
        id=uuid4(),
        document_id=uuid4(),
        content=content,
        token_count=10,
        index=0,
    )
    return RetrievalResult(chunk=chunk, score=score, source="vector")


class MockRetriever:
    """Returns a fixed list of retrieval results."""

    def __init__(self, results: list[RetrievalResult] | None = None) -> None:
        self._results = results or [_make_retrieval_result()]

    async def retrieve(self, query: str, *, top_k: int = 10) -> list[RetrievalResult]:
        return self._results


class MockDuckDBStore:
    """Returns fixed schema and query results."""

    def __init__(self, rows: list[dict[str, Any]] | None = None, fail_first: bool = False) -> None:
        self._rows = rows or [{"quarter": "Q4 2025", "total_revenue_m": 847.0}]
        self._fail_first = fail_first
        self._exec_count = 0

    async def get_schema(self) -> str:
        return "CREATE TABLE quarterly_financials (quarter TEXT, total_revenue_m FLOAT)"

    async def execute(self, sql: str) -> list[dict[str, Any]]:
        self._exec_count += 1
        if self._fail_first and self._exec_count == 1:
            raise RuntimeError("Table 'bar' not found")
        return self._rows


# ---------------------------------------------------------------------------
# RAG Agent streaming tests
# ---------------------------------------------------------------------------


class TestRAGAgentStream:
    async def test_yields_status_sources_status_tokens(self) -> None:
        """execute_stream yields: status(retrieving) -> sources -> status(generating) -> tokens."""
        llm = MockLLM(generate_responses=[], stream_tokens=["The", " answer"])
        retriever = MockRetriever()
        agent = RAGAgent(
            hybrid_retriever=retriever,  # type: ignore[arg-type]
            vector_retriever=retriever,  # type: ignore[arg-type]
            llm_provider=llm,  # type: ignore[arg-type]
        )

        events = []
        async for event in agent.execute_stream("What is X?"):
            events.append(event)

        assert len(events) == 5
        assert isinstance(events[0], AgentStatusEvent)
        assert events[0].phase == "retrieving"
        assert isinstance(events[1], SourcesEvent)
        assert len(events[1].sources) == 1
        assert isinstance(events[2], AgentStatusEvent)
        assert events[2].phase == "generating"
        assert isinstance(events[3], TokenEvent)
        assert events[3].token == "The"
        assert isinstance(events[4], TokenEvent)
        assert events[4].token == " answer"

    async def test_vector_only_strategy(self) -> None:
        """Setting strategy to vector_only uses the vector retriever."""
        llm = MockLLM(generate_responses=[], stream_tokens=["ok"])
        hybrid = MockRetriever([_make_retrieval_result("hybrid")])
        vector = MockRetriever([_make_retrieval_result("vector")])
        agent = RAGAgent(
            hybrid_retriever=hybrid,  # type: ignore[arg-type]
            vector_retriever=vector,  # type: ignore[arg-type]
            llm_provider=llm,  # type: ignore[arg-type]
        )

        events = []
        async for event in agent.execute_stream("Q?", context={"strategy": "vector_only"}):
            events.append(event)

        sources_event = [e for e in events if isinstance(e, SourcesEvent)][0]
        assert sources_event.sources[0].chunk.content == "vector"
        assert sources_event.strategy == "vector_only"


# ---------------------------------------------------------------------------
# SQL Agent streaming tests
# ---------------------------------------------------------------------------


class TestSQLAgentStream:
    async def test_yields_status_sequence_then_tokens(self) -> None:
        """execute_stream yields: generating_sql -> executing -> synthesizing -> tokens."""
        llm = MockLLM(
            generate_responses=["SELECT 1"],
            stream_tokens=["Revenue", " was", " $847M"],
        )
        store = MockDuckDBStore()
        agent = SQLAgent(duckdb_store=store, llm_provider=llm)  # type: ignore[arg-type]

        events = []
        async for event in agent.execute_stream("What was revenue?"):
            events.append(event)

        statuses = [e for e in events if isinstance(e, AgentStatusEvent)]
        tokens = [e for e in events if isinstance(e, TokenEvent)]

        assert len(statuses) == 3
        assert statuses[0].phase == "generating_sql"
        assert statuses[1].phase == "executing"
        assert statuses[2].phase == "synthesizing"
        assert len(tokens) == 3
        assert "".join(t.token for t in tokens) == "Revenue was $847M"

    async def test_retry_emits_retrying_status(self) -> None:
        """When the first SQL execution fails, a 'retrying' status is emitted."""
        llm = MockLLM(
            generate_responses=[
                "SELECT foo FROM bar",   # first attempt (will fail)
                "SELECT 1",              # retry (will succeed)
            ],
            stream_tokens=["ok"],
        )
        store = MockDuckDBStore(fail_first=True)
        agent = SQLAgent(duckdb_store=store, llm_provider=llm)  # type: ignore[arg-type]

        events = []
        async for event in agent.execute_stream("Show revenue"):
            events.append(event)

        statuses = [e for e in events if isinstance(e, AgentStatusEvent)]
        phases = [s.phase for s in statuses]
        assert "retrying" in phases
        assert "synthesizing" in phases


# ---------------------------------------------------------------------------
# Orchestrator streaming tests
# ---------------------------------------------------------------------------


class MockStreamingSQLAgent:
    name = "sql_agent"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        return "SQL result"

    async def execute_stream(
        self, query: str, context: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentStatusEvent | TokenEvent]:
        yield AgentStatusEvent(agent="sql_agent", phase="generating_sql", message="SQL Agent: Generating SQL query...")
        yield TokenEvent(token="SQL answer")


class MockStreamingRAGAgent:
    name = "rag_agent"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        return "RAG result"

    async def execute_stream(
        self, query: str, context: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentStatusEvent | TokenEvent | SourcesEvent]:
        yield AgentStatusEvent(agent="rag_agent", phase="retrieving", message="RAG Agent: Retrieving documents...")
        yield TokenEvent(token="RAG answer")


class TestOrchestratorStream:
    async def test_routes_to_sql_agent_stream(self) -> None:
        """LLM classification of 'sql' should delegate to SQL agent's execute_stream."""
        orchestrator = OrchestratorAgent(
            llm_provider=MockLLM(generate_responses=["sql"]),  # type: ignore[arg-type]
            sql_agent=MockStreamingSQLAgent(),  # type: ignore[arg-type]
            rag_agent=MockStreamingRAGAgent(),  # type: ignore[arg-type]
        )

        events = []
        async for event in orchestrator.execute_stream("What was Q4 revenue?"):
            events.append(event)

        # Should start with orchestrator classifying + routing, then SQL agent events
        assert isinstance(events[0], AgentStatusEvent)
        assert events[0].agent == "orchestrator"
        assert events[0].phase == "classifying"

        assert isinstance(events[1], AgentStatusEvent)
        assert events[1].agent == "orchestrator"
        assert events[1].phase == "routing"

        # SQL agent events follow
        assert isinstance(events[2], AgentStatusEvent)
        assert events[2].agent == "sql_agent"

        assert isinstance(events[3], TokenEvent)
        assert events[3].token == "SQL answer"

    async def test_routes_to_rag_agent_stream(self) -> None:
        """LLM classification of 'rag' should delegate to RAG agent's execute_stream."""
        orchestrator = OrchestratorAgent(
            llm_provider=MockLLM(generate_responses=["rag"]),  # type: ignore[arg-type]
            sql_agent=MockStreamingSQLAgent(),  # type: ignore[arg-type]
            rag_agent=MockStreamingRAGAgent(),  # type: ignore[arg-type]
        )

        events = []
        async for event in orchestrator.execute_stream("What is the refund policy?"):
            events.append(event)

        assert events[0].agent == "orchestrator"
        assert events[1].agent == "orchestrator"
        assert events[1].phase == "routing"
        assert events[2].agent == "rag_agent"
        assert isinstance(events[3], TokenEvent)
        assert events[3].token == "RAG answer"

    async def test_fallback_to_rag_on_unknown(self) -> None:
        """An unrecognised classification falls back to RAG agent stream."""
        orchestrator = OrchestratorAgent(
            llm_provider=MockLLM(generate_responses=["I'm not sure"]),  # type: ignore[arg-type]
            sql_agent=MockStreamingSQLAgent(),  # type: ignore[arg-type]
            rag_agent=MockStreamingRAGAgent(),  # type: ignore[arg-type]
        )

        events = []
        async for event in orchestrator.execute_stream("Tell me about culture"):
            events.append(event)

        # Should route to RAG (the default)
        rag_events = [e for e in events if isinstance(e, AgentStatusEvent) and e.agent == "rag_agent"]
        assert len(rag_events) > 0
