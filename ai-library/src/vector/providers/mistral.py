# src/vector/providers/mistral.py

import httpx
from typing import List

from .base import EmbeddingProvider, EmbeddingProviderConfig


class MistralEmbeddingProvider(EmbeddingProvider):
    """Mistral API embedding provider."""

    DIMENSIONS = {
        "mistral-embed": 1024,
    }

    def __init__(self, config: EmbeddingProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.mistral.ai/v1"
        self.model = config.model or "mistral-embed"

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Mistral API."""
        if not self._api_key:
            raise ValueError(
                "Mistral API key not found. Set MISTRAL_API_KEY environment variable "
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
        return self.DIMENSIONS.get(self.model, 1024)
