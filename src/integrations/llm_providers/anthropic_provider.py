from __future__ import annotations

from collections.abc import AsyncIterator

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential


class AnthropicLLMProvider:
    """Anthropic Claude chat completion provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self._model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def generate(self, prompt: str) -> str:
        """Generate a text response for the given prompt."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def stream(self, prompt: str, *, max_tokens: int = 4096) -> AsyncIterator[str]:
        """Stream text tokens for the given prompt."""
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
