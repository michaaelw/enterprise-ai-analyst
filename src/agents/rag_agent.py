"""RAG agent - retrieves and synthesizes answers from document store."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Union

import structlog

from src.integrations.llm_providers.base import LLMProvider
from src.models import AgentStatusEvent, TokenEvent, SourcesEvent
from src.rag.retrieval.hybrid import HybridRetriever
from src.rag.retrieval.vector_only import VectorOnlyRetriever

logger = structlog.get_logger(__name__)


class RAGAgent:
    """Handles retrieval-augmented generation queries.

    Supports two retrieval strategies controlled via the ``context`` dict:
    - ``"hybrid"`` (default): combines vector similarity with knowledge-graph
      traversal using Reciprocal Rank Fusion.
    - ``"vector_only"``: pure vector similarity search.
    """

    def __init__(
        self,
        hybrid_retriever: HybridRetriever,
        vector_retriever: VectorOnlyRetriever,
        llm_provider: LLMProvider,
    ) -> None:
        self._hybrid_retriever = hybrid_retriever
        self._vector_retriever = vector_retriever
        self._llm_provider = llm_provider

    @property
    def name(self) -> str:
        return "rag_agent"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        """Retrieve relevant document chunks and synthesise a natural language answer.

        Args:
            query:   The user's natural language question.
            context: Optional dict with keys:
                     - ``strategy`` (str): ``"hybrid"`` (default) or ``"vector_only"``.
                     - ``top_k``    (int): Number of chunks to retrieve (default 10).

        Returns:
            A natural language answer grounded in the retrieved context.
        """
        ctx = context or {}
        strategy: str = ctx.get("strategy", "hybrid")
        top_k: int = ctx.get("top_k", 10)

        logger.info("rag_agent.execute.start", query=query, strategy=strategy, top_k=top_k)

        # Retrieve relevant chunks using the selected strategy
        if strategy == "vector_only":
            results = await self._vector_retriever.retrieve(query, top_k=top_k)
        else:
            results = await self._hybrid_retriever.retrieve(query, top_k=top_k)

        logger.debug("rag_agent.retrieved", chunk_count=len(results), strategy=strategy)

        # Build context string from retrieved chunks
        context_str = "\n\n---\n\n".join(r.chunk.content for r in results)

        # Build prompt matching the pattern used in query.py
        prompt = (
            "Based on the following context, answer the question. "
            "If the context doesn't contain enough information, say so.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {query}\n\n"
            "Answer:"
        )

        answer = await self._llm_provider.generate(prompt)
        logger.info("rag_agent.execute.complete", query=query, chunk_count=len(results))
        return answer

    async def execute_stream(
        self, query: str, context: dict[str, Any] | None = None,
    ) -> AsyncIterator[Union[AgentStatusEvent, TokenEvent, SourcesEvent]]:
        """Stream retrieval + generation as a sequence of events."""
        ctx = context or {}
        strategy: str = ctx.get("strategy", "hybrid")
        top_k: int = ctx.get("top_k", 10)

        yield AgentStatusEvent(
            agent="rag_agent", phase="retrieving",
            message="RAG Agent: Retrieving documents...",
        )

        if strategy == "vector_only":
            results = await self._vector_retriever.retrieve(query, top_k=top_k)
        else:
            results = await self._hybrid_retriever.retrieve(query, top_k=top_k)

        yield SourcesEvent(sources=results, query=query, strategy=strategy)

        yield AgentStatusEvent(
            agent="rag_agent", phase="generating",
            message="RAG Agent: Generating response...",
        )

        context_str = "\n\n---\n\n".join(r.chunk.content for r in results)
        prompt = (
            "Based on the following context, answer the question. "
            "If the context doesn't contain enough information, say so.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {query}\n\n"
            "Answer:"
        )

        async for token in self._llm_provider.stream(prompt):
            yield TokenEvent(token=token)
