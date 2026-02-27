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
