"""Structure-aware markdown chunker that respects document boundaries."""
from __future__ import annotations

import re
from uuid import UUID

import tiktoken

from src.models import Chunk
from src.rag.chunking.fixed_size import FixedSizeChunker


# Patterns that signal a logical section boundary in markdown.
_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_HR_RE = re.compile(r"^---\s*$", re.MULTILINE)
_CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)


class DocumentStructureChunker:
    """Splits markdown text on structural boundaries (headers, rules, paragraphs).

    Splitting never occurs inside fenced code blocks or across table rows.
    Sections that exceed *max_tokens* are further subdivided with the
    :class:`~src.rag.chunking.fixed_size.FixedSizeChunker` fallback.

    Parameters
    ----------
    max_tokens:
        Soft token ceiling for each output chunk.
    overlap_tokens:
        Token overlap passed to the fallback fixed-size chunker.
    """

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 50) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self._enc = tiktoken.get_encoding("cl100k_base")
        self._fallback = FixedSizeChunker(
            chunk_size=max_tokens, chunk_overlap=overlap_tokens
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, document_id: UUID) -> list[Chunk]:
        """Return a list of :class:`~src.models.Chunk` objects for *text*."""
        if not text or not text.strip():
            return []

        sections = self._split_into_sections(text)
        chunks: list[Chunk] = []
        index = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            token_ids = self._enc.encode(section)

            if len(token_ids) <= self.max_tokens:
                chunks.append(
                    Chunk(
                        document_id=document_id,
                        content=section,
                        token_count=len(token_ids),
                        index=index,
                    )
                )
                index += 1
            else:
                # Section is too large; subdivide with the fixed-size fallback.
                # Re-index the sub-chunks sequentially within the global stream.
                sub_chunks = self._fallback.chunk(section, document_id)
                for sub in sub_chunks:
                    # Chunk is frozen; rebuild with updated index.
                    chunks.append(
                        Chunk(
                            id=sub.id,
                            document_id=sub.document_id,
                            content=sub.content,
                            token_count=sub.token_count,
                            index=index,
                        )
                    )
                    index += 1

        return chunks

    # ------------------------------------------------------------------
    # Section splitting
    # ------------------------------------------------------------------

    def _split_into_sections(self, text: str) -> list[str]:
        """Split *text* into logical sections.

        The algorithm walks line-by-line, tracking:
        - Whether the current position is inside a fenced code block.
        - Whether the current line is part of a markdown table.

        A new section begins when a header (``#``), horizontal rule
        (``---``), or double newline is encountered outside a code block.
        Table rows are always kept with their surrounding section.
        """
        lines = text.splitlines(keepends=True)
        sections: list[str] = []
        current: list[str] = []
        inside_code_block = False

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.rstrip("\n").rstrip()

            # Toggle code-block state on fence markers.
            if stripped.startswith("```"):
                inside_code_block = not inside_code_block
                current.append(line)
                i += 1
                continue

            if inside_code_block:
                current.append(line)
                i += 1
                continue

            # Table rows: accumulate until the table ends.
            if stripped.startswith("|"):
                current.append(line)
                i += 1
                continue

            # Markdown header → start new section.
            if _HEADER_RE.match(stripped):
                if current:
                    sections.append("".join(current))
                current = [line]
                i += 1
                continue

            # Horizontal rule → flush current section; rule starts next.
            if _HR_RE.match(stripped):
                if current:
                    sections.append("".join(current))
                current = [line]
                i += 1
                continue

            # Double newline (blank line followed by another blank line or
            # a line of content after a blank line) → paragraph boundary.
            if stripped == "":
                # Peek ahead: if the next non-blank line starts content,
                # treat the blank line as a section separator.
                current.append(line)
                # Collect any additional consecutive blank lines.
                while i + 1 < len(lines) and lines[i + 1].strip() == "":
                    i += 1
                    current.append(lines[i])
                # Only split if there is more content after the blank lines.
                if i + 1 < len(lines):
                    sections.append("".join(current))
                    current = []
                i += 1
                continue

            current.append(line)
            i += 1

        if current:
            sections.append("".join(current))

        return sections

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _token_count(self, text: str) -> int:
        return len(self._enc.encode(text))
