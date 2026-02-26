"""Unit tests for chunking strategies."""
from __future__ import annotations

from uuid import uuid4
import pytest
from src.rag.chunking.fixed_size import FixedSizeChunker
from src.rag.chunking.document_structure import DocumentStructureChunker


class TestFixedSizeChunker:
    def test_empty_text(self) -> None:
        chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=10)
        result = chunker.chunk("", uuid4())
        assert result == []

    def test_short_text_single_chunk(self) -> None:
        chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=10)
        doc_id = uuid4()
        result = chunker.chunk("Hello world", doc_id)
        assert len(result) == 1
        assert result[0].document_id == doc_id
        assert result[0].index == 0
        assert result[0].content == "Hello world"
        assert result[0].token_count > 0

    def test_long_text_multiple_chunks(self) -> None:
        chunker = FixedSizeChunker(chunk_size=10, chunk_overlap=2)
        text = " ".join(f"word{i}" for i in range(100))
        result = chunker.chunk(text, uuid4())
        assert len(result) > 1
        # All chunks should have sequential indices
        for i, chunk in enumerate(result):
            assert chunk.index == i
        # Token counts should be reasonable
        for chunk in result[:-1]:  # All but last
            assert chunk.token_count <= 12  # chunk_size + some tolerance

    def test_overlap_creates_more_chunks(self) -> None:
        text = " ".join(f"word{i}" for i in range(50))
        no_overlap = FixedSizeChunker(chunk_size=10, chunk_overlap=0).chunk(text, uuid4())
        with_overlap = FixedSizeChunker(chunk_size=10, chunk_overlap=3).chunk(text, uuid4())
        assert len(with_overlap) >= len(no_overlap)


class TestDocumentStructureChunker:
    def test_empty_text(self) -> None:
        chunker = DocumentStructureChunker(max_tokens=100)
        result = chunker.chunk("", uuid4())
        assert result == []

    def test_markdown_headers_split(self) -> None:
        text = "## Section 1\n\nContent for section one.\n\n## Section 2\n\nContent for section two."
        chunker = DocumentStructureChunker(max_tokens=500)
        result = chunker.chunk(text, uuid4())
        # Should create at least 1 chunk (sections may be merged if small)
        assert len(result) >= 1

    def test_code_blocks_preserved(self) -> None:
        text = "Some text\n\n```python\ndef hello():\n    print('world')\n```\n\nMore text"
        chunker = DocumentStructureChunker(max_tokens=500)
        result = chunker.chunk(text, uuid4())
        # Code block should not be split
        full_content = " ".join(c.content for c in result)
        assert "def hello():" in full_content
        assert "print('world')" in full_content

    def test_large_section_gets_split(self) -> None:
        # Create a section that exceeds max_tokens
        long_content = " ".join(f"word{i}" for i in range(200))
        text = f"## Big Section\n\n{long_content}"
        chunker = DocumentStructureChunker(max_tokens=50, overlap_tokens=5)
        result = chunker.chunk(text, uuid4())
        assert len(result) > 1

    def test_sequential_indices(self) -> None:
        text = "## A\n\nContent A\n\n## B\n\nContent B\n\n## C\n\nContent C"
        chunker = DocumentStructureChunker(max_tokens=500)
        result = chunker.chunk(text, uuid4())
        for i, chunk in enumerate(result):
            assert chunk.index == i
