"""Token-based fixed-size chunker using tiktoken."""
from __future__ import annotations

from uuid import UUID

import tiktoken

from src.models import Chunk


class FixedSizeChunker:
    """Splits text into fixed-size token windows with overlap.

    Parameters
    ----------
    chunk_size:
        Maximum number of tokens per chunk.
    chunk_overlap:
        Number of tokens to overlap between consecutive chunks.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
            )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._enc = tiktoken.get_encoding("cl100k_base")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, document_id: UUID) -> list[Chunk]:
        """Split *text* into overlapping token windows.

        Returns an empty list when *text* is empty or contains only
        whitespace.  Returns a single :class:`~src.models.Chunk` when the
        encoded token count does not exceed ``chunk_size``.
        """
        if not text or not text.strip():
            return []

        token_ids: list[int] = self._enc.encode(text)

        if len(token_ids) <= self.chunk_size:
            return [self._make_chunk(token_ids, document_id, index=0)]

        chunks: list[Chunk] = []
        step = self.chunk_size - self.chunk_overlap
        start = 0
        index = 0

        while start < len(token_ids):
            end = min(start + self.chunk_size, len(token_ids))
            window = token_ids[start:end]
            chunks.append(self._make_chunk(window, document_id, index=index))
            if end == len(token_ids):
                break
            start += step
            index += 1

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_chunk(
        self, token_ids: list[int], document_id: UUID, *, index: int
    ) -> Chunk:
        content = self._enc.decode(token_ids)
        return Chunk(
            document_id=document_id,
            content=content,
            token_count=len(token_ids),
            index=index,
        )
