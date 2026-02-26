"""Base agent protocol for the multi-agent system."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Agent(Protocol):
    @property
    def name(self) -> str: ...

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str: ...
