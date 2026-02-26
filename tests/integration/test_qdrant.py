"""Integration tests for Qdrant vector store."""
from __future__ import annotations

import pytest
from uuid import uuid4
from src.integrations.vector_db.qdrant_store import QdrantStore
from src.models import Chunk

pytestmark = pytest.mark.integration


@pytest.fixture
async def qdrant_store():
    store = QdrantStore(url="http://localhost:6333", collection=f"test_{uuid4().hex[:8]}")
    await store.connect()
    await store.ensure_collection(dimensions=8)
    yield store
    # Cleanup: delete test collection
    try:
        await store.client.delete_collection(store._collection)
    except Exception:
        pass
    await store.close()


class TestQdrantStore:
    async def test_upsert_and_search(self, qdrant_store: QdrantStore) -> None:
        doc_id = uuid4()
        chunks = [
            Chunk(document_id=doc_id, content="revenue growth", token_count=2, index=0, embedding=[0.1]*8),
            Chunk(document_id=doc_id, content="cost reduction", token_count=2, index=1, embedding=[0.9]*8),
        ]
        await qdrant_store.upsert(chunks)

        results = await qdrant_store.search(embedding=[0.1]*8, top_k=2)
        assert len(results) > 0
        assert results[0].source == "vector"

    async def test_delete_by_document(self, qdrant_store: QdrantStore) -> None:
        doc_id = uuid4()
        chunks = [
            Chunk(document_id=doc_id, content="test", token_count=1, index=0, embedding=[0.5]*8),
        ]
        await qdrant_store.upsert(chunks)
        await qdrant_store.delete_by_document(doc_id)

        results = await qdrant_store.search(embedding=[0.5]*8, top_k=5)
        # After deletion, should find no results for this doc
        matching = [r for r in results if r.chunk.document_id == doc_id]
        assert len(matching) == 0
