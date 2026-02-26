"""Ollama local model providers for LLM and embeddings."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx


class OllamaLLMProvider:
    """Ollama local LLM provider using the Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
    ) -> None:
        self._model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)

    async def generate(self, prompt: str) -> str:
        """Generate a text response for the given prompt."""
        response = await self._client.post(
            "/api/chat",
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    async def stream(self, prompt: str, *, max_tokens: int = 4096) -> AsyncIterator[str]:
        """Stream text tokens for the given prompt."""
        async with self._client.stream(
            "POST",
            "/api/chat",
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content")
                if content:
                    yield content
                if chunk.get("done"):
                    break


class OllamaEmbeddingProvider:
    """Ollama local embedding provider using the Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        dimensions: int = 768,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    @property
    def dimensions(self) -> int:
        """Return the embedding dimensionality."""
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts using the Ollama embed endpoint."""
        response = await self._client.post(
            "/api/embed",
            json={
                "model": self._model,
                "input": texts,
            },
        )
        response.raise_for_status()
        return response.json()["embeddings"]
