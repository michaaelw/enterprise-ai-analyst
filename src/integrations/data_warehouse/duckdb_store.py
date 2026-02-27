"""DuckDB data warehouse store — full implementation for SQL analytics."""
from __future__ import annotations

import asyncio
from typing import Any

import duckdb
import structlog

logger = structlog.get_logger(__name__)

_DDL_QUARTERLY_FINANCIALS = """
CREATE TABLE IF NOT EXISTS quarterly_financials (
    quarter          VARCHAR,
    total_revenue_m  DOUBLE,
    gross_margin     DOUBLE,
    operating_margin DOUBLE,
    free_cash_flow_m DOUBLE,
    headcount        INTEGER
)
"""

_DDL_REVENUE_BY_SEGMENT = """
CREATE TABLE IF NOT EXISTS revenue_by_segment (
    quarter      VARCHAR,
    segment      VARCHAR,
    revenue_m    DOUBLE,
    yoy_growth   DOUBLE,
    sub_segments VARCHAR
)
"""

_DDL_HEADCOUNT_BY_DEPARTMENT = """
CREATE TABLE IF NOT EXISTS headcount_by_department (
    quarter    VARCHAR,
    department VARCHAR,
    headcount  INTEGER
)
"""

_SEED_QUARTERLY_FINANCIALS = """
INSERT INTO quarterly_financials
    (quarter, total_revenue_m, gross_margin, operating_margin, free_cash_flow_m, headcount)
VALUES
    ('Q4 2025', 847.0, 72.4, 23.4, 167.0, 12847),
    ('Q4 2024', 688.0, 68.1, 19.8, 112.0, 11203)
"""

_SEED_REVENUE_BY_SEGMENT = """
INSERT INTO revenue_by_segment
    (quarter, segment, revenue_m, yoy_growth, sub_segments)
VALUES
    ('Q4 2025', 'Enterprise Software',   412.0, 28.0, 'Cloud: $267M, On-premise: $145M'),
    ('Q4 2025', 'Professional Services', 235.0, 15.0, 'Implementation: $142M, Consulting: $93M'),
    ('Q4 2025', 'Data Analytics',        200.0, 31.0, 'Platform: $128M, Managed: $72M'),
    ('Q4 2024', 'Enterprise Software',   321.9, NULL, NULL),
    ('Q4 2024', 'Professional Services', 204.3, NULL, NULL),
    ('Q4 2024', 'Data Analytics',        152.7, NULL, NULL)
"""

_SEED_HEADCOUNT_BY_DEPARTMENT = """
INSERT INTO headcount_by_department
    (quarter, department, headcount)
VALUES
    ('Q4 2025', 'Engineering',       4500),
    ('Q4 2025', 'Sales',             2800),
    ('Q4 2025', 'Operations',        2200),
    ('Q4 2025', 'R&D',               1847),
    ('Q4 2025', 'General & Admin',   1500),
    ('Q4 2024', 'Engineering',       3900),
    ('Q4 2024', 'Sales',             2500),
    ('Q4 2024', 'Operations',        1900),
    ('Q4 2024', 'R&D',               1603),
    ('Q4 2024', 'General & Admin',   1301)
"""


