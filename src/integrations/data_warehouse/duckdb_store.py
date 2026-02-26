"""DuckDB data warehouse store - stub for future implementation."""
from __future__ import annotations

from typing import Any


class DuckDBStore:
    """Stub for DuckDB-based SQL analytics. Not yet implemented."""

    def __init__(self, path: str = "./data/analytics.duckdb") -> None:
        self._path = path

    async def connect(self) -> None:
        raise NotImplementedError("DuckDB store not yet implemented")

    async def close(self) -> None:
        raise NotImplementedError("DuckDB store not yet implemented")

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("DuckDB store not yet implemented")
