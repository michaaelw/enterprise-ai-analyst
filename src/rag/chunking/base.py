"""Protocol for text chunking strategies."""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from src.models import Chunk


@runtime_checkable
class Chunker(Protocol):
    def chunk(self, text: str, document_id: UUID) -> list[Chunk]: ...
