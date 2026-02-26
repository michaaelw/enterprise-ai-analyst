"""Summarizer agent - produces concise summaries of retrieved content."""
from __future__ import annotations

from typing import Any


class SummarizerAgent:
    """Summarizes long-form content into concise answers.

    Not yet implemented - placeholder for Phase 2.
    """

    @property
    def name(self) -> str:
        return "summarizer"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        raise NotImplementedError("SummarizerAgent not yet implemented")
