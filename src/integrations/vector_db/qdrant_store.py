"""Qdrant vector database client."""
from __future__ import annotations

import structlog
from uuid import UUID
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)
from src.models import Chunk, RetrievalResult

logger = structlog.get_logger(__name__)


class QdrantStore:
    def __init__(self, url: str = "http://localhost:6333", collection: str = "enterprise_docs") -> None:
        self._url = url
        self._collection = collection
        self._client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        self._client = AsyncQdrantClient(url=self._url)
        logger.info("qdrant_connected", url=self._url)

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> AsyncQdrantClient:
        if not self._client:
            raise RuntimeError("QdrantStore not connected. Call connect() first.")
        return self._client

    async def ensure_collection(self, dimensions: int) -> None:
        """Create collection if it doesn't exist."""
        collections = await self.client.get_collections()
        existing = [c.name for c in collections.collections]
        if self._collection not in existing:
            await self.client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
            )
            logger.info("collection_created", collection=self._collection, dimensions=dimensions)

    async def upsert(self, chunks: list[Chunk]) -> None:
        """Upsert chunks with their embeddings into Qdrant."""
        points = []
        for chunk in chunks:
            if chunk.embedding is None:
                continue
            points.append(
                PointStruct(
                    id=str(chunk.id),
                    vector=chunk.embedding,
                    payload={
                        "document_id": str(chunk.document_id),
                        "content": chunk.content,
                        "token_count": chunk.token_count,
                        "index": chunk.index,
                        "metadata": chunk.metadata,
                    },
                )
            )
        if points:
            await self.client.upsert(collection_name=self._collection, points=points)
            logger.info("chunks_upserted", count=len(points))

    async def search(self, embedding: list[float], top_k: int = 10, score_threshold: float = 0.0) -> list[RetrievalResult]:
        """Search for similar chunks by embedding vector."""
        results = await self.client.query_points(
            collection_name=self._collection,
            query=embedding,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        retrieval_results = []
        for point in results.points:
            payload = point.payload or {}
            chunk = Chunk(
                id=UUID(str(point.id)),
                document_id=UUID(payload.get("document_id", "")),
                content=payload.get("content", ""),
                token_count=payload.get("token_count", 0),
                index=payload.get("index", 0),
                metadata=payload.get("metadata", {}),
            )
            retrieval_results.append(RetrievalResult(chunk=chunk, score=point.score, source="vector"))
        return retrieval_results

    async def delete_by_document(self, document_id: UUID) -> None:
        """Delete all chunks belonging to a document."""
        await self.client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))]
            ),
        )
        logger.info("document_chunks_deleted", document_id=str(document_id))
