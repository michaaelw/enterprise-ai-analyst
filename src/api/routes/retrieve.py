"""Retrieve endpoint for document search."""
from __future__ import annotations

import time
import structlog
from fastapi import APIRouter

from src.models import RetrieveRequest, RetrieveResponse
from src.api.dependencies import get_state

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["retrieve"])


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_endpoint(request: RetrieveRequest) -> RetrieveResponse:
    state = get_state()
    start = time.perf_counter()

    if request.strategy == "hybrid":
        results = await state.hybrid_retriever.retrieve(request.query, top_k=request.top_k)
    else:
        results = await state.vector_retriever.retrieve(request.query, top_k=request.top_k)

    context = "\n\n---\n\n".join(r.chunk.content for r in results)
    latency = (time.perf_counter() - start) * 1000

    logger.info("retrieve_complete", strategy=request.strategy, results=len(results), latency_ms=latency)

    return RetrieveResponse(
        sources=results,
        query=request.query,
        strategy=request.strategy,
        context=context,
        latency_ms=round(latency, 2),
    )
