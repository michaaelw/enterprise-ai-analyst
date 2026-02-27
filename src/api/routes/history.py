"""Chat history endpoints."""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_state
from src.models import ChatSession, ChatMessage, ChatSessionListResponse, ChatHistoryResponse

router = APIRouter(prefix="/history", tags=["history"])


class SaveMessageRequest(BaseModel):
    session_id: str
    role: str
    content: str
    sources_json: str = "[]"
    strategy: str | None = None
    latency_ms: float | None = None


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(limit: int = 50) -> ChatSessionListResponse:
    state = get_state()
    assert state.duckdb_store is not None
    rows = await state.duckdb_store.list_sessions(limit=limit)
    sessions = [ChatSession(**r) for r in rows]
    return ChatSessionListResponse(sessions=sessions)


@router.get("/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_session(session_id: str) -> ChatHistoryResponse:
    state = get_state()
    assert state.duckdb_store is not None
    data = await state.duckdb_store.get_session_messages(session_id)
    if data["session"] is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session = ChatSession(**data["session"])
    messages = [ChatMessage(**m) for m in data["messages"]]
    return ChatHistoryResponse(session=session, messages=messages)


@router.post("/messages", status_code=201)
async def save_message(body: SaveMessageRequest) -> dict[str, str]:
    state = get_state()
    assert state.duckdb_store is not None
    store = state.duckdb_store

    # Auto-create session if it doesn't exist
    existing = await store.get_session_messages(body.session_id)
    if existing["session"] is None:
        title = body.content[:100] if body.role == "user" else ""
        await store.create_session(body.session_id, title)

    msg_id = str(uuid4())
    await store.save_message({
        "id": msg_id,
        "session_id": body.session_id,
        "role": body.role,
        "content": body.content,
        "sources_json": body.sources_json,
        "strategy": body.strategy,
        "latency_ms": body.latency_ms,
    })
    return {"id": msg_id}
