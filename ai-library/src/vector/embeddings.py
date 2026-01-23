# src/vector/embeddings.py

import asyncio
from typing import Optional, Union, Any

from ..utils.async_helpers import _run_sync
from .providers.base import EmbeddingProvider, EmbeddingProviderConfig
from .providers.mistral import MistralEmbeddingProvider
from .providers.openai import OpenAIEmbeddingProvider


class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""

    _providers = {
        "mistral": MistralEmbeddingProvider,
        "openai": OpenAIEmbeddingProvider,
        # Future: "cohere": CohereEmbeddingProvider,
        # Future: "local": LocalEmbeddingProvider,
    }

    @classmethod
    def create(cls, config: EmbeddingProviderConfig) -> EmbeddingProvider:
        """Create an embedding provider based on config."""
        provider_class = cls._providers.get(config.provider)
        if not provider_class:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown embedding provider: {config.provider}. "
                f"Available: {available}"
            )
        return provider_class(config)

    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a custom embedding provider."""
        cls._providers[name] = provider_class


def get_embedding_provider(
    config: Optional[Union[dict, "EmbeddingsConfig"]] = None
) -> EmbeddingProvider:
    """
    Get the configured embedding provider.

    Args:
        config: Optional config dict or EmbeddingsConfig. If not provided, loads from settings.

    Returns:
        Configured EmbeddingProvider instance.
    """
    if config is None:
        # Import here to avoid circular imports
        import asyncio
        from ..config import get_config

        # Get config synchronously if possible, otherwise fail fast with guidance
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, safe to create one
            app_config = asyncio.run(get_config())
            config = app_config.embeddings
        else:
            raise RuntimeError(
                "get_embedding_provider() cannot be called without a config inside an event loop. "
                "Use `await get_embedding_provider_async()` or pass `embedding_config`/`embeddings`."
            )

    # Handle dict config
    if isinstance(config, dict):
        provider_config = EmbeddingProviderConfig(**config)
    else:
        # Handle EmbeddingsConfig (Pydantic model)
        provider_config = EmbeddingProviderConfig(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            api_key_env_var=config.api_key_env_var,
            base_url=config.base_url,
            dimensions=config.dimensions,
        )

    return EmbeddingProviderFactory.create(provider_config)


async def get_embedding_provider_async(
    config: Optional[Union[dict, "EmbeddingsConfig"]] = None
) -> EmbeddingProvider:
    """
    Get the configured embedding provider (async version).

    Args:
        config: Optional config dict or EmbeddingsConfig. If not provided, loads from settings.

    Returns:
        Configured EmbeddingProvider instance.
    """
    if config is None:
        from ..config import get_config
        app_config = await get_config()
        config = app_config.embeddings

    # Handle dict config
    if isinstance(config, dict):
        provider_config = EmbeddingProviderConfig(**config)
    else:
        # Handle EmbeddingsConfig (Pydantic model)
        provider_config = EmbeddingProviderConfig(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            api_key_env_var=config.api_key_env_var,
            base_url=config.base_url,
            dimensions=config.dimensions,
        )

    return EmbeddingProviderFactory.create(provider_config)


class EmbeddingService:
    """Synchronous helper for generating embeddings."""

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        config: Optional[Union[dict, "EmbeddingsConfig"]] = None,
    ):
        self._provider = embedding_provider
        self._config = config

    @property
    def provider(self) -> EmbeddingProvider:
        if self._provider is None:
            self._provider = get_embedding_provider(self._config)
        return self._provider

    def embed(self, text: str) -> list[float]:
        """Generate a single embedding (sync)."""
        return _run_sync(self.provider.embed_single(text))

    async def embed_async(self, text: str) -> list[float]:
        """Generate a single embedding (async)."""
        return await self.provider.embed_single(text)
