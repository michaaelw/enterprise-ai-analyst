"""Core domain types for the enterprise AI analyst."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    metadata: dict[str, Any] = {}
    source: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    content: str
    token_count: int
    index: int
    metadata: dict[str, Any] = {}
    embedding: list[float] | None = None


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    score: float
    source: str  # "vector" or "graph"


class Entity(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    entity_type: str
    properties: dict[str, Any] = {}
    source_chunk_id: UUID | None = None


class Relationship(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    properties: dict[str, Any] = {}
    source_chunk_id: UUID | None = None


class QueryRequest(BaseModel):
    query: str
    top_k: int = 10
    strategy: Literal["hybrid", "vector_only", "auto"] = "hybrid"


class QueryResponse(BaseModel):
    answer: str
    sources: list[RetrievalResult] = []
    query: str
    strategy: str
    latency_ms: float


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 10
    strategy: Literal["hybrid", "vector_only"] = "hybrid"


class RetrieveResponse(BaseModel):
    sources: list[RetrievalResult]
    query: str
    strategy: str
    context: str          # pre-built context string for /generate
    latency_ms: float


class GenerateRequest(BaseModel):
    prompt: str
    stream: bool = False  # when True, returns SSE instead of JSON


class GenerateResponse(BaseModel):
    answer: str
    latency_ms: float


# ---------------------------------------------------------------------------
# Chat history models
# ---------------------------------------------------------------------------

class ChatSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    message_count: int = 0


class ChatMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    role: Literal["user", "assistant"]
    content: str
    sources_json: str = "[]"
    strategy: str | None = None
    latency_ms: float | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSession]


class ChatHistoryResponse(BaseModel):
    session: ChatSession
    messages: list[ChatMessage]


# ---------------------------------------------------------------------------
# Streaming event models (for /query/stream SSE endpoint)
# ---------------------------------------------------------------------------


class AgentStatusEvent(BaseModel):
    event: Literal["status"] = "status"
    agent: str          # "orchestrator", "rag_agent", "sql_agent"
    phase: str          # "classifying", "retrieving", "generating_sql", etc.
    message: str        # Human-readable: "RAG Agent: Retrieving documents..."


class TokenEvent(BaseModel):
    event: Literal["token"] = "token"
    token: str


class SourcesEvent(BaseModel):
    event: Literal["sources"] = "sources"
    sources: list[RetrievalResult]
    query: str
    strategy: str


class QueryStreamRequest(BaseModel):
    query: str
    top_k: int = 10
    strategy: Literal["hybrid", "vector_only", "auto"] = "auto"
