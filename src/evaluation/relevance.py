"""Relevance evaluation - measures if retrieved chunks are relevant to the query."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RelevanceEvaluator(Protocol):
    async def evaluate(self, query: str, chunks: list[str]) -> float: ...
