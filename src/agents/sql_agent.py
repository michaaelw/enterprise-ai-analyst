"""SQL agent - generates and executes SQL queries against DuckDB."""
from __future__ import annotations

from typing import Any


class SQLAgent:
    """Generates SQL queries from natural language and executes against DuckDB.

    Not yet implemented - placeholder for Phase 2.
    """

    @property
    def name(self) -> str:
        return "sql_agent"

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        raise NotImplementedError("SQLAgent not yet implemented")
