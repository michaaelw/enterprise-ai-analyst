"""Dependency injection for FastAPI application state."""
from __future__ import annotations

from dataclasses import dataclass
from src.config import Settings
from src.integrations.vector_db.qdrant_store import QdrantStore
from src.integrations.graph_db.neo4j_store import Neo4jStore
from src.integrations.llm_providers.openai_provider import OpenAILLMProvider, OpenAIEmbeddingProvider
from src.integrations.llm_providers.anthropic_provider import AnthropicLLMProvider
from src.rag.embeddings.pipeline import EmbeddingPipeline
from src.rag.ingestion import IngestionPipeline
from src.rag.retrieval.hybrid import HybridRetriever
from src.rag.retrieval.vector_only import VectorOnlyRetriever
from src.rag.chunking.fixed_size import FixedSizeChunker


@dataclass
class AppState:
    settings: Settings
    vector_store: QdrantStore
    graph_store: Neo4jStore
    embedding_provider: OpenAIEmbeddingProvider
    llm_provider: AnthropicLLMProvider
    embedding_pipeline: EmbeddingPipeline
    ingestion_pipeline: IngestionPipeline
    hybrid_retriever: HybridRetriever
    vector_retriever: VectorOnlyRetriever


_state: AppState | None = None


def get_state() -> AppState:
    if _state is None:
        raise RuntimeError("App state not initialized")
    return _state


def set_state(state: AppState) -> None:
    global _state
    _state = state
