from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

import openai


class OpenAILLMProvider:
    """OpenAI chat completion provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._model = model
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def generate(self, prompt: str) -> str:
        """Generate a text response for the given prompt."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        return content if content is not None else ""


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider with batching and retry logic."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        batch_size: int = 100,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._client = openai.AsyncOpenAI(api_key=api_key)

    @property
    def dimensions(self) -> int:
        """Return the embedding dimensionality."""
        return self._dimensions

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        """Embed a single batch of texts with retry logic."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=batch,
            dimensions=self._dimensions,
        )
        return [item.embedding for item in response.data]

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        """Embed a list of texts, batching requests by batch_size."""
        embeddings: list[list[float]] = []
        for start in range(0, len(inputs), self._batch_size):
            batch = inputs[start : start + self._batch_size]
            batch_embeddings = await self._embed_batch(batch)
            embeddings.extend(batch_embeddings)
        return embeddings