class DuckDBStore:
    """DuckDB-backed SQL analytics store for Acme Corp financial data.

    All public methods are async; synchronous DuckDB calls are dispatched
    via ``asyncio.to_thread`` so as not to block the event loop.
    """

    def __init__(self, path: str = "./data/analytics.duckdb") -> None:
        self._path = path
        self._conn: duckdb.DuckDBPyConnection | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_sync(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *query* synchronously and return rows as a list of dicts.

        ``params`` is passed as positional parameters when provided (DuckDB
        accepts a list/tuple for ``?`` placeholders, but we accept a dict for
        named placeholders using ``$name`` syntax via DuckDB's native support).
        """
        if self._conn is None:
            raise RuntimeError("DuckDBStore is not connected. Call connect() first.")

        if params:
            relation = self._conn.execute(query, list(params.values()))
        else:
            relation = self._conn.execute(query)

        description = relation.description
        if description is None:
            # DDL / INSERT / UPDATE — no result set.
            return []

        column_names = [col[0] for col in description]
        rows = relation.fetchall()
        return [dict(zip(column_names, row)) for row in rows]

    def _setup_sync(self) -> None:
        """Create tables and seed data if the database is empty."""
        assert self._conn is not None

        # Create tables
        for ddl in (
            _DDL_QUARTERLY_FINANCIALS,
            _DDL_REVENUE_BY_SEGMENT,
            _DDL_HEADCOUNT_BY_DEPARTMENT,
        ):
            self._conn.execute(ddl)

        # Seed only when the primary table is empty (idempotent)
        count_result = self._conn.execute(
            "SELECT COUNT(*) AS n FROM quarterly_financials"
        ).fetchone()
        row_count: int = count_result[0] if count_result else 0

        if row_count == 0:
            logger.info("duckdb.seeding", path=self._path)
            for seed_sql in (
                _SEED_QUARTERLY_FINANCIALS,
                _SEED_REVENUE_BY_SEGMENT,
                _SEED_HEADCOUNT_BY_DEPARTMENT,
            ):
                self._conn.execute(seed_sql)
            logger.info("duckdb.seeded", path=self._path)
        else:
            logger.debug("duckdb.already_seeded", row_count=row_count, path=self._path)

    def _get_schema_sync(self) -> str:
        """Return a human-readable schema string suitable for LLM prompts."""
        if self._conn is None:
            raise RuntimeError("DuckDBStore is not connected. Call connect() first.")

        rows = self._conn.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()

        if not rows:
            return "No tables found."

        # Group by table name
        tables: dict[str, list[str]] = {}
        for table_name, column_name, data_type in rows:
            tables.setdefault(table_name, []).append(f"  {column_name} {data_type}")

        parts: list[str] = []
        for table_name, columns in tables.items():
            parts.append(f"Table: {table_name}")
            parts.extend(columns)
            parts.append("")  # blank line between tables

        return "\n".join(parts).rstrip()

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the DuckDB database at ``self._path`` and initialise schema."""

        def _open() -> duckdb.DuckDBPyConnection:
            conn = duckdb.connect(self._path)
            return conn

        logger.info("duckdb.connecting", path=self._path)
        self._conn = await asyncio.to_thread(_open)

        # Create tables and seed inside to_thread so the setup stays off the
        # event loop even though _setup_sync is synchronous.
        await asyncio.to_thread(self._setup_sync)
        logger.info("duckdb.connected", path=self._path)

    async def close(self) -> None:
        """Close the DuckDB connection if it is open."""
        if self._conn is not None:
            logger.info("duckdb.closing", path=self._path)
            await asyncio.to_thread(self._conn.close)
            self._conn = None
            logger.info("duckdb.closed", path=self._path)

    async def execute(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *query* asynchronously and return rows as a list of dicts.

        Args:
            query:  SQL query string.
            params: Optional mapping of parameter names to values. When
                    provided the values are forwarded to DuckDB in insertion
                    order, matching ``$1``/``?`` style positional placeholders.

        Returns:
            A (possibly empty) list of row dicts. DDL and DML statements that
            produce no result set return an empty list.
        """
        logger.debug("duckdb.execute", query=query, params=params)
        result = await asyncio.to_thread(self._execute_sync, query, params)
        logger.debug("duckdb.execute.done", row_count=len(result))
        return result

    async def get_schema(self) -> str:
        """Return a human-readable schema description for use in LLM prompts.

        Queries ``information_schema.columns`` and formats each table's
        columns as plain text, e.g.::

            Table: quarterly_financials
              quarter VARCHAR
              total_revenue_m DOUBLE
              ...

        Returns:
            Multi-line string describing all tables and their columns.
        """
        logger.debug("duckdb.get_schema")
        schema = await asyncio.to_thread(self._get_schema_sync)
        logger.debug("duckdb.get_schema.done")
        return schema
