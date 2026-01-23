# src/vector/providers/openai.py

import httpx
from typing import List

from .base import EmbeddingProvider, EmbeddingProviderConfig


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI API embedding provider."""

    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, config: EmbeddingProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.model = config.model or "text-embedding-3-small"

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not self._api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or provide api_key in config."
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            return [item["embedding"] for item in data["data"]]

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS.get(self.model, 1536)
