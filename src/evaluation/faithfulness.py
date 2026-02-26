"""Faithfulness evaluation - measures if answers are grounded in retrieved context."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FaithfulnessEvaluator(Protocol):
    async def evaluate(self, answer: str, context: str) -> float: ...
