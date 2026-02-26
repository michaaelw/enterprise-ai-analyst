"""Health check endpoints."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    """Readiness check - verifies all dependencies are connected."""
    from src.api.dependencies import get_state

    state = get_state()
    # Will raise if not connected
    _ = state.vector_store.client
    _ = state.graph_store.driver
    return {"status": "ready"}
