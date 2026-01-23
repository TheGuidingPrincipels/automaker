# tests/test_vector_providers.py
"""Tests for embedding providers."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.vector.providers.base import EmbeddingProvider, EmbeddingProviderConfig
from src.vector.providers.mistral import MistralEmbeddingProvider
from src.vector.providers.openai import OpenAIEmbeddingProvider
from src.vector.embeddings import EmbeddingProviderFactory, get_embedding_provider


class TestEmbeddingProviderConfig:
    """Tests for EmbeddingProviderConfig."""

    def test_create_config_with_defaults(self):
        """Create config with minimal required fields."""
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
        )

        assert config.provider == "mistral"
        assert config.model == "mistral-embed"
        assert config.api_key is None
        assert config.api_key_env_var is None
        assert config.base_url is None
        assert config.dimensions is None

    def test_create_config_with_all_fields(self):
        """Create config with all fields."""
        config = EmbeddingProviderConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
            api_key_env_var="CUSTOM_API_KEY",
            base_url="https://custom.api.com",
            dimensions=1536,
        )

        assert config.provider == "openai"
        assert config.api_key == "test-key"
        assert config.base_url == "https://custom.api.com"


class TestEmbeddingProvider:
    """Tests for EmbeddingProvider base class."""

    def test_resolve_api_key_from_config(self):
        """API key from config takes precedence."""
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
            api_key="config-key",
        )
        provider = MistralEmbeddingProvider(config)

        assert provider._api_key == "config-key"

    def test_resolve_api_key_from_custom_env_var(self, monkeypatch):
        """API key from custom env var."""
        monkeypatch.setenv("CUSTOM_KEY", "env-custom-key")
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
            api_key_env_var="CUSTOM_KEY",
        )
        provider = MistralEmbeddingProvider(config)

        assert provider._api_key == "env-custom-key"

    def test_resolve_api_key_from_default_env_var(self, monkeypatch):
        """API key from default provider env var."""
        monkeypatch.setenv("MISTRAL_API_KEY", "env-mistral-key")
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
        )
        provider = MistralEmbeddingProvider(config)

        assert provider._api_key == "env-mistral-key"

    def test_resolve_api_key_missing(self, monkeypatch):
        """Missing API key returns None."""
        # Ensure env vars are not set
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
        )
        provider = MistralEmbeddingProvider(config)

        assert provider._api_key is None


class TestMistralEmbeddingProvider:
    """Tests for MistralEmbeddingProvider."""

    def test_dimensions_mistral_embed(self):
        """Mistral-embed returns 1024 dimensions."""
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
            api_key="test-key",
        )
        provider = MistralEmbeddingProvider(config)

        assert provider.dimensions == 1024

    def test_default_base_url(self):
        """Default base URL is Mistral API."""
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
            api_key="test-key",
        )
        provider = MistralEmbeddingProvider(config)

        assert provider.base_url == "https://api.mistral.ai/v1"

    def test_custom_base_url(self):
        """Custom base URL is used."""
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
            api_key="test-key",
            base_url="https://custom.mistral.com",
        )
        provider = MistralEmbeddingProvider(config)

        assert provider.base_url == "https://custom.mistral.com"

    @pytest.mark.asyncio
    async def test_embed_requires_api_key(self, monkeypatch):
        """Embed raises error without API key."""
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
        )
        provider = MistralEmbeddingProvider(config)

        with pytest.raises(ValueError, match="Mistral API key not found"):
            await provider.embed(["test text"])

    @pytest.mark.asyncio
    async def test_embed_calls_api(self):
        """Embed calls Mistral API correctly."""
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
            api_key="test-key",
        )
        provider = MistralEmbeddingProvider(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            embeddings = await provider.embed(["text1", "text2"])

            assert len(embeddings) == 2
            assert embeddings[0] == [0.1, 0.2, 0.3]
            assert embeddings[1] == [0.4, 0.5, 0.6]


class TestOpenAIEmbeddingProvider:
    """Tests for OpenAIEmbeddingProvider."""

    def test_dimensions_3_small(self):
        """text-embedding-3-small returns 1536 dimensions."""
        config = EmbeddingProviderConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
        )
        provider = OpenAIEmbeddingProvider(config)

        assert provider.dimensions == 1536

    def test_dimensions_3_large(self):
        """text-embedding-3-large returns 3072 dimensions."""
        config = EmbeddingProviderConfig(
            provider="openai",
            model="text-embedding-3-large",
            api_key="test-key",
        )
        provider = OpenAIEmbeddingProvider(config)

        assert provider.dimensions == 3072

    def test_default_base_url(self):
        """Default base URL is OpenAI API."""
        config = EmbeddingProviderConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
        )
        provider = OpenAIEmbeddingProvider(config)

        assert provider.base_url == "https://api.openai.com/v1"

    @pytest.mark.asyncio
    async def test_embed_requires_api_key(self, monkeypatch):
        """Embed raises error without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = EmbeddingProviderConfig(
            provider="openai",
            model="text-embedding-3-small",
        )
        provider = OpenAIEmbeddingProvider(config)

        with pytest.raises(ValueError, match="OpenAI API key not found"):
            await provider.embed(["test text"])


class TestEmbeddingProviderFactory:
    """Tests for EmbeddingProviderFactory."""

    def test_create_mistral_provider(self):
        """Create Mistral provider."""
        config = EmbeddingProviderConfig(
            provider="mistral",
            model="mistral-embed",
            api_key="test-key",
        )
        provider = EmbeddingProviderFactory.create(config)

        assert isinstance(provider, MistralEmbeddingProvider)

    def test_create_openai_provider(self):
        """Create OpenAI provider."""
        config = EmbeddingProviderConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
        )
        provider = EmbeddingProviderFactory.create(config)

        assert isinstance(provider, OpenAIEmbeddingProvider)

    def test_create_unknown_provider_raises(self):
        """Unknown provider raises ValueError."""
        config = EmbeddingProviderConfig(
            provider="unknown",
            model="some-model",
        )

        with pytest.raises(ValueError, match="Unknown embedding provider"):
            EmbeddingProviderFactory.create(config)

    def test_register_custom_provider(self):
        """Register custom provider."""
        class CustomProvider(EmbeddingProvider):
            async def embed(self, texts):
                return [[0.0] * 128 for _ in texts]

            @property
            def dimensions(self):
                return 128

        EmbeddingProviderFactory.register("custom", CustomProvider)

        config = EmbeddingProviderConfig(
            provider="custom",
            model="custom-model",
        )
        provider = EmbeddingProviderFactory.create(config)

        assert isinstance(provider, CustomProvider)


class TestGetEmbeddingProvider:
    """Tests for get_embedding_provider function."""

    def test_get_provider_from_dict_config(self):
        """Get provider from dict config."""
        config = {
            "provider": "mistral",
            "model": "mistral-embed",
            "api_key": "test-key",
        }
        provider = get_embedding_provider(config)

        assert isinstance(provider, MistralEmbeddingProvider)

    def test_get_provider_from_embeddings_config(self):
        """Get provider from EmbeddingsConfig model."""
        from src.config import EmbeddingsConfig

        config = EmbeddingsConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
        )
        provider = get_embedding_provider(config)

        assert isinstance(provider, OpenAIEmbeddingProvider)

    @pytest.mark.asyncio
    async def test_get_provider_without_config_in_async_context_raises_clear_error(self):
        """
        Calling the sync helper without config inside an event loop must not call asyncio.run().
        """
        with pytest.raises(RuntimeError, match="get_embedding_provider_async"):
            get_embedding_provider()
