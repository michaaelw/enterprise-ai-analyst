"""Integration tests for the FastAPI application."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

# These tests require the full application with Docker services running.
# They serve as documentation for the expected API behavior.


class TestHealthEndpoints:
    """Tests for health check endpoints.

    Run with: pytest tests/integration/test_api.py -m integration
    Requires: docker compose -f infra/docker-compose.yml up -d
    """

    async def test_health(self) -> None:
        """GET /health should return 200 with status ok."""
        # To run this test, start the app and use httpx:
        # async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        #     response = await client.get("/health")
        #     assert response.status_code == 200
        #     assert response.json() == {"status": "ok"}
        pass  # Placeholder - requires running app

    async def test_ingest_and_query(self) -> None:
        """POST /ingest then POST /query should return results."""
        # Placeholder - requires running app with all services
        pass
