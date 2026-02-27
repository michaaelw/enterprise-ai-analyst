"""SQL agent - generates and executes SQL queries against DuckDB."""
from __future__ import annotations

import re
from typing import Any

import structlog

from src.integrations.data_warehouse.duckdb_store import DuckDBStore
from src.integrations.llm_providers.base import LLMProvider

logger = structlog.get_logger(__name__)


class SQLAgent:
    """Generates SQL queries from natural language and executes against DuckDB.

    Uses a two-step LLM pattern:
    1. Generate a SELECT query from the schema and user question.
    2. Synthesize a natural language answer from the query results.
    """

    def __init__(self, duckdb_store: DuckDBStore, llm_provider: LLMProvider) -> None:
        self._duckdb_store = duckdb_store
        self._llm_provider = llm_provider

    @property
    def name(self) -> str:
        return "sql_agent"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def execute(self, query: str, context: dict[str, Any] | None = None) -> str:
        """Execute a natural-language query against DuckDB.

        Args:
            query:   The user's natural language question.
            context: Optional extra context (currently unused).

        Returns:
            A natural language answer synthesised from the SQL results.
        """
        logger.info("sql_agent.execute.start", query=query)

        # Step 1 — fetch schema
        schema = await self._duckdb_store.get_schema()

        # Step 2 — ask LLM to generate SQL
        sql_prompt = (
            "You are a SQL expert. Given the following database schema and user question, "
            "generate a single valid SELECT SQL query that answers the question.\n"
            "Return ONLY the raw SQL — no explanations, no markdown fences, no comments.\n"
            "Only SELECT queries are allowed.\n\n"
            f"Schema:\n{schema}\n\n"
            f"Question: {query}\n\n"
            "SQL:"
        )
        raw_sql = await self._llm_provider.generate(sql_prompt, temperature=0.0)
        sql = self._strip_fences(raw_sql)
        logger.debug("sql_agent.generated_sql", sql=sql)

        # Step 3 — execute, with one retry on failure
        try:
            rows = await self._duckdb_store.execute(sql)
        except Exception as first_error:
            logger.warning(
                "sql_agent.execute.first_attempt_failed",
                error=str(first_error),
                sql=sql,
            )
            fix_prompt = (
                "The following SQL query raised an error. Fix it so it executes correctly.\n"
                "Return ONLY the corrected raw SQL — no explanations, no markdown fences.\n"
                "Only SELECT queries are allowed.\n\n"
                f"Schema:\n{schema}\n\n"
                f"Original question: {query}\n\n"
                f"Failing SQL:\n{sql}\n\n"
                f"Error: {first_error}\n\n"
                "Fixed SQL:"
            )
            raw_sql_fixed = await self._llm_provider.generate(fix_prompt, temperature=0.0)
            sql = self._strip_fences(raw_sql_fixed)
            logger.debug("sql_agent.retry_sql", sql=sql)
            rows = await self._duckdb_store.execute(sql)

        # Step 4 — format results as a markdown table
        table = self._format_results(rows)
        logger.debug("sql_agent.results_table", table=table)

        # Step 5 — synthesise a natural language answer
        synthesis_prompt = (
            "You are a helpful data analyst. Given the user's question, the SQL query that was run, "
            "and the results, provide a clear and concise natural language answer.\n\n"
            f"Question: {query}\n\n"
            f"SQL:\n{sql}\n\n"
            f"Results:\n{table}\n\n"
            "Answer:"
        )
        answer = await self._llm_provider.generate(synthesis_prompt)
        logger.info("sql_agent.execute.complete", query=query, row_count=len(rows))
        return answer

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove leading ```sql / ``` fences and surrounding whitespace."""
        text = text.strip()
        # Remove opening fence (with optional language tag)
        text = re.sub(r"^```(?:sql)?\s*\n?", "", text, flags=re.IGNORECASE)
        # Remove closing fence
        text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    @staticmethod
    def _format_results(rows: list[dict[str, Any]]) -> str:
        """Convert a list of row dicts into a GitHub-flavoured markdown table.

        Returns "No results found." when *rows* is empty.
        """
        if not rows:
            return "No results found."

        headers = list(rows[0].keys())

        # Header row
        header_line = "| " + " | ".join(headers) + " |"
        # Separator row
        separator_line = "| " + " | ".join("---" for _ in headers) + " |"
        # Data rows
        data_lines = [
            "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |"
            for row in rows
        ]

        return "\n".join([header_line, separator_line, *data_lines])
