"""Hallucination detection - identifies claims not supported by context."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HallucinationDetector(Protocol):
    async def detect(self, answer: str, context: str) -> list[str]: ...
