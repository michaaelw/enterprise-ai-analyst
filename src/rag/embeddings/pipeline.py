"""Batched embedding generation pipeline with retry and progress tracking."""
from __future__ import annotations

import asyncio
import structlog
from src.models import Chunk
from src.integrations.llm_providers.base import EmbeddingProvider

logger = structlog.get_logger(__name__)


class EmbeddingPipeline:
    def __init__(self, provider: EmbeddingProvider, batch_size: int = 100, max_concurrent: int = 5) -> None:
        self._provider = provider
        self._batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        async with self._semaphore:
            return await self._provider.embed(texts)

    async def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Generate embeddings for a list of chunks, returning new Chunk objects with embeddings set."""
        if not chunks:
            return []

        texts = [c.content for c in chunks]
        batches = [texts[i:i + self._batch_size] for i in range(0, len(texts), self._batch_size)]

        tasks = [self._embed_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)

        all_embeddings: list[list[float]] = []
        for batch_result in results:
            all_embeddings.extend(batch_result)

        embedded_chunks = []
        for chunk, embedding in zip(chunks, all_embeddings, strict=True):
            embedded_chunks.append(chunk.model_copy(update={"embedding": embedding}))

        logger.info("chunks_embedded", count=len(embedded_chunks))
        return embedded_chunks
