"""Document ingestion pipeline: chunk -> embed -> store vectors -> extract entities -> store graph."""
from __future__ import annotations

import structlog
from src.models import Document, Chunk
from src.rag.chunking.base import Chunker
from src.rag.embeddings.pipeline import EmbeddingPipeline
from src.integrations.vector_db.qdrant_store import QdrantStore
from src.integrations.graph_db.neo4j_store import Neo4jStore
from src.integrations.llm_providers.base import LLMProvider

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        chunker: Chunker,
        embedding_pipeline: EmbeddingPipeline,
        vector_store: QdrantStore,
        graph_store: Neo4jStore,
        llm_provider: LLMProvider,
    ) -> None:
        self._chunker = chunker
        self._embedding_pipeline = embedding_pipeline
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._llm_provider = llm_provider

    async def ingest(self, document: Document) -> list[Chunk]:
        """Ingest a document through the full pipeline."""
        logger.info("ingestion_started", document_id=str(document.id), source=document.source)

        # 1. Chunk the document
        chunks = self._chunker.chunk(document.content, document.id)
        logger.info("document_chunked", chunk_count=len(chunks))

        if not chunks:
            return []

        # 2. Generate embeddings
        embedded_chunks = await self._embedding_pipeline.embed_chunks(chunks)

        # 3. Store in vector DB
        await self._vector_store.upsert(embedded_chunks)

        # 4. Extract and store entities/relationships in graph
        for chunk in embedded_chunks:
            try:
                entities, triples = await self._graph_store.extract_entities_from_text(
                    chunk.content, self._llm_provider
                )
                for entity in entities:
                    entity_with_chunk = entity.model_copy(update={"source_chunk_id": chunk.id})
                    await self._graph_store.create_entity(entity_with_chunk)
                for source_ent, target_ent, rel in triples:
                    rel_with_chunk = rel.model_copy(update={"source_chunk_id": chunk.id})
                    await self._graph_store.create_relationship(rel_with_chunk, source_ent.name, target_ent.name)
            except Exception:
                logger.exception("entity_extraction_failed", chunk_id=str(chunk.id))

        logger.info("ingestion_complete", document_id=str(document.id), chunks_stored=len(embedded_chunks))
        return embedded_chunks
