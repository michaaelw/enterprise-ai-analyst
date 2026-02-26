"""Simple vector-only retriever for benchmarking and fallback."""
from __future__ import annotations

from src.models import RetrievalResult
from src.integrations.vector_db.qdrant_store import QdrantStore
from src.integrations.llm_providers.base import EmbeddingProvider


class VectorOnlyRetriever:
    def __init__(self, vector_store: QdrantStore, embedding_provider: EmbeddingProvider) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider

    async def retrieve(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        embeddings = await self._embedding_provider.embed([query])
        return await self._vector_store.search(embeddings[0], top_k=top_k)
