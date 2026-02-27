"""Query endpoint for natural language questions."""
from __future__ import annotations

import time
import structlog
from fastapi import APIRouter

from src.models import QueryRequest, QueryResponse
from src.api.dependencies import get_state

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    state = get_state()
    start = time.perf_counter()

    # Auto strategy: delegate to orchestrator
    if request.strategy == "auto":
        if state.orchestrator is None:
            raise RuntimeError("Orchestrator not initialized")
        answer = await state.orchestrator.execute(request.query)
        latency = (time.perf_counter() - start) * 1000
        logger.info("query_complete", strategy="auto", latency_ms=latency)
        return QueryResponse(
            answer=answer,
            sources=[],
            query=request.query,
            strategy="auto",
            latency_ms=round(latency, 2),
        )

    # Retrieve relevant chunks
    if request.strategy == "hybrid":
        results = await state.hybrid_retriever.retrieve(request.query, top_k=request.top_k)
    else:
        results = await state.vector_retriever.retrieve(request.query, top_k=request.top_k)

    # Build context from retrieved chunks
    context = "\n\n---\n\n".join(r.chunk.content for r in results)

    # Generate answer using LLM
    prompt = f"""Based on the following context, answer the question. If the context doesn't contain enough information, say so.

Context:
{context}

Question: {request.query}

Answer:"""

    answer = await state.llm_provider.generate(prompt)
    latency = (time.perf_counter() - start) * 1000

    logger.info("query_complete", strategy=request.strategy, results=len(results), latency_ms=latency)

    return QueryResponse(
        answer=answer,
        sources=results,
        query=request.query,
        strategy=request.strategy,
        latency_ms=round(latency, 2),
    )
