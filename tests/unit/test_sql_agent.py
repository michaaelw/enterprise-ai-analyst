"""Unit tests for SQLAgent.

Uses a real DuckDB :memory: store (seeded with data) and a mock LLM provider
so no external services are required.
"""
from __future__ import annotations

from typing import Any

import pytest

from src.agents.sql_agent import SQLAgent
from src.integrations.data_warehouse.duckdb_store import DuckDBStore


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------


class MockLLM:
    """Returns pre-recorded responses in order, one per generate() call."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    async def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        result = self._responses[self._call_count]
        self._call_count += 1
        return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def duckdb_store() -> DuckDBStore:  # type: ignore[misc]
    store = DuckDBStore(":memory:")
    await store.connect()
    yield store  # type: ignore[misc]
    await store.close()


# ---------------------------------------------------------------------------
# Tests — end-to-end execute() behaviour
# ---------------------------------------------------------------------------


class TestSQLAgentExecute:
    async def test_execute_success(self, duckdb_store: DuckDBStore) -> None:
        """A valid two-step LLM response should return the synthesis answer."""
        sql = "SELECT total_revenue_m FROM quarterly_financials WHERE quarter = 'Q4 2025'"
        synthesis = "Q4 2025 revenue was $847M"
        agent = SQLAgent(duckdb_store, MockLLM([sql, synthesis]))

        result = await agent.execute("What was Q4 2025 revenue?")

        assert result == synthesis

    async def test_execute_with_fences(self, duckdb_store: DuckDBStore) -> None:
        """SQL wrapped in ```sql fences should be stripped before execution."""
        sql_raw = (
            "```sql\n"
            "SELECT total_revenue_m FROM quarterly_financials WHERE quarter = 'Q4 2025'\n"
            "```"
        )
        synthesis = "Revenue was $847M in Q4 2025."
        agent = SQLAgent(duckdb_store, MockLLM([sql_raw, synthesis]))

        result = await agent.execute("What was Q4 2025 revenue?")

        assert result == synthesis

    async def test_execute_retry_on_failure(self, duckdb_store: DuckDBStore) -> None:
        """A failing SQL on the first attempt triggers a retry with a fixed query."""
        bad_sql = "SELECT foo FROM bar"
        good_sql = "SELECT total_revenue_m FROM quarterly_financials"
        synthesis = "Total revenue retrieved successfully."
        agent = SQLAgent(duckdb_store, MockLLM([bad_sql, good_sql, synthesis]))

        result = await agent.execute("Show me revenue figures")

        # The agent should recover and return the synthesis from the third LLM call.
        assert result == synthesis

    async def test_execute_empty_results(self, duckdb_store: DuckDBStore) -> None:
        """SQL that returns no rows should still produce a synthesis answer."""
        sql = "SELECT * FROM quarterly_financials WHERE quarter = 'Q9 9999'"
        synthesis = "There are no results for Q9 9999."
        agent = SQLAgent(duckdb_store, MockLLM([sql, synthesis]))

        result = await agent.execute("Show me Q9 9999 data")

        assert result == synthesis


# ---------------------------------------------------------------------------
# Tests — private helpers
# ---------------------------------------------------------------------------


class TestSQLAgentStripFences:
    def test_strip_sql_fence(self) -> None:
        """```sql\\n...\\n``` fences should be removed."""
        raw = "```sql\nSELECT 1\n```"
        assert SQLAgent._strip_fences(raw) == "SELECT 1"

    def test_strip_plain_fence(self) -> None:
        """Generic ``` fences without a language tag should also be removed."""
        raw = "```\nSELECT 1\n```"
        assert SQLAgent._strip_fences(raw) == "SELECT 1"

    def test_no_fence_unchanged(self) -> None:
        """Plain SQL with no fences should pass through unchanged."""
        raw = "SELECT 1"
        assert SQLAgent._strip_fences(raw) == "SELECT 1"


class TestSQLAgentFormatResults:
    def test_format_results_empty(self) -> None:
        """An empty result list should return the 'No results found.' sentinel."""
        assert SQLAgent._format_results([]) == "No results found."

    def test_format_results_with_data(self) -> None:
        """Non-empty results should be formatted as a GitHub-flavoured markdown table."""
        rows: list[dict[str, Any]] = [
            {"quarter": "Q4 2025", "total_revenue_m": 847.0},
            {"quarter": "Q4 2024", "total_revenue_m": 688.0},
        ]
        table = SQLAgent._format_results(rows)

        # Header row
        assert "| quarter | total_revenue_m |" in table
        # Separator row
        assert "| --- | --- |" in table
        # Data rows
        assert "| Q4 2025 | 847.0 |" in table
        assert "| Q4 2024 | 688.0 |" in table
