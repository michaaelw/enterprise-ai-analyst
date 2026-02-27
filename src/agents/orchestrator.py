"""Orchestrator agent - routes queries to specialized agents."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Union

import structlog

from src.integrations.llm_providers.base import LLMProvider
from src.models import AgentStatusEvent, TokenEvent, SourcesEvent
from src.agents.sql_agent import SQLAgent
from src.agents.rag_agent import RAGAgent

logger = structlog.get_logger(__name__)

_CLASSIFICATION_PROMPT = """\
You are a query router. Classify the user query below as exactly one of two categories:

  sql  - The query asks about financial data, metrics, numbers, revenue, headcount,
         margins, or any quantitative question that can be answered from structured
         database tables.

  rag  - The query asks about policies, procedures, documents, qualitative
         information, explanations, or anything that requires searching through
         unstructured text.

Respond with ONLY the single word "sql" or "rag". Do not include any other text,
punctuation, or explanation.

User query: {query}"""


class OrchestratorAgent:
    """Routes natural language queries to the appropriate specialized agent.

    Uses the LLM to classify each incoming query as either a structured-data
    (SQL) question or a document-retrieval (RAG) question, then delegates
    execution to the corresponding agent.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        sql_agent: SQLAgent,
        rag_agent: RAGAgent,
    ) -> None:
        self._llm_provider = llm_provider
        self._sql_agent = sql_agent
        self._rag_agent = rag_agent

    @property
    def name(self) -> str:
        return "orchestrator"

    async def _classify(self, query: str) -> str:
        """Classify *query* as ``"sql"`` or ``"rag"`` using the LLM.

        The LLM is asked to respond with only the routing label.  The raw
        response is normalised to lowercase and checked for the literal
        substring ``"sql"``; anything else falls back safely to ``"rag"``.
        """
        prompt = _CLASSIFICATION_PROMPT.format(query=query)
        raw = await self._llm_provider.generate(prompt, temperature=0.0)
        label = raw.strip().lower()
        result = "sql" if "sql" in label else "rag"
        logger.info(
            "query_classified",
            query=query,
            raw_response=raw.strip(),
            classification=result,
        )
        return result

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        """Route *query* to the appropriate agent and return its response."""
        intent = await self._classify(query)
        logger.info("routing_query", intent=intent, query=query)

        if intent == "sql":
            return await self._sql_agent.execute(query, context)

        return await self._rag_agent.execute(query, context)

    async def execute_stream(
        self, query: str, context: dict[str, Any] | None = None,
    ) -> AsyncIterator[Union[AgentStatusEvent, TokenEvent, SourcesEvent]]:
        """Stream classification + delegation as a sequence of events."""
        yield AgentStatusEvent(
            agent="orchestrator", phase="classifying",
            message="Classifying query...",
        )

        intent = await self._classify(query)
        logger.info("routing_query", intent=intent, query=query)

        if intent == "sql":
            yield AgentStatusEvent(
                agent="orchestrator", phase="routing",
                message="Routing to SQL Agent...",
            )
            async for event in self._sql_agent.execute_stream(query, context):
                yield event
        else:
            yield AgentStatusEvent(
                agent="orchestrator", phase="routing",
                message="Routing to RAG Agent...",
            )
            async for event in self._rag_agent.execute_stream(query, context):
                yield event
