# src/config.py

import os
from typing import Optional
import yaml
from pydantic import BaseModel, Field
import anyio


class LibraryConfig(BaseModel):
    path: str = "./library"
    index_file: str = "_index.yaml"


class SessionsConfig(BaseModel):
    path: str = "./sessions"
    auto_save: bool = True


class SDKConfig(BaseModel):
    model: str = Field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-opus-4-5-20251101"))
    max_turns: int = 6
    auth_token_env_var: str = "ANTHROPIC_AUTH_TOKEN"


class SafetyConfig(BaseModel):
    require_all_resolved: bool = True
    verify_before_execute: bool = True
    verify_after_execute: bool = True
    backup_before_write: bool = True
    require_explicit_discard: bool = True
    forbid_merges_in_strict: bool = True


class ExtractionConfig(BaseModel):
    confidence_threshold: float = 0.8
    max_block_size: int = 5000
    preserve_code_blocks: bool = True


class CleanupConfig(BaseModel):
    default_disposition: str = "keep"
    allow_split_suggestions: bool = True
    allow_format_suggestions: bool = True


class StrictConfig(BaseModel):
    canonicalization_version: str = "v1"
    code_blocks_byte_strict: bool = True


class ContentConfig(BaseModel):
    default_mode: str = "strict"


class SourceConfig(BaseModel):
    deletion_behavior: str = "confirm"


# Phase D: REST API Configuration
class APIConfig(BaseModel):
    """Configuration for REST API server."""
    host: str = "0.0.0.0"
    port: int = 8001
    # Both localhost and 127.0.0.1 variants are needed because browsers treat them
    # as different origins - some browsers resolve 'localhost' to the hostname while
    # others resolve it to the IP address 127.0.0.1. CORS requires exact origin match.
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:3007",   # Automaker Vite dev server (hostname)
        "http://localhost:3008",   # Automaker backend (self, for swagger etc)
        "http://localhost:5173",   # Vite alternate port
        "http://localhost:5174",   # Vite alt port
        "http://127.0.0.1:3007",   # Automaker Vite dev server (IP variant)
        "http://127.0.0.1:3008",   # Automaker backend (IP variant)
    ])
    cors_methods: list[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    cors_headers: list[str] = Field(default_factory=lambda: ["Content-Type", "Authorization", "X-Request-ID"])
    debug: bool = False


# Phase 3A: Vector Infrastructure Configuration
class EmbeddingsConfig(BaseModel):
    """Configuration for embedding providers."""
    provider: str = "mistral"
    model: str = "mistral-embed"
    api_key: Optional[str] = None
    api_key_env_var: Optional[str] = None
    base_url: Optional[str] = None
    dimensions: Optional[int] = None


class VectorConfig(BaseModel):
    """Configuration for Qdrant vector store."""
    url: str = "localhost"
    port: int = 6333
    api_key: Optional[str] = None
    collection_name: str = "knowledge_library"


class ChunkingConfig(BaseModel):
    """Configuration for semantic chunking."""
    min_tokens: int = 512
    max_tokens: int = 2048
    overlap_tokens: int = 128
    strategy: str = "semantic"  # "semantic" | "fixed" | "sentence"


# Phase 3B: Intelligence Layer Configuration
class ClassificationConfig(BaseModel):
    """Configuration for two-tier classification."""
    fast_tier_confidence_threshold: float = 0.75
    new_category_confidence_threshold: float = 0.85
    auto_approve_level3_plus: bool = True
    max_content_length_for_llm: int = 2000


class RankingConfig(BaseModel):
    """Configuration for composite ranking."""
    similarity_weight: float = 0.6
    taxonomy_weight: float = 0.25
    recency_weight: float = 0.15
    recency_half_life_days: float = 30.0


class TaxonomyConfig(BaseModel):
    """Configuration for taxonomy management."""
    config_path: str = "configs/taxonomy.yaml"
    centroids_cache_dir: str = "data/centroids"
    min_samples_for_centroid: int = 3


class Config(BaseModel):
    library: LibraryConfig = Field(default_factory=LibraryConfig)
    sessions: SessionsConfig = Field(default_factory=SessionsConfig)
    sdk: SDKConfig = Field(default_factory=SDKConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)
    strict: StrictConfig = Field(default_factory=StrictConfig)
    content: ContentConfig = Field(default_factory=ContentConfig)
    source: SourceConfig = Field(default_factory=SourceConfig)
    # Phase 3A additions
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    vector: VectorConfig = Field(default_factory=VectorConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    # Phase D additions
    api: APIConfig = Field(default_factory=APIConfig)
    # Phase 3B additions
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    ranking: RankingConfig = Field(default_factory=RankingConfig)
    taxonomy: TaxonomyConfig = Field(default_factory=TaxonomyConfig)

    @property
    def library_path(self) -> str:
        return self.library.path


def _get_env_value(name: str) -> Optional[str]:
    """Get environment variable value, treating empty as unset."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _get_env_int(name: str) -> Optional[int]:
    value = _get_env_value(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as e:
        raise ValueError(f"{name} must be an integer") from e


def _apply_env_overrides(config: Config) -> Config:
    api_host = _get_env_value("API_HOST")
    if api_host is not None:
        config.api.host = api_host

    api_port = _get_env_int("API_PORT")
    if api_port is not None:
        config.api.port = api_port

    library_path = _get_env_value("LIBRARY_PATH")
    if library_path is not None:
        config.library.path = library_path

    sessions_path = _get_env_value("SESSIONS_PATH")
    if sessions_path is not None:
        config.sessions.path = sessions_path

    return config


async def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file (async)."""
    path = anyio.Path(config_path or "configs/settings.yaml")
    if await path.exists():
        text = await path.read_text()
        # Run YAML parsing in a thread to avoid blocking the event loop
        data = await anyio.to_thread.run_sync(yaml.safe_load, text)
        config = Config(**data) if data else Config()
        return _apply_env_overrides(config)

    return _apply_env_overrides(Config())


async def get_config() -> Config:
    """Get the global configuration instance (async)."""
    return await load_config()
