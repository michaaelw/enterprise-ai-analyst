"""Unit tests for LLM and embedding providers.

All external HTTP calls are mocked — no real services are required.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.llm_providers.anthropic_provider import AnthropicLLMProvider
from src.integrations.llm_providers.ollama_provider import (
    OllamaEmbeddingProvider,
    OllamaLLMProvider,
)
from src.integrations.llm_providers.openai_provider import (
    OpenAIEmbeddingProvider,
    OpenAILLMProvider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_anthropic_response(text: str) -> MagicMock:
    """Build a minimal mock that looks like an Anthropic messages response."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


def _make_openai_chat_response(content: str | None) -> MagicMock:
    """Build a minimal mock that looks like an OpenAI chat completion response."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_openai_embedding_response(vectors: list[list[float]]) -> MagicMock:
    """Build a minimal mock that looks like an OpenAI embeddings response."""
    items = []
    for vec in vectors:
        item = MagicMock()
        item.embedding = vec
        items.append(item)
    response = MagicMock()
    response.data = items
    return response


def _make_httpx_response(body: dict[str, Any]) -> MagicMock:
    """Build a minimal mock that looks like an httpx.Response."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=body)
    return response


# ---------------------------------------------------------------------------
# Anthropic provider tests
# ---------------------------------------------------------------------------


class TestAnthropicLLMProvider:
    """Tests for AnthropicLLMProvider."""

    def _make_provider(self) -> AnthropicLLMProvider:
        return AnthropicLLMProvider(api_key="test-key", model="claude-test")

    async def test_generate(self) -> None:
        """generate() returns the text from response.content[0].text."""
        provider = self._make_provider()
        mock_response = _make_anthropic_response("Hello")

        with patch.object(
            provider._client.messages,
            "create",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await provider.generate("Say hello")

        assert result == "Hello"

    async def test_stream(self) -> None:
        """stream() yields each token from the underlying text_stream."""
        provider = self._make_provider()
        tokens = ["Hello", " world"]

        async def _fake_text_stream() -> AsyncIterator[str]:
            for tok in tokens:
                yield tok

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.text_stream = _fake_text_stream()
        # Make it work as an async context manager
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch.object(
            provider._client.messages,
            "stream",
            return_value=mock_stream_ctx,
        ):
            collected: list[str] = []
            async for tok in provider.stream("Say hello"):
                collected.append(tok)

        assert collected == ["Hello", " world"]


# ---------------------------------------------------------------------------
# OpenAI LLM provider tests
# ---------------------------------------------------------------------------


class TestOpenAILLMProvider:
    """Tests for OpenAILLMProvider."""

    def _make_provider(self) -> OpenAILLMProvider:
        return OpenAILLMProvider(api_key="test-key", model="gpt-test")

    async def test_generate(self) -> None:
        """generate() returns choices[0].message.content when it is a string."""
        provider = self._make_provider()
        mock_response = _make_openai_chat_response("Hi")

        with patch.object(
            provider._client.chat.completions,
            "create",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await provider.generate("Say hi")

        assert result == "Hi"

    async def test_generate_none_content(self) -> None:
        """generate() returns an empty string when content is None."""
        provider = self._make_provider()
        mock_response = _make_openai_chat_response(None)

        with patch.object(
            provider._client.chat.completions,
            "create",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await provider.generate("Say hi")

        assert result == ""


# ---------------------------------------------------------------------------
# OpenAI embedding provider tests
# ---------------------------------------------------------------------------


class TestOpenAIEmbeddingProvider:
    """Tests for OpenAIEmbeddingProvider."""

    def _make_provider(
        self,
        dimensions: int = 1536,
        batch_size: int = 100,
    ) -> OpenAIEmbeddingProvider:
        return OpenAIEmbeddingProvider(
            api_key="test-key",
            dimensions=dimensions,
            batch_size=batch_size,
        )

    def test_dimensions(self) -> None:
        """dimensions property returns the value passed to the constructor."""
        provider = self._make_provider(dimensions=1536)
        assert provider.dimensions == 1536

    async def test_embed(self) -> None:
        """embed() returns the vectors from the API response."""
        provider = self._make_provider()
        expected_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_response = _make_openai_embedding_response(expected_vectors)

        with patch.object(
            provider._client.embeddings,
            "create",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await provider.embed(["text one", "text two"])

        assert result == expected_vectors

    async def test_embed_batching(self) -> None:
        """embed() with batch_size=2 calls _embed_batch twice for 3 inputs."""
        provider = self._make_provider(batch_size=2)

        # Each batch returns two 2-d vectors (or one for the final batch of 1)
        batch_results = [
            [[0.1, 0.2], [0.3, 0.4]],  # first batch: texts 0 & 1
            [[0.5, 0.6]],              # second batch: text 2
        ]
        call_count = 0

        async def _fake_embed_batch(batch: list[str]) -> list[list[float]]:
            nonlocal call_count
            result = batch_results[call_count]
            call_count += 1
            return result

        with patch.object(provider, "_embed_batch", side_effect=_fake_embed_batch):
            result = await provider.embed(["a", "b", "c"])

        assert call_count == 2
        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]


# ---------------------------------------------------------------------------
# Ollama LLM provider tests
# ---------------------------------------------------------------------------


class TestOllamaLLMProvider:
    """Tests for OllamaLLMProvider."""

    def _make_provider(self) -> OllamaLLMProvider:
        return OllamaLLMProvider(base_url="http://localhost:11434", model="llama-test")

    async def test_generate(self) -> None:
        """generate() extracts message.content from the JSON response."""
        provider = self._make_provider()
        mock_response = _make_httpx_response(
            {"message": {"content": "Hi"}, "done": True}
        )

        with patch.object(
            provider._client,
            "post",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await provider.generate("Say hi")

        assert result == "Hi"

    async def test_stream(self) -> None:
        """stream() yields content tokens from newline-delimited JSON lines."""
        provider = self._make_provider()

        # The newline-delimited JSON lines the server would return.
        lines = [
            json.dumps({"message": {"content": "Hello"}, "done": False}),
            json.dumps({"message": {"content": " world"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]

        async def _fake_aiter_lines() -> AsyncIterator[str]:
            for line in lines:
                yield line

        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_lines = _fake_aiter_lines

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch.object(
            provider._client,
            "stream",
            return_value=mock_stream_ctx,
        ):
            collected: list[str] = []
            async for tok in provider.stream("Say hello"):
                collected.append(tok)

        assert collected == ["Hello", " world"]


# ---------------------------------------------------------------------------
# Ollama embedding provider tests
# ---------------------------------------------------------------------------


class TestOllamaEmbeddingProvider:
    """Tests for OllamaEmbeddingProvider."""

    def _make_provider(self, dimensions: int = 768) -> OllamaEmbeddingProvider:
        return OllamaEmbeddingProvider(
            base_url="http://localhost:11434",
            model="nomic-embed-test",
            dimensions=dimensions,
        )

    def test_dimensions(self) -> None:
        """dimensions property returns the value passed to the constructor."""
        provider = self._make_provider(dimensions=768)
        assert provider.dimensions == 768

    async def test_embed(self) -> None:
        """embed() returns the embeddings list from the API response."""
        provider = self._make_provider()
        expected_vectors = [[0.1, 0.2], [0.3, 0.4]]
        mock_response = _make_httpx_response({"embeddings": expected_vectors})

        with patch.object(
            provider._client,
            "post",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await provider.embed(["text one", "text two"])

        assert result == expected_vectors
