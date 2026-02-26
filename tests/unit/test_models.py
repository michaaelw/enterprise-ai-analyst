"""Unit tests for core domain models."""
from __future__ import annotations

from uuid import UUID, uuid4
from src.models import Document, Chunk, RetrievalResult, Entity, Relationship, QueryRequest, QueryResponse


class TestDocument:
    def test_create_with_defaults(self) -> None:
        doc = Document(content="Hello world")
        assert isinstance(doc.id, UUID)
        assert doc.content == "Hello world"
        assert doc.source == ""
        assert doc.metadata == {}
        assert doc.created_at is not None

    def test_create_with_all_fields(self) -> None:
        doc = Document(content="test", source="file.txt", metadata={"key": "value"})
        assert doc.source == "file.txt"
        assert doc.metadata == {"key": "value"}


class TestChunk:
    def test_create(self) -> None:
        doc_id = uuid4()
        chunk = Chunk(document_id=doc_id, content="chunk text", token_count=5, index=0)
        assert isinstance(chunk.id, UUID)
        assert chunk.document_id == doc_id
        assert chunk.embedding is None

    def test_frozen(self) -> None:
        chunk = Chunk(document_id=uuid4(), content="text", token_count=3, index=0)
        import pytest
        with pytest.raises(Exception):
            chunk.content = "modified"  # type: ignore[misc]

    def test_model_copy_with_embedding(self) -> None:
        chunk = Chunk(document_id=uuid4(), content="text", token_count=3, index=0)
        updated = chunk.model_copy(update={"embedding": [0.1, 0.2, 0.3]})
        assert updated.embedding == [0.1, 0.2, 0.3]
        assert chunk.embedding is None  # original unchanged


class TestRetrievalResult:
    def test_create(self) -> None:
        chunk = Chunk(document_id=uuid4(), content="text", token_count=3, index=0)
        result = RetrievalResult(chunk=chunk, score=0.95, source="vector")
        assert result.score == 0.95
        assert result.source == "vector"


class TestEntity:
    def test_create(self) -> None:
        entity = Entity(name="Acme Corp", entity_type="organization")
        assert entity.name == "Acme Corp"
        assert entity.entity_type == "organization"
        assert entity.source_chunk_id is None


class TestRelationship:
    def test_create(self) -> None:
        src_id = uuid4()
        tgt_id = uuid4()
        rel = Relationship(source_entity_id=src_id, target_entity_id=tgt_id, relationship_type="works_for")
        assert rel.relationship_type == "works_for"


class TestQueryRequest:
    def test_defaults(self) -> None:
        req = QueryRequest(query="What is revenue?")
        assert req.top_k == 10
        assert req.strategy == "hybrid"


class TestQueryResponse:
    def test_create(self) -> None:
        chunk = Chunk(document_id=uuid4(), content="text", token_count=3, index=0)
        result = RetrievalResult(chunk=chunk, score=0.9, source="vector")
        resp = QueryResponse(answer="answer", sources=[result], query="q", strategy="hybrid", latency_ms=42.5)
        assert resp.latency_ms == 42.5
        assert len(resp.sources) == 1
