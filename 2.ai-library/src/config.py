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
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])
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


async def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file (async)."""
    path = anyio.Path(config_path or "configs/settings.yaml")
    if await path.exists():
        text = await path.read_text()
        # Run YAML parsing in a thread to avoid blocking the event loop
        data = await anyio.to_thread.run_sync(yaml.safe_load, text)
        return Config(**data) if data else Config()

    return Config()


async def get_config() -> Config:
    """Get the global configuration instance (async)."""
    return await load_config()
