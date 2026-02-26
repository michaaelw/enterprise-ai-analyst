"""Hybrid retrieval using Reciprocal Rank Fusion (RRF) of vector + graph results."""
from __future__ import annotations

import structlog
from uuid import UUID
from src.models import Chunk, RetrievalResult
from src.integrations.vector_db.qdrant_store import QdrantStore
from src.integrations.graph_db.neo4j_store import Neo4jStore
from src.integrations.llm_providers.base import EmbeddingProvider, LLMProvider

logger = structlog.get_logger(__name__)


class HybridRetriever:
    """Combines vector similarity search with knowledge graph traversal using RRF."""

    def __init__(
        self,
        vector_store: QdrantStore,
        graph_store: Neo4jStore,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        rrf_k: int = 60,
    ) -> None:
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._embedding_provider = embedding_provider
        self._llm_provider = llm_provider
        self._rrf_k = rrf_k

    async def retrieve(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """Retrieve chunks using hybrid vector + graph approach with RRF merging."""
        # 1. Get query embedding and search vector store
        embeddings = await self._embedding_provider.embed([query])
        query_embedding = embeddings[0]
        vector_results = await self._vector_store.search(query_embedding, top_k=top_k * 2)

        # 2. Extract entities from query and do graph traversal
        entities, _ = await self._graph_store.extract_entities_from_text(query, self._llm_provider)
        entity_names = [e.name for e in entities]
        graph_chunk_ids = await self._graph_store.find_related_chunks(entity_names) if entity_names else []

        # 3. If we have graph results, fetch those chunks from vector store too
        graph_results: list[RetrievalResult] = []
        if graph_chunk_ids:
            # Search with higher top_k to find graph-related chunks
            all_vector = await self._vector_store.search(query_embedding, top_k=top_k * 4)
            graph_id_set = set(graph_chunk_ids)
            for r in all_vector:
                if str(r.chunk.id) in graph_id_set:
                    graph_results.append(RetrievalResult(chunk=r.chunk, score=r.score, source="graph"))

        # 4. Apply Reciprocal Rank Fusion
        return self._rrf_merge(vector_results, graph_results, top_k)

    def _rrf_merge(
        self,
        vector_results: list[RetrievalResult],
        graph_results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Merge two ranked lists using Reciprocal Rank Fusion."""
        scores: dict[str, float] = {}
        chunks: dict[str, RetrievalResult] = {}

        for rank, result in enumerate(vector_results):
            chunk_id = str(result.chunk.id)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (self._rrf_k + rank + 1)
            chunks[chunk_id] = result

        for rank, result in enumerate(graph_results):
            chunk_id = str(result.chunk.id)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (self._rrf_k + rank + 1)
            if chunk_id not in chunks:
                chunks[chunk_id] = result

        sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)[:top_k]

        return [
            RetrievalResult(chunk=chunks[cid].chunk, score=scores[cid], source="hybrid")
            for cid in sorted_ids
        ]
