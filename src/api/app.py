"""FastAPI application with lifespan management."""
from __future__ import annotations

import pathlib
import structlog
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from src.models import Document

from src.config import get_settings
from src.observability.logging import configure_logging
from src.integrations.vector_db.qdrant_store import QdrantStore
from src.integrations.graph_db.neo4j_store import Neo4jStore
from src.integrations.data_warehouse.duckdb_store import DuckDBStore
from src.integrations.llm_providers.openai_provider import OpenAIEmbeddingProvider
from src.integrations.llm_providers.anthropic_provider import AnthropicLLMProvider
from src.integrations.llm_providers.ollama_provider import OllamaLLMProvider, OllamaEmbeddingProvider
from src.rag.embeddings.pipeline import EmbeddingPipeline
from src.rag.ingestion import IngestionPipeline
from src.rag.retrieval.hybrid import HybridRetriever
from src.rag.retrieval.vector_only import VectorOnlyRetriever
from src.rag.chunking.fixed_size import FixedSizeChunker
from src.agents.sql_agent import SQLAgent
from src.agents.rag_agent import RAGAgent
from src.agents.orchestrator import OrchestratorAgent
from src.api.dependencies import AppState, set_state
from src.api.routes import health, query, ingest, retrieve, generate, history


logger = structlog.get_logger(__name__)


async def _seed_demo_documents(pipeline: IngestionPipeline) -> None:
    """Seed demo documents from demo/sample_data/ if available."""
    demo_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "demo" / "sample_data"
    if not demo_dir.exists():
        logger.warning("demo_dir_not_found", path=str(demo_dir))
        return

    md_files = sorted(demo_dir.glob("*.md"))
    if not md_files:
        logger.info("no_demo_documents_found")
        return

    logger.info("seeding_demo_documents", count=len(md_files))
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            doc = Document(content=content, source=md_file.name)
            await pipeline.ingest(doc)
            logger.info("demo_document_seeded", source=md_file.name)
        except Exception:
            logger.exception("demo_document_seed_failed", source=md_file.name)

    logger.info("demo_seeding_complete")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    # Init stores
    vector_store = QdrantStore(url=settings.qdrant_url, collection=settings.qdrant_collection)
    await vector_store.connect()
    dims = settings.ollama_embed_dimensions if settings.embedding_provider_type == "ollama" else settings.embedding_dimensions
    await vector_store.ensure_collection(dims)

    graph_store = Neo4jStore(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
    await graph_store.connect()

    # Init providers
    if settings.embedding_provider_type == "ollama":
        embedding_provider = OllamaEmbeddingProvider(
            base_url=settings.ollama_url,
            model=settings.ollama_embed_model,
            dimensions=settings.ollama_embed_dimensions,
        )
    else:
        embedding_provider = OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            batch_size=settings.embedding_batch_size,
        )

    if settings.llm_provider_type == "ollama":
        llm_provider = OllamaLLMProvider(
            base_url=settings.ollama_url,
            model=settings.ollama_llm_model,
        )
    else:
        llm_provider = AnthropicLLMProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)

    # Init pipelines
    chunker = FixedSizeChunker(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    embedding_pipeline = EmbeddingPipeline(
        provider=embedding_provider,
        batch_size=settings.embedding_batch_size,
        max_concurrent=settings.max_concurrent_embeddings,
    )
    ingestion_pipeline = IngestionPipeline(
        chunker=chunker,
        embedding_pipeline=embedding_pipeline,
        vector_store=vector_store,
        graph_store=graph_store,
        llm_provider=llm_provider,
    )
    hybrid_retriever = HybridRetriever(
        vector_store=vector_store,
        graph_store=graph_store,
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
    )
    vector_retriever = VectorOnlyRetriever(vector_store=vector_store, embedding_provider=embedding_provider)

    # Init DuckDB + agents
    duckdb_store = DuckDBStore()
    await duckdb_store.connect()

    sql_agent = SQLAgent(duckdb_store=duckdb_store, llm_provider=llm_provider)
    rag_agent = RAGAgent(
        hybrid_retriever=hybrid_retriever,
        vector_retriever=vector_retriever,
        llm_provider=llm_provider,
    )
    orchestrator = OrchestratorAgent(
        llm_provider=llm_provider,
        sql_agent=sql_agent,
        rag_agent=rag_agent,
    )

    set_state(AppState(
        settings=settings,
        vector_store=vector_store,
        graph_store=graph_store,
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
        embedding_pipeline=embedding_pipeline,
        ingestion_pipeline=ingestion_pipeline,
        hybrid_retriever=hybrid_retriever,
        vector_retriever=vector_retriever,
        duckdb_store=duckdb_store,
        orchestrator=orchestrator,
    ))

    # Seed demo documents if Qdrant is empty
    point_count = await vector_store.count()
    if point_count == 0:
        await _seed_demo_documents(ingestion_pipeline)
    else:
        logger.info("demo_seed_skipped", point_count=point_count)

    yield

    await duckdb_store.close()
    await vector_store.close()
    await graph_store.close()


app = FastAPI(title="Enterprise AI Analyst", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(query.router)
app.include_router(ingest.router)
app.include_router(retrieve.router)
app.include_router(generate.router)
app.include_router(history.router)
