"""Application configuration using Pydantic Settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # OpenAI
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 100

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "enterprise_docs"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # DuckDB
    duckdb_path: str = "./data/analytics.duckdb"

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 10
    similarity_threshold: float = 0.7

    # Ingestion concurrency
    max_concurrent_embeddings: int = 5

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"


def get_settings() -> Settings:
    return Settings()
