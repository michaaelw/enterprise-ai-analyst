"""SSE endpoint that streams agent status + tokens through the orchestrator."""
from __future__ import annotations

import json
import time
import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.models import (
    AgentStatusEvent,
    QueryStreamRequest,
    SourcesEvent,
    TokenEvent,
)
from src.api.dependencies import get_state

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["query_stream"])


@router.post("/query/stream")
async def query_stream_endpoint(request: QueryStreamRequest):
    state = get_state()

    async def event_stream():
        start = time.perf_counter()
        try:
            if request.strategy == "auto":
                if state.orchestrator is None:
                    raise RuntimeError("Orchestrator not initialized")
                events = state.orchestrator.execute_stream(
                    request.query,
                    context={"top_k": request.top_k},
                )
            else:
                if state.rag_agent is None:
                    raise RuntimeError("RAG agent not initialized")
                events = state.rag_agent.execute_stream(
                    request.query,
                    context={
                        "strategy": request.strategy,
                        "top_k": request.top_k,
                    },
                )

            async for event in events:
                if isinstance(event, AgentStatusEvent):
                    data = json.dumps({
                        "agent": event.agent,
                        "phase": event.phase,
                        "message": event.message,
                    })
                    yield f"event: status\ndata: {data}\n\n"
                elif isinstance(event, SourcesEvent):
                    data = json.dumps({
                        "sources": [s.model_dump(mode="json") for s in event.sources],
                        "query": event.query,
                        "strategy": event.strategy,
                    })
                    yield f"event: sources\ndata: {data}\n\n"
                elif isinstance(event, TokenEvent):
                    data = json.dumps({"token": event.token})
                    yield f"event: token\ndata: {data}\n\n"

            latency = (time.perf_counter() - start) * 1000
            done_data = json.dumps({"latency_ms": round(latency, 2)})
            yield f"event: done\ndata: {done_data}\n\n"
            logger.info("query_stream_complete", latency_ms=latency, strategy=request.strategy)
        except Exception as exc:
            error_data = json.dumps({"error": str(exc)})
            yield f"event: error\ndata: {error_data}\n\n"
            logger.error("query_stream_error", error=str(exc))

    return StreamingResponse(event_stream(), media_type="text/event-stream")
