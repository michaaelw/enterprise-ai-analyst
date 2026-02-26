"""Semantic chunker that splits text based on embedding similarity between sentences."""
from __future__ import annotations

import re
from uuid import UUID

import numpy as np
import tiktoken

from src.integrations.llm_providers.base import EmbeddingProvider
from src.models import Chunk
from src.rag.chunking.fixed_size import FixedSizeChunker

# Pattern to split on sentence-ending punctuation followed by whitespace, or newlines.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.?!])\s+|\n")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    vec_a = np.array(a, dtype=np.float64)
    vec_b = np.array(b, dtype=np.float64)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


class SemanticChunker:
    """Splits text into semantically coherent chunks using embedding similarity.

    The algorithm:
    1. Splits the input text into sentences.
    2. Embeds each sentence individually.
    3. Computes cosine similarity between consecutive sentence embeddings.
    4. Inserts a boundary wherever similarity drops below *similarity_threshold*.
    5. Groups the resulting sentence segments into chunks.
    6. Applies a token-count ceiling per chunk; segments that exceed *max_tokens*
       are subdivided using :class:`~src.rag.chunking.fixed_size.FixedSizeChunker`.

    Parameters
    ----------
    embedding_provider:
        Provider used to generate sentence embeddings.
    max_tokens:
        Maximum number of tokens allowed per output chunk.
    similarity_threshold:
        Cosine similarity value below which a segment boundary is inserted.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        max_tokens: int = 512,
        similarity_threshold: float = 0.5,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._max_tokens = max_tokens
        self._similarity_threshold = similarity_threshold
        self._enc = tiktoken.get_encoding("cl100k_base")
        self._fallback = FixedSizeChunker(chunk_size=max_tokens, chunk_overlap=0)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def chunk(self, text: str, document_id: UUID) -> list[Chunk]:
        """Split *text* into semantically coherent chunks.

        Returns an empty list when *text* is empty or contains only whitespace.
        This method is async because it calls the embedding provider.
        """
        if not text or not text.strip():
            return []

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        # Single sentence: no similarity comparison possible; emit as one chunk.
        if len(sentences) == 1:
            return self._sentences_to_chunks([sentences[0]], document_id, start_index=0)

        # Embed all sentences in one batched call.
        embeddings = await self._embedding_provider.embed(sentences)

        # Identify split points where consecutive similarity falls below threshold.
        segments = self._split_on_similarity(sentences, embeddings)

        # Convert segments to Chunk objects, respecting max_tokens.
        chunks: list[Chunk] = []
        index = 0
        for segment_sentences in segments:
            new_chunks = self._sentences_to_chunks(segment_sentences, document_id, start_index=index)
            chunks.extend(new_chunks)
            index += len(new_chunks)

        return chunks

    # ------------------------------------------------------------------
    # Sentence splitting
    # ------------------------------------------------------------------

    def _split_sentences(self, text: str) -> list[str]:
        """Split *text* into individual sentences, discarding blank entries."""
        raw = _SENTENCE_SPLIT_RE.split(text)
        return [s.strip() for s in raw if s.strip()]

    # ------------------------------------------------------------------
    # Similarity-based segmentation
    # ------------------------------------------------------------------

    def _split_on_similarity(
        self,
        sentences: list[str],
        embeddings: list[list[float]],
    ) -> list[list[str]]:
        """Group sentences into segments by detecting low-similarity boundaries.

        A new segment begins after sentence *i* when the cosine similarity
        between embedding *i* and embedding *i+1* is below the threshold.
        """
        segments: list[list[str]] = []
        current_segment: list[str] = [sentences[0]]

        for i in range(1, len(sentences)):
            similarity = _cosine_similarity(embeddings[i - 1], embeddings[i])
            if similarity < self._similarity_threshold:
                segments.append(current_segment)
                current_segment = [sentences[i]]
            else:
                current_segment.append(sentences[i])

        if current_segment:
            segments.append(current_segment)

        return segments

    # ------------------------------------------------------------------
    # Segment -> Chunk conversion
    # ------------------------------------------------------------------

    def _sentences_to_chunks(
        self,
        sentences: list[str],
        document_id: UUID,
        start_index: int,
    ) -> list[Chunk]:
        """Convert a list of sentences forming one segment into Chunk objects.

        When the joined segment text exceeds *max_tokens*, the fixed-size
        fallback chunker is used to subdivide it further.
        """
        segment_text = " ".join(sentences)
        token_ids = self._enc.encode(segment_text)

        if len(token_ids) <= self._max_tokens:
            return [
                Chunk(
                    document_id=document_id,
                    content=segment_text,
                    token_count=len(token_ids),
                    index=start_index,
                )
            ]

        # Segment exceeds token budget; subdivide with fixed-size fallback.
        sub_chunks = self._fallback.chunk(segment_text, document_id)
        result: list[Chunk] = []
        for offset, sub in enumerate(sub_chunks):
            result.append(
                Chunk(
                    id=sub.id,
                    document_id=sub.document_id,
                    content=sub.content,
                    token_count=sub.token_count,
                    index=start_index + offset,
                )
            )
        return result
