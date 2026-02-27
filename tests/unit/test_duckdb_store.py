"""Unit tests for DuckDBStore using a real in-memory DuckDB database."""
from __future__ import annotations

import pytest

from src.integrations.data_warehouse.duckdb_store import DuckDBStore


@pytest.fixture
async def store() -> DuckDBStore:  # type: ignore[misc]
    s = DuckDBStore(":memory:")
    await s.connect()
    yield s  # type: ignore[misc]
    await s.close()


class TestDuckDBStoreConnect:
    async def test_connect_creates_tables(self, store: DuckDBStore) -> None:
        """connect() should create all three analytics tables."""
        rows = await store.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        )
        table_names = {row["table_name"] for row in rows}
        assert "quarterly_financials" in table_names
        assert "revenue_by_segment" in table_names
        assert "headcount_by_department" in table_names
        assert len(table_names) == 3


class TestDuckDBStoreSeedData:
    async def test_seed_data_quarterly_financials(self, store: DuckDBStore) -> None:
        """quarterly_financials should be seeded with exactly 2 rows."""
        rows = await store.execute("SELECT * FROM quarterly_financials")
        assert len(rows) == 2

        quarters = {row["quarter"] for row in rows}
        assert "Q4 2025" in quarters
        assert "Q4 2024" in quarters

    async def test_seed_data_revenue_by_segment(self, store: DuckDBStore) -> None:
        """revenue_by_segment should be seeded with exactly 6 rows."""
        rows = await store.execute("SELECT * FROM revenue_by_segment")
        assert len(rows) == 6

    async def test_seed_data_headcount_by_department(self, store: DuckDBStore) -> None:
        """headcount_by_department should be seeded with exactly 10 rows."""
        rows = await store.execute("SELECT * FROM headcount_by_department")
        assert len(rows) == 10

    async def test_seed_idempotent(self, store: DuckDBStore) -> None:
        """Calling _setup_sync() a second time must not duplicate rows."""
        # Run setup again (tables already exist and are already seeded).
        import asyncio

        await asyncio.to_thread(store._setup_sync)

        rows = await store.execute("SELECT * FROM quarterly_financials")
        assert len(rows) == 2


class TestDuckDBStoreSchema:
    async def test_get_schema(self, store: DuckDBStore) -> None:
        """get_schema() should return a string mentioning all three tables."""
        schema = await store.get_schema()
        assert "quarterly_financials" in schema
        assert "revenue_by_segment" in schema
        assert "headcount_by_department" in schema


class TestDuckDBStoreExecute:
    async def test_execute_select(self, store: DuckDBStore) -> None:
        """execute() should return the correct row for a filtered SELECT."""
        rows = await store.execute(
            "SELECT total_revenue_m FROM quarterly_financials WHERE quarter = 'Q4 2025'"
        )
        assert rows == [{"total_revenue_m": 847.0}]

    async def test_execute_empty_result(self, store: DuckDBStore) -> None:
        """execute() should return an empty list when no rows match."""
        rows = await store.execute(
            "SELECT * FROM quarterly_financials WHERE quarter = 'Q9 9999'"
        )
        assert rows == []


class TestDuckDBStoreLifecycle:
    async def test_close_and_reopen(self) -> None:
        """close() should set _conn to None."""
        s = DuckDBStore(":memory:")
        await s.connect()
        assert s._conn is not None
        await s.close()
        assert s._conn is None
