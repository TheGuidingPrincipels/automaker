# src/vector/providers/base.py

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class EmbeddingProviderConfig(BaseModel):
    """Configuration for an embedding provider."""
    provider: str                     # "mistral", "openai", "cohere", "local"
    model: str                        # Model name/ID
    api_key: Optional[str] = None     # Can be None if using env var
    api_key_env_var: Optional[str] = None  # e.g., "MISTRAL_API_KEY"
    base_url: Optional[str] = None    # Optional custom endpoint
    dimensions: Optional[int] = None  # Expected embedding dimensions


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: EmbeddingProviderConfig):
        self.config = config
        self._api_key = self._resolve_api_key()

    def _resolve_api_key(self) -> Optional[str]:
        """Resolve API key from config or environment variable."""
        import os

        # Direct config takes precedence
        if self.config.api_key:
            return self.config.api_key

        # Fall back to environment variable
        if self.config.api_key_env_var:
            return os.environ.get(self.config.api_key_env_var)

        # Default env var based on provider
        default_env_vars = {
            "mistral": "MISTRAL_API_KEY",
            "openai": "OPENAI_API_KEY",
            "cohere": "COHERE_API_KEY",
        }
        default_var = default_env_vars.get(self.config.provider)
        if default_var:
            return os.environ.get(default_var)

        return None

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed([text])
        return embeddings[0]

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions for this provider/model."""
        pass
