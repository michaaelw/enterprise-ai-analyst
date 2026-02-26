"""Unit tests for configuration."""
from __future__ import annotations

from src.config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        settings = Settings()
        assert settings.chunk_size == 512
        assert settings.chunk_overlap == 50
        assert settings.embedding_model == "text-embedding-3-small"
        assert settings.embedding_dimensions == 1536
        assert settings.top_k == 10
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.api_port == 8000
