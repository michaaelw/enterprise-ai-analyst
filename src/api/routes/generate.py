"""Generate endpoint for LLM text generation."""
from __future__ import annotations

import json
import time
import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.models import GenerateRequest, GenerateResponse
from src.api.dependencies import get_state

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["generate"])


@router.post("/generate")
async def generate_endpoint(request: GenerateRequest):
    state = get_state()

    if not request.stream:
        start = time.perf_counter()
        answer = await state.llm_provider.generate(request.prompt)
        latency = (time.perf_counter() - start) * 1000
        logger.info("generate_complete", stream=False, latency_ms=latency)
        return GenerateResponse(answer=answer, latency_ms=round(latency, 2))

    async def event_stream():
        start = time.perf_counter()
        try:
            async for token in state.llm_provider.stream(request.prompt):
                data = json.dumps({"token": token})
                yield f"event: token\ndata: {data}\n\n"
            latency = (time.perf_counter() - start) * 1000
            done_data = json.dumps({"latency_ms": round(latency, 2)})
            yield f"event: done\ndata: {done_data}\n\n"
            logger.info("generate_complete", stream=True, latency_ms=latency)
        except Exception as exc:
            error_data = json.dumps({"error": str(exc)})
            yield f"event: error\ndata: {error_data}\n\n"
            logger.error("generate_stream_error", error=str(exc))

    return StreamingResponse(event_stream(), media_type="text/event-stream")
